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
from collections import defaultdict

from atopile import address, config, errors, instance_methods
from atopile.instance_methods import (
    all_descendants,
    find_matching_super,
    match_components,
    match_modules,
)

log = logging.getLogger(__name__)


def generate_uuid_from_string(path: str) -> str:
    """Spits out a uuid in hex from a string"""
    path_as_bytes = path.encode("utf-8")
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return str(uuid.UUID(bytes=hashed_path))


def generate_comp_uid(comp_addr: str) -> str:
    """Get a unique identifier for a component."""
    instance_section = address.get_instance_section(comp_addr)
    if not instance_section:
        raise ValueError(f"Component address {comp_addr} has no instance section")
    return generate_uuid_from_string(instance_section)


def _find_module_layouts() -> dict[str, list[config.BuildContext]]:
    """
    Return a dict of all the known entry points of dependencies in the project.
    The dict maps the entry point's address to another map of the entry point's
    build name and the layout file path.
    """
    directory = config.get_project_context().project_path

    entries = defaultdict(list)
    for filepath in directory.glob("**/ato.yaml"):
        cfg = config.get_project_config_from_path(filepath)

        for build_name in cfg.builds:
            ctx = config.BuildContext.from_config_name(cfg, build_name)
            entries[ctx.entry].append(ctx)

    return entries


def generate_module_map(build_ctx: config.BuildContext) -> None:
    """Generate a file containing a list of all the modules and their components in the build."""
    module_map = {}

    laid_out_modules = _find_module_layouts()
    for module_instance in filter(match_modules, all_descendants(build_ctx.entry)):
        module_super = find_matching_super(module_instance, list(laid_out_modules.keys()))
        if not module_super:
            continue

        # Skip build entry point
        if module_instance == build_ctx.entry:
            continue

        # Get the build context for the laid out module
        module_super_ctxs = laid_out_modules[module_super]
        if len(module_super_ctxs) > 1:
            raise errors.AtoNotImplementedError()
        module_super_ctx = module_super_ctxs[0]

        # Build up a map of UUIDs of the children of the module
        # The keys are instance UUIDs and the values are the corresponding UUIDs in the layout
        # FIXME: this currently relies on the `all_descendants` iterator returning the
        # children in the same order. This is pretty fragile and should be fixed.
        uuid_map = {}
        for inst_addr, layout_addr in instance_methods.common_children(
            module_instance, module_super_ctx.entry
        ):
            if not match_components(inst_addr):
                # Skip non-components
                continue

            # This should be enforced by the `common_children` function
            assert address.get_name(inst_addr) == address.get_name(layout_addr)

            uuid_map[generate_comp_uid(inst_addr)] = generate_comp_uid(layout_addr)

        module_map[address.get_instance_section(module_instance)] = {
            "instance_path": module_instance,
            "layout_path": str(module_super_ctx.layout_path),
            "uuid_map": uuid_map,
        }

    with open(build_ctx.output_base.with_suffix(".layouts.json"), "w", encoding="utf-8") as f:
        json.dump(module_map, f)
