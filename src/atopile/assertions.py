"""
Generate a report based on assertions made in the source code.
"""

import logging
from enum import Enum

import rich
from rich.style import Style
from rich.table import Table

from atopile import address, config, errors
from atopile.front_end import Instance, RangedValue, Assertion, lofty
from atopile.instance_methods import all_descendants
from numbers import Number

# import natsort
# from toolz import groupby

log = logging.getLogger(__name__)

light_row = Style(color="bright_black")
dark_row = Style(color="white")


class AssertionStatus(Enum):
    """
    The status of an assertion.
    """

    PASSED = "[green]Passed[/]"
    FAILED = "[red]Failed[/]"
    ERROR = "[red]Error[/]"


def generate_assertion_report(build_ctx: config.BuildContext):
    """
    Generate a report based on assertions made in the source code.
    """
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Status")
    table.add_column("Assertion")
    table.add_column("Numeric")
    table.add_column("Address")
    # table.add_column("Notes")

    rows = 0

    def _add_row(
        status: AssertionStatus,
        assertion_str: str,
        numeric: str,
        addr: address.AddrStr,
        notes: str
    ):
        nonlocal rows
        table.add_row(
            status.value,
            assertion_str,
            numeric,
            address.get_instance_section(addr),
            # notes,
            style=dark_row if rows % 2 else light_row,
        )
        rows += 1


    def _check_assertion(instance: Instance, assertion: Assertion) -> AssertionStatus:
        """
        Check an assertion.
        """
        stmt = assertion.assertion_str

        ops = _which_operators(stmt)
        if len(ops) != 1:
            raise ValueError(
                f"Statement must contain exactly one of the following operators: {OPERATORS}"
            )

        op = ops[0]
        expr_str, bounds_str = stmt.split(op)

        context = _get_context(instance)

        try:
            # This is split in two due to the "within" operator
            expr = eval(expr_str, context)
            bounds = eval(bounds_str, context)
        except (NameError, AttributeError) as ex:
            raise errors.AtoKeyError(f"NameError: {ex}") from ex
            # Hacking some mildly better exceptions since the
            # parser currently doesn't actually, well, parse
            # the expressions in assertions.
            # dotted_path = ex.name.split(".")

            # TODO:
            # 1. Check if something's declared, but not defined
            # 2. If it's not defined or declared, at least convert
            # it to an ato error and re-raise as an ato error
            # if len(dotted_path) == 1:
            #     final_instance = instance
            # try:
            #     final_instance = _follow_the_dots(context, dotted_path[:-1])
            # except AttributeError:
            #     raise

        if _do_op(op, expr, bounds):
            status = AssertionStatus.PASSED
        else:
            status = AssertionStatus.FAILED

        numeric = str(expr) + " " + op + " " + str(bounds)

        _add_row(status, assertion.assertion_str, numeric, instance_addr, "")


    for instance_addr in all_descendants(build_ctx.entry):
        instance = lofty.get_instance(instance_addr)
        for assertion in instance.assertions:
            # try:
            _check_assertion(instance, assertion)
            # except Exception as ex:
            #     log.error(  # pylint: disable=logging-fstring-interpolation
            #         f"Error checking assertion '{assertion}' at {instance_addr}: {ex}"
            #     )
            #     _add_row(AssertionStatus.ERROR, assertion, instance_addr, str(ex))

    rich.print(table)


OPERATORS = ["<", "<=", ">", ">=", "within"]


def _which_operators(stmt: str) -> list[str]:
    """Return which operator is being used by an assertion."""
    return [op for op in OPERATORS if op in stmt]


def _do_op(op: str, this: RangedValue, other: RangedValue) -> bool:
    """Perform the operation specified by the operator."""
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


class DotDict(dict):
    """A dict you can dot"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as ex:
            raise AttributeError(f"Attribute {name} not found", name) from ex


def _get_context(instance: Instance) -> dict:
    """
    Get the context for evaluating assertions.
    TODO: wtf is this? come on Matt
    """
    context = {}
    # Add assignments' values
    for k, a in instance.assignments.items():
        v = a[0].value
        if isinstance(v, (Number, RangedValue)):
            context[k] = v

    # Recurse through children
    for k, v in instance.children.items():
        context[k] = DotDict(_get_context(v))

    return context


def _follow_the_dots(start, dots: list[str]):
    current = start
    for dot in dots:
        current = current[dot]
    return current
