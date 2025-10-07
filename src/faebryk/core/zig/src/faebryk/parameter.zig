const std = @import("std");
const graph = @import("graph").graph;

const BoundNodeReference = graph.BoundNodeReference;
const NodeReference = graph.NodeReference;
const Node = graph.Node;

// defer expression_graph.deinit();

pub const ParameterOperatable = struct {
    NumberLiteral: BoundNodeReference,
    NumberLike: BoundNodeReference,
    BooleanLiteral: BoundNodeReference,
    BooleanLike: BoundNodeReference,
    EnumLiteral: BoundNodeReference,
    EnumLike: BoundNodeReference,
    SetLiteral: BoundNodeReference,

    All: BoundNodeReference,
    Literal: BoundNodeReference,
    Sets: BoundNodeReference,

    pub const Number = struct {
        node: BoundNodeReference,

        pub fn init(g: *graph.GraphView) !*@This() {
            const number = try g.allocator.create(Number);
            number.node = try g.insert_node(try Node.init(g.allocator));
            try number.node.node.attributes.dynamic.values.put("int", .{ .Int = 0 });
            return number;
        }

        pub fn deinit(self: *@This()) void {
            self.node.g.allocator.destroy(self);
        }
    };
};

test "parameter" {
    var expression_graph = graph.GraphView.init(std.testing.allocator);
    defer expression_graph.deinit();

    const parameter1 = try ParameterOperatable.Number.init(&expression_graph);
    defer parameter1.deinit();

    std.debug.print("parameter1: {}\n", .{parameter1.node.node.attributes.uuid});
    std.debug.print("expression_graph: {}\n", .{expression_graph.nodes.items.len});
    std.debug.print("parameter1: {any}\n", .{parameter1.node.node.attributes.dynamic.values.get("int")});
}
