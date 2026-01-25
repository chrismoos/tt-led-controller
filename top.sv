`default_nettype none

module top (
    input clk_25mhz,
    input [6:0] btn,
    output user_programn,
    output reg [7:0] led,
    inout [27:0] gn,
    inout [27:0] gp
);

reg [31:0] reset_cycles;
reg reset_btn_n;

// local reset for modules
reg reset_n;

reg [31:0] init_cycles;

initial begin
    init_cycles <= 0;
    reset_cycles <= 0;
    reset_btn_n <= 1;
    reset_n <= 0;
end

assign user_programn = reset_btn_n;

always @(posedge clk_25mhz) begin
    init_cycles <= init_cycles + 1;

    if (init_cycles == 100) begin
        reset_n <= 1;
    end
end

always @(posedge clk_50) begin
    led <= 0;
    led[0] <= btn[0];
    if (btn[0])
        reset_cycles <= 0;
    else
        reset_cycles <= reset_cycles + 1;

    if (reset_cycles > $rtoi(25_000_000 * 0.01))
        reset_btn_n <= 0;
end

wire clk_50, clk_100;
wire pll_lock;

EHXPLLL#(
    .FEEDBK_PATH("CLKOP"),
    .PLLRST_ENA("ENABLED"),
    .STDBY_ENABLE("DISABLED"),
    .DPHASE_SOURCE("DISABLED"),
    .CLKOP_ENABLE("ENABLED"),
    .PLL_LOCK_MODE(0),
    .INT_LOCK_STICKY("ENABLED"),

    //  ecppll -i 25 --clkout0 100 --clkout1 20
    .CLKI_DIV(1),
    .CLKFB_DIV(4),
    .CLKOP_DIV(6),
    .CLKOS_DIV(12)
) pll(
    .RST(~reset_n),
    .CLKI(clk_25mhz),
    .CLKFB(clk_100),
    .CLKOP(clk_100),
    .CLKOS(clk_50),
    .ENCLKOP(0),
    .ENCLKOS(0),
    .ENCLKOS2(0),
    .ENCLKOS3(0),
    .STDBY(0),
    .PHASESEL1(0),
    .PHASESEL0(0),
    .PHASEDIR(0),
    .PHASESTEP(0),
    .PHASELOADREG(0),
    .PLLWAKESYNC(0),
    .LOCK(pll_lock)
);

wire spi_miso, spi_mosi, spi_sck, spi_ss_n;
wire flash_spi_miso, flash_spi_mosi, flash_spi_sck, flash_spi_ss_n;
wire rgbw_data;
assign gn[26] = rgbw_data;
assign gp[26] = rgbw_data;
//assign gp[26] = gp[18];
assign gn[25] = clk_50;

assign spi_miso = gn[15];
assign spi_mosi = gp[15];
assign spi_ss_n = gn[16];
assign spi_sck = gp[16];

assign flash_spi_ss_n = gn[18];
assign flash_spi_sck = gp[18];
assign flash_spi_mosi = gn[17];
assign flash_spi_miso = gp[17];

led_controller led_controller (
    .i_clk(clk_50),
    .i_reset_n(pll_lock),
    .i_spi_sck(spi_sck),
    .i_spi_mosi(spi_mosi),
    .i_spi_ss_n(spi_ss_n),
    .o_spi_miso(spi_miso),
    .o_data(rgbw_data),
    .o_flash_spi_sck(flash_spi_sck),
    .o_flash_spi_mosi(flash_spi_mosi),
    .o_flash_spi_ss_n(flash_spi_ss_n),
    .i_flash_spi_miso(flash_spi_miso)
);

endmodule
