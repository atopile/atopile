const graph = @import("graph.zig");
const std = @import("std");
const visitor = @import("visitor.zig");

pub const pathfinder = @import("interface_pathfinder/pathfinder.zig");

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

pub const EdgeInterfaceConnection = struct {
    var tid: ?Edge.Type = null;

    // TODO (see graph.zig)
    fn get_tid() Edge.Type {
        if (tid == null) {
            tid = Edge.register_type();
        }
        return tid.?;
    }

    pub fn init(allocator: std.mem.Allocator, from: NodeReference, to: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, from, to, get_tid());
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, get_tid());
    }
};
