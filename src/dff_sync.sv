module dff_sync (
    input i_clk,
    input i_reset_n,
    input i_data,
    output reg o_data
);

reg data;

always @(posedge i_clk) begin
    if (!i_reset_n) begin
        data <= 0;
        o_data <= 0;
    end
    else begin
        data <= i_data;
        o_data <= data;
    end
end

endmodule
