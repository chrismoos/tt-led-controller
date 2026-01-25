`default_nettype none
`timescale 1ns / 1ps

module tb ();

  // Dump the signals to a FST file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    //#1;
  end

  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  // Individual SPI input signals for cocotb access
  reg i_spi_sck;
  reg i_spi_ss_n;
  reg i_spi_mosi;
  reg i_flash_spi_miso;

  // Output signal aliases for cocotb access
  wire o_flash_spi_ss_n;
  wire o_flash_spi_mosi;
  wire o_flash_spi_sck;
  wire o_led_data;
  wire o_spi_miso;

  // Signal to trigger clean simulation shutdown from cocotb
  reg finish_sim;

  // Initialize all registers to known values
  initial begin
    clk = 0;
    rst_n = 0;
    ena = 0;
    uio_in = 0;
    ui_in = 0;
    i_spi_sck = 0;
    i_spi_ss_n = 1;
    i_spi_mosi = 0;
    i_flash_spi_miso = 0;
    finish_sim = 0;
  end

  // Clean shutdown when finish_sim is set
  always @(posedge finish_sim) begin
    $finish;
  end

  // Construct ui_in from individual signals using always_comb
  always @(*) begin
    ui_in = {4'b0, i_flash_spi_miso, i_spi_mosi, i_spi_ss_n, i_spi_sck};
  end

  // Extract output signals from uo_out and uio_out
  assign o_flash_spi_ss_n = uo_out[0];
  assign o_flash_spi_mosi = uo_out[1];
  assign o_flash_spi_sck = uo_out[2];
  assign o_led_data = uo_out[3];
  assign o_spi_miso = uio_out[0];

  tt_um_chrismoos_led_controller user_project (
    .ui_in  (ui_in),
    .uo_out (uo_out),
    .uio_in (uio_in),
    .uio_out(uio_out),
    .uio_oe (uio_oe),
    .ena    (ena),
    .clk    (clk),
    .rst_n  (rst_n)
  );

endmodule
