const graph_mod = @import("graph");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const std = @import("std");
const faebryk = @import("faebryk");
const fabll = faebryk.fabll;
const is_trait = fabll.is_trait;
const collections = @import("collections.zig");
const parameters = @import("parameters.zig");
const literals = @import("literals.zig");

fn append_child_identifier(comptime path: fabll.RefPath, comptime identifier: []const u8) fabll.RefPath {
    return comptime blk: {
        var segments: [path.segments.len + 1]fabll.RefPath.Segment = undefined;
        for (path.segments, 0..) |segment, i| {
            segments[i] = segment;
        }
        segments[path.segments.len] = .{ .child_identifier = identifier };
        const finalized = segments;
        break :blk .{ .segments = &finalized };
    };
}

fn operand_path(comptime path: fabll.RefPath) fabll.RefPath {
    return append_child_identifier(path, "can_be_operand");
}

fn owner_child_field_path(comptime identifier: []const u8) fabll.RefPath {
    return .{
        .segments = &.{
            .{ .owner_child = {} },
            .{ .child_identifier = identifier },
        },
    };
}

pub const is_expression = struct {
    node: fabll.Node,
    _is_trait: is_trait.MakeChild(),
    pub const TypeIdentifier = "is_expression";

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }
};

pub const is_predicate = struct {
    node: fabll.Node,
    _is_trait: is_trait.MakeChild(),
    pub const TypeIdentifier = "is_predicate";

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }
};

pub const OperandPointer = struct {
    node: fabll.Node,
    pub const TypeIdentifier = "OperandPointer";

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn MakeEdge(comptime pointer_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath) type {
        const edge_factory = struct {
            pub fn build() faebryk.edgebuilder.EdgeCreationAttributes {
                return faebryk.operand.EdgeOperand.build(null);
            }
        };
        return fabll.MakeDependantEdge(pointer_ref, elem_ref, edge_factory);
    }

    pub fn point(self: @This(), target: parameters.can_be_operand) void {
        const edge_ref = faebryk.operand.EdgeOperand.init(
            self.node.instance.node,
            target.node.instance.node,
            null,
        );
        _ = self.node.instance.g.insert_edge(edge_ref) catch
            @panic("failed to create operand pointer edge");
    }

    pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]parameters.can_be_operand {
        const Ctx = struct {
            out: std.array_list.Managed(parameters.can_be_operand),

            fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const operand = fabll.Node.bind_instance(
                    parameters.can_be_operand,
                    be.g.bind(faebryk.operand.EdgeOperand.get_operand_node(be.edge)),
                );
                ctx.out.append(operand) catch return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var ctx = Ctx{
            .out = std.array_list.Managed(parameters.can_be_operand).init(allocator),
        };
        errdefer ctx.out.deinit();

        switch (faebryk.operand.EdgeOperand.visit_operand_edges(self.node.instance, void, &ctx, Ctx.visit)) {
            .ERROR => |err| return err,
            else => {},
        }
        return ctx.out.toOwnedSlice();
    }

    pub fn try_deref(self: @This()) ?parameters.can_be_operand {
        const nodes = self.as_list(std.heap.page_allocator) catch return null;
        defer std.heap.page_allocator.free(nodes);
        if (nodes.len == 0) {
            return null;
        }
        return nodes[0];
    }

    pub fn deref(self: @This()) parameters.can_be_operand {
        return self.try_deref() orelse @panic("OperandPointer is not pointing to an operand");
    }
};

pub const IsSubset = struct {
    node: fabll.Node,
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
    is_parameter_operatable: is_trait.MakeEdge(parameters.is_parameter_operatable.MakeChild(), null),
    subset: OperandPointer.MakeChild(),
    superset: OperandPointer.MakeChild(),
    pub const TypeIdentifier = "IsSubset";

    pub fn MakeChild(
        comptime subset_ref: fabll.RefPath,
        comptime superset_ref: fabll.RefPath,
        comptime assert_: bool,
    ) type {
        var out = fabll.Node.MakeChild(@This())
            .add_dependant(
                OperandPointer.MakeEdge(
                    owner_child_field_path("subset"),
                    operand_path(subset_ref),
                ),
            )
            .add_dependant(
                OperandPointer.MakeEdge(
                    owner_child_field_path("superset"),
                    operand_path(superset_ref),
                ),
            );
        if (assert_) {
            out = out.add_dependant(
                is_trait
                    .MakeEdge(
                        is_predicate.MakeChild().with_owner_relative_identifier("predicate"),
                        fabll.RefPath.owner_child(),
                    ),
            );
        }
        return out;
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(
        self: @This(),
        subset: parameters.can_be_operand,
        superset: parameters.can_be_operand,
        assert_: bool,
    ) @This() {
        _ = assert_;
        self.subset.get().point(subset);
        self.superset.get().point(superset);
        return self;
    }
};

pub const Add = struct {
    node: fabll.Node,
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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

pub const Sqrt = struct {
    node: fabll.Node,
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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

pub const Log = struct {
    node: fabll.Node,
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
    operand: collections.PointerOf(parameters.can_be_operand).MakeChild(),
    zbase: collections.PointerOf(parameters.can_be_operand).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup(self: @This(), operand: parameters.can_be_operand, base: ?parameters.can_be_operand) @This() {
        self.operand.get().point(operand);
        if (base) |b| {
            self.zbase.get().point(b);
        } else {
            var tg = self.node.typegraph();
            var base_literal = literals.Numbers.create_instance(self.node.instance.g, &tg);
            base_literal = base_literal.setup_from_singleton(std.math.e, std.heap.page_allocator) catch
                @panic("failed to create default log base");
            self.zbase.get().point(base_literal.can_be_operand.get());
        }
        return self;
    }
};

pub const Sin = struct {
    node: fabll.Node,
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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

pub const Cos = struct {
    node: fabll.Node,
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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

pub const Negate = struct {
    node: fabll.Node,
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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

pub const Round = struct {
    node: fabll.Node,
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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
    is_expression: is_trait.MakeEdge(is_expression.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(parameters.can_be_operand.MakeChild(), null),
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
    const round = Round.create_instance(&g, &tg).setup(p.can_be_operand.get());
    const sqrt = Sqrt.create_instance(&g, &tg).setup(p.can_be_operand.get());
    const sin = Sin.create_instance(&g, &tg).setup(p.can_be_operand.get());
    const cos = Cos.create_instance(&g, &tg).setup(p.can_be_operand.get());
    const log = Log.create_instance(&g, &tg).setup(p.can_be_operand.get(), null);

    try std.testing.expect(neg.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(abs.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(floor.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(ceil.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(round.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(sqrt.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(sin.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(cos.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(log.operand.get().deref().node.instance.node.is_same(p.can_be_operand.get().node.instance.node));
    try std.testing.expect(log.zbase.get().try_deref() != null);
}
