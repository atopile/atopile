const graph_mod = @import("graph");
const std = @import("std");
const composition_mod = @import("composition.zig");
const edgebuilder_mod = @import("edgebuilder.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const BoundNodeReference = graph.BoundNodeReference;
const BoundEdgeReference = graph.BoundEdgeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;
const EdgeComposition = composition_mod.EdgeComposition;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;
const return_first = visitor.return_first;

pub const EdgePointer = struct {
    pub const tid: Edge.EdgeType = 1759771470;

    pub fn init(allocator: std.mem.Allocator, from: NodeReference, to: NodeReference, identifier: ?str) EdgeReference {
        const edge = Edge.init(allocator, from, to, tid);
        build(identifier).apply_to(edge);
        return edge;
    }

    pub fn build(identifier: ?str) EdgeCreationAttributes {
        return .{
            .edge_type = tid,
            .directional = true,
            .name = identifier,
            .dynamic = null,
        };
    }

    pub fn get_referenced_node(edge: EdgeReference) ?NodeReference {
        return edge.get_target();
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn point_to(bound_node: BoundNodeReference, target_node: NodeReference, identifier: ?str) BoundEdgeReference {
        const edge = EdgePointer.init(bound_node.g.allocator, bound_node.node, target_node, identifier);
        const bound_edge = bound_node.g.insert_edge(edge);
        return bound_edge;
    }

    pub fn visit_pointed_edges(
        bound_node: BoundNodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                return self.cb(self.cb_ctx, bound_edge);
            }
        };

        var visit = Visit{ .cb_ctx = ctx, .cb = f };
        return bound_node.visit_edges_of_type(tid, T, &visit, Visit.visit);
    }

    pub fn visit_pointed_edges_with_identifier(
        bound_node: BoundNodeReference,
        identifier: str,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            identifier: str,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, BoundEdgeReference) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                if (bound_edge.edge.attributes.name) |name| {
                    if (!std.mem.eql(u8, name, self.identifier)) {
                        return visitor.VisitResult(T){ .CONTINUE = {} };
                    }
                } else {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }
                return self.cb(self.cb_ctx, bound_edge);
            }
        };

        var visit = Visit{ .identifier = identifier, .cb_ctx = ctx, .cb = f };
        return EdgePointer.visit_pointed_edges(bound_node, T, &visit, Visit.visit);
    }

    // TODO: should be removed/renamed, assumes single connection
    pub fn get_pointed_node_by_identifier(bound_node: BoundNodeReference, identifier: str) ?BoundNodeReference {
        const Finder = struct {
            identifier: str,

            pub fn visit(self_ptr: *anyopaque, bound_edge: BoundEdgeReference) visitor.VisitResult(BoundNodeReference) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                _ = self;
                if (EdgePointer.get_referenced_node(bound_edge.edge)) |target| {
                    return visitor.VisitResult(BoundNodeReference){ .OK = bound_edge.g.bind(target) };
                }
                return visitor.VisitResult(BoundNodeReference){ .CONTINUE = {} };
            }
        };

        var finder = Finder{ .identifier = identifier };
        const result = EdgePointer.visit_pointed_edges_with_identifier(bound_node, identifier, BoundNodeReference, &finder, Finder.visit);
        switch (result) {
            .OK => return result.OK,
            .EXHAUSTED => return null,
            .ERROR => return null,
            .CONTINUE => unreachable,
            .STOP => unreachable,
        }
    }

    // TODO: should be removed/renamed, assumes single connection
    pub fn get_referenced_node_from_node(bound_reference_node: BoundNodeReference) ?BoundNodeReference {
        const Ctx = struct {};
        var ctx = Ctx{};
        const result = EdgePointer.visit_pointed_edges(bound_reference_node, BoundEdgeReference, &ctx, return_first(BoundEdgeReference).visit);
        return switch (result) {
            .OK => |edge| blk: {
                if (EdgePointer.get_referenced_node(edge.edge)) |target| {
                    break :blk edge.g.bind(target);
                }
                break :blk null;
            },
            .EXHAUSTED => null,
            .ERROR => null,
            .CONTINUE => unreachable,
            .STOP => unreachable,
        };
    }
};

//zig test --dep graph -Mroot=src/faebryk/pointer.zig -Mgraph=src/graph/lib.zig
test "basic" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);

    const n1 = g.create_and_insert_node();
    const n2 = g.create_and_insert_node();
    const e12 = EdgePointer.init(a, n1.node, n2.node, null);

    _ = g.insert_edge(e12);

    try std.testing.expect(EdgePointer.is_instance(e12));
    try std.testing.expect(Node.is_same(EdgePointer.get_referenced_node(e12).?, n2.node));

    g.deinit();
}
