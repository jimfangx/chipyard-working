#!/usr/bin/env python3
"""Prepare LVS qualification for all imported clamps and a chip comparison.

Generation does not launch CAD. Original GDS/SPICE and completed reports are
read-only. Standalone supply-assumed tests are explicitly diagnostic; only
the chip-context case tests the physical chip connections without virtual ties.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import shlex
import sys

from hammer.technology.sky130.lvs_compat import io_clamp_cells, padiso_wrapper_roots
from hammer.technology.sky130.lvs_netlists import spice_subcircuits
from hammer.technology.sky130.lvs_translate import instance, logical_lines


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reachable_source(text, roots):
    """Copy complete reachable definitions verbatim, preserving their order."""
    blocks = list(spice_subcircuits(text))
    by_name = {b.name.casefold(): b for b in blocks}
    selected, pending = set(), [name.casefold() for name in roots]
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        if name not in by_name:
            raise ValueError(f"Unresolved isolated-clamp source master: {name}")
        selected.add(name)
        block = by_name[name]
        for line in logical_lines(text[block.start:block.end]):
            if line.lstrip().lower().startswith("x"):
                positional, _ = instance(line)
                pending.append(positional[-1].casefold())
    # Do not silently drop global statements or parameter definitions.
    outside, end = [], 0
    for block in blocks:
        outside.append(text[end:block.start])
        end = block.end
    outside.append(text[end:])
    if any(line.strip() and not line.lstrip().startswith("*")
           for line in "".join(outside).splitlines()):
        raise ValueError("Isolated source copying requires no executable global statements")
    return ("* Reachable definitions copied verbatim from the chip's generated LVS source.\n"
            + "\n".join(text[b.start:b.end] for b in blocks if b.name.casefold() in selected))


def exclusions(control):
    return {name for statement in re.findall(r"^lvs_exclude_hcell\s+([^;]+);", control, re.M)
            for name in statement.split()}


def case_control(control, directory, expanded, *, primary=None, layout=None, source=None):
    text = re.sub(r"^lvs_exclude_hcell\s+[^;]+;\s*", "", control, flags=re.M)
    text = re.sub(r"^lvs_write_netlist[^\n]*\n?", "", text, flags=re.M)
    for keyword in ("lvs_report_file", "results_db", "report_summary"):
        pattern = re.compile(r"(^" + keyword + r'[^\n]*?)"([^"\n]+)"', re.M)
        text = pattern.sub(lambda m: m[1] + '"' + str(directory / Path(m[2]).name) + '"', text)
    if primary:
        text = re.sub(r'^schematic_path\s+"[^"\n]+"\s+verilog[^;]*;\s*', "", text, flags=re.M)
        text, count = re.subn(r'^schematic_path\s+"[^"\n]+"\s+cdl[^;]*;',
                              lambda _: f'schematic_path "{source}" cdl;', text, flags=re.M)
        if count != 1:
            raise ValueError("Expected one compiled chip CDL input")
        text = re.sub(r"^(schematic_primary|layout_primary)\s+[^;]+;",
                      lambda m: f"{m[1]} {primary};", text, flags=re.M)
        text = re.sub(r'^layout_path\s+"[^"\n]+"[^;]*;',
                      lambda _: f'layout_path "{layout}";', text, flags=re.M)
        text = re.sub(r"^lvs_(?:power|ground)_name[^\n]*\n?", "", text, flags=re.M)
    names = sorted(name for name in expanded if not primary or name.casefold() != primary.casefold())
    if names:
        text += "\nlvs_exclude_hcell " + " ".join(names) + ";\n"
    text += (f'\nlvs_write_netlist -layout "{directory / "layout.cdl"}";\n'
             f'lvs_write_netlist -source "{directory / "source.cdl"}";\n')
    if re.search(r"^\s*(?:virtual_connect|lvs_join_nets)\b", text, re.M):
        raise ValueError("Unexpected virtual connection in original control")
    return text


def prepare(source_run, output, cells=None, *, include_chip_context=True, technology_cache=None):
    source_run, output = source_run.resolve(), output.resolve()
    if output.exists():
        raise ValueError("Use a new output directory to preserve completed experiments")
    config = json.loads((source_run / "config_db_tmp.json").read_text())
    manifest = json.loads((source_run / "sky130.pegasus.lvs.json").read_text())
    source = source_run / "sky130.pegasus.lvs.cdl"
    if sha(source) != manifest["compiled_cdl_sha256"]:
        raise ValueError("Compiled chip source differs from its manifest")
    raw = source.read_text()
    roots = padiso_wrapper_roots(raw)
    wrappers = sorted(roots)
    cells = io_clamp_cells(raw) if cells is None else cells
    if not cells:
        raise ValueError("No clamp definitions selected for qualification")
    if not set(cells) <= set(wrappers):
        raise ValueError("Requested clamp is not a wrapper around a qualified PADISO pad")
    for entry in manifest["sources"]:
        if Path(entry["path"]).name in {"sky130_fd_io.spice", "sky130_ef_io.cdl"}:
            if sha(entry["path"]) != entry["sha256"]:
                raise ValueError(f"Original IO source revision changed: {entry['path']}")
    old_control = (source_run / "pegasuslvsctl").read_text()
    baseline = exclusions(old_control)
    candidate = baseline | set(wrappers)
    isolated = reachable_source(raw, cells)
    output.mkdir(parents=True)
    (output / "clamps.cdl").write_text(isolated)
    io = Path(config["technology.sky130.sky130A"]) / "libs.ref/sky130_fd_io"
    io_collateral = None
    ef_gds = None
    if technology_cache is not None:
        technology_cache = technology_cache.resolve()
        io_collateral = json.loads((technology_cache / "sky130.io-collateral.json").read_text())
        for entry in io_collateral["files"]:
            if sha(entry["cached_path"]) != entry["cached_sha256"]:
                raise ValueError("Production IO collateral changed since generation")
            if entry["field"] == "gds_file":
                ef_gds = Path(entry["cached_path"])
            elif entry["field"] == "spice_file":
                if not any(e["path"] == entry["cached_path"] and e["sha256"] == entry["cached_sha256"]
                           for e in manifest["sources"]):
                    raise ValueError("Compiled source does not consume the production IO CDL")
        if ef_gds is None:
            raise ValueError("No production EF IO GDS in technology manifest")
    helpers = runpy.run_path(str(Path(__file__).with_name("sky130-io-lvs.py")))
    helpers["assemble_io_cells"](io, output / "clamps.gds", cells, ef_gds=ef_gds)
    if technology_cache is not None:
        deck = technology_cache / "sky130.pegasus.lvs.pvl"
    else:
        deck = Path(re.search(r'^#####\s+Rules File\s*:\s*(.+)$',
                              (source_run / "ChipTop.lvs_results.cls").read_text(), re.M)[1].strip())
    cases = []
    for cell in cells:
        cases.extend([(f"isolated/{cell}", cell, False),
                      (f"supply-assumed/{cell}", cell, True)])
    if include_chip_context:
        cases.append(("chip-context", None, False))
    records = []
    for label, primary, assume in cases:
        directory = output / label
        directory.mkdir(parents=True)
        ctl = case_control(old_control, directory, candidate,
                           primary=primary, layout=output / "clamps.gds", source=output / "clamps.cdl")
        if assume:
            block = next(b for b in spice_subcircuits(isolated) if b.name == primary)
            ports = block.header.replace("\n+", " ").split()[2:]
            supply_names = [p for p in ports if p.startswith("V") and not p.endswith("_PAD")]
            ctl += ("\n// Standalone same-name supply-port continuity assumptions only.\n"
                    "// This is not evidence of chip physical continuity.\n"
                    "virtual_connect -depth all;\n"
                    f"virtual_connect -name {' '.join(supply_names)} -cell {primary};\n"
                    "virtual_connect -report yes;\n")
        (directory / "control.pvl").write_text(ctl)
        command = [config["lvs.pegasus.pegasus_bin"], "-lvs", "-dp", "2", "-automatch",
                   "-check_schematic", "-rc_data", "-ui_data", "-control", "control.pvl", str(deck)]
        (directory / "run.sh").write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\n'
                                         + "source " + shlex.quote(str(source_run / "enter")) + "\nexec "
                                         + shlex.join(command) + '\n')
        (directory / "run.sh").chmod(0o755)
        records.append({"case": label, "primary": primary or config["vlsi.inputs.top_module"],
                        "supply_assumptions": assume})
    (output / "experiment.json").write_text(json.dumps({
        "source_run": str(source_run), "compiled_source_sha256": sha(source),
        "deck": str(deck), "deck_sha256": sha(deck),
        "copied_reachable_source_sha256": sha(output / "clamps.cdl"),
        "subset_gds_sha256": sha(output / "clamps.gds"),
        "discovered_padiso_wrappers": wrappers, "added_hierarchy_exclusions": sorted(candidate - baseline),
        "clamp_padiso_roots": {cell: roots[cell] for cell in cells},
        "production_io_collateral": io_collateral,
        "cases": records,
        "chip_context_changes": ("Hierarchy exclusions only; same GDS/CDL/Verilog/deck"
                                 if include_chip_context else "Chip-context case not requested"),
        "deferred": "Physical SRAM-channel PG opens; no physical design edits or virtual chip ties",
    }, indent=2) + "\n")
    lines = ['#!/usr/bin/env bash', 'set -euo pipefail', 'cd -- "$(dirname -- "$0")"']
    lines += ['bash ' + shlex.quote(r["case"] + "/run.sh") for r in records]
    lines += [shlex.join([sys.executable, str(Path(__file__).resolve()), "--summarize", str(output)])]
    (output / "run-all.sh").write_text("\n".join(lines) + "\n")
    (output / "run-all.sh").chmod(0o755)
    print("Prepared clamp qualification:", output / "run-all.sh")


def summarize(output):
    record = json.loads((output / "experiment.json").read_text())
    results = []
    for case in record["cases"]:
        directory = output / case["case"]
        report = directory / ("cell.lvs_results.cls" if (directory / "cell.lvs_results.cls").exists()
                              else "ChipTop.lvs_results.cls")
        if not report.exists():
            results.append({**case, "result": "not run"})
            continue
        text = report.read_text()
        results.append({**case, "result": re.search(r"Run Result\s*:\s*(\w+)", text)[1],
                        "report": str(report), "report_sha256": sha(report),
                        "counts": {m[1].strip(): int(m[2]) for m in re.finditer(
                            r"^(Cells[^|\n]+)\|\s*(\d+)", text, re.M)}})
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    for item in results:
        print(item["case"], item["result"])
    if any(case["case"] == "chip-context" for case in record["cases"]):
        print("Chip context may still mismatch due to deferred physical PG opens; inspect device correspondence.")
    else:
        print("Standalone checks do not establish assembled-chip physical supply connectivity.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cells", nargs="+", help="Defaults to every imported EF clamp variant")
    parser.add_argument("--technology-cache", type=Path,
                        help="Use and verify normal Hammer's generated IO CDL/GDS and cached deck")
    parser.add_argument("--skip-chip-context", action="store_true",
                        help="Prepare only the isolated and standalone supply-assumed cases")
    parser.add_argument("--summarize", type=Path)
    args = parser.parse_args()
    if args.summarize:
        summarize(args.summarize.resolve())
    else:
        if args.source_run is None or args.output is None:
            parser.error("--source-run and --output are required for preparation")
        prepare(args.source_run, args.output, args.cells, include_chip_context=not args.skip_chip_context,
                technology_cache=args.technology_cache)
