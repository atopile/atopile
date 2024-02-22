"""
This is a terminal target that will generate BoMs
"""

import csv
import itertools
import logging
from collections import OrderedDict
from io import StringIO

import natsort
import rich
from rich.style import Style
from rich.table import Table
from toolz import groupby

from atopile import address, errors, components
from atopile.instance_methods import all_descendants, match_components

log = logging.getLogger(__name__)


# These functions are used to downgrade the errors to warnings.
# Those warnings are logged and the default value is returned.
_get_mpn = errors.downgrade(
    components.get_mpn, (components.MissingData, components.NoMatchingComponent)
)


def _get_footprint(addr: address.AddrStr) -> str:
    """
    Footprint is a misnomer - it's really a hint to the user

    Firstly, it tried to use the footprint
    Then it attempts to use the package
    Finally, it'll fallback to a question mark "?"
    """
    if value := errors.downgrade(
        components.get_package,
        components.MissingData
    )(addr):
        return value

    if value := errors.downgrade(
        components.get_footprint,
        components.MissingData
    )(addr):
        return value

    return "?"


def _get_value(addr: address.AddrStr) -> str:
    value = errors.downgrade(
        components.get_user_facing_value,
        (components.MissingData, components.NoMatchingComponent)
    )(addr)

    if value is not None:
        return value

    value = str(errors.downgrade(
        components.get_specd_value, components.MissingData
    )(addr))

    if value is not None:
        return value

    return "?"


light_row = Style(color="bright_black")
dark_row = Style(color="white")


def generate_designator_map(entry_addr: address.AddrStr) -> str:
    """Generate a map between the designator and the component name"""

    if address.get_instance_section(entry_addr):
        raise ValueError("Cannot generate a BoM for an instance address.")

    all_components = list(filter(match_components, all_descendants(entry_addr)))

    # Create tables to print to the terminal and to the disc
    sorted_des_table = Table(show_header=True, header_style="bold green")
    sorted_des_table.add_column("Designator ↓", justify="right")
    sorted_des_table.add_column("Name", justify="left")

    sorted_name_table = Table(show_header=True, header_style="bold green")
    sorted_name_table.add_column("Name ↓", justify="left")
    sorted_name_table.add_column("Designator", justify="left")

    # Populate the tables
    sorted_designator_dict = {}
    sorted_comp_name_dict = {}
    for component in all_components:
        c_des = components.get_designator(component)
        c_name = address.get_instance_section(component)
        sorted_designator_dict[c_des] = c_name
        sorted_comp_name_dict[c_name] = c_des

    sorted_designator_dict = OrderedDict(
        natsort.natsorted(sorted_designator_dict.items())
    )
    sorted_comp_name_dict = OrderedDict(sorted(sorted_comp_name_dict.items()))

    for row_index, (s_des, n_comp) in enumerate(sorted_designator_dict.items()):
        sorted_des_table.add_row(
            s_des, n_comp, style=dark_row if row_index % 2 else light_row
        )
    for row_index, (s_comp, n_des) in enumerate(sorted_comp_name_dict.items()):
        sorted_name_table.add_row(
            s_comp, n_des, style=dark_row if row_index % 2 else light_row
        )

    # Print the table
    rich.print(sorted_des_table)
    rich.print(sorted_name_table)


def generate_bom(entry_addr: address.AddrStr) -> str:
    """Generate a BoM for the and print it to a CSV."""

    if address.get_instance_section(entry_addr):
        raise ValueError("Cannot generate a BoM for an instance address.")

    all_components = list(filter(match_components, all_descendants(entry_addr)))
    bom = groupby(_get_mpn, all_components)

    # JLC format: Comment (whatever might be helpful) Designator Footprint LCSC
    COLUMNS = ["Comment", "Designator", "Footprint", "LCSC"]

    # Create tables to print to the terminal and to the disc
    console_table = Table(show_header=True, header_style="bold magenta")
    for column in COLUMNS:
        console_table.add_column(column)

    csv_table = StringIO()
    writer = csv.DictWriter(csv_table, fieldnames=COLUMNS)
    writer.writeheader()

    bom_row_nb_counter = itertools.count()

    # Help to fill both tables
    def _add_row(value, designator, footprint, mpn):
        row_nb = next(bom_row_nb_counter)
        writer.writerow(
            {
                "Comment": value,
                "Designator": designator,
                "Footprint": footprint,
                "LCSC": mpn,
            }
        )
        console_table.add_row(
            value,
            designator,
            footprint,
            mpn,
            style=dark_row if row_nb % 2 else light_row,
        )

    # Populate the tables
    for mpn, components_in_group in bom.items():
        if mpn:
            # representative component
            component = components_in_group[0]

            friendly_designators = ",".join(
                components.get_designator(component)
                for component in components_in_group
            )

            _add_row(
                _get_value(component),
                friendly_designators,
                _get_footprint(component),
                mpn,
            )
        else:
            # for components without an MPN, we add a row for each component
            # this way the user can manually add the MPN as they see fit
            for component in components_in_group:
                _add_row(
                    _get_value(component),
                    components.get_designator(component),
                    _get_footprint(component),
                    "?",
                )

    # Print the table
    rich.print(console_table)

    # Return the CSV
    return csv_table.getvalue()
