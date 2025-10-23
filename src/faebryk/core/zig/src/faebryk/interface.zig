const graph_import = @import("graph");
const graph = graph_import.graph;
const visitor = graph_import.visitor;
const std = @import("std");
const PathFinder = @import("pathfinder.zig").PathFinder;
const EdgeComposition = @import("composition.zig").EdgeComposition;
const edgebuilder_mod = @import("edgebuilder.zig");
const TypeGraph = @import("typegraph.zig").TypeGraph;
const EdgeType = @import("node_type.zig").EdgeType;

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
        const attributes = EdgeCreationAttributes{
            .edge_type = tid,
            .directional = false,
            .name = null,
            .dynamic = graph.DynamicAttributes.init(allocator),
        };
        attributes.apply_to(edge);
        try edge.attributes.dynamic.values.put(shallow_attribute, graph.Literal{ .Bool = shallow });
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    // Get other connected node given an already connected node and edge reference
    pub fn get_other_connected_node(E: EdgeReference, N: NodeReference) ?NodeReference {
        if (Node.is_same(E.source, N)) {
            return E.target;
        } else if (Node.is_same(E.target, N)) {
            return E.source;
        } else {
            return null; // Returns null if given node and edge were not connected in the first place
        }
    }

    pub fn connect(bn1: BoundNodeReference, bn2: BoundNodeReference) !BoundEdgeReference {
        return bn1.g.insert_edge(try EdgeInterfaceConnection.init(bn1.g.allocator, bn1.node, bn2.node, false));
    }

    pub fn connect_shallow(bn1: BoundNodeReference, bn2: BoundNodeReference) !BoundEdgeReference {
        return bn1.g.insert_edge(try EdgeInterfaceConnection.init(bn1.g.allocator, bn1.node, bn2.node, true));
    }

    // visit all connected edges for a given node
    pub fn visit_connected_edges(
        bound_node: graph.BoundNodeReference,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),
    ) visitor.VisitResult(void) {
        const Visit = struct {
            target: graph.BoundNodeReference,
            cb_ctx: *anyopaque,
            cb: *const fn (*anyopaque, graph.BoundEdgeReference) visitor.VisitResult(void),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));
                const connected = EdgeInterfaceConnection.get_other_connected_node(bound_edge.edge, self.target.node);
                if (connected) |_| {
                    const connected_result = self.cb(self.cb_ctx, bound_edge);
                    switch (connected_result) {
                        .CONTINUE => {},
                        else => return connected_result,
                    }
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var visit = Visit{ .target = bound_node, .cb_ctx = ctx, .cb = f };
        return bound_node.visit_edges_of_type(tid, void, &visit, Visit.visit);
    }

    // Find paths from source to target. Returns empty BFSPaths if not connected.
    // Note: Caller is responsible for freeing the returned BFSPaths
    pub fn is_connected_to(allocator: std.mem.Allocator, source: BoundNodeReference, target: BoundNodeReference) !graph.BFSPaths {
        var pf = PathFinder.init(allocator);
        defer pf.deinit();

        return try pf.find_paths(source, &[_]graph.BoundNodeReference{target});
    }

    // Get all nodes connected to the source node (without filtering by end nodes)
    // Note: Caller is responsible for freeing the returned BFSPaths
    pub fn get_connected(allocator: std.mem.Allocator, source: BoundNodeReference) !graph.BFSPaths {
        var pf = PathFinder.init(allocator);
        defer pf.deinit();

        // Pass null for end_nodes to get all reachable paths
        return try pf.find_paths(source, null);
    }

    // visit all paths for a given node (pathfinder)

    // "shallow" links
};

const a = std.testing.allocator;

test "basic" {
    // Allocate some nodes and edges
    var g = graph.GraphView.init(a);
    defer g.deinit(); // Graph owns all inserted nodes/edges and handles their cleanup

    const n1 = Node.init(a);
    const n2 = Node.init(a);
    const n3 = Node.init(a);

    // Insert nodes into GraphView g
    const bn1 = g.insert_node(n1);
    const bn2 = g.insert_node(n2);
    const bn3 = g.insert_node(n3);

    std.debug.print("n1.uuid = {}\n", .{n1.attributes.uuid});
    std.debug.print("n2.uuid = {}\n", .{n2.attributes.uuid});
    std.debug.print("n3.uuid = {}\n", .{n3.attributes.uuid});

    const be1 = try EdgeInterfaceConnection.connect(bn1, bn2);

    std.debug.print("e1.uuid = {}\n", .{be1.edge.attributes.uuid});
    std.debug.print("e1.source.uuid = {}\n", .{be1.edge.source.attributes.uuid});
    std.debug.print("e1.target.uuid = {}\n", .{be1.edge.target.attributes.uuid});

    // const n_list = EdgeInterfaceConnection.list_connections(e1);

    // std.debug.print("n_list.len = {}\n", .{n_list.len});
    // std.debug.print("n_list[0].uuid = {}\n", .{n_list[0].attributes.uuid});
    // std.debug.print("n_list[1].uuid = {}\n", .{n_list[1].attributes.uuid});

    // const n2_ref = EdgeInterfaceConnection.get_connected(e1, n1);
    std.debug.print("n2.uuid = {}\n", .{n2.attributes.uuid});
    // std.debug.print("n2_ref.uuid = {}\n", .{n2_ref.?.attributes.uuid});

    // EdgeInterfaceConnection.connect(e1, n3, n1);

    std.debug.print("e1.source.uuid = {}\n", .{be1.edge.source.attributes.uuid});
    std.debug.print("e1.target.uuid = {}\n", .{be1.edge.target.attributes.uuid});

    // Expect shallow flag to be present and false by default
    const shallow_default = be1.edge.attributes.dynamic.values.get(EdgeInterfaceConnection.shallow_attribute).?;
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

test "self_connect" {
    var g = graph.GraphView.init(a);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();

    // expect not connected
    const paths1 = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn2);
    defer paths1.deinit();
    try std.testing.expect(paths1.paths.items.len == 0);

    // expect connected
    const paths2 = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn1);
    defer paths2.deinit();
    try std.testing.expect(paths2.paths.items.len == 1);
}

test "is_connected_to" {
    var g = graph.GraphView.init(a);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();
    _ = try EdgeInterfaceConnection.connect(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn1, bn3);

    const paths = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn2);
    defer paths.deinit();
    try std.testing.expect(paths.paths.items.len == 1);
}

test "down_connect" {
    // P1 -->  P2
    //  HV      HV
    //  LV      LV

    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const ElectricPowerType = try tg.add_type("ElectricPower");
    const ElectricalType = try tg.add_type("Electrical");

    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "HV");
    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "LV");

    const EP_1 = try tg.instantiate_node(ElectricPowerType);
    const HV_1 = EdgeComposition.get_child_by_identifier(EP_1, "HV").?;
    const LV_1 = EdgeComposition.get_child_by_identifier(EP_1, "LV").?;

    const EP_2 = try tg.instantiate_node(ElectricPowerType);
    const HV_2 = EdgeComposition.get_child_by_identifier(EP_2, "HV").?;
    const LV_2 = EdgeComposition.get_child_by_identifier(EP_2, "LV").?;

    _ = try EdgeInterfaceConnection.connect(EP_1, EP_2);

    const paths = try EdgeInterfaceConnection.is_connected_to(a, EP_1, EP_2);
    defer paths.deinit();
    try std.testing.expect(paths.paths.items.len == 1);

    const paths_hv = try EdgeInterfaceConnection.is_connected_to(a, HV_1, HV_2);
    defer paths_hv.deinit();
    try std.testing.expect(paths_hv.paths.items.len == 1);

    const paths_lv = try EdgeInterfaceConnection.is_connected_to(a, LV_1, LV_2);
    defer paths_lv.deinit();
    try std.testing.expect(paths_lv.paths.items.len == 1);

    const paths_hv_lv = try EdgeInterfaceConnection.is_connected_to(a, HV_1, LV_2);
    defer paths_hv_lv.deinit();
    try std.testing.expect(paths_hv_lv.paths.items.len == 0);

    const paths_lv_hv = try EdgeInterfaceConnection.is_connected_to(a, LV_1, HV_2);
    defer paths_lv_hv.deinit();
    try std.testing.expect(paths_lv_hv.paths.items.len == 0);
}

test "no_connect_cases" {
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

    const parent_child = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn2);
    defer parent_child.deinit();
    try std.testing.expect(parent_child.paths.items.len == 0);

    const parent_child_parent = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn3);
    defer parent_child_parent.deinit();
    try std.testing.expect(parent_child_parent.paths.items.len == 0);

    const p_c_p_s_p = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn5);
    defer p_c_p_s_p.deinit();
    try std.testing.expect(p_c_p_s_p.paths.items.len == 0);
}

test "chains_direct" {
    var g = graph.GraphView.init(a);
    defer g.deinit();

    const M1 = g.create_and_insert_node();
    const M2 = g.create_and_insert_node();
    const M3 = g.create_and_insert_node();

    _ = try EdgeInterfaceConnection.connect(M1, M2);
    _ = try EdgeInterfaceConnection.connect(M2, M3);

    const paths = try EdgeInterfaceConnection.is_connected_to(a, M1, M3);
    defer paths.deinit();
    try std.testing.expect(paths.paths.items.len == 1);
}

test "multiple_paths" {
    var g = graph.GraphView.init(a);
    defer g.deinit();

    const bn1 = g.create_and_insert_node();
    const bn2 = g.create_and_insert_node();
    const bn3 = g.create_and_insert_node();
    const bn4 = g.create_and_insert_node();
    const bn5 = g.create_and_insert_node();
    const bn6 = g.create_and_insert_node();
    const bn7 = g.create_and_insert_node();

    _ = try EdgeInterfaceConnection.connect(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn2, bn4);
    _ = try EdgeInterfaceConnection.connect(bn1, bn3);
    _ = try EdgeInterfaceConnection.connect(bn3, bn6);
    _ = try EdgeInterfaceConnection.connect(bn6, bn4);
    _ = try EdgeInterfaceConnection.connect(bn1, bn5);
    _ = try EdgeInterfaceConnection.connect(bn4, bn7);

    const paths = try EdgeInterfaceConnection.is_connected_to(a, bn1, bn4);
    defer paths.deinit();
    try std.testing.expect(paths.paths.items.len == 1);

    const all_paths = try EdgeInterfaceConnection.get_connected(a, bn1);
    defer all_paths.deinit();
    try std.testing.expect(all_paths.paths.items.len == 8);
}

test "heirarchy_short" {
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const ElectricPowerType = try tg.add_type("ElectricPower");
    const ElectricalType = try tg.add_type("Electrical");
    const LinkType = try tg.add_type("Link");

    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "HV");
    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "LV");

    const electric_power = try tg.instantiate_node(ElectricPowerType);
    const hv_pin = EdgeComposition.get_child_by_identifier(electric_power, "HV").?;
    const lv_pin = EdgeComposition.get_child_by_identifier(electric_power, "LV").?;

    const parent_to_lv = try EdgeInterfaceConnection.is_connected_to(a, electric_power, lv_pin);
    defer parent_to_lv.deinit();
    try std.testing.expect(parent_to_lv.paths.items.len == 0);

    const link_a = try tg.instantiate_node(LinkType);
    const link_b = try tg.instantiate_node(LinkType);

    _ = try EdgeInterfaceConnection.connect(hv_pin, link_a);
    _ = try EdgeInterfaceConnection.connect(link_a, link_b);
    _ = try EdgeInterfaceConnection.connect(link_b, lv_pin);

    const hv_to_lv = try EdgeInterfaceConnection.is_connected_to(a, hv_pin, lv_pin);
    defer hv_to_lv.deinit();
    try std.testing.expect(hv_to_lv.paths.items.len == 1);
}

test "shallow_filter_allows_alternative_route" {
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);
    const ElectricPowerType = try tg.add_type("ElectricPower");
    const ElectricalType = try tg.add_type("Electrical");

    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "HV");
    _ = try tg.add_make_child(ElectricPowerType, ElectricalType, "LV");

    const start_parent = try tg.instantiate_node(ElectricPowerType);
    const start_child = EdgeComposition.get_child_by_identifier(start_parent, "HV").?;
    const target_parent = try tg.instantiate_node(ElectricPowerType);
    const target_child = EdgeComposition.get_child_by_identifier(target_parent, "HV").?;
    const bus = try tg.instantiate_node(ElectricalType);

    _ = try EdgeInterfaceConnection.connect_shallow(start_parent, target_parent);

    _ = try EdgeInterfaceConnection.connect(start_child, bus);
    _ = try EdgeInterfaceConnection.connect(bus, target_child);

    const paths = try EdgeInterfaceConnection.is_connected_to(a, start_child, target_child);
    defer paths.deinit();

    try std.testing.expect(paths.paths.items.len == 1);
}

test "loooooong_chain" {
    // Let's make it hard - create a long chain of nodes
    // Use a more efficient allocator for this stress test instead of testing allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var g = graph.GraphView.init(allocator);
    defer g.deinit();

    const chain_length = 10000;
    var nodes = std.ArrayList(graph.BoundNodeReference).init(allocator);
    defer nodes.deinit();

    // Pre-allocate capacity to avoid repeated reallocations
    try nodes.ensureTotalCapacity(chain_length);

    std.debug.print("\nBuilding chain of {} nodes...\n", .{chain_length});

    // Create nodes
    var i: usize = 0;
    while (i < chain_length) : (i += 1) {
        if (i % 10000 == 0 and i > 0) {
            std.debug.print("  Created {} nodes...\n", .{i});
        }
        const node = g.create_and_insert_node();
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

    // Create pathfinder to access counters
    var pf = PathFinder.init(g.allocator);
    defer pf.deinit();
    const paths = try pf.find_paths(nodes.items[0], &[_]graph.BoundNodeReference{nodes.items[chain_length - 1]});
    defer paths.deinit();

    // Stop timer
    const elapsed = timer.read();
    const elapsed_ms = elapsed / std.time.ns_per_ms;
    const elapsed_s = @as(f64, @floatFromInt(elapsed)) / @as(f64, @floatFromInt(std.time.ns_per_s));

    std.debug.print("\nPathfinding completed!\n", .{});
    std.debug.print("  Total paths explored: {}\n", .{pf.path_counter});
    std.debug.print("  Valid paths found: {}\n", .{paths.paths.items.len});
    std.debug.print("  Time: {d:.3}s ({} ms)\n", .{ elapsed_s, elapsed_ms });

    // Verify we found a path
    var result = false;
    for (paths.paths.items) |path| {
        if (Node.is_same(path.get_last_node().?.node, nodes.items[chain_length - 1].node)) {
            result = true;
            break;
        }
    }

    try std.testing.expect(paths.paths.items.len == 1);
}

test "shallow_edges" {
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

    const shallow_path = try EdgeInterfaceConnection.is_connected_to(a, bn2, bn5);
    defer shallow_path.deinit();
    try std.testing.expect(shallow_path.paths.items.len == 1);

    const dont_cross_shallow_path = try EdgeInterfaceConnection.is_connected_to(a, bn3, bn6);
    defer dont_cross_shallow_path.deinit();
    try std.testing.expect(dont_cross_shallow_path.paths.items.len == 0);
}

test "type_graph_pathfinder" {
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);

    // Build I2C type hierarchy: Sensor -> I2C -> {SCL, SDA}
    const I2C = try tg.add_type("I2C");
    const Sensor = try tg.add_type("Sensor");
    const I2C_SCL = try tg.add_type("I2C_SCL");
    const I2C_SDA = try tg.add_type("I2C_SDA");

    // I2C has dedicated SCL and SDA child types
    _ = try tg.add_make_child(I2C, I2C_SCL, null);
    _ = try tg.add_make_child(I2C, I2C_SDA, null);

    // Sensor has an I2C interface
    _ = try tg.add_make_child(Sensor, I2C, null);

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
    const paths_scl = try EdgeInterfaceConnection.is_connected_to(a, sensor1_scl, sensor2_scl);
    defer paths_scl.deinit();
    try std.testing.expect(paths_scl.paths.items.len == 1);
    std.debug.print("✓ I2C SCL lines connected: found {} path(s)\n", .{paths_scl.paths.items.len});

    // Test 2: Different signal types should not connect (scl ≠ sda)
    const paths_scl_to_sda = try EdgeInterfaceConnection.is_connected_to(a, sensor1_scl, sensor1_sda);
    defer paths_scl_to_sda.deinit();
    try std.testing.expect(paths_scl_to_sda.paths.items.len == 0);
    std.debug.print("✓ SCL ≠ SDA (no crosstalk): found {} path(s)\n", .{paths_scl_to_sda.paths.items.len});

    // Test 3: Shallow link behavior
    // Create a shallow link at I2C level between sensor2 and sensor3
    _ = try EdgeInterfaceConnection.connect_shallow(sensor2_i2c, sensor3_i2c);

    // Test 3a: Direct connection through shallow link works at I2C level
    const paths_i2c_shallow = try EdgeInterfaceConnection.is_connected_to(a, sensor2_i2c, sensor3_i2c);
    defer paths_i2c_shallow.deinit();
    try std.testing.expect(paths_i2c_shallow.paths.items.len == 1);
    std.debug.print("✓ Shallow link at I2C level works: found {} path(s)\n", .{paths_i2c_shallow.paths.items.len});

    // Test 3b: Cannot traverse from child (SCL) up through parent and across shallow link
    // sensor2.scl -> sensor2.i2c ~(shallow)~ sensor3.i2c -> sensor3.scl
    // This should be filtered because we start at SCL (child level) and the shallow link is at I2C (parent level)
    const paths_scl_shallow = try EdgeInterfaceConnection.is_connected_to(a, sensor2_scl, sensor3_scl);
    defer paths_scl_shallow.deinit();
    try std.testing.expect(paths_scl_shallow.paths.items.len == 0);
    std.debug.print("✓ Shallow link blocks child->parent->shallow: found {} path(s)\n", .{paths_scl_shallow.paths.items.len});

    // Test 4: Type mismatch - I2C to I2C_SCL
    const paths_wrong_type = try EdgeInterfaceConnection.is_connected_to(a, sensor1_i2c, sensor1_scl);
    defer paths_wrong_type.deinit();
    try std.testing.expect(paths_wrong_type.paths.items.len == 0);
    std.debug.print("✓ Type mismatch filtered (I2C ≠ I2C_SCL): found {} path(s)\n", .{paths_wrong_type.paths.items.len});

    // Test 5: Multi-hop on same bus (sensor1.scl -> sensor2.scl, sensor2.sda -> sensor3.sda via shallow)
    // First connect SDA lines normally
    _ = try EdgeInterfaceConnection.connect(sensor1_sda, sensor2_sda);

    // Since there's a shallow link at I2C level, we can't reach sensor3.sda from sensor1.sda
    // because the path would be: sensor1.sda -> sensor2.sda -> (up to sensor2.i2c) -> (shallow to sensor3.i2c) -> sensor3.sda
    const paths_sda_chain = try EdgeInterfaceConnection.is_connected_to(a, sensor1_sda, sensor3_sda);
    defer paths_sda_chain.deinit();
    try std.testing.expect(paths_sda_chain.paths.items.len == 0);
    std.debug.print("✓ Shallow link prevents bus chaining from child: found {} path(s)\n", .{paths_sda_chain.paths.items.len});

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
    const paths_scl_hierarchy = try EdgeInterfaceConnection.is_connected_to(a, sensor1_scl, sensor4_scl);
    defer paths_scl_hierarchy.deinit();
    try std.testing.expect(paths_scl_hierarchy.paths.items.len == 1);
    std.debug.print("✓ Normal I2C link allows SCL->I2C->I2C->SCL: found {} path(s)\n", .{paths_scl_hierarchy.paths.items.len});

    // Test 6b: SDA should be connected through I2C hierarchy
    // Path: sensor1.sda -> (up to sensor1.i2c) -> (normal edge to sensor4.i2c) -> (down to sensor4.sda)
    const paths_sda_hierarchy = try EdgeInterfaceConnection.is_connected_to(a, sensor1_sda, sensor4_sda);
    defer paths_sda_hierarchy.deinit();
    try std.testing.expect(paths_sda_hierarchy.paths.items.len == 1);
    std.debug.print("✓ Normal I2C link allows SDA->I2C->I2C->SDA: found {} path(s)\n", .{paths_sda_hierarchy.paths.items.len});

    // Test 6c: But SCL should NOT connect to SDA (different child types, even through hierarchy)
    const paths_scl_to_sda_hierarchy = try EdgeInterfaceConnection.is_connected_to(a, sensor1_scl, sensor4_sda);
    defer paths_scl_to_sda_hierarchy.deinit();
    try std.testing.expect(paths_scl_to_sda_hierarchy.paths.items.len == 0);
    std.debug.print("✓ SCL ≠ SDA even through I2C hierarchy: found {} path(s)\n", .{paths_scl_to_sda_hierarchy.paths.items.len});
}
