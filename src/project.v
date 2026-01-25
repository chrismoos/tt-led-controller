/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_chrismoos_led_controller (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // Assign unused pins
  genvar x;
  for(x = 1; x < 8; x++) begin
    assign uio_out[x] = 0;
    assign uio_oe[x] = 0;
  end
  for(x = 4; x < 8; x++) begin
    assign uo_out[x] = 0;
  end

  // List all unused inputs to prevent warnings
  wire _unused = &{ena};

  wire spi_ss_n;
  assign spi_ss_n = ui_in[1];

  assign uio_oe[0] = !spi_ss_n;

  led_controller led_controller (
    .i_clk(clk),
    .i_reset_n(rst_n),

    .i_spi_sck(ui_in[0]),
    .i_spi_ss_n(spi_ss_n),
    .i_spi_mosi(ui_in[2]),
    .o_spi_miso(uio_out[0]),

    .o_flash_spi_ss_n(uo_out[0]),
    .o_flash_spi_mosi(uo_out[1]),
    .o_flash_spi_sck(uo_out[2]),
    .i_flash_spi_miso(ui_in[3]),

    .o_data(uo_out[3])
  );

endmodule
