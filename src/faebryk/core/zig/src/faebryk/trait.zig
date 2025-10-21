const graph = @import("graph").graph;
const visitor = @import("graph").visitor;
const typegraph_mod = @import("typegraph.zig");
const edgecomposition_mod = @import("composition.zig");
const node_type_mod = @import("node_type.zig");

const BoundNodeReference = graph.BoundNodeReference;
const TypeGraph = typegraph_mod.TypeGraph;
const EdgeType = node_type_mod.EdgeType;
const EdgeComposition = edgecomposition_mod.EdgeComposition;

pub const Trait = struct {
    pub fn add_trait_to(target: BoundNodeReference, trait_type: BoundNodeReference) !BoundNodeReference {
        var tg = TypeGraph.of_type(trait_type).?;
        const trait_instance = try tg.instantiate_node(trait_type);
        _ = EdgeComposition.add_child(target, trait_instance.node, null);
        return trait_instance;
    }

    pub fn try_get_trait(target: BoundNodeReference, trait_type: BoundNodeReference) ?BoundNodeReference {
        return EdgeComposition.try_get_single_child_of_type(target, trait_type.node);
    }

    pub fn visit_implementers(trait_type: BoundNodeReference, comptime T: type, ctx: *anyopaque, f: fn (*anyopaque, BoundNodeReference) visitor.VisitResult(T)) visitor.VisitResult(T) {
        const Visit = struct {
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, BoundNodeReference) visitor.VisitResult(T),

            pub fn visit(ctx_ptr: *anyopaque, bound_node: graph.BoundNodeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const trait_instance_parent = EdgeComposition.get_parent_node_of(bound_node) orelse return visitor.VisitResult(T){ .CONTINUE = {} };
                return self.cb(self.cb_ctx, trait_instance_parent);
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
