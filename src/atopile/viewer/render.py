import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING
from pathlib import Path

import attrs

from atopile.model.accessors import ModelVertexView
from atopile.model.model import EdgeType, Model, VertexType
from atopile.model.names import resolve_rel_name
from atopile.model.visitor import ModelVisitor

if TYPE_CHECKING:
    from .project_handler import ProjectHandler

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@attrs.define
class Pin:
    # mandatory external
    name: str
    type: List[Any]
    locals: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "instance_of": self.type,
            "locals": [self.locals]
        }


@attrs.define
class Link:
    # mandatory external
    name: str
    type: str
    source_connectable: str
    target_connectable: str
    source_connectable_type: str
    target_connectable_type: str
    source_block: str
    target_block: str
    above_source_block: str
    above_target_block: str
    source_block_type: str
    target_block_type: str
    above_source_block_type: str
    above_target_block_type: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "instance_of": "link",
            "source_connectable": self.source_connectable,
            "target_connectable": self.target_connectable,
            "source_connectable_type": self.source_connectable_type,
            "target_connectable_type": self.target_connectable_type,
            "source_block": self.source_block,
            "target_block": self.target_block,
            "above_source_block": self.above_source_block,
            "above_target_block": self.above_target_block,
            "source_block_type": self.source_block_type,
            "target_block_type": self.target_block_type,
            "above_source_block_type": self.above_source_block_type,
            "above_target_block_type": self.above_target_block_type,
        }


BlockType = Literal["file", "module", "component"]


@attrs.define
class Block:
    # mandatory external
    name: str
    type: str
    fields: Dict[str, Any]
    blocks: List["Block"] #TODO: in the future we want all locals here
    pins: List[Pin]
    links: List[Link]
    instance_of: Optional[str]
    config: Dict

    # mandatory internal
    source: ModelVertexView

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "instance_of": self.instance_of,
            "locals": [block.to_dict() for block in self.blocks] + [pin.to_dict() for pin in self.pins] + [link.to_dict() for link in self.links] + [self.fields],
            "config": self.config
            # "pins": [pin.to_dict() for pin in self.pins],
            # "links": [link.to_dict() for link in self.links],
        }


class Bob(ModelVisitor):
    """
    The builder... obviously
    """

    def __init__(self, model: Model, project_handler: "ProjectHandler",) -> None:
        self.model = model
        self.project_handler = project_handler
        self.all_verticies: List[ModelVertexView] = []
        self.block_stack: List[ModelVertexView] = []
        self.block_directory_by_path: Dict[str, Block] = {}
        self.pin_directory_by_vid: Dict[int, Pin] = {}
        super().__init__(model)

    @contextmanager
    def block_context(self, block: ModelVertexView):
        self.block_stack.append(block)
        yield
        self.block_stack.pop()

    @staticmethod
    def build(model: Model, project_handler: "ProjectHandler", main: ModelVertexView) -> Block:
        bob = Bob(model, project_handler)

        root = bob.generic_visit_block(main)
        # TODO: this logic ultimately belongs in the viewer, because this
        # isn't really an instance of anything
        root.instance_of = main.path

        connections = model.graph.es.select(type_eq=EdgeType.connects_to.name)
        all_indicies = {v.index for v in bob.all_verticies}
        for connection in connections:
            if (
                connection.source not in all_indicies
                or connection.target not in all_indicies
            ):
                continue

            lca, link_name = resolve_rel_name(
                ModelVertexView.from_indicies(
                    model, [connection.source, connection.target]
                )
            )

            source_mvv = ModelVertexView(model, connection.source)
            target_mvv = ModelVertexView(model, connection.target)

            #TODO: this mechanism only works at the root level, will need to fix if we want this to work deeper
            source_block_type = "self"
            above_source_block_type = "self"
            source_parent_mvv = source_mvv.parent
            above_source_parent_mvv = source_parent_mvv.parent
            if source_parent_mvv.path != main.path:
                source_block_type = source_parent_mvv.vertex_type.name
                if above_source_parent_mvv.path != main.path:
                    above_source_block_type = above_source_parent_mvv.vertex_type.name


            target_block_type = "self"
            above_target_block_type = "self"
            target_parent_mvv = target_mvv.parent
            above_target_parent_mvv = target_parent_mvv.parent
            if target_parent_mvv.path != main.path:
                target_block_type = target_parent_mvv.vertex_type.name
                if above_target_parent_mvv.path != main.path:
                    above_target_block_type = above_target_parent_mvv.vertex_type.name

            link = Link(
                name=link_name,
                type="link", 
                source_connectable=source_mvv.ref,
                target_connectable=target_mvv.ref,
                source_connectable_type=source_mvv.vertex_type.name,
                target_connectable_type=target_mvv.vertex_type.name,
                source_block=source_mvv.parent.ref,
                target_block=target_mvv.parent.ref,
                above_source_block=source_mvv.parent.parent.ref,
                above_target_block=target_mvv.parent.parent.ref,
                source_block_type=source_block_type,
                target_block_type=target_block_type,
                above_source_block_type=above_source_block_type,
                above_target_block_type=above_target_block_type,
            )

            bob.block_directory_by_path[lca.path].links.append(link)

        return root

    def generic_visit_block(self, vertex: ModelVertexView) -> Block:
        self.all_verticies.append(vertex)

        with self.block_context(vertex):
            # find subelements
            blocks: List[Block] = self.wander(
                vertex=vertex,
                mode="in",
                edge_type=EdgeType.part_of,
                vertex_type=[VertexType.component, VertexType.module],
            )

            pins = self.wander_interface(vertex)


            # check the type of this block
            instance_ofs = vertex.get_adjacents("out", EdgeType.instance_of)
            if len(instance_ofs) > 0:
                if len(instance_ofs) > 1:
                    log.warning(
                        f"Block {vertex.path} is an instance_of multiple things"
                    )
                instance_of = instance_ofs[0].class_path
            else:
                instance_of = None

            config = None
            if instance_of:
                config = self.project_handler.get_config_sync(Path(instance_ofs[0].file_path).with_suffix(".vis.dummy"))
            else:
                config = self.project_handler.get_config_sync(Path(vertex.file_path).with_suffix(".vis.dummy"))

            # do block build
            block = Block(
                name=vertex.ref,
                type=vertex.vertex_type.name,
                fields=vertex.data,  # FIXME: feels wrong to just blindly shove all this data down the pipe
                blocks=blocks,
                pins=pins,
                links=[],
                instance_of=instance_of,
                source=vertex,
                config=config
            )

            self.block_directory_by_path[vertex.path] = block

        return block

    def visit_component(self, vertex: ModelVertexView) -> Block:
        return self.generic_visit_block(vertex)

    def visit_module(self, vertex: ModelVertexView) -> Block:
        return self.generic_visit_block(vertex)

    def wander_interface(self, vertex: ModelVertexView) -> List[Pin]:
        listy_pins: List[Pin, List[Pin]] = filter(
            lambda x: x is not None,
            self.wander(
                vertex=vertex,
                mode="in",
                edge_type=EdgeType.part_of,
                vertex_type=[VertexType.pin, VertexType.signal, VertexType.interface],
            ),
        )
        pins = []
        for listy_pin in listy_pins:
            if isinstance(listy_pin, list):
                pins += listy_pin
            else:
                pins += [listy_pin]
        return pins

    def visit_interface(self, vertex: ModelVertexView) -> Block:
        pins = self.wander_interface(vertex)
        for pin in pins:
            pin.name = vertex.ref + "-" + pin.name
        return self.generic_visit_block(vertex)

    def generic_visit_pin(self, vertex: ModelVertexView) -> Pin:
        vertex_data: dict = self.model.data.get(vertex.path, {})
        pin = Pin(name=vertex.ref, type=vertex.vertex_type, locals=vertex_data.get("fields", {}))
        self.pin_directory_by_vid[vertex.index] = pin
        return pin

    def visit_pin(self, vertex: ModelVertexView) -> Optional[Pin]:
        self.all_verticies.append(vertex)
        # filter out pins that have a single connection to a signal within the same block
        connections_in = vertex.get_edges(mode="in", edge_type=EdgeType.connects_to)
        connections_out = vertex.get_edges(mode="out", edge_type=EdgeType.connects_to)
        if len(connections_in) + len(connections_out) == 1:
            if len(connections_in) == 1:
                target = ModelVertexView(self.model, connections_in[0].source)
            if len(connections_out) == 1:
                target = ModelVertexView(self.model, connections_out[0].target)
            if target.vertex_type == VertexType.signal:
                if target.parent_path == vertex.parent_path:
                    return None

        return self.generic_visit_pin(vertex)

    def visit_signal(self, vertex: ModelVertexView) -> Pin:
        self.all_verticies.append(vertex)
        return self.generic_visit_pin(vertex)


# TODO: resolve the API between this and build_model
def build_view(model: Model, project_handler: "ProjectHandler", root_node: str) -> dict:
    root_node = ModelVertexView.from_path(model, root_node)
    root = Bob.build(model, project_handler, root_node)
    return root.to_dict()
