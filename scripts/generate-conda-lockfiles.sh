#!/usr/bin/env bash

set -ex

CUR_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

CY_DIR=$(cd "$CUR_DIR/.." && pwd)

REQS_DIR="$CUR_DIR/../conda-reqs"
CONDA_LOCK_ENV_PATH="$CY_DIR/.conda-lock-env"

if [ ! -d "$REQS_DIR" ]; then
  echo "$REQS_DIR does not exist, make sure you're calling this script from chipyard/"
  exit 1
fi

if [[ ! -x "$CONDA_LOCK_ENV_PATH/bin/conda-lock" ]]; then
  echo "conda-lock environment not found; run build-setup.sh Step 1 first."
  exit 1
fi

# We never authenticate to a private index, so disable the keyring outright. Otherwise sometimes this hangs
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring

CONDA_EXE="${CONDA_EXE:-$(command -v conda)}"
if [[ ! -x "$CONDA_EXE" ]]; then
  echo "no conda executable found; set CONDA_EXE or put conda on PATH."
  exit 1
fi

for TOOLCHAIN_TYPE in riscv-tools; do
    # note: lock file must end in .conda-lock.yml - see https://github.com/conda-incubator/conda-lock/issues/154
    LOCKFILE=$REQS_DIR/conda-lock-reqs/conda-requirements-$TOOLCHAIN_TYPE-linux-64.conda-lock.yml
    rm -rf $LOCKFILE

    "$CONDA_LOCK_ENV_PATH/bin/conda-lock" \
      --conda "$CONDA_EXE" \
      --no-mamba \
      --no-micromamba \
      -f "$REQS_DIR/chipyard-base.yaml" \
      -f "$REQS_DIR/chipyard-extended.yaml" \
      -f "$REQS_DIR/docs.yaml" \
      -f "$REQS_DIR/$TOOLCHAIN_TYPE.yaml" \
      -p linux-64 \
      --lockfile $LOCKFILE

    LOCKFILE=$REQS_DIR/conda-lock-reqs/conda-requirements-$TOOLCHAIN_TYPE-linux-64-lean.conda-lock.yml
    rm -rf $LOCKFILE

    "$CONDA_LOCK_ENV_PATH/bin/conda-lock" \
      --conda "$CONDA_EXE" \
      --no-mamba \
      --no-micromamba \
      -f "$REQS_DIR/chipyard-base.yaml" \
      -f "$REQS_DIR/docs.yaml" \
      -f "$REQS_DIR/$TOOLCHAIN_TYPE.yaml" \
      -p linux-64 \
      --lockfile $LOCKFILE
done
