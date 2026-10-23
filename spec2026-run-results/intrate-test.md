# SPEC2026 intrate test results

Updated: 2026-10-23. All run-directory timestamps are UTC.

Timing results are available for **all 14 benchmarks**: 13 use the completed 2026-10-23 02:04 suite run, and CPython uses its successful 03:55 corrected rerun. The suite run still contained the missing-model CPython failure, so that failed attempt is excluded from the primary results. Benchmark output correctness has not been formally validated; these are test-input execution measurements, not SPEC reference scores.

The primary source runs are:

- Completed suite: [2026-10-23--02-04-22-spec-intrate-test](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test).
- Corrected CPython: [2026-10-23--03-55-22-spec-intrate-test-714.cpython](../sims/firesim/deploy/results-workload/2026-10-23--03-55-22-spec-intrate-test-714.cpython).
- Suite manager log: [2026-10-23--02-04-22-runworkload-LF9NHTQFOIOU4CD8.log](../sims/firesim/deploy/logs/2026-10-23--02-04-22-runworkload-LF9NHTQFOIOU4CD8.log). It reports all 14 simulator jobs collected and `FireSim Simulation Exited Successfully`; CPython's benchmark-level failure still requires the corrected result above.

The benchmarks used the following setup:

| Setting | Value |
|---|---|
| Suite and inputs | SPEC CPU2026 integer rate (`intrate`), `test` input size |
| Benchmark execution | `./intrate.sh <benchmark> --copies 1`: one independent benchmark instance per simulated machine |
| Benchmark threads | Single-thread configuration (`THREADS=1` when generating SPEC commands); rate workloads use `--copies 1` rather than the intspeed `--threads` option |
| Simulated CPU cores / hardware threads | One RISC-V core / hart per simulated machine; OpenSBI reports `Platform HART Count: 1` |
| Target ISA | RV64IMAFDC (`rv64imafdc` reported by OpenSBI) |
| Guest RAM | **16 GiB** per simulated machine; Linux reports 16,777,216 KiB total physical memory |
| Rootfs disk | **8 GiB** (8,589,934,592 bytes) per benchmark image, explicitly configured for both the parent workload and its runnable job |
| Guest OS | Buildroot base (`br-base.json`), Linux `6.16.0-gef4d69f8a3aa` |
| FireSim hardware configuration | `firesim_megaboom_singlecore_no_nic_l2_llc4mb_ddr3` |
| FPGA image | `agfi-0bada298b0eea9267` |
| Reported FPGA host clock | 40.000 MHz in every collected UART summary |
| Suite batch deployment | 14 AWS `f2.6xlarge` hosts, one FPGA / simulated machine / benchmark job per host |
| Corrected CPython deployment | One AWS `f2.6xlarge` host and one simulated machine |
| Topology | `no_net_config`; 14 nodes in the suite batch, one node for the CPython rerun |
| Instruction tracing / IPC counters | TracerV recording disabled; no retired-instruction or AutoCounter result files collected |

The thread and copy settings control benchmark execution on the simulated RISC-V core. Host compilation parallelism is a separate build setting. Guest RAM and rootfs disk capacity are also separate: these runs have 16 GiB of RAM and an 8 GiB disk per simulated machine.

Setup evidence: the [per-benchmark FireMarshal configurations](../software/spec2026/marshal-configs), [single-thread build helper](../software/spec2026/build-int-single-thread.sh), [saved hardware summary](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-706.stockfish-706.stockfish_r/HW_CFG_SUMMARY), [suite batch UART log](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-706.stockfish-706.stockfish_r/uartlog), and [corrected CPython manager log](../sims/firesim/deploy/logs/2026-10-23--03-55-22-runworkload-YEAJM0GY5Q6PEW8E.log).

**Timing definitions:** Guest elapsed time is `/usr/bin/time`'s `RealTime` inside RISC-V Linux: the simulated wall-clock duration of the benchmark command. Guest user and kernel times are its CPU-time breakdown. Host emulation wall time is FireSim's `Wallclock Time Elapsed`: real-life time spent emulating the whole run, including Linux boot, the benchmark, wrapper waits, and shutdown. It excludes run-farm provisioning and infrastructure setup. The two elapsed-time columns cover different intervals.

The benchmark names below link to their raw timing CSVs. All timing values are seconds; CPython comes from the corrected run.

| Benchmark | Guest elapsed (s) | Guest user CPU (s) | Guest kernel CPU (s) | Host emulation wall (s) | Result source |
|---|---:|---:|---:|---:|---|
| [706.stockfish_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-706.stockfish-706.stockfish_r/output/706.stockfish_r_0.csv) | 17.88 | 16.75 | 0.95 | 641.5 | 02:04 suite run |
| [707.ntest_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-707.ntest-707.ntest_r/output/707.ntest_r_0.csv) | 1.51 | 1.39 | 0.09 | 338.6 | 02:04 suite run |
| [708.sqlite_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-708.sqlite-708.sqlite_r/output/708.sqlite_r_0.csv) | 1.17 | 1.16 | 0.00 | 335.8 | 02:04 suite run |
| [710.omnetpp_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-710.omnetpp-710.omnetpp_r/output/710.omnetpp_r_0.csv) | 0.49 | 0.42 | 0.04 | 338.9 | 02:04 suite run |
| [714.cpython_r](../sims/firesim/deploy/results-workload/2026-10-23--03-55-22-spec-intrate-test-714.cpython/spec-intrate-test-714.cpython-714.cpython_r/output/714.cpython_r_0.csv) | 2.92 | 2.63 | 0.22 | 357.4 | Corrected CPython rerun |
| [721.gcc_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-721.gcc-721.gcc_r/output/721.gcc_r_0.csv) | 0.14 | 0.04 | 0.05 | 342.1 | 02:04 suite run |
| [723.llvm_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-723.llvm-723.llvm_r/output/723.llvm_r_0.csv) | 2.14 | 1.93 | 0.13 | 361.3 | 02:04 suite run |
| [727.cppcheck_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-727.cppcheck-727.cppcheck_r/output/727.cppcheck_r_0.csv) | 135.41 | 134.31 | 0.69 | 5060.2 | 02:04 suite run |
| [729.abc_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-729.abc-729.abc_r/output/729.abc_r_0.csv) | 6.32 | 6.01 | 0.27 | 398.1 | 02:04 suite run |
| [734.vpr_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-734.vpr-734.vpr_r/output/734.vpr_r_0.csv) | 117.04 | 111.12 | 5.60 | 4385.2 | 02:04 suite run |
| [735.gem5_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-735.gem5-735.gem5_r/output/735.gem5_r_0.csv) | 13.06 | 12.84 | 0.14 | 615.6 | 02:04 suite run |
| [750.sealcrypto_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-750.sealcrypto-750.sealcrypto_r/output/750.sealcrypto_r_0.csv) | 58.74 | 58.37 | 0.23 | 1893.0 | 02:04 suite run |
| [753.ns3_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-753.ns3-753.ns3_r/output/753.ns3_r_0.csv) | 25.32 | 25.14 | 0.08 | 1011.4 | 02:04 suite run |
| [777.zstd_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-777.zstd-777.zstd_r/output/777.zstd_r_0.csv) | 1.65 | 1.57 | 0.07 | 346.1 | 02:04 suite run |

The UART logs also provide the whole-simulation statistics below. Each benchmark name links to its UART log.

| Benchmark | Total target cycles | Effective emulation rate (MHz) | FMR |
|---|---:|---:|---:|
| [706.stockfish_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-706.stockfish-706.stockfish_r/uartlog) | 22,559,620,547 | 35.167 | 1.14 |
| [707.ntest_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-707.ntest-707.ntest_r/uartlog) | 12,481,666,892 | 36.863 | 1.09 |
| [708.sqlite_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-708.sqlite-708.sqlite_r/uartlog) | 12,481,666,892 | 37.168 | 1.08 |
| [710.omnetpp_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-710.omnetpp-710.omnetpp_r/uartlog) | 12,503,719,307 | 36.897 | 1.08 |
| [714.cpython_r](../sims/firesim/deploy/results-workload/2026-10-23--03-55-22-spec-intrate-test-714.cpython/spec-intrate-test-714.cpython-714.cpython_r/uartlog) | 12,547,824,137 | 35.111 | 1.14 |
| [721.gcc_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-721.gcc-721.gcc_r/uartlog) | 12,503,719,307 | 36.548 | 1.09 |
| [723.llvm_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-723.llvm-723.llvm_r/uartlog) | 12,503,719,307 | 34.610 | 1.16 |
| [727.cppcheck_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-727.cppcheck-727.cppcheck_r/uartlog) | 143,076,068,522 | 28.275 | 1.41 |
| [729.abc_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-729.abc-729.abc_r/uartlog) | 12,503,719,307 | 31.410 | 1.27 |
| [734.vpr_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-734.vpr-734.vpr_r/uartlog) | 122,964,266,042 | 28.041 | 1.43 |
| [735.gem5_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-735.gem5-735.gem5_r/uartlog) | 22,625,777,792 | 36.756 | 1.09 |
| [750.sealcrypto_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-750.sealcrypto-750.sealcrypto_r/uartlog) | 62,717,068,262 | 33.131 | 1.21 |
| [753.ns3_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-753.ns3-753.ns3_r/uartlog) | 32,593,469,372 | 32.225 | 1.24 |
| [777.zstd_r](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-777.zstd-777.zstd_r/uartlog) | 12,503,719,307 | 36.131 | 1.11 |

Effective emulation rate is the number of simulated target cycles per real-life host second, expressed in millions. It is not the target processor's configured clock frequency. FMR is the reported FPGA-host-cycle to target-cycle ratio; a value near 1 means little FPGA-cycle overhead. These cycle and rate figures refer to the fastest target clock and cover the entire simulation, including boot and waits; they are not benchmark-region cycle counts.

The [intrate wrapper](../software/spec2026/speckle/spec26-run-scripts/intrate.sh) sleeps for 10 guest seconds before its first completion check and polls at 10-second intervals afterward. For short tests, that wait dominates real-life emulation time. This explains why GCC reports 0.14 guest benchmark seconds but 342.1 seconds of host emulation time. Per-benchmark host times must not be summed and described as batch elapsed time: the suite jobs ran concurrently, and CPython was rerun separately.

The [suite manager log](../sims/firesim/deploy/logs/2026-10-23--02-04-22-runworkload-LF9NHTQFOIOU4CD8.log) spans 2026-10-23 **02:04:22.636–03:28:59.882 UTC**, approximately **84 minutes 37 seconds**. This is the logged duration of that `runworkload` invocation, including launch, monitoring, and result collection. Infrastructure setup and the later corrected CPython rerun are outside that interval.

**IPC is unavailable.** No retired-instruction counters or AutoCounter result files were collected, and the UART logs explicitly say instruction tracing was disabled. IPC requires retired instructions and core cycles over the same measurement interval (`IPC = delta(instret) / delta(core cycles)`). Neither benchmark elapsed time nor the whole-simulation cycle total supplies the missing retired-instruction count.

Cppcheck, VPR, and Sealcrypto now have complete timing and UART records. Their host emulation times were **84 minutes 20.2 seconds**, **73 minutes 5.2 seconds**, and **31 minutes 33.0 seconds**, respectively. The earlier 23:38 run was interrupted after about 31 minutes while all three simulator sessions were still running. The new run establishes that these test workloads can complete; the old absence of statistics is no longer an unresolved gap in this report.

The newly collected outputs also provide these execution checks:

- [Cppcheck output](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-727.cppcheck-727.cppcheck_r/output/727.cppcheck_r_0.out): `Testing Complete`, 4,404 tests, 335 todos, and `Tests failed: 0`; it then runs the `hello.c` check.
- [VPR output](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-734.vpr-734.vpr_r/output/734.vpr_r_0.out): ends with `VPR succeeded` and `VPR success: 1`.
- [Sealcrypto output](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-750.sealcrypto-750.sealcrypto_r/output/750.sealcrypto_r_0.out): the encrypted lookup for `Ecuador` returns `Quito`.

CPython in the 02:04 suite still failed after **2.61 guest seconds** and **353.3 host seconds** because `PoseNetMobileNet100S16FP16.mlmodel` was omitted from the disk image. Its [failed timing CSV](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-714.cpython-714.cpython_r/output/714.cpython_r_0.csv) and [traceback](../sims/firesim/deploy/results-workload/2026-10-23--02-04-22-spec-intrate-test/spec-intrate-test-714.cpython-714.cpython_r/output/714.cpython_r_0.err) are retained as historical evidence and excluded from the primary results. After the input was restored, the 03:55 rerun recorded **2.92 guest seconds**, **357.4 host seconds**, empty stderr, and output showing two successful model serializations. See the [corrected benchmark output](../sims/firesim/deploy/results-workload/2026-10-23--03-55-22-spec-intrate-test-714.cpython/spec-intrate-test-714.cpython-714.cpython_r/output/714.cpython_r_0.out).

The `*** PASSED ***` UART marker and the manager's successful simulation exit confirm simulator completion and result collection; they are not proof of SPEC output validation. The failed CPython attempt also printed the UART marker, so execution status must be checked against benchmark output and timing records.

The original [2026-10-22--23-38-14-spec-intrate-test](../sims/firesim/deploy/results-workload/2026-10-22--23-38-14-spec-intrate-test) run and its [partial-statistics.csv](../sims/firesim/deploy/results-workload/2026-10-22--23-38-14-spec-intrate-test/partial-statistics.csv) remain historical sources. Their values have been superseded in the primary tables by the completed 02:04 suite run and the corrected CPython rerun. The original manager aborted at 00:09:31 UTC on an SSH protocol-banner error before collecting Cppcheck, VPR, and Sealcrypto; the farm was subsequently terminated.
