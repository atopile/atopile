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
            const lhs = try resolve_can_be_operand(expr.lhs_ptr.get().deref(), tg);
            const rhs = try resolve_can_be_operand(expr.rhs_ptr.get().deref(), tg);
            return try assert_commensurability(&.{ lhs, rhs });
        }
    }
    if (get_type(tg, expressions.Subtract)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Subtract, node);
            const lhs = try resolve_can_be_operand(expr.lhs_ptr.get().deref(), tg);
            const rhs = try resolve_can_be_operand(expr.rhs_ptr.get().deref(), tg);
            return try assert_commensurability(&.{ lhs, rhs });
        }
    }
    if (get_type(tg, expressions.Multiply)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Multiply, node);
            const lhs = try resolve_can_be_operand(expr.lhs_ptr.get().deref(), tg);
            const rhs = try resolve_can_be_operand(expr.rhs_ptr.get().deref(), tg);
            return units.op_multiply(lhs, rhs, node.g, tg) catch return Error.UnitsNotCommensurable;
        }
    }
    if (get_type(tg, expressions.Divide)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Divide, node);
            const lhs = try resolve_can_be_operand(expr.lhs_ptr.get().deref(), tg);
            const rhs = try resolve_can_be_operand(expr.rhs_ptr.get().deref(), tg);
            return units.op_divide(lhs, rhs, node.g, tg) catch return Error.UnitsNotCommensurable;
        }
    }
    if (get_type(tg, expressions.Power)) |t| {
        if (same_type(node, t)) {
            const expr = fabll.Node.bind_instance(expressions.Power, node);
            const base = try resolve_can_be_operand(expr.base_ptr.get().deref(), tg);
            return units.op_power(base, node.g, tg, expr.get_exponent());
        }
    }

    return Error.UnsupportedNodeType;
}

test "unit resolver basic expression parity" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p_v = parameters.NumericParameter.create_instance(&g, &tg)
        .setup_units(units.to_is_unit(units.Volt.create_instance(&g, &tg)), null);
    const p_a = parameters.NumericParameter.create_instance(&g, &tg)
        .setup_units(units.to_is_unit(units.Ampere.create_instance(&g, &tg)), null);

    const mul = expressions.Multiply.create_instance(&g, &tg).setup(
        p_v.can_be_operand.get(),
        p_a.can_be_operand.get(),
    );
    const div = expressions.Divide.create_instance(&g, &tg).setup(
        p_v.can_be_operand.get(),
        p_a.can_be_operand.get(),
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

