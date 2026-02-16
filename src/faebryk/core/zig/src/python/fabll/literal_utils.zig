const pyzig = @import("pyzig");
const graph_mod = @import("graph");
const faebryk = @import("faebryk");
const child_field = @import("child_field.zig");
const common = @import("common.zig");

const py = pyzig.pybindings;
const graph = graph_mod.graph;

pub fn add_setsuperset_assertion(
    t_obj: *py.PyObject,
    ctx: child_field.TypegraphContext,
    ref_path: *py.PyObject,
    subset_identifier: []const u8,
    literal_identifier: []const u8,
    predicate_identifier: []const u8,
) ?graph.BoundNodeReference {
    const subset_type_node = common.ensure_python_type_node(
        t_obj,
        "faebryk.library.Expressions",
        "IsSubset",
    ) orelse return null;
    const predicate_type_node = common.ensure_python_type_node(
        t_obj,
        "faebryk.library.Expressions",
        "is_predicate",
    ) orelse return null;

    const subset_make_child = ctx.tg.add_make_child(
        ctx.type_node,
        subset_type_node,
        subset_identifier,
        null,
        false,
    ) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to create IsSubset make-child");
        return null;
    };

    _ = ctx.tg.add_make_child(
        ctx.type_node,
        predicate_type_node,
        predicate_identifier,
        null,
        false,
    ) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to create is_predicate make-child");
        return null;
    };

    const trait_lhs_path = [_]child_field.ChildTraversal{
        faebryk.composition.EdgeComposition.traverse(subset_identifier),
    };
    const trait_rhs_path = [_]child_field.ChildTraversal{
        faebryk.composition.EdgeComposition.traverse(predicate_identifier),
    };
    const trait_lhs_ref = ctx.tg.ensure_child_reference(ctx.type_node, &trait_lhs_path, true) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to resolve IsSubset trait lhs reference");
        return null;
    };
    const trait_rhs_ref = ctx.tg.ensure_child_reference(ctx.type_node, &trait_rhs_path, true) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to resolve IsSubset trait rhs reference");
        return null;
    };
    _ = ctx.tg.add_make_link(
        ctx.type_node,
        trait_lhs_ref,
        trait_rhs_ref,
        faebryk.trait.EdgeTrait.build(),
    ) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to add IsSubset predicate trait edge");
        return null;
    };

    var subset_rhs_path = child_field.parse_ref_path(ref_path) orelse return null;
    defer subset_rhs_path.deinit();
    if (!child_field.add_path_identifier(&subset_rhs_path, "can_be_operand")) {
        return null;
    }

    const subset_lhs_path = [_]child_field.ChildTraversal{
        faebryk.composition.EdgeComposition.traverse(subset_identifier),
        faebryk.composition.EdgeComposition.traverse("subset"),
    };
    const subset_lhs_ref = ctx.tg.ensure_child_reference(ctx.type_node, &subset_lhs_path, true) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to resolve IsSubset subset lhs reference");
        return null;
    };
    const subset_rhs_ref = ctx.tg.ensure_child_reference(
        ctx.type_node,
        subset_rhs_path.traversals.items,
        true,
    ) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to resolve IsSubset subset rhs reference");
        return null;
    };
    _ = ctx.tg.add_make_link(
        ctx.type_node,
        subset_lhs_ref,
        subset_rhs_ref,
        faebryk.operand.EdgeOperand.build(null),
    ) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to link IsSubset subset operand");
        return null;
    };

    const superset_lhs_path = [_]child_field.ChildTraversal{
        faebryk.composition.EdgeComposition.traverse(subset_identifier),
        faebryk.composition.EdgeComposition.traverse("superset"),
    };
    const superset_rhs_path = [_]child_field.ChildTraversal{
        faebryk.composition.EdgeComposition.traverse(literal_identifier),
        faebryk.composition.EdgeComposition.traverse("can_be_operand"),
    };
    const superset_lhs_ref = ctx.tg.ensure_child_reference(ctx.type_node, &superset_lhs_path, true) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to resolve IsSubset superset lhs reference");
        return null;
    };
    const superset_rhs_ref = ctx.tg.ensure_child_reference(ctx.type_node, &superset_rhs_path, true) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to resolve IsSubset superset rhs reference");
        return null;
    };
    _ = ctx.tg.add_make_link(
        ctx.type_node,
        superset_lhs_ref,
        superset_rhs_ref,
        faebryk.operand.EdgeOperand.build(null),
    ) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to link IsSubset superset operand");
        return null;
    };

    return subset_make_child;
}
