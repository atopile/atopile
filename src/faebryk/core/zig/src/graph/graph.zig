const std = @import("std");
pub const str = []const u8;
const visitor = @import("visitor.zig");

const NodeRefMap = struct {
    pub fn eql(_: @This(), a: NodeReference, b: NodeReference) bool {
        return Node.is_same(a, b);
    }

    pub fn hash(_: @This(), adapted_key: NodeReference) u64 {
        return adapted_key.uuid;
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

const StrMap = struct {
    pub fn eql(_: @This(), a: str, b: str) bool {
        return std.mem.eql(u8, a, b);
    }

    pub fn hash(_: @This(), adapted_key: str) u64 {
        return std.hash_map.hashString(adapted_key);
    }

    pub fn T(V: type) type {
        return std.HashMap(str, V, StrMap, std.hash_map.default_max_load_percentage);
    }
};

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
    values: StrMap.T(Literal),

    fn init(allocator: std.mem.Allocator) @This() {
        return .{
            .values = StrMap.T(Literal).init(allocator),
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
    var prng = std.Random.DefaultPrng.init(0);

    pub fn gen_uuid() UUID.T {
        return prng.random().int(UUID.T);
    }

    pub fn equals(U1: UUID.T, U2: UUID.T) bool {
        return U1 == U2;
    }
};

pub const Node = struct {
    uuid: UUID.T,
    dynamic: DynamicAttributes,
    _ref_count: GraphReferenceCounter,

    pub fn init(allocator: std.mem.Allocator) !NodeReference {
        const node = try allocator.create(Node);
        node.uuid = UUID.gen_uuid();
        node.dynamic = DynamicAttributes.init(allocator);
        node._ref_count = .{
            .parent = node,
            .allocator = allocator,
        };
        return node;
    }

    pub fn deinit(self: *@This()) !void {
        if (self._ref_count.ref_count > 0) {
            return error.InUse;
        }
        self.dynamic.deinit();
        self._ref_count.allocator.destroy(self);
    }

    pub fn is_same(N1: NodeReference, N2: NodeReference) bool {
        return UUID.equals(N1.uuid, N2.uuid);
    }

    pub fn visit_attributes(self: *@This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        f(ctx, "type", Literal{ .Int = @intFromEnum(self.node_type) }, false);
        f(ctx, "uuid", Literal{ .Int = self.uuid }, false);
        self.dynamic.visit(ctx, f);
    }
};

pub const NodeReference = *Node;
pub const EdgeReference = *Edge;

pub const Edge = struct {
    source: NodeReference,
    target: NodeReference,

    uuid: UUID.T,
    edge_type: Type,
    directional: ?bool,
    name: ?str,
    dynamic: DynamicAttributes,
    _ref_count: GraphReferenceCounter,

    pub fn init(allocator: std.mem.Allocator, source: NodeReference, target: NodeReference, T: Type) !*@This() {
        var edge = try allocator.create(Edge);
        edge.source = source;
        edge.target = target;
        edge.uuid = UUID.gen_uuid();
        edge.edge_type = T;
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

    pub const Type = i64;
    pub var type_counter: Type = 0;

    // pretty janky and not deterministic, for testing ok
    pub fn register_type() Type {
        const out = type_counter;
        type_counter += 1;
        return out;
    }

    pub fn is_instance(E: EdgeReference, T: Type) bool {
        return E.edge_type == T;
    }

    pub fn is_same(E1: EdgeReference, E2: EdgeReference) bool {
        return UUID.equals(E1.uuid, E2.uuid);
    }
};

pub const BoundNodeReference = struct {
    node: NodeReference,
    g: *GraphView,

    pub fn get_edges(self: *const @This()) ?*const std.ArrayList(EdgeReference) {
        return self.g.get_edges(self.node);
    }

    pub fn get_edges_of_type(self: *const @This(), T: Edge.Type) ?*const std.ArrayList(EdgeReference) {
        return self.g.get_edges_of_type(self.node, T);
    }

    pub fn visit_edges(self: *const @This(), comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
        return self.g.visit_edges(self.node, T, ctx, f);
    }

    pub fn visit_edges_of_type(self: *const @This(), edge_type: Edge.Type, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
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
        if (!from_neighbors.contains(edge.edge_type)) {
            try from_neighbors.put(edge.edge_type, std.ArrayList(EdgeReference).init(g.allocator));
        }
        try g.neighbors.getPtr(edge.source).?.append(edge);
        try from_neighbors.getPtr(edge.edge_type).?.append(edge);

        const to_neighbors = g.neighbor_by_type.getPtr(edge.target).?;
        if (!to_neighbors.contains(edge.edge_type)) {
            try to_neighbors.put(edge.edge_type, std.ArrayList(EdgeReference).init(g.allocator));
        }
        try g.neighbors.getPtr(edge.target).?.append(edge);
        try to_neighbors.getPtr(edge.edge_type).?.append(edge);

        return BoundEdgeReference{
            .edge = edge,
            .g = g,
        };
    }

    pub fn get_edges(g: *@This(), node: NodeReference) ?*const std.ArrayList(EdgeReference) {
        return g.neighbors.getPtr(node);
    }

    pub fn get_edges_of_type(g: *@This(), node: NodeReference, T: Edge.Type) ?*const std.ArrayList(EdgeReference) {
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

    pub fn visit_edges_of_type(g: *@This(), node: NodeReference, edge_type: Edge.Type, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
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
    const TestLink = Edge.register_type();

    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const e12 = try Edge.init(a, n1, n2, TestLink);

    _ = try g.insert_node(n1);
    _ = try g.insert_node(n2);
    _ = try g.insert_edge(e12);

    const edges = g.get_edges(n1).?;
    try std.testing.expectEqual(edges.items.len, 1);
    try std.testing.expectEqual(edges.items[0].uuid, e12.uuid);
    try std.testing.expectEqual(edges.items[0].target.uuid, n2.uuid);

    try std.testing.expectEqual(n1._ref_count.ref_count, 1);
    try std.testing.expectEqual(n2._ref_count.ref_count, 1);
    try std.testing.expectEqual(e12._ref_count.ref_count, 1);

    // has to be deleted first
    g.deinit();
    try std.testing.expectEqual(n1._ref_count.ref_count, 0);
    try std.testing.expectEqual(n2._ref_count.ref_count, 0);
    try std.testing.expectEqual(e12._ref_count.ref_count, 0);

    try n1.deinit();
    try n2.deinit();
    try e12.deinit();
}
