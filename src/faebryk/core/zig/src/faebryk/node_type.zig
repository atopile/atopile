const graph_mod = @import("graph");
const std = @import("std");
const edgebuilder_mod = @import("edgebuilder.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;

pub const EdgeType = struct {
    pub const tid: Edge.EdgeType = 1759276800;

    pub fn init(allocator: std.mem.Allocator, type_node: NodeReference, instance_node: NodeReference) EdgeReference {
        const edge = Edge.init(allocator, type_node, instance_node, tid);
        build().apply_to(edge);
        return edge;
    }

    pub fn build() EdgeCreationAttributes {
        return .{
            .edge_type = tid,
            .directional = true,
            .name = null,
            .dynamic = null,
        };
    }

    pub fn add_instance(bound_type_node: graph.BoundNodeReference, bound_instance_node: graph.BoundNodeReference) graph.BoundEdgeReference {
        const link = EdgeType.init(bound_type_node.g.allocator, bound_type_node.node, bound_instance_node.node);
        const bound_edge = bound_type_node.g.insert_edge(link);
        return bound_edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_type_node(E: EdgeReference) NodeReference {
        return E.source;
    }

    pub fn get_instance_node(E: EdgeReference) ?NodeReference {
        return E.target;
    }

    pub fn get_type_edge(bound_instance_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_instance_node, tid, true);
    }

    pub fn is_node_instance_of(bound_node: graph.BoundNodeReference, node_type: NodeReference) bool {
        const type_edge = get_type_edge(bound_node);
        if (type_edge) |edge| {
            if (edge.edge.get_source()) |source| {
                return Node.is_same(source, node_type);
            }
        }
        return false;
    }

    pub fn visit_instance_edges(
        bound_type_node: graph.BoundNodeReference,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),
    ) visitor.VisitResult(void) {
        const Visit = struct {
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const instance = EdgeType.get_instance_node(bound_edge.edge);
                if (instance) |_| {
                    const instance_result = self.cb(self.cb_ctx, bound_edge);
                    switch (instance_result) {
                        .CONTINUE => {},
                        else => return instance_result,
                    }
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .cb_ctx = ctx, .cb = f };
        return bound_type_node.visit_edges_of_type(tid, void, &visit, Visit.visit);
    }
};

//zig test --dep graph -Mroot=src/faebryk/node_type.zig -Mgraph=src/graph/lib.zig
test "basic typegraph" {
    // Visitor callback that collects instance edges into a provided ArrayList
    // Expects ctx to be a *std.ArrayList(graph.BoundEdgeReference)
    const collect = struct {
        pub fn collect_into_list(ctx: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const list: *std.ArrayList(graph.BoundEdgeReference) = @ptrCast(@alignCast(ctx));
            list.append(bound_edge) catch |e| return visitor.VisitResult(void){ .ERROR = e };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);

    const btn1 = g.create_and_insert_node();
    const btn2 = g.create_and_insert_node();
    const bin1 = g.create_and_insert_node();
    const bin2 = g.create_and_insert_node();

    // init ---------------------------------------------------------------------------------------
    const et11 = EdgeType.init(g.allocator, btn1.node, bin1.node);
    _ = g.insert_edge(et11);
    try std.testing.expect(EdgeType.is_node_instance_of(bin1, btn1.node));

    // add_instance -------------------------------------------------------------------------------
    const bet22 = EdgeType.add_instance(btn2, bin2);
    try std.testing.expect(EdgeType.is_node_instance_of(bin2, btn2.node));

    // is_edge_instance -------------------------------------------------------------------------------
    try std.testing.expect(EdgeType.is_instance(et11));
    try std.testing.expect(EdgeType.is_instance(bet22.edge));

    // get_type_node -------------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeType.get_type_node(et11), btn1.node));
    try std.testing.expect(Node.is_same(EdgeType.get_type_node(bet22.edge), btn2.node));

    // get_instance_node -------------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeType.get_instance_node(et11).?, bin1.node));
    try std.testing.expect(Node.is_same(EdgeType.get_instance_node(bet22.edge).?, bin2.node));

    // get_type_edge -------------------------------------------------------------------------------
    try std.testing.expect(Edge.is_same(EdgeType.get_type_edge(bin1).?.edge, et11));
    try std.testing.expect(Edge.is_same(EdgeType.get_type_edge(bin2).?.edge, bet22.edge));

    // is_node_instance_of -------------------------------------------------------------------------------
    try std.testing.expect(EdgeType.is_node_instance_of(bin1, btn1.node));
    try std.testing.expect(EdgeType.is_node_instance_of(bin2, btn2.node));
    try std.testing.expect(EdgeType.is_node_instance_of(bin2, btn1.node) == false);

    // visit_instance_edges -------------------------------------------------------------------------------
    var instances = std.ArrayList(graph.BoundEdgeReference).init(a);
    defer instances.deinit();
    const visit_result = EdgeType.visit_instance_edges(btn2, &instances, collect.collect_into_list);
    switch (visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }
    try std.testing.expect(instances.items.len == 1);
    try std.testing.expect(Edge.is_same(instances.items[0].edge, bet22.edge));

    // Also verify the collected instance edge points to the known instance node
    try std.testing.expect(Node.is_same(EdgeType.get_instance_node(instances.items[0].edge).?, bin2.node));

    // has to be deleted first
    defer g.deinit();
}
