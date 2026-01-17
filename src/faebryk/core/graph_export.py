"""
Export instance graphs to JSON format for visualization.

This module provides functionality to export faebryk instance graphs
to a JSON format that can be consumed by visualization tools.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph

logger = logging.getLogger(__name__)


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively sanitize an object for JSON serialization.

    Handles Infinity, NaN, and other non-JSON-compatible values.
    """
    import math

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif hasattr(obj, "__dict__") and not isinstance(obj, (str, int, bool, type(None))):
        return str(obj)
    return obj


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for non-serializable types."""
    if hasattr(obj, "__dict__"):
        return str(obj)
    return str(obj)


# Edge type configuration with colors for visualization
EDGE_TYPES = {
    "composition": {
        "name": "Composition",
        "color": "#4CAF50",  # Green
        "directional": True,
        "description": "Parent-child composition relationship",
    },
    "trait": {
        "name": "Trait",
        "color": "#9C27B0",  # Purple
        "directional": True,
        "description": "Trait instance attachment",
    },
    "pointer": {
        "name": "Pointer",
        "color": "#FF9800",  # Orange
        "directional": True,
        "description": "Pointer/reference relationship",
    },
    "connection": {
        "name": "Connection",
        "color": "#2196F3",  # Blue
        "directional": False,
        "description": "Interface connection",
    },
    "operand": {
        "name": "Operand",
        "color": "#F44336",  # Red
        "directional": True,
        "description": "Expression operand relationship",
    },
    "type": {
        "name": "Type",
        "color": "#607D8B",  # Gray-blue
        "directional": True,
        "description": "Type edge linking instance to type",
    },
    "next": {
        "name": "Next",
        "color": "#795548",  # Brown
        "directional": True,
        "description": "Next/sequence relationship",
    },
}


@dataclass
class ExportedNode:
    """Represents a node in the exported graph."""

    id: str
    uuid: int
    type_name: str | None = None
    name: str | None = None
    parent_id: str | None = None
    depth: int = 0
    traits: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    child_count: int = 0
    trait_count: int = 0


@dataclass
class ExportedEdge:
    """Represents an edge in the exported graph."""

    id: str
    source: str
    target: str
    edge_type: str
    name: str | None = None
    directional: bool = True


class GraphExporter:
    """Exports instance graphs to JSON format."""

    def __init__(self):
        self.nodes: dict[str, ExportedNode] = {}
        self.edges: list[ExportedEdge] = []
        self.visited_nodes: set[int] = set()
        self.visited_edges: set[tuple[int, int, str]] = set()
        self.edge_counter: int = 0

    def _strip_hex_suffix(self, type_name: str) -> str:
        """Strip hex values in square brackets from type names."""
        return re.sub(r"\[0x[0-9a-fA-F]+\]$", "", type_name)

    def _make_node_id(self, uuid: int) -> str:
        """Create a node ID from UUID."""
        return f"n{uuid:x}"

    def _make_edge_id(self) -> str:
        """Create a unique edge ID."""
        self.edge_counter += 1
        return f"e{self.edge_counter}"

    def _get_type_name(self, bound_node: graph.BoundNode) -> str | None:
        """Get the type name of a node."""
        try:
            type_edge = fbrk.EdgeType.get_type_edge(bound_node=bound_node)
            if type_edge is not None:
                type_node = fbrk.EdgeType.get_type_node(edge=type_edge.edge())
                type_bound = type_edge.g().bind(node=type_node)
                if isinstance(
                    tn := type_bound.node().get_attr(key="type_identifier"),
                    str,
                ):
                    return tn
        except Exception:
            pass
        return None

    def _get_node_name(self, bound_node: graph.BoundNode) -> str | None:
        """Get the name of a node."""
        # Try direct name attribute
        if isinstance(name := bound_node.node().get_attr(key="name"), str):
            return name

        # Try parent edge name
        try:
            parent_edge = fbrk.EdgeComposition.get_parent_edge(bound_node=bound_node)
            if parent_edge is not None:
                edge_name = fbrk.EdgeComposition.get_name(edge=parent_edge.edge())
                if edge_name:
                    return edge_name
        except Exception:
            pass

        return None

    def _collect_traits(self, bound_node: graph.BoundNode) -> list[str]:
        """Collect trait type names for a node."""
        traits: list[str] = []
        trait_edges: list[graph.BoundEdge] = []

        def collect(ctx: list, edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgeTrait.visit_trait_instance_edges(
            bound_node=bound_node, ctx=trait_edges, f=collect
        )

        for edge in trait_edges:
            target_bound = edge.g().bind(node=edge.edge().target())
            trait_name = self._get_type_name(target_bound)
            if trait_name:
                traits.append(self._strip_hex_suffix(trait_name))

        return traits

    def _collect_attributes(self, bound_node: graph.BoundNode) -> dict[str, Any]:
        """Collect attributes of a node (limited set for visualization)."""
        attrs: dict[str, Any] = {}

        # Get a few common attributes if they exist
        for key in ["name", "type_identifier", "value"]:
            try:
                val = bound_node.node().get_attr(key=key)
                if val is not None:
                    if isinstance(val, (str, int, float, bool)):
                        attrs[key] = val
            except Exception:
                pass

        return attrs

    def _export_node(
        self,
        bound_node: graph.BoundNode,
        parent_id: str | None = None,
        depth: int = 0,
    ) -> str:
        """Export a node and its children recursively."""
        uuid = bound_node.node().get_uuid()
        node_id = self._make_node_id(uuid)

        # Skip if already visited
        if uuid in self.visited_nodes:
            return node_id

        self.visited_nodes.add(uuid)

        # Get node properties
        type_name = self._get_type_name(bound_node)
        name = self._get_node_name(bound_node)
        traits = self._collect_traits(bound_node)
        attributes = self._collect_attributes(bound_node)

        # Collect children edges
        children: list[graph.BoundEdge] = []

        def collect_children(ctx: list, edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgeComposition.visit_children_edges(
            bound_node=bound_node, ctx=children, f=collect_children
        )

        # Collect trait edges
        trait_edges: list[graph.BoundEdge] = []

        def collect_traits(ctx: list, edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgeTrait.visit_trait_instance_edges(
            bound_node=bound_node, ctx=trait_edges, f=collect_traits
        )

        # Create exported node
        node = ExportedNode(
            id=node_id,
            uuid=uuid,
            type_name=self._strip_hex_suffix(type_name) if type_name else None,
            name=name,
            parent_id=parent_id,
            depth=depth,
            traits=traits,
            attributes=attributes,
            child_count=len(children),
            trait_count=len(trait_edges),
        )
        self.nodes[node_id] = node

        # Process composition edges (children)
        for edge in children:
            target = edge.edge().target()
            target_uuid = target.get_uuid()
            target_id = self._make_node_id(target_uuid)
            edge_key = (uuid, target_uuid, "composition")

            if edge_key not in self.visited_edges:
                self.visited_edges.add(edge_key)
                edge_name = fbrk.EdgeComposition.get_name(edge=edge.edge())
                self.edges.append(
                    ExportedEdge(
                        id=self._make_edge_id(),
                        source=node_id,
                        target=target_id,
                        edge_type="composition",
                        name=edge_name,
                        directional=True,
                    )
                )

            # Recursively export child
            target_bound = edge.g().bind(node=target)
            self._export_node(target_bound, parent_id=node_id, depth=depth + 1)

        # Process trait edges
        for edge in trait_edges:
            target = edge.edge().target()
            target_uuid = target.get_uuid()
            target_id = self._make_node_id(target_uuid)
            edge_key = (uuid, target_uuid, "trait")

            if edge_key not in self.visited_edges:
                self.visited_edges.add(edge_key)
                self.edges.append(
                    ExportedEdge(
                        id=self._make_edge_id(),
                        source=node_id,
                        target=target_id,
                        edge_type="trait",
                        name=None,
                        directional=True,
                    )
                )

            # Export trait node
            target_bound = edge.g().bind(node=target)
            self._export_node(target_bound, parent_id=node_id, depth=depth + 1)

        # Process pointer edges
        ptr_edges: list[graph.BoundEdge] = []

        def collect_ptr(ctx: list, edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgePointer.visit_pointed_edges(
            bound_node=bound_node, ctx=ptr_edges, f=collect_ptr
        )

        for edge in ptr_edges:
            target = edge.edge().target()
            target_uuid = target.get_uuid()
            target_id = self._make_node_id(target_uuid)
            edge_key = (uuid, target_uuid, "pointer")

            if edge_key not in self.visited_edges:
                self.visited_edges.add(edge_key)
                self.edges.append(
                    ExportedEdge(
                        id=self._make_edge_id(),
                        source=node_id,
                        target=target_id,
                        edge_type="pointer",
                        name=None,
                        directional=True,
                    )
                )

        # Process connection edges
        conn_edges: list[graph.BoundEdge] = []

        def collect_conn(ctx: list, edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgeInterfaceConnection.visit_connected_edges(
            bound_node=bound_node, ctx=conn_edges, f=collect_conn
        )

        for edge in conn_edges:
            other = fbrk.EdgeInterfaceConnection.get_other_connected_node(
                edge=edge.edge(), node=bound_node.node()
            )
            if other is not None and other != bound_node.node():
                other_uuid = other.get_uuid()
                other_id = self._make_node_id(other_uuid)
                # For undirected edges, use sorted key to avoid duplicates
                edge_key = tuple(sorted([uuid, other_uuid])) + ("connection",)

                if edge_key not in self.visited_edges:
                    self.visited_edges.add(edge_key)
                    self.edges.append(
                        ExportedEdge(
                            id=self._make_edge_id(),
                            source=node_id,
                            target=other_id,
                            edge_type="connection",
                            name=None,
                            directional=False,
                        )
                    )

        # Process operand edges
        op_edges: list[graph.BoundEdge] = []

        def collect_op(ctx: list, edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgeOperand.visit_operand_edges(
            bound_node=bound_node, ctx=op_edges, f=collect_op
        )

        for edge in op_edges:
            target = edge.edge().target()
            target_uuid = target.get_uuid()
            target_id = self._make_node_id(target_uuid)
            edge_key = (uuid, target_uuid, "operand")

            if edge_key not in self.visited_edges:
                self.visited_edges.add(edge_key)
                self.edges.append(
                    ExportedEdge(
                        id=self._make_edge_id(),
                        source=node_id,
                        target=target_id,
                        edge_type="operand",
                        name=None,
                        directional=True,
                    )
                )

        return node_id

    def export(self, root: graph.BoundNode) -> dict[str, Any]:
        """Export the graph starting from root to a dictionary."""
        # Reset state
        self.nodes = {}
        self.edges = []
        self.visited_nodes = set()
        self.visited_edges = set()
        self.edge_counter = 0

        # Export starting from root
        root_id = self._export_node(root)

        # Build output
        return {
            "version": "1.0.0",
            "metadata": {
                "rootNodeId": root_id,
                "totalNodes": len(self.nodes),
                "totalEdges": len(self.edges),
            },
            "edgeTypes": {
                k: {
                    "id": i,
                    "name": v["name"],
                    "color": v["color"],
                    "directional": v["directional"],
                    "description": v["description"],
                }
                for i, (k, v) in enumerate(EDGE_TYPES.items())
            },
            "nodes": [
                {
                    "id": n.id,
                    "uuid": n.uuid,
                    "typeName": n.type_name,
                    "name": n.name,
                    "parentId": n.parent_id,
                    "depth": n.depth,
                    "traits": n.traits,
                    "attributes": n.attributes,
                    "childCount": n.child_count,
                    "traitCount": n.trait_count,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    "type": e.edge_type,
                    "name": e.name,
                    "directional": e.directional,
                }
                for e in self.edges
            ],
        }


def export_graph_to_json(
    root: graph.BoundNode, output_path: str | Path | None = None
) -> dict[str, Any]:
    """
    Export an instance graph to JSON format.

    Args:
        root: The root BoundNode of the graph to export.
        output_path: Optional path to write JSON file. If None, returns dict only.

    Returns:
        Dictionary containing the exported graph data.
    """
    exporter = GraphExporter()
    data = exporter.export(root)

    # Sanitize data to handle Infinity, NaN, and other non-JSON values
    data = _sanitize_for_json(data)

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=_json_serializer)
        logger.info(f"Exported graph to {path}")

    return data


def export_module_to_json(
    module_cls: type, output_path: str | Path | None = None
) -> dict[str, Any]:
    """
    Export a module class to JSON by instantiating it.

    Args:
        module_cls: The module class to instantiate and export.
        output_path: Optional path to write JSON file.

    Returns:
        Dictionary containing the exported graph data.
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    instance = module_cls.bind_typegraph(tg=tg).create_instance(g=g)
    return export_graph_to_json(instance.instance, output_path)


if __name__ == "__main__":
    import sys

    from faebryk.library import _F as F

    # Quick test
    output_dir = Path(__file__).parent.parent.parent.parent / "build" / "graphs"
    output_dir.mkdir(parents=True, exist_ok=True)

    modules = [
        ("Electrical", F.Electrical),
        ("Resistor", F.Resistor),
        ("Capacitor", F.Capacitor),
        ("ElectricPower", F.ElectricPower),
        ("I2C", F.I2C),
        ("ResistorVoltageDivider", F.ResistorVoltageDivider),
    ]

    for name, cls in modules:
        output_path = output_dir / f"{name.lower()}.json"
        print(f"Exporting {name}...", end=" ")
        try:
            data = export_module_to_json(cls, output_path)
            print(f"OK ({data['metadata']['totalNodes']} nodes, {data['metadata']['totalEdges']} edges)")
        except Exception as e:
            print(f"ERROR: {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
