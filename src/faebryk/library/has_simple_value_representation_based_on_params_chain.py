# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.parameter import Parameter
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import Quantity, Unit
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

        def get_value(self) -> str:
            raise NotImplementedError()

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
