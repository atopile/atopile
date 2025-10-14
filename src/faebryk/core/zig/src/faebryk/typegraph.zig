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

// TODO: BoundNodeReference and NodeReference used mixed all over the place
// TODO: move add/create functions into respective structs

pub const TypeGraph = struct {
    // Global nodes, not parent to anything, only used to mark type and trait. Bootstrap typegraph
    implements_type_type: BoundNodeReference,
    implements_trait_type: BoundNodeReference,
    make_child_type: BoundNodeReference,
    make_link_type: BoundNodeReference,
    reference_type: BoundNodeReference,
    g: *GraphView,

    const TypeNodeAttributes = struct {
        node: NodeReference,

        pub fn of(node: NodeReference) @This() {
            return .{ .node = node };
        }

        pub const type_identifier = "type_identifier";

        pub fn set_type_name(self: @This(), name: str) void {
            self.node.attributes.dynamic.values.put(type_identifier, .{ .String = name }) catch unreachable;
        }
        pub fn get_type_name(self: @This()) str {
            return self.node.attributes.dynamic.values.get(type_identifier).?.String;
        }
    };

    // Bootstrap helpers
    pub const TypeNode = struct {
        pub fn create_and_insert(g: *GraphView, type_identifier: str) !BoundNodeReference {
            const allocator = g.allocator;
            const implements_type_type_node = try Node.init(allocator);
            TypeNodeAttributes.of(implements_type_type_node).set_type_name(type_identifier);
            const implements_type_type_bnode = try g.insert_node(implements_type_type_node);
            return implements_type_type_bnode;
        }

        pub fn spawn_instance(bound_type_node: BoundNodeReference) !BoundNodeReference {
            const allocator = bound_type_node.g.allocator;
            const instance_node = try Node.init(allocator);
            const instance_bnode = try bound_type_node.g.insert_node(instance_node);
            _ = try bound_type_node.g.insert_edge(try EdgeType.init(bound_type_node.g.allocator, bound_type_node.node, instance_node));
            return instance_bnode;
        }
    };

    pub const TraitNode = struct {
        pub fn add_trait_to(target: BoundNodeReference, trait_type: BoundNodeReference) !BoundNodeReference {
            const trait_instance = try TypeNode.spawn_instance(trait_type);
            _ = try EdgeComposition.add_child(target, trait_instance.node, null);
            return trait_instance;
        }
    };

    pub const MakeChildNode = struct {
        pub const Attributes = struct {
            node: NodeReference,

            pub fn of(node: NodeReference) @This() {
                return .{ .node = node };
            }

            pub const child_identifier = "child_identifier";

            pub fn set_child_identifier(self: @This(), identifier: str) void {
                self.node.attributes.dynamic.values.put(child_identifier, .{ .String = identifier }) catch unreachable;
            }

            pub fn get_child_identifier(self: @This()) str {
                return self.node.attributes.dynamic.values.get(child_identifier).?.String;
            }
        };

        pub fn get_child_type(node: BoundNodeReference) ?NodeReference {
            return EdgePointer.get_referenced_node_from_node(node);
        }
    };

    pub const ChildReferenceNode = struct {
        pub const Attributes = struct {
            node: NodeReference,

            pub fn of(node: NodeReference) @This() {
                return .{ .node = node };
            }

            pub const child_identifier = "child_identifier";

            pub fn set_child_identifier(self: @This(), identifier: str) void {
                self.node.attributes.dynamic.values.put(child_identifier, .{ .String = identifier }) catch unreachable;
            }

            pub fn get_child_identifier(self: @This()) str {
                return self.node.attributes.dynamic.values.get(child_identifier).?.String;
            }
        };

        pub fn create_and_insert(tg: *TypeGraph, path: []const str) !BoundNodeReference {
            var root: ?BoundNodeReference = null;
            var current_node: ?BoundNodeReference = null;
            for (path) |segment| {
                const reference = try tg.instantiate_node(tg.reference_type);
                if (current_node) |_current_node| {
                    _ = try EdgeNext.add_next(_current_node, reference);
                } else {
                    root = reference;
                }
                ChildReferenceNode.Attributes.of(reference.node).set_child_identifier(segment);
                current_node = reference;
            }

            return root.?;
        }

        pub fn resolve(reference: BoundNodeReference, instance: BoundNodeReference) !graph.BoundNodeReference {
            // TODO iterate instead of recursion
            var target = instance;
            const child_identifier = ChildReferenceNode.Attributes.of(reference.node).get_child_identifier();

            const child = EdgeComposition.get_child_by_identifier(instance, child_identifier);
            if (child) |_child| {
                target = _child;
            }

            const next_reference = EdgeNext.get_next_node_from_node(reference);
            if (next_reference) |_next_reference| {
                const next_ref = reference.g.bind(_next_reference);
                target = try ChildReferenceNode.resolve(next_ref, target);
            }
            return target;
        }
    };

    pub const MakeLinkNode = struct {
        pub const Attributes = struct {
            node: NodeReference,

            pub fn of(node: NodeReference) @This() {
                return .{ .node = node };
            }

            pub const link_type_identifier = "link_type";

            pub fn set_link_type(self: @This(), link_type: Edge.EdgeType) void {
                self.node.attributes.dynamic.values.put(link_type_identifier, .{ .Int = link_type }) catch unreachable;
            }

            pub fn get_link_type(self: @This()) Edge.EdgeType {
                return self.node.attributes.dynamic.values.get(link_type_identifier).?.Int;
            }
        };
    };

    pub fn init(g: *GraphView) !TypeGraph {
        // Bootstrap first type and trait type-nodes and instance-nodes
        const implements_type_type = try TypeNode.create_and_insert(g, "ImplementsType");
        const implements_trait_type = try TypeNode.create_and_insert(g, "ImplementsTrait");

        // Assign the traits to the type-nodes
        _ = try TraitNode.add_trait_to(implements_type_type, implements_type_type);
        _ = try TraitNode.add_trait_to(implements_type_type, implements_trait_type);
        _ = try TraitNode.add_trait_to(implements_trait_type, implements_type_type);
        _ = try TraitNode.add_trait_to(implements_trait_type, implements_trait_type);

        var type_graph = TypeGraph{
            .implements_type_type = implements_type_type,
            .implements_trait_type = implements_trait_type,
            .make_child_type = undefined,
            .make_link_type = undefined,
            .reference_type = undefined,
            .g = g,
        };

        type_graph.make_child_type = try TypeNode.create_and_insert(type_graph.g, "MakeChild");
        _ = try TraitNode.add_trait_to(type_graph.make_child_type, type_graph.implements_type_type);

        type_graph.make_link_type = try TypeGraph.add_type(&type_graph, "MakeLink");
        type_graph.reference_type = try TypeGraph.add_type(&type_graph, "Reference");

        return type_graph;
    }

    pub fn add_type(self: *@This(), identifier: str) !BoundNodeReference {
        const type_node = try TypeNode.create_and_insert(self.g, identifier);

        // Add type trait
        const trait_implements_type_instance = try self.instantiate_node(self.implements_type_type);
        _ = try EdgeComposition.add_child(type_node, trait_implements_type_instance.node, null);

        return type_node;
    }

    pub fn add_trait(self: *@This()) !BoundNodeReference {
        const allocator = self.g.allocator;
        const trait = try self.g.insert_node(try Node.init(allocator));

        // Add trait trait
        const implements_trait_instance_node = try self.instantiate_node(self.implements_trait_type);
        _ = try EdgeType.add_instance(trait, implements_trait_instance_node);

        return trait;
    }

    pub fn add_make_child(self: *@This(), target_type: BoundNodeReference, child_type: BoundNodeReference, identifier: str) !BoundNodeReference {
        const make_child = try self.instantiate_node(self.make_child_type);
        MakeChildNode.Attributes.of(make_child.node).set_child_identifier(identifier);

        _ = try EdgePointer.point_to(make_child, child_type.node);
        _ = try EdgeComposition.add_child(target_type, make_child.node, null);

        return make_child;
    }

    pub fn add_make_link(self: *@This(), target_type: BoundNodeReference, lhs_reference: NodeReference, rhs_reference: NodeReference, link_type: Edge.EdgeType) !BoundNodeReference {
        const make_link = try self.instantiate_node(self.make_link_type);
        MakeLinkNode.Attributes.of(make_link.node).set_link_type(link_type);

        _ = try EdgeComposition.add_child(make_link, lhs_reference, "lhs");
        _ = try EdgeComposition.add_child(make_link, rhs_reference, "rhs");
        _ = try EdgeComposition.add_child(target_type, make_link.node, null);

        return make_link;
    }

    pub fn instantiate_node(tg: *@This(), type_node: BoundNodeReference) !graph.BoundNodeReference {
        // 1) Create instance and connect it to its type
        const new_instance = try type_node.g.insert_node(try Node.init(type_node.g.allocator));
        _ = try EdgeType.add_instance(type_node, new_instance);

        // 2) Visit MakeChild nodes of type_node
        const VisitMakeChildren = struct {
            type_graph: *TypeGraph,
            parent_instance_bnode: graph.BoundNodeReference,

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));

                const make_child = bound_edge.g.bind(EdgeComposition.get_child_node(bound_edge.edge));

                // 3) Resolve child instructions (identifier and type)
                const child_identifier = MakeChildNode.Attributes.of(make_child.node).get_child_identifier();
                const referenced_type = MakeChildNode.get_child_type(make_child);
                if (referenced_type == null) {
                    // TODO error?
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }

                // 4) Instantiate child
                const child = self.type_graph.instantiate_node(
                    self.type_graph.g.bind(referenced_type.?),
                ) catch |e| {
                    return visitor.VisitResult(void){ .ERROR = e };
                };

                // 5) Attach child instance to parent instance with the reference name
                _ = EdgeComposition.add_child(self.parent_instance_bnode, child.node, child_identifier) catch |e| {
                    return visitor.VisitResult(void){ .ERROR = e };
                };

                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var visit = VisitMakeChildren{
            .type_graph = tg,
            .parent_instance_bnode = new_instance,
        };
        _ = EdgeComposition.visit_children_of_type(type_node, tg.make_child_type.node, void, &visit, VisitMakeChildren.visit);

        // TODO: Make link implementation

        return new_instance;
    }

    pub fn instantiate(self: *@This(), type_identifier: str) !BoundNodeReference {
        std.debug.print("Instantiating type: {s}\n", .{type_identifier});
        // TODO make trait.zig

        // search for type of name
        const Finder = struct {
            self: *TypeGraph,
            type_identifier: str,

            pub fn visit(ctx_ptr: *anyopaque, bedge: graph.BoundEdgeReference) visitor.VisitResult(NodeReference) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const edge = bedge.edge;

                // Map the rest of the logic to the original selection, using BoundEdgeReference now.
                const implements_type_instance = ctx.self.g.bind(EdgeType.get_instance_node(edge).?);
                const parent_type_edge = EdgeComposition.get_parent_edge(implements_type_instance);
                const parent_type_node = EdgeComposition.get_parent_node(parent_type_edge.?.edge);
                const type_node_name = TypeNodeAttributes.of(parent_type_node).get_type_name();
                if (std.mem.eql(u8, type_node_name, ctx.type_identifier)) {
                    return visitor.VisitResult(NodeReference){ .OK = parent_type_node };
                }
                return visitor.VisitResult(NodeReference){ .CONTINUE = {} };
            }
        };

        var finder = Finder{ .self = self, .type_identifier = type_identifier };
        const result = self.implements_type_type.visit_edges_of_type(
            EdgeType.tid,
            NodeReference,
            &finder,
            Finder.visit,
        );

        switch (result) {
            .OK => |parent_type_node| {
                return try self.instantiate_node(self.g.bind(parent_type_node));
            },
            .ERROR => return error.InvalidArgument,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .EXHAUSTED => return error.InvalidArgument,
        }
    }
};

test "basic typegraph" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    var tg = try TypeGraph.init(&g);

    defer g.deinit();

    const Example = try tg.add_type("Example");
    var children = std.ArrayList(graph.BoundEdgeReference).init(a);
    defer children.deinit();
    const visit_result = EdgeComposition.visit_children_edges(Example, void, &children, visitor.collect(graph.BoundEdgeReference).collect_into_list);
    switch (visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }
    std.debug.print("TYPE collected children: {d}\n", .{children.items.len});
}

//zig test --dep graph -Mroot=src/faebryk/typegraph.zig -Mgraph=src/graph/lib.zig
test "basic instantiation" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    var tg = try TypeGraph.init(&g);

    // Build type graph
    const Electrical = try tg.add_type("Electrical");
    const Capacitor = try tg.add_type("Capacitor");
    _ = try tg.add_make_child(Capacitor, Electrical, "p1");
    _ = try tg.add_make_child(Capacitor, Electrical, "p2");
    const Resistor = try tg.add_type("Resistor");
    _ = try tg.add_make_child(Resistor, Electrical, "p1");
    _ = try tg.add_make_child(Resistor, Electrical, "p2");
    _ = try tg.add_make_child(Resistor, Capacitor, "cap1");

    // Build instance graph
    const resistor = try tg.instantiate_node(Resistor);

    // test: instance graph
    std.debug.print("Resistor Instance: {d}\n", .{resistor.node.attributes.uuid});
    const p1 = EdgeComposition.get_child_by_identifier(resistor, "p1").?;
    const p2 = EdgeComposition.get_child_by_identifier(resistor, "p2").?;
    const cap1 = EdgeComposition.get_child_by_identifier(resistor, "cap1").?;
    const cap1p1 = EdgeComposition.get_child_by_identifier(cap1, "p1").?;
    const cap1p2 = EdgeComposition.get_child_by_identifier(cap1, "p2").?;
    try std.testing.expect(EdgeType.is_node_instance_of(p1, Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(p2, Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1, Capacitor.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1p1, Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1p2, Electrical.node));

    // print children of resistor
    var resistor_children = std.ArrayList(graph.BoundEdgeReference).init(a);
    defer resistor_children.deinit();
    const resistor_visit_result = EdgeComposition.visit_children_edges(resistor, void, &resistor_children, visitor.collect(graph.BoundEdgeReference).collect_into_list);
    switch (resistor_visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }
    std.debug.print("TYPE collected children: {d}\n", .{resistor_children.items.len});

    // Build nested reference
    const cap1p1_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ "cap1", "p1" });
    const cap1p2_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ "cap1", "p2" });

    // test: resolve_instance_reference
    const cap1p1_reference_resolved = try TypeGraph.ChildReferenceNode.resolve(cap1p1_reference, resistor);
    try std.testing.expect(Node.is_same(cap1p1_reference_resolved.node, cap1p1.node));

    // Build make link
    // TODO: use interface link
    _ = try tg.add_make_link(Resistor, cap1p1_reference.node, cap1p2_reference.node, EdgePointer.tid);

    const instantiated_resistor = try tg.instantiate("Resistor");
    const instantiated_p1 = EdgeComposition.get_child_by_identifier(instantiated_resistor, "p1").?;
    const instantiated_cap = EdgeComposition.get_child_by_identifier(instantiated_resistor, "cap1").?;
    const instantiated_cap_p1 = EdgeComposition.get_child_by_identifier(instantiated_cap, "p1").?;
    const instantiated_cap_p2 = EdgeComposition.get_child_by_identifier(instantiated_cap, "p2").?;
    std.debug.print("Instantiated Resistor Instance: {d}\n", .{instantiated_resistor.node.attributes.uuid});
    std.debug.print("Instantiated P1 Instance: {d}\n", .{instantiated_p1.node.attributes.uuid});
    // TODO test link

    defer g.deinit();

    const _Visit = struct {
        seek: BoundNodeReference,

        pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(self_ptr));
            std.testing.expect(EdgePointer.is_instance(bound_edge.edge)) catch return visitor.VisitResult(void){ .ERROR = error.InvalidArgument };
            if (EdgePointer.get_referenced_node(bound_edge.edge)) |referenced_node| {
                if (Node.is_same(referenced_node, self.seek.node)) {
                    return visitor.VisitResult(void){ .OK = {} };
                }
            }
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };
    var _visit = _Visit{ .seek = instantiated_cap_p2 };
    const result = instantiated_cap_p1.visit_edges_of_type(EdgePointer.tid, void, &_visit, _Visit.visit);
    try std.testing.expect(result == .OK);
}
