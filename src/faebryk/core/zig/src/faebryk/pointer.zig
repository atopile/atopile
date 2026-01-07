const graph_mod = @import("graph");
const std = @import("std");
const composition_mod = @import("composition.zig");
const edgebuilder_mod = @import("edgebuilder.zig");
const typegraph_mod = @import("typegraph.zig");

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
const TypeGraph = typegraph_mod.TypeGraph;

pub const EdgePointer = struct {
    pub const tid: Edge.EdgeType = graph.Edge.hash_edge_type(1759771470);
    pub var registered: bool = false;

    /// Create an EdgeTraversal for dereferencing the current Pointer node.
    /// No identifier needed - simply follows the EdgePointer from the current node to its target.
    pub fn traverse() TypeGraph.ChildReferenceNode.EdgeTraversal {
        return .{ .identifier = "", .edge_type = tid };
    }

    pub fn init(from: NodeReference, to: NodeReference, identifier: ?str, index: ?u15) EdgeReference {
        const edge = EdgeReference.init(from, to, tid);
        build(identifier, index).apply_to(edge);
        return edge;
    }

    /// Build EdgeCreationAttributes for an EdgePointer.
    /// The 15-bit index is split MSB-first: `order` gets high 7 bits, `edge_specific` gets low 8 bits.
    pub fn build(identifier: ?str, index: ?u15) EdgeCreationAttributes {
        if (!registered) {
            @branchHint(.unlikely);
            registered = true;
            Edge.register_type(tid) catch {};
        }

        return .{
            .edge_type = tid,
            .directional = true,
            .name = identifier,
            .order = if (index) |i| @intCast(i >> 8) else 0,
            .edge_specific = if (index) |i| @as(u16, i & 0xFF) else null,
            .dynamic = graph.DynamicAttributes.init_on_stack(),
        };
    }

    /// Reconstruct the 15-bit index from order (high 7 bits) and edge_specific (low 8 bits).
    pub fn get_index(edge: EdgeReference) ?u15 {
        const low = edge.get_edge_specific() orelse return null;
        const high: u15 = @intCast(edge.get_order());
        return (high << 8) | @as(u15, @intCast(low & 0xFF));
    }

    pub fn get_referenced_node(edge: EdgeReference) NodeReference {
        return edge.get_directed_target().?;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return E.is_instance(tid);
    }

    pub fn point_to(bound_node: BoundNodeReference, target_node: NodeReference, identifier: ?str, index: ?u15) BoundEdgeReference {
        const edge = EdgePointer.init(bound_node.node, target_node, identifier, index);
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
        // directed = true: from is source, to is target
        return bound_node.g.visit_edges_of_type(bound_node.node, tid, T, &visit, Visit.visit, true);
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
                // Direction filtering is handled by visit_pointed_edges with directed=true
                if (bound_edge.edge.get_attribute_name()) |name| {
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
                const target = EdgePointer.get_referenced_node(bound_edge.edge);
                return visitor.VisitResult(BoundNodeReference){ .OK = bound_edge.g.bind(target) };
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
                const target = EdgePointer.get_referenced_node(edge.edge);
                break :blk edge.g.bind(target);
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
    const e12 = EdgePointer.init(n1.node, n2.node, null, 0);

    _ = g.insert_edge(e12);

    try std.testing.expect(EdgePointer.is_instance(e12));
    try std.testing.expect(EdgePointer.get_referenced_node(e12).is_same(n2.node));

    g.deinit();
}
