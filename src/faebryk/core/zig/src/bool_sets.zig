const std = @import("std");

const graph_mod = @import("graph");
const GraphView = graph_mod.graph.GraphView;
const BoundNodeReference = graph_mod.graph.BoundNodeReference;

const faebryk = @import("faebryk/lib.zig");
const EdgeComposition = faebryk.composition.EdgeComposition;
const EdgeNext = faebryk.next.EdgeNext;

pub const Bool_Node = struct {
    node: BoundNodeReference,
    const value_identifier = "value";
    pub fn init(g: *GraphView, value: bool) !Bool_Node {
        const node = g.create_and_insert_node();
        node.node.attributes.put(value_identifier, .{ .Bool = value });
        return of(node);
    }

    pub fn of(node: BoundNodeReference) Bool_Node {
        return Bool_Node{
            .node = node,
        };
    }

    pub fn get_value(self: Bool_Node) bool {
        return self.node.node.attributes.dynamic.values.get(value_identifier).?.Bool;
    }
};

test "Bool_Node.init" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bool_node = try Bool_Node.init(&g, true);
    try std.testing.expectEqual(bool_node.get_value(), true);
}

test "Bool_Node.of" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bool_node = Bool_Node.of(g.create_and_insert_node());
    bool_node.node.node.attributes.put(Bool_Node.value_identifier, .{ .Bool = false });
    try std.testing.expectEqual(bool_node.get_value(), false);
}

pub const Bool_Set = struct {
    node: BoundNodeReference,

    const set_identifier = "set";
    const head_identifier = "head";

    pub fn init(g: *GraphView, bools: []const Bool_Node) !Bool_Set {
        // Create a new node representing the bool set
        const node = g.create_and_insert_node();

        // If empty, return an empty set
        if (bools.len == 0) {
            return Bool_Set.of(node);
        }

        // For the first bool, add a child node with id 'head'
        const head_bool = bools[0];
        _ = EdgeComposition.add_child(node, head_bool.node.node, head_identifier);

        // For the remaining bools, add a child node with id 'next'
        var previous_node = head_bool.node;
        for (bools[1..]) |next_bool| {
            const new_node = try Bool_Node.init(g, next_bool.get_value());
            _ = EdgeNext.add_next(previous_node, new_node.node);
            previous_node = new_node.node;
        }

        return of(node);
    }

    pub fn init_empty(g: *GraphView) !Bool_Set {
        return try Bool_Set.init(g, &[_]Bool_Node{});
    }

    pub fn init_from_single(g: *GraphView, value: bool) !Bool_Set {
        return try Bool_Set.init(g, &[_]Bool_Node{try Bool_Node.init(g, value)});
    }

    pub fn init_from_bools(g: *GraphView, allocator: std.mem.Allocator, bools: []const bool) !Bool_Set {
        var bool_nodes = std.ArrayList(Bool_Node).init(allocator);
        defer bool_nodes.deinit();
        for (bools) |value| {
            try bool_nodes.append(try Bool_Node.init(g, value));
        }
        return try Bool_Set.init(g, bool_nodes.items);
    }

    pub fn of(node: BoundNodeReference) Bool_Set {
        return Bool_Set{
            .node = node,
        };
    }

    pub fn get_bools(self: *const Bool_Set, allocator: std.mem.Allocator) ![]const Bool_Node {
        // if there is no head node, return an empty array
        if (EdgeComposition.get_child_by_identifier(self.node, head_identifier) == null) {
            return &[_]Bool_Node{};
        }

        var bools = std.ArrayList(Bool_Node).init(allocator);
        defer bools.deinit();

        // get the head node and add it to the bools
        var bound_current = EdgeComposition.get_child_by_identifier(self.node, head_identifier) orelse return error.Empty;
        try bools.append(Bool_Node.of(bound_current));

        // traverse the 'next' edges and collect the Bool_Node nodes
        while (EdgeNext.get_next_node_from_node(bound_current)) |node_ref| {
            bound_current = bound_current.g.bind(node_ref);
            try bools.append(Bool_Node.of(bound_current));
        }

        const owned = try bools.toOwnedSlice();
        return owned;
    }

    pub fn op_not(self: *const Bool_Set, g: *GraphView, allocator: std.mem.Allocator) !Bool_Set {
        var bool_nodes = std.ArrayList(Bool_Node).init(allocator);
        defer bool_nodes.deinit();

        const self_bools = try self.get_bools(allocator);
        defer allocator.free(self_bools);

        for (self_bools) |element| {
            try bool_nodes.append(try Bool_Node.init(g, !element.get_value()));
        }
        return Bool_Set.init(g, bool_nodes.items);
    }

    pub fn op_and(self: *const Bool_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Bool_Set) !Bool_Set {
        var bool_nodes = std.ArrayList(Bool_Node).init(allocator);
        defer bool_nodes.deinit();

        const self_bools = try self.get_bools(allocator);
        defer allocator.free(self_bools);

        const other_bools = try other.get_bools(allocator);
        defer allocator.free(other_bools);

        for (self_bools) |element| {
            for (other_bools) |other_element| {
                try bool_nodes.append(try Bool_Node.init(g, element.get_value() and other_element.get_value()));
            }
        }
        return Bool_Set.init(g, bool_nodes.items);
    }

    pub fn op_or(self: *const Bool_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Bool_Set) !Bool_Set {
        var bool_nodes = std.ArrayList(Bool_Node).init(allocator);
        defer bool_nodes.deinit();

        const self_bools = try self.get_bools(allocator);
        defer allocator.free(self_bools);

        const other_bools = try other.get_bools(allocator);
        defer allocator.free(other_bools);

        for (self_bools) |element| {
            for (other_bools) |other_element| {
                try bool_nodes.append(try Bool_Node.init(g, element.get_value() or other_element.get_value()));
            }
        }
        return Bool_Set.init(g, bool_nodes.items);
    }
};

test "Bool_Set.init" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const elements = [_]Bool_Node{ try Bool_Node.init(&g, true), try Bool_Node.init(&g, false), try Bool_Node.init(&g, true) };
    const set = try Bool_Set.init(&g, &elements);

    const bools = try set.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(bools);

    try std.testing.expectEqual(bools.len, elements.len);
    try std.testing.expectEqual(bools[0].get_value(), true);
    try std.testing.expectEqual(bools[1].get_value(), false);
    try std.testing.expectEqual(bools[2].get_value(), true);
}

test "Bool_Set.init_from_bools" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const bools = [_]bool{ true, true, false };
    const set = try Bool_Set.init_from_bools(&g, allocator, &bools);

    const result_bools = try set.get_bools(allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(result_bools.len, bools.len);
    try std.testing.expectEqual(true, result_bools[0].get_value());
    try std.testing.expectEqual(true, result_bools[1].get_value());
    try std.testing.expectEqual(false, result_bools[2].get_value());
}

test "Bool_Set.op_not" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const elements = [_]bool{ true, true, false };
    const set = try Bool_Set.init_from_bools(&g, allocator, &elements);

    const result = try set.op_not(&g, allocator);
    const result_bools = try result.get_bools(allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(elements.len, result_bools.len);
    try std.testing.expectEqual(result_bools[0].get_value(), false);
    try std.testing.expectEqual(result_bools[1].get_value(), false);
    try std.testing.expectEqual(result_bools[2].get_value(), true);
}

test "Bool_Set.op_and" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs_elements = [_]bool{ true, false };
    const rhs_elements = [_]bool{ false, true };

    const lhs = try Bool_Set.init_from_bools(&g, allocator, &lhs_elements);
    const rhs = try Bool_Set.init_from_bools(&g, allocator, &rhs_elements);

    const result = try lhs.op_and(&g, allocator, &rhs);
    const result_bools = try result.get_bools(allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(result_bools.len, lhs_elements.len * rhs_elements.len);
    try std.testing.expectEqual(result_bools[0].get_value(), false);
    try std.testing.expectEqual(result_bools[1].get_value(), true);
    try std.testing.expectEqual(result_bools[2].get_value(), false);
    try std.testing.expectEqual(result_bools[3].get_value(), false);
}

test "Bool_Set.op_or" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs_elements = [_]bool{ true, false };
    const rhs_elements = [_]bool{ false, true };

    const lhs = try Bool_Set.init_from_bools(&g, allocator, &lhs_elements);
    const rhs = try Bool_Set.init_from_bools(&g, allocator, &rhs_elements);

    const result = try lhs.op_or(&g, allocator, &rhs);
    const result_bools = try result.get_bools(allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(result_bools.len, lhs_elements.len * rhs_elements.len);
    try std.testing.expectEqual(result_bools[0].get_value(), true);
    try std.testing.expectEqual(result_bools[1].get_value(), true);
    try std.testing.expectEqual(result_bools[2].get_value(), false);
    try std.testing.expectEqual(result_bools[3].get_value(), true);
}
