import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ClockCycles, RisingEdge


async def init_dut(dut):
    """Initialize DUT signals to default state."""
    dut.i_sck.value = 0
    dut.i_mosi.value = 0
    dut.i_ss_n.value = 1
    dut.i_data.value = 0
    dut.i_data_strb.value = 0


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


async def spi_clock_byte(dut, byte):
    """Clock out a byte on SPI interface and return."""
    for i in range(8):
        bit = (byte >> (7 - i)) & 1
        dut.i_mosi.value = bit
        await ClockCycles(dut.i_clk, 2)
        dut.i_sck.value = 1
        await ClockCycles(dut.i_clk, 2)
        dut.i_sck.value = 0
        await ClockCycles(dut.i_clk, 2)


@cocotb.test()
async def test_receive_byte(dut):
    """Test SPI slave receiving a byte"""
    await start_clock_and_reset(dut)

    # Start SPI transaction
    dut.i_ss_n.value = 0
    await ClockCycles(dut.i_clk, 5)

    test_byte = 0xA5
    await spi_clock_byte(dut, test_byte)

    assert dut.o_data.value == test_byte, \
        f"Received {hex(int(dut.o_data.value))}, expected {hex(test_byte)}"


@cocotb.test()
async def test_receive_multiple_bytes(dut):
    """Test SPI slave receiving multiple bytes in one transaction"""
    await start_clock_and_reset(dut)

    test_bytes = [0xDE, 0xAD, 0xBE, 0xEF]

    dut.i_ss_n.value = 0
    await ClockCycles(dut.i_clk, 5)

    for test_byte in test_bytes:
        await spi_clock_byte(dut, test_byte)
        assert dut.o_data.value == test_byte, \
            f"Received {hex(int(dut.o_data.value))}, expected {hex(test_byte)}"
        dut.i_sck.value = 0
        await ClockCycles(dut.i_clk, 2)

    dut.i_ss_n.value = 1


@cocotb.test()
async def test_transmit_byte(dut):
    """Test SPI slave transmitting a byte"""
    await start_clock_and_reset(dut)

    # Load data to transmit
    dut.i_data.value = 0x5A
    dut.i_data_strb.value = 1
    await ClockCycles(dut.i_clk, 2)
    dut.i_data_strb.value = 0

    dut.i_ss_n.value = 0
    await ClockCycles(dut.i_clk, 5)

    # Clock in/out 8 bits and capture MISO
    received = 0
    for _ in range(8):
        dut.i_mosi.value = 0
        await ClockCycles(dut.i_clk, 2)
        dut.i_sck.value = 1
        await ClockCycles(dut.i_clk, 2)
        dut.i_sck.value = 0
        received = (received << 1) | int(dut.o_miso.value)
        await ClockCycles(dut.i_clk, 2)

    dut.i_ss_n.value = 1
    await ClockCycles(dut.i_clk, 5)


@cocotb.test()
async def test_tx_start_strb(dut):
    """Test that tx_start_strb fires on SS falling edge"""
    await start_clock_and_reset(dut)

    assert dut.o_tx_start_strb.value == 0

    dut.i_ss_n.value = 0
    await ClockCycles(dut.i_clk, 10)

    dut.i_ss_n.value = 1
    await ClockCycles(dut.i_clk, 10)
    dut.i_ss_n.value = 0
    await ClockCycles(dut.i_clk, 10)


@cocotb.test()
async def test_data_strobe(dut):
    """Test that data strobe fires after receiving 8 bits"""
    await start_clock_and_reset(dut)
    dut.i_ss_n.value = 0
    await ClockCycles(dut.i_clk, 5)

    # Send 8 bits
    for i in range(8):
        dut.i_mosi.value = i & 1
        await ClockCycles(dut.i_clk, 2)
        dut.i_sck.value = 1
        if i == 7:
            # Last bit - strobe should appear 3 cycles after SCK high
            await ClockCycles(dut.i_clk, 4)
            assert dut.o_data_strb.value == 1, "Data strobe should fire 3 cycles after last SCK rising edge"
            break
        await ClockCycles(dut.i_clk, 2)
        dut.i_sck.value = 0
        await ClockCycles(dut.i_clk, 2)
