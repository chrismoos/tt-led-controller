/*
 * Copyright (c) 2024 Chris Moos
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_chrismoos_6502_mcu (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  wire _unused = &{ena};

  // Input assignments
  wire [1:0] mux_sel = ui_in[1:0];
  wire i_rdy = ui_in[2];
  wire i_nmi_n = ui_in[3];
  wire i_irq_n = ui_in[4];
  wire i_so_n = ui_in[5];
  wire [1:0] gpio_in = ui_in[7:6];

  // MCU signals
  wire [7:0] mcu_bus_data_out;
  wire [15:0] mcu_bus_addr;
  wire mcu_rw;
  wire mcu_phi1;
  wire mcu_phi2;
  wire mcu_sync;
  wire [7:0] gpio_out;
  wire [7:0] gpio_oe;

  // Bus multiplexer
  wire [7:0] mux_data_out;
  wire mux_data_oe;

  bus_multiplexer bus_mux (
    .i_sel(mux_sel),
    .i_cpu_data(mcu_bus_data_out),
    .i_cpu_addr(mcu_bus_addr),
    .o_mux_data(mux_data_out),
    .o_mux_data_oe(mux_data_oe),
    .i_mux_data(uio_in)
  );

  // MCU
  mcu #(
    .START_PC_ENABLED(0),
    .START_PC(16'h0400),
    .LED_DEFAULT_CLOCK_DIV(2),
    .CPU_CLOCK_DIV_DEFAULT(8'h00),
    .UART_FIFO_DEPTH(2)
  ) mcu_inst (
    .i_clk(clk),
    .i_reset_n(rst_n),
    .i_bus_data(uio_in),
    .o_bus_data(mcu_bus_data_out),
    .o_bus_addr(mcu_bus_addr),
    .i_gpioa_input({6'b0, gpio_in}),        // GPIO[1:0] inputs
    .o_gpioa_output(gpio_out),              // GPIO[7:0] outputs
    .o_gpioa_oe(gpio_oe),
    .o_bus_rw(mcu_rw),
    .o_phi1(mcu_phi1),
    .o_phi2(mcu_phi2),
    .o_sync(mcu_sync),
    .i_rdy(i_rdy),
    .i_nmi_n(i_nmi_n),
    .i_irq_n_ext(i_irq_n),
    .i_so_n(i_so_n),
    .i_debug_sel(3'b0),
    .o_debug_data()
  );

  // Outputs - dedicated CPU control signals + GPIO outputs
  assign uo_out[0] = mcu_phi1;
  assign uo_out[1] = mcu_phi2;
  assign uo_out[2] = mcu_rw;
  assign uo_out[3] = mcu_sync;
  assign uo_out[7:4] = gpio_out[5:2];  // GPIO[5:2] outputs (output-only)

  assign uio_out = mux_data_out;
  assign uio_oe = {8{mux_data_oe}};

endmodule
