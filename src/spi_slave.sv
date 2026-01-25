module spi_slave (
    input i_clk,
    input i_sck,
    input i_mosi,
    input i_ss_n,
    input i_reset_n,
    input [7:0] i_data,
    input i_data_strb,
    output o_miso,
    output o_data_strb,
    output o_tx_start_strb,
    output [7:0] o_data
);

reg tx_start_strb;
wire sck, mosi, ss_n;
assign o_tx_start_strb = tx_start_strb;

reg miso;
assign o_miso = miso;

reg [3:0] data_bits;
reg [7:0] register;
reg [7:0] output_register;
assign o_data = register;
assign o_data_strb = data_bits == 8;

dff_sync sync_sck (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_data(i_sck),
    .o_data(sck)
);

dff_sync sync_mosi (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_data(i_mosi),
    .o_data(mosi)
);

dff_sync sync_ss_n (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_data(i_ss_n),
    .o_data(ss_n)
);

reg last_sck;
reg last_ss;

always @(posedge i_clk) begin
    if (!i_reset_n) begin
        register <= 0;
        output_register <= 0;
        last_sck <= 0;
        last_ss <= 1;
        data_bits <= 0;
        miso <= 0;
        tx_start_strb <= 0;
    end else begin
        last_sck <= sck;
        last_ss <= ss_n;
        tx_start_strb <= 0;

        if (data_bits == 8) begin
            data_bits <= 0;
            register <= 0;
        end
        if (i_data_strb) begin
            output_register <= i_data;
        end

        // Falling edge of SS
        if (!ss_n && last_ss) begin
            data_bits <= 0;
            register <= 0;
            output_register <= 0;
            miso <= 0;
            tx_start_strb <= 1;
        end

        if (!ss_n) begin
            // Rising edge of SCK
            if (!last_sck && sck) begin
                register <= {register[6:0], mosi};
                data_bits <= data_bits + 1;
            end

            // Falling edge of SCK
            if (last_sck && !sck) begin
                miso <= output_register[7];
                output_register <= {output_register[6:0], 1'b0};
            end
        end
    end
end

endmodule
