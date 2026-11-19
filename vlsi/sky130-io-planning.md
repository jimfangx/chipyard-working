# Sky130 IO planning in CSV

Edit [the Caravel plan](example-sky130-pin-map.csv),
[the larger plan](example-sky130-pin-map-larger.csv), or start with
[the blank template](sky130-io-plan-template.csv). Pin/filler planning uses CSV;
the existing Hammer technology/floorplan configuration remains unchanged in
format. Import/export the plan through Google Sheets as ordinary CSV.

**The editable plans contain no micrometer measurements.** Describe pad order,
cell selection and filler relationships; the planner obtains cell sizes from
LEF and the available edge length from the floorplan.

The larger plan uses `sky130_ef_io__vccd_lvc_clamped_pad` and
`sky130_ef_io__vssd_lvc_clamped_pad` for its single VCCD/VSSD core supply pair.
The `clamped3` variants expose the alternate VCCD1/VSSD1 pair and were inherited
from the old larger YAML without a need for that pair. The Caravel plan retains
its original cell variants. The shared CPF binds VCCD/VCCD1 to VDD and
VSSD/VSSD1 to VSS; those bindings support the Caravel variants and do not
declare independent core voltage domains. Existing ordinary guard slices are
retained in the larger plan; they remain legal beside the plain clamps.

## Choosing placement intent

| Task | What to put in the CSV |
| --- | --- |
| Use the existing Caravel padframe | Set `layout=caravel` on each pad and choose its existing `slot`, e.g. S2. The technology-owned preset supplies the fixed sites. |
| Distribute pads for a different die | Use `layout=spread` and a positive `order` on each edge. The planner calculates spacing from die/corner sizes, actual cell widths and required filler space. Spread is the default for pads without a layout value. |
| Add a reset tap | A filler with `anchor=S2`, `placement=after`. |
| Guard a Caravel clamped3 pad | A filler anchored to its slot with `before` or `after`, on the required physical side. |
| Put a supply-access slice below PoR | A south filler with `anchor=por`, `placement=below`. The technology's existing PoR placement/routing relationship determines its position. |

`order` increases **left to right on N/S and bottom to top on E/W**. Spreadsheet
row order is immaterial. `before` means the lower-coordinate side; `after` means
the higher-coordinate side. These are global edge directions, independent of
the cell orientation. Fillers have no pad order or pitch slot; their anchors
determine their placement.

For example, these fields express pad and filler placement:

| name | kind | side | order | slot | layout | anchor | placement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| reset | pad | S | 2 | S2 | caravel | | |
| IO_FILLER_RESET_TAP | filler | S | | | | S2 | after |
| IO_FILLER_MANUAL_E_2 | filler | E | | | | E2 | before |
| IO_FILLER_POR_TAP | filler | S | | | | por | below |

The `io_cell` column selects the actual master. Its width is read from LEF,
including orientation: wrapped GPIOs are 80 um along the edge, not the 75 um
assumption used by the previous spreadsheet. No pad-width or pitch formula is
needed in Sheets. The spread planner keeps attached pads/fillers together,
reserves the PoR slice, respects corner extents, and uses the Sky130 placement
grid. It fails when the requested pads cannot fit; reduce the pad count or
increase the die size in the normal floorplan configuration.

The Caravel preset is intentionally fixed to the existing frame. Its numerical
sites are technology collateral in
[caravel-io-sites.csv](hammer/hammer/technology/sky130/extra/caravel-io-sites.csv),
not measurements to enter into each design's spreadsheet. Choose spread for a
different die size. The PoR access offsets similarly belong to the technology's
placement/routing integration; the CSV simply says `below por`. Changing that
macro integration requires validating those technology rules, rather than
adjusting a magic number in the sheet.

## Columns

Use one row per intended pad, filler or corner. Include every logical/NC pad;
counts never replicate rows or create RTL instances.

| Column | Meaning |
| --- | --- |
| `name` | Unique planning name; the top-level signal name for a system pad. Use distinct power names such as VDDIO_N2. |
| `kind` | `pad`, `filler`, or `corner`. |
| `category` | Pads use `system`, `power_core`, `power_io`, or `power_analog`. Fillers/corners use `physical`. Categories document intent; CPF/source connectivity supplies the electrical bindings. |
| `side` | N, E, S or W; corners use NW, NE, SE or SW. Include exactly one of each corner. |
| `order` | Positive, unique order on an edge for spread pads. Ignored by the fixed Caravel preset. |
| `slot` | Required site ID for Caravel; optional label/anchor alias for spread. Must match its side, e.g. E70. The label does not calculate pitch or override order. |
| `layout` | `caravel` or `spread` for pads. Blank defaults to spread. |
| `io_cell` | Explicit cell master. Dimensions come from LEF. |
| `direction` | input, output, inout (or input&output), power, ground or unused; blank where inapplicable. This is review metadata, not an RTL edit. |
| `instance` | Exact existing instance path or physical-instance name. Populated in both shipped plans to preserve Tcl/CPF references. |
| `anchor` | A row's name, slot or instance; or the special `por` anchor for a south supply slice. |
| `placement` | `before`/`after` abuts an anchor; `align_start`/`align_end` aligns edges for advanced use. `below` is the PoR supply-access rule. |
| `orientation` | Optional override. Defaults N=R0, E=R270, S=R180, W=R90; corners have their usual corresponding orientations. |
| `assigned_count`, `total_count` | Optional nonnegative review counts, assigned <= total. They do not instantiate cells or change geometry. |
| `needs_attention` | Optional yes/no or true/false review flag. Does not waive checks. |
| `remarks` | Free-text layout and supply-isolation notes. |

Keep the column names; column order is free. CSV quoting, commas/multiline
remarks, CRLF and a UTF-8 BOM are supported. Ordinary Sheets editing requires no
helper formulas or geometry columns.

Default system-pad instances are `iocell_<signal>/iocell`. Bus foo[0] maps to
`iocell_foo/iocell`; foo[N], N>0, maps to `iocell_foo_N/iocell`; reset/reset_io to
`iocell_reset/iocell`; nc_N to `nc_N/iocell`. An explicit `instance` wins.
Preserve physical naming conventions (`clamp_*`, `IO_FILLER_*`, `corner_*`) used
by CPF/Tcl, especially `IO_FILLER_RESET_TAP` and `IO_FILLER_POR_TAP` while using
these reset/PoR routing hooks. The PoR tap's `name` and `instance` must both be
`IO_FILLER_POR_TAP`, with `anchor=por` and `placement=below`. Its routing hook
accepts the ordinary or custom connected 20 um slice and checks orientation,
dimensions and via overlap. Keep any clamp-adjacent `IO_FILLER_MANUAL_S_3`
separate from that tap. Older plans still using that name below PoR must update
their CSV before using the renamed hook. Automatic Innovus fillers populate
other gaps.

## Normal P&R usage

Run your normal `make par` command. For an IO-enabled design, the project driver
automatically reads the selected CSV and writes `par-rundir/sky130-io-plan.io`
while preparing Innovus commands. The hook is registered after floorplan_design,
and its generated read_io_file command consumes that file before placing the
ring. No manual IO-generation step or pause between synthesis and P&R is needed.
The hook uses Hammer's already-loaded settings and active LEFs; it does not
independently read par-input.json.

The Makefiles and Hammer's dependency behavior are unchanged. If P&R has already
completed and you edit only the CSV, use your normal `redo-par` target to force
regeneration. Refresh old configuration snapshots when changing which CSV is
selected. IO generation is skipped for block-mode runs with use_io_cells=false.

## Optional standalone preview

From the repository root, use the matching design's Hammer JSON snapshot for
the floorplan and PDK path. This is only a convenience for previewing the IO file
outside P&R; the normal make flow needs no extra command or JSON input:

```bash
SKY130_PROJECT="vlsi/build/chipyard.harness.TestHarness.Sky130RocketConfig-ChipTop"
.conda-env/bin/python vlsi/sky130-io-plan.py \
  vlsi/example-sky130-pin-map.csv \
  --floorplan-json "$SKY130_PROJECT/par-input.json" \
  -o vlsi/chip-sky130.io
```

For the larger CSV, pass the larger design's floorplan snapshot, rather than
the small Rocket floorplan. `--lef FILE` can be repeated for custom IO libraries;
otherwise the CLI reads IO LEFs under the snapshot's sky130A path.

Optional `--resolved review.csv` writes a **computed** report with absolute
offsets and widths. Edit the intent plan, not that report. Optional
`--design-info path/to/design.sky130io.json` checks the exact logical signal/NC
instance set. Use matching collateral: the Caravel example contains 27 NC pads,
the larger example 62. Planning metadata does not instantiate logical pads.

The parser still accepts the older optional offset_um/width_um/spacing_um fields
and numeric anchor rows for advanced inputs/resolved reports. They are absent
from the editable examples and template and are not required for normal planning.
The former extra/gen-io-file.py and extra/gen-io-file-larger.py commands invoke
this same implementation.

## Mainline integration and validation

The two technology configurations select their respective plans through
`technology.sky130.io_plan_csv` with `prependlocal`. The driver uses the active
floorplan and technology-selected LEF files, regenerates
`par-rundir/sky130-io-plan.io` before read_io_file, and derives promoted signal
ports from that same plan. Persistent supply ports remain included.

The project driver supplies this behavior through its normal P&R hook; no
Makefile include, dependency file or Hammer-core change is required.
The larger project's current
use_io_cells=false block-mode switch is preserved: selecting a CSV alone does
not enable a ring or create logical IO cells.

The Caravel preview remains byte-identical to the preceding CSV-generated .io.
The larger example now distributes its pads from actual LEF widths and the die
boundary instead of retaining the old pitch/offset grid. It retains instance
names and filler relationships, including the PoR supply-access slice. Its
physical placements therefore change and require fresh P&R/LVS/DRC validation.

The planner validates cell sizes, unique names/instances/slots/orders,
references/cycles, pad/filler overlaps, corner extents and edge capacity. These
are placement checks, not rail-connectivity or physical DRC signoff. Existing
reset/PoR/rail-repair hooks retain their geometry and net checks.

The IO-planner and LVS regression suites pass 76 tests together. Both plans
also prepare successfully with real Hammer settings and selected LEFs in
isolated directories, without launching CAD. The larger preparation enables IO
only in a temporary hook-check configuration. No new Innovus/Pegasus result is
claimed for the redistributed larger plan.
