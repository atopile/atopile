const std = @import("std");

const graph_mod = @import("graph");
const GraphView = graph_mod.graph.GraphView;
const BoundNodeReference = graph_mod.graph.BoundNodeReference;

const faebryk = @import("faebryk");
const EdgeComposition = faebryk.composition.EdgeComposition;
const EdgeNext = faebryk.next.EdgeNext;

pub const StringNode = struct {
    node: BoundNodeReference,
    const value_identifier = "value";
    pub fn init(g: *GraphView, value: []const u8) !StringNode {
        const node = g.create_and_insert_node();
        node.node.attributes.put(value_identifier, .{ .String = value });
        return of(node);
    }

    pub fn of(node: BoundNodeReference) StringNode {
        return StringNode{ .node = node };
    }

    pub fn get_value(self: StringNode) ![]const u8 {
        return self.node.node.attributes.dynamic.get(value_identifier).?.String;
    }
};

test "StringNode.init" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const string = try StringNode.init(&g, "test");
    try std.testing.expectEqualStrings("test", try string.get_value());
}

test "StringNode.of" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const string = StringNode.of(g.create_and_insert_node());
    string.node.node.attributes.put(StringNode.value_identifier, .{ .String = "test" });
    try std.testing.expectEqualStrings("test", try string.get_value());
}

pub const StringSet = struct {
    node: BoundNodeReference,

    const set_identifier = "set";
    const head_identifier = "head";

    pub fn init(g: *GraphView, strings: []const StringNode) !StringSet {
        // Create a new node representing the string set
        const node = g.create_and_insert_node();

        // If empty, return an empty set
        if (strings.len == 0) {
            return StringSet.of(node);
        }

        // For the first string, add a child node with id 'head'
        const head_string = strings[0];
        _ = EdgeComposition.add_child(node, head_string.node.node, head_identifier);
        var previous_node = head_string.node;

        // For the remaining strings, add a child node with id 'next'
        for (strings[1..]) |next_string| {
            const new_node = try StringNode.init(g, try next_string.get_value());
            _ = EdgeNext.add_next(previous_node, new_node.node);
            previous_node = new_node.node;
        }

        return of(node);
    }

    pub fn init_empty(g: *GraphView) !StringSet {
        return try StringSet.init(g, &[_]StringNode{});
    }

    pub fn init_from_single(g: *GraphView, value: []const u8) !StringSet {
        return try StringSet.init(g, &[_]StringNode{try StringNode.init(g, value)});
    }

    pub fn init_from_strings(g: *GraphView, allocator: std.mem.Allocator, strings: []const []const u8) !StringSet {
        var string_nodes = std.ArrayList(StringNode).init(allocator);
        defer string_nodes.deinit();
        for (strings) |value| {
            try string_nodes.append(try StringNode.init(g, value));
        }
        return try StringSet.init(g, string_nodes.items);
    }
    pub fn of(node: BoundNodeReference) StringSet {
        return StringSet{ .node = node };
    }

    pub fn get_strings(self: *const StringSet, allocator: std.mem.Allocator) ![]const StringNode {
        // if there is no head node, return an empty array
        if (EdgeComposition.get_child_by_identifier(self.node, head_identifier) == null) {
            return &[_]StringNode{};
        }

        var strings = std.ArrayList(StringNode).init(allocator);
        defer strings.deinit();

        // get the head node and add it to the strings
        var bound_current = EdgeComposition.get_child_by_identifier(self.node, head_identifier) orelse return error.Empty;
        try strings.append(StringNode.of(bound_current));

        // traverse the 'next' edges and collect the StringNode nodes
        while (EdgeNext.get_next_node_from_node(bound_current)) |node_ref| {
            bound_current = bound_current.g.bind(node_ref);
            try strings.append(StringNode.of(bound_current));
        }

        const owned = try strings.toOwnedSlice();
        return owned;
    }
};

test "StringSet.init" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const allocator = std.testing.allocator;
    const string_set = try StringSet.init(&g, &[_]StringNode{try StringNode.init(&g, "test")});
    const nodes = try string_set.get_strings(allocator);
    defer allocator.free(nodes);
    try std.testing.expectEqual(@as(usize, 1), nodes.len);
    try std.testing.expectEqualStrings("test", try nodes[0].get_value());
}

test "StringSet.of" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const string_node = StringNode.of(g.create_and_insert_node());
    string_node.node.node.attributes.put(StringNode.value_identifier, .{ .String = "test" });
    try std.testing.expectEqualStrings("test", try string_node.get_value());
}

test "StringSet.init_from_single" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const string_set = try StringSet.init_from_single(&g, "test");
    const nodes = try string_set.get_strings(allocator);
    defer allocator.free(nodes);
    try std.testing.expectEqual(@as(usize, 1), nodes.len);
    try std.testing.expectEqualStrings("test", try nodes[0].get_value());
}

test "StringSet.init_from_strings" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const expected_strings = [_][]const u8{ "test", "test2", "test3" };
    const allocator = std.testing.allocator;
    const string_set = try StringSet.init_from_strings(&g, allocator, &expected_strings);
    const nodes = try string_set.get_strings(allocator);
    defer allocator.free(nodes);
    try std.testing.expectEqual(expected_strings.len, nodes.len);
    for (nodes, expected_strings) |node, expected| {
        try std.testing.expectEqualStrings(expected, try node.get_value());
    }
}
