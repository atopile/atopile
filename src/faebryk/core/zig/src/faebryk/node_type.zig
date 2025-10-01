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
<<<<<<< HEAD
    var tid: Edge.EdgeType = 1759276800;
=======
    pub const tid: Edge.EdgeType = 0;
>>>>>>> bd281090 (edit type node is instance fn)

    pub fn init(allocator: std.mem.Allocator, type_node: NodeReference, instance_node: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, type_node, instance_node, tid);
        edge.directional = true;
        return edge;
    }

    pub fn add_instance(bound_node: graph.BoundNodeReference, instance: NodeReference, instance_identifier: str) !graph.BoundEdgeReference {
        const link = try Edge.init(bound_node.g.allocator, bound_node.node, instance, instance_identifier);
        const bound_edge = try bound_node.g.insert_edge(link);
        return bound_edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_type_node(E: EdgeReference) NodeReference {
        return E.source;
    }

    pub fn get_instance_node(E: EdgeReference) NodeReference {
        return E.target;
    }

    pub fn get_type_edge(bound_node: graph.BoundNodeReference) ?graph.BoundEdgeReference {
        return Edge.get_single_edge(bound_node, tid, false);
    }

    // pub fn visit_instance_edges(bound_node: graph.BoundNodeReference, f: fn (ctx: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void)) void {
    //     return Edge.visit_edges_of_type(bound_node, get_tid(), void, &visit, Visit.visit);
    // }

    pub fn is_node_instance_of(bound_node: graph.BoundNodeReference, node_type: NodeReference) bool {
        const type_edge = get_type_edge(bound_node);
        if (type_edge) |edge| {
            if (edge.edge.get_target()) |target| {
                return Node.is_same(target, node_type.node);
            }
        }
        return false;
    }

    pub fn get_name(edge: EdgeReference) !str {
        if (!is_instance(edge)) {
            return error.InvalidEdgeType;
        }

        return edge.name.?;
    }
};

//zig test --dep graph -Mroot=src/faebryk/node_type.zig -Mgraph=src/graph/lib.zig
test "basic typegraph" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    const tn1 = try Node.init(a);
    defer tn1.deinit();
    const in1 = try Node.init(a);
    defer in1.deinit();
    // const in2 = try Node.init(a);
    // const tn2 = try Node.init(a);

    // const btn1 = try g.insert_node(tn1);
    const bin1 = try g.insert_node(in1);
    // _ = btn1;
    // _ = bin1;
    // const bn2 = try g.insert_node(n2);
    // _ = try g.insert_node(tn1);
    // _ = try g.insert_node(tn2);

    // const et11 = try EdgeType.init(a, tn1, in1);
    // const et12 = try EdgeType.

    try std.testing.expect(EdgeType.is_node_instance_of(bin1, tn1));
    // try std.testing.expect(EdgeType.is_node_instance_of(bn2, tn1));
    // try std.testing.expect(!EdgeType.is_node_instance_of(bn1, tn2));
    // try std.testing.expect(!EdgeType.is_node_instance_of(bn2, tn2));

    try g.deinit();
    try tn1.deinit();
    try in1.deinit();
    // try btn1.deinit();
    // try bin1.deinit();
}
