const std = @import("std");
const graph = @import("graph.zig");
const visitor = @import("visitor.zig");

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const BoundNodeReference = graph.BoundNodeReference;
const BoundEdgeReference = graph.BoundEdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

pub const Path = struct {
    path: []const EdgeReference,
};

const Ctx = struct {
    visited: graph.EdgeRefMap.T(void),
    // TODO in zig 0.15 there are std.deque, use that instead
    open_path_queue: std.ArrayList(Path),
    visit_ctx: *anyopaque,
    visit: fn (*anyopaque, Path) visitor.VisitResult(void),

    fn handle_path(self: *@This(), path: *Path) visitor.VisitResult(void) {
        // 1. Call visit
        // 2. Check if stop
        // 3. Check if filtered
        // 4. Mark visited
        // 5. Put into open_path_queue

    }
};

fn bfs_visit(
    source: BoundNodeReference,
    destinations: []const NodeReference,
    ctx: *anyopaque,
    visit: fn (*anyopaque, Path) visitor.VisitResult(void),
) visitor.VisitResult(void) {
    const ctx = Ctx{
        .visited = graph.EdgeRefMap.T(void).init(source.g.allocator),
        .open_path_queue = std.ArrayList(Path).init(source.g.allocator),
        .visit_ctx = ctx,
        .visit = visit,
    };

    // 1. Induction Start
    // 1.1. Get all edges of type InterfaceConnection from source
    // 1.2. Call for each handle_path
    // 2. Induction step
    // 2.1 Pop from open_path_queue
    // 2.2 Get all edges of type InterfaceConnection from the popped path
    // 2.3 Check if visited
    // 2.4 If not visited, call handle_path

}

pub fn find_paths(source: BoundNodeReference, destinations: []const NodeReference) ![]const Path {
    //
}
