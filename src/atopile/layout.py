import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, override

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.libs.exceptions
from atopile import front_end
from atopile.address import AddressError, AddrStr
from atopile.config import ProjectConfig, config
from faebryk.libs.util import (
    DefaultFactoryDict,
    cast_assert,
    find,
    get_module_from_path,
)

logger = logging.getLogger(__name__)


class SubPCB(fabll.Node):
    path = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def __create_instance__(
        cls, tg: "fabll.TypeGraph", g: "fabll.GraphView", path: Path
    ) -> "SubPCB":
        out = super()._create_instance(tg, g)
        out.path.get().constrain_to_single(g=g, value=str(path))
        return out

    def get_path(self) -> Path:
        return Path(self.path.get().force_extract_literal(str))


class has_subpcb(fabll.Node):
    subpcb_ = F.Collections.PointerSet.MakeChild()
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def setup(self, subpcb: "SubPCB") -> "has_subpcb":
        self.subpcb_.get().append(subpcb)
        return self

    @property
    def subpcb(self) -> set["SubPCB"]:
        return {subpcb.cast(SubPCB) for subpcb in self.subpcb_.get().as_set()}

    def get_subpcb_by_path(self, path: Path) -> "SubPCB":
        return find(self.subpcb, lambda subpcb: subpcb.get_path() == path)

    @override
    def handle_duplicate(self, old: "has_subpcb", node: fabll.Node) -> bool:
        old.subpcb_.get().append(*self.subpcb_.get().as_list())
        return False


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


class in_sub_pcb(fabll.Node):
    _sub_root_module_identifier = "sub_root_module"
    sub_root_modules = F.Collections.PointerSet.MakeChild()
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def setup(self, sub_root_module: fabll.NodeT) -> "in_sub_pcb":
        self.sub_root_modules.get().append(sub_root_module)
        return self

    @property
    def addresses(self) -> list[SubAddress]:
        obj = fabll.Traits.bind(self).get_obj(fabll.Node)
        root = config.project.paths.root
        return [
            SubAddress(
                str(pcb.get_path().relative_to(root)),
                obj.relative_address(sub_root_module),
            )
            for sub_root_module in self.sub_root_modules.get().as_list()
            for pcb in sub_root_module.get_trait(has_subpcb).subpcb
        ]

    @override
    def handle_duplicate(self, old: "in_sub_pcb", node: fabll.Node) -> bool:
        old.sub_root_modules.get().append(*self.sub_root_modules.get().as_list())
        return False


def _index_module_layouts() -> dict[type[fabll.Node], set[SubPCB]]:
    """Find, tag and return a set of all the modules with layouts."""
    directory = config.project.paths.root

    pcbs: dict[Path, SubPCB] = DefaultFactoryDict(SubPCB)
    entries: dict[type[fabll.Node], set[SubPCB]] = defaultdict(set)
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


def attach_sub_pcbs_to_entry_points(app: fabll.Node):
    module_index = _index_module_layouts()
    has_pcb_bound = has_subpcb.bind_typegraph_from_instance(app.instance)
    g = app.instance.g()
    for module_type, pcbs in module_index.items():
        modules = app.get_children(types=module_type, direct_only=False)
        for module in modules:
            for pcb in pcbs:
                fabll.Traits.add_to(
                    module,
                    has_pcb_bound.create_instance(g=g).setup(subpcb=pcb),
                )


def attach_subaddresses_to_modules(app: fabll.Node):
    pcb_modules = app.bind_typegraph_from_self().nodes_with_trait(has_subpcb)
    in_sub_pcb_bound = in_sub_pcb.bind_typegraph_from_instance(app.instance)
    g = app.instance.g()
    for module, _ in pcb_modules:
        for footprint_child, _ in module.iter_children_with_trait(F.has_footprint):
            footprint_child.connect(
                in_sub_pcb_bound.create_instance(g=g).setup(sub_root_module=module),
                edge_attrs=fbrk.EdgeComposition.build(
                    child_identifier=f"{id(footprint_child)}"
                ),
            )
