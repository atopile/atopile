const std = @import("std");
const visitor = @import("visitor.zig");

pub const str = []const u8;

const base_allocator = std.heap.page_allocator;
var arena_allocator = std.heap.ArenaAllocator.init(base_allocator);
var global_graph_allocator: std.mem.Allocator = arena_allocator.allocator();

// Static storage for edges and attributes (temporary - will be replaced with proper allocator)
var Nodes: [8 * 1024 * 1024]Node = undefined;
var Edges: [8 * 1024 * 1024]Edge = undefined;
var Attrs: [2 * 1024 * 1024]DynamicAttributes = undefined;

// =============================================================================
// Data types
// =============================================================================
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
};

pub const Node = struct {
    var counter: u32 = 0;

    dynamic: DynamicAttributesReference = .{}, // 4b
};

pub const Edge = struct {
    var counter: u32 = 0;

    const Flags = packed struct {
        edge_type: Edge.EdgeType,
        directional: u1 = 0,
        order: u7 = 0,
        edge_specific: u16 = 0,
    };

    source: NodeReference, // 4b
    target: NodeReference, // 4b
    dynamic: DynamicAttributesReference = .{}, // 4b
    flags: Flags, // 4b
    // => 16b total

    // --- Static methods (type-level, not instance) ---
    pub const EdgeType = u8;

    pub fn hash_edge_type(comptime tid: u64) EdgeType {
        return @intCast(tid % 256);
    }

    // Track registrations without heap allocations to stay robust across dylib loads.
    var type_registered: [256]bool = [_]bool{false} ** 256;

    /// Register type and check for duplicates during runtime
    /// Can't do during compile because python will do during runtime
    pub fn register_type(edge_type: EdgeType) !void {
        if (type_registered[edge_type]) {
            return error.DuplicateType;
        }
        type_registered[edge_type] = true;
    }
};

pub const DynamicAttributes = struct {
    var counter: u32 = 0;

    in_use: u3 = 0,
    // try to keep this low enough to fit in a 256b cache line
    // currently attribute is 40b, so max 6
    values: [6]Attribute = undefined,

    /// Create a new empty DynamicAttributes on the stack (for building before copy)
    pub fn init_on_stack() DynamicAttributes {
        return .{ .in_use = 0 };
    }

    /// Put a value into this DynamicAttributes struct (used for building before copy)
    pub fn put(self: *@This(), identifier: str, value: Literal) void {
        if (self.in_use == self.values.len) {
            @panic("Dynamic attributes are full");
        }
        self.values[self.in_use] = .{ .identifier = identifier, .value = value };
        self.in_use += 1;
    }

    /// Copy all attributes from this struct into a reference
    pub fn copy_into(self: *const @This(), dst_ref: DynamicAttributesReference) void {
        if (self.in_use == 0) return;
        if (dst_ref.is_null()) {
            @panic("Cannot copy into null DynamicAttributesReference");
        }
        const dst = &Attrs[dst_ref.uuid];
        for (self.values[0..self.in_use]) |value| {
            if (dst.in_use == dst.values.len) {
                @panic("Dynamic attributes are full");
            }
            dst.values[dst.in_use] = value;
            dst.in_use += 1;
        }
    }
};

// =============================================================================
// UUIDBitSet - Fast O(1) membership testing for UUID-based references
// Uses a simple boolean array indexed by UUID for maximum performance
// =============================================================================
pub const UUIDBitSet = struct {
    // Use a simple slice of bools for direct indexing - faster than DynamicBitSet
    // and avoids iterator issues with pyzig introspection
    data: []bool,
    capacity: u32,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) @This() {
        return .{
            .data = &[_]bool{},
            .capacity = 0,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *@This()) void {
        if (self.capacity > 0) {
            self.allocator.free(self.data);
        }
    }

    /// Ensure capacity for the given uuid
    fn ensureCapacity(self: *@This(), uuid: u32) void {
        if (uuid < self.capacity) return;

        // Grow to next power of 2, minimum 1024
        const new_cap = @max(1024, std.math.ceilPowerOfTwo(u32, uuid + 1) catch uuid + 1);
        const new_data = self.allocator.alloc(bool, new_cap) catch @panic("OOM");
        @memset(new_data, false);

        // Copy old data if any
        if (self.capacity > 0) {
            @memcpy(new_data[0..self.capacity], self.data);
            self.allocator.free(self.data);
        }

        self.data = new_data;
        self.capacity = new_cap;
    }

    /// Add a uuid to the set
    pub fn add(self: *@This(), uuid: u32) void {
        self.ensureCapacity(uuid);
        self.data[uuid] = true;
    }

    /// Remove a uuid from the set
    pub fn remove(self: *@This(), uuid: u32) void {
        if (uuid < self.capacity) {
            self.data[uuid] = false;
        }
    }

    /// Check if uuid is in the set - O(1)
    pub fn contains(self: *const @This(), uuid: u32) bool {
        if (uuid >= self.capacity) return false;
        return self.data[uuid];
    }
};

// =============================================================================
// Reference types (each 4 bytes)
// =============================================================================
pub const NodeReference = struct {
    uuid: u32,

    pub fn init() NodeReference {
        Node.counter += 1;
        return .{
            .uuid = Node.counter,
        };
    }

    pub fn is_same(self: @This(), other: @This()) bool {
        return self.uuid == other.uuid;
    }

    pub fn get_uuid(self: @This()) u32 {
        return self.uuid;
    }

    pub fn put(self: @This(), identifier: str, value: Literal) void {
        _ = Nodes[self.uuid].dynamic.ensure();
        Nodes[self.uuid].dynamic.put(identifier, value);
    }

    pub fn get(self: @This(), identifier: str) ?Literal {
        return Nodes[self.uuid].dynamic.get(identifier);
    }

    /// Copy dynamic attributes from a DynamicAttributes struct into this node's dynamic attributes
    pub fn copy_dynamic_attributes_into(self: @This(), source: *const DynamicAttributes) void {
        if (source.in_use == 0) return;
        _ = Nodes[self.uuid].dynamic.ensure();
        source.copy_into(Nodes[self.uuid].dynamic);
    }

    /// Visit all attributes on this node
    pub fn visit_attributes(self: @This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        Nodes[self.uuid].dynamic.visit(ctx, f);
    }
};

pub const EdgeReference = struct {
    uuid: u32,

    // --- Constructor ---
    pub fn init(source: NodeReference, target: NodeReference, edge_type: Edge.EdgeType) EdgeReference {
        Edge.counter += 1;
        const out: EdgeReference = .{
            .uuid = Edge.counter,
        };
        Edges[out.uuid] = .{
            .source = source,
            .target = target,
            .flags = .{ .edge_type = edge_type, .directional = 0 },
        };
        return out;
    }

    // --- Instance methods ---
    pub fn is_same(self: @This(), other: @This()) bool {
        return self.uuid == other.uuid;
    }

    pub fn get_uuid(self: @This()) u32 {
        return self.uuid;
    }

    // --- Accessors (read from static storage) ---
    pub fn get_source_node(self: @This()) NodeReference {
        return Edges[self.uuid].source;
    }

    pub fn get_target_node(self: @This()) NodeReference {
        return Edges[self.uuid].target;
    }

    pub fn get_attribute_directional(self: @This()) bool {
        return Edges[self.uuid].flags.directional == 1;
    }

    pub fn get_attribute_edge_type(self: @This()) Edge.EdgeType {
        return Edges[self.uuid].flags.edge_type;
    }

    pub fn get(self: @This(), identifier: str) ?Literal {
        return Edges[self.uuid].dynamic.get(identifier);
    }

    // --- Mutators (write to static storage) ---
    pub fn set_attribute_directional(self: @This(), directional: bool) void {
        Edges[self.uuid].flags.directional = if (directional) 1 else 0;
    }

    pub fn put(self: @This(), identifier: str, value: Literal) void {
        _ = Edges[self.uuid].dynamic.ensure();
        Edges[self.uuid].dynamic.put(identifier, value);
    }

    // --- Computed properties ---
    pub fn get_other_node(self: @This(), N: NodeReference) NodeReference {
        const e = &Edges[self.uuid];
        if (e.source.is_same(N)) {
            return e.target;
        } else if (e.target.is_same(N)) {
            return e.source;
        } else {
            @panic("Edge is not connected to the given node");
        }
    }

    pub fn is_instance(self: @This(), edge_type: Edge.EdgeType) bool {
        return self.get_attribute_edge_type() == edge_type;
    }

    /// Returns source if directional, null otherwise
    pub fn get_directed_source(self: @This()) ?NodeReference {
        if (self.get_attribute_directional()) {
            return Edges[self.uuid].source;
        }
        return null;
    }

    /// Returns target if directional, null otherwise
    pub fn get_directed_target(self: @This()) ?NodeReference {
        if (self.get_attribute_directional()) {
            return Edges[self.uuid].target;
        }
        return null;
    }

    pub fn set_attribute_edge_type(self: @This(), edge_type: Edge.EdgeType) void {
        Edges[self.uuid].flags.edge_type = edge_type;
    }

    /// Name is stored in dynamic attributes under "name" key
    pub fn set_attribute_name(self: @This(), name: ?str) void {
        if (name) |n| {
            _ = Edges[self.uuid].dynamic.ensure();
            Edges[self.uuid].dynamic.put("name", .{ .String = n });
        }
    }

    /// Get the name stored in dynamic attributes
    pub fn get_attribute_name(self: @This()) ?str {
        const val = Edges[self.uuid].dynamic.get("name");
        if (val) |v| {
            return v.String;
        }
        return null;
    }

    /// Copy dynamic attributes from a DynamicAttributes struct into this edge's dynamic attributes
    pub fn copy_dynamic_attributes_into(self: @This(), source: *const DynamicAttributes) void {
        if (source.in_use == 0) return;
        _ = Edges[self.uuid].dynamic.ensure();
        source.copy_into(Edges[self.uuid].dynamic);
    }
};

pub const DynamicAttributesReference = struct {
    uuid: u32 = 0,

    /// Create a new initialized DynamicAttributesReference
    pub fn init() DynamicAttributesReference {
        DynamicAttributes.counter += 1;
        Attrs[DynamicAttributes.counter] = .{};
        return .{
            .uuid = DynamicAttributes.counter,
        };
    }

    /// Create a null reference (default state)
    pub fn init_null() DynamicAttributesReference {
        return .{ .uuid = 0 };
    }

    pub fn is_null(self: @This()) bool {
        return self.uuid == 0;
    }

    /// Ensure this reference is initialized, creating storage if null
    /// Returns the (possibly newly initialized) reference
    pub fn ensure(self: *@This()) DynamicAttributesReference {
        if (self.is_null()) {
            self.* = DynamicAttributesReference.init();
        }
        return self.*;
    }

    pub fn visit(self: @This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        if (self.is_null()) return;
        const attrs = &Attrs[self.uuid];
        for (attrs.values[0..attrs.in_use]) |value| {
            f(ctx, value.identifier, value.value, true);
        }
    }

    pub fn put(self: @This(), identifier: str, value: Literal) void {
        if (self.is_null()) {
            @panic("Cannot put on null DynamicAttributesReference - use ensure() first");
        }
        const attrs = &Attrs[self.uuid];
        if (attrs.in_use == attrs.values.len) {
            @panic("Dynamic attributes are full");
        }
        attrs.values[attrs.in_use] = .{ .identifier = identifier, .value = value };
        attrs.in_use += 1;
    }

    pub fn get(self: @This(), identifier: str) ?Literal {
        if (self.is_null()) return null;
        const attrs = &Attrs[self.uuid];
        for (attrs.values[0..attrs.in_use]) |value| {
            // Fast path: pointer + length comparison (works for string literals which share memory)
            // Fall back to byte comparison only if lengths match but pointers differ
            if (value.identifier.len == identifier.len and
                (value.identifier.ptr == identifier.ptr or
                    std.mem.eql(u8, value.identifier, identifier)))
            {
                return value.value;
            }
        }
        return null;
    }

    /// Copy from one reference into another reference
    pub fn copy_into(self: @This(), other: DynamicAttributesReference) void {
        if (self.is_null()) return;
        if (other.is_null()) {
            @panic("Cannot copy into null DynamicAttributesReference");
        }
        const src = &Attrs[self.uuid];
        const dst = &Attrs[other.uuid];
        if (dst.in_use > 0) {
            @panic("Other dynamic attributes are already in use");
        }
        dst.in_use = src.in_use;
        @memcpy(dst.values[0..src.in_use], src.values[0..src.in_use]);
    }
};

// =============================================================================
// Bound References
// =============================================================================
pub const BoundNodeReference = struct {
    node: NodeReference,
    g: *GraphView,

    /// No guarantee that there is only one
    pub fn get_single_edge(self: @This(), edge_type: Edge.EdgeType, is_target: ?bool) ?BoundEdgeReference {
        // is_target = null -> directed = null (any direction)
        // is_target = true -> directed = false (node is target)
        // is_target = false -> directed = true (node is source)

        // optimization for speed, helps compiler a bit
        if (is_target == null) {
            const edges = self.g.nodes.getPtr(self.node) orelse return null;
            const edges_for_type = edges.getPtr(edge_type) orelse return null;
            if (edges_for_type.items.len > 0) {
                return BoundEdgeReference{
                    .edge = edges_for_type.items[0],
                    .g = self.g,
                };
            }
            return null;
        }

        const Visit = struct {
            pub fn visit(ctx: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(BoundEdgeReference) {
                _ = ctx;
                return visitor.VisitResult(BoundEdgeReference){ .OK = bound_edge };
            }
        };

        var visit = Visit{};
        const directed: bool = !is_target.?;
        const result = self.g.visit_edges_of_type(self.node, edge_type, BoundEdgeReference, &visit, Visit.visit, directed);
        switch (result) {
            .OK => return result.OK,
            .EXHAUSTED => return null,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => |err| @panic(@errorName(err)),
        }
    }
};

pub const BoundEdgeReference = struct {
    edge: EdgeReference,
    g: *GraphView,
};

// =============================================================================
// Hash Map Adapters
// =============================================================================
pub const NodeRefMap = struct {
    pub fn eql(_: @This(), a: NodeReference, b: NodeReference) bool {
        return a.is_same(b);
    }

    pub fn hash(_: @This(), adapted_key: NodeReference) u64 {
        return adapted_key.get_uuid();
    }

    pub fn T(V: type) type {
        return std.HashMap(NodeReference, V, NodeRefMap, std.hash_map.default_max_load_percentage);
    }
};

const EdgeRefMap = struct {
    pub fn eql(_: @This(), a: EdgeReference, b: EdgeReference) bool {
        return a.is_same(b);
    }

    pub fn hash(_: @This(), adapted_key: EdgeReference) u64 {
        return adapted_key.get_uuid();
    }

    pub fn T(V: type) type {
        return std.HashMap(EdgeReference, V, EdgeRefMap, std.hash_map.default_max_load_percentage);
    }
};

const EdgeTypeMap = struct {
    pub fn eql(_: @This(), a: Edge.EdgeType, b: Edge.EdgeType) bool {
        return a == b;
    }

    pub fn hash(_: @This(), adapted_key: Edge.EdgeType) u64 {
        var key = adapted_key;
        return std.hash.Wyhash.hash(0, std.mem.asBytes(&key));
    }

    pub fn T(V: type) type {
        return std.HashMap(Edge.EdgeType, V, EdgeTypeMap, std.hash_map.default_max_load_percentage);
    }
};

// =============================================================================
// Path Traversal Types
// =============================================================================
pub const TraversedEdge = struct {
    edge: EdgeReference,
    forward: bool, // true if traversing source->target, false if target->source

    pub fn get_start_node(self: *const @This()) NodeReference {
        return if (self.forward) self.edge.get_source_node() else self.edge.get_target_node();
    }

    pub fn get_end_node(self: *const @This()) NodeReference {
        return if (self.forward) self.edge.get_target_node() else self.edge.get_source_node();
    }
};

pub const BFSPath = struct {
    traversed_edges: std.ArrayList(TraversedEdge),
    g: *GraphView,
    start_node: BoundNodeReference,
    invalid_path: bool = false,
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

        const new_len = base.traversed_edges.items.len + 1;
        try new_path.traversed_edges.ensureTotalCapacity(new_len);

        for (base.traversed_edges.items) |item| {
            new_path.traversed_edges.appendAssumeCapacity(item);
        }

        // Determine traversal direction
        const forward = edge.get_source_node().is_same(from_node.node);
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
            if (traversed_edge.edge.get_source_node().is_same(node) or traversed_edge.edge.get_target_node().is_same(node)) {
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
        _ = fmt;
        _ = options;
        try writer.print("PATH - len: {} - ", .{self.traversed_edges.items.len});
        for (self.traversed_edges.items) |traversed_edge| {
            try writer.print("e{}->", .{traversed_edge.edge.get_uuid()});
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

pub const VisitStrength = enum { unvisited, strong };

pub const VisitInfo = struct {
    visit_strength: VisitStrength,
};

// =============================================================================
// GraphView
// =============================================================================
pub const GraphView = struct {
    base_allocator: std.mem.Allocator,
    arena: *std.heap.ArenaAllocator,
    allocator: std.mem.Allocator,

    // fast (Node, LinkType) -> Edge + Node Storage
    nodes: NodeRefMap.T(EdgeTypeMap.T(std.ArrayList(EdgeReference))),
    // Edge Storage
    edges: EdgeRefMap.T(void),

    // Fast O(1) membership bitsets
    node_set: UUIDBitSet,
    edge_set: UUIDBitSet,

    self_node: NodeReference,

    pub fn init(b_allocator: std.mem.Allocator) @This() {
        const arena_ptr = b_allocator.create(std.heap.ArenaAllocator) catch @panic("OOM allocating arena");
        arena_ptr.* = std.heap.ArenaAllocator.init(b_allocator);
        const allocator = arena_ptr.allocator();
        var out = GraphView{
            .base_allocator = b_allocator,
            .arena = arena_ptr,
            .allocator = allocator,
            .edges = EdgeRefMap.T(void).init(allocator),
            .nodes = NodeRefMap.T(EdgeTypeMap.T(std.ArrayList(EdgeReference))).init(allocator),
            .node_set = UUIDBitSet.init(allocator),
            .edge_set = UUIDBitSet.init(allocator),
            .self_node = NodeReference.init(),
        };
        _ = out.insert_node(out.self_node);
        return out;
    }

    pub fn deinit(g: *@This()) void {
        g.arena.deinit();
        g.base_allocator.destroy(g.arena);
    }

    pub fn get_self_node(g: *@This()) BoundNodeReference {
        return g.bind(g.self_node);
    }

    pub fn insert_node(g: *@This(), node: NodeReference) BoundNodeReference {
        const gop = g.nodes.getOrPut(node) catch @panic("OOM");
        if (!gop.found_existing) {
            gop.value_ptr.* = EdgeTypeMap.T(std.ArrayList(EdgeReference)).init(g.allocator);
            g.node_set.add(node.uuid);
        }
        return g.bind(node);
    }

    /// O(1) node membership check using bitset
    pub fn contains_node(g: *const @This(), node: NodeReference) bool {
        return g.node_set.contains(node.uuid);
    }

    pub fn create_and_insert_node(g: *@This()) BoundNodeReference {
        return g.insert_node(NodeReference.init());
    }

    pub fn bind(g: *@This(), node: NodeReference) BoundNodeReference {
        return BoundNodeReference{
            .node = node,
            .g = g,
        };
    }

    pub fn get_node_count(g: *const @This()) usize {
        return g.nodes.count();
    }

    pub fn get_edge_count(g: *const @This()) usize {
        return g.edges.count();
    }

    pub fn insert_edge(g: *@This(), edge: EdgeReference) BoundEdgeReference {
        // Fast check using bitset first
        if (g.edge_set.contains(edge.uuid)) {
            return BoundEdgeReference{
                .edge = edge,
                .g = g,
            };
        }

        // Add to edge set and hashmap
        g.edge_set.add(edge.uuid);
        g.edges.put(edge, {}) catch @panic("OOM");

        const source = edge.get_source_node();
        const target = edge.get_target_node();

        // Get node neighbors (must exist)
        const from_neighbors = g.nodes.getPtr(source) orelse @panic("Edge source not found");
        const to_neighbors = g.nodes.getPtr(target) orelse @panic("Edge target not found");

        const edge_type = edge.get_attribute_edge_type();

        // Use getOrPut for edge type maps
        const from_gop = from_neighbors.getOrPut(edge_type) catch @panic("OOM");
        if (!from_gop.found_existing) {
            from_gop.value_ptr.* = std.ArrayList(EdgeReference).init(g.allocator);
        }
        from_gop.value_ptr.append(edge) catch @panic("OOM");

        const to_gop = to_neighbors.getOrPut(edge_type) catch @panic("OOM");
        if (!to_gop.found_existing) {
            to_gop.value_ptr.* = std.ArrayList(EdgeReference).init(g.allocator);
        }
        to_gop.value_ptr.append(edge) catch @panic("OOM");

        return BoundEdgeReference{
            .edge = edge,
            .g = g,
        };
    }

    /// O(1) edge membership check using bitset
    pub fn contains_edge(g: *const @This(), edge: EdgeReference) bool {
        return g.edge_set.contains(edge.uuid);
    }

    pub fn get_edges_of_type(g: *@This(), node: NodeReference, T: Edge.EdgeType) ?*const std.ArrayList(EdgeReference) {
        const by_type = g.nodes.getPtr(node) orelse return null;
        return by_type.getPtr(T);
    }

    pub fn visit_edges_of_type(g: *@This(), node: NodeReference, edge_type: Edge.EdgeType, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T), directed: ?bool) visitor.VisitResult(T) {
        const Result = visitor.VisitResult(T);
        const edges = g.get_edges_of_type(node, edge_type);
        if (edges == null) {
            return Result{ .EXHAUSTED = {} };
        }

        for (edges.?.items) |edge| {
            if (directed) |d| {
                if (edge.get_attribute_directional()) {
                    if ((d and !edge.get_source_node().is_same(node)) or (!d and !edge.get_target_node().is_same(node))) {
                        continue;
                    }
                }
            }

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
        var new_g = GraphView.init(g.base_allocator);

        // Pre-allocate capacity for nodes
        const node_count: u32 = @intCast(nodes.items.len);
        new_g.nodes.ensureTotalCapacity(node_count) catch @panic("OOM");

        // Insert nodes (this also populates the node_set bitset)
        for (nodes.items) |node| {
            _ = new_g.insert_node(node);
        }

        // Estimate edge count and pre-allocate
        new_g.edges.ensureTotalCapacity(node_count * 4) catch @panic("OOM");

        // Insert edges where both endpoints are in the subgraph
        // new_g.contains_node is now O(1) using bitset
        for (nodes.items) |node| {
            const edge_map = g.nodes.getPtr(node) orelse continue;
            var edge_by_type_it = edge_map.valueIterator();
            while (edge_by_type_it.next()) |edges_by_type_ptr| {
                for (edges_by_type_ptr.items) |edge| {
                    const other = edge.get_other_node(node);
                    //if (other.get_uuid() < node_uuid) {
                    //    // optimization, for some reason this is slower
                    //    continue;
                    //}
                    if (!new_g.contains_node(other)) {
                        continue;
                    }
                    _ = new_g.insert_edge(edge);
                }
            }
        }
        return new_g;
    }

    pub fn insert_subgraph(g: *@This(), subgraph: *const GraphView) void {
        const added_nodes_len = subgraph.nodes.count();
        g.nodes.ensureUnusedCapacity(@intCast(added_nodes_len)) catch @panic("OOM");

        var node_it = subgraph.nodes.keyIterator();
        while (node_it.next()) |node_ptr| {
            _ = g.insert_node(node_ptr.*);
        }

        const added_edges_len = subgraph.edges.count();
        g.edges.ensureUnusedCapacity(@intCast(added_edges_len)) catch @panic("OOM");

        var edge_it = subgraph.edges.keyIterator();
        while (edge_it.next()) |edge_ptr| {
            _ = g.insert_edge(edge_ptr.*);
        }
    }

    pub fn visit_paths_bfs(
        g: *@This(),
        start_node: BoundNodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: fn (*anyopaque, *BFSPath) visitor.VisitResult(T),
        edge_type_filter: ?[]Edge.EdgeType,
    ) visitor.VisitResult(T) {
        var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
        const allocator = arena.allocator();
        defer arena.deinit();
        var open_path_queue = std.fifo.LinearFifo(*BFSPath, .Dynamic).init(allocator);
        open_path_queue.ensureTotalCapacity(1024) catch @panic("OOM");
        var visited_nodes = NodeRefMap.T(VisitInfo).init(allocator);
        visited_nodes.ensureTotalCapacity(1024) catch @panic("OOM");

        defer {
            while (open_path_queue.readItem()) |bfspath| {
                bfspath.deinit();
            }
            open_path_queue.deinit();
        }
        defer visited_nodes.deinit();

        const EdgeVisitor = struct {
            start_node_ev: BoundNodeReference,
            current_path: *BFSPath,
            open_path_queue: *std.fifo.LinearFifo(*BFSPath, .Dynamic),
            visited_nodes_ev: *NodeRefMap.T(VisitInfo),

            fn valid_node_to_add_to_path(self: *@This(), node: NodeReference) bool {
                if (self.current_path.contains(node)) {
                    return false;
                }

                var node_strength: VisitStrength = .unvisited;
                if (self.visited_nodes_ev.get(node)) |visit_info| {
                    node_strength = visit_info.visit_strength;
                }

                if (node_strength == .strong) {
                    return false;
                }

                return true;
            }

            pub fn visit_fn(self_ptr: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const other_node = bound_edge.edge.get_other_node(self.start_node_ev.node);

                if (self.valid_node_to_add_to_path(other_node)) {
                    const new_path = BFSPath.cloneAndExtend(self.current_path, self.start_node_ev, bound_edge.edge) catch @panic("OOM");
                    self.open_path_queue.writeItem(new_path) catch @panic("OOM");
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        visited_nodes.put(start_node.node, VisitInfo{ .visit_strength = .strong }) catch @panic("OOM");
        const empty_path_copy = BFSPath.init(start_node) catch @panic("OOM");
        open_path_queue.writeItem(empty_path_copy) catch @panic("OOM");

        while (open_path_queue.readItem()) |path| {
            defer path.deinit();

            const bfs_visitor_result = f(ctx, path);

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
                .start_node_ev = path.get_last_node(),
                .visited_nodes_ev = &visited_nodes,
                .current_path = path,
                .open_path_queue = &open_path_queue,
            };

            if (edge_type_filter) |ets| {
                for (ets) |et| {
                    const edge_visitor_result = g.visit_edges_of_type(path.get_last_node().node, et, void, &edge_visitor, EdgeVisitor.visit_fn, null);
                    if (edge_visitor_result == .ERROR) return edge_visitor_result;
                }
            } else {
                const node_edges = g.nodes.getPtr(path.get_last_node().node);
                if (node_edges) |edges_by_type| {
                    var type_it = edges_by_type.keyIterator();
                    while (type_it.next()) |et_ptr| {
                        const edge_visitor_result = g.visit_edges_of_type(path.get_last_node().node, et_ptr.*, void, &edge_visitor, EdgeVisitor.visit_fn, null);
                        if (edge_visitor_result == .ERROR) return edge_visitor_result;
                    }
                }
            }
        }

        return visitor.VisitResult(T){ .EXHAUSTED = {} };
    }
};

// =============================================================================
// Tests
// =============================================================================
test "basic" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();
    const TestLinkType = Edge.hash_edge_type(1759269396);
    try Edge.register_type(TestLinkType);

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const e12 = EdgeReference.init(bn1.node, bn2.node, TestLinkType);

    _ = g.insert_edge(e12);

    try std.testing.expectEqual(@as(usize, 1), g.get_edge_count());
    try std.testing.expectEqual(@as(usize, 3), g.get_node_count());
}

test "BFSPath cloneAndExtend preserves start metadata" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const TestEdgeType = Edge.hash_edge_type(0xFBAF_0001);
    Edge.register_type(TestEdgeType) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();

    const e12 = EdgeReference.init(bn1.node, bn2.node, TestEdgeType);
    const e23 = EdgeReference.init(bn2.node, bn3.node, TestEdgeType);
    _ = g.insert_edge(e12);
    _ = g.insert_edge(e23);

    var base = try BFSPath.init(bn1);
    defer base.deinit();
    try base.traversed_edges.append(TraversedEdge{
        .edge = e12,
        .forward = true,
    });

    const cloned = try BFSPath.cloneAndExtend(base, bn2, e23);
    defer cloned.deinit();

    try std.testing.expect(cloned.start_node.node.is_same(bn1.node));
    try std.testing.expect(cloned.start_node.g == bn1.g);
    try std.testing.expect(cloned.g == bn1.g);
    try std.testing.expectEqual(@as(usize, 2), cloned.traversed_edges.items.len);
    try std.testing.expect(cloned.traversed_edges.items[0].edge.is_same(e12));
    try std.testing.expect(cloned.traversed_edges.items[1].edge.is_same(e23));
}

test "BFSPath detects inconsistent graph view" {
    const a = std.testing.allocator;
    var g1 = GraphView.init(a);
    defer g1.deinit();
    var g2 = GraphView.init(a);
    defer g2.deinit();

    const bn1 = g1.create_and_insert_node();

    var path = try BFSPath.init(bn1);
    defer {
        path.g = path.start_node.g;
        path.deinit();
    }

    try std.testing.expect(path.is_consistent());
    path.g = &g2;
    try std.testing.expect(!path.is_consistent());

    path.g = path.start_node.g;
    try std.testing.expect(path.is_consistent());
}

test "get_subgraph_from_nodes" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const TestEdgeTypeSubgraph = Edge.hash_edge_type(0xFBAF_0002);
    Edge.register_type(TestEdgeTypeSubgraph) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();

    const e12 = EdgeReference.init(bn1.node, bn2.node, TestEdgeTypeSubgraph);
    const e23 = EdgeReference.init(bn2.node, bn3.node, TestEdgeTypeSubgraph);
    const e13 = EdgeReference.init(bn1.node, bn3.node, TestEdgeTypeSubgraph);

    _ = g.insert_edge(e12);
    _ = g.insert_edge(e23);
    _ = g.insert_edge(e13);

    var nodes = std.ArrayList(NodeReference).init(a);
    defer nodes.deinit();
    try nodes.append(bn1.node);
    try nodes.append(bn2.node);

    var subgraph = g.get_subgraph_from_nodes(nodes);
    defer subgraph.deinit();

    try std.testing.expectEqual(@as(usize, 3), subgraph.get_node_count());
    try std.testing.expectEqual(@as(usize, 1), subgraph.get_edge_count());
}

test "duplicate edge insertion" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();

    const TestLinkType = Edge.hash_edge_type(0xDEADBEEF);
    Edge.register_type(TestLinkType) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    const e1 = EdgeReference.init(bn1.node, bn2.node, TestLinkType);

    _ = g.insert_edge(e1);
    try std.testing.expectEqual(@as(usize, 1), g.edges.count());

    _ = g.insert_edge(e1);
    try std.testing.expectEqual(@as(usize, 1), g.edges.count());
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
        _ = g1.create_and_insert_node();
    }

    i = 0;
    while (i < num_nodes) : (i += 1) {
        _ = g2.create_and_insert_node();
    }

    var timer = try std.time.Timer.start();
    g1.insert_subgraph(&g2);
    const duration = timer.read();

    std.debug.print("\ninsert_subgraph with {d} nodes took {d}ns\n", .{ num_nodes, duration });
}

test "mem_compile" {
    const size_node = @sizeOf(Node);
    const size_edge = @sizeOf(Edge);
    const size_str = @sizeOf(str);
    const size_literal = @sizeOf(Literal);
    const size_attribute = @sizeOf(Attribute);
    const size_dynamic_attributes = @sizeOf(DynamicAttributes);
    const size_node_ref = @sizeOf(NodeReference);
    const size_edge_ref = @sizeOf(EdgeReference);
    const size_attr_ref = @sizeOf(DynamicAttributesReference);

    std.debug.print("size_node: {d}\n", .{size_node});
    std.debug.print("size_edge: {d}\n", .{size_edge});
    std.debug.print("size_str: {d}\n", .{size_str});
    std.debug.print("size_literal: {d}\n", .{size_literal});
    std.debug.print("size_attribute: {d}\n", .{size_attribute});
    std.debug.print("size_dynamic_attributes: {d}\n", .{size_dynamic_attributes});
    std.debug.print("size_node_ref: {d}\n", .{size_node_ref});
    std.debug.print("size_edge_ref: {d}\n", .{size_edge_ref});
    std.debug.print("size_attr_ref: {d}\n", .{size_attr_ref});

    // Verify reference types are 4 bytes (not 8 byte pointers)
    try std.testing.expectEqual(@as(usize, 4), size_node_ref);
    try std.testing.expectEqual(@as(usize, 4), size_edge_ref);
    try std.testing.expectEqual(@as(usize, 4), size_attr_ref);
}

test "speed_insert_node_simple" {
    const a = std.heap.c_allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    var timer = try std.time.Timer.start();
    const num_nodes = 100000;
    var i: usize = 0;
    while (i < num_nodes) : (i += 1) {
        _ = g.create_and_insert_node();
    }
    const duration = timer.read();
    const total_ms = duration / std.time.ns_per_ms;
    const per_node_ns = duration / num_nodes;
    std.debug.print("insert_node with {d} nodes took {d}ms\n", .{ num_nodes, total_ms });
    std.debug.print("per node: {d}ns\n", .{per_node_ns});
}

test "speed_insert_edge_simple" {
    const a = std.heap.c_allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const count = 100000;

    var n1s: [count]NodeReference = undefined;
    var i: usize = 0;
    while (i < count) : (i += 1) {
        n1s[i] = g.create_and_insert_node().node;
    }

    var n2s: [count]NodeReference = undefined;
    i = 0;
    while (i < count) : (i += 1) {
        n2s[i] = g.create_and_insert_node().node;
    }

    var timer = try std.time.Timer.start();
    i = 0;
    while (i < count) : (i += 1) {
        const e = EdgeReference.init(n1s[i], n2s[i], 0);
        _ = g.insert_edge(e);
    }
    const duration = timer.read();
    const total_ms = duration / std.time.ns_per_ms;
    const per_edge_ns = duration / count;
    std.debug.print("insert_edge with {d} edges took {d}ms\n", .{ count, total_ms });
    std.debug.print("per edge: {d}ns\n", .{per_edge_ns});
}
