"""
This module contains functions for interacting with layout data,
and generating files required to reuse layouts.

Thanks @nickkrstevski (https://github.com/nickkrstevski) for
the heavy lifting on this one!
"""

import copy
import hashlib
import json
import logging
import uuid
from pathlib import Path
from typing import TypedDict

from more_itertools import first

import faebryk.library._F as F
import faebryk.libs.exceptions
from atopile import errors, front_end
from atopile.address import AddressError, AddrStr
from atopile.config import ProjectConfig, config
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.libs.util import (
    FuncDict,
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    find,
    get_module_from_path,
)

logger = logging.getLogger(__name__)


def _generate_uuid_from_string(path: str) -> str:
    """Spits out a uuid in hex from a string"""
    path_as_bytes = path.encode("utf-8")
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return str(uuid.UUID(bytes=hashed_path))


def _index_module_layouts() -> FuncDict[type[Module], set[Path]]:
    """Find, tag and return a set of all the modules with layouts."""
    directory = config.project.paths.root

    entries: FuncDict[type[Module], set[Path]] = FuncDict()
    ato_modules = front_end.bob.modules

    for filepath in directory.glob("**/ato.yaml"):
        with faebryk.libs.exceptions.downgrade(Exception, logger=logger):
            project_config = ProjectConfig.from_path(filepath.parent)

            if project_config is None:
                raise faebryk.libs.exceptions.UserResourceException(
                    f"Failed to load module config: {filepath}"
                )

            for build in project_config.builds.values():
                with faebryk.libs.exceptions.downgrade(Exception, logger=logger):
                    try:
                        entry_section = build.entry_section
                    except AddressError:
                        # skip builds with no entry, e.g. generics
                        # config validation happens before this point
                        continue

                    # Check if the module is a known python module
                    if (
                        class_ := get_module_from_path(
                            build.entry_file_path,
                            entry_section,
                            # we might have duplicates from different builds
                            allow_ambiguous=True,
                        )
                    ) is not None:
                        # we only bother to index things we've imported,
                        # otherwise we can be sure they weren't used
                        assert isinstance(class_, type)
                        entries.setdefault(class_, set()).add(build.paths.layout)

                    # Check if the module is a known ato module
                    elif class_ := ato_modules.get(
                        # This is the address w/ an absolute path to the entry file
                        # which is the format also used by the frontend to key modules
                        AddrStr.from_parts(build.entry_file_path, build.entry_section)
                    ):
                        entries.setdefault(class_, set()).add(build.paths.layout)

    return entries


class ModuleMap(TypedDict):
    layout_path: str
    """Absolute path to the KiCAD layout file"""

    uuid_to_addr_map: dict[str, str]
    """Map of UUIDs, as expected in the layout, to addresses"""

    addr_map: dict[str, str]
    """Map of addresses in the parent module to addresses in the child module"""

    group_components: list[str]
    """List of components in the group"""

    nested_groups: list[str]
    """List of addresses of nested groups"""


def generate_module_map(app: Module) -> None:
    """Generate a file containing a list of all the modules and their components in the build."""  # noqa: E501  # pre-existing
    module_map: dict[str, ModuleMap] = {}

    module_layouts = _index_module_layouts()

    for module, trait in GraphFunctions(app.get_graph()).nodes_with_trait(
        F.has_reference_layout
    ):
        assert isinstance(module, Module)
        module_layouts.setdefault(type(module), set()).update(trait.paths)

    def _dfs_layouts(module_instance: Module) -> tuple[list[str], set[str]]:
        """
        Pre-order DFS of the module's layout tree
        Returns:
            - a list of addresses of nested groups
            - a set of addresses of child components
        """
        nested_groups: list[str] = []
        child_component_addrs: set[str] = set()

        # FIXME: this was created for nested grouping, however it was too much effort
        # to support this in KiCAD, so we're ignoring it for now
        def _descend() -> None:
            for child_instance in module_instance.get_children_modules(
                types=Module, direct_only=True
            ):
                ngs, cca = _dfs_layouts(child_instance)
                nested_groups.extend(ngs)
                child_component_addrs.update(cca)

        try:
            # TODO: this could be improved if we had the mro of the module
            module_super = find(
                module_layouts.keys(), lambda x: isinstance(module_instance, x)
            )
        except KeyErrorNotFound:
            # For now, only descend if there isn't a layout for this module
            # This means we'll only get the top-level group
            _descend()

        except KeyErrorAmbiguous as e:
            raise errors.UserNotImplementedError(
                "There are multiple build configurations for this module.\n"
                "We don't currently support multiple layouts for the same module."
                "Show the issue some love to get it done: https://github.com/atopile/atopile/issues/399"
            ) from e

        else:
            # Build up a map of UUIDs of the children of the module
            # The keys are instance UUIDs and the values are the
            # corresponding UUIDs in the layout
            # Here we include everything, even if accounted for by a nested group
            uuid_map = {}
            addr_map = {}
            for inst_child in module_instance.get_children_modules(types=Module):
                if not inst_child.has_trait(F.has_footprint):
                    continue

                parent_addr = inst_child.get_full_name()
                # This is a bit of a hack that makes assumptions based on the addressing
                # scheme to get the child's address w/r/t to it's root module
                child_addr = inst_child.relative_address(module_instance)

                addr_map[parent_addr] = child_addr

                for addr in (parent_addr, child_addr):
                    uuid_map[_generate_uuid_from_string(addr)] = addr

            # Add the module map to the module map
            group_name = module_instance.relative_address(app)
            ungrouped_footprints = set(addr_map.keys()) - child_component_addrs

            module_map[group_name] = {
                "layout_path": str(first(module_layouts[module_super])),
                # This maps the UUIDs of footprints to their addresses
                # for compatibility with the old layouts
                # TODO: @v0.4 remove this
                "uuid_to_addr_map": uuid_map,
                "addr_map": addr_map,
                "group_components": list(ungrouped_footprints),
                "nested_groups": copy.copy(nested_groups),
            }

            # Reset the nested_groups here to add only next-of-kin
            nested_groups = [group_name]
            child_component_addrs.update(ungrouped_footprints)

        return nested_groups, child_component_addrs

    # Run the DFS on the root module
    # We add an additional loop at the top here to avoid creating a top-level group
    for child_instance in app.get_children_modules(types=Module, direct_only=True):
        _dfs_layouts(child_instance)

    # Dump the module map to the relevant layout file for the KiCAD extension to use
    with open(
        config.build.paths.output_base.with_suffix(".layouts.json"),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(module_map, f, indent=4)
