const graph_mod = @import("graph");
const std = @import("std");
const pointer_mod = @import("pointer.zig");
const composition_mod = @import("composition.zig");
const typegraph_mod = @import("typegraph.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const GraphView = graph.GraphView;
const BoundNodeReference = graph.BoundNodeReference;
const EdgePointer = pointer_mod.EdgePointer;
const EdgeComposition = composition_mod.EdgeComposition;
const TypeGraph = typegraph_mod.TypeGraph;

const LinkerError = error{ TypeReferenceNotInGraph, TargetTypeNotInGraph, SourceNodeNotInGraph, TargetNodeNotInGraph };

pub const Linker = struct {
    pub const Error = LinkerError;

    const resolved_identifier = "resolved";

    pub fn link_type_reference(g: *GraphView, type_reference: BoundNodeReference, target_type: BoundNodeReference) Error!void {
        if (type_reference.g != g) {
            return Error.TypeReferenceNotInGraph;
        }

        if (target_type.g != g) {
            return Error.TargetTypeNotInGraph;
        }

        _ = try EdgePointer.point_to(type_reference, target_type.node, resolved_identifier, null);
    }

    pub fn try_get_resolved_type(type_reference: BoundNodeReference) ?BoundNodeReference {
        return EdgePointer.get_pointed_node_by_identifier(type_reference, resolved_identifier);
    }

    /// Update an existing type reference to point to a new target type.
    /// If no existing "resolved" edge exists, creates one (same as link_type_reference).
    pub fn update_type_reference(g: *GraphView, type_reference: BoundNodeReference, target_type: BoundNodeReference) Error!void {
        if (type_reference.g != g) {
            return Error.TypeReferenceNotInGraph;
        }
        if (target_type.g != g) {
            return Error.TargetTypeNotInGraph;
        }

        if (get_existing_resolved_edge(type_reference)) |existing_edge| {
            existing_edge.edge.set_target_node(target_type.node);
        } else {
            _ = try EdgePointer.point_to(type_reference, target_type.node, resolved_identifier, null);
        }
    }

    fn get_existing_resolved_edge(type_reference: BoundNodeReference) ?graph.BoundEdgeReference {
        const Finder = struct {
            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(graph.BoundEdgeReference) {
                _ = self_ptr;
                return visitor.VisitResult(graph.BoundEdgeReference){ .OK = bound_edge };
            }
        };
        var finder = Finder{};
        const result = EdgePointer.visit_pointed_edges_with_identifier(
            type_reference,
            resolved_identifier,
            graph.BoundEdgeReference,
            &finder,
            Finder.visit,
        );
        return switch (result) {
            .OK => result.OK,
            else => null,
        };
    }

    pub const UnresolvedTypeReference = struct {
        type_node: BoundNodeReference,
        type_reference: BoundNodeReference,
    };

    pub fn collect_unresolved_type_references(type_graph: *TypeGraph, allocator: std.mem.Allocator) []UnresolvedTypeReference {
        var list = std.ArrayList(UnresolvedTypeReference).init(allocator);
        errdefer list.deinit();

        const VisitMakeChildren = struct {
            type_graph: *TypeGraph,
            type_node: BoundNodeReference,
            list: *std.ArrayList(UnresolvedTypeReference),

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));
                const make_child = edge.g.bind(EdgeComposition.get_child_node(edge.edge));
                const type_reference = TypeGraph.MakeChildNode.get_type_reference(make_child);

                if (try_get_resolved_type(type_reference) == null) {
                    ctx.list.append(.{ .type_node = ctx.type_node, .type_reference = type_reference }) catch |err| switch (err) {
                        error.OutOfMemory => @panic("OOM"),
                    };
                }

                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        const VisitTypes = struct {
            type_graph: *TypeGraph,
            list: *std.ArrayList(UnresolvedTypeReference),

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));
                const type_node = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                var make_children_ctx = VisitMakeChildren{ .type_graph = ctx.type_graph, .type_node = type_node, .list = ctx.list };

                const result = EdgeComposition.visit_children_of_type(
                    type_node,
                    ctx.type_graph.get_MakeChild().node,
                    void,
                    &make_children_ctx,
                    VisitMakeChildren.visit,
                );

                switch (result) {
                    .ERROR => |err| return visitor.VisitResult(void){ .ERROR = err },
                    else => return visitor.VisitResult(void){ .CONTINUE = {} },
                }
            }
        };

        var visit_ctx = VisitTypes{ .type_graph = type_graph, .list = &list };
        const visit_result = EdgeComposition.visit_children_edges(type_graph.self_node, void, &visit_ctx, VisitTypes.visit);

        switch (visit_result) {
            .ERROR => |err| switch (err) {
                error.OutOfMemory => @panic("OOM"),
                else => unreachable,
            },
            else => {},
        }

        return list.toOwnedSlice() catch @panic("OOM");
    }
};
