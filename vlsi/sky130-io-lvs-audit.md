# IO LVS audit, 2026-10-26

## Normal top-level Hammer LVS MATCH confirmed (2026-11-08)

The original project's `lvs-rundir/ChipTop.lvs_results.cls`, starting
01:50:02, now reports **MATCH**: 165 matched types, six expanded, zero not
run, zero mismatching types, zero parameter/subtype mismatches and empty
ERC. Extraction warnings remain. Report SHA256 is
`42b4c2de17d904b7c6ca7b8d9538195d6ffffebf07f63755775fdc6496993609`.
The generated runner's result checker also recorded this MATCH in
`sky130-hammer-lvs-integration/top-level/equivalence.json`.

This validates the integrated normal Hammer deck/source/control hooks
using the repaired physical exports, rather than an independently patched
diagnostic control. The layout/Verilog still come from
`sky130-por-vddio-repair/chip-export`; replacing the historical outputs
under the original `par-rundir` requires fresh mainline P&R and regenerated
configuration snapshots. Physical DRC remains pending.

The final changes and reasoning, exact comparison exceptions, evidence and
mainline refresh commands are collected in
[sky130-lvs-summary.md](sky130-lvs-summary.md). `redo-par` itself does not
rerun synthesis; the preceding `redo-syn-to-par` only converts the saved
synthesis output configuration with the updated project YAML.

## Repeated normal top-level mismatch: stale snapshot confirmed (2026-11-08)

The top-level run starting 01:42:39 again reports 154 matched / 14
expanded / 21 mismatching types, with 20 parameter and four subtype-error
types. Its `lvs-rundir/config_db_tmp.json` explicitly has
`technology.sky130.lvs_mixed_library_compatibility: false`. The saved
`lvs-input.json` has no override for that setting. Both layout and Verilog
still refer to the old `par-rundir` exports. The control contains only the
five earlier IO hierarchy expansions, with the older strict generic
resistor and unpartitioned ESD source handling. These are the same known
failures, not evidence that the qualified repairs regressed.

The generated `hammer.d` `redo-lvs` recipe loads only `lvs-input.json`
plus `HAMMER_EXTRA_ARGS`; it does not reload `example-sky130.yml`.
Consequently, editing the example configuration does not enable the new
profile in an old snapshot. Enabling the profile alone would also leave
the old physical exports, including the missing PoR supply via.

Prepared an explicit wrapper around that existing make target:

```bash
bash "$PWD/vlsi/build/sky130-hammer-lvs-integration/run-top-level.sh"
```

It passes the qualified `inputs.json` through `HAMMER_EXTRA_ARGS`, enabling
the profile and selecting both repaired physical exports. The object/run
directory is the original project, so the report is written to the exact
`lvs-rundir/ChipTop.lvs_results.cls` path the user is inspecting. The runner
checks for a fresh report and requires MATCH. It does not modify the saved
P&R DB, original exports, or saved `lvs-input.json`. Continue using this
explicit override until P&R outputs/config snapshots are regenerated.
The previous report, effective configuration, control, deck and input
snapshot were copied with hashes to
`sky130-hammer-lvs-integration/top-level/before-20261108-014239`.

`sky130-lvs-normal-flow.py` now generates this wrapper as well as the
separate-directory runner. It guards the overlay against the qualified
layout/netlist paths and hashes. A make dry run verifies the override is
passed after the stale input snapshot. All **43 focused tests** pass,
including runner argument/overlay guards. No new CAD execution was
performed locally; the corrected top-level run and physical DRC remain
pending.

## Full chip MATCH; normal Hammer integration prepared (2026-11-08)

`sky130-por-vddio-repair/full-chip/ChipTop.lvs_results.cls` is **MATCH**:
165 matched types, six expanded, zero not run, zero mismatching types,
zero parameter/subtype mismatches, and empty ERC. Extraction warnings
remain. The physical PoR supply via closes the final VDDIO open.
Report counts and SHA256 are saved in that run's `result-summary.json`.

The subsequent normal `Sky130RocketConfig-ChipTop/lvs-rundir` report
(start 01:17:34) has 21 failing types because it uses the original P&R
exports and the earlier basic deck/source preparation. Its saved `par.tcl`
still selects the historical alternate PoR GDS. Updating Python hooks
cannot retroactively change those generated scripts or existing exports.
The normal report and original P&R outputs have been preserved.

The validated transformations now live in the shared technology module
`hammer/hammer/technology/sky130/lvs_compat.py`; diagnostic scripts import
those same functions. The explicit boolean setting
`technology.sky130.lvs_mixed_library_compatibility` defaults to false and
is enabled in `example-sky130.yml`. Its manifest records the compatibility
policies: ordinary MOS/poly/real M1-M4 comparisons stay at zero tolerance;
ESD, annular PADISO and annotated SHORT treatment retain the previously
qualified policies. SRAM internals are expanded for namespace ambiguity,
not blackboxed. Physical-only decaps follow the actual source exclusion
policy. There are no virtual net joins. This remains a compatibility
qualification rather than unmodified vendor-deck signoff.

The normal schematic hook imports the required primitives, preserves ESD
subtypes, classifies IO source models, expands the relevant hierarchy and
creates a hash-guarded PoR source overlay restoring L=1.355 um. The original
PDK files are untouched. Future P&R generation with the profile also
includes the guarded PoR supply-via hook before stream export, alongside
the quiet-rail tie and the configured PoR GDS selection.

`sky130-lvs-normal-flow.py` exercised the actual Hammer technology/tool/
project hooks, stopping before CAD execution, in
`build/sky130-hammer-lvs-integration`. It verified:

- All 1,726 source circuit definitions agree with the passing run; neither
  source contains executable statements outside those definitions.
- The generated extraction deck is byte-identical after its provenance
  header (SHA256 `30dbb5e48ea06d590a14bc009ff215abcabc3fb01e568702e761c44015a08c34`).
- All 310 hierarchy-expansion names agree with the passing run.
- The layout and Verilog are the already qualified repaired physical
  exports; their hashes and the passing report hash are recorded.

Run the unmodified normal Hammer driver and fresh-report result checker:

```bash
bash "$PWD/vlsi/build/sky130-hammer-lvs-integration/run.sh"
```

This overlay explicitly enables the new setting because the old saved
`lvs-input.json` predates it. It uses repaired exports without another P&R
run. Fresh P&R generation is still needed to replace the historical
outputs in the original `par-rundir`. Normal Hammer CAD execution is
pending; preparation does not claim a new LVS result. All **42 focused
regression tests** pass. Physical DRC of the quiet-rail tie, PoR via and
placement remains pending.

## Via insertion succeeded; DEF checker corrected and resume prepared

Innovus completed the `sky130-por-vddio-repair` export and logged
`PoR VDDIO physical repair: via3 {3277.2 177.89}, 4x1 cuts, net VDDIO`.
The DEF contains the intended instance as:

```text
+ FIXED met4 0 + SHAPE IOWIRE ( 3277200 177890 ) M3M4_PR_12
```

The first generated checker incorrectly required the coordinates directly
after `met4 0`, and its generated raw regex was over-escaped. It therefore
missed the actual inserted via and stopped before LVS. This was a checker
failure; the completed physical export does not need regeneration.

`check_def_via` in `sky130-por-power-repair.py` now parses the optional DEF
SHAPE clause and verifies net, point, master layers, 4x1 cuts, cut size
and metal enclosures. Generated wrappers call this checked-in function
directly rather than embedding regexes. It passes on the actual exported
DEF and identifies VDDIO / M3M4_PR_12 at the intended coordinates.

Resume with the existing exports:

```bash
bash "$PWD/vlsi/build/sky130-por-vddio-repair/resume.sh"
```

The resume command repeats the read-only netlist/via checks and runs LVS;
it does not restore Innovus or insert another via. The future `run-all.sh`
generator now delegates its post-export checks/LVS to this resume script.

The 18 IMPVL-520 warnings concern the clamp `*_PAD` PG terminals. Those
pad-side terminals are omitted from the exported clamp instance connections
by the current source, while the internal VDDIO/VDDIO_Q/VSWITCH, VCCD/
VCCHIB, VDDA and ground-rail connections are present. The prior chip
comparison matched the corresponding IO types and had only the PoR supply
open. These warnings do not establish 18 additional physical opens.
The source keeps pad-side and internal rails distinct through explicit M5
resistors (for example VDDIO_PAD--VDDIO and VCCD_PAD--VCCD), so a blanket
global tie would change that model. No clamp binding edits were made.
External pad/bond modeling and the existing timing-library restore errors
remain distinct production-flow cleanup topics; neither caused this
checker traceback. IMPVL-535 merely reports that physical netlist export
ignores `-top_module_first`.

All **39 focused tests** pass. New DEF parser regressions cover both forms
with/without SHAPE and reject wrong nets, duplicate instances, changed
coordinates and wrong via geometry. Actual-export validation, shell syntax
and both repository diff checks pass. Fresh full-chip LVS and physical DRC
of the via/quiet tie remain pending.

## PoR now matches; one confirmed physical VDDIO open remains at ChipTop

The completed `sky130-por-lvs-closeout/isolated` comparison is a strict
MATCH with clean extraction and empty ERC. In the fresh full-chip run,
`simple_por`, all four SRAM macro types and the IO/standard-cell comparison
types match. The report has **164 matches, six expanded, zero not run,
one failing type (ChipTop), zero parameter and subtype mismatches**.
All 121,530 reduced top instances match; all 49 top pins match. One
unmatched layout net remains. The source/deck repairs have therefore
cleared PoR's cell-level failures without relaxing its checks.

The sole ChipTop failure is an OPEN between VDDIO and layout net 451.
The raw top-level layout CDL contains exactly one instance connection to
451: the `simple_por` vdd3v3 pin. Its other PG connections match. The NC
export checker passes: all supplies on 27 unused pads are present and
84,944 retained logical/bus instance connections are unchanged.
`result-summary.json` saves report hashes and the remaining failure.

### Physical cause and repair candidate

The DEF has a VDDIO met3 trunk at x=3277.200 um, y=175.565..247.835 um,
width 1 um. It has the upper via at the short met4 access near PoR, but no
via3 at its lower crossing with the IO rail. `IO_FILLER_MANUAL_S_3` is an
R180 `sky130_ef_io__com_bus_slice_20um` at bbox
(3264,0)-(3284,197.965) um. Its local VDDIO met4 rail y=17.750..22.400
transforms to global **175.565..180.215 um**, overlapping the trunk.
The original filler GDS has no met3 or via3 shapes, confirming it cannot
provide the missing vertical connection. The existing route's local-via
selection considered special wires and did not include this rail inside
the macro. This is an actual missing P&R via, rather than a source/deck
dimension or cell-recognition problem.

`vlsi/sky130-por-vddio.tcl` inserts one fixed VDDIO via3 at
**(3277.200,177.890) um** using the existing M3M4_PR rule, 4x1 cuts,
0.2 um cut size/spacing and 0.065/0.100 um metal enclosures. The resulting
0.330 x 1.600 um metal pads fit fully inside both existing conductors.
The helper checks PoR/filler masters, orientations and filler dimensions,
the overlap and existing trunk net, rejects a via belonging to another
net, and skips an existing VDDIO via. It neither moves the macro nor adds
new wire segments. Commands follow installed Innovus 23.14 documentation
for `create_via_definition`, `create_via`, and `get_obj_in_area`.

Prepared command:

```bash
bash "$PWD/vlsi/build/sky130-por-vddio-repair/run-all.sh"
```

`vlsi/sky130-por-power-repair.py` clones the successful configured-PoR
reexport, adds this hook before stream generation, and runs the same
full-chip source/deck/control policies on separate new exports. It keeps
the NC bindings and quiet-rail tie, preserves the saved DB and performs
no placement/routing optimization. The existing export checker runs,
then a DEF checker requires exactly one correctly sized via on VDDIO at
the intended point before LVS. Fresh CAD results are pending.

All **37 focused tests** pass, including Tcl execution against mock DB
queries for exact placement, orientation rejection, wrong-net rejection
and repeated-call/previous-via idempotence. Offline enclosure/overlap,
unchanged source/deck/control policies, shell/Python/Tcl syntax and both
repository diff checks pass. Input and repair hashes are saved in
`experiment.json`. DRC of this via and the prior quiet-rail tie remains
required, together with production integration and normal Hammer LVS.

## Configured PoR connectivity matches; authoritative source precision correction prepared

The completed `sky130-por-lvs-components-step2/combined/por` comparison has
**matching connectivity**, 130/130 original devices, 36/36 reduced devices,
7/7 pins and 17/17 nets, with zero unmatched devices/pins/nets. Its
extraction report contains no warnings or errors and ERC is empty. Both
MIM capacitors extract as one matching 30 x 30 um device. The standalone
Schmitt terminal-correction case also has matching connectivity. MIM-only
PoR still has the short, whereas the combined case does not: the resistor
terminal gate bypass was an extraction-induced short. No physical edits
were needed to establish this isolated PoR connectivity match.

Only one parameter discrepancy remains: the Schmitt ND resistor is
L=1.355 um in layout versus 1.36 um in the custom PoR source. The original
SkyWater Schmitt SPICE and CDL both specify **1.355 um**. A polygon XOR
comparison finds identical geometry on every layer between the PoR's
Schmitt leaf and the original SkyWater GDS, at 0.000001 um computation
precision. Installed openPDKs SPICE/CDL independently agree on 1.355 um.
Thus the correction restores the original cell's source precision, rather
than relaxing a comparison tolerance or fitting an arbitrary extracted
device. Evidence is in `schmitt-source-provenance.json` and the completed
case counts/report hashes in `result-summary.json`.

`vlsi/sky130-por-closeout.py` prepares the next complete validation chain:

```bash
bash "$PWD/vlsi/build/sky130-por-lvs-closeout/run-all.sh"
```

1. Compare the configured isolated PoR with the validated combined deck
   and a corrected source overlay. The script requires a strict MATCH
   before proceeding to the chip stages.
2. Reopen the saved Sky130RocketConfig P&R DB in memory, retain the proven
   NC PG bindings and quiet-VDDIO tie, and export a separate GDS/Verilog/DEF
   using the configured CARAVEL PoR GDS instead of the older alternate.
   No placement/routing optimization or saved-DB write occurs. Restore
   retains the previously validated scoped `read_db_file_check` handling.
3. Run full-chip LVS using the new exports, validated SRAM/IO policies,
   both PoR deck corrections, and the corrected source overlay. The export
   checker verifies all NC supplies and unchanged retained logic/bus ports
   before this comparison.

The raw source change is guarded to exactly `X4` in
`BC_sky130_fd_sc_hvl__schmittbuf_1`, preserving nodes, width, model, other
devices and all other definitions. The patch is
`sky130-lvs-por-source-precision.patch`; external PDK files remain untouched.
The local generated overlay is `sky130-por-lvs-closeout/simple_por.spice`.
Both original and corrected PoR source families are independently translated
and compared with the saved compiled family. The mixed-library CDL changes
only that one length, from 1.36e-06 to 1.355e-06 m. Manifest source paths
and hashes identify the overlay explicitly.

All **33 focused tests** pass. The combined deck is byte-identical to the
completed connectivity-matching case; all comparison rules/tolerances are
unchanged. Chip control paths point to the fresh exports; the cloned
reexport Tcl differs only in output paths and the PoR GDS merge input.
The original reexport checker is byte-identical. Shell/Python syntax,
Tcl structural completeness and both repository diff checks pass.
Input/overlay/deck/control/Tcl hashes are recorded in `experiment.json`.

Fresh strict PoR and assembled-chip results are pending. The isolated
connectivity result does not yet rule out additional chip-context physical
placement issues. Production integration, normal Hammer LVS and DRC of
the quiet-rail tie remain outstanding.

## PoR components isolate a resistor-terminal gate bypass and a MIM electrode ambiguity

The completed `sky130-por-lvs-components` cases establish:

- The original configured precision-resistor array has 28 matching layout
  and source devices, zero unmatched instances and zero parameter errors.
  Its standalone 57 source-pin labels lack corresponding layout labels;
  this accounts for its remaining boundary/pin verdict.
- The original M3 MIM has one matching device and zero parameter errors;
  its unlabeled standalone layout also has boundary-pin differences.
- The Schmitt buffer reproduces its VGND/VPWR/X net collapse when extracted
  alone. ChipTop and PoR parent placement are unnecessary to trigger it.
- The first MIM2 candidate parses but produces one malformed capacitor:
  `too many pins found`. Intersecting cap2m with metal5 selects both the
  central upper-plate contact metal and a 0.2 um overlap with the lower-
  electrode return strip. These have different nets and cannot both be
  treated as the same upper terminal. The first candidate is not validated.

### Specific Schmitt extraction bypass

The deck derives `np_term` and `pp_term` from full `ndiff` / `pdiff` regions
touching `diff_res`. Those layers have the resistor body removed but still
include transistor gates. The subsequent `connect li1 np_term/pp_term -by
licon1` therefore allows selected active regions to bridge across gates.
The geometric audit finds 0.795 um2 of N-gate area and 1.5 um2 of P-gate
area inside these old resistor terminals. Using the existing gate-cut
`nSourceDrain` / `pSourceDrain` layers for the two terminal selections
reduces both overlaps to zero while retaining two terminal shapes per
polarity. Evidence is saved in `schmitt-terminal-overlap-audit.json`.

`diffusion_terminal_candidate` in `sky130-por-lvs.py` changes exactly these
two selections; device definitions, source geometry/parameters, connection
commands and tolerances are unchanged. The explicit diff is
`sky130-lvs-por-diffusion-terminals-candidate.patch`. This explains a real
extraction bypass, but its fresh CAD effect on the supply short is pending.

### Refined MIM2 candidate and next command

The revised MIM2 rule uses a copy of the cap2m marker as the separate
upper-electrode conductor, connected to metal5 only through via4 inside
cap2m. The lower electrode remains connected to metal4. Ordinary via4
outside cap2m still connect metal4 to metal5. Geometry verifies that 288
interior via centers contact only the central metal5 shape, while 19
exterior via centers contact only the return strip. This avoids the first
candidate's extra upper terminal. The refreshed MIM candidate diff is in
`sky130-lvs-por-mim2-candidate.patch`; the original failed run/deck remain
preserved in `sky130-por-lvs-components`.

```bash
bash "$PWD/vlsi/build/sky130-por-lvs-components-step2/run-all.sh"
```

Five cases test the refined MIM rule on both capacitor leaves and the
configured PoR, the terminal selection correction on the Schmitt leaf,
and both corrections together on the configured PoR. They retain the same
GDS and compiled source, with no source edits, virtual connections,
blackboxes, device filtering, physical edits or relaxed tolerances. The
small Schmitt diffusion-resistor L=1.355/1.36 um discrepancy is intentionally
still visible. Baseline component cases are not needlessly rerun.

All **32 focused tests** pass. The baseline deck is byte-identical; the
terminal variant differs only in the two expected selections; comparison
rules are unchanged in both variants. All six generated shell scripts,
recorded input/deck hashes and both repository diff checks pass. The
separated MIM contact groups are saved in
`mim2-electrode-contact-audit.json`. Fresh Pegasus results are pending;
these candidates do not yet establish PoR closure or resolve any additional
physical placement issues.

## Isolated PoR input views: configured resistor count restored; component/MIM tests prepared

Both completed `sky130-por-lvs-input-views` cases mismatch with connectivity
and parameter errors, empty ERC and zero subtype mismatches. The configured
CARAVEL GDS has **28 layout / 28 source** original precision resistors;
the older alternate has **27 / 28**. Both extract one M3 MIM capacitor and
zero `CAP_MIM_M3_2` devices against one of each in source. Both report
`vdd3v3` and `vss3v3` on the same extracted net, plus Schmitt-buffer rail/X
label conflicts. These errors reproduce without any ChipTop placement or
routing: their causes include intrinsic macro geometry and/or extraction
handling, rather than requiring a chip-level placement overlap. This does
not yet distinguish a real internal macro short from an extraction-induced
short or rule out additional chip-context errors.

The configured layout removes the alternate's missing-resistor discrepancy,
but does not establish overall PoR connectivity. Its reduced precision
resistor topology still differs from source, and the sole listed parameter
error remains Schmitt-buffer diffusion resistor L=1.355 versus 1.36 um
(0.367647%). Neither source dimensions nor tolerances were adjusted.
`result-summary.json` saves report hashes and the input-view findings.

The next seven comparisons are prepared:

```bash
bash "$PWD/vlsi/build/sky130-por-lvs-components/run-all.sh"
```

`baseline/` isolates the configured GDS's two capacitor cells, Schmitt buffer,
and full precision-resistor array. `mim2/` reruns both capacitor cells and
the configured PoR with a candidate second-MIM extraction rule. All cases
use the same completed-run compiled source. Layout root names are matched
explicitly to the corresponding `BC_` source definitions. Unlabeled
primitive/array roots may still show boundary-pin mismatches; inspect raw
device counts, connectivity and parameters, not only their result banners.
The Schmitt case tests whether its rail/X conflict is intrinsic to that
leaf or introduced by PoR parent geometry/connectivity.

The current deck maps `cap2m` (97/44) and `via4` (71/44) but has no second
MIM device statement and treats all via4 as ordinary metal4/metal5
connections. The candidate in `mim2_candidate` in `sky130-por-lvs.py`
mirrors the existing first-MIM rule: subtract cap2m from the ordinary via4
connection layer, derive bottom/top plate contacts on metal4/metal5,
recognize the cap2m body containing via4, and extract `cap_mim_m3_2` using
the existing capacitor property macro. First-MIM extraction and all
comparison rules remain unchanged. A reproducible diff is saved as
`sky130-lvs-por-mim2-candidate.patch`. This is an unqualified diagnostic
candidate, not a claimed repair of the supply short.

The installed openPDKs KLayout primary deck supports the plate/via
distinction: its MIM derivation, connection and extraction sections treat
capm/capm2 as distinct upper electrodes on metal3/metal4 capacitors, with
via3/via4 contacts. The Pegasus candidate follows the existing Pegasus
M3-rule structure for the second metal level. Both original MIM marker
rectangles independently measure 30 x 30 um, matching source. Of 307 via4
centers in the second-MIM cell, 288 lie within cap2m and 19 outside; these
groups must have different electrode-connection semantics. Counts and
marker coordinates are saved in `mim-geometry-audit.json`.

All **31 focused regressions** pass, including first-MIM/comparison-rule
preservation and rejection of unrecognized/duplicate rule inputs. The
baseline deck is byte-identical to the completed input-view run; all eight
generated shell scripts and both repository diff checks pass. Source,
GDS and deck hashes are recorded in `experiment.json`. No source or layout
edits, device filtering, virtual connections, blackboxing or relaxed
tolerances are introduced. Fresh component and MIM-candidate CAD results
are pending; the chip stream still needs the configured PoR view selected
after its remaining issues are understood.

## SRAM edge-device candidate passes in the assembled chip; only PoR remains

The completed `sky130-sram-lvs-edge-devices/ChipTop.lvs_results.cls` reports
**164 matches, six expanded, zero not run and one mismatching type**:
`simple_por`. All four SRAM macro roots and `sram_sp_hstrap` now match.
ChipTop, IO and the previously matching standard cells still match under
the existing diagnostic policies. ERC is empty and there are zero subtype
mismatches. The full-chip source CDL is byte-identical to the namespace
baseline, the control is identical after output-path normalization, and
the extraction deck matches the saved candidate hash. This validates the
one-sided gate sizing correction for this assembled Sky130RocketConfig
comparison without changing source dimensions or comparison tolerances.
`result-summary.json` records the result and report hashes.

Isolated `sram_sp_cell`, `sram_sp_cell_replica`, and `sram_sp_colend` now
have zero parameter-mismatch types. Their standalone pin/boundary failures
remain as expected. Isolated hstrap still compares one unmerged layout
device at W=0.14 um against two merged source devices at W=0.28 um because
of its local gate/bulk net binding discrepancy; its L error is gone. The
full-chip hstrap comparison and all macro roots pass strict sizing and
connectivity checks after those bindings resolve in the enclosing circuit.
An expanded `folded_inv` diagnostic banner still contains local parameter
differences but says no instances were compared there; its actual parent
macro comparisons pass. Do not count these expanded/no-instance banners
as additional failing macro types.

Next, `vlsi/sky130-por-lvs.py` prepares two isolated PoR input-view tests:

```bash
bash "$PWD/vlsi/build/sky130-por-lvs-input-views/run-all.sh"
```

`configured/` uses the CARAVEL `simple_por.gds` paired with the configured
SPICE library. `alternate/` uses the older
`/tools/C/rohankumar/sky130/stac_tapeout/gds/simple_por_drc_lvs.gds` still
merged by the saved v2 export script. Both use the same completed-run
compiled source and a byte-identical copy of the current extraction deck;
their control files differ only in GDS path. Both layout roots and the
saved PoR source hash were verified. No geometry/source/device/parameter
changes, virtual joins, blackboxes or filters are added. Results are
pending. These tests distinguish intrinsic PoR view/extraction failures
from additional chip placement/routing effects before a stream correction.

The generated commands pass shell syntax checks; source/control/deck
invariants and both repository diff checks pass. The 30 focused regressions
passed when the SRAM candidate was prepared. SRAM repair integration into
the normal Hammer flow remains part of the production integration task;
this result is diagnostic closure, not a production-flow LVS/DRC signoff.

## SRAM edge-device sizing candidate prepared

The isolated results reproduce the clipped-gate PFET dimensions
L/W=0.05/0.07 um versus source 0.025/0.14 um, and the raw clipped NFET
dimensions 0.28/0.07 um versus source 0.14/0.14 um. These discrepancies
exist in the original macro inputs independently of ChipTop P&R. The
geometry has a rectangular gate with one full source/drain-facing edge
and three edges on the active boundary. Dividing that one contact's
perimeter by two gives half the physical width; area divided by that
width gives twice the physical length. This explains the repeated pattern
without changing the supplied source dimensions.

`edge_device_candidate` in `vlsi/sky130-sram-lvs.py` prepares a geometric
recognition partition for only `nfet_01v8` and `pfet_01v8_hvt`:

1. Select orthogonal rectangular gate recognition shapes.
2. Require exactly one source/drain-coincident edge and three
   active-boundary-coincident edges. The second condition constrains the
   shape to an active-edge gate rather than an arbitrary partial contact.
3. For selected gates, compute W from the full coincident source/drain
   perimeter and L from gate area / W. Retain built-in sizing for the
   complementary recognition shapes.

The partition is disjoint and exhaustive; device models and terminals are
unchanged. No source edits, filtering, blackboxing, virtual connections,
comparison-rule changes or tolerance changes are introduced. This is a
layout-wide geometric candidate for these two models, not a cell-name
waiver. It needs a full-chip regression before production integration.
The reproducible deck diff is `sky130-lvs-sram-edge-sizing-candidate.patch`.

The PVL selection and device-property syntax follows installed Pegasus
23.10 documentation: `comref_re_rect_chk.html`, `comref_re_edge_select.html`,
`comref_re_select.html` (`-with_edge` and its edge-count constraint),
`comref_re_device.html` (multiple statements with the same model/pins), and
`appa_device_property.html` under the installed `doc/pegasusref` directory.

Prepared command:

```bash
bash "$PWD/vlsi/build/sky130-sram-lvs-edge-devices/run-all.sh"
```

It runs four isolated original cells, followed by the same full-chip
comparison as the completed namespace run. The full-chip source CDL is
byte-identical, and its control differs only in output-directory paths.
All four leaf source blocks are byte-identical to their previous cases.
The full-chip comparison retains SRAM namespace expansion, strict device
checks and the existing documented IO policies; PoR remains visible and
active in the work list.

Independent polygon boolean/edge measurements select exactly seven edge
gates across the four qualification leaf types in **each of the four
original SRAM macro GDS files**. They recover the supplied source L/W
exactly: PFET 0.025/0.14 um and NFET 0.14/0.14 um. Auditing the Cadence
SCL GDS measures 2,008 relevant rectangular gates across 155 cell
definitions and selects zero gates for the new rule. Synthetic R0/R90/
R180/R270 checks retain ordinary two-sided dimensions and correctly size
one-sided gates. Evidence and input hashes are saved in
`edge-geometry-audit.json`, `all-macro-edge-geometry-audit.json`,
`standard-cell-geometry-audit.json`, and `rotated-geometry-checks.json` in
the candidate directory. `check-geometry.py` preserves the independent
polygon audit. These are offline checks, not fresh Pegasus extraction.

All **30 focused tests** pass, including preservation of device models,
pins and strict comparisons, plus rejection of unrecognized/duplicate
deck statements. Source/control invariants, all seven generated shell
scripts and both repository diff checks pass. Fresh CAD results are
pending in the user's CAD shell; no production extraction repair or SRAM
LVS pass is claimed yet. Isolated leaf pin/bulk/abutment issues can persist
even if sizing is corrected, so inspect raw devices and full macro roots
instead of treating a standalone MISMATCH banner as a sizing verdict.

## Active LVS work list (PoR reactivated by user)

The full-chip target is
`chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop`, with LVS primary
`ChipTop`. Current full-chip diagnostics use the actual repaired
`sky130-nc-pg-export-v2/ChipTop_drc_lvs.gds` and `ChipTop.lvs.v` exports
derived from that target's saved P&R database. The most recent four-case
command checks isolated SRAM library cells, not the entire Rocket chip;
its GDS input is the original `sram22_64x22m4w22` macro library.

- [x] **SRAM sizing:** the repeated edge-device parameter errors are resolved
  in the completed full-chip candidate; all four macro roots and hstrap
  pass. Production integration remains a separate task below.
  The four isolated-cell runs have completed and reproduce the primitive
  sizing discrepancies without ChipTop placement/routing. The cell and
  replica PFETs compare L/W=0.05/0.07 um against source 0.025/0.14 um;
  colend/hstrap NMOS extract L/W=0.28/0.07 um per primitive. Standalone
  reports also contain boundary/pin/connectivity issues, including missing
  WL labels and hstrap bulk/gate net bindings. In hstrap this prevents the
  same parallel reduction on each side, giving an apparent 75% reduced
  width error; use raw device dimensions when interpreting that result.
  Macro-root connectivity still matches in the completed full-chip run.
- [x] **PoR input pairing:** the closeout reexport uses the configured
  CARAVEL GDS and corrected source overlay; PoR matches in isolation and
  in the chip. Historical input evidence follows for traceability:
  with the configured source before diagnosing the remaining devices.
  `config_db_tmp.json` selects CARAVEL `simple_por.gds` and
  `simple_por.spice` under `/scratch/jfx/cadence-skywater-130-pdk`, with
  `technology.sky130.por_drc_lvs_gds = null`. However,
  `sky130-nc-pg-export-v2/reexport.tcl:265` and `innovus.log3` confirm that
  the current diagnostic stream still merges
  `/tools/C/rohankumar/sky130/stac_tapeout/gds/simple_por_drc_lvs.gds`.
  The repaired production driver does not retroactively change that saved
  reexport script. The two layout variants differ in a resistor body and
  label, as documented below. Qualify the configured GDS/SPICE pair in
  isolation and regenerate the chip stream with the intended view.
- [x] **PoR physical connectivity:** inserted the missing via3 from the
  PoR VDDIO trunk to the filler met4 rail; full-chip LVS is MATCH. Physical
  DRC is tracked separately below.
- [x] **PoR extraction and parameters:** second-MIM extraction, gate-cut
  resistor terminals, configured GDS resistor count and the authoritative
  1.355 um source precision correction establish a strict PoR match.
- [x] Integrate validated IO/SRAM/PoR handling and explicit compatibility
  policies into the normal Hammer flow; generated inputs agree with MATCH.
- [x] Run normal Hammer full-chip LVS integration check: MATCH, 165 types.
- [ ] DRC-check the quiet-VDDIO rail tie, PoR supply via and placement.

IO, SRAM macros and PoR match under the current diagnostic policies.
The repaired full-chip run and the normal Hammer run with integrated
policies/repaired exports both MATCH with 165 matched types. Fresh mainline
P&R regeneration and physical DRC remain pending.
PoR is no longer deferred;
references to deferral in the historical entries below describe earlier
scope decisions.

## 2026-11-08: namespace result isolates SRAM edge-device sizing

The completed `sky130-sram-lvs-namespace/ChipTop.lvs_results.cls` reports
**159 matches, six expanded, zero not run and six mismatching types**,
with zero subtype mismatches and empty ERC. ChipTop and the IO comparison
types still match under the documented IO compatibility policies. The
false `tristate_inv` and `column_mos` boundaries no longer appear as failed
comparisons. The remaining failed types are the four SRAM macro roots,
`sram_sp_hstrap`, and deferred `simple_por`.

All four macro roots still report matching connectivity. Every parsed
MOS parameter-error row within these four roots has layout **L = 2 * source
L, W = source W / 2**, including widths after parallel reduction. There
are 67,392 rows for `512x64`, 34,113 for `512x32`, 3,737 for `64x24`, and
3,433 for `64x22`; these are report comparison rows, not physical-device
counts. `parameter-patterns.json` records model/dimension patterns and row
counts. The two dominant primitive cases are PFET L/W 0.05/0.07 um versus
source 0.025/0.14 um and NFET 0.28/0.07 um versus source 0.14/0.14 um.
The enormous remaining report is therefore largely repeated instances of
these sizing patterns, rather than thousands of distinct failure causes.

Original `sram22_64x22m4w22.gds` geometry has active-edge-clipped gates in
these SRAM leaves. For example, a hstrap active rectangle terminates at
y=-1.32 um within a poly stripe ending at y=-1.31 um, leaving only one
source/drain-facing edge on that gate. A width calculation assuming two
source/drain edges could explain the factor of two; this remains a
hypothesis pending a focused extraction test and property-rule validation.
Do not globally rescale SRAM dimensions or ignore tied source/drain devices.
The replica leaf's local WL/VSS short also resolves in the enclosing macro
comparison and is not, by itself, a chip P&R connectivity failure.

The next qualification compares four original library leaf cells with the
current extraction deck and exact translated source blocks:

```bash
bash "$PWD/vlsi/build/sky130-sram-lvs-bitcells/run-all.sh"
```

The cases are `sram_sp_cell`, `sram_sp_cell_replica`, `sram_sp_colend`, and
`sram_sp_hstrap`, prepared by `sky130-sram-lvs.py --qualify-bitcells`.
No geometry, device dimensions, extraction computation or tolerance changes
are made. No virtual connections, filters or blackboxes are added. This
isolates the original macro inputs from ChipTop and the helper namespace.
Isolated boundary geometry can differ from abutted arrays, so these results
must be interpreted together with the full macro comparison. Input hashes
and limitations are saved in `experiment.json`; relevant original polygons
are saved in `original-bitcell-geometry.json`. CAD results are pending.

All 29 focused tests pass. The four GDS roots exist, extracted source blocks
are byte-identical to the completed chip run, the deck is byte-identical,
the factor-of-two macro error pattern was checked across all parsed rows,
all five generated shell scripts pass syntax checks, and both repository
diff checks pass. SRAM sizing is the active investigation. PoR, production
integration, the normal Hammer LVS rerun, and quiet-rail DRC remain pending.

## 2026-10-28: assembled IO comparison passes; SRAM namespace diagnostic prepared

The completed `sky130-io-lvs-m3-ring-chip-context-step2` comparison reports
**161 matches, 14 expanded, zero not run and eight mismatching types**.
ChipTop and all compared IO types match under the documented SHORT and
PADISO compatibility policies. Extraction has zero errors and ERC is empty.
The two additional EF wrapper expansions resolved the promoted PADISO
device boundary mismatch without changing the source CDL or extraction deck.
This establishes diagnostic IO closure under those policies, rather than
vendor-qualified extraction accuracy or a completed production-flow signoff.

The remaining failures are seven SRAM types and `simple_por`. All seven
SRAM types report matching connectivity with parameter mismatches. A source
namespace audit found a likely cause of some of those parameter errors:
independently generated macro libraries reuse helper names for differently
sized circuits, and their aggregate SPICE and merged layout assign different
suffixes. For example, the layout comparison's bare `tristate_inv` uses
5 um devices while the aggregate source's bare helper uses 1.2 um devices;
the matching 5 um source circuit exists as `tristate_inv_3`. Similarly, the
layout `column_mos` has 1.6/2.25 um devices while aggregate source
`column_mos` has 1.2/1.7 um devices; the matching aggregate variant is
`column_mos_7`.

Recursive fingerprints establish that each of the four aggregated macro
circuits matches its individual SPICE file after internal subcircuit names
are removed from the comparison. This check preserves instance names,
terminal order, nodes and parameters; it is a sufficient identity check,
not a general graph-isomorphism algorithm. The saved evidence is in
`sky130-io-lvs-m3-ring-chip-context-step2/sram-source-namespace-audit.json`.
Thus this evidence points to false same-name helper comparison boundaries,
not a missing SRAM source library or incorrectly aggregated macro circuit.

`vlsi/sky130-sram-lvs.py` prepares the next diagnostic:

```bash
bash "$PWD/vlsi/build/sky130-sram-lvs-namespace/run.sh"
```

The new control adds `lvs_exclude_hcell` for 299 helper names from 55
ambiguous families, comparing their complete devices in the enclosing
circuits. All four macro boundaries remain intact, and a guard prevents
expansion of Cadence SCL cells. Source CDL and extraction deck remain
byte-identical to the successful IO diagnostic; no transistor, geometry,
parameter tolerance, filtering or blackbox policy changes. The source
hashes, equivalence checks and exclusion list are saved in
`namespace-audit.json`. Fresh CAD results are pending.

This hypothesis does not explain every SRAM parameter error yet.
`sram_sp_hstrap` is not an ambiguous helper family: the report shows layout
L/W of 0.28/0.14 um against source 0.14/0.28 um. Replica pass-device sizing
also needs investigation after the hierarchy diagnostic. Do not discard
these devices merely because their drain and source are tied; they can
represent intentional MOS capacitance. PoR remains deferred with its
GDS/CDL correspondence and possible placement short unresolved.

All 29 focused tests pass, including a synthetic namespace test that checks
equivalent roots, distinguishes helper sizing, and rejects changed macro
circuits and recursive hierarchy. Generated-input comparisons, shell syntax
and both repository diff checks pass. Production integration of the IO
policies, a normal Hammer LVS rerun, and DRC of the quiet-rail tie remain
outstanding.

## First assembled PADISO partition result: dimensions pass; two wrapper boundaries need expansion

The completed `sky130-io-lvs-m3-ring-chip-context` report has **160 matches,
14 expanded, zero not run and 11 mismatching types**. Extraction has no
errors and ERC is empty. All compared standard-cell types match. The ring
parameter errors pass under the explicit 5% equivalent-width policy; the
new IO failures concern comparison hierarchy, not parameter tolerance.

`sky130_ef_io__vssa_hvc_clamped_pad` and
`sky130_ef_io__vdda_hvc_clamped_pad` each have two source PADISO resistors
and zero local layout PADISO resistors. At ChipTop exactly **64 additional
raw ring segments reduce to 16 unmatched layout PADISO resistors**. There
are four instances of each wrapper, giving `8 wrappers * 2 rings = 16`:
the partition derivation promotes the layout devices above these local
comparison boundaries while the source devices remain inside them. Top
instance totals are consequently 121,490 layout versus 121,474 source.
This is not evidence of an additional physical short or missing PDK import.
The focused report is saved as `io-connectivity-excerpt.txt`.

The next diagnostic is prepared:

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-m3-ring-chip-context-step2/run.sh"
```

Opt-in `--expand-padiso-wrappers` adds exactly these two EF names to
`lvs_exclude_hcell`, retaining both complete circuits for comparison at
their common parent. It requires the PADISO partition candidate. The new
run's source CDL and extraction deck are byte-identical to the completed
run; the control policy differs only by those two boundary exclusions.
There are no geometry, tolerance, source-connectivity, filtering or virtual
net-join changes. Its result is pending, so IO closure is not claimed yet.

The remaining non-IO failures are seven SRAM comparison types and PoR.
Every one of those seven SRAM banners explicitly says **CONNECTIVITY
MATCHES / PARAMETER MISMATCHES**: four macros (`512x64m4w8`, `512x32m4w8`,
`64x24m4w8`, `64x22m4w22`) and three internal types (`sram_sp_hstrap`,
`tristate_inv`, `column_mos`). Their device parameter interpretation remains
to be investigated; they are not currently reported as macro connectivity
failures. PoR still has missing source-to-layout device correspondences,
including MIM capacitors, precision resistor segments and Schmitt-buffer
MOS, in addition to its deferred connectivity/placement concern. Confirming
the chosen PoR GDS/CDL pair remains necessary before classifying its errors.

After these diagnostic results are resolved, validated IO extraction/source
handling and its explicit compatibility policies still need integration
into the normal Hammer flow and a clean production-flow rerun. The NC CPF
fix and physical quiet-rail hook exist, but the original saved DB was never
overwritten. The quiet-rail patch also still needs DRC validation.
All 28 focused tests, generated-input comparisons, shell syntax and both
repository diff checks pass for the new boundary experiment.

## All original R0 PADISO variants characterized; bounded full-chip candidate

The user completed the three additional qualification runs. All four
original pad variants have matching connectivity, eight ring segments
reducing to two resistors, zero extraction errors, empty ERC, and exact
normalized reference lengths. Only equivalent-width differences remain:

| Original pad | Left W error | Right W error |
| --- | ---: | ---: |
| Ground HVC | 0.168271% | 0.168271% |
| Ground LVC | 0.168271% | 0.168271% |
| Power HVC v2 | 2.70527% | 2.70527% |
| Power LVC | 3.76675% | 3.63931% |

The supplied source uses W=11.825 um, L=0.01 um for all eight RIL/RIR
calls despite these different ring geometries. These isolated tests compare
the original library inputs, so none of these errors depends on ChipTop P&R.
`qualification-summary.json` records results and report hashes. Residual
errors remain differences between the fixed nominal source and the segment
approximation; an accurate corner-field solution has not been established.

### Assembled-chip candidate with an explicit PADISO-only bound

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-m3-ring-chip-context/run.sh"
```

The chip helper now has opt-in `--partition-padiso-rings` and an explicit
`--padiso-ring-width-tolerance {0,5}` policy. This candidate uses **5% only
for normalized equivalent width of `res_io_padiso_m3`**, retaining 0% for
its normalized length. Five percent is a proposed bounded compatibility
policy covering the 0.168–3.767% observed across these original pad variants;
it is not a vendor-qualified accuracy specification or geometric signoff.
The strict 0% runs remain preserved. No source dimension is adjusted to
match the measured output, and all existing device property checks retain
their prior values. Ordinary MOS/poly and real M1-M4 remain at 0%; M5 and
explicit ESD policies are unchanged. The new bound does not apply to generic
M3 resistors, standard cells, SRAMs, or arbitrary resistor types.

The prepared comparison uses the actual repaired v2 GDS and Verilog. The
only additional source change is subtype renaming on eight RIL/RIR calls
in four explicit IO definitions; reversal proves all nodes, dimensions,
parameters and other definitions identical to the prior source. The full
chip has no virtual connections, net joins or diagnostic NC supply edits.
It writes layout/source comparison netlists for further inspection. The
original-pad evidence is copied to `original-pad-qualification.json`.

This is the first assembled/rotated-context test of the partition method.
Projection interactions, orientation dependence and any remaining ring
mismatches must be checked in its report before promoting a production
repair. SRAM and PoR errors remain visible and deferred. Original P&R
geometry and external PDK files remain unchanged; the quiet-rail tie still
requires DRC validation.

All 28 focused tests pass, including a new regression proving that the 5%
option changes only the new PADISO width check while leaving its length
and generic M3 checks strict. Generated-case validation, source reversal,
absence of virtual net joins, shell syntax and repository diff checks pass.
Fresh full-chip Cadence results are pending in the user's CAD shell.

## Partition result: expected reduction works; residual equivalent-width errors are 3.64–3.77%

The completed `sky130-io-lvs-m3-ring-partition/cell.lvs_results.cls` confirms
the partition candidate parses and extracts correctly in the isolated
power-LVC pad. Eight raw ring segments reduce in parallel to the expected
two source resistors, with zero unmatched instances/nets and matching
connectivity. ERC is empty; only the same explicit standalone supply and
label warnings remain. The normalized lengths match source at 0.01 um.

The remaining parameter errors are now **3.76675% and 3.63931% in equivalent
width**, versus the original 3000+% length errors. Summing the four exported
segment widths per terminal pair independently reproduces the report:

| Source element | Segment-sum equivalent W (um) | Source nominal W (um) | W difference |
| --- | ---: | ---: | ---: |
| RIL | 12.270418 | 11.825 | 3.766748% |
| RIR | 12.255348 | 11.825 | 3.639307% |

The source dimensions and 0% checks remain unchanged. These are residual
differences between a segment approximation and the supplied fixed nominal
model, not yet proof of which model is quantitatively more accurate; corner
field effects remain outside this extraction approximation. No tolerance
has been widened to turn this into a pass. Exported-segment validation is
saved as `partition-result-summary.json` beside the report.

### Qualify the remaining original pad variants

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-m3-ring-qualification/run.sh"
```

The helper now accepts `--cell` restricted to the four known PADISO source
definitions. The batch prepares the remaining three original R0 pad tests:
ground HVC, ground LVC and power HVC v2. It reuses the completed power-LVC
result rather than rerunning it. Each new case has byte-identical strict
deck and source CDL to the completed candidate; only primary-cell selectors
and local file paths differ. Standalone same-name supply assumptions remain
explicit. This broadens validation before choosing any residual comparison
policy or applying the approximation to rotated/assembled pads. No fresh
full-chip run or production PDK change is made.

All 27 focused tests pass. Generated-case comparisons, shell syntax and
repository diff checks pass. The new batch still needs the user's CAD shell.

## Original-pad probe completed; parallel-segment candidate prepared

The user completed `sky130-io-lvs-m3-ring-probe`. The original FD power-LVC
pad GDS versus original FD/EF source reproduces exactly the two M3 failures
seen in ChipTop. Connectivity matches; ERC is empty and no extraction errors
are reported. RIL reports L=0.322861, W=59.76 um and RIR L=0.32644,
W=59.345 um, versus the supplied L=0.01, W=11.825 um. This isolates the
discrepancy to the library/deck property calculation without any ChipTop
placement, routing, quiet-rail patch or NC-pad export in the inputs.
The exported CDL retains standard W/L; it does not expose the additional
`ring_*` properties even though the device table lists their definitions.
No unobserved probe values are used below.

### Parallel-segment candidate

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-m3-ring-partition/run.sh"
```

`sky130-m3-ring-lvs.py --partition-rings` prepares this candidate for the
same isolated original R0 power pad. It intersects M3 resistor markers
with actual M3 metal, identifies rectangular holes, and splits each ring
into its two vertical and two horizontal current paths. These paths still
connect the original conductor terminals. Recognition layers are partitioned;
no metal, routes, vias, or source connections are edited.

Each segment's area/contact-perimeter ratio is normalized to a common
0.01 um reference length, preserving its L/W (sheet-resistance squares).
Parallel resistor reduction can then sum the equivalent widths instead of
treating the whole varying-thickness annulus as one uniform strip. A new
`res_io_padiso_m3` subtype distinguishes these annuli. On the source side
only RIL/RIR in the four qualified pad definitions receive that subtype:
all eight calls retain byte-identical nodes, dimensions and values.
Existing generic M3, other resistor, and MOS checks remain unchanged; the
new equivalent L/W checks are **0%**. Residual differences from nominal
source values remain errors rather than being hidden by a tolerance change.

The original power-pad Magic geometry confirms two rings, eight rectangular
components, equal hole Y extents (needed by the horizontal projection), and
complete preservation of the 38.5106 um^2 marked-conductor area. The result
is saved as `partition-geometry-check.json`. The candidate is limited to
this isolated R0 pad: projection interactions, other orientations and
nonrectangular rings have not been qualified for chip-wide use. Segment
properties are an electrical approximation and do not solve corner fields;
a strict mismatch may remain against the source's nominal equivalent model.
This is not yet a production deck repair or a geometric signoff result.

All 27 focused tests pass, including source-classification scope, terminal
guards and preservation of dimensions/other M3 calls. Generated-source
reversal and deck comparisons verify model-only source changes, unchanged
existing property checks/control policy, and agreement with the generator.
Geometry checks, shell syntax and repository diff checks pass. Fresh CAD
results for this candidate are pending; no new chip run is required yet.

## 2026-10-28 continuation: ring probe pending; equivalent-resistance clue

The isolated M3 probe still has no completed report. A local attempt on
2026-10-28 stops before extraction: Pegasus cannot open its Ctrl-Manager
listening port (`Operation not permitted`, `Failed to initialize gateway`).
No CAD result or deck-parser validation is claimed from that attempt.

Independent analysis of the original ground-HVC Magic layout finds one
rectangular annulus with outer bounds (0.505,57.32)-(24.385,63.56) um and
inner bounds (0.515,57.76)-(24.375,63.12) um. Its vertical walls are 0.01 um
thick and horizontal walls 0.44 um thick. The computed marker area is
21.1216 um^2, agreeing with the original GDS inspection and extracted W*L.

Under the explicit assumption that the inner and outer boundaries form
equipotential terminals, approximate four straight radial-current strips
as parallel sheet resistors. Ignoring corner spreading, normalized
conductance is

`G/Rsheet^-1 = 2*5.36/0.01 + 2*23.86/0.44 = 1180.454545...`.

Thus the approximate resistance in squares is 0.0008471313, versus nominal
source L/W = 0.01/11.825 = 0.0008456660 (**0.1733% difference**). The current
area/contact-perimeter result gives 0.355942/59.34 = 0.0059983485 squares,
about **7.09 times** nominal. This supports investigating the property
calculation for a nonuniform annular conductor; it does not prove a defect
in the imported metal. It also does not validate a replacement extraction
formula: corner fields, actual terminal contacts, and other ring geometries
still require checking. No tolerance or source dimension has been changed.

Inputs, hash, dimensions, assumptions and results are recorded in
`sky130-io-lvs-m3-ring-probe/ground-hvc-strip-analysis.json`. The small probe
now explicitly writes `ring.layout.cdl` and `ring.source.cdl` using the
documented `lvs_write_netlist` command, in addition to the comparison report
and geometry-property data. Its generator and the existing prepared control
file are both updated. The same CAD-shell run command remains valid.

## SHORT-subtype result: ChipTop matches; only eight M3 pad-ring types remain in IO

The completed `sky130-io-lvs-short-markers/ChipTop.lvs_results.cls` has
155 matching types, 14 expanded, zero not run and 16 mismatching types.
There are zero subtype mismatches and no extraction `[ERROR]` entries;
ERC is empty. **ChipTop and `com_res_weak` now match** with real M1-M4
resistor checks still at 0%, M5 at 1%, and the explicit SHORT subtype policy.
No new IO connectivity discrepancy appears. This validates the annotated
SHORT distinction for the devices exercised in this assembled chip.

All remaining IO parameter rows are **28 W/L rows on M3 RIL/RIR devices**
inside eight EF supply-pad types. The other eight failing types are the
deferred SRAM/PoR failures. The summary is saved as
`sky130-io-lvs-short-markers/metal-mismatch-summary.json`.

Further read-only inspection of the original FD GDS disproves a simple
marker-clipping repair: the ground HVC and ground LVC M3 ring marker area
42.2432 um^2 lies entirely within local M3 metal. Power LVC marker area
38.6668 um^2 overlaps 38.5106 um^2 of local M3 metal. The ring walls vary
between roughly 0.01 um and 0.36/0.44 um. A single area/contact-perimeter
pair does not reproduce the source's fixed nominal L=0.01, W=11.825 um;
clipping the marker to metal cannot explain or remove the large mismatch.
The same source values are present in the raw IO source checkout, so they
were not introduced by our translation. No source dimensions have been
edited to force agreement with the extracted values.

### Original-PDK ring probe, independent of ChipTop P&R

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-m3-ring-probe/run.sh"
```

`vlsi/sky130-m3-ring-lvs.py` prepares a small power-LVC-pad comparison from
the original FD GDS and hash-checked raw FD/EF IO SPICE/CDL. It uses the
current strict deck and SHORT classification, but no ChipTop GDS, Verilog,
placement or routes. The M3 property macro retains exactly the current W/L
formula and additionally records recognition area, perimeter and each
terminal's coincident contact length for diagnosis. It is a probe, not a
proposed geometry repair. Existing same-name standalone virtual supply
assumptions are explicit and restricted to the pad; this test cannot
demonstrate assembled-chip power continuity. All real-device dimension
checks remain identical to the full-chip run. The previously validated
standalone pad test completed in about five seconds, avoiding another
full-chip comparison while investigating this property calculation.

All 26 focused tests pass. Preparation checks confirm original-PDK-only
inputs, unchanged W/L computation and check rules, shell syntax, and clean
repository diffs. The new probe result is pending in the user's CAD shell.
No new production deck changes or geometric signoff claims are made.

## Strict metal-dimension result: SHORT surrogates and M3 pad rings

The user completed `sky130-io-lvs-metal-dimensions`. The summary is
153 matches, 14 expanded, zero not run, 18 mismatching types. The ten new
failing comparison types are `com_res_weak`, eight EF supply-pad types,
and ChipTop; all ten have matching connectivity and parameter errors only.
The prior SRAM/PoR failures remain outside this IO investigation. The actual
quiet-rail tie and NC supply completion remain effective.

`metal-mismatch-summary.json` in that run summarizes the IO/top-level
parameter patterns without the much larger SRAM report. For example:

* `com_res_weak`: five series-reduced M1 pairs report L=0.0100752 um versus
  nominal source L=0.02 um, W=0.665 versus 0.66 um.
* ChipTop: repeated M1 marker widths include 0.235, 0.265, 0.655 and
  1.325 um versus a fixed source width of 0.66 um. M2 also reports a
  0.655 um width versus the fixed source 0.26 um.
* Supply-pad M3 rings: individual LVC rings report L=0.322861/0.32644 um,
  W=59.76/59.345 um versus source L=0.01, W=11.825 um. HVC ring pairs
  reduce in parallel in some EF wrappers; their errors remain visible.

The raw source annotates the `tk_em*` calls as former `short` instances,
then supplies fixed nominal metal-R dimensions. Inspection of the original
FD GDS finds distinct `tk_em1s` variants with datatype-15 marker heights
0.23, 0.26, 0.66 and 1.32 um. Their notched marker bodies also explain why
area/coincident-perimeter dimensions differ from the nominal bounding-box
length. These are not failures to import the source or recognize a device.
The M3 pad annuli use datatype 13, and remain a separate geometry question.

### Narrow SHORT-subtype diagnostic

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-short-markers/run.sh"
```

New opt-in `--classify-io-shorts` splits M1-M4 datatype-15 SHORT recognition
from datatype-13 real resistor recognition using the stock `met*_short`
layers. It preserves electrical gaps for both classes. On the source side,
only metal calls with an original `* Rname nodeA nodeB short` annotation
and exactly matching terminals are renamed to `res_io_short_m*`:
**28 calls in 13 IO definitions**. Only subtype names change; every node,
dimension, unit and other device remains byte-identical. No real resistor
call is reclassified from its dimensions or from a report mismatch.

SHORT devices retain subtype/count/terminal comparison and extracted
properties, but nominal W/L are not compared. Every real-device property
check remains identical to the strict run, including all eight 0% M1-M4
checks, 1% M5, and the M3 pad rings. M5 marker handling is unchanged because
the pad's real M5 resistor uses datatype 15. The existing M1 RC/RB filtering
is explicitly applied to the SHORT subtype as well. There are no virtual
connections or net joins. This remains a candidate, not a production waiver
or geometric pass. Unannotated source SHORT surrogates, if present in the
active design, will remain visible as subtype/parameter discrepancies.

All 26 focused tests pass, including rejection of mismatched SHORT annotation
terminals and non-IO annotations, preservation of real/M5 calls, and
idempotence. Generated-source reversal proves the model-only changes;
generated-deck checks prove unchanged real-device comparisons and M5
handling. Shell syntax and repository diff checks pass. Fresh Pegasus
results for this candidate and physical tie DRC remain pending.

## Regenerated chip: ChipTop matches; IO metal dimensions are the next diagnostic

The user completed the corrected v2 export and full-chip comparison:
`vlsi/build/sky130-nc-pg-export-v2/lvs/ChipTop.lvs_results.cls`.
Innovus `innovus.log3` confirms the actual met4 tie at
(213.5,5055.535)-(214.5,5059.035), then writes the new Verilog, DEF and merged
GDS. The export checker passes all 27 NC pads' supplies and unchanged logical
connections for 84,944 retained instances. The new LVS uses these actual
outputs with no diagnostic source supply edits and no virtual connections.

**ChipTop now matches**, with 49 pins and 121,474 reduced instances on each
side. The quiet VDDIO_Q open is gone. The comparison summary is 163 matches,
14 expanded, zero not run, eight failing types. Those types are four SRAM
macros, three SRAM internal types (`sram_sp_hstrap`, `tristate_inv`,
`column_mos`), and the deferred `simple_por`. There are no failing IO or
Cadence standard-cell comparison types. Extraction has no `[ERROR]` entries;
label warnings remain, and ERC is empty. This is still the topology diagnostic
policy: M1-M4 dimensions are omitted and M1 floating/self-loop filters apply.
The physical tie has not yet been DRC validated.

The next run is prepared using the same regenerated GDS and Verilog:

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-metal-dimensions/run.sh"
```

The helper's new `--check-io-metal-dimensions` option adds exactly eight
M1-M4 W/L comparisons at 0%, leaving every other deck rule and the source
CDL unchanged. Ordinary MOS/poly remain at 0%, ESD W/L at 7%/1%, M5 at 1%.
The filters and expansion boundaries remain explicit. This is a geometry
diagnostic, not an assertion that the prototype metal property macro is
already correct or that every source SHORT surrogate describes literal
geometry. No tolerance is widened to obtain a pass. The manifest accurately
records the selected inputs, absence of source supply edits, and active
dimension checks. Preparation checks the eight-rule-only deck difference,
byte-identical CDL, and absence of virtual ties/net joins. All 25 focused
tests, shell syntax and repository diff checks pass. Pegasus execution is
still required in the user's CAD shell; no new result is claimed yet.

## Assembled-chip step 3: every top-level instance corresponds; one quiet-rail open

The step-3 report is now available. It retains nine failing comparison types
(seven SRAM types, PoR, ChipTop), but ChipTop itself has **121,474 reduced
instances on each side and zero unmatched instances**. All 1,500 native FETs
and all 44 reduced diffusion resistors correspond. The XRES resistor short is
gone. The 243 unmatched NC supply nets are gone, and the physical decap filter
removes the extra reduced NFET. Extraction has zero errors and ERC is empty.

ChipTop's only reported remaining connectivity problem is an **OPEN between
VDDIO and layout net 115**, the shared VDDIO_Q quiet rail identified by the
previous terminal report. This is now a physical supply tie problem rather
than missing device imports or a local comparison-boundary problem. The IO
metal-dimension diagnostic exceptions still prevent a geometric signoff claim.

### Physical quiet-rail repair

The custom 20 um connect-filler schematic ties VSWITCH/VDDIO, VCCHIB/VCCD,
and the ground rails, but explicitly leaves VDDIO_Q separate. The CPF maps
VDDIO_Q to VDDIO, so a physical connection is required. Read-only inspection
of the actual custom filler GDS finds met4 quiet rail y=62.05..66.50 and
main VDDIO rail y=68.00..92.965. A local rectangle
**(9.5,65.5)–(10.5,69.0) um** intersects exactly those two met4 components,
with 1 um^2 contact to each, and reduces the component count from 17 to 16.
It touches no third met4 component and requires no vias.

`vlsi/sky130-quiet-vddio.tcl` adds this single fixed met4 rectangle in
`IO_FILLER_N_0`, guarded by exact master, R0 orientation, and 20x197.965 um LEF
dimensions. The saved DEF places this filler at (204,4990.035) um, giving
global rectangle **(213.5,5055.535)–(214.5,5059.035) um**. A per-session guard
prevents duplicate creation. `hammer-driver` invokes the same helper before
`write_design`, so future P&R streams retain the actual tie. This physical
change still needs Cadence LVS and DRC validation; no virtual connection is
used to make it pass. The source intent is unchanged.

The next CAD attempt (`sky130-nc-pg-export-v2/innovus.log2`) restores the DB
and reaches the tie helper, but stops at its incorrect 200 um height guard.
Both the saved checkpoint's filler LEF and the external custom filler LEF
specify `SIZE 20.000 BY 197.965`, with origin (0,0). The helper now checks
that exact size and reports the observed bbox on a failure. The Tcl regression
uses the correct placed bbox (204,4990.035)-(224,5188.000), also checks that
an unexpected 200 um height is rejected, and retains the same tie rectangle.
The corrected helper is sourced directly by the existing v2 run script.

### Saved-DB re-export loader corrected

The first actual Innovus re-export failed during `read_db` with IMPIMEX-7024:
12 saved SRAM Liberty files differ from the binary timing-constraint snapshot.
The v2 attempt confirms **`read_db -no_binary_constraint` alone does not bypass
this saved-file integrity check**: the same 12 errors occur before restoration.
The generator and existing v2 Tcl now set **`read_db_file_check false`** only
around `read_db -no_binary_constraint`, restoring the previous attribute value
on success or failure and propagating any restore error. This is a diagnostic
export with changed SRAM libraries, not a timing validation of that checkpoint.
The old `-no_timing` option is also removed, because the installed manual
notes it can change macro bus ordering without Liberty definitions. There
is still no timing analysis, placement/routing optimization, or saved-DB write.

### New one-command CAD repair and verification

```bash
bash "$PWD/vlsi/build/sky130-nc-pg-export-v2/run_and_lvs.sh"
```

The revised run opens the saved database, reconnects the NC PG pins in memory,
adds the real single-point quiet-rail tie, and writes separate Verilog, DEF,
and merged verification GDS files under `sky130-nc-pg-export-v2`. It preserves
the original macro stream/map arguments, including the previously selected
PoR view. The checker verifies all NC supplies and compares every retained
logical instance/port connection with the saved source, allowing only the
enumerated NC supply additions and configured physical-only exclusions.
It was tested on the completed source: **84,944 instance connections remain
unchanged**; the original incomplete source is rejected.

After successful export/checks, the wrapper prepares and executes a full-chip
LVS under `sky130-nc-pg-export-v2/lvs/`, using the **actual new GDS and actual
new Verilog**. It does not use the temporary PG-completed source view. Existing
results are preserved. The helper now accepts `--chip-gds` alongside
`--chip-verilog` for explicit regenerated inputs.

All **25** focused tests pass, including Tcl execution with CAD stubs checking
the one rectangle's net, layer, global coordinates, duplicate prevention,
and orientation guard. Source-geometry contact analysis, export-checker
fixtures, shell/Python syntax, and repository diff checks pass. The revised
Innovus/Pegasus run and DRC remain pending in the user's CAD shell.

## Continuation: real P&R PG re-export prepared, step-3 CAD result pending

At this continuation the step-3 comparison report does not exist yet. Pegasus
execution remains unavailable in the sandbox because its controller cannot
open a listening port. The prepared physical-context diagnostic remains:

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-chip-context-step3/run.sh"
```

To replace the temporary completed-Verilog view with an actual Innovus export,
`vlsi/sky130-reexport-nc-pg.py` now prepares a separate CAD-shell run:

```bash
bash "$PWD/vlsi/build/sky130-nc-pg-export/run.sh"
```

It opens the existing `post_write_chiptop_netlist_with_pg_pins` database with
`read_db -no_timing`, verifies all 27 expected instance names and wrapped-pad
masters, and applies exactly 243 explicit `connect_global_net -type pg_pin
-single_inst ... -netlist_override` operations in memory. These command
options were checked against the installed Innovus 23.14 TCR documentation.
It writes only `sky130-nc-pg-export/ChipTop.lvs.v`, using the selected Cadence
library's physical-only exclusions and the current IO filler exclusions.
It refuses an existing output netlist. It does not run placement/routing,
write a GDS, save the modified database, replace the original P&R outputs,
or change timing collateral. The fixed CPF remains the durable configuration
for future P&R initialization; this explicit reconnect is for the saved DB.

The run automatically checks the resulting Verilog for the exact 27 NC pads
and all ten PG assignments, including the existing VDDA assignment. The
checker was tested against the completed diagnostic source and original
incomplete export: the former passes and the latter fails. A stubbed Tcl
execution verified all 243 scoped commands, master guards, and export control
flow; **Innovus itself has not been run here**. Shell/Python syntax and both
repository diff checks pass. The 24 focused regressions pass.

The chip diagnostic helper now accepts `--chip-verilog PATH` so the next
comparison can consume the actual regenerated export without using
`--complete-nc-supplies`. That path must exist; preparation rejects an absent
file and preserves the original source/control snapshots.

## Assembled-chip step 2: hierarchy resolved; CPF/export omission identified

The user completed `sky130-io-lvs-chip-context-step2`. It reports 162 matches,
14 expanded cells, **nine** mismatching cells (seven SRAM types, PoR, ChipTop),
seven parameter-mismatch cells, empty ERC, and **zero extraction errors**.
The four previously failing IO local comparisons are now checked in their
parent. At ChipTop, all **1,500 reduced native FETs correspond**. Ordinary
HV and low-Vt MOS also correspond; all IO poly and metal resistor counts
correspond. The source/layout circuit is retained throughout this expansion.

Three concrete issues explain the remaining non-SRAM/PoR findings:

### 1. CPF omitted the unused NC pad instances

The LVS Verilog contains 44 wrapped pads: 17 functional `iocell_*` instances
have their supply connections, but all **27 `nc_*/iocell`** instances have
only VDDA and omit nine other PG pins. These generate exactly **243** floating
source supply nets, equal to ChipTop's unmatched source-net count. Many
reported terminal differences reference `nc_20|iocell/VDDIO_Q`, etc.

`vlsi/sky130.cpf` put `iocell_*/iocell` in domain IO but omitted `nc_*/iocell`.
The NC cells consequently fell into AO, whose only matching IO rail rule is
VDDA. The corrected selector now includes `nc_*/iocell`. These NC instances
already exist in the synthesized RTL before CPF is loaded, so they can be
selected by the existing power-intent flow. The PG mapping remains the same
as for functional pads: VDDIO/VDDIO_Q/VSWITCH -> VDDIO, VCCD/VCCHIB -> VDD,
and VSSIO/VSSIO_Q/VSSD/VSSA -> VSS. This configuration fix needs power-intent
reload and netlist regeneration before it appears in the actual P&R export.

The next diagnostic uses an explicit **copy** of the current Verilog with
only these 243 missing named ports completed, representing the expected
corrected export. Existing ports, functional instances and saved Verilog are
unchanged. Existing conflicting supply connections are rejected. Tests check
the completion is scoped, idempotent and consistent with the actual CPF rules.

### 2. HV diffusion bypasses the XRES resistor body

The remaining XRES resistor is `X3/X6/X74/R0`, a bent ND resistor. Its extracted
R0 has both terminals on net 1, whereas the source resistor XI132 connects
distinct net207/net110. The stock HV conductor is
`HV_Diff NOT HV_poly`, so it conducts through the resistor body even though
the ordinary diffusion conductor correctly subtracts `diff_res`.

A read-only polygon check of the actual `xres4v2_in_buf` geometry confirms
that the old HV conductor forms **one** connected component through this
resistor, while additionally subtracting `diff_res` leaves **two** terminal
components. The new HV-gap candidate makes exactly that subtraction.

The plain area/width macro computes L=1082.12 um at W=0.29 um. Unioning the
fractured GDS marker reveals **34 inner bends**. The previously tested bend
convention gives `1082.12 - 34*0.29/2 = 1077.19 um`, exactly the source length.
The next candidate applies that macro to diffusion R properties as well as
the HV conductor repair. Both remain experimental pending Pegasus results;
the deck delta is in `vlsi/sky130-io-lvs-hv-diffusion-candidate.patch`.

### 3. Physical decap MOS remains in layout comparison

The only extra reduced ordinary NFET traces through
`ChipTop/X31/X4581(FILL_DECAP8)/X4` to a decap NFET. Source export already
excludes FILL_DECAP8/16 as physical-only cells. The next diagnostic applies
layout black-box-plus-open-filter handling to exactly those two physical
masters, preserving functional transistor models and instances.

### Assembled-chip step 3

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-chip-context-step3/run.sh"
```

This uses `--expand-io-tops --diffusion-properties --repair-hv-diffusion
--complete-nc-supplies --exclude-physical-decaps`. It preserves the same GDS,
CDL, strict ordinary-device tolerances and existing IO metal diagnostic policy.
There are no virtual layout connections or net joins. Only the diagnostic
Verilog copy gains the enumerated NC supply ports. Original chip results and
external PDKs remain untouched. The production configuration change is the
CPF selector; other new controls/deck changes remain candidates.

All **24** focused tests pass. Preparation verifies byte-identical CDL, the
exact HV-gap/bend deck delta, exactly 27 instances/243 added source ports,
idempotent completion, unchanged ordinary MOS tolerances, and physical-decap
scope. Shell syntax and both repository diff checks pass. SRAM and PoR
failures remain visible and deferred.

## First assembled-chip diagnostic: no extraction errors; 35 IO types match

The user completed `vlsi/build/sky130-io-lvs-chip-context/run.sh`. The report
has **162 matching cells, 14 expanded, 13 mismatching, zero not run**, versus
36 mismatching cells in the original run. There are **zero extraction errors**,
empty ERC, and no subtype mismatches. All **93** present Cadence 9T standard
cell types match with the original strict ordinary MOS dimensional checks.
The IO summary is **35 matching types, two expanded, four mismatching**.

The four remaining IO comparison types are:

1. `sky130_ef_io__gpiov2_pad_wrapped`: 31 unmatched source native FETs per
   instance, plus rail mergers through higher layout hierarchy. There are 44
   pad instances in ChipTop. The primary has three reduced native FETs versus
   34 source. Non-native transistor and resistor instance counts correspond.
2. `sky130_fd_io__top_xres4v2`: four unmatched source native FETs and a local
   reported net110/net207 short. All 73 raw diffusion resistors correspond
   and reduce to 44 on each side, but the layout has **no W/L properties**:
   the stock `RES_GENERIC_ND/PD` statements have no property macro at all.
   These missing properties cause its parameter report; relaxing tolerances
   would not calculate them.
3. `sky130_fd_io__top_power_lvc_wpad` and
   `sky130_fd_io__top_ground_lvc_wpad`: local PADISO bindings differ. The
   PADISOL/PADISOR pin labels sit ambiguously on annular metal-R regions and
   bind to nets also labeled SRC_BDY_LVC1/2. A local hcell cut therefore
   assigns clamp terminals to PADISO where the source keeps the distinct
   body/core interfaces. These cells matched in standalone context, but that
   did not validate this chip-level cut. No label or geometry change is yet
   justified from this report alone.

At ChipTop, exactly **1,368 unmatched layout native FETs** occur, with 5,108
raw instances reducing to 1,368. The arithmetic is exact:
`44 * 31 + 4 = 1368`, and `44 * 116 + 4 = 5108`. These are the devices missing
from the two local source comparisons above, promoted into the layout's
higher hierarchy. Their absence at the child is not failed implant/device
recognition. The report's supply shorts explicitly reference higher layout
cells; source circuits must be compared at the same complete boundary before
judging these as actual wiring defects.

The other nine failing comparison types are seven SRAM types, `simple_por`,
and `ChipTop`. They remain visible and are outside the current IO focus.
Compact copies of the four IO report sections are saved under the run's
`focused-reports/` directory to avoid scanning the enormous SRAM report.

### Assembled-chip step 2 candidate

Run:

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-chip-context-step2/run.sh"
```

The new helper flags are `--expand-io-tops --diffusion-properties`. The
candidate adds the four incomplete IO boundaries above to `lvs_exclude_hcell`,
retaining all definitions and all devices for comparison at their parent.
It also adds `cmacro RES_PROPERTIES diff_res np_term/pp_term` to the two
stock diffusion resistor device statements. The dimension macro is a
**candidate**: its calculated geometry must be compared against the source,
including any bent/annular shapes, before production use. The rule delta is
recorded in `vlsi/sky130-io-lvs-diffusion-candidate.patch`.

Validation confirms the CDL is byte-identical to the first assembled-chip
diagnostic, the control differs only in paths and four added hierarchy
exclusions, and the deck differs only in those two property-macro calls.
Ordinary MOS/poly checks remain 0%; the prior IO metal/ESD experimental policy
is unchanged. There are no virtual connections or net joins. Shell syntax
and repository diff checks pass. Original results and external PDKs remain
untouched; no additional production changes were made in this step.

## Step 7: both MATCH without extraction errors; PW repair integrated

Both requested runs report **MATCH**, empty ERC, zero parameter/subtype
mismatches, and **no extraction errors**.

- `pw-context/gnd2gnd_120x2_lv_isosub`: the malformed NW diode, duplicate
  ports, and stamping conflict disappear when the repeated VSS_N fingers
  are virtually connected. Only that declared virtual-connection warning
  remains in extraction; comparison also notes the unused extra substrate
  pin. Strict diode dimensions were retained throughout.
- `reference-pw-context/top_power_lvc_wpad`: the false PW diode and duplicate
  supply-port errors disappear. Extraction warnings are the explicitly
  requested VSSA/VSSIO/VDDIO virtual ties plus ambiguous PADISOL/PADISOR
  labels. Comparison notes unconnected corresponding top pins.

### Integrated production change

`patch_pegasus_pw_diode` in `hammer/technology/sky130/lvs_netlists.py` now
applies the proven PW marker selection to Hammer's cached deck, after the
existing pwell and generic-poly repairs. The generated rule statements are
identical to the user-tested candidate (only the explanatory comment differs).
It preserves the entire recognition polygon whenever the required PW_SD
diffusion exists; NW recognition, device declarations, source circuitry, and
comparison tolerances remain unchanged. The external PDK is not modified.
The guard rejects an unknown or duplicated marker derivation and is idempotent.
All **22** focused tests pass, including cached-deck integration and rule
preservation/revision guards. No virtual ties, resistor filters, metal
dimension omissions, ESD policies, or poly-bend candidates were enabled in
production by this integration.

### Next: assembled-chip physical context

`vlsi/sky130-chip-io-lvs.py` prepares a separate full-chip diagnostic from
the saved Hammer run. The prepared command is:

```bash
bash "$PWD/vlsi/build/sky130-io-lvs-chip-context/run.sh"
```

This experiment uses the **existing merged chip GDS and Verilog**, without
stream regeneration, and adds **no virtual connections or net joins**.
All 24 raw source hashes match the saved manifest. The regenerated CDL has
the same 1,726 subcircuits and is byte-identical to the original after
normalizing only the experimental ESD subtype names.

The candidate combines PW/pwell/poly repairs, datatype-15 metal extraction,
poly-bend geometry, ESD recognition, the five established IO hierarchy
expansions, source-only placeholders, and M1 self-loop/dangling filtering.
All ordinary MOS and generic-poly comparisons remain at their original
**0%** tolerance, including Cadence stdcells/HVL. ESD devices alone get
7% W/1% L. M5 has 1% dimensions; M1-M4 dimensions are omitted. Preparation
checks every source generic metal instance is in an FD/EF IO definition,
so these metal policy exceptions do not extend to standard cells or SRAMs.
Precision resistor, diode, capacitor and other device rules stay checked.

This remains a diagnostic, not full geometric signoff. It will test whether
the real assembled ring supplies the connections assumed in isolated runs.
SRAM/PoR failures are retained; the saved GDS still contains the earlier PoR
selection, and this experiment does not repair that separate issue. Source,
input existence, property-rule uniqueness, absence of virtual ties, shell
syntax, and repository diff checks pass. The original chip run/results remain
untouched. Pegasus execution still requires the user's CAD shell.

## Step 6: false PW candidate confirmed; power-pad comparison matches

The user ran the three requested step-6 cases. Results:

- Isolated `generic/gnd2gnd_120x2_lv_isosub`: MISMATCH, with the known false
  PW diode plus one malformed intended NW diode. Four disconnected p+
  diffusion fingers give four PLUS nets inside one diode recognition body;
  only one of the two intended source diodes is extracted. Repeated VSS_N
  labels also cause duplicate top-port errors and a soft-connect conflict.
- `pw-diode/gnd2gnd_120x2_lv_isosub`: the false PW error is gone. The intended
  NW diode error and all duplicate VSS_N errors are unchanged. This confirms
  the candidate acts on the marker-only PW region without changing NW rules;
  it does not repair the isolated fingers' missing parent connections.
- `reference/top_power_lvc_wpad`: **comparison MATCH**, zero parameter
  mismatches under the diagnostic policy. Both intended PD/NW diodes extract
  and match (2 versus 2), demonstrating that the diode fingers' connections
  are supplied in the parent pad. The five poly resistors reduce to two and
  match with 1% dimensions; the real M5 resistor also matches at 1%.
  The root has 15 reduced devices on each side. Extraction still reports the
  false PW diode and duplicate VDDIO/VSSA/VSSIO top-level supply ports, so the
  comparison MATCH is not a clean extraction result. M3 geometry is unchecked
  under this diagnostic policy.

### Step 7: retain the repair and make standalone assumptions explicit

Two focused cases are ready:

```bash
IO7="$PWD/vlsi/build/sky130-io-lvs-step7"
bash "$IO7/pw-context/sky130_fd_io__gnd2gnd_120x2_lv_isosub/run.sh"
bash "$IO7/reference-pw-context/sky130_fd_io__top_power_lvc_wpad/run.sh"
```

The first uses the unchanged PW candidate and strict original dimensions,
adding only a virtual connection among repeated VSS_N labels in that clamp.
It tests whether supplying the missing parent finger connection restores both
NW diodes and removes the duplicate ports/stamping conflict. It never joins
VSS_N to VSSI or VSUB.

The second adds the same PW candidate to the matching power-pad diagnostic
and virtually joins repeated VDDIO, VSSIO and VSSA bands only within that
primary. It keeps different rail names separate. Neither diagnostic proves
assembled-ring physical continuity, and neither changes production rules.
The generated source and layout inputs are unchanged. Candidate deck and
control differences were checked, as were shell syntax and repository diff
checks. The two extraction reports, not comparison status alone, will decide
whether these standalone context assumptions resolve the remaining errors.

## Step 5 MATCH and next supply-pad extraction diagnostics

The user ran the step-5 `supply-dangling` wrapped-pad comparison. The report
confirms **MATCH: 20 matching cells, two expanded, zero mismatching, zero not
run, zero parameter/subtype mismatches, and zero blackboxed comparison cells**.
ERC is empty. Extraction warnings are the three explicitly requested virtual
supply connections (VSSA, VDDIO, VSSIO).

Together with the controlled step-4 comparison, this establishes that the
two dangling M1 branches account for the last instance mismatches under the
IO topology policy. Both ESD transistors and all native transistors correspond.
The result does not establish physical supply continuity or M1-M4 geometric
dimensions: virtual ties and omitted metal dimension checks remain diagnostic.
No additional production rules have been enabled based on this result.

### False PW-diode recognition in the supply clamp

A read-only polygon check of the original openPDKs FD IO GDS reproduces the
deck's `areaid.de NOT nwell` recognition region in
`sky130_fd_io__gnd2gnd_120x2_lv_isosub`: one polygon, area 124.2464 um^2,
bounds (0.005, 0.005) to (40.165, 17.195). Its overlap with `diff AND nsdm`
is **zero**. These bounds exactly match the saved chip's malformed
`diode_pw2nd_05v5` report. The source contains two `diode_pd2nw_05v5`
devices and no PW diode. The same marker-only region appears in
`top_power_lvc_wpad`, translated to (16.530, 1.285)–(56.690, 18.475).

The new `pw-diode` candidate selects PW marker polygons only when they
interact with `diff AND nsdm`. Selection retains the complete polygon of
a genuine diode with an n+ terminal. It leaves the NW diode recognition,
all device statements, property macros, comparison rules, and source netlist
unchanged. This is a candidate for qualification, recorded in
`vlsi/sky130-io-lvs-pw-diode-candidate.patch`, not a production repair yet.

Step 6 prepares independent runs. Run these three first:

```bash
IO6="$PWD/vlsi/build/sky130-io-lvs-step6"
bash "$IO6/generic/sky130_fd_io__gnd2gnd_120x2_lv_isosub/run.sh"
bash "$IO6/pw-diode/sky130_fd_io__gnd2gnd_120x2_lv_isosub/run.sh"
bash "$IO6/reference/sky130_fd_io__top_power_lvc_wpad/run.sh"
```

The first two compare the same diode source and geometry, under strict
dimensions and physical connectivity, with only PW recognition changed.
Check extraction errors as well as comparison status: the old malformed
device can coexist with a reported comparison match. The third run applies
the corrected IO topology policy to the power pad to expose its remaining
failures; it deliberately retains the original PW recognition for now.
The candidate's rule/device preservation, identical translated source, shell
syntax, and both repository diff checks pass. Fresh Pegasus runs require
the user's CAD shell because the sandbox blocks its listening port.

## Step 4 results: only two dangling M1 branches remain in supply context

Both corrected wrapped-pad runs completed successfully as executions, with
overall comparison **MISMATCH**. Each reports 19 matching cells, two expanded
cells, one mismatching root, zero cells with parameter mismatches, and zero
cells with mismatched instance subtypes. There are no cell-list violations.
Both ESD NFETs now correspond as `MN(NFET_G5V0D10V5_ESD)` (2 versus 2).
All ordinary and native MOS devices also correspond.

`reference` retains the VSSIO/net 9 and VDDIO/net 8 opens. `supply-context`
removes these opens through its explicitly reported virtual supply ties. Its
only two unmatched instances are `X0/X888/R0` and `X0/X889/R0`; there are no
unmatched source instances or nets. M1-M4 dimensions remain unchecked in
these diagnostics, so this is not geometric signoff.

Flattening the extracted `*_pin_xy.spi` through all hierarchy gives 2,052
MOS/R devices, equal to the wrapper's recorded FDC. The remaining resistors
connect inner-pad net 7 to nets 1641 and 1642 respectively. Each far net has
**exactly one primitive terminal**, has no connections to empty shape cells,
and does not reach a wrapper port. Both are dangling branches. The source
`Xipath_q0/XI120/Xggnfet{6,1}_q0/RI8` devices instead have both ends on
VDDIO_Q and are removed by the self-loop filter. Their source sibling RI9
and extracted sibling R1 are also dangling. Endpoint evidence, input paths,
and hashes are recorded in
`vlsi/build/sky130-io-lvs-step4/esd-resistor-trace.json`.

A single additional `supply-dangling` experiment is prepared under step 5:

```bash
IO5="$PWD/vlsi/build/sky130-io-lvs-step5"
bash "$IO5/supply-dangling/sky130_ef_io__gpiov2_pad_wrapped/run.sh"
```

Its GDS, source CDL and candidate deck are byte-identical to step 4. The only
additional electrical control is
`lvs_filter_option RB -device R (res_generic_m1) -source_layout;`.
The installed Pegasus reference defines RB as removal of a resistor with a
floating PLUS or MINUS terminal; it does not join nets. This tests whether
the remaining discrepancy is solely dangling-marker comparison. It is still
experimental: a filtered topology comparison cannot establish the physical
ring supply connections or validate metal resistor dimensions. No production
rules or external PDK files were changed. Generated shell syntax and both
repository diff checks pass; the prior 21 production regressions remain
unchanged by this diagnostic-only helper extension.

## Step 3 results and corrected step 4 diagnostics

The user ran all three wrapped-pad step-3 cases. None is a clean LVS pass.

- `cleanup` is a valid strict comparison. The three previously identified
  self-loop M1 mismatches disappear. Two layout ESD-region resistors remain
  unmatched: `X0/X888/R0` at (11.790, 203.335) and `X0/X889/R0` at
  (11.790, 204.005). VSSIO/net 9 and VDDIO/net 8 still report opens, and
  metal and ESD dimensional differences remain. Native MOS correspondence
  remains resolved.
- `reference` and `supply-context` expose two errors in the diagnostic setup.
  The experimental `esd_nfet_*` source model is classified as **ME**, while
  extraction explicitly uses **MN**. Pegasus infers CDL MOS polarity from
  the model name's first character; its installed `.EQUIV` documentation
  confirms this convention. The corrected optional source models are
  `nfet_g5v0d10v5_esd` and `pfet_g5v0d10v5_esd`, with matching extraction
  subtypes. Production translator behavior is unchanged.
- The root-only `IO_REFERENCE` cell list causes restriction violations when
  unbalanced `hvsbt_nor`, `hvsbt_inv_x1`, and `hvsbt_nand2` expand into it.
  Therefore zero reported parameter mismatches in these two runs does not
  validate the proposed comparison policy. Step 4 removes cell lists from
  these isolated diagnostics and replaces the copied deck's twelve stock
  MOS/R dimension rules with explicit, nonoverlapping subtype rules. All
  IO test cells receive the documented diagnostic policy; this copied deck
  must never be installed for chip signoff. Ordinary MOS retain 1% W/L,
  ESD MOS use 7% W and 1% L, poly/M5 retain 1%, other R dimensions remain
  strict, and M1-M4 dimensions are deliberately omitted.
- `supply-context` no longer reports supply opens or unmatched nets. Its
  remaining unmatched instances are the two MN-versus-ME ESD pairs and the
  two layout R0 devices above. This supports the external supply-context
  explanation, but virtual connections cannot establish physical continuity.
  The model-class and cell-list errors still prevent declaring this a pass.

Two corrected runs are ready, with original step-3 evidence preserved:

```bash
IO4="$PWD/vlsi/build/sky130-io-lvs-step4"
bash "$IO4/reference/sky130_ef_io__gpiov2_pad_wrapped/run.sh"
bash "$IO4/supply-context/sky130_ef_io__gpiov2_pad_wrapped/run.sh"
```

All 21 focused regressions pass, including both experimental ESD polarities
and unchanged default translation. Generated source views differ only in the
ESD subtype names, and the assembled layout is byte-identical to step 3.
Generated dimension rules have no cell lists or duplicate subtype/property
checks. Shell syntax and both repository diff checks pass. Pegasus execution
still requires the user's CAD shell because the sandbox blocks its listening
port. No additional production policy or external PDK modification was made.

## Step 2 results and focused remaining diagnostics

The user ran all three step-2 commands. The new evidence is:

- Both pad comparisons now have **34 versus 34 reduced native FETs, with zero
  unmatched native FETs**. Expanding the inner EF pad resolves that hierarchy
  discrepancy; no native implant recognition change is needed.
- The strict `poly-bends/com_res_weak` result no longer lists any poly resistor
  parameter mismatch. Connectivity remains clean. Only the seven metal-R
  parameter discrepancies remain. This validates the U-body correction on this
  cell; other bent resistor shapes still need qualification.
- `context/gpiov2_pad_wrapped` has 19 matches, two expanded cells, and one
  failing comparison at its root. Moving the ESD boundary allows comparison in
  its parent, but does not make the parent pass.
- All root MOS devices correspond, including the ordinary and native types.
  The unmatched devices are five layout M1 resistors versus one source M1
  resistor. Three layout extras (`X0/R5`, `X0/R6`, `X0/R29`) each have their
  two terminals already tied to the same net. The ESD region supplies the
  remaining two layout extras and one source extra.
- The isolated pad still reports two supply opens: VSSIO versus layout net 9,
  and VDDIO versus layout net 8. The extraction report confirms multiple
  disconnected shapes with each supply label inside the inner EF pad. Whether
  the surrounding ring closes these connections must be checked in ring context.

### Integrated hierarchy policy

The production schematic hook now excludes exactly the five proven incomplete
comparison boundaries listed in `IO_HIERARCHY_EXPANSIONS` in `lvs_netlists.py`.
It keeps all source definitions/devices and checks them in the parent. It
preserves the current primary, and leaves ordinary cells and SRAM bindings
alone. All **21** focused regressions pass. No metal dimension waiver, ESD
tolerance change, self-loop filter, or virtual connection is enabled in the
production flow by this change.

### Step 3 candidates

Six case/variant combinations are prepared under
`vlsi/build/sky130-io-lvs-step3/`. Start with the three wrapped-pad cases:

```bash
IO3="$PWD/vlsi/build/sky130-io-lvs-step3"
bash "$IO3/cleanup/sky130_ef_io__gpiov2_pad_wrapped/run.sh"
bash "$IO3/reference/sky130_ef_io__gpiov2_pad_wrapped/run.sh"
bash "$IO3/supply-context/sky130_ef_io__gpiov2_pad_wrapped/run.sh"
```

`cleanup` combines the established parent comparisons and poly-bend candidate
with `lvs_filter_option RC -device R (res_generic_m1) -source_layout`. RC removes
only a resistor whose two terminals **already** share a net; it never joins
different nets. All dimensional checks stay strict.

`reference` is a separate **topology diagnostic**, not an exact port of Netgen
or a geometric LVS pass. It tests the IO library's comparison conventions:

- The source view preserves `esd_nfet_g5v0d10v5`/`esd_pfet_g5v0d10v5` as
  distinct subtypes. An optional translator flag controls this; production
  behavior is unchanged. Checking the two generated source views confirms
  all nodes, dimensions, units and multiplicities are identical; only those
  subtype names differ.
- The candidate deck separates HV recognition polygons inside `areaid.ed`
  into those ESD subtypes. The observed ESD cell has this marker; an ordinary
  HV inverter does not. `sky130-io-lvs-esd-candidate.patch` records the rule.
  This separation still needs comparison against the remaining IO geometries.
- Only the selected IO primary gets 1% ordinary MOS/poly comparisons and
  7% W / 1% L ESD comparisons, as documented by the installed openPDKs setup.
  The ESD tolerance does not apply to ordinary HV transistors.
- M1-M4 dimensions are **not checked in this diagnostic**; their devices,
  subtypes and connections remain compared. This isolates the known SHORT
  surrogate/annular dimension problem. It is stronger than Netgen's loose
  finite metal tolerance and must not be represented as geometric validation.
  M5 dimensions retain 1% checks.

`supply-context` adds virtual connections only between repeated same-name
VDDIO, VSSIO and VSSA labels in the inner EF pad, with reporting enabled. It
tests the external supply connections assumed by the isolated schematic. It
never joins different supply names. **These virtual connections must not be
copied into chip signoff:** the assembled ring needs real physical continuity.

All these candidates retain full, untruncated reports. The ordinary power-pad
case is also prepared for testing bent resistors, M5 geometry, and the existing
diode extraction failure, after the wrapped-pad results have been examined.
The new shell scripts and translated models were checked locally; fresh
Pegasus execution remains unavailable in this environment. Original step-2
reports and PDK files were preserved.

## User-executed IO results at 04:45 and the next comparisons

The three requested runs completed in the user's CAD shell:

| Run | Result |
|---|---|
| `generic/tk_tie_r_out_esd` | MATCH, clean extraction |
| `metal/com_res_weak` | Clean extraction and matching connectivity; parameter mismatches only |
| `hierarchy/gpiov2_pad_wrapped` | 19 matches, 2 expanded cells, 3 mismatches; no cells not run |

The production generic-poly repair therefore has a fresh passing IO result.
`com_res_weak` extracts exactly **8 poly and 12 metal resistors** on both sides.
Its metal lengths remain about half nominal (0.00507576 versus 0.01 um per
unmerged short), and the U-shaped poly resistor contributes **50.8 versus
50 um**, becoming 62.8 versus 62 um after series reduction.

At the wrapped pad, the remaining native-FET discrepancy is located exactly:
the inner `sky130_ef_io__gpiov2_pad` is missing **31 reduced native FETs**,
while its wrapper has **31 extra reduced native FETs**. The layout originals
at the wrapper number 116, reduced into those 31 groups. This is another
hierarchy boundary across which the layout devices climb. The revised
hierarchy experiment excludes the inner EF pad as well as the earlier AMUX
boundaries, retaining all devices for the wrapper comparison.

The report also identifies a source-only opaque `sky130_fd_io__com_pad`.
Inspection confirms its supplied SPICE is an empty two-pin view with PININFO
comments only. The production translator's explicit placeholder allowlist now
includes this cell alongside `condiode`, subject to the same empty-body and
two-pin guards. All **18** focused regressions pass. No generic missing-master
filter or arbitrary-empty-cell filter was introduced.

The ESD leaf still has a local NWELLRING open plus dimensional differences.
A separate `context` experiment expands that overlapping ESD boundary into
the pad comparison. All property checks remain strict; this experiment does
not apply the ESD tolerance policy to ordinary HV devices.

Offline polygon measurements also confirm the U body's area is 40.64 um^2
at W=0.8 um, with two inside bends. The separate `poly-bends` candidate tests
`L = area/W - bends*W/2`, which gives the source's 50 um for this body. It
changes only the generic-poly macro, leaving straight/precision/metal device
rules unchanged. This is an unvalidated geometric convention, not a fitted
source-netlist edit or a property waiver; it needs checks on other bent IO
resistors before production use.

These three next comparisons are prepared in a new directory. From the
repository root, in the same CAD shell:

```bash
IO2="$PWD/vlsi/build/sky130-io-lvs-step2"
bash "$IO2/hierarchy/sky130_ef_io__gpiov2_pad_wrapped/run.sh"
bash "$IO2/context/sky130_ef_io__gpiov2_pad_wrapped/run.sh"
bash "$IO2/poly-bends/sky130_fd_io__com_res_weak/run.sh"
```

Compare native-FET correspondence first, then whether moving the ESD boundary
resolves its local open, then whether the poly length error disappears while
metal errors stay visible. The six prepared case/variant combinations include
other cross-checks, but only the three above are needed first. The previous
user reports were preserved. A new local Pegasus attempt still fails before
parsing because the execution environment denies its listening socket.

## IO-only work after the PoR placement clarification

The user identified a possible physical PoR placement short and narrowed the
active work to IO library/deck compatibility. PoR and SRAM repairs are deferred.

### Production change

The translation hook now emits the established source-only `condiode` rules
when the translator confirms that `sky130_fd_io__condiode` is an empty,
two-terminal definition. A definition with circuitry, or with a different
interface, is retained without filtering. Its declaration and original sources
are preserved. The manifest records `source_only_placeholders` explicitly.
All **15** focused Sky130 regressions pass, including the three placeholder
definition cases and repeated-hook behavior.

### Independent IO runs

`sky130-io-lvs.py` prepares IO experiments from a saved Hammer run's PDK paths.
It reads the IO SPICE and EF wrapper CDL directly and regenerates a separate
geometric source view; it does not reuse stale chip CDL or edit chip outputs.
The generated source has **504 definitions and no unresolved X calls**.

The wrapped-pad GDS is not self-contained: it references
`sky130_ef_io__gpiov2_pad`, which in turn uses the FD library. The helper merges
the reachable structures from the wrapper, EF, and FD GDS files. Its binary
merge retains complete original structure records, including properties;
all **534** resulting cell records match their source SHA-256 hashes, and
there are no missing references. This repairs the standalone test input,
not a missing import in the existing merged full-chip GDS.

To prepare another suite from the repository root, in the project environment:

```bash
python vlsi/sky130-io-lvs.py \
  --source-run vlsi/build/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop/lvs-rundir \
  --output vlsi/build/sky130-io-lvs-next
```

The output directory must be new. A suite is already prepared at
`vlsi/build/sky130-io-lvs/`. It has 13 IO cases and three variants:

| Variant | Purpose |
|---|---|
| `generic` | Current pwell/generic-poly repairs and the guarded placeholder convention |
| `metal` | Also recognize datatype-15 metal resistors and reproduce the earlier simple L/W macro prototype |
| `hierarchy` | Same metal prototype, with only the problematic AMUX child boundaries excluded in AMUX/pad parent comparisons |

The hierarchy variant keeps standalone native-FET leaf comparisons intact.
For parent comparisons it excludes `gpiov2_amux_drvr_ls` and
`gpiov2_amux_ctl_ls`; at the wrapped pad it also excludes `gpiov2_amux`.
Their devices remain checked in the parent. No global expand-on-error or SRAM
hierarchy changes are made. This targeted policy still needs Pegasus validation.

Start with these runs from the repository root in an ordinary CAD shell:

```bash
source vlsi/build/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop/lvs-rundir/enter
bash vlsi/build/sky130-io-lvs/generic/sky130_fd_io__hvsbt_nor/run.sh
bash vlsi/build/sky130-io-lvs/generic/sky130_fd_io__tk_tie_r_out_esd/run.sh
bash vlsi/build/sky130-io-lvs/metal/sky130_fd_io__com_res_weak/run.sh
bash vlsi/build/sky130-io-lvs/hierarchy/sky130_ef_io__gpiov2_pad_wrapped/run.sh
```

Each run writes `cell.lvs_results` and `cell.lvs_results.cls` beside its
`run.sh`. `bash view.sh` in that directory opens its GUI report. Inspect
extraction errors as well as comparison status. The metal prototype is still
expected to fail geometry comparisons; `com_res_weak` should first recover its
eight poly and twelve metal devices, as in the earlier successful connectivity
experiment. `sky130-io-lvs-metal-candidate.patch` records that prototype under
`vlsi/`; it is not installed by the production technology hook.

### ESD policy and geometry diagnostics

The installed `sky130A_setup.tcl` explicitly explains that ESD FETs have flanged
gates and sets **7% W / 1% L** tolerance for their interpretation. This supports
testing that library convention against the observed 3.068% W / 0.581% L
discrepancy; it does not justify relaxing all HV FETs. The suite's
`esd-reference-policy.pvl` applies those percentages only to
`signal_5_sym_hv_local_5term` as an independent comparison-policy experiment:

```bash
bash vlsi/build/sky130-io-lvs/metal/sky130_fd_io__signal_5_sym_hv_local_5term/run.sh \
  "$PWD/vlsi/build/sky130-io-lvs/esd-reference-policy.pvl"
```

Pegasus cell-specific rules require that ESD cell to remain an hcell. Do not
combine the policy with an experiment that expands that boundary; inspect
`CELL LIST VIOLATIONS` if the boundary disappears.

The openPDKs metal-resistor setup also uses much looser comparison tolerances
than ordinary MOS/poly devices, and many IO metal elements are explicitly
annotated as former `short`s. No loose metal tolerance was ported here: the
short-marker and annular extraction formulas still need resolution, and the
simple macro is known to be wrong for some of them.

For recognition-layer inspection, append the diagnostic overlay in a fresh
run directory, for example the previously unused diode case:

```bash
bash vlsi/build/sky130-io-lvs/generic/sky130_fd_io__gnd2gnd_120x2_lv_isosub/run.sh \
  "$PWD/vlsi/sky130-io-lvs-debug.pvl"
```

It exports `sky130-io-debug.gds`: layers 920-923 are poly/M1/M3/M5 resistor
recognition; 924-927 are PW diode recognition, `PW_SD`, `nsd`, and bulk;
928-929 are native/HV MOS recognition. Check the malformed diode's recognition
region against both required terminal layers. Diagnostic ERC output is
intentional and is not a signoff result.

### Current execution limit

The helper, translated calls, GDS dependencies and byte preservation, and all
78 generated shell scripts were checked locally. The first actual new IO run
(`generic/hvsbt_nor`) again stops before rule parsing because the environment
denies Pegasus's listening socket. Its `console.log` records that failure.
No new IO MATCH result is claimed. The metal, hierarchy, ESD-policy, and debug
experiments require execution in a CAD environment that permits that socket.

## Follow-up: latest 03:46 comparison and integrated repairs

The current saved comparison starts at **03:46:54**, after the converter fixes
described below. It reports **152 matches, 36 mismatches, and 3 not run**.
These are cell types, not individual instances. The breakdown is:

| Library group | Matches | Mismatches | Not run |
|---|---:|---:|---:|
| Cadence standard cells | 93 | 0 | 0 |
| IO (`sky130_fd_io` / `sky130_ef_io`) | 24 | 17 | 2 |
| SRAM hierarchy, openPDKs helper cells, PoR, and ChipTop | 35 | 19 | 1 |

The 19 other mismatches comprise 18 SRAM hierarchy cells and `simple_por`.
ChipTop is not run because lower-level pin mismatches prevent comparison.

### Imports and active deck

The current `pegasuslvsctl` uses the generated `sky130.pegasus.lvs.cdl`, the PAR
`ChipTop.lvs.v`, and `ChipTop_drc_lvs.gds`. The generated CDL manifest lists
**24 source files and 1,726 subcircuits**. Recomputing every source SHA-256 gives
no differences from that manifest. Parsing the generated logical statements
finds **zero unresolved X-instance masters** across the CDL. Missing Verilog
masters are not ignored. Together with the passing Cadence and IO cells, this
rules out a wholesale missing-library import as the explanation for the count.

The configured LVS source is actually
`/scratch/jfx/sky130_release_0.1.0/Sky130_LVS/sky130.lvs.v0.0_1.1.pvl`,
via `example-sky130.yml`, followed by the technology-cache repairs. It is not
the stock `/tools/.../sky130_release_0.0.9/Sky130_LVS/sky130.lvs.pvl`.
Cadence standard cells retain their native CDL dimensions and device names;
openPDKs/SRAM wrapper calls use the separate generated geometric LVS view.

### Repairs integrated in this follow-up

1. **Generic-poly extraction:** `patch_pegasus_generic_poly` in
   `hammer/hammer/technology/sky130/lvs_netlists.py` separates generic marked
   poly from RPM/URPM precision poly, then declares `res_generic_po` using
   `RES_PROPERTIES`. `setup_pegasus_lvs_deck` applies this after the existing
   isolated-pwell repair. Original PDK files remain unchanged. The reproducible
   diff is `sky130-lvs-generic-poly.patch`; the manifest now records required
   deck repairs instead of claiming generic poly remains unsupported.
   The earlier isolated `tk_tie_r_out_esd` experiment below passes with this
   generic-poly rule. Metal SHORT-marker/property experiments remain excluded
   from the production patch.
2. **PoR stream input:** `write_chiptop_drc_lvs_layout` formerly removed the
   configured PoR GDS and silently inserted
   `/tools/C/rohankumar/sky130/stac_tapeout/gds/simple_por_drc_lvs.gds`.
   It now keeps the configured library GDS. An alternate view can be selected
   with `technology.sky130.por_drc_lvs_gds` (default `null`); missing overrides
   fail before stream generation. This makes layout selection explicit; it
   does not establish that the configured PoR itself passes LVS.

   A subsequent geometric comparison of all 16 cells in both files found
   identical cell names and placements, with only two substantive differences:
   the alternate adds the `lv_net` text label at (40, 41.3) on 83/44, and
   removes one poly body, two licon shapes, and one NPC shape from
   `sky130_fd_pr__res_xhigh_po_0p69_S5N9F3`. That resistor cell has 28 poly
   bodies in the configured GDS and 27 in the alternate. This is consistent
   with the saved LVS result's 27 layout versus 28 source precision resistors.
   The alternate is therefore not merely an equivalent verification copy;
   retaining the configured GDS avoids this unexplained resistor deletion.

The PoR change requires regenerating the PAR verification stream. Rerunning
LVS alone continues to use the existing merged GDS. The generic-poly repair
is regenerated into the cached deck on the next Hammer technology setup.

### Remaining discrepancies and their implications

- IO metal resistors need datatype-15 recognition and appropriate geometric
  properties. Merely adding `RES_PROPERTIES` gives wrong annular dimensions;
  the earlier candidate is not suitable for integration as a complete repair.
- `sky130_fd_io__condiode` is an imported, empty source placeholder, with no
  corresponding layout cell. The source-only filtering convention below is
  narrowly applicable to it. No production filter was added here.
- Apparent missing native IO FETs include devices promoted into ancestors.
  The earlier isolated leaf and expanded-chip experiments below distinguish
  this from implant recognition failure. Expansion reduces the number of
  failing comparison boundaries; it does not remove their internal failures.
- The latest SRAM report has **eight layout and eight source devices in
  `sram_sp_cell`**, with matching reduced connectivity. Its dummy PFETs compare
  layout W/L = **0.07/0.05 um** against source **0.14/0.025 um**. The colend
  dummy compares **0.07/0.28 um** against **0.14/0.14 um**. Both have equal
  area but different aspect ratios, so boundary/dummy extraction needs
  inspection before treating these as incorrect functional transistor sizes.
  The converter preserves the supplied dummy connections and dimensions.
- Other SRAM discrepancies are not confined to dummies: `folded_inv` compares
  reduced PFET W **2 vs 2.5 um** and NFET W **1.2 vs 1 um**; `column_mos`
  compares NFET W **1.6 vs 1.2 um** and PFET W **2.25 vs 1.7 um**. Decoder
  and array cells also have pin/connectivity failures. Check matched leaf
  identity and GDS/SPICE agreement before changing models or dimensions.
- `simple_por` includes a source **`CAP_MIM_M3_2`**, while the deck extracts
  **zero** such devices. Its capacitor model is imported; the second-MIM
  device extraction rule is absent. The same report shows `vdd3v3` and
  `vss3v3` assigned to the same layout net, and 27 versus 28 original precision
  resistors. The configured and former override GDS both contain the two
  supply labels at those locations; switching the input alone is not a
  demonstrated fix for that connectivity.
- The malformed `diode_pw2nd_05v5` in `gnd2gnd_120x2_lv_isosub` remains a real
  extraction error even though that cell's comparison reports match.

These failures need extraction/connectivity and collateral checks. Timing
recharacterization with Liberate would not resolve them.

### Validation and rerun limitation

All **12** focused Sky130 regressions pass, including cached-deck selection,
patch idempotence/unknown-deck rejection, precision-rule preservation, and
configured/override PoR stream selection. Both repository diff checks pass.

Fresh full-chip and isolated Pegasus runs were prepared under
`build/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop/lvs-audit-generic-poly/`.
Both attempts stop before rule parsing: this execution environment denies
Pegasus's required listening socket (`Error opening listening port for
Ctrl-Manager ... Operation not permitted`). Thus the new integrated repair
has not received a fresh full-chip Pegasus result. The original `lvs-rundir`
reports and external PDK sources were preserved.

## Earlier 03:09 audit

This audits the 03:09 ChipTop LVS run in
`vlsi/build/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop/lvs-rundir`.
The saved chip reports were not overwritten. Diagnostic runs and deck copies
are under `/tmp/sky130-io-audit`.

## Status and inputs

`ChipTop.lvs_results.cls` reports 151 matched cells, 37 mismatched cells and
3 cells not run, out of 191 compared cell types. All 93 Cadence standard-cell
types match. Of the 43 IO cell types, 23 match, 18 mismatch and 2 are not run.
These are cell-type counts, not instance counts.

The report confirms the intended inputs: `ChipTop_drc_lvs.gds`, the regenerated
PAR `ChipTop.lvs.v`, generated `sky130.pegasus.lvs.cdl`, and the tech-cache
`sky130.pegasus.lvs.pvl`. Missing Verilog masters remain fatal. The IO source
definitions are imported and many IO cells match; this is not a wholesale
failure to import the IO library. The `sky130_ef_io` supply wrappers inherit
several of the problems below from their `sky130_fd_io` children.

## 1. Converter incorrectly treated statistical parameters as multiplicity

In `sky130_fd_io__hvsbt_nor`, XI3 and XI12 specify `m=2 mult=2`.
The previous generated view used M=4, giving a source effective W of 4 um
against 2 um in the layout. The primitive model uses `mult` only in statistical
mismatch expressions, not as the internal MOS multiplier. The installed
openPDKs `libs.tech/netgen/sky130A_setup.tcl` explicitly deletes `mult`.
MIM `mf` is likewise a statistical parameter.

Fixed in `hammer/hammer/technology/sky130/lvs_translate.py`: use `m*nf` for
the supported per-finger MOS calls and `m` for capacitors; ignore statistical
`mult`/`mf`. The scratch full-chip rerun confirms `hvsbt_nor` now matches.
Regression coverage is in `hammer/tests/test_sky130_lvs.py`.

## 2. IO native-R suffixes need the numeric-micron conversion too

The raw IO source has, for example:

```
RI21 P_PAD P_CORE sky130_fd_pr__res_generic_m5 w=2.5385e+08u l=100000u
```

These mean W=253.85 um and L=0.1 um. The previous converter evaluated the
suffix but skipped micron-to-meter conversion, resulting in dimensions a
million times too large. Fixed the prefixed IO native-R conversion; existing
Cadence native devices keep their explicit SI units. Added the actual source
example to the regression test.

An isolated `top_power_lvc_wpad` test with the resistor prototype below now
compares source W=253.85 um/L=0.1 um against extracted
W=253.011 um/L=0.0998756 um. Other resistor properties still fail in this test;
this verifies the unit fix, not a clean pad LVS result.

## 3. The PVL has no generic-poly resistor device

The IO GDS uses poly resistor marker 66/13. The deck selects all marked poly
as precision-resistor poly and removes it from the conductor, but its actual
poly-resistor device rules select only the precision RPM/URPM variants.
There is no generic `res_generic_po` extraction rule.

Consequences include:

* `tk_tie_r_out_esd`: source has one generic-poly resistor; layout has none
  and loses both comparison pins.
* `com_res_weak`: source has eight generic-poly and twelve metal resistors;
  the unpatched deck extracts none of these devices.
* `gpiov2_buf_localesd`, AMUX and supply clamp cells lose their poly resistors.

A scratch prototype separates generic marked-poly bodies from RPM/URPM
precision resistors and adds a two-terminal generic-poly R device using
`RES_PROPERTIES`. With that change **`tk_tie_r_out_esd` matches** in isolation.

## 4. Missing metal SHORT markers and metal L/W extraction properties

The IO GDS uses metal `short` datatype 15 as well as `res` datatype 13.
For example `com_res_weak` has twelve M1 68/15 shapes, corresponding to its
twelve source metal resistors. The deck maps only datatype 13 for metals
1 through 5. The supplied KLayout layer table identifies both datatype classes.

Thus the deck leaves those paths conductive and does not extract the expected
R devices. `top_power_lvc_wpad` has no extracted M5 resistor and a resulting
M3-versus-M5 subtype mismatch. Its source M5 resistor uses a 72/15 marker.

Even when metal R is recognized, the existing metal device declarations lack
L/W extraction macros while the deck globally checks R L/W. This produces
`<missing>`/`<can't calculate>` parameter errors on the supply-pad M3 devices.

The scratch prototype maps datatype 15 into the metal R recognition layers
and attaches `RES_PROPERTIES` to the metal device declarations. This is
**incomplete**: `com_res_weak` gains the expected comparison pins and device
connectivity but has about 49% metal-length errors, and pad M3 annular shapes
give substantially wrong L/W under the simple area/contact-perimeter formula.
Poly geometry also has smaller nominal-versus-extracted differences.
The IO source explicitly comments that some resistors are annular and overlap
between cells. A correct fix needs geometry and reduction rules appropriate
to those markers, validated in the assembled pad context. Blanket removal of
resistors or relaxed global tolerances would hide the problem.

## 5. `condiode` is a source-only placeholder, not an unimported diode

Near the beginning of `sky130_fd_io.spice`, `sky130_fd_io__condiode` is an
empty two-pin subcircuit explicitly described as a placeholder. There is no
matching cell in the IO GDS. Pegasus currently treats its calls as opaque
devices and reports them missing from the layout (eight in AMUX, for example).

The installed Netgen setup's "Schematic cells which are not extractable"
section explicitly ignores `sky130_fd_io__condiode` and `sky130_fd_io__tap_1`.
The Pegasus equivalent for the observed placeholder was verified in scratch:

```
lvs_black_box sky130_fd_io__condiode -source;
lvs_filter_device sky130_fd_io__condiode -open -source;
```

Pegasus reports those source instances as filtered rather than unmatched.
This is a specific library convention, not a reason to ignore unknown masters
or remove actual modeled junctions. No production filter was added in this audit.

## 6. Apparent missing 5 V native FETs are a hierarchy problem

`gpiov2_amux_drvr_ls` and `gpiov2_amux_ctl_ls` appear to lack their two reduced
`NFET_05V0_NVT` devices in the chip comparison. However, the unchanged original
`gpiov2_amux_drvr_ls` GDS **matches in isolation with the existing cached deck**,
including its native FETs. Debug layer output confirms the native gate shapes
are recognized; changing the native implant recognition is not supported by
this evidence.

In the full-chip `ChipTop_pin_xy.spi`, those devices are extracted in ancestors
including `sky130_ef_io__gpiov2_pad_wrapped` and generated `MASCO__H*` cells.
Binding and comparing the leaf as if its devices stayed inside it creates a
cascade of mismatches.

A scratch full-chip run with corrected multiplicity and these controls:

```
lvs_expand_on_device_climbing yes;
lvs_expand_cell_on_error yes;
```

moves the comparisons upward. It has 150 matches, 39 expanded cells, no cells
not run, and two mismatches (including ChipTop). At ChipTop all 1,500 reduced
native FETs match, with zero unmatched native FETs on either side. This is
evidence of hierarchy placement, **not a clean result**: expanded child
failures are checked in their ancestors. Broad expansion also expands SRAM
hierarchy and increases comparison ambiguity. Prefer a deliberate IO hierarchy
policy when integrating this fix. No production hierarchy policy was changed.

## 7. Remaining extraction/property issues

`signal_5_sym_hv_local_5term` has ESD MOS W=5.56569 um versus nominal
5.4 um (3.06833%) and L=0.596512 um versus 0.6 um (0.581333%). The converter
maps the special ESD wrapper to the regular HV MOS subtype; its geometric
property calculation needs validation for the nonrectangular ESD layout.
This is separate from absent SPICE definitions.

The saved chip run also reports one malformed `diode_pw2nd_05v5` in
`gnd2gnd_120x2_lv_isosub` at ((0.005,0.005),(40.165,17.195)), missing its
expected diffusion terminal. That extraction error remains even though the
cell comparison matches. It needs recognition-layer inspection separately.

## Artifacts and integration status

Only the two definite converter corrections above were applied to production
code during this audit; the ten Sky130 LVS tests pass. A new Hammer LVS run
will regenerate the translated CDL using them. The user run's generated files,
original PDK sources, YAML and production cached PVL were left intact.

Scratch evidence:

* `chip-expand/`: full-chip hierarchy/multiplicity experiment.
* `sky130_fd_io__gpiov2_amux_drvr_ls/`: passing isolated native-FET test.
* `sky130_fd_io__tk_tie_r_out_esd/`: passing generic-poly extraction test.
* `sky130_fd_io__com_res_weak/`: resistor prototype, remaining property errors.
* `sky130_fd_io__top_power_lvc_wpad/`: corrected M5 dimensions, filtered
  placeholders and matching device connectivity; remaining geometry errors.
* `sky130_fd_io__gpiov2_amux/`: prototype/placeholder/hierarchy experiment;
  all reduced devices correspond at the root but the run still has connectivity
  and extraction errors, including duplicated labels on disconnected top nets.
  An isolated IO slice cannot stand in for the assembled ring comparison.
* `io-resistor-candidate.pvl`: incomplete scratch-only deck prototype.
* `io-fixed.cdl`: IO-only schematic view with both converter corrections.

Integrate validated deck changes through the existing post-install tech-cache
patch mechanism, retaining `technology.sky130.lvs_deck` as the original input.
The prototype must not replace that cached deck as-is: it is not a passing
or fully validated IO deck.
