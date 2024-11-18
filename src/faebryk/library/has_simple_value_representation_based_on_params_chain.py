# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.parameter import (
    Boolean,
    EnumDomain,
    Numbers,
    Parameter,
    ParameterOperableHasNoLiteral,
)
from faebryk.libs.sets.quantity_sets import Quantity_Interval
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.units import Quantity, Unit, to_si_str
from faebryk.libs.util import join_if_non_empty


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
                if isinstance(value, domain.enum_t):
                    return value.value
                elif isinstance(value, P_Set):
                    # TODO
                    raise NotImplementedError()
                raise ValueError(f"value {value} is not an enum")

            if isinstance(domain, Boolean):
                if self.tolerance:
                    raise ValueError("tolerance not supported for boolean")
                if isinstance(value, bool):
                    return str(value).lower()
                if isinstance(value, P_Set):
                    # TODO
                    raise NotImplementedError()
                raise ValueError(f"value {value} is not a boolean")

            if isinstance(domain, Numbers):
                unit = self.unit if self.unit is not None else self.param.units
                # TODO If tolerance, maybe hint that it's weird there isn't any
                if Parameter.is_number_literal(value):
                    assert not isinstance(value, Unit)
                    return to_si_str(value, unit, 2)
                if isinstance(value, P_Set):
                    if isinstance(value, Quantity_Interval):
                        center, tolerance = value.as_center_tuple(relative=True)
                        center_str = to_si_str(center, unit, 2)
                        assert isinstance(tolerance, Quantity)
                        if self.tolerance and tolerance > 0:
                            tolerance_str = f" ±{to_si_str(tolerance, "%", 0)}"
                            return f"{center_str}{tolerance_str}"
                        return center_str
                    # TODO
                    raise NotImplementedError()
                raise ValueError(f"value {value} is not a number")

            raise NotImplementedError(f"No support for {domain}")

        def get_value(self) -> str:
            return join_if_non_empty(
                " ",
                self.prefix,
                self._get_value(),
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
