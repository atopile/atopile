from contextlib import contextmanager
from typing import Dict, List, Optional, Any

import attrs
import logging

from atopile.model.model import EdgeType, Model, VertexType
from atopile.model.utils import generate_uid_from_path
from atopile.model.accessors import ModelVertexView, lowest_common_ancestor
from atopile.model.visitor import ModelVisitor

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@attrs.define
class Pin:
    # mandatory external
    name: str
    fields: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fields": self.fields
        }


@attrs.define
class Link:
    # mandatory external
    net: str
    source: str
    target: str

    def to_dict(self) -> dict:
        return {
            "net": self.net,
            "source": self.source,
            "target": self.target,
        }


@attrs.define
class Block:
    # mandatory external
    name: str
    type: str
    blocks: List["Block"]
    pins: List[Pin]
    links: List[Link]
    instance_of: Optional[str]

    # mandatory internal
    source: ModelVertexView

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "blocks": [block.to_dict() for block in self.blocks],
            "pins": [pin.to_dict() for pin in self.pins],
            "links": [link.to_dict() for link in self.links],
            "instance_of": self.instance_of,
        }


class Bob(ModelVisitor):
    """
    The builder... obviously
    """

    def __init__(self, model: Model) -> None:
        self.model = model
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
    def build(model: Model, main: ModelVertexView) -> Block:
        bob = Bob(model)

        root = bob.generic_visit_block(main)

        connections = model.graph.es.select(type_eq=EdgeType.connects_to.name)
        for connection in connections:
            lca = lowest_common_ancestor(ModelVertexView.from_indicies(model, [connection.source, connection.target]))

            link = Link(
                net="test",
                source=lca.relative_path(ModelVertexView(model, connection.source)),
                target=lca.relative_path(ModelVertexView(model, connection.target)),
            )

            bob.block_directory_by_path[lca.path].links.append(link)

        return root

    def generic_visit_block(self, vertex: ModelVertexView) -> Block:
        with self.block_context(vertex):
            # find subelements
            blocks: List[Block] = self.wander(
                vertex=vertex,
                mode="in",
                edge_type=EdgeType.part_of,
                vertex_type=[VertexType.component, VertexType.module]
            )

            pins: List[Pin] = self.wander(
                vertex=vertex,
                mode="in",
                edge_type=EdgeType.part_of,
                vertex_type=[VertexType.pin, VertexType.signal]
            )
            # filter out Nones
            pins = [p for p in pins if p is not None]

            # check the type of this block
            instance_ofs = vertex.get_adjacents("out", EdgeType.instance_of)
            if len(instance_ofs) > 0:
                instance_of = instance_ofs[0].ref
            else:
                instance_of = None

            # do block build
            block = Block(
                name=vertex.ref,
                type=vertex.vertex_type.name,
                blocks=blocks,
                pins=pins,
                links=[],
                instance_of=instance_of,
                source=vertex,
            )

            self.block_directory_by_path[vertex.path] = block

        return block

    def visit_component(self, vertex: ModelVertexView) -> Block:
        return self.generic_visit_block(vertex)

    def visit_module(self, vertex: ModelVertexView) -> Block:
        return self.generic_visit_block(vertex)

    def generic_visit_pin(self, vertex: ModelVertexView) -> Pin:
        vertex_data: dict = self.model.data[vertex.path]
        pin = Pin(
            name=vertex.ref,
            fields=vertex_data.get("fields", {})
        )
        self.pin_directory_by_vid[vertex.index] = pin
        return pin

    def visit_pin(self, vertex: ModelVertexView) -> Optional[Pin]:
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
        return self.generic_visit_pin(vertex)

# TODO: resolve the API between this and build_model
def build_view(model: Model, root_node: str) -> list:
    root_node = ModelVertexView.from_path(model, root_node)
    root = Bob.build(model, root_node)
    return [root.to_dict()]
