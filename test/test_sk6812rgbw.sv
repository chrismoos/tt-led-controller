`timescale 1ns/1ps
`default_nettype none

module test_sk6812rgbw (
    input i_clk,
    input i_reset_n,
    input [7:0] i_clk_div,
    input i_led_strb,
    input [31:0] i_led_color,
    input i_reset_strb,
    output o_data,
    output o_busy
);

sk6812rgbw dut (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_clk_div(i_clk_div),
    .i_led_strb(i_led_strb),
    .i_led_color(i_led_color),
    .i_reset_strb(i_reset_strb),
    .o_data(o_data),
    .o_busy(o_busy)
);

endmodule
