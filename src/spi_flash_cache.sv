module spi_flash_cache #(
    parameter SPI_CLOCK_PERIOD = 2, // due to cycle latency, 2 is the minimum 
    parameter ADDRESS_WIDTH = 16,
    parameter CPOL = 0,
    parameter CPHA = 0,
    parameter CACHE_LINE_SIZE = 64,
    parameter CACHE_LINES = 2
) (
    input i_clk,
    input i_reset_n,
    input i_addr_valid,
    input i_addr_width_24,
    input [15:0] i_addr,
    output reg [7:0] o_data,
    output reg o_data_valid,
    output o_busy,
    output o_sck,
    output o_mosi,
    output reg o_cs_n,
    input i_miso
);

localparam CACHE_LINES_WIDTH = $clog2(CACHE_LINES);
localparam CACHE_LINE_SIZE_WIDTH = $clog2(CACHE_LINE_SIZE);

reg [7:0] cache_lines [0:CACHE_LINES-1] [0:CACHE_LINE_SIZE-1];
reg [15:0] cache_line_address [0:CACHE_LINES-1];
reg cache_line_valid [0:CACHE_LINES-1];

reg [CACHE_LINES_WIDTH-1:0] cache_line_free;
reg cache_line_free_valid;
reg [15:0] cache_miss_addr;

reg [CACHE_LINES_WIDTH-1:0] last_new_cache_line;

reg [CACHE_LINE_SIZE_WIDTH-1:0] data_counter;

wire flash_busy;
wire flash_data_valid;
reg flash_addr_valid;
wire [7:0] flash_data;
reg [15:0] flash_addr;

typedef enum logic [2:0] {
    STATE_IDLE = 1,
    STATE_CACHE_HIT = 2,
    STATE_CACHE_MISS = 3,
    STATE_CACHE_MISS_WAIT = 4
} state_t;
state_t state;

always @(posedge i_clk) begin
    integer x, y;
    if (!i_reset_n) begin
        for (x = 0; x < CACHE_LINES; x++) begin
            cache_line_address[x] <= 0;
            cache_line_valid[x] <= 0;

            for (y = 0; y < CACHE_LINE_SIZE; y++) begin
                cache_lines[x][y] <= 0;
            end

        end

        state <= STATE_IDLE;
        o_data <= 0;
        o_data_valid <= 0;
        cache_line_free <= 0;
        cache_line_free_valid <= 0;
        cache_miss_addr <= 0;
        data_counter <= 0;
        last_new_cache_line <= CACHE_LINES - 1;
        flash_addr <= 0;
    end else begin
        o_data_valid <= 0;

        case (state)
            STATE_IDLE: begin
                if (i_addr_valid && !o_data_valid) begin
                    state <= STATE_CACHE_MISS;
                    cache_line_free_valid <= 0;
                    cache_miss_addr <= i_addr;
                    for (x = 0; x < CACHE_LINES; x++) begin
                        if (cache_line_valid[x] && i_addr >= cache_line_address[x] && i_addr < cache_line_address[x] + CACHE_LINE_SIZE) begin
                            o_data <= cache_lines[x][i_addr & (CACHE_LINE_SIZE - 1)];
                            //state <= STATE_CACHE_HIT;
                            o_data_valid <= 1;
                            state <= STATE_IDLE;
                        end
                        
                        if (!cache_line_valid[x]) begin
                            cache_line_free <= x[CACHE_LINES_WIDTH-1:0];
                            cache_line_free_valid <= 1;
                        end
                    end
                end
            end
            STATE_CACHE_HIT: begin
                // Not used for now, do right away to reduce latency
                o_data_valid <= 1;
                state <= STATE_IDLE;
            end
            STATE_CACHE_MISS: begin
                data_counter <= 0;
                flash_addr <= cache_miss_addr & ~((1 << $clog2(CACHE_LINE_SIZE)) - 1);
                flash_addr_valid <= 1;

                if (!cache_line_free_valid) begin
                    if (last_new_cache_line == CACHE_LINES - 1) begin
                        cache_line_free <= 0;
                        last_new_cache_line <= 0;
                    end
                    else begin
                        cache_line_free <= last_new_cache_line + 1;
                        last_new_cache_line <= last_new_cache_line + 1;
                    end
                end

                state <= STATE_CACHE_MISS_WAIT;
            end
            STATE_CACHE_MISS_WAIT: begin
                if (flash_data_valid) begin
                    data_counter <= data_counter + 1;

                    cache_lines[cache_line_free][data_counter] <= flash_data;

                    if (data_counter == CACHE_LINE_SIZE - 1) begin
                        flash_addr_valid <= 0;

                        cache_line_valid[cache_line_free] <= 1;
                        cache_line_address[cache_line_free] <= flash_addr;
                        o_data <= cache_lines[cache_line_free][cache_miss_addr & (CACHE_LINE_SIZE - 1)];

                        state <= STATE_CACHE_HIT;
                    end
                end
            end
            default: begin
            end
        endcase
    end
end
assign o_busy = flash_busy || state != STATE_IDLE;

spi_flash #(
    .SPI_CLOCK_PERIOD(SPI_CLOCK_PERIOD),
    .CPOL(CPOL),
    .CPHA(CPHA)
) flash (
    .i_clk(i_clk),
    .i_reset_n(i_reset_n),
    .i_addr_valid(flash_addr_valid),
    .i_addr(flash_addr),
    .i_addr_width_24(i_addr_width_24),
    .o_data(flash_data),
    .o_data_valid(flash_data_valid),
    .o_busy(flash_busy),
    .o_sck(o_sck),
    .o_mosi(o_mosi),
    .o_cs_n(o_cs_n),
    .i_miso(i_miso)
);

endmodule
