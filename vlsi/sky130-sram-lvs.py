#!/usr/bin/env python3
"""Audit SRAM22 source namespaces and prepare a strict hierarchy diagnostic."""

import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import shlex
import shutil

from hammer.technology.sky130.lvs_netlists import spice_subcircuits
from hammer.technology.sky130.lvs_translate import instance, logical_lines

from hammer.technology.sky130.lvs_compat import (
    edge_device_candidate, circuit_fingerprints, namespace_audit
)


MACROS = ("sram22_64x22m4w22", "sram22_64x24m4w8",
          "sram22_512x32m4w8", "sram22_512x64m4w8")
BITCELLS = ("sram_sp_cell", "sram_sp_cell_replica", "sram_sp_colend", "sram_sp_hstrap")








def prepare(source_run, output):
    source_run, output = source_run.resolve(), output.resolve()
    experiment = json.loads((source_run / "experiment.json").read_text())
    config = json.loads((Path(experiment["source_run"]) / "config_db_tmp.json").read_text())
    manifest = json.loads((source_run / "sky130.pegasus.lvs.json").read_text())
    matches = [entry for entry in manifest["sources"] if Path(entry["path"]).name == "sram22.spice"]
    if len(matches) != 1:
        raise ValueError("Expected exactly one saved SRAM22 aggregate source")
    entry = matches[0]
    library = Path(entry["path"])
    if hashlib.sha256(library.read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError("SRAM22 aggregate source changed since the comparison")
    aggregate = circuit_fingerprints(library.read_text())
    individuals, hashes = {}, {str(library): entry["sha256"]}
    for macro in MACROS:
        path = library.parent / macro / (macro + ".spice")
        raw = path.read_bytes()
        individuals[macro] = circuit_fingerprints(raw.decode())
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
    audit = namespace_audit(aggregate, individuals)
    if not audit["excluded_internal_hcells"]:
        raise ValueError("No ambiguous SRAM internal names found")
    # Cadence SCL names come from a separate input; never expand these cells
    # merely because their spelling accidentally collides with a macro helper.
    scl = {name.casefold() for name, origin in manifest["cell_sources"].items()
           if "sky130_scl" in origin}
    if scl.intersection(audit["excluded_internal_hcells"]):
        raise ValueError("SRAM namespace expansion would affect Cadence SCL")
    output.mkdir(parents=True, exist_ok=False)
    for name in ("sky130.pegasus.lvs.cdl", "sky130.pegasus.lvs.json", "chip-io-diagnostic.pvl"):
        shutil.copy2(source_run / name, output / name)
    control = (source_run / "control.pvl").read_text().replace(str(source_run), str(output))
    control += ("\n// Expand ambiguous SRAM helper names; compare their full devices in the parent.\n"
                "lvs_exclude_hcell " + " ".join(audit["excluded_internal_hcells"]) + ";\n")
    (output / "control.pvl").write_text(control)
    command = [config["lvs.pegasus.pegasus_bin"], "-lvs", "-dp", "2", "-automatch",
               "-check_schematic", "-rc_data", "-ui_data", "-control", "control.pvl",
               str(output / "chip-io-diagnostic.pvl")]
    script = output / "run.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\nexec '
                      + shlex.join(command) + ' "$@"\n')
    script.chmod(0o755)
    audit.update({"source_run": str(source_run), "source_hashes": hashes,
                  "changes_source_devices_or_parameters": False,
                  "changes_extraction_or_tolerances": False,
                  "blackboxes_srams": False})
    (output / "namespace-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    experiment.update({"source_diagnostic_run": str(source_run),
                       "sram_namespace_exclusions": audit["excluded_internal_hcells"]})
    (output / "experiment.json").write_text(json.dumps(experiment, indent=2) + "\n")
    print(f"Prepared SRAM namespace diagnostic: {script}")
    print(f"Expanded {len(audit['excluded_internal_hcells'])} helper names from "
          f"{len(audit['ambiguous_internal_names'])} ambiguous families")


def prepare_bitcells(source_run, output):
    """Reproduce sizing errors on original library cells without a chip context."""
    source_run, output = source_run.resolve(), output.resolve()
    experiment = json.loads((source_run / "experiment.json").read_text())
    config = json.loads((Path(experiment["source_run"]) / "config_db_tmp.json").read_text())
    manifest = json.loads((source_run / "sky130.pegasus.lvs.json").read_text())
    entries = [e for e in manifest["sources"] if Path(e["path"]).name == "sram22.spice"]
    if len(entries) != 1:
        raise ValueError("Expected one SRAM22 source library")
    source = Path(entries[0]["path"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != entries[0]["sha256"]:
        raise ValueError("SRAM source library changed since the comparison")
    gds = source.parent / MACROS[0] / (MACROS[0] + ".gds")
    if not gds.is_file():
        raise ValueError(f"Missing original macro layout: {gds}")
    text = (source_run / "sky130.pegasus.lvs.cdl").read_text()
    definitions = {b.name.casefold(): text[b.start:b.end] for b in spice_subcircuits(text)}
    leaves = {}
    for cell in BITCELLS:
        body = definitions[cell]
        # These qualification roots must contain native devices only. A new
        # hierarchical source requires explicitly importing its dependencies.
        if any(line.lstrip().lower().startswith("x") for line in logical_lines(body)):
            raise ValueError(f"Qualification root is no longer a leaf: {cell}")
        leaves[cell] = body
    output.mkdir(parents=True, exist_ok=False)
    deck = output / "bitcell-diagnostic.pvl"
    shutil.copy2(source_run / "chip-io-diagnostic.pvl", deck)
    commands = ['#!/usr/bin/env bash', 'set -euo pipefail', 'cd -- "$(dirname -- "$0")"']
    for cell, body in leaves.items():
        case = output / cell
        case.mkdir()
        (case / "source.cdl").write_text(body)
        (case / "control.pvl").write_text(
            f'schematic_path "{case / "source.cdl"}" cdl;\nschematic_primary {cell};\n'
            f'layout_path "{gds}";\nlayout_primary {cell};\n'
            'lvs_report_file "cell.lvs_results";\nlvs_report_max -all;\n'
            'results_db -erc "cell.erc_errors.ascii" -ascii;\n'
            'report_summary -erc "cell.erc_results" -replace;\n'
            'lvs_write_netlist -layout "layout.cdl";\n'
            'lvs_write_netlist -source "compared-source.cdl";\n'
            'lvs_inconsistent_reduction_threshold -none;\n')
        command = [config["lvs.pegasus.pegasus_bin"], "-lvs", "-dp", "2", "-automatch",
                   "-check_schematic", "-rc_data", "-ui_data", "-control", "control.pvl", str(deck)]
        script = case / "run.sh"
        script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\nexec '
                          + shlex.join(command) + ' "$@"\n')
        script.chmod(0o755)
        commands.append(f'bash {shlex.quote(cell + "/run.sh")} "$@"')
    script = output / "run-all.sh"
    script.write_text("\n".join(commands) + "\n")
    script.chmod(0o755)
    (output / "experiment.json").write_text(json.dumps({
        "source_diagnostic_run": str(source_run), "source_run": experiment["source_run"],
        "layout": str(gds), "layout_sha256": hashlib.sha256(gds.read_bytes()).hexdigest(),
        "source_library": entries[0], "cells": list(BITCELLS),
        "deck_sha256": hashlib.sha256(deck.read_bytes()).hexdigest(),
        "changes_devices_parameters_extraction_or_tolerances": False,
        "changes_relative_to": str(source_run),
        "inherited_sram_edge_device_sizing": experiment.get("sram_edge_device_sizing"),
        "limitations": ["Isolated cell boundaries may differ from abutted array geometry",
                        "Local supply shorts may resolve in the macro parent",
                        "No virtual connections, blackboxes or device filtering added"],
    }, indent=2) + "\n")
    print(f"Prepared four original-cell SRAM comparisons: {script}")


def prepare_edge_devices(source_run, output):
    """Prepare both leaf and assembled-chip tests of one-sided gate sizing."""
    source_run, output = source_run.resolve(), output.resolve()
    experiment = json.loads((source_run / "experiment.json").read_text())
    if not experiment.get("sram_namespace_exclusions"):
        raise ValueError("Start from the completed SRAM namespace diagnostic")
    original = (source_run / "chip-io-diagnostic.pvl").read_text()
    candidate = edge_device_candidate(original)
    config = json.loads((Path(experiment["source_run"]) / "config_db_tmp.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    for name in ("sky130.pegasus.lvs.cdl", "sky130.pegasus.lvs.json"):
        shutil.copy2(source_run / name, output / name)
    deck = output / "chip-io-diagnostic.pvl"
    deck.write_text(candidate)
    (output / "control.pvl").write_text(
        (source_run / "control.pvl").read_text().replace(str(source_run), str(output)))
    command = [config["lvs.pegasus.pegasus_bin"], "-lvs", "-dp", "2", "-automatch",
               "-check_schematic", "-rc_data", "-ui_data", "-control", "control.pvl", str(deck)]
    script = output / "run.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\nexec '
                      + shlex.join(command) + ' "$@"\n')
    script.chmod(0o755)
    experiment.update({"source_diagnostic_run": str(source_run),
                       "sram_edge_device_sizing": {
                           "models": ["nfet_01v8", "pfet_01v8_hvt"],
                           "recognition": "orthogonal rectangle; one SD edge; three active-boundary edges",
                           "width": "full coincident SD perimeter", "length": "gate area / width",
                           "changes_source_or_tolerances": False,
                           "scope": "geometric classification across the layout; full-chip regression required",
                           "baseline_deck_sha256": hashlib.sha256(original.encode()).hexdigest(),
                           "candidate_deck_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
                       }})
    (output / "experiment.json").write_text(json.dumps(experiment, indent=2) + "\n")
    prepare_bitcells(output, output / "bitcells")
    script = output / "run-all.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\n'
                      'bash bitcells/run-all.sh "$@"\nbash run.sh "$@"\n')
    script.chmod(0o755)
    print(f"Prepared SRAM edge-device candidate (four leaf runs plus full chip): {script}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--qualify-bitcells", action="store_true",
                        help="Compare four original SRAM leaf cells with unchanged extraction")
    mode.add_argument("--edge-device-sizing", action="store_true",
                      help="Test geometry-derived one-sided MOS sizing on leaf cells and the full chip")
    args = parser.parse_args()
    action = prepare_edge_devices if args.edge_device_sizing else prepare_bitcells if args.qualify_bitcells else prepare
    action(args.source_run, args.output)
