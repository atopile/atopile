const graph = @import("graph").graph;
const visitor = @import("graph").visitor;
const typegraph_mod = @import("typegraph.zig");
const edgecomposition_mod = @import("composition.zig");
const node_type_mod = @import("node_type.zig");
const edgebuilder_mod = @import("edgebuilder.zig");
const std = @import("std");
const EdgeType = node_type_mod.EdgeType;
const Edge = graph.Edge;
const BoundNodeReference = graph.BoundNodeReference;
const TypeGraph = typegraph_mod.TypeGraph;
const EdgeComposition = edgecomposition_mod.EdgeComposition;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;
const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Node = graph.Node;
const return_first = visitor.return_first;

pub const Trait = struct {
    pub fn add_trait_to(target: BoundNodeReference, trait_type: BoundNodeReference) !BoundNodeReference {
        var tg = TypeGraph.of_type(trait_type).?;
        const trait_instance = switch (tg.instantiate_node(trait_type)) {
            .ok => |n| n,
            .err => return error.InstantiationFailed,
        };
        _ = try EdgeTrait.add_trait_instance(target, trait_instance.node);
        return trait_instance;
    }

    pub fn add_trait_instance_to(target: BoundNodeReference, trait_instance: BoundNodeReference) !BoundNodeReference {
        _ = try EdgeTrait.add_trait_instance(target, trait_instance.node);
        return trait_instance;
    }

    pub fn mark_as_trait(trait_type: BoundNodeReference) !void {
        var tg = TypeGraph.of_type(trait_type) orelse return error.TypeGraphNotFound;
        const impl_trait = switch (tg.instantiate_node(tg.get_ImplementsTrait())) {
            .ok => |n| n,
            .err => return error.InstantiationFailed,
        };
        _ = try EdgeTrait.add_trait_instance(trait_type, impl_trait.node);
    }

    pub fn try_get_trait(target: BoundNodeReference, trait_type: BoundNodeReference) ?BoundNodeReference {
        return EdgeTrait.try_get_trait_instance_of_type(target, trait_type.node);
    }

    /// Batch lookup of multiple traits on a target node.
    /// Returns a slice of optional BoundNodeReferences, one for each input trait type.
    /// Caller must free the returned slice.
    pub fn try_get_traits(
        allocator: std.mem.Allocator,
        target: BoundNodeReference,
        trait_types: []const graph.NodeReference,
    ) []?BoundNodeReference {
        const results = allocator.alloc(?BoundNodeReference, trait_types.len) catch @panic("OOM");
        for (trait_types, 0..) |trait_type, i| {
            results[i] = EdgeTrait.try_get_trait_instance_of_type(target, trait_type);
        }
        return results;
    }

    pub fn visit_implementers(trait_type: BoundNodeReference, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundNodeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
        const Visit = struct {
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, BoundNodeReference) visitor.VisitResult(T),

            pub fn visit(ctx_ptr: *anyopaque, bound_node: graph.BoundNodeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const trait_instance_owner = EdgeTrait.get_owner_node_of(bound_node) orelse return visitor.VisitResult(T){ .CONTINUE = {} };
                return self.cb(self.cb_ctx, trait_instance_owner);
            }
        };

        var visit = Visit{ .cb_ctx = ctx, .cb = f };
        return visit_implementations(trait_type, T, &visit, Visit.visit);
    }

    pub fn visit_implementations(trait_type: BoundNodeReference, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundNodeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
        const Visit = struct {
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, BoundNodeReference) visitor.VisitResult(T),

            pub fn visit(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const trait_instance = bound_edge.g.bind(EdgeType.get_instance_node(bound_edge.edge).?);
                return self.cb(self.cb_ctx, trait_instance);
            }
        };

        var visit = Visit{ .cb_ctx = ctx, .cb = f };
        return EdgeType.visit_instance_edges(trait_type, &visit, Visit.visit);
    }
};

pub const EdgeTrait = struct {
    pub const tid: Edge.EdgeType = graph.Edge.hash_edge_type(1762883874);
    pub var registered: bool = false;

    /// Create an EdgeTraversal for finding a trait instance by its type name.
    pub fn traverse(trait_type_name: graph.str) TypeGraph.ChildReferenceNode.EdgeTraversal {
        return .{ .identifier = trait_type_name, .edge_type = tid };
    }

    pub fn get_tid() Edge.EdgeType {
        return tid;
    }

    pub fn init(owner: NodeReference, trait_instance: NodeReference) EdgeReference {
        const edge = EdgeReference.init(owner, trait_instance, tid);

        build().apply_to(edge);
        return edge;
    }

    pub fn build() EdgeCreationAttributes {
        if (!registered) {
            @branchHint(.unlikely);
            registered = true;
            Edge.register_type(tid) catch {};
        }
        return .{
            .edge_type = tid,
            .directional = true,
            .name = null,
            .dynamic = graph.DynamicAttributes.init_on_stack(),
        };
    }

    pub fn is_instance(E: EdgeReference) bool {
        return E.is_instance(tid);
    }

    pub fn get_owner_node(E: EdgeReference) NodeReference {
        return E.get_source_node();
    }

    pub fn get_trait_instance_node(E: EdgeReference) NodeReference {
        return E.get_target_node();
    }

    pub fn get_trait_instance_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (edge.get_target_node().is_same(node)) {
            return null;
        }
        return get_trait_instance_node(edge);
    }

    pub fn get_owner_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (edge.get_source_node().is_same(node)) {
            return null;
        }
        return get_owner_node(edge);
    }

    pub fn visit_trait_instance_edges(
        bound_node: graph.BoundNodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        // directed = true: owner is source, trait_instance is target
        return bound_node.g.visit_edges_of_type(bound_node.node, tid, T, ctx, f, true);
    }

    pub fn get_owner_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        // traits can have traits as owners, so we need to check both directions
        return bound_node.get_single_edge(tid, true);
    }

    pub fn get_owner_node_of(bound_node: graph.BoundNodeReference) ?graph.BoundNodeReference {
        const owner_edge = EdgeTrait.get_owner_edge(bound_node) orelse return null;
        return owner_edge.g.bind(EdgeTrait.get_owner_node(owner_edge.edge));
    }

    pub fn add_trait_instance(bound_node: graph.BoundNodeReference, trait_instance: NodeReference) graph.GraphView.InsertEdgeError!graph.BoundEdgeReference {
        // add existing trait instance to owner node
        const link = EdgeTrait.init(bound_node.node, trait_instance);
        return bound_node.g.insert_edge(link);
    }

    // TODO this is wayyyyy to slow for how often we use it
    pub fn visit_trait_instances_of_type(
        owner: graph.BoundNodeReference,
        trait_type: graph.NodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            owner: graph.BoundNodeReference,
            trait_type: graph.NodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const trait_instance = bound_edge.g.bind(EdgeTrait.get_trait_instance_node(bound_edge.edge));
                if (!EdgeType.is_node_instance_of(trait_instance, self.trait_type)) {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }
                return self.cb(self.cb_ctx, bound_edge);
            }
        };

        var visit = Visit{ .owner = owner, .trait_type = trait_type, .cb_ctx = ctx, .cb = f };
        // directed = true: owner is source, trait_instance is target
        return owner.g.visit_edges_of_type(owner.node, tid, T, &visit, Visit.visit, true);
    }

    pub fn try_get_trait_instance_of_type(bound_node: graph.BoundNodeReference, trait_type: graph.NodeReference) ?graph.BoundNodeReference {
        const Ctx = struct {};
        var ctx = Ctx{};
        const result = EdgeTrait.visit_trait_instances_of_type(bound_node, trait_type, graph.BoundEdgeReference, &ctx, return_first(graph.BoundEdgeReference).visit);
        switch (result) {
            .OK => |found| return found.g.bind(EdgeTrait.get_trait_instance_node(found.edge)),
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => return null, // Convert error to null since function returns optional
            .EXHAUSTED => return null,
        }
    }

    pub fn try_get_trait_instance_by_identifier(bound_node: graph.BoundNodeReference, identifier: graph.str) ?graph.BoundNodeReference {
        const Finder = struct {
            identifier: graph.str,

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(graph.BoundNodeReference) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                // Skip trait edges without a name - only match by identifier if name is set
                const edge_name = bound_edge.edge.get_attribute_name() orelse return visitor.VisitResult(graph.BoundNodeReference){ .CONTINUE = {} };
                if (std.mem.eql(u8, edge_name, self.identifier)) {
                    return visitor.VisitResult(graph.BoundNodeReference){ .OK = bound_edge.g.bind(EdgeTrait.get_trait_instance_node(bound_edge.edge)) };
                }
                return visitor.VisitResult(graph.BoundNodeReference){ .CONTINUE = {} };
            }
        };

        var finder = Finder{ .identifier = identifier };
        const result = EdgeTrait.visit_trait_instance_edges(bound_node, graph.BoundNodeReference, &finder, Finder.visit);
        return switch (result) {
            .OK => |found| found,
            .CONTINUE => null,
            .STOP => null,
            .ERROR => null,
            .EXHAUSTED => null,
        };
    }
};

//zig test --dep graph -Mroot=src/faebryk/trait.zig -Mgraph=src/graph/lib.zig
test "basic" {
    var g = graph.GraphView.init(std.testing.allocator);
    var tg = TypeGraph.init(&g);

    const trait_type = try tg.add_type("ExampleTrait");
    try tg.mark_constructable(trait_type);
    const trait_type2 = try tg.add_type("ExampleTrait2");
    try tg.mark_constructable(trait_type2);
    const bn1 = g.create_and_insert_node();

    const implements_type_node = tg.get_ImplementsType();
    const implements_type_instance = EdgeTrait.try_get_trait_instance_of_type(implements_type_node, implements_type_node.node) orelse unreachable;
    try std.testing.expect(EdgeType.is_node_instance_of(implements_type_instance, implements_type_node.node));

    _ = try Trait.add_trait_to(bn1, trait_type);
    const trait_instance_recall_1 = EdgeTrait.try_get_trait_instance_of_type(bn1, trait_type.node);
    try std.testing.expect(EdgeTrait.get_owner_node_of(trait_instance_recall_1.?).?.node.is_same(bn1.node));

    const trait_instance2 = switch (tg.instantiate_node(trait_type2)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    _ = try Trait.add_trait_instance_to(bn1, trait_instance2);
    const trait_instance_recall_2 = EdgeTrait.try_get_trait_instance_of_type(bn1, trait_type2.node);
    try std.testing.expect(EdgeTrait.get_owner_node_of(trait_instance_recall_2.?).?.node.is_same(bn1.node));
    try std.testing.expect(trait_instance_recall_2.?.node.is_same(trait_instance2.node));

    // has to be deleted firstb
    defer g.deinit();
}
