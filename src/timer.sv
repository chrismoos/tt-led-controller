module timer #(
    parameter TICKS,
    parameter TICK_WIDTH = 8
) (
    input i_clk,
    input i_reset_n,
    input [7:0] i_div,
    output reg o_strb
);

reg [TICK_WIDTH-1:0] counter;
reg [7:0] div_counter;

always @(posedge i_clk) begin
    if(!i_reset_n) begin
        o_strb <= 0;
        counter <= 0;
        div_counter <= 0;
    end else begin
        o_strb <= 0;

        div_counter <= div_counter + 1;
        if (div_counter == i_div - 1) begin
            div_counter <= 0;
            counter <= counter + 1;
        end

        if (counter == TICKS) begin
            o_strb <= 1;
            counter <= 0;
        end
    end
end

endmodule

module timer_counter #(
    parameter TICKS,
    parameter TICK_WIDTH = 8
) (
    input i_clk,
    input i_reset_n,
    input i_strb,
    output reg o_strb
);

reg [TICK_WIDTH-1:0] counter;

always_comb begin
    if (counter == TICKS)
        o_strb = 1;
    else
        o_strb = 0;
end

always @(posedge i_clk) begin
    if(!i_reset_n) begin
        counter <= 0;
    end else begin
        if (i_strb)
            counter <= counter + 1;

        if (counter == TICKS) begin
            counter <= 0;
        end
    end
end

endmodule
