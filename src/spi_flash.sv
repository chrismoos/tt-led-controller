module spi_flash #(
    parameter SPI_CLOCK_PERIOD = 2,
    parameter CPOL = 0,
    parameter CPHA = 0 
) (
    input i_clk,
    input i_reset_n,
    input i_addr_width_24,
    input i_addr_valid,
    input [15:0] i_addr,
    output [7:0] o_data,
    output reg o_data_valid,
    output o_busy,
    output o_sck,
    output o_mosi,
    output reg o_cs_n,
    input i_miso
);

`define READ_INSTRUCTION 8'b00000011

typedef enum logic [2:0] {
    STATE_IDLE = 0,
    STATE_INSTRUCTION = 1,
    STATE_ADDRESS_HI2 = 2,
    STATE_ADDRESS_HI = 3,
    STATE_ADDRESS_LO = 4,
    STATE_DATA = 5,
    STATE_DATA_READ = 6
} state_t;

state_t state;

reg [15:0] addr;
reg [7:0] spi_tx_data;
reg spi_tx_en;

assign o_busy = state != STATE_IDLE;

wire [7:0] spi_rx_data;
assign o_data = spi_rx_data;
wire spi_busy, rx_data_valid;

reg [7:0] cs_delay_counter;

localparam CS_DELAY = SPI_CLOCK_PERIOD * 2;

//assign spi_tx_en = (i_addr_valid && state != STATE_INSTRUCTION && state != STATE_IDLE) || (!i_addr_valid && state == STATE_DATA_READ);

always_comb begin
    if(state == STATE_ADDRESS_HI2 || state == STATE_ADDRESS_HI || state == STATE_ADDRESS_LO || state == STATE_DATA)
        spi_tx_en = 1;
    else if (state == STATE_DATA_READ)
        spi_tx_en = i_addr_valid;
    else 
        spi_tx_en = 0;
end

always @(posedge i_clk) begin
    if (!i_reset_n) begin
        state <= STATE_IDLE;
        addr <= 0;
        spi_tx_data <= 0;
        o_cs_n <= 1;
        o_data_valid <= 0;
        cs_delay_counter <= 0;
    end else begin
        o_data_valid <= 0;

        if (!i_addr_valid) begin
            state <= STATE_IDLE;

            if (cs_delay_counter == 0)
                cs_delay_counter <= CS_DELAY;
        end

        if (cs_delay_counter > 0)
            cs_delay_counter <= cs_delay_counter - 1;

        case (state) 
            STATE_IDLE: begin
                if (!spi_busy && !o_cs_n && cs_delay_counter == (CS_DELAY / 2)) begin
                    o_cs_n <= 1;
                end
                else if (i_addr_valid && !spi_busy && o_cs_n && cs_delay_counter == 0) begin
                    state <= STATE_INSTRUCTION;
                    addr <= i_addr;
                    o_cs_n <= 0;
                    cs_delay_counter <= CS_DELAY / 2;
                end
            end
            STATE_INSTRUCTION: begin
                if (!spi_busy && cs_delay_counter == 0) begin
                    spi_tx_data <= `READ_INSTRUCTION;

                    if (i_addr_width_24)
                        state <= STATE_ADDRESS_HI2;
                    else
                        state <= STATE_ADDRESS_HI;
                end
            end
            STATE_ADDRESS_HI2: begin
                spi_tx_data <= 0;
                if (rx_data_valid) begin
                    state <= STATE_ADDRESS_HI;
                end
            end
            STATE_ADDRESS_HI: begin
                spi_tx_data <= addr[15:8];
                if (rx_data_valid) begin
                    state <= STATE_ADDRESS_LO;
                end
            end
            STATE_ADDRESS_LO: begin
                spi_tx_data <= addr[7:0];
                if (rx_data_valid) begin
                    state <= STATE_DATA;
                end
            end
            STATE_DATA: begin
                spi_tx_data <= 0;
                if (rx_data_valid) begin
                    state <= STATE_DATA_READ;
                end
            end
            STATE_DATA_READ: begin
                if (rx_data_valid) begin
                    o_data_valid <= 1;
                end
            end
            default:
                state <= STATE_IDLE;
        endcase
    end
end

spi_master #(
    .SPI_CLOCK_PERIOD(SPI_CLOCK_PERIOD),
    .CPOL(CPOL),
    .CPHA(CPHA)
) master (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_miso(i_miso),
    .o_mosi(o_mosi),
    .o_sck(o_sck),
    .i_tx_en(spi_tx_en),
    .i_tx_data(spi_tx_data),
    .o_rx_data(spi_rx_data),
    .o_rx_data_valid(rx_data_valid),
    .o_busy(spi_busy)
);

endmodule
