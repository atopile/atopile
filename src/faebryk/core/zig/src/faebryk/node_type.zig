const graph_mod = @import("graph");
const std = @import("std");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const str = graph.str;

pub const EdgeType = struct {
    pub var tid: Edge.EdgeType = 1759276800;

    pub fn init(allocator: std.mem.Allocator, type_node: NodeReference, instance_node: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, type_node, instance_node, tid);
        edge.attributes.directional = true;
        return edge;
    }

    pub fn add_instance(bound_type_node: graph.BoundNodeReference, bound_instance_node: graph.BoundNodeReference) !graph.BoundEdgeReference {
        const link = try EdgeType.init(bound_type_node.g.allocator, bound_type_node.node, bound_instance_node.node);
        const bound_edge = try bound_type_node.g.insert_edge(link);
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
    const tn1 = try Node.init(a);
    defer tn1.deinit();
    const tn2 = try Node.init(a);
    defer tn2.deinit();
    const in1 = try Node.init(a);
    defer in1.deinit();
    const in2 = try Node.init(a);
    defer in2.deinit();

    _ = try g.insert_node(tn1);
    const btn2 = try g.insert_node(tn2);
    const bin1 = try g.insert_node(in1);
    const bin2 = try g.insert_node(in2);
    // const bn2 = try g.insert_node(n2);
    // _ = try g.insert_node(tn1);
    // _ = try g.insert_node(tn2);

    // init ---------------------------------------------------------------------------------------
    const et11 = try EdgeType.init(g.allocator, tn1, in1);
    defer et11.deinit();
    _ = try g.insert_edge(et11);
    try std.testing.expect(EdgeType.is_node_instance_of(bin1, tn1));

    // add_instance -------------------------------------------------------------------------------
    const bet22 = try EdgeType.add_instance(btn2, bin2);
    defer bet22.edge.deinit();
    try std.testing.expect(EdgeType.is_node_instance_of(bin2, tn2));

    // is_edge_instance -------------------------------------------------------------------------------
    try std.testing.expect(EdgeType.is_instance(et11));
    try std.testing.expect(EdgeType.is_instance(bet22.edge));

    // get_type_node -------------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeType.get_type_node(et11), tn1));
    try std.testing.expect(Node.is_same(EdgeType.get_type_node(bet22.edge), tn2));

    // get_instance_node -------------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeType.get_instance_node(et11).?, in1));
    try std.testing.expect(Node.is_same(EdgeType.get_instance_node(bet22.edge).?, in2));

    // get_type_edge -------------------------------------------------------------------------------
    try std.testing.expect(Edge.is_same(EdgeType.get_type_edge(bin1).?.edge, et11));
    try std.testing.expect(Edge.is_same(EdgeType.get_type_edge(bin2).?.edge, bet22.edge));

    // get_name -------------------------------------------------------------------------------
    // try std.testing.expect(EdgeType.get_name(et11) == "instance1");
    // try std.testing.expect(EdgeType.get_name(bet22.edge) == "instance2");

    // is_node_instance_of -------------------------------------------------------------------------------
    try std.testing.expect(EdgeType.is_node_instance_of(bin1, tn1));
    try std.testing.expect(EdgeType.is_node_instance_of(bin2, tn2));
    try std.testing.expect(EdgeType.is_node_instance_of(bin2, tn1) == false);

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
    try std.testing.expect(Node.is_same(EdgeType.get_instance_node(instances.items[0].edge).?, in2));

    // Print collected information for visibility
    std.debug.print("collected instances: {d}\n", .{instances.items.len});
    for (instances.items, 0..) |be, i| {
        const equals_in2 = Node.is_same(EdgeType.get_instance_node(be.edge).?, in2);
        std.debug.print("instance[{d}]: equals_in2={}\n", .{ i, equals_in2 });
    }

    // has to be deleted first
    defer g.deinit();
}
