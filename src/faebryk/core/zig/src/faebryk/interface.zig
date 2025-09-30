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

    pub fn init(allocator: std.mem.Allocator, from: NodeReference, to: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, from, to, tid);
        edge.directional = false;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn list_connections(E: EdgeReference) []NodeReference {
        return .{ E.source, E.target };
    }

    // get other side of connection given a node and edge
    pub fn get_connected(E: EdgeReference, N: NodeReference) NodeReference {
        if (Node.is_same(E.source, N)) {
            return E.target;
        }
        return E.source;
    }

    // connect given edge to given 2 nodereferences
    pub fn connect(E: EdgeReference, N1: NodeReference, N2: NodeReference) EdgeReference {
        E.source = N1;
        E.target = N2;
        return E;
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
