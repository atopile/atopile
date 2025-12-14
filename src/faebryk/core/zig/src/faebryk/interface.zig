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
    pub const tid: Edge.EdgeType = 1759242069;
    pub const shallow_attribute = "shallow";

    pub fn get_tid() Edge.EdgeType {
        return tid;
    }

    pub fn init(allocator: std.mem.Allocator, N1: NodeReference, N2: NodeReference, shallow: bool) !EdgeReference {
        const edge = Edge.init(allocator, N1, N2, tid);
        var attrs = try build(allocator, shallow);
        defer if (attrs.dynamic) |*dyn| dyn.deinit();
        attrs.apply_to(edge);
        return edge;
    }

    pub fn build(allocator: std.mem.Allocator, shallow: bool) !EdgeCreationAttributes {
        var dynamic = graph.DynamicAttributes.init(allocator);
        dynamic.put(shallow_attribute, .{ .Bool = shallow });
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

            if (!Node.is_same(type1, type2)) {
                return error.IncompatibleTypes;
            }
        }

        return bn1.g.insert_edge(try EdgeInterfaceConnection.init(bn1.g.allocator, bn1.node, bn2.node, false));
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

            if (!Node.is_same(type1, type2)) {
                return error.IncompatibleTypes;
            }
        }

        return bn1.g.insert_edge(try EdgeInterfaceConnection.init(bn1.g.allocator, bn1.node, bn2.node, true));
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_other_connected_node(E: EdgeReference, N: NodeReference) ?NodeReference {
        if (Node.is_same(E.source, N)) {
            return E.target;
        } else if (Node.is_same(E.target, N)) {
            return E.source;
        } else {
            return null;
        }
    }

    pub fn visit_connected_edges(
        bound_node: graph.BoundNodeReference,
        ctx: *anyopaque,
        f: fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),
    ) visitor.VisitResult(void) {
        return bound_node.visit_edges_of_type(tid, void, ctx, f, null);
    }

    pub fn is_connected_to(allocator: std.mem.Allocator, source: BoundNodeReference, target: BoundNodeReference) !*graph.BFSPath {
        var pf = PathFinder.init(allocator);
        defer pf.deinit();

        var paths = try pf.find_paths(source);
        defer paths.deinit();

        for (paths.paths.items, 0..) |path, i| {
            if (Node.is_same(path.get_last_node().node, target.node)) {
                // Transfer ownership by removing from collection
                return paths.paths.swapRemove(i);
            }
        }

        // No path found - return empty path
        return try graph.BFSPath.init(source);
    }

    // TODO - A visitor would be nice instead of just returning a list don't ya think?
    pub fn get_connected(allocator: std.mem.Allocator, source: BoundNodeReference, include_self: bool) !graph.NodeRefMap.T(*graph.BFSPath) {
        var pf = PathFinder.init(allocator);
        defer pf.deinit();

        var paths = try pf.find_paths(source);
        defer paths.paths.deinit(); // Clean up the ArrayList, but not the paths themselves (transferred to map)

        var paths_map = graph.NodeRefMap.T(*graph.BFSPath).init(allocator);

        for (paths.paths.items) |path| {
            const end_node = path.get_last_node().node;

            // Skip self-path if include_self is false
            if (!include_self and Node.is_same(end_node, source.node)) {
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

test "basic" {
    // N1 --> N2
    // N1 --> N3
    // Allocate some nodes and edges
    var g = graph.GraphView.init(a);
    defer g.deinit(); // Graph owns all inserted nodes/edges and handles their cleanup

    var tg = TypeGraph.init(&g);
    const electrical_type = try tg.add_type("Electrical");

    const bn1 = try tg.instantiate_node(electrical_type);
    const bn2 = try tg.instantiate_node(electrical_type);
    const bn3 = try tg.instantiate_node(electrical_type);

    const n1 = bn1.node;
    const n2 = bn2.node;
    const n3 = bn3.node;

    std.debug.print("n1.uuid = {}\n", .{n1.attributes.uuid});
    std.debug.print("n2.uuid = {}\n", .{n2.attributes.uuid});
    std.debug.print("n3.uuid = {}\n", .{n3.attributes.uuid});

    const be1 = try EdgeInterfaceConnection.connect(bn1, bn2);

    std.debug.print("e1.uuid = {}\n", .{be1.edge.attributes.uuid});
    std.debug.print("e1.source.uuid = {}\n", .{be1.edge.source.attributes.uuid});
    std.debug.print("e1.target.uuid = {}\n", .{be1.edge.target.attributes.uuid});

    std.debug.print("n2.uuid = {}\n", .{n2.attributes.uuid});

    std.debug.print("e1.source.uuid = {}\n", .{be1.edge.source.attributes.uuid});
    std.debug.print("e1.target.uuid = {}\n", .{be1.edge.target.attributes.uuid});

    // Expect shallow flag to be present and false by default
    const shallow_default = be1.edge.attributes.dynamic.get(EdgeInterfaceConnection.shallow_attribute).?;
    try std.testing.expect(shallow_default.Bool == false);

    // Expect e1 source and target to match n1 and n2
    try std.testing.expect(Node.is_same(be1.edge.source, n1));
    try std.testing.expect(Node.is_same(be1.edge.target, n2));

    // Expect e1 source and target to not match n3
    try std.testing.expect(!Node.is_same(be1.edge.source, n3));
    try std.testing.expect(!Node.is_same(be1.edge.target, n3));

    // Expect get_connected to return n2 when given n1
    try std.testing.expect(Node.is_same(EdgeInterfaceConnection.get_other_connected_node(be1.edge, n1).?, n2));

    // Expect get_connected to return n1 when given n2
    try std.testing.expect(Node.is_same(EdgeInterfaceConnection.get_other_connected_node(be1.edge, n2).?, n1));

    // Expect get_connected to return null when given n3
    try std.testing.expect(EdgeInterfaceConnection.get_other_connected_node(be1.edge, n3) == null);

    // Create another connection between n1 and n3 to test multiple connections
    const be2 = try EdgeInterfaceConnection.connect(bn1, bn3);
    try std.testing.expect(Node.is_same(be2.edge.source, n1));
    try std.testing.expect(Node.is_same(be2.edge.target, n3));

    // define visitor that visits all edges connected to n1 in g and saves the EdgeReferences to a list (connected_edges)
    const CollectConnectedEdges = struct {
        connected_edges: std.ArrayList(graph.BoundEdgeReference),

        pub fn visit(self_ptr: *anyopaque, connected_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(self_ptr));

            self.connected_edges.append(connected_edge) catch |err| {
                return visitor.VisitResult(void){ .ERROR = err };
            };

            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    // instantiate visitor
    var visit = CollectConnectedEdges{ .connected_edges = std.ArrayList(graph.BoundEdgeReference).init(a) };
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
        if (Node.is_same(edge.edge.source, n1) or Node.is_same(edge.edge.target, n1)) {
            if (Node.is_same(edge.edge.source, n2) or Node.is_same(edge.edge.target, n2)) {
                found_n2 = true;
            }
            if (Node.is_same(edge.edge.source, n3) or Node.is_same(edge.edge.target, n3)) {
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

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();

    // expect not connected (empty path)
    try expectNoPath(a, bn1, bn2);

    // expect connected
    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn1);
    defer path.deinit();
    try std.testing.expect(Node.is_same(path.get_last_node().node, bn1.node));
}

test "is_connected_to" {
    //     A
    //    / \
    //   B   C
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const electrical_type = try tg.add_type("Electrical");

    const bn1 = try tg.instantiate_node(electrical_type);
    const bn2 = try tg.instantiate_node(electrical_type);
    const bn3 = try tg.instantiate_node(electrical_type);
    _ = try EdgeInterfaceConnection.connect(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn1, bn3);

    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn2);
    defer path.deinit();
    try std.testing.expect(Node.is_same(path.get_last_node().node, bn2.node));
}

test "down_connect" {
    // P1 --> P2
    //  |      |
    // HV     HV
    // LV     LV
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const ElectricPowerType = try tg.add_type("ElectricPower");
    const ElectricalType = try tg.add_type("Electrical");
    // const LinkType = try tg.add_type("Link");

    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "HV", null, null);
    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "LV", null, null);

    const EP_1 = try tg.instantiate_node(ElectricPowerType);
    const HV_1 = EdgeComposition.get_child_by_identifier(EP_1, "HV").?;
    const LV_1 = EdgeComposition.get_child_by_identifier(EP_1, "LV").?;

    const EP_2 = try tg.instantiate_node(ElectricPowerType);
    const HV_2 = EdgeComposition.get_child_by_identifier(EP_2, "HV").?;
    const LV_2 = EdgeComposition.get_child_by_identifier(EP_2, "LV").?;

    _ = try EdgeInterfaceConnection.connect(EP_1, EP_2);

    var path = try EdgeInterfaceConnection.is_connected_to(a, EP_1, EP_2);
    defer path.deinit();
    try std.testing.expect(Node.is_same(path.get_last_node().node, EP_2.node));

    var path_hv = try EdgeInterfaceConnection.is_connected_to(a, HV_1, HV_2);
    defer path_hv.deinit();
    try std.testing.expect(Node.is_same(path_hv.get_last_node().node, HV_2.node));

    var path_lv = try EdgeInterfaceConnection.is_connected_to(a, LV_1, LV_2);
    defer path_lv.deinit();
    try std.testing.expect(Node.is_same(path_lv.get_last_node().node, LV_2.node));

    try expectNoPath(a, HV_1, LV_2);
    try expectNoPath(a, LV_1, HV_2);

    const link_a = try tg.instantiate_node(ElectricalType);
    const link_b = try tg.instantiate_node(ElectricalType);
    const link_c = try tg.instantiate_node(ElectricalType);
    _ = try EdgeInterfaceConnection.connect(HV_1, link_a);
    _ = try EdgeInterfaceConnection.connect(link_a, link_b);
    _ = try EdgeInterfaceConnection.connect(link_b, link_c);
    _ = try EdgeInterfaceConnection.connect(link_c, LV_2);

    var path_hv_link_lv = try EdgeInterfaceConnection.is_connected_to(a, HV_1, LV_2);
    defer path_hv_link_lv.deinit();
    try std.testing.expect(Node.is_same(path_hv_link_lv.get_last_node().node, LV_2.node));

    const HV_1_Child = try tg.instantiate_node(ElectricalType);
    _ = EdgeComposition.add_child(HV_1, HV_1_Child.node, "HV/LV Child");

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

    const bn1 = try tg.instantiate_node(GenericType);
    const bn2 = try tg.instantiate_node(GenericType);
    const bn3 = try tg.instantiate_node(GenericType);
    const bn4 = try tg.instantiate_node(GenericType);
    const bn5 = try tg.instantiate_node(GenericType);
    const bn6 = try tg.instantiate_node(GenericType);

    _ = EdgeComposition.add_child(bn1, bn2.node, null);
    _ = EdgeComposition.add_child(bn3, bn2.node, null);
    _ = try EdgeInterfaceConnection.connect(bn3, bn4);
    _ = EdgeComposition.add_child(bn5, bn4.node, null);
    _ = EdgeComposition.add_child(bn6, bn1.node, null);
    _ = EdgeComposition.add_child(bn6, bn3.node, null);

    try expectNoPath(a, bn1, bn2);
    try expectNoPath(a, bn1, bn3);
    try expectNoPath(a, bn1, bn5);
}

test "chains_direct" {
    // M1 --> M2 --> M3
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const electrical_type = try tg.add_type("Electrical");

    const M1 = try tg.instantiate_node(electrical_type);
    const M2 = try tg.instantiate_node(electrical_type);
    const M3 = try tg.instantiate_node(electrical_type);

    _ = try EdgeInterfaceConnection.connect(M1, M2);
    _ = try EdgeInterfaceConnection.connect(M2, M3);

    var path = try EdgeInterfaceConnection.is_connected_to(a, M1, M3);
    defer path.deinit();
    try std.testing.expect(Node.is_same(path.get_last_node().node, M3.node));
}

test "chains_double_shallow_flat" {
    // N1 ==> N2 ==> N3
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const electrical_type = try tg.add_type("Electrical");

    const bn1 = try tg.instantiate_node(electrical_type);
    const bn2 = try tg.instantiate_node(electrical_type);
    const bn3 = try tg.instantiate_node(electrical_type);

    _ = try EdgeInterfaceConnection.connect_shallow(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect_shallow(bn2, bn3);

    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn3);
    defer path.deinit();
    try std.testing.expect(Node.is_same(path.get_last_node().node, bn3.node));
}

test "chains_mixed_shallow_flat" {
    // N1 ==> N2 --> N3
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const electrical_type = try tg.add_type("Electrical");

    const bn1 = try tg.instantiate_node(electrical_type);
    const bn2 = try tg.instantiate_node(electrical_type);
    const bn3 = try tg.instantiate_node(electrical_type);

    _ = try EdgeInterfaceConnection.connect_shallow(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn2, bn3);

    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn3);
    defer path.deinit();
    try std.testing.expect(Node.is_same(path.get_last_node().node, bn3.node));
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
    const electrical_type = try tg.add_type("Electrical");

    const bn1 = try tg.instantiate_node(electrical_type);
    const bn2 = try tg.instantiate_node(electrical_type);
    const bn3 = try tg.instantiate_node(electrical_type);
    const bn4 = try tg.instantiate_node(electrical_type);
    const bn5 = try tg.instantiate_node(electrical_type);
    const bn6 = try tg.instantiate_node(electrical_type);
    const bn7 = try tg.instantiate_node(electrical_type);

    _ = try EdgeInterfaceConnection.connect(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn2, bn4);
    _ = try EdgeInterfaceConnection.connect(bn1, bn3);
    _ = try EdgeInterfaceConnection.connect(bn3, bn6);
    _ = try EdgeInterfaceConnection.connect(bn6, bn4);
    _ = try EdgeInterfaceConnection.connect(bn1, bn5);
    _ = try EdgeInterfaceConnection.connect(bn4, bn7);

    var path = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn4);
    defer path.deinit();
    try std.testing.expect(Node.is_same(path.get_last_node().node, bn4.node));

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
    const ElectricPowerType = try tg.add_type("ElectricPower");
    const ElectricalType = try tg.add_type("Electrical");

    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "HV", null, null);
    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "LV", null, null);

    const electric_power = try tg.instantiate_node(ElectricPowerType);
    const hv_pin = EdgeComposition.get_child_by_identifier(electric_power, "HV").?;
    const lv_pin = EdgeComposition.get_child_by_identifier(electric_power, "LV").?;

    try expectNoPath(a, electric_power, lv_pin);

    const link_a = try tg.instantiate_node(ElectricalType);
    const link_b = try tg.instantiate_node(ElectricalType);

    _ = try EdgeInterfaceConnection.connect(hv_pin, link_a);
    _ = try EdgeInterfaceConnection.connect(link_a, link_b);
    _ = try EdgeInterfaceConnection.connect(link_b, lv_pin);

    var hv_to_lv = try EdgeInterfaceConnection.is_connected_to(a, hv_pin, lv_pin);
    defer hv_to_lv.deinit();
    try std.testing.expect(Node.is_same(hv_to_lv.get_last_node().node, lv_pin.node));
}

test "shallow_filter_allows_alternative_route" {
    // P1 ==> P2 (shallow)
    //  |       |
    // HV ---- Bus --- HV
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const ElectricPowerType = try tg.add_type("ElectricPower");
    const ElectricalType = try tg.add_type("Electrical");

    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "HV", null, null);
    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "LV", null, null);

    const start_parent = try tg.instantiate_node(ElectricPowerType);
    const start_child = EdgeComposition.get_child_by_identifier(start_parent, "HV").?;
    const target_parent = try tg.instantiate_node(ElectricPowerType);
    const target_child = EdgeComposition.get_child_by_identifier(target_parent, "HV").?;
    const bus = try tg.instantiate_node(ElectricalType);

    _ = try EdgeInterfaceConnection.connect_shallow(start_parent, target_parent);

    _ = try EdgeInterfaceConnection.connect(start_child, bus);
    _ = try EdgeInterfaceConnection.connect(bus, target_child);

    var path = try EdgeInterfaceConnection.is_connected_to(a, start_child, target_child);
    defer path.deinit();
    try std.testing.expect(Node.is_same(path.get_last_node().node, target_child.node));
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
    const ElType = try tg.add_type("El");
    const LineType = try tg.add_type("Line");
    const RefType = try tg.add_type("Ref");
    const HVType = try tg.add_type("HV");
    const LVType = try tg.add_type("LV");

    _ = try tg.add_make_child(ElType, LineType, "line", null, null);
    _ = try tg.add_make_child(ElType, RefType, "reference", null, null);
    _ = try tg.add_make_child(RefType, HVType, "hv", null, null);
    _ = try tg.add_make_child(RefType, LVType, "lv", null, null);

    var el: [3]graph.BoundNodeReference = undefined;
    for (&el) |*slot| slot.* = try tg.instantiate_node(ElType);

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
    try std.testing.expect(Node.is_same(el_path.get_last_node().node, el[2].node));

    var line_path = try EdgeInterfaceConnection.is_connected_to(a, line[1], line[2]);
    defer line_path.deinit();
    try std.testing.expect(Node.is_same(line_path.get_last_node().node, line[2].node));

    var ref_path = try EdgeInterfaceConnection.is_connected_to(a, reference[1], reference[2]);
    defer ref_path.deinit();
    try std.testing.expect(Node.is_same(ref_path.get_last_node().node, reference[2].node));

    try expectNoPath(a, line[0], line[1]);
    try expectNoPath(a, reference[0], reference[1]);
    try expectNoPath(a, line[0], line[2]);
    try expectNoPath(a, reference[0], reference[2]);

    _ = try EdgeInterfaceConnection.connect(line[0], line[1]);
    _ = try EdgeInterfaceConnection.connect(reference[0], reference[1]);

    var el_up = try EdgeInterfaceConnection.is_connected_to(a, el[0], el[1]);
    defer el_up.deinit();
    try std.testing.expect(Node.is_same(el_up.get_last_node().node, el[1].node));

    var el_full = try EdgeInterfaceConnection.is_connected_to(a, el[0], el[2]);
    defer el_full.deinit();
    try std.testing.expect(Node.is_same(el_full.get_last_node().node, el[2].node));
}

test "split_flip_negative" {
    // H1     H2
    //  L1 --> L2
    //  L2 --> L1
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const HighType = try tg.add_type("High");
    const LowType = try tg.add_type("Low");

    _ = try tg.add_make_child(HighType, LowType, "lower1", null, null);
    _ = try tg.add_make_child(HighType, LowType, "lower2", null, null);

    var high: [2]graph.BoundNodeReference = undefined;
    for (&high) |*slot| slot.* = try tg.instantiate_node(HighType);

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
    const HighType = try tg.add_type("High");
    const Lower1Type = try tg.add_type("Lower1");
    const Lower2Type = try tg.add_type("Lower2");

    _ = try tg.add_make_child(HighType, Lower1Type, "lower1", null, null);
    _ = try tg.add_make_child(HighType, Lower2Type, "lower2", null, null);

    var high: [2]graph.BoundNodeReference = undefined;
    for (&high) |*slot| slot.* = try tg.instantiate_node(HighType);

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
    const electrical_type = try tg.add_type("Electrical");

    const chain_length = 1000;
    var nodes = std.ArrayList(graph.BoundNodeReference).init(allocator);
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
        const node = try tg.instantiate_node(electrical_type);
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
    var path = try EdgeInterfaceConnection.is_connected_to(g.allocator, nodes.items[0], nodes.items[chain_length - 1]);
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
    try std.testing.expect(Node.is_same(path.get_last_node().node, nodes.items[chain_length - 1].node));
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
    const GenericType = try tg.add_type("Generic");

    const bn1 = try tg.instantiate_node(GenericType);
    const bn2 = try tg.instantiate_node(GenericType);
    const bn3 = try tg.instantiate_node(GenericType);
    const bn4 = try tg.instantiate_node(GenericType);
    const bn5 = try tg.instantiate_node(GenericType);
    const bn6 = try tg.instantiate_node(GenericType);

    _ = EdgeComposition.add_child(bn1, bn2.node, null);
    _ = EdgeComposition.add_child(bn2, bn3.node, null);

    _ = EdgeComposition.add_child(bn4, bn5.node, null);
    _ = EdgeComposition.add_child(bn5, bn6.node, null);

    _ = try EdgeInterfaceConnection.connect_shallow(bn2, bn5);

    var shallow_path = try EdgeInterfaceConnection.is_connected_to(a, bn2, bn5);
    defer shallow_path.deinit();
    try std.testing.expect(Node.is_same(shallow_path.get_last_node().node, bn5.node));

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
    const I2C = try tg.add_type("I2C");
    const Sensor = try tg.add_type("Sensor");
    const I2C_SCL = try tg.add_type("I2C_SCL");
    const I2C_SDA = try tg.add_type("I2C_SDA");

    // I2C has dedicated SCL and SDA child types
    _ = try tg.add_make_child(I2C, I2C_SCL, null, null, null);
    _ = try tg.add_make_child(I2C, I2C_SDA, null, null, null);

    // Sensor has an I2C interface
    _ = try tg.add_make_child(Sensor, I2C, null, null, null);

    // Create sensor instances
    const sensor1 = try tg.instantiate_node(Sensor);
    const sensor2 = try tg.instantiate_node(Sensor);
    const sensor3 = try tg.instantiate_node(Sensor);

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
    try std.testing.expect(Node.is_same(paths_scl.get_last_node().node, sensor2_scl.node));
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
    try std.testing.expect(Node.is_same(paths_i2c_shallow.get_last_node().node, sensor3_i2c.node));
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
    const sensor4 = try tg.instantiate_node(Sensor);
    const sensor4_i2c = EdgeComposition.try_get_single_child_of_type(sensor4, I2C.node).?;
    const sensor4_scl = EdgeComposition.try_get_single_child_of_type(sensor4_i2c, I2C_SCL.node).?;
    const sensor4_sda = EdgeComposition.try_get_single_child_of_type(sensor4_i2c, I2C_SDA.node).?;

    // Connect sensor1.i2c to sensor4.i2c with NORMAL (non-shallow) connection
    _ = try EdgeInterfaceConnection.connect(sensor1_i2c, sensor4_i2c);

    // Test 6a: SCL should be connected through I2C hierarchy
    // Path: sensor1.scl -> (up to sensor1.i2c) -> (normal edge to sensor4.i2c) -> (down to sensor4.scl)
    var paths_scl_hierarchy = try EdgeInterfaceConnection.is_connected_to(a, sensor1_scl, sensor4_scl);
    defer paths_scl_hierarchy.deinit();
    try std.testing.expect(Node.is_same(paths_scl_hierarchy.get_last_node().node, sensor4_scl.node));
    std.debug.print("✓ Normal I2C link allows SCL->I2C->I2C->SCL\n", .{});

    // Test 6b: SDA should be connected through I2C hierarchy
    // Path: sensor1.sda -> (up to sensor1.i2c) -> (normal edge to sensor4.i2c) -> (down to sensor4.sda)
    var paths_sda_hierarchy = try EdgeInterfaceConnection.is_connected_to(a, sensor1_sda, sensor4_sda);
    defer paths_sda_hierarchy.deinit();
    try std.testing.expect(Node.is_same(paths_sda_hierarchy.get_last_node().node, sensor4_sda.node));
    std.debug.print("✓ Normal I2C link allows SDA->I2C->I2C->SDA\n", .{});

    // Test 6c: But SCL should NOT connect to SDA (different child types, even through hierarchy)
    try expectNoPath(a, sensor1_scl, sensor4_sda);
    std.debug.print("✓ SCL ≠ SDA even through I2C hierarchy\n", .{});
}
