from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol

ComponentType = Literal[
    "resistor",
    "capacitor",
    "capacitor_polarized",
    "inductor",
    "diode",
    "led",
    "bjt",
    "mosfet",
    "crystal",
    "ferrite_bead",
    "ldo",
]

RESISTOR_SUBCATEGORIES: tuple[str, ...] = (
    "Current Sense Resistors / Shunt Resistors",
    "Current Sense Resistors/Shunt Resistors",
    "Through Hole Resistors",
    "Chip Resistor - Surface Mount",
    "Low Resistors & Current Sense Resistors - Surface Mount",
    "Low Resistors & Current Sense Resistors (TH)",
)

CAPACITOR_SUBCATEGORIES: tuple[str, ...] = (
    "Film Capacitors",
    "Multilayer Ceramic Capacitors MLCC - Leaded",
    "Through Hole Ceramic Capacitors",
    "Multilayer Ceramic Capacitors MLCC - SMD/SMT",
    "Ceramic Disc Capacitors",
    "Polypropylene Film Capacitors (CBB)",
    "Suppression Capacitors",
    "Safety Capacitors",
    "Mica And PTFE Capacitors",
    "Silicon Capacitors",
    "Paper Dielectric Capacitors",
    "CBB Capacitors(polypropylene film)",
    "CBB Capacitors(Polypropylene Film)",
    "Mylar Capacitor",
)

CAPACITOR_POLARIZED_SUBCATEGORIES: tuple[str, ...] = (
    "Aluminum Electrolytic Capacitors - Leaded",
    "Polymer Aluminum Capacitors",
    "Aluminum Electrolytic Capacitors - SMD",
    "Horn-Type Electrolytic Capacitors",
    "horn-type electrolytic capacitor",
    "Tantalum Capacitors",
    "Solid Capacitors",
    "Solid Polymer Electrolytic Capacitor",
    "Niobium Oxide Capacitors",
    "Hybrid Aluminum Electrolytic Capacitors",
    "Aluminum Electrolytic Capacitors (Can - Screw Terminals)",
)

_INDUCTOR_CATEGORY_SUBCATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Inductors & Chokes & Transformers",
        (
            "General Inductors (TH)",
            "HF Inductors",
            "Inductors (SMD)",
            "Power Inductors",
        ),
    ),
    (
        "Inductors, Coils, Chokes",
        (
            "Color Ring Inductors / Through Hole Inductors",
            "Color Ring Inductors/Through Hole Inductors",
            "Inductors (SMD)",
            "Power Inductors",
            "Through Hole Inductors",
            "Adjustable Inductors",
            "HF Inductors",
        ),
    ),
    (
        "Inductors/Coils/Transformers",
        (
            "Color Ring Inductors/Through Hole Inductors",
            "HF Inductors",
            "Inductors (SMD)",
            "Power Inductors",
            "Through Hole Inductors",
            "Adjustable Inductors",
            "Color Ring Inductors / Through Hole Inductors",
        ),
    ),
    ("inductors/coils/transformers", ("Inductors (SMD)",)),
)

DIODE_SUBCATEGORIES: tuple[str, ...] = (
    "Diodes - General Purpose",
    "Schottky Barrier Diodes (SBD)",
    "Schottky Diodes",
    "Switching Diode",
    "Switching Diodes",
    "Diodes - Fast Recovery Rectifiers",
    "Fast Recovery / High Efficiency Diodes",
    "Fast Recovery/High Efficiency Diode",
    "High Effic Rectifier",
    "Bridge Rectifiers",
    "Super Barrier Rectifier (SBR)",
    "Super Barrier Rectifiers (SBR)",
    "Super Barrier Rectifier（SBR）",
    "Diodes - Rectifiers - Fast Recovery",
    "Diodes Rectifiers Fast Recovery",
)

LED_SUBCATEGORIES: tuple[str, ...] = (
    "Light Emitting Diodes (LED)",
    "LED Indication - Discrete",
    "Infrared (IR) LEDs",
    "Infrared LED Emitters",
    "Ultra Violet LEDs",
    "Ultraviolet LEDs (UVLED)",
    "RGB LEDs",
    "RGB LEDs(Built-In IC)",
)

LED_CATEGORIES: tuple[str, ...] = (
    "Photoelectric Devices",
    "Optoelectronics",
    "Optocoupler/LED/Digital Tube/Photoelectric Device",
    "Optocouplers & LEDs & Infrared",
    "LED/Photoelectric Devices",
    "optoelectronics",
)

TRANSISTOR_CATEGORIES: tuple[str, ...] = (
    "Triode/MOS Tube/Transistor",
    "Transistors",
    "Transistors/Thyristors",
)

BJT_SUBCATEGORIES: tuple[str, ...] = (
    "Bipolar Transistors - BJT",
    "Bipolar (BJT)",
    "Transistors (NPN/PNP)",
)

MOSFET_SUBCATEGORIES: tuple[str, ...] = (
    "MOSFETs",
    "MOSFET",
    "SiC MOSFETs",
    "Silicon Carbide Field Effect Transistor (MOSFET)",
)

CRYSTAL_CATEGORIES: tuple[str, ...] = (
    "Crystals/Oscillators/Resonators",
    "Crystal Oscillator/Oscillator/Resonator",
    "Crystals, Oscillators, Resonators",
    "Resonators/Oscillators",
    "crystals/oscillators/resonators",
    "Crystals",
)

CRYSTAL_SUBCATEGORIES: tuple[str, ...] = ("Crystals",)

FERRITE_BEAD_CATEGORIES: tuple[str, ...] = (
    "Filters/EMI Optimization",
    "Bead/Filter/EMI Optimization",
    "Filters",
    "Inductors & Chokes & Transformers",
)

FERRITE_BEAD_SUBCATEGORIES: tuple[str, ...] = ("Ferrite Beads",)

LDO_CATEGORIES: tuple[str, ...] = (
    "Power Management ICs",
    "Power Supply Chip",
    "Power Management (PMIC)",
    "Power Management",
)

LDO_SUBCATEGORIES: tuple[str, ...] = (
    "Linear Voltage Regulators (LDO)",
    "Voltage Regulators - Linear, Low Drop Out (LDO) Regulators",
    "Dropout Regulators(LDO)",
    "Low Dropout Regulators(LDO)",
)

_SI_PREFIX: dict[str, float] = {
    "y": 1e-24,
    "z": 1e-21,
    "a": 1e-18,
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "": 1.0,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}

_SI_VALUE_RE = re.compile(
    r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
    r"([yzafpnumkMGT]?)"
)
_SI_FRACTION_RE = re.compile(
    r"^([+-]?\d+(?:\.\d+)?)/([+-]?\d+(?:\.\d+)?)\s*([yzafpnumkMGT]?)"
)
_TOLERANCE_SINGLE_RE = re.compile(r"^[±]?\s*([+-]?\d+(?:\.\d+)?)\s*%$")
_TOLERANCE_RANGE_RE = re.compile(
    r"^([+-]?\d+(?:\.\d+)?)\s*%\s*~\s*([+-]?\d+(?:\.\d+)?)\s*%$"
)
_TOLERANCE_SPLIT_RE = re.compile(
    r"^\+?\s*(\d+(?:\.\d+)?)\s*/\s*-?\s*(\d+(?:\.\d+)?)\s*%?$"
)
_TEMPCO_RE = re.compile(r"[±+\-]?\s*(\d+(?:\.\d+)?)\s*ppm", re.IGNORECASE)


@dataclass(frozen=True)
class SourceComponent:
    lcsc_id: int
    component_type: ComponentType
    category: str
    subcategory: str
    manufacturer_name: str | None
    part_number: str
    package: str
    description: str
    is_basic: bool
    is_preferred: bool
    stock: int
    datasheet_url: str | None
    price_json: str
    extra_json: str | None
    resistance_raw: str | None
    tolerance_raw: str | None
    power_raw: str | None
    resistor_voltage_raw: str | None
    tempco_raw: str | None
    capacitance_raw: str | None
    capacitor_voltage_raw: str | None
    data_manual_url: str | None
    model_3d_path: str | None
    easyeda_model_uuid: str | None
    footprint_name: str | None


@dataclass(frozen=True)
class NormalizedComponent:
    lcsc_id: int
    component_type: ComponentType
    category: str
    subcategory: str
    manufacturer_name: str | None
    part_number: str
    package: str
    description: str
    is_basic: bool
    is_preferred: bool
    stock: int
    datasheet_url: str | None
    price_json: str
    attributes_json: str
    extra_json: str | None
    resistance_ohm: float | None
    resistance_min_ohm: float | None
    resistance_max_ohm: float | None
    capacitance_f: float | None
    capacitance_min_f: float | None
    capacitance_max_f: float | None
    tolerance_pct: float | None
    max_power_w: float | None
    max_voltage_v: float | None
    resistor_tempco_ppm: float | None
    capacitor_tempco_code: str | None
    data_manual_url: str | None
    model_3d_path: str | None
    easyeda_model_uuid: str | None
    footprint_name: str | None
    inductance_h: float | None = None
    inductance_min_h: float | None = None
    inductance_max_h: float | None = None
    max_current_a: float | None = None
    dc_resistance_ohm: float | None = None
    saturation_current_a: float | None = None
    self_resonant_frequency_hz: float | None = None
    forward_voltage_v: float | None = None
    reverse_working_voltage_v: float | None = None
    reverse_leakage_current_a: float | None = None
    led_color_code: str | None = None
    max_brightness_cd: float | None = None
    bjt_doping_type: str | None = None
    max_collector_emitter_voltage_v: float | None = None
    max_collector_current_a: float | None = None
    dc_current_gain_hfe: float | None = None
    mosfet_channel_type: str | None = None
    gate_source_threshold_voltage_v: float | None = None
    max_drain_source_voltage_v: float | None = None
    max_continuous_drain_current_a: float | None = None
    on_resistance_ohm: float | None = None
    frequency_hz: float | None = None
    frequency_min_hz: float | None = None
    frequency_max_hz: float | None = None
    load_capacitance_f: float | None = None
    frequency_tolerance_ppm: float | None = None
    frequency_stability_ppm: float | None = None
    ferrite_impedance_ohm: float | None = None
    ferrite_current_rating_a: float | None = None
    ldo_output_voltage_v: float | None = None
    ldo_max_input_voltage_v: float | None = None
    ldo_output_current_a: float | None = None
    ldo_dropout_voltage_v: float | None = None
    ldo_output_type: str | None = None
    ldo_output_polarity: str | None = None


class ComponentSink(Protocol):
    inserted_count: int

    def add_component(self, component: NormalizedComponent) -> None: ...

    def finalize(self) -> None: ...


def category_to_component_type(category: str, subcategory: str) -> ComponentType | None:
    category_norm = category.strip().casefold()
    subcategory_norm = subcategory.strip().casefold()
    if category_norm == "resistors" and subcategory_norm in {
        value.casefold() for value in RESISTOR_SUBCATEGORIES
    }:
        return "resistor"
    if category_norm == "capacitors" and subcategory_norm in {
        value.casefold() for value in CAPACITOR_POLARIZED_SUBCATEGORIES
    }:
        return "capacitor_polarized"
    if category_norm == "capacitors" and subcategory_norm in {
        value.casefold() for value in CAPACITOR_SUBCATEGORIES
    }:
        return "capacitor"
    for inductor_category, inductor_subcategories in _INDUCTOR_CATEGORY_SUBCATEGORIES:
        if category_norm == inductor_category.casefold() and subcategory_norm in {
            value.casefold() for value in inductor_subcategories
        }:
            return "inductor"
    if category_norm == "diodes" and subcategory_norm in {
        value.casefold() for value in DIODE_SUBCATEGORIES
    }:
        return "diode"
    if category_norm in {
        value.casefold() for value in LED_CATEGORIES
    } and subcategory_norm in {value.casefold() for value in LED_SUBCATEGORIES}:
        return "led"
    if category_norm in {
        value.casefold() for value in TRANSISTOR_CATEGORIES
    } and subcategory_norm in {value.casefold() for value in BJT_SUBCATEGORIES}:
        return "bjt"
    if category_norm in {
        value.casefold() for value in TRANSISTOR_CATEGORIES
    } and subcategory_norm in {value.casefold() for value in MOSFET_SUBCATEGORIES}:
        return "mosfet"
    if category_norm in {
        value.casefold() for value in CRYSTAL_CATEGORIES
    } and subcategory_norm in {value.casefold() for value in CRYSTAL_SUBCATEGORIES}:
        return "crystal"
    if category_norm in {
        value.casefold() for value in FERRITE_BEAD_CATEGORIES
    } and subcategory_norm in {
        value.casefold() for value in FERRITE_BEAD_SUBCATEGORIES
    }:
        return "ferrite_bead"
    if category_norm in {
        value.casefold() for value in LDO_CATEGORIES
    } and subcategory_norm in {value.casefold() for value in LDO_SUBCATEGORIES}:
        return "ldo"
    return None


def normalize_component(component: SourceComponent) -> NormalizedComponent:
    attributes = _extract_attributes(component.extra_json)
    attributes_folded = {key.casefold(): value for key, value in attributes.items()}

    def _attr(*keys: str) -> str | None:
        for key in keys:
            value = attributes_folded.get(key.casefold())
            if value:
                return value
        return None

    tolerance_raw = component.tolerance_raw or _attr("Tolerance")
    tolerance_pct = parse_tolerance_percent(tolerance_raw)

    resistance_ohm: float | None = None
    resistance_min_ohm: float | None = None
    resistance_max_ohm: float | None = None
    capacitance_f: float | None = None
    capacitance_min_f: float | None = None
    capacitance_max_f: float | None = None
    max_power_w: float | None = None
    max_voltage_v: float | None = None
    resistor_tempco_ppm: float | None = None
    capacitor_tempco_code: str | None = None
    inductance_h: float | None = None
    inductance_min_h: float | None = None
    inductance_max_h: float | None = None
    max_current_a: float | None = None
    dc_resistance_ohm: float | None = None
    saturation_current_a: float | None = None
    self_resonant_frequency_hz: float | None = None
    forward_voltage_v: float | None = None
    reverse_working_voltage_v: float | None = None
    reverse_leakage_current_a: float | None = None
    led_color_code: str | None = None
    max_brightness_cd: float | None = None
    bjt_doping_type: str | None = None
    max_collector_emitter_voltage_v: float | None = None
    max_collector_current_a: float | None = None
    dc_current_gain_hfe: float | None = None
    mosfet_channel_type: str | None = None
    gate_source_threshold_voltage_v: float | None = None
    max_drain_source_voltage_v: float | None = None
    max_continuous_drain_current_a: float | None = None
    on_resistance_ohm: float | None = None
    frequency_hz: float | None = None
    frequency_min_hz: float | None = None
    frequency_max_hz: float | None = None
    load_capacitance_f: float | None = None
    frequency_tolerance_ppm: float | None = None
    frequency_stability_ppm: float | None = None
    ferrite_impedance_ohm: float | None = None
    ferrite_current_rating_a: float | None = None
    ldo_output_voltage_v: float | None = None
    ldo_max_input_voltage_v: float | None = None
    ldo_output_current_a: float | None = None
    ldo_dropout_voltage_v: float | None = None
    ldo_output_type: str | None = None
    ldo_output_polarity: str | None = None

    if component.component_type == "resistor":
        resistance_ohm = parse_si_value(component.resistance_raw or _attr("Resistance"))
        resistance_min_ohm, resistance_max_ohm = tolerance_bounds(
            nominal=resistance_ohm,
            tolerance_pct=tolerance_pct,
        )
        max_power_w = parse_si_value(
            component.power_raw or _attr("Power(Watts)", "Power")
        )
        max_voltage_v = parse_si_value(
            component.resistor_voltage_raw
            or _attr(
                "Overload Voltage (Max)",
                "Rated Voltage",
                "Voltage Rating",
                "Voltage Rated",
            )
        )
        resistor_tempco_ppm = parse_tempco_ppm(
            component.tempco_raw or _attr("Temperature Coefficient")
        )
    elif component.component_type in {"capacitor", "capacitor_polarized"}:
        capacitance_f = parse_si_value(
            component.capacitance_raw or _attr("Capacitance")
        )
        capacitance_min_f, capacitance_max_f = tolerance_bounds(
            nominal=capacitance_f,
            tolerance_pct=tolerance_pct,
        )
        max_voltage_v = parse_si_value(
            component.capacitor_voltage_raw
            or _attr("Voltage Rated", "Rated Voltage", "Voltage Rating")
        )
        capacitor_tempco_code = normalize_tempco_code(
            component.tempco_raw or _attr("Temperature Coefficient")
        )
    elif component.component_type == "inductor":
        inductance_h = parse_si_value(_attr("Inductance"))
        inductance_min_h, inductance_max_h = tolerance_bounds(
            nominal=inductance_h,
            tolerance_pct=tolerance_pct,
        )
        max_current_a = parse_si_value(_attr("Rated Current", "Current Rating"))
        dc_resistance_ohm = parse_si_value(
            _attr("DC Resistance (DCR)", "DC Resistance", "DC Resistance(DCR)")
        )
        saturation_current_a = parse_si_value(
            _attr("Current - Saturation (Isat)", "Saturation Current (Isat)")
        )
        self_resonant_frequency_hz = parse_si_value(
            _attr("Frequency - Self Resonant", "Self Resonant Frequency")
        )
    elif component.component_type == "diode":
        forward_voltage_v = parse_si_value(
            _attr(
                "Forward Voltage",
                "Forward Voltage (Vf@If)",
                "Voltage - Forward(Vf@If)",
                "Forward Voltage (Vf) @ If",
            )
        )
        reverse_working_voltage_v = parse_si_value(
            _attr(
                "Reverse Voltage (Vr)",
                "Voltage - DC Reverse(Vr)",
                "Reverse Voltage",
                "Reverse Stand-Off Voltage (Vrwm)",
            )
        )
        max_current_a = parse_si_value(
            _attr(
                "Average Rectified Current (Io)",
                "Rectified Current",
                "Current - Rectified",
                "Forward Current",
            )
        )
        reverse_leakage_current_a = parse_si_value(
            _attr(
                "Reverse Leakage Current (Ir)",
                "Reverse Leakage Current",
                "Ir - Reverse Current",
            )
        )
    elif component.component_type == "led":
        led_color_code = normalize_led_color(
            _attr("Emitted Color", "Color", "Emitting Color")
        )
        forward_voltage_v = parse_si_value(
            _attr(
                "Forward Voltage",
                "Forward Voltage (VF)",
                "Forward Voltage (Vf@If)",
            )
        )
        max_current_a = parse_si_value(_attr("Forward Current", "Current - Forward"))
        max_brightness_cd = parse_si_value(
            _attr("Luminous Intensity", "Radiant Intensity")
        )
    elif component.component_type == "bjt":
        bjt_doping_type = normalize_bjt_doping_type(
            _attr("Transistor Type", "Transistor type", "Type", "type")
        )
        max_collector_emitter_voltage_v = parse_si_value(
            _attr(
                "Collector-Emitter Breakdown Voltage (Vceo)",
                "Collector Emitter Voltage (Vceo)",
                "Voltage - Collector Emitter Breakdown (Max)",
            )
        )
        max_collector_current_a = parse_si_value(
            _attr(
                "Collector Current (Ic)",
                "Current - Collector(Ic)",
                "Collector Current",
            )
        )
        max_power_w = parse_si_value(
            _attr(
                "Power Dissipation (Pd)",
                "Pd - Power Dissipation",
                "Power Dissipation",
            )
        )
        dc_current_gain_hfe = parse_si_value(
            _attr(
                "DC Current Gain (hFE@Ic,Vce)",
                "DC Current Gain (hFE)",
                "DC Current Gain",
                "hFE",
            )
        )
    elif component.component_type == "mosfet":
        mosfet_channel_type = normalize_mosfet_channel_type(
            _attr("Type", "Channel Type")
        )
        gate_source_threshold_voltage_v = parse_si_value(
            _attr(
                "Gate Threshold Voltage (Vgs(th)@Id)",
                "Gate Threshold Voltage (Vgs(th))",
                "Vgs(th)",
            )
        )
        max_drain_source_voltage_v = parse_si_value(
            _attr("Drain Source Voltage (Vdss)", "Vdss")
        )
        max_continuous_drain_current_a = parse_si_value(
            _attr(
                "Continuous Drain Current (Id)",
                "Drain Current (Id)",
                "Current - Continuous Drain (Id)",
            )
        )
        on_resistance_ohm = parse_si_value(
            _attr(
                "Drain Source On Resistance (RDS(on)@Vgs,Id)",
                "Drain Source On Resistance (Rds(on))",
                "RDS(on)",
            )
        )
    elif component.component_type == "crystal":
        frequency_hz = parse_si_value(_attr("Frequency"))
        frequency_tolerance_ppm = parse_tempco_ppm(
            _attr(
                "Normal temperature Frequency Tolerance",
                "Frequency Tolerance",
            )
        )
        frequency_stability_ppm = parse_tempco_ppm(
            _attr(
                "Frequency Stability",
                "Frequency Stability(Full temperature range)",
            )
        )
        frequency_min_hz, frequency_max_hz = tolerance_bounds_ppm(
            nominal=frequency_hz,
            tolerance_ppm=frequency_tolerance_ppm,
        )
        load_capacitance_f = parse_si_value(
            _attr(
                "Load Capacitance",
                "Load Capacitor",
                "External load capacitor",
            )
        )
    elif component.component_type == "ferrite_bead":
        ferrite_impedance_ohm = parse_si_value(_attr("Impedance @ Frequency"))
        ferrite_current_rating_a = parse_si_value(
            _attr("Current Rating", "Rated Current")
        )
        dc_resistance_ohm = parse_si_value(
            _attr("DC Resistance", "DC Resistance(DCR)", "DC Resistance (DCR)")
        )
    elif component.component_type == "ldo":
        ldo_output_voltage_v = parse_si_value(_attr("Output Voltage"))
        ldo_max_input_voltage_v = parse_si_value(
            _attr("Maximum Input Voltage", "Input Voltage", "Voltage - Supply")
        )
        ldo_output_current_a = parse_si_value(
            _attr("Output Current", "MAX Output Current")
        )
        ldo_dropout_voltage_v = parse_si_value(
            _attr("Dropout Voltage", "Voltage Dropout")
        )
        ldo_output_type = normalize_ldo_output_type(_attr("Output Type"))
        ldo_output_polarity = normalize_ldo_output_polarity(_attr("Output Polarity"))

    return NormalizedComponent(
        lcsc_id=component.lcsc_id,
        component_type=component.component_type,
        category=component.category,
        subcategory=component.subcategory,
        manufacturer_name=component.manufacturer_name,
        part_number=component.part_number,
        package=component.package,
        description=component.description,
        is_basic=component.is_basic,
        is_preferred=component.is_preferred,
        stock=component.stock,
        datasheet_url=component.datasheet_url,
        price_json=component.price_json,
        attributes_json=json.dumps(
            attributes,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        extra_json=component.extra_json,
        resistance_ohm=resistance_ohm,
        resistance_min_ohm=resistance_min_ohm,
        resistance_max_ohm=resistance_max_ohm,
        capacitance_f=capacitance_f,
        capacitance_min_f=capacitance_min_f,
        capacitance_max_f=capacitance_max_f,
        tolerance_pct=tolerance_pct,
        max_power_w=max_power_w,
        max_voltage_v=max_voltage_v,
        resistor_tempco_ppm=resistor_tempco_ppm,
        capacitor_tempco_code=capacitor_tempco_code,
        data_manual_url=component.data_manual_url,
        model_3d_path=component.model_3d_path,
        easyeda_model_uuid=component.easyeda_model_uuid,
        footprint_name=component.footprint_name,
        inductance_h=inductance_h,
        inductance_min_h=inductance_min_h,
        inductance_max_h=inductance_max_h,
        max_current_a=max_current_a,
        dc_resistance_ohm=dc_resistance_ohm,
        saturation_current_a=saturation_current_a,
        self_resonant_frequency_hz=self_resonant_frequency_hz,
        forward_voltage_v=forward_voltage_v,
        reverse_working_voltage_v=reverse_working_voltage_v,
        reverse_leakage_current_a=reverse_leakage_current_a,
        led_color_code=led_color_code,
        max_brightness_cd=max_brightness_cd,
        bjt_doping_type=bjt_doping_type,
        max_collector_emitter_voltage_v=max_collector_emitter_voltage_v,
        max_collector_current_a=max_collector_current_a,
        dc_current_gain_hfe=dc_current_gain_hfe,
        mosfet_channel_type=mosfet_channel_type,
        gate_source_threshold_voltage_v=gate_source_threshold_voltage_v,
        max_drain_source_voltage_v=max_drain_source_voltage_v,
        max_continuous_drain_current_a=max_continuous_drain_current_a,
        on_resistance_ohm=on_resistance_ohm,
        frequency_hz=frequency_hz,
        frequency_min_hz=frequency_min_hz,
        frequency_max_hz=frequency_max_hz,
        load_capacitance_f=load_capacitance_f,
        frequency_tolerance_ppm=frequency_tolerance_ppm,
        frequency_stability_ppm=frequency_stability_ppm,
        ferrite_impedance_ohm=ferrite_impedance_ohm,
        ferrite_current_rating_a=ferrite_current_rating_a,
        ldo_output_voltage_v=ldo_output_voltage_v,
        ldo_max_input_voltage_v=ldo_max_input_voltage_v,
        ldo_output_current_a=ldo_output_current_a,
        ldo_dropout_voltage_v=ldo_dropout_voltage_v,
        ldo_output_type=ldo_output_type,
        ldo_output_polarity=ldo_output_polarity,
    )


def parse_si_value(raw: str | None) -> float | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped in {"-", "null"}:
        return None

    parts = _split_multi_value_tokens(stripped)
    parsed_values: list[float] = []
    for part in parts:
        candidate = part.split("@", 1)[0]
        normalized = (
            candidate.strip()
            .replace(" ", "")
            .replace(",", "")
            .replace("μ", "u")
            .replace("µ", "u")
            .replace("Ω", "")
            .replace("Ω", "")
        )
        if not normalized:
            continue
        fraction_match = _SI_FRACTION_RE.match(normalized)
        if fraction_match:
            numerator = float(fraction_match.group(1))
            denominator = float(fraction_match.group(2))
            if denominator != 0:
                prefix = fraction_match.group(3)
                multiplier = _SI_PREFIX.get(prefix, 1.0)
                parsed_values.append((numerator / denominator) * multiplier)
                continue
        match = _SI_VALUE_RE.search(normalized)
        if not match:
            continue
        magnitude = float(match.group(1))
        prefix = match.group(2)
        multiplier = _SI_PREFIX.get(prefix)
        if multiplier is None:
            continue
        parsed_values.append(magnitude * multiplier)
    if not parsed_values:
        return None
    return min(parsed_values)


def parse_tolerance_percent(raw: str | None) -> float | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped == "-":
        return None
    match_single = _TOLERANCE_SINGLE_RE.match(stripped)
    if match_single:
        return abs(float(match_single.group(1)))
    match_range = _TOLERANCE_RANGE_RE.match(stripped)
    if match_range:
        left = float(match_range.group(1))
        right = float(match_range.group(2))
        return max(abs(left), abs(right))
    match_split = _TOLERANCE_SPLIT_RE.match(stripped)
    if match_split:
        pos = float(match_split.group(1))
        neg = float(match_split.group(2))
        return max(abs(pos), abs(neg))
    if stripped.endswith("%"):
        try:
            return abs(float(stripped[:-1]))
        except ValueError:
            return None
    return None


def parse_tempco_ppm(raw: str | None) -> float | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped == "-":
        return None
    match = _TEMPCO_RE.search(stripped)
    if not match:
        return None
    return abs(float(match.group(1)))


def normalize_tempco_code(raw: str | None) -> str | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped in {"-", "null"}:
        return None
    first_token = re.split(r"[;,\s]+", stripped)[0].upper()
    if first_token == "NP0":
        return "C0G"
    return first_token


def tolerance_bounds(
    *,
    nominal: float | None,
    tolerance_pct: float | None,
) -> tuple[float | None, float | None]:
    if nominal is None:
        return None, None
    if tolerance_pct is None:
        return nominal, nominal
    fraction = tolerance_pct / 100.0
    return nominal * (1.0 - fraction), nominal * (1.0 + fraction)


def tolerance_bounds_ppm(
    *,
    nominal: float | None,
    tolerance_ppm: float | None,
) -> tuple[float | None, float | None]:
    if nominal is None:
        return None, None
    if tolerance_ppm is None:
        return nominal, nominal
    fraction = tolerance_ppm / 1_000_000.0
    return nominal * (1.0 - fraction), nominal * (1.0 + fraction)


def _split_multi_value_tokens(raw: str) -> list[str]:
    parts = re.split(r"[;~|]", raw)
    if len(parts) == 1:
        return [raw]
    return [part for part in parts if part.strip()]


def _extract_attributes(extra_json: str | None) -> dict[str, str]:
    if not extra_json:
        return {}
    try:
        parsed = json.loads(extra_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    attrs = parsed.get("attributes")
    if not isinstance(attrs, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in attrs.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, (str, int, float)):
            result[key] = str(value)
    return result


def normalize_led_color(raw: str | None) -> str | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped in {"-", "null"}:
        return None
    compact = re.sub(r"[^a-z0-9]+", "", stripped.lower())
    if compact in {"rgb", "multicolor", "colorful"}:
        return None
    if "warmwhite" in compact:
        return "WARM_WHITE"
    if "coldwhite" in compact:
        return "COLD_WHITE"
    if "naturalwhite" in compact or "neutralwhite" in compact:
        return "NATURAL_WHITE"
    if "infrared" in compact or compact in {"ir"}:
        return "INFRA_RED"
    if "ultraviolet" in compact or compact in {"uv"}:
        return "ULTRA_VIOLET"
    if "emerald" in compact:
        return "EMERALD"
    if "amber" in compact:
        return "AMBER"
    if "magenta" in compact:
        return "MAGENTA"
    if "violet" in compact:
        return "VIOLET"
    if "lime" in compact:
        return "LIME"
    if "cyan" in compact:
        return "CYAN"
    if "purple" in compact:
        return "PURPLE"
    if "orange" in compact:
        return "ORANGE"
    if "yellow" in compact:
        return "YELLOW"
    if "green" in compact:
        return "GREEN"
    if "blue" in compact:
        return "BLUE"
    if "red" in compact:
        return "RED"
    if "white" in compact:
        return "WHITE"
    if "pink" in compact:
        return "PINK"
    return None


def normalize_bjt_doping_type(raw: str | None) -> str | None:
    if raw is None:
        return None
    normalized = raw.strip().upper()
    if not normalized:
        return None
    has_npn = "NPN" in normalized
    has_pnp = "PNP" in normalized
    if has_npn and has_pnp:
        return None
    if has_npn:
        return "NPN"
    if has_pnp:
        return "PNP"
    return None


def normalize_mosfet_channel_type(raw: str | None) -> str | None:
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if not normalized:
        return None
    compact = re.sub(r"[^a-z0-9+&]", "", normalized)
    has_n = (
        "nchannel" in compact
        or compact in {"n", "nmos"}
        or "n-channel" in normalized
        or "n channel" in normalized
    )
    has_p = (
        "pchannel" in compact
        or compact in {"p", "pmos"}
        or "p-channel" in normalized
        or "p channel" in normalized
    )
    if has_n and has_p:
        return None
    if has_n:
        return "N_CHANNEL"
    if has_p:
        return "P_CHANNEL"
    return None


def normalize_ldo_output_type(raw: str | None) -> str | None:
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if not normalized or normalized in {"-", "null"}:
        return None
    compact = re.sub(r"[^a-z0-9]+", "", normalized)
    if "adjustable" in compact:
        return "ADJUSTABLE"
    if "fixed" in compact:
        return "FIXED"
    return None


def normalize_ldo_output_polarity(raw: str | None) -> str | None:
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if not normalized or normalized in {"-", "null"}:
        return None
    compact = re.sub(r"[^a-z0-9]+", "", normalized)
    has_positive = "positive" in compact
    has_negative = "negative" in compact
    if has_positive and has_negative:
        return "BIPOLAR"
    if has_positive:
        return "POSITIVE"
    if has_negative:
        return "NEGATIVE"
    return None


def normalize_components(
    source_components: Iterable[SourceComponent],
) -> list[NormalizedComponent]:
    return [normalize_component(component) for component in source_components]


def test_parse_si_value() -> None:
    assert parse_si_value("10kΩ") == 10_000.0
    assert parse_si_value("62.5mW") == 0.0625
    assert parse_si_value("1.2kV;700V") == 700.0
    assert parse_si_value("1.5Ω@10V,500mA") == 1.5
    assert parse_si_value("1/16W") == 0.0625
    assert parse_si_value("-") is None
    assert parse_si_value(None) is None


def test_parse_tolerance_percent() -> None:
    assert parse_tolerance_percent("±5%") == 5.0
    assert parse_tolerance_percent("-20%~+80%") == 80.0
    assert parse_tolerance_percent("+80/-20%") == 80.0
    assert parse_tolerance_percent("-") is None


def test_tolerance_bounds() -> None:
    assert tolerance_bounds(nominal=100.0, tolerance_pct=5.0) == (95.0, 105.0)
    assert tolerance_bounds(nominal=100.0, tolerance_pct=None) == (100.0, 100.0)
    assert tolerance_bounds(nominal=None, tolerance_pct=5.0) == (None, None)
    minimum, maximum = tolerance_bounds_ppm(nominal=16e6, tolerance_ppm=20.0)
    assert abs((minimum or 0.0) - 15_999_680.0) < 1e-6
    assert abs((maximum or 0.0) - 16_000_320.0) < 1e-6


def test_normalize_tempco_and_category() -> None:
    assert normalize_tempco_code("NP0") == "C0G"
    assert normalize_tempco_code("x7r") == "X7R"
    assert normalize_tempco_code("-") is None
    assert (
        category_to_component_type("Resistors", "Chip Resistor - Surface Mount")
        == "resistor"
    )
    assert (
        category_to_component_type("Capacitors", "Tantalum Capacitors")
        == "capacitor_polarized"
    )
    assert (
        category_to_component_type(
            "Capacitors",
            "Aluminum Electrolytic Capacitors - SMD",
        )
        == "capacitor_polarized"
    )
    assert (
        category_to_component_type("Inductors/Coils/Transformers", "Power Inductors")
        == "inductor"
    )
    assert category_to_component_type("Diodes", "Switching Diode") == "diode"
    assert (
        category_to_component_type("Optoelectronics", "LED Indication - Discrete")
        == "led"
    )
    assert (
        category_to_component_type(
            "Triode/MOS Tube/Transistor",
            "Bipolar Transistors - BJT",
        )
        == "bjt"
    )
    assert category_to_component_type("Transistors/Thyristors", "MOSFETs") == "mosfet"
    assert (
        category_to_component_type(
            "Crystals/Oscillators/Resonators",
            "Crystals",
        )
        == "crystal"
    )
    assert (
        category_to_component_type(
            "Filters/EMI Optimization",
            "Ferrite Beads",
        )
        == "ferrite_bead"
    )
    assert (
        category_to_component_type(
            "Power Management ICs",
            "Linear Voltage Regulators (LDO)",
        )
        == "ldo"
    )
    assert category_to_component_type("Resistors", "Resistor Networks & Arrays") is None


def test_normalize_component_resistor() -> None:
    source = SourceComponent(
        lcsc_id=123,
        component_type="resistor",
        category="Resistors",
        subcategory="Chip Resistor - Surface Mount",
        manufacturer_name="MFR",
        part_number="PN",
        package="0402",
        description="desc",
        is_basic=True,
        is_preferred=False,
        stock=10,
        datasheet_url="https://example.com/ds.pdf",
        price_json="[]",
        extra_json='{"attributes":{"Resistance":"10kΩ"}}',
        resistance_raw="10kΩ",
        tolerance_raw="±1%",
        power_raw="62.5mW",
        resistor_voltage_raw="50V",
        tempco_raw="±100ppm/℃",
        capacitance_raw=None,
        capacitor_voltage_raw=None,
        data_manual_url=None,
        model_3d_path=None,
        easyeda_model_uuid=None,
        footprint_name=None,
    )
    normalized = normalize_component(source)
    assert normalized.resistance_ohm == 10_000.0
    assert normalized.resistance_min_ohm == 9_900.0
    assert normalized.resistance_max_ohm == 10_100.0
    assert normalized.tolerance_pct == 1.0
    assert normalized.max_power_w == 0.0625
    assert normalized.max_voltage_v == 50.0
    assert normalized.resistor_tempco_ppm == 100.0


def test_normalize_component_diode_and_channel_enums() -> None:
    source = SourceComponent(
        lcsc_id=777,
        component_type="diode",
        category="Diodes",
        subcategory="Switching Diode",
        manufacturer_name="MFR",
        part_number="D1",
        package="SOD-123",
        description="desc",
        is_basic=False,
        is_preferred=False,
        stock=10,
        datasheet_url=None,
        price_json="[]",
        extra_json=json.dumps(
            {
                "attributes": {
                    "Forward Voltage (Vf@If)": "1.25V@150mA",
                    "Reverse Voltage (Vr)": "100V",
                    "Average Rectified Current (Io)": "300mA",
                    "Reverse Leakage Current (Ir)": "2uA",
                }
            }
        ),
        resistance_raw=None,
        tolerance_raw=None,
        power_raw=None,
        resistor_voltage_raw=None,
        tempco_raw=None,
        capacitance_raw=None,
        capacitor_voltage_raw=None,
        data_manual_url=None,
        model_3d_path=None,
        easyeda_model_uuid=None,
        footprint_name=None,
    )
    normalized = normalize_component(source)
    assert normalized.forward_voltage_v == 1.25
    assert normalized.reverse_working_voltage_v == 100.0
    assert normalized.max_current_a == 0.3
    assert normalized.reverse_leakage_current_a == 2e-06

    assert normalize_bjt_doping_type("NPN") == "NPN"
    assert normalize_bjt_doping_type("PNP") == "PNP"
    assert normalize_bjt_doping_type("NPN/PNP") is None
    assert normalize_mosfet_channel_type("1 Piece N-Channel") == "N_CHANNEL"
    assert normalize_mosfet_channel_type("P channel") == "P_CHANNEL"
    assert normalize_mosfet_channel_type("N-Channel + P-Channel") is None
    assert normalize_led_color("Warm White") == "WARM_WHITE"
    assert normalize_led_color("Ultra Violet") == "ULTRA_VIOLET"


def test_normalize_component_crystal_ferrite_and_ldo() -> None:
    crystal = normalize_component(
        SourceComponent(
            lcsc_id=100,
            component_type="crystal",
            category="Crystals/Oscillators/Resonators",
            subcategory="Crystals",
            manufacturer_name="MFR",
            part_number="XTAL-16M",
            package="SMD-3225",
            description="desc",
            is_basic=False,
            is_preferred=False,
            stock=10,
            datasheet_url=None,
            price_json="[]",
            extra_json=json.dumps(
                {
                    "attributes": {
                        "Frequency": "16MHz",
                        "Normal temperature Frequency Tolerance": "±20ppm",
                        "Frequency Stability": "±30ppm",
                        "Load Capacitance": "18pF",
                    }
                }
            ),
            resistance_raw=None,
            tolerance_raw=None,
            power_raw=None,
            resistor_voltage_raw=None,
            tempco_raw=None,
            capacitance_raw=None,
            capacitor_voltage_raw=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
        )
    )
    assert crystal.frequency_hz == 16_000_000.0
    assert crystal.frequency_tolerance_ppm == 20.0
    assert crystal.frequency_stability_ppm == 30.0
    assert crystal.load_capacitance_f == 18e-12
    assert crystal.frequency_min_hz == 15_999_680.0
    assert abs((crystal.frequency_max_hz or 0.0) - 16_000_320.0) < 1e-6

    ferrite = normalize_component(
        SourceComponent(
            lcsc_id=101,
            component_type="ferrite_bead",
            category="Filters/EMI Optimization",
            subcategory="Ferrite Beads",
            manufacturer_name="MFR",
            part_number="FB-0603",
            package="0603",
            description="desc",
            is_basic=False,
            is_preferred=False,
            stock=10,
            datasheet_url=None,
            price_json="[]",
            extra_json=json.dumps(
                {
                    "attributes": {
                        "Impedance @ Frequency": "120Ω@100MHz",
                        "Current Rating": "2A",
                        "DC Resistance": "50mΩ",
                    }
                }
            ),
            resistance_raw=None,
            tolerance_raw=None,
            power_raw=None,
            resistor_voltage_raw=None,
            tempco_raw=None,
            capacitance_raw=None,
            capacitor_voltage_raw=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
        )
    )
    assert ferrite.ferrite_impedance_ohm == 120.0
    assert ferrite.ferrite_current_rating_a == 2.0
    assert ferrite.dc_resistance_ohm == 0.05

    ldo = normalize_component(
        SourceComponent(
            lcsc_id=102,
            component_type="ldo",
            category="Power Management ICs",
            subcategory="Linear Voltage Regulators (LDO)",
            manufacturer_name="MFR",
            part_number="LDO-3V3",
            package="SOT-23-5",
            description="desc",
            is_basic=False,
            is_preferred=False,
            stock=10,
            datasheet_url=None,
            price_json="[]",
            extra_json=json.dumps(
                {
                    "attributes": {
                        "Output Voltage": "3.3V",
                        "Maximum Input Voltage": "6V",
                        "Output Current": "150mA",
                        "Dropout Voltage": "300mV",
                        "Output Type": "Fixed",
                        "Output Polarity": "Positive electrode",
                    }
                }
            ),
            resistance_raw=None,
            tolerance_raw=None,
            power_raw=None,
            resistor_voltage_raw=None,
            tempco_raw=None,
            capacitance_raw=None,
            capacitor_voltage_raw=None,
            data_manual_url=None,
            model_3d_path=None,
            easyeda_model_uuid=None,
            footprint_name=None,
        )
    )
    assert ldo.ldo_output_voltage_v == 3.3
    assert ldo.ldo_max_input_voltage_v == 6.0
    assert ldo.ldo_output_current_a == 0.15
    assert ldo.ldo_dropout_voltage_v == 0.3
    assert ldo.ldo_output_type == "FIXED"
    assert ldo.ldo_output_polarity == "POSITIVE"
