const std = @import("std");
const graph = @import("graph").graph;
const visitor = @import("graph").visitor;

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
    // visited: graph.EdgeRefMap.T(void),
    visited: std.ArrayList(EdgeReference),
    // TODO in zig 0.15 there are std.deque, use that instead
    open_path_queue: std.ArrayList(Path),
    visit_ctx: *anyopaque,
    visit_fn: *const fn (*anyopaque, Path) visitor.VisitResult(void),

    fn handle_path(self: *@This(), path: *Path) visitor.VisitResult(void) {
        // 1. Call visit

        _ = self;
        _ = path;

        // 2. Check if stop
        // 3. Check if filtered
        // 4. Mark visited
        // 5. Put into open_path_queue

    }
};

fn bfs_visit(
    source: BoundNodeReference,
    // destinations: []const NodeReference,
    visit_ctx: *anyopaque,
    visit_fn: *const fn (*anyopaque, Path) visitor.VisitResult(void),
) visitor.VisitResult(void) {
    const Visit = Ctx{
        // .visited = graph.EdgeRefMap.T(void).init(source.g.allocator),
        .visited = std.ArrayList(EdgeReference).init(source.g.allocator),
        .open_path_queue = std.ArrayList(Path).init(source.g.allocator),
        .visit_ctx = visit_ctx,
        .visit_fn = visit_fn,
    };

    _ = Visit;

    // 1. Induction Start
    // 1.1. Get all edges of type InterfaceConnection from source
    // 1.2. Call for each handle_path
    // 2. Induction step
    // 2.1 Pop from open_path_queue
    // 2.2 Get all edges of type InterfaceConnection from the popped path
    // 2.3 Check if visited
    // 2.4 If not visited, call handle_path
}

pub fn find_paths(source: BoundNodeReference, a: std.mem.Allocator) ![]const Path {
    const FindPaths = struct {
        path_list: std.ArrayList(Path),

        pub fn visit_fn(self_ptr: *anyopaque, path: Path) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(self_ptr));

            self.path_list.append(path) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var visit_ctx = FindPaths{ .path_list = std.ArrayList(Path).init(a) };
    defer visit_ctx.path_list.deinit();

    const result = bfs_visit(source, &visit_ctx, FindPaths.visit_fn);
    _ = result;
}

test "basic" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    const n1 = try Node.init(a);
    defer n1.deinit();
    defer g.deinit();

    const bn1 = try g.insert_node(n1);

    _ = try find_paths(bn1, a);
    // _ = bn1;
}
