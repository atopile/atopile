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

const HierarchyTraverseDirection = enum {
    up, // Child to parent
    down, // Parent to child
    horizontal, // Same level (interface connections)
};

const HierarchyElement = struct {
    edge: EdgeReference,
    traverse_direction: HierarchyTraverseDirection,
    parent_type_node: NodeReference,
    child_type_node: NodeReference,

    fn match(self: *const @This(), other: *const @This()) bool {
        const opposite_directions = (self.traverse_direction == .up and other.traverse_direction == .down) or
            (self.traverse_direction == .down and other.traverse_direction == .up);

        const parent_type_match = Node.is_same(self.parent_type_node, other.parent_type_node);
        const child_type_match = Node.is_same(self.child_type_node, other.child_type_node);
        const child_name_match = switch (self.traverse_direction) {
            .horizontal => true,
            .up, .down => std.mem.eql(u8, self.edge.attributes.name orelse "", other.edge.attributes.name orelse ""),
        };

        return parent_type_match and child_type_match and child_name_match and opposite_directions;
    }
};

// Shallow link attribute key
const shallow = EdgeInterfaceConnection.shallow_attribute;

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    path_list: std.ArrayList(BFSPath), // Valid complete paths (plain paths without metadata)
    end_nodes: std.ArrayList(BoundNodeReference), // End nodes to search for (optional)
    path_counter: u64, // Counters for statistics
    valid_path_counter: u64, // Count of valid complete paths

    pub fn init(allocator: std.mem.Allocator) PathFinder {
        return .{
            .allocator = allocator,
            .path_list = std.ArrayList(BFSPath).init(allocator),
            .end_nodes = std.ArrayList(BoundNodeReference).init(allocator),
            .path_counter = 0,
            .valid_path_counter = 0,
        };
    }

    pub fn deinit(self: *Self) void {
        for (self.path_list.items) |*path| {
            path.deinit();
        }
        self.path_list.deinit();
        self.end_nodes.deinit();
    }

    // Find all valid paths between start and end nodes
    // Note: PathFinder is intended for single-use. Create a new instance for each search.
    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
        end_nodes: ?[]const BoundNodeReference,
    ) !graph.BFSPaths {

        // Clear and pre-allocate lists with reasonable initial capacity
        self.path_list.clearRetainingCapacity();
        try self.path_list.ensureTotalCapacity(256);

        self.end_nodes.clearRetainingCapacity();
        if (end_nodes) |nodes| {
            try self.end_nodes.ensureTotalCapacity(nodes.len);
            self.end_nodes.appendSliceAssumeCapacity(nodes);
        }

        // Run BFS with our visitor callback
        const result = start_node.g.visit_paths_bfs(
            start_node,
            void,
            self,
            Self.visit_fn,
        );

        switch (result) {
            .ERROR => |err| {
                return err;
            },
            .CONTINUE => {},
            .EXHAUSTED => {},
            .OK => {},
            .STOP => {},
        }

        // Transfer ownership to BFSPaths
        var bfs_paths = graph.BFSPaths.init(self.allocator);
        bfs_paths.paths = self.path_list;
        self.path_list = std.ArrayList(BFSPath).init(self.allocator); // Reinitialize empty list

        return bfs_paths;
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

            self.path_list.append(copied_path) catch |err| {
                copied_path.deinit();
                return visitor.VisitResult(void){ .ERROR = err };
            };
            self.valid_path_counter += 1;

            // Only remove end node from search list if we found a VALID path to it
            // Filtered OR stopped paths don't count as "found" - keep searching for better paths
            if (self.end_nodes.items.len > 0) {
                const end_nodes = &self.end_nodes;
                const path_end = path.path.get_other_node(path.start_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };

                // Only mark end node as found if path is valid and not a dead-end
                // This allows BFS to continue searching for better paths (e.g., direct over sibling)
                if (!path.stop) {
                    for (end_nodes.items, 0..) |end_node, i| {
                        if (Node.is_same(path_end.node, end_node.node)) {
                            _ = end_nodes.swapRemove(i);

                            // If all end nodes found, stop the search
                            if (end_nodes.items.len == 0) {
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
            return visitor.VisitResult(void){ .STOP = {} };
        }

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn run_filters(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        for (filters) |filter| {
            const result = filter.func(self, path);
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
        .{ .name = "filter_path_by_same_node_type", .func = Self.filter_path_by_same_node_type },
        .{ .name = "filter_siblings", .func = Self.filter_siblings },
        .{ .name = "filter_hierarchy_stack", .func = Self.filter_hierarchy_stack },
    };

    pub fn count_paths(self: *Self, _: *BFSPath) visitor.VisitResult(void) {
        self.path_counter += 1;

        if (self.path_counter > 1_000_000) {
            return visitor.VisitResult(void){ .STOP = {} };
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_edge_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        const edges = path.path.edges.items;
        if (edges.len == 0) return visitor.VisitResult(void){ .CONTINUE = {} };

        const last_edge_type = edges[edges.len - 1].attributes.edge_type;
        const is_allowed = switch (last_edge_type) {
            EdgeComposition.tid, EdgeInterfaceConnection.tid => true,
            else => false,
        };

        if (!is_allowed) {
            path.stop = true;
            path.filtered = true;
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_same_node_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
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

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // Filter out paths that don't end at any of the target end nodes
    pub fn filter_only_end_nodes(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        // Only filter if end nodes are specified and the list is not empty
        if (self.end_nodes.items.len == 0) {
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }

        const path_end = path.path.get_other_node(path.start_node) orelse {
            // Empty path or invalid - keep it
            return visitor.VisitResult(void){ .CONTINUE = {} };
        };

        // Check if path ends at one of the target nodes
        for (self.end_nodes.items) |end_node| {
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
        // check that all edges are hierarchy edges
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
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // Build the raw hierarchy element sequence from a path's composition edges
    // Returns a list of hierarchy elements representing each UP/DOWN traversal
    fn resolve_node_type(g: *GraphView, node: NodeReference) !NodeReference {
        const bound_node = g.bind(node);
        const type_edge = EdgeType.get_type_edge(bound_node) orelse return error.MissingNodeType;
        return EdgeType.get_type_node(type_edge.edge);
    }

    fn build_hierarchy_elements(
        allocator: std.mem.Allocator,
        path: *const BFSPath,
    ) !std.ArrayList(HierarchyElement) {
        var elements = std.ArrayList(HierarchyElement).init(allocator);
        errdefer elements.deinit();

        var current_node = path.start_node;
        const g = path.start_node.g;

        for (path.path.edges.items) |edge| {
            if (edge.attributes.edge_type == EdgeComposition.tid) {
                // Determine traversal direction based on current node position
                const direction: HierarchyTraverseDirection = if (Node.is_same(EdgeComposition.get_child_node(edge), current_node.node))
                    HierarchyTraverseDirection.up
                else if (Node.is_same(EdgeComposition.get_parent_node(edge), current_node.node))
                    HierarchyTraverseDirection.down
                else
                    return error.InvalidEdge;

                // Create and append hierarchy element
                const elem = HierarchyElement{
                    .edge = edge,
                    .traverse_direction = direction,
                    .parent_type_node = try resolve_node_type(g, EdgeComposition.get_parent_node(edge)),
                    .child_type_node = try resolve_node_type(g, EdgeComposition.get_child_node(edge)),
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
        raw_elements: []const HierarchyElement,
    ) !bool {
        var folded_stack = std.ArrayList(HierarchyElement).init(allocator);
        defer folded_stack.deinit();

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
                if (elem.traverse_direction == HierarchyTraverseDirection.down) {
                    // Invalid - descending without first ascending
                    return false;
                }
                try folded_stack.append(elem);
            }
        }

        // Rule 1: Valid paths must have empty folded stack (balanced hierarchy)
        return folded_stack.items.len == 0;
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
                if (shallow_val) |shallow_value| {
                    if (shallow_value.Bool) {
                        // This is a shallow link - mark path as conditional
                        path.via_conditional = true;

                        // Can only cross if starting node is at same level or higher than the link
                        // depth > 0: we've ascended, meaning start is LOWER than link → reject
                        // depth <= 0: we're at or below start, meaning start is at same/higher than link → allow
                        if (hierarchy_depth > 0) {
                            // We've ascended above the starting level - start is lower than link
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
    pub fn filter_hierarchy_stack(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;

        if (path.filtered) {
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }

        const allocator = path.path.g.allocator;

        // Step 1: Build raw hierarchy elements from path
        var hierarchy_elements = build_hierarchy_elements(allocator, path) catch |err| {
            return visitor.VisitResult(void){ .ERROR = err };
        };
        defer hierarchy_elements.deinit();

        // Step 2: Fold and validate the hierarchy
        const hierarchy_valid = fold_and_validate_hierarchy(allocator, hierarchy_elements.items) catch |err| {
            return visitor.VisitResult(void){ .ERROR = err };
        };

        // Mark path as filtered if hierarchy validation failed
        if (!hierarchy_valid) {
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
    defer paths1.deinit();
}

test "filter_hierarchy_stack" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();
    const bn4 = g.create_and_insert_node();
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
    defer bfs_path.deinit();

    var pf = PathFinder.init(g.allocator);
    defer pf.deinit();
    _ = pf.filter_hierarchy_stack(&bfs_path);
}
