"""
Generate a report based on assertions made in the source code.
"""

import logging

import rich
from rich.style import Style
from rich.table import Table

from atopile import address, config, expressions, instance_methods, parse_utils

log = logging.getLogger(__name__)

light_row = Style(color="bright_black")
dark_row = Style(color="white")


class VariableReport(Table):
    def __init__(self) -> None:
        super().__init__(
            show_header=True, header_style="bold green", title="Variable Values"
        )

        self.add_column("Address")
        self.add_column("Value")
        self.add_column("Comment")

    def add(
        self,
        address: str,
        value: str,
        comment: str,
    ):
        super().add_row(
            address,
            value,
            comment,
            style=dark_row if len(self.rows) % 2 else light_row,
        )


def generate(build_ctx: config.BuildContext):
    """
    Generate a report of all the variables in the design
    """
    report = VariableReport()
    for addr in instance_methods.all_descendants(build_ctx.entry):
        instance = instance_methods.get_instance(addr)
        for key, assignments in instance.assignments.items():
            # Expressions always have always at least two assignments
            if len(assignments) < 2:
                continue

            # We're only out here to display the values of expressions
            if not isinstance(assignments[1].value, expressions.Expression):
                continue

            k_addr = address.get_instance_section(address.add_instance(addr, key))

            if isinstance(assignments[0].value, expressions.Expression):
                # There was not enough information to determine the value
                raw_value: expressions.Expression = assignments[0].value
                value = "Unknown. Missing variables:\n" + "\n".join(
                    address.get_instance_section(s.key) for s in raw_value.symbols
                )
            else:
                # There was sufficent information to determine the value
                value = str(assignments[0].value)
            src_ctx = assignments[1].src_ctx
            if src_ctx:
                comment = parse_utils.get_comment_from_token(src_ctx.stop) or ""
            else:
                comment = ""

            report.add(k_addr, value, comment)

    rich.print(report)
