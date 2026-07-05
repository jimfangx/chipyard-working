#!/usr/bin/env bash
set -euo pipefail

suite="${1:?usage: run-firesim-replace-rtl.sh SUITE PR_NUMBER [CHIPYARD_DIR] [CONFIG_JSON]}"
pr_number="${2:?usage: run-firesim-replace-rtl.sh SUITE PR_NUMBER [CHIPYARD_DIR] [CONFIG_JSON]}"
chipyard_dir="${3:-/root/chipyard}"
config_json="${4:-${chipyard_dir}/.github/workflows/config/firesim-tests.json}"

checkout_pr_merge() {
  cd "${chipyard_dir}"
  git config --global --add safe.directory "*" 2>/dev/null || true
  git remote set-url origin "${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}.git"

  initialized_before="$(mktemp)"
  submodules_after="$(mktemp)"
  initialized_targets="$(mktemp)"
  new_targets="$(mktemp)"
  removed_targets="$(mktemp)"

  git submodule status \
    | awk 'substr($1, 1, 1) != "-" { print $2 }' \
    | sort -u > "${initialized_before}"

  git fetch --no-tags origin "pull/${pr_number}/merge"
  git checkout --detach FETCH_HEAD

  git config --file .gitmodules --get-regexp '^submodule\..*\.path$' \
    | awk '{ print $2 }' \
    | sort -u > "${submodules_after}"

  comm -12 "${initialized_before}" "${submodules_after}" > "${initialized_targets}"
  comm -13 "${initialized_before}" "${submodules_after}" > "${new_targets}"
  comm -23 "${initialized_before}" "${submodules_after}" > "${removed_targets}"

  while read -r submodule_path; do
    [ -n "${submodule_path}" ] || continue
    git submodule deinit --force -- "${submodule_path}" || true
    rm -rf -- "${submodule_path}"
  done < "${removed_targets}"

  while read -r submodule_path; do
    [ -n "${submodule_path}" ] || continue
    git submodule sync -- "${submodule_path}"
    git submodule update -- "${submodule_path}"
  done < "${initialized_targets}"

  while read -r submodule_path; do
    [ -n "${submodule_path}" ] || continue
    git submodule init -- "${submodule_path}"
    git submodule sync -- "${submodule_path}"
    git submodule update --init -- "${submodule_path}"
  done < "${new_targets}"

  git rev-parse --short HEAD
}

prepare_firesim_environment() {
  cd "${chipyard_dir}"
  source env.sh
  cd sims/firesim
  source sourceme-manager.sh --skip-ssh-setup
}

prepare_f2_mgmt_tools() {
  cd "${chipyard_dir}/sims/firesim/platforms/f2/aws-fpga-firesim-f2/sdk/userspace"
  export AWS_FPGA_REPO_DIR
  AWS_FPGA_REPO_DIR="$(git rev-parse --show-toplevel)"
  bash ./mkall_fpga_mgmt_tools.sh
}

run_firesim_scala_test() {
  local test_class="$1"

  if ! [[ "${test_class}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "Invalid FireSim Scala test class name: ${test_class}" >&2
    exit 1
  fi

  if ! grep -Eq "class[[:space:]]+${test_class}([[:space:]({]|$)" \
    "${chipyard_dir}/generators/firechip/chip/src/test/scala/FireSimTestSuite.scala"; then
    echo "FireSim Scala test class does not exist: ${test_class}" >&2
    exit 1
  fi

  cd "${chipyard_dir}"
  echo "========== FireSim Scala test: firechip.chip.${test_class} =========="
  TEST_DISABLE_VCS=1 TEST_DISABLE_VIVADO=1 sbt "project firechip; testOnly firechip.chip.${test_class}"
}

checkout_pr_merge
prepare_firesim_environment

if [ "${suite}" = "f2" ]; then
  prepare_f2_mgmt_tools
fi

while IFS= read -r test_class; do
  run_firesim_scala_test "${test_class}"
done < <(
  python3 - "${config_json}" "${suite}" <<'PY'
import json
import sys

config_json, suite = sys.argv[1], sys.argv[2]
with open(config_json, encoding="utf-8") as config_file:
    config = json.load(config_file)

if suite not in config:
    print(f"Unknown FireSim test suite: {suite}", file=sys.stderr)
    sys.exit(1)

tests = config[suite]
if not isinstance(tests, list):
    print(f"FireSim suite {suite} must be a list of Scala test class names", file=sys.stderr)
    sys.exit(1)

for test in tests:
    print(test)
PY
)
