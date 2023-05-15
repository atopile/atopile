import attrs
import uuid
from typing import List, Dict
from atopile.model.model import Model, EdgeType, VertexType
from atopile.model.visitor import ModelVisitor, ModelVertex

@attrs.define
class Pin:
    name: str
    source_vid: int
    block_uuid_stack: List[str]
    uuid: str
    index: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "uuid": self.uuid,
            "index": self.index,
        }

@attrs.define
class Port:
    name: str
    uuid: str
    location: str
    pins: List[Pin]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "uuid": self.uuid,
            "location": self.location,
            "pins": [pin.to_dict() for pin in self.pins],
        }

@attrs.define
class Link:
    name: str
    uuid: str
    source: Pin
    target: Pin

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "uuid": self.uuid,
            "source": self.source.uuid,
            "target": self.target.uuid,
        }

@attrs.define
class Block:
    name: str
    type: str
    uuid: str
    blocks: List["Block"]
    ports: List[Port]
    links: List[Link]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "uuid": self.uuid,
            "blocks": [block.to_dict() for block in self.blocks],
            "ports": [port.to_dict() for port in self.ports],
            "links": [link.to_dict() for link in self.links],
        }

    def from_model(model: Model, main: str) -> "Block":
        main = ModelVertex.from_path(model, main)
        bob = Bob(model)
        root = bob.build(main)
        return root

class Bob(ModelVisitor):
    """
    The builder... obviously
    """

    def __init__(self, model: Model) -> None:
        self.model = model
        self.block_uuid_stack: List[str] = []
        self.block_directory: Dict[str, Block] = {}
        self.pin_directory: Dict[int, Pin] = {}
        super().__init__(model)

    def build(self, main: ModelVertex) -> Block:
        root = Block(
            name="root",
            type="module",
            uuid=str(uuid.uuid4()),
            blocks=[self.generic_visit_block(main)],
            ports=[],
            links=[],
        )

        connections = self.model.graph.es.select(type_eq=EdgeType.connects_to.name)
        for connection in connections:
            source_pin = self.pin_directory.get(connection.source)
            target_pin = self.pin_directory.get(connection.target)
            if source_pin is None or target_pin is None:
                # assume the pin isn't within the scope of the main block
                continue

            for i in range(min(len(source_pin.block_uuid_stack), len(target_pin.block_uuid_stack))):
                if source_pin.block_uuid_stack[i] != target_pin.block_uuid_stack[i]:
                    if i < 0:
                        raise RuntimeError("No common ancestor found -- how are these two things even linked..?")
                    lowest_common_ancestor = source_pin.block_uuid_stack[i-1]
            else:
                lowest_common_ancestor = source_pin.block_uuid_stack[i]

            block = self.block_directory[lowest_common_ancestor]
            link = Link(
                name="test",
                uuid=str(uuid.uuid4()),
                source=source_pin,
                target=target_pin,
            )
            block.links.append(link)

        return root

    def generic_visit_block(self, vertex: ModelVertex) -> Block:
        uuid_to_be = str(uuid.uuid4())
        self.block_uuid_stack.append(uuid_to_be)

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

        ports = [
            Port(
                name="test",
                uuid=str(uuid.uuid4()),
                location="top",
                pins=pins
            )
        ]

        for i, pin in enumerate(pins):
            pin.index = i

        block = Block(
            name=vertex.ref,
            type=vertex.type.name,
            uuid=uuid_to_be,
            blocks=blocks,
            ports=ports,
            links=[]
        )

        self.block_directory[uuid_to_be] = block
        self.block_uuid_stack.pop()
        return block

    def visit_component(self, vertex: ModelVertex) -> Block:
        return self.generic_visit_block(vertex)

    def visit_module(self, vertex: ModelVertex) -> Block:
        return self.generic_visit_block(vertex)

    def generic_visit_pin(self, vertex: ModelVertex) -> Pin:
        pin = Pin(
            name=vertex.ref,
            source_vid=vertex.index,
            uuid=str(uuid.uuid4()),
            block_uuid_stack=self.block_uuid_stack.copy(),
            index=None
        )

        self.pin_directory[vertex.index] = pin

        return pin

    def visit_pin(self, vertex: ModelVertex) -> Pin:
        return self.generic_visit_pin(vertex)

    def visit_signal(self, vertex: ModelVertex) -> Pin:
        return self.generic_visit_pin(vertex)

def build_dict(model: Model, main: str) -> dict:
    root = Block.from_model(model, main)
    return root.to_dict()
