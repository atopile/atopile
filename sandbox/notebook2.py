# %%

import pint
from atopile.front_end import Base
from attr import define
from typing import Optional
from itertools import combinations, permutations
from numbers import Number
from atopile.ranged_value import RangedValue


v_in = RangedValue(10, 12, pint.Unit("V"))
r_top_value = RangedValue(0.99, 1.01, pint.Unit("Ω"))
r_bot_value = RangedValue(0.99, 1.01, pint.Unit("Ω"))
v_out = RangedValue(5, 10, pint.Unit("V"))

# %%
a = v_in * r_bot_value / (r_top_value + r_bot_value)

# %%
assertions = [
    "v_in * r_bot_value / (r_top_value + r_bot_value) within v_out"
]
operators = ["<", "<=", ">", ">=", "within"]

def which_operators(stmt: str) -> list[str]:
    return [op for op in operators if op in stmt]

def do_op(op: str, this: RangedValue, other: RangedValue) -> bool:
    if op == "within":
        return this.within(other)
    elif op == "<":
        return this < other
    elif op == "<=":
        return this <= other
    elif op == ">":
        return this > other
    elif op == ">=":
        return this >= other
    else:
        raise ValueError(f"Unrecognized operator: {op}")

# %%
def test_assertion(stmt: str, context: dict) -> bool:
    ops = which_operators(stmt)
    if len(ops) != 1:
        raise ValueError(f"Statement must contain exactly one of the following operators: {operators}")

    op = ops[0]
    expr_str, bounds_str = stmt.split(op)

    expr = eval(expr_str, context)
    bounds = eval(bounds_str, context)

    return do_op(op, expr, bounds)

# %%
test_assertion("v_in * r_bot_value / (r_top_value + r_bot_value) within v_out", locals())

# %%
