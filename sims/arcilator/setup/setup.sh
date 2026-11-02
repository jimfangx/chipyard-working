# Sourced by Chipyard setup to construct and activate native Arcilator tools.
if [ "$(uname -m)" = x86_64 ] && [ "$BUILD_CIRCT" = false ]; then
    if run_step "1"; then
        ARC_SETUP_SDK=$CONDA_PREFIX/$TOOLCHAIN_TYPE
    else
        ARC_SETUP_SDK=${RISCV:?Source env.sh before skipping Conda setup}
    fi
    ARC_SETUP_PREFIX=${CONDA_PREFIX:?Activate the Chipyard Conda environment before Arcilator setup}
    ARC_SETUP_ENV=$ARC_SETUP_PREFIX/arcilator-env.sh
    (
        set -e
        export RISCV="$ARC_SETUP_SDK"
        export PATH="$RISCV/bin:$PATH"
        # Step 3 normally installs Espresso. Cover existing/lean setups
        # that skipped that step before generating the reference models.
        if [ ! -x "$RISCV/bin/espresso" ]; then
            git -C "$CYDIR" submodule update --init generators/constellation
            (
                cd "$CYDIR/generators/constellation"
                MAKEFLAGS="-j${ARC_BUILD_JOBS:-$(nproc)}" scripts/install-espresso.sh "$RISCV"
            )
            test -x "$RISCV/bin/espresso"
        fi
        python3 "$CYDIR/sims/arcilator/compiler/toolchain.py" setup \
            --sdk "$ARC_SETUP_SDK" --jobs "${ARC_BUILD_JOBS:-$(nproc)}" \
            --work "$ARC_SETUP_PREFIX/arcilator-toolchain" \
            --activation "$ARC_SETUP_ENV"
    )
    exit_if_last_command_failed
    printf -v ARC_SETUP_SOURCE '. %q' "$ARC_SETUP_ENV"
    replace_content "$CYDIR/env.sh" build-setup-arcilator "$ARC_SETUP_SOURCE"
    exit_if_last_command_failed
else
    echo "Optimized Arcilator construction is qualified for the prebuilt Linux x86-64 CIRCT SDK."
    echo "Using the installed native CIRCT tools for this architecture/source build instead."
    replace_content "$CYDIR/env.sh" build-setup-arcilator \
        "# Optimized Arcilator activation is disabled for this SDK."
    exit_if_last_command_failed
fi
