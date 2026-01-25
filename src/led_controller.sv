`default_nettype none

module led_controller #(
    parameter TICKS_100_HZ = 10_000_000 / 100
) (
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

wire reset_n;
reset reset (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .o_reset_n(reset_n)
);

// Divider for i_clk to derive 100ns ticks
reg [7:0] clock_divider;

typedef enum logic [3:0] {
    EFFECT_NONE = 0,
    EFFECT_CHASE = 1,
    EFFECT_PULSE = 2,
    EFFECT_CUSTOM = 3
} effect_t;
effect_t effect;

wire [15:0] rom_addr;
wire timer_100hz_strb;
wire timer_2hz_strb;


//reg [7:0] colors_indexed [0:11];
reg [7:0] num_leds;
reg [95:0] colors;
reg [1:0] num_colors;
reg led_strb;
reg [31:0] led_color;
reg [1:0] led_color_index;

wire effect_none_led_strb, effect_pulse_led_strb, effect_chase_led_strb,
    effect_custom_led_strb;
wire [1:0] effect_none_led_color, effect_chase_led_color,
    effect_custom_led_color;
wire effect_none_reset_strb, effect_pulse_reset_strb, effect_chase_reset_strb;

wire [31:0] effect_pulse_led_color;
wire rgbw_busy;

wire timer_10hz_strb;
wire spi_data_strb;
wire [7:0] spi_data;

wire flash_data_valid, flash_busy;
wire [7:0] flash_data;

always_comb begin
    led_strb = effect == EFFECT_CUSTOM ? effect_custom_led_strb : (effect == EFFECT_PULSE ? effect_pulse_led_strb :
        effect_chase_led_strb);
    led_color_index = effect == EFFECT_CUSTOM ? effect_custom_led_color : (
        effect_chase_led_color);
end

always @(*) begin
    if (effect == EFFECT_PULSE)
        led_color = effect_pulse_led_color;
    else begin
        case(led_color_index)
            0: led_color = colors[95:64];
            1: led_color = colors[63:32];
            2: led_color = colors[31:0];
            3: led_color = 0;
        endcase
    end
end

led_effect_pulse led_effect_pulse (
    .i_clk(i_clk),
    .i_reset_n(reset_n),
    .i_en(effect == EFFECT_PULSE),
    .i_led_busy(rgbw_busy),
    .i_num_leds(num_leds),
    .i_num_colors(num_colors),
    .i_timer(timer_10hz_strb),
    .i_colors(colors),
    .o_led_strb(effect_pulse_led_strb),
    .o_led_color(effect_pulse_led_color)
);

led_effect_chase led_effect_chase (
    .i_clk(i_clk),
    .i_reset_n(reset_n),
    .i_en(effect == EFFECT_CHASE || effect == EFFECT_NONE),
    .i_led_busy(rgbw_busy),
    .i_num_leds(num_leds),
    .i_num_colors(num_colors),
    .i_timer(timer_2hz_strb),
    .i_chase_en(effect == EFFECT_CHASE),
    .o_led_strb(effect_chase_led_strb),
    .o_led_color(effect_chase_led_color)
);

typedef enum logic [6:0] {
    REGISTER_EFFECT = 1,
    REGISTER_CHIP_ID_H = 2,
    REGISTER_CHIP_ID_L = 3,
    // Register 4 - 15 are colors
    REGISTER_NUM_LEDS = 16,
    REGISTER_NUM_COLORS = 17,
    REGISTER_CLOCK_DIVIDER = 18,
    REGISTER_FLASH_24_BIT = 19,
    REGISTER_CPU_RESET = 20 // Clears Flash cache and resets CPU
} register_t;


reg [7:0] register_address;
reg [7:0] register_data;
reg [7:0] spi_data_write;
reg spi_trigger_flash_read;
reg spi_data_write_strb;
reg flash_addr_width_24;
wire register_spi_write;
wire spi_tx_start_strb;
assign register_spi_write = register_address[7];

typedef enum logic [2:0] {
    WAIT_REGISTER = 0,
    PROCESS_DATA = 1,
    WAIT_DATA = 2
} spi_state_t;
spi_state_t spi_state;


reg [3:0] cpu_reset_counter;
reg cpu_reset_n;
reg led_reset_strb;

always_comb begin
    cpu_reset_n = cpu_reset_counter == 0;
end

always @(posedge i_clk) begin
    if (!reset_n) begin
        // Configure demo after reset
        effect <= EFFECT_CHASE;
        register_address <= 0;
        register_data <= 0;
        spi_data_write <= 0;
        spi_data_write_strb <= 0;
        spi_state <= WAIT_REGISTER;
        num_leds <= 30;
        spi_trigger_flash_read <= 0;
        colors <= {
            32'h00ff0000,
            32'hff000000,
            32'h0000ff00
        };
        num_colors <= 3;
        flash_addr_width_24 <= 1;
        cpu_reset_counter <= 0;
        led_reset_strb <= 0;

        // By default we assume a 50Mhz i_clk 
        clock_divider <= 5;
    end
    else begin
        if (cpu_reset_counter > 0 && !rgbw_busy)
            cpu_reset_counter <= cpu_reset_counter - 1;

        spi_trigger_flash_read <= 0;
        spi_data_write_strb <= 0;
        if (spi_tx_start_strb) begin
            spi_state <= WAIT_REGISTER;
        end

        if (spi_data_strb) begin
            case (spi_state)
                WAIT_REGISTER: begin
                    register_address <= spi_data;

                    if (spi_data[7])
                        spi_state <= WAIT_DATA;
                    else
                        spi_state <= PROCESS_DATA;
                end
                WAIT_DATA: begin
                    register_data <= spi_data;
                    spi_state <= PROCESS_DATA;
                end
                default: begin
                end
            endcase
        end

        if (spi_state == PROCESS_DATA) begin
            spi_data_write <= 0;
            spi_data_write_strb <= 1;

            spi_state <= WAIT_DATA;
            register_address <= register_address + 1;

            if (!register_address[7]) begin
                case (register_address[6:0])
                    REGISTER_EFFECT: begin
                        spi_data_write <= {4'b0, effect};
                    end
                    REGISTER_CHIP_ID_H: begin
                        spi_data_write <= 8'h69;
                    end
                    REGISTER_CHIP_ID_L: begin
                        spi_data_write <= 8'h25;
                    end
                    REGISTER_NUM_COLORS: begin
                        spi_data_write <= {6'b0, num_colors};
                    end
                    REGISTER_NUM_LEDS: begin
                        spi_data_write <= num_leds[7:0];
                    end
                    REGISTER_CLOCK_DIVIDER: begin
                        spi_data_write <= clock_divider;
                    end
                    REGISTER_FLASH_24_BIT: begin
                        spi_data_write <= {7'b0, flash_addr_width_24};
                    end
                    default: begin
                    end
                endcase

                if (register_address[6:0] >= 4 && register_address[6:0] < 16) begin
                    spi_data_write <= colors[95 - ((register_address[6:0] - 4) * 8)-:8];
                end
            end
            if (register_address[7]) begin
                case (register_address[6:0])
                    REGISTER_EFFECT: begin
                        `ifdef YOSYS
                            effect <= register_data[3:0];
                        `else
                            effect <= effect_t'(register_data[3:0]);
                        `endif
                    end
                    REGISTER_NUM_COLORS: begin
                        num_colors <= register_data[1:0];
                    end
                    REGISTER_NUM_LEDS: begin
                        num_leds <= register_data;
                    end
                    REGISTER_CLOCK_DIVIDER: begin
                        clock_divider <= register_data;
                    end
                    REGISTER_FLASH_24_BIT: begin
                        flash_addr_width_24 <= register_data[0];
                        cpu_reset_counter <= 10;
                    end
                    REGISTER_CPU_RESET: begin
                        cpu_reset_counter <= 10;
                    end
                    default: begin
                    end
                endcase

                if (register_address[6:0] >= 4 && register_address[6:0] < 16) begin
                    colors[95 - ((register_address[6:0] - 4) * 8)-:8] <= register_data[7:0];
                end
            end
        end
    end
end

wire flash_addr_valid;
wire [15:0] flash_addr;

// The cache is effective at around 32-64 bytes total (16-32 instructions),
// but there isn't enough room on a 2x2 to include this cache as well.
// Instead, XIP is used.
/*spi_flash_cache #(
    .CACHE_LINE_SIZE(8),
    .CACHE_LINES(2)
) flash (*/
spi_flash flash (
    .i_clk(i_clk),
    .i_reset_n(reset_n && cpu_reset_n),
    .i_addr_width_24(flash_addr_width_24),
    .i_addr_valid(flash_addr_valid),
    .i_addr(flash_addr),
    .o_data(flash_data),
    .o_data_valid(flash_data_valid),
    .i_miso(i_flash_spi_miso),
    .o_mosi(o_flash_spi_mosi),
    .o_sck(o_flash_spi_sck),
    .o_cs_n(o_flash_spi_ss_n),
    .o_busy(flash_busy)
);

localparam ROM_SIZE = 256;

wire rom_addr_strb;
cpu #(
    .ROM_SIZE(ROM_SIZE)
) cpu (
    .i_clk(i_clk),
    .i_reset_n(reset_n && cpu_reset_n),
    .i_num_leds(num_leds),
    .i_timer_100hz(timer_100hz_strb),
    .i_num_colors(num_colors),
    .i_colors(colors),
    .i_led_busy(rgbw_busy),
    .i_bus_data(flash_data),
    .i_bus_data_valid(flash_data_valid),
    .o_bus_addr(flash_addr),
    .o_bus_addr_valid(flash_addr_valid),
    .o_led_strb(effect_custom_led_strb),
    .o_led_color(effect_custom_led_color)
);


sk6812rgbw #(

) rgbw (
    .i_clk(i_clk),
    .i_clk_div(clock_divider),
    .i_reset_n(reset_n),
    .i_led_strb(led_strb),
    .i_led_color(led_color),
    .i_reset_strb(led_reset_strb),
    .o_busy(rgbw_busy),
    .o_data(o_data)
);

wire timer_2s_strb;
timer_counter #(
    .TICKS(8'd200),
    .TICK_WIDTH(8)
) timer_2s (
    .i_clk(i_clk),
    .i_strb(timer_100hz_strb),
    .i_reset_n(reset_n),
    .o_strb(timer_2s_strb)
);

timer #(
    .TICKS(TICKS_100_HZ),
    .TICK_WIDTH(32)
) timer_100hz (
    .i_clk(i_clk),
    .i_div(clock_divider),
    .i_reset_n(reset_n),
    .o_strb(timer_100hz_strb)
);

timer_counter #(
    .TICKS(4'd10),
    .TICK_WIDTH(4)
) timer_10hz (
    .i_clk(i_clk),
    .i_strb(timer_100hz_strb),
    .i_reset_n(reset_n),
    .o_strb(timer_10hz_strb)
);

timer_counter #(
    .TICKS(6'd50),
    .TICK_WIDTH(6)
) timer_2hz (
    .i_clk(i_clk),
    .i_strb(timer_100hz_strb),
    .i_reset_n(reset_n),
    .o_strb(timer_2hz_strb)
);

spi_slave spi_slave (
    .i_clk(i_clk),
    .i_reset_n(reset_n),
    .i_sck(i_spi_sck),
    .i_mosi(i_spi_mosi),
    .i_ss_n(i_spi_ss_n),
    .i_data(spi_data_write),
    .i_data_strb(spi_data_write_strb),
    .o_miso(o_spi_miso),
    .o_data_strb(spi_data_strb),
    .o_tx_start_strb(spi_tx_start_strb),
    .o_data(spi_data)
);

endmodule
