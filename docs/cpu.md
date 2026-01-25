# LED Controller CPU

The LED Controller includes a custom 8-bit microprocessor for executing LED animation programs stored in SPI flash memory via XIP (Execute-In-Place).

The instruction set is inspired by the MOS 6502, using familiar mnemonics (LDX, LDY, STX, STY, CPX, CPY, INX, INY, DEX, DEY, BNE, BEQ, BMI, BPL, JMP, NOP) and addressing modes (immediate, absolute). However, it is a simplified implementation with only two general-purpose registers (X and Y), no accumulator, no stack, and a limited set of operations tailored for LED animation control.

## Specifications

| Parameter | Value |
|-----------|-------|
| Data Width | 8-bit |
| Instruction Width | 16-bit (8-bit opcode + 8-bit operand) |
| Program Memory | External SPI flash (XIP) |
| Scratch Memory | 16 bytes (addresses 0x10-0x1F) |
| Registers | X (8-bit), Y (8-bit), PC (8-bit) |
| Status Flags | Zero (Z), Negative (N) |

## Registers

| Register | Size | Description |
|----------|------|-------------|
| X | 8-bit | General purpose register |
| Y | 8-bit | General purpose register |
| PC | 8-bit | Program counter (byte address) |
| Z | 1-bit | Zero flag (set when result equals zero) |
| N | 1-bit | Negative flag (set when result bit 7 is 1) |

## Instruction Set

All instructions are 16 bits wide: the high byte is the opcode, the low byte is the operand.

### Load Instructions

| Opcode | Binary | Mnemonic | Description |
|--------|--------|----------|-------------|
| 0x01 | 00001 | `ldx #imm` | Load immediate value into X |
| 0x02 | 00010 | `ldy #imm` | Load immediate value into Y |
| 0x0A | 01010 | `ldx $addr` | Load value from memory address into X |
| 0x0B | 01011 | `ldy $addr` | Load value from memory address into Y |

### Store Instructions

| Opcode | Binary | Mnemonic | Description |
|--------|--------|----------|-------------|
| 0x0E | 01110 | `sty $addr` | Store Y register to memory address |
| 0x0F | 01111 | `stx $addr` | Store X register to memory address |

### Compare Instructions

Compare instructions subtract the operand from the register and set flags accordingly, without storing the result.

| Opcode | Binary | Mnemonic | Description |
|--------|--------|----------|-------------|
| 0x03 | 00011 | `cpx #imm` | Compare X with immediate value, set Z/N flags |
| 0x04 | 00100 | `cpy #imm` | Compare Y with immediate value, set Z/N flags |
| 0x0C | 01100 | `cpx $addr` | Compare X with memory value, set Z/N flags |
| 0x0D | 01101 | `cpy $addr` | Compare Y with memory value, set Z/N flags |

**Flag behavior:**
- **Z flag**: Set if register equals operand (result is zero)
- **N flag**: Set if register is less than operand (result is negative, i.e., bit 7 is set)

### Increment/Decrement Instructions

| Opcode | Binary | Mnemonic | Description |
|--------|--------|----------|-------------|
| 0x05 | 00101 | `iny` | Increment Y register |
| 0x06 | 00110 | `inx` | Increment X register |
| 0x13 | 10011 | `dey` | Decrement Y register |
| 0x14 | 10100 | `dex` | Decrement X register |

### Branch Instructions

Branch instructions use PC-relative addressing with a signed 8-bit offset.

| Opcode | Binary | Mnemonic | Description |
|--------|--------|----------|-------------|
| 0x07 | 00111 | `bne offset` | Branch if not equal (Z=0) |
| 0x08 | 01000 | `beq offset` | Branch if equal (Z=1) |
| 0x11 | 10001 | `bmi offset` | Branch if minus (N=1) |
| 0x12 | 10010 | `bpl offset` | Branch if plus (N=0) |

**Branch offset calculation:**
```
Target Address = PC + 2 + offset
```
- The offset is a signed 8-bit value (-128 to +127)
- The +2 accounts for the 16-bit instruction width (2 bytes)

### Jump Instructions

| Opcode | Binary | Mnemonic | Description |
|--------|--------|----------|-------------|
| 0x10 | 10000 | `jmp addr` | Unconditional jump to absolute address |

### Special Instructions

| Opcode | Binary | Mnemonic | Description |
|--------|--------|----------|-------------|
| 0x00 | 00000 | `nop` | No operation |
| 0x09 | 01001 | `stall #n` | Delay for n × 10ms |

**Note:** Any undefined opcode is treated as NOP.

## Memory Map

### Hardware Registers (Read)

| Address | Name | Description |
|---------|------|-------------|
| 0x00 | NUM_LEDS | Number of LEDs configured (read-only) |
| 0x01 | NUM_COLORS | Number of active colors 1-3 (read-only) |

### Hardware Registers (Write)

| Address | Name | Description |
|---------|------|-------------|
| 0x02 | LED_PIXEL | Write LED pixel (bits [1:0] = color index) |

**LED_PIXEL values:**
- 0: Use COLOR0
- 1: Use COLOR1
- 2: Use COLOR2
- 3: LED off (black)

### Scratch Memory

| Address | Name | Description |
|---------|------|-------------|
| 0x10-0x1F | SCRATCH | 16 bytes of general-purpose RAM |

## Assembly Syntax

The assembler supports the following syntax:

```asm
; Comments start with semicolon
label:              ; Labels end with colon
    ldx #10         ; Immediate values prefixed with #
    ldx $10         ; Memory addresses prefixed with $
    ldx $0F         ; Hex values (no prefix after $)
    jmp label       ; Jump to label
    bne label       ; Branch to label
```

### Addressing Modes

| Mode | Syntax | Example | Description |
|------|--------|---------|-------------|
| Immediate | `#value` | `ldx #42` | Use literal value |
| Absolute | `$addr` | `ldx $10` | Load from memory address |
| Label | `name` | `jmp loop` | Jump/branch to label |


## Execution Model

1. **Fetch**: Read 16-bit instruction from SPI flash at PC address
2. **Decode**: Extract opcode (high byte) and operand (low byte)
3. **Execute**: Perform operation, update registers and flags
4. **Advance**: Increment PC by 2 (unless branch/jump taken)

The CPU stalls during:
- SPI flash reads (XIP latency)
- STALL instruction execution
- LED pixel writes (waiting for SK6812RGBW driver)

## Reset State

On reset, the CPU initializes to:

| Register/Flag | Value |
|---------------|-------|
| X | 0x00 |
| Y | 0x00 |
| PC | 0x00 |
| Z | 0 |
| N | 0 |

The CPU immediately begins fetching instructions from SPI flash address 0x0000.
