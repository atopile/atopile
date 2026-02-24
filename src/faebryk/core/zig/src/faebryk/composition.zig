const graph_mod = @import("graph");
const std = @import("std");
const node_type_mod = @import("node_type.zig");
const trait_mod = @import("trait.zig");
const edgebuilder_mod = @import("edgebuilder.zig");
const typegraph_mod = @import("typegraph.zig");
const linker_mod = @import("linker.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const EdgeType = node_type_mod.EdgeType;
const EdgeTrait = trait_mod.EdgeTrait;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;
const return_first = visitor.return_first;
const TypeGraph = typegraph_mod.TypeGraph;
const Linker = linker_mod.Linker;

pub const ChildQuery = struct {
    direct_only: bool,
    types: []const graph.NodeReference,
    include_root: bool,
    sort: bool,
    required_traits: []const graph.NodeReference,
};

pub const EdgeComposition = struct {
    pub const tid: Edge.EdgeType = graph.Edge.hash_edge_type(1759269250);
    pub var registered: bool = false;

    /// Create an EdgeTraversal for following a Composition edge by identifier.
    pub fn traverse(identifier: str) TypeGraph.ChildReferenceNode.EdgeTraversal {
        return .{ .identifier = identifier, .edge_type = tid };
    }

    pub fn init(parent: NodeReference, child: NodeReference, child_identifier: str) EdgeReference {
        const edge = EdgeReference.init(parent, child, tid);

        build(child_identifier).apply_to(edge);
        return edge;
    }

    pub fn build(child_identifier: str) EdgeCreationAttributes {
        if (!registered) {
            @branchHint(.unlikely);
            registered = true;
            Edge.register_type(tid) catch {};
        }
        return .{
            .edge_type = tid,
            .directional = true,
            .name = child_identifier,
            .dynamic = graph.DynamicAttributes.init_on_stack(),
        };
    }

    pub fn is_instance(E: EdgeReference) bool {
        return E.is_instance(tid);
    }

    pub fn get_parent_node(E: EdgeReference) NodeReference {
        return E.get_source_node();
    }

    pub fn get_child_node(E: EdgeReference) NodeReference {
        return E.get_target_node();
    }

    pub fn get_child_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (edge.get_target_node().is_same(node)) {
            return null;
        }
        return get_child_node(edge);
    }

    pub fn get_parent_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (edge.get_source_node().is_same(node)) {
            return null;
        }
        return get_parent_node(edge);
    }

    pub fn visit_children_edges(
        bound_node: graph.BoundNodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            target: graph.BoundNodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const child = EdgeComposition.get_child_of(bound_edge.edge, self.target.node);
                if (child) |_| {
                    const child_result = self.cb(self.cb_ctx, bound_edge);
                    switch (child_result) {
                        .CONTINUE => {},
                        else => return child_result,
                    }
                }
                return visitor.VisitResult(T){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .target = bound_node, .cb_ctx = ctx, .cb = f };
        // directed = true: parent is source, child is target
        return bound_node.g.visit_edges_of_type(bound_node.node, tid, T, &visit, Visit.visit, true);
    }

    pub fn get_parent_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return bound_node.get_single_edge(tid, true);
    }

    pub fn get_parent_node_of(bound_node: graph.BoundNodeReference) ?graph.BoundNodeReference {
        const parent_edge = EdgeComposition.get_parent_edge(bound_node) orelse return null;
        return parent_edge.g.bind(EdgeComposition.get_parent_node(parent_edge.edge));
    }

    pub fn add_child(bound_node: graph.BoundNodeReference, child: NodeReference, child_identifier: ?str) graph.GraphView.InsertEdgeError!graph.BoundEdgeReference {
        // if child identifier is null, then generate a unique identifier
        const link = EdgeComposition.init(bound_node.node, child, child_identifier orelse "");
        return bound_node.g.insert_edge(link);
    }

    pub fn get_name(edge: EdgeReference) !str {
        if (!is_instance(edge)) {
            return error.InvalidEdgeType;
        }

        return edge.get_attribute_name() orelse "";
    }

    pub fn get_child_by_identifier(bound_parent_node: graph.BoundNodeReference, child_identifier: str) ?graph.BoundNodeReference {
        // Visit edges of type and find the one with matching name
        const Finder = struct {
            identifier: str,

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(graph.BoundEdgeReference) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                if (bound_edge.edge.get_attribute_name()) |name| {
                    if (std.mem.eql(u8, name, self.identifier)) {
                        return visitor.VisitResult(graph.BoundEdgeReference){ .OK = bound_edge };
                    }
                }
                return visitor.VisitResult(graph.BoundEdgeReference){ .CONTINUE = {} };
            }
        };

        var finder = Finder{ .identifier = child_identifier };
        const result = bound_parent_node.g.visit_edges_of_type(bound_parent_node.node, tid, graph.BoundEdgeReference, &finder, Finder.visit, true);
        switch (result) {
            .OK => |edge| return bound_parent_node.g.bind(EdgeComposition.get_child_node(edge.edge)),
            .EXHAUSTED => return null,
            .ERROR => return null,
            .CONTINUE => unreachable,
            .STOP => unreachable,
        }
    }

    pub fn visit_children_of_type(
        parent: graph.BoundNodeReference,
        child_type: graph.NodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            parent: graph.BoundNodeReference,
            child_type: graph.NodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const child = bound_edge.g.bind(EdgeComposition.get_child_node(bound_edge.edge));
                if (!EdgeType.is_node_instance_of(child, self.child_type)) {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }
                return self.cb(self.cb_ctx, bound_edge);
            }
        };

        var visit = Visit{ .parent = parent, .child_type = child_type, .cb_ctx = ctx, .cb = f };
        // directed = true: parent is source, child is target
        return parent.g.visit_edges_of_type(parent.node, tid, T, &visit, Visit.visit, true);
    }

    pub fn try_get_single_child_of_type(bound_node: graph.BoundNodeReference, child_type: graph.NodeReference) ?graph.BoundNodeReference {
        const Ctx = struct {};
        var ctx = Ctx{};
        const result = EdgeComposition.visit_children_of_type(bound_node, child_type, graph.BoundEdgeReference, &ctx, return_first(graph.BoundEdgeReference).visit);
        switch (result) {
            .OK => |found| return found.g.bind(EdgeComposition.get_child_node(found.edge)),
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => return null, // Convert error to null since function returns optional
            .EXHAUSTED => return null,
        }
    }

    fn check_node_matches(bound_child: graph.BoundNodeReference, query: ChildQuery) bool {
        if (query.types.len > 0) {
            var type_matches = false;
            for (query.types) |t| {
                if (EdgeType.is_node_instance_of(bound_child, t)) {
                    type_matches = true;
                    break;
                }
            }
            if (!type_matches) {
                return false;
            }
        }
        for (query.required_traits) |t| {
            if (EdgeTrait.try_get_trait_instance_of_type(bound_child, t) == null) {
                return false;
            }
        }
        return true;
    }

    pub fn get_children_query(node: graph.BoundNodeReference, query: ChildQuery, allocator: std.mem.Allocator) std.array_list.Managed(graph.NodeReference) {
        var out = std.array_list.Managed(graph.NodeReference).init(allocator);

        const ChildEntry = struct {
            node: graph.NodeReference,
            name: str,
        };

        // First, collect ALL direct children (without filtering)
        var direct_children = std.array_list.Managed(ChildEntry).init(allocator);
        defer direct_children.deinit();

        const CollectAllChildren = struct {
            children: *std.array_list.Managed(ChildEntry),

            pub fn visit_edge(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const child = EdgeComposition.get_child_node(bound_edge.edge);
                const name = bound_edge.edge.get_attribute_name() orelse "";
                self.children.append(.{ .node = child, .name = name }) catch @panic("OOM");
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var collector = CollectAllChildren{ .children = &direct_children };
        _ = EdgeComposition.visit_children_edges(node, void, &collector, CollectAllChildren.visit_edge);

        if (query.sort) {
            const Sorter = struct {
                pub fn lessThan(_: void, lhs: ChildEntry, rhs: ChildEntry) bool {
                    return std.mem.lessThan(u8, lhs.name, rhs.name);
                }
            };
            std.sort.block(ChildEntry, direct_children.items, {}, Sorter.lessThan);
        }

        // For each direct child: add if matches, and recurse if not direct_only
        for (direct_children.items) |entry| {
            const child_node = entry.node;
            const bound_child = node.g.bind(child_node);

            // Add to result if it matches the filter
            if (check_node_matches(bound_child, query)) {
                out.append(child_node) catch @panic("OOM");
            }

            // Recursively visit ALL children (regardless of match), if not direct_only
            if (!query.direct_only) {
                const down_query = ChildQuery{
                    .direct_only = false,
                    .types = query.types,
                    .include_root = false,
                    .sort = query.sort,
                    .required_traits = query.required_traits,
                };
                var child_results = EdgeComposition.get_children_query(bound_child, down_query, allocator);
                defer child_results.deinit();
                out.appendSlice(child_results.items) catch @panic("OOM");
            }
        }

        // Check and add root if requested
        if (query.include_root and check_node_matches(node, query)) {
            out.insert(0, node.node) catch @panic("OOM");
        }

        return out;
    }
};

test "basic" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(std.testing.allocator);

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();

    _ = try EdgeComposition.add_child(bn1, bn2.node, "child1");
    _ = try EdgeComposition.add_child(bn1, bn3.node, "child2");

    // has to be deleted first
    defer g.deinit();

    const parent_edge_bn2 = EdgeComposition.get_parent_edge(bn2);
    const parent_edge_bn3 = EdgeComposition.get_parent_edge(bn3);
    try std.testing.expect(EdgeComposition.get_parent_node(parent_edge_bn2.?.edge).is_same(bn1.node));
    try std.testing.expect(EdgeComposition.get_parent_node(parent_edge_bn3.?.edge).is_same(bn1.node));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(parent_edge_bn2.?.edge), "child1"));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(parent_edge_bn3.?.edge), "child2"));

    const CollectChildren = struct {
        child_edges: std.array_list.Managed(graph.BoundEdgeReference),

        pub fn visit(ctx: *anyopaque, child_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(ctx));
            self.child_edges.append(child_edge) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var visit = CollectChildren{ .child_edges = std.array_list.Managed(graph.BoundEdgeReference).init(a) };
    defer visit.child_edges.deinit();
    const result = EdgeComposition.visit_children_edges(bn1, void, &visit, CollectChildren.visit);

    try std.testing.expectEqual(result, visitor.VisitResult(void){ .EXHAUSTED = {} });
    try std.testing.expectEqual(visit.child_edges.items.len, 2);
    try std.testing.expect(EdgeComposition.get_child_node(visit.child_edges.items[0].edge).is_same(bn2.node));
    try std.testing.expect(EdgeComposition.get_child_node(visit.child_edges.items[1].edge).is_same(bn3.node));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(visit.child_edges.items[0].edge), "child1"));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(visit.child_edges.items[1].edge), "child2"));

    const bchild = EdgeComposition.get_child_by_identifier(bn1, "child1");
    try std.testing.expect(bchild.?.node.is_same(bn2.node));
}

test "add_child with null identifier" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const parent = g.create_and_insert_node();
    const child = g.create_and_insert_node();

    // When child_identifier is null, the edge name is empty string
    const edge = try EdgeComposition.add_child(parent, child.node, null);

    // Verify edge was created
    try std.testing.expect(EdgeComposition.is_instance(edge.edge));

    // Verify parent-child relationship
    try std.testing.expect(EdgeComposition.get_parent_node(edge.edge).is_same(parent.node));
    try std.testing.expect(EdgeComposition.get_child_node(edge.edge).is_same(child.node));

    // Verify name is empty string when null was passed
    const name = try EdgeComposition.get_name(edge.edge);
    try std.testing.expect(std.mem.eql(u8, name, ""));

    // Verify get_parent_edge works
    const parent_edge = EdgeComposition.get_parent_edge(child);
    try std.testing.expect(parent_edge != null);
    try std.testing.expect(parent_edge.?.edge.is_same(edge.edge));
}

test "get_children_query direct_only" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();

    // Create a hierarchy: parent -> child1, child2; child1 -> grandchild1
    const parent = g.create_and_insert_node();
    const child1 = g.create_and_insert_node();
    const child2 = g.create_and_insert_node();
    const grandchild1 = g.create_and_insert_node();

    _ = try EdgeComposition.add_child(parent, child1.node, "child1");
    _ = try EdgeComposition.add_child(parent, child2.node, "child2");
    _ = try EdgeComposition.add_child(child1, grandchild1.node, "grandchild1");

    // Test direct_only = true: should only return child1 and child2
    const query_direct = ChildQuery{
        .direct_only = true,
        .types = &[_]graph.NodeReference{},
        .include_root = false,
        .sort = false,
        .required_traits = &[_]graph.NodeReference{},
    };

    var direct_children = EdgeComposition.get_children_query(parent, query_direct, a);
    defer direct_children.deinit();

    try std.testing.expectEqual(@as(usize, 2), direct_children.items.len);
    // Both child1 and child2 should be in the result
    var found_child1 = false;
    var found_child2 = false;
    for (direct_children.items) |child| {
        if (child.is_same(child1.node)) found_child1 = true;
        if (child.is_same(child2.node)) found_child2 = true;
    }
    try std.testing.expect(found_child1);
    try std.testing.expect(found_child2);
}

test "get_children_query recursive" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();

    // Create a hierarchy: parent -> child1, child2; child1 -> grandchild1
    const parent = g.create_and_insert_node();
    const child1 = g.create_and_insert_node();
    const child2 = g.create_and_insert_node();
    const grandchild1 = g.create_and_insert_node();

    _ = try EdgeComposition.add_child(parent, child1.node, "child1");
    _ = try EdgeComposition.add_child(parent, child2.node, "child2");
    _ = try EdgeComposition.add_child(child1, grandchild1.node, "grandchild1");

    // Test direct_only = false: should return child1, child2, and grandchild1
    const query_recursive = ChildQuery{
        .direct_only = false,
        .types = &[_]graph.NodeReference{},
        .include_root = false,
        .sort = false,
        .required_traits = &[_]graph.NodeReference{},
    };

    var all_children = EdgeComposition.get_children_query(parent, query_recursive, a);
    defer all_children.deinit();

    try std.testing.expectEqual(@as(usize, 3), all_children.items.len);
    var found_child1 = false;
    var found_child2 = false;
    var found_grandchild1 = false;
    for (all_children.items) |child| {
        if (child.is_same(child1.node)) found_child1 = true;
        if (child.is_same(child2.node)) found_child2 = true;
        if (child.is_same(grandchild1.node)) found_grandchild1 = true;
    }
    try std.testing.expect(found_child1);
    try std.testing.expect(found_child2);
    try std.testing.expect(found_grandchild1);
}

test "get_children_query include_root" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();

    const parent = g.create_and_insert_node();
    const child1 = g.create_and_insert_node();

    _ = try EdgeComposition.add_child(parent, child1.node, "child1");

    // Test include_root = true
    const query_with_root = ChildQuery{
        .direct_only = true,
        .types = &[_]graph.NodeReference{},
        .include_root = true,
        .sort = false,
        .required_traits = &[_]graph.NodeReference{},
    };

    var children_with_root = EdgeComposition.get_children_query(parent, query_with_root, a);
    defer children_with_root.deinit();

    try std.testing.expectEqual(@as(usize, 2), children_with_root.items.len);
    var found_parent = false;
    var found_child1 = false;
    for (children_with_root.items) |child| {
        if (child.is_same(parent.node)) found_parent = true;
        if (child.is_same(child1.node)) found_child1 = true;
    }
    try std.testing.expect(found_parent);
    try std.testing.expect(found_child1);
}

test "get_children_query empty" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();

    const parent = g.create_and_insert_node();

    // Test with no children
    const query = ChildQuery{
        .direct_only = true,
        .types = &[_]graph.NodeReference{},
        .include_root = false,
        .sort = false,
        .required_traits = &[_]graph.NodeReference{},
    };

    var children = EdgeComposition.get_children_query(parent, query, a);
    defer children.deinit();

    try std.testing.expectEqual(@as(usize, 0), children.items.len);
}

test "get_children_query type filtering" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();
    var tg = TypeGraph.init(&g);

    // Build type graph with Electrical and Capacitor types
    const Electrical = try tg.add_type("Electrical");
    try tg.mark_constructable(Electrical);
    const Capacitor = try tg.add_type("Capacitor");
    _ = try tg.add_make_child(Capacitor, Electrical, "p1", null);
    _ = try tg.add_make_child(Capacitor, Electrical, "p2", null);
    try tg.mark_constructable(Capacitor);
    const Resistor = try tg.add_type("Resistor");
    _ = try tg.add_make_child(Resistor, Electrical, "rp1", null);
    _ = try tg.add_make_child(Resistor, Electrical, "rp2", null);
    _ = try tg.add_make_child(Resistor, Capacitor, "cap1", null);
    try tg.mark_constructable(Resistor);

    // Instantiate a Resistor (which has p1, p2 as Electrical and cap1 as Capacitor)
    const resistor = switch (tg.instantiate_node(Resistor)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };

    // Test: filter children by Electrical type only (should get rp1, rp2 but not cap1)
    const query_electrical = ChildQuery{
        .direct_only = true,
        .types = &[_]graph.NodeReference{Electrical.node},
        .include_root = false,
        .sort = false,
        .required_traits = &[_]graph.NodeReference{},
    };

    var electrical_children = EdgeComposition.get_children_query(resistor, query_electrical, a);
    defer electrical_children.deinit();

    try std.testing.expectEqual(@as(usize, 2), electrical_children.items.len);

    // Verify all results are Electrical type
    for (electrical_children.items) |child| {
        try std.testing.expect(EdgeType.is_node_instance_of(g.bind(child), Electrical.node));
    }

    // Test: filter children by Capacitor type only (should get only cap1)
    const query_capacitor = ChildQuery{
        .direct_only = true,
        .types = &[_]graph.NodeReference{Capacitor.node},
        .include_root = false,
        .sort = false,
        .required_traits = &[_]graph.NodeReference{},
    };

    var capacitor_children = EdgeComposition.get_children_query(resistor, query_capacitor, a);
    defer capacitor_children.deinit();

    try std.testing.expectEqual(@as(usize, 1), capacitor_children.items.len);
    try std.testing.expect(EdgeType.is_node_instance_of(g.bind(capacitor_children.items[0]), Capacitor.node));

    // Test: filter with multiple types (both Electrical and Capacitor - should get all 3)
    const query_both = ChildQuery{
        .direct_only = true,
        .types = &[_]graph.NodeReference{ Electrical.node, Capacitor.node },
        .include_root = false,
        .sort = false,
        .required_traits = &[_]graph.NodeReference{},
    };

    var both_children = EdgeComposition.get_children_query(resistor, query_both, a);
    defer both_children.deinit();

    try std.testing.expectEqual(@as(usize, 3), both_children.items.len);
}

test "get_children_query recursive with type filtering" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();
    var tg = TypeGraph.init(&g);

    // Build type graph: Resistor has a Capacitor child, Capacitor has Electrical children
    const Electrical = try tg.add_type("Electrical");
    try tg.mark_constructable(Electrical);
    const Capacitor = try tg.add_type("Capacitor");
    _ = try tg.add_make_child(Capacitor, Electrical, "p1", null);
    _ = try tg.add_make_child(Capacitor, Electrical, "p2", null);
    try tg.mark_constructable(Capacitor);
    const Resistor = try tg.add_type("Resistor");
    _ = try tg.add_make_child(Resistor, Capacitor, "cap1", null);
    try tg.mark_constructable(Resistor);

    // Instantiate a Resistor
    const resistor = switch (tg.instantiate_node(Resistor)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };

    // Test: recursively get all Electrical children (should find cap1.p1 and cap1.p2)
    const query_electrical_recursive = ChildQuery{
        .direct_only = false,
        .types = &[_]graph.NodeReference{Electrical.node},
        .include_root = false,
        .sort = false,
        .required_traits = &[_]graph.NodeReference{},
    };

    var electrical_recursive = EdgeComposition.get_children_query(resistor, query_electrical_recursive, a);
    defer electrical_recursive.deinit();

    // Should find the 2 Electrical children of the Capacitor (p1, p2)
    try std.testing.expectEqual(@as(usize, 2), electrical_recursive.items.len);
    for (electrical_recursive.items) |child| {
        try std.testing.expect(EdgeType.is_node_instance_of(g.bind(child), Electrical.node));
    }
}

test "get_children_query sorted" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();

    const parent = g.create_and_insert_node();
    const child1 = g.create_and_insert_node();
    const child2 = g.create_and_insert_node();
    const child3 = g.create_and_insert_node();

    // Insert in unsorted order: c, a, b
    _ = try EdgeComposition.add_child(parent, child3.node, "c");
    _ = try EdgeComposition.add_child(parent, child1.node, "a");
    _ = try EdgeComposition.add_child(parent, child2.node, "b");

    const query = ChildQuery{
        .direct_only = true,
        .types = &[_]graph.NodeReference{},
        .include_root = false,
        .sort = true,
        .required_traits = &[_]graph.NodeReference{},
    };

    var children = EdgeComposition.get_children_query(parent, query, a);
    defer children.deinit();

    try std.testing.expectEqual(@as(usize, 3), children.items.len);
    // Should be a, b, c (child1, child2, child3)
    try std.testing.expect(children.items[0].is_same(child1.node));
    try std.testing.expect(children.items[1].is_same(child2.node));
    try std.testing.expect(children.items[2].is_same(child3.node));
}
