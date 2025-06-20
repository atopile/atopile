# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.parameter import (
    Boolean,
    EnumDomain,
    Numbers,
    Parameter,
    ParameterOperableHasNoLiteral,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import BoolSet, EnumSet
from faebryk.libs.units import Quantity, Unit, to_si_str
from faebryk.libs.util import join_if_non_empty

logger = logging.getLogger(__name__)


class has_simple_value_representation_based_on_params_chain(
    F.has_simple_value_representation.impl()
):
    @dataclass
    class Spec:
        param: Parameter
        unit: Unit | Quantity | None = None
        """
        Override unit of param \n
        E.g use VA instead of W
        """
        tolerance: bool = False
        prefix: str = ""
        suffix: str = ""
        default: str | None = ""
        """
        Set to None to require the parameter to be set.
        """

        def _get_value(self) -> str:
            try:
                value = self.param.get_literal()
            except ParameterOperableHasNoLiteral:
                if self.default is not None:
                    return self.default
                raise

            domain = self.param.domain

            # TODO this is probably not the only place we will ever need this big switch
            # consider moving it somewhere else
            if isinstance(domain, EnumDomain):
                if self.tolerance:
                    raise ValueError("tolerance not supported for enum")
                # TODO handle units
                enum = EnumSet.from_value(value)
                if not enum.is_single_element():
                    raise NotImplementedError()
                val = next(iter(enum.elements))
                # TODO not sure I like this
                if isinstance(val.value, str):
                    return val.value
                return val.name

            if isinstance(domain, Boolean):
                if self.tolerance:
                    raise ValueError("tolerance not supported for boolean")
                bool_val = BoolSet.from_value(value)
                if not bool_val.is_single_element():
                    raise NotImplementedError()
                return str(next(iter(bool_val.elements))).lower()

            if isinstance(domain, Numbers):
                unit = self.unit if self.unit is not None else self.param.units
                # TODO If tolerance, maybe hint that it's weird there isn't any
                value_lit = Quantity_Interval_Disjoint.from_value(value)
                if value_lit.is_single_element():
                    return to_si_str(value_lit.min_elem, unit, 2)
                if len(value_lit._intervals.intervals) > 1:
                    raise NotImplementedError()
                center, tolerance = value_lit.as_gapless().as_center_tuple(
                    relative=True
                )
                center_str = to_si_str(center, unit, 2)
                assert isinstance(tolerance, Quantity)
                if self.tolerance and tolerance > 0:
                    tolerance_str = f" ±{to_si_str(tolerance, '%', 0)}"
                    return f"{center_str}{tolerance_str}"
                return center_str

            raise NotImplementedError(f"No support for {domain}")

        def get_value(self) -> str:
            try:
                value = self._get_value()
            except Exception as e:
                if self.default is None:
                    raise
                logger.debug(f"Failed to get value for `{self.param}`: {e}")
                return ""
            return join_if_non_empty(
                " ",
                self.prefix,
                value,
                self.suffix,
            )

    def __init__(self, *specs: Spec, prefix: str = "", suffix: str = "") -> None:
        super().__init__()
        self.specs = specs
        self.prefix = prefix
        self.suffix = suffix

    def get_value(self) -> str:
        return join_if_non_empty(
            " ",
            self.prefix,
            *[s.get_value() for s in self.specs],
            self.suffix,
        )
