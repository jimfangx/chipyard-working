#!/usr/bin/env bash

# exit script if any command fails
set -e
set -o pipefail

CYDIR=$(git rev-parse --show-toplevel)

# get helpful utilities
source $CYDIR/scripts/utils.sh

common_setup

usage() {
    echo "Usage: ${0} [OPTIONS] [riscv-tools]"
    echo ""
    echo "Installation Types"
    echo "  riscv-tools: if set, builds the riscv toolchain (this is also the default)"
    echo ""
    echo "Helper script to fully initialize repository that wraps other scripts."
    echo "By default it initializes/installs things in the following order:"
    echo "   1. Pixi environment"
    echo "   2. Chipyard submodules"
    echo "   3. Toolchain collateral (Spike, PK, tests, libgloss)"
    echo "   4. Ctags"
    echo "   5. Chipyard pre-compile sources"
    echo "   6. FireSim"
    echo "   7. FireSim pre-compile sources"
    echo "   8. FireMarshal"
    echo "   9. FireMarshal pre-compile default buildroot Linux sources"
    echo "  10. Install CIRCT"
    echo "  11. Runs repository clean-up"
    echo ""
    echo "**See below for options to skip parts of the setup. Skipping parts of the setup is not guaranteed to be tested/working.**"
    echo ""
    echo "Options"
    echo "  --help -h               : Display this message"
    echo "  --verbose -v            : Verbose printout"
    echo "  --use-unpinned-deps -ud : Deprecated for Pixi; kept for CLI compatibility"
    echo "  --use-lean-conda        : Install a leaner version of the repository (uses Pixi 'lean' env; no FireSim, no FireMarshal)"
    echo "  --build-circt           : Builds CIRCT from source, instead of downloading the precompiled binary"
    echo "  --conda-env-name NAME   : Deprecated for Pixi; kept for CLI compatibility"
    echo "  --github-token TOKEN    : Optionally use a Github token to download CIRCT"

    echo "  --skip -s N             : Skip step N in the list above. Use multiple times to skip multiple steps ('-s N -s M ...')."
    echo "  --skip-conda            : Skip environment initialization (step 1)"
    echo "  --skip-submodules       : Skip submodule initialization (step 2)"
    echo "  --skip-toolchain        : Skip toolchain collateral (step 3)"
    echo "  --skip-ctags            : Skip ctags (step 4)"
    echo "  --skip-precompile       : Skip precompiling sources (steps 5/7)"
    echo "  --skip-firesim          : Skip Firesim initialization (steps 6/7)"
    echo "  --skip-marshal          : Skip firemarshal initialization (steps 8/9)"
    echo "  --skip-circt            : Skip CIRCT install (step 10)"
    echo "  --skip-clean            : Skip repository clean-up (step 11)"

    exit "$1"
}

TOOLCHAIN_TYPE="riscv-tools"
VERBOSE=false
VERBOSE_FLAG=""
USE_UNPINNED_DEPS=false
USE_LEAN_CONDA=false
SKIP_LIST=()
BUILD_CIRCT=false
GLOBAL_ENV_NAME=""
GITHUB_TOKEN="null"
PIXI_ENV_NAME=""
PIXI_ENV_PREFIX=""

# getopts does not support long options, and is inflexible
while [ "$1" != "" ];
do
    case $1 in
        -h | --help )
            usage 3 ;;
        riscv-tools )
            TOOLCHAIN_TYPE=$1 ;;
        --verbose | -v)
            VERBOSE=true
            VERBOSE_FLAG=$1
            ;;
        --use-lean-conda)
            USE_LEAN_CONDA=true
            SKIP_LIST+=(4 6 7 8 9) ;;
        --build-circt)
            BUILD_CIRCT=true ;;
        --conda-env-name)
            shift
            GLOBAL_ENV_NAME=${1} ;;
        --github-token)
            shift
            GITHUB_TOKEN=${1} ;;
        -ud | --use-unpinned-deps )
            USE_UNPINNED_DEPS=true ;;
        --skip | -s)
            shift
            SKIP_LIST+=(${1}) ;;
        --skip-conda)
            SKIP_LIST+=(1) ;;
        --skip-submodules)
            SKIP_LIST+=(2) ;;
        --skip-toolchain)
            SKIP_LIST+=(3) ;;
        --skip-ctags)
            SKIP_LIST+=(4) ;;
        --skip-precompile)
            SKIP_LIST+=(5 6) ;;
        --skip-firesim)
            SKIP_LIST+=(6 7) ;;
        --skip-marshal)
            SKIP_LIST+=(8 9) ;;
        --skip-circt)
            SKIP_LIST+=(10) ;;
        --skip-clean)
            SKIP_LIST+=(11) ;;
        * )
            error "invalid option $1"
            usage 1 ;;
    esac
    shift
done

# return true if the arg is not found in the SKIP_LIST
run_step() {
    local value=$1
    [[ ! " ${SKIP_LIST[*]} " =~ " ${value} " ]]
}

{

#######################################
###### BEGIN STEP-BY-STEP SETUP #######
#######################################

# In order to run code on error, we must handle errors manually
set +e;

function begin_step
{
    thisStepNum=$1;
    thisStepDesc=$2;
    echo " ========== BEGINNING STEP $thisStepNum: $thisStepDesc =========="
}
function exit_if_last_command_failed
{
    local exitcode=$?;
    if [ $exitcode -ne 0 ]; then
        die "Build script failed with exit code $exitcode at step $thisStepNum: $thisStepDesc" $exitcode;
    fi
}

function version_ge
{
    [ "$1" = "$2" ] && return 0
    [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -n1)" = "$1" ]
}

# add helper variable pointing to current chipyard top-level dir
replace_content env.sh cy-dir-helper "CY_DIR=${CYDIR}"

# setup and install pixi environment
if run_step "1"; then
    begin_step "1" "Pixi environment setup"
    PIXI_MANIFEST=$CYDIR/pixi-reqs/pixi.toml
    PIXI_LOCK=$CYDIR/pixi-reqs/pixi.lock
    MANIFEST_SYSROOT_VERSION=""

    # Detect host glibc and export an override for conda-style solving paths.
    # This helps avoid selecting binaries that require a newer glibc than host.
    HOST_GLIBC_VERSION=""
    if type ldd >& /dev/null; then
        HOST_GLIBC_VERSION="$(ldd --version 2>/dev/null | head -n1 | sed -E 's/.* ([0-9]+\.[0-9]+).*/\1/')"
        if [[ "$HOST_GLIBC_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
            export CONDA_OVERRIDE_GLIBC="$HOST_GLIBC_VERSION"
            echo "Detected host glibc $HOST_GLIBC_VERSION (exported CONDA_OVERRIDE_GLIBC)"
        fi
    fi

    if ! type pixi >& /dev/null; then
        die "pixi is required for step 1 but was not found on PATH"
    fi

    if [ ! -f "$PIXI_MANIFEST" ]; then
        die "Pixi manifest not found at $PIXI_MANIFEST"
    fi

    MANIFEST_SYSROOT_VERSION="$(grep -m1 -E '^sysroot_linux-64 = "[0-9]+\.[0-9]+\.\*"' "$PIXI_MANIFEST" | sed -E 's/.*"([0-9]+\.[0-9]+)\.\*".*/\1/')"

    if [[ "$HOST_GLIBC_VERSION" =~ ^[0-9]+\.[0-9]+$ ]] && [[ "$MANIFEST_SYSROOT_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
        if ! version_ge "$HOST_GLIBC_VERSION" "$MANIFEST_SYSROOT_VERSION"; then
            echo "Adjusting Pixi sysroot pin from $MANIFEST_SYSROOT_VERSION to host glibc $HOST_GLIBC_VERSION"
            sed -i.bak -E "s/^sysroot_linux-64 = \"[0-9]+\.[0-9]+\\.\*\"/sysroot_linux-64 = \"$HOST_GLIBC_VERSION.*\"/" "$PIXI_MANIFEST"
            rm -f "$PIXI_MANIFEST.bak"
            MANIFEST_SYSROOT_VERSION="$HOST_GLIBC_VERSION"
        fi
    fi

    if [ "$USE_LEAN_CONDA" = false ]; then
        PIXI_ENV_NAME="full"
    else
        PIXI_ENV_NAME="lean"
    fi

    if [ -n "$GLOBAL_ENV_NAME" ]; then
        die "--conda-env-name is not supported with Pixi environments"
    fi

    if [ "$USE_UNPINNED_DEPS" = true ]; then
        echo "WARNING: --use-unpinned-deps is ignored when using Pixi."
    fi

    LOCK_NEEDS_UPDATE=false
    LOCK_UPDATE_REASON=""
    LOCKED_GLIBC_VERSION=""

    if [ ! -f "$PIXI_LOCK" ]; then
        LOCK_NEEDS_UPDATE=true
        LOCK_UPDATE_REASON="missing lockfile"
    elif ! pixi lock --manifest-path "$PIXI_MANIFEST" --check > /dev/null 2>&1; then
        LOCK_NEEDS_UPDATE=true
        LOCK_UPDATE_REASON="manifest and lockfile are out of sync"
    else
        LOCKED_GLIBC_VERSION="$(grep -m1 -E 'sysroot_linux-64 ==[0-9]+\.[0-9]+' "$PIXI_LOCK" | sed -E 's/.*==([0-9]+\.[0-9]+).*/\1/')"
        if [ -z "$LOCKED_GLIBC_VERSION" ]; then
            LOCKED_GLIBC_VERSION="$(grep -m1 -E 'sysroot_linux-64-[0-9]+\.[0-9]+' "$PIXI_LOCK" | sed -E 's/.*sysroot_linux-64-([0-9]+\.[0-9]+).*/\1/')"
        fi
    fi

    if [[ "$HOST_GLIBC_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
        if [ -z "$LOCKED_GLIBC_VERSION" ]; then
            LOCK_NEEDS_UPDATE=true
            LOCK_UPDATE_REASON="unable to determine locked sysroot glibc"
        elif ! version_ge "$HOST_GLIBC_VERSION" "$LOCKED_GLIBC_VERSION"; then
            LOCK_NEEDS_UPDATE=true
            LOCK_UPDATE_REASON="host glibc $HOST_GLIBC_VERSION is older than locked sysroot $LOCKED_GLIBC_VERSION"
        fi
    fi

    if [ "$LOCK_NEEDS_UPDATE" = true ]; then
        echo "Refreshing Pixi lockfile ($LOCK_UPDATE_REASON)"
        pixi lock --manifest-path "$PIXI_MANIFEST"
        exit_if_last_command_failed
    else
        echo "Pixi lockfile is up to date; skipping lock resolution"
    fi

    PIXI_INSTALL_CMD=(pixi install --manifest-path "$PIXI_MANIFEST" --environment "$PIXI_ENV_NAME" --locked)
    printf -v PIXI_INSTALL_SHELL_CMD '%q ' "${PIXI_INSTALL_CMD[@]}"
    echo "Running: ${PIXI_INSTALL_CMD[*]}"

    if type script >& /dev/null; then
        script -qefc "$PIXI_INSTALL_SHELL_CMD" /dev/null
    else
        "${PIXI_INSTALL_CMD[@]}"
    fi
    exit_if_last_command_failed

    OLD_BASH_XTRACEFD="${BASH_XTRACEFD-}"
    exec {PIXI_XTRACE_FD}>/dev/null
    export BASH_XTRACEFD="$PIXI_XTRACE_FD"
    set +x
    eval "$(pixi shell-hook --as-is --manifest-path "$PIXI_MANIFEST" --environment "$PIXI_ENV_NAME")"
    set +x
    if [ -n "$OLD_BASH_XTRACEFD" ]; then
        export BASH_XTRACEFD="$OLD_BASH_XTRACEFD"
    else
        unset BASH_XTRACEFD
    fi
    exec {PIXI_XTRACE_FD}>&-
    exit_if_last_command_failed

    PIXI_ENV_PREFIX="$CYDIR/pixi-reqs/.pixi/envs/$PIXI_ENV_NAME"

    # Pixi setup
    # Provide a sourceable snippet that can be used in subshells that may not have
    # inherited shell state from an interactive session (e.g., VSCode, CI)
    read -r -d '\0' PIXI_ACTIVATE_PREAMBLE <<'END_PIXI_ACTIVATE'
if ! type pixi >& /dev/null; then
    echo "::ERROR:: you must have pixi in your environment first"
    return 1  # don't want to exit here because this file is sourced
fi
\0
END_PIXI_ACTIVATE

    replace_content env.sh build-setup-conda "# line auto-generated by $0
$PIXI_ACTIVATE_PREAMBLE

if ! type python3 >& /dev/null; then
    echo \"::ERROR:: python3 is required to parse pixi JSON shell-hook output\"
    return 1
fi

eval \"\$(pixi shell-hook --json --as-is --manifest-path $CYDIR/pixi-reqs/pixi.toml --environment $PIXI_ENV_NAME | python3 -c 'import json, shlex, sys; d = json.load(sys.stdin).get(\"environment_variables\", {}); print(\"\\n\".join(f\"export {k}={shlex.quote(v)}\" for k, v in d.items()))')\"
if [ \$? -ne 0 ]; then
    echo \"::ERROR:: failed to activate Pixi environment metadata\"
    return 1
fi

DRAMSIM2_INCLUDE="$CYDIR/tools/DRAMSim2"

if [ -n "\$RISCV" ]; then
    if [ -n "\${C_INCLUDE_PATH-}" ]; then
        export C_INCLUDE_PATH="\$RISCV/include:\$DRAMSIM2_INCLUDE:\$C_INCLUDE_PATH"
    else
        export C_INCLUDE_PATH="\$RISCV/include:\$DRAMSIM2_INCLUDE"
    fi

    if [ -n "\${CPLUS_INCLUDE_PATH-}" ]; then
        export CPLUS_INCLUDE_PATH="\$RISCV/include:\$DRAMSIM2_INCLUDE:\$CPLUS_INCLUDE_PATH"
    else
        export CPLUS_INCLUDE_PATH="\$RISCV/include:\$DRAMSIM2_INCLUDE"
    fi
fi

echo \"Chipyard Pixi environment activated in current shell\"

# After 'pixi add/remove/update', automatically re-install the active environment
# (full or lean) so the change takes effect immediately.
pixi() {
    command pixi \"\$@\"
    local ret=\$?
    if [[ \$ret -eq 0 && \"\$1\" =~ ^(add|remove|update)\$ ]]; then
        echo \":: Re-installing pixi environment '\${PIXI_ENVIRONMENT_NAME}' ...\"
        command pixi install --manifest-path \"$CYDIR/pixi-reqs/pixi.toml\" \\
            --environment \"\${PIXI_ENVIRONMENT_NAME:-$PIXI_ENV_NAME}\"
    fi
    return \$ret
}

source $CYDIR/scripts/fix-open-files.sh"
fi

if run_step "1" && [ -z "$PIXI_ENV_NAME" ]; then
    echo "!!!!! WARNING: No Pixi environment selected in step 1."
fi

# initialize all submodules (without the toolchain submodules)
if run_step "2"; then
    begin_step "2" "Initializing Chipyard submodules"
    $CYDIR/scripts/init-submodules-no-riscv-tools.sh --full
    exit_if_last_command_failed
fi

# build extra toolchain collateral (i.e. spike, pk, riscv-tests, libgloss)
if run_step "3"; then
    begin_step "3" "Building toolchain collateral"
    if run_step "1"; then
        PREFIX=$PIXI_ENV_PREFIX/$TOOLCHAIN_TYPE
    else
        if [ -z "$RISCV" ] ; then
            error "ERROR: If environment initialization is skipped, \$RISCV variable must be defined."
            exit 1
        fi
        PREFIX=$RISCV
    fi
    $CYDIR/scripts/build-toolchain-extra.sh $TOOLCHAIN_TYPE -p $PREFIX
    exit_if_last_command_failed
fi

# run ctags for code navigation
if run_step "4"; then
    begin_step "4" "Running ctags for code navigation"
    $CYDIR/scripts/gen-tags.sh
    exit_if_last_command_failed
fi

# precompile chipyard scala sources
if run_step "5"; then
    begin_step "5" "Pre-compiling Chipyard Scala sources"
    pushd $CYDIR/sims/verilator &&
    make launch-sbt SBT_COMMAND=";project chipyard; compile" &&
    make launch-sbt SBT_COMMAND=";project tapeout; compile" &&
    popd
    exit_if_last_command_failed
fi

# setup firesim
if run_step "6"; then
    begin_step "6" "Setting up FireSim"
    $CYDIR/scripts/firesim-setup.sh &&
    $CYDIR/sims/firesim/gen-tags.sh
    exit_if_last_command_failed

    # precompile firesim scala sources
    if run_step "7"; then
        begin_step "7" "Pre-compiling Firesim Scala sources"
        pushd $CYDIR/sims/firesim &&
        (
            set -e # Subshells un-set "set -e" so it must be re enabled
            source sourceme-manager.sh --skip-ssh-setup
            pushd sim
            # avoid directly building classpath s.t. target-injected files can be recompiled
            make sbt SBT_COMMAND="compile"
            popd
        )
        exit_if_last_command_failed
        popd
    fi
fi

# setup firemarshal
if run_step "8"; then
    begin_step "8" "Setting up FireMarshal"
    pushd $CYDIR/software/firemarshal &&
    ./init-submodules.sh
    exit_if_last_command_failed

    # precompile firemarshal buildroot sources
    if run_step "9"; then
        begin_step "9" "Pre-compiling FireMarshal buildroot sources"
        source $CYDIR/scripts/fix-open-files.sh &&
        ./marshal $VERBOSE_FLAG build br-base.json &&
        ./marshal $VERBOSE_FLAG build bare-base.json
        exit_if_last_command_failed
    fi
    popd
    # Ensure FireMarshal CLI is on PATH in env.sh (idempotent)
    replace_content env.sh build-setup-marshal "# line auto-generated by build-setup.sh\n__DIR=\"$CYDIR\"\nPATH=\\$__DIR/software/firemarshal:\\$PATH"
fi

if run_step "10"; then
    begin_step "10" "Installing CIRCT"
    # install CIRCT into the selected environment prefix
    if run_step "1"; then
        PREFIX=$PIXI_ENV_PREFIX/$TOOLCHAIN_TYPE
    else
        if [ -z "$RISCV" ] ; then
            error "ERROR: If environment initialization is skipped, \$RISCV variable must be defined."
            exit 1
        fi
        PREFIX=$RISCV
    fi

    if [ "$BUILD_CIRCT" = true ] ; then
	echo "Building CIRCT from source, and installing to $PREFIX"
	$CYDIR/scripts/build-circt-from-source.sh --prefix $PREFIX
    else
	echo "Downloading CIRCT from nightly build"

	git submodule update --init $CYDIR/tools/install-circt &&
	    $CYDIR/tools/install-circt/bin/download-release-or-nightly-circt.sh \
		-f circt-full-static-linux-x64.tar.gz \
		-i $PREFIX \
		-v version-file \
		-x $CYDIR/pixi-reqs/circt.json \
		-g $GITHUB_TOKEN
    fi
    exit_if_last_command_failed
fi


# do misc. cleanup for a "clean" git status
if run_step "11"; then
    begin_step "11" "Cleaning up repository"
    $CYDIR/scripts/repo-clean.sh
    exit_if_last_command_failed
fi

echo "Setup complete!"

} 2>&1 | tee build-setup.log
