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

pub const EdgeInterfaceConnection = struct {
    const tid: Edge.EdgeType = 1759242069;

    pub fn init(allocator: std.mem.Allocator, N1: NodeReference, N2: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, N1, N2, tid);
        edge.attributes.directional = false;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn list_connections(E: EdgeReference) [2]NodeReference {
        return [_]NodeReference{ E.source, E.target };
    }

    // get other side of connection given a node and edge
    pub fn get_connected(E: EdgeReference, N: NodeReference) ?NodeReference {
        if (Node.is_same(E.source, N)) {
            return E.target;
        }
        return E.source;
    }

    // connect given edge to given 2 nodereferences
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
                const connected = EdgeInterfaceConnection.get_connected(bound_edge.edge, self.target.node);
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

    // TODO: visit all paths for a given node (pathfinder)
    // TODO: "shallow" links
};

test "basic" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    const n1 = try Node.init(a);
    defer n1.deinit();
    const n2 = try Node.init(a);
    defer n2.deinit();
    const n3 = try Node.init(a);
    defer n3.deinit();
    defer g.deinit(); // Defer AFTER nodes so it runs BEFORE node cleanup

    std.debug.print("n1.uuid = {}\n", .{n1.attributes.uuid});
    std.debug.print("n2.uuid = {}\n", .{n2.attributes.uuid});
    std.debug.print("n3.uuid = {}\n", .{n3.attributes.uuid});

    const e1 = try EdgeInterfaceConnection.init(a, n1, n2);
    defer e1.deinit();

    std.debug.print("e1.uuid = {}\n", .{e1.attributes.uuid});
    std.debug.print("e1.source.uuid = {}\n", .{e1.source.attributes.uuid});
    std.debug.print("e1.target.uuid = {}\n", .{e1.target.attributes.uuid});

    const n_list = EdgeInterfaceConnection.list_connections(e1);

    std.debug.print("n_list.len = {}\n", .{n_list.len});
    std.debug.print("n_list[0].uuid = {}\n", .{n_list[0].attributes.uuid});
    std.debug.print("n_list[1].uuid = {}\n", .{n_list[1].attributes.uuid});

    const n2_ref = EdgeInterfaceConnection.get_connected(e1, n1);
    std.debug.print("n2.uuid = {}\n", .{n2.attributes.uuid});
    std.debug.print("n2_ref.uuid = {}\n", .{n2_ref.?.attributes.uuid});

    EdgeInterfaceConnection.connect(e1, n3, n1);

    std.debug.print("e1.source.uuid = {}\n", .{e1.source.attributes.uuid});
    std.debug.print("e1.target.uuid = {}\n", .{e1.target.attributes.uuid});

    const bn1 = try g.insert_node(n1);

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

    var visit = CollectConnectedEdges{ .connected_edges = std.ArrayList(graph.BoundEdgeReference).init(a) };
    defer visit.connected_edges.deinit();
    const result = EdgeInterfaceConnection.visit_connected_edges(bn1, &visit, CollectConnectedEdges.visit);
    _ = result;
}
