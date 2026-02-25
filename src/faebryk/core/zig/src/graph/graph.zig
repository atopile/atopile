const std = @import("std");
const visitor = @import("visitor.zig");

pub const str = []const u8;

const base_allocator = std.heap.page_allocator;
var arena_allocator = std.heap.ArenaAllocator.init(base_allocator);
var global_graph_allocator: std.mem.Allocator = arena_allocator.allocator();

// Static storage for edges and attributes (temporary - will be replaced with proper allocator)
var Nodes: [8 * 1024 * 1024]Node = undefined;
var Edges: [16 * 1024 * 1024]Edge = undefined;
var Attrs: [4 * 1024 * 1024]DynamicAttributes = undefined;

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
        order: u7 = 0, // TODO: consider removing
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
    count: u32 = 0,

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

    pub fn add(self: *@This(), uuid: u32) void {
        self.ensureCapacity(uuid);
        self.data[uuid] = true;
        self.count += 1;
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

    pub fn get_or_set(self: *@This(), uuid: u32) bool {
        self.ensureCapacity(uuid);
        if (self.data[uuid]) {
            return true;
        }
        self.data[uuid] = true;
        self.count += 1;
        return false;
    }

    pub fn get_count(self: *const @This()) u32 {
        return self.count;
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

    pub fn set_target_node(self: @This(), target: NodeReference) void {
        Edges[self.uuid].target = target;
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

    pub fn get_order(self: @This()) u7 {
        return Edges[self.uuid].flags.order;
    }

    pub fn set_order(self: @This(), order: u7) void {
        Edges[self.uuid].flags.order = order;
    }

    pub fn get_edge_specific(self: @This()) ?u16 {
        return Edges[self.uuid].flags.edge_specific;
    }

    pub fn set_edge_specific(self: @This(), edge_specific: u16) void {
        Edges[self.uuid].flags.edge_specific = edge_specific;
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

pub const EdgeRefMap = struct {
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

pub const EdgeTypeMap = struct {
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
    traversed_edges: std.array_list.Managed(TraversedEdge),
    allocator: std.mem.Allocator,
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

    pub fn init(allocator: std.mem.Allocator, start: BoundNodeReference) !*@This() {
        var path = try allocator.create(BFSPath);
        path.* = BFSPath{
            .traversed_edges = std.array_list.Managed(TraversedEdge).init(allocator),
            .allocator = allocator,
            .g = start.g,
            .start_node = start,
            .invalid_path = false,
            .stop_new_path_discovery = false,
        };
        path.assert_consistent();
        return path;
    }

    pub fn cloneAndExtend(allocator: std.mem.Allocator, base: *const BFSPath, from_node: BoundNodeReference, edge: EdgeReference) !*BFSPath {
        base.assert_consistent();
        const g = base.g;
        std.debug.assert(base.start_node.g == g);

        var new_path = try BFSPath.init(allocator, base.start_node);

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

    /// Copy path to a different allocator (for returning from BFS)
    pub fn copy(self: *const @This(), allocator: std.mem.Allocator) !*@This() {
        var new_path = try allocator.create(BFSPath);
        new_path.* = BFSPath{
            .traversed_edges = std.array_list.Managed(TraversedEdge).init(allocator),
            .allocator = allocator,
            .g = self.g,
            .start_node = self.start_node,
            .invalid_path = self.invalid_path,
            .stop_new_path_discovery = self.stop_new_path_discovery,
            .visit_strength = self.visit_strength,
        };
        try new_path.traversed_edges.ensureTotalCapacity(self.traversed_edges.items.len);
        new_path.traversed_edges.appendSliceAssumeCapacity(self.traversed_edges.items);
        return new_path;
    }

    pub fn deinit(self: *@This()) void {
        self.assert_consistent();
        self.traversed_edges.deinit();
        self.allocator.destroy(self);
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
    paths: std.array_list.Managed(*BFSPath),
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) @This() {
        return .{ .paths = std.array_list.Managed(*BFSPath).init(allocator), .allocator = allocator };
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
    accepted: bool = false,
};

pub fn BFSVisitResult(comptime T: type) type {
    return struct {
        result: visitor.VisitResult(T),
        accept_path: bool = true,
    };
}

// =============================================================================
// GraphView
// =============================================================================
pub const GraphView = struct {
    base_allocator: std.mem.Allocator,
    arena: *std.heap.ArenaAllocator,
    allocator: std.mem.Allocator,

    // fast (Node, LinkType) -> Edge + Node Storage
    nodes: NodeRefMap.T(EdgeTypeMap.T(std.array_list.Managed(EdgeReference))),

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
            .nodes = NodeRefMap.T(EdgeTypeMap.T(std.array_list.Managed(EdgeReference))).init(allocator),
            .node_set = UUIDBitSet.init(allocator),
            .edge_set = UUIDBitSet.init(allocator),
            .self_node = NodeReference.init(),
        };
        _ = out.insert_node(out.self_node);
        return out;
    }

    /// Like init but without creating a self_node. Used by loads() where
    /// merge_diff will set self_node from the serialized payload.
    fn init_bare(b_allocator: std.mem.Allocator) @This() {
        const arena_ptr = b_allocator.create(std.heap.ArenaAllocator) catch @panic("OOM allocating arena");
        arena_ptr.* = std.heap.ArenaAllocator.init(b_allocator);
        const allocator = arena_ptr.allocator();
        return GraphView{
            .base_allocator = b_allocator,
            .arena = arena_ptr,
            .allocator = allocator,
            .nodes = NodeRefMap.T(EdgeTypeMap.T(std.array_list.Managed(EdgeReference))).init(allocator),
            .node_set = UUIDBitSet.init(allocator),
            .edge_set = UUIDBitSet.init(allocator),
            .self_node = .{ .uuid = 0 },
        };
    }

    pub fn deinit(g: *@This()) void {
        g.arena.deinit();
        g.base_allocator.destroy(g.arena);
    }

    pub fn get_self_node(g: *@This()) BoundNodeReference {
        return g.bind(g.self_node);
    }

    pub fn insert_node(g: *@This(), node: NodeReference) BoundNodeReference {
        if (g.contains_node(node)) {
            return g.bind(node);
        }
        const gop = g.nodes.getOrPut(node) catch @panic("OOM");
        if (!gop.found_existing) {
            gop.value_ptr.* = EdgeTypeMap.T(std.array_list.Managed(EdgeReference)).init(g.allocator);
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
        return g.edge_set.get_count();
    }

    pub fn insert_edge_unchecked(g: *@This(), edge: EdgeReference) void {
        // special function for typegraph.copy_node_into
        // assumes edge already in edge_set
        // assumes both nodes in graph

        const source = edge.get_source_node();
        const target = edge.get_target_node();

        // Get node neighbors (must exist)
        const from_neighbors = g.nodes.getPtr(source).?;
        const to_neighbors = g.nodes.getPtr(target).?;

        const edge_type = edge.get_attribute_edge_type();

        // Use getOrPut for edge type maps
        const from_gop = from_neighbors.getOrPut(edge_type) catch @panic("OOM");
        if (!from_gop.found_existing) {
            from_gop.value_ptr.* = std.array_list.Managed(EdgeReference).initCapacity(g.allocator, 1) catch @panic("OOM");
            from_gop.value_ptr.appendAssumeCapacity(edge);
        } else {
            from_gop.value_ptr.append(edge) catch @panic("OOM");
        }

        const to_gop = to_neighbors.getOrPut(edge_type) catch @panic("OOM");
        if (!to_gop.found_existing) {
            to_gop.value_ptr.* = std.array_list.Managed(EdgeReference).initCapacity(g.allocator, 1) catch @panic("OOM");
            to_gop.value_ptr.appendAssumeCapacity(edge);
        } else {
            to_gop.value_ptr.append(edge) catch @panic("OOM");
        }
    }

    pub const InsertEdgeError = error{
        SourceNodeNotInGraph,
        TargetNodeNotInGraph,
    };

    pub fn insert_edge(g: *@This(), edge: EdgeReference) InsertEdgeError!BoundEdgeReference {
        // Fast check using bitset first
        if (g.edge_set.contains(edge.uuid)) {
            return BoundEdgeReference{
                .edge = edge,
                .g = g,
            };
        }

        // Add to edge set and hashmap
        g.edge_set.add(edge.uuid);

        const source = edge.get_source_node();
        const target = edge.get_target_node();

        // Get node neighbors (must exist)
        const from_neighbors = g.nodes.getPtr(source) orelse return error.SourceNodeNotInGraph;
        const to_neighbors = g.nodes.getPtr(target) orelse return error.TargetNodeNotInGraph;

        const edge_type = edge.get_attribute_edge_type();

        // Use getOrPut for edge type maps
        const from_gop = from_neighbors.getOrPut(edge_type) catch @panic("OOM");
        if (!from_gop.found_existing) {
            from_gop.value_ptr.* = std.array_list.Managed(EdgeReference).initCapacity(g.allocator, 1) catch @panic("OOM");
            from_gop.value_ptr.appendAssumeCapacity(edge);
        } else {
            from_gop.value_ptr.append(edge) catch @panic("OOM");
        }

        const to_gop = to_neighbors.getOrPut(edge_type) catch @panic("OOM");
        if (!to_gop.found_existing) {
            to_gop.value_ptr.* = std.array_list.Managed(EdgeReference).initCapacity(g.allocator, 1) catch @panic("OOM");
            to_gop.value_ptr.appendAssumeCapacity(edge);
        } else {
            to_gop.value_ptr.append(edge) catch @panic("OOM");
        }

        return BoundEdgeReference{
            .edge = edge,
            .g = g,
        };
    }

    /// O(1) edge membership check using bitset
    pub fn contains_edge(g: *const @This(), edge: EdgeReference) bool {
        return g.edge_set.contains(edge.uuid);
    }

    pub fn get_edges_of_type(g: *@This(), node: NodeReference, T: Edge.EdgeType) ?*const std.array_list.Managed(EdgeReference) {
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

    pub fn get_subgraph_from_nodes(g: *@This(), nodes: std.array_list.Managed(NodeReference)) GraphView {
        var new_g = GraphView.init(g.base_allocator);

        // Pre-allocate capacity for nodes
        const node_count: u32 = @intCast(nodes.items.len);
        new_g.nodes.ensureTotalCapacity(node_count) catch @panic("OOM");

        // Insert nodes (this also populates the node_set bitset)
        for (nodes.items) |node| {
            _ = new_g.insert_node(node);
        }

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
                    // Both source and target are confirmed in new_g, so only OOM can fail
                    _ = new_g.insert_edge(edge) catch @panic("OOM");
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
        // FIXME

        //var edge_it = subgraph.edges.keyIterator();
        //while (edge_it.next()) |edge_ptr| {
        //    _ = g.insert_edge(edge_ptr.*);
        //}
    }

    // Ring buffer queue for BFS - reuses memory slots to prevent unbounded growth.
    // Replaces std.fifo.LinearFifo which was removed in Zig 0.15.
    const PathQueue = struct {
        buffer: []*BFSPath,
        head: usize = 0, // write position
        tail: usize = 0, // read position
        count: usize = 0,
        allocator: std.mem.Allocator,

        const initial_capacity = 256;

        fn init(allocator: std.mem.Allocator) @This() {
            const buffer = allocator.alloc(*BFSPath, initial_capacity) catch @panic("OOM");
            return .{ .buffer = buffer, .allocator = allocator };
        }

        fn deinit(self: *@This()) void {
            // Clean up remaining items
            while (self.pop()) |p| {
                p.deinit();
            }
            self.allocator.free(self.buffer);
        }

        fn push(self: *@This(), item: *BFSPath) void {
            if (self.count == self.buffer.len) {
                self.grow();
            }
            self.buffer[self.head] = item;
            self.head = (self.head + 1) % self.buffer.len;
            self.count += 1;
        }

        fn pop(self: *@This()) ?*BFSPath {
            if (self.count == 0) return null;
            const item = self.buffer[self.tail];
            self.tail = (self.tail + 1) % self.buffer.len;
            self.count -= 1;
            return item;
        }

        fn grow(self: *@This()) void {
            const new_cap = self.buffer.len * 2;
            const new_buffer = self.allocator.alloc(*BFSPath, new_cap) catch @panic("OOM");

            // Copy items in order from tail to head
            var i: usize = 0;
            var idx = self.tail;
            while (i < self.count) : (i += 1) {
                new_buffer[i] = self.buffer[idx];
                idx = (idx + 1) % self.buffer.len;
            }

            self.allocator.free(self.buffer);
            self.buffer = new_buffer;
            self.tail = 0;
            self.head = self.count;
        }
    };

    pub fn visit_paths_bfs(
        g: *@This(),
        start_node: BoundNodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: fn (*anyopaque, *BFSPath) BFSVisitResult(T),
        edge_type_filter: ?[]const Edge.EdgeType,
    ) visitor.VisitResult(T) {
        // Use C allocator for path metadata to avoid Arena ballooning.
        // Paths are manually deinitialized when popped from the queue.
        const allocator = std.heap.c_allocator;

        var open_path_queue = PathQueue.init(allocator);
        defer open_path_queue.deinit();

        var visited_nodes = NodeRefMap.T(VisitInfo).init(allocator);
        defer visited_nodes.deinit();

        const EdgeVisitor = struct {
            start_node_ev: BoundNodeReference,
            current_path: *BFSPath,
            open_path_queue: *PathQueue,
            visited_nodes_ev: *NodeRefMap.T(VisitInfo),
            path_allocator: std.mem.Allocator,

            pub fn visit_fn(self_ptr: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const other_node = bound_edge.edge.get_other_node(self.start_node_ev.node);

                if (self.current_path.contains(other_node)) {
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
                if (self.visited_nodes_ev.get(other_node)) |info| {
                    if (info.accepted) {
                        return visitor.VisitResult(void){ .CONTINUE = {} };
                    }
                }
                const new_path = BFSPath.cloneAndExtend(self.path_allocator, self.current_path, self.start_node_ev, bound_edge.edge) catch @panic("OOM");
                self.open_path_queue.push(new_path);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        const empty_path_copy = BFSPath.init(allocator, start_node) catch @panic("OOM");
        open_path_queue.push(empty_path_copy);

        while (open_path_queue.pop()) |path| {
            defer path.deinit();
            if (visited_nodes.get(path.get_last_node().node)) |info| {
                if (info.accepted) {
                    continue;
                }
            }
            const bfs_decision = f(ctx, path);
            if (bfs_decision.accept_path) {
                const end_node = path.get_last_node().node;
                if (visited_nodes.getPtr(end_node)) |info| {
                    info.accepted = true;
                } else {
                    visited_nodes.put(end_node, VisitInfo{ .accepted = true }) catch @panic("OOM");
                }
            }
            const bfs_visitor_result = bfs_decision.result;

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
                .path_allocator = allocator,
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

    // =========================================================================
    // Binary Serialization Methods
    // =========================================================================

    pub fn dumps(g: *@This(), allocator: std.mem.Allocator) SerializationError![]u8 {
        var packed_nodes = std.array_list.Managed(PackedNode).init(allocator);
        defer packed_nodes.deinit();
        var packed_edges = std.array_list.Managed(PackedEdge).init(allocator);
        defer packed_edges.deinit();
        var packed_attrs = std.array_list.Managed(PackedDynamicAttributes).init(allocator);
        defer packed_attrs.deinit();
        var string_table = std.array_list.Managed(u8).init(allocator);
        defer string_table.deinit();
        var attr_set = std.AutoHashMap(u32, void).init(allocator);
        defer attr_set.deinit();

        // Pack nodes
        {
            var i: u32 = 0;
            while (i < g.node_set.capacity) : (i += 1) {
                if (g.node_set.data[i]) {
                    const da_uuid = Nodes[i].dynamic.uuid;
                    packed_nodes.append(.{
                        .original_uuid = i,
                        .dynamic_attr_uuid = da_uuid,
                    }) catch return error.OutOfMemory;
                    if (da_uuid != 0) {
                        attr_set.put(da_uuid, {}) catch return error.OutOfMemory;
                    }
                }
            }
        }

        // Pack edges
        {
            var i: u32 = 0;
            while (i < g.edge_set.capacity) : (i += 1) {
                if (g.edge_set.data[i]) {
                    const edge = &Edges[i];
                    const da_uuid = edge.dynamic.uuid;
                    packed_edges.append(.{
                        .original_uuid = i,
                        .source = edge.source.uuid,
                        .target = edge.target.uuid,
                        .dynamic_attr_uuid = da_uuid,
                        .flags = @bitCast(edge.flags),
                    }) catch return error.OutOfMemory;
                    if (da_uuid != 0) {
                        attr_set.put(da_uuid, {}) catch return error.OutOfMemory;
                    }
                }
            }
        }

        // Pack attributes
        {
            var attr_it = attr_set.keyIterator();
            while (attr_it.next()) |uuid_ptr| {
                const uuid = uuid_ptr.*;
                const attrs = &Attrs[uuid];
                var pda = PackedDynamicAttributes{
                    .original_uuid = uuid,
                    .in_use = @intCast(attrs.in_use),
                    .values = undefined,
                };
                // Zero out all values first
                @memset(std.mem.asBytes(&pda.values), 0);

                for (0..attrs.in_use) |j| {
                    const attr = &attrs.values[j];
                    const ident_ref = appendString(&string_table, attr.identifier);
                    const lit = packLiteral(attr.value, &string_table);
                    pda.values[j] = .{
                        .identifier = ident_ref,
                        .value_tag = @intFromEnum(lit.tag),
                        .value = lit.value,
                    };
                }
                packed_attrs.append(pda) catch return error.OutOfMemory;
            }
        }

        // Assemble buffer
        const nodes_size = packed_nodes.items.len * @sizeOf(PackedNode);
        const edges_size = packed_edges.items.len * @sizeOf(PackedEdge);
        const attrs_size = packed_attrs.items.len * @sizeOf(PackedDynamicAttributes);
        const str_size = string_table.items.len;
        const total_size = @sizeOf(BinaryHeader) + nodes_size + edges_size + attrs_size + str_size;

        const buf = allocator.alloc(u8, total_size) catch return error.OutOfMemory;

        var offset: usize = 0;

        // Header
        const header = BinaryHeader{
            .magic_number = MAGIC,
            .version = FORMAT_VERSION,
            .self_node_uuid = g.self_node.uuid,
            .node_count = @intCast(packed_nodes.items.len),
            .edge_count = @intCast(packed_edges.items.len),
            .attr_count = @intCast(packed_attrs.items.len),
            .string_table_size = @intCast(str_size),
        };
        @memcpy(buf[offset..][0..@sizeOf(BinaryHeader)], std.mem.asBytes(&header));
        offset += @sizeOf(BinaryHeader);

        // Nodes
        if (nodes_size > 0) {
            @memcpy(buf[offset..][0..nodes_size], std.mem.sliceAsBytes(packed_nodes.items));
            offset += nodes_size;
        }

        // Edges
        if (edges_size > 0) {
            @memcpy(buf[offset..][0..edges_size], std.mem.sliceAsBytes(packed_edges.items));
            offset += edges_size;
        }

        // Attrs
        if (attrs_size > 0) {
            @memcpy(buf[offset..][0..attrs_size], std.mem.sliceAsBytes(packed_attrs.items));
            offset += attrs_size;
        }

        // String table
        if (str_size > 0) {
            @memcpy(buf[offset..][0..str_size], string_table.items);
        }

        return buf;
    }

    pub fn merge_diff(g: *@This(), bytes: []const u8) SerializationError!void {
        // Step 1: Validate header
        if (bytes.len < @sizeOf(BinaryHeader)) return error.MalformedPayload;
        const header: BinaryHeader = @bitCast(bytes[0..@sizeOf(BinaryHeader)].*);
        if (header.magic_number != MAGIC) return error.InvalidMagic;
        if (header.version != FORMAT_VERSION) return error.VersionMismatch;

        const expected = try computeExpectedSize(header);
        if (bytes.len != expected) return error.BufferSizeMismatch;

        // Step 2: Compute section offsets
        const nodes_start = @sizeOf(BinaryHeader);
        const nodes_size = @as(usize, header.node_count) * @sizeOf(PackedNode);
        const edges_start = nodes_start + nodes_size;
        const edges_size = @as(usize, header.edge_count) * @sizeOf(PackedEdge);
        const attrs_start = edges_start + edges_size;
        const attrs_size = @as(usize, header.attr_count) * @sizeOf(PackedDynamicAttributes);
        const str_start = attrs_start + attrs_size;

        // Step 3: Copy string table into graph-owned memory
        const string_memory = g.allocator.alloc(u8, header.string_table_size) catch return error.OutOfMemory;
        if (header.string_table_size > 0) {
            @memcpy(string_memory, bytes[str_start..][0..header.string_table_size]);
        }

        // Step 4: Translation tables
        var remap_nodes = std.AutoHashMap(u32, u32).init(g.allocator);
        defer remap_nodes.deinit();
        var remap_attrs = std.AutoHashMap(u32, u32).init(g.allocator);
        defer remap_attrs.deinit();

        // Step 5: Restore attributes
        {
            var attr_idx: u32 = 0;
            while (attr_idx < header.attr_count) : (attr_idx += 1) {
                const da_offset = attrs_start + @as(usize, attr_idx) * @sizeOf(PackedDynamicAttributes);
                const packed_da: PackedDynamicAttributes = @bitCast(bytes[da_offset..][0..@sizeOf(PackedDynamicAttributes)].*);

                var restored_values: [6]Attribute = undefined;
                const in_use: u3 = @intCast(packed_da.in_use);

                for (0..in_use) |j| {
                    const pa = &packed_da.values[j];

                    // Validate value tag
                    if (pa.value_tag > @intFromEnum(ValueTag.Bool)) return error.InvalidValueTag;
                    const tag: ValueTag = @enumFromInt(pa.value_tag);

                    // Validate identifier string bounds
                    try validateStringRef(pa.identifier, header.string_table_size);

                    const ident = resolveString(pa.identifier, string_memory);

                    // Reconstruct literal
                    const value: Literal = switch (tag) {
                        .Int => .{ .Int = pa.value.Int },
                        .Uint => .{ .Uint = pa.value.Uint },
                        .Float => .{ .Float = pa.value.Float },
                        .String => blk: {
                            try validateStringRef(pa.value.String, header.string_table_size);
                            break :blk .{ .String = resolveString(pa.value.String, string_memory) };
                        },
                        .Bool => .{ .Bool = pa.value.Bool != 0 },
                    };

                    restored_values[j] = .{ .identifier = ident, .value = value };
                }

                // Allocate new DA slot
                DynamicAttributes.counter += 1;
                const new_uuid = DynamicAttributes.counter;
                Attrs[new_uuid] = .{
                    .in_use = in_use,
                    .values = restored_values,
                };
                remap_attrs.put(packed_da.original_uuid, new_uuid) catch return error.OutOfMemory;
            }
        }

        // Step 6: Restore nodes
        {
            var node_idx: u32 = 0;
            while (node_idx < header.node_count) : (node_idx += 1) {
                const n_offset = nodes_start + @as(usize, node_idx) * @sizeOf(PackedNode);
                const pn: PackedNode = @bitCast(bytes[n_offset..][0..@sizeOf(PackedNode)].*);

                const bound = g.create_and_insert_node();
                remap_nodes.put(pn.original_uuid, bound.node.uuid) catch return error.OutOfMemory;

                if (pn.dynamic_attr_uuid != 0) {
                    const remapped_attr = remap_attrs.get(pn.dynamic_attr_uuid) orelse pn.dynamic_attr_uuid;
                    Nodes[bound.node.uuid].dynamic.uuid = remapped_attr;
                }
            }
        }

        // Step 7: Restore edges
        {
            var edge_idx: u32 = 0;
            while (edge_idx < header.edge_count) : (edge_idx += 1) {
                const e_offset = edges_start + @as(usize, edge_idx) * @sizeOf(PackedEdge);
                const pe: PackedEdge = @bitCast(bytes[e_offset..][0..@sizeOf(PackedEdge)].*);

                const local_source = remap_nodes.get(pe.source) orelse pe.source;
                const local_target = remap_nodes.get(pe.target) orelse pe.target;

                if (!g.contains_node(.{ .uuid = local_source })) return error.InvalidNodeReference;
                if (!g.contains_node(.{ .uuid = local_target })) return error.InvalidNodeReference;

                const remapped_attr: u32 = if (pe.dynamic_attr_uuid != 0)
                    remap_attrs.get(pe.dynamic_attr_uuid) orelse pe.dynamic_attr_uuid
                else
                    0;

                Edge.counter += 1;
                const new_edge = EdgeReference{ .uuid = Edge.counter };
                Edges[new_edge.uuid] = .{
                    .source = .{ .uuid = local_source },
                    .target = .{ .uuid = local_target },
                    .flags = @bitCast(pe.flags),
                    .dynamic = .{ .uuid = remapped_attr },
                };

                g.edge_set.add(new_edge.uuid);
                g.insert_edge_unchecked(new_edge);
            }
        }

        // Step 8: Restore self node
        g.self_node = .{ .uuid = remap_nodes.get(header.self_node_uuid) orelse header.self_node_uuid };
    }

    pub fn loads(allocator: std.mem.Allocator, bytes: []const u8) SerializationError!*@This() {
        const g_ptr = allocator.create(@This()) catch return error.OutOfMemory;
        g_ptr.* = @This().init_bare(allocator);
        g_ptr.merge_diff(bytes) catch |err| {
            g_ptr.deinit();
            allocator.destroy(g_ptr);
            return err;
        };
        return g_ptr;
    }

    pub fn clone(g: *@This()) SerializationError!*@This() {
        const bytes = try g.dumps(std.heap.c_allocator);
        defer std.heap.c_allocator.free(bytes);
        return loads(g.base_allocator, bytes);
    }
};

// =============================================================================
// Binary Serialization
// =============================================================================

pub const SerializationError = error{
    MalformedPayload,
    VersionMismatch,
    InvalidMagic,
    BufferSizeMismatch,
    IntegerOverflow,
    InvalidValueTag,
    StringOutOfBounds,
    InvalidNodeReference,
    OutOfMemory,
};

const MAGIC: u32 = 0x52494E53; // "RINS"
const FORMAT_VERSION: u32 = 1;

const BinaryHeader = extern struct {
    magic_number: u32,
    version: u32,
    self_node_uuid: u32,
    node_count: u32,
    edge_count: u32,
    attr_count: u32,
    string_table_size: u32,
    _pad: u32 = 0,
};

const PackedStringRef = extern struct {
    offset: u32,
    length: u32,
};

const PackedLiteralValue = extern union {
    Int: i64,
    Uint: u64,
    Float: f64,
    String: PackedStringRef,
    Bool: u8,
    _pad: [8]u8,
};

const PackedAttribute = extern struct {
    identifier: PackedStringRef,
    value_tag: u8,
    _pad: [7]u8 = .{0} ** 7,
    value: PackedLiteralValue,
};

const PackedDynamicAttributes = extern struct {
    original_uuid: u32,
    in_use: u32,
    values: [6]PackedAttribute,
};

const PackedNode = extern struct {
    original_uuid: u32,
    dynamic_attr_uuid: u32,
};

const PackedEdge = extern struct {
    original_uuid: u32,
    source: u32,
    target: u32,
    dynamic_attr_uuid: u32,
    flags: u32,
    _pad: u32 = 0,
};

const ValueTag = enum(u8) {
    Int = 0,
    Uint = 1,
    Float = 2,
    String = 3,
    Bool = 4,
};

comptime {
    std.debug.assert(@sizeOf(BinaryHeader) == 32);
    std.debug.assert(@sizeOf(PackedNode) == 8);
    std.debug.assert(@sizeOf(PackedEdge) == 24);
    std.debug.assert(@sizeOf(PackedAttribute) == 24);
    std.debug.assert(@sizeOf(PackedDynamicAttributes) == 152);
    std.debug.assert(@sizeOf(PackedStringRef) == 8);
    std.debug.assert(@sizeOf(PackedLiteralValue) == 8);
}

fn appendString(string_table: *std.array_list.Managed(u8), s: str) PackedStringRef {
    const offset: u32 = @intCast(string_table.items.len);
    string_table.appendSlice(s) catch @panic("OOM");
    return .{ .offset = offset, .length = @intCast(s.len) };
}

fn packLiteral(lit: Literal, string_table: *std.array_list.Managed(u8)) struct { tag: ValueTag, value: PackedLiteralValue } {
    return switch (lit) {
        .Int => |v| .{ .tag = .Int, .value = .{ .Int = v } },
        .Uint => |v| .{ .tag = .Uint, .value = .{ .Uint = v } },
        .Float => |v| .{ .tag = .Float, .value = .{ .Float = v } },
        .String => |v| .{ .tag = .String, .value = .{ .String = appendString(string_table, v) } },
        .Bool => |v| .{ .tag = .Bool, .value = .{ .Bool = if (v) 1 else 0 } },
    };
}

fn computeExpectedSize(h: BinaryHeader) SerializationError!usize {
    var size: usize = @sizeOf(BinaryHeader);
    size = std.math.add(usize, size, std.math.mul(usize, h.node_count, @sizeOf(PackedNode)) catch return error.IntegerOverflow) catch return error.IntegerOverflow;
    size = std.math.add(usize, size, std.math.mul(usize, h.edge_count, @sizeOf(PackedEdge)) catch return error.IntegerOverflow) catch return error.IntegerOverflow;
    size = std.math.add(usize, size, std.math.mul(usize, h.attr_count, @sizeOf(PackedDynamicAttributes)) catch return error.IntegerOverflow) catch return error.IntegerOverflow;
    size = std.math.add(usize, size, h.string_table_size) catch return error.IntegerOverflow;
    return size;
}

fn validateStringRef(ref: PackedStringRef, string_table_size: u32) SerializationError!void {
    const end = std.math.add(u32, ref.offset, ref.length) catch return error.StringOutOfBounds;
    if (end > string_table_size) return error.StringOutOfBounds;
}

fn resolveString(ref: PackedStringRef, string_memory: []const u8) []const u8 {
    return string_memory[ref.offset..][0..ref.length];
}

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

    _ = try g.insert_edge(e12);

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
    _ = try g.insert_edge(e12);
    _ = try g.insert_edge(e23);

    var base = try BFSPath.init(a, bn1);
    defer base.deinit();
    try base.traversed_edges.append(TraversedEdge{
        .edge = e12,
        .forward = true,
    });

    const cloned = try BFSPath.cloneAndExtend(a, base, bn2, e23);
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

    var path = try BFSPath.init(a, bn1);
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

    _ = try g.insert_edge(e12);
    _ = try g.insert_edge(e23);
    _ = try g.insert_edge(e13);

    var nodes = std.array_list.Managed(NodeReference).init(a);
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

    _ = try g.insert_edge(e1);
    try std.testing.expectEqual(@as(usize, 1), g.get_edge_count());

    _ = try g.insert_edge(e1);
    try std.testing.expectEqual(@as(usize, 1), g.get_edge_count());
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
        _ = try g.insert_edge(e);
    }
    const duration = timer.read();
    const total_ms = duration / std.time.ns_per_ms;
    const per_edge_ns = duration / count;
    std.debug.print("insert_edge with {d} edges took {d}ms\n", .{ count, total_ms });
    std.debug.print("per edge: {d}ns\n", .{per_edge_ns});
    //
}

// =============================================================================
// Serialization Tests
// =============================================================================

test "serialization: sparse identity roundtrip" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const SerTestEdgeType = Edge.hash_edge_type(0xBEEF_0001);
    Edge.register_type(SerTestEdgeType) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    // Create nodes with attributes
    var node_refs: [20]NodeReference = undefined;
    for (0..20) |i| {
        const bn = g.create_and_insert_node();
        node_refs[i] = bn.node;
    }

    // Add attributes to some nodes
    node_refs[0].put("name", .{ .String = "first_node" });
    node_refs[0].put("count", .{ .Int = 42 });
    node_refs[1].put("ratio", .{ .Float = 3.14 });
    node_refs[1].put("active", .{ .Bool = true });
    node_refs[2].put("empty_str", .{ .String = "" });
    node_refs[3].put("unsigned", .{ .Uint = 999 });

    // Create edges between nodes
    for (0..19) |i| {
        const e = EdgeReference.init(node_refs[i], node_refs[i + 1], SerTestEdgeType);
        _ = try g.insert_edge(e);
    }

    // Add attributes to an edge
    const edge_with_attr = EdgeReference.init(node_refs[0], node_refs[5], SerTestEdgeType);
    edge_with_attr.put("weight", .{ .Float = 1.5 });
    _ = try g.insert_edge(edge_with_attr);

    const orig_node_count = g.get_node_count();
    const orig_edge_count = g.get_edge_count();

    // Serialize
    const data = try g.dumps(a);
    defer a.free(data);

    // Deserialize into a new graph
    var g2 = GraphView.init(a);
    defer g2.deinit();

    try g2.merge_diff(data);

    // The destination graph had 1 self_node + now has all the serialized nodes remapped
    // merge_diff creates new nodes for each packed node, so count = 1 (orig self) + orig_node_count
    // But merge_diff also sets self_node to the remapped one, so the original self_node of g2
    // might be orphaned in the nodes map. Let's just check the new node count >= orig_node_count.
    try std.testing.expectEqual(orig_node_count + 1, g2.get_node_count());
    try std.testing.expectEqual(orig_edge_count, g2.get_edge_count());
}

test "serialization: string table bounds and swizzling" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    // Create nodes with various string attributes
    const bn1 = g.create_and_insert_node();
    bn1.node.put("empty", .{ .String = "" });
    bn1.node.put("short", .{ .String = "x" });

    const bn2 = g.create_and_insert_node();
    bn2.node.put("long", .{ .String = "this is a longer test string for serialization" });

    // Serialize
    const data = try g.dumps(a);
    defer a.free(data);

    // Deserialize into a new graph
    var g2 = GraphView.init(a);
    defer g2.deinit();
    try g2.merge_diff(data);

    // Verify by checking the deserialized graph has the right node count
    // (3 nodes: self + bn1 + bn2, plus g2's original self node)
    try std.testing.expectEqual(@as(usize, 4), g2.get_node_count());

    // Test out-of-bounds string ref rejection
    // Create a malicious payload with bad string ref
    const good_data = try g.dumps(a);
    defer a.free(good_data);

    // Read the header to find where attrs are
    const hdr: BinaryHeader = @bitCast(good_data[0..@sizeOf(BinaryHeader)].*);
    if (hdr.attr_count > 0) {
        const a_start = @sizeOf(BinaryHeader) +
            @as(usize, hdr.node_count) * @sizeOf(PackedNode) +
            @as(usize, hdr.edge_count) * @sizeOf(PackedEdge);

        // Read the first PackedDynamicAttributes
        var first_da: PackedDynamicAttributes = @bitCast(good_data[a_start..][0..@sizeOf(PackedDynamicAttributes)].*);

        if (first_da.in_use > 0) {
            // Corrupt the identifier offset
            const saved_offset = first_da.values[0].identifier.offset;
            _ = saved_offset;
            first_da.values[0].identifier.offset = hdr.string_table_size + 100;

            // Write the corrupted DA back into good_data
            @memcpy(good_data[a_start..][0..@sizeOf(PackedDynamicAttributes)], std.mem.asBytes(&first_da));

            var g3 = GraphView.init(a);
            defer g3.deinit();
            const result = g3.merge_diff(good_data);
            try std.testing.expectError(error.StringOutOfBounds, result);
        }
    }
}

test "serialization: malicious payload rejection" {
    const a = std.testing.allocator;

    // Test 1: Wrong magic number
    {
        var buf: [@sizeOf(BinaryHeader)]u8 = undefined;
        const bad_header = BinaryHeader{
            .magic_number = 0xDEADBEEF,
            .version = FORMAT_VERSION,
            .self_node_uuid = 0,
            .node_count = 0,
            .edge_count = 0,
            .attr_count = 0,
            .string_table_size = 0,
        };
        @memcpy(&buf, std.mem.asBytes(&bad_header));
        var g = GraphView.init(a);
        defer g.deinit();
        try std.testing.expectError(error.InvalidMagic, g.merge_diff(&buf));
    }

    // Test 2: Version mismatch
    {
        var buf: [@sizeOf(BinaryHeader)]u8 = undefined;
        const bad_header = BinaryHeader{
            .magic_number = MAGIC,
            .version = 99,
            .self_node_uuid = 0,
            .node_count = 0,
            .edge_count = 0,
            .attr_count = 0,
            .string_table_size = 0,
        };
        @memcpy(&buf, std.mem.asBytes(&bad_header));
        var g = GraphView.init(a);
        defer g.deinit();
        try std.testing.expectError(error.VersionMismatch, g.merge_diff(&buf));
    }

    // Test 3: Buffer size mismatch (claims 1000 nodes but buffer is header-only)
    {
        var buf: [@sizeOf(BinaryHeader)]u8 = undefined;
        const bad_header = BinaryHeader{
            .magic_number = MAGIC,
            .version = FORMAT_VERSION,
            .self_node_uuid = 0,
            .node_count = 1000,
            .edge_count = 0,
            .attr_count = 0,
            .string_table_size = 0,
        };
        @memcpy(&buf, std.mem.asBytes(&bad_header));
        var g = GraphView.init(a);
        defer g.deinit();
        try std.testing.expectError(error.BufferSizeMismatch, g.merge_diff(&buf));
    }

    // Test 4: Too small payload
    {
        var g = GraphView.init(a);
        defer g.deinit();
        try std.testing.expectError(error.MalformedPayload, g.merge_diff("too short"));
    }

    // Test 5: Dangling edge reference
    {
        // Build a payload with one edge whose source is not a node in the payload
        const header_size = @sizeOf(BinaryHeader);
        const edge_size = @sizeOf(PackedEdge);
        const total = header_size + edge_size;
        var buf: [total]u8 = undefined;

        const hdr = BinaryHeader{
            .magic_number = MAGIC,
            .version = FORMAT_VERSION,
            .self_node_uuid = 0,
            .node_count = 0,
            .edge_count = 1,
            .attr_count = 0,
            .string_table_size = 0,
        };
        @memcpy(buf[0..header_size], std.mem.asBytes(&hdr));

        const dangling_edge = PackedEdge{
            .original_uuid = 1,
            .source = 0xFFFFFF,
            .target = 0xFFFFFE,
            .dynamic_attr_uuid = 0,
            .flags = 0,
        };
        @memcpy(buf[header_size..][0..edge_size], std.mem.asBytes(&dangling_edge));

        var g = GraphView.init(a);
        defer g.deinit();
        try std.testing.expectError(error.InvalidNodeReference, g.merge_diff(&buf));
    }

    // Test 6: Invalid value tag
    {
        const header_size = @sizeOf(BinaryHeader);
        const attr_size = @sizeOf(PackedDynamicAttributes);
        const total = header_size + attr_size;
        var buf: [total]u8 = undefined;

        const hdr = BinaryHeader{
            .magic_number = MAGIC,
            .version = FORMAT_VERSION,
            .self_node_uuid = 0,
            .node_count = 0,
            .edge_count = 0,
            .attr_count = 1,
            .string_table_size = 0,
        };
        @memcpy(buf[0..header_size], std.mem.asBytes(&hdr));

        var bad_attrs: PackedDynamicAttributes = undefined;
        @memset(std.mem.asBytes(&bad_attrs), 0);
        bad_attrs.original_uuid = 1;
        bad_attrs.in_use = 1;
        bad_attrs.values[0].value_tag = 255; // invalid
        bad_attrs.values[0].identifier = .{ .offset = 0, .length = 0 };
        @memcpy(buf[header_size..][0..attr_size], std.mem.asBytes(&bad_attrs));

        var g = GraphView.init(a);
        defer g.deinit();
        try std.testing.expectError(error.InvalidValueTag, g.merge_diff(&buf));
    }
}

test "serialization: remapping collision" {
    const a = std.testing.allocator;

    const SerCollisionEdgeType = Edge.hash_edge_type(0xBEEF_0002);
    Edge.register_type(SerCollisionEdgeType) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    // Create main graph
    var g_main = GraphView.init(a);
    defer g_main.deinit();
    const main_n1 = g_main.create_and_insert_node();
    const main_n2 = g_main.create_and_insert_node();
    _ = try g_main.insert_edge(EdgeReference.init(main_n1.node, main_n2.node, SerCollisionEdgeType));

    const main_node_count_before = g_main.get_node_count();
    const main_edge_count_before = g_main.get_edge_count();

    // Create worker graph (UUIDs will be higher since counter is global monotonic)
    var g_worker = GraphView.init(a);
    defer g_worker.deinit();
    const w_n1 = g_worker.create_and_insert_node();
    const w_n2 = g_worker.create_and_insert_node();
    const w_n3 = g_worker.create_and_insert_node();
    w_n1.node.put("worker", .{ .String = "node1" });
    const w_e12 = EdgeReference.init(w_n1.node, w_n2.node, SerCollisionEdgeType);
    const w_e23 = EdgeReference.init(w_n2.node, w_n3.node, SerCollisionEdgeType);
    _ = try g_worker.insert_edge(w_e12);
    _ = try g_worker.insert_edge(w_e23);

    const worker_node_count = g_worker.get_node_count();
    const worker_edge_count = g_worker.get_edge_count();

    // Advance main by adding more nodes to potentially collide
    _ = g_main.create_and_insert_node();

    // Serialize worker
    const data = try g_worker.dumps(a);
    defer a.free(data);

    // Merge into main
    try g_main.merge_diff(data);

    // Main should now have: original nodes + worker nodes (remapped)
    // main had main_node_count_before + 1 (the extra node we added)
    // worker contributed worker_node_count new nodes
    const expected_nodes = main_node_count_before + 1 + worker_node_count;
    try std.testing.expectEqual(expected_nodes, g_main.get_node_count());

    // Edges: main had main_edge_count_before, worker contributed worker_edge_count
    const expected_edges = main_edge_count_before + worker_edge_count;
    try std.testing.expectEqual(expected_edges, g_main.get_edge_count());
}

test "serialization: loads and clone" {
    const a = std.testing.allocator;

    const CloneEdgeType = Edge.hash_edge_type(0xBEEF_0003);
    Edge.register_type(CloneEdgeType) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    var g = GraphView.init(a);
    defer g.deinit();

    const n1 = g.create_and_insert_node();
    const n2 = g.create_and_insert_node();
    n1.node.put("key", .{ .String = "value" });
    const e = EdgeReference.init(n1.node, n2.node, CloneEdgeType);
    _ = try g.insert_edge(e);

    // Test loads
    const data = try g.dumps(a);
    defer a.free(data);
    const loaded = try GraphView.loads(a, data);
    defer {
        loaded.deinit();
        a.destroy(loaded);
    }
    try std.testing.expectEqual(g.get_node_count(), loaded.get_node_count());
    try std.testing.expectEqual(g.get_edge_count(), loaded.get_edge_count());

    // Test clone
    const cloned = try g.clone();
    defer {
        cloned.deinit();
        a.destroy(cloned);
    }
    try std.testing.expectEqual(g.get_node_count(), cloned.get_node_count());
    try std.testing.expectEqual(g.get_edge_count(), cloned.get_edge_count());
}
