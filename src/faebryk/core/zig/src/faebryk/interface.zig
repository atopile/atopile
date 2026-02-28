const graph_import = @import("graph");
const graph = graph_import.graph;
const visitor = graph_import.visitor;
const std = @import("std");
const PathFinder = @import("pathfinder.zig").PathFinder;
const EdgeComposition = @import("composition.zig").EdgeComposition;
const edgebuilder_mod = @import("edgebuilder.zig");
const TypeGraph = @import("typegraph.zig").TypeGraph;
const EdgeType = @import("node_type.zig").EdgeType;
const Linker = @import("linker.zig").Linker;
const Trait = @import("trait.zig").Trait;

const Node = graph.Node;
const NodeReference = graph.NodeReference;
const BoundNodeReference = graph.BoundNodeReference;

const Edge = graph.Edge;
const EdgeReference = graph.EdgeReference;
const BoundEdgeReference = graph.BoundEdgeReference;

const GraphView = graph.GraphView;
const str = graph.str;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;

pub const EdgeInterfaceConnection = struct {
    pub const tid: Edge.EdgeType = graph.Edge.hash_edge_type(1759242069);
    pub var registered: bool = false;
    pub const shallow_attribute = "shallow";

    pub fn get_tid() Edge.EdgeType {
        return tid;
    }

    pub fn init(N1: NodeReference, N2: NodeReference, shallow: bool) !EdgeReference {
        const edge = EdgeReference.init(N1, N2, tid);
        const attrs = try build(shallow);
        attrs.apply_to(edge);
        return edge;
    }

    pub fn build(shallow: bool) !EdgeCreationAttributes {
        var dynamic = graph.DynamicAttributes.init_on_stack();
        dynamic.put(shallow_attribute, .{ .Bool = shallow });
        if (!registered) {
            @branchHint(.unlikely);
            registered = true;
            Edge.register_type(tid) catch {};
        }
        return .{
            .edge_type = tid,
            .directional = false,
            .name = null,
            .dynamic = dynamic,
        };
    }

    pub fn connect(bn1: BoundNodeReference, bn2: BoundNodeReference) !BoundEdgeReference {
        const bn1_type_edge = EdgeType.get_type_edge(bn1);
        const bn2_type_edge = EdgeType.get_type_edge(bn2);

        if (bn1_type_edge == null and bn2_type_edge == null) {
            // no type information on either node – allow connection
        } else if (bn1_type_edge == null or bn2_type_edge == null) {
            return error.IncompatibleTypes;
        } else {
            const type1 = EdgeType.get_type_node(bn1_type_edge.?.edge);
            const type2 = EdgeType.get_type_node(bn2_type_edge.?.edge);

            if (!type1.is_same(type2)) {
                return error.IncompatibleTypes;
            }
        }

        return try bn1.g.insert_edge(try EdgeInterfaceConnection.init(bn1.node, bn2.node, false));
    }

    pub fn connect_shallow(bn1: BoundNodeReference, bn2: BoundNodeReference) !BoundEdgeReference {
        const bn1_type_edge = EdgeType.get_type_edge(bn1);
        const bn2_type_edge = EdgeType.get_type_edge(bn2);

        if (bn1_type_edge == null and bn2_type_edge == null) {
            // no type information on either node – allow connection
        } else if (bn1_type_edge == null or bn2_type_edge == null) {
            return error.IncompatibleTypes;
        } else {
            const type1 = EdgeType.get_type_node(bn1_type_edge.?.edge);
            const type2 = EdgeType.get_type_node(bn2_type_edge.?.edge);

            if (!type1.is_same(type2)) {
                return error.IncompatibleTypes;
            }
        }

        return try bn1.g.insert_edge(try EdgeInterfaceConnection.init(bn1.node, bn2.node, true));
    }

    pub fn is_instance(E: EdgeReference) bool {
        return E.is_instance(tid);
    }

    pub fn get_other_connected_node(E: EdgeReference, N: NodeReference) ?NodeReference {
        if (E.get_source_node().is_same(N)) {
            return E.get_target_node();
        } else if (E.get_target_node().is_same(N)) {
            return E.get_source_node();
        } else {
            return null;
        }
    }

    pub fn visit_connected_edges(
        bound_node: graph.BoundNodeReference,
        ctx: *anyopaque,
        f: fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),
    ) visitor.VisitResult(void) {
        return bound_node.g.visit_edges_of_type(bound_node.node, tid, void, ctx, f, null);
    }

    pub fn is_connected_to(allocator: std.mem.Allocator, source: BoundNodeReference, target: BoundNodeReference) !*graph.BFSPath {
        var pf: PathFinder = undefined;
        pf.init(allocator);
        defer pf.deinit();

        var paths = try pf.find_paths(source);
        defer paths.deinit();

        for (paths.paths.items, 0..) |path, i| {
            if (path.get_last_node().node.is_same(target.node)) {
                // Transfer ownership by removing from collection
                return paths.paths.swapRemove(i);
            }
        }

        // No path found - return empty path
        return try graph.BFSPath.init(allocator, source);
    }

    // TODO - A visitor would be nice instead of just returning a list don't ya think?
    pub fn get_connected(allocator: std.mem.Allocator, source: BoundNodeReference, include_self: bool) !graph.NodeRefMap.T(*graph.BFSPath) {
        var pf: PathFinder = undefined;
        pf.init(allocator);
        defer pf.deinit();

        var paths = try pf.find_paths(source);
        defer paths.paths.deinit(); // Clean up the ArrayList, but not the paths themselves (transferred to map)

        var paths_map = graph.NodeRefMap.T(*graph.BFSPath).init(allocator);

        for (paths.paths.items) |path| {
            const end_node = path.get_last_node().node;

            // Skip self-path if include_self is false
            if (!include_self and end_node.is_same(source.node)) {
                path.deinit();
                continue;
            }

            // Only add the first path to each destination node
            if (!paths_map.contains(end_node)) {
                paths_map.put(end_node, path) catch @panic("OOM");
            } else {
                // Skip duplicate path and clean it up
                path.deinit();
            }
        }

        return paths_map;
    }
};

const a = std.testing.allocator;

const is_interface_type_name = "is_interface.node.core.faebryk";

const TestTypes = struct {
    is_interface: BoundNodeReference,
    electrical: BoundNodeReference,
    generic: BoundNodeReference,
    electric_power: BoundNodeReference,
};

fn ensure_is_interface_type(tg: *TypeGraph) !BoundNodeReference {
    if (tg.get_type_by_name(is_interface_type_name)) |trait_type| {
        return trait_type;
    }
    const trait_type = try tg.add_type(is_interface_type_name);
    try tg.mark_constructable(trait_type);
    try Trait.mark_as_trait(trait_type);
    return trait_type;
}

fn init_test_types(tg: *TypeGraph) !TestTypes {
    const is_interface = try ensure_is_interface_type(tg);
    const electrical = try tg.add_type("Electrical");
    try tg.mark_constructable(electrical);
    const generic = try tg.add_type("Generic");
    try tg.mark_constructable(generic);
    const electric_power = try tg.add_type("ElectricPower");
    return .{
        .is_interface = is_interface,
        .electrical = electrical,
        .generic = generic,
        .electric_power = electric_power,
    };
}

fn add_is_interface_recursive(tg: *TypeGraph, root: BoundNodeReference) !void {
    const trait_type = try ensure_is_interface_type(tg);
    var stack = std.array_list.Managed(BoundNodeReference).init(a);
    defer stack.deinit();
    try stack.append(root);

    while (stack.items.len > 0) {
        const node = stack.pop().?;
        _ = try Trait.add_trait_to(node, trait_type);

        const CollectChildren = struct {
            stack: *std.array_list.Managed(BoundNodeReference),
            g: *GraphView,

            pub fn visit_edge(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const child = self.g.bind(EdgeComposition.get_child_node(bound_edge.edge));
                self.stack.append(child) catch @panic("OOM");
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var collect = CollectChildren{ .stack = &stack, .g = node.g };
        _ = EdgeComposition.visit_children_edges(node, void, &collect, CollectChildren.visit_edge);
    }
}

fn instantiate_interface(tg: *TypeGraph, node_type: BoundNodeReference) !BoundNodeReference {
    const node = switch (tg.instantiate_node(node_type)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    try add_is_interface_recursive(tg, node);
    return node;
}

test "basic" {
    // N1 --> N2
    // N1 --> N3
    // Allocate some nodes and edges
    var g = graph.GraphView.init(a);
    defer g.deinit(); // Graph owns all inserted nodes/edges and handles their cleanup

    var tg = TypeGraph.init(&g);
    const electrical_type = try tg.add_type("Electrical");
    try tg.mark_constructable(electrical_type);

    const bn1 = try instantiate_interface(&tg, electrical_type);
    const bn2 = try instantiate_interface(&tg, electrical_type);
    const bn3 = try instantiate_interface(&tg, electrical_type);

    const n1 = bn1.node;
    const n2 = bn2.node;
    const n3 = bn3.node;

    std.debug.print("n1.uuid = {}\n", .{n1.get_uuid()});
    std.debug.print("n2.uuid = {}\n", .{n2.get_uuid()});
    std.debug.print("n3.uuid = {}\n", .{n3.get_uuid()});

    const be1 = try EdgeInterfaceConnection.connect(bn1, bn2);

    std.debug.print("e1.uuid = {}\n", .{be1.edge.get_uuid()});
    std.debug.print("e1.source.uuid = {}\n", .{be1.edge.get_source_node().get_uuid()});
    std.debug.print("e1.target.uuid = {}\n", .{be1.edge.get_target_node().get_uuid()});

    std.debug.print("n2.uuid = {}\n", .{n2.get_uuid()});

    std.debug.print("e1.source.uuid = {}\n", .{be1.edge.get_source_node().get_uuid()});
    std.debug.print("e1.target.uuid = {}\n", .{be1.edge.get_target_node().get_uuid()});

    // Expect shallow flag to be present and false by default
    const shallow_default = be1.edge.get(EdgeInterfaceConnection.shallow_attribute).?;
    try std.testing.expect(shallow_default.Bool == false);

    // Expect e1 source and target to match n1 and n2
    try std.testing.expect(be1.edge.get_source_node().is_same(n1));
    try std.testing.expect(be1.edge.get_target_node().is_same(n2));

    // Expect e1 source and target to not match n3
    try std.testing.expect(!be1.edge.get_source_node().is_same(n3));
    try std.testing.expect(!be1.edge.get_target_node().is_same(n3));

    // Expect get_connected to return n2 when given n1
    try std.testing.expect(EdgeInterfaceConnection.get_other_connected_node(be1.edge, n1).?.is_same(n2));

    // Expect get_connected to return n1 when given n2
    try std.testing.expect(EdgeInterfaceConnection.get_other_connected_node(be1.edge, n2).?.is_same(n1));

    // Expect get_connected to return null when given n3
    try std.testing.expect(EdgeInterfaceConnection.get_other_connected_node(be1.edge, n3) == null);

    // Create another connection between n1 and n3 to test multiple connections
    const be2 = try EdgeInterfaceConnection.connect(bn1, bn3);
    try std.testing.expect(be2.edge.get_source_node().is_same(n1));
    try std.testing.expect(be2.edge.get_target_node().is_same(n3));

    // define visitor that visits all edges connected to n1 in g and saves the EdgeReferences to a list (connected_edges)
    const CollectConnectedEdges = struct {
        connected_edges: std.array_list.Managed(graph.BoundEdgeReference),

        pub fn visit(self_ptr: *anyopaque, connected_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(self_ptr));

            self.connected_edges.append(connected_edge) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };

            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    // instantiate visitor
    var visit = CollectConnectedEdges{ .connected_edges = std.array_list.Managed(graph.BoundEdgeReference).init(a) };
    defer visit.connected_edges.deinit();
    // call visitor
    const result = EdgeInterfaceConnection.visit_connected_edges(bn1, &visit, CollectConnectedEdges.visit);
    _ = result;

    // check the visitor is correct - should find 2 edges (n1->n2 and n1->n3)
    try std.testing.expectEqual(visit.connected_edges.items.len, 2);
    // Verify one edge connects to n2
    var found_n2 = false;
    var found_n3 = false;
    for (visit.connected_edges.items) |edge| {
        if (edge.edge.get_source_node().is_same(n1) or edge.edge.get_target_node().is_same(n1)) {
            if (edge.edge.get_source_node().is_same(n2) or edge.edge.get_target_node().is_same(n2)) {
                found_n2 = true;
            }
            if (edge.edge.get_source_node().is_same(n3) or edge.edge.get_target_node().is_same(n3)) {
                found_n3 = true;
            }
        }
    }
    try std.testing.expect(found_n2);
    try std.testing.expect(found_n3);
}

// Helper function for tests to check that no path exists
fn expectNoPath(allocator: std.mem.Allocator, source: graph.BoundNodeReference, target: graph.BoundNodeReference) !void {
    const path = try EdgeInterfaceConnection.is_connected_to(allocator, source, target);
    defer path.deinit();
    try std.testing.expectEqual(@as(usize, 0), path.traversed_edges.items.len);
}

test "self_connect" {
    // N1 (self-connect implied)
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const electrical_type = try tg.add_type("Electrical");
    try tg.mark_constructable(electrical_type);
    const bn1 = try instantiate_interface(&tg, electrical_type);
    const bn2 = try instantiate_interface(&tg, electrical_type);

    // expect not connected (empty path)
    try expectNoPath(a, bn1, bn2);

    // expect connected
    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn1);
    defer path.deinit();
    try std.testing.expect(path.get_last_node().node.is_same(bn1.node));
}

test "is_connected_to" {
    //     A
    //    / \
    //   B   C
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    const bn1 = try instantiate_interface(&tg, test_types.electrical);
    const bn2 = try instantiate_interface(&tg, test_types.electrical);
    const bn3 = try instantiate_interface(&tg, test_types.electrical);
    _ = try EdgeInterfaceConnection.connect(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn1, bn3);

    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn2);
    defer path.deinit();
    try std.testing.expect(path.get_last_node().node.is_same(bn2.node));
}

test "simple_electric_power_hierarchy" {
    // ElectricPower (EP_1)
    //   |
    //   +--(ref)--> ElectricSignal (signal_1) --(iface)--> ElectricSignal (signal_2)
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    const electric_signal = try tg.add_type("ElectricSignal");

    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "HV", null);
    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "LV", null);
    try tg.mark_constructable(test_types.electric_power);
    _ = try tg.add_make_child(electric_signal, test_types.electrical, "line", null);
    _ = try tg.add_make_child(electric_signal, test_types.electric_power, "reference", null);
    try tg.mark_constructable(electric_signal);

    const EP_1 = try instantiate_interface(&tg, test_types.electric_power);
    const HV_1 = EdgeComposition.get_child_by_identifier(EP_1, "HV").?;
    const signal_1 = try instantiate_interface(&tg, electric_signal);
    const signal_2 = try instantiate_interface(&tg, electric_signal);
    const signal_1_reference = EdgeComposition.get_child_by_identifier(signal_1, "reference").?;

    const extra_electric_signal = try instantiate_interface(&tg, electric_signal);
    const extra_electrical = EdgeComposition.get_child_by_identifier(extra_electric_signal, "line").?;

    const EP_2 = try instantiate_interface(&tg, test_types.electric_power);
    const LV_2 = EdgeComposition.get_child_by_identifier(EP_2, "LV").?;

    _ = try EdgeInterfaceConnection.connect(EP_1, signal_1_reference);
    _ = try EdgeInterfaceConnection.connect(signal_1, signal_2);
    _ = try EdgeInterfaceConnection.connect(extra_electrical, HV_1);

    _ = try EdgeInterfaceConnection.connect(EP_1, EP_2);
    // _ = try EdgeInterfaceConnection.connect(HV_1, LV_2);
    _ = LV_2;

    var paths = try EdgeInterfaceConnection.get_connected(a, HV_1, true);
    defer {
        var it = paths.iterator();
        while (it.next()) |entry| {
            entry.value_ptr.*.deinit();
        }
        paths.deinit();
    }
}

test "down_connect" {
    // P1 --> P2
    //  |      |
    // HV     HV
    // LV     LV
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);
    // const LinkType = try tg.add_type("Link");

    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "HV", null);
    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "LV", null);
    try tg.mark_constructable(test_types.electric_power);

    const EP_1 = try instantiate_interface(&tg, test_types.electric_power);
    const HV_1 = EdgeComposition.get_child_by_identifier(EP_1, "HV").?;
    const LV_1 = EdgeComposition.get_child_by_identifier(EP_1, "LV").?;

    const EP_2 = try instantiate_interface(&tg, test_types.electric_power);
    const HV_2 = EdgeComposition.get_child_by_identifier(EP_2, "HV").?;
    const LV_2 = EdgeComposition.get_child_by_identifier(EP_2, "LV").?;

    _ = try EdgeInterfaceConnection.connect(EP_1, EP_2);

    var path = try EdgeInterfaceConnection.is_connected_to(a, EP_1, EP_2);
    defer path.deinit();
    try std.testing.expect(path.get_last_node().node.is_same(EP_2.node));

    var path_hv = try EdgeInterfaceConnection.is_connected_to(a, HV_1, HV_2);
    defer path_hv.deinit();
    try std.testing.expect(path_hv.get_last_node().node.is_same(HV_2.node));

    var path_lv = try EdgeInterfaceConnection.is_connected_to(a, LV_1, LV_2);
    defer path_lv.deinit();
    try std.testing.expect(path_lv.get_last_node().node.is_same(LV_2.node));

    try expectNoPath(a, HV_1, LV_2);
    try expectNoPath(a, LV_1, HV_2);

    const link_a = try instantiate_interface(&tg, test_types.electrical);
    const link_b = try instantiate_interface(&tg, test_types.electrical);
    const link_c = try instantiate_interface(&tg, test_types.electrical);
    _ = try EdgeInterfaceConnection.connect(HV_1, link_a);
    _ = try EdgeInterfaceConnection.connect(link_a, link_b);
    _ = try EdgeInterfaceConnection.connect(link_b, link_c);
    _ = try EdgeInterfaceConnection.connect(link_c, LV_2);

    var path_hv_link_lv = try EdgeInterfaceConnection.is_connected_to(a, HV_1, LV_2);
    defer path_hv_link_lv.deinit();
    try std.testing.expect(path_hv_link_lv.get_last_node().node.is_same(LV_2.node));

    const HV_1_Child = try instantiate_interface(&tg, test_types.electrical);
    _ = try EdgeComposition.add_child(HV_1, HV_1_Child.node, "HV/LV Child");

    _ = try EdgeInterfaceConnection.connect(HV_1, LV_2);
    try expectNoPath(a, HV_1_Child, LV_2);
}

test "no_connect_cases" {
    // N1 --> N2 <-- N3
    //        |        \
    //        v         v
    //       N5 <-- N4
    //        ^
    //        |
    //       N6
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const GenericType = try tg.add_type("Generic");
    try tg.mark_constructable(GenericType);

    const bn1 = try instantiate_interface(&tg, GenericType);
    const bn2 = try instantiate_interface(&tg, GenericType);
    const bn3 = try instantiate_interface(&tg, GenericType);
    const bn4 = try instantiate_interface(&tg, GenericType);
    const bn5 = try instantiate_interface(&tg, GenericType);
    const bn6 = try instantiate_interface(&tg, GenericType);

    _ = try EdgeComposition.add_child(bn1, bn2.node, null);
    _ = try EdgeComposition.add_child(bn3, bn2.node, null);
    _ = try EdgeInterfaceConnection.connect(bn3, bn4);
    _ = try EdgeComposition.add_child(bn5, bn4.node, null);
    _ = try EdgeComposition.add_child(bn6, bn1.node, null);
    _ = try EdgeComposition.add_child(bn6, bn3.node, null);

    try expectNoPath(a, bn1, bn2);
    try expectNoPath(a, bn1, bn3);
    try expectNoPath(a, bn1, bn5);
}

test "chains_direct" {
    // M1 --> M2 --> M3
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    const M1 = try instantiate_interface(&tg, test_types.electrical);
    const M2 = try instantiate_interface(&tg, test_types.electrical);
    const M3 = try instantiate_interface(&tg, test_types.electrical);

    _ = try EdgeInterfaceConnection.connect(M1, M2);
    _ = try EdgeInterfaceConnection.connect(M2, M3);

    var path = try EdgeInterfaceConnection.is_connected_to(a, M1, M3);
    defer path.deinit();
    try std.testing.expect(path.get_last_node().node.is_same(M3.node));
}

test "chains_double_shallow_flat" {
    // N1 ==> N2 ==> N3
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    const bn1 = try instantiate_interface(&tg, test_types.electrical);
    const bn2 = try instantiate_interface(&tg, test_types.electrical);
    const bn3 = try instantiate_interface(&tg, test_types.electrical);

    _ = try EdgeInterfaceConnection.connect_shallow(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect_shallow(bn2, bn3);

    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn3);
    defer path.deinit();
    try std.testing.expect(path.get_last_node().node.is_same(bn3.node));
}

test "chains_mixed_shallow_flat" {
    // N1 ==> N2 --> N3
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    const bn1 = try instantiate_interface(&tg, test_types.electrical);
    const bn2 = try instantiate_interface(&tg, test_types.electrical);
    const bn3 = try instantiate_interface(&tg, test_types.electrical);

    _ = try EdgeInterfaceConnection.connect_shallow(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn2, bn3);

    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn3);
    defer path.deinit();
    try std.testing.expect(path.get_last_node().node.is_same(bn3.node));
}

test "multiple_paths" {
    //         N5
    //        /
    // N1 ---N2--> N4 --> N7
    //   \        ^
    //    N3 ----+
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    const bn1 = try instantiate_interface(&tg, test_types.electrical);
    const bn2 = try instantiate_interface(&tg, test_types.electrical);
    const bn3 = try instantiate_interface(&tg, test_types.electrical);
    const bn4 = try instantiate_interface(&tg, test_types.electrical);
    const bn5 = try instantiate_interface(&tg, test_types.electrical);
    const bn6 = try instantiate_interface(&tg, test_types.electrical);
    const bn7 = try instantiate_interface(&tg, test_types.electrical);

    _ = try EdgeInterfaceConnection.connect(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn2, bn4);
    _ = try EdgeInterfaceConnection.connect(bn1, bn3);
    _ = try EdgeInterfaceConnection.connect(bn3, bn6);
    _ = try EdgeInterfaceConnection.connect(bn6, bn4);
    _ = try EdgeInterfaceConnection.connect(bn1, bn5);
    _ = try EdgeInterfaceConnection.connect(bn4, bn7);

    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn4);
    defer path.deinit();
    try std.testing.expect(path.get_last_node().node.is_same(bn4.node));

    var all_paths = try EdgeInterfaceConnection.get_connected(a, bn1, true);

    defer {
        var it = all_paths.iterator();
        while (it.next()) |entry| {
            entry.value_ptr.*.deinit();
        }
        all_paths.deinit();
    }

    try std.testing.expect(all_paths.count() == 7);
}

test "hierarchy_short" {
    // ElectricPower
    //   |      |
    //  HV --> LinkA --> LinkB --> LV
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "HV", null);
    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "LV", null);
    try tg.mark_constructable(test_types.electric_power);

    const electric_power = try instantiate_interface(&tg, test_types.electric_power);
    const hv_pin = EdgeComposition.get_child_by_identifier(electric_power, "HV").?;
    const lv_pin = EdgeComposition.get_child_by_identifier(electric_power, "LV").?;

    try expectNoPath(a, electric_power, lv_pin);

    const link_a = try instantiate_interface(&tg, test_types.electrical);
    const link_b = try instantiate_interface(&tg, test_types.electrical);

    _ = try EdgeInterfaceConnection.connect(hv_pin, link_a);
    _ = try EdgeInterfaceConnection.connect(link_a, link_b);
    _ = try EdgeInterfaceConnection.connect(link_b, lv_pin);

    var hv_to_lv = try EdgeInterfaceConnection.is_connected_to(a, hv_pin, lv_pin);
    defer hv_to_lv.deinit();
    try std.testing.expect(hv_to_lv.get_last_node().node.is_same(lv_pin.node));
}

test "indirect_short" {
    // EP0 --- EP1 --- EP2
    //  |             |
    //  HV --------- LV
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "HV", null);
    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "LV", null);
    try tg.mark_constructable(test_types.electric_power);

    const ep0 = try instantiate_interface(&tg, test_types.electric_power);
    const ep1 = try instantiate_interface(&tg, test_types.electric_power);
    const ep2 = try instantiate_interface(&tg, test_types.electric_power);

    const ep0_hv = EdgeComposition.get_child_by_identifier(ep0, "HV").?;
    const ep1_hv = EdgeComposition.get_child_by_identifier(ep1, "HV").?;
    const ep1_lv = EdgeComposition.get_child_by_identifier(ep1, "LV").?;
    const ep2_lv = EdgeComposition.get_child_by_identifier(ep2, "LV").?;

    _ = try EdgeInterfaceConnection.connect(ep0, ep1);
    _ = try EdgeInterfaceConnection.connect(ep1, ep2);

    try expectNoPath(a, ep1_hv, ep1_lv);

    _ = try EdgeInterfaceConnection.connect(ep0_hv, ep2_lv);

    var ep1_short = try EdgeInterfaceConnection.is_connected_to(a, ep1_hv, ep1_lv);
    defer ep1_short.deinit();
    try std.testing.expect(ep1_short.get_last_node().node.is_same(ep1_lv.node));
}

test "shallow_filter_allows_alternative_route" {
    // P1 ==> P2 (shallow)
    //  |       |
    // HV ---- Bus --- HV
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "HV", null);
    _ = try tg.add_make_child(test_types.electric_power, test_types.electrical, "LV", null);
    try tg.mark_constructable(test_types.electric_power);

    const start_parent = try instantiate_interface(&tg, test_types.electric_power);
    const start_child = EdgeComposition.get_child_by_identifier(start_parent, "HV").?;
    const target_parent = try instantiate_interface(&tg, test_types.electric_power);
    const target_child = EdgeComposition.get_child_by_identifier(target_parent, "HV").?;
    const bus = try instantiate_interface(&tg, test_types.electrical);

    _ = try EdgeInterfaceConnection.connect_shallow(start_parent, target_parent);

    _ = try EdgeInterfaceConnection.connect(start_child, bus);
    _ = try EdgeInterfaceConnection.connect(bus, target_child);

    var path = try EdgeInterfaceConnection.is_connected_to(a, start_child, target_child);
    defer path.deinit();
    try std.testing.expect(path.get_last_node().node.is_same(target_child.node));
}

test "chains_mixed_shallow_nested" {
    // El0 ==> El1 --> El2
    //  |       |
    // Line    Line
    //  |       |
    // Ref     Ref
    //  |       |
    // HV      HV
    // LV      LV
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const LineType = try tg.add_type("Line");
    try tg.mark_constructable(LineType);
    const HVType = try tg.add_type("HV");
    try tg.mark_constructable(HVType);
    const LVType = try tg.add_type("LV");
    try tg.mark_constructable(LVType);
    const RefType = try tg.add_type("Ref");
    _ = try tg.add_make_child(RefType, HVType, "hv", null);
    _ = try tg.add_make_child(RefType, LVType, "lv", null);
    try tg.mark_constructable(RefType);
    const ElType = try tg.add_type("El");
    _ = try tg.add_make_child(ElType, LineType, "line", null);
    _ = try tg.add_make_child(ElType, RefType, "reference", null);
    try tg.mark_constructable(ElType);

    var el: [3]graph.BoundNodeReference = undefined;
    for (&el) |*slot| slot.* = try instantiate_interface(&tg, ElType);

    var line: [3]graph.BoundNodeReference = undefined;
    var reference: [3]graph.BoundNodeReference = undefined;
    var hv: [3]graph.BoundNodeReference = undefined;
    var lv: [3]graph.BoundNodeReference = undefined;

    for (el, 0..) |node, idx| {
        line[idx] = EdgeComposition.get_child_by_identifier(node, "line").?;
        reference[idx] = EdgeComposition.get_child_by_identifier(node, "reference").?;
        hv[idx] = EdgeComposition.get_child_by_identifier(reference[idx], "hv").?;
        lv[idx] = EdgeComposition.get_child_by_identifier(reference[idx], "lv").?;
    }

    _ = try EdgeInterfaceConnection.connect_shallow(el[0], el[1]);
    _ = try EdgeInterfaceConnection.connect(el[1], el[2]);

    var el_path = try EdgeInterfaceConnection.is_connected_to(a, el[0], el[2]);
    defer el_path.deinit();
    try std.testing.expect(el_path.get_last_node().node.is_same(el[2].node));

    var line_path = try EdgeInterfaceConnection.is_connected_to(a, line[1], line[2]);
    defer line_path.deinit();
    try std.testing.expect(line_path.get_last_node().node.is_same(line[2].node));

    var ref_path = try EdgeInterfaceConnection.is_connected_to(a, reference[1], reference[2]);
    defer ref_path.deinit();
    try std.testing.expect(ref_path.get_last_node().node.is_same(reference[2].node));

    try expectNoPath(a, line[0], line[1]);
    try expectNoPath(a, reference[0], reference[1]);
    try expectNoPath(a, line[0], line[2]);
    try expectNoPath(a, reference[0], reference[2]);

    _ = try EdgeInterfaceConnection.connect(line[0], line[1]);
    _ = try EdgeInterfaceConnection.connect(reference[0], reference[1]);

    var el_up = try EdgeInterfaceConnection.is_connected_to(a, el[0], el[1]);
    defer el_up.deinit();
    try std.testing.expect(el_up.get_last_node().node.is_same(el[1].node));

    var el_full = try EdgeInterfaceConnection.is_connected_to(a, el[0], el[2]);
    defer el_full.deinit();
    try std.testing.expect(el_full.get_last_node().node.is_same(el[2].node));
}

test "split_flip_negative" {
    // H1     H2
    //  L1 --> L2
    //  L2 --> L1
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const LowType = try tg.add_type("Low");
    try tg.mark_constructable(LowType);
    const HighType = try tg.add_type("High");
    _ = try tg.add_make_child(HighType, LowType, "lower1", null);
    _ = try tg.add_make_child(HighType, LowType, "lower2", null);
    try tg.mark_constructable(HighType);

    var high: [2]graph.BoundNodeReference = undefined;
    for (&high) |*slot| slot.* = try instantiate_interface(&tg, HighType);

    var lower1: [2]graph.BoundNodeReference = undefined;
    var lower2: [2]graph.BoundNodeReference = undefined;
    for (high, 0..) |node, idx| {
        lower1[idx] = EdgeComposition.get_child_by_identifier(node, "lower1").?;
        lower2[idx] = EdgeComposition.get_child_by_identifier(node, "lower2").?;
    }

    _ = try EdgeInterfaceConnection.connect(lower1[0], lower2[1]);
    _ = try EdgeInterfaceConnection.connect(lower2[0], lower1[1]);

    try expectNoPath(a, high[0], high[1]);
}

test "up_connect_simple_two_negative" {
    // H1      H2
    //  L1 -->  L1
    //  L2      L2
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const Lower1Type = try tg.add_type("Lower1");
    try tg.mark_constructable(Lower1Type);
    const Lower2Type = try tg.add_type("Lower2");
    try tg.mark_constructable(Lower2Type);
    const HighType = try tg.add_type("High");
    _ = try tg.add_make_child(HighType, Lower1Type, "lower1", null);
    _ = try tg.add_make_child(HighType, Lower2Type, "lower2", null);
    try tg.mark_constructable(HighType);

    var high: [2]graph.BoundNodeReference = undefined;
    for (&high) |*slot| slot.* = try instantiate_interface(&tg, HighType);

    var lower1: [2]graph.BoundNodeReference = undefined;
    var lower2: [2]graph.BoundNodeReference = undefined;
    for (high, 0..) |node, idx| {
        lower1[idx] = EdgeComposition.get_child_by_identifier(node, "lower1").?;
        lower2[idx] = EdgeComposition.get_child_by_identifier(node, "lower2").?;
    }

    _ = try EdgeInterfaceConnection.connect(lower1[0], lower1[1]);

    try expectNoPath(a, high[0], high[1]);
}

test "loooooong_chain" {
    // N0 --> N1 --> ... --> N1000
    // Let's make it hard - create a long chain of nodes
    // Use a more efficient allocator for this stress test instead of testing allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var g = graph.GraphView.init(allocator);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    const chain_length = 1000;
    var nodes = std.array_list.Managed(graph.BoundNodeReference).init(allocator);
    defer nodes.deinit();

    // Pre-allocate capacity to avoid repeated reallocations
    try nodes.ensureTotalCapacity(chain_length);

    std.debug.print("\nBuilding chain of {} nodes...\n", .{chain_length});

    // Create nodes
    var i: usize = 0;
    while (i < chain_length) : (i += 1) {
        if (i % 1000 == 0 and i > 0) {
            std.debug.print("  Created {} nodes...\n", .{i});
        }
        const node = try instantiate_interface(&tg, test_types.electrical);
        nodes.appendAssumeCapacity(node);
    }
    std.debug.print("  All {} nodes created.\n", .{chain_length});

    // Connect consecutive nodes
    std.debug.print("  Connecting nodes...\n", .{});
    i = 0;
    while (i < chain_length - 1) : (i += 1) {
        if (i % 10000 == 0 and i > 0) {
            std.debug.print("  Connected {} edges...\n", .{i});
        }
        _ = try EdgeInterfaceConnection.connect(nodes.items[i], nodes.items[i + 1]);
    }

    std.debug.print("Chain built. Starting pathfinding...\n", .{});

    // Start timer
    var timer = try std.time.Timer.start();

    // Test pathfinding from first to last node
    var path = try EdgeInterfaceConnection.is_connected_to(allocator, nodes.items[0], nodes.items[chain_length - 1]);
    defer path.deinit();

    // Stop timer
    const elapsed = timer.read();
    const elapsed_ms = elapsed / std.time.ns_per_ms;
    const elapsed_s = @as(f64, @floatFromInt(elapsed)) / @as(f64, @floatFromInt(std.time.ns_per_s));

    std.debug.print("\nPathfinding completed!\n", .{});
    std.debug.print("  Total paths explored: N/A (using is_connected_to)\n", .{});
    std.debug.print("  Valid paths found: 1\n", .{});
    std.debug.print("  Time: {d:.3}s ({} ms)\n", .{ elapsed_s, elapsed_ms });

    // Verify we found a path to the correct target
    try std.testing.expect(path.get_last_node().node.is_same(nodes.items[chain_length - 1].node));
}

test "shallow_edges" {
    // N1 --> N2 --> N3
    //      ||
    //      || (shallow)
    //      ||
    // N4 --> N5 --> N6
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const test_types = try init_test_types(&tg);

    const bn1 = try instantiate_interface(&tg, test_types.generic);
    const bn2 = try instantiate_interface(&tg, test_types.generic);
    const bn3 = try instantiate_interface(&tg, test_types.generic);
    const bn4 = try instantiate_interface(&tg, test_types.generic);
    const bn5 = try instantiate_interface(&tg, test_types.generic);
    const bn6 = try instantiate_interface(&tg, test_types.generic);

    _ = try EdgeComposition.add_child(bn1, bn2.node, null);
    _ = try EdgeComposition.add_child(bn2, bn3.node, null);

    _ = try EdgeComposition.add_child(bn4, bn5.node, null);
    _ = try EdgeComposition.add_child(bn5, bn6.node, null);

    _ = try EdgeInterfaceConnection.connect_shallow(bn2, bn5);

    var shallow_path = try EdgeInterfaceConnection.is_connected_to(a, bn2, bn5);
    defer shallow_path.deinit();
    try std.testing.expect(shallow_path.get_last_node().node.is_same(bn5.node));

    try expectNoPath(a, bn3, bn6);
}

test "type_graph_pathfinder" {
    // Sensor
    //   └── I2C
    //        ├── SCL
    //        └── SDA
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);

    // Build I2C type hierarchy: Sensor -> I2C -> {SCL, SDA}
    const I2C_SCL = try tg.add_type("I2C_SCL");
    try tg.mark_constructable(I2C_SCL);
    const I2C_SDA = try tg.add_type("I2C_SDA");
    try tg.mark_constructable(I2C_SDA);
    const I2C = try tg.add_type("I2C");
    _ = try tg.add_make_child(I2C, I2C_SCL, "scl", null);
    _ = try tg.add_make_child(I2C, I2C_SDA, "sda", null);
    try tg.mark_constructable(I2C);
    const Sensor = try tg.add_type("Sensor");
    _ = try tg.add_make_child(Sensor, I2C, null, null);
    try tg.mark_constructable(Sensor);

    // Create sensor instances
    const sensor1 = try instantiate_interface(&tg, Sensor);
    const sensor2 = try instantiate_interface(&tg, Sensor);
    const sensor3 = try instantiate_interface(&tg, Sensor);

    // Get I2C interfaces from each sensor
    const sensor1_i2c = EdgeComposition.try_get_single_child_of_type(sensor1, I2C.node).?;
    const sensor2_i2c = EdgeComposition.try_get_single_child_of_type(sensor2, I2C.node).?;
    const sensor3_i2c = EdgeComposition.try_get_single_child_of_type(sensor3, I2C.node).?;

    // Get SCL and SDA lines
    const sensor1_scl = EdgeComposition.try_get_single_child_of_type(sensor1_i2c, I2C_SCL.node).?;
    const sensor1_sda = EdgeComposition.try_get_single_child_of_type(sensor1_i2c, I2C_SDA.node).?;
    const sensor2_scl = EdgeComposition.try_get_single_child_of_type(sensor2_i2c, I2C_SCL.node).?;
    const sensor2_sda = EdgeComposition.try_get_single_child_of_type(sensor2_i2c, I2C_SDA.node).?;
    const sensor3_scl = EdgeComposition.try_get_single_child_of_type(sensor3_i2c, I2C_SCL.node).?;
    const sensor3_sda = EdgeComposition.try_get_single_child_of_type(sensor3_i2c, I2C_SDA.node).?;

    // Verify types
    try std.testing.expect(EdgeType.is_node_instance_of(sensor1_i2c, I2C.node));
    try std.testing.expect(EdgeType.is_node_instance_of(sensor1_scl, I2C_SCL.node));
    try std.testing.expect(EdgeType.is_node_instance_of(sensor1_sda, I2C_SDA.node));

    // Test 1: Connect I2C bus normally (sensor1.scl <-> sensor2.scl)
    _ = try EdgeInterfaceConnection.connect(sensor1_scl, sensor2_scl);
    var paths_scl = try EdgeInterfaceConnection.is_connected_to(a, sensor1_scl, sensor2_scl);
    defer paths_scl.deinit();
    try std.testing.expect(paths_scl.get_last_node().node.is_same(sensor2_scl.node));
    std.debug.print("✓ I2C SCL lines connected\n", .{});

    // Test 2: Different signal types should not connect (scl ≠ sda)
    try expectNoPath(a, sensor1_scl, sensor1_sda);
    std.debug.print("✓ SCL ≠ SDA (no crosstalk)\n", .{});

    // Test 3: Shallow link behavior
    // Create a shallow link at I2C level between sensor2 and sensor3
    _ = try EdgeInterfaceConnection.connect_shallow(sensor2_i2c, sensor3_i2c);

    // Test 3a: Direct connection through shallow link works at I2C level
    var paths_i2c_shallow = try EdgeInterfaceConnection.is_connected_to(a, sensor2_i2c, sensor3_i2c);
    defer paths_i2c_shallow.deinit();
    try std.testing.expect(paths_i2c_shallow.get_last_node().node.is_same(sensor3_i2c.node));
    std.debug.print("✓ Shallow link at I2C level works\n", .{});

    // Test 3b: Cannot traverse from child (SCL) up through parent and across shallow link
    // sensor2.scl -> sensor2.i2c ~(shallow)~ sensor3.i2c -> sensor3.scl
    // This should be filtered because we start at SCL (child level) and the shallow link is at I2C (parent level)
    try expectNoPath(a, sensor2_scl, sensor3_scl);
    std.debug.print("✓ Shallow link blocks child->parent->shallow\n", .{});

    // Test 4: Type mismatch - I2C to I2C_SCL
    try expectNoPath(a, sensor1_i2c, sensor1_scl);
    std.debug.print("✓ Type mismatch filtered (I2C ≠ I2C_SCL)\n", .{});

    // Test 5: Multi-hop on same bus (sensor1.scl -> sensor2.scl, sensor2.sda -> sensor3.sda via shallow)
    // First connect SDA lines normally
    _ = try EdgeInterfaceConnection.connect(sensor1_sda, sensor2_sda);

    // Since there's a shallow link at I2C level, we can't reach sensor3.sda from sensor1.sda
    // because the path would be: sensor1.sda -> sensor2.sda -> (up to sensor2.i2c) -> (shallow to sensor3.i2c) -> sensor3.sda
    try expectNoPath(a, sensor1_sda, sensor3_sda);
    std.debug.print("✓ Shallow link prevents bus chaining from child\n", .{});

    // Test 6: Normal (non-shallow) I2C connection allows child traversal
    // Create a 4th sensor and connect its I2C with a normal (non-shallow) edge
    const sensor4 = try instantiate_interface(&tg, Sensor);
    const sensor4_i2c = EdgeComposition.try_get_single_child_of_type(sensor4, I2C.node).?;
    const sensor4_scl = EdgeComposition.try_get_single_child_of_type(sensor4_i2c, I2C_SCL.node).?;
    const sensor4_sda = EdgeComposition.try_get_single_child_of_type(sensor4_i2c, I2C_SDA.node).?;

    // Connect sensor1.i2c to sensor4.i2c with NORMAL (non-shallow) connection
    _ = try EdgeInterfaceConnection.connect(sensor1_i2c, sensor4_i2c);

    // Test 6a: SCL should be connected through I2C hierarchy
    // Path: sensor1.scl -> (up to sensor1.i2c) -> (normal edge to sensor4.i2c) -> (down to sensor4.scl)
    var paths_scl_hierarchy = try EdgeInterfaceConnection.is_connected_to(a, sensor1_scl, sensor4_scl);
    defer paths_scl_hierarchy.deinit();
    try std.testing.expect(paths_scl_hierarchy.get_last_node().node.is_same(sensor4_scl.node));
    std.debug.print("✓ Normal I2C link allows SCL->I2C->I2C->SCL\n", .{});

    // Test 6b: SDA should be connected through I2C hierarchy
    // Path: sensor1.sda -> (up to sensor1.i2c) -> (normal edge to sensor4.i2c) -> (down to sensor4.sda)
    var paths_sda_hierarchy = try EdgeInterfaceConnection.is_connected_to(a, sensor1_sda, sensor4_sda);
    defer paths_sda_hierarchy.deinit();
    try std.testing.expect(paths_sda_hierarchy.get_last_node().node.is_same(sensor4_sda.node));
    std.debug.print("✓ Normal I2C link allows SDA->I2C->I2C->SDA\n", .{});

    // Test 6c: But SCL should NOT connect to SDA (different child types, even through hierarchy)
    try expectNoPath(a, sensor1_scl, sensor4_sda);
    std.debug.print("✓ SCL ≠ SDA even through I2C hierarchy\n", .{});
}
