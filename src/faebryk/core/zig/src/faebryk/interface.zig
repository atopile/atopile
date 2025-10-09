const graph = @import("graph").graph;
const std = @import("std");
const visitor = @import("graph").visitor;

// pub const pathfinder = @import("interface_pathfinder/pathfinder.zig");

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

const shallow_link = "shallow_link";

pub const EdgeInterfaceConnection = struct {
    const tid: Edge.EdgeType = 1759242069;

    pub fn init(allocator: std.mem.Allocator, N1: NodeReference, N2: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, N1, N2, tid);
        edge.attributes.directional = false; // interface connections are not directional
        edge.attributes.dynamic.values.put(shallow_link, graph.Literal{ .Bool = false }) // interfaces connections can be shallow but are not by default
        catch |err| {
            return err;
        };
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_both_connected_nodes(E: EdgeReference) [2]NodeReference {
        return [_]NodeReference{ E.source, E.target };
    }

    // Get other connected node given an already connected node and edge reference
    pub fn get_other_connected_node(E: EdgeReference, N: NodeReference) ?NodeReference {
        if (Node.is_same(E.source, N)) {
            return E.target;
        } else if (Node.is_same(E.target, N)) {
            return E.source;
        } else {
            return null; // Returns null if given node and edge were not connected in the first place
        }
    }

    // Connect given EdgeReference to given 2 NodeReferences
    pub fn connect(E: EdgeReference, N1: NodeReference, N2: NodeReference) void {
        E.source = N1;
        E.target = N2;
        return;
    }

    // visit all connected edges for a given node
    pub fn visit_connected_edges(
        bound_node: graph.BoundNodeReference,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),
    ) visitor.VisitResult(void) {
        const Visit = struct {
            target: graph.BoundNodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const connected = EdgeInterfaceConnection.get_other_connected_node(bound_edge.edge, self.target.node);
                if (connected) |_| {
                    const connected_result = self.cb(self.cb_ctx, bound_edge);
                    switch (connected_result) {
                        .CONTINUE => {},
                        else => return connected_result,
                    }
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .target = bound_node, .cb_ctx = ctx, .cb = f };
        return bound_node.visit_edges_of_type(tid, void, &visit, Visit.visit);
    }

    // visit all paths for a given node (pathfinder)

    // "shallow" links
};

test "basic" {
    // Allocate some nodes and edges
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);
    const e1 = try EdgeInterfaceConnection.init(a, n1, n2);
    defer g.deinit(); // Graph owns all inserted nodes/edges and handles their cleanup

    // Expect e1 source and target to match n1 and n2
    try std.testing.expect(Node.is_same(e1.source, n1));
    try std.testing.expect(Node.is_same(e1.target, n2));

    // Expect e1 source and target to not match n3
    try std.testing.expect(!Node.is_same(e1.source, n3));
    try std.testing.expect(!Node.is_same(e1.target, n3));

    // Expect list of 2 connections that reference n1 and n2
    const n_list = EdgeInterfaceConnection.get_both_connected_nodes(e1);
    try std.testing.expectEqual(n_list.len, 2);
    try std.testing.expect(Node.is_same(n_list[0], n1));
    try std.testing.expect(Node.is_same(n_list[1], n2));

    // Expect get_connected to return n2 when given n1
    try std.testing.expect(Node.is_same(EdgeInterfaceConnection.get_other_connected_node(e1, n1).?, n2));

    // Expect get_connected to return n1 when given n2
    try std.testing.expect(Node.is_same(EdgeInterfaceConnection.get_other_connected_node(e1, n2).?, n1));

    // Expect get_connected to return null when given n3
    try std.testing.expect(EdgeInterfaceConnection.get_other_connected_node(e1, n3) == null);

    // Take e1 and connect source to n1 and target to n3
    EdgeInterfaceConnection.connect(e1, n1, n3);
    try std.testing.expect(Node.is_same(e1.source, n1));
    try std.testing.expect(Node.is_same(e1.target, n3));

    // Expect no connections to n2 anymore
    try std.testing.expect(EdgeInterfaceConnection.get_other_connected_node(e1, n2) == null);

    // Insert n1, n2, n3 into GraphView g
    const bn1 = try g.insert_node(n1);
    _ = try g.insert_node(n2);
    _ = try g.insert_node(n3);
    _ = try g.insert_edge(e1);

    // define visitor that visits all edges connected to n1 in g and saves the EdgeReferences to a list (connected_edges)
    const CollectConnectedEdges = struct {
        connected_edges: std.ArrayList(graph.BoundEdgeReference),

        pub fn visit(self_ptr: *anyopaque, connected_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(self_ptr));

            self.connected_edges.append(connected_edge) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };

            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    // instantiate visitor
    var visit = CollectConnectedEdges{ .connected_edges = std.ArrayList(graph.BoundEdgeReference).init(a) };
    defer visit.connected_edges.deinit();
    // call visitor
    const result = EdgeInterfaceConnection.visit_connected_edges(bn1, &visit, CollectConnectedEdges.visit);
    _ = result;

    // check the visitor is correct
    try std.testing.expectEqual(visit.connected_edges.items.len, 1);
    try std.testing.expect(Node.is_same(visit.connected_edges.items[0].edge.source, n1));
    try std.testing.expect(Node.is_same(visit.connected_edges.items[0].edge.target, n3));
}
