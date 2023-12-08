"""
This is a terminal target that will generate BoMs
"""

import csv
import logging
from io import StringIO
from typing import Optional
from collections import OrderedDict
import natsort

import rich
from rich.table import Table
from toolz import groupby

import atopile.components
from atopile import address
from atopile.instance_methods import all_descendants, match_components

log = logging.getLogger("build.bom")


def _get_mpn(addr: address.AddrStr) -> Optional[str]:
    """
    Return the MPN for a component, or None of it's unavailable
    """
    try:
        return atopile.components.get_mpn(addr)
    except KeyError:
        log.error("No MPN for for %s", addr)
        return None


def _default_to_none(func, addr):
    try:
        return func(addr)
    except KeyError:
        return "None"


def generate_designator_map(entry_addr: address.AddrStr) -> str:
    """Generate a map between the designator and the component name"""

    if address.get_instance_section(entry_addr):
        raise ValueError("Cannot generate a BoM for an instance address.")

    all_components = list(filter(match_components, all_descendants(entry_addr)))

    COLUMNS = ["Name", "Des", "Name", "Des"]

    # Create tables to print to the terminal and to the disc
    console_table = Table(show_header=True, header_style="bold green")
    console_table.add_column("des", justify="right")
    console_table.add_column("name", justify="left")
    console_table.add_column("name", justify="right")
    console_table.add_column("des", justify="left")

    csv_table = StringIO()
    writer = csv.DictWriter(csv_table, fieldnames=COLUMNS)
    writer.writeheader()

    # Populate the tables
    sorted_designator_dict = {}
    sorted_comp_name_dict = {}
    for component in all_components:
        c_des = _default_to_none(atopile.components.get_designator, component)
        c_name = _default_to_none(address.get_instance_section, component)
        sorted_designator_dict[c_des] = c_name
        sorted_comp_name_dict[c_name] = c_des

    sorted_designator_dict = OrderedDict(
        natsort.natsorted(sorted_designator_dict.items())
    )
    sorted_comp_name_dict = OrderedDict(sorted(sorted_comp_name_dict.items()))

    for (s_des, n_comp), (s_comp, n_des) in zip(
        sorted_designator_dict.items(), sorted_comp_name_dict.items()
    ):
        console_table.add_row(s_des, n_comp, s_comp, n_des)

    # Print the table
    rich.print(console_table)


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

    # Help to fill both tables
    def _add_row(value, designator, footprint, mpn):
        writer.writerow(
            {
                "Comment": value,
                "Designator": designator,
                "Footprint": footprint,
                "LCSC": mpn,
            }
        )
        console_table.add_row(value, designator, footprint, mpn)

    # Populate the tables
    for mpn, components_in_group in bom.items():
        if not mpn:
            continue  # skip

        # representative component
        component = components_in_group[0]

        _add_row(
            _default_to_none(atopile.components.get_value, component),
            _default_to_none(atopile.components.get_designator, component),
            _default_to_none(atopile.components.get_footprint, component),
            mpn,
        )

    # Print the table
    rich.print(console_table)

    # Return the CSV
    return csv_table.getvalue()
