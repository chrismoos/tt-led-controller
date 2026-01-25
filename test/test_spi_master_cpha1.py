import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ClockCycles, RisingEdge


async def init_dut(dut):
    """Initialize DUT signals to default state."""
    dut.i_miso.value = 0
    dut.i_tx_en.value = 0
    dut.i_tx_data.value = 0


async def start_clock_and_reset(dut, clock_period=0.02):
    """Start clock and perform reset sequence."""
    clk = Clock(dut.i_clk, clock_period, 'us')
    cocotb.start_soon(clk.start())

    await init_dut(dut)
    await FallingEdge(dut.i_clk)
    dut.i_reset_n.value = 0
    await ClockCycles(dut.i_clk, 5)
    dut.i_reset_n.value = 1
    await ClockCycles(dut.i_clk, 10)


async def start_tx(dut, data):
    """Start a transmission and wait for busy."""
    dut.i_tx_data.value = data
    dut.i_tx_en.value = 1
    await RisingEdge(dut.o_busy)


async def stop_tx(dut):
    """Stop transmission and wait for idle."""
    dut.i_tx_en.value = 0
    await FallingEdge(dut.o_busy)


async def capture_mosi_byte(dut):
    """Capture 8 bits from MOSI on falling edges (CPHA=1 timing)."""
    result = 0
    for _ in range(8):
        await FallingEdge(dut.o_sck)
        result = (result << 1) | int(dut.o_mosi.value)
    return result


async def send_miso_byte(dut, data):
    """Send a byte on MISO, setting bits after rising edges (CPHA=1 timing)."""
    for i in range(8):
        await RisingEdge(dut.o_sck)
        dut.i_miso.value = (data >> (7 - i)) & 1


@cocotb.test()
async def test_transmit_cpha1(dut):
    """Test SPI master transmitting a byte with CPHA=1."""
    await start_clock_and_reset(dut)
    await start_tx(dut, 0xA5)

    transmitted = await capture_mosi_byte(dut)
    assert transmitted == 0xA5, f"Transmitted {hex(transmitted)}, expected 0xA5"

    await stop_tx(dut)


@cocotb.test()
async def test_receive_cpha1(dut):
    """Test SPI master receiving a byte with CPHA=1."""
    await start_clock_and_reset(dut)

    test_byte = 0x5A
    await start_tx(dut, 0x00)
    await send_miso_byte(dut, test_byte)
    await RisingEdge(dut.o_rx_data_valid)

    assert dut.o_rx_data.value == test_byte, \
        f"Received {hex(int(dut.o_rx_data.value))}, expected {hex(test_byte)}"

    await stop_tx(dut)


@cocotb.test()
async def test_busy_signal_cpha1(dut):
    """Test that busy signal is asserted during transmission with CPHA=1."""
    await start_clock_and_reset(dut)

    assert dut.o_busy.value == 0, "Should not be busy initially"

    await start_tx(dut, 0xFF)
    assert dut.o_busy.value == 1, "Should be busy during transmission"

    await stop_tx(dut)
    assert dut.o_busy.value == 0, "Should not be busy after transmission"


@cocotb.test()
async def test_continuous_transmit_cpha1(dut):
    """Test transmitting multiple bytes continuously with CPHA=1."""
    await start_clock_and_reset(dut)

    test_bytes = [0xDE, 0xAD, 0xBE, 0xEF]
    captured_bytes = []

    dut.i_tx_en.value = 1
    dut.i_tx_data.value = test_bytes[0]

    for idx in range(len(test_bytes)):
        next_data = test_bytes[idx + 1] if idx + 1 < len(test_bytes) else 0
        captured = 0
        for bit in range(8):
            # Set next byte on rising edge (before falling edge where it's latched)
            await RisingEdge(dut.o_sck)
            dut.i_tx_data.value = next_data
            # Sample MOSI on falling edge
            await FallingEdge(dut.o_sck)
            captured = (captured << 1) | int(dut.o_mosi.value)
        captured_bytes.append(captured)
        await RisingEdge(dut.o_rx_data_valid)

    await stop_tx(dut)

    assert captured_bytes == test_bytes, \
        f"Transmitted {[hex(b) for b in captured_bytes]}, expected {[hex(b) for b in test_bytes]}"


@cocotb.test()
async def test_sck_idle_low_cpha1(dut):
    """Test that SCK is low when idle (CPOL=0, CPHA=1)."""
    await start_clock_and_reset(dut)

    assert dut.o_sck.value == 0, "SCK should be low when idle (CPOL=0)"

    await start_tx(dut, 0xAA)
    await stop_tx(dut)
    await ClockCycles(dut.i_clk, 5)

    assert dut.o_sck.value == 0, "SCK should return to low after transmission"


@cocotb.test()
async def test_loopback_cpha1(dut):
    """Test loopback - transmit and receive same data with CPHA=1."""
    await start_clock_and_reset(dut)

    test_byte = 0xC3
    await start_tx(dut, test_byte)

    # Loop MOSI back to MISO: read after rising edge, sampled on falling edge
    for _ in range(8):
        await RisingEdge(dut.o_sck)
        dut.i_miso.value = int(dut.o_mosi.value)

    await RisingEdge(dut.o_rx_data_valid)

    assert dut.o_rx_data.value == test_byte, \
        f"Loopback received {hex(int(dut.o_rx_data.value))}, expected {hex(test_byte)}"

    await stop_tx(dut)
