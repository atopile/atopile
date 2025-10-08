const graph_mod = @import("graph");
const std = @import("std");
const composition_mod = @import("composition.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const BoundNodeReference = graph.BoundNodeReference;
const BoundEdgeReference = graph.BoundEdgeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;
const EdgeComposition = composition_mod.EdgeComposition;

pub const EdgePointer = struct {
    pub const tid: Edge.EdgeType = 1759771470;

    pub fn init(allocator: std.mem.Allocator, from: NodeReference, to: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, from, to, tid);
        edge.attributes.directional = true;
        // edge.attributes.name = identifier;
        return edge;
    }

    pub fn get_referenced_node(edge: EdgeReference) ?NodeReference {
        return edge.get_target();
    }

    pub fn get_referenced_node_from_node(bound_reference_node: BoundNodeReference) ?NodeReference {
        const edge = Edge.get_single_edge(bound_reference_node, tid, false);
        if (edge) |e| {
            return e.edge.get_target();
        }
        return null;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }
};

//zig test --dep graph -Mroot=src/faebryk/pointer.zig -Mgraph=src/graph/lib.zig
test "basic" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);

    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const e12 = try EdgePointer.init(a, n1, n2);

    _ = try g.insert_node(n1);
    _ = try g.insert_node(n2);
    _ = try g.insert_edge(e12);

    try std.testing.expect(EdgePointer.is_instance(e12));
    try std.testing.expect(Node.is_same(EdgePointer.get_referenced_node(e12).?, n2));

    g.deinit();
}
