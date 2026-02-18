const std = @import("std");
const pyzig = @import("pyzig");
const fabll = @import("fabll");
const graph_mod = @import("graph");
const faebryk = @import("faebryk");
const graph_py = @import("../graph/graph_py.zig");
const child_field = @import("child_field.zig");
const literal_utils = @import("literal_utils.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const graph = graph_mod.graph;

extern fn PyObject_Str(obj: ?*py.PyObject) ?*py.PyObject;

pub const ChildField = struct {
    base: child_field.ChildFieldBase = .{},
    values: []const []const u8,
    ref_path: ?*py.PyObject = null,
};

pub const ChildFieldWrapper = bind.PyObjectWrapper(ChildField);

pub fn next_strings_anon_identifier() ?[]const u8 {
    return child_field.next_anon_identifier("Strings");
}

fn next_string_literal_identifier() ?[]const u8 {
    return child_field.next_anon_identifier("String");
}

pub fn next_is_subset_identifier() ?[]const u8 {
    return child_field.next_anon_identifier("IsSubset");
}

fn coerce_string_copy(value_obj: *py.PyObject) ?[]const u8 {
    if (bind.unwrap_str_copy(value_obj)) |value| {
        return value;
    }
    py.PyErr_Clear();

    const value_str = PyObject_Str(value_obj) orelse return null;
    defer py.Py_DECREF(value_str);
    return bind.unwrap_str_copy(value_str) orelse return null;
}

fn collect_string_values_from_sequence(values_obj: *py.PyObject) ?[]const []const u8 {
    if (py.PySequence_Check(values_obj) == 0) {
        py.PyErr_SetString(py.PyExc_TypeError, "values must be a sequence of strings");
        return null;
    }

    const size = py.PySequence_Size(values_obj);
    if (size < 0) {
        return null;
    }

    var values = std.array_list.Managed([]const u8).init(std.heap.c_allocator);
    errdefer {
        for (values.items) |v| std.heap.c_allocator.free(v);
        values.deinit();
    }

    var i: isize = 0;
    while (i < size) : (i += 1) {
        const item = py.PySequence_GetItem(values_obj, i) orelse return null;
        defer py.Py_DECREF(item);

        const value_copy = coerce_string_copy(item) orelse return null;
        values.append(value_copy) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return null;
        };
    }

    return values.toOwnedSlice() catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
}

fn collect_string_values_from_args(args: ?*py.PyObject, start_index: isize) ?[]const []const u8 {
    const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
    if (positional_count < 0) {
        return null;
    }
    if (positional_count <= start_index) {
        return std.heap.c_allocator.alloc([]const u8, 0) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return null;
        };
    }

    var values = std.array_list.Managed([]const u8).init(std.heap.c_allocator);
    errdefer {
        for (values.items) |v| std.heap.c_allocator.free(v);
        values.deinit();
    }

    var i: isize = start_index;
    while (i < positional_count) : (i += 1) {
        const item = py.PyTuple_GetItem(args, i) orelse return null;
        const value_copy = coerce_string_copy(item) orelse return null;
        values.append(value_copy) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return null;
        };
    }

    return values.toOwnedSlice() catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
}

pub fn parse_strings_makechild_values(args: ?*py.PyObject, kwargs: ?*py.PyObject, start_index: isize) ?[]const []const u8 {
    if (kwargs) |kw| {
        if (py.PyDict_GetItemString(kw, "values")) |kw_values| {
            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }
            if (positional_count > start_index) {
                py.PyErr_SetString(py.PyExc_TypeError, "Use either positional values or keyword 'values', not both");
                return null;
            }
            return collect_string_values_from_sequence(kw_values);
        }
    }
    return collect_string_values_from_args(args, start_index);
}

pub fn child_field_dealloc(self: *py.PyObject) callconv(.c) void {
    const wrapper = @as(*ChildFieldWrapper, @ptrCast(@alignCast(self)));

    child_field.deinit_base(&wrapper.data.base);

    for (wrapper.data.values) |value| {
        std.heap.c_allocator.free(value);
    }
    std.heap.c_allocator.free(wrapper.data.values);

    if (wrapper.data.ref_path) |ref_path| {
        py.Py_DECREF(ref_path);
    }

    std.heap.c_allocator.destroy(wrapper.data);

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.c) void, @ptrCast(@alignCast(free_fn_any)));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn strings_make_child_with_values(
    ctx: child_field.TypegraphContext,
    identifier: []const u8,
    values: []const []const u8,
) ?graph.BoundNodeReference {
    const strings_type_node = faebryk.fabll.Node.bind_typegraph(fabll.literals.Strings, ctx.tg).get_or_create_type();
    const make_child = ctx.tg.add_make_child(
        ctx.type_node,
        strings_type_node,
        identifier,
        null,
        false,
    ) catch {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to create Strings make-child");
        return null;
    };

    const string_type_node = faebryk.fabll.Node.bind_typegraph(fabll.literals.String, ctx.tg).get_or_create_type();
    for (values) |value| {
        const lit_identifier = next_string_literal_identifier() orelse return null;
        var node_attrs: faebryk.nodebuilder.NodeCreationAttributes = .{
            .dynamic = graph.DynamicAttributes.init_on_stack(),
        };
        node_attrs.dynamic.put("value", .{ .String = value });
        _ = ctx.tg.add_make_child(
            ctx.type_node,
            string_type_node,
            lit_identifier,
            &node_attrs,
            false,
        ) catch {
            py.PyErr_SetString(py.PyExc_ValueError, "Failed to create String literal make-child");
            return null;
        };

        const lhs_path = [_]child_field.ChildTraversal{
            faebryk.composition.EdgeComposition.traverse(identifier),
            faebryk.composition.EdgeComposition.traverse("values"),
        };
        const rhs_path = [_]child_field.ChildTraversal{
            faebryk.composition.EdgeComposition.traverse(lit_identifier),
        };
        const lhs_ref = ctx.tg.ensure_child_reference(ctx.type_node, &lhs_path, true) catch {
            py.PyErr_SetString(py.PyExc_ValueError, "Failed to create Strings values reference");
            return null;
        };
        const rhs_ref = ctx.tg.ensure_child_reference(ctx.type_node, &rhs_path, true) catch {
            py.PyErr_SetString(py.PyExc_ValueError, "Failed to create String literal reference");
            return null;
        };
        _ = ctx.tg.add_make_link(
            ctx.type_node,
            lhs_ref,
            rhs_ref,
            faebryk.pointer.EdgePointer.build("e", null),
        ) catch {
            py.PyErr_SetString(py.PyExc_ValueError, "Failed to link Strings values");
            return null;
        };
    }

    return make_child;
}

fn strings_child_field_exec_literal(
    wrapper: *ChildFieldWrapper,
    t_obj: *py.PyObject,
    type_field: bool,
) ?*py.PyObject {
    const ctx = child_field.context_from_typebound(t_obj) orelse return null;
    if (wrapper.data.base.identifier == null) {
        wrapper.data.base.identifier = next_strings_anon_identifier() orelse return null;
    }
    const identifier = wrapper.data.base.identifier.?;

    if (type_field) {
        const g_ptr = ctx.tg.get_graph_view();
        var strings_instance = faebryk.fabll.Node.bind_typegraph(fabll.literals.Strings, ctx.tg).create_instance(g_ptr);
        _ = strings_instance.setup_from_values(wrapper.data.values);
        _ = faebryk.composition.EdgeComposition.add_child(
            ctx.type_node,
            strings_instance.node.instance.node,
            identifier,
        ) catch {
            py.PyErr_SetString(py.PyExc_ValueError, "Failed to add Strings type child");
            return null;
        };
        py.Py_INCREF(py.Py_None());
        return py.Py_None();
    }

    const make_child = strings_make_child_with_values(ctx, identifier, wrapper.data.values) orelse return null;
    return graph_py.makeBoundNodePyObject(make_child);
}

fn strings_child_field_exec_set_superset(
    wrapper: *ChildFieldWrapper,
    t_obj: *py.PyObject,
) ?*py.PyObject {
    const ctx = child_field.context_from_typebound(t_obj) orelse return null;
    if (wrapper.data.ref_path == null) {
        py.PyErr_SetString(py.PyExc_ValueError, "MakeChild_SetSuperset is missing ref path");
        return null;
    }

    if (wrapper.data.base.identifier == null) {
        wrapper.data.base.identifier = next_is_subset_identifier() orelse return null;
    }
    const subset_identifier = wrapper.data.base.identifier.?;
    const literal_identifier = child_field.alloc_identifier_suffix(subset_identifier, "lit") orelse return null;
    const predicate_identifier = child_field.alloc_identifier_suffix(subset_identifier, "predicate") orelse return null;

    _ = strings_make_child_with_values(ctx, literal_identifier, wrapper.data.values) orelse return null;

    const subset_make_child = literal_utils.add_setsuperset_assertion(
        t_obj,
        ctx,
        wrapper.data.ref_path.?,
        subset_identifier,
        literal_identifier,
        predicate_identifier,
    ) orelse return null;

    return graph_py.makeBoundNodePyObject(subset_make_child);
}

pub fn child_field_exec(
    wrapper: *ChildFieldWrapper,
    t_obj: *py.PyObject,
    type_field: bool,
) ?*py.PyObject {
    if (wrapper.data.ref_path != null) {
        return strings_child_field_exec_set_superset(wrapper, t_obj);
    }
    return strings_child_field_exec_literal(wrapper, t_obj, type_field);
}
