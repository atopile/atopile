"""
This module contains functions for interacting with layout data,
and generating files required to reuse layouts.

Thanks @nickkrstevski (https://github.com/nickkrstevski) for
the heavy lifting on this one!
"""

import hashlib
import json
import logging
import uuid
from pathlib import Path
from typing import Iterable

from more_itertools import first

import faebryk.library._F as F
from atopile import address, config, errors, utils
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.util import (
    FuncDict,
    FuncSet,
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    find,
    get_module_from_path,
    has_attr_or_property,
)

logger = logging.getLogger(__name__)


def _generate_uuid_from_string(path: str) -> str:
    """Spits out a uuid in hex from a string"""
    path_as_bytes = path.encode("utf-8")
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return str(uuid.UUID(bytes=hashed_path))


def _clean_full_name(node: Module, root: Module | None = None) -> str:
    # TODO: this function shouldn't exist
    # See: https://github.com/atopile/atopile/issues/547
    addr: list[str] = []
    for n, name in reversed(list(node.get_hierarchy())):
        if root is not None and n is root:
            break
        addr.append(name)
    else:
        return node.get_full_name()
    return ".".join(reversed(addr))


def _index_module_layouts() -> FuncDict[Module, set[Path]]:
    """Find, tag and return a set of all the modules with layouts."""
    directory = config.get_project_context().project_path

    entries: FuncDict[Module, set[Path]] = FuncDict()
    for filepath in directory.glob("**/ato.yaml"):
        cfg = config.get_project_config_from_path(filepath)

        for build_name in cfg.builds:
            ctx = config.BuildContext.from_config_name(cfg, build_name)

            if (class_ := get_module_from_path(ctx.entry.file_path, ctx.entry.entry_section)) is not None:
                # we only bother to index things we've imported, otherwise we can be sure they weren't used
                entries.setdefault(class_, set()).add(ctx.layout_path)

    return entries


def _cmp_uuid(inst: Module, root: Module) -> str:
    return _generate_uuid_from_string(_clean_full_name(inst, root))


def generate_module_map(build_ctx: config.BuildContext, app: Module) -> None:
    """Generate a file containing a list of all the modules and their components in the build."""
    module_map = {}

    module_layouts = _index_module_layouts()

    for module, trait in GraphFunctions(app.get_graph()).nodes_with_trait(F.has_reference_layout):
        module_layouts.setdefault(module, set()).update(trait.paths)

    for module_instance in app.get_children_modules(types=Module):
        try:
            # TODO: this could be improved if we had the mro of the module
            module_super = find(
                lambda x: isinstance(module_instance, x) in x, module_layouts.keys()
            )
        except KeyErrorNotFound:
            continue
        except KeyErrorAmbiguous as e:
            raise errors.AtoNotImplementedError(
                "There are multiple build configurations for this module.\n"
                "We don't currently support multiple layouts for the same module."
                "Show the issue some love to get it done: https://github.com/atopile/atopile/issues/399"
            ) from e

        # Build up a map of UUIDs of the children of the module
        # The keys are instance UUIDs and the values are the corresponding UUIDs in the layout
        uuid_map = {}
        for inst_child in GraphFunctions(module_instance.get_graph()).nodes_with_trait(F.has_footprint):
            uuid_map[_cmp_uuid(inst_child, app)] = _cmp_uuid(inst_child, module_instance)

        module_map[address.get_instance_section(module_instance)] = {
            "instance_path": module_instance,
            "layout_path": str(first(module_layouts[module_super])),
            "uuid_map": uuid_map,
        }

    with open(
        build_ctx.output_base.with_suffix(".layouts.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(module_map, f)
