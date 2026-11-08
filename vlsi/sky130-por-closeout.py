#!/usr/bin/env python3
"""Prepare strict PoR source correction, configured-GDS reexport and chip LVS."""

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import sys

from hammer.technology.sky130.lvs_netlists import spice_subcircuits
from hammer.technology.sky130.lvs_translate import translate_libraries

from hammer.technology.sky130.lvs_compat import (
    correct_por_source
)


CELL = "BC_sky130_fd_sc_hvl__schmittbuf_1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()




def write_run(path, command):
    path.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\nexec '
                    + shlex.join(command) + ' "$@"\n')
    path.chmod(0o755)


def prepare(source_run, export_run, output):
    source_run, export_run, output = source_run.resolve(), export_run.resolve(), output.resolve()
    exp = json.loads((source_run / "experiment.json").read_text())
    chip_run = Path(exp["source_diagnostic_run"])
    config = json.loads((Path(exp["source_run"]) / "config_db_tmp.json").read_text())
    report = (source_run / "combined/por/cell.lvs_results.cls").read_text()
    if "CONNECTIVITY MATCHES" not in report or report.count("(mip 1)") != 1 or "L: 1.355 u" not in report:
        raise ValueError("Expected the completed PoR connectivity match with its single length discrepancy")
    manifest = json.loads((chip_run / "sky130.pegasus.lvs.json").read_text())
    source = Path(exp["source_library"]["path"])
    if sha(source) != exp["source_library"]["sha256"]:
        raise ValueError("Original PoR source changed")
    configured_gds = Path(exp["layouts"]["configured"]["path"])
    if sha(configured_gds) != exp["layouts"]["configured"]["sha256"]:
        raise ValueError("Configured PoR GDS changed")
    pdk = Path(config["technology.sky130.sky130A"])
    canonical = pdk.parents[1] / "sources/sky130_fd_sc_hvl/cells/schmittbuf/sky130_fd_sc_hvl__schmittbuf_1"
    if not re.search(r"res_generic_nd__hv.*\bl=1\.355\b", canonical.with_suffix(".cdl").read_text()):
        raise ValueError("Original SkyWater CDL does not confirm 1.355 um")
    if "l=1.355e+06u" not in canonical.with_suffix(".spice").read_text():
        raise ValueError("Original SkyWater SPICE does not confirm 1.355 um")
    import gdspy
    geometries = []
    for path in (configured_gds, canonical.with_suffix(".gds")):
        lib = gdspy.GdsLibrary(); lib.read_gds(str(path))
        geometries.append(lib.cell_dict["sky130_fd_sc_hvl__schmittbuf_1"].get_polygons(by_spec=True))
    for layer in set(geometries[0]) | set(geometries[1]):
        a, b = (g.get(layer, []) for g in geometries)
        if not a or not b:
            if a or b:
                raise ValueError(f"PoR / canonical Schmitt geometry differs on {layer}")
        else:
            xor = gdspy.fast_boolean(a, b, "xor", precision=.000001, max_points=0)
            if xor is not None and xor.area() > 1e-10:
                raise ValueError(f"PoR / canonical Schmitt geometry differs on {layer}")
    output.mkdir(parents=True, exist_ok=False)
    fixed = output / "simple_por.spice"
    original = source.read_text()
    fixed.write_text(correct_por_source(original))
    patch = Path(__file__).with_name("sky130-lvs-por-source-precision.patch")
    patch.write_text("".join(difflib.unified_diff(original.splitlines(keepends=True), fixed.read_text().splitlines(keepends=True),
                                               fromfile="a/simple_por.spice", tofile="b/simple_por.spice")))
    # Independently regenerate the old/new PoR definitions, verifying the
    # complete family against the saved mixed-library CDL before replacing it.
    old_por, new_por = output / "original-por.cdl", output / "corrected-por.cdl"
    translate_libraries([source], old_por, preserve_esd_subtypes=True)
    translate_libraries([fixed], new_por, preserve_esd_subtypes=True)
    def definitions(text):
        return {b.name: text[b.start:b.end] for b in spice_subcircuits(text)}
    old_defs, new_defs = definitions(old_por.read_text()), definitions(new_por.read_text())
    if set(old_defs) != set(new_defs) or [n for n in old_defs if old_defs[n] != new_defs[n]] != [CELL]:
        raise ValueError("PoR correction changed other source definitions")
    old_cdl = (chip_run / "sky130.pegasus.lvs.cdl").read_text()
    blocks = list(spice_subcircuits(old_cdl))
    for b in blocks:
        if b.name in old_defs and old_cdl[b.start:b.end] != old_defs[b.name]:
            raise ValueError(f"Saved compiled PoR differs from original source: {b.name}")
    target = next(b for b in blocks if b.name == CELL)
    cdl = output / "sky130.pegasus.lvs.cdl"
    cdl.write_text(old_cdl[:target.start] + new_defs[CELL] + old_cdl[target.end:])
    for entry in manifest["sources"]:
        if entry["path"] == str(source):
            entry.update({"path": str(fixed), "sha256": sha(fixed), "original_source": str(source)})
    for cell, origin in manifest["cell_sources"].items():
        if origin == str(source):
            manifest["cell_sources"][cell] = str(fixed)
    (output / "sky130.pegasus.lvs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    deck = output / "por-combined-candidate.pvl"
    shutil.copy2(source_run / "por-combined-candidate.pvl", deck)
    isolated = output / "isolated"
    isolated.mkdir()
    (isolated / "control.pvl").write_text((source_run / "combined/por/control.pvl").read_text().replace(
        str(chip_run / "sky130.pegasus.lvs.cdl"), str(cdl)))
    pegasus = [config["lvs.pegasus.pegasus_bin"], "-lvs", "-dp", "2", "-automatch", "-check_schematic",
               "-rc_data", "-ui_data", "-control", "control.pvl", str(deck)]
    write_run(isolated / "run.sh", pegasus)
    checker = output / "check-isolated.py"
    checker.write_text("from pathlib import Path\nimport re\n"
                      "p=Path(__file__).resolve().parent/'isolated/cell.lvs_results.cls'\n"
                      "s=p.read_text()\n"
                      "assert re.search(r'Run Result\\s*:\\s*MATCH\\b',s), 'Isolated PoR still mismatches; inspect its report before chip reexport'\n"
                      "assert '[ERROR]' not in s, 'Isolated PoR has errors'\n"
                      "print('Isolated configured PoR matches strict comparison')\n")
    # Clone the previously successful in-memory NC/quiet-rail reexport. Only
    # output paths and the PoR merge input change; DB restore/ties stay exact.
    exported = output / "chip-export"
    exported.mkdir()
    tcl = (export_run / "reexport.tcl").read_text().replace(str(export_run), str(exported))
    streams = [line for line in tcl.splitlines() if line.startswith("write_stream ")]
    if len(streams) != 1:
        raise ValueError("Expected one verification stream in the successful reexport")
    por_paths = re.findall(r"\S*/simple_por(?:_drc_lvs)?\.gds", streams[0])
    if len(por_paths) != 1 or not Path(por_paths[0]).is_file():
        raise ValueError("Expected one existing PoR GDS in the saved merge command")
    if any(c.isspace() or c in "{}" for c in str(configured_gds)):
        raise ValueError("Unsupported configured GDS path in saved Tcl merge list")
    tcl = tcl.replace(por_paths[0], str(configured_gds))
    (exported / "reexport.tcl").write_text(tcl)
    shutil.copy2(export_run / "check_export.py", exported / "check_export.py")
    export_manifest = json.loads((export_run / "export.json").read_text().replace(str(export_run), str(exported)))
    export_manifest.update({"configured_por_gds": str(configured_gds), "configured_por_gds_sha256": sha(configured_gds)})
    (exported / "export.json").write_text(json.dumps(export_manifest, indent=2) + "\n")
    innovus = [config["par.innovus.innovus_bin"], "-stylus", "-no_gui", "-files", str(exported / "reexport.tcl"),
               "-log", str(exported / "innovus.log")]
    export_script = exported / "run.sh"
    export_script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\n'
                             + shlex.join(innovus) + "\nexec " + shlex.join([sys.executable, str(exported / "check_export.py")]) + "\n")
    export_script.chmod(0o755)
    full = output / "full-chip"
    full.mkdir()
    control = (chip_run / "control.pvl").read_text().replace(str(chip_run), str(full)).replace(str(export_run), str(exported))
    control = control.replace(str(full / "sky130.pegasus.lvs.cdl"), str(cdl))
    (full / "control.pvl").write_text(control)
    write_run(full / "run.sh", pegasus)
    script = output / "run-all.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\n'
                      'bash isolated/run.sh\n' + shlex.join([sys.executable, str(checker)]) + '\n'
                      'bash chip-export/run.sh\nbash full-chip/run.sh\n')
    script.chmod(0o755)
    (output / "experiment.json").write_text(json.dumps({
        "source_diagnostic_run": str(source_run), "source_chip_run": str(chip_run),
        "source_run": exp["source_run"], "source_export_run": str(export_run),
        "source_correction": {"cell": CELL, "instance": "X4", "old_length_um": 1.36, "new_length_um": 1.355,
                              "canonical_cdl": str(canonical.with_suffix('.cdl')), "canonical_spice": str(canonical.with_suffix('.spice')),
                              "canonical_cdl_sha256": sha(canonical.with_suffix('.cdl')), "canonical_spice_sha256": sha(canonical.with_suffix('.spice')),
                              "canonical_gds": str(canonical.with_suffix('.gds')), "canonical_gds_sha256": sha(canonical.with_suffix('.gds')),
                              "canonical_geometry_matches_por": True, "raw_source_sha256": sha(source), "corrected_source_sha256": sha(fixed)},
        "compiled_source_sha256": sha(cdl), "deck_sha256": sha(deck),
        "reexport_tcl_sha256": sha(exported / "reexport.tcl"), "full_chip_control_sha256": sha(full / "control.pvl"),
        "configured_por_gds": str(configured_gds), "old_export_por_gds": por_paths[0],
        "changes_tolerances_or_placement": False, "saves_database": False,
        "limitations": ["Prior IO compatibility policies retained", "Quiet-rail tie still needs DRC", "Production integration pending"],
    }, indent=2) + "\n")
    print(f"Prepared strict PoR check, configured-GDS chip reexport and full-chip LVS: {script}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--export-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_run, args.export_run, args.output)
