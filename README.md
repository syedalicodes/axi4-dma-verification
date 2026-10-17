# AXI4-Lite DMA Register Verification

A SystemVerilog RTL verification project focused on validating an AXI4-Lite register interface using Cocotb, Verilator, functional coverage, and formal verification.

## Project Overview

This project verifies the register interface intended for a DMA controller. The verification environment exercises register access, AXI write-channel independence, response backpressure, invalid addresses, interrupt behavior, reset behavior, and byte-strobe handling.

**Current scope:** AXI4-Lite register block verification. This is not yet a complete end-to-end DMA engine.

## Technology Stack

- SystemVerilog — RTL and formal harness
- Python and Cocotb — simulation testbench
- Verilator — RTL simulation
- SymbiYosys — formal verification
- Git and GitHub — version control

## Verification Results

| Metric | Result |
|---|---|
| Cocotb regression | 21/21 tests passed |
| Defined functional coverage | 31/31 bins hit |
| Functional coverage percentage | 100% |
| Formal proof status | PASS |
| Regression failures | 0 |

*Functional coverage represents the user-defined transaction coverage bins. It is not RTL code coverage or toggle coverage.*

## Register Map

| Register | Address | Purpose |
|---|---:|---|
| CONTROL | `0x00` | Control and start command |
| STATUS | `0x04` | Busy, done, and error status |
| SRC_ADDR | `0x08` | Source address |
| DST_ADDR | `0x0C` | Destination address |
| LENGTH | `0x10` | Transfer length |
| WORDS_DONE | `0x14` | Transfer progress |
| IRQ_ENABLE | `0x18` | Interrupt enables |
| IRQ_STATUS | `0x1C` | Interrupt status |
| ERROR_CODE | `0x20` | Error information |

## Project Structure

```text
axi4-dma-verification/
├── docs/
│   └── specification.md
├── formal/
│   ├── axi4_lite_regs.sby
│   └── axi4_lite_regs_formal.sv
├── reports/
│   └── functional_coverage.txt
├── rtl/
│   └── axi4_lite_regs.sv
├── tb/
│   ├── functional_coverage.py
│   └── test_axi4_lite_regs.py
├── .gitignore
├── Makefile
└── README.md
```

## Run the Regression

Requirements: Ubuntu or WSL2, Python, Cocotb, Verilator, and the project's required build tools.

Activate your configured Python environment and run:

```bash
cd ~/projects/axi4-dma-verification
source .venv/bin/activate
make clean
make PYTHON_BIN="$VIRTUAL_ENV/bin/python"
```

## Formal Verification

The formal harness and SymbiYosys configuration are located in `formal/`. To rerun the formal proof, use:

```bash
sby -f formal/axi4_lite_regs.sby
```

Check the resulting proof status before reporting a new result.

## Future Improvements

- Add automated regression using GitHub Actions.
- Expand assertions and corner-case verification.
- Add a DMA datapath and memory transaction model.
- Verify end-to-end transfer correctness, error recovery, and additional protocol scenarios.

## Author

**Syed Ali U Khan**

GitHub: [@syedalicodes](https://github.com/syedalicodes)
