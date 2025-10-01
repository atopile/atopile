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

    /// No guarantee that there is only one
    pub fn get_single_edge(bound_node: BoundNodeReference, edge_type: EdgeType, is_target: ?bool) ?BoundEdgeReference {
        const Visit = struct {
            bound_node: BoundNodeReference,
            is_target: ?bool,

            pub fn visit(ctx: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(BoundEdgeReference) {
                const self: *@This() = @ptrCast(@alignCast(ctx));
                if (self.is_target) |d| {
                    const target = bound_edge.edge.get_target();
                    if (target) |t| {
                        if (d and Node.is_same(t, self.bound_node.node)) {
                            return visitor.VisitResult(BoundEdgeReference){ .OK = bound_edge };
                        }
                    }
                    return visitor.VisitResult(BoundEdgeReference){ .CONTINUE = {} };
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
        }
        g.edges.deinit();
        for (g.nodes.items) |node| {
            node._ref_count.dec(g);
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
};

test "basic" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    const TestLinkType = 1759269396;
    try Edge.register_type(TestLinkType);

    const n1 = try Node.init(a);
    defer n1.deinit();
    const n2 = try Node.init(a);
    defer n2.deinit();
    const e12 = try Edge.init(a, n1, n2, TestLinkType);
    defer e12.deinit();

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

    // has to be deleted first
    g.deinit();
    try std.testing.expectEqual(n1._ref_count.ref_count, 0);
    try std.testing.expectEqual(n2._ref_count.ref_count, 0);
    try std.testing.expectEqual(e12._ref_count.ref_count, 0);
}
