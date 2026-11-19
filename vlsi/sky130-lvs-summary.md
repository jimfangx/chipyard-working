# Sky130RocketConfig LVS closure summary

Status: 2026-11-08. Design: `chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop`.

The latest normal Hammer top-level comparison, started at 02:48:53, reports
**MATCH: 166 matched cell types, six expanded, zero not run, zero mismatching
types, zero parameter/subtype mismatches, zero blackboxed types, and empty ERC**.
Its inputs are the original project's `par-rundir` exports.
The earlier repaired diagnostic run matched 165 cell types. Extraction warnings
remain; physical DRC is a separate outstanding check.

The later DualShuttle run uses different clamp variants. Its additional
PADISO wrapper discovery change and pending qualification are documented in
[the generalization notes](sky130-lvs-generalization.md#plain-clamp-padiso-hierarchy).
The Rocket MATCH above does not establish a DualShuttle MATCH. SRAM-channel
PG opens in that design remain deferred.

The large original error count came from several repeated extraction, source
representation and hierarchy problems, plus actual supply-connection problems.
It was not a wholesale failure to import the IO/SRAM libraries: the source audit
found 24 input files, 1,726 subcircuits and zero unresolved X-instance masters.
Cadence standard-cell types already matched before most IO/SRAM fixes.

The [independent verification guide](sky130-lvs-verification.md) gives an
inspection procedure for **every change below**: original and generated files,
source/deck locations, GDS layers and measurements, expected discrepancies,
before/after evidence, and the implementation/collateral files changed. Each
table row links directly to its procedure. Original external collateral is
distinguished from generated overlays and actual chip-level physical repairs.

## Scope and implementation

Original external PDK and simulation libraries were left unchanged. Corrections
live under `vlsi/` and produce a cached Pegasus deck, generated LVS CDL, source
overlays and physical-design exports. The active raw deck is
`/scratch/jfx/sky130_release_0.1.0/Sky130_LVS/sky130.lvs.v0.0_1.1.pvl`, as selected
by `example-sky130.yml`; the Cadence standard cells come from `sky130_scl_9T_0.1.2`.
IO/SRAM/PoR circuitry uses openPDKs primitives.

The main implementation files are:

- [lvs_netlists.py](hammer/hammer/technology/sky130/lvs_netlists.py): guarded basic
  PVL repairs and source-library utilities.
- [lvs_translate.py](hammer/hammer/technology/sky130/lvs_translate.py): geometric
  LVS source generation from the mixed simulation/CDL libraries.
- [lvs_compat.py](hammer/hammer/technology/sky130/lvs_compat.py): the shared,
  explicitly enabled extraction/source/comparison profile. Diagnostic scripts
  import the same functions used by the normal technology hooks.
- [io_collateral.py](hammer/hammer/technology/sky130/io_collateral.py): checked
  clamped2 CDL/GDS repairs applied to cached technology libraries for P&R
  and verification. See the [integration and pending CAD checks](sky130-lvs-generalization.md#production-integration-of-the-clamped2-repairs).
- [Sky130 technology hooks](hammer/hammer/technology/sky130/__init__.py),
  [hammer-driver](hammer-driver), [sky130.cpf](sky130.cpf), and
  [example-sky130.yml](example-sky130.yml): normal-flow integration.

`technology.sky130.lvs_mixed_library_compatibility: true` is enabled in the project
YAML. Its technology default is false. The cached deck and generated source
manifests record the enabled policies, source hashes and transformations.

## PDK extraction corrections

| Change | Reason and evidence |
| --- | --- |
| Restore isolated-pwell bulk coverage while preserving the deep-nwell guard-ring gap. | The original bulk derivation omitted the SRAM interior. A small-macro audit found 11,480 NMOS gate regions outside the bulk layer and 991 malformed-device entries. The corrected derivation removed both defects without joining isolated and global body domains. Implemented by `patch_pegasus_pwell`. [Verify A1](sky130-lvs-verification.md#a1). |
| Add generic marked-poly resistor extraction separately from RPM/URPM precision resistors. | The deck removed marked poly from the conductor but declared only precision-poly devices. `tk_tie_r_out_esd` consequently had one resistor in source and none in layout. Adding `res_generic_po` with geometric properties made the isolated cell match. **This was a deck repair, not an edit to the cell GDS or SPICE.** Implemented by `patch_pegasus_generic_poly`; reproducible diff: [generic-poly patch](sky130-lvs-generic-poly.patch). [Verify A2](sky130-lvs-verification.md#a2). |
| Recognize metal datatype-15 SHORT markers and attach metal resistor properties. | IO layouts use datatype 15 as well as datatype 13. Ignoring those markers omitted devices and left paths conductive; the original device declarations also lacked L/W properties. `com_res_weak` subsequently extracted the expected eight poly and twelve metal resistors. Real resistors and annotated SHORT surrogates receive separate comparison treatment below. [Verify A3](sky130-lvs-verification.md#a3). |
| Compute bent poly/diffusion resistor length using the inside-bend convention. | The U-shaped poly body gave `A/W = 50.8 um` against a 50 um source length. The geometric correction `L = A/W - BENDS*W/2` accounts for the two bends without changing source dimensions. Applied to generic poly and the diffusion meander. [Verify A4](sky130-lvs-verification.md#a4). |
| Require actual n+ diffusion for PW diode recognition. | Marker border extending outside the intended well created a false PW diode. Requiring interaction with `nsdm AND diff` retains valid diode recognition polygons while rejecting marker-only regions; NW diode rules remain intact. Implemented by `patch_pegasus_pw_diode`. [Verify A5](sky130-lvs-verification.md#a5). |
| Remove diffusion-resistor bodies from the HV source/drain conductor and attach diffusion resistor properties. | The HV conductor otherwise bypassed the marked XRES resistor, producing a false short. W/L properties make the extracted diffusion resistor dimensions comparable rather than merely recognizing its topology. [Verify A6](sky130-lvs-verification.md#a6). |
| Use gate-cut source/drain regions for diffusion-resistor terminals. | Full `ndiff`/`pdiff` terminal selections crossed MOS gates in the PoR Schmitt buffer. The old terminal shapes overlapped 0.795 um2 of N-gate and 1.5 um2 of P-gate area; the corrected selections overlap zero. This removed an extraction-induced supply short. See [terminal-selection patch](sky130-lvs-por-diffusion-terminals-candidate.patch). [Verify A7](sky130-lvs-verification.md#a7). |
| Add second-layer MIM extraction with a separate `cap2m` upper electrode. | The deck mapped `cap2m` but had no corresponding capacitor device. Simply using intersecting metal5 also selected a lower-electrode return strip and created an extra terminal. The final rule connects the upper electrode through via4 inside `cap2m`, retaining ordinary M4/M5 connections outside it. Both PoR 30 x 30 um capacitors then matched. See [MIM2 patch](sky130-lvs-por-mim2-candidate.patch). [Verify A8](sky130-lvs-verification.md#a8). |
| Size rectangular SRAM active-edge gates from their single source/drain-facing edge. | The stock calculation assumed two edges, giving half-width/twice-length for clipped edge gates. The new partition requires one source/drain edge and three active-boundary edges, then uses full contact perimeter for W and area/W for L; ordinary gates retain built-in sizing. It recovers PFET L/W = 0.025/0.14 um and NFET 0.14/0.14 um. Independent geometry audits covered all four SRAM macro files and selected zero of 2,008 relevant Cadence standard-cell gates. No source resizing or tolerance relaxation was used. See [SRAM edge-sizing patch](sky130-lvs-sram-edge-sizing-candidate.patch). [Verify A9](sky130-lvs-verification.md#a9). |

These transformations are composed by `build_compatibility_deck`. Historical
`*-candidate.patch` files preserve individual experiments; the shared Python
implementation defines the final combined profile.

## Source collateral, hierarchy and comparison policies

| Change | Reason and scope |
| --- | --- |
| Generate a geometric Pegasus CDL view rather than importing ngspice model implementations directly. | OpenPDKs primitives use wrapper subcircuits, simulator model names, parameter expressions and simulation-only resistor/capacitor networks. The translator maps recognized MOS/R/C/diode calls to extracted device names, handles continuations/includes and parameter scope, normalizes units, and preserves pin order, bulk terminals and connections. Native Cadence CDL is not rescaled. SRAM per-finger W is retained with electrical multiplicity `m*nf`; IO statistical `mult` and MIM statistical `mf` do not become electrical multiplicity. Unknown primitives and conflicting definitions fail explicitly. [Verify B1](sky130-lvs-verification.md#b1). |
| Preserve the custom level-shifter source while importing the rest of the HVL library. | The modified `sky130_fd_sc_hvl__lsbufhv2lv_1` already has custom GDS/source collateral. Loading the entire stock HVL library duplicates that definition; removing the whole library loses other cells needed by PoR. A generated copy removes only the overridden cell. Managed imports are deduplicated. [Verify B2](sky130-lvs-verification.md#b2). |
| Expand selected IO hierarchy boundaries into their parent comparison. | Extracted devices crossed AMUX, ESD and pad-wrapper boundaries. One example had 31 reduced native FETs missing from a child and the same 31 extra in its wrapper. Eleven selected IO boundaries are expanded; their complete circuitry remains compared. No virtual supply joins are used in the assembled-chip run. [Verify B3](sky130-lvs-verification.md#b3). |
| Expand ambiguous SRAM helper names while retaining all four macro roots. | Independently generated SRAMs reuse names such as `tristate_inv` and `column_mos` for different device sizes. Source aggregation and GDS merging assign different suffixes, causing false same-name comparisons. Recursive fingerprints verified that each aggregate macro circuit agrees with its individual source. Expanding 299 helper names from 55 ambiguous families compares their devices in the enclosing circuit; it does not blackbox SRAMs or change dimensions. [Verify B4](sky130-lvs-verification.md#b4). |
| Treat annotated M1-M4 SHORT surrogates separately from real resistors. | Original IO comments identify 28 calls in 13 definitions as former SHORTs, despite fixed nominal source W/L. Actual marker widths vary. Only calls with matching annotation names and terminals are retyped as `res_io_short_m*`; topology, subtype and count remain checked, while nominal W/L are omitted for those surrogates. Real M1-M4 resistor dimensions remain checked at zero tolerance. M5 is handled separately because real M5 resistors also use datatype 15. [Verify B5](sky130-lvs-verification.md#b5). |
| Model the four PADISO M3 annuli as parallel strips with a dedicated subtype. | A single rectangular-resistor formula does not represent the annular terminal geometry. Four extracted strips per side reduce to the intended equivalent resistance. Source nodes and dimensions are unchanged; eight RIL/RIR calls receive the dedicated subtype. Normalized length is checked at zero tolerance; equivalent width has an explicit 5% bound covering 0.168-3.767% residuals measured in the four original pad variants. This is an approximation, not a vendor-qualified corner-field solution. [Verify B6](sky130-lvs-verification.md#b6). |
| Preserve ESD MOS subtypes and use explicit ESD tolerances. | Devices marked by `areaid.ed` need separate recognition/comparison from ordinary HV MOS. ESD-only W/L bounds are 7%/1%, following the investigated openPDKs comparison convention. Ordinary MOS remain at zero tolerance. M5 resistor W/L remain at 1%. [Verify B7](sky130-lvs-verification.md#b7). |
| Retain narrow placeholder and physical-only policies. | Only the verified empty two-pin IO source placeholders `com_pad` and `condiode` are filtered on the source side. Layout `FILL_DECAP8/16` are excluded consistently with the source physical-only policy, which the hook checks. The final control also preserves M1 self-loop/dangling-resistor reduction rules. Functional standard cells, SRAMs and PoR remain compared. [Verify B8](sky130-lvs-verification.md#b8). |
| Restore the PoR Schmitt resistor's original source precision. | Custom `simple_por.spice` rounded one X4 length from 1.355 to 1.36 um. Original SkyWater SPICE/CDL and openPDKs sources specify 1.355 um; polygon comparison confirmed identical Schmitt geometry. A hash-guarded generated overlay corrects only that value. The external source is unchanged. See [source-precision patch](sky130-lvs-por-source-precision.patch). [Verify B9](sky130-lvs-verification.md#b9). |

The final MATCH therefore means agreement under these documented compatibility
policies. It does not mean every original foundry rule was used unchanged or
that nominal SHORT dimensions and PADISO geometry received unrestricted strict
comparison. Ordinary MOS, generic poly and real M1-M4 dimension checks are strict.

## Mainline flow and actual physical repairs

| Change | Reason and implementation |
| --- | --- |
| Use the configured PoR GDS/SPICE pair. | The driver previously discarded the configured GDS and inserted another project's `simple_por_drc_lvs.gds`. That alternate removed a resistor body: 27 layout resistors versus 28 source devices. The driver now retains the configured CARAVEL `simple_por.gds`. The special PoR GDS override and its setting have been removed; all GDS inputs come from the configured libraries. [Verify C1](sky130-lvs-verification.md#c1). |
| Assign unused NC pads to the IO CPF domain. | The old selector omitted `nc_*/iocell`, leaving 243 expected supply connections absent from the source export across 27 pads. `sky130.cpf` now includes them. Re-export validation confirmed all NC supplies and unchanged logical/bus connections for 84,944 retained instances. This was a real power-intent/export problem. [Verify C2](sky130-lvs-verification.md#c2). |
| Add the missing quiet-VDDIO rail tie. | CPF alone could not connect physically separate VDDIO_Q and VDDIO conductors in the custom north filler. [sky130-quiet-vddio.tcl](sky130-quiet-vddio.tcl) adds a guarded met4 rectangle at (213.5,5055.535)-(214.5,5059.035) um for the qualified filler geometry. The driver runs it before final exports. This repairs an actual physical open. [Verify C3](sky130-lvs-verification.md#c3). |
| Add the missing PoR VDDIO via3. | The existing met3 trunk crossed the south filler met4 VDDIO rail without a via. [sky130-por-vddio.tcl](sky130-por-vddio.tcl) inserts a fixed 4x1 array of 0.2 um cuts at (3277.2,177.89) um, with checked enclosure/overlap. It guards masters, orientations, dimensions and net identity, and is idempotent. Closing this actual P&R open produced the final full-chip MATCH. The hook is enabled with the mixed-library profile. [Verify C4](sky130-lvs-verification.md#c4). |
| Align exported physical-only cells with the selected technology. | The old netlist override hardcoded open-source HD cell names. It now uses Hammer's physical-only cell list, including Cadence fillers/decaps/ANTENNA, plus the intended IO filler/corner exclusions. [Verify C5](sky130-lvs-verification.md#c5). |
| Select the actual verification GDS and reject missing masters. | DRC/LVS hooks select `<top>_drc_lvs.gds` before control generation and fail if absent. Missing Verilog masters are no longer silently ignored. Block runs with IO disabled retain their ordinary layout selection. [Verify C6](sky130-lvs-verification.md#c6). |
| Generate and record repairs through normal technology hooks. | `setup_pegasus_lvs_deck` rebuilds the cache from the selected raw deck. The schematic hook produces CDL, source overlay and manifest; explicit control rules handle hierarchy and physical-only devices. Input/source hashes and guards prevent silent application to unknown revisions. [Verify C7](sky130-lvs-verification.md#c7). |

The external custom PoR, M1-access level shifter and quiet-supply filler were
pre-existing project collateral, not newly authored library replacements in this
investigation. No new timing characterization or Liberate run was needed.

For the saved-DB diagnostic export only, `read_db_file_check` was disabled around
restore and restored immediately afterward because SRAM Liberty files had changed.
Those scripts performed no placement/routing optimization and did not save the
original DB. The initial via checker also needed a parser correction for DEF's
optional `SHAPE IOWIRE` clause; that checker failure did not mean via insertion
had failed. Neither workaround is a new blanket production setting.
Verification and edited-file details: [DB restore](sky130-lvs-verification.md#d1)
and [DEF checker](sky130-lvs-verification.md#d2).

## Validation and remaining work

| Evidence | Result |
| --- | --- |
| Repaired full-chip report: `build/sky130-por-vddio-repair/full-chip/ChipTop.lvs_results.cls`, start 01:13:50 on Nov 8 | MATCH; 165 matched / six expanded / zero failures; empty ERC. SHA256 `541c052850a287d0d5dc286b024a34982c8aabcaa0b87c14778e59b9355fcff3`. |
| Historical normal Hammer integration, start 01:50:02 on Nov 8 | MATCH; 165 matched / six expanded / zero failures, using integrated hooks and repaired diagnostic exports. Report SHA256 `42b4c2de17d904b7c6ca7b8d9538195d6ffffebf07f63755775fdc6496993609`; this report has since been overwritten by the mainline run below. |
| Current mainline report: `build/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop/lvs-rundir/ChipTop.lvs_results.cls`, start 02:48:53 on Nov 8 | MATCH; 166 matched / six expanded / zero failures or blackboxed types; empty ERC. Uses the original project's `par-rundir` GDS/Verilog. SHA256 `491a9ef525526ac79f2133c7f5257b342da33d28daa3816683eaae7ce7dc4b61`. |
| Historical integration input-equivalence check | All 1,726 source definitions and 310 hierarchy-expansion names agree with the diagnostic; no executable source statements outside the definitions. Deck is byte-identical after its provenance header: SHA256 `30dbb5e48ea06d590a14bc009ff215abcabc3fb01e568702e761c44015a08c34`. |
| Focused regressions | 43 passed, covering translation, guarded patches, hierarchy, physical hooks, export checks and stale-config override generation. |

The current report names
`build/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop/par-rundir/{ChipTop_drc_lvs.gds,ChipTop.lvs.v}`;
the diagnostic-export override is no longer its input. Physical DRC of the
quiet-rail tie, PoR via and placement remains pending. The physical
hooks deliberately stop if the qualified geometry changes and their guards fail.
Extraction warnings and existing clamp pad-terminal/export-model conventions
remain review items; a blanket tie of clamp `*_PAD` pins would bypass their
explicit source resistors and was not applied.

## Refreshing the mainline run

The subsequent [generalization changes](sky130-lvs-generalization.md) replace
the fixed SRAM audit list with discovery from the current netlist, derive quiet
ties from the placed pins on every qualifying filler, and source repair Tcl at
runtime. The example CSVs now identify the PoR tap as `IO_FILLER_POR_TAP`.
These changes have generation/unit-test coverage; they have **not** established
a new DualShuttle LVS MATCH. The results above describe the earlier Rocket run.

`redo-par` runs P&R only. `redo-syn-to-par` is a configuration conversion using
existing synthesis results, not a synthesis run. Ordinary `make par` follows
dependencies and can rerun synthesis if its inputs are out of date; it also need
not rerun P&R if make considers the old outputs current.

In the CAD shell, run these commands sequentially, continuing only after success:

```bash
cd /scratch/jfx/cy-upstream-release-sky130/vlsi
SKY130_PROJECT="$PWD/build/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop"

make -f "$SKY130_PROJECT/hammer.d" redo-syn-to-par \
  HAMMER_EXTRA_ARGS="-p $PWD/example-sky130.yml"
make -f "$SKY130_PROJECT/hammer.d" redo-par
make -f "$SKY130_PROJECT/hammer.d" redo-par-to-lvs
make -f "$SKY130_PROJECT/hammer.d" redo-lvs
make -f "$SKY130_PROJECT/hammer.d" redo-par-to-drc
make -f "$SKY130_PROJECT/hammer.d" redo-drc
```

This replaces the current P&R results and regenerates LVS/DRC inputs from those
new results. The current report establishes LVS agreement on the named exports;
its header alone does not establish that all P&R stages were rerun. The YAML
reload is needed when saved snapshots predate
the enabled profile. Subsequent snapshots carry it forward. The temporary
repaired-export overlay was used to validate integration against the known
passing design; the sequence above uses new mainline P&R exports.

Repository changes span the parent repository and the `vlsi/hammer` submodule.
Both must be included when landing
the work. The detailed experiment history is in
[sky130-io-lvs-audit.md](sky130-io-lvs-audit.md); older candidate statuses there are
historical and superseded by the final results above.
