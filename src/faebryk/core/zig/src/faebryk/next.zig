const graph_mod = @import("graph");
const std = @import("std");
const edgebuilder_mod = @import("edgebuilder.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;

pub const EdgeNext = struct {
    pub const tid: Edge.EdgeType = graph.Edge.hash_edge_type(1759356969);
    pub var registered: bool = false;

    pub fn init(previous_node: NodeReference, next_node: NodeReference) EdgeReference {
        const edge = Edge.init(previous_node, next_node, tid);
        build().apply_to(edge);
        return edge;
    }

    pub fn build() EdgeCreationAttributes {
        if (!registered) {
            @branchHint(.unlikely);
            registered = true;
            Edge.register_type(tid) catch {};
        }
        return .{
            .edge_type = tid,
            .directional = true,
            .name = null,
            .dynamic = graph.DynamicAttributes.init(),
        };
    }

    pub fn add_next(bound_previous_node: graph.BoundNodeReference, bound_next_node: graph.BoundNodeReference) graph.BoundEdgeReference {
        const link = EdgeNext.init(bound_previous_node.node, bound_next_node.node);
        const bound_edge = bound_previous_node.g.insert_edge(link);
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

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();

    // init ---------------------------------------------------------------------------------------
    const en12 = EdgeNext.init(bn1.node, bn2.node);

    const ben12 = g.insert_edge(en12);

    // add_next -----------------------------------------------------------------------------------
    const ben23 = EdgeNext.add_next(bn2, bn3);

    // is_instance -------------------------------------------------------------------------------
    try std.testing.expect(EdgeNext.is_instance(ben12.edge));
    try std.testing.expect(EdgeNext.is_instance(ben23.edge));

    // get_previous_node -------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeNext.get_previous_node(ben12.edge).?, bn1.node));
    try std.testing.expect(Node.is_same(EdgeNext.get_previous_node(ben23.edge).?, bn2.node));

    // get_next_node -----------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeNext.get_next_node(ben12.edge).?, bn2.node));
    try std.testing.expect(Node.is_same(EdgeNext.get_next_node(ben23.edge).?, bn3.node));

    // get_previous_edge --------------------------------------------------------------------------
    try std.testing.expect(Edge.is_same(EdgeNext.get_previous_edge(bn2).?.edge, ben12.edge));
    try std.testing.expect(Edge.is_same(EdgeNext.get_previous_edge(bn3).?.edge, ben23.edge));

    // get_next_edge ------------------------------------------------------------------------------
    try std.testing.expect(Edge.is_same(EdgeNext.get_next_edge(bn1).?.edge, ben12.edge));
    try std.testing.expect(Edge.is_same(EdgeNext.get_next_edge(bn2).?.edge, ben23.edge));

    // get_next_node_from_node --------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeNext.get_next_node_from_node(bn1).?, bn2.node));
    try std.testing.expect(Node.is_same(EdgeNext.get_next_node_from_node(bn2).?, bn3.node));

    // get_previous_node_from_node ----------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeNext.get_previous_node_from_node(bn2).?, bn1.node));
    try std.testing.expect(Node.is_same(EdgeNext.get_previous_node_from_node(bn3).?, bn2.node));

    // has to be deleted first
    defer g.deinit();
}
