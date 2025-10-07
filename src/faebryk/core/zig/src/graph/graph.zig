const std = @import("std");
pub const str = []const u8;
const visitor = @import("visitor.zig");

const NodeRefMap = struct {
    pub fn eql(_: @This(), a: NodeReference, b: NodeReference) bool {
        return Node.is_same(a, b);
    }

    pub fn hash(_: @This(), adapted_key: NodeReference) u64 {
        return adapted_key.attributes.uuid;
    }

    pub fn T(V: type) type {
        return std.HashMap(NodeReference, V, NodeRefMap, std.hash_map.default_max_load_percentage);
    }
};

const EdgeRefMap = struct {
    pub fn eql(_: @This(), a: EdgeReference, b: EdgeReference) bool {
        return Edge.is_same(a, b);
    }

    pub fn hash(_: @This(), adapted_key: EdgeReference) u64 {
        return adapted_key.uuid;
    }

    pub fn T(V: type) type {
        return std.HashMap(EdgeReference, V, EdgeRefMap, std.hash_map.default_max_load_percentage);
    }
};

const IntMap = struct {
    pub fn eql(_: @This(), a: i64, b: i64) bool {
        return a == b;
    }

    pub fn hash(_: @This(), adapted_key: i64) u64 {
        var key = adapted_key;
        return std.hash.Wyhash.hash(0, std.mem.asBytes(&key));
    }

    pub fn T(V: type) type {
        return std.HashMap(i64, V, IntMap, std.hash_map.default_max_load_percentage);
    }
};

const EdgeTypeMap = IntMap;

pub const Literal = union(enum) {
    Int: i64,
    Uint: u64,
    Float: f64,
    String: str,
    Bool: bool,
};

pub const Attribute = struct {
    identifier: str,
    value: Literal,

    fn gen_string_property(comptime identifier: str) Attribute {
        return struct {
            pub fn get(N: NodeReference) str {
                return N.dynamic.get(identifier).?.String;
            }

            pub fn set(N: NodeReference, value: str) void {
                N.dynamic.put(identifier, Literal{ .String = value });
            }
        };
    }

    fn gen_tristate_property(comptime identifier: str) Attribute {
        return struct {
            pub fn get(N: NodeReference) ?bool {
                const out = N.dynamic.get(identifier);
                if (out) |o| {
                    return o.Bool;
                }
                return null;
            }

            pub fn set(N: NodeReference, value: bool) void {
                N.dynamic.put(identifier, Literal{ .Bool = value });
            }
        };
    }

    fn gen_enum_property(comptime identifier: str, comptime T: type) Attribute {
        return struct {
            pub fn get(N: NodeReference) ?T {
                const out = N.dynamic.get(identifier);
                if (out) |o| {
                    return std.meta.intToEnum(T, o.Int).?;
                }
                return null;
            }

            pub fn set(N: NodeReference, value: T) void {
                N.dynamic.put(identifier, Literal{ .Int = @intFromEnum(value) });
            }
        };
    }
};

pub const DynamicAttributes = struct {
    values: std.StringHashMap(Literal),

    fn init(allocator: std.mem.Allocator) @This() {
        return .{
            .values = std.StringHashMap(Literal).init(allocator),
        };
    }

    fn deinit(self: *@This()) void {
        self.values.deinit();
    }

    fn visit(self: *@This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        for (self.values.keys()) |key| {
            f(ctx, key, self.values.get(key).?, true);
        }
    }
};

pub const GraphReferenceCounter = struct {
    ref_count: usize = 0,
    parent: *anyopaque,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator, parent: *anyopaque) @This() {
        return .{
            .ref_count = 0,
            .parent = parent,
            .allocator = allocator,
        };
    }

    pub fn check_in_use(self: *@This()) !void {
        if (self.ref_count > 0) {
            return error.InUse;
        }
    }

    pub fn inc(self: *@This(), g: *GraphView) void {
        _ = g;
        self.ref_count += 1;
    }

    pub fn dec(self: *@This(), g: *GraphView) void {
        _ = g;
        self.ref_count -= 1;
    }
};

pub const UUID = struct {
    const T = u64;

    pub fn gen_uuid(obj: *anyopaque) UUID.T {
        // convert pointer to int
        // guaranteed to be unique inside process
        return @intFromPtr(obj);
    }

    pub fn equals(U1: UUID.T, U2: UUID.T) bool {
        return U1 == U2;
    }
};

pub const NodeAttributes = struct {
    uuid: UUID.T,
    dynamic: DynamicAttributes,

    pub fn visit(self: *@This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        f(ctx, "uuid", Literal{ .Int = self.uuid }, false);
        self.dynamic.visit(ctx, f);
    }
};

pub const Node = struct {
    attributes: NodeAttributes,
    _ref_count: GraphReferenceCounter,

    pub fn init(allocator: std.mem.Allocator) !NodeReference {
        const node = try allocator.create(Node);

        // Attributes
        node.attributes.uuid = UUID.gen_uuid(node);
        node.attributes.dynamic = DynamicAttributes.init(allocator);

        node._ref_count = GraphReferenceCounter.init(allocator, node);
        return node;
    }

    pub fn deinit(self: *@This()) void {
        self._ref_count.check_in_use() catch {
            @panic("Node is still in use");
        };
        self.attributes.dynamic.deinit();
        self._ref_count.allocator.destroy(self);
    }

    pub fn is_same(N1: NodeReference, N2: NodeReference) bool {
        return UUID.equals(N1.attributes.uuid, N2.attributes.uuid);
    }
};

pub const NodeReference = *Node;
pub const EdgeReference = *Edge;

pub const EdgeAttributes = struct {
    source_id: UUID.T,
    target_id: UUID.T,
    uuid: UUID.T,
    edge_type: Edge.EdgeType,
    directional: ?bool,
    name: ?str,
    dynamic: DynamicAttributes,

    pub fn init(allocator: std.mem.Allocator, source: NodeReference, target: NodeReference, edge_type: Edge.EdgeType) !*@This() {
        var edge = try allocator.create(Edge);
        edge.source = source;
        edge.target = target;
        edge.uuid = UUID.gen_uuid();
        edge.edge_type = edge_type;
        edge.dynamic = DynamicAttributes.init(allocator);
        edge._ref_count = .{
            .parent = edge,
            .allocator = allocator,
        };
        return edge;
    }

    pub fn deinit(self: *@This()) !void {
        if (self._ref_count.ref_count > 0) {
            return error.InUse;
        }
        self.dynamic.deinit();
        self._ref_count.allocator.destroy(self);
    }

    fn visit_attributes(self: *@This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        f(ctx, "source", Literal{ .Int = self.source.uuid }, false);
        f(ctx, "target", Literal{ .Int = self.target.uuid }, false);
        f(ctx, "type", Literal{ .Int = @intFromEnum(self.edge_type) }, false);
        f(ctx, "uuid", Literal{ .Int = self.uuid }, false);
        f(ctx, "directional", Literal{ .Bool = self.directional.? }, false);
        f(ctx, "name", Literal{ .String = self.name.? }, false);
        self.dynamic.visit(ctx, f);
    }
};

pub fn ComptimeIntSet(max_count: usize, int_type: type) type {
    return struct {
        values: [max_count]int_type = undefined,
        count: usize = 0,

        pub fn add(self: *@This(), value: int_type) !void {
            for (self.values[0..self.count]) |v| {
                if (v == value) {
                    return error.AlreadyExists;
                }
            }
            if (self.count == max_count) {
                return error.MaxCountReached;
            }
            self.values[self.count] = value;
            self.count += 1;
        }

        pub fn contains(self: *@This(), value: int_type) bool {
            for (self.values[0..self.count]) |v| {
                if (v == value) {
                    return true;
                }
            }
            return false;
        }
    };
}

pub const Edge = struct {
    source: NodeReference,
    target: NodeReference,

    attributes: EdgeAttributes,
    _ref_count: GraphReferenceCounter,

    pub fn init(allocator: std.mem.Allocator, source: NodeReference, target: NodeReference, edge_type: EdgeType) !*@This() {
        var edge = try allocator.create(Edge);
        edge.source = source;
        edge.target = target;

        // Attributes
        edge.attributes.uuid = UUID.gen_uuid(edge);
        edge.attributes.edge_type = edge_type;
        edge.attributes.source_id = source.attributes.uuid;
        edge.attributes.target_id = target.attributes.uuid;
        edge.attributes.dynamic = DynamicAttributes.init(allocator);

        edge._ref_count = GraphReferenceCounter.init(allocator, edge);
        return edge;
    }

    pub fn deinit(self: *@This()) void {
        self._ref_count.check_in_use() catch {
            @panic("Edge is still in use");
        };
        self.attributes.dynamic.deinit();
        self._ref_count.allocator.destroy(self);
    }

    pub const EdgeType = i64;
    pub var type_set: IntMap.T(void) = IntMap.T(void).init(std.heap.page_allocator);

    /// Register type and check for duplicates during runtime
    /// Can't do during compile because python will do during runtime
    pub fn register_type(edge_type: EdgeType) !void {
        if (type_set.get(edge_type)) |_| {
            return error.DuplicateType;
        }
        try type_set.put(edge_type, {});
    }

    pub fn is_instance(E: EdgeReference, edge_type: EdgeType) bool {
        return E.attributes.edge_type == edge_type;
    }

    pub fn is_same(E1: EdgeReference, E2: EdgeReference) bool {
        return UUID.equals(E1.attributes.uuid, E2.attributes.uuid);
    }

    pub fn get_source(E: EdgeReference) ?NodeReference {
        if (E.attributes.directional) |d| {
            if (d) {
                return E.source;
            }
            return E.target;
        }
        return null;
    }

    pub fn get_target(E: EdgeReference) ?NodeReference {
        if (E.attributes.directional) |d| {
            if (d) {
                return E.target;
            }
            return E.source;
        }
        return null;
    }

    pub fn get_other_node(self: *const @This(), N: NodeReference) ?NodeReference {
        if (Node.is_same(self.source, N)) {
            return self.target;
        } else if (Node.is_same(self.target, N)) {
            return self.source;
        } else {
            return null; // Returns null if given node and edge were not connected in the first place
        }
    }

    /// No guarantee that there is only one
    pub fn get_single_edge(bound_node: BoundNodeReference, edge_type: EdgeType, is_target: ?bool) ?BoundEdgeReference {
        const Visit = struct {
            bound_node: BoundNodeReference,
            is_target: ?bool,

            pub fn visit(ctx: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(BoundEdgeReference) {
                const self: *@This() = @ptrCast(@alignCast(ctx));
                if (self.is_target) |d| {
                    if (d) {
                        const target = bound_edge.edge.get_target();
                        if (target) |t| {
                            if (Node.is_same(t, self.bound_node.node)) {
                                return visitor.VisitResult(BoundEdgeReference){ .OK = bound_edge };
                            }
                        }
                        return visitor.VisitResult(BoundEdgeReference){ .CONTINUE = {} };
                    } else {
                        const source = bound_edge.edge.get_source();
                        if (source) |s| {
                            if (Node.is_same(s, self.bound_node.node)) {
                                return visitor.VisitResult(BoundEdgeReference){ .OK = bound_edge };
                            }
                        }
                        return visitor.VisitResult(BoundEdgeReference){ .CONTINUE = {} };
                    }
                }
                return visitor.VisitResult(BoundEdgeReference){ .OK = bound_edge };
            }
        };

        var visit = Visit{ .bound_node = bound_node, .is_target = is_target };

        const result = bound_node.visit_edges_of_type(edge_type, BoundEdgeReference, &visit, Visit.visit);
        switch (result) {
            .OK => return result.OK,
            .EXHAUSTED => return null,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => |err| @panic(@errorName(err)),
        }
    }
};

pub const Path = struct {
    edges: std.ArrayList(EdgeReference),

    pub fn init(a: std.mem.Allocator) @This() {
        return .{
            .edges = std.ArrayList(EdgeReference).init(a),
        };
    }

    pub fn deinit(self: *@This()) void {
        self.edges.deinit();
    }

    pub fn print_path(self: *const @This()) void {
        std.debug.print("PATH - len: {} - ", .{self.edges.items.len});
        for (self.edges.items) |edge| {
            std.debug.print("{}->", .{edge.attributes.uuid});
        }
        std.debug.print("\n", .{});
    }

    pub fn get_other_node(self: *const @This(), bn: BoundNodeReference) ?BoundNodeReference {
        if (self.edges.items.len == 0) {
            return null;
        }
        // const first_edge = self.edges.items[0];
        const last_edge = self.edges.items[self.edges.items.len - 1];

        // special case - path length 1
        if (self.edges.items.len == 1) {
            return bn.g.bind(last_edge.get_other_node(bn.node) orelse return null);
        }
        const second_last_edge = self.edges.items[self.edges.items.len - 2];

        // this doesn't check if the start and end node are the same
        if (Node.is_same(last_edge.target, second_last_edge.target)) {
            return bn.g.bind(last_edge.get_other_node(last_edge.target) orelse return null);
        }
        if (Node.is_same(last_edge.target, second_last_edge.source)) {
            return bn.g.bind(last_edge.get_other_node(last_edge.target) orelse return null);
        }
        if (Node.is_same(last_edge.source, second_last_edge.target)) {
            return bn.g.bind(last_edge.get_other_node(last_edge.source) orelse return null);
        }
        if (Node.is_same(last_edge.source, second_last_edge.source)) {
            return bn.g.bind(last_edge.get_other_node(last_edge.source) orelse return null);
        }

        return null;
    }
};

pub const BoundNodeReference = struct {
    node: NodeReference,
    g: *GraphView,

    pub fn get_edges(self: *const @This()) ?*const std.ArrayList(EdgeReference) {
        return self.g.get_edges(self.node);
    }

    pub fn get_edges_of_type(self: *const @This(), T: Edge.EdgeType) ?*const std.ArrayList(EdgeReference) {
        return self.g.get_edges_of_type(self.node, T);
    }

    pub fn visit_edges(self: *const @This(), comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
        return self.g.visit_edges(self.node, T, ctx, f);
    }

    pub fn visit_edges_of_type(self: *const @This(), edge_type: Edge.EdgeType, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
        return self.g.visit_edges_of_type(self.node, edge_type, T, ctx, f);
    }
};

pub const BoundEdgeReference = struct {
    edge: EdgeReference,
    g: *GraphView,
};

pub const GraphView = struct {
    base: ?*GraphView,
    allocator: std.mem.Allocator,
    nodes: std.ArrayList(NodeReference),
    edges: std.ArrayList(EdgeReference),

    // caches for fast lookups ---
    // fast Node->Edges lookup
    neighbors: NodeRefMap.T(std.ArrayList(EdgeReference)),
    // fast (Node, LinkType) -> Edge (TODO: consider neighbor in here too)
    neighbor_by_type: NodeRefMap.T(EdgeTypeMap.T(std.ArrayList(EdgeReference))),
    // fast cluster->Nodes lookup
    //clusters: std.ArrayList(std.ArrayList(NodeReference)),
    // fast Node->Cluster lookup
    //node_to_cluster: Map(NodeReference, *std.ArrayList(NodeReference)),
    // ----

    // need graph merging logic
    // need fast graph views (no copy)
    // => operations all through graph, no graph reference in Nodes or Edges

    pub fn init(allocator: std.mem.Allocator) @This() {
        return .{
            .base = null,
            .allocator = allocator,
            .nodes = std.ArrayList(NodeReference).init(allocator),
            .edges = std.ArrayList(EdgeReference).init(allocator),
            .neighbors = NodeRefMap.T(std.ArrayList(EdgeReference)).init(allocator),
            .neighbor_by_type = NodeRefMap.T(EdgeTypeMap.T(std.ArrayList(EdgeReference))).init(allocator),
        };
    }

    pub fn deinit(g: *@This()) void {
        var neighbors_it = g.neighbors.iterator();
        while (neighbors_it.next()) |entry| {
            // delete array list (not contents)
            entry.value_ptr.deinit();
        }
        // delete hash map (not contents)
        g.neighbors.deinit();

        var neighbor_by_type_it = g.neighbor_by_type.iterator();
        while (neighbor_by_type_it.next()) |entry| {
            var type_map = entry.value_ptr;
            var type_it = type_map.iterator();
            while (type_it.next()) |type_entry| {
                // delete arraylist (not contents)
                type_entry.value_ptr.deinit();
            }
            // delete hash map (not contents)
            type_map.deinit();
        }
        // delete hash map (not contents)
        g.neighbor_by_type.deinit();

        for (g.edges.items) |edge| {
            edge._ref_count.dec(g);
            edge._ref_count.check_in_use() catch {
                continue;
            };
            edge.deinit();
        }
        g.edges.deinit();
        for (g.nodes.items) |node| {
            node._ref_count.dec(g);
            node._ref_count.check_in_use() catch {
                continue;
            };
            node.deinit();
        }
        g.nodes.deinit();
    }

    pub fn insert_node(g: *@This(), node: NodeReference) !BoundNodeReference {
        try g.nodes.append(node);
        node._ref_count.inc(g);

        // handle caches
        try g.neighbors.put(node, std.ArrayList(EdgeReference).init(g.allocator));
        try g.neighbor_by_type.put(node, EdgeTypeMap.T(std.ArrayList(EdgeReference)).init(g.allocator));

        return BoundNodeReference{
            .node = node,
            .g = g,
        };
    }

    pub fn bind(g: *@This(), node: NodeReference) BoundNodeReference {
        // TODO maybe checks
        return BoundNodeReference{
            .node = node,
            .g = g,
        };
    }

    pub fn insert_edge(g: *@This(), edge: EdgeReference) !BoundEdgeReference {
        try g.edges.append(edge);
        edge._ref_count.inc(g);

        // handle caches
        const from_neighbors = g.neighbor_by_type.getPtr(edge.source).?;
        if (!from_neighbors.contains(edge.attributes.edge_type)) {
            try from_neighbors.put(edge.attributes.edge_type, std.ArrayList(EdgeReference).init(g.allocator));
        }
        try g.neighbors.getPtr(edge.source).?.append(edge);
        try from_neighbors.getPtr(edge.attributes.edge_type).?.append(edge);

        const to_neighbors = g.neighbor_by_type.getPtr(edge.target).?;
        if (!to_neighbors.contains(edge.attributes.edge_type)) {
            try to_neighbors.put(edge.attributes.edge_type, std.ArrayList(EdgeReference).init(g.allocator));
        }
        try g.neighbors.getPtr(edge.target).?.append(edge);
        try to_neighbors.getPtr(edge.attributes.edge_type).?.append(edge);

        return BoundEdgeReference{
            .edge = edge,
            .g = g,
        };
    }

    pub fn get_edges(g: *@This(), node: NodeReference) ?*const std.ArrayList(EdgeReference) {
        return g.neighbors.getPtr(node);
    }

    pub fn get_edges_of_type(g: *@This(), node: NodeReference, T: Edge.EdgeType) ?*const std.ArrayList(EdgeReference) {
        return g.neighbor_by_type.getPtr(node).?.getPtr(T);
    }

    pub fn visit_edges(g: *@This(), node: NodeReference, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
        const Result = visitor.VisitResult(T);
        const edges = g.get_edges(node);
        if (edges == null) {
            return Result{ .EXHAUSTED = {} };
        }

        for (edges.?.items) |edge| {
            const bound_edge = BoundEdgeReference{ .edge = edge, .g = g };
            const result = f(ctx, bound_edge);
            switch (result) {
                .CONTINUE => {},
                .STOP => return Result{ .STOP = {} },
                .ERROR => |err| return Result{ .ERROR = err },
                .OK => |value| return Result{ .OK = value },
                .EXHAUSTED => unreachable,
            }
        }

        return Result{ .EXHAUSTED = {} };
    }

    pub fn visit_edges_of_type(g: *@This(), node: NodeReference, edge_type: Edge.EdgeType, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
        const Result = visitor.VisitResult(T);
        const edges = g.get_edges_of_type(node, edge_type);
        if (edges == null) {
            return Result{ .EXHAUSTED = {} };
        }

        for (edges.?.items) |edge| {
            const bound_edge = BoundEdgeReference{ .edge = edge, .g = g };
            const result = f(ctx, bound_edge);
            switch (result) {
                .CONTINUE => {},
                .STOP => return Result{ .STOP = {} },
                .ERROR => |err| return Result{ .ERROR = err },
                .OK => |value| return Result{ .OK = value },
                .EXHAUSTED => unreachable,
            }
        }

        return Result{ .EXHAUSTED = {} };
    }

    // optional: filter for paths of specific edge type
    pub fn visit_paths_bfs(g: *@This(), start_node: BoundNodeReference, edge_type: ?Edge.EdgeType, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, Path) visitor.VisitResult(T)) visitor.VisitResult(T) {

        // Initialize variables required for BFS
        var open_path_queue = std.ArrayList(Path).init(g.allocator);
        var visited_nodes = std.ArrayList(NodeReference).init(g.allocator);

        defer {
            for (open_path_queue.items) |*path| {
                path.deinit();
            }
            open_path_queue.deinit();
        }
        defer visited_nodes.deinit();

        // Initialize edge visitor
        const EdgeVisitor = struct {
            start_node: BoundNodeReference,
            current_path: Path,
            open_path_queue: *std.ArrayList(Path),
            visited_nodes: std.ArrayList(NodeReference),
            g: *GraphView,

            // TODO this can probably be optimized since this iterates through the whole visited_nodes list to find if the node has been visited already
            fn node_visited(self: *@This(), node: NodeReference) bool {
                for (self.visited_nodes.items) |visited| {
                    if (Node.is_same(visited, node)) {
                        return true;
                    }
                }
                return false;
            }

            pub fn visit_fn(self_ptr: *anyopaque, edge: BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                std.debug.print("EDGE VISITOR - Visiting e-{} from n-{}\n", .{ edge.edge.attributes.uuid, self.start_node.node.attributes.uuid });

                // Check if other node has been visited
                const other_node = edge.edge.get_other_node(self.start_node.node);
                const other_node_visited = other_node != null and self.node_visited(other_node.?);

                // If visited, exit edge visitor and continue with BFS
                if (other_node_visited) {
                    std.debug.print("Already visited node {}\n", .{other_node.?.attributes.uuid});
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
                // If not visited, create a new path and append it to the open path queue
                else {
                    var new_path = Path.init(self.g.allocator);

                    // Append current path edges to new path
                    new_path.edges.appendSlice(self.current_path.edges.items) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    };

                    // Append current edge to new path
                    new_path.edges.append(edge.edge) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    };

                    // Append new path to open path queue
                    self.open_path_queue.append(new_path) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    };

                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            }
        };

        // BFS setup

        // Assume provided root node is already visited
        visited_nodes.append(start_node.node) catch |err| {
            return visitor.VisitResult(T){ .ERROR = err };
        };

        // TODO possibly a better way to do this using an edge visitor
        // Get list of edges connected to root node
        var initial_edges: *const std.ArrayList(EdgeReference) = undefined;
        if (edge_type) |et| {
            initial_edges = start_node.get_edges_of_type(et) orelse {
                return visitor.VisitResult(T){ .ERROR = error.NoEdges };
            };
        } else {
            initial_edges = start_node.get_edges() orelse {
                return visitor.VisitResult(T){ .ERROR = error.NoEdges };
            };
        }

        // Add initial edges to open path queue
        for (initial_edges.items) |edge| {
            var path = Path.init(g.allocator);
            path.edges.append(edge) catch |err| {
                return visitor.VisitResult(T){ .ERROR = err };
            };
            open_path_queue.append(path) catch |err| {
                return visitor.VisitResult(T){ .ERROR = err };
            };
        }

        // BFS iterations
        while (open_path_queue.items.len > 0) {
            // Pop path from start of queue
            var path = open_path_queue.pop() orelse unreachable;
            defer path.deinit();
            // path.print_path();

            // Run provided path visitor
            const bfs_visitor_result = f(ctx, path);

            // Mark node at end of path as visited
            const node_at_path_end = path.get_other_node(start_node) orelse {
                return visitor.VisitResult(T){ .ERROR = error.InvalidPath };
            };
            visited_nodes.append(node_at_path_end.node) catch |err| {
                return visitor.VisitResult(T){ .ERROR = err };
            };
            std.debug.print("node_at_end: {}\n", .{node_at_path_end.node.attributes.uuid});

            // Report BFS visitor status
            switch (bfs_visitor_result) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(T){ .STOP = {} },
                .ERROR => |err| return visitor.VisitResult(T){ .ERROR = err },
                .OK => |value| return visitor.VisitResult(T){ .OK = value },
                .EXHAUSTED => return visitor.VisitResult(T){ .EXHAUSTED = {} },
            }

            // Use edge visitor to find more paths and append to open path queue
            var edge_visitor = EdgeVisitor{
                .start_node = node_at_path_end,
                .visited_nodes = visited_nodes,
                .current_path = path,
                .open_path_queue = &open_path_queue,
                .g = g,
            };

            // Check edge visitor for errors
            var edge_visitor_result = visitor.VisitResult(void){ .ERROR = error.InvalidVisitorResult };
            if (edge_type) |et| {
                edge_visitor_result = g.visit_edges_of_type(node_at_path_end.node, et, void, &edge_visitor, EdgeVisitor.visit_fn);
            } else {
                edge_visitor_result = g.visit_edges(node_at_path_end.node, void, &edge_visitor, EdgeVisitor.visit_fn);
            }
            switch (edge_visitor_result) {
                .ERROR => |err| return visitor.VisitResult(T){ .ERROR = err },
                else => {},
            }
        }

        if (open_path_queue.items.len > 0) {
            for (open_path_queue.items) |path| {
                path.print_path();
            }
            return visitor.VisitResult(T){ .ERROR = error.InvalidVisitorResult };
        } else {
            return visitor.VisitResult(T){ .EXHAUSTED = {} };
        }
    }
};

// Pathfinder namespace
pub const PathFinder = struct {

    // High-level find paths function
    pub fn find_paths(start_node: BoundNodeReference, edge_type: ?Edge.EdgeType, a: std.mem.Allocator) ![]const Path {

        // BFS visitor
        const FindPaths = struct {
            path_list: std.ArrayList(Path),

            pub fn visit_fn(self_ptr: *anyopaque, path: Path) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));

                if (!PathFinder.run_filters(path)) {
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }

                self.path_list.append(path) catch |err| {
                    return visitor.VisitResult(void){ .ERROR = err };
                };
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        // Instantiate visitor
        var visit_ctx = FindPaths{ .path_list = std.ArrayList(Path).init(a) };
        defer visit_ctx.path_list.deinit();

        // Run BFS visitor
        const result = GraphView.visit_paths_bfs(start_node.g, start_node, edge_type, void, &visit_ctx, FindPaths.visit_fn);
        _ = result;

        return visit_ctx.path_list.items;
    }

    const Self = @This();

    pub const FilterFn = *const fn (Path) bool;

    pub const Filter = struct {
        name: []const u8,
        func: FilterFn,
    };

    pub const FilterList = struct {
        items: []const Filter,

        pub fn init() FilterList {
            return .{
                .items = &[_]Filter{
                    .{ .name = "filter_path_by_node_type", .func = Self.filter_path_by_node_type },
                    .{ .name = "filter_path_by_edge_type", .func = Self.filter_path_by_edge_type },
                },
            };
        }
    };

    const filters = FilterList.init();

    pub fn run_filters(path: Path) bool {
        path.print_path();
        std.debug.print("FILTERS - ", .{});
        for (filters.items) |filter| {
            std.debug.print("{s}, ", .{filter.name});
            if (!filter.func(path)) {
                return false;
            }
        }
        std.debug.print("\n", .{});
        return true;
    }

    pub fn filter_path_by_node_type(path: Path) bool {
        // path.get_other_node(bn: BoundNodeReference)
        _ = path;
        return true;
    }

    pub fn filter_path_by_edge_type(path: Path) bool {
        _ = path;
        return true;
    }
};

test "visit_paths_bfs" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);
    const n4 = try Node.init(a);
    const n5 = try Node.init(a);
    const n6 = try Node.init(a);
    const e1 = try Edge.init(a, n1, n2, 1759242069);
    const e2 = try Edge.init(a, n1, n3, 1759242069);
    const e3 = try Edge.init(a, n2, n4, 1759242069);
    const e4 = try Edge.init(a, n2, n5, 1759242069);
    const e5 = try Edge.init(a, n5, n6, 1759242069);
    const e6 = try Edge.init(a, n6, n1, 1759242069);
    n1.attributes.uuid = 1001;
    n2.attributes.uuid = 1002;
    n3.attributes.uuid = 1003;
    n4.attributes.uuid = 1004;
    n5.attributes.uuid = 1005;
    n6.attributes.uuid = 1006;
    e1.attributes.uuid = 2001;
    e2.attributes.uuid = 2002;
    e3.attributes.uuid = 2003;
    e4.attributes.uuid = 2004;
    e5.attributes.uuid = 2005;
    e6.attributes.uuid = 2006;
    defer g.deinit();

    const bn1 = try g.insert_node(n1);
    _ = try g.insert_node(n2);
    _ = try g.insert_node(n3);
    _ = try g.insert_node(n4);
    _ = try g.insert_node(n5);
    _ = try g.insert_node(n6);
    _ = try g.insert_edge(e1);
    _ = try g.insert_edge(e2);
    _ = try g.insert_edge(e3);
    _ = try g.insert_edge(e4);
    _ = try g.insert_edge(e5);
    _ = try g.insert_edge(e6);

    const MockPathVisitor = struct {
        // visitor context
        x: i64 = 0,

        // visitor function
        pub fn visit_fn(self_ptr: *anyopaque, path: Path) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(self_ptr));
            _ = path; // doing nothing with the path in this example

            // just counting the number of times the visitor has ran
            self.x += 1;
            std.debug.print("visit_fn iterations: {}\n", .{self.x});
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var visitor_instance = MockPathVisitor{};
    _ = g.visit_paths_bfs(bn1, 1759242069, void, &visitor_instance, MockPathVisitor.visit_fn);

    const paths = try PathFinder.find_paths(bn1, 1759242069, bn1.g.allocator);
    std.debug.print("paths: {}\n", .{paths.len});
    try std.testing.expectEqual(paths.len, 6);

    // paths = try PathFinder.find_paths(bn1, 22, bn1.g.allocator);
    // std.debug.print("paths: {}\n", .{paths.len});
    // try std.testing.expectEqual(paths.len, 0);

    // paths = try PathFinder.find_paths(bn1, null, bn1.g.allocator);
    // std.debug.print("paths: {}\n", .{paths.len});
    // try std.testing.expectEqual(paths.len, 6);

    // be1.get_nodes();
}

test "basic" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    const TestLinkType = 1759269396;
    try Edge.register_type(TestLinkType);

    const n1 = try Node.init(a);
    // defer n1.deinit();
    const n2 = try Node.init(a);
    // defer n2.deinit();
    const e12 = try Edge.init(a, n1, n2, TestLinkType);
    // defer e12.deinit();

    _ = try g.insert_node(n1);
    _ = try g.insert_node(n2);
    _ = try g.insert_edge(e12);

    const edges = g.get_edges(n1).?;
    try std.testing.expectEqual(edges.items.len, 1);
    try std.testing.expectEqual(edges.items[0].attributes.uuid, e12.attributes.uuid);
    try std.testing.expectEqual(edges.items[0].target.attributes.uuid, n2.attributes.uuid);

    try std.testing.expectEqual(n1._ref_count.ref_count, 1);
    try std.testing.expectEqual(n2._ref_count.ref_count, 1);
    try std.testing.expectEqual(e12._ref_count.ref_count, 1);

    g.deinit();
    // has to be deleted first
    // try std.testing.expectEqual(n1._ref_count.ref_count, 0); //these tests are broken now because we automtically deinit when graph view is deinited
    // try std.testing.expectEqual(n2._ref_count.ref_count, 0);
    // try std.testing.expectEqual(e12._ref_count.ref_count, 0);
}
