const std = @import("std");
const graph_mod = @import("graph");
const composition_mod = @import("composition.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const Node = graph.Node;
const Edge = graph.Edge;
const Path = graph.Path;
const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const BoundNodeReference = graph.BoundNodeReference;
const GraphView = graph.GraphView;
const NodeRefMap = graph.NodeRefMap;
const EdgeComposition = composition_mod.EdgeComposition;

/// Extended path with split tracking metadata
pub const PathWithSplits = struct {
    path: Path,
    split_stack: std.ArrayList(SplitPoint),
    unresolved_up_down: std.ArrayList(TraversalStep),
    confidence: f64 = 1.0,
    not_complete: bool = false,
    hibernated: bool = false,

    pub fn init(allocator: std.mem.Allocator, initial_node: NodeReference) PathWithSplits {
        _ = initial_node; // TODO: Use this to initialize path
        const p = Path.init(allocator);
        return .{
            .path = p,
            .split_stack = std.ArrayList(SplitPoint).init(allocator),
            .unresolved_up_down = std.ArrayList(TraversalStep).init(allocator),
            .confidence = 1.0,
            .not_complete = false,
            .hibernated = false,
        };
    }

    pub fn deinit(self: *@This()) void {
        self.path.deinit();
        self.split_stack.deinit();
        self.unresolved_up_down.deinit();
    }

    pub fn clone(self: *const @This(), allocator: std.mem.Allocator) !PathWithSplits {
        var new_path = PathWithSplits{
            .path = Path.init(allocator),
            .split_stack = std.ArrayList(SplitPoint).init(allocator),
            .unresolved_up_down = std.ArrayList(TraversalStep).init(allocator),
            .confidence = self.confidence,
            .not_complete = self.not_complete,
            .hibernated = self.hibernated,
        };

        try new_path.path.edges.appendSlice(self.path.edges.items);
        try new_path.split_stack.appendSlice(self.split_stack.items);
        try new_path.unresolved_up_down.appendSlice(self.unresolved_up_down.items);

        return new_path;
    }
};

/// Represents a point where a path splits into multiple branches
pub const SplitPoint = struct {
    parent_node: NodeReference,
    children: std.ArrayList(NodeReference),

    pub fn init(allocator: std.mem.Allocator, parent: NodeReference) SplitPoint {
        return .{
            .parent_node = parent,
            .children = std.ArrayList(NodeReference).init(allocator),
        };
    }

    pub fn deinit(self: *@This()) void {
        self.children.deinit();
    }
};

/// Direction of hierarchy traversal
pub const TraversalDirection = enum {
    up, // child -> parent
    down, // parent -> child
};

/// Tracks hierarchy traversal: UP (child->parent) or DOWN (parent->child)
pub const TraversalStep = struct {
    edge: EdgeReference,
    direction: TraversalDirection,
    parent: NodeReference,
    child: NodeReference,

    pub fn matches_reverse(self: @This(), other: TraversalStep) bool {
        return Node.is_same(self.parent, other.parent) and
            Node.is_same(self.child, other.child) and
            self.direction != other.direction;
    }
};

/// Tracks state of a split point during path exploration
pub const SplitState = struct {
    split_point: NodeReference,
    children: std.ArrayList(NodeReference),
    /// Paths that completed successfully for each child
    complete_paths_per_child: NodeRefMap.T(std.ArrayList(*PathWithSplits)),
    /// Paths waiting to be processed for each child
    hibernated_paths_per_child: NodeRefMap.T(std.ArrayList(*PathWithSplits)),
    complete: bool = false,

    pub fn init(allocator: std.mem.Allocator, split_point: NodeReference) SplitState {
        return .{
            .split_point = split_point,
            .children = std.ArrayList(NodeReference).init(allocator),
            .complete_paths_per_child = NodeRefMap.T(std.ArrayList(*PathWithSplits)).init(allocator),
            .hibernated_paths_per_child = NodeRefMap.T(std.ArrayList(*PathWithSplits)).init(allocator),
            .complete = false,
        };
    }

    pub fn deinit(self: *@This()) void {
        self.children.deinit();

        var complete_iter = self.complete_paths_per_child.valueIterator();
        while (complete_iter.next()) |list| {
            list.deinit();
        }
        self.complete_paths_per_child.deinit();

        var hibernated_iter = self.hibernated_paths_per_child.valueIterator();
        while (hibernated_iter.next()) |list| {
            list.deinit();
        }
        self.hibernated_paths_per_child.deinit();
    }

    /// Check if all children have at least one complete path
    pub fn is_complete(self: *const @This()) bool {
        for (self.children.items) |child| {
            const paths = self.complete_paths_per_child.get(child) orelse return false;
            if (paths.items.len == 0) return false;
        }
        return true;
    }
};

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    /// Track splits by parent node
    splits: NodeRefMap.T(SplitState),
    /// All paths being explored (with split metadata)
    all_paths: std.ArrayList(*PathWithSplits),
    /// Valid complete paths (plain paths without metadata)
    path_list: ?std.ArrayList(Path) = null,
    /// End nodes to search for (optional)
    end_nodes: ?std.ArrayList(BoundNodeReference) = null,
    /// Counters for statistics
    path_counter: u64 = 0,
    valid_path_counter: u64 = 0,

    pub fn init(allocator: std.mem.Allocator) PathFinder {
        return .{
            .allocator = allocator,
            .splits = NodeRefMap.T(SplitState).init(allocator),
            .all_paths = std.ArrayList(*PathWithSplits).init(allocator),
            .path_list = null,
            .end_nodes = null,
            .path_counter = 0,
            .valid_path_counter = 0,
        };
    }

    pub fn deinit(self: *@This()) void {
        // Clean up all paths with split metadata
        for (self.all_paths.items) |path_ptr| {
            path_ptr.deinit();
            self.allocator.destroy(path_ptr);
        }
        self.all_paths.deinit();

        // Clean up path list
        if (self.path_list) |*list| {
            for (list.items) |*path| {
                path.deinit();
            }
            list.deinit();
        }
        self.path_list = null;

        // Clean up end nodes
        if (self.end_nodes) |*list| {
            list.deinit();
        }
        self.end_nodes = null;

        // Clean up splits
        var split_iter = self.splits.valueIterator();
        while (split_iter.next()) |split_state| {
            split_state.deinit();
        }
        self.splits.deinit();
    }

    /// Main entry point: find all valid paths between start and end nodes
    /// Compatible with the old simple API
    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
        end_nodes: ?[]const BoundNodeReference,
        edge_type: ?Edge.EdgeType,
    ) ![]const Path {
        // Clean up any previous path list
        if (self.path_list) |*list| {
            for (list.items) |*path| {
                path.deinit();
            }
            list.deinit();
        }

        // Clean up previous end nodes
        if (self.end_nodes) |*list| {
            list.deinit();
        }

        // Re-initialize lists
        self.path_list = std.ArrayList(Path).init(self.allocator);
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
            edge_type,
            void,
            self,
            Self.visit_fn,
        );
        _ = result;

        return self.path_list.?.items;
    }

    /// BFS visitor callback - receives ownership of path
    /// Must either keep it or deinit it
    pub fn visit_fn(self_ptr: *anyopaque, path: Path) visitor.VisitResult(void) {
        const self: *Self = @ptrCast(@alignCast(self_ptr));

        // Run filters on path
        const result = self.run_filters(path);

        // Filter says keep!
        if (result == .CONTINUE) {
            // Move path into the list
            self.path_list.?.append(path) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };
            self.valid_path_counter += 1;
        }
        // Filter says don't keep - deinit since we own it
        else {
            var mutable_path = path;
            mutable_path.deinit();
        }

        // Filter says shut it down!
        if (result == .STOP) {
            std.debug.print("STOP!!!!!!!!! FILTER - path stopped\n", .{});
            return visitor.VisitResult(void){ .STOP = {} };
        }

        // Check if path ends in an end node
        if (self.end_nodes) |*end_nodes| {
            for (end_nodes.items, 0..) |end_node, i| {
                if (path.get_other_node(end_node)) |_| {
                    _ = end_nodes.swapRemove(i);
                    if (end_nodes.items.len == 0) {
                        std.debug.print("STOP!!!!!!!!! END NODES - all end nodes found\n", .{});
                        return visitor.VisitResult(void){ .STOP = {} };
                    }
                    break;
                }
            }
        }

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    /// Filter pipeline
    const filters = [_]struct {
        name: []const u8,
        func: *const fn (*Self, Path) visitor.VisitResult(void),
    }{
        .{ .name = "count_paths", .func = Self.count_paths },
        .{ .name = "filter_path_by_edge_type", .func = Self.filter_path_by_edge_type },
    };

    pub fn run_filters(self: *Self, path: Path) visitor.VisitResult(void) {
        std.debug.print("FILTERS - ", .{});
        for (filters) |filter| {
            std.debug.print("{s}, ", .{filter.name});
            const result = filter.func(self, path);
            switch (result) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(void){ .STOP = {} },
                .ERROR => |err| return visitor.VisitResult(void){ .ERROR = err },
                .OK => |value| return visitor.VisitResult(void){ .OK = value },
                .EXHAUSTED => return visitor.VisitResult(void){ .EXHAUSTED = {} },
            }
        }
        std.debug.print("\n", .{});
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    /// Filter: count paths and stop after limit
    pub fn count_paths(self: *Self, path: Path) visitor.VisitResult(void) {
        _ = path;
        self.path_counter += 1;
        std.debug.print("path_counter: {}\n", .{self.path_counter});
        if (self.path_counter > 3) {
            return visitor.VisitResult(void){ .STOP = {} };
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    /// Filter: only keep paths with specific edge type
    pub fn filter_path_by_edge_type(self: *Self, path: Path) visitor.VisitResult(void) {
        _ = self;
        for (path.edges.items) |edge| {
            if (edge.attributes.edge_type != 1759242069) {
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // TODO: Split-related methods below are stubs for future hierarchical pathfinding
    // They will be needed when integrating composition edges into path resolution

    /// TODO: Process a path with split detection
    fn process_path_with_splits(self: *@This(), path: Path) !visitor.VisitResult(void) {
        _ = self;
        _ = path;
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    /// TODO: Handle traversal through a composition (hierarchy) edge
    fn handle_hierarchy_edge(
        self: *@This(),
        path: *PathWithSplits,
        edge: EdgeReference,
    ) !void {
        _ = self;
        _ = path;
        _ = edge;
    }

    /// TODO: Determine if we're going UP or DOWN through a composition edge
    fn determine_direction(
        self: *@This(),
        path: *PathWithSplits,
        edge: EdgeReference,
    ) TraversalDirection {
        _ = self;
        _ = path;
        _ = edge;
        return .down;
    }

    /// TODO: Detect if parent has multiple children (split) and handle it
    fn detect_and_handle_split(
        self: *@This(),
        path: *PathWithSplits,
        parent: NodeReference,
    ) !void {
        _ = self;
        _ = path;
        _ = parent;
    }

    /// TODO: Count number of children for a parent node
    fn count_children(self: *@This(), parent: NodeReference) !usize {
        _ = self;
        _ = parent;
        return 0;
    }

    /// TODO: Get list of all children for a parent
    fn get_children_list(
        self: *@This(),
        parent: NodeReference,
        children: *std.ArrayList(NodeReference),
    ) !void {
        _ = self;
        _ = parent;
        _ = children;
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
    const e3 = try Edge.init(a, n2, n4, 1759242069);
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

    const end_nodes = [_]BoundNodeReference{ bn2, bn4 };

    const paths1 = try pf1.find_paths(bn1, &end_nodes, null);
    std.debug.print("Found {} paths\n", .{paths1.len});

    // Print paths for debugging
    for (paths1) |path| {
        std.debug.print("path: ", .{});
        path.print_path();
    }
}

test "pathfinder composition edges" {
    const a = std.testing.allocator;

    var g = GraphView.init(a);
    defer g.deinit();

    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);

    const bn1 = try g.insert_node(n1);
    const bn2 = try g.insert_node(n2);
    _ = try g.insert_node(n3);

    // Create parent-child relationships
    _ = try EdgeComposition.add_child(bn1, n2, "child1");
    _ = try EdgeComposition.add_child(bn1, n3, "child2");

    var pf = PathFinder.init(a);
    defer pf.deinit();

    // Find paths through composition edges
    const end_nodes = [_]BoundNodeReference{bn2};
    _ = try pf.find_paths(bn1, &end_nodes, null);
}
