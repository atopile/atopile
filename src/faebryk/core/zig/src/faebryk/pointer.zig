const graph_mod = @import("graph");
const std = @import("std");
const composition_mod = @import("composition.zig");
const edgebuilder_mod = @import("edgebuilder.zig");

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
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;

pub const EdgePointer = struct {
    pub const tid: Edge.EdgeType = 1759771470;

    pub fn init(allocator: std.mem.Allocator, from: NodeReference, to: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, from, to, tid);
        build().apply_to(edge);
        return edge;
    }

    pub fn build() EdgeCreationAttributes {
        return .{
            .edge_type = tid,
            .directional = true,
            .name = null,
            .dynamic = null,
        };
    }

    pub fn get_referenced_node(edge: EdgeReference) ?NodeReference {
        return edge.get_target();
    }

    pub fn get_referenced_node_from_node(bound_reference_node: BoundNodeReference) ?BoundNodeReference {
        const edge = Edge.get_single_edge(bound_reference_node, tid, false);
        if (edge) |e| {
            if (e.edge.get_target()) |target| {
                return bound_reference_node.g.bind(target);
            }
        }
        return null;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn point_to(bound_node: BoundNodeReference, target_node: NodeReference) !BoundEdgeReference {
        const edge = try EdgePointer.init(bound_node.g.allocator, bound_node.node, target_node);
        const bound_edge = try bound_node.g.insert_edge(edge);
        return bound_edge;
    }
};

//zig test --dep graph -Mroot=src/faebryk/pointer.zig -Mgraph=src/graph/lib.zig
test "basic" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);

    const n1 = g.create_and_insert_node();
    const n2 = g.create_and_insert_node();
    const e12 = try EdgePointer.init(a, n1.node, n2.node);

    _ = try g.insert_edge(e12);

    try std.testing.expect(EdgePointer.is_instance(e12));
    try std.testing.expect(Node.is_same(EdgePointer.get_referenced_node(e12).?, n2.node));

    g.deinit();
}
