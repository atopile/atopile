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
};

const BoundNodeReferenceList = struct {
    elements: std.ArrayList(BoundNodeReference),

    fn add_element(self: *@This(), bound_node: BoundNodeReference) void {
        for (self.elements.items) |existing| {
            if (existing.g == bound_node.g and existing.node.is_same(bound_node.node)) {
                return;
            }
        }
        self.elements.append(bound_node) catch @panic("OOM");
    }

    fn add_elements(self: *@This(), other: @This()) void {
        for (other.elements.items) |bound_node| {
            self.add_element(bound_node);
        }
    }
};

const VisitedLevel = struct {
    type_element_list: TypeElementList,
    bound_node_reference_list: BoundNodeReferenceList,

    fn print(self: *const @This()) void {
        std.debug.print("VisitedLevel: ", .{});
        for (self.type_element_list.elements.items) |type_element| {
            std.debug.print("{}:{s} ", .{ type_element.type_node.node.get_uuid(), type_element.child_identifier orelse "<null>" });
        }
        std.debug.print("\n", .{});
        for (self.bound_node_reference_list.elements.items) |bound_node| {
            std.debug.print("  {}\n", .{bound_node.node.get_uuid()});
        }
    }
};

const VisitedLevelList = struct {
    elements: std.ArrayList(VisitedLevel),

    fn add_element(self: *@This(), key: TypeElementList, value: BoundNodeReferenceList) void {
        for (self.elements.items) |*visited_level| {
            if (!visited_level.type_element_list.equals(&key)) continue;
            visited_level.bound_node_reference_list.add_elements(value);
            return;
        }

        var deduped = BoundNodeReferenceList{
            .elements = std.ArrayList(BoundNodeReference).init(value.elements.allocator),
        };
        deduped.add_elements(value);

        self.elements.append(.{
            .type_element_list = key,
            .bound_node_reference_list = deduped,
        }) catch @panic("OOM");
    }
};

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    arena: std.heap.ArenaAllocator,
    visited_path_counter: u64,
    current_bfs_paths: std.ArrayList(*BFSPath),
    nodes_to_bfs: std.ArrayList(BoundNodeReference),
    visited_level_list: VisitedLevelList,

    pub fn init(allocator: std.mem.Allocator) Self {
        var self = Self{
            .allocator = allocator,
            .arena = std.heap.ArenaAllocator.init(allocator),
            .visited_path_counter = 0,
            .current_bfs_paths = undefined,
            .nodes_to_bfs = undefined,
            .visited_level_list = undefined,
        };
        self.current_bfs_paths = std.ArrayList(*BFSPath).init(allocator);
        self.nodes_to_bfs = std.ArrayList(BoundNodeReference).init(allocator);
        self.visited_level_list = VisitedLevelList{
            .elements = std.ArrayList(VisitedLevel).init(self.arena.allocator()),
        };
        return self;
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

        while (self.nodes_to_bfs.pop()) |bound_node| {
            _ = bound_node.g.visit_paths_bfs(
                bound_node,
                void,
                self,
                Self.bfs_visit_fn,
                &[_]graph.Edge.EdgeType{EdgeInterfaceConnection.tid},
            );

            // on first iteration, handle this a bit differently
            if (bound_node.node.is_same(start_node.node)) {
                std.debug.print("First!\n", .{});
                const type_edge = EdgeType.get_type_edge(bound_node) orelse @panic("Missing type edge");
                const type_node = bound_node.g.bind(EdgeType.get_type_node(type_edge.edge));
                const type_element = TypeElement{
                    .type_node = type_node,
                    .child_identifier = null,
                };
                var type_element_list = TypeElementList{
                    .elements = std.ArrayList(TypeElement).init(self.arena.allocator()),
                };
                type_element_list.elements.append(type_element) catch @panic("OOM");
                var bound_node_reference_list = BoundNodeReferenceList{
                    .elements = std.ArrayList(BoundNodeReference).init(self.arena.allocator()),
                };
                bound_node_reference_list.elements.append(bound_node) catch @panic("OOM");
                self.visited_level_list.add_element(type_element_list, bound_node_reference_list);
            }

            for (self.visited_level_list.elements.items) |visited_level| {
                visited_level.print();
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
