`timescale 1ns/1ps
`default_nettype none

module test_led_controller (
    input i_clk,
    input i_reset_n,

    // SPI
    input i_spi_sck,
    input i_spi_mosi,
    input i_spi_ss_n,
    output o_spi_miso,

    // SPI Flash
    output o_flash_spi_ss_n,
    output o_flash_spi_mosi,
    output o_flash_spi_sck,
    input i_flash_spi_miso,

    // SK6812RGBW
    output o_data
);

led_controller #(
    .TICKS_100_HZ(20)
) led_controller (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_spi_sck(i_spi_sck),
    .i_spi_mosi(i_spi_mosi),
    .i_spi_ss_n(i_spi_ss_n),
    .o_spi_miso(o_spi_miso),
    .o_flash_spi_sck(o_flash_spi_sck),
    .o_flash_spi_mosi(o_flash_spi_mosi),
    .o_flash_spi_ss_n(o_flash_spi_ss_n),
    .i_flash_spi_miso(i_flash_spi_miso),
    .o_data(o_data)
);

endmodule
