const graph = @import("graph.zig");
const std = @import("std");
const visitor = @import("visitor.zig");

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

pub const EdgeComposition = struct {
    var tid: ?Edge.Type = null;

    // pretty janky and not deterministic, for testing ok
    pub fn get_tid() Edge.Type {
        if (tid == null) {
            tid = Edge.register_type();
        }
        return tid.?;
    }

    pub fn init(allocator: std.mem.Allocator, parent: NodeReference, child: NodeReference, child_identifier: str) !EdgeReference {
        const edge = try Edge.init(allocator, parent, child, get_tid());
        edge.directional = true;
        edge.name = child_identifier;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, get_tid());
    }

    pub fn get_parent_node(E: EdgeReference) NodeReference {
        return E.from;
    }

    pub fn get_child_node(E: EdgeReference) NodeReference {
        return E.to;
    }
    fn get_child_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is(edge.to, node)) {
            return null;
        }
        return get_child_node(edge);
    }

    fn get_parent_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is(edge.from, node)) {
            return null;
        }
        return get_parent_node(edge);
    }

    pub fn visit_children_edges(
        bound_node: graph.BoundNodeReference,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),
    ) visitor.VisitResult(void) {
        const Visit = struct {
            target: graph.BoundNodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const child = EdgeComposition.get_child_of(bound_edge.edge, self.target.node);
                if (child) |_| {
                    const child_result = self.cb(self.cb_ctx, bound_edge);
                    switch (child_result) {
                        .CONTINUE => {},
                        else => return child_result,
                    }
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .target = bound_node, .cb_ctx = ctx, .cb = f };
        return GraphView.visit_edges_of_type(bound_node, get_tid(), void, &visit, Visit.visit);
    }

    pub fn get_parent_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        const Visit = struct {
            bound_node: graph.BoundNodeReference,

            pub fn visit(ctx: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(graph.BoundEdgeReference) {
                const self: *@This() = @ptrCast(@alignCast(ctx));
                const parent = EdgeComposition.get_parent_of(bound_edge.edge, self.bound_node.node);
                if (parent) |_| {
                    return visitor.VisitResult(graph.BoundEdgeReference){ .OK = bound_edge };
                }
                return visitor.VisitResult(graph.BoundEdgeReference){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .bound_node = bound_node };

        const result = GraphView.visit_edges_of_type(bound_node, get_tid(), graph.BoundEdgeReference, &visit, Visit.visit);
        switch (result) {
            .OK => return result.OK,
            .EXHAUSTED => return null,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => |err| @panic(@errorName(err)),
        }
    }

    pub fn add_child(bound_node: graph.BoundNodeReference, child: NodeReference, child_identifier: str) !graph.BoundEdgeReference {
        const link = try EdgeComposition.init(bound_node.g.allocator, bound_node.node, child, child_identifier);
        const bound_edge = try bound_node.g.insert_edge(link);
        return bound_edge;
    }

    pub fn get_name(edge: EdgeReference) !str {
        if (!is_instance(edge)) {
            return error.InvalidEdgeType;
        }

        return edge.name.?;
    }
};

test "basic" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(std.testing.allocator);
    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);

    const bn1 = try g.insert_node(n1);
    const bn2 = try g.insert_node(n2);
    const bn3 = try g.insert_node(n3);

    const be12 = try EdgeComposition.add_child(bn1, n2, "child1");
    const be13 = try EdgeComposition.add_child(bn1, n3, "child2");

    const parent_edge_bn2 = EdgeComposition.get_parent_edge(bn2);
    const parent_edge_bn3 = EdgeComposition.get_parent_edge(bn3);
    try std.testing.expect(Node.is(EdgeComposition.get_parent_node(parent_edge_bn2.?.edge), n1));
    try std.testing.expect(Node.is(EdgeComposition.get_parent_node(parent_edge_bn3.?.edge), n1));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(parent_edge_bn2.?.edge), "child1"));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(parent_edge_bn3.?.edge), "child2"));

    const CollectChildren = struct {
        child_edges: std.ArrayList(graph.BoundEdgeReference),

        pub fn visit(ctx: *anyopaque, child_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(ctx));
            self.child_edges.append(child_edge) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var visit = CollectChildren{ .child_edges = std.ArrayList(graph.BoundEdgeReference).init(a) };
    defer visit.child_edges.deinit();
    const result = EdgeComposition.visit_children_edges(bn1, &visit, CollectChildren.visit);

    try std.testing.expectEqual(result, visitor.VisitResult(void){ .EXHAUSTED = {} });
    try std.testing.expectEqual(visit.child_edges.items.len, 2);
    try std.testing.expect(Node.is(EdgeComposition.get_child_node(visit.child_edges.items[0].edge), n2));
    try std.testing.expect(Node.is(EdgeComposition.get_child_node(visit.child_edges.items[1].edge), n3));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(visit.child_edges.items[0].edge), "child1"));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(visit.child_edges.items[1].edge), "child2"));

    // cleanup
    g.deinit();
    try n1.deinit();
    try n2.deinit();
    try n3.deinit();
    try be12.edge.deinit();
    try be13.edge.deinit();
}
