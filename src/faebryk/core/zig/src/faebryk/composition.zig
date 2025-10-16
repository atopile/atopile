const graph_mod = @import("graph");
const std = @import("std");
const node_type_mod = @import("node_type.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const EdgeType = node_type_mod.EdgeType;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

pub const EdgeComposition = struct {
    pub const tid: Edge.EdgeType = 1759269250;

    pub fn init(allocator: std.mem.Allocator, parent: NodeReference, child: NodeReference, child_identifier: str) !EdgeReference {
        const edge = try Edge.init(allocator, parent, child, tid);
        errdefer edge.deinit();

        edge.attributes.directional = true;
        edge.attributes.name = child_identifier;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_parent_node(E: EdgeReference) NodeReference {
        return E.source;
    }

    pub fn get_child_node(E: EdgeReference) NodeReference {
        return E.target;
    }

    pub fn get_child_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is_same(edge.target, node)) {
            return null;
        }
        return get_child_node(edge);
    }

    pub fn get_parent_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is_same(edge.source, node)) {
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
        return bound_node.visit_edges_of_type(tid, T, &visit, Visit.visit);
    }

    pub fn get_parent_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_node, tid, true);
    }

    pub fn add_child(bound_node: graph.BoundNodeReference, child: NodeReference, child_identifier: ?str) !graph.BoundEdgeReference {
        // if child identifier is null, then generate a unique identifier
        const link = try EdgeComposition.init(bound_node.g.allocator, bound_node.node, child, child_identifier orelse "");
        const bound_edge = try bound_node.g.insert_edge(link);
        return bound_edge;
    }

    pub fn get_name(edge: EdgeReference) !str {
        if (!is_instance(edge)) {
            return error.InvalidEdgeType;
        }

        return edge.attributes.name.?;
    }

    pub fn get_child_by_identifier(bound_parent_node: graph.BoundNodeReference, child_identifier: str) ?graph.BoundNodeReference {
        const Finder = struct {
            identifier: str,

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(graph.BoundNodeReference) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                if (bound_edge.edge.attributes.name) |n| {
                    if (std.mem.eql(u8, n, self.identifier)) {
                        const target = bound_edge.edge.get_target() orelse return visitor.VisitResult(graph.BoundNodeReference){ .CONTINUE = {} };
                        return visitor.VisitResult(graph.BoundNodeReference){ .OK = bound_edge.g.bind(target) };
                    }
                }
                return visitor.VisitResult(graph.BoundNodeReference){ .CONTINUE = {} };
            }
        };

        var finder = Finder{ .identifier = child_identifier };
        const result = EdgeComposition.visit_children_edges(bound_parent_node, graph.BoundNodeReference, &finder, Finder.visit);
        switch (result) {
            .OK => |found| return found,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => return null, // Convert error to null since function returns optional
            .EXHAUSTED => return null,
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
        return parent.visit_edges_of_type(tid, T, &visit, Visit.visit);
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

    _ = try EdgeComposition.add_child(bn1, n2, "child1");
    _ = try EdgeComposition.add_child(bn1, n3, "child2");

    // has to be deleted first
    defer g.deinit();

    const parent_edge_bn2 = EdgeComposition.get_parent_edge(bn2);
    const parent_edge_bn3 = EdgeComposition.get_parent_edge(bn3);
    try std.testing.expect(Node.is_same(EdgeComposition.get_parent_node(parent_edge_bn2.?.edge), n1));
    try std.testing.expect(Node.is_same(EdgeComposition.get_parent_node(parent_edge_bn3.?.edge), n1));
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
    const result = EdgeComposition.visit_children_edges(bn1, void, &visit, CollectChildren.visit);

    try std.testing.expectEqual(result, visitor.VisitResult(void){ .EXHAUSTED = {} });
    try std.testing.expectEqual(visit.child_edges.items.len, 2);
    try std.testing.expect(Node.is_same(EdgeComposition.get_child_node(visit.child_edges.items[0].edge), n2));
    try std.testing.expect(Node.is_same(EdgeComposition.get_child_node(visit.child_edges.items[1].edge), n3));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(visit.child_edges.items[0].edge), "child1"));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(visit.child_edges.items[1].edge), "child2"));

    const bchild = EdgeComposition.get_child_by_identifier(bn1, "child1");
    try std.testing.expect(Node.is_same(bchild.?.node, n2));
}
