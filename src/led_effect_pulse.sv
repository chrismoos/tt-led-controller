module led_effect_pulse (
    input i_clk,
    input i_en,
    input i_reset_n,
    input i_led_busy,
    input [7:0] i_num_leds,
    input [1:0] i_num_colors,
    input [95:0] i_colors,
    input i_timer,
    output reg o_led_strb,
    output reg [31:0] o_led_color
);

reg finished;
reg [7:0] current_led;
reg [1:0] color_index;
reg [4:0] brightness;

reg fade_out;

typedef enum logic [1:0] {
    STATE_CALC_COLOR = 0,
    STATE_RUN = 1
} state_t;
state_t state;

reg [31:0] calc_color;
wire [31:0] calc_color_out;
wire calc_color_valid;
reg color_strb;
color_brightness color_1 (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_color(calc_color),
    .i_strb(color_strb),
    .i_brightness(brightness),
    .o_color(calc_color_out),
    .o_valid(calc_color_valid)
);

always @(*) begin
    case (color_index)
        0:
            calc_color = i_colors[95:64];
        1:
            calc_color = i_colors[63:32];
        2:
            calc_color = i_colors[31:0];
        default:
            calc_color = 0;
    endcase
end

reg [1:0] next_color_index;
always_comb begin
    if (color_index == i_num_colors - 1)
        next_color_index = 0;
    else next_color_index = color_index + 1;
end

localparam [7:0] fade_step = 5;

always @(posedge i_clk) begin
    if (!i_reset_n || (finished && !i_en)) begin
        current_led <= 0;
        color_index <= 0;
        brightness <= 8;
        fade_out <= 0;
        finished <= 0;
        state <= STATE_CALC_COLOR;
        color_strb <= 1;
        o_led_strb <= 0;
        o_led_color <= 0;
    end
    else begin
        if (i_en) begin
            color_strb <= 0;

            if (state == STATE_CALC_COLOR) begin
                if (calc_color_valid) begin
                    state <= STATE_RUN;
                    color_strb <= 0;
                end
            end
            else begin
                if (finished && i_timer) begin
                    finished <= 0;
                    current_led <= 0;

                    if (fade_out) begin
                        brightness <= brightness - 1;
                        if (brightness == 0) begin
                            fade_out <= 0;
                            brightness <= 0;
                        end
                    end else begin
                        brightness <= brightness + 1;
                        if (brightness == 16) begin
                            fade_out <= 1;
                            brightness <= 16;
                        end
                    end
                end
                if (!i_led_busy && !o_led_strb && !finished && calc_color_valid) begin
                    o_led_color <= calc_color_out;
                    o_led_strb <= 1;
                end

                if (i_led_busy && o_led_strb && !finished) begin
                    o_led_strb <= 0;
                    current_led <= current_led + 1;
                    color_index <= next_color_index;
                    state <= STATE_CALC_COLOR;
                    color_strb <= 1;
                    if (current_led >= i_num_leds - 1) begin
                        finished <= 1;
                    end
                end
            end
        end
    end
end

endmodule

module color_brightness (
    input i_clk,
    input i_reset_n,
    input i_strb,
    input [31:0] i_color,
    input [4:0] i_brightness,  // 0-15 range
    output reg [31:0] o_color,
    output reg o_valid
);

reg [1:0] counter;
wire [7:0] current_color = counter == 0 ? i_color[31:24] :
    (counter == 1 ? i_color[23:16] : (counter == 2 ? i_color[15:8] : i_color[7:0]));
wire [11:0] r_mult = current_color * i_brightness;


reg active;

always @(posedge i_clk) begin
    if (!i_reset_n) begin
        o_valid <= 0;
        o_color <= 0;
        active <= 0;
        counter <= 0;
    end else begin
            counter <= counter + 1;
            if (i_strb && !active) begin
                counter <= 0;
                o_color <= 0;
                active <= 1;
                o_valid <= 0;
            end
            if (active) begin
                if (counter == 0)
                    o_color[31:24] <= r_mult[11:4];
                else if (counter == 1)
                    o_color[23:16] <= r_mult[11:4];
                else if (counter == 2)
                    o_color[15:8] <= r_mult[11:4];
                else if (counter == 3) begin
                    o_color[7:0] <= r_mult[11:4];
                    o_valid <= 1;
                    active <= 0;
                end
            end
    end
end


endmodule
