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

const debug_pathfinder = true;

const BoundNodeRefMap = struct {
    pub fn eql(_: @This(), a: BoundNodeReference, b: BoundNodeReference) bool {
        return a.g == b.g and a.node.is_same(b.node);
    }

    pub fn hash(_: @This(), key: BoundNodeReference) u64 {
        var h: u64 = 0;
        var uuid = key.node.get_uuid();
        h = std.hash.Wyhash.hash(h, std.mem.asBytes(&uuid));
        var g_ptr: usize = @intFromPtr(key.g);
        h = std.hash.Wyhash.hash(h, std.mem.asBytes(&g_ptr));
        return h;
    }

    pub fn T(V: type) type {
        return std.HashMap(BoundNodeReference, V, BoundNodeRefMap, std.hash_map.default_max_load_percentage);
    }

    pub fn print_set(set: *const BoundNodeRefMap.T(void)) void {
        var it = set.keyIterator();
        var first = true;
        std.debug.print("[", .{});
        while (it.next()) |bn_ptr| {
            if (!first) std.debug.print(", ", .{});
            first = false;
            print_node_uuid_and_type(bn_ptr.*);
        }
        std.debug.print("]", .{});
    }
};

const StackElement = struct {
    // Pair of node and named child identifier
    bound_node: BoundNodeReference,
    child_identifier: []const u8,

    pub fn print_element(self: *const @This()) void {
        print_node_uuid_and_type(self.bound_node);
        if (self.child_identifier.len == 0) {
            std.debug.print(".<null>", .{});
        } else {
            std.debug.print(".{s}", .{self.child_identifier});
        }
    }
};

const StackElementMap = struct {
    pub fn eql(_: @This(), a: StackElement, b: StackElement) bool {
        return a.bound_node.g == b.bound_node.g and
            a.bound_node.node.is_same(b.bound_node.node) and
            std.mem.eql(u8, a.child_identifier, b.child_identifier);
    }

    pub fn hash(_: @This(), key: StackElement) u64 {
        var h: u64 = 0;
        var uuid = key.bound_node.node.get_uuid();
        h = std.hash.Wyhash.hash(h, std.mem.asBytes(&uuid));
        var g_ptr: usize = @intFromPtr(key.bound_node.g);
        h = std.hash.Wyhash.hash(h, std.mem.asBytes(&g_ptr));
        h = std.hash.Wyhash.hash(h, key.child_identifier);
        return h;
    }

    pub fn T(V: type) type {
        return std.HashMap(StackElement, V, StackElementMap, std.hash_map.default_max_load_percentage);
    }

    pub fn add_node(
        map: *StackElementMap.T(BoundNodeRefSet),
        allocator: std.mem.Allocator,
        key: StackElement,
        node: BoundNodeReference,
    ) void {
        const gop = map.getOrPut(key) catch @panic("OOM");
        if (!gop.found_existing) {
            gop.value_ptr.* = BoundNodeRefSet.init(allocator);
        }
        gop.value_ptr.put(node, {}) catch @panic("OOM");
    }

    pub fn print_key_value(map: *StackElementMap.T(BoundNodeRefSet), key: StackElement) void {
        const value = map.getPtr(key) orelse return;
        std.debug.print("Stack element: ", .{});
        key.print_element();
        std.debug.print(" - ", .{});
        BoundNodeRefMap.print_set(value);
        std.debug.print("\n", .{});
    }

    pub fn remove_node(
        map: *StackElementMap.T(BoundNodeRefSet),
        key: StackElement,
        node: BoundNodeReference,
    ) bool {
        if (map.getPtr(key)) |set_ptr| {
            return set_ptr.remove(node);
        }
        return false;
    }
};

const BoundNodeRefSet = BoundNodeRefMap.T(void);

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    visited_path_counter: u64,
    current_bfs_paths: std.ArrayList(*BFSPath),
    stack_elements_to_bfs: std.ArrayList(StackElement),
    stack_element_nodes: StackElementMap.T(BoundNodeRefSet),

    pub fn init(allocator: std.mem.Allocator) Self {
        return .{
            .allocator = allocator,
            .visited_path_counter = 0,
            .current_bfs_paths = std.ArrayList(*BFSPath).init(allocator),
            .stack_elements_to_bfs = std.ArrayList(StackElement).init(allocator),
            .stack_element_nodes = StackElementMap.T(BoundNodeRefSet).init(allocator),
        };
    }

    pub fn deinit(self: *Self) void {
        for (self.current_bfs_paths.items) |path| {
            path.deinit();
        }
        self.current_bfs_paths.deinit();
        self.stack_elements_to_bfs.deinit();
        var it = self.stack_element_nodes.valueIterator();
        while (it.next()) |set_ptr| {
            set_ptr.deinit();
        }
        self.stack_element_nodes.deinit();
    }

    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
    ) !graph.BFSPaths {
        self.stack_elements_to_bfs.append(.{ .bound_node = start_node, .child_identifier = "" }) catch @panic("OOM");

        while (self.stack_elements_to_bfs.pop()) |stack_element| {

            // Find all connected interfaces in current hierarchy level
            _ = stack_element.bound_node.g.visit_paths_bfs(
                stack_element.bound_node,
                void,
                self,
                Self.bfs_visit_fn,
                &[_]graph.Edge.EdgeType{EdgeInterfaceConnection.tid},
            );

            // Add connected interfaces for a given stack element to the stack element nodes
            for (self.current_bfs_paths.items) |path| {
                const last_node = path.get_last_node();
                StackElementMap.add_node(&self.stack_element_nodes, self.allocator, stack_element, last_node);
            }

            if (comptime debug_pathfinder) {
                StackElementMap.print_key_value(&self.stack_element_nodes, stack_element);
            }

            // For each connected interface, see if we can go down according to the child identifier
            if (self.stack_element_nodes.getPtr(stack_element)) |node_set| {
                var it = node_set.keyIterator();
                while (it.next()) |node_ptr| {
                    const child_node = EdgeComposition.get_child_by_identifier(node_ptr.*, stack_element.child_identifier);
                    if (child_node != null) {
                        std.debug.print("Found child node!!!!\t", .{});
                        print_node_uuid_and_type(node_ptr.*);
                        std.debug.print("\n", .{});
                    }
                }
            }

            // For each connected interface, add parent stack element to BFS queue
            for (self.current_bfs_paths.items) |path| {
                const bound_node = EdgeComposition.get_parent_node_of(path.get_last_node()) orelse continue;
                const parent_edge = EdgeComposition.get_parent_edge(path.get_last_node()) orelse continue;
                const child_identifier = EdgeComposition.get_name(parent_edge.edge) catch continue;
                const stack_element_to_append = StackElement{
                    .bound_node = bound_node,
                    .child_identifier = child_identifier,
                };
                self.stack_elements_to_bfs.append(stack_element_to_append) catch @panic("OOM");
                if (comptime debug_pathfinder) {
                    std.debug.print("Adding parent stack element to bfs queue: ", .{});
                    stack_element_to_append.print_element();
                    std.debug.print("\n", .{});
                }
            }

            // Clean up current_bfs_paths for next iteration
            for (self.current_bfs_paths.items) |path| {
                path.deinit();
            }
            self.current_bfs_paths.deinit();
            self.current_bfs_paths = std.ArrayList(*BFSPath).init(self.allocator);
        }

        // TODO this stuff below isn't going to yield all the paths because we're discarding each bfs iteration
        // Transfer ownership to BFSPaths
        var bfs_paths = graph.BFSPaths.init(self.allocator);
        bfs_paths.paths = self.current_bfs_paths;

        //required else we can get a double free seg-fault from the transferred ownership
        self.current_bfs_paths = std.ArrayList(*BFSPath).init(self.allocator);
        return bfs_paths;
    }

    fn bfs_visit_fn(self_ptr: *anyopaque, path: *graph.BFSPath) visitor.VisitResult(void) {
        const self: *Self = @ptrCast(@alignCast(self_ptr));

        self.visited_path_counter += 1;

        if (comptime debug_pathfinder) {
            self.print_path(path);
        }

        const copied_path = path.copy(self.allocator) catch @panic("OOM");
        self.current_bfs_paths.append(copied_path) catch @panic("OOM");

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn print_path(self: *Self, path: *BFSPath) void {
        std.debug.print("Path {}: ", .{self.visited_path_counter});

        print_node_uuid_and_type(path.start_node);

        for (path.traversed_edges.items) |traversed_edge| {
            std.debug.print(" -> ", .{});
            const end_node = traversed_edge.get_end_node();
            print_node_uuid_and_type(path.start_node.g.bind(end_node));
        }

        std.debug.print("\n", .{});
    }
};

fn try_get_node_type_name(bound_node: BoundNodeReference) ?graph.str {
    if (EdgeType.get_type_edge(bound_node)) |type_edge| {
        const type_node = EdgeType.get_type_node(type_edge.edge);
        return TypeNodeAttributes.of(type_node).get_type_name();
    }
    return null;
}

fn print_node_uuid_and_type(bound_node: BoundNodeReference) void {
    const type_name = try_get_node_type_name(bound_node) orelse @panic("Missing type");
    std.debug.print("{}:{s}", .{ bound_node.node.get_uuid(), type_name });
}
