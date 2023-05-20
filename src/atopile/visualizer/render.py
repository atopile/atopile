import uuid
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

import attrs
import logging

from atopile.model.model import EdgeType, Model, VertexType
from atopile.model.visitor import ModelVertex, ModelVisitor

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

@attrs.define
class Pin:
    name: str
    uuid: str
    index: int

    # internal properties used downstream for generation
    location: str
    source_vid: int
    source_path: str
    block_uuid_stack: List[str]
    connection_stubbed: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "uuid": self.uuid,
            "index": self.index,
        }

@attrs.define
class Stub:
    name: str
    source: Pin
    uuid: str
    direction: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source": self.source,
            "uuid": self.uuid,
            "direction": self.direction,
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
class Position:
    x: int
    y: int

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
        }

@attrs.define
class Block:
    name: str
    type: str
    uuid: str
    blocks: List["Block"]
    ports: List[Port]
    links: List[Link]
    stubs: List[Stub]
    position: Optional[Position] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "uuid": self.uuid,
            "blocks": [block.to_dict() for block in self.blocks],
            "ports": [port.to_dict() for port in self.ports],
            "links": [link.to_dict() for link in self.links],
            "stubs": [stub.to_dict() for stub in self.stubs],
            "position": self.position.to_dict() if self.position is not None else None,
        }

    def from_model(model: Model, main: str, vis_data: dict) -> "Block":
        main = ModelVertex.from_path(model, main)
        bob = Bob(model, vis_data)
        root = bob.build(main)
        return root

# FIXME: this should go to something intelligent instead of this jointjs hack
# eg. up, down, left, right
pin_location_stub_direction_map = {
    "top": "bottm",
    "bottom": "top",
    "left": "right",
    "right": "left",
}

default_stub_direction = list(pin_location_stub_direction_map.values())[0]

class Bob(ModelVisitor):
    """
    The builder... obviously
    """

    def __init__(self, model: Model, vis_data: dict) -> None:
        self.model = model
        self.vis_data = vis_data
        self.block_uuid_stack: List[str] = []
        self.block_directory_by_uuid: Dict[str, Block] = {}
        self.block_directory_by_path: Dict[str, Block] = {}
        self.pin_directory: Dict[int, Pin] = {}
        super().__init__(model)

    @contextmanager
    def block_context(self, block: str):
        self.block_uuid_stack.append(block)
        yield
        self.block_uuid_stack.pop()

    def find_lowest_common_ancestor(self, pins: List[Pin]) -> str:
        if len(pins) == 0:
            raise RuntimeError("No pins to check for lowest common ancestor")
        if len(pins) == 1:
            return pins[0].uuid
        for i in range(min(len(p.block_uuid_stack) for p in pins)):
            # descend into the block stack

            uuids: List[str] = [p.block_uuid_stack[i] for p in pins]
            if not all(uuids[0] == puuid for puuid in uuids):
                # if all the blocks aren't the same, then our last check was... well our last
                if i < 0:
                    raise RuntimeError("No common ancestor found -- how are these two things even linked..?")
                lowest_common_ancestor = pins[0].block_uuid_stack[i-1]
                break
        else:
            lowest_common_ancestor = pins[0].block_uuid_stack[i]
        return lowest_common_ancestor

    def build(self, main: ModelVertex) -> Block:
        root = Block(
            name="root",
            type="module",
            uuid="root",
            blocks=[self.generic_visit_block(main)],
            ports=[],
            links=[],
            stubs=[],
        )

        stubbed_pins_vids: List[int] = []

        connections = self.model.graph.es.select(type_eq=EdgeType.connects_to.name)
        for connection in connections:
            source_pin = self.pin_directory.get(connection.source)
            target_pin = self.pin_directory.get(connection.target)
            block = self.block_directory_by_path.get(self.model.data.get(connection["uid"], {}).get("defining_block"), root)
            if source_pin is None or target_pin is None:
                # assume the pin isn't within the scope of the main block
                continue

            if source_pin.connection_stubbed or target_pin.connection_stubbed:
                if source_pin.connection_stubbed and target_pin.connection_stubbed:
                    raise NotImplementedError(f"Both pins {source_pin.uuid} and {target_pin.uuid} are stubbed")
                if source_pin.connection_stubbed:
                    stubbed_pin = source_pin
                    connecting_pin = target_pin
                else:
                    stubbed_pin = target_pin
                    connecting_pin = source_pin

                stub_name = stubbed_pin.source_path[len(main.path)+1:]
                if stubbed_pin.source_vid not in stubbed_pins_vids:
                    block.stubs.append(Stub(
                        name=stub_name,
                        source=stubbed_pin.uuid,
                        uuid=str(uuid.uuid4()),
                        direction=pin_location_stub_direction_map.get(stubbed_pin.location, default_stub_direction),
                    ))
                    stubbed_pins_vids.append(stubbed_pin.source_vid)

                block.stubs.append(Stub(
                    name=stub_name,
                    source=connecting_pin.uuid,
                    uuid=str(uuid.uuid4()),
                    direction=pin_location_stub_direction_map.get(connecting_pin.location, default_stub_direction),
                ))

            else:
                link = Link(
                    name="test",  # TODO: give these better names
                    uuid=str(uuid.uuid4()),
                    source=source_pin,
                    target=target_pin,
                )
                block.links.append(link)

        return root

    def generic_visit_block(self, vertex: ModelVertex) -> Block:
        uuid_to_be = vertex.path
        with self.block_context(uuid_to_be):
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

            # pin locations specify ports they'll belong to
            pin_locations = {}
            for pin in pins:
                pin_locations.setdefault(pin.location, []).append(pin)

            ports: List[Port] = []
            for location, pins_at_location in pin_locations.items():
                ports.append(Port(
                    name=location,
                    uuid=f"{uuid_to_be}/port@{location}",
                    location=location,
                    pins=pins_at_location
                ))

            for i, pin in enumerate(pins):
                pin.index = i

            # check if there's position data for this block
            block_vis_data = self.vis_data.get(vertex.path, {})
            try:
                position = Position(
                    x=block_vis_data["position"]["x"],
                    y=block_vis_data["position"]["y"]
                )
            except KeyError as ex:
                log.warning(f"Got exception {ex} while trying to get position for {vertex.path}")
                position = None

            # do block build
            block = Block(
                name=vertex.ref,
                type=vertex.vertex_type.name,
                uuid=uuid_to_be,
                blocks=blocks,
                ports=ports,
                links=[],
                stubs=[],
                position=position
            )

            self.block_directory_by_uuid[uuid_to_be] = block
            self.block_directory_by_path[vertex.path] = block

        return block

    def visit_component(self, vertex: ModelVertex) -> Block:
        return self.generic_visit_block(vertex)

    def visit_module(self, vertex: ModelVertex) -> Block:
        return self.generic_visit_block(vertex)

    def generic_visit_pin(self, vertex: ModelVertex) -> Pin:
        pin = Pin(
            name=vertex.ref,
            uuid=vertex.path,
            index=None,
            location=self.model.data[vertex.path].get("visualizer", {}).get("location", "top"),
            source_vid=vertex.index,
            source_path=vertex.path,
            block_uuid_stack=self.block_uuid_stack.copy(),
            connection_stubbed=self.model.data[vertex.path].get("visualizer", {}).get("stub", False),
        )

        self.pin_directory[vertex.index] = pin

        return pin

    def visit_pin(self, vertex: ModelVertex) -> Optional[Pin]:
        # filter out pins that have a single connection to a signal within the same block
        connections_in = vertex.get_edges(mode="in", edge_type=EdgeType.connects_to)
        connections_out = vertex.get_edges(mode="out", edge_type=EdgeType.connects_to)
        if len(connections_in) + len(connections_out) == 1:
            if len(connections_in) == 1:
                target = ModelVertex(self.model, connections_in[0].source)
            if len(connections_out) == 1:
                target = ModelVertex(self.model, connections_out[0].target)
            if target.vertex_type == VertexType.signal:
                if target.parent == vertex.parent:
                    return None

        return self.generic_visit_pin(vertex)

    def visit_signal(self, vertex: ModelVertex) -> Pin:
        return self.generic_visit_pin(vertex)

def build_visualisation(model: Model, main: str, vis_data: dict) -> dict:
    root = Block.from_model(model, main, vis_data)
    return root.to_dict()
