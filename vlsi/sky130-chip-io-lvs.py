#!/usr/bin/env python3
"""Prepare a full-chip IO diagnostic with physical connections and strict stdcells.

Existing chip inputs/results remain untouched. Run the resulting run.sh in
the CAD shell. IO M1-M4 dimensions are omitted unless explicitly enabled.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import shlex

from hammer.technology.sky130.lvs_netlists import (
    IO_HIERARCHY_EXPANSIONS, SCHEMATIC_PATH, patch_pegasus_generic_poly,
    patch_pegasus_pwell, patch_pegasus_pw_diode, spice_subcircuits,
)
from hammer.technology.sky130.lvs_translate import translate_libraries


IO_SUPPLIES = {
    "VDDIO": "VDDIO", "VDDIO_Q": "VDDIO", "VSWITCH": "VDDIO",
    "VSSIO": "VSS", "VSSIO_Q": "VSS", "VSSD": "VSS", "VSSA": "VSS",
    "VCCD": "VDD", "VCCHIB": "VDD", "VDDA": "VDDA",
}


def complete_nc_supplies(text):
    """Diagnostic copy of the PG export expected after fixing the CPF domain.

    Only the exact unused wrapped-pad instances are eligible. Existing ports
    and every other instance remain unchanged; conflicting supplies fail.
    """
    pattern = re.compile(
        r"(\bsky130_ef_io__gpiov2_pad_wrapped\s+(\\nc_\d+/iocell)\s*\()(.*?)(\);)", re.S)
    repairs = {}
    def replace(match):
        connections = dict(re.findall(r"\.(\w+)\s*\(([^()]*)\)", match[3]))
        for pin, net in IO_SUPPLIES.items():
            if pin in connections and connections[pin].strip() != net:
                raise ValueError(f"Conflicting {pin} connection in {match[2]}")
        missing = {pin: net for pin, net in IO_SUPPLIES.items() if pin not in connections}
        if not missing:
            return match[0]
        repairs[match[2]] = missing
        return (match[1] + match[3].rstrip() + ",\n"
                + ",\n".join(f"\t.{pin}({net})" for pin, net in missing.items()) + match[4])
    return pattern.sub(replace, text), repairs


def prepare(source_run, output, *, expand_io_tops=False, diffusion_properties=False,
            repair_hv_diffusion=False, complete_nc_pg=False, exclude_physical_decaps=False,
            chip_verilog=None, chip_gds=None, check_io_metal_dimensions=False,
            classify_io_shorts=False, partition_padiso_rings=False,
            padiso_ring_width_tolerance=0, expand_padiso_wrappers=False):
    if partition_padiso_rings and not (classify_io_shorts and check_io_metal_dimensions):
        raise ValueError("PADISO partition requires explicit SHORT classification and real-metal checks")
    if padiso_ring_width_tolerance and not partition_padiso_rings:
        raise ValueError("PADISO width policy requires the partition candidate")
    if expand_padiso_wrappers and not partition_padiso_rings:
        raise ValueError("PADISO wrapper expansion requires the partition candidate")
    source_run, output = source_run.resolve(), output.resolve()
    config = json.loads((source_run / "config_db_tmp.json").read_text())
    original_cdl = source_run / "sky130.pegasus.lvs.cdl"
    original_manifest = json.loads(original_cdl.with_suffix(".json").read_text())
    source_paths = []
    for entry in original_manifest["sources"]:
        path = Path(entry["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Source changed since the saved chip comparison: {path}")
        source_paths.append(path)
    original_control = (source_run / "pegasuslvsctl").read_text()
    if chip_verilog is not None:
        chip_verilog = chip_verilog.resolve(strict=True)
        original_control, count = re.subn(
            r'(schematic_path ")[^"\n]+(" verilog\b)',
            lambda match: match[1] + str(chip_verilog) + match[2], original_control)
        if count != 1:
            raise ValueError("Expected exactly one original chip Verilog input")
    if chip_gds is not None:
        chip_gds = chip_gds.resolve(strict=True)
        original_control, count = re.subn(
            r'(layout_path ")[^"\n]+(";)',
            lambda match: match[1] + str(chip_gds) + match[2], original_control)
        if count != 1:
            raise ValueError("Expected exactly one original chip GDS input")
    if re.search(r"^\s*virtual_connect\b|^\s*lvs_join_nets\b", original_control, re.M):
        raise ValueError("Expected a physical-only input control file")
    output.mkdir(parents=True, exist_ok=False)
    cdl = output / original_cdl.name
    manifest = translate_libraries(source_paths, cdl, preserve_esd_subtypes=True)
    # The assembled-context test must not introduce additional source edits.
    normalized = cdl.read_text().replace("nfet_g5v0d10v5_esd", "nfet_g5v0d10v5").replace(
        "pfet_g5v0d10v5_esd", "pfet_g5v0d10v5")
    if normalized != original_cdl.read_text():
        raise ValueError("Regenerated source differs beyond the experimental ESD subtype names")
    metal_cells = {}
    for block in spice_subcircuits(normalized):
        hits = re.findall(r"^R\S+\s+\S+\s+\S+\s+res_generic_m[1-5]\b",
                          normalized[block.start:block.end], re.M | re.I)
        if hits:
            if not re.match(r"sky130_(?:fd|ef)_io__", block.name):
                raise ValueError(f"Metal dimension policy would affect a non-IO cell: {block.name}")
            metal_cells[block.name] = len(hits)
    helpers = runpy.run_path(str(Path(__file__).with_name("sky130-io-lvs.py")))
    source_deck = Path(config["technology.sky130.lvs_deck"])
    deck = patch_pegasus_pw_diode(patch_pegasus_generic_poly(patch_pegasus_pwell(source_deck.read_text())))
    deck = helpers["esd_candidate"](helpers["poly_bend_candidate"](helpers["metal_candidate"](deck)))
    if diffusion_properties:
        deck = helpers["diffusion_candidate"](deck)
    if repair_hv_diffusion:
        if not diffusion_properties:
            raise ValueError("HV diffusion/bend experiment requires --diffusion-properties")
        deck = helpers["diffusion_bend_candidate"](helpers["hv_diffusion_candidate"](deck))
    # Preserve the original 0% checks for all ordinary MOS and generic poly,
    # including Cadence stdcells/HVL. Only explicit ESD subtypes get 7%/1%.
    deck = helpers["reference_candidate"](
        deck, ordinary_mos_tolerance=0, poly_tolerance=0,
        check_metal_dimensions=check_io_metal_dimensions)
    short_changes = {}
    if classify_io_shorts:
        if not check_io_metal_dimensions:
            raise ValueError("SHORT classification requires strict real-metal dimension checks")
        source, short_changes = helpers["classify_source_shorts"](cdl.read_text())
        if not short_changes:
            raise ValueError("No explicitly annotated IO SHORTs found")
        cdl.write_text(source)
        deck = helpers["split_short_marker_candidate"](deck)
    ring_changes = {}
    if partition_padiso_rings:
        ring = runpy.run_path(str(Path(__file__).with_name("sky130-m3-ring-lvs.py")))
        source, ring_changes = ring["classify_padiso_rings"](cdl.read_text())
        if set(ring_changes) != ring["PADISO_CELLS"]:
            raise ValueError("Expected all four qualified PADISO source definitions")
        cdl.write_text(source)
        deck = ring["partition_ring_deck"](deck, width_tolerance=padiso_ring_width_tolerance)
    deck_path = output / "chip-io-diagnostic.pvl"
    deck_path.write_text(deck)
    control = original_control.replace(str(source_run), str(output))
    nc_repairs = {}
    if complete_nc_pg:
        verilog = re.findall(r'schematic_path "([^"\n]+)" verilog\b', control)
        if len(verilog) != 1:
            raise ValueError("Expected one chip Verilog input")
        text, nc_repairs = complete_nc_supplies(Path(verilog[0]).read_text())
        if not nc_repairs:
            raise ValueError("No missing unused-pad supply ports found")
        copy = output / "ChipTop.pg-complete.lvs.v"
        copy.write_text(text)
        control = control.replace(f'"{verilog[0]}" verilog', f'"{copy}" verilog')
    if exclude_physical_decaps:
        # These two Cadence cells are already excluded from the source by
        # the technology's physical-only policy. Keep their MOS caps out of
        # the layout comparison without filtering functional MOS devices.
        for cell in ["FILL_DECAP8", "FILL_DECAP16"]:
            control += f"\nlvs_black_box {cell} -layout;\nlvs_filter_device {cell} -open -layout;\n"
    for cell in manifest["source_only_placeholders"]:
        control += f"\nlvs_black_box {cell} -source;\nlvs_filter_device {cell} -open -source;\n"
    available = {name.casefold() for name in manifest["cell_sources"]}
    expansions = [name for name in IO_HIERARCHY_EXPANSIONS if name in available]
    if expand_io_tops:
        # In chip context, 44 pad wrappers promote 31 native FETs each and
        # XRES promotes four: all 1,368 appear unmatched at ChipTop. Supply
        # pad PADISO pin labels also make incomplete local cut points.
        tops = ["sky130_ef_io__gpiov2_pad_wrapped", "sky130_fd_io__top_xres4v2",
                "sky130_fd_io__top_power_lvc_wpad", "sky130_fd_io__top_ground_lvc_wpad"]
        expansions.extend(name for name in tops if name in available)
    if expand_padiso_wrappers:
        # Eight supply wrappers each lose two local layout rings when the
        # partition derivation promotes them to ChipTop (64 segments -> 16 R).
        # Retain both complete circuits and compare them at that common level.
        wrappers = ["sky130_ef_io__vssa_hvc_clamped_pad", "sky130_ef_io__vdda_hvc_clamped_pad"]
        if not all(name in available for name in wrappers):
            raise ValueError("Expected both PADISO wrapper definitions")
        expansions.extend(wrappers)
    control += "\nlvs_exclude_hcell " + " ".join(expansions) + ";\n"
    control += ("lvs_filter_option RC RB -device R (res_generic_m1) -source_layout;\n"
                "lvs_report_max -all;\n")
    if classify_io_shorts:
        control += "lvs_filter_option RC RB -device R (res_io_short_m1) -source_layout;\n"
    if partition_padiso_rings:
        control += ('lvs_write_netlist -layout "chip.ring.layout.cdl";\n'
                    'lvs_write_netlist -source "chip.ring.source.cdl";\n')
    assert not re.search(r"^\s*virtual_connect\b|^\s*lvs_join_nets\b", control, re.M)
    assert list(SCHEMATIC_PATH.finditer(control))[0][1] == str(cdl)
    (output / "control.pvl").write_text(control)
    command = [config["lvs.pegasus.pegasus_bin"], "-lvs", "-dp", "2", "-automatch",
               "-check_schematic", "-rc_data", "-ui_data", "-control", "control.pvl", str(deck_path)]
    script = output / "run.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\nexec '
                      + shlex.join(command) + ' "$@"\n')
    script.chmod(0o755)
    (output / "experiment.json").write_text(json.dumps({
        "source_run": str(source_run), "source_deck": str(source_deck),
        "metal_source_cells": metal_cells, "cell_count": manifest["cell_count"],
        "io_hierarchy_expansions": expansions,
        "diffusion_property_candidate": diffusion_properties,
        "hv_diffusion_gap_and_bend_candidate": repair_hv_diffusion,
        "nc_supply_export_repairs": nc_repairs,
        "chip_verilog_override": str(chip_verilog) if chip_verilog is not None else None,
        "chip_gds_override": str(chip_gds) if chip_gds is not None else None,
        "exclude_layout_physical_decaps": exclude_physical_decaps,
        "ordinary_mos_tolerance_percent": 0, "generic_poly_tolerance_percent": 0,
        "esd_w_l_tolerance_percent": [7, 1], "io_m5_tolerance_percent": 1,
        "io_m1_m4_tolerance_percent": 0 if check_io_metal_dimensions else None,
        "annotated_io_short_model_changes": short_changes,
        "padiso_ring_model_changes": ring_changes,
        "padiso_ring_l_w_tolerance_percent": [0, padiso_ring_width_tolerance] if partition_padiso_rings else None,
        "expand_padiso_wrapper_boundaries": expand_padiso_wrappers,
        "limitations": [
            ("IO M1-M4 W/L checked at 0%; geometry diagnostic, not signoff"
             if check_io_metal_dimensions else
             "IO M1-M4 dimensions omitted; this is not geometric signoff"),
            "IO M1 dangling/self-loop filtering is diagnostic",
            ("M1-M4 annotated SHORTs have distinct subtypes; their nominal W/L are not compared"
             if classify_io_shorts else "SHORT markers and real metal resistors share subtypes"),
            "optional diffusion property macro is a geometry candidate requiring validation",
            ("PADISO ring equivalent model is a segment approximation; full-chip projection/orientation validation pending"
             if partition_padiso_rings else "PADISO ring partition candidate disabled"),
            ("PADISO-only 5% equivalent-width bound is a compatibility policy, not literal geometric signoff"
             if padiso_ring_width_tolerance else "No PADISO equivalent-width tolerance relaxation"),
            ("NC supply completion is a diagnostic source edit" if complete_nc_pg else
             "NC supply connections taken from the selected Verilog without edits"),
            "uses the selected chip GDS with its existing PoR view; this helper does not regenerate streams",
            "SRAM and PoR errors are retained and remain outside this IO investigation",
        ],
    }, indent=2) + "\n")
    print(f"Prepared physical-context chip diagnostic: {script}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expand-io-tops", action="store_true")
    parser.add_argument("--diffusion-properties", action="store_true")
    parser.add_argument("--repair-hv-diffusion", action="store_true")
    parser.add_argument("--complete-nc-supplies", action="store_true")
    parser.add_argument("--exclude-physical-decaps", action="store_true")
    parser.add_argument("--check-io-metal-dimensions", action="store_true",
                        help="Check IO M1-M4 W/L at 0%% to diagnose the remaining geometry differences")
    parser.add_argument("--classify-io-shorts", action="store_true",
                        help="Distinguish annotated IO SHORTs from real M1-M4 resistors")
    parser.add_argument("--partition-padiso-rings", action="store_true")
    parser.add_argument("--expand-padiso-wrappers", action="store_true")
    parser.add_argument("--padiso-ring-width-tolerance", type=int, choices=[0, 5], default=0,
                        help="PADISO equivalent-width policy only; length remains 0%%")
    parser.add_argument("--chip-verilog", type=Path,
                        help="Use an actual regenerated P&R netlist instead of the saved export")
    parser.add_argument("--chip-gds", type=Path, help="Use an actual regenerated verification stream")
    args = parser.parse_args()
    prepare(args.source_run, args.output, expand_io_tops=args.expand_io_tops,
            diffusion_properties=args.diffusion_properties,
            repair_hv_diffusion=args.repair_hv_diffusion,
            complete_nc_pg=args.complete_nc_supplies,
            exclude_physical_decaps=args.exclude_physical_decaps,
            chip_verilog=args.chip_verilog, chip_gds=args.chip_gds,
            check_io_metal_dimensions=args.check_io_metal_dimensions,
            classify_io_shorts=args.classify_io_shorts,
            partition_padiso_rings=args.partition_padiso_rings,
            padiso_ring_width_tolerance=args.padiso_ring_width_tolerance,
            expand_padiso_wrappers=args.expand_padiso_wrappers)
