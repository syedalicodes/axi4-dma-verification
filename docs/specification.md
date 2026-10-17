# AXI4 DMA Controller
## Design Specification v0.1

### 1. Objective
Design and verify a 32-bit DMA controller that copies data between
memory locations. The project targets ASIC/SoC design verification.

### 2. Architecture
- AXI4-Lite slave interface for configuration and status.
- DMA control and sequencing engine.
- AXI4 master read and write interfaces.
- Status, error, and interrupt logic.
- cocotb testbench, behavioral memory model, and scoreboard.

### 3. Initial scope
- Address width: 32 bits.
- Data width: 32 bits.
- Word size: 4 bytes.
- LENGTH represents the number of 32-bit words.
- One 32-bit beat per AXI memory transaction.
- Multi-beat bursts and multiple outstanding transactions are excluded
  from the initial implementation.

### 4. Register map

| Offset | Register | Access | Description |
|---|---|---|---|
| 0x00 | CONTROL | RW | Bit 0: START write-one pulse |
| 0x04 | STATUS | RO | Bit 0: BUSY, bit 1: DONE, bit 2: ERROR |
| 0x08 | SRC_ADDR | RW | Source byte address |
| 0x0C | DST_ADDR | RW | Destination byte address |
| 0x10 | LENGTH | RW | Number of words to copy |
| 0x14 | WORDS_DONE | RO | Successfully completed destination writes |
| 0x18 | IRQ_ENABLE | RW | Bit 0 enables interrupt |
| 0x1C | IRQ_STATUS | RW1C | Bit 0: done pending, bit 1: error pending |
| 0x20 | ERROR_CODE | RO | Zero means no error |

RW = read/write; RO = read-only; RW1C = write one to clear.

### 5. Transfer behavior
1. Software programs source, destination, and length.
2. Software writes START while the controller is idle.
3. Zero length or unaligned source/destination addresses are rejected.
4. Each word is read from source and written to destination.
5. Addresses advance by four bytes after each successful word.
6. WORDS_DONE counts successful destination writes.
7. DONE is set only after all requested writes complete.
8. BUSY remains asserted during an active transfer.
9. A start request while busy must not corrupt the active operation.

### 6. AXI behavior
- Single-beat transfers: AWLEN = 0 and ARLEN = 0.
- Transfer size: AWSIZE = 2 and ARSIZE = 2.
- Burst type: INCR.
- WSTRB = 4'b1111 and WLAST = 1.
- VALID and payload remain stable until handshake.
- Read and write channel backpressure must be handled independently.
- Non-OKAY read or write responses cause a controlled error.

### 7. Reset and interrupts
Reset clears controller state, status, counters, pending interrupts,
and error state. No new transactions may be issued during reset.
The exact behavior of reset during an in-flight AXI transaction must
be defined and tested.

IRQ_ENABLE controls interrupt output. IRQ_STATUS is write-one-to-clear.

### 8. Verification plan
- Register access and byte-strobe tests.
- Reset and idle tests.
- One-word and multi-word copies.
- Address progression and scoreboard checks.
- Independent channel backpressure.
- Read/write response errors.
- Invalid parameters and start-while-busy.
- Interrupt enable, pending, and clear behavior.
- Randomized transfers with reproducible seeds.
- Assertions, functional coverage, and formal checks where supported.

### 9. Initial exclusions
- Multi-beat bursts.
- Multiple outstanding transactions.
- Scatter-gather descriptors.
- Cache coherency.
- Multiple DMA channels.

### 10. Acceptance criteria
The release requires reproducible builds, passing directed and
randomized tests, scoreboard checks, protocol checks, documented
coverage results, and honest reporting of formal assumptions and
known limitations.

### 11. Finalized status and error rules

- DONE and ERROR are sticky until a new valid transfer is accepted
  or reset is asserted.
- A rejected start request caused by invalid parameters sets ERROR
  and the appropriate ERROR_CODE without issuing memory traffic.
- A START request while BUSY is ignored and must not alter the active
  transfer.
- ERROR_CODE 0: no error.
- ERROR_CODE 1: invalid parameters.
- ERROR_CODE 2: AXI read response error.
- ERROR_CODE 3: AXI write response error.
- ERROR_CODE 4: address overflow.
- IRQ_STATUS bits are independently write-one-to-clear.
- Clearing IRQ_STATUS does not clear STATUS.ERROR or STATUS.DONE.
- WORDS_DONE increments only after a successful destination write.

### 12. Reset contract

Reset abandons the controller's current operation and clears its
internal state. The verification environment must reset or coordinate
the memory model and bus agents as part of system reset. The design
must not assume that resetting the DMA alone cancels transactions
already accepted by an external AXI component.

### 13. Parameter validation precedence

Before starting memory traffic:
1. Reject zero length or unaligned source/destination addresses
   with ERROR_CODE 1.
2. Reject source or destination address-range wraparound with
   ERROR_CODE 4.
3. Otherwise accept the transfer and enter BUSY.

The address range is checked using the final word address:
base + (LENGTH - 1) * 4. Arithmetic must not wrap at 32 bits.
