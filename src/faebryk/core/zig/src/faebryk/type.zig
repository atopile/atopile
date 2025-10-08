const graph_mod = @import("graph");
const std = @import("std");
const node_type_mod = @import("node_type.zig");
const composition_mod = @import("composition.zig");
const next_mod = @import("next.zig");
const pointer_mod = @import("pointer.zig");

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
const EdgePointer = pointer_mod.EdgePointer;
const EdgeNext = next_mod.EdgeNext;

pub const TypeGraph = struct {
    // Global nodes, not parent to anything, only used to mark type and trait. Bootstrap typegraph
    // parent_node: NodeReference,
    implements_type_type_bnode: BoundNodeReference,
    implements_trait_type_bnode: BoundNodeReference,
    make_child_type_bnode: BoundNodeReference,
    make_link_type_bnode: BoundNodeReference,
    reference_type_bnode: BoundNodeReference,
    type_graph_view_ptr: *GraphView,

    pub const ImplementsTypeType = struct {
        pub const identifier = "ImplementsType";

        pub fn create(allocator: std.mem.Allocator) !NodeReference {
            const implements_type_type_node = try Node.init(allocator);
            try implements_type_type_node.attributes.dynamic.values.put("name", .{ .String = identifier });
            return implements_type_type_node;
        }
        // std.debug.print("implements_type_type_node: {s}\n", .{implements_type_type_node.attributes.dynamic.values.get("name").?.String});
    };

    pub const ImplementsTraitType = struct {
        pub const identifier = "ImplementsTrait";

        pub fn create(allocator: std.mem.Allocator) !NodeReference {
            const implements_type_type_node = try Node.init(allocator);
            try implements_type_type_node.attributes.dynamic.values.put("name", .{ .String = identifier });
            return implements_type_type_node;
        }
    };

    // Only exists to group init and set name together
    pub const TypeNode = struct {
        pub fn create(allocator: std.mem.Allocator, identifier: str) !NodeReference {
            const implements_type_type_node = try Node.init(allocator);
            try implements_type_type_node.attributes.dynamic.values.put("name", .{ .String = identifier });
            return implements_type_type_node;
        }
    };

    pub fn create_typegraph(allocator: std.mem.Allocator) !TypeGraph {
        // Bootstrap first type and trait type-nodes and instance-nodes
        const implements_type_type_node = try ImplementsTypeType.create(allocator);
        const implements_trait_type_node = try ImplementsTraitType.create(allocator);

        const type_graph_view_ptr = try allocator.create(GraphView); // Allocate on heap for later use after return
        type_graph_view_ptr.* = GraphView.init(allocator);

        var type_graph = TypeGraph{
            .implements_type_type_bnode = undefined,
            .implements_trait_type_bnode = undefined,
            .make_child_type_bnode = undefined,
            .make_link_type_bnode = undefined,
            .reference_type_bnode = undefined,
            .type_graph_view_ptr = type_graph_view_ptr,
        };

        const type_implements_type_instance = try Node.init(allocator);
        const type_implements_trait_instance = try Node.init(allocator);
        const trait_implements_type_instance = try Node.init(allocator);
        const trait_implements_trait_instance = try Node.init(allocator);

        // Insert type and trait type-nodes and instance-nodes into type graph view
        const implements_type_type_bnode = try type_graph.type_graph_view_ptr.insert_node(implements_type_type_node);
        type_graph.implements_type_type_bnode = implements_type_type_bnode;
        const implements_trait_type_bnode = try type_graph.type_graph_view_ptr.insert_node(implements_trait_type_node);
        type_graph.implements_trait_type_bnode = implements_trait_type_bnode;
        _ = try type_graph.type_graph_view_ptr.insert_node(type_implements_type_instance);
        _ = try type_graph.type_graph_view_ptr.insert_node(type_implements_trait_instance);
        _ = try type_graph.type_graph_view_ptr.insert_node(trait_implements_type_instance);
        _ = try type_graph.type_graph_view_ptr.insert_node(trait_implements_trait_instance);

        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeType.init(type_graph.type_graph_view_ptr.allocator, implements_type_type_node, type_implements_type_instance));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeType.init(type_graph.type_graph_view_ptr.allocator, implements_trait_type_node, type_implements_trait_instance));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeType.init(type_graph.type_graph_view_ptr.allocator, implements_type_type_node, trait_implements_type_instance));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeType.init(type_graph.type_graph_view_ptr.allocator, implements_trait_type_node, trait_implements_trait_instance));

        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, implements_type_type_node, type_implements_type_instance, "implements_type"));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, implements_type_type_node, type_implements_trait_instance, "implements_trait"));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, implements_trait_type_node, trait_implements_type_instance, "implements_type"));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, implements_trait_type_node, trait_implements_trait_instance, "implements_trait"));

        const make_child_type_bnode = try TypeGraph.init_type_node(&type_graph, "MakeChild");
        type_graph.make_child_type_bnode = make_child_type_bnode;
        const make_link_type_bnode = try TypeGraph.init_type_node(&type_graph, "MakeLink");
        type_graph.make_link_type_bnode = make_link_type_bnode;
        const reference_type_bnode = try TypeGraph.init_type_node(&type_graph, "Reference");
        type_graph.reference_type_bnode = reference_type_bnode;
        // const make_child_type_bnode = try type_graph_view.insert_node(make_child_type_node);
        // _ = try type_graph_view.insert_edge(try EdgeType.init(type_graph_view.allocator, make_child_type_node, make_child_type_bnode));
        // const make_link_type_bnode = try type_graph_view.insert_node(make_link_type_node);
        // _ = try type_graph_view.insert_edge(try EdgeType.init(type_graph_view.allocator, make_link_type_node, make_link_type_bnode));
        // const reference_type_bnode = try type_graph_view.insert_node(reference_type_node);
        // _ = try type_graph_view.insert_edge(try EdgeType.init(type_graph_view.allocator, reference_type_bnode.?.node, reference_type_bnode.node));

        return type_graph;
    }

    // pub fn create_instance_graph(typegraph: GraphView) !graph.GraphView {}

    pub fn init_type_node(type_graph: *TypeGraph, identifier: str) !BoundNodeReference {
        const type_node = try TypeNode.create(std.testing.allocator, identifier);
        const type_bnode = try type_graph.type_graph_view_ptr.insert_node(type_node);
        if (std.mem.eql(u8, identifier, "MakeChild")) {
            const implements_type_instance_node = try Node.init(std.testing.allocator);
            const implements_type_instance_bnode = try type_graph.type_graph_view_ptr.insert_node(implements_type_instance_node);
            _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeType.init(type_graph.type_graph_view_ptr.allocator, type_graph.implements_type_type_bnode.node, implements_type_instance_node));
            _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, type_node, implements_type_instance_bnode.node, "implements_type"));
            return type_bnode;
        }
        const implements_type_instance_bnode = try TypeGraph.instantiate_node(type_graph, type_graph.implements_type_type_bnode.node, type_graph.type_graph_view_ptr);
        // const implements_trait_instance_node = try TypeGraph.instantiate(type_graph_view, TypeGraph.implements_trait_type_node);
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, type_node, implements_type_instance_bnode.node, "implements_type"));
        // _ = try type_graph_view.insert_edge(try EdgeComposition.init(type_graph_view.allocator, implements_trait_instance_node, type_node, "implements_trait"));
        return type_bnode;
    }

    pub fn init_trait_node(type_graph: *TypeGraph) !BoundNodeReference {
        const trait_node = Node.init(std.testing.allocator);
        const trait_bnode = try type_graph.type_graph_view_ptr.insert_node(trait_node);
        const implements_trait_instance_node = try TypeGraph.instantiate_node(type_graph, type_graph.implements_trait_type_bnode.node, type_graph.type_graph_view_ptr);
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, trait_node, implements_trait_instance_node.node, "implements_trait"));
        return trait_bnode;
    }

    pub fn init_make_child_node(type_graph: *TypeGraph, type_bnode: BoundNodeReference, identifier: str) !BoundNodeReference {
        const make_child_bnode = try TypeGraph.instantiate_node(type_graph, type_graph.make_child_type_bnode.node, type_graph.type_graph_view_ptr);
        const child_reference_bnode = try TypeGraph.init_reference_node(type_graph, type_bnode);
        _ = try EdgeComposition.add_child(make_child_bnode, child_reference_bnode.node, identifier);
        return make_child_bnode;
    }

    pub fn init_reference_node(type_graph: *TypeGraph, type_bnode: ?BoundNodeReference) !BoundNodeReference {
        const reference_bnode = try TypeGraph.instantiate_node(type_graph, type_graph.reference_type_bnode.node, type_graph.type_graph_view_ptr);
        if (type_bnode) |bnode| {
            _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgePointer.init(type_graph.type_graph_view_ptr.allocator, reference_bnode.node, bnode.node));
        }
        return reference_bnode;
    }

    pub fn init_make_link_node(type_graph: *TypeGraph, lhs_target_node: NodeReference, rhs_target_node: NodeReference, connection_identifier: str) !BoundNodeReference {
        const make_link_bnode = try TypeGraph.instantiate_node(type_graph, type_graph.make_link_type_bnode.node, type_graph.type_graph_view_ptr);
        // make_link_bnode.node.attributes.connection_identifier = connection_identifier;
        std.debug.print("Making connection of type: {s}\n", .{connection_identifier});
        const lhs_node = try Node.init(type_graph.type_graph_view_ptr.allocator);
        const rhs_node = try Node.init(type_graph.type_graph_view_ptr.allocator);
        _ = try type_graph.type_graph_view_ptr.insert_node(lhs_node);
        _ = try type_graph.type_graph_view_ptr.insert_node(rhs_node);
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, make_link_bnode.node, lhs_node, "lhs"));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgeComposition.init(type_graph.type_graph_view_ptr.allocator, make_link_bnode.node, rhs_node, "rhs"));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgePointer.init(type_graph.type_graph_view_ptr.allocator, lhs_node, lhs_target_node));
        _ = try type_graph.type_graph_view_ptr.insert_edge(try EdgePointer.init(type_graph.type_graph_view_ptr.allocator, rhs_node, rhs_target_node));
        return make_link_bnode;
    }

    pub fn instantiate_node(type_graph: *TypeGraph, type_node: NodeReference, graph_view: *GraphView) !graph.BoundNodeReference {
        // 1) Create instance and connect it to its type
        const new_instance_node = try Node.init(std.testing.allocator);
        const new_instance_bnode = try graph_view.insert_node(new_instance_node);
        _ = try graph_view.insert_edge(try EdgeType.init(graph_view.allocator, type_node, new_instance_node));

        // Make child implementation
        // 2) Visit composition children of the type_node and handle MakeChild
        const Visit = struct {
            type_graph: *TypeGraph,
            parent_instance_bnode: graph.BoundNodeReference,

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));

                // Child under the type (could be MakeChild)
                const child_type_node = EdgeComposition.get_child_node(bound_edge.edge);
                const child_type_bnode = bound_edge.g.bind(child_type_node);

                // Only process MakeChild instances
                if (!EdgeType.is_node_instance_of(child_type_bnode, self.type_graph.make_child_type_bnode.node)) {
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }

                // Find the child reference node (of 'Reference' type) under this MakeChild
                const RefFinder = struct {
                    type_graph: *TypeGraph,
                    found_ref_bnode: ?graph.BoundNodeReference = null,

                    pub fn visit(self_ptr2: *anyopaque, mc_child_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                        const s: *@This() = @ptrCast(@alignCast(self_ptr2));
                        const mc_child_node = EdgeComposition.get_child_node(mc_child_edge.edge);
                        const mc_child_bnode = mc_child_edge.g.bind(mc_child_node);

                        if (node_type_mod.EdgeType.is_node_instance_of(mc_child_bnode, s.type_graph.reference_type_bnode.node)) {
                            s.found_ref_bnode = mc_child_bnode;
                            return visitor.VisitResult(void){ .STOP = {} };
                        }
                        return visitor.VisitResult(void){ .CONTINUE = {} };
                    }
                };

                var rf = RefFinder{ .type_graph = self.type_graph, .found_ref_bnode = null };
                _ = EdgeComposition.visit_children_edges(child_type_bnode, &rf, RefFinder.visit);
                if (rf.found_ref_bnode) |ref_bnode| {
                    // 3) Use the child reference edge name as the instance child name
                    const parent_edge = EdgeComposition.get_parent_edge(ref_bnode).?;
                    const child_name = EdgeComposition.get_name(parent_edge.edge) catch |e| {
                        return visitor.VisitResult(void){ .ERROR = e };
                    };

                    // 4) Resolve referenced type and instantiate it into the instance graph
                    const referenced_type_node_ref = EdgePointer.get_referenced_node_from_node(ref_bnode);
                    if (referenced_type_node_ref) |ref_type_nr| {
                        const child_instance_bnode = TypeGraph.instantiate_node(
                            self.type_graph,
                            ref_type_nr,
                            self.type_graph.type_graph_view_ptr,
                        ) catch |e| {
                            return visitor.VisitResult(void){ .ERROR = e };
                        };

                        // 5) Attach child instance to parent instance with the reference name
                        std.debug.print("Adding child instance to parent instance with the reference name: {s}\n", .{child_name});
                        _ = EdgeComposition.add_child(self.parent_instance_bnode, child_instance_bnode.node, child_name) catch |e| {
                            return visitor.VisitResult(void){ .ERROR = e };
                        };
                    }
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var visit = Visit{
            .type_graph = type_graph,
            .parent_instance_bnode = new_instance_bnode,
        };
        const type_bnode = GraphView.bind(type_graph.type_graph_view_ptr, type_node);
        _ = EdgeComposition.visit_children_edges(type_bnode, &visit, Visit.visit);

        // TODO: Make link implementation

        return new_instance_bnode;
    }

    pub fn resolve_instance_reference(reference_bnode: BoundNodeReference, base_bnode: BoundNodeReference) !graph.BoundNodeReference {
        var target_bnode = base_bnode;
        const child_identifier = try EdgeComposition.get_name(EdgeComposition.get_parent_edge(reference_bnode).?.edge);

        const child_bnode = EdgeComposition.get_child_by_identifier(base_bnode, child_identifier);
        if (child_bnode) |bnode| {
            target_bnode = bnode;
        }

        const next_ref_node = EdgeNext.get_next_node_from_node(reference_bnode);
        if (next_ref_node) |next_ref| {
            const next_ref_bnode = reference_bnode.g.bind(next_ref);
            target_bnode = try TypeGraph.resolve_instance_reference(next_ref_bnode, target_bnode);
        }
        return target_bnode;
    }

    pub fn instantiate(type_graph: *TypeGraph, build_target_type_identifier: str) !BoundNodeReference {
        std.debug.print("Instantiating type: {s}\n", .{build_target_type_identifier});
        const implements_type_instance_edges = type_graph.implements_type_type_bnode.get_edges_of_type(EdgeType.tid).?;
        for (implements_type_instance_edges.items) |edge| {
            const implements_type_instance_node = EdgeType.get_instance_node(edge).?;
            const implements_type_instance_bnode = type_graph.type_graph_view_ptr.bind(implements_type_instance_node);
            const parent_type_edge = EdgeComposition.get_parent_edge(implements_type_instance_bnode);
            const parent_type_node = EdgeComposition.get_parent_node(parent_type_edge.?.edge);
            const type_node_name = parent_type_node.attributes.dynamic.values.get("name").?.String;
            if (std.mem.eql(u8, type_node_name, build_target_type_identifier)) {
                const instance_bnode = try TypeGraph.instantiate_node(type_graph, parent_type_node, type_graph.type_graph_view_ptr);
                return instance_bnode;
            }
        }

        std.debug.print("Type node not found for build target: {s}\n", .{build_target_type_identifier});
        return error.InvalidArgument;
    }
};

//zig test --dep graph -Mroot=src/faebryk/type.zig -Mgraph=src/graph/lib.zig
test "basic instantiation" {
    var type_graph = try TypeGraph.create_typegraph(std.testing.allocator);

    const collect = struct {
        pub fn collect_into_list(ctx: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const list: *std.ArrayList(graph.BoundEdgeReference) = @ptrCast(@alignCast(ctx));
            list.append(bound_edge) catch |e| return visitor.VisitResult(void){ .ERROR = e };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };
    // init_type_node -------------------------------------------------------------------------------
    const example_type_bnode = try TypeGraph.init_type_node(&type_graph, "Example");

    // init ---------------------------------------------------------------------------------------
    // visit_children_edges of base types ---------------------------------------------------------
    var children = std.ArrayList(graph.BoundEdgeReference).init(type_graph.type_graph_view_ptr.allocator);
    defer children.deinit();
    // const visit_result = EdgeComposition.visit_children_edges(type_graph.implements_type_type_bnode, &children, collect.collect_into_list);
    const visit_result = EdgeComposition.visit_children_edges(example_type_bnode, &children, collect.collect_into_list);
    switch (visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }
    std.debug.print("TYPE collected children: {d}\n", .{children.items.len});

    // Electrical and Capacitor types
    const Type_Electrical = try TypeGraph.init_type_node(&type_graph, "Electrical");
    const Type_Capacitor = try TypeGraph.init_type_node(&type_graph, "Capacitor");
    const make_child_bnode_cp1 = try TypeGraph.init_make_child_node(&type_graph, Type_Electrical, "cp1");
    _ = try EdgeComposition.add_child(Type_Capacitor, make_child_bnode_cp1.node, "cp1_make_child");
    const make_child_bnode_cp2 = try TypeGraph.init_make_child_node(&type_graph, Type_Electrical, "cp2");
    _ = try EdgeComposition.add_child(Type_Capacitor, make_child_bnode_cp2.node, "cp2_make_child");

    const Type_Resistor = try TypeGraph.init_type_node(&type_graph, "Resistor");
    // MAKE CHILD
    const make_child_bnode_p1 = try TypeGraph.init_make_child_node(&type_graph, Type_Electrical, "p1");
    _ = try EdgeComposition.add_child(Type_Resistor, make_child_bnode_p1.node, "p1_make_child");
    const make_child_bnode_p2 = try TypeGraph.init_make_child_node(&type_graph, Type_Electrical, "p2");
    _ = try EdgeComposition.add_child(Type_Resistor, make_child_bnode_p2.node, "p2_make_child");
    const make_child_bnode_cap = try TypeGraph.init_make_child_node(&type_graph, Type_Capacitor, "cap1");
    _ = try EdgeComposition.add_child(Type_Resistor, make_child_bnode_cap.node, "cap1_make_child");

    const p1_ref_bnode = EdgeComposition.get_child_by_identifier(make_child_bnode_p1, "p1").?;
    try std.testing.expect(EdgeType.is_node_instance_of(p1_ref_bnode, type_graph.reference_type_bnode.node));
    // resolve_reference -------------------------------------------------------------------------------
    const resolved_type_node = EdgePointer.get_referenced_node_from_node(p1_ref_bnode);
    try std.testing.expect(Node.is_same(resolved_type_node.?, Type_Electrical.node));

    // INSTANTIATE
    const resistor_instance_bnode = try TypeGraph.instantiate_node(&type_graph, Type_Resistor.node, type_graph.type_graph_view_ptr);
    std.debug.print("Resistor Instance: {d}\n", .{resistor_instance_bnode.node.attributes.uuid});
    const p1_instance_bnode = EdgeComposition.get_child_by_identifier(resistor_instance_bnode, "p1").?;
    const p2_instance_bnode = EdgeComposition.get_child_by_identifier(resistor_instance_bnode, "p2").?;
    const cap1_instance_bnode = EdgeComposition.get_child_by_identifier(resistor_instance_bnode, "cap1").?;
    const cap1p1_instance_bnode = EdgeComposition.get_child_by_identifier(cap1_instance_bnode, "cp1").?;
    const cap1p2_instance_bnode = EdgeComposition.get_child_by_identifier(cap1_instance_bnode, "cp2").?;
    try std.testing.expect(EdgeType.is_node_instance_of(p1_instance_bnode, Type_Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(p2_instance_bnode, Type_Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1_instance_bnode, Type_Capacitor.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1p1_instance_bnode, Type_Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1p2_instance_bnode, Type_Electrical.node));

    // visit_children_edges of base types ---------------------------------------------------------
    var resistor_children = std.ArrayList(graph.BoundEdgeReference).init(type_graph.type_graph_view_ptr.allocator);
    defer resistor_children.deinit();
    // const visit_result = EdgeComposition.visit_children_edges(type_graph.implements_type_type_bnode, &children, collect.collect_into_list);
    const resistor_visit_result = EdgeComposition.visit_children_edges(resistor_instance_bnode, &resistor_children, collect.collect_into_list);
    switch (resistor_visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }
    std.debug.print("TYPE collected children: {d}\n", .{resistor_children.items.len});

    // Nested Reference
    const cap1_reference_bnode = try TypeGraph.init_reference_node(&type_graph, null);
    _ = try EdgeComposition.add_child(Type_Resistor, cap1_reference_bnode.node, "cap1");
    const cap1p1_reference_bnode = try TypeGraph.init_reference_node(&type_graph, Type_Electrical);
    _ = try EdgeComposition.add_child(cap1_reference_bnode, cap1p1_reference_bnode.node, "cp1");
    _ = try EdgeNext.add_next(cap1_reference_bnode, cap1p1_reference_bnode);

    const cap1p1_instance_search_bnode = try TypeGraph.resolve_instance_reference(cap1_reference_bnode, resistor_instance_bnode);
    try std.testing.expect(Node.is_same(cap1p1_instance_search_bnode.node, cap1p1_instance_bnode.node));

    // MAKE LINK
    const make_link_bnode = try TypeGraph.init_make_link_node(&type_graph, cap1p1_instance_bnode.node, cap1p2_instance_bnode.node, "connection");
    _ = try EdgeComposition.add_child(Type_Resistor, make_link_bnode.node, "caplinks");
    const link1_instance_bnode = EdgeComposition.get_child_by_identifier(Type_Resistor, "caplinks").?;
    const link1_lhs_instance_bnode = EdgeComposition.get_child_by_identifier(link1_instance_bnode, "lhs").?;
    const link1_rhs_instance_bnode = EdgeComposition.get_child_by_identifier(link1_instance_bnode, "rhs").?;
    try std.testing.expect(Node.is_same(EdgePointer.get_referenced_node_from_node(link1_lhs_instance_bnode).?, cap1p1_instance_bnode.node));
    try std.testing.expect(Node.is_same(EdgePointer.get_referenced_node_from_node(link1_rhs_instance_bnode).?, cap1p2_instance_bnode.node));

    // _ = type_graph.implements_type_type_bnode.get_edges();
    // defer link1_children.deinit();
    // link1_children = type_graph.implements_type_type_bnode.get_edges().?;

    const instantiated_resistor_bnode = try TypeGraph.instantiate(&type_graph, "Resistor");
    const instantiated_p1_bnode = EdgeComposition.get_child_by_identifier(instantiated_resistor_bnode, "p1").?;
    std.debug.print("Instantiated Resistor Instance: {d}\n", .{instantiated_resistor_bnode.node.attributes.uuid});
    std.debug.print("Instantiated P1 Instance: {d}\n", .{instantiated_p1_bnode.node.attributes.uuid});

    defer std.testing.allocator.destroy(type_graph.type_graph_view_ptr);
    defer type_graph.type_graph_view_ptr.*.deinit();
}
