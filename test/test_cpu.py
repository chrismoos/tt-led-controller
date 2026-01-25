import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ClockCycles, RisingEdge


async def init_dut(dut):
    """Initialize DUT signals to default state."""
    dut.i_timer_100hz.value = 0
    dut.i_num_leds.value = 10
    dut.i_num_colors.value = 3
    dut.i_colors.value = 0
    dut.i_led_busy.value = 0
    dut.i_bus_data.value = 0
    dut.i_bus_data_valid.value = 0


async def start_clock_and_reset(dut, clock_period=0.02):
    """Start clock and perform reset sequence."""
    clk = Clock(dut.i_clk, clock_period, 'us')
    cocotb.start_soon(clk.start())

    await init_dut(dut)
    await FallingEdge(dut.i_clk)
    dut.i_reset_n.value = 0
    await ClockCycles(dut.i_clk, 5)
    dut.i_reset_n.value = 1
    await ClockCycles(dut.i_clk, 2)


async def feed_instruction(dut, opcode, operand):
    """Feed a 16-bit instruction to the CPU byte-by-byte.

    The CPU fetches high byte (opcode) first, then low byte (operand).
    """
    # Wait for CPU to request first byte (high byte / opcode)
    while dut.o_bus_addr_valid.value != 1:
        await ClockCycles(dut.i_clk, 1)

    # Feed high byte (opcode)
    dut.i_bus_data.value = opcode
    dut.i_bus_data_valid.value = 1
    await ClockCycles(dut.i_clk, 1)
    dut.i_bus_data_valid.value = 0
    await ClockCycles(dut.i_clk, 1)

    # Feed low byte (operand)
    dut.i_bus_data.value = operand
    dut.i_bus_data_valid.value = 1
    await ClockCycles(dut.i_clk, 1)
    dut.i_bus_data_valid.value = 0
    await ClockCycles(dut.i_clk, 1)


async def execute_instruction(dut, opcode, operand):
    """Feed an instruction and wait for it to execute."""
    await feed_instruction(dut, opcode, operand)
    # Wait for instruction to be processed
    await ClockCycles(dut.i_clk, 3)


@cocotb.test()
async def test_ldx_immediate(dut):
    """Test LDX immediate instruction (opcode 0x01)"""
    await start_clock_and_reset(dut)

    # Feed LDX #42 instruction (opcode=0x01, operand=42)
    await execute_instruction(dut, 0x01, 42)

    # Check that X register is loaded
    assert dut.dut.register_x.value == 42, f"X register should be 42, got {dut.dut.register_x.value}"


@cocotb.test()
async def test_ldy_immediate(dut):
    """Test LDY immediate instruction (opcode 0x02)"""
    await start_clock_and_reset(dut)

    # Feed LDY #55 instruction (opcode=0x02, operand=55)
    await execute_instruction(dut, 0x02, 55)

    # Check that Y register is loaded
    assert dut.dut.register_y.value == 55, f"Y register should be 55, got {dut.dut.register_y.value}"


@cocotb.test()
async def test_inx(dut):
    """Test INX instruction (opcode 0x06)"""
    await start_clock_and_reset(dut)

    # First load X with 10
    await execute_instruction(dut, 0x01, 10)  # LDX #10

    # Now increment X
    await execute_instruction(dut, 0x06, 0)  # INX

    assert dut.dut.register_x.value == 11, f"X should be 11 after INX, got {int(dut.dut.register_x.value)}"


@cocotb.test()
async def test_iny(dut):
    """Test INY instruction (opcode 0x05)"""
    await start_clock_and_reset(dut)

    # First load Y with 20
    await execute_instruction(dut, 0x02, 20)  # LDY #20

    # Now increment Y
    await execute_instruction(dut, 0x05, 0)  # INY

    assert dut.dut.register_y.value == 21, f"Y should be 21 after INY, got {dut.dut.register_y.value}"


@cocotb.test()
async def test_dex(dut):
    """Test DEX instruction (opcode 0x14)"""
    await start_clock_and_reset(dut)

    # First load X with 10
    await execute_instruction(dut, 0x01, 10)  # LDX #10

    # Now decrement X
    await execute_instruction(dut, 0x14, 0)  # DEX

    assert dut.dut.register_x.value == 9, f"X should be 9 after DEX, got {dut.dut.register_x.value}"


@cocotb.test()
async def test_dey(dut):
    """Test DEY instruction (opcode 0x13)"""
    await start_clock_and_reset(dut)

    # First load Y with 10
    await execute_instruction(dut, 0x02, 10)  # LDY #10

    # Now decrement Y
    await execute_instruction(dut, 0x13, 0)  # DEY

    assert dut.dut.register_y.value == 9, f"Y should be 9 after DEY, got {dut.dut.register_y.value}"


@cocotb.test()
async def test_cpx_sets_zero_flag(dut):
    """Test CPX sets zero flag correctly"""
    await start_clock_and_reset(dut)

    # Load X with 5
    await execute_instruction(dut, 0x01, 5)  # LDX #5

    # Compare X with 10 (not equal, so Z=0)
    await execute_instruction(dut, 0x03, 10)  # CPX #10

    assert dut.dut.status_zero.value == 0, "Zero flag should be 0 (5 != 10)"

    # Compare X with 5 (equal, so Z=1)
    await execute_instruction(dut, 0x03, 5)  # CPX #5

    assert dut.dut.status_zero.value == 1, "Zero flag should be 1 (5 == 5)"


@cocotb.test()
async def test_cpy_sets_zero_flag(dut):
    """Test CPY sets zero flag correctly"""
    await start_clock_and_reset(dut)

    # Load Y with 7
    await execute_instruction(dut, 0x02, 7)  # LDY #7

    # Compare Y with 10 (not equal, so Z=0)
    await execute_instruction(dut, 0x04, 10)  # CPY #10

    assert dut.dut.status_zero.value == 0, "Zero flag should be 0 (7 != 10)"

    # Compare Y with 7 (equal, so Z=1)
    await execute_instruction(dut, 0x04, 7)  # CPY #7

    assert dut.dut.status_zero.value == 1, "Zero flag should be 1 (7 == 7)"


@cocotb.test()
async def test_bne_branch_taken(dut):
    """Test BNE branch is taken when Z=0"""
    await start_clock_and_reset(dut)

    # Load X with 5
    await execute_instruction(dut, 0x01, 5)  # LDX #5

    # Compare X with 10 (not equal, Z=0)
    await execute_instruction(dut, 0x03, 10)  # CPX #10

    # Record PC before branch
    pc_before = int(dut.dut.pc.value)

    # BNE with offset 10 (should branch since Z=0)
    await execute_instruction(dut, 0x07, 10)  # BNE #10

    # Expected: PC = pc_before + 2 + 10
    expected_pc = pc_before + 2 + 10
    assert dut.dut.pc.value == expected_pc, f"PC should be {expected_pc}, got {dut.dut.pc.value}"


@cocotb.test()
async def test_bne_branch_not_taken(dut):
    """Test BNE branch is not taken when Z=1"""
    await start_clock_and_reset(dut)

    # Load X with 5
    await execute_instruction(dut, 0x01, 5)  # LDX #5

    # Compare X with 5 (equal, Z=1)
    await execute_instruction(dut, 0x03, 5)  # CPX #5

    # Record PC before branch
    pc_before = int(dut.dut.pc.value)

    # BNE with offset 10 (should NOT branch since Z=1)
    await execute_instruction(dut, 0x07, 10)  # BNE #10

    # Expected: PC = pc_before + 2 (no branch taken)
    expected_pc = pc_before + 2
    assert dut.dut.pc.value == expected_pc, f"PC should be {expected_pc}, got {dut.dut.pc.value}"


@cocotb.test()
async def test_beq_branch_taken(dut):
    """Test BEQ branch is taken when Z=1"""
    await start_clock_and_reset(dut)

    # Load X with 5
    await execute_instruction(dut, 0x01, 5)  # LDX #5

    # Compare X with 5 (equal, Z=1)
    await execute_instruction(dut, 0x03, 5)  # CPX #5

    # Record PC before branch
    pc_before = int(dut.dut.pc.value)

    # BEQ with offset 8 (should branch since Z=1)
    await execute_instruction(dut, 0x08, 8)  # BEQ #8

    # Expected: PC = pc_before + 2 + 8
    expected_pc = pc_before + 2 + 8
    assert dut.dut.pc.value == expected_pc, f"PC should be {expected_pc}, got {dut.dut.pc.value}"


@cocotb.test()
async def test_jmp(dut):
    """Test JMP instruction"""
    await start_clock_and_reset(dut)

    # JMP to address 0x50
    await execute_instruction(dut, 0x10, 0x50)  # JMP #0x50

    assert dut.dut.pc.value == 0x50, f"PC should be 0x50, got {hex(int(dut.dut.pc.value))}"


@cocotb.test()
async def test_sty_write_led(dut):
    """Test STY to LED output ($2)"""
    await start_clock_and_reset(dut)

    # Load Y with color index 1
    await execute_instruction(dut, 0x02, 1)  # LDY #1

    # Store Y to LED output (address $2)
    await execute_instruction(dut, 0x0E, 0x02)  # STY $2

    # Wait for LED write to complete
    await ClockCycles(dut.i_clk, 5)

    # Check that LED color output matches
    assert dut.o_led_color.value == 1, f"LED color should be 1, got {dut.o_led_color.value}"


@cocotb.test()
async def test_stx_write_led(dut):
    """Test STX to LED output ($2)"""
    await start_clock_and_reset(dut)

    # Load X with color index 2
    await execute_instruction(dut, 0x01, 2)  # LDX #2

    # Store X to LED output (address $2)
    await execute_instruction(dut, 0x0F, 0x02)  # STX $2

    # Wait for LED write to complete
    await ClockCycles(dut.i_clk, 5)

    # Check that LED color output matches
    assert dut.o_led_color.value == 2, f"LED color should be 2, got {dut.o_led_color.value}"


@cocotb.test()
async def test_ldx_from_num_leds(dut):
    """Test LDX from address $0 (num_leds)"""
    await start_clock_and_reset(dut)
    dut.i_num_leds.value = 25

    # Load X from address $0 (num_leds) - opcode 0x0A
    await execute_instruction(dut, 0x0A, 0x00)  # LDX $0

    assert dut.dut.register_x.value == 25, f"X should be 25 (num_leds), got {dut.dut.register_x.value}"


@cocotb.test()
async def test_ldy_from_num_colors(dut):
    """Test LDY from address $1 (num_colors)"""
    await start_clock_and_reset(dut)
    dut.i_num_colors.value = 2

    # Load Y from address $1 (num_colors) - opcode 0x0B
    await execute_instruction(dut, 0x0B, 0x01)  # LDY $1

    assert dut.dut.register_y.value == 2, f"Y should be 2 (num_colors), got {dut.dut.register_y.value}"


@cocotb.test()
async def test_scratch_memory(dut):
    """Test scratch memory read/write ($10-$1F)"""
    await start_clock_and_reset(dut)

    # Load Y with 42
    await execute_instruction(dut, 0x02, 42)  # LDY #42

    # Store Y to scratch memory at $10
    await execute_instruction(dut, 0x0E, 0x10)  # STY $10

    # Load X from scratch memory at $10
    await execute_instruction(dut, 0x0A, 0x10)  # LDX $10

    assert dut.dut.register_x.value == 42, f"X should be 42 from scratch memory, got {dut.dut.register_x.value}"


@cocotb.test()
async def test_stall(dut):
    """Test STALL instruction delays execution"""
    await start_clock_and_reset(dut)

    # STALL for 2 ticks
    await execute_instruction(dut, 0x09, 2)  # STALL #2

    pc_after_stall = int(dut.dut.pc.value)

    # Try to feed next instruction - PC should not advance during stall
    await ClockCycles(dut.i_clk, 10)

    # Without timer ticks, PC should stay the same
    assert dut.dut.pc.value == pc_after_stall, "PC should not advance during stall without timer"

    # Send timer ticks to complete stall
    for _ in range(3):
        dut.i_timer_100hz.value = 1
        await ClockCycles(dut.i_clk, 1)
        dut.i_timer_100hz.value = 0
        await ClockCycles(dut.i_clk, 5)

    # Feed next instruction
    await execute_instruction(dut, 0x01, 99)  # LDX #99

    # Now X should be updated
    assert dut.dut.register_x.value == 99, "X should be 99 after stall completes"


@cocotb.test()
async def test_bmi_branch_taken(dut):
    """Test BMI branch is taken when N=1"""
    await start_clock_and_reset(dut)

    # Load X with 5
    await execute_instruction(dut, 0x01, 5)  # LDX #5

    # Compare X with 10 (5 < 10, so N=1)
    await execute_instruction(dut, 0x03, 10)  # CPX #10

    # Record PC before branch
    pc_before = int(dut.dut.pc.value)

    # BMI with offset 6 (should branch since N=1)
    await execute_instruction(dut, 0x11, 6)  # BMI #6

    # Expected: PC = pc_before + 2 + 6
    expected_pc = pc_before + 2 + 6
    assert dut.dut.pc.value == expected_pc, f"PC should be {expected_pc}, got {dut.dut.pc.value}"


@cocotb.test()
async def test_bpl_branch_taken(dut):
    """Test BPL branch is taken when N=0"""
    await start_clock_and_reset(dut)

    # Load X with 10
    await execute_instruction(dut, 0x01, 10)  # LDX #10

    # Compare X with 5 (10 >= 5, so N=0)
    await execute_instruction(dut, 0x03, 5)  # CPX #5

    # Record PC before branch
    pc_before = int(dut.dut.pc.value)

    # BPL with offset 4 (should branch since N=0)
    await execute_instruction(dut, 0x12, 4)  # BPL #4

    # Expected: PC = pc_before + 2 + 4
    expected_pc = pc_before + 2 + 4
    assert dut.dut.pc.value == expected_pc, f"PC should be {expected_pc}, got {dut.dut.pc.value}"
