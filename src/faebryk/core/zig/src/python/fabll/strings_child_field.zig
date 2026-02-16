const std = @import("std");
const pyzig = @import("pyzig");
const fabll = @import("fabll");
const graph_mod = @import("graph");
const faebryk = @import("faebryk");
const graph_py = @import("../graph/graph_py.zig");
const common = @import("common.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const graph = graph_mod.graph;

extern fn PyObject_Str(obj: ?*py.PyObject) ?*py.PyObject;

pub const StringsChildFieldMode = enum(u8) {
    literal,
    set_superset,
};

pub const StringsChildField = struct {
    mode: StringsChildFieldMode = .literal,
    values: []const []const u8,
    identifier: ?[]const u8 = null,
    locator: ?[]const u8 = null,
    ref_path: ?*py.PyObject = null,
    type_child: bool = false,
    dependant: bool = false,
};

pub const StringsChildFieldWrapper = bind.PyObjectWrapper(StringsChildField);

var strings_child_field_counter: usize = 0;

pub fn next_strings_anon_identifier() ?[]const u8 {
    strings_child_field_counter += 1;
    return std.fmt.allocPrint(std.heap.c_allocator, "anon{d}_Strings", .{strings_child_field_counter}) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
}

fn next_string_literal_identifier() ?[]const u8 {
    strings_child_field_counter += 1;
    return std.fmt.allocPrint(std.heap.c_allocator, "anon{d}_String", .{strings_child_field_counter}) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
}

pub fn next_is_subset_identifier() ?[]const u8 {
    strings_child_field_counter += 1;
    return std.fmt.allocPrint(std.heap.c_allocator, "anon{d}_IsSubset", .{strings_child_field_counter}) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
}

fn alloc_child_identifier_suffix(base_identifier: []const u8, suffix: []const u8) ?[]const u8 {
    return std.fmt.allocPrint(std.heap.c_allocator, "{s}_{s}", .{ base_identifier, suffix }) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
}

fn call_attr_noargs(obj: *py.PyObject, attr_name: [:0]const u8) ?*py.PyObject {
    const method = py.PyObject_GetAttrString(obj, attr_name) orelse return null;
    defer py.Py_DECREF(method);

    const empty_args = py.PyTuple_New(0) orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    defer py.Py_DECREF(empty_args);

    return py.PyObject_Call(method, empty_args, null);
}

fn ensure_python_type_node(
    t_obj: *py.PyObject,
    module_name: [:0]const u8,
    class_name: [:0]const u8,
) ?graph.BoundNodeReference {
    const tg_obj = py.PyObject_GetAttrString(t_obj, "tg") orelse return null;
    defer py.Py_DECREF(tg_obj);

    const module = py.PyImport_ImportModule(module_name) orelse return null;
    defer py.Py_DECREF(module);
    const cls = py.PyObject_GetAttrString(module, class_name) orelse return null;
    defer py.Py_DECREF(cls);

    const bind_typegraph = py.PyObject_GetAttrString(cls, "bind_typegraph") orelse return null;
    defer py.Py_DECREF(bind_typegraph);

    const empty_args = py.PyTuple_New(0) orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    defer py.Py_DECREF(empty_args);

    const kwargs = py.PyDict_New() orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    defer py.Py_DECREF(kwargs);
    if (py.PyDict_SetItemString(kwargs, "tg", tg_obj) < 0) {
        return null;
    }

    const bound_type = py.PyObject_Call(bind_typegraph, empty_args, kwargs) orelse return null;
    defer py.Py_DECREF(bound_type);

    const get_or_create_type = py.PyObject_GetAttrString(bound_type, "get_or_create_type") orelse return null;
    defer py.Py_DECREF(get_or_create_type);
    const type_node_obj = py.PyObject_Call(get_or_create_type, empty_args, null) orelse return null;
    defer py.Py_DECREF(type_node_obj);

    const type_node_wrapper = bind.castWrapper(
        "BoundNode",
        &graph_py.bound_node_type,
        graph_py.BoundNodeWrapper,
        type_node_obj,
    ) orelse return null;
    return type_node_wrapper.data.*;
}

const ChildTraversal = faebryk.typegraph.TypeGraph.ChildReferenceNode.EdgeTraversal;

const TraversalPath = struct {
    traversals: std.array_list.Managed(ChildTraversal),
    held_refs: std.array_list.Managed(*py.PyObject),

    fn init() TraversalPath {
        return .{
            .traversals = std.array_list.Managed(ChildTraversal).init(std.heap.c_allocator),
            .held_refs = std.array_list.Managed(*py.PyObject).init(std.heap.c_allocator),
        };
    }

    fn deinit(self: *TraversalPath) void {
        for (self.held_refs.items) |ref_obj| {
            py.Py_DECREF(ref_obj);
        }
        self.held_refs.deinit();
        self.traversals.deinit();
    }
};

fn traversal_path_append(path: *TraversalPath, traversal: ChildTraversal) bool {
    path.traversals.append(traversal) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return false;
    };
    return true;
}

fn traversal_path_append_identifier(path: *TraversalPath, identifier: []const u8) bool {
    return traversal_path_append(path, faebryk.composition.EdgeComposition.traverse(identifier));
}

fn traversal_path_append_segment(path: *TraversalPath, segment: *py.PyObject) bool {
    if (bind.unwrap_str(segment)) |identifier| {
        return traversal_path_append_identifier(path, identifier);
    }
    py.PyErr_Clear();

    if (call_attr_noargs(segment, "get_identifier")) |identifier_obj| {
        if (identifier_obj == py.Py_None()) {
            py.Py_DECREF(identifier_obj);
            py.PyErr_SetString(py.PyExc_ValueError, "RefPath child segment has no identifier");
            return false;
        }

        path.held_refs.append(identifier_obj) catch {
            py.Py_DECREF(identifier_obj);
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return false;
        };

        const identifier = bind.unwrap_str(identifier_obj) orelse return false;
        return traversal_path_append_identifier(path, identifier);
    }
    py.PyErr_Clear();

    if (call_attr_noargs(segment, "_type_identifier")) |type_identifier_obj| {
        path.held_refs.append(type_identifier_obj) catch {
            py.Py_DECREF(type_identifier_obj);
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return false;
        };

        const type_identifier = bind.unwrap_str(type_identifier_obj) orelse return false;
        return traversal_path_append_identifier(path, type_identifier);
    }
    py.PyErr_Clear();

    py.PyErr_SetString(py.PyExc_TypeError, "RefPath segments must be str, child field, or Node type");
    return false;
}

fn parse_ref_path(ref_obj: *py.PyObject) ?TraversalPath {
    if (py.PySequence_Check(ref_obj) == 0) {
        py.PyErr_SetString(py.PyExc_TypeError, "ref must be a RefPath sequence");
        return null;
    }

    const size = py.PySequence_Size(ref_obj);
    if (size < 0) {
        return null;
    }

    var path = TraversalPath.init();
    errdefer path.deinit();

    var i: isize = 0;
    while (i < size) : (i += 1) {
        const segment = py.PySequence_GetItem(ref_obj, i) orelse return null;
        defer py.Py_DECREF(segment);
        if (!traversal_path_append_segment(&path, segment)) {
            return null;
        }
    }

    return path;
}

fn add_operand_suffix(path: *TraversalPath) bool {
    return traversal_path_append_identifier(path, "can_be_operand");
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

pub fn strings_child_field_dealloc(self: *py.PyObject) callconv(.c) void {
    const wrapper = @as(*StringsChildFieldWrapper, @ptrCast(@alignCast(self)));

    if (wrapper.data.identifier) |identifier| {
        std.heap.c_allocator.free(identifier);
    }
    if (wrapper.data.locator) |locator| {
        std.heap.c_allocator.free(locator);
    }
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

const StringsChildFieldContext = struct {
    tg: *faebryk.typegraph.TypeGraph,
    type_node: graph.BoundNodeReference,
};

fn strings_child_field_context(t_obj: *py.PyObject) ?StringsChildFieldContext {
    const tg_obj = py.PyObject_GetAttrString(t_obj, "tg") orelse return null;
    defer py.Py_DECREF(tg_obj);
    const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, tg_obj) orelse return null;

    const get_or_create_type = py.PyObject_GetAttrString(t_obj, "get_or_create_type") orelse return null;
    defer py.Py_DECREF(get_or_create_type);
    const empty_args = py.PyTuple_New(0) orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    defer py.Py_DECREF(empty_args);
    const type_node_obj = py.PyObject_Call(get_or_create_type, empty_args, null) orelse return null;
    defer py.Py_DECREF(type_node_obj);

    const type_node_wrapper = bind.castWrapper(
        "BoundNode",
        &graph_py.bound_node_type,
        graph_py.BoundNodeWrapper,
        type_node_obj,
    ) orelse return null;

    return .{
        .tg = tg_ptr,
        .type_node = type_node_wrapper.data.*,
    };
}

fn strings_make_child_with_values(
    ctx: StringsChildFieldContext,
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

        const lhs_path = [_]ChildTraversal{
            faebryk.composition.EdgeComposition.traverse(identifier),
            faebryk.composition.EdgeComposition.traverse("values"),
        };
        const rhs_path = [_]ChildTraversal{
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
    wrapper: *StringsChildFieldWrapper,
    t_obj: *py.PyObject,
    type_field: bool,
) ?*py.PyObject {
    const ctx = strings_child_field_context(t_obj) orelse return null;
    if (wrapper.data.identifier == null) {
        wrapper.data.identifier = next_strings_anon_identifier() orelse return null;
    }
    const identifier = wrapper.data.identifier.?;

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
    wrapper: *StringsChildFieldWrapper,
    t_obj: *py.PyObject,
) ?*py.PyObject {
    const ctx = strings_child_field_context(t_obj) orelse return null;
    if (wrapper.data.ref_path == null) {
        py.PyErr_SetString(py.PyExc_ValueError, "MakeChild_SetSuperset is missing ref path");
        return null;
    }

    if (wrapper.data.identifier == null) {
        wrapper.data.identifier = next_is_subset_identifier() orelse return null;
    }
    const subset_identifier = wrapper.data.identifier.?;
    const literal_identifier = alloc_child_identifier_suffix(subset_identifier, "lit") orelse return null;
    const predicate_identifier = alloc_child_identifier_suffix(subset_identifier, "predicate") orelse return null;

    _ = strings_make_child_with_values(ctx, literal_identifier, wrapper.data.values) orelse return null;

    const subset_type_node = ensure_python_type_node(
        t_obj,
        "faebryk.library.Expressions",
        "IsSubset",
    ) orelse return null;
    const predicate_type_node = ensure_python_type_node(
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

    const trait_lhs_path = [_]ChildTraversal{
        faebryk.composition.EdgeComposition.traverse(subset_identifier),
    };
    const trait_rhs_path = [_]ChildTraversal{
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

    var subset_rhs_path = parse_ref_path(wrapper.data.ref_path.?) orelse return null;
    defer subset_rhs_path.deinit();
    if (!add_operand_suffix(&subset_rhs_path)) {
        return null;
    }

    const subset_lhs_path = [_]ChildTraversal{
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

    const superset_lhs_path = [_]ChildTraversal{
        faebryk.composition.EdgeComposition.traverse(subset_identifier),
        faebryk.composition.EdgeComposition.traverse("superset"),
    };
    const superset_rhs_path = [_]ChildTraversal{
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

    return graph_py.makeBoundNodePyObject(subset_make_child);
}

pub fn strings_child_field_exec(
    wrapper: *StringsChildFieldWrapper,
    t_obj: *py.PyObject,
    type_field: bool,
) ?*py.PyObject {
    return switch (wrapper.data.mode) {
        .literal => strings_child_field_exec_literal(wrapper, t_obj, type_field),
        .set_superset => strings_child_field_exec_set_superset(wrapper, t_obj),
    };
}
