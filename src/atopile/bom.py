"""
This is a terminal target that will generate BoMs
"""

import csv
import itertools
import logging
from collections import OrderedDict, defaultdict
from io import StringIO
from typing import Optional

import natsort
import rich
from rich.table import Table
from toolz import groupby

import atopile.components
from atopile import address
from atopile.components import (
    get_capacitor_lcsc,
    get_component_data_by_lscs,
    get_resistor_lcsc,
)
from atopile.instance_methods import all_descendants, match_components


log = logging.getLogger(__name__)


GENERIC_RESISTOR = 'generic_resistor'
GENERIC_CAPACITOR = 'generic_capacitor'

GENERICS_KEYS = [GENERIC_RESISTOR, GENERIC_CAPACITOR]

def _get_mpn(addr: address.AddrStr) -> Optional[str]:
    """
    Return the MPN for a component, or None of it's unavailable
    """
    try:
        mpn = atopile.components.get_mpn(addr)
    except KeyError:
        log.warning("No MPN for for %s", addr)
        return None
    return mpn


def _default_to(func, addr, default):
    try:
        return func(addr)
    except KeyError:
        name = func.__name__.split("_")[-1]
        log.warning("No %s for for %s", name, addr)
        return default


def generate_designator_map(entry_addr: address.AddrStr) -> str:
    """Generate a map between the designator and the component name"""

    if address.get_instance_section(entry_addr):
        raise ValueError("Cannot generate a BoM for an instance address.")

    all_components = list(filter(match_components, all_descendants(entry_addr)))

    # Create tables to print to the terminal and to the disc
    console_table = Table(show_header=True, header_style="bold green")
    console_table.add_column("Des", justify="right")
    console_table.add_column("Name", justify="left")
    console_table.add_column("Name", justify="left")
    console_table.add_column("Des", justify="left")

    # Populate the tables
    sorted_designator_dict = {}
    sorted_comp_name_dict = {}
    for component in all_components:
        c_des = atopile.components.get_designator(component)
        c_name = address.get_instance_section(component)
        sorted_designator_dict[c_des] = c_name
        sorted_comp_name_dict[c_name] = c_des

    sorted_designator_dict = OrderedDict(
        natsort.natsorted(sorted_designator_dict.items())
    )
    sorted_comp_name_dict = OrderedDict(sorted(sorted_comp_name_dict.items()))

    for row_index, ((s_des, n_comp), (s_comp, n_des)) in enumerate(zip(
        sorted_designator_dict.items(), sorted_comp_name_dict.items()
    )):
        if row_index % 2 == 0:
            console_table.add_row(
                f"[bright_black]{s_des}[/bright_black]",
                f"[bright_black]{n_comp}[/bright_black]",
                f"[bright_black]{s_comp}[/bright_black]",
                f"[bright_black]{n_des}[/bright_black]")
        else:
            console_table.add_row(
                f"[white]{s_des}[/white]",
                f"[white]{n_comp}[/white]",
                f"[white]{s_comp}[/white]",
                f"[white]{n_des}[/white]")

    # Print the table
    rich.print(console_table)


#TODO: currently a hack until we develop the required infrastructure
footprint_to_package_map = {
    "R01005" : "01005",
    "R0201" : "0201",
    "R0402" : "0402",
    "R0603" : "0603",
    "R0805" : "0805",
    "C01005" : "01005",
    "C0201" : "0201",
    "C0402" : "0402",
    "C0603" : "0603",
    "C0805" : "0805",
    "C1206" : "1206",
}

def _strip_letter_if_r_or_f(s):
    if s.endswith(('R', 'F', 'r', 'f')):
        return s[:-1]
    return s

def _parse_number_string(s):
    s = _strip_letter_if_r_or_f(s)
    multipliers = {
        'k': 1000,
        'M': 1000000,
        'm': 0.001,
        'u': 0.000001,
        'n': 0.000000001,
        'p': 0.000000000001,
    }

    if s[-1].isdigit():  # Check if the last character is a digit
        return float(s)
    else:
        # Extract the number and the multiplier
        number, multiplier = s[:-1], s[-1].lower()
        return float(float(number) * multipliers.get(multiplier, 1))

def _fetch_suggested_lcsc(key, value, footprint) -> Optional[str]:
    # See if the footprint can be processed
    try:
        lib_package = footprint_to_package_map[footprint]
    except Exception:  # pylint: disable=broad-except
        log.warning(f"LCSC resolver can't handle {footprint}")
        return None

    # process the format of the value 10uF -> 0.01
    processed_value = _parse_number_string(value)

    # try find a matching lcsc number with hard coded +-5% tolerance
    if key == GENERIC_RESISTOR:
        tentative_lcsc_pn = get_resistor_lcsc(processed_value * 0.95, processed_value * 1.05, lib_package)

    elif key == GENERIC_CAPACITOR:
        tentative_lcsc_pn = get_capacitor_lcsc(processed_value * 0.95, processed_value * 1.05, lib_package)

    else:
        return None

    if tentative_lcsc_pn:
        return tentative_lcsc_pn[0]
    else:
        return None

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
        if row_nb % 2 == 0:
            console_table.add_row(f"[bright_black]{value}[/bright_black]", f"[bright_black]{designator}[/bright_black]", f"[bright_black]{footprint}[/bright_black]", f"[bright_black]{mpn}[/bright_black]")
        else:
            console_table.add_row(f"[white]{value}[/white]", f"[white]{designator}[/white]", f"[white]{footprint}[/white]", f"[white]{mpn}[/white]")

    # Populate the tables
    for mpn, components_in_group in bom.items():
        # if the component is a generic component, we can try populate it automatically
        if mpn in GENERICS_KEYS:
            generated_lcsc_dict = defaultdict(list)
            failed_generation = []
            for component in components_in_group:
                found_lcsc = _fetch_suggested_lcsc(mpn, atopile.components.get_value(component), atopile.components.get_footprint(component))
                if found_lcsc:
                    generated_lcsc_dict[found_lcsc].append(component)
                else:
                    failed_generation.append(component)
                    log.warning("Could not generate LCSC for %s", component)
            for lcsc_pn, components in generated_lcsc_dict.items():
                _add_row(
                    str(get_component_data_by_lscs(lcsc_pn)['value']) + ' ' + str(get_component_data_by_lscs(lcsc_pn)['unit']),
                    ",".join([_default_to(atopile.components.get_designator, component, "<empty>") for component in components]),
                    _default_to(atopile.components.get_footprint, component, "<empty>"),
                    lcsc_pn,
                )

            for component in failed_generation:
                _add_row(
                    _default_to(atopile.components.get_value, component, ""),
                    _default_to(atopile.components.get_designator, component, "<empty>"),
                    _default_to(atopile.components.get_footprint, component, "<empty>"),
                    "<empty>",
                )
        elif not mpn:
            # for components without an MPN, we add a row for each component
            # this way the user can manually add the MPN as they see fit
            for component in components_in_group:
                _add_row(
                    _default_to(atopile.components.get_value, component, ""),
                    _default_to(atopile.components.get_designator, component, "<empty>"),
                    _default_to(atopile.components.get_footprint, component, "<empty>"),
                    "<empty>",
                )
        else:
            # representative component
            component = components_in_group[0]

            friendly_designators = ",".join(
                _default_to(atopile.components.get_designator, component, "?")
                for component in components_in_group
            )

            _add_row(
                _default_to(atopile.components.get_value, component, ""),
                friendly_designators,
                _default_to(atopile.components.get_footprint, component, "<empty>"),
                mpn,
            )

    # Print the table
    rich.print(console_table)

    # Return the CSV
    return csv_table.getvalue()
