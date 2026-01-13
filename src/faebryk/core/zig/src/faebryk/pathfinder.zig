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

fn dbg_print(comptime fmt: []const u8, args: anytype) void {
    if (comptime debug_pathfinder) {
        std.debug.print(fmt, args);
    }
}

const BoundNodeRefMap = struct {};

const TypeElement = struct {
    type_node: BoundNodeReference,
    child_identifier: ?[]const u8,

    fn equals(self: *const @This(), other: *const @This()) bool {
        if (!self.type_node.node.is_same(other.type_node.node)) return false;
        if (self.child_identifier == null) return other.child_identifier == null;
        if (other.child_identifier == null) return false;
        return std.mem.eql(u8, self.child_identifier.?, other.child_identifier.?);
    }

    fn print(self: *const @This()) void {
        print_type_node(self.type_node);
        dbg_print(":{s} ", .{
            self.child_identifier orelse "<null>",
        });
    }
};

const TypeElementList = struct {
    elements: std.ArrayList(TypeElement),

    fn equals(self: *const @This(), other: *const @This()) bool {
        if (self.elements.items.len != other.elements.items.len) return false;
        for (self.elements.items, 0..) |element, i| {
            if (!element.equals(&other.elements.items[i])) return false;
        }
        return true;
    }

    fn print(self: *const @This()) void {
        dbg_print("[", .{});
        for (self.elements.items) |element| {
            element.print();
        }
        dbg_print("]", .{});
    }
};

const InstancePathList = struct {
    elements: std.ArrayList(*BFSPath),

    fn add_path(self: *@This(), path: *BFSPath) void {
        const path_last = path.get_last_node();
        for (self.elements.items, 0..) |existing, i| {
            const existing_last = existing.get_last_node();
            // Dedup by end node; type path is handled at the TypePath key level.
            if (existing_last.g == path_last.g and existing_last.node.is_same(path_last.node)) {
                if (path.traversed_edges.items.len < existing.traversed_edges.items.len) {
                    self.elements.items[i] = path;
                }
                return;
            }
        }
        self.elements.append(path) catch @panic("OOM");
    }

    fn add_paths(self: *@This(), other: @This()) void {
        for (other.elements.items) |path| {
            self.add_path(path);
        }
    }

    fn print(self: *const @This()) void {
        for (self.elements.items, 0..) |path, i| {
            if (i != 0) dbg_print("\n", .{});
            dbg_print("\t", .{});
            print_instance_path(path);
        }
    }
};

const TypePath = struct {
    type_element_list: TypeElementList,
    instance_paths: InstancePathList,

    fn print(self: *const @This()) void {
        dbg_print("Type Path: ", .{});
        self.type_element_list.print();
        dbg_print("\tInstances:\n", .{});
        self.instance_paths.print();
    }
};

const TypePathList = struct {
    allocator: std.mem.Allocator,
    elements: std.ArrayList(*TypePath),

    fn add_element(self: *@This(), key: TypeElementList, value: InstancePathList) void {
        for (self.elements.items) |type_path| {
            if (!type_path.type_element_list.equals(&key)) continue;
            type_path.instance_paths.add_paths(value);
            return;
        }

        var deduped = InstancePathList{
            .elements = std.ArrayList(*BFSPath).init(value.elements.allocator),
        };
        deduped.add_paths(value);

        const new_type_path = self.allocator.create(TypePath) catch @panic("OOM");
        new_type_path.* = .{
            .type_element_list = key,
            .instance_paths = deduped,
        };
        self.elements.append(new_type_path) catch @panic("OOM");
    }

    fn get_paths(self: @This(), key: TypeElementList) ?*InstancePathList {
        for (self.elements.items) |type_path| {
            if (type_path.type_element_list.equals(&key)) {
                return &type_path.instance_paths;
            }
        }

        return null;
    }

    fn contains_node(self: *const @This(), key: TypeElementList, node: BoundNodeReference) bool {
        const paths = self.get_paths(key) orelse return false;
        for (paths.elements.items) |existing| {
            const existing_last = existing.get_last_node();
            if (existing_last.g == node.g and existing_last.node.is_same(node.node)) return true;
        }
        return false;
    }
};

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    arena: std.heap.ArenaAllocator,
    visited_path_counter: u64,
    current_bfs_paths: std.ArrayList(*BFSPath),
    nodes_to_bfs: std.ArrayList(BoundNodeReference),
    bfs_type_element_stack: TypeElementList,
    to_visit_list: TypePathList,
    visited_list: TypePathList,

    pub fn init(self: *Self, allocator: std.mem.Allocator) void {
        self.* = .{
            .allocator = allocator,
            .arena = std.heap.ArenaAllocator.init(allocator),
            .visited_path_counter = 0,
            .current_bfs_paths = undefined,
            .nodes_to_bfs = undefined,
            .bfs_type_element_stack = undefined,
            .to_visit_list = undefined,
            .visited_list = undefined,
        };
        self.current_bfs_paths = std.ArrayList(*BFSPath).init(allocator);
        self.nodes_to_bfs = std.ArrayList(BoundNodeReference).init(allocator);
        self.bfs_type_element_stack = TypeElementList{
            .elements = std.ArrayList(TypeElement).init(self.arena.allocator()),
        };
        self.to_visit_list = TypePathList{
            .allocator = self.arena.allocator(),
            .elements = std.ArrayList(*TypePath).init(self.arena.allocator()),
        };
        self.visited_list = TypePathList{
            .allocator = self.arena.allocator(),
            .elements = std.ArrayList(*TypePath).init(self.arena.allocator()),
        };
    }

    pub fn deinit(self: *Self) void {
        self.arena.deinit();
        self.nodes_to_bfs.deinit();
    }

    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
    ) !graph.BFSPaths {
        self.nodes_to_bfs.append(start_node) catch @panic("OOM");

        // boot strap first iteration
        const first_type_edge = EdgeType.get_type_edge(start_node).?;
        const first_type_node = start_node.g.bind(EdgeType.get_type_node(first_type_edge.edge));
        const first_type_element = TypeElement{
            .type_node = first_type_node,
            .child_identifier = null,
        };
        self.bfs_type_element_stack.elements.append(first_type_element) catch @panic("OOM");

        const start_path = BFSPath.init(self.arena.allocator(), start_node) catch @panic("OOM");
        var first_instance_path_list = InstancePathList{
            .elements = std.ArrayList(*BFSPath).init(self.arena.allocator()),
        };
        first_instance_path_list.add_path(start_path);
        self.to_visit_list.add_element(self.bfs_type_element_stack, first_instance_path_list);
        self.visited_list.add_element(self.bfs_type_element_stack, first_instance_path_list);

        // iterate through each type path
        while (self.to_visit_list.elements.pop()) |type_path| {

            // iterate through all connected nodes for a given type path
            while (type_path.instance_paths.elements.pop()) |path_to_bfs| {
                const node_to_bfs = path_to_bfs.get_last_node();

                // Horizontal traverse
                _ = node_to_bfs.g.visit_paths_bfs(
                    node_to_bfs,
                    void,
                    self,
                    Self.bfs_visit_fn,
                    &[_]graph.Edge.EdgeType{EdgeInterfaceConnection.tid},
                );

                var visited_path_list = InstancePathList{
                    .elements = std.ArrayList(*BFSPath).init(self.arena.allocator()),
                };

                for (self.current_bfs_paths.items) |path| {
                    const combined_path = self.concat_paths(path_to_bfs, path);
                    if (!has_is_interface_trait(combined_path.get_last_node())) {
                        continue;
                    }
                    const start_len = self.bfs_type_element_stack.elements.items.len;
                    const current_len = type_path.type_element_list.elements.items.len;
                    const allow_shallow = current_len <= start_len;
                    if (!allow_shallow and path_has_shallow_edge(combined_path)) {
                        continue;
                    }
                    visited_path_list.add_path(combined_path);
                }

                self.visited_list.add_element(type_path.type_element_list, visited_path_list);

                // Down traverse
                for (visited_path_list.elements.items) |path| {
                    const last_node = path.get_last_node();
                    const child_type_element = type_path.type_element_list.elements.getLast();
                    if (child_type_element.child_identifier) |child_identifier| {
                        const child_node = EdgeComposition.get_child_by_identifier(last_node, child_identifier) orelse {
                            dbg_print("Skipping missing child '{s}' on node ", .{child_identifier});
                            print_instance_node(last_node);
                            dbg_print("\n", .{});
                            continue;
                        };
                        const child_edge = EdgeComposition.get_parent_edge(child_node) orelse @panic("child edge not found");
                        const child_path = self.extend_path(path, last_node, child_edge);
                        // dbg_print("CHILD NODE: ", .{});
                        // print_instance_node(child_node);
                        // dbg_print("\n", .{});
                        // dbg_print("PARENT TYPE ELEMENT LIST: ", .{});
                        // type_path.type_element_list.print();
                        // dbg_print("\n", .{});
                        var child_type_element_list = TypeElementList{
                            .elements = std.ArrayList(TypeElement).init(self.arena.allocator()),
                        };
                        const type_items = type_path.type_element_list.elements.items;
                        if (type_items.len > 0) {
                            child_type_element_list.elements.appendSlice(type_items[0 .. type_items.len - 1]) catch @panic("OOM");
                        }
                        // dbg_print("CHILD TYPE ELEMENT LIST: ", .{});
                        // child_type_element_list.print();
                        // dbg_print("\n", .{});

                        var child_path_list = InstancePathList{
                            .elements = std.ArrayList(*BFSPath).init(self.arena.allocator()),
                        };
                        child_path_list.add_path(child_path);

                        if (!self.visited_list.contains_node(child_type_element_list, child_node) and
                            !self.to_visit_list.contains_node(child_type_element_list, child_node))
                        {
                            self.to_visit_list.add_element(child_type_element_list, child_path_list);
                            self.visited_list.add_element(child_type_element_list, child_path_list);
                        }
                    }
                }

                // Up traverse
                for (visited_path_list.elements.items) |path| {
                    const last_node = path.get_last_node();
                    if (EdgeComposition.get_parent_node_of(last_node)) |parent_node| {
                        // parent_node_list.add_element(parent_node);
                        const parent_edge = EdgeComposition.get_parent_edge(last_node).?;
                        const parent_path = self.extend_path(path, last_node, parent_edge);
                        const child_identifier = EdgeComposition.get_name(parent_edge.edge) catch @panic("corrupt edge");
                        const parent_type_edge = EdgeType.get_type_edge(parent_node).?;
                        const parent_type_node = parent_node.g.bind(EdgeType.get_type_node(parent_type_edge.edge));
                        const type_element = TypeElement{
                            .type_node = parent_type_node,
                            .child_identifier = child_identifier,
                        };

                        var type_element_list = TypeElementList{
                            .elements = std.ArrayList(TypeElement).init(self.arena.allocator()),
                        };

                        for (type_path.type_element_list.elements.items) |element| {
                            type_element_list.elements.append(element) catch @panic("OOM");
                        }

                        type_element_list.elements.append(type_element) catch @panic("OOM");

                        var parent_path_list = InstancePathList{
                            .elements = std.ArrayList(*BFSPath).init(self.arena.allocator()),
                        };
                        parent_path_list.add_path(parent_path);

                        if (!self.visited_list.contains_node(type_element_list, parent_node) and
                            !self.to_visit_list.contains_node(type_element_list, parent_node))
                        {
                            self.to_visit_list.add_element(type_element_list, parent_path_list);
                            self.visited_list.add_element(type_element_list, parent_path_list);
                        }

                        for (self.to_visit_list.elements.items) |to_visit| {
                            dbg_print("To visit: ", .{});
                            to_visit.print();
                            dbg_print("\n", .{});
                        }
                    }
                }

                // Clean up current_bfs_paths for next iteration
                for (self.current_bfs_paths.items) |path| {
                    path.deinit();
                }
                self.current_bfs_paths.deinit();
                self.current_bfs_paths = std.ArrayList(*BFSPath).init(self.allocator);
            }
        }
        dbg_print("RESULTING VISITED LIST\n", .{});
        for (self.visited_list.elements.items) |visited| {
            visited.print();
            dbg_print("\n", .{});
        }

        dbg_print("RESULTING TO VISIT LIST\n", .{});
        for (self.to_visit_list.elements.items) |to_visit_list| {
            to_visit_list.print();
            dbg_print("\n", .{});
        }

        // Return paths at the same hierarchy level as the start node.
        var bfs_paths = graph.BFSPaths.init(self.allocator);
        if (self.visited_list.get_paths(self.bfs_type_element_stack)) |root_paths| {
            bfs_paths.paths.ensureTotalCapacity(root_paths.elements.items.len) catch @panic("OOM");
            for (root_paths.elements.items) |path| {
                const copied_path = path.copy(self.allocator) catch @panic("OOM");
                bfs_paths.paths.appendAssumeCapacity(copied_path);
            }
        }
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
        dbg_print("Path {}: ", .{self.visited_path_counter});

        print_instance_path(path);

        dbg_print("\n", .{});
    }

    fn concat_paths(self: *Self, prefix: *const BFSPath, suffix: *const BFSPath) *BFSPath {
        std.debug.assert(prefix.g == suffix.g);
        const prefix_last = prefix.get_last_node();
        std.debug.assert(prefix_last.node.is_same(suffix.start_node.node));

        var combined = BFSPath.init(self.arena.allocator(), prefix.start_node) catch @panic("OOM");
        const total_len = prefix.traversed_edges.items.len + suffix.traversed_edges.items.len;
        combined.traversed_edges.ensureTotalCapacity(total_len) catch @panic("OOM");
        combined.traversed_edges.appendSliceAssumeCapacity(prefix.traversed_edges.items);
        combined.traversed_edges.appendSliceAssumeCapacity(suffix.traversed_edges.items);
        combined.invalid_path = prefix.invalid_path or suffix.invalid_path;
        combined.stop_new_path_discovery = prefix.stop_new_path_discovery or suffix.stop_new_path_discovery;
        combined.visit_strength = suffix.visit_strength;
        return combined;
    }

    fn extend_path(self: *Self, base: *const BFSPath, from_node: BoundNodeReference, edge: BoundEdgeReference) *BFSPath {
        return BFSPath.cloneAndExtend(self.arena.allocator(), base, from_node, edge.edge) catch @panic("OOM");
    }
};

fn try_get_node_type_name(bound_node: BoundNodeReference) ?graph.str {
    if (EdgeType.get_type_edge(bound_node)) |type_edge| {
        const type_node = EdgeType.get_type_node(type_edge.edge);
        return TypeNodeAttributes.of(type_node).get_type_name();
    }
    return null;
}

fn print_instance_node(bound_node: BoundNodeReference) void {
    const type_name = try_get_node_type_name(bound_node) orelse @panic("Missing type");
    dbg_print("{}:{s}", .{ bound_node.node.get_uuid(), type_name });
}

fn has_is_interface_trait(bound_node: BoundNodeReference) bool {
    const tg = typegraph_mod.TypeGraph.of_instance(bound_node) orelse return false;
    const is_interface_type = tg.get_type_by_name("is_interface.node.core.faebryk") orelse return false;
    return EdgeTrait.try_get_trait_instance_of_type(bound_node, is_interface_type.node) != null;
}

fn path_has_shallow_edge(path: *const BFSPath) bool {
    for (path.traversed_edges.items) |traversed_edge| {
        const edge = traversed_edge.edge;
        if (EdgeInterfaceConnection.is_instance(edge)) {
            const shallow_edge = (edge.get(EdgeInterfaceConnection.shallow_attribute) orelse continue).Bool;
            if (shallow_edge) return true;
        }
    }
    return false;
}

fn print_instance_path(path: *const BFSPath) void {
    print_instance_node(path.start_node);
    for (path.traversed_edges.items) |traversed_edge| {
        dbg_print(" -> ", .{});
        const end_node = traversed_edge.get_end_node();
        print_instance_node(path.start_node.g.bind(end_node));
    }
}

fn print_type_node(bound_node: BoundNodeReference) void {
    const type_name = TypeNodeAttributes.of(bound_node.node).get_type_name();
    dbg_print("type:", .{});
    dbg_print("{s}", .{type_name});
}
