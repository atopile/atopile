"""
Generate a report based on assertions made in the source code.
"""

import logging
from enum import Enum
from typing import Any

import rich
from rich.style import Style
from rich.table import Table

from atopile import address, config, errors, instance_methods, datatypes
from atopile.front_end import RangedValue, lofty, Instance

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


class _Context:
    def __init__(self, ctx: Instance) -> None:
        self.ctx = ctx
        self._cache = {}
        super().__init__()

    def __getitem__(self, key: datatypes.Ref) -> Any:
        if key in self._cache:
            return self._cache[key]

        parent_inst = self.ctx
        for k in key[:-1]:
            if k not in parent_inst.children:
                raise errors.AtoKeyError(f"No instance '{k}' in '{parent_inst.addr}'")
            parent_inst = parent_inst.children[k]
        assign_name = key[-1]

        if assign_name not in parent_inst.assignments:
            raise errors.AtoKeyError(
                f"No attribute '{assign_name}' bound on '{parent_inst.addr}'"
            )

        assignment = parent_inst.assignments[assign_name][0]
        if assignment.value is None:
            raise errors.AtoTypeError(f"'{key}' is declared, but no value is defined.")

        self._cache[key] = assignment.value
        return assignment.value


def generate_assertion_report(build_ctx: config.BuildContext):
    """
    Generate a report based on assertions made in the source code.
    """
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Status")
    table.add_column("Assertion")
    table.add_column("Numeric")
    table.add_column("Address")
    table.add_column("Notes")

    rows = 0

    def _add_row(
        status: AssertionStatus,
        assertion_str: str,
        numeric: str,
        addr: address.AddrStr,
        notes: str,
    ):
        nonlocal rows
        table.add_row(
            status.value,
            assertion_str,
            numeric,
            address.get_instance_section(addr),
            notes,
            style=dark_row if rows % 2 else light_row,
        )
        rows += 1


    for instance_addr in instance_methods.all_descendants(build_ctx.entry):
        instance = lofty.get_instance(instance_addr)
        context = _Context(instance)
        for assertion in instance.assertions:
            try:
                a = assertion.lhs(context)
                b = assertion.rhs(context)
            except errors.AtoError as e:
                _add_row(AssertionStatus.ERROR, str(assertion), "", instance_addr, str(e))
                continue

            if _do_op(a, assertion.operator, b):
                status = AssertionStatus.PASSED
            else:
                status = AssertionStatus.FAILED

            numeric = str(a) + " " + assertion.operator + " " + str(b)

            _add_row(status, str(assertion), numeric, instance_addr, "")

    rich.print(table)


def _do_op(a: RangedValue, op: str, b: RangedValue) -> bool:
    """Perform the operation specified by the operator."""
    if op == "within":
        return a.within(b)
    elif op == "<":
        return a < b
    elif op == ">":
        return a > b
    else:
        raise ValueError(f"Unrecognized operator: {op}")
