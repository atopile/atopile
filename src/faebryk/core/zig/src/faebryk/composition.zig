const graph_mod = @import("graph");
const std = @import("std");
const node_type_mod = @import("node_type.zig");
const edgebuilder_mod = @import("edgebuilder.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const EdgeType = node_type_mod.EdgeType;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;
const return_first = visitor.return_first;

pub const EdgeComposition = struct {
    pub const tid: Edge.EdgeType = 1759269250;

    pub fn init(allocator: std.mem.Allocator, parent: NodeReference, child: NodeReference, child_identifier: str) EdgeReference {
        const edge = Edge.init(allocator, parent, child, tid);

        build(child_identifier).apply_to(edge);
        return edge;
    }

    pub fn build(child_identifier: str) EdgeCreationAttributes {
        return .{
            .edge_type = tid,
            .directional = true,
            .name = child_identifier,
            .dynamic = null,
        };
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

    pub fn get_parent_node_of(bound_node: graph.BoundNodeReference) ?graph.BoundNodeReference {
        const parent_edge = EdgeComposition.get_parent_edge(bound_node) orelse return null;
        return parent_edge.g.bind(EdgeComposition.get_parent_node(parent_edge.edge));
    }

    pub fn add_child(bound_node: graph.BoundNodeReference, child: NodeReference, child_identifier: ?str) graph.BoundEdgeReference {
        // if child identifier is null, then generate a unique identifier
        const link = EdgeComposition.init(bound_node.g.allocator, bound_node.node, child, child_identifier orelse "");
        const bound_edge = bound_node.g.insert_edge(link);
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
};

pub const EdgeOperand = struct {
    pub const tid: Edge.EdgeType = 1760649153;

    pub fn init(
        allocator: std.mem.Allocator,
        expression: NodeReference,
        operand: NodeReference,
        operand_identifier: ?str,
    ) !EdgeReference {
        const edge = try Edge.init(allocator, expression, operand, tid);
        errdefer edge.deinit();

        edge.attributes.directional = true;
        edge.attributes.name = operand_identifier;
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_expression_node(E: EdgeReference) NodeReference {
        return E.source;
    }

    pub fn get_operand_node(E: EdgeReference) NodeReference {
        return E.target;
    }

    pub fn get_operand_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is_same(edge.target, node)) {
            return null;
        }
        return get_operand_node(edge);
    }

    pub fn get_expression_of(edge: EdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is_same(edge.source, node)) {
            return null;
        }
        return get_expression_node(edge);
    }

    pub fn visit_operand_edges(
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
                const operand = EdgeOperand.get_operand_of(bound_edge.edge, self.target.node);
                if (operand) |_| {
                    const operand_result = self.cb(self.cb_ctx, bound_edge);
                    switch (operand_result) {
                        .CONTINUE => {},
                        else => return operand_result,
                    }
                }
                return visitor.VisitResult(T){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .target = bound_node, .cb_ctx = ctx, .cb = f };
        return bound_node.visit_edges_of_type(tid, T, &visit, Visit.visit);
    }

    pub fn get_expression_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_node, tid, true);
    }

    pub fn add_operand(
        bound_node: graph.BoundNodeReference,
        operand: NodeReference,
        operand_identifier: ?str,
    ) !graph.BoundEdgeReference {
        const link = try EdgeOperand.init(
            bound_node.g.allocator,
            bound_node.node,
            operand,
            operand_identifier,
        );
        const bound_edge = try bound_node.g.insert_edge(link);
        return bound_edge;
    }

    pub fn get_name(edge: EdgeReference) !?str {
        if (!is_instance(edge)) {
            return error.InvalidEdgeType;
        }

        return edge.attributes.name;
    }

    pub fn get_operand_by_identifier(
        bound_expression_node: graph.BoundNodeReference,
        operand_identifier: str,
    ) ?graph.BoundNodeReference {
        const Finder = struct {
            identifier: str,

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(graph.BoundNodeReference) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                if (bound_edge.edge.attributes.name) |n| {
                    if (std.mem.eql(u8, n, self.identifier)) {
                        const target = bound_edge.edge.get_target() orelse {
                            return visitor.VisitResult(graph.BoundNodeReference){ .CONTINUE = {} };
                        };
                        return visitor.VisitResult(graph.BoundNodeReference){
                            .OK = bound_edge.g.bind(target),
                        };
                    }
                }
                return visitor.VisitResult(graph.BoundNodeReference){ .CONTINUE = {} };
            }
        };

        var finder = Finder{ .identifier = operand_identifier };
        const result = EdgeOperand.visit_operand_edges(
            bound_expression_node,
            graph.BoundNodeReference,
            &finder,
            Finder.visit,
        );
        switch (result) {
            .OK => |found| return found,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .ERROR => return null,
            .EXHAUSTED => return null,
        }
    }

    pub fn visit_operands_of_type(
        expression: graph.BoundNodeReference,
        operand_type: graph.NodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            expression: graph.BoundNodeReference,
            operand_type: graph.NodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const operand = bound_edge.g.bind(EdgeOperand.get_operand_node(bound_edge.edge));
                if (!EdgeType.is_node_instance_of(operand, self.operand_type)) {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }
                return self.cb(self.cb_ctx, bound_edge);
            }
        };

        var visit = Visit{
            .expression = expression,
            .operand_type = operand_type,
            .cb_ctx = ctx,
            .cb = f,
        };
        return expression.visit_edges_of_type(tid, T, &visit, Visit.visit);
    }
};

test "basic" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(std.testing.allocator);

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();

    _ = EdgeComposition.add_child(bn1, bn2.node, "child1");
    _ = EdgeComposition.add_child(bn1, bn3.node, "child2");

    // has to be deleted first
    defer g.deinit();

    const parent_edge_bn2 = EdgeComposition.get_parent_edge(bn2);
    const parent_edge_bn3 = EdgeComposition.get_parent_edge(bn3);
    try std.testing.expect(Node.is_same(EdgeComposition.get_parent_node(parent_edge_bn2.?.edge), bn1.node));
    try std.testing.expect(Node.is_same(EdgeComposition.get_parent_node(parent_edge_bn3.?.edge), bn1.node));
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
    try std.testing.expect(Node.is_same(EdgeComposition.get_child_node(visit.child_edges.items[0].edge), bn2.node));
    try std.testing.expect(Node.is_same(EdgeComposition.get_child_node(visit.child_edges.items[1].edge), bn3.node));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(visit.child_edges.items[0].edge), "child1"));
    try std.testing.expect(std.mem.eql(u8, try EdgeComposition.get_name(visit.child_edges.items[1].edge), "child2"));

    const bchild = EdgeComposition.get_child_by_identifier(bn1, "child1");
    try std.testing.expect(Node.is_same(bchild.?.node, bn2.node));
}

test "edge operand basic" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const expression = try Node.init(a);
    const operand_a = try Node.init(a);
    const operand_b = try Node.init(a);
    const operand_c = try Node.init(a);

    const b_expr = try g.insert_node(expression);
    const b_operand_a = try g.insert_node(operand_a);
    const b_operand_b = try g.insert_node(operand_b);
    const b_operand_c = try g.insert_node(operand_c);

    _ = try EdgeOperand.add_operand(b_expr, operand_a, "lhs");
    _ = try EdgeOperand.add_operand(b_expr, operand_b, "rhs");
    _ = try EdgeOperand.add_operand(b_expr, operand_c, null);

    const expression_edge_a = EdgeOperand.get_expression_edge(b_operand_a);
    const expression_edge_b = EdgeOperand.get_expression_edge(b_operand_b);
    const expression_edge_c = EdgeOperand.get_expression_edge(b_operand_c);
    try std.testing.expect(Node.is_same(
        EdgeOperand.get_expression_node(expression_edge_a.?.edge),
        expression,
    ));
    try std.testing.expect(Node.is_same(
        EdgeOperand.get_expression_node(expression_edge_b.?.edge),
        expression,
    ));
    try std.testing.expect(Node.is_same(
        EdgeOperand.get_expression_node(expression_edge_c.?.edge),
        expression,
    ));
    try std.testing.expect(std.mem.eql(u8, (try EdgeOperand.get_name(expression_edge_a.?.edge)).?, "lhs"));
    try std.testing.expect(std.mem.eql(u8, (try EdgeOperand.get_name(expression_edge_b.?.edge)).?, "rhs"));
    try std.testing.expect((try EdgeOperand.get_name(expression_edge_c.?.edge)) == null);

    const lhs_lookup = EdgeOperand.get_operand_by_identifier(b_expr, "lhs");
    const rhs_lookup = EdgeOperand.get_operand_by_identifier(b_expr, "rhs");
    try std.testing.expect(lhs_lookup != null);
    try std.testing.expect(rhs_lookup != null);
    try std.testing.expect(Node.is_same(lhs_lookup.?.node, operand_a));
    try std.testing.expect(Node.is_same(rhs_lookup.?.node, operand_b));

    const CollectOperands = struct {
        edges: std.ArrayList(graph.BoundEdgeReference),

        pub fn visit(ctx: *anyopaque, operand_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(ctx));
            self.edges.append(operand_edge) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var collector = CollectOperands{ .edges = std.ArrayList(graph.BoundEdgeReference).init(a) };
    defer collector.edges.deinit();
    const visit_result = EdgeOperand.visit_operand_edges(b_expr, void, &collector, CollectOperands.visit);
    try std.testing.expectEqual(visit_result, visitor.VisitResult(void){ .EXHAUSTED = {} });
    try std.testing.expectEqual(collector.edges.items.len, 3);
    try std.testing.expect(Node.is_same(EdgeOperand.get_operand_node(collector.edges.items[0].edge), operand_a));
    try std.testing.expect(Node.is_same(EdgeOperand.get_operand_node(collector.edges.items[1].edge), operand_b));
    try std.testing.expect(Node.is_same(EdgeOperand.get_operand_node(collector.edges.items[2].edge), operand_c));
}
