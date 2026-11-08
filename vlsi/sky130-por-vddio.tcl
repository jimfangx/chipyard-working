# Connect the existing PoR VDDIO met3 trunk to the met4 IO filler rail.
# Qualified for the saved Sky130RocketConfig placement and filler geometry.
proc sky130_connect_por_vddio {} {
    global sky130_por_vddio_via
    if {[info exists sky130_por_vddio_via]} { return }
    set por [get_db insts por]
    set filler [get_db insts IO_FILLER_MANUAL_S_3]
    if {[llength $por] != 1 || [llength $filler] != 1} {
        error "PoR VDDIO repair requires one por and one IO_FILLER_MANUAL_S_3"
    }
    if {[get_db $por .base_cell.name] ne "simple_por" || [string tolower [get_db $por .orient]] ne "mx"} {
        error "PoR VDDIO repair requires the expected simple_por master/orientation"
    }
    if {[get_db $filler .base_cell.name] ne "sky130_ef_io__com_bus_slice_20um" ||
        [string tolower [get_db $filler .orient]] ne "r180"} {
        error "PoR VDDIO repair requires the expected R180 com_bus_slice_20um filler"
    }
    lassign [lindex [get_db $por .location] 0] px py
    lassign [lindex [get_db $filler .bbox] 0] fx0 fy0 fx1 fy1
    if {abs($fx1-$fx0-20.0) > 0.001 || abs($fy1-$fy0-197.965) > 0.001} {
        error "PoR VDDIO repair filler dimensions changed"
    }
    set x [expr {$px-4.440}]
    # Local VDDIO met4 rail y=17.750..22.400, transformed by R180.
    set rail_lo [expr {$fy1-22.400}]
    set rail_hi [expr {$fy1-17.750}]
    set y [expr {($rail_lo+$rail_hi)/2.0}]
    # The selected 4x1 cut array has a 0.330 x 1.600 um metal enclosure.
    if {$x-0.165 < $fx0 || $x+0.165 > $fx1 ||
        $y-0.800 < $rail_lo || $y+0.800 > $rail_hi ||
        $y-0.800 < $py-70.395 || $y+0.800 > $py+1.875} {
        error "PoR VDDIO via does not fit the existing trunk/filler overlap"
    }
    set probe [list [list [expr {$x-0.01}] [expr {$y-0.01}] [expr {$x+0.01}] [expr {$y+0.01}]]]
    set wires [get_obj_in_area -obj_type special_wire -areas $probe -layers {met3}]
    set wires [get_db $wires -if ".net.name == VDDIO"]
    if {[llength $wires] != 1} { error "Expected one existing VDDIO met3 trunk at the repair point" }
    set existing [get_obj_in_area -obj_type special_via -areas $probe -layers {via3} -strict_via_inst_layer_check]
    if {[llength $existing]} {
        if {[llength [get_db $existing -if ".net.name == VDDIO"]] != [llength $existing]} {
            error "Another net has a via3 at the PoR VDDIO repair point"
        }
        set sky130_por_vddio_via [lindex $existing 0]
        puts "PoR VDDIO via3 already present at {$x $y}"
        return
    }
    set master [create_via_definition -via_rule M3M4_PR -row_column {4 1} \
        -cut_size {0.200 0.200} -cut_spacing {0.200 0.200} \
        -bottom_enclosure {0.065 0.100} -top_enclosure {0.065 0.100}]
    set sky130_por_vddio_via [create_via -via_def $master -location [list $x $y] \
        -net VDDIO -shape iowire -status fixed]
    if {$sky130_por_vddio_via eq ""} { error "Failed to create the PoR VDDIO via3" }
    puts "PoR VDDIO physical repair: via3 {$x $y}, 4x1 cuts, net VDDIO"
}
sky130_connect_por_vddio
