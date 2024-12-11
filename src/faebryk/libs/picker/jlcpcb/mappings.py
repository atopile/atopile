import logging
from enum import Enum
from typing import Callable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.picker.jlcpcb.jlcpcb import (
    MappingParameterDB,
)
from faebryk.libs.util import (
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    closest_base_class,
    find,
)

logger = logging.getLogger(__name__)


def str_to_enum[T: Enum](enum: type[T], x: str) -> L.EnumSet[T]:
    name = x.replace(" ", "_").replace("-", "_").upper()
    if name not in [e.name for e in enum]:
        raise ValueError(f"Enum translation error: {x}[={name}] not in {enum}")
    return L.EnumSet(enum[name])


def str_to_enum_func[T: Enum](enum: type[T]) -> Callable[[str], L.EnumSet[T]]:
    def f(x: str) -> L.EnumSet[T]:
        return str_to_enum(enum, x)

    return f


_MAPPINGS_BY_TYPE: dict[type[Module], list[MappingParameterDB]] = {
    F.Resistor: [
        MappingParameterDB(
            "resistance",
            ["Resistance"],
            "Tolerance",
        ),
        MappingParameterDB(
            "max_power",
            ["Power(Watts)"],
        ),
        MappingParameterDB(
            "max_voltage",
            ["Overload Voltage (Max)"],
        ),
    ],
    F.Capacitor: [
        MappingParameterDB("capacitance", ["Capacitance"], "Tolerance"),
        MappingParameterDB(
            "max_voltage",
            ["Voltage Rated"],
        ),
        MappingParameterDB(
            "temperature_coefficient",
            ["Temperature Coefficient"],
            transform_fn=lambda x: str_to_enum(
                F.Capacitor.TemperatureCoefficient, x.replace("NP0", "C0G")
            ),
        ),
    ],
    F.Inductor: [
        MappingParameterDB(
            "inductance",
            ["Inductance"],
            "Tolerance",
        ),
        MappingParameterDB(
            "max_current",
            ["Rated Current"],
        ),
        MappingParameterDB(
            "dc_resistance",
            ["DC Resistance (DCR)", "DC Resistance"],
        ),
        MappingParameterDB(
            "self_resonant_frequency",
            ["Frequency - Self Resonant"],
        ),
    ],
    F.TVS: [
        MappingParameterDB(
            "forward_voltage",
            ["Breakdown Voltage"],
        ),
        # TODO: think about the difference of meaning for max_current between Diode
        # and TVS
        MappingParameterDB(
            "max_current",
            ["Peak Pulse Current (Ipp)@10/1000us"],
        ),
        MappingParameterDB(
            "reverse_working_voltage",
            ["Reverse Voltage (Vr)", "Reverse Stand-Off Voltage (Vrwm)"],
        ),
        MappingParameterDB(
            "reverse_leakage_current",
            ["Reverse Leakage Current", "Reverse Leakage Current (Ir)"],
        ),
        MappingParameterDB(
            "reverse_breakdown_voltage",
            ["Breakdown Voltage"],
        ),
    ],
    F.Diode: [
        MappingParameterDB(
            "forward_voltage",
            ["Forward Voltage", "Forward Voltage (Vf@If)"],
        ),
        MappingParameterDB(
            "max_current",
            ["Average Rectified Current (Io)"],
        ),
        MappingParameterDB(
            "reverse_working_voltage",
            ["Reverse Voltage (Vr)", "Reverse Stand-Off Voltage (Vrwm)"],
        ),
        MappingParameterDB(
            "reverse_leakage_current",
            ["Reverse Leakage Current", "Reverse Leakage Current (Ir)"],
        ),
    ],
    F.LED: [
        MappingParameterDB(
            "color",
            ["Emitted Color"],
            transform_fn=str_to_enum_func(F.LED.Color),
        ),
        MappingParameterDB(
            "max_brightness",
            ["Luminous Intensity"],
        ),
        MappingParameterDB(
            "max_current",
            ["Forward Current"],
        ),
        MappingParameterDB(
            "forward_voltage",
            ["Forward Voltage", "Forward Voltage (VF)"],
        ),
    ],
    F.MOSFET: [
        MappingParameterDB(
            "max_drain_source_voltage",
            ["Drain Source Voltage (Vdss)"],
        ),
        MappingParameterDB(
            "max_continuous_drain_current",
            ["Continuous Drain Current (Id)"],
        ),
        MappingParameterDB(
            "channel_type",
            ["Type"],
            transform_fn=str_to_enum_func(F.MOSFET.ChannelType),
        ),
        MappingParameterDB(
            "gate_source_threshold_voltage",
            ["Gate Threshold Voltage (Vgs(th)@Id)"],
        ),
        MappingParameterDB(
            "on_resistance",
            ["Drain Source On Resistance (RDS(on)@Vgs,Id)"],
        ),
    ],
    F.LDO: [
        MappingParameterDB(
            "output_polarity",
            ["Output Polarity"],
            transform_fn=str_to_enum_func(F.LDO.OutputPolarity),
        ),
        MappingParameterDB(
            "max_input_voltage",
            ["Maximum Input Voltage"],
        ),
        MappingParameterDB(
            "output_type",
            ["Output Type"],
            transform_fn=str_to_enum_func(F.LDO.OutputType),
        ),
        MappingParameterDB(
            "output_current",
            ["Output Current"],
        ),
        MappingParameterDB(
            "dropout_voltage",
            ["Dropout Voltage"],
        ),
        MappingParameterDB(
            "output_voltage",
            ["Output Voltage"],
        ),
        MappingParameterDB(
            "quiescent_current",
            [
                "Quiescent Current",
                "standby current",
                "Quiescent Current (Ground Current)",
            ],
        ),
    ],
}


def try_get_param_mapping(module: Module) -> list[MappingParameterDB]:
    try:
        mapping = find(_MAPPINGS_BY_TYPE.items(), lambda m: isinstance(module, m[0]))[1]
    except KeyErrorAmbiguous as e:
        mapping = _MAPPINGS_BY_TYPE[
            closest_base_class(type(module), [k for k, _ in e.duplicates])
        ]
    except KeyErrorNotFound:
        mapping = []

    return mapping
