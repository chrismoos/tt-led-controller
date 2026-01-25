module cpu #(
    parameter ROM_SIZE = 32
) (
    input i_clk,
    input i_reset_n,
    input i_timer_100hz,
    input [7:0] i_num_leds,
    input [1:0] i_num_colors,
    input [95:0] i_colors,
    input [7:0] i_bus_data,
    input i_bus_data_valid,
    input i_led_busy,
    output reg [15:0] o_bus_addr,
    output reg o_bus_addr_valid,
    output reg o_led_strb,
    output reg [1:0] o_led_color
);

reg [15:0] pc;
reg [7:0] register_x;
reg [7:0] register_y;
reg status_zero;
reg status_negative;
reg [7:0] stall_counter;

reg [7:0] scratch_memory [0:15];

reg [15:0] fetch_pc;
reg [15:0] fetch_instruction;
reg [15:0] current_instruction;
reg [15:0] current_instruction_pc;
reg current_instruction_valid;
reg bus_hi_valid, fetch_pc_valid;

always @(posedge i_clk) begin
    if (!i_reset_n) begin
        fetch_pc <= 0;
        fetch_instruction <= 0;
        fetch_pc_valid <= 0;
        o_bus_addr <= 0;
        o_bus_addr_valid <= 1;
        bus_hi_valid <= 0;

        current_instruction <= 0;
        current_instruction_pc <= 0;
        current_instruction_valid <= 0;
    end else begin
        if (i_bus_data_valid) begin
            if (bus_hi_valid) begin
                fetch_instruction <= {fetch_instruction[15:8], i_bus_data};
                fetch_pc_valid <= 1;
                bus_hi_valid <= 0;
                o_bus_addr_valid <= 0;
            end
            else begin
                fetch_instruction <= {i_bus_data, 8'b0};
                o_bus_addr <= o_bus_addr + 1; 
                bus_hi_valid <= 1;
            end
        end

        if (fetch_pc_valid && fetch_pc == pc) begin
            current_instruction <= fetch_instruction;
            current_instruction_pc <= fetch_pc;
            current_instruction_valid <= 1;
            fetch_pc_valid <= 0;
            fetch_pc <= fetch_pc + 2;
            o_bus_addr_valid <= 1;
            o_bus_addr <= fetch_pc + 2;
        end

        // restart pipeline
        if (!o_bus_addr_valid && current_instruction_pc != pc && fetch_pc != pc) begin
            fetch_pc <= pc;
            fetch_pc_valid <= 0;
            o_bus_addr <= pc;
            o_bus_addr_valid <= 1;
        end
    end
end

wire [7:0] opcode;
assign opcode = current_instruction[15:8];

wire [7:0] operand;
assign operand = current_instruction[7:0];

reg led_writing, led_write_pending;
reg led_write_strb;
reg [1:0] led_write_color;

reg [7:0] operand_value;
reg [15:0] branch_offset;
always @(*) begin
    if ((opcode >= 8'b1010) && (opcode <= 8'b1111)) begin
        if (operand == 0)
            operand_value = i_num_leds;
        else if (operand == 1)
            operand_value = {6'b0, i_num_colors};
        else if (operand >= 8'h10 && operand <= 8'h20)
            operand_value = scratch_memory[operand[3:0]];
        else 
            operand_value = 0;
    end
    else begin
        operand_value = operand;
    end

    if (operand_value[7])
        branch_offset = {8'hff, operand_value};
    else
        branch_offset = {8'b0, operand_value};
end

wire [7:0] store_source = opcode == 8'b1110 ? register_y : 
    (opcode == 8'b1111 ? register_x : 0);

integer x;
always @(posedge i_clk) begin
    if (!i_reset_n) begin
        //instruction <= 0;
        pc <= 0;
        register_x <= 0;
        register_y <= 0;
        status_zero <= 0;
        status_negative <= 0;
        stall_counter <= 0;
        led_write_strb <= 0;
        led_write_color <= 0;
        //o_rom_addr_strb <= 1;

        for (x = 0; x < 16; x = x + 1) begin
            scratch_memory[x] <= 0;
        end

    end else begin
        led_write_strb <= 0;
        if (stall_counter > 0 && i_timer_100hz) begin
            stall_counter <= stall_counter - 1;
        end
        else if (led_writing || led_write_pending) begin
            // stall
        end
        else if (stall_counter == 0 && (!led_write_strb && !led_write_pending) && current_instruction_valid && current_instruction_pc == pc) begin
                pc <= pc + 2;

                // ldx
                if (opcode == 8'b0001) begin
                    register_x <= operand_value;
                    status_zero <= operand_value == 0;
                    status_negative <= operand_value[7];
                end
                if (opcode == 8'b1010) begin
                    register_x <= operand_value;
                    status_zero <= operand_value == 0;
                    status_negative <= operand_value[7];
                end

                // ldy
                if (opcode == 8'b0010) begin
                    register_y <= operand_value;
                    status_zero <= operand_value == 0;
                    status_negative <= operand_value[7];
                end
                if (opcode == 8'b1011) begin
                    register_y <= operand_value;
                    status_zero <= operand_value == 0;
                    status_negative <= operand_value[7];
                end

                // iny
                if (opcode == 8'b0101) begin
                    register_y <= register_y + 1;
                    status_zero <= register_y + 1 == 0;
                    status_negative <= (register_y + 1) > 128;
                end

                // inx
                if (opcode == 8'b0110) begin
                    register_x <= register_x + 1;
                    status_zero <= register_x + 1 == 0;
                    status_negative <= (register_x + 1) > 128;
                end

                // dey
                if (opcode == 8'b10011) begin
                    register_y <= register_y - 1;
                    status_zero <= register_y - 1 == 0;
                    status_negative <= (register_y - 1) > 128;
                end
                
                // dex
                if (opcode == 8'b10100) begin
                    register_x <= register_x - 1;
                    status_zero <= register_x - 1 == 0;
                    status_negative <= (register_x - 1) > 128;
                end

                // cpx
                if ((opcode == 8'b0011) || (opcode == 8'b1100)) begin
                    status_zero <= (register_x - operand_value) == 0;
                    status_negative <= (register_x - operand_value) > 128;
                end
                
                // cpy
                if ((opcode == 8'b0100) || (opcode == 8'b1101)) begin
                    status_zero <= (register_y - operand_value) == 0;
                    status_negative <= (register_y - operand_value) > 128;
                end

                // bne
                if(opcode == 8'b0111) begin
                    if (!status_zero) begin
                        pc <= pc + 2 + branch_offset;
                    end
                end

                // beq
                if (opcode == 8'b1000) begin
                    if (status_zero) begin
                        pc <= pc + 2 + branch_offset;
                    end
                end

                // bmi
                if (opcode == 8'b10001) begin
                    if (status_negative) begin
                        pc <= pc + 2 + branch_offset;
                    end
                end

                // bpl
                if (opcode == 8'b10010) begin
                    if (!status_negative) begin
                        pc <= pc + 2 + branch_offset;
                    end
                end

                // jmp
                if (opcode == 8'b10000) begin
                    pc <= {8'b0, operand_value};
                end

                // sty
                if ((opcode == 8'b1110) || (opcode == 8'b1111)) begin
                    if (operand == 2) begin
                        led_write_strb <= 1;
                        led_write_color <= store_source[1:0];
                    end
                    else if (operand >= 8'h10 && operand <= 8'h20)
                        scratch_memory[operand[3:0]] <= store_source;
                end

                // stall
                if (opcode == 8'b1001) stall_counter <= operand_value;
        end
    end
end


always @(posedge i_clk) begin
    if (!i_reset_n) begin
        led_writing <= 0;
        led_write_pending <= 0;
        o_led_color <= 0;
        o_led_strb <= 0;
    end else begin
        if (led_write_strb && !led_writing) begin
            led_write_pending <= 1;
        end

        if (!i_led_busy && led_write_pending) begin
            o_led_strb <= 1;
            o_led_color <= led_write_color;
            led_write_pending <= 0;
            led_writing <= 1;
        end

        if (i_led_busy)
            o_led_strb <= 0;

        if (!i_led_busy && led_writing && !o_led_strb) begin
            led_writing <= 0;
        end
    end
end

endmodule
