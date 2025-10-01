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
    var tid: Edge.EdgeType = 1759276800;

    pub fn init(allocator: std.mem.Allocator, type_node: NodeReference, instance_node: NodeReference, instance_identifier: str) !EdgeReference {
        const edge = try Edge.init(allocator, type_node, instance_node, tid);
        edge.attributes.name = instance_identifier;
        edge.attributes.directional = true;
        return edge;
    }

    pub fn add_instance(bound_type_node: graph.BoundNodeReference, bound_instance_node: graph.BoundNodeReference, instance_identifier: str) !graph.BoundEdgeReference {
        const link = try EdgeType.init(bound_type_node.g.allocator, bound_type_node.node, bound_instance_node.node, instance_identifier);
        const bound_edge = try bound_type_node.g.insert_edge(link);
        return bound_edge;
    }

    pub fn is_edge_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_type_node(E: EdgeReference) NodeReference {
        return E.source;
    }

    pub fn get_instance_node(E: EdgeReference) NodeReference {
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

    pub fn get_name(edge: EdgeReference) !str {
        if (!is_edge_instance(edge)) {
            return error.InvalidEdgeType;
        }

        return edge.attributes.name.?;
    }

    // pub fn visit_instance_edges(bound_type_node: graph.BoundNodeReference, f: fn (ctx: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void)) void {
    //     return Edge.visit_edges_of_type(bound_type_node, get_tid(), void, &visit, Visit.visit);
    // }
};

//zig test --dep graph -Mroot=src/faebryk/node_type.zig -Mgraph=src/graph/lib.zig
test "basic typegraph" {
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
    const et11 = try EdgeType.init(g.allocator, tn1, in1, "instance1");
    defer et11.deinit();
    _ = try g.insert_edge(et11);
    try std.testing.expect(EdgeType.is_node_instance_of(bin1, tn1));

    // add_instance -------------------------------------------------------------------------------
    const bet22 = try EdgeType.add_instance(btn2, bin2, "instance2");
    defer bet22.edge.deinit();
    try std.testing.expect(EdgeType.is_node_instance_of(bin2, tn2));

    // is_edge_instance -------------------------------------------------------------------------------
    try std.testing.expect(EdgeType.is_edge_instance(et11));
    try std.testing.expect(EdgeType.is_edge_instance(bet22.edge));

    // get_type_node -------------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeType.get_type_node(et11), tn1));
    try std.testing.expect(Node.is_same(EdgeType.get_type_node(bet22.edge), tn2));

    // get_instance_node -------------------------------------------------------------------------------
    try std.testing.expect(Node.is_same(EdgeType.get_instance_node(et11), in1));
    try std.testing.expect(Node.is_same(EdgeType.get_instance_node(bet22.edge), in2));

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

    // get_name -------------------------------------------------------------------------------
    try std.testing.expect(std.mem.eql(u8, try EdgeType.get_name(et11), "instance1"));
    try std.testing.expect(std.mem.eql(u8, try EdgeType.get_name(bet22.edge), "instance2"));

    // has to be deleted first
    defer g.deinit();
}
