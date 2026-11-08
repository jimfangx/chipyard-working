#!/usr/bin/env python3
"""Compare the configured and optional alternate PoR GDS with one saved LVS source/deck."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil

from hammer.technology.sky130.lvs_netlists import spice_subcircuits

from hammer.technology.sky130.lvs_compat import (
    mim2_candidate, diffusion_terminal_candidate
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


COMPONENTS = {
    "cap_m3": "sky130_fd_pr__cap_mim_m3_1_WRT4AW",
    "cap_m4": "sky130_fd_pr__cap_mim_m3_2_W5U4AW",
    "schmitt": "sky130_fd_sc_hvl__schmittbuf_1",
    "resistors": "sky130_fd_pr__res_xhigh_po_0p69_S5N9F3",
}






def prepare(source_run, output, alternate_gds=None, components_and_mim=False, refine_components=False):
    components_and_mim = components_and_mim or refine_components
    source_run, output = source_run.resolve(), output.resolve()
    experiment = json.loads((source_run / "experiment.json").read_text())
    config = json.loads((Path(experiment["source_run"]) / "config_db_tmp.json").read_text())
    manifest = json.loads((source_run / "sky130.pegasus.lvs.json").read_text())
    source = Path(manifest["cell_sources"]["simple_por"])
    entry = next(item for item in manifest["sources"] if item["path"] == str(source))
    if sha256(source) != entry["sha256"]:
        raise ValueError("PoR source changed since the completed chip comparison")
    libraries = [item["library"] for item in config["vlsi.technology.extra_libraries"]
                 if item.get("library", {}).get("spice_file") == str(source)]
    if len(libraries) != 1:
        raise ValueError("Expected exactly one configured library for the saved PoR source")
    layouts = {"configured": Path(libraries[0]["gds_file"]).resolve()}
    if alternate_gds is not None:
        layouts["alternate"] = alternate_gds.resolve()
    # Validate original GDS roots before preparing any run directories.
    import gdspy
    layout_cells = {}
    for path in layouts.values():
        lib = gdspy.GdsLibrary(); lib.read_gds(str(path))
        if "simple_por" not in lib.cell_dict:
            raise ValueError(f"Missing simple_por layout root: {path}")
        layout_cells[str(path)] = set(lib.cell_dict)
    cdl = source_run / "sky130.pegasus.lvs.cdl"
    source_cells = {block.name for block in spice_subcircuits(cdl.read_text())}
    if "simple_por" not in source_cells:
        raise ValueError("Missing simple_por in saved compiled source")
    output.mkdir(parents=True, exist_ok=False)
    deck = output / "por-diagnostic.pvl"
    shutil.copy2(source_run / "chip-io-diagnostic.pvl", deck)
    cases = [(label, gds, "simple_por", "simple_por", deck) for label, gds in layouts.items()]
    candidate_deck = None
    if components_and_mim:
        candidate_deck = output / "por-mim2-candidate.pvl"
        candidate_deck.write_text(mim2_candidate(deck.read_text()))
        gds = layouts["configured"]
        cases = []
        for label, cell in COMPONENTS.items():
            source_cell = "BC_" + cell
            if cell not in layout_cells[str(gds)] or source_cell not in source_cells:
                raise ValueError(f"Missing PoR component root: {cell} / {source_cell}")
            if not refine_components:
                cases.append(("baseline/" + label, gds, source_cell, cell, deck))
            if label in ("cap_m3", "cap_m4"):
                cases.append(("mim2/" + label, gds, source_cell, cell, candidate_deck))
        cases.append(("mim2/por", gds, "simple_por", "simple_por", candidate_deck))
        if refine_components:
            terminal_deck = output / "por-terminal-candidate.pvl"
            terminal_deck.write_text(diffusion_terminal_candidate(deck.read_text()))
            combined_deck = output / "por-combined-candidate.pvl"
            combined_deck.write_text(diffusion_terminal_candidate(candidate_deck.read_text()))
            cell = COMPONENTS["schmitt"]
            cases.extend([("terminals/schmitt", gds, "BC_" + cell, cell, terminal_deck),
                          ("combined/por", gds, "simple_por", "simple_por", combined_deck)])
    commands = ['#!/usr/bin/env bash', 'set -euo pipefail', 'cd -- "$(dirname -- "$0")"']
    for label, gds, schematic_primary, layout_primary, case_deck in cases:
        case = output / label
        case.mkdir(parents=True)
        (case / "control.pvl").write_text(
            f'schematic_path "{cdl}" cdl;\nschematic_primary {schematic_primary};\n'
            f'layout_path "{gds}";\nlayout_primary {layout_primary};\n'
            'lvs_report_file "cell.lvs_results";\nlvs_report_max -all;\n'
            'results_db -erc "cell.erc_errors.ascii" -ascii;\n'
            'report_summary -erc "cell.erc_results" -replace;\n'
            'lvs_write_netlist -layout "layout.cdl";\n'
            'lvs_write_netlist -source "source.cdl";\n'
            'lvs_inconsistent_reduction_threshold -none;\n')
        command = [config["lvs.pegasus.pegasus_bin"], "-lvs", "-dp", "2", "-automatch",
                   "-check_schematic", "-rc_data", "-ui_data", "-control", "control.pvl", str(case_deck)]
        script = case / "run.sh"
        script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\nexec '
                          + shlex.join(command) + ' "$@"\n')
        script.chmod(0o755)
        commands.append(f'bash {shlex.quote(label + "/run.sh")} "$@"')
    script = output / "run-all.sh"
    script.write_text("\n".join(commands) + "\n")
    script.chmod(0o755)
    (output / "experiment.json").write_text(json.dumps({
        "source_diagnostic_run": str(source_run), "source_run": experiment["source_run"],
        "source_library": entry,
        "compiled_source": {"path": str(cdl), "sha256": sha256(cdl)},
        "deck_sha256": sha256(deck),
        "mim2_candidate_deck_sha256": sha256(candidate_deck) if candidate_deck else None,
        "cases": [{"name": label, "schematic_primary": sch, "layout_primary": lay,
                   "deck": str(case_deck), "deck_sha256": sha256(case_deck)}
                  for label, _, sch, lay, case_deck in cases],
        "layouts": {label: {"path": str(path), "sha256": sha256(path)}
                    for label, path in layouts.items()},
        "changes_source_or_tolerances": False,
        "changes_extraction": components_and_mim,
        "adds_virtual_connections_filters_or_blackboxes": False,
        "limitations": ["Isolated PoR input comparison; excludes chip placement and routing",
                        "Use chip-context extraction to diagnose added placement/routing shorts",
                        "Unlabeled component roots can have standalone pin mismatches; inspect raw extracted devices",
                        "The copied deck retains the preceding diagnostic compatibility policies"],
    }, indent=2) + "\n")
    print(f"Prepared PoR diagnostics: {script}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--alternate-gds", type=Path)
    parser.add_argument("--components-and-mim", action="store_true",
                        help="Isolate four original components and test a second-MIM extraction candidate")
    parser.add_argument("--refine-components", action="store_true",
                        help="Test refined MIM electrodes and gate-cut diffusion-resistor terminals")
    args = parser.parse_args()
    prepare(args.source_run, args.output, args.alternate_gds, args.components_and_mim, args.refine_components)
