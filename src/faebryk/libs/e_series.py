import logging
from collections.abc import Sequence
from math import ceil, floor, log10
from typing import Tuple, TypeVar, cast

from faebryk.libs.library import L
from faebryk.libs.sets import Range, Ranges
from faebryk.libs.units import Quantity, Unit, dimensionless
from faebryk.libs.util import once

logger = logging.getLogger(__name__)

E_SERIES = frozenset[float]


class E_SERIES_VALUES:
    E192 = frozenset(
        [
            1.00,
            1.01,
            1.02,
            1.04,
            1.05,
            1.06,
            1.07,
            1.09,
            1.10,
            1.11,
            1.13,
            1.14,
            1.15,
            1.17,
            1.18,
            1.20,
            1.21,
            1.23,
            1.24,
            1.26,
            1.27,
            1.29,
            1.30,
            1.32,
            1.33,
            1.35,
            1.37,
            1.38,
            1.40,
            1.42,
            1.43,
            1.45,
            1.47,
            1.49,
            1.50,
            1.52,
            1.54,
            1.56,
            1.58,
            1.60,
            1.62,
            1.64,
            1.65,
            1.67,
            1.69,
            1.72,
            1.74,
            1.76,
            1.78,
            1.80,
            1.82,
            1.84,
            1.87,
            1.89,
            1.91,
            1.93,
            1.96,
            1.98,
            2.00,
            2.03,
            2.05,
            2.08,
            2.10,
            2.13,
            2.15,
            2.18,
            2.21,
            2.23,
            2.26,
            2.29,
            2.32,
            2.34,
            2.37,
            2.40,
            2.43,
            2.46,
            2.49,
            2.52,
            2.55,
            2.58,
            2.61,
            2.64,
            2.67,
            2.71,
            2.74,
            2.77,
            2.80,
            2.84,
            2.87,
            2.91,
            2.94,
            2.98,
            3.01,
            3.05,
            3.09,
            3.12,
            3.16,
            3.20,
            3.24,
            3.28,
            3.32,
            3.36,
            3.40,
            3.44,
            3.48,
            3.52,
            3.57,
            3.61,
            3.65,
            3.70,
            3.74,
            3.79,
            3.83,
            3.88,
            3.92,
            3.97,
            4.02,
            4.07,
            4.12,
            4.17,
            4.22,
            4.27,
            4.32,
            4.37,
            4.42,
            4.48,
            4.53,
            4.59,
            4.64,
            4.70,
            4.75,
            4.81,
            4.87,
            4.93,
            4.99,
            5.05,
            5.11,
            5.17,
            5.23,
            5.30,
            5.36,
            5.42,
            5.49,
            5.56,
            5.62,
            5.69,
            5.76,
            5.83,
            5.90,
            5.97,
            6.04,
            6.12,
            6.19,
            6.26,
            6.34,
            6.42,
            6.49,
            6.57,
            6.65,
            6.73,
            6.81,
            6.90,
            6.98,
            7.06,
            7.15,
            7.23,
            7.32,
            7.41,
            7.50,
            7.59,
            7.68,
            7.77,
            7.87,
            7.96,
            8.06,
            8.16,
            8.25,
            8.35,
            8.45,
            8.56,
            8.66,
            8.76,
            8.87,
            8.98,
            9.09,
            9.20,
            9.31,
            9.42,
            9.53,
            9.65,
            9.76,
            9.88,
        ]
    )

    E96 = frozenset(
        [
            1.00,
            1.02,
            1.05,
            1.07,
            1.10,
            1.13,
            1.15,
            1.18,
            1.21,
            1.24,
            1.27,
            1.30,
            1.33,
            1.37,
            1.40,
            1.43,
            1.47,
            1.50,
            1.54,
            1.58,
            1.62,
            1.65,
            1.69,
            1.74,
            1.78,
            1.82,
            1.87,
            1.91,
            1.96,
            2.00,
            2.05,
            2.10,
            2.15,
            2.21,
            2.26,
            2.32,
            2.37,
            2.43,
            2.49,
            2.55,
            2.61,
            2.67,
            2.74,
            2.80,
            2.87,
            2.94,
            3.01,
            3.09,
            3.16,
            3.24,
            3.32,
            3.40,
            3.48,
            3.57,
            3.65,
            3.74,
            3.83,
            3.92,
            4.02,
            4.12,
            4.22,
            4.32,
            4.42,
            4.53,
            4.64,
            4.75,
            4.87,
            4.99,
            5.11,
            5.23,
            5.36,
            5.49,
            5.62,
            5.76,
            5.90,
            6.04,
            6.19,
            6.34,
            6.49,
            6.65,
            6.81,
            6.98,
            7.15,
            7.32,
            7.50,
            7.68,
            7.87,
            8.06,
            8.25,
            8.45,
            8.66,
            8.87,
            9.09,
            9.31,
            9.53,
            9.76,
        ]
    )

    E48 = frozenset(
        [
            1.00,
            1.05,
            1.10,
            1.15,
            1.21,
            1.27,
            1.33,
            1.40,
            1.47,
            1.54,
            1.62,
            1.69,
            1.78,
            1.87,
            1.96,
            2.05,
            2.15,
            2.26,
            2.37,
            2.49,
            2.61,
            2.74,
            2.87,
            3.01,
            3.16,
            3.32,
            3.48,
            3.65,
            3.83,
            4.02,
            4.22,
            4.42,
            4.64,
            4.87,
            5.11,
            5.36,
            5.62,
            5.90,
            6.19,
            6.49,
            6.81,
            7.15,
            7.50,
            7.87,
            8.25,
            8.66,
            9.09,
            9.53,
        ]
    )

    E24 = frozenset(
        [
            1.0,
            1.1,
            1.2,
            1.3,
            1.5,
            1.6,
            1.8,
            2.0,
            2.2,
            2.4,
            2.7,
            3.0,
            3.3,
            3.6,
            3.9,
            4.3,
            4.7,
            5.1,
            5.6,
            6.2,
            6.8,
            7.5,
            8.2,
            9.1,
        ]
    )

    E12 = frozenset(
        [
            1.0,
            1.2,
            1.5,
            1.8,
            2.2,
            2.7,
            3.3,
            3.9,
            4.7,
            5.6,
            6.8,
            8.2,
        ]
    )

    E6 = frozenset(
        [
            1.0,
            1.5,
            2.2,
            3.3,
            4.7,
            6.8,
        ]
    )

    E3 = frozenset(
        [
            1.0,
            2.2,
            4.7,
        ]
    )
    E_ALL = frozenset(sorted(E24 | E192))


QuantityT = TypeVar("QuantityT", int, float, Quantity)


def repeat_set_over_base(
    values: set[float],
    base: int,
    exp_range: Sequence[int],
    unit: Unit,
    n_decimals: int = 13,
) -> L.Singles[QuantityT]:
    assert all(v >= 1 and v < base for v in values)
    return L.Singles[QuantityT](
        *(
            round(val * base**exp, n_decimals) * unit
            for val in values
            for exp in exp_range
        )
    )


@once
def e_series_intersect(
    value_set: Range[QuantityT] | Ranges[QuantityT],
    e_series: E_SERIES | None = None,
) -> L.Ranges[QuantityT]:
    if e_series is None:
        e_series = E_SERIES_VALUES.E_ALL

    if isinstance(value_set, Range):
        value_set = Ranges(value_set)

    if (
        value_set.is_empty()
        or value_set.min_elem() < 0
        or value_set.max_elem() == float("inf")
    ):
        raise ValueError("Need positive finite set")

    out = L.Empty(value_set.units)

    for sub_range in value_set:
        min_val_q = sub_range.min_elem().to_compact()
        max_val_q = sub_range.max_elem().to(min_val_q.units)

        min_val = min_val_q.magnitude
        max_val = max_val_q.magnitude

        e_series_values = repeat_set_over_base(
            values=e_series,
            base=10,
            exp_range=range(floor(log10(min_val)), ceil(log10(max_val)) + 1),
            unit=min_val_q.units,
        )
        out = out.op_union_ranges(e_series_values.op_intersect_range(sub_range))
    return out


def e_series_discretize_to_nearest(
    value: Range[Quantity], e_series: E_SERIES = E_SERIES_VALUES.E_ALL
) -> Quantity:
    target = cast(Quantity, (value.min_elem() + value.max_elem())) / 2

    e_series_values = repeat_set_over_base(
        e_series, 10, range(floor(log10(target)), ceil(log10(target)) + 1), target.units
    )

    return min(e_series_values, key=lambda x: abs(x - target))


def e_series_ratio(
    RH: Range[float],
    RL: Range[float],
    output_input_ratio: Range[float],
    e_values: E_SERIES = E_SERIES_VALUES.E_ALL,
) -> Tuple[float, float]:
    """
    Calculates the values for two components in the E series range which are bound by a
    ratio.

    RH and RL define the contstraints for the components, and output_input_ratio is the
    output/input voltage ratio as defined below.

    output_input_ratio = RL/(RH + RL)
    RL/oir = RH + RL
    RL * (1/oir -1) = RH
    RL = RH / (1/oir -1)

    Returns a tuple of RH/RL values.

    Can be used for a resistive divider.
    """

    rh_factor = output_input_ratio.op_invert().op_subtract_ranges(
        L.Singles(1.0 * dimensionless)
    )

    rh = Ranges(RH).op_intersect_ranges(rh_factor.op_mul_ranges(Ranges(RL)))
    rh_e = e_series_intersect(rh, e_values)
    rl = Ranges(RL).op_intersect_ranges(
        rh_factor.op_invert().op_mul_ranges(Ranges(rh_e))
    )
    rl_e = e_series_intersect(rl, e_values)

    target_ratio = (
        cast(Quantity, (output_input_ratio.min_elem() + output_input_ratio.max_elem()))
        / 2
    )

    solutions = []

    for rh_range in rh_e:
        rh_val = rh_range.min_elem()
        rl_ideal = rh_val / (1 / target_ratio - 1)

        rl_nearest_e_val = rl_e.closest_elem(rl_ideal)
        real_ratio = rl_nearest_e_val / (rh_val + rl_nearest_e_val)

        solutions.append((real_ratio, (float(rh_val), float(rl_nearest_e_val))))

    optimum = min(solutions, key=lambda x: abs(x[0] - target_ratio))

    logger.debug(
        f"{target_ratio=}, {optimum[0]=}, {output_input_ratio}, "
        f"error: {abs(optimum[0]/ target_ratio - 1)*100:.4f}%"
    )

    if optimum[0] not in output_input_ratio:
        raise ArithmeticError(
            "Calculated optimum RH RL value pair gives output/input voltage ratio "
            "outside of specified range. Consider relaxing the constraints"
        )

    return optimum[1]
