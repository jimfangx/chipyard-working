#!/usr/bin/env python3
"""Prepare diagnostic CDL/overlay candidates for the two defective clamped2 views.

Original PDK files and completed reports stay unchanged. These candidates
require CAD comparison and review of the intended supply domains before any
production integration. No virtual net connections or dimension changes.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import shlex
import struct
import sys

from hammer.technology.sky130.lvs_netlists import spice_subcircuits
from hammer.technology.sky130.lvs_translate import instance, logical_lines


PREFIX = "sky130_ef_io__"
POWER = PREFIX + "vccd_lvc_clamped2_pad"
GROUND = PREFIX + "vssd_lvc_clamped2_pad"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def correct_calls(text):
    """Candidate mappings consistent with the installed VCCD clamped2 geometry."""
    blocks = {b.name: b for b in spice_subcircuits(text)}
    changes = {}
    for name in (POWER, GROUND):
        block = blocks[name]
        body = text[block.start:block.end]
        calls = [line for line in logical_lines(body) if line[:1].lower() == "x"]
        if len(calls) != 1:
            raise ValueError(f"Expected one base pad call: {name}")
        positional, parameters = instance(calls[0])
        expected_master = "sky130_fd_io__top_" + ("power" if name == POWER else "ground") + "_lvc_wpad"
        if parameters or positional[-1] != expected_master:
            raise ValueError(f"Unexpected base pad master or parameters: {name}")
        ports = logical_lines(blocks[expected_master].header)[0].split()[2:]
        if len(ports) != len(positional) - 2:
            raise ValueError(f"Base pad arity differs: {name}")
        bindings = dict(zip(ports, positional[1:-1]))
        old = ({"BDY2_B2B": "VSSA", "OGC_LVC": "VSSA", "PADISOL": "PADISOL",
                "PADISOR": "PADISOR", "SRC_BDY_LVC1": "VSSIO", "SRC_BDY_LVC2": "VSSD"}
               if name == POWER else
               {"BDY2_B2B": "VSSA", "OGC_LVC": "PADISOL", "PADISOL": "PADISOR",
                "PADISOR": "VSSA", "SRC_BDY_LVC1": "VSSIO", "SRC_BDY_LVC2": "VSSD"})
        if any(bindings[p] != value for p, value in old.items()):
            raise ValueError(f"Original clamped2 pin map changed: {name}")
        new = {**old, "BDY2_B2B": "VSSIO", "OGC_LVC": "VSSA", "PADISOL": "PADISOL",
               "PADISOR": "PADISOR", "SRC_BDY_LVC1": "VSSD"}
        changes[name] = {p: {"before": old[p], "candidate": value}
                         for p, value in new.items() if old[p] != value}
        replacement = " ".join([positional[0], *(new.get(p, bindings[p]) for p in ports), expected_master])
        revised = body.replace(calls[0], replacement)
        if revised == body:
            raise ValueError(f"No candidate replacement made: {name}")
        text = text[:block.start] + revised + text[block.end:]
        # Recompute offsets after changing a block's length.
        blocks = {b.name: b for b in spice_subcircuits(text)}
    return text, changes


def records(data):
    offset = 0
    while offset < len(data):
        length, kind, _ = struct.unpack_from(">HBB", data, offset)
        if length < 4 or offset + length > len(data):
            raise ValueError("Invalid GDS record")
        yield kind, data[offset:offset + length]
        offset += length


def add_missing_overlays(data):
    """Copy original overlay SREF records verbatim; preserve all other records."""
    cells, current, name = {}, None, None
    for kind, raw in records(data):
        if kind == 5:
            current = []
        if current is not None:
            current.append(raw)
            if kind == 6:
                name = raw[4:].rstrip(b"\0").decode()
            if kind == 7:
                cells[name] = b"".join(current)
                current = None

    def refs(cell):
        result, element, master = {}, None, None
        for kind, raw in records(cells[cell]):
            if kind == 10:
                element = []
            if element is not None:
                element.append(raw)
                if kind == 18:
                    master = raw[4:].rstrip(b"\0").decode()
                if kind == 17:
                    if master in result:
                        raise ValueError(f"Duplicate overlay reference: {master}")
                    result[master] = b"".join(element)
                    element = None
        return result

    if set(refs(GROUND)) != {"sky130_fd_io__top_ground_lvc_wpad"}:
        raise ValueError("Ground clamped2 reference set changed; revalidate missing overlays")
    templates = [(PREFIX + "vssd_lvc_clamped_pad", "sky130_fd_io__overlay_vssd_lvc"),
                 (POWER, PREFIX + "lvc_vccd_overlay")]
    additions = b"".join(refs(cell)[master] for cell, master in templates)
    original = cells[GROUND]
    end = struct.pack(">HBB", 4, 7, 0)
    if not original.endswith(end) or data.count(original) != 1:
        raise ValueError("Ground clamped2 GDS block is not unique/complete")
    candidate = original[:-len(end)] + additions + end
    return data.replace(original, candidate, 1), [{"template_cell": c, "master": m} for c, m in templates]


def prepare(source, output):
    source, output = source.resolve(), output.resolve()
    if output.exists():
        raise ValueError("Use a new output directory to preserve completed reports")
    experiment = json.loads((source / "experiment.json").read_text())
    cdl, gds = (source / "clamps.cdl").read_bytes(), (source / "clamps.gds").read_bytes()
    if sha(cdl) != experiment["copied_reachable_source_sha256"] or sha(gds) != experiment["subset_gds_sha256"]:
        raise ValueError("Qualification inputs changed since preparation")
    corrected, mappings = correct_calls(cdl.decode())
    candidate, overlays = add_missing_overlays(gds)
    output.mkdir(parents=True)
    (output / "clamps.cdl").write_text(corrected)
    (output / "clamps.gds").write_bytes(candidate)
    cases = []
    for label, cell, layout in [("source-only/" + POWER, POWER, source / "clamps.gds"),
                                ("source-only/" + GROUND, GROUND, source / "clamps.gds"),
                                ("source-and-overlays/" + GROUND, GROUND, output / "clamps.gds")]:
        previous = source / "isolated" / cell
        directory = output / label
        directory.mkdir(parents=True)
        control = (previous / "control.pvl").read_text().replace(str(previous), str(directory))
        control = control.replace(str(source / "clamps.cdl"), str(output / "clamps.cdl"))
        control = control.replace(str(source / "clamps.gds"), str(layout))
        if re.search(r"^\s*(virtual_connect|lvs_join_nets)\b", control, re.M):
            raise ValueError("Unexpected virtual connection")
        (directory / "control.pvl").write_text(control)
        (directory / "run.sh").write_text((previous / "run.sh").read_text())
        cases.append({"case": label, "primary": cell, "supply_assumptions": False})
    (output / "experiment.json").write_text(json.dumps({
        "source_experiment": str(source), "cases": cases,
        "input_cdl_sha256": sha(cdl), "candidate_cdl_sha256": sha(corrected.encode()),
        "input_gds_sha256": sha(gds), "candidate_gds_sha256": sha(candidate),
        "candidate_pin_map_changes": mappings, "ground_candidate_added_overlays": overlays,
        "status": "Diagnostic candidates; CAD comparison and supply-intent review pending",
        "external_files_modified": False,
    }, indent=2) + "\n")
    summarizer = Path(__file__).with_name("sky130-clamp-lvs.py").resolve()
    lines = ['#!/usr/bin/env bash', 'set -euo pipefail', 'cd -- "$(dirname -- "$0")"']
    lines += ["bash " + shlex.quote(case["case"] + "/run.sh") for case in cases]
    lines.append(shlex.join([sys.executable, str(summarizer), "--summarize", str(output)]))
    (output / "run-all.sh").write_text("\n".join(lines) + "\n")
    print("Prepared diagnostic candidates:", output / "run-all.sh")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.output)
