# SPDX-FileCopyrightText: © 2024 Chris Moos
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, with_timeout, Timer
from cocotb.handle import Force

# MUX_SEL encoding (bus_multiplexer.sv)
MUX_ADDR_LO  = 0  # 2'b00 → addr[7:0]
MUX_ADDR_HI  = 1  # 2'b01 → addr[15:8]
MUX_DATA_IN  = 2  # 2'b10 → external drives uio_in (CPU read)
MUX_DATA_OUT = 3  # 2'b11 → uio_out = write data

# Must match CPU_CLOCK_DIV_DEFAULT in project.v (0x49 = 73 → divide by 74)
CPU_PERIOD = 0x49 + 1  # 74 sysclk cycles per CPU cycle

# ui_in base: SO_N=1, IRQ_N=1, NMI_N=1, RDY=1, GPIOA[1:0]=0, MUX_SEL=0
# bits: [7:6]=GPIOA, [5]=SO_N, [4]=IRQ_N, [3]=NMI_N, [2]=RDY, [1:0]=MUX_SEL
UI_BASE = 0b00111100

# Number of sysclk cycles spent on each address phase.
# The remaining CPU_PERIOD cycles hold DATA_IN, ensuring cpu_clk_en fires
# while correct data is present on uio_in.
ADDR_PHASE_LEN = 2


def make_memory():
    """64 KB flat memory with reset vector → 0x0200 and a minimal program."""
    mem = bytearray(65536)
    mem[0xFFFC] = 0x00  # reset vector lo
    mem[0xFFFD] = 0x02  # reset vector hi → 0x0200
    return mem


def load_prog(mem, org, prog):
    for i, b in enumerate(prog):
        mem[org + i] = b


async def reset_dut(dut):
    dut.ui_in.value  = UI_BASE | MUX_ADDR_HI
    dut.uio_in.value = 0
    dut.ena.value    = 1
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value  = 1
    # Brief settle after reset de-assertion
    await ClockCycles(dut.clk, 2)


async def run_bus(dut, mem, cpu_cycles, accesses=None):
    """
    Simulate the external memory controller for `cpu_cycles` CPU cycles.
    """
    data_phase_len = CPU_PERIOD - 2 * ADDR_PHASE_LEN

    for _ in range(cpu_cycles):
        # --- ADDR_HI ---
        dut.ui_in.value = (int(dut.ui_in.value) & ~0x03) | MUX_ADDR_HI
        await ClockCycles(dut.clk, ADDR_PHASE_LEN)
        await FallingEdge(dut.clk)
        addr_hi = int(dut.uio_out.value)

        # --- ADDR_LO ---
        dut.ui_in.value = (int(dut.ui_in.value) & ~0x03) | MUX_ADDR_LO
        await ClockCycles(dut.clk, ADDR_PHASE_LEN)
        await FallingEdge(dut.clk)
        addr_lo = int(dut.uio_out.value)

        addr = (addr_hi << 8) | addr_lo
        rw   = (int(dut.uo_out.value) >> 2) & 1  # uo_out[2] = R/W

        if rw:
            # Read: hold DATA_IN with memory contents until end of CPU cycle
            dut.ui_in.value  = (int(dut.ui_in.value) & ~0x03) | MUX_DATA_IN
            dut.uio_in.value = int(mem[addr])
            if accesses is not None:
                accesses.append(('R', addr, mem[addr]))
            await ClockCycles(dut.clk, data_phase_len)
        else:
            # Write: switch to DATA_OUT so uio_out carries the write data
            dut.ui_in.value = (int(dut.ui_in.value) & ~0x03) | MUX_DATA_OUT
            await ClockCycles(dut.clk, data_phase_len)
            # Sample write data near end of cycle
            if int(dut.uio_oe.value) == 0xFF:
                write_val = int(dut.uio_out.value)
                mem[addr] = write_val
                if accesses is not None:
                    accesses.append(('W', addr, write_val))


async def loopback_uart(dut):
    """Loopback uo_out[4] (TX) to ui_in[6] (RX) every clock."""
    while True:
        await FallingEdge(dut.clk)
        tx_bit = (int(dut.uo_out.value) >> 4) & 1
        current_ui = int(dut.ui_in.value)
        if tx_bit:
            dut.ui_in.value = current_ui | 0x40
        else:
            dut.ui_in.value = current_ui & ~0x40


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@cocotb.test()
async def test_phi2_toggles(dut):
    """PHI2 must toggle after reset — confirms the CPU clock divider is running."""
    cocotb.start_soon(Clock(dut.clk, 50, unit="ns").start())
    await reset_dut(dut)

    # Simple check: sample, run bus, sample again
    phi2_init = (int(dut.uo_out.value) >> 1) & 1
    
    # Run the bus for a few cycles
    await run_bus(dut, bytearray(65536), cpu_cycles=5)
    
    phi2_now = (int(dut.uo_out.value) >> 1) & 1
    
    # If it's still the same, run a bit more but with offset
    if phi2_init == phi2_now:
        await ClockCycles(dut.clk, CPU_PERIOD // 2)
        phi2_now = (int(dut.uo_out.value) >> 1) & 1
        
    dut._log.info(f"PHI2 initial: {phi2_init}, current: {phi2_now}")
    assert phi2_init != phi2_now, "PHI2 did not toggle"


@cocotb.test()
async def test_reset_vector_read(dut):
    """CPU must read from 0xFFFC and 0xFFFD during the reset sequence."""
    cocotb.start_soon(Clock(dut.clk, 50, unit="ns").start())

    mem = make_memory()
    load_prog(mem, 0x0200, [0x4C, 0x00, 0x02])

    accesses = []
    await reset_dut(dut)
    await run_bus(dut, mem, cpu_cycles=12, accesses=accesses)

    read_addrs = {a for op, a, _ in accesses if op == 'R'}
    dut._log.info(f"Bus reads: {[hex(a) for a in sorted(read_addrs)]}")

    assert 0xFFFC in read_addrs and 0xFFFD in read_addrs, "Reset vector reads missing"


@cocotb.test()
async def test_gpio_output(dut):
    """CPU writes to GPIO OE (0xA000) and GPIO OUT (0xA001)."""
    cocotb.start_soon(Clock(dut.clk, 50, unit="ns").start())

    mem = make_memory()
    prog = [
        0xA9, 0xFF,        # LDA #$FF
        0x8D, 0x00, 0xA0,  # STA $A000
        0xA9, 0x3C,        # LDA #$3C
        0x8D, 0x01, 0xA0,  # STA $A001
        0x4C, 0x0A, 0x02,  # JMP $020A
    ]
    load_prog(mem, 0x0200, prog)

    await reset_dut(dut)
    await run_bus(dut, mem, cpu_cycles=30)

    gpio_nibble = (int(dut.uo_out.value) >> 4) & 0xF
    assert gpio_nibble == 0xF, f"GPIO output failed, got 0b{gpio_nibble:04b}"


@cocotb.test()
async def test_timer_irq(dut):
    """Test Timer IRQ with robust vector checks."""
    cocotb.start_soon(Clock(dut.clk, 50, unit="ns").start())

    mem = make_memory()
    prog = [
        0x78,              # SEI
        0xA9, 0x00, 0x8D, 0x26, 0xA0, # PRESCALER = 0
        0xA9, 0xF0, 0x8D, 0x24, 0xA0, # RELOAD_LO = F0
        0xA9, 0xFF, 0x8D, 0x25, 0xA0, # RELOAD_HI = FF
        0xA9, 0x08, 0x8D, 0x20, 0xA0, # LOAD
        0xA9, 0x05, 0x8D, 0x20, 0xA0, # EN | IRQ_EN
        0x4C, 0x18, 0x02,  # JMP HERE
    ]
    load_prog(mem, 0x0200, prog)
    mem[0xFFFE] = 0x00
    mem[0xFFFF] = 0x03
    mem[0x0300] = 0x40 # RTI

    accesses = []
    await reset_dut(dut)
    await run_bus(dut, mem, cpu_cycles=150, accesses=accesses)

    read_addrs = [a for op, a, _ in accesses if op == 'R']
    assert 0xFFFE in read_addrs and 0xFFFF in read_addrs, "Timer IRQ vector read not seen"


@cocotb.test()
async def test_uart_loopback(dut):
    """Test UART with a robust background loopback task."""
    cocotb.start_soon(Clock(dut.clk, 50, unit="ns").start())

    # Start loopback task
    cocotb.start_soon(loopback_uart(dut))

    mem = make_memory()
    # Program:
    # Pin 2 (GPIO2) = TX, Pin 0 (GPIO0) = RX
    # Baud div = 1 (fast)
    prog = [
        0xA9, 0x01, 0x8D, 0x06, 0xA0, # MODE TX (GPIO 2)
        0xA9, 0x02, 0x8D, 0x04, 0xA0, # MODE RX (GPIO 0)
        0xA9, 0x01, 0x8D, 0x43, 0xA0, # BAUD LO = 1
        0xA9, 0x00, 0x8D, 0x44, 0xA0, # BAUD HI = 0
        0xA9, 0x03, 0x8D, 0x40, 0xA0, # CTRL = TX_EN | RX_EN
        0xA9, 0x55, 0x8D, 0x42, 0xA0, # DATA = 0x55
        0xAD, 0x41, 0xA0,             # WAIT: LDA STATUS
        0x29, 0x02,                   # AND #2 (RX_READY)
        0xF0, 0xF9,                   # BEQ WAIT
        0xAD, 0x42, 0xA0,             # LDA DATA
        0x85, 0x00,                   # STA $00
        0x4C, 0x22, 0x02              # JMP $0222
    ]
    load_prog(mem, 0x0200, prog)

    await reset_dut(dut)
    
    # Run for 5000 cycles
    for _ in range(5000):
        await run_bus(dut, mem, cpu_cycles=1)
        if mem[0x0000] == 0x55:
            break

    assert mem[0x0000] == 0x55, f"UART Loopback failed, expected 0x55, got {hex(mem[0x0000])}"
