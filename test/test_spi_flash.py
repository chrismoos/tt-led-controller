import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ClockCycles, RisingEdge


async def init_dut(dut):
    """Initialize DUT signals to default state."""
    dut.i_addr_width_24.value = 0
    dut.i_addr_valid.value = 0
    dut.i_addr.value = 0
    dut.i_miso.value = 0


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


async def capture_spi_byte(dut):
    """Capture 8 bits from MOSI on rising SCK edges."""
    result = 0
    for _ in range(8):
        await RisingEdge(dut.o_sck)
        result = (result << 1) | int(dut.o_mosi.value)
    return result


async def start_read(dut, addr, addr_24bit=False):
    """Start a flash read operation at the given address."""
    dut.i_addr_width_24.value = 1 if addr_24bit else 0
    dut.i_addr.value = addr
    dut.i_addr_valid.value = 1
    await FallingEdge(dut.o_cs_n)


async def end_read(dut):
    """End a flash read operation."""
    dut.i_addr_valid.value = 0
    await ClockCycles(dut.i_clk, 20)


@cocotb.test()
async def test_read_command(dut):
    """Test that flash sends 0x03 read command"""
    await start_clock_and_reset(dut)

    await start_read(dut, 0x1234)

    command = await capture_spi_byte(dut)
    assert command == 0x03, f"Command should be 0x03 (read), got {hex(command)}"

    await end_read(dut)


@cocotb.test()
async def test_16bit_address(dut):
    """Test 16-bit address transmission"""
    await start_clock_and_reset(dut)
    await start_read(dut, 0x1234)

    await capture_spi_byte(dut)  # Skip command byte
    addr_hi = await capture_spi_byte(dut)
    addr_lo = await capture_spi_byte(dut)

    assert addr_hi == 0x12, f"Address high byte should be 0x12, got {hex(addr_hi)}"
    assert addr_lo == 0x34, f"Address low byte should be 0x34, got {hex(addr_lo)}"

    await end_read(dut)


@cocotb.test()
async def test_24bit_address(dut):
    """Test 24-bit address transmission"""
    await start_clock_and_reset(dut)
    await start_read(dut, 0x5678, addr_24bit=True)

    await capture_spi_byte(dut)  # Skip command byte
    addr_upper = await capture_spi_byte(dut)
    addr_hi = await capture_spi_byte(dut)
    addr_lo = await capture_spi_byte(dut)

    assert addr_upper == 0x00, f"Upper address byte should be 0x00, got {hex(addr_upper)}"
    assert addr_hi == 0x56, f"Address high byte should be 0x56, got {hex(addr_hi)}"
    assert addr_lo == 0x78, f"Address low byte should be 0x78, got {hex(addr_lo)}"

    await end_read(dut)


@cocotb.test()
async def test_read_data(dut):
    """Test reading data from flash"""
    await start_clock_and_reset(dut)
    await start_read(dut, 0x0000)

    # Skip command (8 bits) + address (16 bits) = 24 bits
    for _ in range(24):
        await RisingEdge(dut.o_sck)

    # Feed data byte 0xAB on MISO
    test_data = 0xAB
    for i in range(8):
        dut.i_miso.value = (test_data >> (7 - i)) & 1
        await RisingEdge(dut.o_sck)

    await RisingEdge(dut.o_data_valid)
    assert dut.o_data.value == test_data, f"Read data should be {hex(test_data)}, got {hex(dut.o_data.value)}"

    await end_read(dut)


async def send_miso_byte(dut, byte):
    """Send a byte on MISO line."""
    for i in range(8):
        dut.i_miso.value = (byte >> (7 - i)) & 1
        await RisingEdge(dut.o_sck)


@cocotb.test()
async def test_continuous_read(dut):
    """Test continuous reading (multiple bytes)"""
    await start_clock_and_reset(dut)
    await start_read(dut, 0x0000)

    # Skip command + address
    for _ in range(24):
        await RisingEdge(dut.o_sck)

    test_bytes = [0xDE, 0xAD, 0xBE, 0xEF]
    received_bytes = []

    for test_byte in test_bytes:
        await send_miso_byte(dut, test_byte)
        await RisingEdge(dut.o_data_valid)
        received_bytes.append(int(dut.o_data.value))

    assert received_bytes == test_bytes, \
        f"Received {[hex(b) for b in received_bytes]}, expected {[hex(b) for b in test_bytes]}"

    await end_read(dut)


@cocotb.test()
async def test_busy_signal(dut):
    """Test busy signal during flash operation"""
    await start_clock_and_reset(dut)

    assert dut.o_busy.value == 0, "Should not be busy initially"

    dut.i_addr.value = 0x0000
    dut.i_addr_valid.value = 1
    await ClockCycles(dut.i_clk, 10)

    assert dut.o_busy.value == 1, "Should be busy during read"

    dut.i_addr_valid.value = 0
    await ClockCycles(dut.i_clk, 100)


@cocotb.test()
async def test_cs_timing(dut):
    """Test chip select assertion and deassertion"""
    await start_clock_and_reset(dut)

    assert dut.o_cs_n.value == 1, "CS should be high initially"

    await start_read(dut, 0x1234)
    assert dut.o_cs_n.value == 0, "CS should go low when reading"

    # Complete the transaction (skip cmd + addr + 1 data byte)
    for _ in range(24):
        await RisingEdge(dut.o_sck)

    # Feed one data byte
    for i in range(8):
        dut.i_miso.value = i & 1
        await RisingEdge(dut.o_sck)

    dut.i_addr_valid.value = 0
    await RisingEdge(dut.o_cs_n)
    assert dut.o_cs_n.value == 1, "CS should go high after transaction"


@cocotb.test()
async def test_address_change_restarts(dut):
    """Test that changing address during read restarts the transaction"""
    await start_clock_and_reset(dut)
    await start_read(dut, 0x0000)

    await capture_spi_byte(dut)  # Skip command

    dut.i_addr_valid.value = 0
    await ClockCycles(dut.i_clk, 20)

    # CS should eventually go high
    timeout = 0
    while dut.o_cs_n.value == 0 and timeout < 50:
        await RisingEdge(dut.i_clk)
        timeout += 1

    # Start new read at different address
    await start_read(dut, 0x5678)

    await capture_spi_byte(dut)  # Skip command
    addr_hi = await capture_spi_byte(dut)

    assert addr_hi == 0x56, f"New address high byte should be 0x56, got {hex(addr_hi)}"

    await end_read(dut)
