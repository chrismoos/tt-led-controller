module spi_master #(
    parameter SPI_CLOCK_PERIOD = 2,
    parameter CPOL = 0,
    parameter CPHA = 0
) (
    input i_clk,
    input i_reset_n,
    output reg o_sck,
    output reg o_mosi,
    input i_miso,
    
    input i_tx_en,
    input [7:0] i_tx_data,
    output reg [7:0] o_rx_data,
    output reg o_rx_data_valid,
    output reg o_busy
);

reg [7:0] sck_counter;
reg sck, sck_final;
always_comb begin
    sck_final = i_tx_en ? sck : sck_counter > 0 && sck;
    o_sck = CPOL ? !sck_final : sck_final;
end

reg [3:0] bit_counter;
reg tx_done;
reg [7:0] tx_data;
reg active;

always @(posedge i_clk) begin
    if (!i_reset_n) begin
        o_mosi <= 0;
        sck_counter <= 0;
        bit_counter <= 0;
        o_busy <= 0;
        tx_done <= 0;
        o_rx_data <= 0;
        sck <= 0;
        active <= 0;
        o_rx_data_valid <= 0;
        tx_data <= 0;
    end else begin
        o_rx_data_valid <= 0;
        tx_done <= 0;

        if (!i_tx_en) begin
            active <= 0;
        end

        if (!o_busy )
            sck <= 0;
        else begin
            sck <= sck_counter == (SPI_CLOCK_PERIOD / 2) - 1 ? !sck : sck;
            sck_counter <= sck_counter + 1;
            if (sck_counter == (SPI_CLOCK_PERIOD / 2) - 1) begin
                sck_counter <= 0;

            end
            if ((!active || !i_tx_en) && sck_counter == (SPI_CLOCK_PERIOD / 2) - 1) begin
                o_busy <= 0;
                sck <= 0;
            end
        end

        if (o_busy) begin
            // at an edge
            if (sck_counter == (SPI_CLOCK_PERIOD / 2) - 1) begin
                // falling
                if(!CPHA == sck) begin
                    if (bit_counter == 1) begin
                        o_mosi <= i_tx_data[7];
                        tx_data <= {tx_data[6:0], 1'b0};
                    end
                    else begin
                        o_mosi <= tx_data[7];
                        tx_data <= {tx_data[6:0], 1'b0};
                    end
                end
                else begin
                    o_rx_data <= {o_rx_data[6:0], i_miso};
                    bit_counter <= bit_counter + 1;
                    if (bit_counter == 8) begin
                        bit_counter <= 1;
                        o_rx_data_valid <= 1;
                        tx_done <= 1;
                        tx_data <= i_tx_data;
                    end
                end
            end
        end

        // start transaction
        if (i_tx_en && !o_busy) begin
            sck_counter <= 0;
            o_busy <= 1;
            bit_counter <= 0;
            tx_done <= 0;
            tx_data <= i_tx_data;
            active <= 1;

            if (!CPHA) begin
                o_mosi <= i_tx_data[7];
                tx_data <= {i_tx_data[6:0], 1'b0};
            end else
                tx_data <= i_tx_data;

            bit_counter <= 1;
        end
    end
end

endmodule
