import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import ParameterOperatable
from faebryk.libs.library import L
from faebryk.libs.units import P, Unit
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


@dataclass(frozen=True)
class AttributeMapping:
    name: str
    tolerance_name: str | None = None
    transform_fn: Callable[[str], ParameterOperatable.Literal] | None = None
    unit: Unit | None = None


_MAPPINGS_BY_TYPE: dict[type[Module], list[AttributeMapping]] = {
    F.Resistor: [
        AttributeMapping("resistance", "resistance_tolerance", unit=P.ohm),
        AttributeMapping("max_power", unit=P.W),
        AttributeMapping("max_voltage", unit=P.V),
    ],
    F.Capacitor: [
        AttributeMapping("capacitance", "capacitance_tolerance", unit=P.F),
        AttributeMapping("max_voltage", unit=P.V),
        AttributeMapping(
            "temperature_coefficient",
            transform_fn=lambda x: str_to_enum(
                F.Capacitor.TemperatureCoefficient, x.replace("NP0", "C0G")
            ),
        ),
    ],
    F.Inductor: [
        AttributeMapping("inductance", "inductance_tolerance", unit=P.H),
        AttributeMapping("max_current", unit=P.A),
        AttributeMapping("dc_resistance", unit=P.ohm),
        AttributeMapping("self_resonant_frequency", unit=P.Hz),
    ],
    F.TVS: [
        AttributeMapping("forward_voltage", unit=P.V),
        # TODO: think about the difference of meaning for max_current between Diode
        # and TVS
        AttributeMapping("max_current", unit=P.A),
        AttributeMapping("reverse_working_voltage", unit=P.V),
        AttributeMapping("reverse_leakage_current", unit=P.A),
        AttributeMapping("reverse_breakdown_voltage", unit=P.V),
    ],
    F.Diode: [
        AttributeMapping("forward_voltage", unit=P.V),
        AttributeMapping("max_current", unit=P.A),
        AttributeMapping("reverse_working_voltage", unit=P.V),
        AttributeMapping("reverse_leakage_current", unit=P.A),
    ],
    F.LED: [
        AttributeMapping(
            "color",
            transform_fn=str_to_enum_func(F.LED.Color),
        ),
        AttributeMapping("max_brightness"),
        AttributeMapping("max_current", unit=P.A),
        AttributeMapping("forward_voltage", unit=P.V),
    ],
    F.MOSFET: [
        AttributeMapping("max_drain_source_voltage", unit=P.V),
        AttributeMapping("max_continuous_drain_current", unit=P.A),
        AttributeMapping(
            "channel_type",
            transform_fn=str_to_enum_func(F.MOSFET.ChannelType),
        ),
        AttributeMapping("gate_source_threshold_voltage", unit=P.V),
        AttributeMapping("on_resistance", unit=P.ohm),
    ],
    F.LDO: [
        AttributeMapping(
            "output_polarity",
            transform_fn=str_to_enum_func(F.LDO.OutputPolarity),
        ),
        AttributeMapping("max_input_voltage", unit=P.V),
        AttributeMapping(
            "output_type",
            transform_fn=str_to_enum_func(F.LDO.OutputType),
        ),
        AttributeMapping("output_current", unit=P.A),
        AttributeMapping("dropout_voltage", unit=P.V),
        AttributeMapping("output_voltage", unit=P.V),
        AttributeMapping("quiescent_current", unit=P.A),
    ],
}


def try_get_param_mapping(module: Module) -> list[AttributeMapping]:
    try:
        mapping = find(_MAPPINGS_BY_TYPE.items(), lambda m: isinstance(module, m[0]))[1]
    except KeyErrorAmbiguous as e:
        mapping = _MAPPINGS_BY_TYPE[
            closest_base_class(type(module), [k for k, _ in e.duplicates])
        ]
    except KeyErrorNotFound:
        mapping = []

    return mapping
