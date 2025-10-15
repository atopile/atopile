const std = @import("std");
const graph_mod = @import("graph");
const composition_mod = @import("composition.zig");
const interface_mod = @import("interface.zig");

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
const EdgeInterfaceConnection = interface_mod.EdgeInterfaceConnection;

const DEBUG = false;

const HeirarchyTraverseDirection = enum {
    up,
    down,
    horizontal,
};

const HeirarchyElement = struct {
    parent_type: u64,
    child_type: u64,
    child_name: []const u8,
    traverse_direction: HeirarchyTraverseDirection,

    pub fn match(self: *const @This(), other: *const @This()) bool {
        // Match if same parent/child/name but opposite directions (up vs down)
        const opposite_directions = (self.traverse_direction == .up and other.traverse_direction == .down) or
            (self.traverse_direction == .down and other.traverse_direction == .up);

        return self.parent_type == other.parent_type and
            self.child_type == other.child_type and
            std.mem.eql(u8, self.child_name, other.child_name) and
            opposite_directions;
    }
};

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

        // Re-initialize lists with reasonable initial capacity
        self.path_list = std.ArrayList(BFSPath).init(self.allocator);
        try self.path_list.?.ensureTotalCapacity(256); // Start with room for 256 paths
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

        switch (result) {
            .ERROR => |err| {
                if (DEBUG) std.debug.print("!!!ERROR!!!: {}\n", .{err});
                return err;
            },
            .CONTINUE => {},
            .EXHAUSTED => {},
            .OK => {},
            .STOP => {},
        }

        if (DEBUG) {
            for (self.path_list.?.items) |path| {
                std.debug.print("path: ", .{});
                path.path.print_path();
            }
        }

        return self.path_list.?.items;
    }

    // BFS visitor callback
    pub fn visit_fn(self_ptr: *anyopaque, path: *BFSPath) visitor.VisitResult(void) {
        const self: *Self = @ptrCast(@alignCast(self_ptr));

        // Run filters on path
        const result = self.run_filters(path);

        if (result == .ERROR) {
            return result;
        }

        // Filter says keep!
        if (!path.filtered) {
            // Deep copy the path - pre-allocate capacity to avoid reallocations
            var copied_path = BFSPath.init(path.start);
            copied_path.path.edges.ensureTotalCapacity(path.path.edges.items.len) catch |err| {
                copied_path.deinit();
                return visitor.VisitResult(void){ .ERROR = err };
            };
            copied_path.path.edges.appendSliceAssumeCapacity(path.path.edges.items);
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
            if (DEBUG) std.debug.print("STOP BFS!!! - Filter stopped\n", .{});
            return visitor.VisitResult(void){ .STOP = {} };
        }

        // Check if path ends in an end node
        if (self.end_nodes) |*end_nodes| {
            const path_end = path.path.get_other_node(path.start) orelse return visitor.VisitResult(void){ .CONTINUE = {} };

            for (end_nodes.items, 0..) |end_node, i| {
                if (Node.is_same(path_end.node, end_node.node)) {
                    _ = end_nodes.swapRemove(i);

                    // If all end nodes found, stop the search
                    if (end_nodes.items.len == 0) {
                        if (DEBUG) std.debug.print("STOP BFS!!! - All end nodes found\n", .{});
                        return visitor.VisitResult(void){ .STOP = {} };
                    }
                    break;
                }
            }
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn run_filters(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        if (DEBUG) std.debug.print("FILTERS\n", .{});
        for (filters) |filter| {
            if (DEBUG) std.debug.print("{s:<32}", .{filter.name});
            const result = filter.func(self, path);
            if (DEBUG) std.debug.print("filtered:{} stop:{}\n", .{ path.filtered, path.stop });
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
        .{ .name = "filter_only_end_nodes", .func = Self.filter_only_end_nodes },
        .{ .name = "filter_path_by_edge_type", .func = Self.filter_path_by_edge_type },
        .{ .name = "filter_path_by_node_type", .func = Self.filter_path_by_node_type },
        .{ .name = "filter_siblings", .func = Self.filter_siblings },
        .{ .name = "filter_heirarchy_stack", .func = Self.filter_heirarchy_stack },
    };

    pub fn count_paths(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = path;
        self.path_counter += 1;

        // Print progress every 1000 paths
        if (self.path_counter % 1000 == 0) {
            std.debug.print("Progress: {} paths explored\n", .{self.path_counter});
        }

        if (DEBUG) std.debug.print("path_counter: {}", .{self.path_counter});
        if (self.path_counter > 1_000_000) {
            return visitor.VisitResult(void){ .STOP = {} };
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // TODO this can be optimized, we don't really need to iterate through the entire edge list, just the first and last
    pub fn filter_path_by_edge_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;

        const allowed_edge_types = comptime [_]Edge.EdgeType{
            EdgeComposition.tid,
            EdgeInterfaceConnection.tid,
        };

        edge_loop: for (path.path.edges.items) |edge| {
            inline for (allowed_edge_types) |allowed| {
                if (edge.attributes.edge_type == allowed) continue :edge_loop;
            }
            path.stop = true;
            path.filtered = true;
            return visitor.VisitResult(void){ .CONTINUE = {} };
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

    // Filter out paths that don't end at any of the target end nodes
    pub fn filter_only_end_nodes(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        // Only filter if end nodes are specified and the list is not empty
        const end_nodes = self.end_nodes orelse return visitor.VisitResult(void){ .CONTINUE = {} };
        if (end_nodes.items.len == 0) {
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }

        const path_end = path.path.get_other_node(path.start) orelse {
            // Empty path or invalid - keep it
            return visitor.VisitResult(void){ .CONTINUE = {} };
        };

        // Check if path ends at one of the target nodes
        for (end_nodes.items) |end_node| {
            if (Node.is_same(path_end.node, end_node.node)) {
                // Path ends at target - keep it
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        }

        // Path doesn't end at any target node - filter it out
        path.filtered = true;
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
    // Additionally, reject paths that descend into children before ascending from the starting point
    pub fn filter_heirarchy_stack(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;

        if (path.filtered) {
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }

        var hierarchy_stack = std.ArrayList(HeirarchyElement).init(path.path.g.allocator);
        defer hierarchy_stack.deinit(); // Clean up the ArrayList
        var current_node = path.start;

        // generate stack
        for (path.path.edges.items) |edge| {
            if (edge.attributes.edge_type == EdgeComposition.tid) { // this is a heirarchy connection
                var current_direction = HeirarchyTraverseDirection.horizontal;

                if (Node.is_same(EdgeComposition.get_child_node(edge), current_node.node)) {
                    current_direction = HeirarchyTraverseDirection.up;
                } else if (Node.is_same(EdgeComposition.get_parent_node(edge), current_node.node)) {
                    current_direction = HeirarchyTraverseDirection.down;
                } else {
                    return visitor.VisitResult(void){ .ERROR = error.InvalidEdge };
                }

                const elem = HeirarchyElement{
                    .parent_type = EdgeComposition.get_parent_node(edge).attributes.fake_type orelse 0,
                    .child_type = EdgeComposition.get_child_node(edge).attributes.fake_type orelse 0,
                    .child_name = EdgeComposition.get_child_node(edge).attributes.name orelse "",
                    .traverse_direction = current_direction,
                };

                if (hierarchy_stack.items.len > 0) {
                    const top = &hierarchy_stack.items[hierarchy_stack.items.len - 1];
                    if (top.match(&elem)) {
                        _ = hierarchy_stack.pop();
                    } else {
                        hierarchy_stack.append(elem) catch |err| {
                            return visitor.VisitResult(void){ .ERROR = err };
                        };
                    }
                } else {
                    // Stack is empty - we're at the starting hierarchy level
                    // Reject paths that descend (go DOWN) from the starting point without first ascending
                    if (current_direction == HeirarchyTraverseDirection.down) {
                        path.filtered = true;
                        return visitor.VisitResult(void){ .CONTINUE = {} };
                    }

                    hierarchy_stack.append(elem) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    };
                }
            } else if (edge.attributes.edge_type == EdgeInterfaceConnection.tid) {} else {
                return visitor.VisitResult(void){ .ERROR = error.InvalidEdgeType };
            }
            current_node = current_node.g.bind(edge.get_other_node(current_node.node) orelse return visitor.VisitResult(void){ .ERROR = error.InvalidNode });
        }

        if (DEBUG) {
            for (hierarchy_stack.items) |heirarchy_element| {
                std.debug.print("direction: {} child_name: {s} parent_type: {} child_type: {}\n", .{ heirarchy_element.traverse_direction, heirarchy_element.child_name, heirarchy_element.parent_type, heirarchy_element.child_type });
            }
        }

        // if stack is empty then path is valid
        if (hierarchy_stack.items.len > 0) {
            path.filtered = true;
        } else {
            path.filtered = false;
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

    if (DEBUG) {
        std.debug.print("\nTEST\nFound {} paths:\n", .{paths1.len});
        // Print paths for debugging
        for (paths1) |path| {
            path.path.print_path();
        }
        std.debug.print("\n", .{});
    }
}

test "filter_heirarchy_stack" {
    if (DEBUG) std.debug.print("test filter_heirarchy_stack\n", .{});
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = try g.insert_node(try Node.init(g.allocator));
    bn1.node.attributes.name = "node1";
    const bn2 = try g.insert_node(try Node.init(g.allocator));
    bn2.node.attributes.name = "node2";
    const bn3 = try g.insert_node(try Node.init(g.allocator));
    bn3.node.attributes.name = "node3";
    const bn4 = try g.insert_node(try Node.init(g.allocator));
    bn4.node.attributes.name = "node1";
    const be1 = try g.insert_edge(try Edge.init(g.allocator, bn2.node, bn1.node, EdgeComposition.tid));
    const be2 = try g.insert_edge(try Edge.init(g.allocator, bn3.node, bn4.node, EdgeComposition.tid));
    const be3 = try g.insert_edge(try Edge.init(g.allocator, bn2.node, bn3.node, EdgeInterfaceConnection.tid));

    var path = Path.init(&g);
    defer path.deinit(); // Clean up path second

    path.edges.append(be1.edge) catch @panic("OOM");
    path.edges.append(be3.edge) catch @panic("OOM");
    path.edges.append(be2.edge) catch @panic("OOM");

    var bfs_path = BFSPath{
        .path = path,
        .start = bn1,
        .filtered = false,
        .stop = false,
    };
    var pf = PathFinder.init(g.allocator);
    defer pf.deinit();
    _ = pf.filter_heirarchy_stack(&bfs_path);
}
