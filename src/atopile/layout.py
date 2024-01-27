"""
This module contains functions for interacting with layout data,
and generating files required to reuse layouts.

Thanks @nickkrstevski (https://github.com/nickkrstevski) for
the heavy lifting on this one!
"""


import csv
import glob
from io import StringIO

import yaml

from atopile import address, config, components
from atopile.instance_methods import (
    all_descendants,
    find_matching_super,
    match_components,
    match_modules,
)


def descend_entry_points():
    entries = []
    directory = config.get_project_context().project_path
    pattern = f"{directory}/.ato/modules/**/ato.yaml"

    # Use glob to find all 'ato.yaml' files in the directory and its subdirectories
    for filepath in glob.glob(pattern, recursive=True):
        # Open and parse the YAML file
        with open(filepath, 'r') as file:
            try:
                data = yaml.safe_load(file)
                # Check if 'entry' is in the 'builds' -> 'default' section
                entry = data.get('builds', {}).get('default', {}).get('entry')
                if entry:
                    entries.append(entry)
            except yaml.YAMLError as exc:
                print(f"Error parsing YAML file {filepath}: {exc}")

    return entries


def generate_module_map(entry_addr: address.AddrStr) -> StringIO:
    """Generate a CSV file containing a list of all the modules and their components in the project."""
    csv_table = StringIO()
    writer = csv.DictWriter(csv_table, fieldnames=["Package", "PackageInstance", "Name", "Designator"])
    writer.writeheader()

    package_names = list(address.get_entry_section(p) for p in descend_entry_points())
    modules = list(filter(match_modules, all_descendants(entry_addr)))

    for module in modules:
        package_type = find_matching_super(module, package_names)
        if package_type:
            package_type = package_type.split(":")[0].split('/')[-2]
            for comp_addr in filter(match_components, all_descendants(module)):
                writer.writerow(
                    {
                        "Package": package_type,  # The path to the module/entry point - it's hard to tell
                        "PackageInstance": address.get_instance_section(module),  # The instance path of the module in the project
                        "Name": address.get_instance_section(comp_addr),  # The instance path of the component in the project
                        "Designator": components.get_designator(comp_addr),  # The designator of the component
                    }
                )

    return csv_table.getvalue()
