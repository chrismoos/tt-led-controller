import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ClockCycles, RisingEdge


async def init_dut(dut):
    """Initialize DUT signals to default state."""
    dut.i_clk_div.value = 1
    dut.i_led_strb.value = 0
    dut.i_led_color.value = 0
    dut.i_reset_strb.value = 0


async def start_clock_and_reset(dut, clock_period=0.02):
    """Start clock and perform reset sequence."""
    clk = Clock(dut.i_clk, clock_period, 'us')
    clk.start()

    await init_dut(dut)
    await FallingEdge(dut.i_clk)
    dut.i_reset_n.value = 0
    await ClockCycles(dut.i_clk, 5)
    dut.i_reset_n.value = 1
    await ClockCycles(dut.i_clk, 10)


async def wait_for_idle(dut):
    """Wait for the module to exit reset/busy state."""
    while dut.o_busy.value == 1:
        await RisingEdge(dut.i_clk)


async def send_led_color(dut, color):
    """Send a color to the LED driver."""
    dut.i_led_color.value = color
    dut.i_led_strb.value = 1
    await RisingEdge(dut.i_clk)
    dut.i_led_strb.value = 0
    await RisingEdge(dut.o_busy)


@cocotb.test()
async def test_reset_timing(dut):
    """Test that the SK6812RGBW module outputs low during reset period (800 ticks)"""
    await start_clock_and_reset(dut)

    # After reset, module should be in RESET state outputting low
    assert dut.o_busy.value == 1, "Should be busy during reset"
    assert dut.o_data.value == 0, "Data should be low during reset"

    # Wait for reset to complete
    for _ in range(810):
        await RisingEdge(dut.i_clk)
        assert dut.o_data.value == 0, "Data should stay low during reset"

    # Should now be idle
    await ClockCycles(dut.i_clk, 5)
    assert dut.o_busy.value == 0, "Should not be busy after reset completes"


@cocotb.test()
async def test_logic_zero_timing(dut):
    """Test Logic 0 timing: 3 ticks high, 8 ticks low"""
    await start_clock_and_reset(dut)
    await wait_for_idle(dut)

    await send_led_color(dut, 0x00000000)

    # Wait for first rising edge of data (start of first bit)
    timeout = 0
    while dut.o_data.value == 0 and timeout < 100:
        await RisingEdge(dut.i_clk)
        timeout += 1

    # Track timing for first few bits
    for bit_num in range(3):
        # Count high ticks
        high_count = 0
        while dut.o_data.value == 1:
            await RisingEdge(dut.i_clk)
            high_count += 1
            if high_count > 20:
                break

        # Count low ticks until next high or end
        low_count = 0
        while dut.o_data.value == 0 and dut.o_busy.value == 1:
            await RisingEdge(dut.i_clk)
            low_count += 1
            if low_count > 20 or dut.o_data.value == 1:
                break

        # Logic 0: expect 3 high ticks, 8 low ticks
        assert 2 <= high_count <= 4, f"Bit {bit_num}: Logic 0 high count {high_count} not in range 2-4"
        if dut.o_busy.value == 1:  # Only check low if not done
            assert 7 <= low_count <= 10, f"Bit {bit_num}: Logic 0 low count {low_count} not in range 7-10"


@cocotb.test()
async def test_logic_one_timing(dut):
    """Test Logic 1 timing: 6 ticks high, 5 ticks low"""
    await start_clock_and_reset(dut)
    await wait_for_idle(dut)

    await send_led_color(dut, 0xFFFFFFFF)

    # Wait for first rising edge of data
    timeout = 0
    while dut.o_data.value == 0 and timeout < 100:
        await RisingEdge(dut.i_clk)
        timeout += 1

    # Track timing for first few bits
    for bit_num in range(3):
        # Count high ticks
        high_count = 0
        while dut.o_data.value == 1:
            await RisingEdge(dut.i_clk)
            high_count += 1
            if high_count > 20:
                break

        # Count low ticks until next high or end
        low_count = 0
        while dut.o_data.value == 0 and dut.o_busy.value == 1:
            await RisingEdge(dut.i_clk)
            low_count += 1
            if low_count > 20 or dut.o_data.value == 1:
                break

        # Logic 1: expect 6 high ticks, 5 low ticks
        assert 5 <= high_count <= 7, f"Bit {bit_num}: Logic 1 high count {high_count} not in range 5-7"
        if dut.o_busy.value == 1:
            assert 4 <= low_count <= 7, f"Bit {bit_num}: Logic 1 low count {low_count} not in range 4-7"


@cocotb.test()
async def test_32bit_transmission(dut):
    """Test that exactly 32 bits are transmitted for one LED color"""
    await start_clock_and_reset(dut)
    await wait_for_idle(dut)

    await send_led_color(dut, 0xAA55AA55)

    # Count bits by tracking rising edges on o_data
    bit_count = 0
    timeout = 0
    last_data = 0

    while dut.o_busy.value == 1 and timeout < 2000:
        await RisingEdge(dut.i_clk)
        timeout += 1
        current_data = int(dut.o_data.value)
        # Detect rising edge
        if current_data == 1 and last_data == 0:
            bit_count += 1
        last_data = current_data

    assert bit_count == 32, f"Expected 32 bits, got {bit_count}"


@cocotb.test()
async def test_clk_divider(dut):
    """Test that clock divider affects timing correctly"""
    await start_clock_and_reset(dut)
    dut.i_clk_div.value = 2  # 2 clocks per tick
    await wait_for_idle(dut)

    await send_led_color(dut, 0xFFFFFFFF)

    # Wait for first data bit
    timeout = 0
    while dut.o_data.value == 0 and timeout < 200:
        await RisingEdge(dut.i_clk)
        timeout += 1

    # Count high clocks for first bit (should be ~12 clocks = 6 ticks * 2)
    high_count = 0
    while dut.o_data.value == 1:
        await RisingEdge(dut.i_clk)
        high_count += 1
        if high_count > 50:
            break

    # With clk_div=2, logic 1 high time should be ~12 clocks (6 ticks * 2)
    assert 10 <= high_count <= 14, f"High count {high_count} not in expected range 10-14 for clk_div=2"


@cocotb.test()
async def test_reset_strb(dut):
    """Test that reset_strb returns module to reset state with 800 tick delay"""
    await start_clock_and_reset(dut)
    await wait_for_idle(dut)

    await send_led_color(dut, 0xFFFFFFFF)
    await ClockCycles(dut.i_clk, 50)

    # Assert reset strobe mid-transmission
    dut.i_reset_strb.value = 1
    await RisingEdge(dut.i_clk)
    dut.i_reset_strb.value = 0

    await ClockCycles(dut.i_clk, 5)

    # Should be back in reset state (busy)
    assert dut.o_busy.value == 1, "Should be busy after reset_strb"

    # Wait for data to go low (may take a tick or two)
    timeout = 0
    while dut.o_data.value == 1 and timeout < 20:
        await RisingEdge(dut.i_clk)
        timeout += 1

    assert dut.o_data.value == 0, f"Data should be low during reset state, took {timeout} cycles"

    # Count how many ticks until busy goes low (should be ~800)
    tick_count = 0
    while dut.o_busy.value == 1 and tick_count < 850:
        await RisingEdge(dut.i_clk)
        tick_count += 1

    # Should take approximately 800 ticks (RESET_CYCLES) to complete
    assert 795 <= tick_count <= 810, f"Reset should take ~800 ticks, got {tick_count}"
