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
    operands: collections.PointerSequenceOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), operands: []const parameters.can_be_operand) @This() {
        self.operands.get().append(operands);
        return self;
    }

    pub fn setup2(self: @This(), lhs: parameters.can_be_operand, rhs: parameters.can_be_operand) @This() {
        _ = self.setup(&.{ lhs, rhs });
        return self;
    }
};

pub const Subtract = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    minuend: collections.PointerOf(parameters.can_be_operand).MakeChild(),
    subtrahends: collections.PointerSequenceOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), minuend: parameters.can_be_operand, subtrahends: []const parameters.can_be_operand) @This() {
        self.minuend.get().point(minuend);
        self.subtrahends.get().append(subtrahends);
        return self;
    }

    pub fn setup2(self: @This(), lhs: parameters.can_be_operand, rhs: parameters.can_be_operand) @This() {
        _ = self.setup(lhs, &.{rhs});
        return self;
    }
};

pub const Multiply = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    operands: collections.PointerSequenceOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), operands: []const parameters.can_be_operand) @This() {
        self.operands.get().append(operands);
        return self;
    }

    pub fn setup2(self: @This(), lhs: parameters.can_be_operand, rhs: parameters.can_be_operand) @This() {
        _ = self.setup(&.{ lhs, rhs });
        return self;
    }
};

pub const Divide = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    numerator: collections.PointerOf(parameters.can_be_operand).MakeChild(),
    denominators: collections.PointerSequenceOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), numerator: parameters.can_be_operand, denominators: []const parameters.can_be_operand) @This() {
        self.numerator.get().point(numerator);
        self.denominators.get().append(denominators);
        return self;
    }

    pub fn setup2(self: @This(), lhs: parameters.can_be_operand, rhs: parameters.can_be_operand) @This() {
        _ = self.setup(lhs, &.{rhs});
        return self;
    }
};

pub const Power = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    base_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),
    exponent_ptr: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), base: parameters.can_be_operand, exponent: parameters.can_be_operand) @This() {
        self.base_ptr.get().point(base);
        self.exponent_ptr.get().point(exponent);
        return self;
    }
};

pub const Negate = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    operand: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), operand: parameters.can_be_operand) @This() {
        self.operand.get().point(operand);
        return self;
    }
};

pub const Abs = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    operand: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), operand: parameters.can_be_operand) @This() {
        self.operand.get().point(operand);
        return self;
    }
};

pub const Floor = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    operand: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), operand: parameters.can_be_operand) @This() {
        self.operand.get().point(operand);
        return self;
    }
};

pub const Ceil = struct {
    node: fabll.Node,
    is_expression: is_expression.MakeChild(),
    can_be_operand: parameters.can_be_operand.MakeChild(),
    operand: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), operand: parameters.can_be_operand) @This() {
        self.operand.get().point(operand);
        return self;
    }
};

test "expressions binary setup stores operands" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p1 = parameters.NumericParameter.create_instance(&g, &tg);
    const p2 = parameters.NumericParameter.create_instance(&g, &tg);
    const add = Add.create_instance(&g, &tg).setup2(p1.can_be_operand.get(), p2.can_be_operand.get());
    const ops = try add.operands.get().as_list(std.testing.allocator);
    defer std.testing.allocator.free(ops);
    try std.testing.expect(ops.len == 2);
    try std.testing.expect(ops[0].node.instance.node.is_same(p1.can_be_operand.get().node.instance.node));
    try std.testing.expect(ops[1].node.instance.node.is_same(p2.can_be_operand.get().node.instance.node));
}

test "expressions power setup stores operands" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p1 = parameters.NumericParameter.create_instance(&g, &tg);
    const p2 = parameters.NumericParameter.create_instance(&g, &tg);
    const pow = Power.create_instance(&g, &tg).setup(p1.can_be_operand.get(), p2.can_be_operand.get());

    try std.testing.expect(pow.base_ptr.get().deref().node.instance.node.is_same(p1.can_be_operand.get().node.instance.node));
    try std.testing.expect(pow.exponent_ptr.get().deref().node.instance.node.is_same(p2.can_be_operand.get().node.instance.node));
}

test "expressions unary setup stores operand" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p = parameters.NumericParameter.create_instance(&g, &tg);
    const neg = Negate.create_instance(&g, &tg).setup(p.can_be_operand.get());
    const abs = Abs.create_instance(&g, &tg).setup(p.can_be_operand.get());
    const floor = Floor.create_instance(&g, &tg).setup(p.can_be_operand.get());
    const ceil = Ceil.create_instance(&g, &tg).setup(p.can_be_operand.get());

    try std.testing.expect(neg.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(abs.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(floor.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(ceil.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
}
