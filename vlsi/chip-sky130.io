(global
  version = 3
  io_order = "default"
)
(row_margin
  (top
    (io_row
      ring_number = 1
      margin = 0
    )
  )
  (right
    (io_row
      ring_number = 1
      margin = 0
    )
  )
  (bottom
    (io_row
      ring_number = 1
      margin = 0
    )
  )
  (left
    (io_row
      ring_number = 1
      margin = 0
    )
  )
)
(iopad
  (topleft
    (locals
      ring_number = 1
    )
    (inst
      name = "corner_topleft"
      orientation = R90
      cell = "sky130_ef_io__corner_pad"
    )
  )
  (topright
    (locals
      ring_number = 1
    )
    (inst
      name = "corner_topright"
      orientation = R0
      cell = "sky130_ef_io__corner_pad"
    )
  )
  (bottomright
    (locals
      ring_number = 1
    )
    (inst
      name = "corner_bottomright"
      orientation = R270
      cell = "sky130_ef_io__corner_pad"
    )
  )
  (bottomleft
    (locals
      ring_number = 1
    )
    (inst
      name = "corner_bottomleft"
      orientation = R180
      cell = "sky130_ef_io__corner_pad"
    )
  )
  (top
    (locals
      ring_number = 1
    )
    (inst
      orientation = R0
      offset = 381
      name = "nc_0/iocell"
    )
    (inst
      orientation = R0
      offset = 638
      name = "nc_1/iocell"
    )
    (inst
      orientation = R0
      offset = 895
      name = "nc_2/iocell"
    )
    (inst
      orientation = R0
      offset = 1152
      name = "nc_3/iocell"
    )
    (inst
      orientation = R0
      offset = 1410
      name = "nc_4/iocell"
    )
    (inst
      orientation = R0
      offset = 1667
      name = "clamp_n6_vssio"
      cell = "sky130_ef_io__vssio_hvc_clamped_pad"
    )
    (inst
      orientation = R0
      offset = 1919
      name = "nc_5/iocell"
    )
    (inst
      orientation = R0
      offset = 2364
      name = "nc_6/iocell"
    )
    (inst
      orientation = R0
      offset = 2621
      name = "iocell_clock_tap/iocell"
    )
    (inst
      orientation = R0
      offset = 2878
      name = "clamp_n10_vssa"
      cell = "sky130_ef_io__vssa_hvc_clamped_pad"
    )
    (inst
      orientation = R0
      offset = 3130
      name = "iocell_custom_boot/iocell"
    )
  )
  (right
    (locals
      ring_number = 1
    )
    (inst
      orientation = R270
      offset = 500
      name = "iocell_serial_tl_0_clock_in/iocell"
    )
    (inst
      orientation = R270
      offset = 726
      name = "nc_7/iocell"
    )
    (inst
      orientation = R270
      offset = 951
      name = "nc_8/iocell"
    )
    (inst
      orientation = R270
      offset = 1177
      name = "nc_9/iocell"
    )
    (inst
      orientation = R270
      offset = 1402
      name = "nc_10/iocell"
    )
    (inst
      orientation = R270
      offset = 1627
      name = "nc_11/iocell"
    )
    (inst
      orientation = R270
      offset = 1853
      name = "nc_12/iocell"
    )
    (inst
      orientation = R270
      offset = 2078
      name = "clamp_e13_vssa"
      cell = "sky130_ef_io__vssa_hvc_clamped_pad"
    )
    (inst
      orientation = R270
      offset = 2299
      name = "clamp_e12_vssd"
      cell = "sky130_ef_io__vssd_lvc_clamped3_pad"
    )
    (inst
      orientation = R270
      offset = 2519
      name = "clamp_e11_vdda"
      cell = "sky130_ef_io__vdda_hvc_clamped_pad"
    )
    (inst
      orientation = R270
      offset = 2739
      name = "nc_13/iocell"
    )
    (inst
      orientation = R270
      offset = 2965
      name = "nc_14/iocell"
    )
    (inst
      orientation = R270
      offset = 3190
      name = "nc_15/iocell"
    )
    (inst
      orientation = R270
      offset = 3416
      name = "nc_16/iocell"
    )
    (inst
      orientation = R270
      offset = 3641
      name = "nc_17/iocell"
    )
    (inst
      orientation = R270
      offset = 3871
      name = "nc_18/iocell"
    )
    (inst
      orientation = R270
      offset = 4092
      name = "clamp_e4_vdda"
      cell = "sky130_ef_io__vdda_hvc_clamped_pad"
    )
    (inst
      orientation = R270
      offset = 4312
      name = "nc_19/iocell"
    )
    (inst
      orientation = R270
      offset = 4538
      name = "clamp_e2_vccd"
      cell = "sky130_ef_io__vccd_lvc_clamped3_pad"
    )
    (inst
      orientation = R270
      offset = 4758
      name = "nc_20/iocell"
    )
    (inst
      orientation = R270
      name = "IO_FILLER_MANUAL_E_1"
      offset = 4518
      cell = "sky130_ef_io__com_bus_slice_20um"
    )
    (inst
      orientation = R270
      name = "IO_FILLER_MANUAL_E_2"
      offset = 2279
      cell = "sky130_ef_io__com_bus_slice_20um"
    )
  )
  (bottom
    (locals
      ring_number = 1
    )
    (inst
      orientation = R180
      offset = 394
      name = "clamp_s1_vssa"
      cell = "sky130_ef_io__vssa_hvc_clamped_pad"
    )
    (inst
      orientation = R180
      offset = 663
      name = "iocell_reset/iocell"
    )
    (inst
      orientation = R180
      offset = 932
      name = "iocell_clock/iocell"
    )
    (inst
      orientation = R180
      offset = 1206
      name = "clamp_s4_vssd"
      cell = "sky130_ef_io__vssd_lvc_clamped_pad"
    )
    (inst
      orientation = R180
      offset = 1475
      name = "iocell_jtag_TCK/iocell"
    )
    (inst
      orientation = R180
      offset = 1749
      name = "iocell_jtag_TMS/iocell"
    )
    (inst
      orientation = R180
      offset = 2023
      name = "iocell_jtag_TDI/iocell"
    )
    (inst
      orientation = R180
      offset = 2297
      name = "iocell_jtag_TDO/iocell"
    )
    (inst
      orientation = R180
      offset = 2571
      name = "iocell_jtag_reset/iocell"
    )
    (inst
      orientation = R180
      offset = 2845
      name = "clamp_s10_vssio"
      cell = "sky130_ef_io__vssio_hvc_clamped_pad"
    )
    (inst
      orientation = R180
      offset = 3114
      name = "clamp_s11_vdda"
      cell = "sky130_ef_io__vdda_hvc_clamped_pad"
    )
    (inst
      orientation = R180
      name = "IO_FILLER_RESET_TAP"
      offset = 738
      cell = "sky130_ef_io__com_bus_slice_20um"
    )
    (inst
      orientation = R180
      name = "IO_FILLER_MANUAL_S_2"
      offset = 1186
      cell = "sky130_ef_io__com_bus_slice_20um"
    )
    (inst
      orientation = R180
      name = "IO_FILLER_MANUAL_S_3"
      offset = 3264
      cell = "sky130_ef_io__com_bus_slice_20um"
    )
  )
  (left
    (locals
      ring_number = 1
    )
    (inst
      orientation = R90
      offset = 340
      name = "clamp_w22_vccd"
      cell = "sky130_ef_io__vccd_lvc_clamped_pad"
    )
    (inst
      orientation = R90
      offset = 551
      name = "clamp_w21_vddio"
      cell = "sky130_ef_io__vddio_hvc_clamped_pad"
    )
    (inst
      orientation = R90
      offset = 908
      name = "iocell_serial_tl_0_in_valid/iocell"
    )
    (inst
      orientation = R90
      offset = 1124
      name = "iocell_serial_tl_0_out_bits_phit/iocell"
    )
    (inst
      orientation = R90
      offset = 1340
      name = "iocell_serial_tl_0_in_bits_phit/iocell"
    )
    (inst
      orientation = R90
      offset = 1556
      name = "iocell_serial_tl_0_in_ready/iocell"
    )
    (inst
      orientation = R90
      offset = 1772
      name = "iocell_serial_tl_0_out_valid/iocell"
    )
    (inst
      orientation = R90
      offset = 1988
      name = "iocell_serial_tl_0_out_ready/iocell"
    )
    (inst
      orientation = R90
      offset = 2204
      name = "clamp_w13_vssd"
      cell = "sky130_ef_io__vssd_lvc_clamped3_pad"
    )
    (inst
      orientation = R90
      offset = 2415
      name = "clamp_w12_vdda"
      cell = "sky130_ef_io__vdda_hvc_clamped_pad"
    )
    (inst
      orientation = R90
      offset = 2626
      name = "iocell_uart_0_rxd/iocell"
    )
    (inst
      orientation = R90
      offset = 2842
      name = "iocell_uart_0_txd/iocell"
    )
    (inst
      orientation = R90
      offset = 3058
      name = "nc_21/iocell"
    )
    (inst
      orientation = R90
      offset = 3274
      name = "nc_22/iocell"
    )
    (inst
      orientation = R90
      offset = 3490
      name = "nc_23/iocell"
    )
    (inst
      orientation = R90
      offset = 3706
      name = "nc_24/iocell"
    )
    (inst
      orientation = R90
      offset = 3922
      name = "nc_25/iocell"
    )
    (inst
      orientation = R90
      offset = 4138
      name = "clamp_w4_vssa"
      cell = "sky130_ef_io__vssa_hvc_clamped_pad"
    )
    (inst
      orientation = R90
      offset = 4349
      name = "clamp_w3_vddio"
      cell = "sky130_ef_io__vddio_hvc_clamped_pad"
    )
    (inst
      orientation = R90
      offset = 4560
      name = "clamp_w2_vccd"
      cell = "sky130_ef_io__vccd_lvc_clamped3_pad"
    )
    (inst
      orientation = R90
      offset = 4771
      name = "nc_26/iocell"
    )
    (inst
      orientation = R90
      name = "IO_FILLER_MANUAL_W_1"
      offset = 415
      cell = "sky130_ef_io__com_bus_slice_20um"
    )
    (inst
      orientation = R90
      name = "IO_FILLER_MANUAL_W_2"
      offset = 2279
      cell = "sky130_ef_io__com_bus_slice_20um"
    )
    (inst
      orientation = R90
      name = "IO_FILLER_MANUAL_W_3"
      offset = 4635
      cell = "sky130_ef_io__com_bus_slice_20um"
    )
  )
)
