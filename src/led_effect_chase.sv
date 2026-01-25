module led_effect_chase (
    input i_clk,
    input i_en,
    input i_reset_n,
    input i_led_busy,
    input [7:0] i_num_leds,
    input [1:0] i_num_colors,
    input i_timer,
    input i_chase_en,
    output reg o_led_strb,
    output reg [1:0] o_led_color
);

reg finished;
reg [7:0] current_led;
reg [1:0] color;

reg [1:0] next_color;

always_comb begin
    if (o_led_color == i_num_colors - 1)
        next_color = 0;
    else
        next_color = o_led_color + 1;
end

always @(posedge i_clk) begin
    if (!i_reset_n) begin
        current_led <= 0;
        finished <= 0;
        o_led_color <= 0;
        o_led_strb <= 0;
    end
    else begin
        if (finished) begin
            if (!i_en) begin
                current_led <= 0;
                finished <= 0;
                o_led_color <= 0;
                o_led_strb <= 0;
            end
            if (i_timer) begin
                if (i_chase_en) begin
                    if (o_led_color == 0)
                        o_led_color <= i_num_colors - 1;
                    else
                        o_led_color = o_led_color - 1;
                end
                else begin
                    o_led_color <= 0;
                end
                
                finished <= 0;
                current_led <= 0;
            end
        end
        else begin
            if (i_en) begin
                if (!i_led_busy && !o_led_strb)
                    o_led_strb <= 1;

                if (i_led_busy && o_led_strb) begin
                    o_led_strb <= 0;
                    o_led_color <= next_color;
                    if (current_led == i_num_leds - 1) begin
                        finished <= 1;
                    end else begin
                        current_led <= current_led + 1;
                    end
                end
            end
        end
    end
end

endmodule
