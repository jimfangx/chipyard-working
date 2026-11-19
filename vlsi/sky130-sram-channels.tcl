# Reject stale/narrow SRAM channels before placing standard cells or PG rails.
# Fully halo-covered gaps contain no standard-cell corridor and are allowed.
proc sky130_check_sram_channels {sram_insts minimum_x halo} {
    set boxes {}
    foreach inst $sram_insts {
        lappend boxes [list [get_db $inst .name] \
            [get_db $inst .bbox.ll.x] [get_db $inst .bbox.ll.y] \
            [get_db $inst .bbox.ur.x] [get_db $inst .bbox.ur.y]]
    }
    set bad {}
    set tolerance 0.001
    for {set i 0} {$i < [llength $boxes]} {incr i} {
        lassign [lindex $boxes $i] an ax0 ay0 ax1 ay1
        for {set j [expr {$i + 1}]} {$j < [llength $boxes]} {incr j} {
            lassign [lindex $boxes $j] bn bx0 by0 bx1 by1
            set overlap [expr {min($ay1,$by1) - max($ay0,$by0)}]
            set gap [expr {max($bx0-$ax1, $ax0-$bx1)}]
            if {$overlap > $tolerance && $gap > 2*$halo+$tolerance && $gap < $minimum_x-$tolerance} {
                lappend bad [list $an $bn $gap]
            }
        }
    }
    if {[llength $bad]} {
        foreach pair [lrange $bad 0 9] {
            lassign $pair a b gap
            puts "SRAM PG channel too narrow: $a <-> $b: gap=$gap um, required=$minimum_x um"
        }
        error "Found [llength $bad] narrow SRAM PG channels. Rerun macro placement without cached SRAM hardmacro constraints; fixed coordinates cannot honor the new spacing."
    }
    puts "SRAM PG channel spacing checked for [llength $boxes] macros (minimum x gap $minimum_x um)"
}
