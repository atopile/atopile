const std = @import("std");
const visitor = @import("visitor.zig");

pub const str = []const u8;

const base_allocator = std.heap.page_allocator;
var arena_allocator = std.heap.ArenaAllocator.init(base_allocator);
var global_graph_allocator: std.mem.Allocator = arena_allocator.allocator();

var Edges: [1024]Edge = [_]Edge{undefined} ** 1024;
var Attrs: [1024]DynamicAttributes = [_]DynamicAttributes{undefined} ** 1024;

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

pub const NodeReference = struct {
    uuid: u32,

    pub fn is_same(self: @This(), other: @This()) bool {
        return self.uuid == other.uuid;
    }

    pub fn get_uuid(self: @This()) u32 {
        return self.uuid;
    }
};

pub const EdgeReference = struct {
    uuid: u32,

    pub fn init(source: NodeReference, target: NodeReference, edge_type: Edge.EdgeType) EdgeReference {
        Edge.counter += 1;
        const out: EdgeReference = .{
            .uuid = Edge.counter,
        };
        Edges[out.uuid].source = source;
        Edges[out.uuid].target = target;
        Edges[out.uuid].flags.edge_type = edge_type;
        return out;
    }

    pub fn is_same(self: @This(), other: @This()) bool {
        return self.uuid == other.uuid;
    }

    pub fn deref(self: @This()) Edge {
        if (self.uuid >= Edge.counter) {
            @panic("Edge reference out of bounds");
        }
        return Edges[self.uuid];
    }

    pub fn get_uuid(self: @This()) u32 {
        return self.uuid;
    }
};

pub const DynamicAttributesReference = struct {
    uuid: u32 = 0,

    pub fn deref(self: @This()) DynamicAttributes {
        if (self.uuid == 0) {
            @panic("Dynamic attribute null pointer");
        }
        if (self.uuid >= DynamicAttributes.counter) {
            @panic("Dynamic attributes reference out of bounds");
        }
        return Attrs[self.uuid];
    }
};

pub const BoundNodeReference = struct {
    node: NodeReference,
    g: *GraphView,

    /// No guarantee that there is only one
    pub fn get_single_edge(self: @This(), edge_type: Edge.EdgeType, is_target: ?bool) ?BoundEdgeReference {
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

pub const Node = struct {
    var counter: u32 = 0;
    pub fn init() NodeReference {
        counter += 1;
        return .{
            .uuid = counter,
        };
    }
};

pub const Edge = struct {
    var counter: u32 = 0;
    const Flags = packed struct {
        edge_type: EdgeType,
        directional: u1 = 0,
        order: u7 = 0,
        edge_specific: u16 = 0,
    };
    source: NodeReference, // 4b
    target: NodeReference, // 4b
    dynamic: DynamicAttributesReference = .{}, // 4b
    flags: Flags, // 4b
    // => 16b

    //_ref_count: GraphReferenceCounter,node_

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

    /// Put a dynamic attribute on this edge
    pub fn put(self: *@This(), identifier: str, value: Literal) void {
        self.attributes.put(identifier, value);
    }

    /// Get a dynamic attribute from this edge
    pub fn get(self: @This(), identifier: str) ?Literal {
        return self.dynamic.get(identifier);
    }

    pub fn get_attribute_name(self: @This()) ?str {
        return self.attributes.name;
    }

    pub fn get_attribute_directional(self: @This()) bool {
        return self.attributes.directional;
    }

    pub fn get_attribute_edge_type(self: @This()) EdgeType {
        return self.attributes.edge_type;
    }

    /// Set the name attribute
    pub fn set_attribute_name(self: @This(), name: ?str) void {
        self.attributes.name = name;
    }

    /// Set the directional attribute
    pub fn set_attribute_directional(self: @This(), directional: ?bool) void {
        self.attributes.directional = directional;
    }

    /// Set the edge type attribute
    pub fn set_attribute_edge_type(self: @This(), edge_type: EdgeType) void {
        self.attributes.edge_type = edge_type;
    }

    /// Copy dynamic attributes from another DynamicAttributes into this edge
    pub fn copy_dynamic_attributes_into(self: @This(), from: *const DynamicAttributes) void {
        from.copy_into(&self.attributes.dynamic);
    }

    /// Visit all attributes on this edge (both static and dynamic)
    pub fn visit_attributes(self: @This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        // Visit static attributes
        f(ctx, "edge_type", Literal{ .Int = @intCast(self.attributes.edge_type) }, false);
        if (self.attributes.directional) |d| {
            f(ctx, "directional", Literal{ .Bool = d }, false);
        }
        if (self.attributes.name) |n| {
            f(ctx, "name", Literal{ .String = n }, false);
        }
        // Visit dynamic attributes
        self.attributes.dynamic.visit(ctx, f);
    }

    pub fn get_target(self: @This()) ?NodeReference {
        if (self.get_attribute_directional()) |d| {
            if (d) {
                return self.deref().target;
            }
            return self.deref().source;
        }
        return null;
    }

    pub fn get_other_node(self: @This(), N: NodeReference) NodeReference {
        if (self.deref().source.is_same(N)) {
            return self.deref().target;
        } else if (self.deref().target.is_same(N)) {
            return self.deref().source;
        } else {
            @panic("Edge is not connected to the given node");
        }
    }

    pub fn is_instance(self: @This(), edge_type: Edge.EdgeType) bool {
        return self.get_attribute_edge_type() == edge_type;
    }

    pub fn get_source(self: @This()) ?NodeReference {
        if (self.get_attribute_directional()) |d| {
            if (d) {
                return self.source;
            }
            return self.target;
        }
        return null;
    }
};

pub const DynamicAttributes = struct {
    var counter: u32 = 0;

    in_use: u3 = 0,
    // try to keep this low enough to fit in a 256b cache line
    // currently attribute is 40b, so max 6
    values: [6]Attribute,

    pub fn init() DynamicAttributesReference {
        counter += 1;
        return .{
            .uuid = counter,
        };
    }

    pub fn visit(self: *@This(), ctx: *anyopaque, f: fn (*anyopaque, str, Literal, bool) void) void {
        for (self.values) |value| {
            f(ctx, value.identifier, value.value, true);
        }
    }

    pub fn copy_into(self: *const @This(), other: *@This()) void {
        if (other.in_use > 0) {
            @panic("Other dynamic attributes are already in use");
        }
        other.in_use = self.in_use;
        @memcpy(other.values, self.values);
    }

    pub fn put(self: *@This(), identifier: str, value: Literal) void {
        if (self.is_use == self.values.len) {
            @panic("Dynamic attributes are full");
        }
        self.values[self.in_use] = .{ .identifier = identifier, .value = value };
        self.in_use += 1;
    }

    pub fn get(self: *@This(), identifier: str) ?Literal {
        for (self.values[0..self.in_use]) |value| {
            if (std.mem.eql(u8, value.identifier, identifier)) {
                return value.value;
            }
        }
        return null;
    }
};

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

pub const GraphView = struct {

    // allocators
    base_allocator: std.mem.Allocator,
    arena: *std.heap.ArenaAllocator,
    allocator: std.mem.Allocator,

    // fast (Node, LinkType) -> Edge + Node Storage
    nodes: NodeRefMap.T(EdgeTypeMap.T(std.ArrayList(EdgeReference))),
    // Edge Storage
    edges: EdgeRefMap.T(void),

    self_node: NodeReference,

    pub fn init(b_allocator: std.mem.Allocator) @This() {
        const arena_ptr = b_allocator.create(std.heap.ArenaAllocator) catch @panic("OOM allocating arena");
        arena_ptr.* = std.heap.ArenaAllocator.init(b_allocator);
        const allocator = arena_ptr.allocator();
        var out = GraphView{
            .base_allocator = b_allocator,
            .arena = arena_ptr,
            .allocator = allocator,
            //
            .edges = EdgeRefMap.T(void).init(allocator),
            .nodes = NodeRefMap.T(EdgeTypeMap.T(std.ArrayList(EdgeReference))).init(allocator),
            .self_node = Node.init(),
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
        if (g.contains_node(node)) {
            return g.bind(node);
        }

        g.nodes.put(node, EdgeTypeMap.T(std.ArrayList(EdgeReference)).init(g.allocator)) catch {
            @panic("OOM");
        };

        return g.bind(node);
    }

    pub fn contains_node(g: *@This(), node: NodeReference) bool {
        return g.nodes.contains(node);
    }

    pub fn create_and_insert_node(g: *@This()) BoundNodeReference {
        return g.insert_node(Node.init());
    }

    pub fn bind(g: *@This(), node: NodeReference) BoundNodeReference {
        // TODO maybe checks
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

        g.edges.put(edge, {}) catch @panic("OOM");

        // handle caches
        const edge_type = edge.get_attribute_edge_type();
        const from_neighbors = g.nodes.getPtr(edge.source).?;
        const to_neighbors = g.nodes.getPtr(edge.target).?;

        if (!from_neighbors.contains(edge_type)) {
            from_neighbors.put(edge_type, std.ArrayList(EdgeReference).init(g.allocator)) catch @panic("OOM");
        }
        if (!to_neighbors.contains(edge_type)) {
            to_neighbors.put(edge_type, std.ArrayList(EdgeReference).init(g.allocator)) catch @panic("OOM");
        }

        from_neighbors.getPtr(edge_type).?.append(edge) catch @panic("OOM");
        to_neighbors.getPtr(edge_type).?.append(edge) catch @panic("OOM");

        return BoundEdgeReference{
            .edge = edge,
            .g = g,
        };
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
            // Filter by direction if specified
            if (directed) |d| {
                if (edge.deref().get_attribute_directional()) {
                    if ((d and !edge.deref().source.is_same(node)) or (!d and !edge.deref().target.is_same(node))) {
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

    pub fn get_edge_with_type_and_identifier(g: *@This(), node: NodeReference, edge_type: Edge.EdgeType, identifier: str) ?EdgeReference {
        // visit edges by type and check for identifier match
        const Visit = struct {
            pub fn visit(ctx: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(EdgeReference) {
                _ = ctx;
                if (bound_edge.edge.get_attribute_name() == identifier) {
                    return visitor.VisitResult(EdgeReference){ .OK = bound_edge.edge };
                }
                return visitor.VisitResult(EdgeReference){ .CONTINUE = {} };
            }
        };
        var visit = Visit{};
        const result = g.visit_edges_of_type(node, edge_type, EdgeReference, &visit, Visit.visit, true);
        switch (result) {
            .OK => return result.OK,
            .EXHAUSTED => return null,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => |err| @panic(@errorName(err)),
        }
    }

    pub fn get_subgraph_from_nodes(g: *@This(), nodes: std.ArrayList(NodeReference)) GraphView {
        // create new graph view
        // that contains only the nodes in the list and the edges between them
        var new_g = GraphView.init(g.base_allocator);

        for (nodes.items) |node| {
            _ = new_g.insert_node(node);
        }
        for (nodes.items) |node| {
            var edge_by_type_it = g.nodes.getPtr(node).?.valueIterator();
            while (edge_by_type_it.next()) |edges_by_type_ptr| {
                var edges_it = edges_by_type_ptr.valueIterator();
                while (edges_it.next()) |edge_ptr| {
                    const edge = edge_ptr.*;
                    if (!new_g.contains_node(edge.source) or !new_g.contains_node(edge.target)) {
                        continue;
                    }
                    _ = new_g.insert_edge(edge);
                }
            }
        }
        return new_g;
    }

    pub fn insert_subgraph(g: *@This(), subgraph: GraphView) void {
        // TODO consider adding multi insert node/edges function
        //  and some way to disable the guards to improve performance
        //  but not 100% sure whether that will have measurable benefits

        // Pre-allocate for nodes
        const added_nodes_len = subgraph.nodes.items.len;
        g.neighbors.ensureUnusedCapacity(@intCast(added_nodes_len)) catch @panic("OOM");
        g.nodes.ensureUnusedCapacity(@intCast(added_nodes_len)) catch @panic("OOM");
        g.neighbor_by_type_and_name.ensureUnusedCapacity(@intCast(added_nodes_len)) catch @panic("OOM");

        for (subgraph.nodes.items) |node| {
            _ = g.insert_node(node);
        }

        // Pre-allocate for edges
        const added_edges_len = subgraph.edges.count();
        g.edges.ensureUnusedCapacity(@intCast(added_edges_len)) catch @panic("OOM");

        var it = subgraph.edges.keyIterator();
        while (it.next()) |edge_ptr| {
            const edge = edge_ptr.*;
            _ = g.insert_edge(edge);
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
        // TODO get base allocator passed
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
    const TestLinkType = Edge.hash_edge_type(1759269396);
    try Edge.register_type(TestLinkType);

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const e12 = Edge.init(bn1.node, bn2.node, TestLinkType);
    // no deinit defer required, since graph will deinit all nodes and edges if they reach 0

    _ = g.insert_edge(e12);

    //const edges = g.get_edges(bn1.node).?;
    //try std.testing.expectEqual(edges.items.len, 1);
    //try std.testing.expectEqual(edges.items[0].get_uuid(), e12.get_uuid());
    //try std.testing.expectEqual(edges.items[0].target.get_uuid(), bn2.node.get_uuid());

    //try std.testing.expectEqual(bn1.node._ref_count.ref_count, 1);
    //try std.testing.expectEqual(bn2.node._ref_count.ref_count, 1);
    //try std.testing.expectEqual(e12._ref_count.ref_count, 1);
}

test "nodeattributes" {
    const a = std.testing.allocator;
    global_graph_allocator = a;
    var g = GraphView.init(a);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();

    try std.testing.expect(bn1.get("test") == null);
    bn1.node.put("test", .{ .String = "test" });
    const attr_read = bn1.get("test");
    try std.testing.expect(attr_read != null);
    try std.testing.expect(attr_read.? == .String);
    try std.testing.expect(std.mem.eql(u8, attr_read.?.String, "test"));

    bn1.node.put("test2", .{ .Int = 5 });
    const attr_read2 = bn1.node.get("test2");
    try std.testing.expect(attr_read2 != null);
    try std.testing.expect(attr_read2.? == .Int);
    try std.testing.expect(attr_read2.?.Int == 5);

    const VisitorCtx = struct {
        values: std.ArrayList(Literal),
        failed: bool,
        pub fn visit(ctx: *anyopaque, key: str, value: Literal, _: bool) void {
            const self: *@This() = @ptrCast(@alignCast(ctx));
            if (!std.mem.eql(u8, key, "test") and !std.mem.eql(u8, key, "test2")) {
                self.failed = true;
                return;
            }
            self.values.append(value) catch @panic("OOM");
        }
    };
    var visitor_ctx = VisitorCtx{ .values = std.ArrayList(Literal).init(a), .failed = false };
    defer visitor_ctx.values.deinit();

    bn1.node.visit_attributes(&visitor_ctx, VisitorCtx.visit);
    try std.testing.expectEqual(@as(usize, 2), visitor_ctx.values.items.len);
    try std.testing.expect(visitor_ctx.values.items[0] == .String);
    try std.testing.expect(visitor_ctx.values.items[1] == .Int);
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

    const e12 = Edge.init(bn1.node, bn2.node, TestEdgeType);
    const e23 = Edge.init(bn2.node, bn3.node, TestEdgeType);
    _ = g.insert_edge(e12);
    _ = g.insert_edge(e23);

    var base = try BFSPath.init(bn1);
    defer base.deinit();
    try base.traversed_edges.append(TraversedEdge{
        .edge = e12,
        .forward = true, // n1 -> n2 is forward (source to target)
    });

    const cloned = try BFSPath.cloneAndExtend(base, bn2, e23);
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

    const bn1 = g1.create_and_insert_node();

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

    const TestEdgeTypeSubgraph = Edge.hash_edge_type(0xFBAF_0002);
    Edge.register_type(TestEdgeTypeSubgraph) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();

    const e12 = Edge.init(bn1.node, bn2.node, TestEdgeTypeSubgraph);
    const e23 = Edge.init(bn2.node, bn3.node, TestEdgeTypeSubgraph);
    const e13 = Edge.init(bn1.node, bn3.node, TestEdgeTypeSubgraph);

    _ = g.insert_edge(e12);
    _ = g.insert_edge(e23);
    _ = g.insert_edge(e13);

    var nodes = std.ArrayList(NodeReference).init(a);
    defer nodes.deinit();
    try nodes.append(bn1.node);
    try nodes.append(bn2.node);

    var subgraph = g.get_subgraph_from_nodes(nodes);
    defer subgraph.deinit();

    // 2 nodes + 1 self_node
    try std.testing.expectEqual(@as(usize, 3), subgraph.get_node_count());

    const sub_edges_n1 = subgraph.get_edges(bn1.node).?;
    try std.testing.expectEqual(@as(usize, 1), sub_edges_n1.items.len);
    try std.testing.expectEqual(e12.get_uuid(), sub_edges_n1.items[0].get_uuid());

    const sub_edges_n2 = subgraph.get_edges(bn2.node).?;
    try std.testing.expectEqual(@as(usize, 1), sub_edges_n2.items.len);
    try std.testing.expectEqual(e12.get_uuid(), sub_edges_n2.items[0].get_uuid());
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

    const e1 = Edge.init(bn1.node, bn2.node, TestLinkType);

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
        _ = g1.create_and_insert_node();
    }

    i = 0;
    while (i < num_nodes) : (i += 1) {
        _ = g2.create_and_insert_node();
    }

    var timer = try std.time.Timer.start();
    g1.insert_subgraph(g2);
    const duration = timer.read();

    std.debug.print("\ninsert_subgraph with {d} nodes took {d}ns\n", .{ num_nodes, duration });
}

test "get_edge_with_type_and_identifier" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();

    const TestEdgeType = Edge.hash_edge_type(0xFBAF_0003);
    Edge.register_type(TestEdgeType) catch |err| switch (err) {
        error.DuplicateType => {},
        else => return err,
    };

    const e12 = Edge.init(bn1.node, bn2.node, TestEdgeType);
    e12.set_attribute_directional(true);
    e12.set_attribute_name("e12");
    _ = g.insert_edge(e12);

    const out = g.get_edge_with_type_and_identifier(bn1.node, TestEdgeType, "e12");
    try std.testing.expect(out != null);
    try std.testing.expect(out.?.get_uuid() == e12.get_uuid());

    const out2 = g.get_edge_with_type_and_identifier(bn2.node, TestEdgeType, "e12");
    try std.testing.expect(out2 == null);

    const out3 = g.get_edge_with_type_and_identifier(bn1.node, TestEdgeType, "e13");
    try std.testing.expect(out3 == null);
}

const _TrackingAllocator = struct {
    underlying: std.mem.Allocator,
    totalRequested: usize,
    totalFreed: usize,

    pub fn init(underlying: std.mem.Allocator) _TrackingAllocator {
        return .{ .underlying = underlying, .totalRequested = 0, .totalFreed = 0 };
    }

    pub fn allocator(self: *_TrackingAllocator) std.mem.Allocator {
        return std.mem.Allocator{
            .ptr = self,
            .vtable = &std.mem.Allocator.VTable{
                .alloc = alloc,
                .resize = resize,
                .free = free,
                .remap = remap,
            },
        };
    }

    fn alloc(
        context: *anyopaque,
        len: usize,
        alignment: std.mem.Alignment,
        ret_addr: usize,
    ) ?[*]u8 {
        const self: *_TrackingAllocator = @ptrCast(@alignCast(context));
        self.totalRequested += len;
        std.debug.print("alloc: +{d} = {d}\n", .{ len, self.totalRequested - self.totalFreed });
        return self.underlying.vtable.alloc(self.underlying.ptr, len, alignment, ret_addr);
    }

    fn resize(
        context: *anyopaque,
        memory: []u8,
        alignment: std.mem.Alignment,
        new_len: usize,
        ret_addr: usize,
    ) bool {
        const self: *_TrackingAllocator = @ptrCast(@alignCast(context));
        self.totalRequested += new_len - memory.len;
        return self.underlying.vtable.resize(self.underlying.ptr, memory, alignment, new_len, ret_addr);
    }

    fn free(
        context: *anyopaque,
        old_memory: []u8,
        alignment: std.mem.Alignment,
        ret_addr: usize,
    ) void {
        const self: *_TrackingAllocator = @ptrCast(@alignCast(context));
        self.totalFreed += old_memory.len;
        std.debug.print("free: -{d} = {d}\n", .{ old_memory.len, self.totalRequested - self.totalFreed });
        self.underlying.vtable.free(self.underlying.ptr, old_memory, alignment, ret_addr);
    }

    fn remap(
        context: *anyopaque,
        memory: []u8,
        alignment: std.mem.Alignment,
        new_len: usize,
        return_address: usize,
    ) ?[*]u8 {
        const self: *_TrackingAllocator = @ptrCast(@alignCast(context));
        self.totalRequested += new_len - memory.len;
        return self.underlying.vtable.remap(self.underlying.ptr, memory, alignment, new_len, return_address);
    }
};

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

    //try std.testing.expectEqual(24, @as(usize, size_literal));

    //try std.testing.expectEqual(2, @as(usize, size_ref_count));
    //try std.testing.expectEqual(16, @as(usize, size_node_attr));
    //try std.testing.expectEqual(24, size_node);
}

test "mem_node_with_string" {
    const a = std.testing.allocator;
    var t = _TrackingAllocator.init(a);
    global_graph_allocator = t.allocator();

    std.debug.print("cache_line: {d}\n", .{std.atomic.cache_line});

    const node = Node.init();
    //try std.testing.expectEqual(@as(usize, 16), t.totalRequested);
    const value: Literal = .{ .String = "test" };
    node.put("test", value);

    //try std.testing.expectEqual(@as(usize, 96), t.totalRequested - t.totalFreed);

    node.put("test2", value);
    node.put("test3", value);

    std.debug.print("allocated: {d}\n", .{t.totalRequested - t.totalFreed});
    std.debug.print("freed: {d}\n", .{t.totalFreed});
    //try std.testing.expectEqual(@as(usize, 216), t.totalRequested - t.totalFreed);
}

test "speed_insert_node_simple" {
    const a = std.heap.c_allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    // measure time
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

test "speed_insert_node_with_attr" {
    const a = std.heap.c_allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    // measure time
    var timer = try std.time.Timer.start();
    const num_nodes = 100000;
    var i: usize = 0;
    while (i < num_nodes) : (i += 1) {
        const n = g.create_and_insert_node();
        n.node.put("test", .{ .Int = @as(i64, @intCast(i)) });
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

    // measure time
    var timer = try std.time.Timer.start();
    i = 0;
    while (i < count) : (i += 1) {
        const e = Edge.init(n1s[i], n2s[i], 0);
        _ = g.insert_edge(e);
    }
    const duration = timer.read();
    const total_ms = duration / std.time.ns_per_ms;
    const per_edge_ns = duration / count;
    std.debug.print("insert_edge with {d} edges took {d}ms\n", .{ count, total_ms });
    std.debug.print("per edge: {d}ns\n", .{per_edge_ns});
}
