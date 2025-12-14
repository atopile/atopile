const std = @import("std");

const graph_mod = @import("graph");
const GraphView = graph_mod.graph.GraphView;
const BoundNodeReference = graph_mod.graph.BoundNodeReference;

const faebryk = @import("faebryk");
const EdgeComposition = faebryk.composition.EdgeComposition;
const EdgeNext = faebryk.next.EdgeNext;

pub const BoolNode = struct {
    node: BoundNodeReference,
    const value_identifier = "value";
    pub fn init(g: *GraphView, value: bool) !BoolNode {
        const node = g.create_and_insert_node();
        node.node.attributes.put(value_identifier, .{ .Bool = value });
        return of(node);
    }

    pub fn of(node: BoundNodeReference) BoolNode {
        return BoolNode{
            .node = node,
        };
    }

    pub fn get_value(self: BoolNode) bool {
        return self.node.node.attributes.dynamic.get(value_identifier).?.Bool;
    }
};

test "BoolNode.init" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bool_node = try BoolNode.init(&g, true);
    try std.testing.expectEqual(bool_node.get_value(), true);
}

test "BoolNode.of" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const bool_node = BoolNode.of(g.create_and_insert_node());
    bool_node.node.node.attributes.put(BoolNode.value_identifier, .{ .Bool = false });
    try std.testing.expectEqual(bool_node.get_value(), false);
}

pub const BoolSet = struct {
    node: BoundNodeReference,

    const set_identifier = "set";
    const head_identifier = "head";

    pub fn init(g: *GraphView, bools: []const BoolNode) !BoolSet {
        // Create a new node representing the bool set
        const node = g.create_and_insert_node();

        // If empty, return an empty set
        if (bools.len == 0) {
            return BoolSet.of(node);
        }

        // For the first bool, add a child node with id 'head'
        const head_bool = bools[0];
        _ = EdgeComposition.add_child(node, head_bool.node.node, head_identifier);

        // For the remaining bools, add a child node with id 'next'
        var previous_node = head_bool.node;
        for (bools[1..]) |next_bool| {
            const new_node = try BoolNode.init(g, next_bool.get_value());
            _ = EdgeNext.add_next(previous_node, new_node.node);
            previous_node = new_node.node;
        }

        return of(node);
    }

    pub fn init_empty(g: *GraphView) !BoolSet {
        return try BoolSet.init(g, &[_]BoolNode{});
    }

    pub fn init_from_single(g: *GraphView, value: bool) !BoolSet {
        return try BoolSet.init(g, &[_]BoolNode{try BoolNode.init(g, value)});
    }

    pub fn init_from_bools(g: *GraphView, allocator: std.mem.Allocator, bools: []const bool) !BoolSet {
        var bool_nodes = std.ArrayList(BoolNode).init(allocator);
        defer bool_nodes.deinit();
        for (bools) |value| {
            try bool_nodes.append(try BoolNode.init(g, value));
        }
        return try BoolSet.init(g, bool_nodes.items);
    }

    pub fn of(node: BoundNodeReference) BoolSet {
        return BoolSet{
            .node = node,
        };
    }

    pub fn get_bools(self: *const BoolSet, allocator: std.mem.Allocator) ![]const BoolNode {
        // if there is no head node, return an empty array
        if (EdgeComposition.get_child_by_identifier(self.node, head_identifier) == null) {
            return &[_]BoolNode{};
        }

        var bools = std.ArrayList(BoolNode).init(allocator);
        defer bools.deinit();

        // get the head node and add it to the bools
        var bound_current = EdgeComposition.get_child_by_identifier(self.node, head_identifier) orelse return error.Empty;
        try bools.append(BoolNode.of(bound_current));

        // traverse the 'next' edges and collect the BoolNode nodes
        while (EdgeNext.get_next_node_from_node(bound_current)) |node_ref| {
            bound_current = bound_current.g.bind(node_ref);
            try bools.append(BoolNode.of(bound_current));
        }

        const owned = try bools.toOwnedSlice();
        return owned;
    }

    pub fn op_not(self: *const BoolSet, g: *GraphView, allocator: std.mem.Allocator) !BoolSet {
        var bool_nodes = std.ArrayList(BoolNode).init(allocator);
        defer bool_nodes.deinit();

        const self_bools = try self.get_bools(allocator);
        defer allocator.free(self_bools);

        for (self_bools) |element| {
            try bool_nodes.append(try BoolNode.init(g, !element.get_value()));
        }
        return BoolSet.init(g, bool_nodes.items);
    }

    pub fn op_and(self: *const BoolSet, g: *GraphView, allocator: std.mem.Allocator, other: *const BoolSet) !BoolSet {
        var bool_nodes = std.ArrayList(BoolNode).init(allocator);
        defer bool_nodes.deinit();

        const self_bools = try self.get_bools(allocator);
        defer allocator.free(self_bools);

        const other_bools = try other.get_bools(allocator);
        defer allocator.free(other_bools);

        for (self_bools) |element| {
            for (other_bools) |other_element| {
                try bool_nodes.append(try BoolNode.init(g, element.get_value() and other_element.get_value()));
            }
        }
        return BoolSet.init(g, bool_nodes.items);
    }

    pub fn op_or(self: *const BoolSet, g: *GraphView, allocator: std.mem.Allocator, other: *const BoolSet) !BoolSet {
        var bool_nodes = std.ArrayList(BoolNode).init(allocator);
        defer bool_nodes.deinit();

        const self_bools = try self.get_bools(allocator);
        defer allocator.free(self_bools);

        const other_bools = try other.get_bools(allocator);
        defer allocator.free(other_bools);

        for (self_bools) |element| {
            for (other_bools) |other_element| {
                try bool_nodes.append(try BoolNode.init(g, element.get_value() or other_element.get_value()));
            }
        }
        return BoolSet.init(g, bool_nodes.items);
    }
};

test "BoolSet.init" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const elements = [_]BoolNode{ try BoolNode.init(&g, true), try BoolNode.init(&g, false), try BoolNode.init(&g, true) };
    const set = try BoolSet.init(&g, &elements);

    const bools = try set.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(bools);

    try std.testing.expectEqual(bools.len, elements.len);
    try std.testing.expectEqual(bools[0].get_value(), true);
    try std.testing.expectEqual(bools[1].get_value(), false);
    try std.testing.expectEqual(bools[2].get_value(), true);
}

test "BoolSet.init_from_bools" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const bools = [_]bool{ true, true, false };
    const set = try BoolSet.init_from_bools(&g, allocator, &bools);

    const result_bools = try set.get_bools(allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(result_bools.len, bools.len);
    try std.testing.expectEqual(true, result_bools[0].get_value());
    try std.testing.expectEqual(true, result_bools[1].get_value());
    try std.testing.expectEqual(false, result_bools[2].get_value());
}

test "BoolSet.op_not" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const elements = [_]bool{ true, true, false };
    const set = try BoolSet.init_from_bools(&g, allocator, &elements);

    const result = try set.op_not(&g, allocator);
    const result_bools = try result.get_bools(allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(elements.len, result_bools.len);
    try std.testing.expectEqual(result_bools[0].get_value(), false);
    try std.testing.expectEqual(result_bools[1].get_value(), false);
    try std.testing.expectEqual(result_bools[2].get_value(), true);
}

test "BoolSet.op_and" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs_elements = [_]bool{ true, false };
    const rhs_elements = [_]bool{ false, true };

    const lhs = try BoolSet.init_from_bools(&g, allocator, &lhs_elements);
    const rhs = try BoolSet.init_from_bools(&g, allocator, &rhs_elements);

    const result = try lhs.op_and(&g, allocator, &rhs);
    const result_bools = try result.get_bools(allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(result_bools.len, lhs_elements.len * rhs_elements.len);
    try std.testing.expectEqual(result_bools[0].get_value(), false);
    try std.testing.expectEqual(result_bools[1].get_value(), true);
    try std.testing.expectEqual(result_bools[2].get_value(), false);
    try std.testing.expectEqual(result_bools[3].get_value(), false);
}

test "BoolSet.op_or" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs_elements = [_]bool{ true, false };
    const rhs_elements = [_]bool{ false, true };

    const lhs = try BoolSet.init_from_bools(&g, allocator, &lhs_elements);
    const rhs = try BoolSet.init_from_bools(&g, allocator, &rhs_elements);

    const result = try lhs.op_or(&g, allocator, &rhs);
    const result_bools = try result.get_bools(allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(result_bools.len, lhs_elements.len * rhs_elements.len);
    try std.testing.expectEqual(result_bools[0].get_value(), true);
    try std.testing.expectEqual(result_bools[1].get_value(), true);
    try std.testing.expectEqual(result_bools[2].get_value(), false);
    try std.testing.expectEqual(result_bools[3].get_value(), true);
}
