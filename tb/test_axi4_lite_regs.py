import cocotb
from cocotb.triggers import Timer
from functional_coverage import FunctionalCoverage

coverage = FunctionalCoverage()


async def cycle(dut):
    dut.aclk.value = 0
    await Timer(5, unit="ns")
    dut.aclk.value = 1
    await Timer(5, unit="ns")


async def reset_dut(dut):
    dut.aclk.value = 0
    dut.aresetn.value = 0
    dut.s_awaddr.value = 0
    dut.s_awvalid.value = 0
    dut.s_wdata.value = 0
    dut.s_wstrb.value = 0
    dut.s_wvalid.value = 0
    dut.s_bready.value = 0
    dut.s_araddr.value = 0
    dut.s_arvalid.value = 0
    dut.s_rready.value = 0
    dut.busy.value = 0
    dut.done.value = 0
    dut.error.value = 0
    dut.words_done.value = 0
    dut.error_code.value = 0

    for _ in range(3):
        await cycle(dut)

    dut.aresetn.value = 1
    await cycle(dut)


async def write_reg(dut, addr, data, strobe=0xF):
    dut.s_awaddr.value = addr
    dut.s_awvalid.value = 1
    dut.s_wdata.value = data
    dut.s_wstrb.value = strobe
    dut.s_wvalid.value = 1
    dut.s_bready.value = 0

    aw_done = False
    w_done = False

    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")

        aw = int(dut.s_awready.value) and int(dut.s_awvalid.value)
        w = int(dut.s_wready.value) and int(dut.s_wvalid.value)

        dut.aclk.value = 1
        await Timer(5, unit="ns")

        if aw:
            dut.s_awvalid.value = 0
            aw_done = True
        if w:
            dut.s_wvalid.value = 0
            w_done = True
        if int(dut.s_bvalid.value):
            break
    else:
        raise AssertionError(f"Write timeout at {addr:#x}")

    assert aw_done and w_done, "AW/W handshake incomplete"
    assert int(dut.s_bvalid.value) == 1
    response = int(dut.s_bresp.value)

    coverage.sample_register_write(addr, strobe)
    coverage.sample_response(response)

    dut.s_bready.value = 1
    await cycle(dut)
    dut.s_bready.value = 0

    return response


async def read_reg(dut, addr):
    dut.s_araddr.value = addr
    dut.s_arvalid.value = 1
    dut.s_rready.value = 0

    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        accepted = (
            int(dut.s_arready.value) and int(dut.s_arvalid.value)
        )
        dut.aclk.value = 1
        await Timer(5, unit="ns")

        if accepted:
            dut.s_arvalid.value = 0
        if int(dut.s_rvalid.value):
            data = int(dut.s_rdata.value)
            response = int(dut.s_rresp.value)
            coverage.sample_register_read(addr)
            coverage.sample_response(response)
            dut.s_rready.value = 1
            await cycle(dut)
            dut.s_rready.value = 0
            assert response == 0, (
                f"Read response error at {addr:#x}: {response}"
            )
            return data

    raise AssertionError(f"Read timeout at {addr:#x}")


@cocotb.test()
async def reset_and_register_readback(dut):
    coverage.sample_scenario("reset")
    await reset_dut(dut)

    assert await read_reg(dut, 0x08) == 0
    assert await read_reg(dut, 0x0C) == 0
    assert await read_reg(dut, 0x10) == 0

    assert await write_reg(dut, 0x08, 0x11223344) == 0
    assert await write_reg(dut, 0x0C, 0x55667788) == 0
    assert await write_reg(dut, 0x10, 16) == 0

    assert await read_reg(dut, 0x08) == 0x11223344
    assert await read_reg(dut, 0x0C) == 0x55667788
    assert await read_reg(dut, 0x10) == 16


@cocotb.test()
async def independent_aw_w_channels(dut):
    coverage.sample_scenario("independent_aw_w")
    await reset_dut(dut)

    # Send the address channel first and delay the data channel.
    dut.s_awaddr.value = 0x08
    dut.s_awvalid.value = 1
    dut.s_wvalid.value = 0
    dut.s_wdata.value = 0xCAFEBABE
    dut.s_wstrb.value = 0xF
    dut.s_bready.value = 0

    await cycle(dut)
    dut.s_awvalid.value = 0

    for _ in range(2):
        await cycle(dut)

    dut.s_wvalid.value = 1
    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        accepted = int(dut.s_wready.value) and int(dut.s_wvalid.value)
        dut.aclk.value = 1
        await Timer(5, unit="ns")
        if accepted:
            dut.s_wvalid.value = 0
        if int(dut.s_bvalid.value):
            break
    else:
        raise AssertionError("Write response timeout")

    assert int(dut.s_bresp.value) == 0
    dut.s_bready.value = 1
    await cycle(dut)
    dut.s_bready.value = 0

    assert await read_reg(dut, 0x08) == 0xCAFEBABE


@cocotb.test()
async def byte_strobe_write(dut):
    await reset_dut(dut)

    assert await write_reg(dut, 0x08, 0x11223344) == 0
    assert await write_reg(dut, 0x08, 0x000000AA, 0x1) == 0
    assert await read_reg(dut, 0x08) == 0x112233AA


@cocotb.test()
async def write_response_backpressure(dut):
    coverage.sample_scenario("write_backpressure")
    await reset_dut(dut)

    dut.s_awaddr.value = 0x08
    dut.s_awvalid.value = 1
    dut.s_wdata.value = 0xABCDEF12
    dut.s_wstrb.value = 0xF
    dut.s_wvalid.value = 1
    dut.s_bready.value = 0

    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        aw = int(dut.s_awready.value) and int(dut.s_awvalid.value)
        w = int(dut.s_wready.value) and int(dut.s_wvalid.value)
        dut.aclk.value = 1
        await Timer(5, unit="ns")
        if aw:
            dut.s_awvalid.value = 0
        if w:
            dut.s_wvalid.value = 0
        if int(dut.s_bvalid.value):
            break
    else:
        raise AssertionError("Write response timeout")

    data_resp = int(dut.s_bresp.value)
    for _ in range(3):
        await cycle(dut)
        assert int(dut.s_bvalid.value) == 1
        assert int(dut.s_bresp.value) == data_resp

    dut.s_bready.value = 1
    await cycle(dut)
    dut.s_bready.value = 0
    assert await read_reg(dut, 0x08) == 0xABCDEF12


@cocotb.test()
async def read_response_backpressure(dut):
    coverage.sample_scenario("read_backpressure")
    await reset_dut(dut)
    assert await write_reg(dut, 0x08, 0xDEADBEEF) == 0

    dut.s_araddr.value = 0x08
    dut.s_arvalid.value = 1
    dut.s_rready.value = 0

    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        accepted = int(dut.s_arready.value) and int(dut.s_arvalid.value)
        dut.aclk.value = 1
        await Timer(5, unit="ns")
        if accepted:
            dut.s_arvalid.value = 0
        if int(dut.s_rvalid.value):
            break
    else:
        raise AssertionError("Read response timeout")

    expected = int(dut.s_rdata.value)
    response = int(dut.s_rresp.value)
    assert expected == 0xDEADBEEF

    for _ in range(3):
        await cycle(dut)
        assert int(dut.s_rvalid.value) == 1
        assert int(dut.s_rdata.value) == expected
        assert int(dut.s_rresp.value) == response

    dut.s_rready.value = 1
    await cycle(dut)
    dut.s_rready.value = 0


@cocotb.test()
async def reset_clears_registers(dut):
    await reset_dut(dut)

    assert await write_reg(dut, 0x08, 0x12345678) == 0
    assert await write_reg(dut, 0x0C, 0x87654321) == 0
    assert await write_reg(dut, 0x10, 32) == 0

    await reset_dut(dut)

    assert await read_reg(dut, 0x08) == 0
    assert await read_reg(dut, 0x0C) == 0
    assert await read_reg(dut, 0x10) == 0


@cocotb.test()
async def invalid_write_address_returns_slverr(dut):
    coverage.sample_scenario("invalid_address")
    await reset_dut(dut)

    response = await write_reg(dut, 0x24, 0x12345678)
    assert response == 2, f"Expected SLVERR (2), got {response}"
    assert await read_reg(dut, 0x08) == 0

    dut._log.info("Invalid-write address test passed")


@cocotb.test()
async def invalid_read_address_returns_slverr(dut):
    await reset_dut(dut)

    dut.s_araddr.value = 0x24
    dut.s_arvalid.value = 1
    dut.s_rready.value = 0

    accepted = False
    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        accepted = (
            int(dut.s_arready.value) and int(dut.s_arvalid.value)
        )
        dut.aclk.value = 1
        await Timer(5, unit="ns")

        if accepted:
            dut.s_arvalid.value = 0
        if int(dut.s_rvalid.value):
            break
    else:
        raise AssertionError("Invalid-read response timeout")

    assert int(dut.s_rresp.value) == 2
    assert int(dut.s_rdata.value) == 0

    dut.s_rready.value = 1
    await cycle(dut)
    dut.s_rready.value = 0

    dut._log.info("Invalid-read address test passed")


@cocotb.test()
async def done_interrupt_behavior(dut):
    coverage.sample_scenario("interrupts")
    await reset_dut(dut)

    # Enable the DONE interrupt.
    assert await write_reg(dut, 0x18, 0x1) == 0
    assert int(dut.irq.value) == 0

    # Generate a one-cycle DONE event.
    dut.done.value = 1
    await cycle(dut)
    dut.done.value = 0
    await cycle(dut)

    # Check that status is latched and IRQ is asserted.
    status = await read_reg(dut, 0x1C)
    assert status & 0x1, f"DONE status not set: {status:#x}"
    assert int(dut.irq.value) == 1, "DONE IRQ did not assert"

    # Clear DONE status using write-one-to-clear.
    assert await write_reg(dut, 0x1C, 0x1) == 0
    status = await read_reg(dut, 0x1C)
    assert (status & 0x1) == 0, f"DONE status did not clear: {status:#x}"
    assert int(dut.irq.value) == 0, "IRQ remained asserted after clearing"

    dut._log.info("DONE interrupt test passed")


@cocotb.test()
async def error_interrupt_behavior(dut):
    await reset_dut(dut)

    # Enable the ERROR interrupt.
    assert await write_reg(dut, 0x18, 0x2) == 0
    assert int(dut.irq.value) == 0

    # Generate a one-cycle ERROR event.
    dut.error.value = 1
    await cycle(dut)
    dut.error.value = 0
    await cycle(dut)

    # Check the latched ERROR status and IRQ.
    status = await read_reg(dut, 0x1C)
    assert status & 0x2, f"ERROR status not set: {status:#x}"
    assert int(dut.irq.value) == 1, "ERROR IRQ did not assert"

    # Clear ERROR status using write-one-to-clear.
    assert await write_reg(dut, 0x1C, 0x2) == 0
    status = await read_reg(dut, 0x1C)
    assert (status & 0x2) == 0, f"ERROR status did not clear: {status:#x}"
    assert int(dut.irq.value) == 0, "IRQ remained asserted after clearing"

    dut._log.info("ERROR interrupt test passed")


@cocotb.test()
async def interrupt_pending_while_disabled(dut):
    await reset_dut(dut)

    # Keep the ERROR interrupt disabled.
    assert await write_reg(dut, 0x18, 0x0) == 0

    # Generate an ERROR event while disabled.
    dut.error.value = 1
    await cycle(dut)
    dut.error.value = 0
    await cycle(dut)

    # Status should latch even though the IRQ output stays low.
    status = await read_reg(dut, 0x1C)
    assert status & 0x2, f"ERROR status not latched: {status:#x}"
    assert int(dut.irq.value) == 0, "IRQ asserted while disabled"

    # Enable the ERROR interrupt after the event.
    assert await write_reg(dut, 0x18, 0x2) == 0
    assert int(dut.irq.value) == 1, (
        "IRQ did not assert when enabling a pending ERROR"
    )

    dut._log.info("Pending interrupt test passed")


@cocotb.test()
async def done_event_wins_over_simultaneous_clear(dut):
    await reset_dut(dut)

    # Enable DONE interrupt and create a pending DONE status.
    assert await write_reg(dut, 0x18, 0x1) == 0

    dut.done.value = 1
    await cycle(dut)
    dut.done.value = 0
    await cycle(dut)

    status = await read_reg(dut, 0x1C)
    assert status & 0x1, "Initial DONE status was not set"

    # Present W1C and a new DONE event for the same clock edge.
    dut.s_awaddr.value = 0x1C
    dut.s_awvalid.value = 1
    dut.s_wdata.value = 0x1
    dut.s_wstrb.value = 0xF
    dut.s_wvalid.value = 1
    dut.s_bready.value = 0
    dut.done.value = 1

    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        aw = int(dut.s_awready.value) and int(dut.s_awvalid.value)
        w = int(dut.s_wready.value) and int(dut.s_wvalid.value)

        dut.aclk.value = 1
        await Timer(5, unit="ns")

        if aw:
            dut.s_awvalid.value = 0
        if w:
            dut.s_wvalid.value = 0
        if int(dut.s_bvalid.value):
            break
    else:
        raise AssertionError("W1C write response timeout")

    dut.done.value = 0
    assert int(dut.s_bresp.value) == 0

    dut.s_bready.value = 1
    await cycle(dut)
    dut.s_bready.value = 0

    status = await read_reg(dut, 0x1C)
    assert status & 0x1, (
        f"New DONE event was lost during W1C clear: {status:#x}"
    )
    assert int(dut.irq.value) == 1, "IRQ should remain asserted"

    dut._log.info("Simultaneous DONE/W1C priority test passed")


@cocotb.test()
async def independent_done_error_interrupts(dut):
    await reset_dut(dut)

    # Enable both interrupt sources.
    assert await write_reg(dut, 0x18, 0x3) == 0

    # Latch both DONE and ERROR status.
    dut.done.value = 1
    dut.error.value = 1
    await cycle(dut)
    dut.done.value = 0
    dut.error.value = 0
    await cycle(dut)

    status = await read_reg(dut, 0x1C)
    assert (status & 0x3) == 0x3, (
        f"Expected DONE and ERROR status, got {status:#x}"
    )
    assert int(dut.irq.value) == 1, "IRQ should assert for both events"

    # Clear DONE only.
    assert await write_reg(dut, 0x1C, 0x1) == 0
    status = await read_reg(dut, 0x1C)

    assert (status & 0x1) == 0, "DONE status did not clear"
    assert status & 0x2, "Clearing DONE incorrectly cleared ERROR"
    assert int(dut.irq.value) == 1, (
        "IRQ should remain asserted while ERROR is pending"
    )

    # Clear ERROR only.
    assert await write_reg(dut, 0x1C, 0x2) == 0
    status = await read_reg(dut, 0x1C)

    assert (status & 0x3) == 0, (
        f"Interrupt status did not fully clear: {status:#x}"
    )
    assert int(dut.irq.value) == 0, "IRQ should deassert after both clears"

    dut._log.info("Independent DONE/ERROR interrupt test passed")


@cocotb.test()
async def invalid_writes_preserve_valid_registers(dut):
    await reset_dut(dut)

    # Initialize valid registers with known values.
    assert await write_reg(dut, 0x08, 0x12345678) == 0
    assert await write_reg(dut, 0x0C, 0xABCDEF00) == 0
    assert await write_reg(dut, 0x10, 8) == 0

    # Try invalid and unmapped addresses.
    invalid_addresses = [0x24, 0x28, 0xFC]

    for addr in invalid_addresses:
        response = await write_reg(dut, addr, 0xFFFFFFFF)
        assert response == 2, (
            f"Expected SLVERR for address {addr:#x}, got {response}"
        )

    # Confirm valid registers retain their original values.
    assert await read_reg(dut, 0x08) == 0x12345678
    assert await read_reg(dut, 0x0C) == 0xABCDEF00
    assert await read_reg(dut, 0x10) == 8

    dut._log.info("Invalid writes preserve valid registers test passed")


@cocotb.test()
async def all_byte_strobes(dut):
    await reset_dut(dut)

    # Initialize all four bytes.
    assert await write_reg(dut, 0x08, 0x11223344) == 0

    # Update byte lane 0 only.
    assert await write_reg(dut, 0x08, 0x000000AA, 0x1) == 0
    assert await read_reg(dut, 0x08) == 0x112233AA

    # Update byte lane 1 only.
    assert await write_reg(dut, 0x08, 0x0000BB00, 0x2) == 0
    assert await read_reg(dut, 0x08) == 0x1122BBAA

    # Update byte lane 2 only.
    assert await write_reg(dut, 0x08, 0x00CC0000, 0x4) == 0
    assert await read_reg(dut, 0x08) == 0x11CCBBAA

    # Update byte lane 3 only.
    assert await write_reg(dut, 0x08, 0xDD000000, 0x8) == 0
    assert await read_reg(dut, 0x08) == 0xDDCCBBAA

    dut._log.info("All four byte strobes test passed")


@cocotb.test()
async def randomized_src_addr_writes(dut):
    import random

    await reset_dut(dut)
    rng = random.Random(20261017)

    expected = 0

    for iteration in range(50):
        data = rng.getrandbits(32)
        strobe = rng.randint(0, 15)

        assert await write_reg(dut, 0x08, data, strobe) == 0

        for lane in range(4):
            if strobe & (1 << lane):
                mask = 0xFF << (8 * lane)
                expected = (expected & ~mask) | (data & mask)

        actual = await read_reg(dut, 0x08)
        assert actual == expected, (
            f"Iteration {iteration}: WSTRB={strobe:#x}, "
            f"expected={expected:#010x}, actual={actual:#010x}"
        )

    dut._log.info("Randomized SRC_ADDR writes test passed")


@cocotb.test()
async def randomized_multiple_register_writes(dut):
    import random

    await reset_dut(dut)
    rng = random.Random(20261018)

    registers = {
        0x08: 0,
        0x0C: 0,
        0x10: 0,
    }

    for iteration in range(30):
        addr = rng.choice(list(registers.keys()))
        data = rng.getrandbits(32)
        strobe = rng.randint(0, 15)

        assert await write_reg(dut, addr, data, strobe) == 0

        expected = registers[addr]
        for lane in range(4):
            if strobe & (1 << lane):
                mask = 0xFF << (8 * lane)
                expected = (expected & ~mask) | (data & mask)

        registers[addr] = expected

        for check_addr, expected_value in registers.items():
            actual = await read_reg(dut, check_addr)
            assert actual == expected_value, (
                f"Iteration {iteration}, register {check_addr:#x}: "
                f"expected={expected_value:#010x}, actual={actual:#010x}"
            )

    dut._log.info("Randomized multiple-register test passed")


@cocotb.test()
async def no_new_write_while_response_stalled(dut):
    await reset_dut(dut)

    # Complete the first write but keep its response stalled.
    assert await write_reg(dut, 0x08, 0x12345678) == 0

    # write_reg consumes the response, so create a stalled response
    # explicitly for a second transaction.
    dut.s_bready.value = 0
    dut.s_awaddr.value = 0x0C
    dut.s_awvalid.value = 1
    dut.s_wdata.value = 0xA5A5A5A5
    dut.s_wstrb.value = 0xF
    dut.s_wvalid.value = 1

    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        aw = int(dut.s_awready.value) and int(dut.s_awvalid.value)
        w = int(dut.s_wready.value) and int(dut.s_wvalid.value)
        dut.aclk.value = 1
        await Timer(5, unit="ns")
        if aw:
            dut.s_awvalid.value = 0
        if w:
            dut.s_wvalid.value = 0
        if int(dut.s_bvalid.value):
            break
    else:
        raise AssertionError("Second write response timeout")

    held_resp = int(dut.s_bresp.value)
    held_dst = await read_reg(dut, 0x0C)

    for _ in range(3):
        await cycle(dut)
        assert int(dut.s_bvalid.value) == 1
        assert int(dut.s_bresp.value) == held_resp

    # Release the response and confirm the write took effect.
    dut.s_bready.value = 1
    await cycle(dut)
    dut.s_bready.value = 0

    assert await read_reg(dut, 0x0C) == 0xA5A5A5A5


@cocotb.test()
async def write_channels_not_accepted_during_stalled_response(dut):
    await reset_dut(dut)

    # Start first write and stall its response.
    dut.s_awaddr.value = 0x08
    dut.s_awvalid.value = 1
    dut.s_wdata.value = 0x11112222
    dut.s_wstrb.value = 0xF
    dut.s_wvalid.value = 1
    dut.s_bready.value = 0

    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        aw = int(dut.s_awvalid.value) and int(dut.s_awready.value)
        w = int(dut.s_wvalid.value) and int(dut.s_wready.value)
        dut.aclk.value = 1
        await Timer(5, unit="ns")
        if aw:
            dut.s_awvalid.value = 0
        if w:
            dut.s_wvalid.value = 0
        if int(dut.s_bvalid.value):
            break
    else:
        raise AssertionError("First write response timeout")

    assert int(dut.s_bvalid.value) == 1

    # Present a second request while the first response is stalled.
    dut.s_awaddr.value = 0x0C
    dut.s_awvalid.value = 1
    dut.s_wdata.value = 0xAABBCCDD
    dut.s_wstrb.value = 0xF
    dut.s_wvalid.value = 1

    for _ in range(3):
        await cycle(dut)
        assert int(dut.s_bvalid.value) == 1
        assert int(dut.s_awready.value) == 0
        assert int(dut.s_wready.value) == 0

    assert int(dut.s_awvalid.value) == 1
    assert int(dut.s_wvalid.value) == 1
    assert await read_reg(dut, 0x0C) == 0

    # Release the first response.
    dut.s_bready.value = 1
    await cycle(dut)
    dut.s_bready.value = 0

    for _ in range(10):
        dut.aclk.value = 0
        await Timer(5, unit="ns")
        aw = int(dut.s_awvalid.value) and int(dut.s_awready.value)
        w = int(dut.s_wvalid.value) and int(dut.s_wready.value)
        dut.aclk.value = 1
        await Timer(5, unit="ns")
        if aw:
            dut.s_awvalid.value = 0
        if w:
            dut.s_wvalid.value = 0
        if int(dut.s_bvalid.value):
            break
    else:
        raise AssertionError("Second write response timeout")

    assert int(dut.s_bvalid.value) == 1
    assert await read_reg(dut, 0x0C) == 0xAABBCCDD


@cocotb.test()
async def remaining_register_coverage(dut):
    """Exercise remaining register read and CONTROL write coverage."""
    await reset_dut(dut)

    # CONTROL is readable but reads as zero.
    assert await read_reg(dut, 0x00) == 0

    # STATUS reflects busy, done, and error.
    assert await read_reg(dut, 0x04) == 0
    dut.busy.value = 1
    await cycle(dut)
    assert await read_reg(dut, 0x04) == 1
    dut.busy.value = 0
    await cycle(dut)

    # Exercise the remaining read-only status registers.
    assert await read_reg(dut, 0x14) == 0
    assert await read_reg(dut, 0x18) == 0
    assert await read_reg(dut, 0x20) == 0

    # CONTROL is a command register, not a stored data register.
    # A zero write is valid and does not request a DMA start.
    response = await write_reg(dut, 0x00, 0x00000000)
    assert response == 0
    assert await read_reg(dut, 0x00) == 0


@cocotb.test()
async def write_functional_coverage_report(dut):
    """Write the accumulated functional coverage report."""
    coverage.write_report()
    dut._log.info(
        "Functional coverage report written to reports/functional_coverage.txt"
    )
