#!/usr/bin/env python3
"""
STM32 .ato generator — reads STM32_open_pin_data XML and produces
an atopile module definition for the MCU.

Key insight: After `ato create part` installs a part, we parse the
generated component .ato file to discover the *actual* signal names
(which vary per chip in unpredictable ways for power pins).

Usage:
    python stm32_gen.py /path/to/STM32F103C8Tx.xml \
        --mfr-search STMicroelectronics:STM32F103C8T6
    python stm32_gen.py /path/to/STM32H743ZITx.xml --lcsc C114408
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Data Model ──────────────────────────────────────────────────────────


@dataclass
class McuSignal:
    name: str
    io_modes: Optional[str] = None


@dataclass
class McuPin:
    name: str  # e.g. "PA0-WKUP", "VDD", "PB3(JTDO/TRACESWO)"
    position: str  # string — numeric for LQFP, alphanumeric for BGA
    pin_type: str  # "I/O", "Power", "Reset", "Boot", "MonoIO"
    signals: list[McuSignal] = field(default_factory=list)

    @property
    def is_io(self) -> bool:
        return self.pin_type == "I/O"

    @property
    def is_power(self) -> bool:
        return self.pin_type == "Power"

    @property
    def gpio_port_pin(self) -> tuple[str, int] | None:
        """Extract (port_letter, pin_number) from name like 'PA0-WKUP'."""
        m = re.match(r"^P([A-Z])(\d+)", self.name)
        if m:
            return m.group(1), int(m.group(2))
        return None

    @property
    def signal_names(self) -> list[str]:
        return [sig.name for sig in self.signals if sig.name != "GPIO"]


@dataclass
class McuInfo:
    ref_name: str
    family: str
    line: str
    package_type: str
    core: str
    frequency: int
    ram: int
    flash: list[int]
    voltage_min: float
    voltage_max: float
    temp_min: int
    temp_max: int
    ip_instances: dict[str, str]  # instance_name -> ip_name
    pins: list[McuPin]


# ── Installed Part Model ────────────────────────────────────────────────


@dataclass
class PartSignal:
    """A signal from the auto-generated package .ato file."""

    name: str  # e.g. "VDD", "VDD_1", "PA0_WKUP", "VREFpos", "Vcap_1"
    pin_numbers: list[str]  # physical pin positions this signal connects to


@dataclass
class InstalledPart:
    """Parsed info from the auto-generated package .ato file."""

    import_name: str  # e.g. "STMicroelectronics_STM32F103C8T6"
    component_name: str  # e.g. "STMicroelectronics_STM32F103C8T6_package"
    signals: dict[str, PartSignal]  # signal_name -> PartSignal

    def find_gpio_signal(self, port: str, num: int) -> str | None:
        """Find the signal name for a GPIO pin like PA0, PB3, etc.

        Handles LCSC naming quirks:
        - Standard: PA0, PB3, PC14_OSC32_IN
        - Wakeup suffix: PA0_WKUP, PA0_CK_IN
        - SWD fused: PA13SWDIO, PA14SWCLK
        - Boot fused: PA14_BOOT0, PB8_BOOT0, PH3_BOOT0
        - Remappable (G0/C0): PA11PA9, PA12PA10
        - NRST fused: PF2_NRST, PG10_NRST
        """
        target = f"P{port}{num}"

        # 1. Exact match
        if target in self.signals:
            return target

        # 2. Exact match on the "base" part (strip first _ and everything after)
        for name in self.signals:
            base = re.split(r"[_]", name)[0]
            if base == target:
                return name

        # 3. Prefix match: signal starts with P{port}{num} followed by non-digit
        #    (to distinguish PA1 from PA10, PA11, etc.)
        for name in self.signals:
            if re.match(rf"^{re.escape(target)}(?:\D|$)", name):
                return name

        return None

    def find_power_signals(self, pattern: str) -> list[str]:
        """Find all signal names matching a regex pattern."""
        return [n for n in self.signals if re.match(pattern, n, re.IGNORECASE)]


def parse_part_ato(part_dir: Path) -> InstalledPart | None:
    """Parse the auto-generated package .ato file to extract signal names."""
    ato_files = list(part_dir.glob("*.ato"))
    if not ato_files:
        return None

    ato_file = ato_files[0]
    import_name = ato_file.stem
    component_name = f"{import_name}_package"
    signals: dict[str, PartSignal] = {}

    text = ato_file.read_text()
    # Match both "signal NAME ~ pin N" and "NAME ~ pin N" (continuation)
    current_signal: str | None = None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"signal\s+(\w+)\s+~\s+pin\s+(\S+)", line)
        if m:
            current_signal = m.group(1)
            pin_num = m.group(2)
            if current_signal in signals:
                signals[current_signal].pin_numbers.append(pin_num)
            else:
                signals[current_signal] = PartSignal(
                    name=current_signal, pin_numbers=[pin_num]
                )
            continue
        m = re.match(r"(\w+)\s+~\s+pin\s+(\S+)", line)
        if m:
            sig_name = m.group(1)
            pin_num = m.group(2)
            if sig_name in signals:
                signals[sig_name].pin_numbers.append(pin_num)

    return InstalledPart(
        import_name=import_name, component_name=component_name, signals=signals
    )


# ── XML Parser ──────────────────────────────────────────────────────────

NS = {"stm": "http://dummy.com"}


def parse_mcu_xml(xml_path: Path) -> McuInfo:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    ref_name = root.attrib["RefName"]
    family = root.attrib["Family"]
    line = root.attrib.get("Line", "")
    package_type = root.attrib["Package"]

    core = root.findtext("stm:Core", "", NS)
    frequency = int(root.findtext("stm:Frequency", "0", NS))
    ram = int(root.findtext("stm:Ram", "0", NS))
    flash_values = [int(f.text) for f in root.findall("stm:Flash", NS) if f.text]

    voltage_el = root.find("stm:Voltage", NS)
    voltage_min = (
        float(voltage_el.attrib.get("Min", "0")) if voltage_el is not None else 0
    )
    voltage_max = (
        float(voltage_el.attrib.get("Max", "0")) if voltage_el is not None else 0
    )

    temp_el = root.find("stm:Temperature", NS)
    temp_min = (
        int(float(temp_el.attrib.get("Min", "-40"))) if temp_el is not None else -40
    )
    temp_max = (
        int(float(temp_el.attrib.get("Max", "85"))) if temp_el is not None else 85
    )

    ip_instances: dict[str, str] = {}
    for ip_el in root.findall("stm:IP", NS):
        inst = ip_el.attrib.get("InstanceName", "")
        name = ip_el.attrib.get("Name", "")
        if inst and name:
            ip_instances[inst] = name

    pins: list[McuPin] = []
    for pin_el in root.findall("stm:Pin", NS):
        sigs = []
        for sig_el in pin_el.findall("stm:Signal", NS):
            sigs.append(
                McuSignal(
                    name=sig_el.attrib["Name"],
                    io_modes=sig_el.attrib.get("IOModes"),
                )
            )
        pins.append(
            McuPin(
                name=pin_el.attrib["Name"],
                position=pin_el.attrib["Position"],
                pin_type=pin_el.attrib["Type"],
                signals=sigs,
            )
        )

    return McuInfo(
        ref_name=ref_name,
        family=family,
        line=line,
        package_type=package_type,
        core=core,
        frequency=frequency,
        ram=ram,
        flash=flash_values,
        voltage_min=voltage_min,
        voltage_max=voltage_max,
        temp_min=temp_min,
        temp_max=temp_max,
        ip_instances=ip_instances,
        pins=pins,
    )


# ── Interface Discovery ─────────────────────────────────────────────────


@dataclass
class InterfaceMapping:
    iface_type: str
    instance_name: str
    pin_map: dict[str, tuple[str, int]]  # role -> (port, pin_num)


# Interface discovery patterns — ORDER MATTERS for pin conflict resolution.
# Higher priority interfaces are discovered first and get their preferred pins.
# Priority: SWD > USB > I2C > UART > SPI (SPI last because it has the most
# alternate pin options and can afford to lose a few).
SIGNAL_PATTERNS: list[tuple[str, list[tuple[str, re.Pattern]]]] = [
    (
        "SWD",
        [
            ("dio", re.compile(r"^(?:SYS|DEBUG)_(?:JTMS[_-])?SWDIO$")),
            ("clk", re.compile(r"^(?:SYS|DEBUG)_(?:JTCK[_-])?SWCLK$")),
        ],
    ),
    # Prefer Full-Speed USB (direct connection) over High-Speed (needs ULPI PHY)
    (
        "USB",
        [
            ("dm", re.compile(r"^USB(?:_OTG_FS)?_DM?$")),
            ("dp", re.compile(r"^USB(?:_OTG_FS)?_DP?$")),
        ],
    ),
    (
        "I2C",
        [
            ("scl", re.compile(r"^I2C(\d+)_SCL$")),
            ("sda", re.compile(r"^I2C(\d+)_SDA$")),
        ],
    ),
    (
        "UART",
        [
            ("tx", re.compile(r"^(?:USART|UART|LPUART)(\d+)_TX$")),
            ("rx", re.compile(r"^(?:USART|UART|LPUART)(\d+)_RX$")),
        ],
    ),
    (
        "SPI",
        [
            ("sclk", re.compile(r"^SPI(\d+)_SCK$")),
            ("miso", re.compile(r"^SPI(\d+)_MISO$")),
            ("mosi", re.compile(r"^SPI(\d+)_MOSI$")),
        ],
    ),
]


def discover_interfaces(mcu: McuInfo) -> list[InterfaceMapping]:
    signal_pins: dict[str, list[tuple[str, int]]] = {}
    for pin in mcu.pins:
        gpp = pin.gpio_port_pin
        if gpp is None:
            continue
        port, pin_num = gpp
        for sig in pin.signals:
            if sig.name != "GPIO":
                signal_pins.setdefault(sig.name, []).append((port, pin_num))

    found: dict[str, InterfaceMapping] = {}
    used_pins: set[tuple[str, int]] = set()  # Track used pins to avoid conflicts

    for iface_type, role_patterns in SIGNAL_PATTERNS:
        instances: dict[str, dict[str, list[tuple[str, int]]]] = {}

        for role, pattern in role_patterns:
            for sig_name, pin_locs in signal_pins.items():
                m = pattern.match(sig_name)
                if m:
                    if iface_type in ("USB", "SWD"):
                        inst_id = "1"
                    else:
                        inst_id = m.group(1)

                    inst_name_map = {
                        "I2C": f"I2C{inst_id}",
                        "SPI": f"SPI{inst_id}",
                        "UART": f"USART{inst_id}"
                        if f"USART{inst_id}" in mcu.ip_instances
                        else f"UART{inst_id}",
                        "USB": "USB",
                        "SWD": "SWD",
                    }
                    inst_name = inst_name_map.get(iface_type, f"{iface_type}{inst_id}")
                    instances.setdefault(inst_name, {}).setdefault(role, []).extend(
                        pin_locs
                    )

        for inst_name, roles in sorted(instances.items()):
            required = {r for r, _ in role_patterns}
            if required <= set(roles.keys()):
                pin_map = {}
                conflict = False
                for role in required:
                    # Pick first candidate pin not already used by a higher-priority
                    # interface.
                    chosen = None
                    for candidate in roles[role]:
                        if candidate not in used_pins:
                            chosen = candidate
                            break
                    if chosen is None:
                        # All candidates conflict — skip this peripheral instance
                        conflict = True
                        break
                    pin_map[role] = chosen
                if not conflict:
                    # Mark pins as used
                    for pin_loc in pin_map.values():
                        used_pins.add(pin_loc)
                    found[inst_name] = InterfaceMapping(
                        iface_type=iface_type,
                        instance_name=inst_name,
                        pin_map=pin_map,
                    )

    return list(found.values())


# ── Power Domain Analysis ────────────────────────────────────────────────


@dataclass
class PowerDomain:
    name: str
    hv_signals: list[str]  # actual package signal names
    lv_signals: list[str]
    voltage_min: float
    voltage_max: float
    is_required: bool
    decoupling: list[tuple[str, str, int]]  # (capacitance, pkg_size, count)


def analyze_power_from_part(part: InstalledPart, mcu: McuInfo) -> list[PowerDomain]:
    """Analyze power domains from the actual installed part signal names."""
    domains: list[PowerDomain] = []

    # Find VDD signals
    vdd_sigs = part.find_power_signals(r"^VDD(_\d+)?$")
    vss_sigs = part.find_power_signals(r"^VSS(_\d+)?$")

    # Combined VDD/VDDA (e.g. C031: VDD_VDDA)
    vdd_vdda_sigs = part.find_power_signals(r"^VDD_VDDA$")

    # Analog
    vdda_sigs = part.find_power_signals(r"^VDDA$")
    vssa_sigs = part.find_power_signals(r"^VSSA$")

    # Combined VDDA_VREFpos
    vdda_vref_sigs = part.find_power_signals(r"^VDDA_VREFpos$")
    vssa_vref_sigs = part.find_power_signals(r"^VSSA_VREFneg$")

    # Combined VSS/VSSA
    vss_vssa_sigs = part.find_power_signals(r"^VSS_VSSA$")

    # USB
    usb_sigs = part.find_power_signals(r"^VDD(33)?USB$")

    # VCAP
    vcap_sigs = part.find_power_signals(r"^[Vv]cap")

    # VBAT
    vbat_sigs = part.find_power_signals(r"^VBAT$")

    # VREF
    vref_sigs = part.find_power_signals(r"^VREFpos$")

    # Count total VDD physical pins for decoupling sizing
    total_vdd_pins = sum(
        len(part.signals[s].pin_numbers) for s in vdd_sigs if s in part.signals
    )
    total_vdd_pins += sum(
        len(part.signals[s].pin_numbers) for s in vdd_vdda_sigs if s in part.signals
    )

    all_hv = vdd_sigs + vdd_vdda_sigs
    all_lv = vss_sigs + vss_vssa_sigs

    if all_hv or vdd_vdda_sigs:
        n_caps = max(total_vdd_pins, 1)
        decoupling = [("100nF +/- 20%", "0402", n_caps)]
        if total_vdd_pins >= 3:
            decoupling.append(("4.7uF +/- 20%", "0402", 1))
        else:
            decoupling.append(("1uF +/- 20%", "0402", 1))

        domains.append(
            PowerDomain(
                name="power_3v3",
                hv_signals=all_hv,
                lv_signals=all_lv,
                voltage_min=mcu.voltage_min,
                voltage_max=mcu.voltage_max,
                is_required=True,
                decoupling=decoupling,
            )
        )

    # Separate analog domain (only if not combined with VDD)
    analog_hv = vdda_sigs + vdda_vref_sigs
    analog_lv = vssa_sigs + vssa_vref_sigs
    if analog_hv:
        domains.append(
            PowerDomain(
                name="power_analog",
                hv_signals=analog_hv,
                lv_signals=analog_lv,
                voltage_min=mcu.voltage_min,
                voltage_max=mcu.voltage_max,
                is_required=False,
                decoupling=[("1uF +/- 20%", "0402", 1), ("100nF +/- 20%", "0402", 1)],
            )
        )

    if usb_sigs:
        domains.append(
            PowerDomain(
                name="power_usb",
                hv_signals=usb_sigs,
                lv_signals=[],
                voltage_min=3.0,
                voltage_max=3.6,
                is_required=False,
                decoupling=[("100nF +/- 20%", "0402", 1), ("1uF +/- 20%", "0402", 1)],
            )
        )

    if vcap_sigs:
        domains.append(
            PowerDomain(
                name="power_vcap",
                hv_signals=vcap_sigs,
                lv_signals=[],
                voltage_min=1.0,
                voltage_max=1.4,
                is_required=False,
                decoupling=[("2.2uF +/- 20%", "0402", len(vcap_sigs))],
            )
        )

    if vbat_sigs:
        domains.append(
            PowerDomain(
                name="vbat",
                hv_signals=vbat_sigs,
                lv_signals=[],
                voltage_min=1.65,
                voltage_max=3.6,
                is_required=False,
                decoupling=[("100nF +/- 20%", "0402", 1)],
            )
        )

    # Standalone VREF+ (only if not combined with VDDA)
    if vref_sigs and not vdda_vref_sigs:
        domains.append(
            PowerDomain(
                name="power_vref",
                hv_signals=vref_sigs,
                lv_signals=[],
                voltage_min=mcu.voltage_min,
                voltage_max=mcu.voltage_max,
                is_required=False,
                decoupling=[("1uF +/- 20%", "0402", 1), ("100nF +/- 20%", "0402", 1)],
            )
        )

    # VDDIO (I/O power domain, e.g. F072)
    vddio_sigs = part.find_power_signals(r"^VDDIO$")
    if vddio_sigs:
        domains.append(
            PowerDomain(
                name="power_io",
                hv_signals=vddio_sigs,
                lv_signals=[],
                voltage_min=mcu.voltage_min,
                voltage_max=mcu.voltage_max,
                is_required=False,
                decoupling=[("100nF +/- 20%", "0402", 1)],
            )
        )

    # VLCD (LCD supply, e.g. L073)
    vlcd_sigs = part.find_power_signals(r"^VLCD$")
    if vlcd_sigs:
        domains.append(
            PowerDomain(
                name="power_lcd",
                hv_signals=vlcd_sigs,
                lv_signals=[],
                voltage_min=2.5,
                voltage_max=3.6,
                is_required=False,
                decoupling=[("1uF +/- 20%", "0402", 1)],
            )
        )

    # PDR_ON (power-down reset, e.g. H723/H743 - connect to VDD)
    pdr_sigs = part.find_power_signals(r"^PDR_ON$")
    if pdr_sigs:
        domains.append(
            PowerDomain(
                name="pdr_on",
                hv_signals=pdr_sigs,
                lv_signals=[],
                voltage_min=mcu.voltage_min,
                voltage_max=mcu.voltage_max,
                is_required=False,
                decoupling=[],  # No decoupling, just a connection to VDD
            )
        )

    return domains


# ── GPIO Port Analysis ──────────────────────────────────────────────────


@dataclass
class GpioPort:
    letter: str
    pins: dict[int, McuPin]

    @property
    def max_index(self) -> int:
        return max(self.pins.keys()) if self.pins else -1

    @property
    def array_size(self) -> int:
        return self.max_index + 1


def analyze_gpio_ports(mcu: McuInfo) -> dict[str, GpioPort]:
    ports: dict[str, GpioPort] = {}
    for pin in mcu.pins:
        gpp = pin.gpio_port_pin
        if gpp is None or not pin.is_io:
            continue
        port_letter, pin_num = gpp
        if port_letter not in ports:
            ports[port_letter] = GpioPort(letter=port_letter, pins={})
        ports[port_letter].pins[pin_num] = pin
    return dict(sorted(ports.items()))


# ── Crystal Detection ────────────────────────────────────────────────────


@dataclass
class CrystalInterface:
    name: str
    xin_signal: str  # actual package signal name
    xout_signal: str


def detect_crystals(mcu: McuInfo, part: InstalledPart) -> list[CrystalInterface]:
    crystals: list[CrystalInterface] = []

    # Find pins with RCC_OSC_IN/OUT signals
    osc_in_port = None
    osc_out_port = None
    osc32_in_port = None
    osc32_out_port = None

    for pin in mcu.pins:
        gpp = pin.gpio_port_pin
        for sig in pin.signals:
            if sig.name == "RCC_OSC_IN":
                osc_in_port = gpp
            elif sig.name == "RCC_OSC_OUT":
                osc_out_port = gpp
            elif sig.name == "RCC_OSC32_IN":
                osc32_in_port = gpp
            elif sig.name == "RCC_OSC32_OUT":
                osc32_out_port = gpp

    # Find the actual signal name in the installed part for these pins
    if osc_in_port and osc_out_port:
        xin_sig = part.find_gpio_signal(osc_in_port[0], osc_in_port[1])
        xout_sig = part.find_gpio_signal(osc_out_port[0], osc_out_port[1])
        if xin_sig and xout_sig:
            crystals.append(CrystalInterface("hse", xin_sig, xout_sig))

    if osc32_in_port and osc32_out_port:
        xin_sig = part.find_gpio_signal(osc32_in_port[0], osc32_in_port[1])
        xout_sig = part.find_gpio_signal(osc32_out_port[0], osc32_out_port[1])
        if xin_sig and xout_sig:
            crystals.append(CrystalInterface("lse", xin_sig, xout_sig))

    return crystals


# ── Code Generator ──────────────────────────────────────────────────────


def make_module_name(ref_name: str) -> str:
    cleaned = re.sub(r"\(([^)]*)\)", lambda m: m.group(1).split("-")[0], ref_name)
    cleaned = cleaned.rstrip("x") + "6" if cleaned.endswith("x") else cleaned
    return f"ST_{cleaned}"


def generate_ato(
    mcu: McuInfo,
    part: InstalledPart,
    interfaces: list[InterfaceMapping],
    power_domains: list[PowerDomain],
    gpio_ports: dict[str, GpioPort],
    crystals: list[CrystalInterface],
) -> str:
    lines: list[str] = []
    indent = "    "
    module_name = make_module_name(mcu.ref_name)

    # ── Pragmas ──
    lines.append('#pragma experiment("MODULE_TEMPLATING")')
    lines.append('#pragma experiment("BRIDGE_CONNECT")')
    lines.append('#pragma experiment("FOR_LOOP")')
    lines.append('#pragma experiment("TRAITS")')
    lines.append("")

    # ── Imports ──
    imports_needed = {"ElectricPower", "ElectricLogic", "Capacitor"}
    iface_types_used = {i.iface_type for i in interfaces}
    if "SWD" in iface_types_used:
        imports_needed.add("SWD")
    if "USB" in iface_types_used:
        imports_needed.add("USB2_0")
    if "UART" in iface_types_used:
        imports_needed.add("UART")
    if "SPI" in iface_types_used:
        imports_needed.add("SPI")
    if "I2C" in iface_types_used:
        imports_needed.add("I2C")
    if crystals:
        imports_needed.add("XtalIF")

    for imp in sorted(imports_needed):
        lines.append(f"import {imp}")
    lines.append("")

    import_line = (
        f'from "parts/{part.import_name}/{part.import_name}.ato" '
        f"import {part.component_name}"
    )
    lines.append(import_line)
    lines.append("")

    # ── Module ──
    flash_str = "/".join(str(f) for f in mcu.flash)
    lines.append(f"module {module_name}:")
    lines.append(f'{indent}"""')
    lines.append(f"{indent}STMicroelectronics {mcu.ref_name}")
    lines.append(f"{indent}({mcu.core} up to {mcu.frequency} MHz).")
    lines.append(
        f"{indent}{flash_str} KB Flash, {mcu.ram} KB SRAM, {mcu.package_type}."
    )
    lines.append(f'{indent}"""')
    lines.append("")
    lines.append(f"{indent}# --- Package ---")
    lines.append(f"{indent}package = new {part.component_name}")
    lines.append("")

    # ── Power domains ──
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append(f"{indent}# Power domains")
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append("")

    domain_map: dict[str, PowerDomain] = {d.name: d for d in power_domains}
    main = domain_map.get("power_3v3")
    analog = domain_map.get("power_analog")
    usb_pwr = domain_map.get("power_usb")
    vcap = domain_map.get("power_vcap")
    vbat_d = domain_map.get("vbat")
    vref = domain_map.get("power_vref")
    vddio = domain_map.get("power_io")
    vlcd = domain_map.get("power_lcd")
    pdr_on = domain_map.get("pdr_on")

    if main:
        lines.append(f"{indent}power_3v3 = new ElectricPower")
        lines.append(f'{indent}"""Primary supply domain')
        lines.append(f"{indent}({main.voltage_min}V to {main.voltage_max}V).")
        lines.append(f'{indent}"""')
        lines.append(f"{indent}power_3v3.required = True")
        lines.append(
            f"{indent}assert power_3v3.voltage within "
            f"{main.voltage_min}V to {main.voltage_max}V"
        )
        lines.append("")

    if analog:
        lines.append(f"{indent}power_analog = new ElectricPower")
        lines.append(f'{indent}"""Analog supply domain (VDDA/VSSA)."""')
        lines.append("")

    if usb_pwr:
        lines.append(f"{indent}power_usb = new ElectricPower")
        lines.append(f'{indent}"""USB dedicated supply."""')
        lines.append("")

    if vcap:
        lines.append(f"{indent}power_vcap = new ElectricPower")
        lines.append(f'{indent}"""Core regulator output (VCAP)."""')
        lines.append("")

    if vbat_d:
        lines.append(f"{indent}vbat = new ElectricPower")
        lines.append(f'{indent}"""Backup battery domain (VBAT)."""')
        lines.append("")

    if vref:
        lines.append(f"{indent}power_vref = new ElectricPower")
        lines.append(f'{indent}"""Voltage reference (VREF+)."""')
        lines.append("")

    if vddio:
        lines.append(f"{indent}power_io = new ElectricPower")
        lines.append(f'{indent}"""I/O power supply domain (VDDIO)."""')
        lines.append("")

    if vlcd:
        lines.append(f"{indent}power_lcd = new ElectricPower")
        lines.append(f'{indent}"""LCD power supply domain (VLCD)."""')
        lines.append("")

    # Tie secondary domains to main
    ties = []
    if analog and main:
        ties.append("power_3v3 ~ power_analog")
    if usb_pwr and main:
        ties.append("power_3v3 ~ power_usb")
    if vddio and main:
        ties.append("power_3v3 ~ power_io")
    for t in ties:
        lines.append(f"{indent}{t}")
    if ties:
        lines.append("")

    # ── External interfaces ──
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append(f"{indent}# External interfaces")
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append("")

    swd_ifaces = [i for i in interfaces if i.iface_type == "SWD"]
    usb_ifaces = [i for i in interfaces if i.iface_type == "USB"]
    uart_ifaces = sorted(
        [i for i in interfaces if i.iface_type == "UART"], key=lambda x: x.instance_name
    )
    spi_ifaces = sorted(
        [i for i in interfaces if i.iface_type == "SPI"], key=lambda x: x.instance_name
    )
    i2c_ifaces = sorted(
        [i for i in interfaces if i.iface_type == "I2C"], key=lambda x: x.instance_name
    )

    if swd_ifaces:
        lines.append(f"{indent}swd = new SWD")
        lines.append(f'{indent}"""Program/debug via Serial Wire Debug."""')
        lines.append("")

    if usb_ifaces:
        lines.append(f"{indent}usb = new USB2_0")
        lines.append(f'{indent}"""USB 2.0 Full-Speed device."""')
        lines.append("")

    def emit_iface_array(var_name, type_name, iface_list):
        if not iface_list:
            return
        if len(iface_list) == 1:
            lines.append(f"{indent}{var_name} = new {type_name}")
            lines.append(f'{indent}"""{iface_list[0].instance_name}."""')
        else:
            lines.append(f"{indent}{var_name} = new {type_name}[{len(iface_list)}]")
            desc = ", ".join(
                f"[{i}]={x.instance_name}" for i, x in enumerate(iface_list)
            )
            lines.append(f'{indent}"""{desc}."""')
        lines.append("")

    emit_iface_array("uart", "UART", uart_ifaces)
    emit_iface_array("spi", "SPI", spi_ifaces)
    emit_iface_array("i2c", "I2C", i2c_ifaces)

    for crystal in crystals:
        lines.append(f"{indent}{crystal.name} = new XtalIF")
        desc = (
            "High-speed external crystal oscillator."
            if crystal.name == "hse"
            else "Low-speed external crystal (32.768 kHz for RTC)."
        )
        lines.append(f'{indent}"""{desc}"""')
        lines.append("")

    # ── GPIO arrays ──
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append(f"{indent}# GPIO arrays by port")
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append("")
    for letter, port in gpio_ports.items():
        size = port.array_size
        n_bonded = len(port.pins)
        lines.append(f"{indent}gpio_{letter.lower()} = new ElectricLogic[{size}]")
        note = (
            f"all {size} pins bonded out"
            if n_bonded >= size
            else f"{n_bonded} of {size} pins bonded out"
        )
        lines.append(f'{indent}"""Port {letter}: {note}."""')
        lines.append("")

    # ── Decoupling ──
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append(f"{indent}# Decoupling capacitors")
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append("")

    for domain in power_domains:
        for cap_value, cap_pkg, cap_count in domain.decoupling:
            var_base = re.sub(
                r"[^a-zA-Z0-9_]",
                "",
                f"decoupling_{domain.name}_{cap_value.split()[0].replace('.', 'p')}",
            )
            if cap_count > 1:
                lines.append(f"{indent}{var_base} = new Capacitor[{cap_count}]")
                lines.append(f"{indent}for cap in {var_base}:")
                lines.append(f"{indent}    cap.capacitance = {cap_value}")
                lines.append(f'{indent}    cap.package = "{cap_pkg}"')
                lines.append(f"{indent}    {domain.name}.hv ~> cap ~> {domain.name}.lv")
            else:
                lines.append(f"{indent}{var_base} = new Capacitor")
                lines.append(f"{indent}{var_base}.capacitance = {cap_value}")
                lines.append(f'{indent}{var_base}.package = "{cap_pkg}"')
                lines.append(
                    f"{indent}{domain.name}.hv ~> {var_base} ~> {domain.name}.lv"
                )
            lines.append("")

    # ── Power pin connections ──
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append(f"{indent}# Package power connections")
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append("")

    if main:
        for sig in main.hv_signals:
            lines.append(f"{indent}package.{sig} ~ power_3v3.hv")
        for sig in main.lv_signals:
            lines.append(f"{indent}package.{sig} ~ power_3v3.lv")
        lines.append("")

    if analog:
        for sig in analog.hv_signals:
            lines.append(f"{indent}package.{sig} ~ power_analog.hv")
        for sig in analog.lv_signals:
            lines.append(f"{indent}package.{sig} ~ power_analog.lv")
        lines.append("")

    if usb_pwr:
        for sig in usb_pwr.hv_signals:
            lines.append(f"{indent}package.{sig} ~ power_usb.hv")
        lines.append(f"{indent}power_usb.lv ~ power_3v3.lv")
        lines.append("")

    if vcap:
        for sig in vcap.hv_signals:
            lines.append(f"{indent}package.{sig} ~ power_vcap.hv")
        lines.append(f"{indent}power_vcap.lv ~ power_3v3.lv")
        lines.append("")

    if vbat_d:
        for sig in vbat_d.hv_signals:
            lines.append(f"{indent}package.{sig} ~ vbat.hv")
        lines.append(f"{indent}vbat.lv ~ power_3v3.lv")
        lines.append("")

    if vref:
        ref_target = "power_analog" if analog else "power_3v3"
        for sig in vref.hv_signals:
            lines.append(f"{indent}package.{sig} ~ {ref_target}.hv")
        lines.append("")

    if vddio:
        for sig in vddio.hv_signals:
            lines.append(f"{indent}package.{sig} ~ power_io.hv")
        lines.append(f"{indent}power_io.lv ~ power_3v3.lv")
        lines.append("")

    if vlcd:
        for sig in vlcd.hv_signals:
            lines.append(f"{indent}package.{sig} ~ power_lcd.hv")
        lines.append(f"{indent}power_lcd.lv ~ power_3v3.lv")
        lines.append("")

    if pdr_on:
        lines.append(f"{indent}# PDR_ON — connect to VDD for internal power-on reset")
        for sig in pdr_on.hv_signals:
            lines.append(f"{indent}package.{sig} ~ power_3v3.hv")
        lines.append("")

    # ── Interface pin assignments ──
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append(f"{indent}# Interface pin assignments")
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append("")

    for iface in swd_ifaces:
        p_dio, n_dio = iface.pin_map["dio"]
        p_clk, n_clk = iface.pin_map["clk"]
        lines.append(f"{indent}# SWD debug")
        lines.append(f"{indent}swd.dio ~ gpio_{p_dio.lower()}[{n_dio}]")
        lines.append(f"{indent}swd.clk ~ gpio_{p_clk.lower()}[{n_clk}]")
        lines.append("")

    for iface in usb_ifaces:
        p_dm, n_dm = iface.pin_map["dm"]
        p_dp, n_dp = iface.pin_map["dp"]
        lines.append(f"{indent}# USB Full-Speed")
        lines.append(f"{indent}usb.usb_if.d.n ~ gpio_{p_dm.lower()}[{n_dm}]")
        lines.append(f"{indent}usb.usb_if.d.p ~ gpio_{p_dp.lower()}[{n_dp}]")
        lines.append("")

    for idx, iface in enumerate(uart_ifaces):
        p_tx, n_tx = iface.pin_map["tx"]
        p_rx, n_rx = iface.pin_map["rx"]
        prefix = f"uart[{idx}]" if len(uart_ifaces) > 1 else "uart"
        lines.append(
            f"{indent}# {iface.instance_name} (P{p_tx}{n_tx}=TX, P{p_rx}{n_rx}=RX)"
        )
        lines.append(f"{indent}{prefix}.base_uart.tx ~ gpio_{p_tx.lower()}[{n_tx}]")
        lines.append(f"{indent}{prefix}.base_uart.rx ~ gpio_{p_rx.lower()}[{n_rx}]")
        lines.append("")

    for idx, iface in enumerate(spi_ifaces):
        p_s, n_s = iface.pin_map["sclk"]
        p_mi, n_mi = iface.pin_map["miso"]
        p_mo, n_mo = iface.pin_map["mosi"]
        prefix = f"spi[{idx}]" if len(spi_ifaces) > 1 else "spi"
        lines.append(f"{indent}# {iface.instance_name}")
        lines.append(f"{indent}{prefix}.sclk ~ gpio_{p_s.lower()}[{n_s}]")
        lines.append(f"{indent}{prefix}.miso ~ gpio_{p_mi.lower()}[{n_mi}]")
        lines.append(f"{indent}{prefix}.mosi ~ gpio_{p_mo.lower()}[{n_mo}]")
        lines.append("")

    for idx, iface in enumerate(i2c_ifaces):
        p_scl, n_scl = iface.pin_map["scl"]
        p_sda, n_sda = iface.pin_map["sda"]
        prefix = f"i2c[{idx}]" if len(i2c_ifaces) > 1 else "i2c"
        lines.append(f"{indent}# {iface.instance_name}")
        lines.append(f"{indent}{prefix}.scl ~ gpio_{p_scl.lower()}[{n_scl}]")
        lines.append(f"{indent}{prefix}.sda ~ gpio_{p_sda.lower()}[{n_sda}]")
        lines.append("")

    # ── Crystal connections ──
    if crystals:
        lines.append(f"{indent}# " + "=" * 67)
        lines.append(f"{indent}# Crystal connections")
        lines.append(f"{indent}# " + "=" * 67)
        lines.append("")
        for crystal in crystals:
            lines.append(f"{indent}{crystal.name}.xin ~ package.{crystal.xin_signal}")
            lines.append(f"{indent}{crystal.name}.xout ~ package.{crystal.xout_signal}")
            lines.append(f"{indent}{crystal.name}.gnd ~ power_3v3.lv")
            lines.append("")

    # ── GPIO-to-package pin mappings ──
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append(f"{indent}# GPIO-to-package pin mappings")
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append("")

    for letter, port in gpio_ports.items():
        lines.append(f"{indent}# Port {letter}")
        for pin_num in sorted(port.pins.keys()):
            sig_name = part.find_gpio_signal(letter, pin_num)
            if sig_name:
                lines.append(
                    f"{indent}package.{sig_name} ~ "
                    f"gpio_{letter.lower()}[{pin_num}].line"
                )
            else:
                lines.append(
                    f"{indent}# WARNING: no package signal found for P{letter}{pin_num}"
                )
        lines.append("")

    # ── GPIO references ──
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append(f"{indent}# GPIO reference power connections")
    lines.append(
        f"{indent}# ==================================================================="
    )
    lines.append("")
    for letter in gpio_ports:
        lines.append(f"{indent}for io in gpio_{letter.lower()}:")
        lines.append(f"{indent}    io.reference ~ power_3v3")
    lines.append("")

    return "\n".join(lines)


# ── Part Installation ────────────────────────────────────────────────────


def install_part(project_dir: Path, search: str) -> str | None:
    """Run `ato create part` to install a part. Returns import name or None."""
    try:
        result = subprocess.run(
            ["ato", "create", "part", "-s", search, "-a", "-p", str(project_dir)],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "import" in line and "_package" in line:
                    m = re.search(r"import (\w+)_package", line)
                    if m:
                        return m.group(1)
        else:
            print(
                f"  WARNING: ato create part failed:\n{result.stderr[:300]}",
                file=sys.stderr,
            )
    except Exception as e:
        print(f"  WARNING: ato create part error: {e}", file=sys.stderr)
    return None


# ── Main ────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Generate .ato module from STM32 open pin data XML"
    )
    parser.add_argument("xml_path", type=Path, help="Path to STM32 MCU XML file")
    parser.add_argument(
        "--lcsc", type=str, default=None, help="LCSC part ID (e.g. C8734)"
    )
    parser.add_argument(
        "--mfr-search",
        type=str,
        default=None,
        help="Manufacturer search (e.g. STMicroelectronics:STM32F103C8T6)",
    )
    parser.add_argument("--output", "-o", type=Path, default=None)
    parser.add_argument("--project-dir", "-p", type=Path, default=Path("."))
    parser.add_argument("--skip-part-install", action="store_true")
    parser.add_argument(
        "--part-dir",
        type=Path,
        default=None,
        help="Path to existing installed part directory (skips install)",
    )
    args = parser.parse_args()

    print(f"Parsing {args.xml_path.name}...")
    mcu = parse_mcu_xml(args.xml_path)
    print(f"  MCU: {mcu.ref_name} ({mcu.core}, {mcu.frequency}MHz, {mcu.package_type})")
    print(f"  Flash: {mcu.flash} KB, RAM: {mcu.ram} KB")
    print(f"  Voltage: {mcu.voltage_min}V - {mcu.voltage_max}V")

    module_name = make_module_name(mcu.ref_name)

    # Install part or find existing
    part: InstalledPart | None = None

    if args.part_dir:
        part = parse_part_ato(args.part_dir)
    elif not args.skip_part_install:
        search = args.lcsc or args.mfr_search
        if search:
            print(f"\n  Installing part ({search})...")
            import_name = install_part(args.project_dir, search)
            if import_name:
                part_dir = args.project_dir / "parts" / import_name
                part = parse_part_ato(part_dir)
                if part:
                    print(
                        f"  Installed: {part.import_name} ({len(part.signals)} signals)"
                    )

    if not part:
        # Try to find any matching part directory
        parts_dir = args.project_dir / "parts"
        if parts_dir.exists():
            for d in parts_dir.iterdir():
                if d.is_dir() and "STM32" in d.name:
                    # Match against the MCU ref_name
                    cleaned = re.sub(
                        r"\(([^)]*)\)", lambda m: m.group(1).split("-")[0], mcu.ref_name
                    )
                    cleaned = (
                        cleaned.rstrip("x") + "6" if cleaned.endswith("x") else cleaned
                    )
                    if (
                        cleaned.replace("-", "").replace("(", "").replace(")", "")
                        in d.name
                    ):
                        part = parse_part_ato(d)
                        if part:
                            print(f"  Found existing part: {part.import_name}")
                            break

    if not part:
        print(
            (
                "  ERROR: No installed part found. "
                "Run with --lcsc or --mfr-search to install."
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    # Analyze
    print("\n  Analyzing interfaces...")
    interfaces = discover_interfaces(mcu)
    for iface in interfaces:
        pins_str = ", ".join(
            f"{r}=P{p[0]}{p[1]}" for r, p in sorted(iface.pin_map.items())
        )
        print(f"    {iface.iface_type:5s} {iface.instance_name:10s} -> {pins_str}")

    print("\n  Analyzing power domains...")
    power_domains = analyze_power_from_part(part, mcu)
    for domain in power_domains:
        print(f"    {domain.name}: HV={domain.hv_signals}, LV={domain.lv_signals}")

    print("\n  Analyzing GPIO ports...")
    gpio_ports = analyze_gpio_ports(mcu)
    for letter, port in gpio_ports.items():
        print(f"    Port {letter}: {len(port.pins)} pins (array[{port.array_size}])")

    print("\n  Detecting crystals...")
    crystals = detect_crystals(mcu, part)
    for c in crystals:
        print(f"    {c.name}: xin={c.xin_signal}, xout={c.xout_signal}")

    # Generate
    print("\n  Generating .ato code...")
    ato_code = generate_ato(mcu, part, interfaces, power_domains, gpio_ports, crystals)

    output_path = args.output or (
        args.project_dir / f"{module_name.lower().replace('st_', '')}.ato"
    )
    output_path.write_text(ato_code)
    print(f"\n  Wrote {len(ato_code)} bytes to {output_path}")
    print(f"  Module: {module_name}")


if __name__ == "__main__":
    main()
