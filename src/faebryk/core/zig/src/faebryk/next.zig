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

pub const EdgeNext = struct {
    pub var tid: Edge.EdgeType = 1759356969;

    pub fn init(allocator: std.mem.Allocator, previous_node: NodeReference, next_node: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, previous_node, next_node, tid);
        edge.attributes.directional = true;
        return edge;
    }

    pub fn add_next(bound_previous_node: graph.BoundNodeReference, bound_next_node: graph.BoundNodeReference) !graph.BoundEdgeReference {
        const link = try EdgeNext.init(bound_previous_node.g.allocator, bound_previous_node.node, bound_next_node.node);
        const bound_edge = try bound_previous_node.g.insert_edge(link);
        return bound_edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_previous_node(E: EdgeReference) ?NodeReference {
        return E.source;
    }

    pub fn get_next_node(E: EdgeReference) ?NodeReference {
        return E.target;
    }

    pub fn get_previous_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_node, tid, true);
    }

    pub fn get_next_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_node, tid, false);
    }

    pub fn get_next_node_from_node(bound_node: graph.BoundNodeReference) ?NodeReference {
        const bedge = get_next_edge(bound_node);
        if (bedge) |b| {
            return b.edge.target;
        }
        return null;
    }

    pub fn get_previous_node_from_node(bound_node: graph.BoundNodeReference) ?NodeReference {
        const bedge = get_previous_edge(bound_node);
        if (bedge) |b| {
            return b.edge.source;
        }
        return null;
    }
};

//zig test --dep graph -Mroot=src/faebryk/next.zig -Mgraph=src/graph/lib.zig
test "basic chain" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    const node1 = try Node.init(a);
    defer node1.deinit();
    const node2 = try Node.init(a);
    defer node2.deinit();
    const node3 = try Node.init(a);
    defer node3.deinit();

    const bn1 = try g.insert_node(node1);
    const bn2 = try g.insert_node(node2);
    const bn3 = try g.insert_node(node3);

    // init ---------------------------------------------------------------------------------------
    const en12 = try EdgeNext.init(g.allocator, node1, node2);
    std.debug.print("en12 source: {}\n", .{EdgeNext.get_previous_node(en12).?});
    std.debug.print("en12 target: {}\n", .{EdgeNext.get_next_node(en12).?});
    defer en12.deinit();
    const ben12 = try g.insert_edge(en12);

    // add_next -----------------------------------------------------------------------------------
    const ben23 = try EdgeNext.add_next(bn2, bn3);
    std.debug.print("en23 source: {}\n", .{EdgeNext.get_previous_node(ben23.edge).?});
    std.debug.print("en23 target: {}\n", .{EdgeNext.get_next_node(ben23.edge).?});
    defer ben23.edge.deinit();

    // is_instance -------------------------------------------------------------------------------
    try std.testing.expect(EdgeNext.is_instance(ben12.edge));
    try std.testing.expect(EdgeNext.is_instance(ben23.edge));

    // get_previous_node -------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeNext.get_previous_node(ben12.edge).?, node1));
    try std.testing.expect(Node.is_same(EdgeNext.get_previous_node(ben23.edge).?, node2));

    // get_next_node -----------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeNext.get_next_node(ben12.edge).?, node2));
    try std.testing.expect(Node.is_same(EdgeNext.get_next_node(ben23.edge).?, node3));

    // get_previous_edge --------------------------------------------------------------------------
    try std.testing.expect(Edge.is_same(EdgeNext.get_previous_edge(bn2).?.edge, ben12.edge));
    try std.testing.expect(Edge.is_same(EdgeNext.get_previous_edge(bn3).?.edge, ben23.edge));

    // get_next_edge ------------------------------------------------------------------------------
    try std.testing.expect(Edge.is_same(EdgeNext.get_next_edge(bn1).?.edge, ben12.edge));
    try std.testing.expect(Edge.is_same(EdgeNext.get_next_edge(bn2).?.edge, ben23.edge));

    // get_next_node_from_node --------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeNext.get_next_node_from_node(bn1).?, node2));
    try std.testing.expect(Node.is_same(EdgeNext.get_next_node_from_node(bn2).?, node3));

    // get_previous_node_from_node ----------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeNext.get_previous_node_from_node(bn2).?, node1));
    try std.testing.expect(Node.is_same(EdgeNext.get_previous_node_from_node(bn3).?, node2));

    // has to be deleted first
    defer g.deinit();
}
