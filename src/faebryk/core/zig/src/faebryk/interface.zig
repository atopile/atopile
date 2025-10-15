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

const shallow_link = "shallow_link";

pub const EdgeInterfaceConnection = struct {
    pub const tid: Edge.EdgeType = 1759242069;

    pub fn init(allocator: std.mem.Allocator, N1: NodeReference, N2: NodeReference) !EdgeReference {
        const edge = try Edge.init(allocator, N1, N2, tid);
        edge.attributes.directional = false; // interface connections are not directional
        edge.attributes.dynamic.values.put(shallow_link, graph.Literal{ .Bool = false }) // interfaces connections can be shallow but are not by default
        catch |err| {
            return err;
        };
        return edge;
    }

    pub fn is_instance(E: EdgeReference) bool {
        return Edge.is_instance(E, tid);
    }

    pub fn get_both_connected_nodes(E: EdgeReference) [2]NodeReference {
        return [_]NodeReference{ E.source, E.target };
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

    // Connect given EdgeReference to given 2 NodeReferences
    // TODO might be a good idea to have some type checking here, make sure nodes of same type are being connected?
    pub fn connect(E: EdgeReference, N1: NodeReference, N2: NodeReference) void {
        if (E.attributes.edge_type != tid) {
            @panic("Edge type mismatch");
        }
        E.source = N1;
        E.target = N2;
        return;
    }

    pub fn connect_shallow(E: EdgeReference, N1: NodeReference, N2: NodeReference) void {
        EdgeInterfaceConnection.connect(E, N1, N2);
        E.attributes.dynamic.values.put(shallow_link, graph.Literal{ .Bool = true }) catch {
            @panic("Failed to put shallow link value");
        };
        return;
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

    pub fn is_connected_to(source: BoundNodeReference, target: BoundNodeReference) !bool {
        var pf = PathFinder.init(source.g.allocator);
        defer pf.deinit();
        const paths = try pf.find_paths(source, &[_]graph.BoundNodeReference{target});
        for (paths) |path| {
            if (Node.is_same(path.get_last_node().?.node, target.node)) {
                std.debug.print("true\n", .{});
                return true;
            }
        }
        std.debug.print("false\n", .{});
        return false;
    }
    // visit all paths for a given node (pathfinder)

    // "shallow" links
};

test "basic" {
    // Allocate some nodes and edges
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);
    const e1 = try EdgeInterfaceConnection.init(a, n1, n2);
    defer g.deinit(); // Graph owns all inserted nodes/edges and handles their cleanup

    // Expect shallow flag to be present and false by default
    const shallow_default = e1.attributes.dynamic.values.get(shallow_link).?;
    try std.testing.expect(shallow_default.Bool == false);

    // Expect e1 source and target to match n1 and n2
    try std.testing.expect(Node.is_same(e1.source, n1));
    try std.testing.expect(Node.is_same(e1.target, n2));

    // Expect e1 source and target to not match n3
    try std.testing.expect(!Node.is_same(e1.source, n3));
    try std.testing.expect(!Node.is_same(e1.target, n3));

    // Expect list of 2 connections that reference n1 and n2
    const n_list = EdgeInterfaceConnection.get_both_connected_nodes(e1);
    try std.testing.expectEqual(n_list.len, 2);
    try std.testing.expect(Node.is_same(n_list[0], n1));
    try std.testing.expect(Node.is_same(n_list[1], n2));

    // Expect get_connected to return n2 when given n1
    try std.testing.expect(Node.is_same(EdgeInterfaceConnection.get_other_connected_node(e1, n1).?, n2));

    // Expect get_connected to return n1 when given n2
    try std.testing.expect(Node.is_same(EdgeInterfaceConnection.get_other_connected_node(e1, n2).?, n1));

    // Expect get_connected to return null when given n3
    try std.testing.expect(EdgeInterfaceConnection.get_other_connected_node(e1, n3) == null);

    // Take e1 and connect source to n1 and target to n3
    EdgeInterfaceConnection.connect(e1, n1, n3);
    try std.testing.expect(Node.is_same(e1.source, n1));
    try std.testing.expect(Node.is_same(e1.target, n3));

    // Expect no connections to n2 anymore
    try std.testing.expect(EdgeInterfaceConnection.get_other_connected_node(e1, n2) == null);

    // Insert n1, n2, n3 into GraphView g
    const bn1 = try g.insert_node(n1);
    _ = try g.insert_node(n2);
    _ = try g.insert_node(n3);
    _ = try g.insert_edge(e1);

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

    // check the visitor is correct
    try std.testing.expectEqual(visit.connected_edges.items.len, 1);
    try std.testing.expect(Node.is_same(visit.connected_edges.items[0].edge.source, n1));
    try std.testing.expect(Node.is_same(visit.connected_edges.items[0].edge.target, n3));
}

test "connect vs connect_shallow" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();

    // Nodes
    const n1 = try Node.init(a);
    const n2 = try Node.init(a);
    const n3 = try Node.init(a);
    const n4 = try Node.init(a);

    // Insert nodes (graph owns them)
    _ = try g.insert_node(n1);
    _ = try g.insert_node(n2);
    _ = try g.insert_node(n3);
    _ = try g.insert_node(n4);

    // Edge using regular connect (should not be shallow)
    const e_connect = try EdgeInterfaceConnection.init(a, n1, n2);
    EdgeInterfaceConnection.connect(e_connect, n1, n2);
    _ = try g.insert_edge(e_connect);
    const shallow_val_connect = e_connect.attributes.dynamic.values.get(shallow_link).?;
    try std.testing.expect(shallow_val_connect.Bool == false);

    // Edge using connect_shallow (should be shallow)
    const e_shallow = try EdgeInterfaceConnection.init(a, n3, n4);
    EdgeInterfaceConnection.connect_shallow(e_shallow, n3, n4);
    _ = try g.insert_edge(e_shallow);
    const shallow_val_shallow = e_shallow.attributes.dynamic.values.get(shallow_link).?;
    try std.testing.expect(shallow_val_shallow.Bool == true);

    // Sanity: endpoints remained as set
    try std.testing.expect(Node.is_same(e_connect.source, n1));
    try std.testing.expect(Node.is_same(e_connect.target, n2));
    try std.testing.expect(Node.is_same(e_shallow.source, n3));
    try std.testing.expect(Node.is_same(e_shallow.target, n4));
}

test "self_connect" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = try g.insert_node(try Node.init(g.allocator));
    const bn2 = try g.insert_node(try Node.init(g.allocator));

    // expect not connected
    const result1 = try EdgeInterfaceConnection.is_connected_to(bn1, bn2);
    try std.testing.expect(result1 == false);

    // expect connected
    const result2 = try EdgeInterfaceConnection.is_connected_to(bn1, bn1);
    try std.testing.expect(result2 == true);
}

test "is_connected_to" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bn1 = try g.insert_node(try Node.init(g.allocator));
    const bn2 = try g.insert_node(try Node.init(g.allocator));
    const be1 = try g.insert_edge(try Edge.init(g.allocator, bn1.node, bn2.node, EdgeInterfaceConnection.tid));
    _ = be1;

    const result = try EdgeInterfaceConnection.is_connected_to(bn1, bn2);
    try std.testing.expect(result == true);
}

test "down_connect" {
    // P1 -->  P2
    //  HV      HV
    //  LV      LV

    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const EP_1 = try g.insert_node(try Node.init(g.allocator));
    const LV_1 = try g.insert_node(try Node.init(g.allocator));
    LV_1.node.attributes.name = "LV";
    const HV_1 = try g.insert_node(try Node.init(g.allocator));
    HV_1.node.attributes.name = "HV";

    _ = try g.insert_edge(try Edge.init(g.allocator, EP_1.node, LV_1.node, EdgeComposition.tid));
    _ = try g.insert_edge(try Edge.init(g.allocator, EP_1.node, HV_1.node, EdgeComposition.tid));

    const EP_2 = try g.insert_node(try Node.init(g.allocator));
    const LV_2 = try g.insert_node(try Node.init(g.allocator));
    LV_2.node.attributes.name = "LV";
    const HV_2 = try g.insert_node(try Node.init(g.allocator));
    HV_2.node.attributes.name = "HV";

    _ = try g.insert_edge(try Edge.init(g.allocator, EP_2.node, LV_2.node, EdgeComposition.tid));
    _ = try g.insert_edge(try Edge.init(g.allocator, EP_2.node, HV_2.node, EdgeComposition.tid));

    _ = try g.insert_edge(try Edge.init(g.allocator, EP_1.node, EP_2.node, EdgeInterfaceConnection.tid));

    const result = try EdgeInterfaceConnection.is_connected_to(EP_1, EP_2);
    try std.testing.expect(result == true);

    const result_hv = try EdgeInterfaceConnection.is_connected_to(HV_1, HV_2);
    try std.testing.expect(result_hv == true);

    const result_lv = try EdgeInterfaceConnection.is_connected_to(LV_1, LV_2);
    try std.testing.expect(result_lv == true);

    const result_hv_lv = try EdgeInterfaceConnection.is_connected_to(HV_1, LV_2);
    try std.testing.expect(result_hv_lv == false);

    const result_lv_hv = try EdgeInterfaceConnection.is_connected_to(LV_1, HV_2);
    try std.testing.expect(result_lv_hv == false);
}

test "chains_direct" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();

    const M1 = try g.insert_node(try Node.init(g.allocator));
    const M2 = try g.insert_node(try Node.init(g.allocator));
    const M3 = try g.insert_node(try Node.init(g.allocator));

    _ = try g.insert_edge(try Edge.init(g.allocator, M1.node, M2.node, EdgeInterfaceConnection.tid));
    _ = try g.insert_edge(try Edge.init(g.allocator, M2.node, M3.node, EdgeInterfaceConnection.tid));

    const result = try EdgeInterfaceConnection.is_connected_to(M1, M3);
    try std.testing.expect(result == true);
}

test "loooooong_chain" {
    // Let's make it hard - create a long chain of nodes
    // Use a more efficient allocator for this stress test instead of testing allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var g = graph.GraphView.init(allocator);
    defer g.deinit();

    const chain_length = 10000; // Large enough to be interesting, small enough to not consume 44GB RAM
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
        _ = try g.insert_edge(try EdgeInterfaceConnection.init(g.allocator, nodes.items[i].node, nodes.items[i + 1].node));
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

    try std.testing.expect(result == true);
}
