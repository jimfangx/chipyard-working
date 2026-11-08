#!/usr/bin/env python3
"""Prepare a small original-PDK pad comparison with M3 ring property probes."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import shlex

from hammer.technology.sky130.lvs_translate import translate_libraries
from hammer.technology.sky130.lvs_netlists import spice_subcircuits

from hammer.technology.sky130.lvs_compat import (
    classify_padiso_rings, partition_ring_deck
)


PADISO_CELLS = frozenset("sky130_fd_io__" + name for name in (
    "top_ground_hvc_wpad", "top_power_hvc_wpadv2",
    "top_ground_lvc_wpad", "top_power_lvc_wpad",
))






def prepare(source_run, output, *, partition_rings=False,
            cell="sky130_fd_io__top_power_lvc_wpad"):
    if cell not in PADISO_CELLS:
        raise ValueError(f"Unsupported PADISO qualification cell: {cell}")
    source_run, output = source_run.resolve(), output.resolve()
    experiment = json.loads((source_run / "experiment.json").read_text())
    config = json.loads((Path(experiment["source_run"]) / "config_db_tmp.json").read_text())
    manifest = json.loads((source_run / "sky130.pegasus.lvs.json").read_text())
    sources = []
    for entry in manifest["sources"]:
        path = Path(entry["path"])
        if path.name not in {"sky130_fd_io.spice", "sky130_ef_io.cdl"}:
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"IO source changed since the chip run: {path}")
        sources.append(path)
    if len(sources) != 2:
        raise ValueError("Expected the two original FD/EF IO source libraries")
    gds = Path(config["technology.sky130.sky130A"]) / "libs.ref/sky130_fd_io/gds/sky130_fd_io.gds"
    deck = (source_run / "chip-io-diagnostic.pvl").read_text()
    original = "cmacro RES_PROPERTIES met3_res met3"
    if deck.count(original) != 1:
        raise ValueError("Expected one M3 property macro call")
    # Keep the existing W/L computation and checks exactly; these additional
    # values expose the recognition area and each terminal's contact length.
    deck = deck.replace(original, "cmacro IO_M3_RING_PROBE met3_res met3")
    deck += """
dmacro IO_M3_RING_PROBE dev_shape term_shape {
    [
    PROPERTY l, w, ring_area, ring_perimeter, ring_contact_p, ring_contact_n
    w = PERIMETER_COINCIDE(dev_shape, term_shape) / 2
    l = AREA(dev_shape) / w
    ring_area = AREA(dev_shape)
    ring_perimeter = PERIMETER(dev_shape)
    ring_contact_p = PERIMETER_COINCIDE(dev_shape, P)
    ring_contact_n = PERIMETER_COINCIDE(dev_shape, N)
    ]
}
"""
    if partition_rings:
        deck = partition_ring_deck(deck)
    output.mkdir(parents=True, exist_ok=False)
    cdl = output / "io.cdl"
    translate_libraries(sources, cdl, preserve_esd_subtypes=True)
    helpers = runpy.run_path(str(Path(__file__).with_name("sky130-io-lvs.py")))
    source, changes = helpers["classify_source_shorts"](cdl.read_text())
    ring_changes = {}
    if partition_rings:
        source, ring_changes = classify_padiso_rings(source)
    cdl.write_text(source)
    deck_path = output / "ring-probe.pvl"
    deck_path.write_text(deck)
    control = (f'schematic_path "{cdl}" cdl;\nschematic_primary {cell};\n'
               f'layout_path "{gds}";\nlayout_primary {cell};\n'
               'lvs_report_file "cell.lvs_results";\nlvs_report_max -all;\n'
               'results_db -erc "cell.erc_errors.ascii" -ascii;\n'
               'report_summary -erc "cell.erc_results" -replace;\n'
               'lvs_write_netlist -layout "ring.layout.cdl";\n'
               'lvs_write_netlist -source "ring.source.cdl";\n'
               'lvs_inconsistent_reduction_threshold -none;\n')
    for placeholder in ("sky130_fd_io__com_pad", "sky130_fd_io__condiode"):
        control += f"lvs_black_box {placeholder} -source;\nlvs_filter_device {placeholder} -open -source;\n"
    control += ("lvs_filter_option RC RB -device R (res_generic_m1) -source_layout;\n"
                "lvs_filter_option RC RB -device R (res_io_short_m1) -source_layout;\n"
                "// Standalone supply assumptions from the previously validated pad case.\n"
                "// These virtual connections do not establish chip power continuity.\n"
                "virtual_connect -depth all;\n"
                f"virtual_connect -name VDDIO VSSIO VSSA -cell {cell};\n"
                "virtual_connect -report yes;\n")
    (output / "control.pvl").write_text(control)
    command = [config["lvs.pegasus.pegasus_bin"], "-lvs", "-dp", "2", "-automatch",
               "-check_schematic", "-rc_data", "-ui_data", "-control", "control.pvl", str(deck_path)]
    script = output / "run.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\nexec '
                      + shlex.join(command) + ' "$@"\n')
    script.chmod(0o755)
    (output / "experiment.json").write_text(json.dumps({
        "source_chip_run": str(source_run), "layout": str(gds), "primary": cell,
        "layout_sha256": hashlib.sha256(gds.read_bytes()).hexdigest(),
        "sources": [e for e in manifest["sources"] if e["path"] in {str(p) for p in sources}],
        "annotated_io_short_model_changes": changes,
        "changes_m3_w_l_computation": partition_rings,
        "padiso_model_changes": ring_changes,
        "ring_dimension_tolerance_percent": 0,
        "limitations": ["Standalone same-name virtual supply connections; no chip continuity claim",
                        "M3 properties are diagnostic; no geometry repair or pass is claimed",
                        "Partition candidate is qualified only for this isolated R0 pad",
                        "Segment resistance approximation omits detailed corner-field solving"],
    }, indent=2) + "\n")
    print(f"Prepared original-PDK M3 ring probe: {script}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--partition-rings", action="store_true",
                        help="Test parallel-segment ring properties with strict equivalent L/W checks")
    parser.add_argument("--cell", choices=sorted(PADISO_CELLS),
                        default="sky130_fd_io__top_power_lvc_wpad")
    args = parser.parse_args()
    prepare(args.source_run, args.output, partition_rings=args.partition_rings, cell=args.cell)
