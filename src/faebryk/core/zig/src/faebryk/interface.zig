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
        const edge = try Edge.init(allocator, from, to, get_tid());
        edge.directional = false;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, get_tid());
    }

    pub fn get_connections(E: EdgeReference) []NodeReference {
        return .{ E.source, E.target };
    }

    // get other side of connection given a node

    // create edge given 2 nodes (connect)

    // visit all connected edges for a given node

    // visit all paths for a given node (pathfinder)

    // "shallow" links
};
