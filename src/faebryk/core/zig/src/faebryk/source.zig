const graph_mod = @import("graph");
const std = @import("std");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;

pub const EdgeSource = struct {
    pub const tid: Edge.EdgeType = 0x68DC5A00;

    pub fn get_tid() Edge.EdgeType {
        return tid;
    }

    pub fn init(allocator: std.mem.Allocator, node: NodeReference, source_node: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, node, source_node, tid);
        edge.attributes.directional = true;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn add_source(bound_node: graph.BoundNodeReference, source_node: NodeReference) !graph.BoundEdgeReference {
        const link = try EdgeSource.init(bound_node.g.allocator, bound_node.node, source_node);
        return try bound_node.g.insert_edge(link);
    }

    pub fn get_subject_node(E: EdgeReference) ?NodeReference {
        return Edge.get_source(E);
    }

    pub fn get_source_node(E: EdgeReference) ?NodeReference {
        return Edge.get_target(E);
    }

    pub fn get_source_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_node, tid, false);
    }

    pub fn visit_source_edges(
        bound_node: graph.BoundNodeReference,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),
    ) visitor.VisitResult(void) {
        const Visit = struct {
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const source_node = EdgeSource.get_source_node(bound_edge.edge);
                if (source_node) |_| {
                    const result = self.cb(self.cb_ctx, bound_edge);
                    switch (result) {
                        .CONTINUE => {},
                        else => return result,
                    }
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .cb_ctx = ctx, .cb = f };
        return bound_node.visit_edges_of_type(tid, void, &visit, Visit.visit);
    }
};
