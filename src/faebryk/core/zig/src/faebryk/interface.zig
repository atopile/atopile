const graph = @import("graph").graph;
const std = @import("std");
const visitor = graph.visitor;

// pub const pathfinder = @import("interface_pathfinder/pathfinder.zig");

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

pub const EdgeInterfaceConnection = struct {
    const tid: Edge.Type = 1759242069;

    pub fn get_tid() Edge.Type {
        return tid;
    }

    pub fn init(allocator: std.mem.Allocator, N1: NodeReference, N2: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, N1, N2, tid);
        edge.directional = false;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn list_connections(E: EdgeReference) [2]NodeReference {
        return [_]NodeReference{ E.source, E.target };
    }

    // get other side of connection given a node and edge
    pub fn get_connected(E: EdgeReference, N: NodeReference) NodeReference {
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
    ) visitor.VisitResult(void) {
        return bound_node.visit_edges_of_type(tid);
    }

    // visit all paths for a given node (pathfinder)

    // "shallow" links
};

test "basic" {
    const a = std.testing.allocator;
    const n1 = try Node.init(a);
    defer _ = n1.deinit() catch {};
    const n2 = try Node.init(a);
    defer _ = n2.deinit() catch {};
    const n3 = try Node.init(a);
    defer _ = n3.deinit() catch {};

    std.debug.print("n1.uuid = {}\n", .{n1.uuid});
    std.debug.print("n2.uuid = {}\n", .{n2.uuid});
    std.debug.print("n3.uuid = {}\n", .{n3.uuid});

    const e1 = try EdgeInterfaceConnection.init(a, n1, n2);
    defer _ = e1.deinit() catch {};

    std.debug.print("e1.uuid = {}\n", .{e1.uuid});
    std.debug.print("e1.source.uuid = {}\n", .{e1.source.uuid});
    std.debug.print("e1.target.uuid = {}\n", .{e1.target.uuid});

    const n_list = EdgeInterfaceConnection.list_connections(e1);

    std.debug.print("n_list.len = {}\n", .{n_list.len});
    std.debug.print("n_list[0].uuid = {}\n", .{n_list[0].uuid});
    std.debug.print("n_list[1].uuid = {}\n", .{n_list[1].uuid});

    EdgeInterfaceConnection.connect(e1, n3, n1);

    std.debug.print("e1.source.uuid = {}\n", .{e1.source.uuid});
    std.debug.print("e1.target.uuid = {}\n", .{e1.target.uuid});
}
