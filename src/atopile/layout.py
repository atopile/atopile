import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.libs.exceptions
from atopile.address import AddrStr
from atopile.compiler.ast_visitor import is_ato_module
from atopile.config import ProjectConfig, config
from faebryk.libs.util import DefaultFactoryDict, KeyErrorNotFound, find, not_none

logger = logging.getLogger(__name__)


class SubPCB(fabll.Node):
    path = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def __create_instance__(
        cls, tg: "fbrk.TypeGraph", g: "graph.GraphView", path: Path
    ) -> "SubPCB":
        out = super()._create_instance(tg, g)
        out.path.get().alias_to_single(g=g, value=str(path))
        return out

    def get_path(self) -> Path:
        return Path(self.path.get().force_extract_literal(str))


class has_subpcb(fabll.Node):
    subpcb_ = F.Collections.PointerSet.MakeChild()
    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def setup(self, subpcb: "SubPCB") -> "has_subpcb":  # type: ignore[invalid-method-override]
        self.subpcb_.get().append(subpcb)
        return self

    @property
    def subpcb(self) -> set["SubPCB"]:
        return {subpcb.cast(SubPCB) for subpcb in self.subpcb_.get().as_set()}

    def get_subpcb_by_path(self, path: Path) -> "SubPCB":
        return find(self.subpcb, lambda subpcb: subpcb.get_path() == path)

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
    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def setup(self, sub_root_module: fabll.NodeT) -> "in_sub_pcb":  # type: ignore[invalid-method-override]
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

    def handle_duplicate(self, old: "in_sub_pcb", node: fabll.Node) -> bool:
        old.sub_root_modules.get().append(*self.sub_root_modules.get().as_list())
        return False


def _index_module_layouts(tg: fbrk.TypeGraph) -> "dict[graph.BoundNode, set[SubPCB]]":
    """Find, tag and return a set of all the modules with layouts."""
    from atopile.compiler import ast_types as AST
    from atopile.compiler.ast_visitor import AnyAtoBlock

    pcbs: dict[Path, SubPCB] = DefaultFactoryDict(lambda _: SubPCB)  # type: ignore[arg-type]
    entries: "dict[graph.BoundNode, set[SubPCB]]" = defaultdict(set)

    modules_by_address: "dict[AddrStr, graph.BoundNode]" = {}

    modules = fabll.Traits.get_implementor_objects(
        is_ato_module.bind_typegraph(tg), g=tg.get_graph_view()
    )

    for module in modules:
        type_node = not_none(module.get_type_node())
        definition = fabll.Node.bind_instance(
            not_none(
                fbrk.EdgePointer.get_pointed_node_by_identifier(
                    bound_node=not_none(type_node),
                    identifier=AnyAtoBlock._definition_identifier,
                )
            )
        )

        try:
            _, path_trait = definition.get_parent_with_trait(AST.has_path)
        except KeyErrorNotFound:
            continue

        file_path = (
            Path(path_trait.get_path()).resolve().relative_to(config.project.paths.root)
        )
        module_name = not_none(module.get_type_name())
        modules_by_address[AddrStr.from_parts(file_path, module_name)] = type_node

    # scan project and all dependencies
    # TODO: only active dependencies
    for filepath in config.project.paths.root.glob("**/ato.yaml"):
        with faebryk.libs.exceptions.downgrade(Exception, logger=logger):
            project_config = ProjectConfig.from_path(filepath.parent)

            if project_config is None:
                raise faebryk.libs.exceptions.UserResourceException(
                    f"Failed to load module config: {filepath}"
                )

            for build in project_config.builds.values():
                with faebryk.libs.exceptions.downgrade(Exception, logger=logger):
                    pcb = pcbs[build.paths.layout]
                    if type_node := modules_by_address.get(AddrStr(build.address)):
                        entries[type_node].add(pcb)

    return entries


def attach_sub_pcbs_to_entry_points(app: fabll.Node):
    module_index = _index_module_layouts(app.tg)
    has_pcb_bound = has_subpcb.bind_typegraph_from_instance(app.instance)
    g = app.instance.g()
    for type_node, pcbs in module_index.items():
        # Find all instances of this type by visiting instance edges
        instances: list[graph.BoundNode] = []
        fbrk.EdgeType.visit_instance_edges(
            bound_node=type_node,
            ctx=instances,
            f=lambda ctx, edge: ctx.append(edge.g().bind(node=edge.edge().target())),
        )
        for instance in instances:
            module = fabll.Node.bind_instance(instance)
            # Only attach to modules that are descendants of app
            if not module.is_descendant_of(app):
                continue
            for pcb in pcbs:
                fabll.Traits.add_to(
                    module,
                    has_pcb_bound.create_instance(g=g).setup(subpcb=pcb),
                )


def attach_subaddresses_to_modules(app: fabll.Node):
    pcb_modules = fabll.Traits.get_implementor_objects(
        has_subpcb.bind_typegraph(app.tg), g=app.g
    )
    in_sub_pcb_bound = in_sub_pcb.bind_typegraph_from_instance(app.instance)
    g = app.instance.g()
    for module in pcb_modules:
        for footprint_child, _ in module.iter_children_with_trait(
            F.Footprints.has_associated_footprint
        ):
            footprint_child.connect(
                in_sub_pcb_bound.create_instance(g=g).setup(sub_root_module=module),
                edge_attrs=fbrk.EdgeComposition.build(
                    child_identifier=f"{id(footprint_child)}"
                ),
            )
