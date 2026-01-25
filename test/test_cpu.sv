`timescale 1ns/1ps
`default_nettype none

module test_cpu (
    input i_clk,
    input i_reset_n,
    input i_timer_100hz,
    input [7:0] i_num_leds,
    input [1:0] i_num_colors,
    input [95:0] i_colors,
    input [7:0] i_bus_data,
    input i_bus_data_valid,
    input i_led_busy,
    output [15:0] o_bus_addr,
    output o_bus_addr_valid,
    output o_led_strb,
    output [1:0] o_led_color
);

cpu #(
    .ROM_SIZE(256)
) dut (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_timer_100hz(i_timer_100hz),
    .i_num_leds(i_num_leds),
    .i_num_colors(i_num_colors),
    .i_colors(i_colors),
    .i_bus_data(i_bus_data),
    .i_bus_data_valid(i_bus_data_valid),
    .i_led_busy(i_led_busy),
    .o_bus_addr(o_bus_addr),
    .o_bus_addr_valid(o_bus_addr_valid),
    .o_led_strb(o_led_strb),
    .o_led_color(o_led_color)
);

endmodule
