On Linux x86-64 with the prebuilt CIRCT SDK, step 12 builds and qualifies the
optimized Arcilator compiler tools and adds their activation to ``env.sh``.
The Conda lockfiles include the matching Clang 18, linker, profile tools and
development libraries. This one-time compiler construction can take substantial
time and memory; ``ARC_BUILD_JOBS`` controls its workers and defaults to the
available CPUs. Repeating this step validates completed tools or resumes an
identical interrupted construction. Source-built SDKs and other architectures
retain the ordinary native CIRCT flow.
The setup-managed compilers live under ``$CONDA_PREFIX/arcilator-toolchain``
so cleaning a simulator's generated files does not remove them.
