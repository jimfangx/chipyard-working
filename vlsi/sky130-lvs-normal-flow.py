#!/usr/bin/env python3
"""Prepare the normal Hammer LVS flow on repaired exports; verify input equivalence."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import shlex
import sys

from hammer.vlsi import HammerDriver, HammerDriverOptions
from hammer.technology.sky130.lvs_netlists import spice_subcircuits


def definitions(text):
    return {b.name: text[b.start:b.end] for b in spice_subcircuits(text)}


def outside_statements(text):
    chunks, last = [], 0
    for block in spice_subcircuits(text):
        chunks.append(text[last:block.start])
        last = block.end
    chunks.append(text[last:])
    return [line.strip() for line in "".join(chunks).splitlines()
            if line.strip() and not line.lstrip().startswith("*")]


def exclusions(text):
    return {name for statement in re.findall(r"^lvs_exclude_hcell\s+([^;]+);", text, re.M)
            for name in statement.split()}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_results(output):
    record = output / "equivalence.json"
    result = json.loads(record.read_text())
    report = Path(result["normal_run_directory"]) / "ChipTop.lvs_results.cls"
    if report.stat().st_mtime_ns < (output / "run-start").stat().st_mtime_ns:
        raise ValueError("Normal Hammer report predates this invocation")
    text = report.read_text()
    counts = {}
    for label in ("Cells matched", "Cells expanded", "Cells not run", "Cells which mismatch",
                  "Cells with parameter mismatches", "Cells with mismatched instance subtypes"):
        counts[label] = int(re.search(r"^" + re.escape(label) + r"\s*\|\s*(\d+)", text, re.M)[1])
    result.update(normal_hammer_cad_run_pending=False, normal_report_sha256=sha(report),
                  normal_result=re.search(r"Run Result\s*:\s*(\w+)", text)[1], normal_counts=counts)
    record.write_text(json.dumps(result, indent=2) + "\n")
    if result["normal_result"] != "MATCH" or any(counts[label] for label in counts
                                                    if label not in ("Cells matched", "Cells expanded")):
        raise ValueError(f"Normal Hammer LVS did not close: {counts}")
    print(f"Normal Hammer LVS MATCH: {counts['Cells matched']} matched, zero mismatches: {report}")


def write_top_level_runner(project, output):
    """Use the same explicit overlay with the project's existing redo-lvs target."""
    project, output = project.resolve(), output.resolve()
    root = Path(__file__).resolve().parent
    record = json.loads((output / "equivalence.json").read_text())
    overlay = json.loads((output / "inputs.json").read_text())
    if (overlay.get("technology.sky130.lvs_mixed_library_compatibility") is not True
            or overlay.get("lvs.inputs.layout_file") != record["layout"]
            or overlay.get("lvs.inputs.schematic_files") != [record["netlist"]]):
        raise ValueError("Top-level overlay differs from the qualified integration inputs")
    for kind in ("layout", "netlist"):
        if sha(Path(record[kind])) != record[kind + "_sha256"]:
            raise ValueError(f"Qualified {kind} changed; prepare integration again")
    directory = output / "top-level"
    directory.mkdir(exist_ok=True)
    saved = directory / "equivalence.json"
    if saved.exists() and not json.loads(saved.read_text()).get("normal_hammer_cad_run_pending"):
        raise ValueError("Preserve the completed top-level integration result before preparing another")
    record.update(normal_run_directory=str(project / "lvs-rundir"),
                  normal_hammer_cad_run_pending=True)
    saved.write_text(json.dumps(record, indent=2) + "\n")
    command = ["make", "-f", str(project / "hammer.d"), "redo-lvs",
               "HAMMER_EXEC=" + shlex.join([sys.executable, str(root / "hammer-driver")]),
               "HAMMER_EXTRA_ARGS=" + shlex.join(["-p", str(output / "inputs.json")])]
    script = output / "run-top-level.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- ' + shlex.quote(str(root)) + '\n'
                      'export PYTHONPATH=' + shlex.quote(str(root / "hammer")) + '${PYTHONPATH:+:$PYTHONPATH}\n'
                      'touch -- ' + shlex.quote(str(directory / "run-start")) + '\n'
                      + shlex.join(command) + '\nexec '
                      + shlex.join([sys.executable, str(Path(__file__).resolve()), "--check-results", str(directory)]) + '\n')
    script.chmod(0o755)
    print(f"Top-level redo-lvs with qualified inputs: {script}")


def prepare(project, passed_run, output):
    project, passed_run, output = project.resolve(), passed_run.resolve(), output.resolve()
    root = Path(__file__).resolve().parent
    if output.exists():
        saved = json.loads((output / "equivalence.json").read_text())
        if (not saved.get("normal_hammer_cad_run_pending")
                or (output / "lvs-rundir/ChipTop.lvs_results.cls").exists()):
            raise ValueError("Use a new output directory to preserve completed CAD results")
    output.mkdir(parents=True, exist_ok=True)
    exports = passed_run / "chip-export"
    baseline = passed_run / "full-chip"
    report = (baseline / "ChipTop.lvs_results.cls").read_text()
    if not re.search(r"Run Result\s*:\s*MATCH\b", report):
        raise ValueError("Expected a completed full-chip MATCH before normal-flow integration")
    override = output / "inputs.json"
    override.write_text(json.dumps({
        "technology.sky130.lvs_mixed_library_compatibility": True,
        "lvs.inputs.layout_file": str(exports / "ChipTop_drc_lvs.gds"),
        "lvs.inputs.schematic_files": [str(exports / "ChipTop.lvs.v")],
    }, indent=2) + "\n")
    options = HammerDriverOptions(environment_configs=[str(root / "env.yml")],
        project_configs=[str(project / "lvs-input.json"), str(override)],
        log_file=str(output / "prepare.log"), obj_dir=str(output / "obj"))
    driver = HammerDriver(options)
    run = output / "lvs-rundir"
    if not driver.load_lvs_tool(str(run)):
        raise RuntimeError("Failed to load normal Hammer LVS tool")
    # Run all normal generation hooks, but do not invoke a CAD binary locally.
    # The generated run.sh below uses the unmodified driver in a fresh process.
    driver.lvs_tool.run_pegasus = lambda: True
    namespace = runpy.run_path(str(root / "hammer-driver"))
    hooks = (driver.lvs_tool.get_tool_hooks() + driver.tech.get_tech_lvs_hooks(driver.lvs_tool.name)
             + namespace["Driver"]().get_extra_lvs_hooks())
    success, _ = driver.run_lvs(hooks)
    if not success:
        raise RuntimeError("Normal Hammer LVS input generation failed")
    cdl = run / "sky130.pegasus.lvs.cdl"
    prior_source = Path(re.search(r'schematic_path "([^"\n]+)" cdl;', (baseline / "control.pvl").read_text())[1])
    actual, expected = definitions(cdl.read_text()), definitions(prior_source.read_text())
    if actual != expected:
        changed = sorted(n for n in set(actual) | set(expected) if actual.get(n) != expected.get(n))
        raise ValueError(f"Normal Hammer source circuits differ from full-chip MATCH: {changed[:20]}")
    if outside_statements(cdl.read_text()) != outside_statements(prior_source.read_text()):
        raise ValueError("Normal Hammer source directives outside subcircuits differ")
    deck = Path(driver.lvs_tool.get_lvs_decks()[0].path)
    cached = deck.read_text()
    if cached.startswith("// Cached by Hammer from "):
        cached = cached.split("\n", 1)[1]
    prior_deck = Path(json.loads((passed_run / "experiment.json").read_text())["deck"])
    if cached != prior_deck.read_text():
        raise ValueError("Normal Hammer deck differs from the passing deck")
    control = Path(driver.lvs_tool.lvs_ctl_file).read_text()
    if exclusions(control) != exclusions((baseline / "control.pvl").read_text()):
        raise ValueError("Normal Hammer hierarchy expansions differ from the passing run")
    if re.search(r"^\s*(?:virtual_connect|lvs_join_nets)\b", control, re.M):
        raise ValueError("Unexpected virtual connectivity in normal Hammer inputs")
    command = [sys.executable, str(root / "hammer-driver"), "-e", str(root / "env.yml"),
               "-p", str(project / "lvs-input.json"), "-p", str(override),
               "--obj_dir", str(output / "obj"), "--lvs_rundir", str(run), "lvs"]
    script = output / "run.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- ' + shlex.quote(str(root)) + '\n'
                      'export PYTHONPATH=' + shlex.quote(str(root / "hammer")) + '${PYTHONPATH:+:$PYTHONPATH}\n'
                      'touch -- ' + shlex.quote(str(output / "run-start")) + '\n'
                      + shlex.join(command) + '\nexec '
                      + shlex.join([sys.executable, str(Path(__file__).resolve()), "--check-results", str(output)]) + '\n')
    script.chmod(0o755)
    (output / "equivalence.json").write_text(json.dumps({
        "passing_run": str(passed_run), "passing_report_sha256": sha(baseline / "ChipTop.lvs_results.cls"),
        "normal_run_directory": str(run), "source_definitions_identical": len(actual),
        "source_outside_statements_identical": True,
        "source_cdl_sha256": sha(cdl), "deck_sha256_excluding_provenance_header": hashlib.sha256(cached.encode()).hexdigest(),
        "hierarchy_expansions_identical": len(exclusions(control)),
        "layout": str(exports / "ChipTop_drc_lvs.gds"), "layout_sha256": sha(exports / "ChipTop_drc_lvs.gds"),
        "netlist": str(exports / "ChipTop.lvs.v"), "netlist_sha256": sha(exports / "ChipTop.lvs.v"),
        "preparation_only": True, "normal_hammer_cad_run_pending": True,
    }, indent=2) + "\n")
    write_top_level_runner(project, output)
    print(f"Normal Hammer deck/source/hierarchy agree with full-chip MATCH: {script}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-results", type=Path)
    parser.add_argument("--write-top-level-runner", action="store_true")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--passed-run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.check_results:
        check_results(args.check_results)
    elif args.write_top_level_runner and args.project and args.output:
        write_top_level_runner(args.project, args.output)
    elif args.project and args.passed_run and args.output:
        prepare(args.project, args.passed_run, args.output)
    else:
        parser.error("Provide --check-results or all of --project, --passed-run and --output")
