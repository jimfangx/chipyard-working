# Arcilator file guide

`compiler/` builds the hardware model; `native/` supplies the code that runs during simulation.

## Top-level files

| File | Summary |
| --- | --- |
| [.gitignore](.gitignore) | Excludes generated simulator files, compiler caches, output directories, and trace dumps from Git. |
| [Makefile](Makefile) | Builds native or hybrid Arcilator simulators and tracks the inputs and settings needed for incremental compilation. |
| [README.md](README.md) | Provides a one-sentence description of every maintained file in the Arcilator backend. |
| [adapter.py](adapter.py) | Generates the hybrid runtime’s DPI adapter and two-phase state commits from compiler layout metadata. |
| [build-toolchain.sh](build-toolchain.sh) | Launches the reproducible native compiler toolchain setup after the Chipyard environment is loaded. |
| [c_sources.py](c_sources.py) | Adds rules to compile C sources as C in a Verilator-generated makefile. |
| [filelists.py](filelists.py) | Parses HDL source lists and records selected source inputs without invoking an HDL simulator. |
| [frontend.py](frontend.py) | Lowers generated FIRRTL into CIRCT hardware while preserving foreign analog connections. |
| [native.py](native.py) | Generates connections between the compiled hardware model and native runtime bindings from compiler metadata. |
| [native_build.py](native_build.py) | Generates native compilation rules or directly compiles and links the runtime with original C and C++ device drivers. |
| [native_exports.py](native_exports.py) | Reads compiler DPI export contracts and generates scoped C ABI wrappers for exported SystemVerilog routines. |
| [native_hw.py](native_hw.py) | Imports selected foreign RTL into CIRCT hardware and prepares its interfaces for native compilation. |
| [partition.py](partition.py) | Splits generated hardware at foreign-module boundaries and emits the model, boundary wrappers, and connection metadata. |
| [rtl_libraries.py](rtl_libraries.py) | Discovers vendor RTL libraries omitted from selected Chipyard blackbox packages and records their dependencies. |
| [settings.py](settings.py) | Updates a build-settings record only when its effective values change so unchanged builds stay cached. |
| [trace.h](trace.h) | Writes VCD snapshots of Arcilator state using the hybrid simulator’s Verilator simulation time. |

## compiler/

| File | Summary |
| --- | --- |
| [AggregateStores.cpp](compiler/AggregateStores.cpp) | Rewrites large aggregate update chains into stores at their final destination to reduce LLVM compilation work. |
| [ArcToLLVM.cpp](compiler/ArcToLLVM.cpp) | Lowers Arc models, state storage, memory, and simulation-time operations into LLVM dialect operations. |
| [Codegen.cpp](compiler/Codegen.cpp) | Bounds expensive LLVM vectorization and instruction-selection work while preserving the model’s optimization attributes. |
| [CompactStructs.cpp](compiler/CompactStructs.cpp) | Shares large literal LLVM structure types to reduce serialized IR size without changing their layout. |
| [Convergence.cpp](compiler/Convergence.cpp) | Records model effects and identifies outputs that can safely be excluded from native settling comparisons. |
| [FULL_TOOLCHAIN.md](compiler/FULL_TOOLCHAIN.md) | Documents complete private LLVM construction, profile training, source provenance, and output qualification. |
| [FloatMath.cpp](compiler/FloatMath.cpp) | Lowers SystemVerilog real-to-integer rounding into operations accepted by the pinned Arcilator pipeline. |
| [FormatStrings.cpp](compiler/FormatStrings.cpp) | Preserves format-expression trees and lowers them to native formatting and string-buffer calls. |
| [HierarchyFormats.cpp](compiler/HierarchyFormats.cpp) | Preserves and resolves source hierarchy names used by formatting operations across hardware flattening. |
| [IdleClock.cpp](compiler/IdleClock.cpp) | Identifies sampling transitions that the native runtime can process without reevaluating the full model. |
| [LargeArguments.cpp](compiler/LargeArguments.cpp) | Moves large private helper argument lists into shared memory buffers to reduce machine calling-convention overhead. |
| [LargeReturns.cpp](compiler/LargeReturns.cpp) | Moves large private helper return values into caller-owned scratch storage to simplify generated machine code. |
| [LocalMemory.cpp](compiler/LocalMemory.cpp) | Lowers automatic procedural reference storage into invocation-local native stack memory with bounds checks. |
| [LowerArrays.cpp](compiler/LowerArrays.cpp) | Lowers hardware array operations and aggregate function interfaces into LLVM-compatible representations. |
| [Model.cpp](compiler/Model.cpp) | Prepares DPI calls, normalizes arrays, outlines model procedures, and exports allocated state-layout metadata. |
| [NativeArithmetic.cpp](compiler/NativeArithmetic.cpp) | Lowers backend-owned wide-shift calls directly into native arithmetic within the LLVM optimization pipeline. |
| [NativeContexts.cpp](compiler/NativeContexts.cpp) | Resolves DPI imports, tasks, and captured references against their physical SystemVerilog declaration scopes. |
| [NativeHandles.cpp](compiler/NativeHandles.cpp) | Converts SystemVerilog opaque handles into native pointer-width integer storage. |
| [NativeMem2Reg.cpp](compiler/NativeMem2Reg.cpp) | Promotes eligible procedural signal and memory slots into SSA values while preserving assignment timing. |
| [NativePlusArgs.cpp](compiler/NativePlusArgs.cpp) | Lowers SystemVerilog plus-argument tests to the native runtime’s VPI argument interface. |
| [NativeStrings.cpp](compiler/NativeStrings.cpp) | Converts dynamic SystemVerilog strings into immutable string handles owned by the native runtime. |
| [Partition.cpp](compiler/Partition.cpp) | Bounds hardware compilation units while preserving boundary ports and resolving supported combinational feedback. |
| [ProceduralFeedback.cpp](compiler/ProceduralFeedback.cpp) | Exposes procedural combinational feedback loops to the native runtime’s same-cycle settling mechanism. |
| [Properties.cpp](compiler/Properties.cpp) | Converts assertion expressions with proven single-cycle Boolean semantics into ordinary combinational logic. |
| [RTL.cpp](compiler/RTL.cpp) | Prepares imported RTL processes, DPI metadata, reference boundaries, initializers, and timing operations for native lowering. |
| [RemoveI0Types.cpp](compiler/RemoveI0Types.cpp) | Removes zero-width integer values and updates affected operations and function interfaces. |
| [SamplingFreeze.cpp](compiler/SamplingFreeze.cpp) | Prevents sensitized combinational DPI caches from changing while native registers sample their pre-edge inputs. |
| [ScopeFrames.h](compiler/ScopeFrames.h) | Provides helpers for carrying, rebasing, and resolving physical DPI scope frames during compiler transformations. |
| [SharedProcedures.cpp](compiler/SharedProcedures.cpp) | Routes private procedure inputs and results through an invocation-local workspace to reduce repeated ABI traffic. |
| [SignalMemory.cpp](compiler/SignalMemory.cpp) | Lowers procedural references that cannot become SSA registers into bounded native signal-memory storage. |
| [SignalState.cpp](compiler/SignalState.cpp) | Preserves conditional signal writes and declaration initializers through native state and startup lowering. |
| [SignalWrites.cpp](compiler/SignalWrites.cpp) | Splits procedural signal writes into forms consumed by the native signal-state and memory passes. |
| [SplitCodegen.cpp](compiler/SplitCodegen.cpp) | Partitions optimized LLVM definitions into independently compiled units while tracking symbol identity for final linking. |
| [StartupState.cpp](compiler/StartupState.cpp) | Lowers supported startup captures using the matching SDK’s state-lowering pass. |
| [StatePartition.cpp](compiler/StatePartition.cpp) | Plans and materializes model partitions using state dependencies and emits scheduling and partition reports. |
| [StateProperties.cpp](compiler/StateProperties.cpp) | Infers reset and enable properties of Arc state operations to simplify state updates. |
| [TOOLCHAIN.md](compiler/TOOLCHAIN.md) | Documents private LLVM implementation overlays, legacy build recipes, and SDK compatibility requirements. |
| [TemporalProperties.cpp](compiler/TemporalProperties.cpp) | Compiles supported finite temporal assertion sequences into sampled native monitors. |
| [UnionBits.cpp](compiler/UnionBits.cpp) | Lowers packed union operations into their underlying bit representation. |
| [VectorPacking.cpp](compiler/VectorPacking.cpp) | Uses target-supported vector operations for eligible integer packing expressions. |
| [WideArithmetic.cpp](compiler/WideArithmetic.cpp) | Preserves owned wide shifts through Arc optimization and lowers them to native helper calls. |
| [WideArithmetic.h](compiler/WideArithmetic.h) | Declares the compiler helpers that identify owned wide-shift operations and their shift modes. |
| [WideStores.cpp](compiler/WideStores.cpp) | Distributes eligible wide store expressions over incoming control-flow edges while retaining memory ordering. |
| [codegen.py](compiler/codegen.py) | Optimizes LLVM model IR and produces bitcode and machine objects using bounded or stock compilation pipelines. |
| [frontend-implementation.profile-list](compiler/frontend-implementation.profile-list) | Excludes header-defined code from frontend profile instrumentation so training focuses on implementation files. |
| [full_toolchain.py](compiler/full_toolchain.py) | Constructs, profiles, and qualifies complete private LLVM compiler binaries with explicit source and SDK provenance. |
| [llvm.py](compiler/llvm.py) | Rewrites generated wide arithmetic calls and private helper interfaces into native C ABI forms. |
| [memories.py](compiler/memories.py) | Replaces eligible large canonical FIRRTL memories with native sparse-memory bindings. |
| [model.py](compiler/model.py) | Runs Arc model compilation with array normalization, optional outlining, native lowering, and layout export. |
| [native_combin.py](compiler/native_combin.py) | Keeps supported scalar glue logic inside the compiled hardware model while retaining real latch state. |
| [partition.py](compiler/partition.py) | Builds compiler plugins and runs bounded hardware partitioning with the matching CIRCT or LLVM SDK. |
| [sdk_overlay.py](compiler/sdk_overlay.py) | Builds private LLVM drivers by replacing selected implementation objects in matching SDK archives. |
| [text_spans.py](compiler/text_spans.py) | Provides byte-span and sparse-text helpers that avoid rewriting unchanged portions of large hardware files. |
| [thin_codegen.py](compiler/thin_codegen.py) | Compiles state partitions in parallel using the matching SDK’s ThinLTO summaries and import pipeline. |
| [toolchain-configs.json](compiler/toolchain-configs.json) | Defines hardware configurations and per-model settings used for compiler profile training and held-out qualification. |
| [toolchain.py](compiler/toolchain.py) | Orchestrates native compiler setup, prerequisite checks, resumable builds, qualification, and environment activation. |
| [toolchain_cases.py](compiler/toolchain_cases.py) | Generates fresh SDK reference models and manifests used by compiler training and output qualification. |
| [toolchain_source.py](compiler/toolchain_source.py) | Downloads pinned sources, verifies their identities, applies patches, and prepares the SDK and optional driver. |

## compiler/arcilator-driver/

| File | Summary |
| --- | --- |
| [CMakeLists.txt](compiler/arcilator-driver/CMakeLists.txt) | Builds a private Arcilator driver from verified source against the pinned CIRCT SDK. |
| [Provenance.cmake](compiler/arcilator-driver/Provenance.cmake) | Records driver source, SDK, and build-configuration identities when CMake configures the driver. |
| [RecordBuild.cmake](compiler/arcilator-driver/RecordBuild.cmake) | Records the completed driver binary’s identity after a successful link. |

## compiler/circt-patches/

| File | Summary |
| --- | --- |
| [LICENSE.txt](compiler/circt-patches/LICENSE.txt) | Contains the upstream license covering the included CIRCT driver patch. |
| [emit-bytecode.patch](compiler/circt-patches/emit-bytecode.patch) | Adds optional MLIR bytecode output to the pinned Arcilator driver. |
| [manifest.json](compiler/circt-patches/manifest.json) | Records the pinned CIRCT revision and hashes required to verify the driver source and bytecode patch. |

## compiler/llvm-patches/

| File | Summary |
| --- | --- |
| [0001-codegen-skip-repeated-schedule-dag-visits.patch](compiler/llvm-patches/0001-codegen-skip-repeated-schedule-dag-visits.patch) | Avoids revisiting already-examined nodes during scheduling DAG traversal. |
| [0002-codegen-skip-use-scan-without-subregister-tracking.patch](compiler/llvm-patches/0002-codegen-skip-use-scan-without-subregister-tracking.patch) | Skips register-use scans that cannot contribute subranges when subregister liveness is disabled. |
| [0003-codegen-skip-slot-prefix-before-live-range.patch](compiler/llvm-patches/0003-codegen-skip-slot-prefix-before-live-range.patch) | Skips slot-index prefixes that precede the first segment of a live range. |
| [0004-analysis-index-lvi-value-block-membership.patch](compiler/llvm-patches/0004-analysis-index-lvi-value-block-membership.patch) | Indexes value-to-block cache membership to reduce LazyValueInfo invalidation scans. |
| [0005-vectorize-group-alias-cache-by-source.patch](compiler/llvm-patches/0005-vectorize-group-alias-cache-by-source.patch) | Groups cached alias queries by source to reduce repeated vectorizer alias-analysis work. |
| [0006-codegen-collect-physical-register-use-suffix.patch](compiler/llvm-patches/0006-codegen-collect-physical-register-use-suffix.patch) | Collects the relevant physical-register use suffix without repeatedly scanning unrelated operands. |
| [0007-codegen-search-scheduling-reachability-bidirectionally.patch](compiler/llvm-patches/0007-codegen-search-scheduling-reachability-bidirectionally.patch) | Uses bidirectional scheduling-graph searches for Boolean reachability queries. |
| [0008-analysis-short-circuit-edge-dominance.patch](compiler/llvm-patches/0008-analysis-short-circuit-edge-dominance.patch) | Short-circuits edge-dominance queries using immediate-dominator relationships. |
| [0009-codegen-parallelize-initial-scalar-live-ranges.patch](compiler/llvm-patches/0009-codegen-parallelize-initial-scalar-live-ranges.patch) | Parallelizes independent initial scalar live-range calculations in the LLVM backend. |
| [0010-build-skip-hidden-IR-profile-alias-exports.patch](compiler/llvm-patches/0010-build-skip-hidden-IR-profile-alias-exports.patch) | Excludes hidden IR-profile alias symbols from generated LLVM shared-library export lists. |
| [0011-analysis-prune-memoryssa-traversal-frames.patch](compiler/llvm-patches/0011-analysis-prune-memoryssa-traversal-frames.patch) | Reduces MemorySSA traversal bookkeeping by retaining stack frames only for pending sibling work. |
| [0012-transforms-skip-impossible-dominated-use-walks.patch](compiler/llvm-patches/0012-transforms-skip-impossible-dominated-use-walks.patch) | Avoids dominated-use searches that cannot produce valid non-PHI matches. |
| [0013-codegen-index-source-order-ready-prefix.patch](compiler/llvm-patches/0013-codegen-index-source-order-ready-prefix.patch) | Indexes source-order scheduling candidates to avoid repeated scans of the ready-queue prefix. |
| [LICENSE.txt](compiler/llvm-patches/LICENSE.txt) | Contains the upstream license covering the included LLVM patches. |
| [manifest.json](compiler/llvm-patches/manifest.json) | Records LLVM source pins, patch order, expected hashes, and compiler construction provenance. |

## compiler/verilog/

| File | Summary |
| --- | --- |
| [CMakeLists.txt](compiler/verilog/CMakeLists.txt) | Builds the patched SystemVerilog importer and frontend executable against installed CIRCT and Slang libraries. |
| [build.py](compiler/verilog/build.py) | Fetches verified frontend sources, applies compatibility patches, and builds a cached SystemVerilog importer. |
| [canonicalization-order.patch](compiler/verilog/canonicalization-order.patch) | Processes uses before definitions during frontend canonicalization to avoid pathological rewrites in unreachable loops. |
| [declaration-initializers.patch](compiler/verilog/declaration-initializers.patch) | Retains declaration-initializer provenance when canonicalization removes the original variable operation. |
| [delay-precision.patch](compiler/verilog/delay-precision.patch) | Rounds fractional delays once at the declaration scope’s lexical time precision. |
| [dpi-abi.patch](compiler/verilog/dpi-abi.patch) | Preserves original SystemVerilog argument types and C ABI metadata across DPI import lowering. |
| [dpi-context-scopes.patch](compiler/verilog/dpi-context-scopes.patch) | Retains physical DPI declaration scopes through hierarchical calls and function inlining. |
| [dpi-exports.patch](compiler/verilog/dpi-exports.patch) | Preserves exported DPI signatures, instance scopes, and captured storage through optimization. |
| [dpi-open-arrays.patch](compiler/verilog/dpi-open-arrays.patch) | Preserves actual array shape and element representation when importing DPI open-array calls. |
| [dpi-source-hierarchy.patch](compiler/verilog/dpi-source-hierarchy.patch) | Records original source hierarchy metadata for DPI declarations and calls. |
| [global-identity.patch](compiler/verilog/global-identity.patch) | Preserves qualified identities of global and static storage across independently imported module variants. |
| [hierarchical-call-captures.patch](compiler/verilog/hierarchical-call-captures.patch) | Routes nonlocal storage captured by hierarchical subroutine calls across module boundaries. |
| [hierarchical-queries.patch](compiler/verilog/hierarchical-queries.patch) | Treats fixed-size hierarchical bit-width queries as type queries rather than live signal references. |
| [hierarchy-formats.patch](compiler/verilog/hierarchy-formats.patch) | Preserves source hierarchy formatting and observable system-task effects during frontend lowering. |
| [inertial-delays.patch](compiler/verilog/inertial-delays.patch) | Retains inertial continuous-assignment semantics before generic signal canonicalization. |
| [interface-arrays.patch](compiler/verilog/interface-arrays.patch) | Flattens interface arrays into directed ports while preserving element mapping and member access. |
| [nonoverlap.patch](compiler/verilog/nonoverlap.patch) | Corrects the placement of the extra cycle in nonoverlapping implication and followed-by assertions. |
| [packed-case.patch](compiler/verilog/packed-case.patch) | Compares packed aggregate case operands using their underlying bit representation. |
| [packed-ref-slices.patch](compiler/verilog/packed-ref-slices.patch) | Preserves packed aggregate bit and range references for native reference-memory lowering. |
| [parenthesized-delays.patch](compiler/verilog/parenthesized-delays.patch) | Accepts single-expression parenthesized delay controls in imported SystemVerilog. |
| [port-connections.patch](compiler/verilog/port-connections.patch) | Preserves declared source signedness when extending output port connections. |
| [port-initializers.patch](compiler/verilog/port-initializers.patch) | Preserves initializers attached to output variable port declarations. |
| [realtime-f64.patch](compiler/verilog/realtime-f64.patch) | Represents SystemVerilog realtime values as floating-point numbers in the declaration scope’s time unit. |
| [rounded-real-casts.patch](compiler/verilog/rounded-real-casts.patch) | Rounds real-to-integer conversions to nearest with ties away from zero before integer conversion. |
| [scope-lookups.patch](compiler/verilog/scope-lookups.patch) | Resolves subroutine lookup provenance in the original lexical scope. |
| [sources.json](compiler/verilog/sources.json) | Pins the frontend’s CIRCT and Slang source revisions and expected source hashes. |
| [static-formals.patch](compiler/verilog/static-formals.patch) | Preserves persistent formal storage while keeping default arguments evaluated by the caller. |
| [static-storage.patch](compiler/verilog/static-storage.patch) | Allocates static procedural locals in their enclosing module instance or package. |
| [task-export-abi.patch](compiler/verilog/task-export-abi.patch) | Preserves exported coroutine task metadata needed to retain the native task ABI. |
| [timing.patch](compiler/verilog/timing.patch) | Preserves fractional time values while scaling SystemVerilog timing expressions into femtoseconds. |
| [unary-increment.patch](compiler/verilog/unary-increment.patch) | Writes the updated value back for one-bit pre-increment, post-increment, and decrement operations. |
| [unit-static.patch](compiler/verilog/unit-static.patch) | Declares compilation-unit static storage before lowering top-level subroutines. |
| [unknown-comparisons.patch](compiler/verilog/unknown-comparisons.patch) | Resolves literal X and Z masks before four-state comparisons are lowered to native two-state values. |
| [unpacked-reshape.patch](compiler/verilog/unpacked-reshape.patch) | Reshapes compatible packed elements in fixed unpacked-array assignments while preserving array positions. |
| [vpi-source-metadata.patch](compiler/verilog/vpi-source-metadata.patch) | Records elaborated source metadata needed for native VPI hierarchy and timing queries. |

## native/

| File | Summary |
| --- | --- |
| [additional.cpp](native/additional.cpp) | Binds legacy debug transport, Dromajo, memory trace, logging, and lane-driver models to their original device code. |
| [analog.cpp](native/analog.cpp) | Implements native bindings for analog constants, digital GPIO cells, and SPI flash models. |
| [analog_nets.cpp](native/analog_nets.cpp) | Resolves native analog-net connections and propagates their driven values. |
| [bindings.cpp](native/bindings.cpp) | Implements core native models for state, sparse memory, delays, latches, clocks, and basic simulation peripherals. |
| [compat.cpp](native/compat.cpp) | Implements DPI scope management, caller data, VPI argument queries, and compatibility error reporting. |
| [compat.h](native/compat.h) | Declares native DPI scope, context, and open-array compatibility data structures. |
| [contexts.cpp](native/contexts.cpp) | Registers and connects physical SystemVerilog scope roots and context bindings for DPI calls. |
| [control.cpp](native/control.cpp) | Exposes runtime print and stop controls, physical time, and scoped export lookups to compiled DPI code. |
| [cosim.cpp](native/cosim.cpp) | Connects Spike cosimulation, DebugROB, and traffic-evaluation bindings to their original drivers. |
| [evaluation.cpp](native/evaluation.cpp) | Tracks the active native sampling phase for compiled model and DPI callbacks. |
| [evaluation.h](native/evaluation.h) | Declares the sampling-phase guard and query interface used to preserve pre-edge evaluation ordering. |
| [exports.cpp](native/exports.cpp) | Registers scoped DPI exports and dispatches calls using their captured storage and argument layouts. |
| [files.cpp](native/files.cpp) | Implements native file handles, output channels, stream ownership, and formatted file writes. |
| [format.cpp](native/format.cpp) | Supplies dynamic real-number formatting missing from the pinned CIRCT Arc runtime. |
| [format_strings.cpp](native/format_strings.cpp) | Builds and renders native formatting buffers used by lowered SystemVerilog format expressions. |
| [models.def](native/models.def) | Lists supported hardware model names and maps them to native binding classes. |
| [open_arrays.cpp](native/open_arrays.cpp) | Implements DPI open-array shape queries and scalar or vector element access. |
| [peripherals.cpp](native/peripherals.cpp) | Connects debug transport, block devices, networking, branch predictors, BTBs, and TraceROM models to original drivers. |
| [readmem.cpp](native/readmem.cpp) | Parses SystemVerilog memory initialization files and loads their values into native model storage. |
| [runtime.cpp](native/runtime.cpp) | Runs native simulation scheduling, settling, timed events, signal updates, and binding dispatch. |
| [runtime.h](native/runtime.h) | Declares model signals, parameters, binding interfaces, callback contracts, and the native runtime state. |
| [scope_guard.h](native/scope_guard.h) | Restores the previous DPI context automatically when a scoped native call returns. |
| [spike.cpp](native/spike.cpp) | Implements the native SpikeBlackBox processor binding using the original Spike driver. |
| [strings.cpp](native/strings.cpp) | Manages immutable native string handles and copies returned DPI string buffers into owned storage. |
| [trace.h](native/trace.h) | Writes native model signals and timestamped state changes to VCD waveform files. |
| [vpi_lifecycle.cpp](native/vpi_lifecycle.cpp) | Registers and dispatches VPI startup, simulation-start, and simulation-end callbacks for native models. |
| [vpi_lifecycle.h](native/vpi_lifecycle.h) | Declares the optional VPI lifecycle hooks used by the native runtime. |
| [wide.cpp](native/wide.cpp) | Implements bounded arbitrary-width shifts and other native wide-value helper operations. |

## native/include/

| File | Summary |
| --- | --- |
| [svdpi.h](native/include/svdpi.h) | Declares the scalar, packed-vector, scope, and open-array SystemVerilog DPI interface used by native drivers. |
| [vpi_user.h](native/include/vpi_user.h) | Declares the native VPI argument, error, and simulation-lifecycle callback interfaces. |
