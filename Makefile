PYTHON_BIN = $(VIRTUAL_ENV)/bin/python
TOPLEVEL_LANG = verilog
SIM = verilator

VERILOG_SOURCES = $(PWD)/rtl/axi4_lite_regs.sv
TOPLEVEL = axi4_lite_regs
MODULE = test_axi4_lite_regs

export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += --timing
COMPILE_ARGS += -Wno-fatal

include $(shell $(VIRTUAL_ENV)/bin/cocotb-config --makefiles)/Makefile.sim
