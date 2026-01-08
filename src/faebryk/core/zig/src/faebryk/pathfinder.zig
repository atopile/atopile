const std = @import("std");
const graph_mod = @import("graph");
const composition_mod = @import("composition.zig");
const interface_mod = @import("interface.zig");
const type_mod = @import("node_type.zig");
const typegraph_mod = @import("typegraph.zig");
const trait_mod = @import("trait.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const Node = graph.Node;
const Edge = graph.Edge;
const BFSPath = graph.BFSPath;
const TraversedEdge = graph.TraversedEdge;
const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const BoundNodeReference = graph.BoundNodeReference;
const BoundEdgeReference = graph.BoundEdgeReference;
const GraphView = graph.GraphView;
const NodeRefMap = graph.NodeRefMap;
const EdgeComposition = composition_mod.EdgeComposition;
const EdgeInterfaceConnection = interface_mod.EdgeInterfaceConnection;
const EdgeType = type_mod.EdgeType;
const TypeNodeAttributes = typegraph_mod.TypeGraph.TypeNodeAttributes;
const EdgeTrait = trait_mod.EdgeTrait;

const debug_pathfinder = false;

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

        const parent_type_match = self.parent_type_node.is_same(other.parent_type_node);
        const child_type_match = self.child_type_node.is_same(other.child_type_node);
        const child_name_match = switch (self.traverse_direction) {
            .horizontal => true,
            .up, .down => std.mem.eql(u8, self.edge.get_attribute_name() orelse "", other.edge.get_attribute_name() orelse ""),
        };

        return parent_type_match and child_type_match and child_name_match and opposite_directions;
    }
};

// Shallow link attribute key
const shallow = EdgeInterfaceConnection.shallow_attribute;

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    path_list: std.ArrayList(*BFSPath),
    path_counter: u64,
    valid_path_counter: u64,

    pub fn init(allocator: std.mem.Allocator) PathFinder {
        return .{
            .allocator = allocator,
            .path_list = std.ArrayList(*BFSPath).init(allocator),
            .path_counter = 0,
            .valid_path_counter = 0,
        };
    }

    pub fn deinit(self: *Self) void {
        for (self.path_list.items) |path| {
            path.deinit();
        }
        self.path_list.deinit();
    }

    // Find all valid paths from start node
    // Note: PathFinder is intended for single-use. Create a new instance for each search.
    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
    ) !graph.BFSPaths {
        self.path_list.clearRetainingCapacity();
        try self.path_list.ensureTotalCapacity(256);

        const allowed_edges = [_]graph.Edge.EdgeType{
            EdgeComposition.tid,
            EdgeInterfaceConnection.tid,
        };

        const result = start_node.g.visit_paths_bfs(
            start_node,
            void,
            self,
            Self.visit_fn,
            @constCast(&allowed_edges),
        );

        switch (result) {
            .ERROR => |err| return err,
            .CONTINUE => {},
            .EXHAUSTED => {},
            .OK => {},
            .STOP => {},
        }

        // Transfer ownership to BFSPaths
        var bfs_paths = graph.BFSPaths.init(self.allocator);
        bfs_paths.paths = self.path_list;
        self.path_list = std.ArrayList(*BFSPath).init(self.allocator);

        if (comptime debug_pathfinder) {
            std.debug.print("********* Pathfinder find_paths Summary *********\n", .{});
            std.debug.print("Start node: {}\n", .{start_node.node.uuid});
            std.debug.print("Paths explored: {}\tValid Paths: {}\n", .{ self.path_counter, bfs_paths.paths.items.len });
        }

        return bfs_paths;
    }

    // BFS visitor callback
    pub fn visit_fn(self_ptr: *anyopaque, path: *BFSPath) visitor.VisitResult(void) {
        const self: *Self = @ptrCast(@alignCast(self_ptr));
        const result = self.run_filters(path);
        _ = self.print_paths(path);
        // std.debug.print("path_counter: {} len: {}\n", .{ self.path_counter, path.traversed_edges.items.len });
        if (result == .ERROR) return result;
        if (result == .STOP) return result;

        // if path is invalid, don't save to path_list
        if (path.invalid_path) {
            path.visit_strength = .unvisited;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }

        path.visit_strength = .strong;

        // Copy path to long-lived allocator (BFS arena paths are freed when BFS ends)
        var copied_path = path.copy(self.allocator) catch @panic("OOM");
        copied_path.stop_new_path_discovery = path.stop_new_path_discovery;
        copied_path.visit_strength = path.visit_strength;
        self.path_list.append(copied_path) catch @panic("OOM");
        self.valid_path_counter += 1;

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn run_filters(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        for (filters) |filter| {
            const result = filter.func(self, path);
            switch (result) {
                .CONTINUE => {},
                .STOP => return result,
                .ERROR => return result,
                .OK => {},
                .EXHAUSTED => return result,
            }

            if (path.stop_new_path_discovery) {
                // no point iterating through other filters
                break;
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
        .{ .name = "filter_path_by_is_interface", .func = Self.filter_path_by_is_interface },
        .{ .name = "filter_path_by_same_node_type", .func = Self.filter_path_by_same_node_type },
        .{ .name = "filter_siblings", .func = Self.filter_siblings },
        .{ .name = "filter_hierarchy_stack", .func = Self.filter_hierarchy_stack },
    };

    pub fn count_paths(self: *Self, _: *BFSPath) visitor.VisitResult(void) {
        self.path_counter += 1;
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    fn try_get_node_type_name(g: *GraphView, node: NodeReference) ?graph.str {
        if (EdgeType.get_type_edge(g.bind(node))) |type_edge| {
            const type_node = EdgeType.get_type_node(type_edge.edge);
            return TypeNodeAttributes.of(type_node).get_type_name();
        }
        return null;
    }

    fn print_node_uuid_and_type(g: *GraphView, node: NodeReference) void {
        if (try_get_node_type_name(g, node)) |type_name| {
            std.debug.print("{}:{s}", .{ node.get_uuid(), type_name });
        } else std.debug.print("{}:<no_type>", .{node.get_uuid()});
    }

    pub fn print_paths(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        if (comptime !debug_pathfinder) return visitor.VisitResult(void){ .CONTINUE = {} };
        const g = path.start_node.g;
        std.debug.print("Path {}: ", .{self.path_counter});
        print_node_uuid_and_type(g, path.start_node.node);
        for (path.traversed_edges.items) |traversed_edge| {
            std.debug.print(" -> ", .{});
            const end_node = traversed_edge.get_end_node();
            print_node_uuid_and_type(g, end_node);
        }
        if (!path.invalid_path) {
            std.debug.print(" (VALID)", .{});
        }
        std.debug.print("\n", .{});
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_is_interface(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;

        // Get the end node from the path
        const end_node = path.get_last_node();

        // Get the TypeGraph to lookup the is_interface trait type
        const tg = typegraph_mod.TypeGraph.of_instance(end_node) orelse {
            // Node has no type, mark as invalid
            path.invalid_path = true;
            path.stop_new_path_discovery = true;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        };

        // Look up the is_interface trait type by name
        // Note: Core traits have fully qualified names like "is_interface.node.core.faebryk"
        // We need to try the full name since that's what's registered in the TypeGraph
        const is_interface_type = tg.get_type_by_name("is_interface.node.core.faebryk") orelse {
            // is_interface type not found in this TypeGraph - this shouldn't happen
            // but we'll treat it as "no trait" and invalidate the path
            path.invalid_path = true;
            path.stop_new_path_discovery = true;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        };

        // Check if the end node instance has the is_interface trait using the proper API
        const has_is_interface = EdgeTrait.try_get_trait_instance_of_type(end_node, is_interface_type.node);

        if (has_is_interface == null) {
            // No is_interface trait found - mark path as invalid and stop discovery
            path.invalid_path = true;
            path.stop_new_path_discovery = true;
        }

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_same_node_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        const start_node = path.start_node;
        const end_node = path.get_last_node();

        const start_type_edge = EdgeType.get_type_edge(start_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };
        const end_type_edge = EdgeType.get_type_edge(end_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };

        const start_node_type = EdgeType.get_type_node(start_type_edge.edge);
        const end_node_type = EdgeType.get_type_node(end_type_edge.edge);

        if (!start_node_type.is_same(end_node_type)) {
            path.invalid_path = true;
        }

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // Filters out paths where last 2 edges form child -> parent -> child (sibling traversal)
    pub fn filter_siblings(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        const traversed_edges = path.traversed_edges.items;

        if (traversed_edges.len < 2) return visitor.VisitResult(void){ .CONTINUE = {} };

        const last_edges = [_]EdgeReference{ traversed_edges[traversed_edges.len - 1].edge, traversed_edges[traversed_edges.len - 2].edge };
        for (last_edges) |edge| {
            if (!EdgeComposition.is_instance(edge)) {
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        }

        const edge_1_and_edge_2_share_parent = EdgeComposition.get_parent_node(last_edges[0]).is_same(EdgeComposition.get_parent_node(last_edges[1]));
        if (edge_1_and_edge_2_share_parent) {
            path.invalid_path = true;
            path.stop_new_path_discovery = true;
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    fn resolve_node_type(g: *GraphView, node: NodeReference) !NodeReference {
        const te = EdgeType.get_type_edge(g.bind(node)) orelse return error.MissingNodeType;
        return EdgeType.get_type_node(te.edge);
    }

    // Validates paths follow hierarchy rules:
    // 1. Must return to same level (balanced stack)
    // 2. Cannot descend from starting level
    // 3. Shallow links only if at same or deeper level
    pub fn filter_hierarchy_stack(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        // if (path.invalid_path) return visitor.VisitResult(void){ .CONTINUE = {} };

        var stack = std.ArrayList(HierarchyElement).init(self.allocator);
        defer stack.deinit();

        const g = path.start_node.g;
        var depth: i32 = 0;

        // iterate through path
        for (path.traversed_edges.items) |traversed_edge| {
            const edge = traversed_edge.edge;
            const start_node = traversed_edge.get_start_node();

            // hierarchical edge
            if (EdgeComposition.is_instance(edge)) {
                // determine traversal direction
                var hierarchy_direction: HierarchyTraverseDirection = undefined;
                if (EdgeComposition.get_child_node(edge).is_same(start_node)) {
                    hierarchy_direction = .up;
                    depth += 1;
                } else if (EdgeComposition.get_parent_node(edge).is_same(start_node)) {
                    hierarchy_direction = .down;
                    depth -= 1;
                }

                if (depth <= 0) {
                    path.stop_new_path_discovery = true;
                }

                const hierarchy_element = HierarchyElement{
                    .edge = edge,
                    .traverse_direction = hierarchy_direction,
                    .parent_type_node = resolve_node_type(g, EdgeComposition.get_parent_node(edge)) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    },
                    .child_type_node = resolve_node_type(g, EdgeComposition.get_child_node(edge)) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    },
                };

                if (stack.items.len == 0 and hierarchy_direction == .down) {
                    path.invalid_path = true;
                    path.stop_new_path_discovery = true;
                }

                if (stack.items.len > 0 and stack.items[stack.items.len - 1].match(&hierarchy_element)) {
                    _ = stack.pop();
                } else {
                    stack.append(hierarchy_element) catch @panic("OOM");
                }
            }

            if (EdgeInterfaceConnection.is_instance(edge)) {
                const shallow_edge = (edge.get(shallow) orelse continue).Bool;
                if (shallow_edge and depth > 0) path.invalid_path = true;
            }
        }

        if (stack.items.len != 0) {
            path.invalid_path = true;
        }

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }
};

// Test from graph.zig - basic pathfinding with end nodes
test "visit_paths_bfs" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();
    const bn4 = g.create_and_insert_node();
    const bn5 = g.create_and_insert_node();
    const bn6 = g.create_and_insert_node();
    const bn7 = g.create_and_insert_node();
    const tid1 = Edge.hash_edge_type(1759242069);
    const tid2 = Edge.hash_edge_type(1759242068);
    const e1 = EdgeReference.init(bn1.node, bn2.node, tid1);
    const e2 = EdgeReference.init(bn1.node, bn3.node, tid1);
    const e3 = EdgeReference.init(bn2.node, bn4.node, tid2);
    const e4 = EdgeReference.init(bn2.node, bn5.node, tid1);
    const e5 = EdgeReference.init(bn2.node, bn5.node, tid1);
    const e6 = EdgeReference.init(bn5.node, bn6.node, tid1);
    const e7 = EdgeReference.init(bn4.node, bn7.node, tid1);
    defer g.deinit();

    _ = g.insert_edge(e1);
    _ = g.insert_edge(e2);
    _ = g.insert_edge(e3);
    _ = g.insert_edge(e4);
    _ = g.insert_edge(e5);
    _ = g.insert_edge(e6);
    _ = g.insert_edge(e7);

    var pf1 = PathFinder.init(a);
    defer pf1.deinit();

    var paths1 = try pf1.find_paths(bn1);
    defer paths1.deinit();
}

test "filter_hierarchy_stack" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();
    const bn4 = g.create_and_insert_node();
    const be1 = g.insert_edge(EdgeReference.init(bn2.node, bn1.node, EdgeComposition.tid));
    const be2 = g.insert_edge(EdgeReference.init(bn3.node, bn4.node, EdgeComposition.tid));
    const be3 = g.insert_edge(EdgeReference.init(bn2.node, bn3.node, EdgeInterfaceConnection.tid));

    var bfs_path = try BFSPath.init(a, bn1);

    try bfs_path.traversed_edges.append(TraversedEdge{ .edge = be1.edge, .forward = false }); // bn1 -> bn2 (target -> source)
    try bfs_path.traversed_edges.append(TraversedEdge{ .edge = be3.edge, .forward = true }); // bn2 -> bn3 (source -> target)
    try bfs_path.traversed_edges.append(TraversedEdge{ .edge = be2.edge, .forward = true }); // bn3 -> bn4 (source -> target)
    defer bfs_path.deinit();

    var pf = PathFinder.init(a);
    defer pf.deinit();
    _ = pf.filter_hierarchy_stack(bfs_path);
}
