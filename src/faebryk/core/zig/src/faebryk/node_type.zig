const graph_mod = @import("graph");
const std = @import("std");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

pub const EdgeType = struct {
    var tid: Edge.EdgeType = 1759273701;

    pub fn init(allocator: std.mem.Allocator, type_node: NodeReference, instance_node: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, type_node, instance_node, tid);
        edge.attributes.directional = true;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_type_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_node, tid, false);
    }

    pub fn is_node_instance_of(bound_node: graph.BoundNodeReference, node_type: NodeReference) bool {
        const type_edge = get_type_edge(bound_node);
        if (type_edge) |edge| {
            if (edge.edge.get_target()) |target| {
                return Node.is_same(target, node_type);
            }
        }
        return false;
    }
};

test "basic" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const tn1 = try Node.init(a);
    const tn2 = try Node.init(a);

    const bn1 = try g.insert_node(n1);
    const bn2 = try g.insert_node(n2);
    _ = try g.insert_node(tn1);
    _ = try g.insert_node(tn2);

    const et11 = try EdgeType.init(a, tn1, n1);
    const et12 = try EdgeType.init(a, tn1, n2);

    try std.testing.expect(EdgeType.is_node_instance_of(bn1, tn1));
    try std.testing.expect(EdgeType.is_node_instance_of(bn2, tn1));
    try std.testing.expect(!EdgeType.is_node_instance_of(bn1, tn2));
    try std.testing.expect(!EdgeType.is_node_instance_of(bn2, tn2));

    g.deinit();
    try n1.deinit();
    try n2.deinit();
    try tn1.deinit();
    try tn2.deinit();
    try et11.deinit();
    try et12.deinit();
}
