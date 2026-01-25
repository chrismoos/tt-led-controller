`timescale 1ns/1ps
`default_nettype none

module test_spi_flash (
    input i_clk,
    input i_reset_n,
    input i_addr_width_24,
    input i_addr_valid,
    input [15:0] i_addr,
    output [7:0] o_data,
    output o_data_valid,
    output o_busy,
    output o_sck,
    output o_mosi,
    output o_cs_n,
    input i_miso
);

spi_flash #(
    .SPI_CLOCK_PERIOD(2),
    .CPOL(0),
    .CPHA(0)
) dut (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_addr_width_24(i_addr_width_24),
    .i_addr_valid(i_addr_valid),
    .i_addr(i_addr),
    .o_data(o_data),
    .o_data_valid(o_data_valid),
    .o_busy(o_busy),
    .o_sck(o_sck),
    .o_mosi(o_mosi),
    .o_cs_n(o_cs_n),
    .i_miso(i_miso)
);

endmodule
