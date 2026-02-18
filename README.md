![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# m6502 Microcontroller for TinyTapeout

A complete MOS Technology 6502-compatible CPU with integrated peripherals, designed for TinyTapeout. Features a bus multiplexer architecture that efficiently exposes the full 64KB address space through the limited 24-pin interface.

## Features

- **Complete 6502 CPU** - Cycle-accurate implementation with all documented opcodes
- **Bus Multiplexer** - 4-phase multiplexing reduces pin count from 24 to 8 data pins
- **External Memory** - Full 64KB address space via multiplexed bus
- **Rich Peripherals**:
  - GPIO (6 pins with pin multiplexing)
  - UART (8N1 with 4-byte FIFOs)
  - Timer (16-bit with prescaler and interrupts)
  - SK6812 RGB LED controller
  - Clock control for dynamic frequency scaling
- **Pin Multiplexing** - Route UART and SK6812 to any GPIO pin
- **TinyTapeout Optimized** - Fits in 2×2 tile allocation

## Quick Start

### Pinout

| Input (ui_in) | Output (uo_out) | Bidirectional (uio) |
|---------------|-----------------|---------------------|
| MUX_SEL[1:0] (0-1) | PHI1 (0) | MUX_DATA[7:0] |
| RDY (2) | PHI2 (1) | (multiplexed bus) |
| NMI_N (3) | R/W (2) | |
| IRQ_N (4) | SYNC (3) | |
| SO_N (5) | GPIOA2-5 (4-7) | |
| GPIOA0-1 (6-7) | | |

### Memory Map

| Address | Peripheral | Description |
|---------|-----------|-------------|
| 0xA000-0xA00B | GPIO | 6 I/O pins with mode registers |
| 0xA010-0xA017 | SK6812 | RGB LED controller |
| 0xA020-0xA027 | Timer | 16-bit timer/counter |
| 0xA030-0xA033 | Clock | CPU clock control |
| 0xA040-0xA047 | UART | Serial communication |
| All others | External | Via bus multiplexer |

### Example: Blink LED

```asm
; Configure GPIO2 as output
LDA #$04          ; Bit 2
STA $A000         ; OE register

loop:
    LDA $A001     ; Read current output
    EOR #$04      ; Toggle bit 2
    STA $A001     ; Write back
    JSR delay
    JMP loop
```

### Example: UART Hello World

```asm
; Configure GPIO2 as UART TX
LDA #$01          ; UART0_TX mode
STA $A006         ; MODE_PIN2

; Set 9600 baud @ 50MHz
LDA #$45
STA $A043         ; BAUD_LO
LDA #$01
STA $A044         ; BAUD_HI

; Enable TX and send
LDA #$01
STA $A040         ; Enable transmitter

; Send "Hello"
LDX #0
send:
    LDA msg, X
    BEQ done
wait:
    LDA $A041     ; Check TX_READY
    AND #$01
    BEQ wait
    LDA msg, X
    STA $A042     ; Write byte
    INX
    BNE send
done:

msg: .byte "Hello", $0D, $0A, 0
```

## Documentation

- **[Complete Datasheet](docs/6502_mcu_datasheet.pdf)** - Full technical reference (build with `cd docs && make`)
- **[Quick Reference](docs/info.md)** - Peripheral registers and examples
- **[Upstream m6502](https://github.com/chrismoos/6502-mcu)** - Full MCU project with RP2040 memory controller

## How It Works

The m6502 uses a **bus multiplexer** to expose the 6502's 16-bit address bus and 8-bit data bus through just 8 bidirectional pins. An external controller (RP2040 on TinyTapeout demo board) sequences through 4 phases per CPU cycle:

1. **ADDR_HI** - Latch address[15:8]
2. **ADDR_LO** - Latch address[7:0]
3. **DATA_IN/OUT** - Read or write data

All phases complete within one CPU cycle, so **there's no performance penalty** compared to a parallel bus.

The CPU accesses memory-mapped peripherals at 0xA000-0xA047 internally, while all other addresses are routed to external memory via the multiplexer.

## Building

### Hardware Requirements

- TinyTapeout ASIC or FPGA implementation
- External memory controller (RP2040 recommended)
- 50MHz clock (configurable)
- 3.3V I/O, 1.2V core

### Software Toolchain

- **cc65** - C compiler and assembler for 6502
- **ACME** or **xa65** - Alternative assemblers
- **py65** - Python-based simulator for testing

### Synthesis

The design uses the TinyTapeout/LibreLane flow:

```bash
# Local hardening (requires Docker)
# See: https://www.tinytapeout.com/guides/local-hardening/
```

GitHub Actions automatically builds the GDS on push.

## Testing

Testbenches use cocotb for simulation:

```bash
cd test
make
```

Tests cover:
- CPU instruction execution
- Peripheral register access
- Bus multiplexer protocol
- UART TX/RX
- Timer operation
- GPIO modes

## Architecture

**Technology**: IHP SG13G2 130nm
**Die Size**: 2×2 TinyTapeout tiles
**Clock**: 50 MHz nominal

## Resources

- **6502 Reference**: [6502.org](http://www.6502.org/)
- **TinyTapeout**: [tinytapeout.com](https://tinytapeout.com)
- **W65C02S Datasheet**: Western Design Center
- **MOS 6502 Programming Manual**: Original documentation

## License

Apache-2.0

## Author

Chris Moos ([@xoclipse](https://discord.com/users/xoclipse))

## What is TinyTapeout?

Tiny Tapeout is an educational project that makes it easier and cheaper than ever to get your digital designs manufactured on a real chip. Learn more at [tinytapeout.com](https://tinytapeout.com).
