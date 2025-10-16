const std = @import("std");
pub const str = []const u8;
const visitor = @import("visitor.zig");

const DEBUG = false;

pub const NodeRefMap = struct {
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

    pub fn init(allocator: std.mem.Allocator) @This() {
        return .{
            .values = std.StringHashMap(Literal).init(allocator),
        };
    }

    pub fn deinit(self: *@This()) void {
        self.values.deinit();
    }

    pub fn visit(self: *@This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        var it = self.values.iterator();
        while (it.next()) |e| {
            f(ctx, e.key_ptr.*, e.value_ptr.*, true);
        }
    }

    pub fn copy_into(self: *const @This(), other: *@This()) void {
        var it = self.values.iterator();
        while (it.next()) |e| {
            other.values.put(e.key_ptr.*, e.value_ptr.*) catch unreachable;
        }
    }
};

const GraphObjectReference = union(enum) {
    Node: NodeReference,
    Edge: EdgeReference,
};

pub const GraphReferenceCounter = struct {
    ref_count: usize = 0,
    parent: GraphObjectReference,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator, parent: GraphObjectReference) @This() {
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
        if (self.ref_count == 0) {
            switch (self.parent) {
                .Node => |node| node.deinit(),
                .Edge => |edge| edge.deinit(),
            }
        }
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
    name: ?str, // TODO keeping this for now to keep my pathfinder building but I need to switch to type graph
    fake_type: ?u64, // TODO keeping this for now to keep my pathfinder building but I need to switch to type graph

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
        node.attributes.name = null; // TODO keeping this for now to keep my pathfinder building but I need to switch to type graph
        node.attributes.fake_type = null; // TODO keeping this for now to keep my pathfinder building but I need to switch to type graph

        node._ref_count = GraphReferenceCounter.init(allocator, .{ .Node = node });
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
        edge.attributes.directional = null;
        edge.attributes.name = null;

        edge._ref_count = GraphReferenceCounter.init(allocator, .{ .Edge = edge });
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
    g: *GraphView,

    pub fn init(g: *GraphView) @This() {
        return .{
            .edges = std.ArrayList(EdgeReference).init(g.allocator),
            .g = g,
        };
    }

    pub fn deinit(self: *@This()) void {
        self.edges.deinit();
    }

    pub fn print_path(self: *const @This()) void {
        if (DEBUG) {
            std.debug.print("PATH - len: {} - ", .{self.edges.items.len});
            for (self.edges.items) |edge| {
                std.debug.print("e{}->", .{edge.attributes.uuid});
            }
            std.debug.print("\n", .{});
        }
    }

    pub fn get_other_node(self: *const @This(), bn: BoundNodeReference) ?BoundNodeReference {
        if (self.edges.items.len == 0) {
            return bn;
        }
        const last_edge = self.edges.items[self.edges.items.len - 1];

        // special case - path length 1: need the starting node to disambiguate
        if (self.edges.items.len == 1) {
            return bn.g.bind(last_edge.get_other_node(bn.node) orelse return null);
        }

        // For length >= 2, infer the junction node shared by the last two edges,
        // then return the opposite node on the last edge.
        const second_last_edge = self.edges.items[self.edges.items.len - 2];
        const shared_node = blk: {
            if (Node.is_same(last_edge.source, second_last_edge.source)) break :blk last_edge.source;
            if (Node.is_same(last_edge.source, second_last_edge.target)) break :blk last_edge.source;
            if (Node.is_same(last_edge.target, second_last_edge.source)) break :blk last_edge.target;
            if (Node.is_same(last_edge.target, second_last_edge.target)) break :blk last_edge.target;
            // If no shared node, path is invalid
            return null;
        };

        const end = last_edge.get_other_node(shared_node) orelse return null;
        return bn.g.bind(end);
    }

    pub fn get_last_node(self: *const @This()) ?BoundNodeReference {
        if (self.edges.items.len == 0) {
            return null;
        }
        const last_edge = self.edges.items[self.edges.items.len - 1];

        // For undirected edges, try to infer the end node using the previous edge.
        if (self.edges.items.len >= 2) {
            const second_last_edge = self.edges.items[self.edges.items.len - 2];
            const shared_node = blk: {
                if (Node.is_same(last_edge.source, second_last_edge.source)) break :blk last_edge.source;
                if (Node.is_same(last_edge.source, second_last_edge.target)) break :blk last_edge.source;
                if (Node.is_same(last_edge.target, second_last_edge.source)) break :blk last_edge.target;
                if (Node.is_same(last_edge.target, second_last_edge.target)) break :blk last_edge.target;
                return null; // invalid path: last two edges do not connect
            };
            return self.g.bind(last_edge.get_other_node(shared_node) orelse return null);
        }

        // If the last edge is directional, we can use its target.
        if (last_edge.attributes.directional) |d| {
            if (d) {
                return self.g.bind(last_edge.target);
            }
            return null;
        }

        // Single undirected edge with no context: ambiguous
        return null;
    }

    pub fn get_first_node(self: *const @This()) ?BoundNodeReference {
        if (self.edges.items.len == 0) {
            return null;
        }
        const last_node = self.get_last_node() orelse return null;
        return self.get_other_node(last_node);
    }
};

// Hierarchy traversal direction for composition edges
pub const HeirarchyTraverseDirection = enum {
    up, // Child to parent
    down, // Parent to child
    horizontal, // Same level (interface connections)
};

// Element representing a single hierarchy traversal step
pub const HeirarchyElement = struct {
    parent_type: u64,
    child_type: u64,
    child_name: []const u8,
    traverse_direction: HeirarchyTraverseDirection,

    pub fn match(self: *const @This(), other: *const @This()) bool {
        // Match if same parent/child/name but opposite directions (up vs down)
        const opposite_directions = (self.traverse_direction == .up and other.traverse_direction == .down) or
            (self.traverse_direction == .down and other.traverse_direction == .up);

        return self.parent_type == other.parent_type and
            self.child_type == other.child_type and
            std.mem.eql(u8, self.child_name, other.child_name) and
            opposite_directions;
    }
};

pub const BFSPath = struct {
    path: Path,
    start_node: BoundNodeReference,
    filtered: bool = false, // filter this path out
    stop: bool = false, // Do not keep going down this path (do not add to open_path_queue)

    // Hierarchy analysis data (computed by pathfinder filters)
    hierarchy_elements_raw: ?std.ArrayList(HeirarchyElement) = null, // Raw sequence before folding
    hierarchy_stack_folded: ?std.ArrayList(HeirarchyElement) = null, // After folding matching pairs

    fn is_consistent(self: *const @This()) bool {
        return self.start_node.g == self.path.g;
    }

    fn assert_consistent(self: *const @This()) void {
        std.debug.assert(self.is_consistent());
    }

    pub fn init(start: BoundNodeReference) @This() {
        var path = BFSPath{
            .path = Path.init(start.g),
            .start_node = start,
            .filtered = false,
            .stop = false,
        };
        path.assert_consistent();
        return path;
    }

    pub fn cloneAndExtend(base: *const BFSPath, edge: EdgeReference) !*BFSPath {
        base.assert_consistent();
        const g = base.path.g;
        std.debug.assert(base.start_node.g == g);

        var new_path = try g.allocator.create(BFSPath);
        new_path.* = BFSPath.init(base.start_node);
        errdefer new_path.destroy(g.allocator);

        // Pre-allocate exact capacity needed to avoid reallocation
        const new_len = base.path.edges.items.len + 1;
        try new_path.path.edges.ensureTotalCapacity(new_len);

        // Extend with prior edges before adding the new edge.
        new_path.path.edges.appendSliceAssumeCapacity(base.path.edges.items);
        new_path.path.edges.appendAssumeCapacity(edge);

        return new_path;
    }

    pub fn deinit(self: *@This()) void {
        self.assert_consistent();
        self.path.deinit();

        // Clean up hierarchy analysis data if present
        if (self.hierarchy_elements_raw) |*raw| {
            raw.deinit();
            self.hierarchy_elements_raw = null;
        }
        if (self.hierarchy_stack_folded) |*folded| {
            folded.deinit();
            self.hierarchy_stack_folded = null;
        }
    }

    pub fn destroy(self: *@This(), allocator: std.mem.Allocator) void {
        self.assert_consistent();
        self.deinit();
        allocator.destroy(self);
    }

    pub fn get_last_node(self: *const @This()) ?BoundNodeReference {
        return self.path.get_other_node(self.start_node);
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

    // optional: filter for paths of specific edge type
    // Visitor receives ownership of the path value and must either keep it or deinit it
    pub fn visit_paths_bfs(
        g: *@This(),
        start_node: BoundNodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: fn (*anyopaque, *BFSPath) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        // Initialize variables required for BFS with reasonable initial capacity
        var open_path_queue = std.fifo.LinearFifo(*BFSPath, .Dynamic).init(g.allocator);
        open_path_queue.ensureTotalCapacity(1024) catch {}; // Pre-allocate for 1024 paths in queue
        // Use HashMap for O(1) visited node checks
        var visited_nodes = NodeRefMap.T(void).init(g.allocator);
        visited_nodes.ensureTotalCapacity(1024) catch {}; // Pre-allocate for 1024 visited nodes

        defer {
            while (open_path_queue.readItem()) |bfspath| {
                bfspath.destroy(g.allocator);
            }
            open_path_queue.deinit();
        }
        defer visited_nodes.deinit();

        // Initialize edge visitor
        const EdgeVisitor = struct {
            start_node: BoundNodeReference,
            current_path: *BFSPath,
            open_path_queue: *std.fifo.LinearFifo(*BFSPath, .Dynamic),
            visited_nodes: *NodeRefMap.T(void),
            g: *GraphView,

            // O(1) lookup using HashMap
            fn node_visited(self: *@This(), node: NodeReference) bool {
                return self.visited_nodes.contains(node);
            }

            pub fn visit_fn(self_ptr: *anyopaque, edge: BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                if (DEBUG) std.debug.print("e-{} ", .{edge.edge.attributes.uuid});

                // Check if other node has been visited
                const other_node = edge.edge.get_other_node(self.start_node.node);
                const other_node_visited = other_node != null and self.node_visited(other_node.?);

                // If visited, exit edge visitor and continue with BFS
                if (other_node_visited) {
                    if (DEBUG) std.debug.print("ignored, already visited n-{}\n", .{other_node.?.attributes.uuid});
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
                // If not visited, create a new path and append it to the open path queue
                else {
                    if (DEBUG) std.debug.print("added\n", .{});
                    const new_path = BFSPath.cloneAndExtend(self.current_path, edge.edge) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    };

                    // Enqueue new path
                    self.open_path_queue.writeItem(new_path) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    };

                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            }
        };

        // BFS setup

        // Assume provided root node is already visited
        visited_nodes.put(start_node.node, {}) catch |err| {
            return visitor.VisitResult(T){ .ERROR = err };
        };

        _ = start_node.get_edges() orelse {
            return visitor.VisitResult(T){ .ERROR = error.NoEdges };
        };

        // Create empty base path for extending with edges
        var empty_base = BFSPath.init(start_node);
        defer empty_base.deinit();

        // Always add empty path (node is connected to itself)
        const empty_path_copy = start_node.g.allocator.create(BFSPath) catch |err| {
            return visitor.VisitResult(T){ .ERROR = err };
        };
        empty_path_copy.* = BFSPath{
            .path = Path.init(start_node.g),
            .start_node = start_node,
            .filtered = false,
            .stop = false,
        };
        open_path_queue.writeItem(empty_path_copy) catch |err| {
            return visitor.VisitResult(T){ .ERROR = err };
        };

        // BFS iterations
        while (open_path_queue.readItem()) |path| {
            defer path.destroy(g.allocator);
            const node_at_path_end = path.path.get_other_node(start_node) orelse {
                return visitor.VisitResult(T){ .ERROR = error.InvalidPath };
            };

            if (DEBUG) {
                std.debug.print("PATH - len: {} - ", .{path.path.edges.items.len});
                std.debug.print("n{}->", .{start_node.node.attributes.uuid});
                for (path.path.edges.items) |edge| {
                    std.debug.print("e{}->", .{edge.attributes.uuid});
                }
                std.debug.print("n{}\n", .{node_at_path_end.node.attributes.uuid});
            }

            // Call visitor - visitor can modify the path
            const bfs_visitor_result = f(ctx, path);

            // Mark node at end of path as visited (O(1) with HashMap)
            visited_nodes.put(node_at_path_end.node, {}) catch |err| {
                return visitor.VisitResult(T){ .ERROR = err };
            };

            // Report BFS visitor status
            switch (bfs_visitor_result) {
                .STOP => {
                    return visitor.VisitResult(T){ .STOP = {} };
                },
                .ERROR => |err| {
                    return visitor.VisitResult(T){ .ERROR = err };
                },
                .EXHAUSTED => {
                    return visitor.VisitResult(T){ .EXHAUSTED = {} };
                },
                .CONTINUE => {},
                .OK => {},
            }

            if (!path.stop) {
                // Use edge visitor to extend this path and create new paths for the queue
                if (DEBUG) std.debug.print("EDGE VISITOR - Visiting edges from n-{}\n", .{node_at_path_end.node.attributes.uuid});
                var edge_visitor = EdgeVisitor{
                    .start_node = node_at_path_end,
                    .visited_nodes = &visited_nodes,
                    .current_path = path,
                    .open_path_queue = &open_path_queue,
                    .g = g,
                };

                const edge_visitor_result = g.visit_edges(node_at_path_end.node, void, &edge_visitor, EdgeVisitor.visit_fn);

                switch (edge_visitor_result) {
                    .ERROR => |err| return visitor.VisitResult(T){ .ERROR = err },
                    else => {},
                }
            } else {
                if (DEBUG) std.debug.print("PATH - stopped\n", .{});
            }
        }

        if (DEBUG) std.debug.print("STOP BFS!!! - Exhausted\n", .{});
        return visitor.VisitResult(T){ .EXHAUSTED = {} };
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

test "BFSPath cloneAndExtend preserves start metadata" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const TestEdgeType = 0xFBAF_0001;
    Edge.register_type(TestEdgeType) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);

    const bn1 = try g.insert_node(n1);
    _ = try g.insert_node(n2);
    _ = try g.insert_node(n3);

    const e12 = try Edge.init(a, n1, n2, TestEdgeType);
    const e23 = try Edge.init(a, n2, n3, TestEdgeType);
    _ = try g.insert_edge(e12);
    _ = try g.insert_edge(e23);

    var base = BFSPath.init(bn1);
    defer base.deinit();
    try base.path.edges.append(e12);

    const cloned = try BFSPath.cloneAndExtend(&base, e23);
    defer cloned.destroy(g.allocator);

    try std.testing.expect(cloned.start_node.node == bn1.node);
    try std.testing.expect(cloned.start_node.g == bn1.g);
    try std.testing.expect(cloned.path.g == bn1.g);
    try std.testing.expectEqual(@as(usize, 2), cloned.path.edges.items.len);
    try std.testing.expect(cloned.path.edges.items[0] == e12);
    try std.testing.expect(cloned.path.edges.items[1] == e23);
}

test "BFSPath detects inconsistent graph view" {
    const a = std.testing.allocator;
    var g1 = GraphView.init(a);
    defer g1.deinit();
    var g2 = GraphView.init(a);
    defer g2.deinit();

    const n1 = try Node.init(a);
    const bn1 = try g1.insert_node(n1);

    var path = BFSPath.init(bn1);
    defer {
        path.path.g = path.start_node.g;
        path.deinit();
    }

    try std.testing.expect(path.is_consistent());
    path.path.g = &g2;
    try std.testing.expect(!path.is_consistent());

    // Restoring the original graph view before cleanup prevents the assertion from firing.
    path.path.g = path.start_node.g;
    try std.testing.expect(path.is_consistent());
}
