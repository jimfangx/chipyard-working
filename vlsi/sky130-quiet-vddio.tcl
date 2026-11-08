# One physical tie implements the CPF's VDDIO_Q -> VDDIO connection.
# Qualified for the custom 20 x 197.965 um filler used by this ChipTop IO ring.
# Local met4 rails: VDDIO_Q y=62.05..66.50; VDDIO y=68.00..92.965.
proc sky130_tie_quiet_vddio {} {
    global sky130_quiet_vddio_tie
    if {[info exists sky130_quiet_vddio_tie]} { return }
    set inst [get_db insts IO_FILLER_N_0]
    if {[llength $inst] != 1} { error "Expected one IO_FILLER_N_0 for the quiet supply tie" }
    set master sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_and_vssio_vssa_vssd_slice_20um
    if {[get_db $inst .base_cell.name] ne $master} { error "Quiet supply tie filler master changed" }
    if {[string tolower [get_db $inst .orient]] ne "r0"} { error "Quiet supply tie requires an R0 filler" }
    lassign [lindex [get_db $inst .bbox] 0] x0 y0 x1 y1
    if {abs($x1-$x0-20.0) > 0.001 || abs($y1-$y0-197.965) > 0.001} {
        error "Quiet supply tie filler dimensions changed: bbox {$x0 $y0 $x1 $y1}; expected 20 x 197.965 um"
    }
    set rect [list [expr {$x0+9.5}] [expr {$y0+65.5}] [expr {$x0+10.5}] [expr {$y0+69.0}]]
    set sky130_quiet_vddio_tie [create_shape -net VDDIO -layer met4 -rect $rect -status fixed]
    puts "VDDIO_Q physical tie: IO_FILLER_N_0 met4 $rect"
}
sky130_tie_quiet_vddio
