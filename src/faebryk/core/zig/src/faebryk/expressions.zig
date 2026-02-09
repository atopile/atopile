const graph_mod = @import("graph");
const graph = graph_mod.graph;
const std = @import("std");
const faebryk = @import("faebryk");
const fabll = @import("fabll.zig");
const collections = @import("collections.zig");
const parameters = @import("parameters.zig");

pub const is_expression = struct {
    node: fabll.Node,

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }
};

pub const Add = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    lhs_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),
    rhs_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), lhs: parameters.can_be_operand, rhs: parameters.can_be_operand) @This() {
        self.lhs_ptr.get().point(lhs);
        self.rhs_ptr.get().point(rhs);
        return self;
    }
};

pub const Subtract = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    lhs_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),
    rhs_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), lhs: parameters.can_be_operand, rhs: parameters.can_be_operand) @This() {
        self.lhs_ptr.get().point(lhs);
        self.rhs_ptr.get().point(rhs);
        return self;
    }
};

pub const Multiply = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    lhs_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),
    rhs_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), lhs: parameters.can_be_operand, rhs: parameters.can_be_operand) @This() {
        self.lhs_ptr.get().point(lhs);
        self.rhs_ptr.get().point(rhs);
        return self;
    }
};

pub const Divide = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    lhs_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),
    rhs_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), lhs: parameters.can_be_operand, rhs: parameters.can_be_operand) @This() {
        self.lhs_ptr.get().point(lhs);
        self.rhs_ptr.get().point(rhs);
        return self;
    }
};

pub const Power = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    base_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub const Attributes = struct {
        exponent: i64,
    };

    pub fn MakeChild(comptime exponent: i64) type {
        return fabll.MakeChildWithTypedAttrs(@This(), .{ .exponent = exponent });
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, exponent: i64) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance_with_attrs(g, .{ .exponent = exponent });
    }

    pub fn setup(self: @This(), base: parameters.can_be_operand) @This() {
        self.base_ptr.get().point(base);
        return self;
    }

    pub fn get_exponent(self: @This()) i64 {
        return fabll.get_typed_attributes(self).exponent;
    }
};

test "expressions binary setup stores operands" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p1 = parameters.NumericParameter.create_instance(&g, &tg);
    const p2 = parameters.NumericParameter.create_instance(&g, &tg);
    const add = Add.create_instance(&g, &tg).setup(p1.can_be_operand.get(), p2.can_be_operand.get());

    try std.testing.expect(add.lhs_ptr.get().deref().node.instance.node.is_same(p1.can_be_operand.get().node.instance.node));
    try std.testing.expect(add.rhs_ptr.get().deref().node.instance.node.is_same(p2.can_be_operand.get().node.instance.node));
}
