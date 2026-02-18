# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # 20ns clock period = 50MHz
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    # ui_in: MUX_SEL=0, RDY=1, NMI_N=1, IRQ_N=1, SO_N=1, GPIO[1:0]=0
    dut.ui_in.value  = 0b00111100  # RDY=1, NMI_N=1, IRQ_N=1, SO_N=1
    dut.uio_in.value = 0
    dut.ena.value    = 1
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value  = 1

    dut._log.info("Reset released, running...")
    await ClockCycles(dut.clk, 100)

    dut._log.info("Done")
