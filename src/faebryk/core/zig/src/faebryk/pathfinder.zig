const std = @import("std");
const graph_mod = @import("graph");
const composition_mod = @import("composition.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const Node = graph.Node;
const Edge = graph.Edge;
const Path = graph.Path;
const BFSPath = graph.BFSPath;
const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const BoundNodeReference = graph.BoundNodeReference;
const BoundEdgeReference = graph.BoundEdgeReference;
const GraphView = graph.GraphView;
const NodeRefMap = graph.NodeRefMap;
const EdgeComposition = composition_mod.EdgeComposition;

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    path_list: ?std.ArrayList(BFSPath) = null, // Valid complete paths (plain paths without metadata)
    end_nodes: ?std.ArrayList(BoundNodeReference) = null, // End nodes to search for (optional)
    path_counter: u64 = 0, // Counters for statistics
    valid_path_counter: u64 = 0, // Count of valid complete paths

    pub fn init(allocator: std.mem.Allocator) PathFinder {
        return .{
            .allocator = allocator,
            .path_list = null,
            .end_nodes = null,
            .path_counter = 0,
            .valid_path_counter = 0,
        };
    }

    pub fn deinit(self: *Self) void {
        if (self.path_list) |*list| {
            for (list.items) |*path| {
                path.deinit();
            }
            list.deinit();
            self.path_list = null;
        }

        if (self.end_nodes) |*list| {
            list.deinit();
            self.end_nodes = null;
        }
    }

    // Find all valid paths between start and end nodes
    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
        end_nodes: ?[]const BoundNodeReference,
    ) ![]const BFSPath {
        self.deinit();

        // Re-initialize lists
        self.path_list = std.ArrayList(BFSPath).init(self.allocator);
        self.end_nodes = std.ArrayList(BoundNodeReference).init(self.allocator);

        if (end_nodes) |nodes| {
            try self.end_nodes.?.ensureTotalCapacity(nodes.len);
            self.end_nodes.?.appendSliceAssumeCapacity(nodes);
        }

        // Reset counters
        self.path_counter = 0;
        self.valid_path_counter = 0;

        // Run BFS with our visitor callback
        const result = start_node.g.visit_paths_bfs(
            start_node,
            void,
            self,
            Self.visit_fn,
        );
        _ = result;

        return self.path_list.?.items;
    }

    // BFS visitor callback
    pub fn visit_fn(self_ptr: *anyopaque, path: *BFSPath) visitor.VisitResult(void) {
        const self: *Self = @ptrCast(@alignCast(self_ptr));

        // Run filters on path
        const result = self.run_filters(path);

        // Filter says keep!
        if (!path.filtered) {
            // Deep copy the path
            var copied_path = BFSPath{
                .path = Path.init(path.path.g),
                .filtered = false,
                .stop = false,
            };
            copied_path.path.edges.appendSlice(path.path.edges.items) catch |err| {
                copied_path.deinit();
                return visitor.VisitResult(void){ .ERROR = err };
            };
            copied_path.filtered = path.filtered;
            copied_path.stop = path.stop;

            self.path_list.?.append(copied_path) catch |err| {
                copied_path.deinit();
                return visitor.VisitResult(void){ .ERROR = err };
            };
            self.valid_path_counter += 1;
        }
        // Filter says don't keep - BFS will deinitialize

        // Filter says shut it down!
        if (result == .STOP) {
            std.debug.print("STOP BFS!!! - Filter stopped\n", .{});
            return visitor.VisitResult(void){ .STOP = {} };
        }

        // Check if path ends in an end node
        if (self.end_nodes) |*end_nodes| {
            for (end_nodes.items, 0..) |end_node, i| {
                if (path.path.get_other_node(end_node)) |_| {
                    _ = end_nodes.swapRemove(i);

                    // If all end nodes found, stop the search
                    if (end_nodes.items.len == 0) {
                        std.debug.print("STOP BFS!!! - All end nodes found\n", .{});
                        return visitor.VisitResult(void){ .STOP = {} };
                    }
                    break;
                }
            }
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn run_filters(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        std.debug.print("FILTERS\n", .{});
        for (filters) |filter| {
            std.debug.print("{s:<32}", .{filter.name});
            const result = filter.func(self, path);
            std.debug.print("filtered:{} stop:{}\n", .{ path.filtered, path.stop });
            switch (result) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(void){ .STOP = {} },
                .ERROR => |err| return visitor.VisitResult(void){ .ERROR = err },
                .OK => |value| return visitor.VisitResult(void){ .OK = value },
                .EXHAUSTED => return visitor.VisitResult(void){ .EXHAUSTED = {} },
            }
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // Filters
    const filters = [_]struct {
        name: []const u8,
        func: *const fn (*Self, *BFSPath) visitor.VisitResult(void),
    }{
        .{ .name = "count_paths", .func = Self.count_paths },
        .{ .name = "filter_path_by_edge_type", .func = Self.filter_path_by_edge_type },
        .{ .name = "filter_path_by_node_type", .func = Self.filter_path_by_node_type },
        .{ .name = "filter_siblings", .func = Self.filter_siblings },
        .{ .name = "filter_heirarchy_stack", .func = Self.filter_heirarchy_stack },
    };

    pub fn count_paths(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = path;
        self.path_counter += 1;
        std.debug.print("path_counter: {}", .{self.path_counter});
        if (self.path_counter > 10) {
            return visitor.VisitResult(void){ .STOP = {} };
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // TODO this can be optimized, we don't really need to iterate through the entire edge list, just the first and last
    pub fn filter_path_by_edge_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        for (path.path.edges.items) |edge| {
            if (edge.attributes.edge_type != 1759242069) {
                std.debug.print("{} != 1759242069", .{edge.attributes.uuid});
                path.stop = true;
                path.filtered = true;
            }
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_node_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        _ = path;
        // waiting on type graph implementation for node types
        // var first_node = path.path.get_first_node();
        // var last_node = path.path.get_last_node();

        // if (last_node.?.node.attributes.dynamic.values.get("node type") != first_node.?.node.attributes.dynamic.values.get("node type")) {
        //     path.filtered = true;
        // }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // formerly known as filter_path_by_dead_end_split
    // filters out paths where the last 2 edges represent a child -> parent -> child path
    pub fn filter_siblings(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;

        const edges = path.path.edges.items;
        if (edges.len < 2) {
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
        const last_edges = [_]EdgeReference{
            edges[edges.len - 1],
            edges[edges.len - 2],
        };
        // check that all edges are heirarchy edges
        for (last_edges) |edge| {
            if (edge.attributes.edge_type != EdgeComposition.tid) {
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        }
        // check that the connections are child -> parent -> child
        const edge_1_and_edge_2_share_parent = graph.Node.is_same(EdgeComposition.get_parent_node(last_edges[0]), EdgeComposition.get_parent_node(last_edges[1]));
        if (edge_1_and_edge_2_share_parent) {
            path.filtered = true;
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // the goal here is everytime we cross a composition edge, we track what type of heirarchy it is and add it to a stack.
    // then as we start going the oppisite hiearchy direction, we decrement the heiarchy stack
    // the idea is to ensure start and end node are at the same level of heirarchy
    pub fn filter_heirarchy_stack(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;

        var hierarchy_stack = std.ArrayList(u64).init(path.path.g.allocator);

        for (path.path.edges.items) |edge| {
            if (edge.attributes.edge_type == EdgeComposition.tid) {
                hierarchy_stack.append(edge.attributes.uuid) catch |err| {
                    return visitor.VisitResult(void){ .ERROR = err };
                };
            }
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }
};

// Test from graph.zig - basic pathfinding with end nodes
test "visit_paths_bfs" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);
    const n4 = try Node.init(a);
    const n5 = try Node.init(a);
    const n6 = try Node.init(a);
    const n7 = try Node.init(a);
    const e1 = try Edge.init(a, n1, n2, 1759242069);
    const e2 = try Edge.init(a, n1, n3, 1759242069);
    const e3 = try Edge.init(a, n2, n4, 1759242068);
    const e4 = try Edge.init(a, n2, n5, 1759242069);
    const e5 = try Edge.init(a, n5, n6, 1759242069);
    const e6 = try Edge.init(a, n6, n1, 1759242069);
    const e7 = try Edge.init(a, n4, n7, 1759242069);
    n1.attributes.uuid = 1001;
    n2.attributes.uuid = 1002;
    n3.attributes.uuid = 1003;
    n4.attributes.uuid = 1004;
    n5.attributes.uuid = 1005;
    n6.attributes.uuid = 1006;
    n7.attributes.uuid = 1007;
    e1.attributes.uuid = 2001;
    e2.attributes.uuid = 2002;
    e3.attributes.uuid = 2003;
    e4.attributes.uuid = 2004;
    e5.attributes.uuid = 2005;
    e6.attributes.uuid = 2006;
    e7.attributes.uuid = 2007;
    defer g.deinit();

    const bn1 = try g.insert_node(n1);
    const bn2 = try g.insert_node(n2);
    const bn4 = try g.insert_node(n4);
    _ = try g.insert_node(n3);
    _ = try g.insert_node(n5);
    _ = try g.insert_node(n6);
    _ = try g.insert_node(n7);
    _ = try g.insert_edge(e1);
    _ = try g.insert_edge(e2);
    _ = try g.insert_edge(e3);
    _ = try g.insert_edge(e4);
    _ = try g.insert_edge(e5);
    _ = try g.insert_edge(e6);
    _ = try g.insert_edge(e7);

    var pf1 = PathFinder.init(a);
    defer pf1.deinit();

    _ = bn2;
    _ = bn4;

    const end_nodes = [_]BoundNodeReference{};

    const paths1 = try pf1.find_paths(bn1, &end_nodes);
    std.debug.print("\nTEST\nFound {} paths:\n", .{paths1.len});

    // Print paths for debugging
    for (paths1) |path| {
        path.path.print_path();
    }
}
