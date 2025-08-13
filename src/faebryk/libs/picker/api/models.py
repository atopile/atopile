# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import functools
import logging
from dataclasses import asdict, dataclass, field, make_dataclass
from textwrap import indent
from typing import Any

from dataclasses_json import config as dataclass_json_config
from dataclasses_json import dataclass_json

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.libs.exceptions import UserException, downgrade
from faebryk.libs.picker.lcsc import PickedPartLCSC
from faebryk.libs.picker.lcsc import attach as lcsc_attach
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import Serializable, SerializableJSONEncoder, md_list, once

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Interval:
    min: float | None
    max: float | None


ApiParamT = P_Set | None


def SerializableField():
    return field(
        metadata=dataclass_json_config(encoder=SerializableJSONEncoder().default)
    )


# Consider making this a mixin instead
def _pretty_params_helper(params) -> str:
    def _map(v: Any) -> str:
        if v is None:
            return "**unconstrained**"
        elif isinstance(v, (P_Set, int, float)):
            return f"`{v}`"
        elif isinstance(v, str):
            return f'"{v}"'
        else:
            return str(v)

    return md_list(f"`{k}`: {_map(v)}" for k, v in asdict(params).items())


@dataclass_json
@dataclass(frozen=True, kw_only=True)
class BaseParams(Serializable):
    package: ApiParamT = SerializableField()
    qty: int
    endpoint: F.is_pickable_by_type.Endpoint | None = None

    def serialize(self) -> dict:
        return self.to_dict()  # type: ignore

    def pretty_str(self) -> str:
        return _pretty_params_helper(self)


@once
def make_params_for_type(module_type: type[Module]) -> type:
    m = module_type()
    assert m.has_trait(F.is_pickable_by_type)
    pickable_trait = m.get_trait(F.is_pickable_by_type)

    fields = [
        (
            "endpoint",
            F.is_pickable_by_type.Endpoint,
            field(default=pickable_trait.endpoint.value, init=False),
        ),
        *[
            (param.get_name(), ApiParamT, SerializableField())
            for param in pickable_trait.params
        ],
    ]

    cls = make_dataclass(
        f"{module_type.__name__}Params",
        fields,
        bases=(BaseParams,),
        frozen=True,
        kw_only=True,
    )
    return dataclass_json(cls)


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

    def pretty_str(self) -> str:
        return _pretty_params_helper(self)


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

    def pretty_str(self) -> str:
        return _pretty_params_helper(self)


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
            F.has_part_picked(
                PickedPartLCSC(
                    manufacturer=self.manufacturer_name,
                    partno=self.part_number,
                    supplier_partno=self.lcsc_display,
                    info=PickedPartLCSC.Info(
                        stock=self.stock,
                        price=self.get_price(qty),
                        description=self.description,
                        basic=bool(self.is_basic),
                        preferred=bool(self.is_preferred),
                    ),
                )
            )
        )
        module.add(F.has_datasheet_defined(self.datasheet_url))

        missing_attrs = []
        # only for type picks
        if module.has_trait(F.is_pickable_by_type):
            for name, literal in self.attribute_literals.items():
                if not hasattr(module, name):
                    missing_attrs.append(name)
                    continue

                p = getattr(module, name)
                assert isinstance(p, Parameter)
                if literal is None:
                    literal = p.domain.unbounded(p)

                p.alias_is(literal)

        if missing_attrs:
            with downgrade(UserException):
                # TODO: suggest specific library module
                # (requires Component to know its type)
                attrs = "\n".join(f"- {attr}" for attr in missing_attrs)
                raise UserException(
                    f"Module `{module}` is missing attributes:\n{attrs}\n\n"
                    "Consider using the standard library version of this module.",
                    title="Attribute(s) not found",
                )

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Attached component {self.lcsc_display} to module {module}: \n"
                f"{indent(str(self.attributes), ' ' * 4)}\n--->\n"
                f"{indent(module.pretty_params(), ' ' * 4)}"
            )

    def __rich_repr__(self):
        yield f"{type(self).__name__}({self.lcsc_display})"

    class ParseError(Exception):
        pass
