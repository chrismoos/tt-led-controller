from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, FallingEdge, ClockCycles, RisingEdge, First, Combine

from test.spi_helpers import SPIMasterConfig, SPIMaster, FlashSPI

ROM_FILE = Path(__file__).resolve().parent.parent / 'firmware/pacman.bin'


async def start_clock_and_reset(dut, clock_period=0.02):
    """Start clock and perform reset sequence."""
    clk = Clock(dut.i_clk, clock_period, 'us')
    clk.start()

    await FallingEdge(dut.i_clk)
    dut.i_reset_n.value = 0
    await ClockCycles(dut.i_clk, 5)
    dut.i_reset_n.value = 1
    await ClockCycles(dut.i_clk, 10)


@cocotb.test()
async def test_execute_flash(dut):
    rom = Path(ROM_FILE).read_bytes()

    flash_spi_slave = FlashSPI(dut.o_flash_spi_sck, dut.o_flash_spi_mosi, dut.i_flash_spi_miso,
                         dut.o_flash_spi_ss_n, rom)
    cocotb.start_soon(flash_spi_slave.run())

    spi_master = SPIMaster(dut.i_spi_sck, dut.i_spi_mosi, dut.o_spi_miso,
                         dut.i_spi_ss_n, config=SPIMasterConfig())

    await start_clock_and_reset(dut)

    dut.led_controller.num_leds.value = 3

    # disable 24-bit flash spi mode, switch to custom program
    assert dut.led_controller.flash_addr_width_24.value
    await spi_master.write([1 | 0x80, 3])
    await spi_master.write([19 | 0x80, 0])

    assert not dut.led_controller.flash_addr_width_24.value

    # wait for 6 periods of setting all LEDs for animation to finish
    iterations = []
    leds = []
    for x in range(0, 3 * 6):
        timeout = Timer(1, unit='ms')
        result = await First(FallingEdge(dut.led_controller.led_strb), timeout)
        if result is timeout:
            assert False, "timed out waiting for strobe"
        leds.append(int(dut.led_controller.led_color.value))
        if len(leds) == 3:
            iterations.append(leds)
            leds = []

    assert len(iterations) == 6
    assert iterations[0] == [0x0000ff00, 0, 0]
    assert iterations[1] == [0, 0x0000ff00, 0]
    assert iterations[2] == [0, 0, 0x0000ff00]
    assert iterations[3] == [0xff000000, 0, 0x0000ff00]
    assert iterations[4] == [0, 0xff000000, 0x0000ff00]
    assert iterations[5] == [0x00ff0000, 0xff000000, 0x0000ff00]
