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

    fn print(self: *const @This()) void {
        print_type_node(self.type_node);
        std.debug.print(":{s} ", .{
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
        std.debug.print("[", .{});
        for (self.elements.items) |element| {
            element.print();
        }
        std.debug.print("]", .{});
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

    fn print(self: *const @This()) void {
        std.debug.print("[", .{});
        for (self.elements.items) |bound_node| {
            print_instance_node(bound_node);
            std.debug.print(" ", .{});
        }
        std.debug.print("]", .{});
    }
};

const TypePath = struct {
    type_element_list: TypeElementList,
    bound_node_reference_list: BoundNodeReferenceList,

    fn print(self: *const @This()) void {
        std.debug.print("Type Path: ", .{});
        self.type_element_list.print();
        std.debug.print("\tInstances: ", .{});
        self.bound_node_reference_list.print();
    }
};

const TypePathList = struct {
    allocator: std.mem.Allocator,
    elements: std.ArrayList(*TypePath),

    fn add_element(self: *@This(), key: TypeElementList, value: BoundNodeReferenceList) void {
        for (self.elements.items) |type_path| {
            if (!type_path.type_element_list.equals(&key)) continue;
            type_path.bound_node_reference_list.add_elements(value);
            return;
        }

        var deduped = BoundNodeReferenceList{
            .elements = std.ArrayList(BoundNodeReference).init(value.elements.allocator),
        };
        deduped.add_elements(value);

        const new_type_path = self.allocator.create(TypePath) catch @panic("OOM");
        new_type_path.* = .{
            .type_element_list = key,
            .bound_node_reference_list = deduped,
        };
        self.elements.append(new_type_path) catch @panic("OOM");
    }

    fn get_nodes(self: @This(), key: TypeElementList) ?*BoundNodeReferenceList {
        for (self.elements.items) |type_path| {
            if (type_path.type_element_list.equals(&key)) {
                return &type_path.bound_node_reference_list;
            }
        }

        return null;
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

        self.visited_list.add_element(self.bfs_type_element_stack, BoundNodeReferenceList{
            .elements = std.ArrayList(BoundNodeReference).init(self.arena.allocator()),
        });

        var first_bound_node_reference_list = BoundNodeReferenceList{
            .elements = std.ArrayList(BoundNodeReference).init(self.arena.allocator()),
        };
        first_bound_node_reference_list.add_element(start_node);
        self.to_visit_list.add_element(self.bfs_type_element_stack, first_bound_node_reference_list);

        // iterate through each type path
        while (self.to_visit_list.elements.pop()) |type_path| {

            // iterate through all connected nodes for a given type path
            while (type_path.bound_node_reference_list.elements.pop()) |node_to_bfs| {

                // Horizontal traverse
                _ = node_to_bfs.g.visit_paths_bfs(
                    node_to_bfs,
                    void,
                    self,
                    Self.bfs_visit_fn,
                    &[_]graph.Edge.EdgeType{EdgeInterfaceConnection.tid},
                );

                var visited_node_list = BoundNodeReferenceList{
                    .elements = std.ArrayList(BoundNodeReference).init(self.arena.allocator()),
                };

                for (self.current_bfs_paths.items) |path| {
                    visited_node_list.elements.append(path.get_last_node()) catch @panic("OOM");
                }

                self.visited_list.add_element(type_path.type_element_list, visited_node_list);

                // Down traverse
                for (self.current_bfs_paths.items) |path| {
                    std.debug.print("GOING DOWNNNN: ", .{});
                    const last_node = path.get_last_node();
                    const child_type_element = type_path.type_element_list.elements.getLast();
                    if (child_type_element.child_identifier) |child_identifier| {
                        child_type_element.print();

                        print_instance_node(last_node);
                        std.debug.print("CHILD IDENTIFIER:{s}", .{child_identifier});

                        std.debug.print("\n", .{});
                    } else {
                        std.debug.print("NADA\n", .{});
                    }
                }

                // Up traverse
                for (self.current_bfs_paths.items) |path| {
                    const last_node = path.get_last_node();
                    if (EdgeComposition.get_parent_node_of(last_node)) |parent_node| {
                        // parent_node_list.add_element(parent_node);
                        const parent_edge = EdgeComposition.get_parent_edge(last_node).?;
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

                        const blank_list = BoundNodeReferenceList{
                            .elements = std.ArrayList(BoundNodeReference).init(self.arena.allocator()),
                        };
                        _ = blank_list;

                        var parent_node_list = BoundNodeReferenceList{
                            .elements = std.ArrayList(BoundNodeReference).init(self.arena.allocator()),
                        };
                        parent_node_list.add_element(parent_node);

                        self.to_visit_list.add_element(type_element_list, parent_node_list);
                        self.visited_list.add_element(type_element_list, parent_node_list);

                        for (self.to_visit_list.elements.items) |to_visit| {
                            std.debug.print("To visit: ", .{});
                            to_visit.print();
                            std.debug.print("\n", .{});
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

        for (self.visited_list.elements.items) |visited| {
            std.debug.print("Visited: ", .{});
            visited.print();
            std.debug.print("\n", .{});
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

        print_instance_node(path.start_node);

        for (path.traversed_edges.items) |traversed_edge| {
            std.debug.print(" -> ", .{});
            const end_node = traversed_edge.get_end_node();
            print_instance_node(path.start_node.g.bind(end_node));
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

fn print_instance_node(bound_node: BoundNodeReference) void {
    const type_name = try_get_node_type_name(bound_node) orelse @panic("Missing type");
    std.debug.print("{}:{s}", .{ bound_node.node.get_uuid(), type_name });
}

fn print_type_node(bound_node: BoundNodeReference) void {
    const type_name = TypeNodeAttributes.of(bound_node.node).get_type_name();
    std.debug.print("type:", .{});
    std.debug.print("{s}", .{type_name});
}
