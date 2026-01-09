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

pub const StackElement = struct {
    // Pair of node and named child identifier
    bound_node: BoundNodeReference,
    child_identifier: []const u8,

    pub fn print_element(self: *const @This()) void {
        print_node_uuid_and_type(self.bound_node);
        std.debug.print(".{s}\n", .{self.child_identifier});
    }
};

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    visited_path_counter: u64,
    current_bfs_paths: std.ArrayList(*BFSPath),
    stack_elements_to_bfs: std.ArrayList(StackElement),

    pub fn init(allocator: std.mem.Allocator) Self {
        return .{
            .allocator = allocator,
            .visited_path_counter = 0,
            .current_bfs_paths = std.ArrayList(*BFSPath).init(allocator),
            .stack_elements_to_bfs = std.ArrayList(StackElement).init(allocator),
        };
    }

    pub fn deinit(self: *Self) void {
        for (self.current_bfs_paths.items) |path| {
            path.deinit();
        }
        self.current_bfs_paths.deinit();
        self.stack_elements_to_bfs.deinit();
    }

    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
    ) !graph.BFSPaths {
        std.debug.print("Finding paths from {}\n", .{start_node.node.get_uuid()});

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

            // For each connected interface, add stack element to BFS queue
            for (self.current_bfs_paths.items) |path| {
                const bound_node = EdgeComposition.get_parent_node_of(path.get_last_node()) orelse continue;
                const parent_edge = EdgeComposition.get_parent_edge(path.get_last_node()) orelse continue;
                const child_identifier = EdgeComposition.get_name(parent_edge.edge) catch continue;
                const stack_element_to_append = StackElement{ .bound_node = bound_node, .child_identifier = child_identifier };
                self.stack_elements_to_bfs.append(stack_element_to_append) catch @panic("OOM");
                if (comptime debug_pathfinder) {
                    std.debug.print("Adding stack element: ", .{});
                    stack_element_to_append.print_element();
                }
            }

            for (self.current_bfs_paths.items) |path| {
                path.deinit();
            }
            self.current_bfs_paths.deinit();
            self.current_bfs_paths = std.ArrayList(*BFSPath).init(self.allocator);
        }

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
    if (try_get_node_type_name(bound_node)) |type_name| {
        std.debug.print("{}:{s}", .{ bound_node.node.get_uuid(), type_name });
    } else std.debug.print("{}:<no_type>", .{bound_node.node.get_uuid()});
}
