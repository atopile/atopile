"""
This module contains functions for interacting with layout data,
and generating files required to reuse layouts.

Thanks @nickkrstevski (https://github.com/nickkrstevski) for
the heavy lifting on this one!
"""


import csv
import glob
from io import StringIO
from pathlib import Path
from collections import defaultdict

import yaml

from atopile import address, components, config
from atopile.instance_methods import (
    all_descendants,
    find_matching_super,
    match_components,
    match_modules,
)


def find_packages_with_layouts() -> dict[str, dict[str, Path]]:
    """
    Return a dict of all the known entry points of dependencies in the project.
    The dict maps the entry point's address to another map of the entry point's
    build name and the layout file path.
    """
    directory = config.get_project_context().project_path
    pattern = f"{directory}/.ato/modules/*/ato.yaml"

    entries = defaultdict(dict)
    for filepath in glob.glob(pattern):
        cfg = config.get_project_config_from_path(filepath)

        for build_name in cfg.builds:
            ctx = config.BuildContext.from_config(cfg, build_name)
            entries[ctx.entry][build_name] = {
                "layout": Path(ctx.layout_path),
            }

    return entries


def generate_module_map(entry_addr: address.AddrStr) -> StringIO:
    """Generate a CSV file containing a list of all the modules and their components in the project."""
    csv_table = StringIO()
    writer = csv.DictWriter(csv_table, fieldnames=["Package", "PackageInstance", "Name", "Designator"])
    writer.writeheader()

    packages_with_layouts = find_packages_with_layouts()
    modules = list(filter(match_modules, all_descendants(entry_addr)))

    for module in modules:
        package_type = find_matching_super(module, packages_with_layouts)
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
