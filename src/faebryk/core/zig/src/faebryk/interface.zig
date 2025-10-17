const graph = @import("graph").graph;
const std = @import("std");
const visitor = @import("graph").visitor;
const PathFinder = @import("pathfinder.zig").PathFinder;
const EdgeComposition = @import("composition.zig").EdgeComposition;

const Node = graph.Node;
const NodeReference = graph.NodeReference;
const BoundNodeReference = graph.BoundNodeReference;

const Edge = graph.Edge;
const EdgeReference = graph.EdgeReference;
const BoundEdgeReference = graph.BoundEdgeReference;

const GraphView = graph.GraphView;
const str = graph.str;

pub const EdgeInterfaceConnection = struct {
    pub const tid: Edge.EdgeType = 1759242069;
    pub const shallow_attribute = "shallow";

    pub fn get_tid() Edge.EdgeType {
        return tid;
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
        const e = try Edge.init(bn1.g.allocator, bn1.node, bn2.node, tid);
        e.attributes.directional = false;
        e.attributes.dynamic.values.put(shallow_attribute, graph.Literal{ .Bool = false }) catch {
            @panic("Failed to put shallow link value");
        };
        return try bn1.g.insert_edge(e);
    }

    pub fn connect_shallow(bn1: BoundNodeReference, bn2: BoundNodeReference) !BoundEdgeReference {
        var e = try EdgeInterfaceConnection.connect(bn1, bn2);
        try e.edge.attributes.dynamic.values.put(shallow_attribute, graph.Literal{ .Bool = true });
        return e;
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

    // Find paths from source to target. Returns empty slice if not connected.
    // Note: Caller is responsible for freeing the returned paths
    pub fn is_connected_to(allocator: std.mem.Allocator, source: BoundNodeReference, target: BoundNodeReference) ![]graph.BFSPath {
        var pf = PathFinder.init(allocator);
        // Don't defer pf.deinit() - we're transferring ownership of the paths
        errdefer pf.deinit();

        const paths = try pf.find_paths(source, &[_]graph.BoundNodeReference{target});

        // Transfer ownership by cloning the paths into a new array
        var result = std.ArrayList(graph.BFSPath).init(allocator);
        errdefer {
            for (result.items) |*path| path.deinit();
            result.deinit();
        }

        try result.ensureTotalCapacity(paths.len);
        for (paths) |path| {
            result.appendAssumeCapacity(path);
        }

        // Clear the pathfinder's list without freeing the paths (we transferred them)
        if (pf.path_list) |*list| {
            list.clearRetainingCapacity();
            list.deinit();
            pf.path_list = null;
        }

        // Clean up other pathfinder resources
        if (pf.end_nodes) |*list| {
            list.deinit();
            pf.end_nodes = null;
        }

        return result.toOwnedSlice();
    }

    // Get all nodes connected to the source node (without filtering by end nodes)
    // Note: Caller is responsible for freeing the returned paths
    pub fn get_connected(allocator: std.mem.Allocator, source: BoundNodeReference) ![]graph.BFSPath {
        var pf = PathFinder.init(allocator);
        // Don't defer pf.deinit() - we're transferring ownership of the paths
        errdefer pf.deinit();

        // Pass null for end_nodes to get all reachable paths
        const paths = try pf.find_paths(source, null);

        // Transfer ownership by cloning the paths into a new array
        var result = std.ArrayList(graph.BFSPath).init(allocator);
        errdefer {
            for (result.items) |*path| path.deinit();
            result.deinit();
        }

        try result.ensureTotalCapacity(paths.len);
        for (paths) |path| {
            result.appendAssumeCapacity(path);
        }

        // Clear the pathfinder's list without freeing the paths (we transferred them)
        if (pf.path_list) |*list| {
            list.clearRetainingCapacity();
            list.deinit();
            pf.path_list = null;
        }

        // Clean up other pathfinder resources
        if (pf.end_nodes) |*list| {
            list.deinit();
            pf.end_nodes = null;
        }

        return result.toOwnedSlice();
    }

    // visit all paths for a given node (pathfinder)

    // "shallow" links
};

test "basic" {
    // Allocate some nodes and edges
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit(); // Graph owns all inserted nodes/edges and handles their cleanup

    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);

    // Insert nodes into GraphView g
    const bn1 = try g.insert_node(n1);
    const bn2 = try g.insert_node(n2);
    const bn3 = try g.insert_node(n3);

    // Create connection between n1 and n2
    const be1 = try EdgeInterfaceConnection.connect(bn1, bn2);

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
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = try g.insert_node(try Node.init(g.allocator));
    const bn2 = try g.insert_node(try Node.init(g.allocator));

    // expect not connected
    const paths1 = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, bn1, bn2);
    defer {
        for (paths1) |*path| path.deinit();
        std.testing.allocator.free(paths1);
    }
    try std.testing.expect(paths1.len == 0);

    // expect connected
    const paths2 = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, bn1, bn1);
    defer {
        for (paths2) |*path| path.deinit();
        std.testing.allocator.free(paths2);
    }
    try std.testing.expect(paths2.len == 1);
}

test "is_connected_to" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = try g.insert_node(try Node.init(g.allocator));
    const bn2 = try g.insert_node(try Node.init(g.allocator));
    const bn3 = try g.insert_node(try Node.init(g.allocator));
    _ = try EdgeInterfaceConnection.connect(bn1, bn2);
    _ = try EdgeInterfaceConnection.connect(bn1, bn3);

    const paths = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, bn1, bn2);
    defer {
        for (paths) |*path| path.deinit();
        std.testing.allocator.free(paths);
    }
    try std.testing.expect(paths.len == 1);
}

test "down_connect" {
    // P1 -->  P2
    //  HV      HV
    //  LV      LV

    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const EP_1 = try g.insert_node(try Node.init(g.allocator));
    const LV_1 = try g.insert_node(try Node.init(g.allocator));
    const HV_1 = try g.insert_node(try Node.init(g.allocator));

    _ = try EdgeComposition.add_child(EP_1, LV_1.node, "LV");
    _ = try EdgeComposition.add_child(EP_1, HV_1.node, "HV");

    const EP_2 = try g.insert_node(try Node.init(g.allocator));
    const LV_2 = try g.insert_node(try Node.init(g.allocator));
    const HV_2 = try g.insert_node(try Node.init(g.allocator));

    _ = try EdgeComposition.add_child(EP_2, LV_2.node, "LV");
    _ = try EdgeComposition.add_child(EP_2, HV_2.node, "HV");

    _ = try EdgeInterfaceConnection.connect(EP_1, EP_2);

    const paths = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, EP_1, EP_2);
    defer {
        for (paths) |*path| path.deinit();
        std.testing.allocator.free(paths);
    }
    try std.testing.expect(paths.len == 1);

    const paths_hv = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, HV_1, HV_2);
    defer {
        for (paths_hv) |*path| path.deinit();
        std.testing.allocator.free(paths_hv);
    }
    try std.testing.expect(paths_hv.len == 1);

    const paths_lv = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, LV_1, LV_2);
    defer {
        for (paths_lv) |*path| path.deinit();
        std.testing.allocator.free(paths_lv);
    }
    try std.testing.expect(paths_lv.len == 1);

    const paths_hv_lv = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, HV_1, LV_2);
    defer {
        for (paths_hv_lv) |*path| path.deinit();
        std.testing.allocator.free(paths_hv_lv);
    }
    try std.testing.expect(paths_hv_lv.len == 0);

    const paths_lv_hv = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, LV_1, HV_2);
    defer {
        for (paths_lv_hv) |*path| path.deinit();
        std.testing.allocator.free(paths_lv_hv);
    }
    try std.testing.expect(paths_lv_hv.len == 0);
}

test "no_connect_cases" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = try g.insert_node(try Node.init(g.allocator));
    const bn2 = try g.insert_node(try Node.init(g.allocator));
    const bn3 = try g.insert_node(try Node.init(g.allocator));
    const bn4 = try g.insert_node(try Node.init(g.allocator));
    const bn5 = try g.insert_node(try Node.init(g.allocator));
    const bn6 = try g.insert_node(try Node.init(g.allocator));

    _ = try EdgeComposition.add_child(bn1, bn2.node, null);
    _ = try EdgeComposition.add_child(bn3, bn2.node, null);
    _ = try EdgeInterfaceConnection.connect(bn3, bn4);
    _ = try EdgeComposition.add_child(bn5, bn4.node, null);
    _ = try EdgeComposition.add_child(bn6, bn1.node, null);
    _ = try EdgeComposition.add_child(bn6, bn3.node, null);

    const parent_child = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, bn1, bn2);
    defer {
        for (parent_child) |*path| path.deinit();
        std.testing.allocator.free(parent_child);
    }
    try std.testing.expect(parent_child.len == 0);

    const parent_child_parent = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, bn1, bn3);
    defer {
        for (parent_child_parent) |*path| path.deinit();
        std.testing.allocator.free(parent_child_parent);
    }
    try std.testing.expect(parent_child_parent.len == 0);

    const p_c_p_s_p = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, bn1, bn5);
    defer {
        for (p_c_p_s_p) |*path| path.deinit();
        std.testing.allocator.free(p_c_p_s_p);
    }
    try std.testing.expect(p_c_p_s_p.len == 0);
}

test "chains_direct" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const M1 = try g.insert_node(try Node.init(g.allocator));
    const M2 = try g.insert_node(try Node.init(g.allocator));
    const M3 = try g.insert_node(try Node.init(g.allocator));

    _ = try EdgeInterfaceConnection.connect(M1, M2);
    _ = try EdgeInterfaceConnection.connect(M2, M3);

    const paths = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, M1, M3);
    defer {
        for (paths) |*path| path.deinit();
        std.testing.allocator.free(paths);
    }
    try std.testing.expect(paths.len == 1);
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
        const node = try g.insert_node(try Node.init(g.allocator));
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

    // Stop timer
    const elapsed = timer.read();
    const elapsed_ms = elapsed / std.time.ns_per_ms;
    const elapsed_s = @as(f64, @floatFromInt(elapsed)) / @as(f64, @floatFromInt(std.time.ns_per_s));

    std.debug.print("\nPathfinding completed!\n", .{});
    std.debug.print("  Total paths explored: {}\n", .{pf.path_counter});
    std.debug.print("  Valid paths found: {}\n", .{paths.len});
    std.debug.print("  Time: {d:.3}s ({} ms)\n", .{ elapsed_s, elapsed_ms });

    // Verify we found a path
    var result = false;
    for (paths) |path| {
        if (Node.is_same(path.get_last_node().?.node, nodes.items[chain_length - 1].node)) {
            result = true;
            break;
        }
    }

    try std.testing.expect(paths.len == 1);
}

test "shallow_edges" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = try g.insert_node(try Node.init(g.allocator));
    const bn2 = try g.insert_node(try Node.init(g.allocator));
    const bn3 = try g.insert_node(try Node.init(g.allocator));
    const bn4 = try g.insert_node(try Node.init(g.allocator));
    const bn5 = try g.insert_node(try Node.init(g.allocator));
    const bn6 = try g.insert_node(try Node.init(g.allocator));

    _ = try EdgeComposition.add_child(bn1, bn2.node, null);
    _ = try EdgeComposition.add_child(bn2, bn3.node, null);

    _ = try EdgeComposition.add_child(bn4, bn5.node, null);
    _ = try EdgeComposition.add_child(bn5, bn6.node, null);

    _ = try EdgeInterfaceConnection.connect_shallow(bn2, bn5);

    const shallow_path = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, bn2, bn5);
    defer {
        for (shallow_path) |*path| path.deinit();
        std.testing.allocator.free(shallow_path);
    }
    try std.testing.expect(shallow_path.len == 1);

    const dont_cross_shallow_path = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, bn3, bn6);
    defer {
        for (dont_cross_shallow_path) |*path| path.deinit();
        std.testing.allocator.free(dont_cross_shallow_path);
    }
    try std.testing.expect(dont_cross_shallow_path.len == 0);
}

test "type_graph_pathfinder" {
    const TypeGraph = @import("typegraph.zig").TypeGraph;
    const EdgeType = @import("node_type.zig").EdgeType;

    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    var tg = try TypeGraph.init(&g);

    // Build I2C type hierarchy: ElectricLogic -> I2C (scl, sda) -> Sensor
    const ElectricLogic = try tg.add_type("ElectricLogic");
    const I2C = try tg.add_type("I2C");
    const Sensor = try tg.add_type("Sensor");

    // I2C has scl and sda lines (both ElectricLogic)
    _ = try tg.add_make_child(I2C, ElectricLogic, "scl");
    _ = try tg.add_make_child(I2C, ElectricLogic, "sda");

    // Sensor has an I2C interface
    _ = try tg.add_make_child(Sensor, I2C, "i2c");

    // Create sensor instances
    const sensor1 = try tg.instantiate_node(Sensor);
    const sensor2 = try tg.instantiate_node(Sensor);
    const sensor3 = try tg.instantiate_node(Sensor);

    // Get I2C interfaces from each sensor
    const sensor1_i2c = EdgeComposition.get_child_by_identifier(sensor1, "i2c").?;
    const sensor2_i2c = EdgeComposition.get_child_by_identifier(sensor2, "i2c").?;
    const sensor3_i2c = EdgeComposition.get_child_by_identifier(sensor3, "i2c").?;

    // Get SCL and SDA lines
    const sensor1_scl = EdgeComposition.get_child_by_identifier(sensor1_i2c, "scl").?;
    const sensor1_sda = EdgeComposition.get_child_by_identifier(sensor1_i2c, "sda").?;
    const sensor2_scl = EdgeComposition.get_child_by_identifier(sensor2_i2c, "scl").?;
    const sensor2_sda = EdgeComposition.get_child_by_identifier(sensor2_i2c, "sda").?;
    const sensor3_scl = EdgeComposition.get_child_by_identifier(sensor3_i2c, "scl").?;
    const sensor3_sda = EdgeComposition.get_child_by_identifier(sensor3_i2c, "sda").?;

    // Verify types
    try std.testing.expect(EdgeType.is_node_instance_of(sensor1_i2c, I2C.node));
    try std.testing.expect(EdgeType.is_node_instance_of(sensor1_scl, ElectricLogic.node));
    try std.testing.expect(EdgeType.is_node_instance_of(sensor1_sda, ElectricLogic.node));

    // Test 1: Connect I2C bus normally (sensor1.scl <-> sensor2.scl)
    _ = try EdgeInterfaceConnection.connect(sensor1_scl, sensor2_scl);
    const paths_scl = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor1_scl, sensor2_scl);
    defer {
        for (paths_scl) |*path| path.deinit();
        std.testing.allocator.free(paths_scl);
    }
    try std.testing.expect(paths_scl.len == 1);
    std.debug.print("✓ I2C SCL lines connected: found {} path(s)\n", .{paths_scl.len});

    // Test 2: Different signal types should not connect (scl ≠ sda)
    const paths_scl_to_sda = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor1_scl, sensor1_sda);
    defer {
        for (paths_scl_to_sda) |*path| path.deinit();
        std.testing.allocator.free(paths_scl_to_sda);
    }
    try std.testing.expect(paths_scl_to_sda.len == 0);
    std.debug.print("✓ SCL ≠ SDA (no crosstalk): found {} path(s)\n", .{paths_scl_to_sda.len});

    // Test 3: Shallow link behavior
    // Create a shallow link at I2C level between sensor2 and sensor3
    _ = try EdgeInterfaceConnection.connect_shallow(sensor2_i2c, sensor3_i2c);

    // Test 3a: Direct connection through shallow link works at I2C level
    const paths_i2c_shallow = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor2_i2c, sensor3_i2c);
    defer {
        for (paths_i2c_shallow) |*path| path.deinit();
        std.testing.allocator.free(paths_i2c_shallow);
    }
    try std.testing.expect(paths_i2c_shallow.len == 1);
    std.debug.print("✓ Shallow link at I2C level works: found {} path(s)\n", .{paths_i2c_shallow.len});

    // Test 3b: Cannot traverse from child (SCL) up through parent and across shallow link
    // sensor2.scl -> sensor2.i2c ~(shallow)~ sensor3.i2c -> sensor3.scl
    // This should be filtered because we start at SCL (child level) and the shallow link is at I2C (parent level)
    const paths_scl_shallow = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor2_scl, sensor3_scl);
    defer {
        for (paths_scl_shallow) |*path| path.deinit();
        std.testing.allocator.free(paths_scl_shallow);
    }
    try std.testing.expect(paths_scl_shallow.len == 0);
    std.debug.print("✓ Shallow link blocks child->parent->shallow: found {} path(s)\n", .{paths_scl_shallow.len});

    // Test 4: Type mismatch - I2C to ElectricLogic
    const paths_wrong_type = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor1_i2c, sensor1_scl);
    defer {
        for (paths_wrong_type) |*path| path.deinit();
        std.testing.allocator.free(paths_wrong_type);
    }
    try std.testing.expect(paths_wrong_type.len == 0);
    std.debug.print("✓ Type mismatch filtered (I2C ≠ ElectricLogic): found {} path(s)\n", .{paths_wrong_type.len});

    // Test 5: Multi-hop on same bus (sensor1.scl -> sensor2.scl, sensor2.sda -> sensor3.sda via shallow)
    // First connect SDA lines normally
    _ = try EdgeInterfaceConnection.connect(sensor1_sda, sensor2_sda);

    // Since there's a shallow link at I2C level, we can't reach sensor3.sda from sensor1.sda
    // because the path would be: sensor1.sda -> sensor2.sda -> (up to sensor2.i2c) -> (shallow to sensor3.i2c) -> sensor3.sda
    const paths_sda_chain = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor1_sda, sensor3_sda);
    defer {
        for (paths_sda_chain) |*path| path.deinit();
        std.testing.allocator.free(paths_sda_chain);
    }
    try std.testing.expect(paths_sda_chain.len == 0);
    std.debug.print("✓ Shallow link prevents bus chaining from child: found {} path(s)\n", .{paths_sda_chain.len});

    // Test 6: Normal (non-shallow) I2C connection allows child traversal
    // Create a 4th sensor and connect its I2C with a normal (non-shallow) edge
    const sensor4 = try tg.instantiate_node(Sensor);
    const sensor4_i2c = EdgeComposition.get_child_by_identifier(sensor4, "i2c").?;
    const sensor4_scl = EdgeComposition.get_child_by_identifier(sensor4_i2c, "scl").?;
    const sensor4_sda = EdgeComposition.get_child_by_identifier(sensor4_i2c, "sda").?;

    // Connect sensor1.i2c to sensor4.i2c with NORMAL (non-shallow) connection
    _ = try EdgeInterfaceConnection.connect(sensor1_i2c, sensor4_i2c);

    // Test 6a: SCL should be connected through I2C hierarchy
    // Path: sensor1.scl -> (up to sensor1.i2c) -> (normal edge to sensor4.i2c) -> (down to sensor4.scl)
    const paths_scl_hierarchy = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor1_scl, sensor4_scl);
    defer {
        for (paths_scl_hierarchy) |*path| path.deinit();
        std.testing.allocator.free(paths_scl_hierarchy);
    }
    try std.testing.expect(paths_scl_hierarchy.len == 1);
    std.debug.print("✓ Normal I2C link allows SCL->I2C->I2C->SCL: found {} path(s)\n", .{paths_scl_hierarchy.len});

    // Test 6b: SDA should be connected through I2C hierarchy
    // Path: sensor1.sda -> (up to sensor1.i2c) -> (normal edge to sensor4.i2c) -> (down to sensor4.sda)
    const paths_sda_hierarchy = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor1_sda, sensor4_sda);
    defer {
        for (paths_sda_hierarchy) |*path| path.deinit();
        std.testing.allocator.free(paths_sda_hierarchy);
    }
    try std.testing.expect(paths_sda_hierarchy.len == 1);
    std.debug.print("✓ Normal I2C link allows SDA->I2C->I2C->SDA: found {} path(s)\n", .{paths_sda_hierarchy.len});

    // Test 6c: But SCL should NOT connect to SDA (different child names, even through hierarchy)
    const paths_scl_to_sda_hierarchy = try EdgeInterfaceConnection.is_connected_to(std.testing.allocator, sensor1_scl, sensor4_sda);
    defer {
        for (paths_scl_to_sda_hierarchy) |*path| path.deinit();
        std.testing.allocator.free(paths_scl_to_sda_hierarchy);
    }
    try std.testing.expect(paths_scl_to_sda_hierarchy.len == 0);
    std.debug.print("✓ SCL ≠ SDA even through I2C hierarchy: found {} path(s)\n", .{paths_scl_to_sda_hierarchy.len});
}
