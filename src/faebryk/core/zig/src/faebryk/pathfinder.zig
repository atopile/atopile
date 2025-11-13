const std = @import("std");
const graph_mod = @import("graph");
const composition_mod = @import("composition.zig");
const interface_mod = @import("interface.zig");
const type_mod = @import("node_type.zig");

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
const DynamicBitSetUnmanaged = std.bit_set.DynamicBitSetUnmanaged;

const HierarchyTraverseDirection = enum {
    up, // Child to parent
    down, // Parent to child
    horizontal, // Same level (interface connections)
};

const HierarchyElement = struct {
    edge: EdgeReference,
    traverse_direction: HierarchyTraverseDirection,
    parent_type_node: NodeReference,
    child_type_node: NodeReference,

    fn match(self: *const @This(), other: *const @This()) bool {
        const opposite_directions = (self.traverse_direction == .up and other.traverse_direction == .down) or
            (self.traverse_direction == .down and other.traverse_direction == .up);

        const parent_type_match = Node.is_same(self.parent_type_node, other.parent_type_node);
        const child_type_match = Node.is_same(self.child_type_node, other.child_type_node);
        const child_name_match = switch (self.traverse_direction) {
            .horizontal => true,
            .up, .down => std.mem.eql(u8, self.edge.attributes.name orelse "", other.edge.attributes.name orelse ""),
        };

        return parent_type_match and child_type_match and child_name_match and opposite_directions;
    }
};

// Shallow link attribute key
const shallow = EdgeInterfaceConnection.shallow_attribute;

pub const PathFinder = struct {
    const Self = @This();

    allocator: std.mem.Allocator,
    path_list: std.ArrayList(*BFSPath),
    graph: ?*GraphView = null,
    path_counter: u64,
    valid_path_counter: u64,

    pub fn init(allocator: std.mem.Allocator) PathFinder {
        return .{
            .allocator = allocator,
            .path_list = std.ArrayList(*BFSPath).init(allocator),
            .path_counter = 0,
            .valid_path_counter = 0,
        };
    }

    pub fn deinit(self: *Self) void {
        for (self.path_list.items) |path| {
            path.deinit();
        }
        self.path_list.deinit();
    }

    // Find all valid paths from start node
    // Note: PathFinder is intended for single-use. Create a new instance for each search.
    pub fn find_paths(
        self: *Self,
        start_node: BoundNodeReference,
    ) !graph.BFSPaths {
        self.graph = start_node.g;
        defer self.graph = null;

        self.path_list.clearRetainingCapacity();
        try self.path_list.ensureTotalCapacity(256);

        const result = start_node.g.visit_paths_bfs(
            start_node,
            void,
            self,
            Self.visit_fn,
        );

        switch (result) {
            .ERROR => |err| return err,
            .CONTINUE => {},
            .EXHAUSTED => {},
            .OK => {},
            .STOP => {},
        }

        if (self.path_list.items.len > 0) {
            try self.apply_split_validation();
        }

        // Transfer ownership to BFSPaths
        var bfs_paths = graph.BFSPaths.init(self.allocator);
        bfs_paths.paths = self.path_list;
        self.path_list = std.ArrayList(*BFSPath).init(self.allocator);

        return bfs_paths;
    }

    // BFS visitor callback
    pub fn visit_fn(self_ptr: *anyopaque, path: *BFSPath) visitor.VisitResult(void) {
        const self: *Self = @ptrCast(@alignCast(self_ptr));
        const result = self.run_filters(path);
        if (result == .ERROR) return result;
        if (result == .STOP) return result;

        // if path is invalid, don't save to path_list
        if (path.invalid_path) {
            path.visit_strength = .unvisited;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }

        path.visit_strength = .strong;

        // else save to path_list
        var copied_path = BFSPath.init(path.start_node) catch @panic("OOM");
        copied_path.traversed_edges.ensureTotalCapacity(path.traversed_edges.items.len) catch @panic("OOM");
        copied_path.traversed_edges.appendSliceAssumeCapacity(path.traversed_edges.items);
        copied_path.stop_new_path_discovery = path.stop_new_path_discovery;
        copied_path.visit_strength = path.visit_strength;
        self.path_list.append(copied_path) catch @panic("OOM");
        self.valid_path_counter += 1;

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn run_filters(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        for (filters) |filter| {
            const result = filter.func(self, path);
            switch (result) {
                .CONTINUE => {},
                .STOP => return result,
                .ERROR => return result,
                .OK => {},
                .EXHAUSTED => return result,
            }

            if (path.stop_new_path_discovery) {
                // no point iterating through other filters
                break;
            }
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    fn apply_split_validation(self: *Self) !void {
        if (self.graph == null) return;
        var tracker = SplitTracker.init(self.allocator, self.graph.?);
        defer tracker.deinit();

        var paths_require_validation = false;
        for (self.path_list.items) |path| {
            if (try tracker.process_path(path)) {
                paths_require_validation = true;
            }
        }

        if (!paths_require_validation) return;

        tracker.invalidate_paths();

        var i: usize = 0;
        while (i < self.path_list.items.len) {
            const path = self.path_list.items[i];
            if (path.invalid_path) {
                path.deinit();
                _ = self.path_list.swapRemove(i);
            } else {
                i += 1;
            }
        }
    }

    // Filters
    const filters = [_]struct {
        name: []const u8,
        func: *const fn (*Self, *BFSPath) visitor.VisitResult(void),
    }{
        .{ .name = "count_paths", .func = Self.count_paths },
        .{ .name = "filter_path_by_edge_type", .func = Self.filter_path_by_edge_type },
        .{ .name = "filter_path_by_same_node_type", .func = Self.filter_path_by_same_node_type },
        .{ .name = "filter_siblings", .func = Self.filter_siblings },
        .{ .name = "filter_hierarchy_stack", .func = Self.filter_hierarchy_stack },
    };

    pub fn count_paths(self: *Self, _: *BFSPath) visitor.VisitResult(void) {
        self.path_counter += 1;

        if (self.path_counter > 1_000_000) {
            return visitor.VisitResult(void){ .STOP = {} };
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_edge_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;

        // skip this check if no edges in path
        if (path.traversed_edges.items.len == 0) return visitor.VisitResult(void){ .CONTINUE = {} };

        // filter out edges that aren't composition or interface
        const last_edge = path.traversed_edges.items[path.traversed_edges.items.len - 1].edge;
        if (EdgeComposition.is_instance(last_edge) or EdgeInterfaceConnection.is_instance(last_edge)) {
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
        path.stop_new_path_discovery = true;
        path.invalid_path = true;
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    pub fn filter_path_by_same_node_type(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        const start_node = path.start_node;
        const end_node = path.get_last_node();

        const start_type_edge = EdgeType.get_type_edge(start_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };
        const end_type_edge = EdgeType.get_type_edge(end_node) orelse return visitor.VisitResult(void){ .CONTINUE = {} };

        const start_node_type = EdgeType.get_type_node(start_type_edge.edge);
        const end_node_type = EdgeType.get_type_node(end_type_edge.edge);

        if (!Node.is_same(start_node_type, end_node_type)) {
            path.invalid_path = true;
        }

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    // Filters out paths where last 2 edges form child -> parent -> child (sibling traversal)
    pub fn filter_siblings(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        _ = self;
        const traversed_edges = path.traversed_edges.items;

        if (traversed_edges.len < 2) return visitor.VisitResult(void){ .CONTINUE = {} };

        const last_edges = [_]EdgeReference{ traversed_edges[traversed_edges.len - 1].edge, traversed_edges[traversed_edges.len - 2].edge };
        for (last_edges) |edge| {
            if (!EdgeComposition.is_instance(edge)) {
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        }

        const edge_1_and_edge_2_share_parent = graph.Node.is_same(EdgeComposition.get_parent_node(last_edges[0]), EdgeComposition.get_parent_node(last_edges[1]));
        if (edge_1_and_edge_2_share_parent) {
            path.invalid_path = true;
            path.stop_new_path_discovery = true;
        }
        return visitor.VisitResult(void){ .CONTINUE = {} };
    }

    fn resolve_node_type(g: *GraphView, node: NodeReference) !NodeReference {
        const te = EdgeType.get_type_edge(g.bind(node)) orelse return error.MissingNodeType;
        return EdgeType.get_type_node(te.edge);
    }

    // Validates paths follow hierarchy rules:
    // 1. Must return to same level (balanced stack)
    // 2. Cannot descend from starting level
    // 3. Shallow links only if at same or deeper level
    pub fn filter_hierarchy_stack(self: *Self, path: *BFSPath) visitor.VisitResult(void) {
        if (path.invalid_path) return visitor.VisitResult(void){ .CONTINUE = {} };

        var stack = std.ArrayList(HierarchyElement).init(self.allocator);
        defer stack.deinit();

        const g = path.start_node.g;
        var depth: i32 = 0;

        // iterate through path
        for (path.traversed_edges.items) |traversed_edge| {
            const edge = traversed_edge.edge;
            const start_node = traversed_edge.get_start_node();

            // hierarchical edge
            if (EdgeComposition.is_instance(edge)) {
                // determine traversal direction
                var hierarchy_direction: HierarchyTraverseDirection = undefined;
                if (Node.is_same(EdgeComposition.get_child_node(edge), start_node)) {
                    hierarchy_direction = .up;
                    depth += 1;
                } else if (Node.is_same(EdgeComposition.get_parent_node(edge), start_node)) {
                    hierarchy_direction = .down;
                    depth -= 1;
                }

                const hierarchy_element = HierarchyElement{
                    .edge = edge,
                    .traverse_direction = hierarchy_direction,
                    .parent_type_node = resolve_node_type(g, EdgeComposition.get_parent_node(edge)) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    },
                    .child_type_node = resolve_node_type(g, EdgeComposition.get_child_node(edge)) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    },
                };

                if (stack.items.len > 0 and stack.items[stack.items.len - 1].match(&hierarchy_element)) {
                    _ = stack.pop();
                } else {
                    stack.append(hierarchy_element) catch @panic("OOM");
                }
            }

            if (EdgeInterfaceConnection.is_instance(edge)) {
                const shallow_edge = (edge.attributes.dynamic.values.get(shallow) orelse continue).Bool;
                if (shallow_edge and depth > 0) path.invalid_path = true;
            }
        }

        if (stack.items.len != 0) {
            path.invalid_path = true;
        }

        return visitor.VisitResult(void){ .CONTINUE = {} };
    }
};

const SplitKey = struct {
    parent: NodeReference,
    context_hash: u64,

    const Ctx = struct {
        pub fn eql(_: @This(), a: SplitKey, b: SplitKey) bool {
            return a.context_hash == b.context_hash and Node.is_same(a.parent, b.parent);
        }

        pub fn hash(_: @This(), key: SplitKey) u64 {
            var hasher = std.hash.Wyhash.init(key.context_hash);
            hasher.update(std.mem.asBytes(&key.parent.attributes.uuid));
            return hasher.final();
        }
    };
};

const SplitKeyMap = std.HashMap(SplitKey, *SplitCoverage, SplitKey.Ctx, std.hash_map.default_max_load_percentage);
const SplitKeySet = std.HashMap(SplitKey, void, SplitKey.Ctx, std.hash_map.default_max_load_percentage);

const ParentInfo = struct {
    children: std.ArrayList(NodeReference),
    child_index: graph.NodeRefMap.T(usize),

    fn init(allocator: std.mem.Allocator) ParentInfo {
        return .{
            .children = std.ArrayList(NodeReference).init(allocator),
            .child_index = graph.NodeRefMap.T(usize).init(allocator),
        };
    }

    fn deinit(self: *ParentInfo) void {
        self.children.deinit();
        self.child_index.deinit();
    }

    fn populate(self: *ParentInfo, graph_view: *GraphView, parent: NodeReference) !void {
        const bound_parent = graph_view.bind(parent);
        const Visitor = struct {
            info: *ParentInfo,

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx_self: *@This() = @ptrCast(@alignCast(self_ptr));
                const child = EdgeComposition.get_child_node(edge.edge);
                ctx_self.info.children.append(child) catch return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
                ctx_self.info.child_index.put(child, ctx_self.info.children.items.len - 1) catch return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var ctx = Visitor{ .info = self };
        const visit_result = EdgeComposition.visit_children_edges(bound_parent, void, &ctx, Visitor.visit);
        switch (visit_result) {
            .ERROR => |err| return err,
            else => {},
        }
    }

    fn child_count(self: *const ParentInfo) usize {
        return self.children.items.len;
    }

    fn get_child_index(self: *const ParentInfo, child: NodeReference) ?usize {
        return self.child_index.get(child);
    }
};

const TargetCoverage = struct {
    bits: DynamicBitSetUnmanaged,
    child_count: usize,

    fn init(allocator: std.mem.Allocator, child_count: usize) !TargetCoverage {
        return .{
            .bits = try DynamicBitSetUnmanaged.initEmpty(allocator, child_count),
            .child_count = child_count,
        };
    }

    fn deinit(self: *TargetCoverage, allocator: std.mem.Allocator) void {
        self.bits.deinit(allocator);
    }

    fn mark(self: *TargetCoverage, child_index: usize) void {
        if (!self.bits.isSet(child_index)) {
            self.bits.set(child_index);
        }
    }

    fn complete(self: *const TargetCoverage) bool {
        return self.bits.count() == self.child_count;
    }
};

const SplitCoverage = struct {
    parent_info: *ParentInfo,
    targets: graph.NodeRefMap.T(*TargetCoverage),

    fn init(allocator: std.mem.Allocator, parent_info: *ParentInfo) SplitCoverage {
        return .{
            .parent_info = parent_info,
            .targets = graph.NodeRefMap.T(*TargetCoverage).init(allocator),
        };
    }

    fn deinit(self: *SplitCoverage, allocator: std.mem.Allocator) void {
        var it = self.targets.iterator();
        while (it.next()) |entry| {
            const coverage_ptr = entry.value_ptr.*;
            coverage_ptr.deinit(allocator);
            allocator.destroy(coverage_ptr);
        }
        self.targets.deinit();
    }

    fn ensure_target(self: *SplitCoverage, allocator: std.mem.Allocator, target: NodeReference) !*TargetCoverage {
        const gop = try self.targets.getOrPut(target);
        if (!gop.found_existing) {
            const coverage_ptr = try allocator.create(TargetCoverage);
            coverage_ptr.* = try TargetCoverage.init(allocator, self.parent_info.child_count());
            gop.value_ptr.* = coverage_ptr;
        }
        return gop.value_ptr.*;
    }
};

const PathMeta = struct {
    keys: std.ArrayList(SplitKey),

    fn init(allocator: std.mem.Allocator) PathMeta {
        return .{ .keys = std.ArrayList(SplitKey).init(allocator) };
    }

    fn deinit(self: *PathMeta) void {
        self.keys.deinit();
    }
};

const SplitEvent = struct {
    key: SplitKey,
    child_index: usize,
    info: *ParentInfo,
};

const SplitTracker = struct {
    allocator: std.mem.Allocator,
    graph: *GraphView,
    parent_infos: graph.NodeRefMap.T(*ParentInfo),
    split_entries: SplitKeyMap,
    path_meta: std.AutoHashMap(*BFSPath, *PathMeta),

    fn init(allocator: std.mem.Allocator, graph_view: *GraphView) SplitTracker {
        return .{
            .allocator = allocator,
            .graph = graph_view,
            .parent_infos = graph.NodeRefMap.T(*ParentInfo).init(allocator),
            .split_entries = SplitKeyMap.init(allocator),
            .path_meta = std.AutoHashMap(*BFSPath, *PathMeta).init(allocator),
        };
    }

    fn deinit(self: *SplitTracker) void {
        var meta_it = self.path_meta.iterator();
        while (meta_it.next()) |entry| {
            entry.value_ptr.*.deinit();
            self.allocator.destroy(entry.value_ptr.*);
        }
        self.path_meta.deinit();

        var split_it = self.split_entries.iterator();
        while (split_it.next()) |entry| {
            entry.value_ptr.*.deinit(self.allocator);
            self.allocator.destroy(entry.value_ptr.*);
        }
        self.split_entries.deinit();

        var parent_it = self.parent_infos.iterator();
        while (parent_it.next()) |entry| {
            entry.value_ptr.*.deinit();
            self.allocator.destroy(entry.value_ptr.*);
        }
        self.parent_infos.deinit();
    }

    fn process_path(self: *SplitTracker, path: *BFSPath) !bool {
        var events = std.ArrayList(SplitEvent).init(self.allocator);
        defer events.deinit();

        var prefix_hash = hash_node(0, path.start_node.node);

        for (path.traversed_edges.items) |traversed| {
            const parent_context_hash = prefix_hash;

            if (EdgeComposition.is_instance(traversed.edge)) {
                const parent_node = EdgeComposition.get_parent_node(traversed.edge);
                const child_node = EdgeComposition.get_child_node(traversed.edge);
                const is_down = Node.is_same(traversed.get_start_node(), parent_node);

                if (is_down) {
                    if (try self.fetch_parent_info(parent_node)) |info| {
                        if (info.get_child_index(child_node)) |child_index| {
                            const key = SplitKey{ .parent = parent_node, .context_hash = parent_context_hash };
                            try events.append(.{ .key = key, .child_index = child_index, .info = info });
                        }
                    }
                }
            }

            prefix_hash = hash_edge(prefix_hash, traversed.edge);
        }

        if (events.items.len == 0) {
            return false;
        }

        try self.record_events(path, &events);
        return true;
    }

    fn invalidate_paths(self: *SplitTracker) void {
        var it = self.path_meta.iterator();
        while (it.next()) |entry| {
            const path = entry.key_ptr.*;
            const meta = entry.value_ptr.*;
            const target = path.get_last_node().node;
            var valid = true;

            for (meta.keys.items) |key| {
                const coverage_ptr = self.split_entries.get(key) orelse {
                    valid = false;
                    break;
                };
                const target_ptr = coverage_ptr.*.targets.get(target) orelse {
                    valid = false;
                    break;
                };
                if (!target_ptr.complete()) {
                    valid = false;
                    break;
                }
            }

            if (!valid) {
                path.invalid_path = true;
            }
        }
    }

    fn record_events(self: *SplitTracker, path: *BFSPath, events: *std.ArrayList(SplitEvent)) !void {
        const target_node = path.get_last_node().node;

        for (events.items) |event| {
            const coverage_ptr = try self.get_or_create_split_coverage(event.key, event.info);
            const target_cov = try coverage_ptr.ensure_target(self.allocator, target_node);
            target_cov.mark(event.child_index);
        }

        var meta_ptr = try self.allocator.create(PathMeta);
        meta_ptr.* = PathMeta.init(self.allocator);
        errdefer {
            meta_ptr.deinit();
            self.allocator.destroy(meta_ptr);
        }

        var seen = SplitKeySet.init(self.allocator);
        defer seen.deinit();

        for (events.items) |event| {
            const res = try seen.getOrPut(event.key);
            if (res.found_existing) continue;
            try meta_ptr.keys.append(event.key);
        }

        try self.path_meta.put(path, meta_ptr);
    }

    fn fetch_parent_info(self: *SplitTracker, parent: NodeReference) !?*ParentInfo {
        if (self.parent_infos.get(parent)) |info| {
            return if (info.child_count() >= 2) info else null;
        }

        const info_ptr = try self.allocator.create(ParentInfo);
        info_ptr.* = ParentInfo.init(self.allocator);
        errdefer {
            info_ptr.deinit();
            self.allocator.destroy(info_ptr);
        }

        try info_ptr.populate(self.graph, parent);
        try self.parent_infos.put(parent, info_ptr);

        if (info_ptr.child_count() < 2) {
            return null;
        }
        return info_ptr;
    }

    fn get_or_create_split_coverage(self: *SplitTracker, key: SplitKey, info: *ParentInfo) !*SplitCoverage {
        const gop = try self.split_entries.getOrPut(key);
        if (!gop.found_existing) {
            const coverage_ptr = try self.allocator.create(SplitCoverage);
            coverage_ptr.* = SplitCoverage.init(self.allocator, info);
            gop.value_ptr.* = coverage_ptr;
        }
        return gop.value_ptr.*;
    }
};

fn hash_node(base: u64, node: NodeReference) u64 {
    var hasher = std.hash.Wyhash.init(base);
    const uuid = node.attributes.uuid;
    hasher.update(std.mem.asBytes(&uuid));
    return hasher.final();
}

fn hash_edge(base: u64, edge: EdgeReference) u64 {
    var hasher = std.hash.Wyhash.init(base);
    const uuid = edge.attributes.uuid;
    hasher.update(std.mem.asBytes(&uuid));
    return hasher.final();
}

// Test from graph.zig - basic pathfinding with end nodes
test "visit_paths_bfs" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    const n1 = Node.init(a);
    const n2 = Node.init(a);
    const n3 = Node.init(a);
    const n4 = Node.init(a);
    const n5 = Node.init(a);
    const n6 = Node.init(a);
    const n7 = Node.init(a);
    const e1 = Edge.init(a, n1, n2, 1759242069);
    const e2 = Edge.init(a, n1, n3, 1759242069);
    const e3 = Edge.init(a, n2, n4, 1759242068);
    const e4 = Edge.init(a, n2, n5, 1759242069);
    const e5 = Edge.init(a, n5, n6, 1759242069);
    const e6 = Edge.init(a, n6, n1, 1759242069);
    const e7 = Edge.init(a, n4, n7, 1759242069);
    n1.attributes.uuid = 1001;
    n2.attributes.uuid = 1002;
    n3.attributes.uuid = 1003;
    n4.attributes.uuid = 1004;
    n5.attributes.uuid = 1005;
    n6.attributes.uuid = 1006;
    n7.attributes.uuid = 1007;
    e1.attributes.uuid = 2001;
    e2.attributes.uuid = 2002;
    e3.attributes.uuid = 2003;
    e4.attributes.uuid = 2004;
    e5.attributes.uuid = 2005;
    e6.attributes.uuid = 2006;
    e7.attributes.uuid = 2007;
    defer g.deinit();

    const bn1 = g.insert_node(n1);
    const bn2 = g.insert_node(n2);
    const bn4 = g.insert_node(n4);
    _ = g.insert_node(n3);
    _ = g.insert_node(n5);
    _ = g.insert_node(n6);
    _ = g.insert_node(n7);
    _ = g.insert_edge(e1);
    _ = g.insert_edge(e2);
    _ = g.insert_edge(e3);
    _ = g.insert_edge(e4);
    _ = g.insert_edge(e5);
    _ = g.insert_edge(e6);
    _ = g.insert_edge(e7);

    var pf1 = PathFinder.init(a);
    defer pf1.deinit();

    _ = bn2;
    _ = bn4;

    var paths1 = try pf1.find_paths(bn1);
    defer paths1.deinit();
}

test "filter_hierarchy_stack" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();
    const bn4 = g.create_and_insert_node();
    const be1 = g.insert_edge(Edge.init(g.allocator, bn2.node, bn1.node, EdgeComposition.tid));
    const be2 = g.insert_edge(Edge.init(g.allocator, bn3.node, bn4.node, EdgeComposition.tid));
    const be3 = g.insert_edge(Edge.init(g.allocator, bn2.node, bn3.node, EdgeInterfaceConnection.tid));

    var bfs_path = try BFSPath.init(bn1);

    try bfs_path.traversed_edges.append(TraversedEdge{ .edge = be1.edge, .forward = false }); // bn1 -> bn2 (target -> source)
    try bfs_path.traversed_edges.append(TraversedEdge{ .edge = be3.edge, .forward = true }); // bn2 -> bn3 (source -> target)
    try bfs_path.traversed_edges.append(TraversedEdge{ .edge = be2.edge, .forward = true }); // bn3 -> bn4 (source -> target)
    defer bfs_path.deinit();

    var pf = PathFinder.init(g.allocator);
    defer pf.deinit();
    _ = pf.filter_hierarchy_stack(bfs_path);
}
