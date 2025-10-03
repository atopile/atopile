const graph_mod = @import("graph");
const std = @import("std");
const node_type_mod = @import("node_type.zig");
const composition_mod = @import("composition.zig");
const next_mod = @import("next.zig");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const BoundNodeReference = graph.BoundNodeReference;
const str = graph.str;
const EdgeType = node_type_mod.EdgeType;
const EdgeComposition = composition_mod.EdgeComposition;

pub const TypeGraph = struct {
    // Global nodes, not parent to anything, only used to mark type and trait. Bootstrap typegraph
    // parent_node: NodeReference,
    implements_type_type_bnode: BoundNodeReference,
    implements_trait_type_bnode: BoundNodeReference,
    make_child_type_bnode: BoundNodeReference,
    make_link_type_bnode: BoundNodeReference,
    type_graph_view: GraphView,

    pub fn create_typegraph() !TypeGraph {
        const implements_type_type_node = try Node.init(std.testing.allocator);
        const implements_trait_type_node = try Node.init(std.testing.allocator);
        const make_child_type_node = try Node.init(std.testing.allocator);
        const make_link_type_node = try Node.init(std.testing.allocator);

        const type_implements_type_instance = try Node.init(std.testing.allocator);
        const type_implements_trait_instance = try Node.init(std.testing.allocator);
        const trait_implements_type_instance = try Node.init(std.testing.allocator);
        const trait_implements_trait_instance = try Node.init(std.testing.allocator);

        var type_graph_view = graph.GraphView.init(std.testing.allocator);
        const implements_type_type_bnode = try type_graph_view.insert_node(implements_type_type_node);
        const implements_trait_type_bnode = try type_graph_view.insert_node(implements_trait_type_node);
        const make_child_type_bnode = try type_graph_view.insert_node(make_child_type_node);
        const make_link_type_bnode = try type_graph_view.insert_node(make_link_type_node);
        _ = try type_graph_view.insert_node(type_implements_type_instance);
        _ = try type_graph_view.insert_node(type_implements_trait_instance);
        _ = try type_graph_view.insert_node(trait_implements_type_instance);
        _ = try type_graph_view.insert_node(trait_implements_trait_instance);

        _ = try type_graph_view.insert_edge(try EdgeComposition.init(type_graph_view.allocator, implements_type_type_node, type_implements_type_instance, "implements_type"));
        _ = try type_graph_view.insert_edge(try EdgeComposition.init(type_graph_view.allocator, implements_type_type_node, type_implements_trait_instance, "implements_trait"));
        _ = try type_graph_view.insert_edge(try EdgeComposition.init(type_graph_view.allocator, implements_trait_type_node, trait_implements_type_instance, "implements_type"));
        _ = try type_graph_view.insert_edge(try EdgeComposition.init(type_graph_view.allocator, implements_trait_type_node, trait_implements_trait_instance, "implements_trait"));

        return TypeGraph{
            .implements_type_type_bnode = implements_type_type_bnode,
            .implements_trait_type_bnode = implements_trait_type_bnode,
            .make_child_type_bnode = make_child_type_bnode,
            .make_link_type_bnode = make_link_type_bnode,
            .type_graph_view = type_graph_view,
        };
    }

    // pub fn create_instance_graph(typegraph: GraphView) !graph.GraphView {}

    pub fn init_type_node(type_graph: *TypeGraph) !BoundNodeReference {
        const type_node = try Node.init(std.testing.allocator);
        const type_bnode = try type_graph.type_graph_view.insert_node(type_node);
        const implements_type_instance_bnode = try TypeGraph.instantiate(&type_graph.type_graph_view, type_graph.implements_type_type_bnode.node);
        // const implements_trait_instance_node = try TypeGraph.instantiate(type_graph_view, TypeGraph.implements_trait_type_node);
        _ = try type_graph.type_graph_view.insert_edge(try EdgeComposition.init(type_graph.type_graph_view.allocator, type_node, implements_type_instance_bnode.node, "implements_type"));
        // _ = try type_graph_view.insert_edge(try EdgeComposition.init(type_graph_view.allocator, implements_trait_instance_node, type_node, "implements_trait"));
        return type_bnode;
    }

    pub fn init_trait_node(type_graph: *TypeGraph) !BoundNodeReference {
        const trait_node = Node.init(std.testing.allocator);
        const trait_bnode = try type_graph.type_graph_view.insert_node(trait_node);
        const implements_trait_instance_node = try TypeGraph.instantiate(&type_graph.type_graph_view, type_graph.implements_trait_type_bnode.node);
        _ = try type_graph.type_graph_view.insert_edge(try EdgeComposition.init(type_graph.type_graph_view.allocator, trait_node, implements_trait_instance_node.node, "implements_trait"));
        return trait_bnode;
    }

    pub fn init_make_child_node(type_graph: *TypeGraph, identifiers: []const str) !BoundNodeReference {
        const make_child_bnode = try TypeGraph.instantiate(&type_graph.type_graph_view, type_graph.make_child_type_bnode.node);
        return make_child_bnode;
    }

    pub fn init_make_link_node(type_graph: *TypeGraph) !BoundNodeReference {
        const make_link_bnode = try TypeGraph.instantiate(&type_graph.type_graph_view, type_graph.make_link_type_bnode.node);
        return make_link_bnode;
    }

    pub fn init_reference_node() !BoundNodeReference {
        const reference_node = try Node.init(std.testing.allocator);
        const reference_bnode = try type_graph.type_graph_view.insert_node(reference_node);
        return reference_bnode;
    }

    pub fn instantiate(type_graph_view: *GraphView, type_node: NodeReference) !graph.BoundNodeReference {
        const instance_node = try Node.init(std.testing.allocator);
        const instance_bnode = try type_graph_view.insert_node(instance_node);
        _ = try type_graph_view.insert_edge(try EdgeType.init(type_graph_view.allocator, type_node, instance_node));
        return instance_bnode;
    }
};

//zig test --dep graph -Mroot=src/faebryk/type.zig -Mgraph=src/graph/lib.zig
test "basic instantiation" {
    var type_graph = try TypeGraph.create_typegraph();

    const collect = struct {
        pub fn collect_into_list(ctx: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const list: *std.ArrayList(graph.BoundEdgeReference) = @ptrCast(@alignCast(ctx));
            list.append(bound_edge) catch |e| return visitor.VisitResult(void){ .ERROR = e };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };
    // init_type_node -------------------------------------------------------------------------------
    const example_type_bnode = try TypeGraph.init_type_node(&type_graph);

    // init ---------------------------------------------------------------------------------------
    // visit_children_edges of base types ---------------------------------------------------------
    var children = std.ArrayList(graph.BoundEdgeReference).init(type_graph.type_graph_view.allocator);
    defer children.deinit();
    // const visit_result = EdgeComposition.visit_children_edges(type_graph.implements_type_type_bnode, &children, collect.collect_into_list);
    const visit_result = EdgeComposition.visit_children_edges(example_type_bnode, &children, collect.collect_into_list);
    switch (visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }

    // try std.testing.expect(instances.items.len == 1);

    // Print collected information for visibility
    std.debug.print("TYPE collected children: {d}\n", .{children.items.len});
    // for (instances.items, 0..) |be, i| {
    //     // const equals_in2 = Node.is_same(EdgeType.get_instance_node(be.edge).?, in2);
    //     // std.debug.print("instance[{d}]: equals_in2={}\n", .{ i, equals_in2 });
    // }

    // // is_instance -------------------------------------------------------------------------------
    // std.debug.print("en12 source: {}\n", .{EdgeNext.get_previous_node(en12).?});
    // try std.testing.expect(EdgeNext.is_instance(ben23.edge));

    // has to be deleted first
    defer type_graph.type_graph_view.deinit();
}
