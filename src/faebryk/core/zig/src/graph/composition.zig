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

    pub fn get_child(E: EdgeReference) NodeReference {
        return E.to;
    }

    fn get_child_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is(edge.to, node)) {
            return null;
        }
        return edge.to;
    }

    fn get_parent_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is(edge.from, node)) {
            return null;
        }
        return edge.from;
    }

    pub fn visit_children(
        bound_node: graph.BoundNodeReference,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, NodeReference) visitor.VisitResult(void),
    ) visitor.VisitResult(void) {
        const Visit = struct {
            target: graph.BoundNodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, NodeReference) visitor.VisitResult(void),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const child = EdgeComposition.get_child_of(bound_edge.edge, self.target.node);
                if (child) |c| {
                    const child_result = self.cb(self.cb_ctx, c);
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

    pub fn get_parent(bound_node: graph.BoundNodeReference) ?NodeReference {
        const Visit = struct {
            bound_node: graph.BoundNodeReference,

            pub fn visit(ctx: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(NodeReference) {
                const self: *@This() = @ptrCast(@alignCast(ctx));
                const parent = EdgeComposition.get_parent_of(bound_edge.edge, self.bound_node.node);
                if (parent) |p| {
                    return visitor.VisitResult(NodeReference){ .OK = p };
                }
                return visitor.VisitResult(NodeReference){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .bound_node = bound_node };

        const result = GraphView.visit_edges_of_type(bound_node, get_tid(), NodeReference, &visit, Visit.visit);
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

    const parent_bn2 = EdgeComposition.get_parent(bn2);
    const parent_bn3 = EdgeComposition.get_parent(bn3);
    try std.testing.expect(Node.is(parent_bn2.?, n1));
    try std.testing.expect(Node.is(parent_bn3.?, n1));

    const CollectChildren = struct {
        children: std.ArrayList(NodeReference),

        pub fn visit(ctx: *anyopaque, child: NodeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(ctx));
            self.children.append(child) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var visit = CollectChildren{ .children = std.ArrayList(NodeReference).init(a) };
    defer visit.children.deinit();
    const result = EdgeComposition.visit_children(bn1, &visit, CollectChildren.visit);

    try std.testing.expectEqual(result, visitor.VisitResult(void){ .EXHAUSTED = {} });
    try std.testing.expectEqual(visit.children.items.len, 2);
    try std.testing.expect(Node.is(visit.children.items[0], n2));
    try std.testing.expect(Node.is(visit.children.items[1], n3));

    // cleanup
    g.deinit();
    try n1.deinit();
    try n2.deinit();
    try n3.deinit();
    try be12.edge.deinit();
    try be13.edge.deinit();
}
