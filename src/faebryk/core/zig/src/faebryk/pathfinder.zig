const std = @import("std");
const graph_mod = @import("graph");
const composition_mod = @import("composition.zig");
const interface_mod = @import("interface.zig");
const type_mod = @import("node_type.zig");

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
const EdgeType = type_mod.EdgeType;

const DEBUG = false;

// Import hierarchy types from graph module
const HeirarchyTraverseDirection = graph.HeirarchyTraverseDirection;
const HeirarchyElement = graph.HeirarchyElement;

// Shallow link attribute key
const shallow = EdgeInterfaceConnection.shallow_attribute;

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
            var copied_path = BFSPath.init(path.start_node);
            copied_path.path.edges.ensureTotalCapacity(path.path.edges.items.len) catch |err| {
                copied_path.deinit();
                return visitor.VisitResult(void){ .ERROR = err };
            };
            copied_path.path.edges.appendSliceAssumeCapacity(path.path.edges.items);
            copied_path.filtered = path.filtered;
            copied_path.stop = path.stop;
            copied_path.via_conditional = path.via_conditional;

            self.path_list.?.append(copied_path) catch |err| {
                copied_path.deinit();
                return visitor.VisitResult(void){ .ERROR = err };
            };
            self.valid_path_counter += 1;

            // Only remove end node from search list if we found a VALID path to it
            // Filtered OR stopped paths don't count as "found" - keep searching for better paths
            if (self.end_nodes) |*end_nodes| {
                const path_end = path.path.get_other_node(path.start_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };

                // Only mark end node as found if path is valid and not a dead-end
                // This allows BFS to continue searching for better paths (e.g., direct over sibling)
                if (!path.stop) {
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
            }
        }
        // Filter says don't keep - BFS will deinitialize

        // Filter says shut it down!
        if (result == .STOP) {
            if (DEBUG) std.debug.print("STOP BFS!!! - Filter stopped\n", .{});
            return visitor.VisitResult(void){ .STOP = {} };
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
        self.path_counter += 1;

        if (DEBUG) {
            std.debug.print("path_counter: {} len: {}\n", .{ self.path_counter, path.path.edges.items.len });
        }
        if (self.path_counter > 1_000_000) {
            return visitor.VisitResult(void){ .STOP = {} };
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_edge_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        const edges = path.path.edges.items;
        if (edges.len == 0) return visitor.VisitResult(void){ .CONTINUE = {} };

        const first = edges[0].attributes.edge_type;
        const last = edges[edges.len - 1].attributes.edge_type;

        const first_allowed = switch (first) {
            EdgeComposition.tid, EdgeInterfaceConnection.tid => true,
            else => false,
        };
        const last_allowed = switch (last) {
            EdgeComposition.tid, EdgeInterfaceConnection.tid => true,
            else => false,
        };

        if (!first_allowed or !last_allowed) {
            path.stop = true;
            path.filtered = true;
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_node_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        const start_node = path.start_node;
        const end_node = path.path.get_other_node(start_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };

        const start_type_edge = EdgeType.get_type_edge(start_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };
        const end_type_edge = EdgeType.get_type_edge(end_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };

        const start_node_type = EdgeType.get_type_node(start_type_edge.edge);
        const end_node_type = EdgeType.get_type_node(end_type_edge.edge);

        if (!Node.is_same(start_node_type, end_node_type)) {
            path.filtered = true;
        }

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

        const path_end = path.path.get_other_node(path.start_node) orelse {
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
            // Sibling paths are conditional/weak - they can be overridden by direct paths
            // Filter them out, stop exploration, and mark as conditional
            path.filtered = true;
            path.stop = true;
            path.via_conditional = true;
            if (DEBUG) {
                std.debug.print("SIBLING PATH FILTERED! Path length: {}, last 2 edges are composition edges sharing parent\n", .{edges.len});
            }
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // Build the raw hierarchy element sequence from a path's composition edges
    // Returns a list of hierarchy elements representing each UP/DOWN traversal
    fn build_hierarchy_elements(
        allocator: std.mem.Allocator,
        path: *const BFSPath,
    ) !std.ArrayList(HeirarchyElement) {
        var elements = std.ArrayList(HeirarchyElement).init(allocator);
        errdefer elements.deinit();

        var current_node = path.start_node;

        for (path.path.edges.items) |edge| {
            if (edge.attributes.edge_type == EdgeComposition.tid) {
                // Determine traversal direction based on current node position
                const direction: HeirarchyTraverseDirection = if (Node.is_same(EdgeComposition.get_child_node(edge), current_node.node))
                    HeirarchyTraverseDirection.up
                else if (Node.is_same(EdgeComposition.get_parent_node(edge), current_node.node))
                    HeirarchyTraverseDirection.down
                else
                    return error.InvalidEdge;

                // Create and append hierarchy element
                const elem = HeirarchyElement{
                    .edge = edge,
                    .traverse_direction = direction,
                };
                try elements.append(elem);
            } else if (edge.attributes.edge_type == EdgeInterfaceConnection.tid) {
                // Interface connections don't create hierarchy elements
            } else {
                return error.InvalidEdgeType;
            }

            // Move to next node in path
            current_node = current_node.g.bind(
                edge.get_other_node(current_node.node) orelse return error.InvalidNode,
            );
        }

        return elements;
    }

    // Fold and validate hierarchy elements using stack-based matching
    // Returns true if path is valid (empty folded stack), false otherwise
    // Also returns true (invalid) if Rule 2 violated (DOWN from starting level)
    fn fold_and_validate_hierarchy(
        allocator: std.mem.Allocator,
        raw_elements: []const HeirarchyElement,
    ) !struct { valid: bool, folded_stack: std.ArrayList(HeirarchyElement) } {
        var folded_stack = std.ArrayList(HeirarchyElement).init(allocator);
        errdefer folded_stack.deinit();

        for (raw_elements) |elem| {
            if (folded_stack.items.len > 0) {
                // Stack has elements - check for matching pair to fold
                const top = &folded_stack.items[folded_stack.items.len - 1];
                if (top.match(&elem)) {
                    // Matching UP/DOWN pair - fold by popping
                    _ = folded_stack.pop();
                } else {
                    // No match - push to stack
                    try folded_stack.append(elem);
                }
            } else {
                // Stack is empty - we're at the starting hierarchy level
                // Rule 2: Reject paths that descend (DOWN) from starting level
                if (elem.traverse_direction == HeirarchyTraverseDirection.down) {
                    // Invalid - descending without first ascending
                    return .{ .valid = false, .folded_stack = folded_stack };
                }
                try folded_stack.append(elem);
            }
        }

        if (DEBUG) {
            for (folded_stack.items) |elem| {
                std.debug.print("Folded stack - direction: {} child_name: {s} parent_type: {} child_type: {}\n", .{
                    elem.traverse_direction,
                    elem.edge.attributes.name orelse "",
                    elem.edge.source.attributes.fake_type orelse 0,
                    elem.edge.target.attributes.fake_type orelse 0,
                });
            }
        }

        // Rule 1: Valid paths must have empty folded stack (balanced hierarchy)
        const valid = folded_stack.items.len == 0;
        return .{ .valid = valid, .folded_stack = folded_stack };
    }

    // Validate shallow links in the path
    // Shallow links can only be crossed if the starting node is at the same level or higher
    // than where the shallow link is located
    // Also marks path as conditional if it crosses any shallow links
    // Returns false if path violates shallow link rules
    fn validate_shallow_edges(path: *BFSPath) bool {
        var current_node = path.start_node;
        var hierarchy_depth: i32 = 0; // 0 = starting level, positive = higher (toward root), negative = lower (toward leaves)

        for (path.path.edges.items) |edge| {
            if (edge.attributes.edge_type == EdgeComposition.tid) {
                // Update hierarchy depth based on traversal direction
                const child_node = EdgeComposition.get_child_node(edge);
                const parent_node = EdgeComposition.get_parent_node(edge);

                if (Node.is_same(child_node, current_node.node)) {
                    // Going UP (child to parent) - moving toward root
                    hierarchy_depth += 1;
                } else if (Node.is_same(parent_node, current_node.node)) {
                    // Going DOWN (parent to child) - moving away from root
                    hierarchy_depth -= 1;
                }
            } else if (edge.attributes.edge_type == EdgeInterfaceConnection.tid) {
                // Check if this is a shallow link
                const shallow_val = edge.attributes.dynamic.values.get(shallow);
                if (DEBUG) {
                    std.debug.print("Checking interface edge for shallow, found: {}\n", .{shallow_val != null});
                }
                if (shallow_val) |shallow_value| {
                    if (DEBUG) {
                        std.debug.print("Shallow value: {}\n", .{shallow_value.Bool});
                    }
                    if (shallow_value.Bool) {
                        // This is a shallow link - mark path as conditional
                        path.via_conditional = true;
                        if (DEBUG) {
                            std.debug.print("Path marked as via_conditional due to shallow link\n", .{});
                        }

                        // Can only cross if starting node is at same level or higher than the link
                        // depth > 0: we've ascended, meaning start is LOWER than link → reject
                        // depth <= 0: we're at or below start, meaning start is at same/higher than link → allow
                        if (hierarchy_depth > 0) {
                            // We've ascended above the starting level - start is lower than link
                            if (DEBUG) {
                                std.debug.print("Shallow link crossed at depth {}, starting node is lower than link level, rejecting path\n", .{hierarchy_depth});
                            }
                            return false;
                        }
                    }
                }
            }

            // Move to next node
            current_node = current_node.g.bind(
                edge.get_other_node(current_node.node) orelse return false,
            );
        }

        return true;
    }

    // Main filter: validates that paths follow proper hierarchy traversal rules
    // Rule 1: Paths must return to the same hierarchy level (balanced stack)
    // Rule 2: Paths cannot descend into children from the starting level
    // Rule 3: Shallow links can only be crossed if starting node is at same level or higher than the link
    pub fn filter_heirarchy_stack(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;

        if (path.filtered) {
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }

        const allocator = path.path.g.allocator;

        // Step 1: Build raw hierarchy elements from path and store in BFSPath
        path.hierarchy_elements_raw = build_hierarchy_elements(allocator, path) catch |err| {
            return visitor.VisitResult(void){ .ERROR = err };
        };

        // Step 2: Fold and validate the hierarchy, store folded stack in BFSPath
        const result = fold_and_validate_hierarchy(allocator, path.hierarchy_elements_raw.?.items) catch |err| {
            return visitor.VisitResult(void){ .ERROR = err };
        };
        path.hierarchy_stack_folded = result.folded_stack;

        // Mark path as filtered if hierarchy validation failed
        if (!result.valid) {
            path.filtered = true;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }

        // Step 3: Validate shallow links
        if (!validate_shallow_edges(path)) {
            path.filtered = true;
            path.stop = true;
        }

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }
};

// Test from graph.zig - basic pathfinding with end nodes
test "visit_paths_bfs" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    const n1 = Node.init(a);
    const n2 = Node.init(a);
    const n3 = Node.init(a);
    const n4 = Node.init(a);
    const n5 = Node.init(a);
    const n6 = Node.init(a);
    const n7 = Node.init(a);
    const e1 = Edge.init(a, n1, n2, 1759242069);
    const e2 = Edge.init(a, n1, n3, 1759242069);
    const e3 = Edge.init(a, n2, n4, 1759242068);
    const e4 = Edge.init(a, n2, n5, 1759242069);
    const e5 = Edge.init(a, n5, n6, 1759242069);
    const e6 = Edge.init(a, n6, n1, 1759242069);
    const e7 = Edge.init(a, n4, n7, 1759242069);
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

    const bn1 = g.insert_node(n1);
    const bn2 = g.insert_node(n2);
    const bn4 = g.insert_node(n4);
    _ = g.insert_node(n3);
    _ = g.insert_node(n5);
    _ = g.insert_node(n6);
    _ = g.insert_node(n7);
    _ = g.insert_edge(e1);
    _ = g.insert_edge(e2);
    _ = g.insert_edge(e3);
    _ = g.insert_edge(e4);
    _ = g.insert_edge(e5);
    _ = g.insert_edge(e6);
    _ = g.insert_edge(e7);

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

    const bn1 = g.create_and_insert_node();
    bn1.node.attributes.name = "node1";
    const bn2 = g.create_and_insert_node();
    bn2.node.attributes.name = "node2";
    const bn3 = g.create_and_insert_node();
    bn3.node.attributes.name = "node3";
    const bn4 = g.create_and_insert_node();
    bn4.node.attributes.name = "node1";
    const be1 = g.insert_edge(Edge.init(g.allocator, bn2.node, bn1.node, EdgeComposition.tid));
    const be2 = g.insert_edge(Edge.init(g.allocator, bn3.node, bn4.node, EdgeComposition.tid));
    const be3 = g.insert_edge(Edge.init(g.allocator, bn2.node, bn3.node, EdgeInterfaceConnection.tid));

    var path = Path.init(&g);

    try path.edges.append(be1.edge);
    try path.edges.append(be3.edge);
    try path.edges.append(be2.edge);

    var bfs_path = BFSPath{
        .path = path,
        .start_node = bn1,
        .filtered = false,
        .stop = false,
    };
    defer bfs_path.deinit(); // This will clean up path and hierarchy stacks

    var pf = PathFinder.init(g.allocator);
    defer pf.deinit();
    _ = pf.filter_heirarchy_stack(&bfs_path);
}
