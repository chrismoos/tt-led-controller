module reset (
    input i_clk,
    input i_reset_n,
    output o_reset_n
);

reg reset1, reset2;
assign o_reset_n = reset2;

always @(posedge i_clk or negedge i_reset_n) begin
    if (!i_reset_n) begin
        reset1 <= 0;
        reset2 <= 0;
    end
    else begin
        reset1 <= i_reset_n;
        reset2 <= reset1;
    end
end

endmodule
