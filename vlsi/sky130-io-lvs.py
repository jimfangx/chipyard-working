#!/usr/bin/env python3
"""Prepare independent IO LVS experiments without changing the chip reports.

Run with the project's Python/Hammer environment. Generated run.sh files invoke
Pegasus in an ordinary CAD shell. The metal and hierarchy variants are diagnostic
candidates, not additional production-deck repairs.
"""

import argparse
import difflib
import json
from pathlib import Path
import re
import shlex
import struct

from hammer.technology.sky130.lvs_netlists import (
    IO_HIERARCHY_EXPANSIONS, SCHEMATIC_PATH,
    patch_pegasus_generic_poly, patch_pegasus_pwell, patch_pegasus_pw_diode,
    spice_subcircuits,
)
from hammer.technology.sky130.lvs_translate import translate_libraries

from hammer.technology.sky130.lvs_compat import (
    metal_candidate, split_short_marker_candidate, classify_source_shorts, diffusion_candidate, hv_diffusion_candidate, diffusion_bend_candidate, poly_bend_candidate, esd_candidate, reference_candidate
)


FD = "sky130_fd_io__"
EF = "sky130_ef_io__"
CASES = [
    FD + "hvsbt_inv_x1", FD + "hvsbt_nor",
    FD + "gpiov2_amux_drvr_ls", FD + "gpiov2_amux_ctl_ls",
    FD + "tk_tie_r_out_esd", FD + "com_res_weak",
    FD + "signal_5_sym_hv_local_5term", FD + "gpiov2_buf_localesd",
    FD + "gnd2gnd_120x2_lv_isosub", FD + "gpiov2_amux",
    FD + "top_power_lvc_wpad", FD + "top_ground_lvc_wpad",
    EF + "gpiov2_pad_wrapped",
]


def assemble_wrapped_pad(io, output):
    """Merge the reachable original GDS records, including their properties."""
    cells = {}
    units = None
    library_header = []
    for index, library in enumerate(["sky130_ef_io__gpiov2_pad_wrapped", "sky130_ef_io", "sky130_fd_io"]):
        chunks, name, refs = None, None, set()
        seen_cell = False
        with (io / "gds" / (library + ".gds")).open("rb") as stream:
            while header := stream.read(4):
                length, kind, _ = struct.unpack(">HBB", header)
                if length < 4:
                    raise ValueError("Invalid GDS record length")
                payload = stream.read(length - 4)
                if len(payload) != length - 4:
                    raise ValueError("Truncated GDS record")
                record = header + payload
                if kind == 3:  # UNITS
                    if units is not None and units != payload:
                        raise ValueError("IO GDS input units disagree")
                    units = payload
                if kind == 5:  # BGNSTR
                    chunks, name, refs = [record], None, set()
                    seen_cell = True
                elif chunks is not None:
                    chunks.append(record)
                    if kind == 6:  # STRNAME
                        name = payload.rstrip(b"\0").decode("ascii")
                    elif kind == 18:  # SNAME
                        refs.add(payload.rstrip(b"\0").decode("ascii"))
                    elif kind == 7:  # ENDSTR
                        if name is None or name in cells:
                            raise ValueError(f"Missing or duplicate GDS cell name: {name}")
                        cells[name] = (b"".join(chunks), refs)
                        chunks = None
                elif index == 0 and not seen_cell and kind != 4:
                    library_header.append(record)
    selected = {}
    pending = [EF + "gpiov2_pad_wrapped"]
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        body, refs = cells[name]  # A missing referenced master must be fatal.
        selected[name] = body
        pending.extend(refs - selected.keys())
    with output.open("wb") as stream:
        stream.write(b"".join(library_header))
        for name in sorted(selected):
            stream.write(selected[name])
        stream.write(struct.pack(">HBB", 4, 4, 0))  # ENDLIB
















def pw_diode_candidate(text):
    """Test rejecting marker-only PW regions without an n+ diffusion body.

    Selection preserves the entire recognition polygon when a real terminal
    is present; it does not change the NW diode rules or terminal connectivity.
    """
    return patch_pegasus_pw_diode(text)






def prepare(args):
    source_run = args.source_run.resolve()
    config = json.loads((source_run / "config_db_tmp.json").read_text())
    io = Path(config["technology.sky130.sky130A"]) / "libs.ref/sky130_fd_io"
    source_deck = Path(config["technology.sky130.lvs_deck"])
    pegasus = config["lvs.pegasus.pegasus_bin"]
    sources = [io / "spice/sky130_fd_io.spice", io / "cdl/sky130_ef_io.cdl"]
    layouts = {cell: io / "gds" / (
        "sky130_ef_io__gpiov2_pad_wrapped.gds" if cell.startswith(EF)
        else "sky130_fd_io.gds") for cell in CASES}
    for path in [source_deck, *sources, *layouts.values()]:
        if not path.is_file():
            raise FileNotFoundError(path)

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    wrapped = output / "gpiov2_pad_wrapped.gds"
    assemble_wrapped_pad(io, wrapped)
    layouts[EF + "gpiov2_pad_wrapped"] = wrapped
    manifest = translate_libraries(sources, output / "io.cdl")
    translate_libraries(sources, output / "io-esd.cdl", preserve_esd_subtypes=True)
    generic = patch_pegasus_generic_poly(patch_pegasus_pwell(source_deck.read_text()))
    metal = metal_candidate(generic)
    (output / "deck-generic.pvl").write_text(generic)
    (output / "deck-pw-diode-candidate.pvl").write_text(pw_diode_candidate(generic))
    (output / "deck-metal-candidate.pvl").write_text(metal)
    (output / "deck-poly-bends-candidate.pvl").write_text(poly_bend_candidate(metal))
    (output / "deck-esd-candidate.pvl").write_text(
        reference_candidate(esd_candidate(poly_bend_candidate(metal))))
    (output / "deck-esd-pw-diode-candidate.pvl").write_text(
        pw_diode_candidate(reference_candidate(esd_candidate(poly_bend_candidate(metal)))))
    (output / "metal-candidate.patch").write_text("".join(difflib.unified_diff(
        generic.splitlines(True), metal.splitlines(True),
        fromfile="deck-generic.pvl", tofile="deck-metal-candidate.pvl")))
    controls = {}
    for variant in args.variants:
        policy = {"pw-context": "pw-diode", "reference-pw-context": "reference"}.get(variant, variant)
        for cell in args.cells:
            run = output / variant / cell
            run.mkdir(parents=True)
            controls[f"{variant}/{cell}"] = str(layouts[cell])
            reference = policy in ["reference", "supply-context", "supply-dangling"]
            schematic = output / ("io-esd.cdl" if reference else "io.cdl")
            text = (f'schematic_path "{schematic}" cdl;\n'
                    f'schematic_primary {cell};\n'
                    f'layout_path "{layouts[cell]}";\n'
                    f'layout_primary {cell};\n'
                    'lvs_report_file "cell.lvs_results";\n'
                    'results_db -erc "cell.erc_errors.ascii" -ascii;\n'
                    'report_summary -erc "cell.erc_results" -replace;\n'
                    'lvs_inconsistent_reduction_threshold -none;\n'
                    'lvs_report_max -all;\n')
            for placeholder in manifest["source_only_placeholders"]:
                text += (f"lvs_black_box {placeholder} -source;\n"
                         f"lvs_filter_device {placeholder} -open -source;\n")
            if policy in ["hierarchy", "context", "cleanup", "reference", "supply-context", "supply-dangling"] and cell in [FD + "gpiov2_amux", EF + "gpiov2_pad_wrapped"]:
                # Source instances expand into their parent comparison. Keep
                # the standalone native-FET leaf controls as independent tests.
                names = [FD + "gpiov2_amux_drvr_ls", FD + "gpiov2_amux_ctl_ls"]
                if cell.startswith(EF):
                    # Its native devices also climb across the inner EF pad.
                    names.extend([FD + "gpiov2_amux", EF + "gpiov2_pad"])
                if policy != "hierarchy":
                    names.append(FD + "signal_5_sym_hv_local_5term")
                text += "lvs_exclude_hcell " + " ".join(names) + ";\n"
            if policy in ["cleanup", "reference", "supply-context", "supply-dangling"]:
                # RC removes only a resistor whose two terminals already share
                # one net, on either side. It never joins different nets.
                text += "lvs_filter_option RC -device R (res_generic_m1) -source_layout;\n"
            if variant == "supply-dangling":
                # Diagnostic only: the two remaining ESD M1 R0 branches have
                # a far node with one primitive terminal and no top port.
                # RB removes a dangling resistor without joining its nets.
                text += "lvs_filter_option RB -device R (res_generic_m1) -source_layout;\n"
            if variant in ["supply-context", "supply-dangling"]:
                # Explicit standalone environment experiment. This must never
                # be copied into the chip signoff flow: real ring continuity
                # must be demonstrated with physical connections there.
                text += ("virtual_connect -depth all;\n"
                         "virtual_connect -name VDDIO VSSIO VSSA -cell sky130_ef_io__gpiov2_pad;\n"
                         "virtual_connect -report yes;\n")
            if variant in ["pw-context", "reference-pw-context"]:
                # Standalone boundary assumptions, separate from production:
                # Assume the connections that gnd2gnd's parent or the pad's
                # surrounding ring must supply in the assembled design.
                context_names = {
                    FD + "gnd2gnd_120x2_lv_isosub": "VSS_N",
                    FD + "top_power_lvc_wpad": "VDDIO VSSIO VSSA",
                    FD + "top_ground_lvc_wpad": "VDDIO VSSIO VSSA",
                }
                if cell not in context_names:
                    raise ValueError(f"No explicit standalone context labels for {cell}")
                text += ("virtual_connect -depth all;\n"
                         f"virtual_connect -name {context_names[cell]} -cell {cell};\n"
                         "virtual_connect -report yes;\n")
            (run / "control.pvl").write_text(text)
            deck = output / ("deck-esd-pw-diode-candidate.pvl" if variant == "reference-pw-context" else
                             "deck-generic.pvl" if policy == "generic" else
                             "deck-pw-diode-candidate.pvl" if policy == "pw-diode" else
                             "deck-esd-candidate.pvl" if reference else
                             "deck-poly-bends-candidate.pvl" if policy in ["poly-bends", "cleanup"] else
                             "deck-metal-candidate.pvl")
            command = [pegasus, "-lvs", "-dp", "2", "-automatch", "-check_schematic",
                       "-rc_data", "-ui_data", "-control", "control.pvl", str(deck)]
            script = ('#!/usr/bin/env bash\nset -euo pipefail\n'
                      'cd -- "$(dirname -- "$0")"\nexec ' + shlex.join(command) + ' "$@"\n')
            (run / "run.sh").write_text(script)
            (run / "run.sh").chmod(0o755)
            (run / "dr.mac").write_text(f'PVS::invoke_pvsrv("{run}");\n')
            view = [pegasus + "DesignReview", "-qrv", "-tech", "sky130", "-data",
                    str(layouts[cell]), "-post", str(run / "dr.mac"), "-verbose"]
            (run / "view.sh").write_text(
                '#!/usr/bin/env bash\nset -euo pipefail\n'
                'cd -- "$(dirname -- "$0")"\nexec ' + shlex.join(view) + '\n')

    (output / "suite.json").write_text(json.dumps({
        "source_run": str(source_run), "source_deck": str(source_deck),
        "layouts": controls,
        "limitations": [
            "metal candidate still has incorrect annular and short-marker dimensions",
            "isolated-cell pin/stamping errors must be checked in assembled context",
            "hierarchy exclusions include AMUX and the inner EF pad",
            "context variant also expands overlapping ESD cells; strict property checks remain enabled",
            "poly-bends is an unvalidated geometric length candidate; metal dimensions remain strict",
            "reference variant uses standalone IO-only subtype rules without cell lists; M1-M4 dimensions omitted",
            "supply-context virtually joins same-name supply labels only in the inner EF pad; not signoff",
            "supply-dangling additionally filters M1 resistors with a floating terminal on either side; no net joining",
            "pw-diode rejects PW marker regions lacking n+ diffusion; genuine PW diode preservation still needs qualification",
            "pw-context/reference-pw-context add explicit standalone VSS_N or supply-band ties; physical parent continuity remains to be checked",
        ],
    }, indent=2) + "\n")
    print(f"Prepared {len(controls)} independent runs under {output}")
    print("Run selected run.sh files in your CAD shell; inspect cell.lvs_results.cls and cell.lvs_results.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True,
                        help="Existing Hammer LVS run with config_db_tmp.json")
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory; existing directories are rejected")
    parser.add_argument("--cells", nargs="+", choices=CASES, default=CASES,
                        help="Optional subset of IO cell cases")
    parser.add_argument("--variants", nargs="+", choices=["generic", "pw-diode", "pw-context", "reference-pw-context", "metal", "hierarchy", "context", "poly-bends", "cleanup", "reference", "supply-context", "supply-dangling"],
                        default=["generic", "metal", "hierarchy"],
                        help="context additionally expands overlapping ESD leaf boundaries")
    prepare(parser.parse_args())
