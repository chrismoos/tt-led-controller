# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, FallingEdge, ClockCycles, RisingEdge, First

from spi_helpers import SPIMasterConfig, SPIMaster, FlashSPI

ROM_FILE = Path(__file__).resolve().parent.parent / 'firmware/pacman.bin'


class SK6812Decoder:
    """Decode SK6812RGBW data from the LED output line."""

    def __init__(self, dut, data_signal, clock_period_ns=20, clock_divider=5):
        self.dut = dut
        self.data_signal = data_signal
        self.tick_ns = clock_period_ns * clock_divider  # 100ns per tick
        # Threshold to distinguish '0' (3 ticks high) from '1' (6 ticks high)
        # Use 4.5 ticks as threshold = 450ns
        self.threshold_ns = 500

    async def read_bit(self, timeout_ms=100):
        """Read a single bit by measuring high pulse width."""
        # Wait for rising edge
        timeout = Timer(timeout_ms, 'ms')
        result = await First(RisingEdge(self.data_signal), timeout)
        if result is timeout:
            return None

        # Measure high pulse duration
        start_time = cocotb.utils.get_sim_time('ns')

        timeout = Timer(10, 'us')
        result = await First(FallingEdge(self.data_signal), timeout)
        if result is timeout:
            return None

        high_duration = cocotb.utils.get_sim_time('ns') - start_time

        # Decode: longer high pulse = 1, shorter = 0
        return 1 if high_duration > self.threshold_ns else 0

    async def read_color(self, timeout_ms=100):
        """Read 32 bits (one GRBW color value)."""
        bits = []
        for i in range(32):
            # Only use long timeout for first bit (waiting for frame to start)
            bit = await self.read_bit(timeout_ms if i == 0 else 10)
            if bit is None:
                return None
            bits.append(bit)

        # Convert bits to integer (MSB first)
        value = 0
        for bit in bits:
            value = (value << 1) | bit
        return value

    async def wait_for_reset(self, timeout_ms=500):
        """Wait for the reset period (long low time) that precedes each frame.

        SK6812 reset is 80+ microseconds of low signal. We wait for at least 50us
        of continuous low to ensure we're synchronized with the frame start.
        After this returns True, the signal is low and the next rising edge
        will be the start of the first bit.
        """
        reset_threshold_us = 50  # Wait for 50us of low
        timeout = Timer(timeout_ms, 'ms')

        while True:
            # First, wait for signal to go low (end of any current bit)
            if int(self.data_signal.value) == 1:
                result = await First(FallingEdge(self.data_signal), timeout)
                if result is timeout:
                    return False

            # Wait for either rising edge (new bit) or threshold time
            reset_timeout = Timer(reset_threshold_us, 'us')
            result = await First(RisingEdge(self.data_signal), reset_timeout)

            if result is reset_timeout:
                # Signal stayed low for threshold - found reset period
                # Signal is still low, caller's read_bit will catch the first rising edge
                return True

            # Rising edge came before threshold - just a normal bit gap, keep looking

    async def run(self, num_leds, num_frames, timeout_ms=500):
        """Collect colors for specified number of LEDs and frames."""
        frames = []
        for frame_idx in range(num_frames):
            frame = []
            for led_idx in range(num_leds):
                color = await self.read_color(timeout_ms)
                if color is None:
                    self.dut._log.warning(f"Timeout reading LED {led_idx} in frame {frame_idx}")
                    return frames
                frame.append(color)
                self.dut._log.info(f"Frame {frame_idx} LED {led_idx}: 0x{color:08x}")
            frames.append(frame)
        return frames


async def start_clock_and_reset(dut, clock_period=0.02):
    """Start clock and perform reset sequence."""
    clock = Clock(dut.clk, clock_period, 'us')
    cocotb.start_soon(clock.start())

    await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)


@cocotb.test()
async def test_led_controller(dut):
    """Test the LED controller by decoding the SK6812RGBW output.

    This test uses only external interfaces (SPI, Flash SPI, LED data output)
    so it works for both RTL and gate-level simulation.
    """
    dut._log.info("Start")

    # Start clock and reset first to initialize the design
    await start_clock_and_reset(dut)

    dut._log.info("Clock and reset done")

    # Just run for a bit to verify basic simulation works
    await ClockCycles(dut.clk, 100)
    dut._log.info("Basic simulation works")

    rom = bytearray(Path(ROM_FILE).read_bytes())

    # replace stall with NOP for test
    rom[0] = 0
    rom[1] = 0

    # Create Flash SPI slave to provide firmware to the CPU
    dut._log.info("Creating FlashSPI...")
    flash_spi_slave = FlashSPI(
        dut.o_flash_spi_sck,
        dut.o_flash_spi_mosi,
        dut.i_flash_spi_miso,
        dut.o_flash_spi_ss_n,
        rom
    )
    dut._log.info("Starting FlashSPI coroutine...")
    cocotb.start_soon(flash_spi_slave.run())

    # Create SPI master for sending configuration commands
    dut._log.info("Creating SPIMaster...")
    spi_config = SPIMasterConfig(clock_period=0.00001, ss_delay=0.00002)
    dut._log.info(f"SPI config: clock_period={spi_config.clock_period}, ss_delay={spi_config.ss_delay}")
    spi_master = SPIMaster(
        dut.i_spi_sck,
        dut.i_spi_mosi,
        dut.o_spi_miso,
        dut.i_spi_ss_n,
        config=spi_config
    )

    # Configure via SPI:
    # Register 16 (0x10) = num_leds, set to 3
    # Register 19 (0x13) = flash_24_bit mode, set to 0 (16-bit addressing)
    dut._log.info("Configuring LED controller via SPI")

    # Write num_leds = 3
    dut._log.info("Writing num_leds...")
    await spi_master.write([16 | 0x80, 3])
    dut._log.info("Done writing num_leds")

    # set program custom
    await spi_master.write([1 | 0x80, 3])

    # Write flash_24_bit = 0 (this also triggers CPU reset)
    await spi_master.write([19 | 0x80, 0])

    # Create decoder for the LED data output
    decoder = SK6812Decoder(dut, dut.o_led_data, clock_period_ns=20, clock_divider=5)

    # Read 6 frames of 3 LEDs each
    # Use longer timeout since we're running at real speed
    dut._log.info("Reading LED data output...")
    frames = await decoder.run(num_leds=3, num_frames=6, timeout_ms=2000)

    dut._log.info(f"Got {len(frames)} frames")

    # Verify the expected LED colors from the pacman animation
    assert len(frames) == 6, f"Expected 6 frames, got {len(frames)}"

    expected = [
        [0x0000ff00, 0, 0],
        [0, 0x0000ff00, 0],
        [0, 0, 0x0000ff00],
        [0xff000000, 0, 0x0000ff00],
        [0, 0xff000000, 0x0000ff00],
        [0x00ff0000, 0xff000000, 0x0000ff00],
    ]

    for i, (got, exp) in enumerate(zip(frames, expected)):
        assert got == exp, f"Frame {i}: expected {[hex(x) for x in exp]}, got {[hex(x) for x in got]}"

    dut._log.info("Test passed!")
