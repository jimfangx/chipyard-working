Arcilator (Experimental)
-----------------------

The ``sims/arcilator`` backend compiles Chisel-generated hardware with CIRCT's
Arcilator and LLVM. Its default native runtime schedules clocks and asynchronous
register banks and connects the original C/C++ peripheral drivers, including
DRAMSim2, SimUART, SimTSI, SimJTAG, and SimDTM. It does not require Verilator to
build or run. Ordinary RTL blackboxes can be imported through CIRCT's Verilog
frontend. An optional ``ARC_RUNTIME=hybrid`` reference still uses Verilator.

The standard Chipyard setup installs the matching full CIRCT
firtool-1.162.0 suite with its headers and libraries. Source ``env.sh`` to
activate the environment; the backend discovers the suite on ``PATH``.
Existing environments with older CIRCT tools must rerun setup step 10.
On Linux x86-64, setup step 12 also constructs and qualifies the optimized
native LLVM toolchain and arranges activation through the same ``env.sh``.
The normal setup installs its pinned Conda dependencies and supplies their
CMake search paths automatically. No separate toolchain build or activation
command is needed after successful setup. ``--skip-arcilator`` skips this
one-time optimized-toolchain construction.
For example, from the Chipyard root:

.. code-block:: shell

    source env.sh
    cd sims/arcilator
    make CONFIG=RocketConfig
    make CONFIG=RocketConfig run-binary-fast \
        BINARY=/absolute/path/to/program.riscv

The backend uses the shared configuration and simulation targets. Its
``README.md`` lists the backend files; simulation sources and generated outputs
live under ``sims/arcilator/simulation``.
