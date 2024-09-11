import copy
import logging
import math
from math import ceil, floor, log10
from typing import Tuple

import faebryk.library._F as F
from faebryk.core.parameter import Parameter
from faebryk.libs.units import Quantity

logger = logging.getLogger(__name__)

E_SERIES = set[float]


class E_SERIES_VALUES:
    E192 = {
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
    }

    E96 = {
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
    }

    E48 = {
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
    }

    E24 = {
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
    }

    E12 = {
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
    }

    E6 = {
        1.0,
        1.5,
        2.2,
        3.3,
        4.7,
        6.8,
    }

    E3 = {
        1.0,
        2.2,
        4.7,
    }

    E_ALL = set(sorted(E24 | E192))


def repeat_set_over_base(
    values: set[float], base: int, exp_range: range, n_decimals: int = 13
) -> set[float]:
    assert all(v >= 1 and v < base for v in values)
    return set(
        [round(val * base**exp, n_decimals) for val in values for exp in exp_range]
    )


class ParamNotResolvedError(Exception): ...


_e_series_cache: list[tuple[Parameter, int, set]] = []


def e_series_intersect[T: float | Quantity](
    value: Parameter[T], e_series: E_SERIES = E_SERIES_VALUES.E_ALL
) -> F.Set[T]:
    # TODO this got really uglu, need to clean up

    value = value.get_most_narrow()

    for k, i, v in _e_series_cache:
        if k == value and i == id(e_series):
            return F.Set(v)

    if isinstance(value, F.Constant):
        value = F.Range(value)
    elif isinstance(value, F.Set):
        raise NotImplementedError
    elif isinstance(value, (F.Operation, F.TBD)):
        raise ParamNotResolvedError()
    elif isinstance(value, F.ANY):
        # TODO
        raise ParamNotResolvedError()

    assert isinstance(value, F.Range)

    min_val = value.min
    max_val = value.max
    unit = 1

    if not isinstance(min_val, F.Constant) or not isinstance(max_val, F.Constant):
        # TODO
        raise Exception()

    min_val = min_val.value
    max_val = max_val.value

    if isinstance(min_val, Quantity):
        assert isinstance(max_val, Quantity)

        min_val_q = min_val.to_compact()

        unit = min_val_q.units
        max_val_q = max_val.to(unit)
        assert max_val_q.units == unit

        min_val: float = min_val_q.magnitude
        max_val: float = max_val_q.magnitude

    assert isinstance(min_val, (float, int)) and isinstance(max_val, (float, int))

    # TODO ugly
    if max_val == math.inf:
        max_val = min_val * 10e3

    e_series_values = repeat_set_over_base(
        e_series, 10, range(floor(log10(min_val)), ceil(log10(max_val)) + 1)
    )
    out = value & {e * unit for e in e_series_values}
    _e_series_cache.append((copy.copy(value), id(e_series), out.params))
    return out


def e_series_discretize_to_nearest(
    value: Parameter, e_series: E_SERIES = E_SERIES_VALUES.E_ALL
) -> F.Constant:
    if not isinstance(value, (F.Constant, F.Range)):
        raise NotImplementedError

    target = value.value if isinstance(value, F.Constant) else sum(value.as_tuple()) / 2

    e_series_values = repeat_set_over_base(
        e_series, 10, range(floor(log10(target)), ceil(log10(target)) + 1)
    )

    return F.Constant(min(e_series_values, key=lambda x: abs(x - target)))


def e_series_ratio(
    RH: Parameter,
    RL: Parameter,
    output_input_ratio: Parameter,
    e_values: E_SERIES = E_SERIES_VALUES.E_ALL,
) -> Tuple[float, float]:
    """
    Calculates the values for two components in the E series range which are bound by a
    ratio.

    RH and RL define the contstraints for the components, and output_input_ratio is the
    output/input voltage ratio as defined below.
    RH and output_input_ratio must be constrained to a range or constant, but RL can be
    ANY.

    output_input_ratio = RL/(RH + RL)
    RL/oir = RH + RL
    RL * (1/oir -1) = RH
    RL = RH / (1/oir -1)

    Returns a tuple of RH/RL values.

    Can be used for a resistive divider.
    """

    if (
        not isinstance(RH, (F.Constant, F.Range))
        or not isinstance(RL, (F.Constant, F.Range, F.ANY))
        or not isinstance(output_input_ratio, (F.Constant, F.Range))
    ):
        raise NotImplementedError

    if not output_input_ratio.is_subset_of(F.Range(0, 1)):
        raise ValueError("Invalid output/input voltage ratio")

    rh = F.Range(RH.value, RH.value) if isinstance(RH, F.Constant) else RH
    rl = F.Range(RL.value, RL.value) if isinstance(RL, F.Constant) else RL
    oir = (
        F.Range(output_input_ratio.value, output_input_ratio.value)
        if isinstance(output_input_ratio, F.Constant)
        else output_input_ratio
    )

    rh_values = e_series_intersect(rh, e_values)
    rl_values = e_series_intersect(rl, e_values) if isinstance(rl, F.Range) else None

    target_ratio = oir.as_center_tuple()[0]

    solutions = []

    for rh_val in rh_values.params:
        rl_ideal = rh_val / (F.Constant(1) / target_ratio - 1)

        rl_nearest_e_val = (
            min(rl_values.params, key=lambda x: abs(x - rl_ideal))
            if rl_values
            else e_series_discretize_to_nearest(rl_ideal, e_values)
        )
        real_ratio = rl_nearest_e_val / (rh_val + rl_nearest_e_val)

        solutions.append((real_ratio, (rh_val, rl_nearest_e_val)))

    optimum = min(solutions, key=lambda x: abs(x[0] - target_ratio))

    logger.debug(
        f"{target_ratio=}, {optimum[0]=}, {oir}, "
        f"error: {abs(optimum[0]/ target_ratio - 1)*100:.4f}%"
    )

    if optimum[0] not in oir:
        raise ArithmeticError(
            "Calculated optimum RH RL value pair gives output/input voltage ratio "
            "outside of specified range. Consider relaxing the constraints"
        )

    return optimum[1]
