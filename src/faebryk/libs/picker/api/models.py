# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import functools
import logging
from dataclasses import dataclass, field
from textwrap import indent

from dataclasses_json import config as dataclass_json_config
from dataclasses_json import dataclass_json

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.libs.exceptions import UserException, downgrade
from faebryk.libs.picker.lcsc import LCSC_Part
from faebryk.libs.picker.lcsc import attach as lcsc_attach
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import Serializable, SerializableJSONEncoder

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass(frozen=True)
class PackageCandidate:
    package: str


@dataclass_json
@dataclass(frozen=True, kw_only=True)
class BaseParams(Serializable):
    package_candidates: frozenset[PackageCandidate]
    qty: int
    endpoint: str | None = None

    def serialize(self) -> dict:
        return self.to_dict()  # type: ignore


@dataclass(frozen=True)
class Interval:
    min: float | None
    max: float | None


ApiParamT = P_Set | None


def SerializableField():
    return field(
        metadata=dataclass_json_config(encoder=SerializableJSONEncoder().default)
    )


@dataclass(frozen=True, kw_only=True)
class ResistorParams(BaseParams):
    endpoint: str = "resistors"
    resistance: ApiParamT = SerializableField()
    max_power: ApiParamT = SerializableField()
    max_voltage: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class CapacitorParams(BaseParams):
    endpoint: str = "capacitors"
    capacitance: ApiParamT = SerializableField()
    max_voltage: ApiParamT = SerializableField()
    temperature_coefficient: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class InductorParams(BaseParams):
    endpoint: str = "inductors"
    inductance: ApiParamT = SerializableField()
    self_resonant_frequency: ApiParamT = SerializableField()
    max_current: ApiParamT = SerializableField()
    dc_resistance: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class DiodeParams(BaseParams):
    endpoint: str = "diodes"
    forward_voltage: ApiParamT = SerializableField()
    reverse_working_voltage: ApiParamT = SerializableField()
    reverse_leakage_current: ApiParamT = SerializableField()
    max_current: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class TVSParams(DiodeParams):
    endpoint: str = "tvs"
    reverse_breakdown_voltage: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class LEDParams(DiodeParams):
    endpoint: str = "leds"
    max_brightness: ApiParamT = SerializableField()
    color: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class LDOParams(BaseParams):
    endpoint: str = "ldos"
    max_input_voltage: ApiParamT = SerializableField()
    output_voltage: ApiParamT = SerializableField()
    quiescent_current: ApiParamT = SerializableField()
    dropout_voltage: ApiParamT = SerializableField()
    # psrr: ApiParamT = SerializableField()  # TODO
    output_polarity: ApiParamT = SerializableField()
    output_type: ApiParamT = SerializableField()
    output_current: ApiParamT = SerializableField()


@dataclass(frozen=True, kw_only=True)
class MOSFETParams(BaseParams):
    endpoint: str = "mosfets"
    channel_type: ApiParamT = SerializableField()
    # saturation_type: ApiParamT = SerializableField()  # TODO
    gate_source_threshold_voltage: ApiParamT = SerializableField()
    max_drain_source_voltage: ApiParamT = SerializableField()
    max_continuous_drain_current: ApiParamT = SerializableField()
    on_resistance: ApiParamT = SerializableField()


@dataclass_json
@dataclass(frozen=True)
class LCSCParams(Serializable):
    lcsc: int
    quantity: int

    def serialize(self) -> dict:
        return self.to_dict()  # type: ignore

    @classmethod
    def deserialize(cls, data: dict) -> "LCSCParams":
        return cls(**data)


@dataclass_json
@dataclass(frozen=True)
class ManufacturerPartParams(Serializable):
    manufacturer_name: str
    part_number: str
    quantity: int

    def serialize(self) -> dict:
        return self.to_dict()  # type: ignore

    @classmethod
    def deserialize(cls, data: dict) -> "ManufacturerPartParams":
        return cls(**data)


@dataclass_json
@dataclass
class ComponentPrice:
    qTo: int | None
    price: float
    qFrom: int | None


@dataclass_json
@dataclass
class Component:
    lcsc: int
    manufacturer_name: str
    part_number: str
    package: str
    datasheet_url: str
    description: str
    is_basic: int
    is_preferred: int
    stock: int
    price: list[ComponentPrice]
    attributes: dict[str, dict]  # FIXME: more specific

    @property
    def lcsc_display(self) -> str:
        return f"C{self.lcsc}"

    def get_price(self, qty: int = 1) -> float:
        """
        Get the price for qty of the component including handling fees

        For handling fees and component price classifications, see:
        https://jlcpcb.com/help/article/pcb-assembly-faqs
        """
        BASIC_HANDLING_FEE = 0
        PREFERRED_HANDLING_FEE = 0
        EXTENDED_HANDLING_FEE = 3

        if qty < 1:
            raise ValueError("Quantity must be greater than 0")

        if self.is_basic:
            handling_fee = BASIC_HANDLING_FEE
        elif self.is_preferred:
            handling_fee = PREFERRED_HANDLING_FEE
        else:
            handling_fee = EXTENDED_HANDLING_FEE

        unit_price = float("inf")
        try:
            for p in self.price:
                if p.qTo is None or qty < p.qTo:
                    unit_price = float(p.price)
            unit_price = float(self.price[-1].price)
        except LookupError:
            pass

        return unit_price * qty + handling_fee

    @functools.cached_property
    def attribute_literals(self) -> dict[str, P_Set | None]:
        def deserialize(k, v):
            if v is None:
                return None
            return P_Set.deserialize(v)

        return {k: deserialize(k, v) for k, v in self.attributes.items()}

    def attach(self, module: Module, qty: int = 1):
        lcsc_attach(module, self.lcsc_display)

        module.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.partno: self.part_number,
                    DescriptiveProperties.manufacturer: self.manufacturer_name,
                    DescriptiveProperties.datasheet: self.datasheet_url,
                    "JLCPCB stock": str(self.stock),
                    "JLCPCB price": f"{self.get_price(qty):.4f}",
                    "JLCPCB description": self.description,
                    "JLCPCB Basic": str(bool(self.is_basic)),
                    "JLCPCB Preferred": str(bool(self.is_preferred)),
                },
            )
        )

        module.add(F.has_part_picked(LCSC_Part(self.lcsc_display)))

        for name, literal in self.attribute_literals.items():
            if not hasattr(module, name):
                with downgrade(UserException):
                    raise UserException(
                        f"{module} does not have attribute {name}",
                        title="Attribute not found",
                    )
                continue

            p = getattr(module, name)
            assert isinstance(p, Parameter)
            if literal is None:
                literal = p.domain.unbounded(p)

            p.alias_is(literal)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Attached component {self.lcsc_display} to module {module}: \n"
                f"{indent(str(self.attributes), ' '*4)}\n--->\n"
                f"{indent(module.pretty_params(), ' '*4)}"
            )

    class ParseError(Exception):
        pass
