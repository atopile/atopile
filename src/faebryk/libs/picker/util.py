# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.parameter import Parameter
from faebryk.library.Set import Set
from faebryk.libs.e_series import (
    E_SERIES_VALUES,
    ParamNotResolvedError,
    e_series_intersect,
)
from faebryk.libs.picker.picker import PickError
from faebryk.libs.units import Quantity, to_si_str
from faebryk.libs.util import cast_assert


def generate_si_values(
    value: Parameter[Quantity], si_unit: str, e_series: set[float] | None = None
):
    """
    Generate a list of permissible SI values for the given parameter from an
    E-series
    """

    value = value.get_most_narrow()

    try:
        intersection = Set(
            [e_series_intersect(value, e_series or E_SERIES_VALUES.E_ALL)]
        ).params
    except ParamNotResolvedError as e:
        raise PickError(value, f"Could not run e_series_intersect: {e}") from e

    return [
        to_si_str(cast_assert(F.Constant, r).value, si_unit)
        .replace("µ", "u")
        .replace("inf", "∞")
        for r in intersection
    ]
