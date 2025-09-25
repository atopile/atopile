const graph = @import("graph.zig");
const std = @import("std");
const visitor = @import("visitor.zig");

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

pub const EdgePointer = struct {
    var tid: ?Edge.Type = null;

    // TODO (see graph.zig)
    fn get_tid() Edge.Type {
        if (tid == null) {
            tid = Edge.register_type();
        }
        return tid.?;
    }

    pub fn init(allocator: std.mem.Allocator, from: NodeReference, to: NodeReference, identifier: str) !EdgeReference {
        const edge = try Edge.init(allocator, from, to, get_tid());
        edge.directional = true;
        edge.name = identifier;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, get_tid());
    }
};
