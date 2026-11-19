# Sky130 LVS integration generalization

Changes following inspection of the 2026-11-08 15:23:32 DualShuttle report.
These do not establish a DualShuttle LVS MATCH or replace physical DRC.

## SRAM source/hierarchy coverage

`hammer/hammer/technology/sky130/lvs_compat.py` now discovers SRAM22 macro
definitions from the imported bundle and selects the macros referenced by the
current Verilog inputs (or the isolated primary macro). There is no fixed list
of Rocket macro types. Diagnostics without a top-level netlist audit all
imported roots. A missing selected individual source or a root fingerprint
disagreement is an error. The manifest records the selected roots, individual
source paths/hashes and expansion names.

The namespace audit also handles a single selected macro whose local helper
name differs from the aggregate's bare-name definition. Previously it only
recognized families with two different selected signatures. Macro roots and
Cadence standard-cell boundaries remain protected from helper expansion.

**Files edited:** `lvs_compat.py`, the schematic hook in the technology
`__init__.py`, and `hammer/tests/test_sky130_lvs.py`. External SRAM SPICE/GDS
is unchanged.

**Verify:** compare `audit_sram_namespace` with the supplied individual source
files and the current mapped Verilog. The generation audit artifacts are under
`build/sky130-lvs-generalization/`:

- `Sky130RocketConfig-namespace-audit.json`: four selected roots, 62 ambiguous
  families, 310 helper names.
- `Sky130DualShuttleConfig-namespace-audit.json`: five selected roots, 67
  ambiguous families, 365 helper names.

Those are helper counts; the complete control also includes IO expansions.
All selected macro-root circuit fingerprints agree with their individual
sources. These checks do not validate layout connectivity or predict a MATCH.

## Quiet-supply physical ties

`sky130-quiet-vddio.tcl` enumerates every instance of the qualified custom
connected slice, regardless of its name, side, location or orientation.
For each instance it reads the actual VDDIO_Q/VDDIO PG bindings. A pair on
different nets stays separate; an unbound pair causes an error. Same-net pairs
get a local met4 bridge derived from their rectangular LEF pin shapes, using
`get_transform_shapes` to obtain placed coordinates. The nearest adjacent
rail pair is selected. The library-specific 1.5 um maximum gap and 1 um
width/overlap checks remain; unknown geometry is not silently accepted.
Existing covering metal makes reruns idempotent, and a crossing special wire
on another net is rejected. There is no implicit source-net join in LVS.

**Files edited:** `sky130-quiet-vddio.tcl`, `hammer-driver`'s export hook and
the existing Tcl regression in `hammer/tests/test_sky130_lvs.py`. No filler
library GDS/LEF is changed. Fresh chip exports will contain additional bridges
where the placed design logically ties quiet and main supplies.

**Verify:** open the custom connected-slice LEF. VDDIO_Q is local met4
y=62.05..66.50; the nearest VDDIO rail begins at y=68.00. For R0 the bridge
is local (9.5,65.5)-(10.5,69.0), reproducing the original qualified rectangle.
For a rotated instance, transform these corners with its actual placement.
Inspect every created shape's net, rail overlap and DRC. Check that instances
whose two pins bind to different nets receive no bridge. The Tcl logs totals;
the unit regression covers R0/R90/R180/R270 and a separate quiet supply.

This change addresses quiet-VDDIO intent. It does not join VSS or claim that
all other IO-ring supply islands are repaired.

## PoR identity and generated scripts

`hammer-driver` now emits `source` commands for `sky130-quiet-vddio.tcl` and
`sky130-por-vddio.tcl`. New generated P&R scripts load the current repository
hooks rather than embedding copies that become stale. Existing historical
scripts and chip exports are not rewritten; regenerate the P&R script once to
switch an old embedded copy to this mechanism.

Both example CSVs use `IO_FILLER_POR_TAP` for the PoR access instance. The small
Caravel plan keeps its ordinary spacer geometry. In the larger plan the PoR
tap uses the custom connected spacer, while `IO_FILLER_MANUAL_S_3` is restored
to `anchor=S13, placement=before`. The routing Tcl already requires the stable
PoR tap name and accepts either qualified 20 um master.

**Files edited:** `hammer-driver`, `example-sky130-pin-map.csv`,
`example-sky130-pin-map-larger.csv`, and the IO-planner regression. CSV
positions derive from floorplan and LEF inputs; existing PoR library/routing
geometry guards still apply.

**Verify:** the generation-only prepared
`build/sky130-lvs-generalization/par-rundir/par.tcl` sources both repository
hooks. Its `sky130-io-plan.io` places the larger-plan ordinary guard immediately
before S13 and the separate connected PoR tap at offset 9676 um. These are
review artifacts generated with CAD execution intercepted, not new P&R results.

## Plain clamp PADISO hierarchy

The larger padframe uses `vccd_lvc_clamped_pad`, `vssd_lvc_clamped_pad` and
`vddio_hvc_clamped_pad`, rather than the earlier Caravel clamp combination.
Their underlying FD pad cells already have the qualified PADISO extraction
rules, but the EF wrapper expansion policy only named two older variants.
The source kept RIL/RIR inside the new wrappers while extraction promoted
their resistor strips into `ChipTop`.

**Evidence:** in `build/sky130-lvs-generalization/power-debug/layout.cdl`,
count native `res_io_padiso_m3` records inside `ChipTop`: 656. There are 31
VCCD, 23 VSSD and 28 VDDIO clamp instances, giving `(31+23+28)*8 = 656`
strips. The corresponding layout wrappers contain no local PADISO resistors;
`source.cdl` retains two per wrapper. Each source annulus uses four extracted
strips. The four VSSIO clamps retain eight strips each locally and provide a
regression control. The devices are present; the comparison boundaries differ.

`padiso_wrapper_expansions` now follows source X-instance calls and discovers
all EF wrapper ancestors of the four qualified FD PADISO cells. This covers
plain, clamped2, clamped3 and other wrappers using those cells without a
per-design list. Their circuitry remains compared in the parent; no new
device filtering, source dimensions, tolerances or physical geometry change.
An isolated primary is protected from expansion. The compatibility manifest
records the discovered wrappers and their qualified FD pad ancestors in
`padiso_wrapper_expansions` and `padiso_wrapper_roots`. Current policy version
5 rejects reuse of an older compiled control, requiring normal Hammer input
regeneration. An imported `*_clamped[digits]_pad` wrapper that has no recognized
PADISO ancestor raises an explicit qualification error.

**Files edited:** `hammer/hammer/technology/sky130/lvs_compat.py`,
`hammer/tests/test_sky130_lvs.py`, and the raw GDS subset helper in
`sky130-io-lvs.py`. New `sky130-clamp-lvs.py` prepares qualification cases
from the existing chip run. Original PDK GDS/SPICE/CDL is unchanged.

**Verify:** compare EF wrapper X-calls in the original
`sky130_fd_io/cdl/sky130_ef_io.cdl` with the four qualified FD cells listed
in `PADISO_CELLS`. Inspect `padiso_wrapper_expansions` and
`hierarchy_expansions` in a freshly generated `sky130.pegasus.lvs.json`;
all four plain clamp wrappers must appear. In
`build/sky130-plain-clamp-lvs/experiment.json`, inspect the unchanged input
hashes and added hierarchy exclusions. Run:

```bash
bash vlsi/build/sky130-plain-clamp-lvs/run-all.sh
```

This runs four isolated cells, four explicitly labelled standalone cases
assuming same-name supply-port continuity, and a full-chip case with only
the hierarchy exclusions changed. Standalone assumptions do not establish
physical chip connectivity; the chip-context case has no virtual ties.
Each case writes its own reports and extracted layout/source netlists.
The full chip can still mismatch because the SRAM-channel PG opens below
are deliberately deferred. Check where PADISO devices are compared and any
remaining device/property errors, rather than treating a reduced total error
count as closure.

The older standalone `sky130-chip-io-lvs.py --expand-padiso-wrappers` diagnostic
now calls the same discovery function, replacing its separate vdda/vssa list.
There is no design-specific clamp list in either implementation.

All twelve available clamp variants have been audited against the actual
imported source:

| EF clamp variants (omit `sky130_ef_io__` prefix) | Qualified FD ancestor (omit `sky130_fd_io__` prefix) |
| --- | --- |
| `vddio_hvc_clamped_pad`, `vdda_hvc_clamped_pad` | `top_power_hvc_wpadv2` |
| `vssio_hvc_clamped_pad`, `vssa_hvc_clamped_pad` | `top_ground_hvc_wpad` |
| `vccd_lvc_clamped_pad`, `vccd_lvc_clamped2_pad`, `vccd_lvc_clamped3_pad`, `vddio_lvc_clamped_pad` | `top_power_lvc_wpad` |
| `vssd_lvc_clamped_pad`, `vssd_lvc_clamped2_pad`, `vssd_lvc_clamped3_pad`, `vssio_lvc_clamped_pad` | `top_ground_lvc_wpad` |

The qualification generator now defaults to discovering every imported EF
clamp variant. For the complete library, 24 separate cases have been prepared
in `build/sky130-all-clamp-lvs/`: twelve isolated and twelve standalone
same-name supply-assumed checks. `experiment.json` records the exact source
mapping and GDS/CDL/deck hashes. This preparation omitted another chip-context
run, preserving the earlier separate comparison:

```bash
bash vlsi/build/sky130-all-clamp-lvs/run-all.sh
```

Validation so far: 98 LVS/IO-planner tests pass, including each listed variant
alone in the imported wrapper set, preservation of isolated comparison roots,
rejection of unknown clamp topology, stale-policy rejection and unchanged
diagnostic inputs. The earlier four plain clamps each report MATCH both with
and without standalone supply assumptions, with zero parameter/subtype
mismatches. The complete CAD qualification finished on 2026-11-08 at 23:36:11:
ten variants MATCH with and without standalone supply assumptions. Both
`vccd_lvc_clamped2_pad` and `vssd_lvc_clamped2_pad` MISMATCH in both modes,
with zero parameter or subtype mismatches. Source hierarchy coverage alone
does not establish layout MATCH.

The installed `vccd_lvc_clamped2_pad` layout connects the diode pair between
VSSIO and VSSD, and all 413 NFET fingers' bodies to VSSD. Its CDL instead
puts the diode pair between VSSA and VSSIO and splits the clamp bodies between
VSSIO (204 fingers) and VSSD (209). The VCCD plain/clamped2 CDL calls are
identical despite their different physical overlays.

The installed `vssd_lvc_clamped2_pad` GDS has only the base pad reference:
both the pad overlay and clamp overlay are absent. This omission is also
visible in the installed and custom-source Magic files. Additionally its CDL
misorders the OGC_LVC/PADISOL/PADISOR bindings as PADISOL/PADISOR/VSSA,
unlike the correctly ordered plain wrapper. Its extracted devices remain
on disconnected internal nets even with standalone supply assumptions.
These are collateral discrepancies independent of the chip's SRAM PG gaps.

`sky130-clamped2-lvs.py` prepares three diagnostic candidates, preserving the
completed qualification and all original PDK files:

```bash
bash vlsi/build/sky130-clamped2-lvs-repair/run-all.sh
```

Two cases change only the clamped2 CDL bindings; the third also adds the
missing VSSD pad-overlay and clamp-overlay references, copied as original
GDS SREF records from the existing VSSD plain and VCCD clamped2 wrappers.
The candidate CDL follows the installed VCCD clamped2 geometry: both clamp
returns on VSSD and the diode pair on VSSIO/VSSD. This differs from the
original clamped2 CDL comments. A MATCH alone establishes consistency of
the candidate views; the independent source/history check below establishes
which supply-domain topology the library intended.
The candidate CAD runs finished at 23:48:18 on 2026-11-08: VCCD source-only
MATCH, VSSD source-only MISMATCH, and VSSD source-plus-overlays MATCH.
Both matching cases have zero parameter/subtype mismatches and no blackboxed
types. This isolates the missing VSSD physical overlays from the CDL issues.
These historical candidates preserve the original comparisons; the subsequent
production integration below uses the same checked repairs. External libraries
remain unchanged, and no virtual ties are added.

### Independent clamped2 intent audit

The named-port Verilog independently resolves the apparent intent ambiguity.
In the original local `sky130/custom/sky130_fd_io/verilog/sky130_ef_io.v`,
the VCCD clamped2 module starts at line 1141 and the VSSD clamped2 module
at line 1191. Both explicitly bind:

| Base pad port | Intended clamped2 connection |
| --- | --- |
| `DRN_LVC1`, `DRN_LVC2` | `VCCD` |
| `SRC_BDY_LVC1`, `SRC_BDY_LVC2` | `VSSD` |
| `BDY2_B2B` | `VSSIO` |
| `P_CORE` / `G_CORE` | `VCCD` / `VSSD`, respectively |

The upstream [Verilog source](https://raw.githubusercontent.com/RTimothyEdwards/open_pdks/master/sky130/custom/sky130_fd_io/verilog/sky130_ef_io.v)
contains the same named-port wiring. This agrees with both candidates and
with the existing VCCD clamped2 GDS. The conflicting CDL comments describe
the plain clamp topology and are not a sound basis for changing the candidates.

Local Git history independently confirms the missing VSSD overlays:

- `e8de007a437056b21a0393a709eeea2e90b303c5`, 2021-06-17, explicitly corrected
  the clamped/clamped2 layout naming while retaining the electrical views.
  Its VSSD clamped2 Magic wrapper contains the base ground pad, the VSSD pad
  overlay and the `lvc_vccd_overlay` clamp overlay.
- `081c79415c0de198543defd8b09e9f382ca5a1d3`, 2022-11-02, removed both overlay
  references from that wrapper during the IO overhaul. The intended named-port
  Verilog wiring remains present.

The read-only audit `build/sky130-clamped2-lvs-repair/audit-intent.py` checks
every nonempty named Verilog connection against the candidate CDL for both
cells. It also checks that the candidate VSSD GDS reference set and placement
transforms exactly reproduce the pre-overhaul Magic wrapper. Both checks pass.
Verilog's empty `OGC_LVC()` port is explicitly excluded as intent evidence;
the candidate retains the existing CDL convention for that port.

`intent-audit.json` records the local repository HEAD
`7c71dc10f76cf49eeb9664811957bd1a94a81c7e`, clean status of these source files,
the Verilog SHA256, all checked connections, and the historical transforms.
`history-e8de007.patch`, `history-081c794.patch` and `history-cdl-blame.txt`
preserve the evidence beside the completed CAD results. Reproduce with:

```bash
PYTHONPATH=vlsi/hammer .conda-env/bin/python \
  vlsi/build/sky130-clamped2-lvs-repair/audit-intent.py
```

The source/history evidence supports the guarded CDL corrections and VSSD
overlay restoration integrated below. The isolated MATCH is not an ESD
performance characterization.

### Production integration of the clamped2 repairs

`hammer/hammer/technology/sky130/io_collateral.py` now applies the repairs in
technology setup when `technology.sky130.lvs_mixed_library_compatibility` is
enabled. It recognizes the original and already-corrected cell revisions,
rejects unfamiliar modified cells, and leaves unrelated library cells intact.
CDL guards cover each complete affected definition. GDS guards cover the
affected wrapper and the overlay/template cells, ignoring structure timestamps
but retaining geometry, labels, reference transforms and properties.

`SKY130Tech.post_install_script` creates technology-cache copies under
`io-collateral/sky130_ef_io.cdl` and `io-collateral/sky130_ef_io.gds`, then
redirects every matching corner/library entry. Both normal P&R stream-out
and schematic translation therefore use the corrected views. The GDS patch
copies the two qualified SREF records verbatim; it does not redraw polygons.
`sky130.io-collateral.json` records original and generated file hashes,
cell revision hashes and the individual pin/reference changes. Repeated
preparation is idempotent and detects tampering with a reused cached view.

The installed PDK is read-only. The source patch
`sky130-clamped2-open-pdks.patch` separately repairs the upstream CDL and
Magic wrapper source so a future upstream GDS rebuild retains these changes.
It was checked by applying it to a temporary copy, not the installed PDK.
Hammer uses the cached GDS transformation and requires no Magic invocation.

Verification completed for this integration:

- 106 LVS/IO-planner/collateral regressions pass.
- Fresh normal Hammer P&R generation merges the corrected cached EF GDS;
  fresh normal LVS compilation imports the corrected cached EF CDL.
- Both translated clamped2 circuit fingerprints equal the earlier isolated
  MATCH candidates. The generated VSSD GDS cell is byte-identical to the
  matching repaired candidate.
- All 59 checked met3/met4/met5 supply-pin rectangles in each clamped2 cell
  are covered by the generated GDS metal. No LEF change was required for
  those declared pin shapes. This geometric coverage check does not replace
  routing, obstruction or physical DRC checks.

`build/sky130-clamps-integrated/experiment.json` records qualification inputs
from the actual technology cache and fresh compiled source. The diagnostic
generator's `--technology-cache` option verifies that its compiled source
consumes the same cached CDL and assembles its GDS from the cached EF view
plus the original FD dependencies. The separate run contains twelve isolated
and twelve explicitly supply-assumed LVS cases. A paired baseline/repaired
VSSD macro DRC comparison has no IO-cell exclusion (the normal technology
DRC hook otherwise excludes `sky130_ef_io__*`). Run in the CAD shell:

```bash
bash vlsi/build/sky130-clamps-integrated/run-all.sh
```

`run-lvs.sh` and `run-drc.sh` can also be run separately. The DRC summaries
are `drc-baseline/cell.drc_results` and `drc-repaired/cell.drc_results`;
`lef-pin-coverage.json` records the pin-area checks. The CAD run completed on
2026-11-09: all 24 LVS cases MATCH. The baseline and repaired macro DRC each
report seven results; both runs have no excluded cells. The result types differ
(density checks and `x.prBndry`), so this is not a claim of DRC closure.
Existing chip GDS files have not been re-exported. A design
that instantiates the repaired VSSD clamped2 cell needs fresh physical exports
to contain the restored geometry, followed by chip LVS/DRC. Synthesis is not
required for these cell-view changes. The current example CSV plans use plain
or clamped3 cells, so their placed instances receive no clamped2 geometry change.

## No-IO source preparation and configured PoR views

`use_io_cells: false` controls the driver's chip IO hooks, independently of
the mixed-library extraction profile used for SRAMs and Cadence/openPDKs
comparison. Previously source preparation required annotated IO SHORTs and
all four PADISO definitions whenever that profile was enabled. A reduced
import with no IO could therefore fail even though no IO instances existed.
The technology currently imports IO collateral when installed, regardless
of this flag; that incidental import could conceal the unconditional check.

Source preparation now accepts absent or partial IO libraries. Its classifiers
continue to validate every applicable PADISO definition and annotated SHORT
that is present; unrelated missing IO definitions are no longer required.
The manifest records `imported_padiso_cells`. The profile stays enabled for
the core/SRAM corrections. Regressions cover no IO, one pad family, a subset
of pad families, malformed imported pads, and the no-IO schematic hook.

The PoR GDS override branch, default/type setting, and override-specific tests
were removed. `write_chiptop_drc_lvs_layout` now merges the configured GDS
libraries and input ILMs directly. The configured CARAVEL PoR stream regression
is retained. Original run snapshots and historical audit notes are preserved;
they can still mention the retired setting. New P&R generation must be used
to update previously emitted Tcl scripts.

## Extra ground connection: confirmed PG islands

The saved Rocket and DualShuttle P&R configurations have **identical values
for all 67 power/ground-related settings**, including the complete embedded
CPF, supply mapping, selected SCL and strap recipe. The record is
`build/sky130-lvs-generalization/power-config-comparison.json`. There is one
declared ground net, VSS. No extra ground domain was introduced.

Their physical implementations differ: padframe size and placement, plain
versus Caravel clamp variants, macro set and routed topology. Thus the same
power recipe does not establish the same physical connectivity.

The subsequent power-debug run dumped the actual precompare layout/source
netlists. In `power-debug/layout.cdl:4`, CLKBUFX4 has ports
`A VDD VSS Y 15`; its NFET source terminals connect to VSS and bodies connect
to 15. In `source.cdl:4`, both connect to VSS. The representative body port is
therefore an NMOS substrate/body connection, not a new intended ground supply.

At the parent level, 15,536 of 15,587 CLKBUFX4 instances connect both ports to
global VSS, but 51 do not. Auditing the 44 affected Cadence cell types finds
890 instances whose VSS/body bindings differ, with 879 also disconnected from
global VDD. `power-debug/ground-connectivity-audit.json` records every instance,
its source correspondence, location and extracted nets. The passing Rocket
dump has no split body port on CLKBUFX4. A few physically disconnected instances
force a common cell definition to expose its body separately, propagating the
extra-pin failure across that cell type.

For example, `layout.cdl:1144067` contains:

```text
X192/X233 X192/23844 X192/23845 1154738 1145988 VSS CLKBUFX4
```

This is source instance
`system/tile_prci_domain_1/element_reset_domain_shuttle_tile/buffer/nodeOut_a_q/ram_ext/CTS_ccl_a_buf_03807`,
placed at DEF (5234.340,10726.280), orientation S. Its VSS pin is on local net
1154738, its body is on global VSS, and its VDD is on local net X192/23845.
The report documents these exact mismatches around line 156456.

The DEF independently locates a physical PG gap at this instance:

- The buffer lies in the channel between two `sram22_64x22m4w22` macros.
  Their body bboxes are x=4932.075..5218.955 and 5260.355..5547.235,
  y=10618.400..10812.120; PG keepouts shorten the usable M1 row rails further.
- VSS M1 at y=10730.420 has centerline endpoints x=5227.860..5251.400,
  width 0.400 (DEF line 16592956).
- The nearest VSS M2 stripe is x=5225.830, width 0.600 (line 16599368).
  Even including half-width end extensions, its edge stops 1.53 um before
  the M1 island starts. The VDD rail misses its M2 stripe similarly.
- There are **zero M1/M2 via centers** in the window covering these complete
  M1 fragments: (5220,10720)..(5255,10740). Higher-layer PG mesh is present.

`power-debug/pg-window-audit.json` records the exact DEF statements and the
[diagram](build/sky130-lvs-generalization/power-debug/pg-island-example.svg)
shows the geometry. The existing uniform M2 same-net pitch is 36.8 um; short
M1 fragments left between SRAM keepouts can miss the grid entirely. The
`connect_core_stripes_to_ring` hook only repairs met4/met5 floating stripes,
so it does not repair these orphan M1 rails.

The bulk-stamping warning around extraction-report line 7735 is consistent:
SCONNECT selects global VSS for the common pwell while rejecting the isolated
local tap/rail nets. This is not a reason to hard-connect them in the LVS deck.
The representative case is a real P&R PG-connectivity defect. A repair must
connect orphan M1 fragments into the upper PG mesh or prevent them through
channel-aware grid/placement planning, followed by connectivity, DRC and LVS
checks. This investigation has not yet repaired those physical islands or
proven that all other DualShuttle mismatches have the same cause.

The exported DEF already contains the PoR VDDIO via at (9689.2,177.89); the
remaining chip-level PoR VDDIO mismatch therefore also requires tracing the
connected rail, rather than blindly repeating the old missing-via diagnosis.

Verification completed: 84 LVS/IO-planner tests passed; both real-netlist SRAM
audits passed; fresh mainline P&R input generation passed without CAD execution.
The original failing report and exports remain preserved.

The separate diagnostic in `build/sky130-lvs-generalization/power-debug/` keeps
the failing run's inputs/policies and adds layout/source netlist dumps. From
the repository root, run in the CAD shell:

```bash
bash vlsi/build/sky130-lvs-generalization/power-debug/run.sh
```

The CAD-shell run completed on 2026-11-08 at 16:12 and supplied the netlists
used above. It reproduces the original 104 matched / 68 mismatching / 11
expanded types. Local CAD execution remains unavailable due to the
control-manager listening-port restriction; the analysis scripts themselves
read existing netlists/DEF and do not run CAD or modify the design.

## Preventing orphan row rails with PG-aware SRAM spacing

`hammer-driver` now derives horizontal SRAM spacing from the effective
`par.generate_power_straps_options.by_tracks` configuration and technology
stackup. It uses Hammer's own `specify_power_straps_by_tracks` calculation
with a geometry sink, avoiding a separate width/pitch formula and avoiding
side effects on the tool's PG-generation state. The calculation includes
the selected power-net weights and leaves the generated PG grid unchanged.

For the current `example-sky130-larger.yml` settings:

| Quantity | Value |
| --- | --- |
| M2 strap width | 0.60 um |
| VSS/VDD edge spacing | 0.32 um |
| Complete pair span | 1.52 um |
| Same-net/group repeat period | 36.80 um |
| SRAM placement halo per edge | 8.28 um |
| Row-rail end allowance per edge | 0.92 um (two placement-site columns) |
| New minimum horizontal macro gap | 57.04 um |
| Retained minimum vertical gap | 41.40 um |

A channel must accommodate the repeat period plus a complete VSS/VDD pair
to be independent of the grid's phase. Space sufficient for a single 0.6 um
wire does not ensure either supply stripe actually falls in the channel.
The minimum horizontal gap is rounded upward to the placement-site grid:

```text
2 * max(placement halo, M2 blockage spacing)
+ M2 group period + complete pair span + 2 * row-end allowance
= 56.72 um before rounding -> 57.04 um
```

After the two halos and allowances, the new gap has 38.64 um usable span,
exceeding the 38.32 um required for one complete pair at arbitrary phase.
The old 41.4 um gap could miss both supplies. The end allowance exceeds the
approximately 0.65 um rail-center trimming seen at each edge of the audited
island. It is a conservative placement margin, not a measured DRC rule.
The default 8.28 um halo remains the pin-escape reservation, and the actual
Tcl halo and channel calculation use the same value.

The cold placement constraint now emits
`-min_space_to_macro {57.04 41.40}` and
`-honor_strict_spacing_constraint true`. The existing core spacing and
forbidden-spacing/abutment policy are retained. The obsolete comment about
a Rocket-specific route-halo exception was removed; the actual behavior
remains route halo met1..met2 and PG blockage met1 for all SRAM22 instances.

Both cold and warm paths call `sky130_check_sram_channels` from
`sky130-sram-channels.tcl` before standard-cell placement continues. It
checks actual macro bboxes with overlapping vertical extents. Positive
channels narrower than the derived minimum are rejected if the two placement
halos leave a standard-cell corridor. Fully halo-covered gaps/abutments are
allowed. It reports instance pairs and measured gaps. A cached placement
with the old narrow channels now fails with instructions to remove the SRAM
hardmacro-constraint overlay and rerun macro placement; it is not silently
accepted or moved behind the user's back.

Verification: 112 tests pass, including changed grid settings, arbitrary
grid-phase samples, cold/warm generation and Tcl checks that reject the old
41.4 um gap. Fresh normal P&R input generation passed without CAD execution.
Review artifacts are `build/sky130-sram-channel-fix/par-rundir/par.tcl` and
`sram-pg-channel-plan.json`. Each new P&R run writes the plan JSON into its
own run directory.

From the repository root, rerun P&R from floorplanning using the existing
synthesis result, without a cached SRAM placement overlay:

```bash
make -f vlsi/build/chipyard.harness.TestHarness.Sky130DualShuttleConfig-ChipTop/hammer.d redo-par
```

Remove any `HAMMER_EXTRA_ARGS=-p ...sram_macro_placement.yml` selection for
that run. The current saved `par-input.json` has no hardmacro coordinates;
the extra cache overlay would be what selects the warm path. No synthesis
or Makefile changes are required for this hook change.

The old routed design is not physically repaired by editing a placement
constraint. New P&R, special-net connectivity checks, DRC and LVS are still
required. In the new Innovus database, run:

```tcl
check_connectivity -type special -nets {VDD VSS} -out_file core-pg-connectivity.rpt
```

Inspect M1/M2 via coverage near the previously affected instance paths using
their new coordinates. The spacing constraint prevents the demonstrated
grid-phase failure; it does not by itself prove every PG island is gone.
