const graph_mod = @import("graph");
const graph = graph_mod.graph;
const std = @import("std");
const faebryk = @import("faebryk");
const units = @import("units.zig");
const parameters = @import("parameters.zig");
const literals = @import("literals.zig");
const expressions = @import("expressions.zig");
const fabll = @import("fabll.zig");

pub const Error = error{
    UnsupportedNodeType,
    ExponentMustBeDimensionless,
    ExponentMustBeSingletonInteger,
    UnitsNotCommensurable,
    EvalRequiresNumbers,
};

fn same_type(bound_node: graph.BoundNodeReference, type_node: graph.BoundNodeReference) bool {
    return faebryk.node_type.EdgeType.is_node_instance_of(bound_node, type_node.node);
}

fn get_type(tg: *faebryk.typegraph.TypeGraph, comptime T: type) ?graph.BoundNodeReference {
    return tg.get_type_by_name(@typeName(T));
}

pub fn assert_commensurability(items: []const ?units.is_unit) Error!?units.is_unit {
    if (items.len == 0) return null;
    const first = items[0];
    for (items[1..]) |item| {
        if (!units.is_commensurable_with(first, item)) return Error.UnitsNotCommensurable;
    }
    return first;
}

pub fn resolve_can_be_operand(op: parameters.can_be_operand, tg: *faebryk.typegraph.TypeGraph) Error!?units.is_unit {
    const owner = op.get_owner_node() orelse return null;
    return resolve_node(owner, tg);
}

pub fn resolve_node(node: graph.BoundNodeReference, tg: *faebryk.typegraph.TypeGraph) Error!?units.is_unit {
    if (get_type(tg, parameters.NumericParameter)) |t| {
        if (same_type(node, t)) {
            const p = fabll.Node.bind_instance(parameters.NumericParameter, node);
            return p.try_get_units();
        }
    }
    if (get_type(tg, literals.Numbers)) |t| {
        if (same_type(node, t)) {
            const n = fabll.Node.bind_instance(literals.Numbers, node);
            return n.get_is_unit();
        }
    }

    if (get_type(tg, expressions.Add)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Add, node);
            const ops = expr.operands.get().as_list(std.heap.page_allocator) catch return Error.UnsupportedNodeType;
            defer std.heap.page_allocator.free(ops);
            if (ops.len == 0) return null;
            const first = try resolve_can_be_operand(ops[0], tg);
            for (ops[1..]) |operand| {
                const other = try resolve_can_be_operand(operand, tg);
                _ = try assert_commensurability(&.{ first, other });
            }
            return first;
        }
    }
    if (get_type(tg, expressions.Subtract)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Subtract, node);
            const minuend = try resolve_can_be_operand(expr.minuend.get().deref(), tg);
            const subtrahends = expr.subtrahends.get().as_list(std.heap.page_allocator) catch return Error.UnsupportedNodeType;
            defer std.heap.page_allocator.free(subtrahends);
            for (subtrahends) |operand| {
                const other = try resolve_can_be_operand(operand, tg);
                _ = try assert_commensurability(&.{ minuend, other });
            }
            return minuend;
        }
    }
    if (get_type(tg, expressions.Multiply)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Multiply, node);
            const ops = expr.operands.get().as_list(std.heap.page_allocator) catch return Error.UnsupportedNodeType;
            defer std.heap.page_allocator.free(ops);
            if (ops.len == 0) return null;
            var acc = try resolve_can_be_operand(ops[0], tg);
            for (ops[1..]) |operand| {
                const other = try resolve_can_be_operand(operand, tg);
                acc = units.op_multiply(acc, other, node.g, tg) catch return Error.UnitsNotCommensurable;
            }
            return acc;
        }
    }
    if (get_type(tg, expressions.Divide)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Divide, node);
            var acc = try resolve_can_be_operand(expr.numerator.get().deref(), tg);
            const denoms = expr.denominators.get().as_list(std.heap.page_allocator) catch return Error.UnsupportedNodeType;
            defer std.heap.page_allocator.free(denoms);
            for (denoms) |operand| {
                const other = try resolve_can_be_operand(operand, tg);
                acc = units.op_divide(acc, other, node.g, tg) catch return Error.UnitsNotCommensurable;
            }
            return acc;
        }
    }
    if (get_type(tg, expressions.Power)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Power, node);
            const base = try resolve_can_be_operand(expr.base_ptr.get().deref(), tg);
            const exponent_operand = expr.exponent_ptr.get().deref();
            const exponent_owner = exponent_operand.get_owner_node() orelse return Error.ExponentMustBeSingletonInteger;

            const numbers_type = get_type(tg, literals.Numbers) orelse return Error.ExponentMustBeSingletonInteger;
            if (!same_type(exponent_owner, numbers_type)) return Error.ExponentMustBeSingletonInteger;

            const exponent_numbers = fabll.Node.bind_instance(literals.Numbers, exponent_owner);
            if (!units.is_dimensionless(exponent_numbers.get_is_unit())) return Error.ExponentMustBeDimensionless;
            if (!(exponent_numbers.is_singleton(std.heap.page_allocator) catch return Error.ExponentMustBeSingletonInteger)) {
                return Error.ExponentMustBeSingletonInteger;
            }
            const exponent_value = exponent_numbers.get_single(std.heap.page_allocator) catch return Error.ExponentMustBeSingletonInteger;
            if (!std.math.approxEqAbs(f64, exponent_value, @round(exponent_value), 1e-9)) {
                return Error.ExponentMustBeSingletonInteger;
            }
            const exponent: i64 = @intFromFloat(@round(exponent_value));
            return units.op_power(base, node.g, tg, exponent);
        }
    }

    return Error.UnsupportedNodeType;
}

fn resolve_numbers_can_be_operand(
    op: parameters.can_be_operand,
    tg: *faebryk.typegraph.TypeGraph,
    allocator: std.mem.Allocator,
) Error!literals.Numbers {
    const owner = op.get_owner_node() orelse return Error.EvalRequiresNumbers;
    return resolve_numbers_node(owner, tg, allocator);
}

pub fn resolve_numbers_node(
    node: graph.BoundNodeReference,
    tg: *faebryk.typegraph.TypeGraph,
    allocator: std.mem.Allocator,
) Error!literals.Numbers {
    if (get_type(tg, literals.Numbers)) |t| {
        if (same_type(node, t)) return fabll.Node.bind_instance(literals.Numbers, node);
    }
    if (get_type(tg, expressions.Add)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Add, node);
            const ops = expr.operands.get().as_list(allocator) catch return Error.UnsupportedNodeType;
            defer allocator.free(ops);
            if (ops.len == 0) return Error.EvalRequiresNumbers;
            var acc = try resolve_numbers_can_be_operand(ops[0], tg, allocator);
            for (ops[1..]) |operand| {
                const other = try resolve_numbers_can_be_operand(operand, tg, allocator);
                acc = acc.op_add_intervals(other, allocator) catch return Error.UnitsNotCommensurable;
            }
            return acc;
        }
    }
    if (get_type(tg, expressions.Subtract)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Subtract, node);
            var acc = try resolve_numbers_can_be_operand(expr.minuend.get().deref(), tg, allocator);
            const subs = expr.subtrahends.get().as_list(allocator) catch return Error.UnsupportedNodeType;
            defer allocator.free(subs);
            for (subs) |operand| {
                const other = try resolve_numbers_can_be_operand(operand, tg, allocator);
                acc = acc.op_sub_intervals(other, allocator) catch return Error.UnitsNotCommensurable;
            }
            return acc;
        }
    }
    if (get_type(tg, expressions.Multiply)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Multiply, node);
            const ops = expr.operands.get().as_list(allocator) catch return Error.UnsupportedNodeType;
            defer allocator.free(ops);
            if (ops.len == 0) return Error.EvalRequiresNumbers;
            var acc = try resolve_numbers_can_be_operand(ops[0], tg, allocator);
            for (ops[1..]) |operand| {
                const other = try resolve_numbers_can_be_operand(operand, tg, allocator);
                acc = literals.Numbers.op_mul_intervals(acc, other, allocator) catch return Error.UnitsNotCommensurable;
            }
            return acc;
        }
    }
    if (get_type(tg, expressions.Divide)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Divide, node);
            var acc = try resolve_numbers_can_be_operand(expr.numerator.get().deref(), tg, allocator);
            const denoms = expr.denominators.get().as_list(allocator) catch return Error.UnsupportedNodeType;
            defer allocator.free(denoms);
            for (denoms) |operand| {
                const other = try resolve_numbers_can_be_operand(operand, tg, allocator);
                acc = literals.Numbers.op_div_intervals(acc, other, allocator) catch return Error.UnitsNotCommensurable;
            }
            return acc;
        }
    }
    if (get_type(tg, expressions.Power)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Power, node);
            const base = try resolve_numbers_can_be_operand(expr.base_ptr.get().deref(), tg, allocator);
            const exponent_numbers = try resolve_numbers_can_be_operand(expr.exponent_ptr.get().deref(), tg, allocator);
            if (!units.is_dimensionless(exponent_numbers.get_is_unit())) return Error.ExponentMustBeDimensionless;
            if (!(exponent_numbers.is_singleton(allocator) catch return Error.ExponentMustBeSingletonInteger)) {
                return Error.ExponentMustBeSingletonInteger;
            }
            const exponent = exponent_numbers.get_single(allocator) catch return Error.ExponentMustBeSingletonInteger;
            return base.op_pow_intervals(exponent, allocator) catch return Error.UnitsNotCommensurable;
        }
    }
    return Error.EvalRequiresNumbers;
}

test "unit resolver basic expression parity" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p_v = parameters.NumericParameter.create_instance(&g, &tg)
        .setup_units(units.to_is_unit(units.Volt.create_instance(&g, &tg)), null);
    const p_a = parameters.NumericParameter.create_instance(&g, &tg)
        .setup_units(units.to_is_unit(units.Ampere.create_instance(&g, &tg)), null);

    const mul = expressions.Multiply.create_instance(&g, &tg).setup(&.{
        p_v.can_be_operand.get(),
        p_a.can_be_operand.get(),
    });
    const div = expressions.Divide.create_instance(&g, &tg).setup(
        p_v.can_be_operand.get(),
        &.{p_a.can_be_operand.get()},
    );

    const mul_u = try resolve_node(mul.node.instance, &tg);
    const div_u = try resolve_node(div.node.instance, &tg);
    try std.testing.expect(mul_u != null);
    try std.testing.expect(div_u != null);

    const mul_repr = try units.compact_repr(mul_u, std.testing.allocator);
    defer std.testing.allocator.free(mul_repr);
    const div_repr = try units.compact_repr(div_u, std.testing.allocator);
    defer std.testing.allocator.free(div_repr);

    try std.testing.expect(std.mem.eql(u8, mul_repr, "W"));
    try std.testing.expect(std.mem.eql(u8, div_repr, "Ω"));
}

test "unit resolver power expression with numeric exponent operand" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p_v = parameters.NumericParameter.create_instance(&g, &tg)
        .setup_units(units.to_is_unit(units.Volt.create_instance(&g, &tg)), null);

    var exp = literals.Numbers.create_instance(&g, &tg);
    exp = try exp.setup_from_singleton(2.0, std.testing.allocator);

    const pow_expr = expressions.Power.create_instance(&g, &tg).setup(
        p_v.can_be_operand.get(),
        exp.can_be_operand.get(),
    );
    const resolved = try resolve_node(pow_expr.node.instance, &tg);
    try std.testing.expect(resolved != null);

    const ref = units.op_power(p_v.try_get_units(), &g, &tg, 2);
    try std.testing.expect(ref != null);
    try std.testing.expect(std.meta.eql(units.info_of(resolved), units.info_of(ref)));
}

test "unit resolver power exponent must be dimensionless integer singleton" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p_v = parameters.NumericParameter.create_instance(&g, &tg)
        .setup_units(units.to_is_unit(units.Volt.create_instance(&g, &tg)), null);

    var exp_non_integer = literals.Numbers.create_instance(&g, &tg);
    exp_non_integer = try exp_non_integer.setup_from_singleton(2.5, std.testing.allocator);
    const bad_non_integer = expressions.Power.create_instance(&g, &tg).setup(
        p_v.can_be_operand.get(),
        exp_non_integer.can_be_operand.get(),
    );
    try std.testing.expectError(Error.ExponentMustBeSingletonInteger, resolve_node(bad_non_integer.node.instance, &tg));

    var exp_unitful = literals.Numbers.create_instance(&g, &tg);
    exp_unitful = try exp_unitful.setup_from_singleton_with_unit(
        2.0,
        units.to_is_unit(units.Volt.create_instance(&g, &tg)),
        std.testing.allocator,
    );
    const bad_unitful = expressions.Power.create_instance(&g, &tg).setup(
        p_v.can_be_operand.get(),
        exp_unitful.can_be_operand.get(),
    );
    try std.testing.expectError(Error.ExponentMustBeDimensionless, resolve_node(bad_unitful.node.instance, &tg));
}

test "numbers evaluator nested arithmetic expression parity" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const volt = units.to_is_unit(units.Volt.create_instance(&g, &tg));
    const ampere = units.to_is_unit(units.Ampere.create_instance(&g, &tg));

    var v = literals.Numbers.create_instance(&g, &tg);
    v = try v.setup_from_min_max_with_unit(2.0, 3.0, volt, std.testing.allocator);
    var i = literals.Numbers.create_instance(&g, &tg);
    i = try i.setup_from_min_max_with_unit(4.0, 5.0, ampere, std.testing.allocator);
    var two = literals.Numbers.create_instance(&g, &tg);
    two = try two.setup_from_singleton(2.0, std.testing.allocator);

    const mul = expressions.Multiply.create_instance(&g, &tg).setup(&.{
        v.can_be_operand.get(),
        i.can_be_operand.get(),
    });
    const pow = expressions.Power.create_instance(&g, &tg).setup(
        mul.can_be_operand.get(),
        two.can_be_operand.get(),
    );

    const out = try resolve_numbers_node(pow.node.instance, &tg, std.testing.allocator);
    const intervals = try out.get_numeric_set().get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);
    try std.testing.expect(intervals.len == 1);
    try std.testing.expectApproxEqAbs(@as(f64, 64.0), intervals[0].min, 1e-9);
    try std.testing.expectApproxEqAbs(@as(f64, 225.0), intervals[0].max, 1e-9);
}
