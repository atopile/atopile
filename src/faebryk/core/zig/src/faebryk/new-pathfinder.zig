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

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    visited_path_counter: u64,
    current_bfs_paths: std.ArrayList(*BFSPath),
    nodes_to_bfs: std.ArrayList(BoundNodeReference),

    pub fn init(allocator: std.mem.Allocator) Self {
        return .{
            .allocator = allocator,
            .visited_path_counter = 0,
            .current_bfs_paths = std.ArrayList(*BFSPath).init(allocator),
            .nodes_to_bfs = std.ArrayList(BoundNodeReference).init(allocator),
        };
    }

    pub fn deinit(self: *Self) void {
        for (self.current_bfs_paths.items) |path| {
            path.deinit();
        }
        self.current_bfs_paths.deinit();
        self.nodes_to_bfs.deinit();
    }

    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
    ) !graph.BFSPaths {
        std.debug.print("Finding paths from {}\n", .{start_node.node.get_uuid()});

        self.nodes_to_bfs.append(start_node) catch @panic("OOM");

        while (self.nodes_to_bfs.pop()) |node| {
            _ = node.g.visit_paths_bfs(
                node,
                void,
                self,
                Self.bfs_visit_fn,
                &[_]graph.Edge.EdgeType{EdgeInterfaceConnection.tid},
            );

            for (self.current_bfs_paths.items) |path| {
                const parent_node = EdgeComposition.get_parent_node_of(path.get_last_node()) orelse continue;
                print_node_uuid_and_type(parent_node);
                std.debug.print("\n", .{});
                self.nodes_to_bfs.append(parent_node) catch @panic("OOM");
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
