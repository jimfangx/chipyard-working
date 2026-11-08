# Sky130 mixed-PDK LVS investigation

For the final changes, reasoning, comparison policies and completed MATCH
results, see [sky130-lvs-summary.md](sky130-lvs-summary.md). The investigation
notes below retain earlier intermediate results and limitations.

The August 22 ChipTop results precede the September 16 GDS/netlist and later
driver changes. Regenerate the P&R write-design outputs and run LVS into a fresh
directory before interpreting chip-level connectivity after these changes.

## Applied flow fixes

- The chip IO-ring flow selects `<top>_drc_lvs.gds` before Pegasus DRC/LVS
  control-file generation. Missing replacement GDS is an error. Block-level runs
  with `technology.sky130.use_io_cells: false` retain their normal GDS.
- The supplemental HVL library is copied to the LVS run directory with only
  `sky130_fd_sc_hvl__lsbufhv2lv_1` removed when a custom definition is imported.
  The custom extraction remains authoritative; other HVL cells used by the PoR
  remain available. Managed imports are deduplicated across repeated hook calls.
- The project's netlist override uses Hammer's technology/configuration physical
  cell list, retaining Cadence exclusions `FILL1/2/4/8/16/32/64`,
  `FILL_DECAP8/16`, and `ANTENNA`. The routing hook already selects Cadence
  `ANTENNA` for `sky130_scl`; the old hardcoded HD diode exclusion is gone.
  These are **netlist exclusions**, not newly added CDL device models.
- The project removes Pegasus's `-ignore_instances_with_missing_cell_master`:
  remaining missing Verilog masters must be diagnosed rather than dropped.
- SRAM gray boxing replaces the aggregate `sram22.spice` (and supported individual
  macro files) with generated CDL pin stubs. Exact `.SUBCKT` headers, continuation
  lines, bus-bit order and supply ports are retained; transistor bodies and
  internal subcircuits are omitted. Removing the include outright would lose the
  Verilog-to-CDL pin mapping. The `lvs_blackbox_srams` setting remains opt-in.

The original foundry deck and external PDK libraries are not modified. The
Pegasus mixed-library hook now calls `lvs_translate.py` and replaces its library
imports with `sky130.pegasus.lvs.cdl` in the LVS run directory. A companion
`sky130.pegasus.lvs.json` records source hashes, converted calls, device-unit
conventions and remaining deck limitations. The original Verilog input and
gray-box directives remain in the control file.

Technology post-install processing patches the PVL into
`tech-sky130-cache/sky130.pegasus.lvs.pvl`. The in-memory TechJSON's Pegasus deck
path is `cache/sky130.pegasus.lvs.pvl`, resolved by Hammer before launching the
tool. The same TechJSON is saved as `sky130.tech.json` in that cache. The YAML
setting `technology.sky130.lvs_deck` continues to point to the original source;
each installation refreshes the edited copy from that source. An unrecognized
pwell calculation is rejected rather than silently patched.

## Translation behavior and remaining deck limits

Use a separate generated LVS view; keep the simulation netlists intact. This is
a structural conversion, not just replacing a prefix in text.

1. Read logical SPICE statements with `+` continuations, comments, `.SUBCKT`
   scopes and parameter defaults. Follow `.include` paths relative to each input
   file. In particular, the r+c model library includes additional diffusion
   resistor subcircuits. Resolve reachable dependencies, report missing masters,
   and reject conflicting definitions while honoring explicit custom overrides.
2. Preserve ordinary cell hierarchy, instance connections, bus pin ordering,
   bulk pins, supply aliases and explicit connectivity. Lower only recognized
   primitive calls. Do not rename arbitrary hierarchy or short VNB to VGND / VPB
   to VPWR globally: these are separate schematic terminals in many cells.
3. Convert primitive MOS `X... d g s b sky130_fd_pr__...` calls into deck-named
   `M... d g s b ...` devices, or generate equivalent parameterized LVS wrappers.
   Regular examples are `nfet_01v8`, `nfet_01v8_lvt`, `pfet_01v8`,
   `pfet_01v8_hvt`, `nfet_05v0_nvt`, `nfet_g5v0d10v5`, and
   `pfet_g5v0d10v5`. The existing `...__model` and binned `...__model.0` names are
   simulation model names, not the extracted deck's device subtypes.
4. Resolve parameter expressions or emit the syntax Pegasus accepts; importing
   ngspice `{l}` / `{w}` expressions produced undefined-parameter warnings here.
   For ordinary openPDKs MOS calls, unsuffixed L/W values are in microns. Emit
   explicit units (`L=0.150u W=0.740u`) or one consistently scaled CDL view.
   Preserve native SPICE/SI quantities and avoid scaling the Cadence CDL a
   second time. Primitive-wrapper parameters require evaluating SPICE suffixes
   before converting numeric microns: e.g. `w=290000u` means 0.29 microns. Area,
   perimeter, resistor dimensions, and capacitor dimensions
   need their own unit handling, not a blanket multiplication.
5. Preserve device multiplicity correctly. The SRAM bundle contains `nf=2` and
   `nf=4` as well as `nf=1`; IO cells contain substantial `m` multiplicity and
   some non-unit `mult`. Establish total-width versus per-finger-width semantics
   from the wrapper/model and extracted fingers. In this SRAM22 library, GDS
   confirms that W is per finger: the hook multiplies parallel MOS multiplicity
   by `nf`, retaining the specified per-finger W. The converted sense amplifier
   matches with both `nf=2` and `nf=4`; caller `m` also contributes. The IO
   wrappers use `mult` only in statistical mismatch expressions, not as
   electrical multiplicity; the openPDKs Netgen setup deletes that property.
   Likewise MIM `mf` is statistical and does not multiply geometric capacitance.
6. Map SRAM special devices to what the layout extractor actually recognizes.
   The saved bitcell report recognizes the special NFET geometry as
   `nfet_01v8` and its PFET geometry as `pfet_01v8_hvt`. Validate this on bitcell,
   replica, strap and end cells. Preserve the explicit 0.025-um dummy PFET
   connections until their extraction behavior is understood. ESD devices and
   MOS capacitors similarly need leaf-level validation.
7. Translate two-terminal diodes to the deck's diode names, preserving polarity.
   The supplied `DIO_PARAMS` macro multiplies geometric area/perimeter by
   `1e12/1e6`. To match those checked properties, the converter divides the
   wrapper's `area/perim` by `1e12/1e6` before emitting native `AREA/PJ`.
   For example `area=90E+12 perim=132E+6` becomes `AREA=90 PJ=132`.
   This deliberately follows this deck's property convention, rather than
   imposing the simulator's SI convention. The isolated diode test confirms
   parameter agreement; it still has a separate extraction/connectivity failure.
8. Translate MIM capacitors to the deck's geometric `cap_mim_m3__base` device
   with the proper terminals and L/W. Do not expand their simulation series-R
   networks and behavioral capacitance into LVS devices. Likewise, precision
   resistors need geometric devices such as `res_xhigh_po_0p69`, retaining bulk
   and terminal order; the simulation model's `RESHEAD/RESBODY` network is not
   what the deck extracts. Diffusion/metal resistors need subtype, property and
   intentional junction handling consistent with this deck.
9. Produce a manifest of source files, custom overrides, converted device
   counts, units and unresolved features. Fail on unknown reachable primitives.
   Unsupported extraction categories remain distinct schematic devices and
   produce warnings; they are not filtered or mapped onto unrelated devices.

Known limitations of this PVL include missing generic-poly resistor extraction,
missing extraction for the second MIM layer (`cap2m`), and missing L/W properties
on metal resistors. Its generic diffusion-resistor devices are two-terminal,
so simulation junction networks are not expanded into LVS devices. These
limitations are recorded in the manifest and remain visible during comparison.

A literal proof was run for `sky130_fd_sc_hs__inv_2`: its four `nf=1` calls were
converted to `M` devices named `pfet_01v8` and `nfet_01v8_lvt`, with explicit
micron L/W. Unchanged inverter GDS then **matched**, with clean extraction.
Further production-hook validation is summarized below.
The experiment and report are in `/tmp/sky130-lvs-audit/translated-inverter`.

## Isolated-well PVL defect

The small SRAM was tested directly from its supplied 7.3-MB GDS and the supplied
SPICE bundle, without ChipTop or Innovus. The selected PVL was
`/scratch/jfx/sky130_release_0.1.0/Sky130_LVS/sky130.lvs.v0.0_1.1.pvl`.

Its substrate calculation subtracts `ptub` from `pwell_all_1` but does not include
the isolated pwell in the final `pwell_all`. In the exported layers, `ptub` is the
SRAM interior; `pwell_all` is only an outer rim. All 11,480 NMOS gate regions lie
outside that bulk layer. Standalone and single-parent inverter tests extract
cleanly because they lack the macro's deep-nwell context.

| 64x24 SRAM test | Malformed-device report entries | NMOS bulk-gap polygons |
|---|---:|---:|
| Original PVL | 991 | 11,480 |
| Local isolated-well candidate | 0 | 0 |

`sky130-lvs-isolated-pwell.patch` contains the tested candidate. It adds `ptub`
back to the bulk union **and excludes the deep-nwell-associated nwell guard ring**
from the substrate region, so isolated and global bulk regions remain separated.
The debug output has two distinct bulk polygons after this change. Simply OR-ing
`ptub` into the original full background could join the two body domains.

This establishes a PVL compatibility defect for the supplied SRAM. The plugin
now applies this repair automatically to its cached deck, without changing
`example-sky130.yml`. It has not been qualified on the complete IO ring, PoR,
or chip. The converted small SRAM still has connectivity and dimensional
mismatches; the hook does not relax checks or waive them.
Flattening the SRAM did not fix extraction and is not a recommended workaround.

## Inspecting bulk coverage and VSS opens

After a fresh LVS run, launch `bash generated-scripts/view_lvs` in its run
directory. Select `CLKINVX1` in the comparison cell list and cross-probe its
VSS/open-pin discrepancy. Inspect gate, diffusion, bulk, tap and LI/M1 contact
connectivity separately.

The saved extracted `ChipTop_pin_xy.spi` makes the issue explicit:

```spice
.subckt CLKINVX1 1 2 3 4 5 6 7 8 9
M0 4 1 3 9 nfet_01v8 L=1.5e-07 W=7.6e-07
M1 4 1 2 2 pfet_01v8 L=1.5e-07 W=1.13e-06
```

MOS pins are D/G/S/B: the NMOS source is net 3 (VSS), while its body is net 9.
The source CDL ties both to VSS. Trace the p-tap contact through licon/LI/mcon to
the VSS rail, then inspect the `sconnect ptap pwell_all` result. A global-net
assignment in Innovus alone does not establish that physical connection.
Check the ChipTop stamping-conflict report as well: it lists rejected tap nets.
The five other failing Cadence cells have the same VSS/open-body signature.

For derived-layer inspection, pass `sky130-lvs-debug.pvl` **after** the normal
deck in a separate debug run. It explicitly selects its ERC checks and exports
`sky130-bulk-debug.gds`:

| GDS layer/datatype | Derived content |
|---|---|
| 900/0 | pwell_all |
| 901/0 | nfet_01v8 recognition regions |
| 902/0 | nfet_01v8_lvt recognition regions |
| 903/0 | nSourceDrain |
| 904/0 | ptap |
| 905/0 | localSub |
| 906/0 | ptub |
| 907/0 | recognized NMOS regions outside pwell_all |

Load this GDS with the original layout at the same origin. The debug run
intentionally produces ERC output, so its ERC status is not a signoff result.
Prepared runs are available under `/tmp/sky130-lvs-audit/sram64-debug` and
`sram64-bulk-candidate`; do not point old control files at original report paths
when creating additional experiments.

## Verification

- Focused Python regressions cover macro pin stubs, custom-cell precedence,
  replacement-GDS selection, technology physical-cell exclusions, strict master
  handling, Cadence ANTENNA selection, translation units/multiplicity and
  parameter scope, include cycles, unknown primitives, cached-deck selection,
  unchanged original collateral, and replacement of simulation imports.
- Auditing the patched control with the real imported libraries finds no
  duplicate subcircuits; the level shifter comes only from the custom extraction.
- The SRAM gray-box experiment is accepted by Pegasus and reports MATCH, with
  the expected empty internal networks. This validates interface-only boxing,
  not SRAM transistor correctness.
- With the production translation hook and cached PVL, the small SRAM matches
  33 subcells and has zero malformed-device extraction errors. Ten subcells
  still mismatch, and the top cannot run due to lower-level connectivity errors.
  Examples include genuine checked width differences (4.16 vs 4 microns in
  decoder logic), bitcell dimensions and decoder connectivity.
- Isolated IO inverter, diode, MIM1 and precision-resistor checks parse the
  generated native devices and bind the corresponding device types. MIM1 and
  the 28 precision resistors agree in parameters; their isolated layouts lack
  the schematic's named interface pins. The IO inverter has supply/body opens,
  and the diode layout extracts one device for two schematic devices. These
  checks do not claim complete leaf LVS passes.
- Integration artifacts are under `/tmp/sky130-lvs-conversion`, including the
  generated TechJSON/cache, converted CDL/manifest, and Pegasus reports.
- The broader existing `test_hooks.py` suite fails during fixture setup because
  `NopTechnology` lacks `gen_config`, which the existing Hammer driver calls.
  Those failures are independent of these changes.
