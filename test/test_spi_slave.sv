`timescale 1ns/1ps
`default_nettype none

module test_spi_slave (
    input i_clk,
    input i_reset_n,
    input i_sck,
    input i_mosi,
    input i_ss_n,
    input [7:0] i_data,
    input i_data_strb,
    output o_miso,
    output o_data_strb,
    output o_tx_start_strb,
    output [7:0] o_data
);

spi_slave dut (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_sck(i_sck),
    .i_mosi(i_mosi),
    .i_ss_n(i_ss_n),
    .i_data(i_data),
    .i_data_strb(i_data_strb),
    .o_miso(o_miso),
    .o_data_strb(o_data_strb),
    .o_tx_start_strb(o_tx_start_strb),
    .o_data(o_data)
);

endmodule
