# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import indent
from typing import Any, Callable

from tortoise.expressions import Q
from tortoise.fields import CharField, DatetimeField, IntField, JSONField, TextField
from tortoise.models import Model

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import (
    Parameter,
    ParameterOperatable,
)
from faebryk.libs.picker.lcsc import (
    LCSC_Part,
    attach,
)
from faebryk.libs.picker.picker import (
    DescriptiveProperties,
    has_part_picked_defined,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Singleton,
)
from faebryk.libs.units import UndefinedUnitError, quantity
from faebryk.libs.util import once

logger = logging.getLogger(__name__)

# TODO dont hardcode relative paths
BUILD_FOLDER = Path("./build")
CACHE_FOLDER = BUILD_FOLDER / Path("cache")

INSPECT_KNOWN_SUPERSETS_LIMIT = 100


class JLCPCB_Part(LCSC_Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno)


@dataclass(frozen=True)
class MappingParameterDB:
    param_name: str
    attr_keys: list[str] = field(hash=False)
    attr_tolerance_key: str | None = None
    transform_fn: Callable[[str], ParameterOperatable.Literal] | None = None
    ignore_at: bool = True


class Category(Model):
    id = IntField(primary_key=True)
    category = CharField(max_length=255)
    subcategory = CharField(max_length=255)

    class Meta:
        table = "categories"

    async def get_ids(
        self, category: str = "", subcategory: str = ""
    ) -> list[dict[str, Any]]:
        """
        Get the category ids for the given category and subcategory

        :param category: The category to search for, use "" for any
        :param subcategory: The subcategory to search for, use "" for any

        :return: A list of category ids for the JLCPCB database Component id field
        """
        filter_query = Q()
        if category != "":
            filter_query &= Q(category__icontains=category)
        if subcategory != "":
            filter_query &= Q(subcategory__icontains=subcategory)
        category_ids = await self.filter(filter_query).values("id")
        if len(category_ids) < 1:
            raise LookupError(
                f"Could not find a match for category {category} "
                f"and subcategory {subcategory}",
            )
        return [c["id"] for c in category_ids]


class Manufacturers(Model):
    id = IntField(primary_key=True)
    name = CharField(max_length=255)

    class Meta:
        table = "manufacturers"

    async def get_ids(self, manufacturer: str) -> list[int]:
        """
        Get the manufacturer ids for the given manufacturer

        :param manufacturer: The manufacturer to search for

        :return: A list of manufacturer ids for the JLCPCB database Component id field
        """
        manufacturer_ids = await self.filter(name__icontains=manufacturer).values("id")
        if len(manufacturer_ids) < 1:
            raise LookupError(f"Could not find a match for manufacturer {manufacturer}")
        return [m["id"] for m in manufacturer_ids]

    async def get_from_id(self, manufacturer_id: int) -> str:
        return (await self.get(id=manufacturer_id)).name


class Component(Model):
    lcsc = IntField(primary_key=True)
    category_id = IntField()
    category = CharField(max_length=255)
    subcategory = CharField(max_length=255, optional=True)
    mfr = CharField(max_length=255)
    package = CharField(max_length=255)
    joints = IntField()
    manufacturer_id = IntField()
    manufacturer_name = CharField(max_length=255, optional=True)
    basic = IntField()
    description = CharField(max_length=255)
    datasheet = CharField(max_length=255)
    stock = IntField()
    price = JSONField()
    last_update = DatetimeField()
    extra = TextField()
    flag = IntField()
    last_on_stock = DatetimeField()
    preferred = IntField()

    class Meta:
        table = "components"

    class ParseError(Exception):
        pass

    @property
    def partno(self):
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

        if self.basic:
            handling_fee = BASIC_HANDLING_FEE
        elif self.preferred:
            handling_fee = PREFERRED_HANDLING_FEE
        else:
            handling_fee = EXTENDED_HANDLING_FEE

        unit_price = float("inf")
        try:
            for p in self.price:
                if p["qTo"] is None or qty < p["qTo"]:
                    unit_price = float(p["price"])
            unit_price = float(self.price[-1]["price"])
        except LookupError:
            pass

        return unit_price * qty + handling_fee

    @property
    @once
    def extra_(self) -> dict:
        if isinstance(self.extra, str):
            return json.loads(self.extra)
        assert isinstance(self.extra, dict)
        return self.extra

    def attribute_to_range(
        self, attribute_name: str, use_tolerance: bool = False, ignore_at: bool = True
    ) -> Quantity_Interval:
        """
        Convert a component value in the extra['attributes'] dict to a parameter

        :param attribute_name: The key in the extra['attributes'] dict to convert
        :param use_tolerance: Whether to use the tolerance field in the component

        :return: The parameter representing the attribute value
        """
        assert isinstance(self.extra_, dict) and "attributes" in self.extra_

        value_field = self.extra_["attributes"][attribute_name]
        # parse fields like "850mV@1A"
        # TODO better to actually parse this
        if ignore_at:
            value_field = value_field.split("@")[0]

        # parse fields like "110mA;130mA"
        # TODO: better data model so we can choose the appropriate value
        if ";" in value_field:
            value_field = value_field.split(";")[0]

        value_field = value_field.replace("cd", "candela")

        # parse fields like "1.5V~2.5V"
        if "~" in value_field:
            values = value_field.split("~")
            if len(values) != 2:
                raise ValueError(f"Invalid range from value '{value_field}'")
            low, high = map(quantity, values)
            return Quantity_Interval(low, high)

        # unit hacks

        try:
            value = quantity(value_field)
        except (AssertionError, UndefinedUnitError) as e:
            raise ValueError(f"Could not parse value field '{value_field}'") from e

        if not use_tolerance:
            return Quantity_Singleton(value)

        if "Tolerance" not in self.extra_["attributes"]:
            raise ValueError(f"No Tolerance field in component (lcsc: {self.lcsc})")
        if "ppm" in self.extra_["attributes"]["Tolerance"]:
            tolerance = float(self.extra_["attributes"]["Tolerance"].strip("±pm")) / 1e6
        elif "%~+" in self.extra_["attributes"]["Tolerance"]:
            tolerances = self.extra_["attributes"]["Tolerance"].split("~")
            tolerances = [float(t.strip("%+-")) for t in tolerances]
            tolerance = max(tolerances) / 100
        elif "%" in self.extra_["attributes"]["Tolerance"]:
            tolerance = float(self.extra_["attributes"]["Tolerance"].strip("%±")) / 100
        else:
            raise ValueError(
                "Could not parse tolerance field "
                f"'{self.extra_['attributes']['Tolerance']}'"
            )

        return Quantity_Interval.from_center_rel(value, tolerance)

    def get_literal(self, m: MappingParameterDB) -> ParameterOperatable.Literal:
        """
        Transform a component attribute to a parameter

        :param attribute_search_keys: The key in the component's extra['attributes']
        dict that holds the value to check
        :param tolerance_search_key: The key in the component's extra['attributes'] dict
        that holds the tolerance value
        :param parser: A function to convert the attribute value to the correct type

        :return: The parameter representing the attribute value
        """

        attribute_search_keys = m.attr_keys
        tolerance_search_key = m.attr_tolerance_key
        parser = m.transform_fn

        if tolerance_search_key is not None and parser is not None:
            raise NotImplementedError(
                "Cannot provide both tolerance_search_key and parser arguments"
            )

        assert isinstance(self.extra_, dict)

        attr_key = next(
            (
                k
                for k in attribute_search_keys
                if k in self.extra_.get("attributes", "")
            ),
            None,
        )

        if "attributes" not in self.extra_:
            raise LookupError("does not have any attributes")
        if attr_key is None:
            raise LookupError(
                f"does not have any of required attribute fields: "
                f"{attribute_search_keys} in {self.extra_['attributes']}"
            )
        if (
            tolerance_search_key is not None
            and tolerance_search_key not in self.extra_["attributes"]
        ):
            raise LookupError(
                f"does not have any of required tolerance fields: "
                f"{tolerance_search_key}"
            )

        if parser is not None:
            return parser(self.extra_["attributes"][attr_key])

        return self.attribute_to_range(
            attr_key, tolerance_search_key is not None, m.ignore_at
        )

    def get_literal_for_mappings(
        self, mapping: list[MappingParameterDB]
    ) -> dict[MappingParameterDB, ParameterOperatable.Literal | None]:
        params = {}
        for m in mapping:
            try:
                params[m] = self.get_literal(m)
            except (ValueError, LookupError):
                params[m] = None
        return params

    def attach(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
        qty: int = 1,
    ):
        params = self.get_literal_for_mappings(mapping)

        attach(module, self.partno)

        module.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.partno: self.mfr,
                    DescriptiveProperties.manufacturer: self.mfr_name,
                    DescriptiveProperties.datasheet: self.datasheet,
                    "JLCPCB stock": str(self.stock),
                    "JLCPCB price": f"{self.get_price(qty):.4f}",
                    "JLCPCB description": self.description,
                    "JLCPCB Basic": str(bool(self.basic)),
                    "JLCPCB Preferred": str(bool(self.preferred)),
                },
            )
        )

        module.add(has_part_picked_defined(JLCPCB_Part(self.partno)))

        for name, value in params.items():
            p = getattr(module, name.param_name)
            assert isinstance(p, Parameter)
            if value is None:
                p.constrain_superset(p.domain.unbounded(p))
            else:
                p.alias_is(value)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Attached component {self.partno} to module {module}: \n"
                f"{indent(str(params), ' '*4)}\n--->\n"
                f"{indent(module.pretty_params(), ' '*4)}"
            )

    @property
    def mfr_name(self):
        try:
            return self.manufacturer_name
        except AttributeError:
            return asyncio.run(Manufacturers().get_from_id(self.manufacturer_id))
