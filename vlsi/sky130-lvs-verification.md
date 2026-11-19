# How to independently verify the Sky130 LVS changes

Companion to [sky130-lvs-summary.md](sky130-lvs-summary.md). Each numbered entry
matches a row in that summary. Paths/line numbers were inspected on 2026-11-08;
use the supplied search strings if later edits move the lines.

For the subsequent dynamic SRAM/quiet-tie integration changes, see
[sky130-lvs-generalization.md](sky130-lvs-generalization.md). Historical run
artifacts below retain their original instance names and expansion counts.

The important distinction is between an extraction defect, a physical open, and
an explicit comparison policy. Geometry and a before/after netlist can establish
the first two. A MATCH under a tolerance does not independently prove that the
tolerance is appropriate; the SHORT, PADISO and ESD entries state that limit.

## Files and viewing conventions

Repository implementation abbreviations used below:

| Label | File |
| --- | --- |
| N | [lvs_netlists.py](hammer/hammer/technology/sky130/lvs_netlists.py) |
| T | [lvs_translate.py](hammer/hammer/technology/sky130/lvs_translate.py) |
| C | [lvs_compat.py](hammer/hammer/technology/sky130/lvs_compat.py) |
| H | [Sky130 technology hooks](hammer/hammer/technology/sky130/__init__.py) |
| D | [project hammer-driver](hammer-driver) |

For the commands below, run from the repository root and define:

```bash
LVS_ROOT="$PWD"
LVS_VLSI="$LVS_ROOT/vlsi"
LVS_BUILD="$LVS_VLSI/build"
LVS_PROJECT="$LVS_BUILD/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop"
LVS_RUN="$LVS_PROJECT/lvs-rundir"
LVS_RAW="/scratch/jfx/sky130_release_0.1.0/Sky130_LVS/sky130.lvs.v0.0_1.1.pvl"
LVS_DECK="$LVS_PROJECT/tech-sky130-cache/sky130.pegasus.lvs.pvl"
LVS_CDL="$LVS_RUN/sky130.pegasus.lvs.cdl"
LVS_CTL="$LVS_RUN/pegasuslvsctl"
LVS_OPEN="/scratch/jfx/open-pdks/sky130/sky130A"
LVS_IO="$LVS_OPEN/libs.ref/sky130_fd_io"
LVS_IOSP="$LVS_IO/spice/sky130_fd_io.spice"
LVS_SRAM="/scratch/jfx/sram22_sky130_macros"
LVS_POR="/scratch/jfx/cadence-skywater-130-pdk/CARAVEL/simple_por"
```

In the prose, `build/...` means `vlsi/build/...` from the repository root.
`sky130_fd_io.gds` means `$LVS_IO/gds/sky130_fd_io.gds`; use the separate
EF library/wrapper files when named. Notation such as `$LVS_RAW:658` means
line 658 of that file, not a literal filename to pass to the shell.

Open original library GDS in KLayout or Virtuoso, select the named leaf cell,
and measure in micrometers. Leaf coordinates below are local, not transformed
chip coordinates. Enable the drawing **and marker** datatypes: drawing alone
cannot show resistor/ESD recognition intent. Useful raw layers are:

| Geometry | GDS layer/datatype |
| --- | --- |
| Diffusion / tap | 65/20, 65/44 |
| Poly / poly-resistor marker | 66/20, 66/13 |
| Nwell / deep nwell | 64/20, 64/18 |
| n+ / p+ implants | 93/44, 94/20 |
| HV identifier / diffusion-resistor marker | 75/20, 65/13 |
| Precision-poly identifiers | RPM 86/20, URPM 79/20 |
| ESD identifier | 81/19 (`areaid.ed`) |
| Diode identifier | 81/23 (`areaid.de`) |
| Local contact / local interconnect / NPC | 66/44, 67/20, 95/20 |
| Metal1..5 drawing | 68..72 / 20 |
| Metal1..5 resistor / SHORT markers | 68..72 / 13 and /15 |
| Via3 / via4 | 70/44, 71/44 |
| MIM1 / MIM2 marker | 89/44, 97/44 |

For Boolean operations, copy shapes into a scratch view or use the existing
geometry-audit JSONs. Do not save edits into the original libraries. Derived
layers such as `pwell_all`, `nSourceDrain` and `np_term` require extraction or
reproducing the deck Booleans; they are not raw GDS layers.

## Collateral change inventory

| Original input/collateral | What the LVS work actually writes |
| --- | --- |
| `$LVS_RAW` | A patched **cache copy**, `$LVS_DECK`, plus `sky130.pegasus.lvs.policy.json`. The original PVL is unchanged. |
| Original IO, HVL, primitive, SRAM and Cadence SCL SPICE/CDL | Generated `$LVS_CDL` and `sky130.pegasus.lvs.json`. Original source libraries are unchanged. |
| Stock HVL SPICE containing the custom level-shifter name | Generated `$LVS_RUN/sky130_fd_sc_hvl.lvs.spice`, removing only the overridden definition. |
| `$LVS_POR/simple_por.spice` | Generated `$LVS_RUN/source_overlays/simple_por.spice`, correcting one resistor length. The original remains at 1.36. |
| Original IO/SRAM/PoR GDS and LEF | No geometry edit for the extraction/source fixes. Isolated-test GDS subsets and diagnostic derived-layer GDS are generated separately. |
| Chip physical design | NC PG binding changes in the design, one quiet-supply metal rectangle and one PoR supply via; newly exported chip GDS/DEF/Verilog. These are actual design edits. |
| Project configuration/flow | `sky130.cpf`, `hammer-driver`, the Sky130 technology hooks/defaults/types, `example-sky130.yml`, and the helper/patch files named below. |

The custom CARAVEL PoR, modified M1-access level shifter and custom quiet-supply
filler under `/scratch/jfx/cadence-skywater-130-pdk` already existed. The LVS work
selects/consumes them; it did not author or overwrite those external libraries.
No new Liberate characterization or Liberty file was produced by LVS closure.

<a id="a0"></a>

## A0. Establish the inputs and missing-import baseline

**Inspect:** the first 30 lines of `ChipTop.lvs_results.cls`, `$LVS_CTL`, and
`$LVS_RUN/sky130.pegasus.lvs.json`. The report names the actual layout, source
and rules files. The manifest lists 24 source entries and 1,726 circuit
definitions, including sources reached through includes.

```bash
sed -n '1,30p' "$LVS_RUN/ChipTop.lvs_results.cls"
rg -n 'layout_path|schematic_path' "$LVS_CTL"
```

Read the manifest's `sources`, `cell_sources`, `converted_calls`,
`source_overlays` and `compiled_cdl_sha256`. Source hashes identify the consumed
revision; for the PoR overlay compare the recorded `original_path` hash to its
`original_sha256`, not to the overlay hash. Read T's dependency checking at the
end of `translate_libraries`: unresolved X masters are rejected. This supports
the conclusion that repeated failures were not a wholesale missing IO/SRAM
import. It does not prove every device translation is correct; B1 checks that.

**Edited/generated files:** T, H's schematic hook, generated CDL/manifest/control.
No external library was added or edited to conceal missing masters.

<a id="a1"></a>

## A1. Isolated pwell bulk

**Inspect:** `$LVS_RAW:658` versus `$LVS_DECK`, searching `pwell_all_2`.
The old union excludes `ptub`; the new union includes `ptub` while also removing
`nwell_cut_dnw` from the background substrate region. This keeps an isolated bulk
region without joining across the guard ring.

Open `$LVS_SRAM/sram22_64x24m4w8/sram22_64x24m4w8.gds`. Display deep nwell,
nwell, diffusion and poly. To inspect the actual derived coverage, run two
separate debug extractions of this macro with the same source/control and only
this deck change, supplying [sky130-lvs-debug.pvl](sky130-lvs-debug.pvl) after
each deck. Open the resulting `sky130-bulk-debug.gds` with the original GDS:
900/0 is bulk, 906/0 is ptub, and 907/0 is recognized NMOS outside bulk.
The recorded original audit found 11,480 bulk-gap regions and 991 malformed-device
entries; the repair removed both. Check that isolated and background bulk still
form separate regions. Early `/tmp/sky130-lvs-audit` outputs are no longer
available in this workspace, so these early counts require a fresh debug run
for independent reproduction; [the notes](sky130-lvs-notes.md) retain the record.

**Edited/generated files:** N:76, H `setup_pegasus_lvs_deck`,
[isolated-pwell patch](sky130-lvs-isolated-pwell.patch), generated cache PVL.
Original SRAM GDS/SPICE and the external raw PVL were unchanged.

<a id="a2"></a>

## A2. Missing generic-poly extraction, including tk_tie_r_out_esd

**Inspect:** `$LVS_IOSP:6997`: this cell has one `res_generic_po`, W=0.5,
L=10.2 um. Open `sky130_fd_io.gds`, cell
`sky130_fd_io__tk_tie_r_out_esd`, and display 66/13 over 66/20. Check that its
marked body exists and is not an RPM/URPM precision resistor.

At `$LVS_RAW:706`, all marked poly is selected/removed from the conductor,
but there is no `device R (res_generic_po)` declaration. Search the whole raw
deck to confirm that absence. In `$LVS_DECK`, find `generic_poly_resistor` and
the corresponding device declaration. The passing isolated report is
`build/sky130-io-lvs/generic/sky130_fd_io__tk_tie_r_out_esd/cell.lvs_results.cls`.
Compare raw device counts with the source rather than just its MATCH banner.

**Edited/generated files:** N:100, H's cached-deck setup,
[generic-poly patch](sky130-lvs-generic-poly.patch), cache PVL. **The
tk_tie_r_out_esd GDS and source were not edited.**

<a id="a3"></a>

## A3. Metal SHORT marker recognition and missing properties

Open `sky130_fd_io.gds`, `sky130_fd_io__com_res_weak`, and its `tk_em1s`/
`tk_em1o` children. Display metal1 68/20 and markers 68/15; repeat for the
relevant other metal layers. Compare the twelve source metal resistors reached
through this cell's helper instances with the marker bodies. `$LVS_IOSP:958`
contains the parent calls.

Search the raw PVL for metal mappings with datatype 13 and datatype 15; the
missing 15 mappings explain why expected devices were absent. At raw lines
683..687, resistor devices also lack a property macro. The repaired deck maps
the SHORT markers and attaches properties. The isolated
`build/sky130-io-lvs/metal/sky130_fd_io__com_res_weak/cell.lvs_results.cls` should
show eight poly and twelve metal devices before reduction. Parameter failures
in that intermediate run are intentional evidence for B5, not a clean pass.

**Edited/generated files:** C:133 and C:149, cache PVL;
[metal candidate diff](sky130-io-lvs-metal-candidate.patch) records the earlier
recognition experiment. Final behavior also includes B5; the early diff alone
is not the complete final rule. Original IO GDS/source unchanged.

<a id="a4"></a>

## A4. Bent poly and diffusion resistor length

Open `com_res_weak` in the original IO GDS and locate the long U-shaped
66/13-marked poly body. `$LVS_IOSP:969` specifies `XRI85`, W=0.8, L=50 um.
Measure width perpendicular to the strip and the Boolean resistor-body area,
not its bounding box. For this body A/W=50.8 um, with two inside bends.
Subtracting `2 * 0.8/2` gives 50 um. Compare this with the old `RES_PROPERTIES`
formula at `$LVS_RAW:1492` and `SKY130_IO_POLY_BENDS` in the repaired deck.

The isolated comparison is under
`build/sky130-io-lvs-step2/poly-bends/sky130_fd_io__com_res_weak/`. The same
formula is applied to the XRES diffusion meander: inspect its 65/13 body and
verify the bend correction independently. Use the inside-bend convention on
the actual recognition polygon, not a generic count of all polygon vertices.

**Edited/generated files:** C:238 and C:226, cache PVL,
[poly-bend diff](sky130-io-lvs-poly-bends-candidate.patch) and
[HV-diffusion diff](sky130-io-lvs-hv-diffusion-candidate.patch). No source
resistor length or GDS was changed.

<a id="a5"></a>

## A5. False PW diode from a marker-only region

Open `sky130_fd_io__gnd2gnd_120x2_lv_isosub` in the IO GDS, and inspect the
areaid.de marker, nwell, n+ implant and diffusion. The raw rule at
`$LVS_RAW:770` derives a PW diode from marker minus nwell even where the
required n+ diffusion terminal is absent. Compare that selection with the
patched `SKY130_IO_PW_MARKER` rule: a valid PW recognition polygon must
interact with `(nsdm AND diff)`.

The [IO debug overlay](sky130-io-lvs-debug.pvl) exports recognition on 924/0
and PW_SD on 925/0. Inspect those together; a marker-only recognition shape
with no corresponding PW_SD is the defect. Compare the isolated step-7
`pw-context/...gnd2gnd_120x2_lv_isosub` and `reference-pw-context/...top_power_lvc_wpad`
reports. Their controls use declared standalone supply assumptions; those
virtual connections are not evidence of physical chip continuity and were not
copied into the final chip control.

**Edited/generated files:** N:137, cache PVL,
[PW diode diff](sky130-io-lvs-pw-diode-candidate.patch). NW diode rules and the
original source/layout are unchanged.

<a id="a6"></a>

## A6. HV diffusion bypass and diffusion resistor properties

Open `sky130_fd_io__top_xres4v2` and its diffusion-resistor/meander children.
Display diffusion 65/20, resistor marker 65/13, HV identifier 75/20 and poly.
At `$LVS_RAW:1065`, HV_source_drain removes only HV poly; its conductor can
continue through the marked resistor body. Trace this bypass in a scratch
Boolean view. The repaired expression also removes `diff_res`, retaining the
electrical gap occupied by the resistor device.

Raw `RES_GENERIC_ND/PD` declarations at lines 990..991 have no L/W macro.
Inspect the repaired declarations for their property macro, then compare the
source and raw extracted resistor dimensions. The full-chip case
`build/sky130-io-lvs-chip-context-step3` records the combined HV gap/bend change
in `experiment.json`; inspect its `ChipTop.lvs_results.cls` for disappearance
of the XRES bypass symptoms. Multiple changes in that experiment require
separating connectivity from the property correction when drawing conclusions.

**Edited/generated files:** C:204, C:216 and C:226, cache PVL,
[diffusion-property diff](sky130-io-lvs-diffusion-candidate.patch),
[HV-diffusion diff](sky130-io-lvs-hv-diffusion-candidate.patch). No original
XRES GDS/SPICE edits.

<a id="a7"></a>

## A7. PoR Schmitt resistor terminals crossing MOS gates

Open `$LVS_POR/simple_por.gds`, select `sky130_fd_sc_hvl__schmittbuf_1`, and
show diffusion, poly and resistor markers. The old `np_term`/`pp_term` rules
at `$LVS_RAW:934` and :937 select full ndiff/pdiff touching a resistor. Reproduce
these Boolean selections in a scratch view: they still include gate regions.
Following the subsequent licon/LI connectivity shows how a terminal shape can
bridge a transistor gate and collapse supply/internal nets.

Repeat with `nSourceDrain`/`pSourceDrain`, which already have gate regions cut
out. Compare the recorded N/P overlap areas in
`build/sky130-por-lvs-components/schmitt-terminal-overlap-audit.json`:
**0.795/1.5 um2 before, 0/0 after**, with two terminal shapes per polarity on
both versions. The isolated `build/sky130-por-lvs-components-step2/terminals/schmitt`
and combined PoR reports establish the corresponding connectivity change.

**Edited/generated files:** C:591, helper
[sky130-por-lvs.py](sky130-por-lvs.py), cache/candidate PVLs and
[terminal-selection diff](sky130-lvs-por-diffusion-terminals-candidate.patch).
No transistor geometry, source nodes or comparison tolerance was edited.

<a id="a8"></a>

## A8. Second MIM layer and upper-electrode connectivity

Open `$LVS_POR/simple_por.gds`, cell
`sky130_fd_pr__cap_mim_m3_2_W5U4AW`. Measure its 97/44 marker: **30 x 30 um**.
Show metal4, metal5 and via4. Distinguish the central upper-electrode contact
metal5 from the separate metal5 return strip belonging to the lower electrode.
The raw deck maps cap2m at line 175 but has no corresponding device declaration.

Read `build/sky130-por-lvs-components-step2/mim2-electrode-contact-audit.json`:
288 via centers inside the marker contact the central shape; 19 outside
contact the return strip. Selecting both metal5 shapes as one upper terminal
caused the first candidate's `too many pins found` error. The final rule uses
cap2m as a distinct upper conductor connected through **inside** via4, while
outside via4 retains ordinary M4/M5 connectivity. Compare the two capacitor
leaf reports under that directory's `mim2/cap_m3` and `mim2/cap_m4`: parameters
should agree; standalone missing interface labels are a separate issue.

**Edited/generated files:** C:557, cache PVL,
[MIM2 diff](sky130-lvs-por-mim2-candidate.patch), diagnostic helper
`sky130-por-lvs.py`. Original capacitor GDS/source unchanged.

<a id="a9"></a>

## A9. SRAM one-sided gate sizing

Open `$LVS_SRAM/sram22_64x22m4w22/sram22_64x22m4w22.gds`, cell `sram_sp_cell`.
Inspect active intersected with poly, with well/threshold recognition masks.
One selected PFET recognition rectangle is locally
**(-1.01,-0.27)-(-0.87,-0.245) um**: its contact edge is 0.14 um and its
orthogonal gate extent is 0.025 um. It has one SD-facing edge and three edges
on the active boundary. Measure that intersection, not the entire poly stripe.

The ordinary two-contact calculation divides the one contact edge by two,
giving W=0.07 and L=0.05; full contact width gives the source's W=0.14,
L=0.025. Check the analogous NFET in colend/hstrap: old L/W=0.28/0.07 versus
source 0.14/0.14. Inspect raw devices before parallel reduction.

Evidence is under `build/sky130-sram-lvs-edge-devices`: `edge-geometry-audit.json`
contains coordinates, edge counts and dimensions; `all-macro-edge-geometry-audit.json`
covers all four original macro GDS files; `standard-cell-geometry-audit.json`
records zero selected gates out of 2,008 measured in 155 SCL definitions.
`rotated-geometry-checks.json` checks rotations. Its `check-geometry.py` exposes
the independent Boolean/edge algorithm; importing and calling `audit` is
read-only, but running its main program overwrites the audit JSON.

**Edited/generated files:** C:386, helper [sky130-sram-lvs.py](sky130-sram-lvs.py),
cache PVL and [edge-sizing diff](sky130-lvs-sram-edge-sizing-candidate.patch).
SRAM source L/W, original GDS and ordinary-gate sizing are unchanged.

<a id="b1"></a>

## B1. Geometric source translation, units and multiplicity

Use one leaf at a time. Compare its original `.SUBCKT` with the same block in
`$LVS_CDL`; retain port order, nodes and hierarchy while checking these cases:

1. MOS: an openPDKs X wrapper with W=0.74, L=0.15 becomes a native deck-named
   M device with W=7.4e-7, L=1.5e-7 in SI units. Native Cadence CDL must retain
   its existing SI dimensions. Look at T:145 for native calls and T:165 for
   wrapper conversion; an indiscriminate prefix replacement is insufficient.
2. Suffixes: source `w=290000u` evaluates to 0.29 in a wrapper's numeric-micron
   convention, hence 2.9e-7 m. In `$LVS_IOSP`, find the `top_power_lvc_wpad`
   `RI21` call: `w=2.5385e+08u l=100000u` must become **253.85/0.1 um**,
   not a source resistor thousands of meters wide.
3. Fingers: at `$LVS_SRAM/sram22.spice:25804`, `XTAIL` has nf=4, W=1.680.
   Inspect its sense-amplifier leaf in the matching macro GDS: four parallel
   fingers must correspond to native W=1.68e-6 and M=4, not M=1. Check nf=2
   examples nearby and caller m as well. `mult` is different: inspect the
   primitive wrapper's inner M statement to see whether it is electrically
   applied, and Netgen setup's `delete mult` statements. Do not multiply IO
   widths by a statistical parameter.
4. Diodes/MIM/precision resistors: compare the actual extracted geometric
   device with the translated native D/C/R, not the simulator's junction,
   RESHEAD/RESBODY or behavioral network. `DIO_PARAMS` in the raw PVL defines
   the area/perimeter scaling; the translator uses AREA=wrapper-area/1e12 and
   PJ=wrapper-perimeter/1e6 to match that convention. Check MIM L/W and verify
   statistical mf does not replicate the capacitor.

For the SRAM `special_*` MOS mappings, read T:30–38 and compare original
bitcell/replica/strap source calls with the **raw extracted subtypes** in the
isolated reports. The investigated special NFETs extract as `nfet_01v8`
(or its LVT subtype), and special PFETs as `pfet_01v8_hvt`. Check the GDS
well/threshold identifiers that select those devices rather than assuming
the simulation wrapper name must appear in the extracted netlist. L/W,
nodes and bulk connections remain checked.

The statistical-parameter check can start with
`$LVS_OPEN/libs.ref/sky130_fd_pr/spice/sky130_fd_pr__esd_nfet_g5v0d10v5.pm3.spice`:
compare its parameter declaration at line 18 with the inner M call at line 19
and later mismatch expressions. It does not electrically multiply M by `mult`.

`sky130.pegasus.lvs.json` records `nf_policy`, `statistical_multipliers`,
`diode_properties` and `converted_calls`. A useful isolated starting point is
the original SRAM sense-amplifier leaf with nf=2/4, followed by a full macro
comparison. Preserve unknown reachable devices as errors instead of deleting
them. These tests establish the mapping for the supplied wrappers, not every
possible SPICE syntax or parameter convention.

**Edited/generated files:** T:109..305, H `pegasus_lvs_prepare_schematic`,
generated CDL/manifest. Original IO/primitives/SRAM/SCL sources are unchanged;
the source overlay exception is specifically identified in B9.

<a id="b2"></a>

## B2. Custom level-shifter precedence without losing HVL dependencies

Compare the definition at
`$LVS_OPEN/libs.ref/sky130_fd_sc_hvl/spice/sky130_fd_sc_hvl.spice:1452` with
`/scratch/jfx/cadence-skywater-130-pdk/OPEN-PDKS-Modifications/sky130_fd_sc_hvl__lsbufhv2lv_1_m1_access/sky130_fd_sc_hvl__lsbufhv2lv_1.spice:3`.
The cell name/ports are shared, but the latter is the configured custom source
paired with its modified GDS. In that collateral directory, the README and
GDS show the pre-existing M1 access rectangles on A and X; this geometry
customization predates the LVS work.

Inspect `$LVS_RUN/sky130_fd_sc_hvl.lvs.spice`: it must omit only that one
definition while retaining the other HVL cells required by PoR. In the final
CDL there must be exactly one definition of the level shifter. Use the
manifest's `cell_sources` to confirm it came from the custom file. Removing
the whole stock HVL include would instead leave other cells unresolved;
keeping both definitions would make precedence ambiguous.

**Edited/generated files:** H:1844 (`pegasus_lvs_add_130a_primitives`), N's
subcircuit-removal utilities, generated filtered HVL file and CDL/control.
The original stock HVL source and custom GDS/LEF/SPICE were not edited here.

<a id="b3"></a>

## B3. IO hierarchy boundaries

Inspect the before/after reports under
`build/sky130-io-lvs/hierarchy/sky130_ef_io__gpiov2_pad_wrapped` and
`build/sky130-io-lvs-step2/hierarchy/sky130_ef_io__gpiov2_pad_wrapped`.
Use the cell detail sections: one comparison shows 31 reduced native FETs
missing from the inner EF pad and the same 31 extra in its wrapper (116 raw
wrapper devices reduced into those groups). Match subtype, nodes and instance
correspondence; equal counts alone are not proof of equivalent circuitry.

Open the generated `build/sky130-io-lvs-step2/gpiov2_pad_wrapped.gds`
and descend through the AMUX/EF-pad boundaries. Devices sharing geometry across
those boundaries can be promoted into the parent by extraction. Inspect
`lvs_exclude_hcell` in the final control and `hierarchy_expansions` in the
manifest: eleven IO boundaries are expanded, not deleted from the source.
Verify the devices still exist in the parent comparison, and that no
`virtual_connect`/`lvs_join_nets` statements appear in the final chip control.

**Edited/generated files:** N's `IO_HIERARCHY_EXPANSIONS`, C:87,
H's schematic hook, generated control. Diagnostic helpers include
`sky130-io-lvs.py` and `sky130-chip-io-lvs.py`; isolated GDS is a subset copy.
No original cell GDS or source devices were removed.

<a id="b4"></a>

## B4. SRAM helper namespace collisions

Compare the aggregate `$LVS_SRAM/sram22.spice` with each macro's individual
`<macro>/<macro>.spice`. In the aggregate, start at `tristate_inv:731771`
versus `tristate_inv_3:25774`, and `column_mos:26086` versus `column_mos_7:25963`.
Follow the MOS wrapper masters to their numerical W parameters. The bare
tristate helper uses 1.2 um devices; the matching large-macro helper uses
5 um devices. The column drain pair is 1.2/1.7 versus 1.6/2.25 um.

Open the original large macro GDS and inspect the leaf actually bound to its
bare helper name. The report's dimensions match a *different aggregate suffix*,
not the aggregate's bare helper. Check
`build/sky130-io-lvs-m3-ring-chip-context-step2/sram-source-namespace-audit.json`
for the individual-to-aggregate equivalents, and
`build/sky130-sram-lvs-namespace/namespace-audit.json` for the 55 ambiguous
families and 299 expanded names. Read C:429/C:527: fingerprints preserve nodes,
ordered terminals, parameters and instance names while resolving helper names
recursively. All four macro-root fingerprints agree with their individual
sources. The macro roots remain compared after helper expansion.

**Edited/generated files:** C:429/C:527 and C:87, helper
`sky130-sram-lvs.py`, generated control/namespace-audit data. Original aggregate
and individual SRAM SPICE/GDS files were not renamed, resized or edited.

<a id="b5"></a>

## B5. Annotated SHORT surrogates versus real resistors

Inspect `$LVS_IOSP:6747`: `RI1`/`RI2` are explicitly annotated as SHORTs,
followed by native metal-R calls with fixed nominal dimensions. Open the
original `tk_em1s` variants and compare 68/15 marker dimensions. Recorded
marker widths include 0.23, 0.26, 0.66 and 1.32 um despite repeated fixed source
nominals. Marker notches also explain why A/contact-perimeter length differs
from a simple bounding-box length.

Read `build/sky130-io-lvs-metal-dimensions/metal-mismatch-summary.json` for the
strict dimensional failures, then the corresponding summary under
`build/sky130-io-lvs-short-markers`. In the final manifest,
`annotated_io_short_model_changes` must identify only 28 calls in 13 IO
definitions. Compare old/generated calls: only the subtype changes; terminals,
parameters and dimensions remain. C:172 requires an annotation with the same
instance name and terminal pair; it does not infer SHORTs from a mismatch.

Inspect final rules for `res_io_short_m*` versus `res_generic_m*`. Nominal SHORT
W/L are omitted, but real M1-M4 W/L remain at zero tolerance. M1 RC/RB filtering
still applies as described in B8. This is a documented comparison policy;
its MATCH does not independently verify SHORT nominal geometry.

**Edited/generated files:** C:149/C:172/C:275, generated CDL/manifest and cache
PVL. Original IO source comments, source dimensions and marker GDS unchanged.

<a id="b6"></a>

## B6. PADISO annuli and the 5% equivalent-width bound

Open `sky130_fd_io__top_power_lvc_wpad` in the original IO GDS. Show met3
70/20 and its 70/13 resistor marker, and form their Boolean intersection.
Inspect each ring's two connections to P_CORE/PADISO. A single rectangle
formula cannot represent the two paths around a hole.

The geometry audit in
`build/sky130-io-lvs-m3-ring-partition/partition-geometry-check.json` gives exact
local strip coordinates. For the left LVC ring, inspect the narrow vertical
strips around x=0.505..0.515 and x=24.475..24.485, with inner y=61.56..67.07,
and the top/bottom strips. Measure their actual marked-conductor area and
contact edges. The partition must preserve area, not include marker-only area
outside metal. Compute each strip's resistance in squares L/W. The generated
macro normalizes it to L=0.01 um using Wnormalized=Lref*Wstrip/Lstrip, then
parallel reduction adds normalized widths. Verify eight segments reduce to
two source RIL/RIR resistors, with matching endpoints.

At `$LVS_IOSP:7849`, the source block assigns RIL/RIR W=11.825, L=0.01 despite
different ring geometries across four original pad variants. Read
`build/sky130-io-lvs-m3-ring-qualification/qualification-summary.json`: residual
equivalent-W errors are 0.168%, 2.705%, and up to 3.767%. The chosen 5% bound
covers those measurements. It is **not** a derived corner-field accuracy
guarantee. Verify the strict 0% reports to see the residuals directly, and
verify the final deck limits this bound to `res_io_padiso_m3`; generic M3 stays
strict. No source W/L was adjusted to the extracted result.

**Edited/generated files:** C:317/C:339, helpers
`sky130-m3-ring-lvs.py`/`sky130-chip-io-lvs.py`, generated source subtype names,
cache PVL/control and qualification data. Original annular GDS and source
dimensions unchanged. This entry explicitly includes an approximation policy.

<a id="b7"></a>

## B7. ESD subtype partition and tolerances

Open `sky130_fd_io__signal_5_sym_hv_local_5term` and the relevant local-ESD
leaf in the original IO GDS. Display 81/19 over HV gate geometry. Inspect the
flanged/nonrectangular gate and compare its effective width with the source's
ESD wrapper call. The recorded isolated example had extracted W=5.56569 um
against nominal 5.4 um; the geometric interpretation differs from ordinary MOS.

Read `$LVS_OPEN/libs.tech/netgen/sky130A_setup.tcl:231`: the comments describe
the flanged-gate width ambiguity, and lines 247/256 specify W=0.07, L=0.01
fractional tolerances for **ESD** devices. Pegasus's generated rules use
7%/1%, with `areaid.ed` selecting the separate `*_esd` subtypes. Check ordinary
HV gates take the complementary recognition shapes and retain zero tolerance.
The generated source preserves ESD subtype identity; otherwise an ESD tolerance
cannot be scoped correctly. Inspect T:110 and C:257/C:275.

Also inspect explicit M5 rules: they retain 1% dimensions. OpenPDKs' comparison
convention motivates this compatibility policy; it is not proof that every
ESD/M5 geometry or future PDK revision is accurate to that bound.

**Edited/generated files:** T's ESD mapping, C's recognition/property rules,
cache PVL and generated CDL. Original primitive model files, Netgen setup,
ESD GDS and nominal source dimensions unchanged.

<a id="b8"></a>

## B8. Placeholders, physical-only decaps, and M1 filtering

Inspect `$LVS_IOSP:19` (`condiode`) and :571 (`com_pad`): both are empty
two-pin `.SUBCKT` declarations with no device body. The schematic hook checks
that exact shape before adding source-only blackbox/open filters. A future
nonempty definition must not be silently discarded. Compare the final control
lines for these two exact names with T's `source_only_placeholders` manifest.

For decaps, inspect H's Cadence `physical_only_cells` list and D's exported
netlist exclusions. `FILL_DECAP8/16` are deliberately absent from the functional
source, while layout contains their MOS devices. Verify only those physical-only
types receive the corresponding layout filter and that functional standard
cells/SRAMs/PoR remain compared. This policy does not verify decap transistor
connectivity against a transistor-level source model.

Finally inspect `$LVS_CTL` for `lvs_filter_option RC RB` on generic/SHORT M1.
The installed Pegasus reference
`/tools/cadence/PEGASUS/PEGASUS231/doc/pegasusref/comref_re_lvs_filter_option.html`
defines RB as a resistor with a floating terminal and RC as PLUS/MINUS tied
together (HTML lines 210/211). Cross-probe the corresponding raw extracted
M1 branches; filtering must not remove a resistor connecting two live nets.

**Edited/generated files:** T's allowlist/empty-body checks, H's schematic hook,
C:122 and D's physical-netlist exclusion logic, generated control. No empty
source block was populated, and no decap layout/model was modified.

<a id="b9"></a>

## B9. Authoritative PoR source precision

Compare `$LVS_POR/simple_por.spice:143` with
`$LVS_RUN/source_overlays/simple_por.spice:143`: only X4's L changes from 1.36
to 1.355 um. Compare the full files with `diff -u`; nodes, W, model and all
other content should agree. Now inspect the independent originals:

- `/scratch/jfx/open-pdks/sources/sky130_fd_sc_hvl/cells/schmittbuf/sky130_fd_sc_hvl__schmittbuf_1.cdl:19`
  specifies l=1.355.
- The neighboring original `.spice:21` specifies l=1.355e+06u, equivalent to
  1.355 numeric microns under the wrapper convention.

Open canonical `sky130_fd_sc_hvl__schmittbuf_1.gds` and the Schmitt cell in
`simple_por.gds` at the same local origin. An XOR on every layer must be empty.
`build/sky130-por-lvs-components-step2/schmitt-source-provenance.json` records
that comparison at 1e-6 um precision and the canonical GDS hash; the companion
`experiment.json` identifies/hashes the PoR GDS. This independent
source/geometry agreement is the reason to correct the custom source, rather
than widen a resistor tolerance. The isolated corrected PoR MATCH is under
`build/sky130-por-lvs-closeout/isolated`.

**Edited/generated files:** C:56/C:605, helper
`sky130-por-closeout.py`, [source-precision diff](sky130-lvs-por-source-precision.patch),
generated `source_overlays/simple_por.spice` and compiled CDL. **The external
CARAVEL simple_por.spice remains unedited at 1.36.** Its accepted original hash
and the corrected overlay hash are recorded/guarded by the implementation.

<a id="c1"></a>

## C1. Configured PoR GDS/SPICE pair

Read `write_chiptop_drc_lvs_layout` in `hammer-driver`: the merge list comes
from the configured libraries and input ILMs. There is no separate PoR
replacement branch or override setting. Compare with the old driver in
version control. The old
hardcoded alternate was
`/tools/C/rohankumar/sky130/stac_tapeout/gds/simple_por_drc_lvs.gds`.
The configured pair is `$LVS_POR/simple_por.gds` and `simple_por.spice`.
Inspect the configured extra library and generated `write_stream -merge`
command: both should name that configured PoR GDS. Historical snapshots may
retain the retired override setting; fresh runs no longer define or read it.

Open both GDS files and select `sky130_fd_pr__res_xhigh_po_0p69_S5N9F3`.
Overlay/XOR their poly and contact layers: the alternate removed one poly body,
two licon shapes and one NPC shape. It also added an `lv_net` label at
(40,41.3) on 83/44. Count the precision-poly resistor bodies: configured
layout/source are 28/28, alternate layout/source are 27/28. The reports and
`result-summary.json` in `build/sky130-por-lvs-input-views` record both counts;
`experiment.json` identifies the exact inputs/hashes. This input-pair fix alone
did **not** resolve the other PoR extraction/source issues in A7/A8/B9.

**Edited/generated files:** `hammer-driver`, Sky130 `defaults.yml` and
`defaults_types.yml` (the override setting was removed), and the configured
PoR stream regression in `hammer/tests/test_sky130_lvs.py` (override-specific
checks removed). The separate diagnostic helper `sky130-por-lvs.py` can still
compare explicitly supplied layouts for investigation. Neither external PoR
GDS was modified; the production flow selects its configured library.

<a id="c2"></a>

## C2. NC-pad supply binding in CPF

Read [sky130.cpf](sky130.cpf):46 and its IO supply mappings at lines 64–67.
The added instance pattern is `nc_*/iocell`; the old `iocell_*/iocell` pattern
did not select those instances. In a matching old export and repaired export,
locate `\\nc_0/iocell` through `\\nc_26/iocell`. Each should gain these nine
connections, giving 27 x 9 = 243 formerly absent PG bindings:

| Pins | Expected net |
| --- | --- |
| VDDIO, VDDIO_Q, VSWITCH | VDDIO |
| VCCD, VCCHIB | VDD |
| VSSIO, VSSIO_Q, VSSD, VSSA | VSS |

Inspect `build/sky130-por-vddio-repair/chip-export/export.json`, specifically
`nc_supply_connections`, and the generated `reexport.tcl`. It applies scoped
`connect_global_net` commands and exports the repaired design. Inspect
`check_export.py` beside it: it verifies the 27 pads and compares logic/bus
connections for 84,944 retained instances. The historical `source_netlist`
path now points to a regenerated mainline file, so the old baseline comparison
requires the original archived netlist; do not mistake that changing path for
an immutable before snapshot. The recorded connection list and repaired export
remain available to inspect directly.

Use the physical netlist to check bindings, then LVS/GDS to check continuity:
CPF assignment alone does not join separate metal shapes, as C3/C4 demonstrate.
Do not blanket-connect clamp `*_PAD` pins; inspect their explicit source
resistors before deciding whether any terminal is missing a connection.

**Edited/generated files:** `sky130.cpf`, helper
[sky130-reexport-nc-pg.py](sky130-reexport-nc-pg.py), generated diagnostic
Tcl/manifest/checker and chip Verilog. Fresh mainline P&R applies the CPF to its
own design DB and exports. No IO source/GDS/LEF library was edited.

<a id="c3"></a>

## C3. Physical quiet-VDDIO tie

Open the custom north filler
`sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_and_vssio_vssa_vssd_slice_20um`
from its existing GDS under
`/scratch/jfx/cadence-skywater-130-pdk/OPEN-PDKS-Modifications/`.
On met4 (71/20), measure its two separate local rails:
VDDIO_Q y=62.05..66.50 and VDDIO y=68.00..92.965 um. The 1.50 um gap explains
why mapping both pins to VDDIO in CPF is insufficient.

Read [sky130-quiet-vddio.tcl](sky130-quiet-vddio.tcl):4. For R0 instance
`IO_FILLER_N_0`, it inserts the local rectangle
(9.5,65.5)–(10.5,69.0), overlapping both rails. In the qualified Rocket
placement the filler lower-left is (204,4990.035); the chip rectangle is
(213.5,5055.535)–(214.5,5059.035). Compare the old chip GDS with
`build/sky130-nc-pg-export-v2/ChipTop_drc_lvs.gds` at that location. The latter
must contain the added met4 bridge. Cross-probe the formerly disconnected
VDDIO_Q island in the preceding `sky130-io-lvs-chip-context-step3` report.
These are a geometry check and a connectivity check of the same physical open.

For a new placement, recompute chip coordinates from the actual instance bbox;
the local rectangle is the useful invariant. The hook checks master,
orientation and 20 x 197.965 um dimensions and fails when they change.

**Edited/generated files:** `sky130-quiet-vddio.tcl`, D:2050 and its pre-export
hook, diagnostic re-export helper, new chip GDS/DEF. The custom filler library
was pre-existing and **was not edited**; the bridge is added at chip level.
LVS verifies continuity; DRC must separately qualify spacing/enclosure.

<a id="c4"></a>

## C4. Physical PoR VDDIO via

The saved before/after exports below use the historical instance name
`IO_FILLER_MANUAL_S_3`. The current mainline Tcl now requires
`IO_FILLER_POR_TAP`; future CSVs must use that instance name for the PoR tap.
It accepts the ordinary or custom connected 20 um slice, both of which expose
the lower met4 VDDIO rail at local y=17.750..22.400 um. The geometry checks and
via dimensions below remain in force; this naming change does not modify old
exports or regenerate existing P&R scripts.

Compare the pre-repair `build/sky130-por-lvs-closeout/chip-export/ChipTop_drc_lvs.gds`
with `build/sky130-por-vddio-repair/chip-export/ChipTop_drc_lvs.gds`.
At (3277.2,177.89) enable met3 70/20, via3 70/44 and met4 71/20.
The existing VDDIO met3 trunk spans
(3276.7,175.565)–(3277.7,247.835); the south filler met4 rail spans
(3264,175.565)–(3284,180.215). Before repair they overlap in XY but lack a
via3. Inspect the filler macro too: it supplies no met3/via3 connection there.

Read [sky130-por-vddio.tcl](sky130-por-vddio.tcl):4. Verify the new 4-row,
1-column via: 0.2 um cuts, 0.2 um cut spacing, x/y metal enclosures
0.065/0.100 um. Its metal enclosure is 0.330 x 1.600 um and fits inside both
conductors. Check the repaired DEF's SPECIALNETS entry and its referenced VIAS
definition. At 1,000 DEF units/um the position is `(3277200 177890)`;
`M3M4_PR_12` is this export's via name, not a universal required suffix.

The existing checker is read-only and verifies position, one VDDIO-net hit,
layer stack, cut size, array and enclosure:

```bash
.conda-env/bin/python "$LVS_BUILD/sky130-por-vddio-repair/check-via.py"
```

Compare the pre-via full-chip report in `sky130-por-lvs-closeout/full-chip`
(164 matches, one top-level failure, no parameter/subtype failures) with
`sky130-por-vddio-repair/full-chip` (165 matches, no failures). The old open is
PoR `vdd3v3` versus VDDIO, recorded as layout net 451 in that run; net numbers
are run-specific. The policy/deck/source stayed the same for this physical
repair. `via-verification.json` records the geometry, but its historical
`full_chip_lvs_pending` flag predates the final report; use `result-summary.json`
and the actual report for the final outcome.

**Edited/generated files:** `sky130-por-vddio.tcl`, D:2050, helper
[sky130-por-power-repair.py](sky130-por-power-repair.py), diagnostic scripts and
verification JSON; new chip GDS/DEF. No PoR/filler library cell was edited.
This closes a real P&R open; physical DRC remains a separate check.

<a id="c5"></a>

## C5. Physical-only source-export list

Read D:2060 `write_chiptop_netlist_with_pg_pins`: exclusions now come from
`x.get_physical_only_cells()` plus named IO fillers/corners. Read H's Cadence
library `physical_only_cells_list` and any effective manual/append overrides
in `par-rundir/config_db_tmp.json`. Cadence names include `FILL*`,
`FILL_DECAP8/16`, `ANTENNA`; the old hardcoded HD names did not describe the
selected Cadence library.

Inspect the generated Innovus `write_netlist ... -exclude_insts_of_cells`
command and the output Verilog. These physical-only instances should be absent
from functional source; functional standard cells and macro roots must remain.
Compare that list to the narrow layout decap policy in B8. Excluding a source
cell does not by itself justify dropping arbitrary layout circuitry.

**Edited/generated files:** D:2060; the saved-DB re-export helper uses the same
selected-library intent. Generated P&R Tcl and physical Verilog change.
No Cadence CDL, Liberty, LEF or GDS was edited.

<a id="c6"></a>

## C6. Verification GDS selection and missing-master rejection

Read D:2150 `use_drc_lvs_gds` and its DRC/LVS pre-control hooks. Compare
`lvs.inputs.layout_file` in the saved input JSON with the actual `layout_path`
in `$LVS_CTL` and report header. For IO-enabled top-level runs the consumed
file must be `<top>_drc_lvs.gds`, generated by D:2081, including the configured
macro GDS views. The hook raises an error if it is absent. Verify the
`use_io_cells` guard leaves IO-disabled block runs on their ordinary layout.

Read D:2164 `require_lvs_cell_masters` and search `$LVS_CTL` for
`ignore_instances_with_missing_cell_master`: it must be absent. A missing
functional master must fail rather than silently delete instances. Also audit
the source manifest as in A0; absence of the ignore option alone does not
prove import completeness.

**Edited/generated files:** D's stream-selection and control hooks; generated
verification GDS/control. This changes input selection/error handling, not
library geometry or device models.

<a id="c7"></a>

## C7. Normal technology integration, provenance and stale settings

Trace H:1406 `setup_pegasus_lvs_deck` to C:44 `build_compatibility_deck` and
H:1895 `pegasus_lvs_prepare_schematic` to the translator/source-policy code.
The original deck selected by YAML is read, patched into the tech cache, and
referenced in the actual control/report. Compare its policy JSON's
`source_sha256` with the original raw file and `patched_deck_sha256` with the
generated body after removing the one-line cache-provenance header.
The compiled-CDL hash and all source hashes are recorded in its manifest.
Review exact-text/hash guards before applying this profile to another PDK
revision; matching this revision is not evidence that a changed revision is safe.

Check [example-sky130.yml](example-sky130.yml):77 enables
`technology.sky130.lvs_mixed_library_compatibility`, while technology defaults
set it false. Inspect the **effective** saved `par-input.json`, `lvs-input.json`
and tool `config_db*.json` values: editing YAML does not update old snapshots.
The refresh commands in the summary reload it through the conversion steps.
Verify `lvs_blackbox_srams` is false and the report's blackboxed count is zero.
The optional SRAM pin-stub/graybox utility is not what established this MATCH.
If reviewing that utility separately, inspect N:46 `blackbox_subcircuits` and
H:1817 `pegasus_lvs_blackbox_srams`: generated `*.blackboxes.cdl` must retain
the original macro headers, continuation lines, ordered bus bits and supply
ports while omitting bodies. It fixes graybox port mapping when enabled; it
does not verify SRAM internals and was not enabled for the reported closure.

For the integration experiment, inspect
`build/sky130-hammer-lvs-integration/equivalence.json` and
`top-level/equivalence.json`, then
[sky130-lvs-normal-flow.py](sky130-lvs-normal-flow.py):16. The comparison checks
all 1,726 source definitions, no stray executable statements, the same 310
hierarchy exclusions and the deck body hash. The historical integration run
used repaired diagnostic exports; the latest mainline report instead names the
original project's `par-rundir` exports. Check the actual report header rather
than assuming an old equivalence JSON describes a newly overwritten report.

**Edited/generated files:** H, N, T, C;
`defaults.yml`, `defaults_types.yml`, `example-sky130.yml`, D and the normal-flow
helper. Generated cache PVL/policy, filtered HVL SPICE, source overlay, compiled
CDL/manifest and Pegasus control are disposable outputs. They must regenerate
from the checked-in implementation; no external source library is overwritten.

<a id="d1"></a>

## D1. Diagnostic DB restore with changed Liberty collateral

Read [sky130-reexport-nc-pg.py](sky130-reexport-nc-pg.py):25
`database_restore_tcl`, then the generated diagnostic `reexport.tcl` and its
Innovus log. The restore warning/error identifies changed SRAM Liberty files;
compare those named files with the saved DB's expected collateral revision.
The Tcl saves `read_db_file_check`, sets it false only around
`read_db -no_binary_constraint`, and restores the previous value even when
restore raises an error. Check that no later command saves the original DB or
runs placement/routing optimization. Export checks compare logic/bus connections
after restore, but do not establish timing equivalence of changed Liberty files.

**Edited/generated files:** the diagnostic helper and generated restore Tcl.
This workaround did not edit Liberty files or introduce a blanket mainline
`read_db_file_check false` setting. No Liberate work was performed as part of it.

<a id="d2"></a>

## D2. DEF checker accepting SHAPE IOWIRE

Read [sky130-por-power-repair.py](sky130-por-power-repair.py):18
`check_def_via`. In the repaired DEF find the special-net via line:

```text
+ FIXED met4 0 + SHAPE IOWIRE ( 3277200 177890 ) M3M4_PR_12
```

The old regex expected the position immediately after `met4 0`, so it returned
no hits even though the via was present. The updated regex accepts the optional
`+ SHAPE <type>` clause; it still checks exactly one VDDIO hit and the VIAS
definition. Run the read-only checker in C4 and inspect the geometry as well.

**Edited/generated files:** `sky130-por-power-repair.py`, regenerated
`check-via.py`/resume scripts. This repairs the verification parser; it does
not insert or move a via, change a deck, or edit PDK collateral.

## Confirming a result independently

Start with the report header, cell statistics, ERC and extraction warnings;
do not use a MATCH banner alone. The current 02:48:53 mainline report has
166 matched types, six expanded, zero not run/mismatching/parameter/subtype/
blackboxed types and empty ERC. The earlier diagnostic repair had 165 matched
types. Those are separate runs and should retain their own provenance.

For a controlled experiment, preserve the original report, controls, manifests
and input hashes, then make a **new** run directory and change only the rule or
physical edit being tested. Some historical steps combined several fixes and
are described as such above. Check that expected devices reappear with the
right nodes/dimensions, not merely that the error count falls. Debug-derived
layer extraction is diagnostic, not a signoff result. Physical DRC, comparison
tolerance justification and extraction-warning review remain separate from
LVS agreement. Original-library files must stay untouched during these checks.
