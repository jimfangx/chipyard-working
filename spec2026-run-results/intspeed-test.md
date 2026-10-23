# SPEC2026 intspeed test results

Updated: 2026-10-23. All run-directory timestamps are UTC.

Timing results are available for **all 13 benchmarks** from the 2026-10-23 04:55 suite run. All 13 simulator sessions completed, the manager collected their results, and no timing CSV records an explicit nonzero command exit. Benchmark output correctness has not been formally validated against SPEC reference outputs; these are test-input execution measurements, not SPEC reference scores.

The source run is:

- Completed suite: [2026-10-23--04-55-25-spec-intspeed-test](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test).
- Suite manager log: [2026-10-23--04-55-25-runworkload-82TL4CUYJ1G0RHDJ.log](../sims/firesim/deploy/logs/2026-10-23--04-55-25-runworkload-82TL4CUYJ1G0RHDJ.log). It reports all 13 jobs complete and `FireSim Simulation Exited Successfully`.

The benchmarks used the following setup:

| Setting | Value |
|---|---|
| Suite and inputs | SPEC CPU2026 integer speed (`intspeed`), `test` input size |
| Benchmark execution | `./intspeed.sh <benchmark> --threads 1`: one benchmark run per simulated machine |
| Benchmark threads | One requested benchmark thread; the wrapper sets `OMP_NUM_THREADS=1`, and SPEC command generation uses `THREADS=1` for embedded thread arguments |
| Simulated CPU cores / hardware threads | One RISC-V core / hart per simulated machine; OpenSBI reports `Platform HART Count: 1` |
| Target ISA | RV64IMAFDC (`rv64imafdc` reported by OpenSBI) |
| Guest RAM | **16 GiB** per simulated machine; Linux reports 16,777,216 KiB total physical memory |
| Rootfs disk | **8 GiB** (8,589,934,592 bytes) per benchmark image, explicitly configured for both the parent workload and its runnable job |
| Guest OS | Buildroot base (`br-base.json`), Linux `6.16.0-gef4d69f8a3aa` |
| FireSim hardware configuration | `firesim_megaboom_singlecore_no_nic_l2_llc4mb_ddr3` |
| FPGA image | `agfi-0bada298b0eea9267` |
| Reported FPGA host clock | 40.000 MHz in every collected UART summary |
| Suite batch deployment | 13 AWS `f2.6xlarge` hosts, one FPGA / simulated machine / benchmark job per host |
| Topology | `no_net_config`; 13 simulated nodes |
| Instruction tracing / IPC counters | TracerV recording disabled; AutoCounter read rate 0; no retired-instruction or AutoCounter result files collected |

The thread setting controls benchmark execution on the simulated RISC-V core. Host compilation parallelism is a separate build setting. Guest RAM and rootfs disk capacity are also separate: these runs have 16 GiB of RAM and an 8 GiB disk per simulated machine.

Setup evidence: the [per-benchmark FireMarshal configurations](../software/spec2026/marshal-configs), [single-thread build helper](../software/spec2026/build-int-single-thread.sh), [intspeed wrapper](../software/spec2026/speckle/spec26-run-scripts/intspeed.sh), [saved hardware summary](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-801.xz-801.xz_s/HW_CFG_SUMMARY), and [suite UART log](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-801.xz-801.xz_s/uartlog).

**Timing definitions:** Guest elapsed time is `/usr/bin/time`'s `RealTime` inside RISC-V Linux: the simulated wall-clock duration of the benchmark command. Guest user and kernel times are its CPU-time breakdown. Host emulation wall time is FireSim's `Wallclock Time Elapsed`: real-life time spent emulating the whole run, including Linux boot, the benchmark, and shutdown. It excludes run-farm provisioning and infrastructure setup. The two elapsed-time columns cover different intervals.

The benchmark names below link to their raw timing CSVs. All timing values are seconds.

| Benchmark | Guest elapsed (s) | Guest user CPU (s) | Guest kernel CPU (s) | Host emulation wall (s) | Collection status |
|---|---:|---:|---:|---:|---|
| [801.xz_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-801.xz-801.xz_s/output/801.xz_s.csv) | 45.69 | 29.80 | 15.85 | 1523.3 | Collected |
| [807.ntest_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-807.ntest-807.ntest_s/output/807.ntest_s.csv) | 1.46 | 1.37 | 0.06 | 124.3 | Collected |
| [817.flac_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-817.flac-817.flac_s/output/817.flac_s.csv) | 20.40 | 19.50 | 0.64 | 653.4 | Collected |
| [821.gcc_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-821.gcc-821.gcc_s/output/821.gcc_s.csv) | 0.31 | 0.11 | 0.14 | 99.2 | Collected |
| [823.llvm_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-823.llvm-823.llvm_s/output/823.llvm_s.csv) | 8.69 | 8.36 | 0.23 | 378.0 | Collected |
| [827.cppcheck_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-827.cppcheck-827.cppcheck_s/output/827.cppcheck_s.csv) | 167.72 | 166.43 | 1.05 | 5809.1 | Collected |
| [829.abc_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-829.abc-829.abc_s/output/829.abc_s.csv) | 6.32 | 5.99 | 0.29 | 304.6 | Collected |
| [834.vpr_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-834.vpr-834.vpr_s/output/834.vpr_s.csv) | 117.25 | 111.58 | 5.59 | 4301.2 | Collected |
| [835.gem5_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-835.gem5-835.gem5_s/output/835.gem5_s.csv) | 13.03 | 12.81 | 0.17 | 437.0 | Collected |
| [838.diamond_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-838.diamond-838.diamond_s/output/838.diamond_s.csv) | 67.72 | 53.24 | 14.44 | 1804.8 | Collected |
| [846.minizinc_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-846.minizinc-846.minizinc_s/output/846.minizinc_s.csv) | 2.88 | 2.54 | 0.30 | 190.7 | Collected |
| [853.ns3_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-853.ns3-853.ns3_s/output/853.ns3_s.csv) | 25.21 | 25.08 | 0.07 | 886.5 | Collected |
| [854.graph500_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-854.graph500-854.graph500_s/output/854.graph500_s.csv) | 32.91 | 32.12 | 0.57 | 1738.5 | Collected |

The UART logs also provide the whole-simulation statistics below. Each benchmark name links to its UART log.

| Benchmark | Total target cycles | Effective emulation rate (MHz) | FMR |
|---|---:|---:|---:|
| [801.xz_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-801.xz-801.xz_s/uartlog) | 48,162,474,362 | 31.618 | 1.27 |
| [807.ntest_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-807.ntest-807.ntest_s/uartlog) | 3,925,329,872 | 31.570 | 1.27 |
| [817.flac_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-817.flac-817.flac_s/uartlog) | 22,912,459,187 | 35.068 | 1.14 |
| [821.gcc_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-821.gcc-821.gcc_s/uartlog) | 2,778,604,292 | 27.996 | 1.43 |
| [823.llvm_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-823.llvm-823.llvm_s/uartlog) | 11,158,521,992 | 29.521 | 1.35 |
| [827.cppcheck_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-827.cppcheck-827.cppcheck_s/uartlog) | 170,178,486,557 | 29.295 | 1.37 |
| [829.abc_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-829.abc-829.abc_s/uartlog) | 8,776,861,172 | 28.814 | 1.39 |
| [834.vpr_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-834.vpr-834.vpr_s/uartlog) | 119,700,508,622 | 27.830 | 1.44 |
| [835.gem5_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-835.gem5-835.gem5_s/uartlog) | 15,502,847,747 | 35.472 | 1.13 |
| [838.diamond_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-838.diamond-838.diamond_s/uartlog) | 70,170,784,532 | 38.880 | 1.03 |
| [846.minizinc_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-846.minizinc-846.minizinc_s/uartlog) | 5,336,684,432 | 27.986 | 1.43 |
| [853.ns3_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-853.ns3-853.ns3_s/uartlog) | 27,675,780,827 | 31.220 | 1.28 |
| [854.graph500_s](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-854.graph500-854.graph500_s/uartlog) | 35,372,073,662 | 20.346 | 1.97 |

Effective emulation rate is the number of simulated target cycles per real-life host second, expressed in millions. It is not the target processor's configured clock frequency. FMR is the reported FPGA-host-cycle to target-cycle ratio; a value near 1 means little FPGA-cycle overhead. These cycle and rate figures refer to the fastest target clock and cover the entire simulation, including boot and shutdown; they are not benchmark-region cycle counts.

The intspeed wrapper runs its benchmark script in the foreground and has no fixed 10-second completion-polling sleep. Host emulation time still includes boot and shutdown overhead; for example, GCC reports 0.31 guest benchmark seconds and 99.2 host emulation seconds. The per-benchmark host times must not be summed and described as batch elapsed time because all 13 jobs ran concurrently.

The [suite manager log](../sims/firesim/deploy/logs/2026-10-23--04-55-25-runworkload-82TL4CUYJ1G0RHDJ.log) spans 2026-10-23 **04:55:25.289–06:32:25.416 UTC**, approximately **97 minutes**. This is the logged duration of the `runworkload` invocation, including launch, monitoring, and result collection. Run-farm provisioning and infrastructure setup are outside that interval. Cppcheck was the longest-running collected simulation at **5,809.1 host seconds (96 minutes 49.1 seconds)**, followed by VPR at **4,301.2 host seconds (71 minutes 41.2 seconds)**.

**IPC is unavailable.** No retired-instruction counters or AutoCounter result files were collected, and the UART logs explicitly say instruction tracing was disabled. IPC requires retired instructions and core cycles over the same measurement interval (`IPC = delta(instret) / delta(core cycles)`). Neither benchmark elapsed time nor the whole-simulation cycle total supplies the missing retired-instruction count.

The collected benchmark outputs provide these additional execution checks:

- [XZ output](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-801.xz-801.xz_s/output/801.xz_s.out): all 12 buffer tests report `OK!`, including successful decompression/hash checks and comparisons of uncompressed data. Its [stderr](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-801.xz-801.xz_s/output/801.xz_s.err) contains compression-length diagnostics, with no explicit failed-command marker in the timing record.
- [Cppcheck output](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-827.cppcheck-827.cppcheck_s/output/827.cppcheck_s.out): `Testing Complete`, 4,428 tests, 335 todos, and `Tests failed: 0`. The subsequent sample `hello.c` analysis emits array-bounds diagnostics; these are analyzer output, and the timing record contains no nonzero-exit marker.
- [VPR output](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-834.vpr-834.vpr_s/output/834.vpr_s.out): ends with `VPR succeeded` and `VPR success: 1`.
- [Graph500 output](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-854.graph500-854.graph500_s/output/854.graph500_s.out): all 64 BFS verification runs report success; the APSP phase reports completion for 100 vertices and 62 edges, with shortest-path results written for verification.
- [DIAMOND output](../sims/firesim/deploy/results-workload/2026-10-23--04-55-25-spec-intspeed-test/spec-intspeed-test-838.diamond-838.diamond_s/output/838.diamond_s.out): reports 17,795 pairwise alignments / HSPs and 14,320 aligned queries.

The `*** PASSED ***` UART marker and the manager's successful simulation exit confirm simulator completion and result collection; they are not proof of full SPEC output validation. The checks above are limited to messages produced by the benchmark programs themselves.
