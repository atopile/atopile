# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# TODO replace with pint or something

from faebryk.libs.util import round_str

k = 1000
M = 1000_000
G = 1000_000_000

n = 0.001 * 0.001 * 0.001
u = 0.001 * 0.001
m = 0.001

si_prefixes = {
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "µ": 1e-6,
    "m": 1e-3,
    "%": 0.01,
    "": 1,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
    "P": 1e15,
}


def si_str_to_float(si_value: str) -> float:
    """
    Convert a string with SI prefix and unit to a float.
    """

    prefix = ""
    value = si_value.replace("u", "µ")

    while value[-1].isalpha():
        prefix = value[-1]
        value = value[:-1]

    if prefix in si_prefixes:
        return float(value) * si_prefixes[prefix]

    return float(value)


def float_to_si_str(value: float, unit: str, num_decimals: int = 2) -> str:
    """
    Convert a float to a string with SI prefix and unit.
    """
    if value == float("inf"):
        return "∞" + unit
    elif value == float("-inf"):
        return "-∞" + unit

    res_factor = 1
    res_prefix = ""
    for prefix, factor in si_prefixes.items():
        if abs(value) >= factor:
            res_prefix = prefix
            res_factor = factor
        else:
            break

    value_str = round_str(value / res_factor, num_decimals)

    return value_str + res_prefix + unit
