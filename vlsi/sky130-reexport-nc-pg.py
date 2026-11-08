#!/usr/bin/env python3
"""Prepare an Innovus netlist re-export for the saved Sky130 unused-pad PG fix.

The generated run opens a saved database and repairs NC pad PG bindings in
memory. It can also add the reviewed quiet-rail tie and export a separate GDS.
It never saves the DB or runs placement/routing optimization.
"""

import argparse
import json
from pathlib import Path
import re
import runpy
import shlex
import sys


def tcl_word(value):
    value = str(value)
    if any(char in value for char in "{}\n\r\\"):
        raise ValueError(f"Unsupported Tcl path/name: {value}")
    return "{" + value + "}"


def database_restore_tcl(database):
    # The saved SRAM Liberty files changed since this DB was written. Scope
    # the file-check override to this diagnostic restore, including errors.
    return ("# Diagnostic export: permit changed saved SRAM Liberty files during restore only.\n"
            "set nc_pg_saved_file_check [get_db read_db_file_check]\n"
            "set_db read_db_file_check false\n"
            "set nc_pg_restore_status [catch {\n"
            f"    read_db -no_binary_constraint {tcl_word(database)}\n"
            "} nc_pg_restore_message nc_pg_restore_options]\n"
            "set_db read_db_file_check $nc_pg_saved_file_check\n"
            "if {$nc_pg_restore_status} {\n"
            "    return -options $nc_pg_restore_options $nc_pg_restore_message\n"
            "}\n")


def prepare(par_run, output, *, tie_quiet_vddio=False):
    par_run, output = par_run.resolve(), output.resolve()
    config = json.loads((par_run / "config_db_tmp.json").read_text())
    if config["technology.sky130.stdcell_library"] != "sky130_scl":
        raise ValueError("This export helper is qualified for the saved Cadence SCL run only")
    database = (par_run / "post_write_chiptop_netlist_with_pg_pins").resolve(strict=True)
    helpers = runpy.run_path(str(Path(__file__).with_name("sky130-chip-io-lvs.py")))
    source = par_run / "ChipTop.lvs.v"
    _, repairs = helpers["complete_nc_supplies"](source.read_text())
    if not repairs:
        raise ValueError("The source export has no missing NC supplies")
    names = sorted(name.removeprefix("\\") for name in repairs)
    if any(not re.fullmatch(r"nc_\d+/iocell", name) for name in names):
        raise ValueError("Unexpected NC instance name")
    physical = ["FILL1", "FILL2", "FILL4", "FILL8", "FILL16", "FILL32", "FILL64",
                "FILL_DECAP8", "FILL_DECAP16", "ANTENNA"]
    mode = config["par.inputs.physical_only_cells_mode"]
    manual = config["par.inputs.physical_only_cells_list"]
    if mode == "manual":
        physical = manual
    elif mode == "append":
        physical += manual
    elif mode != "auto":
        raise ValueError(f"Unknown physical-only mode: {mode}")
    # Same IO exclusions as write_chiptop_netlist_with_pg_pins in hammer-driver.
    physical += ["sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_and_vssio_vssa_vssd_slice_20um",
                 *[f"sky130_ef_io__com_bus_slice_{width}um" for width in [1, 5, 10, 20]],
                 "sky130_ef_io__corner_pad"]
    output.mkdir(parents=True, exist_ok=False)
    netlist = output / "ChipTop.lvs.v"
    tcl = (f"set nc_pg_output {tcl_word(netlist)}\n"
           'if {[file exists $nc_pg_output]} { error "Refusing to overwrite the new netlist" }\n'
           + database_restore_tcl(database) +
           f"set nc_pg_names [list {' '.join(tcl_word(name) for name in names)}]\n"
           "foreach nc_pg_name $nc_pg_names {\n"
           "    set nc_pg_inst [get_db insts $nc_pg_name]\n"
           "    if {[llength $nc_pg_inst] != 1} { error \"Missing/ambiguous pad $nc_pg_name\" }\n"
           "    if {[get_db $nc_pg_inst .base_cell.name] ne \"sky130_ef_io__gpiov2_pad_wrapped\"} {\n"
           "        error \"Unexpected master for $nc_pg_name\"\n"
           "    }\n"
           "}\n")
    # Enumerate only the ports absent from the saved export. VDDA, existing
    # functional connections and all other instances are left unchanged.
    for escaped_name, pins in sorted(repairs.items()):
        name = escaped_name.removeprefix("\\")
        for pin, net in pins.items():
            tcl += (f"connect_global_net {net} -type pg_pin -pin_base_name {pin} "
                    f"-single_inst {tcl_word(name)} -netlist_override -verbose\n")
    gds = None
    if tie_quiet_vddio:
        tie = Path(__file__).with_name("sky130-quiet-vddio.tcl").resolve()
        tcl += f"source {tcl_word(tie)}\n"
        streams = [line for line in (par_run / "par.tcl").read_text().splitlines()
                   if line.startswith("write_stream ") and line.rstrip().endswith("_drc_lvs.gds")]
        if len(streams) != 1:
            raise ValueError("Expected one original verification stream command")
        original_stream, original_gds = streams[0].rsplit(None, 1)
        if not Path(original_gds).is_file():
            raise ValueError("Original verification GDS no longer exists")
        gds = output / "ChipTop_drc_lvs.gds"
        tcl += original_stream + " " + tcl_word(gds) + "\n"
        tcl += "write_def " + tcl_word(output / "ChipTop.def") + "\n"
    tcl += ("write_netlist $nc_pg_output -top_module_first -top_module ChipTop "
            "-exclude_leaf_cells -phys -flat -exclude_insts_of_cells "
            + tcl_word(" ".join(dict.fromkeys(physical))) + "\n"
            'puts "NC PG export written to $nc_pg_output; saved database was not modified"\n'
            "exit\n")
    (output / "reexport.tcl").write_text(tcl)
    command = [config["par.innovus.innovus_bin"], "-stylus", "-no_gui", "-files",
               str(output / "reexport.tcl"), "-log", str(output / "innovus.log")]
    checker = output / "check_export.py"
    checker.write_text('''from pathlib import Path
import json, re
root = Path(__file__).resolve().parent
manifest = json.loads((root / "export.json").read_text())
text = Path(manifest["output_netlist"]).read_text()
pattern = re.compile(r"\\bsky130_ef_io__gpiov2_pad_wrapped\\s+(\\\\nc_\\d+/iocell)\\s*\\((.*?)\\);", re.S)
instances = {m[1]: dict(re.findall(r"\\.(\\w+)\\s*\\(([^()]*)\\)", m[2])) for m in pattern.finditer(text)}
if set(instances) != set(manifest["nc_supply_connections"]):
    raise ValueError("The exported NC pad set differs from the saved design")
for name, ports in instances.items():
    for pin, net in manifest["expected_io_supplies"].items():
        if ports.get(pin, "").strip() != net:
            raise ValueError(f"Incorrect/missing {pin} on {name}")
def logical_instances(source):
    pattern = re.compile(r"^\\s*([A-Za-z_$][\\w$]*)\\s+(\\\\[^\\s]+|[A-Za-z_$][\\w$]*)\\s*\\((.*?)\\);", re.M | re.S)
    result = {}
    for match in pattern.finditer(source):
        master, name = match[1], match[2]
        ports = {pin: " ".join(expr.split()) for pin, expr in re.findall(r"\\.(\\w+)\\s*\\(([^()]*)\\)", match[3])}
        if not ports or master in manifest["excluded_cells"]:
            continue
        if name in manifest["nc_supply_connections"]:
            ports.update(manifest["expected_io_supplies"])
        if name in result:
            raise ValueError(f"Duplicate exported instance {name}")
        result[name] = (master, ports)
    return result
before = logical_instances(Path(manifest["source_netlist"]).read_text())
after = logical_instances(text)
if not before or before != after:
    changed = sorted(name for name in set(before) | set(after) if before.get(name) != after.get(name))
    raise ValueError(f"Unexpected logical connectivity changes: {changed[:10]}")
print(f"Verified all supply connections on {len(instances)} NC pads")
print(f"Verified unchanged logic and bus connections for {len(before)} instances")
''')
    run = output / "run.sh"
    run.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\n'
                   + shlex.join(command) + '\nexec '
                   + shlex.join([sys.executable, str(checker)]) + '\n')
    run.chmod(0o755)
    (output / "export.json").write_text(json.dumps({
        "source_netlist": str(source), "saved_database": str(database),
        "output_netlist": str(netlist), "nc_supply_connections": repairs,
        "expected_io_supplies": helpers["IO_SUPPLIES"],
        "excluded_cells": list(dict.fromkeys(physical)),
        "saves_database": False, "changes_routing": tie_quiet_vddio,
        "runs_placement_or_routing_optimization": False,
        "output_gds": str(gds) if gds is not None else None,
        "binary_timing_constraints": False,
    }, indent=2) + "\n")
    if gds is not None:
        lvs = output / "lvs"
        lvs_helper = Path(__file__).with_name("sky130-chip-io-lvs.py").resolve()
        lvs_command = [sys.executable, str(lvs_helper),
                       "--source-run", str(par_run.parent / "lvs-rundir"),
                       "--output", str(lvs), "--chip-verilog", str(netlist),
                       "--chip-gds", str(gds), "--expand-io-tops", "--diffusion-properties",
                       "--repair-hv-diffusion", "--exclude-physical-decaps"]
        (output / "verify.sh").write_text(
            '#!/usr/bin/env bash\nset -euo pipefail\n'
            + "if [[ ! -f " + shlex.quote(str(lvs / "control.pvl")) + " ]]; then\n  "
            + shlex.join(lvs_command) + "\nfi\nexec bash " + shlex.quote(str(lvs / "run.sh")) + "\n")
        (output / "run_and_lvs.sh").write_text(
            '#!/usr/bin/env bash\nset -euo pipefail\nbash '
            + shlex.quote(str(run)) + "\nexec bash " + shlex.quote(str(output / "verify.sh")) + "\n")
    print(f"Prepared {sum(map(len, repairs.values()))} PG connections on {len(names)} pads: {run}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--par-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tie-quiet-vddio", action="store_true")
    args = parser.parse_args()
    prepare(args.par_run, args.output, tie_quiet_vddio=args.tie_quiet_vddio)
