`timescale 1ns/1ps
`default_nettype none

module test_spi_master (
    input i_clk,
    input i_reset_n,
    output o_sck,
    output o_mosi,
    input i_miso,
    input i_tx_en,
    input [7:0] i_tx_data,
    output [7:0] o_rx_data,
    output o_rx_data_valid,
    output o_busy
);

spi_master #(
    .SPI_CLOCK_PERIOD(2),
    .CPOL(0),
    .CPHA(0)
) dut (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .o_sck(o_sck),
    .o_mosi(o_mosi),
    .i_miso(i_miso),
    .i_tx_en(i_tx_en),
    .i_tx_data(i_tx_data),
    .o_rx_data(o_rx_data),
    .o_rx_data_valid(o_rx_data_valid),
    .o_busy(o_busy)
);

endmodule
