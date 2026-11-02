# Sourced by Chipyard setup after installing the matching CIRCT SDK.
# The prebuilt Linux SDK loads the distro SONAME libz3.so.4. Conda's
# compatible Z3 4.x package uses a minor-version SONAME (e.g. .so.4.16).
# CIRCT already searches PREFIX/lib; point it at the environment's library
# so installation does not depend on a host-system Z3 package.
if [ -n "${CONDA_PREFIX:-}" ] && [ -f "$CONDA_PREFIX/lib/libz3.so" ]; then
    mkdir -p "$PREFIX/lib"
    exit_if_last_command_failed
    if [ "$(realpath "$PREFIX/lib")" != "$(realpath "$CONDA_PREFIX/lib")" ]; then
        # Newly linked frontend tools request Conda's own SONAME too.
        for CIRCT_Z3_LIBRARY in "$CONDA_PREFIX"/lib/libz3.so*; do
            ln -sfn "$(realpath --no-symlinks --relative-to="$PREFIX/lib" "$CIRCT_Z3_LIBRARY")" \
                "$PREFIX/lib/${CIRCT_Z3_LIBRARY##*/}"
            exit_if_last_command_failed
        done
    fi
    if [ ! -e "$PREFIX/lib/libz3.so.4" ]; then
        ln -sfn "$(realpath --no-symlinks --relative-to="$PREFIX/lib" "$CONDA_PREFIX/lib/libz3.so")" \
            "$PREFIX/lib/libz3.so.4"
        exit_if_last_command_failed
    fi
    # SDK CMake exports also embed the release builder's distro Z3 path.
    # Native frontend plugins must link the same environment library.
    if [ -f "$PREFIX/lib/cmake/llvm/LLVMExports.cmake" ]; then
        sed -i 's|/usr/lib/[^";]*libz3\.so|${_IMPORT_PREFIX}/lib/libz3.so.4|g' \
            "$PREFIX/lib/cmake/llvm/LLVMExports.cmake"
        exit_if_last_command_failed
    fi
fi
"$PREFIX/bin/circt-opt" --version > /dev/null
exit_if_last_command_failed
