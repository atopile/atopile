import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import override

import faebryk.library._F as F
import faebryk.libs.exceptions
from atopile import front_end
from atopile.address import AddressError, AddrStr
from atopile.config import ProjectConfig, config
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.util import (
    DefaultFactoryDict,
    cast_assert,
    find,
    get_module_from_path,
)

logger = logging.getLogger(__name__)


# TODO should be Node
class SubPCB:
    def __init__(self, path: Path) -> None:
        self._path = path


class has_subpcb(Module.TraitT.decless()):
    def __init__(self, subpcb: SubPCB) -> None:
        super().__init__()
        self._subpcb = {subpcb}

    @override
    def handle_duplicate(self, old: "has_subpcb", node: Node) -> bool:
        old._subpcb.update(self._subpcb)
        return False

    @property
    def subpcb(self) -> set["SubPCB"]:
        return self._subpcb

    def get_subpcb_by_path(self, path: Path) -> "SubPCB":
        return find(self._subpcb, lambda subpcb: subpcb._path == path)


@dataclass(frozen=True)
class SubAddress:
    pcb_address: str
    module_address: str

    @classmethod
    def deserialize(cls, address: str) -> "SubAddress":
        pcb_address, module_address = address.split(":")
        return cls(pcb_address, module_address)

    def serialize(self) -> str:
        return f"{self.pcb_address}:{self.module_address}"


class in_sub_pcb(Module.TraitT.decless()):
    def __init__(self, sub_root_module: Module):
        super().__init__()
        self._sub_root_modules = {sub_root_module}

    @property
    def addresses(self) -> list[SubAddress]:
        obj = self.get_obj(Module)
        root = config.project.paths.root
        return [
            SubAddress(
                str(pcb._path.relative_to(root)), obj.relative_address(sub_root_module)
            )
            for sub_root_module in self._sub_root_modules
            for pcb in sub_root_module.get_trait(has_subpcb).subpcb
        ]

    @override
    def handle_duplicate(self, old: "in_sub_pcb", node: Node) -> bool:
        old._sub_root_modules.update(self._sub_root_modules)
        return False


def _index_module_layouts() -> dict[type[Module], set[SubPCB]]:
    """Find, tag and return a set of all the modules with layouts."""
    directory = config.project.paths.root

    pcbs: dict[Path, SubPCB] = DefaultFactoryDict(SubPCB)
    entries: dict[type[Module], set[SubPCB]] = defaultdict(set)
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

                    pcb = pcbs[build.paths.layout]
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
                        entries[cast_assert(type, class_)].add(pcb)

                    # Check if the module is a known ato module
                    elif class_ := ato_modules.get(
                        # This is the address w/ an absolute path to the entry file
                        # which is the format also used by the frontend to key modules
                        AddrStr.from_parts(build.entry_file_path, build.entry_section)
                    ):
                        entries[cast_assert(type, class_)].add(pcb)

    return entries


def attach_sub_pcbs_to_entry_points(app: Module):
    module_index = _index_module_layouts()
    for module_type, pcbs in module_index.items():
        modules = app.get_children_modules(types=module_type, direct_only=False)
        for module in modules:
            for pcb in pcbs:
                module.add(has_subpcb(pcb))


def attach_subaddresses_to_modules(app: Module):
    pcb_modules = GraphFunctions(app.get_graph()).nodes_with_trait(has_subpcb)
    for module, _ in pcb_modules:
        assert isinstance(module, Module)

        footprint_children = module.get_children(
            direct_only=False,
            f_filter=lambda c: c.has_trait(F.has_footprint),
            types=Module,
        )
        for footprint_child in footprint_children:
            footprint_child.add(in_sub_pcb(module))
