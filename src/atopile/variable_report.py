"""
Generate a report based on assertions made in the source code.
"""

import logging

import rich
from rich.style import Style
from rich.table import Table

from atopile import address, config, instance_methods, parse_utils

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
        log.debug("Generating report for %s", addr)
        instance = instance_methods.get_instance(addr)
        for key, assignments in instance.assignments.items():
            assert len(assignments) > 0

            # If it's merely an assigned value, ignore and continue
            if not assignments[0].value_is_derived:
                continue

            value = str(assignments[0].value) or ""

            comment = ""
            for assignment in assignments:
                if hasattr(assignment, "src_ctx"):
                    if assignment.src_ctx:
                        comment = parse_utils.get_comment_from_token(assignment.src_ctx.stop) or ""
                    break

            k_addr = address.get_instance_section(address.add_instance(addr, key))
            report.add(k_addr, value, comment)

    rich.print(report)
