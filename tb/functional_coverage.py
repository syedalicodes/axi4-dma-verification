"""User-defined functional coverage for the AXI4-Lite register block."""

from collections import Counter
from pathlib import Path

REGISTER_NAMES = {
    0x00: "CONTROL",
    0x04: "STATUS",
    0x08: "SRC_ADDR",
    0x0C: "DST_ADDR",
    0x10: "LENGTH",
    0x14: "WORDS_DONE",
    0x18: "IRQ_ENABLE",
    0x1C: "IRQ_STATUS",
    0x20: "ERROR_CODE",
}

WRITABLE_REGISTERS = {
    0x00, 0x08, 0x0C, 0x10, 0x18, 0x1C
}
EXPECTED_STROBES = {0x0, 0x1, 0x2, 0x4, 0x8, 0x3, 0xC, 0xF}
EXPECTED_RESPONSES = {"OKAY", "SLVERR"}
EXPECTED_SCENARIOS = {
    "reset",
    "write_backpressure",
    "read_backpressure",
    "invalid_address",
    "interrupts",
    "independent_aw_w",
}


class FunctionalCoverage:
    def __init__(self):
        self.register_reads = set()
        self.register_writes = set()
        self.strobes = set()
        self.responses = set()
        self.scenarios = set()
        self.counts = Counter()

    def sample_register_read(self, address):
        if address in REGISTER_NAMES:
            self.register_reads.add(address)
        self.counts["register_reads"] += 1

    def sample_register_write(self, address, strobe=0xF):
        if address in WRITABLE_REGISTERS:
            self.register_writes.add(address)
        self.strobes.add(strobe & 0xF)
        self.counts["register_writes"] += 1

    def sample_response(self, response):
        names = {0: "OKAY", 2: "SLVERR"}
        name = names.get(int(response))
        if name is not None:
            self.responses.add(name)
        self.counts["responses"] += 1

    def sample_scenario(self, scenario):
        if scenario in EXPECTED_SCENARIOS:
            self.scenarios.add(scenario)

    def write_report(self, path="reports/functional_coverage.txt"):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        total_bins = (
            len(REGISTER_NAMES)
            + len(WRITABLE_REGISTERS)
            + len(EXPECTED_STROBES)
            + len(EXPECTED_RESPONSES)
            + len(EXPECTED_SCENARIOS)
        )
        covered_bins = (
            len(self.register_reads)
            + len(self.register_writes)
            + len(self.strobes & EXPECTED_STROBES)
            + len(self.responses & EXPECTED_RESPONSES)
            + len(self.scenarios & EXPECTED_SCENARIOS)
        )
        percentage = 100.0 * covered_bins / total_bins

        with path.open("w", encoding="utf-8") as report:
            report.write("AXI4-Lite Register Functional Coverage\n")
            report.write("=" * 40 + "\n")
            report.write(f"Coverage bins hit: {covered_bins}/{total_bins}\n")
            report.write(f"Coverage percentage: {percentage:.1f}%\n")
            report.write(
                "Note: user-defined transaction coverage; "
                "not RTL code or toggle coverage.\n\n"
            )

            report.write("Register reads:\n")
            for address, name in REGISTER_NAMES.items():
                status = "HIT" if address in self.register_reads else "MISS"
                report.write(f"  {name:12} 0x{address:02X}: {status}\n")

            report.write("\nSoftware-writable registers:\n")
            for address in sorted(WRITABLE_REGISTERS):
                name = REGISTER_NAMES[address]
                status = "HIT" if address in self.register_writes else "MISS"
                report.write(f"  {name:12} 0x{address:02X}: {status}\n")

            report.write("\nByte strobes:\n")
            for strobe in sorted(EXPECTED_STROBES):
                status = "HIT" if strobe in self.strobes else "MISS"
                report.write(f"  0x{strobe:X}: {status}\n")

            report.write("\nAXI responses:\n")
            for response in sorted(EXPECTED_RESPONSES):
                status = "HIT" if response in self.responses else "MISS"
                report.write(f"  {response}: {status}\n")

            report.write("\nScenarios:\n")
            for scenario in sorted(EXPECTED_SCENARIOS):
                status = "HIT" if scenario in self.scenarios else "MISS"
                report.write(f"  {scenario}: {status}\n")

            report.write("\nSample counts:\n")
            for name, count in sorted(self.counts.items()):
                report.write(f"  {name}: {count}\n")
