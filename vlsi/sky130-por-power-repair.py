#!/usr/bin/env python3
"""Prepare the missing PoR VDDIO via insertion and unchanged-policy chip LVS."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_def_via(path):
    """Check the repair in DEF, including optional special-wire SHAPE syntax."""
    masters, hits = {}, []
    section, name, block = None, None, []
    pattern = re.compile(r"\bmet[34]\s+0(?:\s+\+\s+SHAPE\s+\S+)?\s+"
                         r"\(\s*3277200\s+177890\s*\)\s+(\S+)")
    for line in Path(path).open():
        stripped = line.strip()
        if stripped.startswith("VIAS "): section = "vias"
        if stripped == "END VIAS": section = None
        if stripped.startswith("SPECIALNETS "): section = "nets"
        if stripped == "END SPECIALNETS": section = None
        if section == "vias":
            if stripped.startswith("- "): name, block = stripped.split()[1], []
            block.append(line)
            if ";" in line and name: masters[name] = "".join(block)
        if section == "nets":
            if stripped.startswith("- "): name = stripped.split()[1]
            hits.extend((name, match[1]) for match in pattern.finditer(line))
    if len(hits) != 1 or hits[0][0] != "VDDIO":
        raise ValueError(f"Missing/duplicate/wrong-net repair via: {hits}")
    master = masters.get(hits[0][1], "")
    for expression in (r"\+\s+LAYERS\s+met3\s+via3\s+met4\b",
                       r"\+\s+ROWCOL\s+4\s+1\b", r"\+\s+CUTSIZE\s+200\s+200\b",
                       r"\+\s+ENCLOSURE\s+65\s+100\s+65\s+100\b"):
        if not re.search(expression, master):
            raise ValueError(f"Unexpected repair via definition: {master}")
    return {"net": hits[0][0], "via_def": hits[0][1], "location_um": [3277.2,177.89]}


def write_resume_scripts(output):
    """Use the checked-in parser directly, avoiding generated regex escaping."""
    helper = Path(__file__).resolve()
    checker = output / "check-via.py"
    checker.write_text("from pathlib import Path\nimport runpy\n"
                       f"helper = runpy.run_path({str(helper)!r})\n"
                       "result = helper['check_def_via'](Path(__file__).resolve().parent/'chip-export/ChipTop.def')\n"
                       "print('Verified repair via:', result)\n")
    resume = output / "resume.sh"
    resume.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\n'
                      + shlex.join([sys.executable, str(output / "chip-export/check_export.py")]) + '\n'
                      + shlex.join([sys.executable, str(checker)]) + '\nbash full-chip/run.sh\n')
    resume.chmod(0o755)
    script = output / "run-all.sh"
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd -- "$(dirname -- "$0")"\n'
                      'bash chip-export/run.sh\nbash resume.sh\n')
    script.chmod(0o755)


def prepare(source_run, output):
    source_run, output = source_run.resolve(), output.resolve()
    prior = json.loads((source_run / "experiment.json").read_text())
    full = source_run / "full-chip"
    exported = source_run / "chip-export"
    report = (full / "ChipTop.lvs_results.cls").read_text()
    summary = report.split("CELL MATCH SUMMARY", 1)[1].split("LVS RULES", 1)[0]
    if [line.split('|')[0].strip(' .') for line in summary.splitlines() if '| mismatch' in line] != ['ChipTop']:
        raise ValueError("Expected only ChipTop to mismatch")
    if not re.search(r"Cells with parameter mismatches\s*\|\s*0", report):
        raise ValueError("Unexpected remaining parameter errors")
    if not re.search(r"Layout Pin: VDDIO.*?OPEN", report, flags=re.S):
        raise ValueError("Expected the PoR VDDIO open")
    if sha(source_run / "por-combined-candidate.pvl") != prior["deck_sha256"]:
        raise ValueError("Validated extraction deck changed")
    if sha(source_run / "sky130.pegasus.lvs.cdl") != prior["compiled_source_sha256"]:
        raise ValueError("Validated source changed")
    text = (exported / "ChipTop.def").read_text()
    if '+ FIXED met3 1000 ( 3277200 175565 ) ( * 247835 )' not in text:
        raise ValueError("Qualified PoR VDDIO trunk geometry changed")
    if re.search(r"met[34] 0 \( 3277200 177890 \) M3M4_", text):
        raise ValueError("A via already exists at the qualified repair point")
    output.mkdir(parents=True, exist_ok=False)
    new_export = output / "chip-export"
    new_export.mkdir()
    hook = Path(__file__).with_name("sky130-por-vddio.tcl").resolve()
    tcl = (exported / "reexport.tcl").read_text().replace(str(exported), str(new_export))
    stream = [line for line in tcl.splitlines() if line.startswith("write_stream ")]
    if len(stream) != 1:
        raise ValueError("Expected one configured-PoR GDS stream")
    tcl = tcl.replace(stream[0], f"source {{{hook}}}\n" + stream[0])
    (new_export / "reexport.tcl").write_text(tcl)
    for name in ("run.sh", "check_export.py", "export.json"):
        data = (exported / name).read_text().replace(str(exported), str(new_export))
        (new_export / name).write_text(data)
    (new_export / "run.sh").chmod(0o755)
    new_full = output / "full-chip"
    new_full.mkdir()
    for name in ("run.sh", "control.pvl"):
        data = (full / name).read_text().replace(str(full), str(new_full)).replace(str(exported), str(new_export))
        (new_full / name).write_text(data)
    (new_full / "run.sh").chmod(0o755)
    write_resume_scripts(output)
    (output / "experiment.json").write_text(json.dumps({
        "source_run": str(source_run), "baseline_report_sha256": sha(full / "ChipTop.lvs_results.cls"),
        "baseline_def_sha256": sha(exported / "ChipTop.def"),
        "source_gds_sha256": sha(exported / "ChipTop_drc_lvs.gds"),
        "compiled_source": str(source_run / "sky130.pegasus.lvs.cdl"),
        "compiled_source_sha256": prior["compiled_source_sha256"],
        "deck": str(source_run / "por-combined-candidate.pvl"), "deck_sha256": prior["deck_sha256"],
        "repair": {"net": "VDDIO", "location_um": [3277.200,177.890], "cut_layer": "via3",
                   "row_column": [4,1], "cut_size_um": [.2,.2], "enclosure_um": [.065,.1],
                   "filler": "IO_FILLER_MANUAL_S_3", "filler_met4_rail_um": [3264.,175.565,3284.,180.215],
                   "trunk_met3_um": [3276.7,175.565,3277.7,247.835]},
        "repair_tcl": str(hook), "repair_tcl_sha256": sha(hook),
        "changes_source_deck_tolerances_or_placement": False, "saves_database": False,
        "needs_drc": ["PoR supply via insertion", "Prior quiet-VDDIO tie"],
    }, indent=2) + "\n")
    print(f"Prepared physical PoR VDDIO repair and full-chip comparison: {output / 'run-all.sh'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_run, args.output)
