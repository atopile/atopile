const graph_mod = @import("graph");
const std = @import("std");
const edgebuilder_mod = @import("edgebuilder.zig");
const node_type_mod = @import("node_type.zig");
const composition_mod = @import("composition.zig");
const typegraph_mod = @import("typegraph.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const Edge = graph.Edge;
const Node = graph.Node;
const EdgeReference = graph.EdgeReference;
const NodeReference = graph.NodeReference;
const str = graph.str;
const EdgeType = node_type_mod.EdgeType;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;
const EdgeComposition = composition_mod.EdgeComposition;
const TypeGraph = typegraph_mod.TypeGraph;

pub const EdgeOperand = struct {
    pub const tid: Edge.EdgeType = graph.Edge.hash_edge_type(1760649153);
    pub var registered: bool = false;

    /// Create an EdgeTraversal for finding an operand by identifier.
    pub fn traverse(identifier: str) TypeGraph.ChildReferenceNode.EdgeTraversal {
        return .{ .identifier = identifier, .edge_type = tid };
    }

    pub fn init(
        operands_set: NodeReference,
        operand: NodeReference,
        operand_identifier: ?str,
    ) EdgeReference {
        const edge = Edge.init(operands_set, operand, tid);

        build(operand_identifier).apply_to(edge);
        return edge;
    }

    pub fn build(operand_identifier: ?str) EdgeCreationAttributes {
        if (!registered) {
            @branchHint(.unlikely);
            registered = true;
            Edge.register_type(tid) catch {};
        }
        return .{
            .edge_type = tid,
            .directional = true,
            .name = operand_identifier,
            .dynamic = graph.DynamicAttributes.init(),
        };
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_expression_node(E: graph.BoundEdgeReference) NodeReference {
        return EdgeComposition.get_parent_node_of(E.g.bind(E.edge.source)).?.node;
    }

    pub fn get_operands_set_node(expression_bound_node: graph.BoundNodeReference) ?graph.BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(expression_bound_node, "operands");
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

    pub fn get_expression_of(bedge: graph.BoundEdgeReference, node: NodeReference) ?NodeReference {
        if (Node.is_same(bedge.edge.source, node)) {
            return null;
        }
        return get_expression_node(bedge);
    }

    pub fn visit_operand_edges(
        operand_set_node: graph.BoundNodeReference,
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

        var visit = Visit{ .target = operand_set_node, .cb_ctx = ctx, .cb = f };
        // directed = true: only edges where bound_node is the source (outgoing edges)
        return operand_set_node.visit_edges_of_type(tid, T, &visit, Visit.visit, true);
    }

    pub fn visit_expression_edges(
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
                // Filter out self-references
                const expression = EdgeOperand.get_expression_of(bound_edge, self.target.node);
                if (expression) |_| {
                    const expression_result = self.cb(self.cb_ctx, bound_edge);
                    switch (expression_result) {
                        .CONTINUE => {},
                        else => return expression_result,
                    }
                }
                return visitor.VisitResult(T){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .target = bound_node, .cb_ctx = ctx, .cb = f };
        // directed = false: only edges where bound_node is the target (incoming edges)
        return bound_node.visit_edges_of_type(tid, T, &visit, Visit.visit, false);
    }

    //TODO not sure we want to advertise this, only in aliases interesting
    pub fn get_expression_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_node, tid, true);
    }

    pub fn add_operand(
        bound_node: graph.BoundNodeReference,
        operand: NodeReference,
        operand_identifier: ?str,
    ) graph.BoundEdgeReference {
        const op_set = get_operands_set_node(bound_node).?;
        const link = EdgeOperand.init(
            op_set.node,
            operand,
            operand_identifier,
        );
        const bound_edge = bound_node.g.insert_edge(link);
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
            operands_set: graph.BoundNodeReference,
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

        const op_set = get_operands_set_node(expression).?;
        var visit = Visit{
            .operands_set = op_set,
            .operand_type = operand_type,
            .cb_ctx = ctx,
            .cb = f,
        };
        // directed = true: operands_set is source, operand is target
        return op_set.visit_edges_of_type(tid, T, &visit, Visit.visit, true);
    }

    pub fn visit_expression_edges_of_type(
        operand: graph.BoundNodeReference,
        expression_type: graph.NodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            operand: graph.BoundNodeReference,
            expression_type: graph.NodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(T) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const expression = bound_edge.g.bind(EdgeOperand.get_expression_node(bound_edge));
                if (!EdgeType.is_node_instance_of(expression, self.expression_type)) {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }
                return self.cb(self.cb_ctx, bound_edge);
            }
        };

        var visit = Visit{
            .operand = operand,
            .expression_type = expression_type,
            .cb_ctx = ctx,
            .cb = f,
        };
        // directed = false: operand is target, expression is source
        return operand.visit_edges_of_type(tid, T, &visit, Visit.visit, false);
    }
};

test "edge operand basic" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const expression = Node.init();
    const operands = Node.init();
    const operand_a = Node.init();
    const operand_b = Node.init();
    const operand_c = Node.init();

    const b_expr = g.insert_node(expression);
    const b_operands = g.insert_node(operands);
    const b_operand_a = g.insert_node(operand_a);
    const b_operand_b = g.insert_node(operand_b);
    const b_operand_c = g.insert_node(operand_c);

    _ = EdgeComposition.add_child(b_expr, b_operands.node, "operands");
    _ = EdgeOperand.add_operand(b_expr, operand_a, "lhs");
    _ = EdgeOperand.add_operand(b_expr, operand_b, "rhs");
    _ = EdgeOperand.add_operand(b_expr, operand_c, null);

    const expression_edge_a = EdgeOperand.get_expression_edge(b_operand_a);
    const expression_edge_b = EdgeOperand.get_expression_edge(b_operand_b);
    const expression_edge_c = EdgeOperand.get_expression_edge(b_operand_c);
    try std.testing.expect(Node.is_same(
        EdgeOperand.get_expression_node(expression_edge_a.?),
        expression,
    ));
    try std.testing.expect(Node.is_same(
        EdgeOperand.get_expression_node(expression_edge_b.?),
        expression,
    ));
    try std.testing.expect(Node.is_same(
        EdgeOperand.get_expression_node(expression_edge_c.?),
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
    // Pass the operands container node directly (e.g., OperandSequence, OperandPointer)
    const visit_result = EdgeOperand.visit_operand_edges(b_operands, void, &collector, CollectOperands.visit);
    try std.testing.expectEqual(visit_result, visitor.VisitResult(void){ .EXHAUSTED = {} });
    try std.testing.expectEqual(collector.edges.items.len, 3);
    try std.testing.expect(Node.is_same(EdgeOperand.get_operand_node(collector.edges.items[0].edge), operand_a));
    try std.testing.expect(Node.is_same(EdgeOperand.get_operand_node(collector.edges.items[1].edge), operand_b));
    try std.testing.expect(Node.is_same(EdgeOperand.get_operand_node(collector.edges.items[2].edge), operand_c));
}
