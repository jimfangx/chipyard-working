# Implement same-net quiet/main supply bindings on every connected IO slice.
# Instance names, locations and orientations come from the placed database;
# bridge endpoints come from the loaded LEF pins, not a padframe coordinate.
proc sky130_quiet_rect {rect} {
    if {[llength $rect] == 1} { set rect [lindex $rect 0] }
    if {[llength $rect] != 4} { error "Expected a rectangular IO supply shape: $rect" }
    return $rect
}

proc sky130_quiet_pin_rects {inst pin} {
    set layers [get_db $pin .pg_base_pin.physical_pins.layer_shapes -if {.layer.name == met4}]
    set result {}
    foreach shape [get_db $layers .shapes] {
        if {[get_db $shape .type] ne "rect"} {
            error "Quiet supply tie requires rectangular met4 pins on [get_db $inst .name]"
        }
        set local [sky130_quiet_rect [get_db $shape .rect]]
        lappend result [sky130_quiet_rect [get_transform_shapes -inst $inst -local_pt $local]]
    }
    return $result
}

proc sky130_quiet_bridge {quiet main} {
    # A 1 um bridge with 1 um overlap into both rails, on their shared axis.
    # Work in global coordinates so all orientations are handled identically.
    lassign $quiet qx0 qy0 qx1 qy1
    lassign $main mx0 my0 mx1 my1
    if {$qx0 < $mx1 && $mx0 < $qx1 && $qy0 < $my1 && $my0 < $qy1} {
        return [list 0 {}]
    }
    set xlo [expr {max($qx0,$mx0)}]
    set xhi [expr {min($qx1,$mx1)}]
    if {$xhi-$xlo >= 1.0 && min($qy1-$qy0,$my1-$my0) >= 1.0} {
        set x [expr {($xlo+$xhi)/2.0}]
        if {$qy1 <= $my0} { return [list [expr {$my0-$qy1}] [list [expr {$x-0.5}] [expr {$qy1-1.0}] [expr {$x+0.5}] [expr {$my0+1.0}]]] }
        if {$my1 <= $qy0} { return [list [expr {$qy0-$my1}] [list [expr {$x-0.5}] [expr {$my1-1.0}] [expr {$x+0.5}] [expr {$qy0+1.0}]]] }
    }
    set ylo [expr {max($qy0,$my0)}]
    set yhi [expr {min($qy1,$my1)}]
    if {$yhi-$ylo >= 1.0 && min($qx1-$qx0,$mx1-$mx0) >= 1.0} {
        set y [expr {($ylo+$yhi)/2.0}]
        if {$qx1 <= $mx0} { return [list [expr {$mx0-$qx1}] [list [expr {$qx1-1.0}] [expr {$y-0.5}] [expr {$mx0+1.0}] [expr {$y+0.5}]]] }
        if {$mx1 <= $qx0} { return [list [expr {$qx0-$mx1}] [list [expr {$mx1-1.0}] [expr {$y-0.5}] [expr {$qx0+1.0}] [expr {$y+0.5}]]] }
    }
    return {}
}

proc sky130_tie_quiet_vddio {} {
    set master sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_and_vssio_vssa_vssd_slice_20um
    set insts [get_db insts -if ".base_cell.name == $master"]
    set created 0
    set separate 0
    foreach inst $insts {
        set quiet [get_db $inst .pg_pins -if {.base_name == VDDIO_Q}]
        set main [get_db $inst .pg_pins -if {.base_name == VDDIO}]
        if {[llength $quiet] != 1 || [llength $main] != 1} {
            error "Missing/ambiguous IO supply pins on [get_db $inst .name]"
        }
        set net [get_db $main .net]
        set quiet_net [get_db $quiet .net]
        if {$net eq "" || $quiet_net eq ""} {
            error "Unbound IO supply pin on [get_db $inst .name]; apply CPF before physical ties"
        }
        if {$net ne $quiet_net} {
            incr separate
            continue
        }
        set best {}
        foreach qrect [sky130_quiet_pin_rects $inst $quiet] {
            foreach mrect [sky130_quiet_pin_rects $inst $main] {
                set candidate [sky130_quiet_bridge $qrect $mrect]
                if {$candidate ne "" && ($best eq "" || [lindex $candidate 0] < [lindex $best 0])} {
                    set best $candidate
                }
            }
        }
        if {$best eq ""} { error "No legal quiet/main met4 bridge on [get_db $inst .name]" }
        lassign $best gap rect
        if {$rect eq ""} { continue }
        # The qualified library has adjacent rails. Refuse an unexpectedly
        # long crossing rather than connecting through other macro pins.
        if {$gap > 1.5 + 0.001} { error "Quiet/main IO rail gap changed on [get_db $inst .name]: $gap" }
        set exists 0
        foreach wire [get_obj_in_area -obj_type special_wire -areas [list $rect] -layers {met4}] {
            if {[get_db $wire .net] ne $net} {
                error "Another net crosses the quiet supply bridge on [get_db $inst .name]"
            }
            if {[get_db $wire .type] ne "rect"} { continue }
            lassign [sky130_quiet_rect [get_db $wire .rect]] x0 y0 x1 y1
            lassign $rect rx0 ry0 rx1 ry1
            if {$x0 <= $rx0 && $y0 <= $ry0 && $x1 >= $rx1 && $y1 >= $ry1} { set exists 1; break }
        }
        if {!$exists} {
            create_shape -net [get_db $net .name] -layer met4 -rect $rect -status fixed
            incr created
        }
    }
    puts "Quiet IO supply ties: created $created; preserved $separate separately bound quiet supplies"
}
sky130_tie_quiet_vddio
