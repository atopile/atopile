const std = @import("std");
pub const str = []const u8;
const visitor = @import("visitor.zig");

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
        return adapted_key.attributes.uuid;
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
    pub fn visit(self: *@This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        f(ctx, "uuid", Literal{ .Uint = self.uuid }, false);
        self.dynamic.visit(ctx, f);
    }

    pub fn put(self: *@This(), identifier: str, value: Literal) void {
        self.dynamic.values.put(identifier, value) catch @panic("OOM dynamic attributes put");
    }
};

pub const Node = struct {
    attributes: NodeAttributes,
    _ref_count: GraphReferenceCounter,

    pub fn init(allocator: std.mem.Allocator) NodeReference {
        const node = allocator.create(Node) catch @panic("Failed to allocate Node");

        // Attributes
        node.attributes.uuid = UUID.gen_uuid(node);
        node.attributes.dynamic = DynamicAttributes.init(allocator);
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

    pub fn get_uuid(self: *@This()) UUID.T {
        return self.attributes.uuid;
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

    // TODO make set_name function that duplicates and owns the string and deallocates it on deinit
    // ^ same for NodeAttributes
    // Then ownership in python api layer also easier
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

    pub fn init(allocator: std.mem.Allocator, source: NodeReference, target: NodeReference, edge_type: EdgeType) *@This() {
        var edge = allocator.create(Edge) catch @panic("OOM creating Edge");
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
        type_set.put(edge_type, {}) catch @panic("OOM registering edge type");
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

    pub fn get_other_node(self: *const @This(), N: NodeReference) NodeReference {
        if (Node.is_same(self.source, N)) {
            return self.target;
        } else if (Node.is_same(self.target, N)) {
            return self.source;
        } else {
            @panic("Edge is not connected to the given node");
        }
    }

    /// No guarantee that there is only one
    pub fn get_single_edge(bound_node: BoundNodeReference, edge_type: EdgeType, is_target: ?bool) ?BoundEdgeReference {
        const Visit = struct {
            pub fn visit(ctx: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(BoundEdgeReference) {
                _ = ctx;
                return visitor.VisitResult(BoundEdgeReference){ .OK = bound_edge };
            }
        };

        var visit = Visit{};
        // Convert is_target to directed parameter:
        // is_target = true -> directed = false (node is target)
        // is_target = false -> directed = true (node is source)
        // is_target = null -> directed = null (any direction)
        const directed: ?bool = if (is_target) |d| !d else null;
        const result = bound_node.visit_edges_of_type(edge_type, BoundEdgeReference, &visit, Visit.visit, directed);
        switch (result) {
            .OK => return result.OK,
            .EXHAUSTED => return null,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => |err| @panic(@errorName(err)),
        }
    }
};

pub const TraversedEdge = struct {
    edge: EdgeReference,
    forward: bool, // true if traversing source→target, false if target→source
    // basically tracking if we traversed an edge in the same direction as the edge defined source/target

    pub fn get_start_node(self: *const @This()) NodeReference {
        return if (self.forward) self.edge.source else self.edge.target;
    }

    pub fn get_end_node(self: *const @This()) NodeReference {
        return if (self.forward) self.edge.target else self.edge.source;
    }
};

pub const BFSPath = struct {
    traversed_edges: std.ArrayList(TraversedEdge),
    g: *GraphView,
    start_node: BoundNodeReference,
    invalid_path: bool = false, // invalid path (e.g., hierarchy violation, shallow link violation, etc.)
    stop_new_path_discovery: bool = false,
    visit_strength: VisitStrength = .unvisited,

    fn is_consistent(self: *const @This()) bool {
        return self.start_node.g == self.g;
    }

    fn assert_consistent(self: *const @This()) void {
        std.debug.assert(self.is_consistent());
    }

    pub fn init(start: BoundNodeReference) !*@This() {
        var path = try start.g.allocator.create(BFSPath);
        path.* = BFSPath{
            .traversed_edges = std.ArrayList(TraversedEdge).init(start.g.allocator),
            .g = start.g,
            .start_node = start,
            .invalid_path = false,
            .stop_new_path_discovery = false,
        };
        path.assert_consistent();
        return path;
    }

    pub fn cloneAndExtend(base: *const BFSPath, from_node: BoundNodeReference, edge: EdgeReference) !*BFSPath {
        base.assert_consistent();
        const g = base.g;
        std.debug.assert(base.start_node.g == g);

        var new_path = try BFSPath.init(base.start_node);

        // Pre-allocate exact capacity needed to avoid reallocation
        const new_len = base.traversed_edges.items.len + 1;
        try new_path.traversed_edges.ensureTotalCapacity(new_len);

        // Copy prior edges
        for (base.traversed_edges.items) |item| {
            new_path.traversed_edges.appendAssumeCapacity(item);
        }

        // Add new edge with traversal direction
        const forward = Node.is_same(edge.source, from_node.node);
        new_path.traversed_edges.appendAssumeCapacity(TraversedEdge{
            .edge = edge,
            .forward = forward,
        });

        new_path.visit_strength = base.visit_strength;

        return new_path;
    }

    pub fn deinit(self: *@This()) void {
        self.assert_consistent();
        self.traversed_edges.deinit();
        self.g.allocator.destroy(self);
    }

    /// Returns the final destination of the path
    pub fn get_last_node(self: *const @This()) BoundNodeReference {
        if (self.traversed_edges.items.len == 0) {
            return self.start_node;
        }
        const traversed_edge = self.traversed_edges.items[self.traversed_edges.items.len - 1];
        const last_node = traversed_edge.get_end_node();
        return self.g.bind(last_node);
    }

    pub fn contains(self: *const @This(), node: NodeReference) bool {
        for (self.traversed_edges.items) |traversed_edge| {
            if (Node.is_same(traversed_edge.edge.source, node) or Node.is_same(traversed_edge.edge.target, node)) {
                return true;
            }
        }
        return false;
    }

    pub fn format(
        self: @This(),
        comptime fmt: []const u8,
        options: std.fmt.FormatOptions,
        writer: anytype,
    ) !void {
        _ = fmt; // Unused
        _ = options; // Unused
        try writer.print("PATH - len: {} - ", .{self.traversed_edges.items.len});
        for (self.traversed_edges.items) |traversed_edge| {
            try writer.print("e{}->", .{traversed_edge.edge.attributes.uuid});
        }
        try writer.print("\n", .{});
    }
};

pub const BFSPaths = struct {
    paths: std.ArrayList(*BFSPath),
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) @This() {
        return .{ .paths = std.ArrayList(*BFSPath).init(allocator), .allocator = allocator };
    }

    pub fn deinit(self: *@This()) void {
        for (self.paths.items) |path| {
            path.deinit();
        }
        self.paths.deinit();
    }

    pub fn destroy(self: *@This()) void {
        const allocator = self.allocator;
        self.deinit();
        allocator.destroy(self);
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

    pub fn visit_edges_of_type(self: *const @This(), edge_type: Edge.EdgeType, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T), directed: ?bool) visitor.VisitResult(T) {
        return self.g.visit_edges_of_type(self.node, edge_type, T, ctx, f, directed);
    }
};

pub const BoundEdgeReference = struct {
    edge: EdgeReference,
    g: *GraphView,
};

pub const VisitStrength = enum { unvisited, strong };

pub const VisitInfo = struct {
    visit_strength: VisitStrength,
};

pub const GraphView = struct {
    base: ?*GraphView,
    allocator: std.mem.Allocator,
    nodes: std.ArrayList(NodeReference),
    edges: EdgeRefMap.T(void),
    self_node: NodeReference,

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
        var out = GraphView{
            .base = null,
            .allocator = allocator,
            .nodes = std.ArrayList(NodeReference).init(allocator),
            .edges = EdgeRefMap.T(void).init(allocator),
            .neighbors = NodeRefMap.T(std.ArrayList(EdgeReference)).init(allocator),
            .neighbor_by_type = NodeRefMap.T(EdgeTypeMap.T(std.ArrayList(EdgeReference))).init(allocator),
            .self_node = Node.init(allocator),
        };
        _ = out.insert_node(out.self_node);
        return out;
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

        var edge_it = g.edges.keyIterator();
        while (edge_it.next()) |edge| {
            edge.*._ref_count.dec(g);
        }
        g.edges.deinit();
        for (g.nodes.items) |node| {
            node._ref_count.dec(g);
        }
        g.nodes.deinit();
    }

    pub fn insert_node(g: *@This(), node: NodeReference) BoundNodeReference {
        if (g.contains_node(node)) {
            return g.bind(node);
        }

        g.nodes.append(node) catch {
            @panic("Failed to append node");
        };
        node._ref_count.inc(g);

        // handle caches
        g.neighbors.put(node, std.ArrayList(EdgeReference).init(g.allocator)) catch {
            @panic("Failed to allocate ArrayList");
        };
        g.neighbor_by_type.put(node, EdgeTypeMap.T(std.ArrayList(EdgeReference)).init(g.allocator)) catch {
            @panic("Failed to allocate EdgeTypeMap");
        };

        return g.bind(node);
    }

    pub fn contains_node(g: *@This(), node: NodeReference) bool {
        return g.neighbors.contains(node);
    }

    pub fn create_and_insert_node(g: *@This()) BoundNodeReference {
        return g.insert_node(Node.init(g.allocator));
    }

    pub fn bind(g: *@This(), node: NodeReference) BoundNodeReference {
        // TODO maybe checks
        return BoundNodeReference{
            .node = node,
            .g = g,
        };
    }

    pub fn get_node_count(g: *const @This()) usize {
        return g.nodes.items.len;
    }

    pub fn get_nodes(g: *const @This()) []const NodeReference {
        return g.nodes.items;
    }

    pub fn insert_edge(g: *@This(), edge: EdgeReference) BoundEdgeReference {
        if (g.edges.contains(edge)) {
            return BoundEdgeReference{
                .edge = edge,
                .g = g,
            };
        }

        if (!g.contains_node(edge.source) or !g.contains_node(edge.target)) {
            // TODO consider making this an error instead of panic
            @panic("Edge source or target not found");
        }

        g.edges.put(edge, {}) catch @panic("OOM inserting edge");
        edge._ref_count.inc(g);

        // handle caches
        const from_neighbors = g.neighbor_by_type.getPtr(edge.source).?;
        if (!from_neighbors.contains(edge.attributes.edge_type)) {
            from_neighbors.put(edge.attributes.edge_type, std.ArrayList(EdgeReference).init(g.allocator)) catch @panic("OOM inserting neighbor type");
        }
        g.neighbors.getPtr(edge.source).?.append(edge) catch @panic("OOM appending neighbor edge");
        from_neighbors.getPtr(edge.attributes.edge_type).?.append(edge) catch @panic("OOM appending neighbor type edge");

        const to_neighbors = g.neighbor_by_type.getPtr(edge.target).?;
        if (!to_neighbors.contains(edge.attributes.edge_type)) {
            to_neighbors.put(edge.attributes.edge_type, std.ArrayList(EdgeReference).init(g.allocator)) catch @panic("OOM inserting reverse neighbor type");
        }
        g.neighbors.getPtr(edge.target).?.append(edge) catch @panic("OOM appending reverse neighbor edge");
        to_neighbors.getPtr(edge.attributes.edge_type).?.append(edge) catch @panic("OOM appending reverse neighbor type edge");

        return BoundEdgeReference{
            .edge = edge,
            .g = g,
        };
    }

    pub fn get_edges(g: *@This(), node: NodeReference) ?*const std.ArrayList(EdgeReference) {
        return g.neighbors.getPtr(node);
    }

    pub fn get_edges_of_type(g: *@This(), node: NodeReference, T: Edge.EdgeType) ?*const std.ArrayList(EdgeReference) {
        const by_type = g.neighbor_by_type.getPtr(node) orelse return null;
        return by_type.getPtr(T);
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

    pub fn visit_edges_of_type(g: *@This(), node: NodeReference, edge_type: Edge.EdgeType, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T), directed: ?bool) visitor.VisitResult(T) {
        const Result = visitor.VisitResult(T);
        const edges = g.get_edges_of_type(node, edge_type);
        if (edges == null) {
            return Result{ .EXHAUSTED = {} };
        }

        for (edges.?.items) |edge| {
            // Filter by direction if specified
            if (directed) |d| {
                if (d) {
                    // directed = true: node must be source
                    if (!Node.is_same(edge.source, node)) {
                        continue;
                    }
                } else {
                    // directed = false: node must be target
                    if (!Node.is_same(edge.target, node)) {
                        continue;
                    }
                }
            }
            // directed = null: ignore direction (process all edges)

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

    pub fn get_subgraph_from_nodes(g: *@This(), nodes: std.ArrayList(NodeReference)) GraphView {
        // create new graph view
        // that contains only the nodes in the list and the edges between them
        var new_g = GraphView.init(g.allocator);
        const EdgeVisitor = struct {
            new_g: *GraphView,
            nodes: std.HashMap(NodeReference, void, NodeRefMap, std.hash_map.default_max_load_percentage),

            fn visit_fn(self_ptr: *anyopaque, edge: BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                if (!self.nodes.contains(edge.edge.source) or !self.nodes.contains(edge.edge.target)) {
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
                _ = self.new_g.insert_edge(edge.edge);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };
        var edge_visitor = EdgeVisitor{
            .new_g = &new_g,
            .nodes = std.HashMap(NodeReference, void, NodeRefMap, std.hash_map.default_max_load_percentage).init(g.allocator),
        };
        defer edge_visitor.nodes.deinit();
        for (nodes.items) |node| {
            _ = new_g.insert_node(node);
            edge_visitor.nodes.put(node, {}) catch @panic("OOM");
        }
        for (nodes.items) |node| {
            _ = g.visit_edges(node, void, &edge_visitor, EdgeVisitor.visit_fn);
        }
        return new_g;
    }

    pub fn insert_subgraph(g: *@This(), subgraph: GraphView) void {
        // Pre-allocate for nodes
        const added_nodes_len = subgraph.nodes.items.len;
        g.nodes.ensureUnusedCapacity(added_nodes_len) catch @panic("OOM");
        g.neighbors.ensureUnusedCapacity(@intCast(added_nodes_len)) catch @panic("OOM");
        g.neighbor_by_type.ensureUnusedCapacity(@intCast(added_nodes_len)) catch @panic("OOM");

        for (subgraph.nodes.items) |node| {
            if (g.contains_node(node)) {
                continue;
            }

            // Inline insert_node logic with assumption of capacity
            g.nodes.appendAssumeCapacity(node);
            node._ref_count.inc(g);

            g.neighbors.putAssumeCapacity(node, std.ArrayList(EdgeReference).init(g.allocator));
            g.neighbor_by_type.putAssumeCapacity(node, EdgeTypeMap.T(std.ArrayList(EdgeReference)).init(g.allocator));
        }

        // Pre-allocate for edges
        const added_edges_len = subgraph.edges.count();
        g.edges.ensureUnusedCapacity(@intCast(added_edges_len)) catch @panic("OOM");

        var it = subgraph.edges.keyIterator();
        while (it.next()) |edge_ptr| {
            const edge = edge_ptr.*;
            if (g.edges.contains(edge)) {
                continue;
            }

            // Inline insert_edge logic
            g.edges.putAssumeCapacity(edge, {});
            edge._ref_count.inc(g);

            // handle caches
            // We trust nodes exist now (were inserted above or already existed)
            {
                const from_neighbors = g.neighbor_by_type.getPtr(edge.source).?;
                const res_from = from_neighbors.getOrPut(edge.attributes.edge_type) catch @panic("OOM");
                if (!res_from.found_existing) {
                    res_from.value_ptr.* = std.ArrayList(EdgeReference).init(g.allocator);
                }
                res_from.value_ptr.append(edge) catch @panic("OOM");
                g.neighbors.getPtr(edge.source).?.append(edge) catch @panic("OOM");
            }

            {
                const to_neighbors = g.neighbor_by_type.getPtr(edge.target).?;
                const res_to = to_neighbors.getOrPut(edge.attributes.edge_type) catch @panic("OOM");
                if (!res_to.found_existing) {
                    res_to.value_ptr.* = std.ArrayList(EdgeReference).init(g.allocator);
                }
                res_to.value_ptr.append(edge) catch @panic("OOM");
                g.neighbors.getPtr(edge.target).?.append(edge) catch @panic("OOM");
            }
        }
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
        var open_path_queue = std.fifo.LinearFifo(*BFSPath, .Dynamic).init(g.allocator);
        open_path_queue.ensureTotalCapacity(1024) catch @panic("OOM");
        var visited_nodes = NodeRefMap.T(VisitInfo).init(g.allocator);
        visited_nodes.ensureTotalCapacity(1024) catch @panic("OOM");

        defer {
            while (open_path_queue.readItem()) |bfspath| {
                bfspath.deinit();
            }
            open_path_queue.deinit();
        }
        defer visited_nodes.deinit();

        const EdgeVisitor = struct {
            start_node: BoundNodeReference,
            current_path: *BFSPath,
            open_path_queue: *std.fifo.LinearFifo(*BFSPath, .Dynamic),
            visited_nodes: *NodeRefMap.T(VisitInfo),
            g: *GraphView,

            fn valid_node_to_add_to_path(self: *@This(), node: NodeReference) bool {
                // if node is contained in current path, we should not add to the path
                if (self.current_path.contains(node)) {
                    return false;
                }

                var node_strength: VisitStrength = .unvisited;
                if (self.visited_nodes.get(node)) |visit_info| {
                    node_strength = visit_info.visit_strength;
                }

                if (node_strength == .strong) {
                    return false;
                }

                return true;
            }

            pub fn visit_fn(self_ptr: *anyopaque, edge: BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const other_node = edge.edge.get_other_node(self.start_node.node);

                if (self.valid_node_to_add_to_path(other_node)) {
                    const new_path = BFSPath.cloneAndExtend(self.current_path, self.start_node, edge.edge) catch @panic("OOM");
                    self.open_path_queue.writeItem(new_path) catch @panic("OOM");
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        // BFS setup
        visited_nodes.put(start_node.node, VisitInfo{ .visit_strength = .strong }) catch @panic("OOM");
        const empty_path_copy = BFSPath.init(start_node) catch @panic("OOM");
        open_path_queue.writeItem(empty_path_copy) catch @panic("OOM");

        // BFS iterations
        while (open_path_queue.readItem()) |path| {
            defer path.deinit();

            const bfs_visitor_result = f(ctx, path);

            // mark node with visited strength from BFS visitor
            visited_nodes.put(path.get_last_node().node, VisitInfo{ .visit_strength = path.visit_strength }) catch @panic("OOM");

            switch (bfs_visitor_result) {
                .STOP => return bfs_visitor_result,
                .ERROR => return bfs_visitor_result,
                .EXHAUSTED => return bfs_visitor_result,
                .CONTINUE => {},
                .OK => {},
            }

            if (path.stop_new_path_discovery) {
                continue;
            }

            var edge_visitor = EdgeVisitor{
                .start_node = path.get_last_node(),
                .visited_nodes = &visited_nodes,
                .current_path = path,
                .open_path_queue = &open_path_queue,
                .g = g,
            };

            const edge_visitor_result = g.visit_edges(path.get_last_node().node, void, &edge_visitor, EdgeVisitor.visit_fn);
            if (edge_visitor_result == .ERROR) return edge_visitor_result;
        }

        return visitor.VisitResult(T){ .EXHAUSTED = {} };
    }
};

test "basic" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();
    const TestLinkType = 1759269396;
    try Edge.register_type(TestLinkType);

    const n1 = Node.init(a);
    const n2 = Node.init(a);
    const e12 = Edge.init(a, n1, n2, TestLinkType);
    // no deinit defer required, since graph will deinit all nodes and edges if they reach 0

    _ = g.insert_node(n1);
    _ = g.insert_node(n2);
    _ = g.insert_edge(e12);

    const edges = g.get_edges(n1).?;
    try std.testing.expectEqual(edges.items.len, 1);
    try std.testing.expectEqual(edges.items[0].attributes.uuid, e12.attributes.uuid);
    try std.testing.expectEqual(edges.items[0].target.attributes.uuid, n2.attributes.uuid);

    try std.testing.expectEqual(n1._ref_count.ref_count, 1);
    try std.testing.expectEqual(n2._ref_count.ref_count, 1);
    try std.testing.expectEqual(e12._ref_count.ref_count, 1);
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

    const n1 = Node.init(a);
    const n2 = Node.init(a);
    const n3 = Node.init(a);

    const bn1 = g.insert_node(n1);
    _ = g.insert_node(n2);
    _ = g.insert_node(n3);

    const e12 = Edge.init(a, n1, n2, TestEdgeType);
    const e23 = Edge.init(a, n2, n3, TestEdgeType);
    _ = g.insert_edge(e12);
    _ = g.insert_edge(e23);

    var base = try BFSPath.init(bn1);
    defer base.deinit();
    try base.traversed_edges.append(TraversedEdge{
        .edge = e12,
        .forward = true, // n1 -> n2 is forward (source to target)
    });

    const bn2_bound = g.bind(n2);
    const cloned = try BFSPath.cloneAndExtend(base, bn2_bound, e23);
    defer cloned.deinit();

    try std.testing.expect(cloned.start_node.node == bn1.node);
    try std.testing.expect(cloned.start_node.g == bn1.g);
    try std.testing.expect(cloned.g == bn1.g);
    try std.testing.expectEqual(@as(usize, 2), cloned.traversed_edges.items.len);
    try std.testing.expect(cloned.traversed_edges.items[0].edge == e12);
    try std.testing.expect(cloned.traversed_edges.items[1].edge == e23);
}

test "BFSPath detects inconsistent graph view" {
    const a = std.testing.allocator;
    var g1 = GraphView.init(a);
    defer g1.deinit();
    var g2 = GraphView.init(a);
    defer g2.deinit();

    const n1 = Node.init(a);
    const bn1 = g1.insert_node(n1);

    var path = try BFSPath.init(bn1);
    defer {
        path.g = path.start_node.g;
        path.deinit();
    }

    try std.testing.expect(path.is_consistent());
    path.g = &g2;
    try std.testing.expect(!path.is_consistent());

    // Restoring the original graph view before cleanup prevents the assertion from firing.
    path.g = path.start_node.g;
    try std.testing.expect(path.is_consistent());
}

test "get_subgraph_from_nodes" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const TestEdgeTypeSubgraph = 0xFBAF_0002;
    Edge.register_type(TestEdgeTypeSubgraph) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    const n1 = Node.init(a);
    const n2 = Node.init(a);
    const n3 = Node.init(a);

    _ = g.insert_node(n1);
    _ = g.insert_node(n2);
    _ = g.insert_node(n3);

    const e12 = Edge.init(a, n1, n2, TestEdgeTypeSubgraph);
    const e23 = Edge.init(a, n2, n3, TestEdgeTypeSubgraph);
    const e13 = Edge.init(a, n1, n3, TestEdgeTypeSubgraph);

    _ = g.insert_edge(e12);
    _ = g.insert_edge(e23);
    _ = g.insert_edge(e13);

    var nodes = std.ArrayList(NodeReference).init(a);
    defer nodes.deinit();
    try nodes.append(n1);
    try nodes.append(n2);

    var subgraph = g.get_subgraph_from_nodes(nodes);
    defer subgraph.deinit();

    // 2 nodes + 1 self_node
    try std.testing.expectEqual(@as(usize, 3), subgraph.get_node_count());

    const sub_edges_n1 = subgraph.get_edges(n1).?;
    try std.testing.expectEqual(@as(usize, 1), sub_edges_n1.items.len);
    try std.testing.expectEqual(e12.attributes.uuid, sub_edges_n1.items[0].attributes.uuid);

    const sub_edges_n2 = subgraph.get_edges(n2).?;
    try std.testing.expectEqual(@as(usize, 1), sub_edges_n2.items.len);
    try std.testing.expectEqual(e12.attributes.uuid, sub_edges_n2.items[0].attributes.uuid);
}

test "duplicate edge insertion" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const n1 = Node.init(a);
    const n2 = Node.init(a);
    _ = g.insert_node(n1);
    _ = g.insert_node(n2);

    const TestLinkType = 0xDEADBEEF;
    Edge.register_type(TestLinkType) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    const e1 = Edge.init(a, n1, n2, TestLinkType);

    _ = g.insert_edge(e1);
    try std.testing.expectEqual(@as(usize, 1), g.edges.count());
    try std.testing.expectEqual(@as(usize, 1), e1._ref_count.ref_count);

    _ = g.insert_edge(e1);
    try std.testing.expectEqual(@as(usize, 1), g.edges.count());
    try std.testing.expectEqual(@as(usize, 1), e1._ref_count.ref_count);
}

test "insert_subgraph performance" {
    const a = std.testing.allocator;
    var g1 = GraphView.init(a);
    defer g1.deinit();
    var g2 = GraphView.init(a);
    defer g2.deinit();

    const num_nodes = 10000;

    var i: usize = 0;
    while (i < num_nodes) : (i += 1) {
        const n = Node.init(a);
        _ = g1.insert_node(n);
    }

    i = 0;
    while (i < num_nodes) : (i += 1) {
        const n = Node.init(a);
        _ = g2.insert_node(n);
    }

    var timer = try std.time.Timer.start();
    g1.insert_subgraph(g2);
    const duration = timer.read();

    std.debug.print("\ninsert_subgraph with {d} nodes took {d}ns\n", .{ num_nodes, duration });
}
