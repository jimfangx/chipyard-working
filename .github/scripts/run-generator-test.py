#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys


def run_shell(command, chipyard_dir, sim_dir, env):
    wrapped = (
        f'source "{chipyard_dir}/env.sh"\n'
        f'cd "{sim_dir}"\n'
        f'{command}'
    )
    print("::group::" + command, flush=True)
    try:
        subprocess.run(
            ["bash", "-leo", "pipefail", "-c", wrapped],
            check=True,
            env=env,
        )
    finally:
        print("::endgroup::", flush=True)


def run_entry(entry, chipyard_dir, sim_dir, env):
    if entry.get("custom") is True:
        command = entry.get("string")
        if not command:
            raise ValueError("custom test entry must include a non-empty string")
        run_shell(command, chipyard_dir, sim_dir, env)
        return

    if entry.get("custom") is not False:
        raise ValueError("test entry must set custom to true or false")

    configs = entry.get("config")
    binaries = entry.get("binary")
    loadmem = entry.get("loadmem")

    if not isinstance(configs, list) or not configs:
        raise ValueError("non-custom test entry must include a non-empty config list")
    if not isinstance(binaries, list) or not binaries:
        raise ValueError("non-custom test entry must include a non-empty binary list")
    if loadmem != "1":
        raise ValueError("non-custom test entries must set loadmem to string value \"1\"")

    for config in configs:
        for binary in binaries:
            run_shell(
                f"make run-binary CONFIG={config} BINARY={binary} LOADMEM=1",
                chipyard_dir,
                sim_dir,
                env,
            )


def main():
    parser = argparse.ArgumentParser(description="Run a JSON-defined Chipyard generator test group.")
    parser.add_argument("test_name")
    parser.add_argument(
        "--tests-json",
        default="/root/chipyard/.github/workflows/config/generator-tests.json",
    )
    parser.add_argument("--chipyard-dir", default="/root/chipyard")
    args = parser.parse_args()

    chipyard_dir = os.path.abspath(args.chipyard_dir)
    sim_dir = os.path.join(chipyard_dir, "sims", "verilator")

    with open(args.tests_json, encoding="utf-8") as tests_file:
        tests = json.load(tests_file)

    if args.test_name not in tests:
        print(f"Unknown test group: {args.test_name}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env.setdefault("FORCE_NON_EC2", "1")
    env.setdefault("JVM_OPTS", "-Xmx3200m")
    env["LOCAL_CHIPYARD_DIR"] = chipyard_dir
    env["LOCAL_SIM_DIR"] = sim_dir

    entries = tests[args.test_name]
    if not isinstance(entries, list) or not entries:
        print(f"Test group {args.test_name} must be a non-empty list", file=sys.stderr)
        return 1

    for entry in entries:
        run_entry(entry, chipyard_dir, sim_dir, env)

    print(f"Generator test complete: {args.test_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
