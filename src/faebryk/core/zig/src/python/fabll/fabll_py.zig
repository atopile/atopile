const std = @import("std");
const pyzig = @import("pyzig");
const fabll = @import("fabll");
const graph_mod = @import("graph");
const faebryk = @import("faebryk");
const graph_py = @import("../graph/graph_py.zig");
const common = @import("common.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const type_registry = pyzig.type_registry;
const util = pyzig.util;
const graph = graph_mod.graph;

extern fn PyObject_Str(obj: ?*py.PyObject) ?*py.PyObject;

const StringWrapper = bind.PyObjectWrapper(fabll.literals.String);
const StringsWrapper = bind.PyObjectWrapper(fabll.literals.Strings);
const StringsChildFieldMode = enum(u8) {
    literal,
    set_superset,
};
const StringsChildField = struct {
    mode: StringsChildFieldMode = .literal,
    values: []const []const u8,
    identifier: ?[]const u8 = null,
    locator: ?[]const u8 = null,
    ref_path: ?*py.PyObject = null,
    type_child: bool = false,
    dependant: bool = false,
};
const StringsChildFieldWrapper = bind.PyObjectWrapper(StringsChildField);
const CountsWrapper = bind.PyObjectWrapper(fabll.literals.Counts);
const BooleansWrapper = bind.PyObjectWrapper(fabll.literals.Booleans);
const StringsBoundType = faebryk.fabll.TypeNodeBoundTG(fabll.literals.Strings);
const StringsBoundWrapper = bind.PyObjectWrapper(StringsBoundType);
const CountsBoundType = faebryk.fabll.TypeNodeBoundTG(fabll.literals.Counts);
const CountsBoundWrapper = bind.PyObjectWrapper(CountsBoundType);
const BooleansBoundType = faebryk.fabll.TypeNodeBoundTG(fabll.literals.Booleans);
const BooleansBoundWrapper = bind.PyObjectWrapper(BooleansBoundType);

var string_type: ?*py.PyTypeObject = null;
var strings_type: ?*py.PyTypeObject = null;
var counts_type: ?*py.PyTypeObject = null;
var booleans_type: ?*py.PyTypeObject = null;
var strings_child_field_type: ?*py.PyTypeObject = null;
var strings_bound_type: ?*py.PyTypeObject = null;
var counts_bound_type: ?*py.PyTypeObject = null;
var booleans_bound_type: ?*py.PyTypeObject = null;
var strings_child_field_counter: usize = 0;

fn wrap_strings_obj(value: fabll.literals.Strings) ?*py.PyObject {
    return common.wrap_owned_obj(
        "Strings",
        fabll.literals.Strings,
        StringsWrapper,
        &strings_type,
        value,
    );
}

fn wrap_strings_child_field_obj(value: StringsChildField) ?*py.PyObject {
    return common.wrap_owned_obj(
        "StringsChildField",
        StringsChildField,
        StringsChildFieldWrapper,
        &strings_child_field_type,
        value,
    );
}

fn wrap_booleans_obj(value: fabll.literals.Booleans) ?*py.PyObject {
    return common.wrap_owned_obj(
        "Booleans",
        fabll.literals.Booleans,
        BooleansWrapper,
        &booleans_type,
        value,
    );
}

fn wrap_counts_obj(value: fabll.literals.Counts) ?*py.PyObject {
    return common.wrap_owned_obj(
        "Counts",
        fabll.literals.Counts,
        CountsWrapper,
        &counts_type,
        value,
    );
}

fn wrap_strings_bound_obj(value: StringsBoundType) ?*py.PyObject {
    return common.wrap_owned_obj(
        "StringsBoundType",
        StringsBoundType,
        StringsBoundWrapper,
        &strings_bound_type,
        value,
    );
}

fn wrap_counts_bound_obj(value: CountsBoundType) ?*py.PyObject {
    return common.wrap_owned_obj(
        "CountsBoundType",
        CountsBoundType,
        CountsBoundWrapper,
        &counts_bound_type,
        value,
    );
}

fn wrap_booleans_bound_obj(value: BooleansBoundType) ?*py.PyObject {
    return common.wrap_owned_obj(
        "BooleansBoundType",
        BooleansBoundType,
        BooleansBoundWrapper,
        &booleans_bound_type,
        value,
    );
}

fn make_bound_child_accessor(
    instance: graph.BoundNodeReference,
    module_name: [:0]const u8,
    nodetype_name: [:0]const u8,
    identifier: [:0]const u8,
) ?*py.PyObject {
    const node_mod = py.PyImport_ImportModule("faebryk.core.node") orelse return null;
    defer py.Py_DECREF(node_mod);
    const accessor_cls = py.PyObject_GetAttrString(node_mod, "InstanceChildBoundInstance") orelse return null;
    defer py.Py_DECREF(accessor_cls);

    const trait_mod = py.PyImport_ImportModule(module_name) orelse return null;
    defer py.Py_DECREF(trait_mod);
    const nodetype = py.PyObject_GetAttrString(trait_mod, nodetype_name) orelse return null;
    defer py.Py_DECREF(nodetype);

    const instance_obj = graph_py.makeBoundNodePyObject(instance) orelse return null;
    defer py.Py_DECREF(instance_obj);

    const identifier_obj = bind.wrap_str(identifier) orelse return null;
    defer py.Py_DECREF(identifier_obj);

    const kwargs = py.PyDict_New() orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    defer py.Py_DECREF(kwargs);

    if (py.PyDict_SetItemString(kwargs, "nodetype", nodetype) < 0) {
        return null;
    }
    if (py.PyDict_SetItemString(kwargs, "identifier", identifier_obj) < 0) {
        return null;
    }
    if (py.PyDict_SetItemString(kwargs, "instance", instance_obj) < 0) {
        return null;
    }

    const empty_args = py.PyTuple_New(0) orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    defer py.Py_DECREF(empty_args);

    return py.PyObject_Call(accessor_cls, empty_args, kwargs);
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

fn strings_getattro(self: ?*py.PyObject, attr: ?*py.PyObject) callconv(.c) ?*py.PyObject {
    const base = py.PyObject_GenericGetAttr(self, attr);
    if (base != null) {
        return base;
    }
    if (py.PyErr_Occurred() == null) {
        return null;
    }
    py.PyErr_Clear();

    const attr_name = bind.unwrap_str(attr) orelse return null;
    if (!std.mem.eql(u8, attr_name, "is_literal")) {
        py.PyErr_SetString(py.PyExc_AttributeError, "attribute not found");
        return null;
    }

    const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
    return make_bound_child_accessor(
        wrapper.data.node.instance,
        "faebryk.library.Literals",
        "is_literal",
        "is_literal",
    );
}

fn next_strings_anon_identifier() ?[]const u8 {
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

fn next_is_subset_identifier() ?[]const u8 {
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

fn parse_strings_makechild_values(args: ?*py.PyObject, kwargs: ?*py.PyObject, start_index: isize) ?[]const []const u8 {
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

fn strings_child_field_dealloc(self: *py.PyObject) callconv(.c) void {
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

fn strings_child_field_exec(
    wrapper: *StringsChildFieldWrapper,
    t_obj: *py.PyObject,
    type_field: bool,
) ?*py.PyObject {
    return switch (wrapper.data.mode) {
        .literal => strings_child_field_exec_literal(wrapper, t_obj, type_field),
        .set_superset => strings_child_field_exec_set_superset(wrapper, t_obj),
    };
}

fn wrap_strings_child_field_set_locator() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "_set_locator",
            .doc = "Set field locator for Strings child field",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            _ = kwargs;
            const wrapper = bind.castWrapper("StringsChildField", &strings_child_field_type, StringsChildFieldWrapper, self) orelse return null;

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count != 1) {
                py.PyErr_SetString(py.PyExc_TypeError, "_set_locator expects exactly one argument");
                return null;
            }
            const locator_obj = py.PyTuple_GetItem(args, 0) orelse return null;

            if (wrapper.data.locator) |old| {
                std.heap.c_allocator.free(old);
                wrapper.data.locator = null;
            }

            if (locator_obj != py.Py_None()) {
                const locator_copy = bind.unwrap_str_copy(locator_obj) orelse return null;
                wrapper.data.locator = locator_copy;
                if (wrapper.data.identifier == null) {
                    wrapper.data.identifier = std.heap.c_allocator.dupe(u8, locator_copy) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                        return null;
                    };
                }
            } else if (wrapper.data.identifier == null) {
                wrapper.data.identifier = switch (wrapper.data.mode) {
                    .literal => next_strings_anon_identifier(),
                    .set_superset => next_is_subset_identifier(),
                } orelse return null;
            }

            py.Py_INCREF(self.?);
            return self;
        }
    };
}

fn wrap_strings_child_field_get_identifier() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_identifier",
            .doc = "Get identifier for Strings child field",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("StringsChildField", &strings_child_field_type, StringsChildFieldWrapper, self) orelse return null;
            if (wrapper.data.identifier) |identifier| {
                return bind.wrap_str(identifier);
            }
            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_strings_child_field_get_nodetype() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_nodetype",
            .doc = "Return nodetype for this child field",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("StringsChildField", &strings_child_field_type, StringsChildFieldWrapper, self) orelse return null;
            if (wrapper.data.mode == .set_superset) {
                py.Py_INCREF(py.Py_None());
                return py.Py_None();
            }

            const cls = strings_type orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "Strings type is not registered");
                return null;
            };
            const out = @as(*py.PyObject, @ptrCast(@alignCast(cls)));
            py.Py_INCREF(out);
            return out;
        }
    };
}

fn wrap_strings_child_field_put_on_type() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "put_on_type",
            .doc = "Mark this child field as type-level",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("StringsChildField", &strings_child_field_type, StringsChildFieldWrapper, self) orelse return null;
            wrapper.data.type_child = true;
            py.Py_INCREF(self.?);
            return self;
        }
    };
}

fn wrap_strings_child_field_mark_dependant() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "mark_dependant",
            .doc = "Mark this child field as dependant",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("StringsChildField", &strings_child_field_type, StringsChildFieldWrapper, self) orelse return null;
            wrapper.data.dependant = true;
            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_strings_child_field_is_dependant() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_dependant",
            .doc = "Return whether this child field is marked as dependant",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("StringsChildField", &strings_child_field_type, StringsChildFieldWrapper, self) orelse return null;
            return bind.wrap_bool(wrapper.data.dependant);
        }
    };
}

fn wrap_strings_child_field_is_type_child() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_type_child",
            .doc = "Return whether this field is marked put_on_type",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("StringsChildField", &strings_child_field_type, StringsChildFieldWrapper, self) orelse return null;
            return bind.wrap_bool(wrapper.data.type_child);
        }
    };
}

fn wrap_strings_child_field_exec_to_typegraph() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "_exec_to_typegraph",
            .doc = "Materialize this Strings child field into the target typegraph",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("StringsChildField", &strings_child_field_type, StringsChildFieldWrapper, self) orelse return null;

            var t_obj: ?*py.PyObject = null;
            var type_field = false;

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }
            if (positional_count >= 1) {
                t_obj = py.PyTuple_GetItem(args, 0);
            }
            if (positional_count >= 2) {
                type_field = bind.unwrap_bool(py.PyTuple_GetItem(args, 1));
            }

            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "t")) |kw_t| {
                    if (t_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "_exec_to_typegraph received duplicate 't' argument");
                        return null;
                    }
                    t_obj = kw_t;
                }
                if (py.PyDict_GetItemString(kw, "type_field")) |kw_type_field| {
                    type_field = bind.unwrap_bool(kw_type_field);
                }
            }

            const t = t_obj orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "_exec_to_typegraph requires t");
                return null;
            };

            return strings_child_field_exec(wrapper, t, type_field or wrapper.data.type_child);
        }
    };
}

fn wrap_strings_child_field(root: *py.PyObject) void {
    const methods = [_]type{
        wrap_strings_child_field_set_locator(),
        wrap_strings_child_field_get_identifier(),
        wrap_strings_child_field_get_nodetype(),
        wrap_strings_child_field_put_on_type(),
        wrap_strings_child_field_mark_dependant(),
        wrap_strings_child_field_is_dependant(),
        wrap_strings_child_field_is_type_child(),
        wrap_strings_child_field_exec_to_typegraph(),
    };
    bind.wrap_namespace_struct(root, StringsChildField, methods);
    strings_child_field_type = type_registry.getRegisteredTypeObject(util.shortTypeName(StringsChildField));

    if (strings_child_field_type) |typ| {
        typ.tp_dealloc = @ptrCast(&strings_child_field_dealloc);
    }
}

fn wrap_strings_make_child() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "MakeChild",
            .doc = "Create a Strings child field with optional values",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const values = parse_strings_makechild_values(args, kwargs, 0) orelse return null;
            return wrap_strings_child_field_obj(.{ .values = values }) orelse {
                for (values) |value| std.heap.c_allocator.free(value);
                std.heap.c_allocator.free(values);
                return null;
            };
        }
    };
}

fn wrap_strings_make_child_set_superset() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "MakeChild_SetSuperset",
            .doc = "Create an asserted IsSubset child linking a ref to a Strings literal",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }

            var ref_obj: ?*py.PyObject = null;
            if (positional_count >= 1) {
                ref_obj = py.PyTuple_GetItem(args, 0);
            }
            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "ref")) |kw_ref| {
                    if (ref_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "MakeChild_SetSuperset received duplicate 'ref' argument");
                        return null;
                    }
                    ref_obj = kw_ref;
                }
            }
            if (ref_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "MakeChild_SetSuperset requires ref");
                return null;
            }

            const values = parse_strings_makechild_values(args, kwargs, 1) orelse return null;
            py.Py_INCREF(ref_obj.?);
            return wrap_strings_child_field_obj(.{
                .mode = .set_superset,
                .values = values,
                .ref_path = ref_obj.?,
            }) orelse {
                py.Py_DECREF(ref_obj.?);
                for (values) |value| std.heap.c_allocator.free(value);
                std.heap.c_allocator.free(values);
                return null;
            };
        }
    };
}

fn wrap_string_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a new Zig fabll String literal instance",
            .args_def = struct {
                g: *py.PyObject,
                tg: *py.PyObject,
                value: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const value_copy = bind.unwrap_str_copy(kwarg_obj.value) orelse return null;

            const literal = fabll.literals.String.create_instance(g_ptr, tg_ptr, value_copy);
            return common.wrap_owned_obj(
                "String",
                fabll.literals.String,
                StringWrapper,
                &string_type,
                literal,
            );
        }
    };
}

fn wrap_string_bind_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_instance",
            .doc = "Bind an existing node instance as a Zig fabll String",
            .args_def = struct {
                instance: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .instance = bind.ARG{ .Wrapper = graph_py.BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const literal = faebryk.fabll.Node.bind_instance(fabll.literals.String, kwarg_obj.instance.*);
            return common.wrap_owned_obj(
                "String",
                fabll.literals.String,
                StringWrapper,
                &string_type,
                literal,
            );
        }
    };
}

fn wrap_string_get_value() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_value",
            .doc = "Get literal string value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("String", &string_type, StringWrapper, self) orelse return null;
            return bind.wrap_str(wrapper.data.get_value());
        }
    };
}

fn wrap_string_get_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_instance",
            .doc = "Get bound node instance for this literal",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("String", &string_type, StringWrapper, self) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.node.instance);
        }
    };
}

fn wrap_string(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_string_create_instance(),
        wrap_string_bind_instance(),
        wrap_string_get_value(),
        wrap_string_get_instance(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.String, extra_methods);
    string_type = type_registry.getRegisteredTypeObject("String");

    if (string_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(StringWrapper));
    }
}

fn wrap_strings_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a new Zig fabll Strings literal instance",
            .args_def = struct {
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const literal = faebryk.fabll.Node.bind_typegraph(fabll.literals.Strings, tg_ptr).create_instance(g_ptr);
            return common.wrap_owned_obj(
                "Strings",
                fabll.literals.Strings,
                StringsWrapper,
                &strings_type,
                literal,
            );
        }
    };
}

fn wrap_strings_bind_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_instance",
            .doc = "Bind an existing node instance as a Zig fabll Strings literal",
            .args_def = struct {
                instance: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .instance = bind.ARG{ .Wrapper = graph_py.BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const literal = faebryk.fabll.Node.bind_instance(fabll.literals.Strings, kwarg_obj.instance.*);
            return common.wrap_owned_obj(
                "Strings",
                fabll.literals.Strings,
                StringsWrapper,
                &strings_type,
                literal,
            );
        }
    };
}

fn wrap_strings_get_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_instance",
            .doc = "Get bound node instance for this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.node.instance);
        }
    };
}

fn wrap_strings_setup_from_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "setup_from_values",
            .doc = "Populate this Strings literal set from provided values",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const values_obj: *py.PyObject = blk: {
                if (kwargs) |kw| {
                    if (py.PyDict_GetItemString(kw, "values")) |kw_values| {
                        if (args != null and py.PyTuple_Size(args) != 0) {
                            py.PyErr_SetString(py.PyExc_TypeError, "Use either positional values or keyword 'values', not both");
                            return null;
                        }
                        break :blk kw_values;
                    }
                }

                const pos_args = args orelse {
                    py.PyErr_SetString(py.PyExc_TypeError, "Missing values");
                    return null;
                };
                break :blk pos_args;
            };

            if (py.PySequence_Check(values_obj) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "values must be a sequence of strings");
                return null;
            }

            const size = py.PySequence_Size(values_obj);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed([]const u8).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(values_obj, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                const value_copy = bind.unwrap_str_copy(item) orelse return null;
                values.append(value_copy) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            _ = wrapper.data.setup_from_values(values.items);
            const self_obj = self orelse return null;
            py.Py_INCREF(self_obj);
            return self_obj;
        }
    };
}

fn wrap_strings_get_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_values",
            .doc = "Return all string values in this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const values = wrapper.data.get_values(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to retrieve values");
                return null;
            };
            defer allocator.free(values);

            const out_list = py.PyList_New(@intCast(values.len));
            if (out_list == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (values, 0..) |value, idx| {
                const py_value = bind.wrap_str(value) orelse {
                    py.Py_DECREF(out_list.?);
                    return null;
                };
                if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
            }

            return out_list;
        }
    };
}

fn wrap_strings_is_singleton() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_singleton",
            .doc = "Check whether this Strings literal set has exactly one value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const out = wrapper.data.is_singleton(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute singleton check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_strings_get_single() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_single",
            .doc = "Get the single value in this Strings literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const out = wrapper.data.get_single(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected singleton StringSet");
                return null;
            };
            return bind.wrap_str(out);
        }
    };
}

fn wrap_strings_is_empty() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_empty",
            .doc = "Check whether this Strings literal set is empty",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const out = wrapper.data.is_empty(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute emptiness check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_strings_any() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "any",
            .doc = "Return an arbitrary member of this Strings literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const out = wrapper.data.any(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Cannot select a value from an empty StringSet");
                return null;
            };
            return bind.wrap_str(out);
        }
    };
}

fn strings_parse_binary_other(args: ?*py.PyObject, kwargs: ?*py.PyObject) ?*fabll.literals.Strings {
    var other_obj: ?*py.PyObject = null;

    const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
    if (positional_count < 0) {
        return null;
    }
    if (positional_count > 1) {
        py.PyErr_SetString(py.PyExc_TypeError, "Expected at most one positional argument for 'other'");
        return null;
    }
    if (positional_count == 1) {
        other_obj = py.PyTuple_GetItem(args, 0);
    }

    if (kwargs) |kw| {
        if (py.PyDict_GetItemString(kw, "other")) |kw_other| {
            if (other_obj != null) {
                py.PyErr_SetString(py.PyExc_TypeError, "Received both positional and keyword argument for 'other'");
                return null;
            }
            other_obj = kw_other;
        }
    }

    if (other_obj == null) {
        py.PyErr_SetString(py.PyExc_TypeError, "Missing required argument 'other'");
        return null;
    }

    const other_wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, other_obj) orelse return null;
    return other_wrapper.data;
}

const StringsBinaryReturnKind = enum {
    bool,
    strings,
    booleans,
};

fn wrap_strings_binary_method(
    comptime method_ident: []const u8,
    comptime method_name: [:0]const u8,
    comptime doc: [:0]const u8,
    comptime return_kind: StringsBinaryReturnKind,
    comptime error_message: [:0]const u8,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = method_name,
            .doc = doc,
            .args_def = struct {
                other: *fabll.literals.Strings,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = StringsWrapper, .storage = &strings_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const other = strings_parse_binary_other(args, kwargs) orelse return null;
            const method = @field(fabll.literals.Strings, method_ident);

            switch (return_kind) {
                .bool => {
                    const out = method(wrapper.data.*, other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return bind.wrap_bool(out);
                },
                .strings => {
                    const out = method(wrapper.data.*, other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_strings_obj(out);
                },
                .booleans => {
                    const out = method(wrapper.data.*, other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_booleans_obj(out);
                },
            }
        }
    };
}

fn wrap_strings_op_setic_equals() type {
    return wrap_strings_binary_method(
        "op_setic_equals",
        "op_setic_equals",
        "Setic equality for Strings literals",
        .bool,
        "Failed to compare StringSets",
    );
}

fn wrap_strings_op_setic_is_subset_of() type {
    return wrap_strings_binary_method(
        "op_setic_is_subset_of",
        "op_setic_is_subset_of",
        "Setic subset check for Strings literals",
        .bool,
        "Failed to compare StringSets",
    );
}

fn wrap_strings_uncertainty_equals() type {
    return wrap_strings_binary_method(
        "uncertainty_equals",
        "uncertainty_equals",
        "Uncertainty equality for Strings literals",
        .booleans,
        "Failed to compare uncertainty for StringSets",
    );
}

fn wrap_strings_nary_method(
    comptime method_ident: []const u8,
    comptime method_name: [:0]const u8,
    comptime doc: [:0]const u8,
    comptime error_message: [:0]const u8,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = method_name,
            .doc = doc,
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const method = @field(fabll.literals.Strings, method_ident);

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }

            var collected = std.array_list.Managed(*fabll.literals.Strings).init(std.heap.c_allocator);
            defer collected.deinit();

            var i: isize = 0;
            while (i < positional_count) : (i += 1) {
                const item = py.PyTuple_GetItem(args, i);
                const other = bind.castWrapper("Strings", &strings_type, StringsWrapper, item) orelse return null;
                collected.append(other.data) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "other")) |kw_other| {
                    const other = bind.castWrapper("Strings", &strings_type, StringsWrapper, kw_other) orelse return null;
                    collected.append(other.data) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                        return null;
                    };
                }
            }

            if (collected.items.len == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "Expected at least one other Strings operand");
                return null;
            }

            var acc = wrapper.data.*;
            for (collected.items) |other| {
                acc = method(acc, other.*, std.heap.c_allocator) catch {
                    py.PyErr_SetString(py.PyExc_ValueError, error_message);
                    return null;
                };
            }
            return wrap_strings_obj(acc);
        }
    };
}

fn wrap_strings_op_intersect_intervals() type {
    return wrap_strings_nary_method(
        "op_intersect_intervals",
        "op_intersect_intervals",
        "Set intersection for Strings literals",
        "Failed to intersect StringSets",
    );
}

fn wrap_strings_op_union_intervals() type {
    return wrap_strings_nary_method(
        "op_union_intervals",
        "op_union_intervals",
        "Set union for Strings literals",
        "Failed to union StringSets",
    );
}

fn wrap_strings_op_symmetric_difference_intervals() type {
    return wrap_strings_binary_method(
        "op_symmetric_difference_intervals",
        "op_symmetric_difference_intervals",
        "Set symmetric difference for Strings literals",
        .strings,
        "Failed to compute symmetric difference for StringSets",
    );
}

fn wrap_strings_pretty_str() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "pretty_str",
            .doc = "Pretty-print this Strings literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const out = wrapper.data.pretty_str(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to pretty-print StringSet");
                return null;
            };
            defer allocator.free(out);
            return bind.wrap_str(out);
        }
    };
}

fn wrap_strings_serialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "serialize",
            .doc = "Serialize this Strings literal set to API format",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const values = wrapper.data.get_values(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to serialize StringSet");
                return null;
            };
            defer allocator.free(values);

            const out = py.PyDict_New();
            if (out == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const type_obj = bind.wrap_str("StringSet") orelse {
                py.Py_DECREF(out.?);
                return null;
            };
            if (py.PyDict_SetItemString(out, "type", type_obj) < 0) {
                py.Py_DECREF(type_obj);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(type_obj);

            const data_obj = py.PyDict_New();
            if (data_obj == null) {
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const values_list = py.PyList_New(@intCast(values.len));
            if (values_list == null) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (values, 0..) |value, idx| {
                const py_value = bind.wrap_str(value) orelse {
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                };
                if (py.PyList_SetItem(values_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value);
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                }
            }

            if (py.PyDict_SetItemString(data_obj, "values", values_list) < 0) {
                py.Py_DECREF(values_list.?);
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(values_list.?);

            if (py.PyDict_SetItemString(out, "data", data_obj) < 0) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(data_obj.?);

            return out;
        }
    };
}

fn wrap_strings_deserialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "deserialize",
            .doc = "Deserialize a Strings literal set from API format",
            .args_def = struct {
                data: *py.PyObject,
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            _ = self;
            var data_obj: ?*py.PyObject = null;
            var g_obj: ?*py.PyObject = null;
            var tg_obj: ?*py.PyObject = null;

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }
            if (positional_count > 3) {
                py.PyErr_SetString(py.PyExc_TypeError, "deserialize accepts at most three positional arguments: data, g, tg");
                return null;
            }
            if (positional_count >= 1) data_obj = py.PyTuple_GetItem(args, 0);
            if (positional_count >= 2) g_obj = py.PyTuple_GetItem(args, 1);
            if (positional_count >= 3) tg_obj = py.PyTuple_GetItem(args, 2);

            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "data")) |kw_data| {
                    if (data_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "deserialize received duplicate 'data' argument");
                        return null;
                    }
                    data_obj = kw_data;
                }
                if (py.PyDict_GetItemString(kw, "g")) |kw_g| {
                    if (g_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "deserialize received duplicate 'g' argument");
                        return null;
                    }
                    g_obj = kw_g;
                }
                if (py.PyDict_GetItemString(kw, "tg")) |kw_tg| {
                    if (tg_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "deserialize received duplicate 'tg' argument");
                        return null;
                    }
                    tg_obj = kw_tg;
                }
            }

            if (data_obj == null or g_obj == null or tg_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "deserialize requires data, g, and tg");
                return null;
            }

            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, g_obj.?) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, tg_obj.?) orelse return null;

            const type_obj = py.PyDict_GetItemString(data_obj.?, "type") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing required field 'type'");
                return null;
            };

            const type_value = bind.unwrap_str(type_obj) orelse return null;
            if (!std.mem.eql(u8, type_value, "StringSet")) {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected type 'StringSet'");
                return null;
            }

            const payload_obj = py.PyDict_GetItemString(data_obj.?, "data") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'data' field");
                return null;
            };

            const values_obj = py.PyDict_GetItemString(payload_obj, "values") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            };
            if (py.PySequence_Check(values_obj) == 0) {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            }

            const size = py.PySequence_Size(values_obj);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed([]const u8).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(values_obj, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                const value_copy = bind.unwrap_str_copy(item) orelse return null;
                values.append(value_copy) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            const serialized = fabll.literals.StringsSerialized{
                .@"type" = "StringSet",
                .data = .{ .values = values.items },
            };
            const out = fabll.literals.Strings.deserialize(serialized, g_ptr, tg_ptr) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to deserialize StringSet");
                return null;
            };
            return wrap_strings_obj(out);
        }
    };
}

fn wrap_strings_type_identifier() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "_type_identifier",
            .doc = "Return Zig type identifier for this literal type",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            return bind.wrap_str(@typeName(fabll.literals.Strings));
        }
    };
}

fn wrap_strings_bind_typegraph() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_typegraph",
            .doc = "Bind Strings type to a Zig TypeGraph",
            .args_def = struct {
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            _ = self;
            var tg_obj: ?*py.PyObject = null;

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }
            if (positional_count > 1) {
                py.PyErr_SetString(py.PyExc_TypeError, "bind_typegraph accepts at most one positional argument");
                return null;
            }
            if (positional_count == 1) {
                tg_obj = py.PyTuple_GetItem(args, 0);
            }

            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "tg")) |kw_tg| {
                    if (tg_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "bind_typegraph received duplicate 'tg' argument");
                        return null;
                    }
                    tg_obj = kw_tg;
                }
            }

            if (tg_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "bind_typegraph requires tg");
                return null;
            }

            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, tg_obj.?) orelse return null;
            const bound = faebryk.fabll.Node.bind_typegraph(fabll.literals.Strings, tg_ptr);
            return wrap_strings_bound_obj(bound);
        }
    };
}

fn wrap_strings_bound_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a Strings instance from a bound Zig type",
            .args_def = struct {
                g: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(
                "StringsBoundType",
                &strings_bound_type,
                StringsBoundWrapper,
                self,
            ) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            return wrap_strings_obj(wrapper.data.create_instance(g_ptr));
        }
    };
}

fn wrap_strings_bound_get_or_create_type() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_or_create_type",
            .doc = "Get or create the Zig type node for this bound Strings type",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(
                "StringsBoundType",
                &strings_bound_type,
                StringsBoundWrapper,
                self,
            ) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.get_or_create_type());
        }
    };
}

fn wrap_strings_bound(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_strings_bound_create_instance(),
        wrap_strings_bound_get_or_create_type(),
    };
    bind.wrap_namespace_struct(root, StringsBoundType, extra_methods);
    strings_bound_type = type_registry.getRegisteredTypeObject(
        util.shortTypeName(StringsBoundType),
    );

    if (strings_bound_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(StringsBoundWrapper));
    }
}

fn wrap_strings(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_strings_make_child(),
        wrap_strings_make_child_set_superset(),
        wrap_strings_create_instance(),
        wrap_strings_bind_instance(),
        wrap_strings_bind_typegraph(),
        wrap_strings_type_identifier(),
        wrap_strings_get_instance(),
        wrap_strings_setup_from_values(),
        wrap_strings_get_values(),
        wrap_strings_is_singleton(),
        wrap_strings_get_single(),
        wrap_strings_is_empty(),
        wrap_strings_any(),
        wrap_strings_op_setic_equals(),
        wrap_strings_op_setic_is_subset_of(),
        wrap_strings_uncertainty_equals(),
        wrap_strings_op_intersect_intervals(),
        wrap_strings_op_union_intervals(),
        wrap_strings_op_symmetric_difference_intervals(),
        wrap_strings_pretty_str(),
        wrap_strings_serialize(),
        wrap_strings_deserialize(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.Strings, extra_methods);
    strings_type = type_registry.getRegisteredTypeObject("Strings");

    if (strings_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(StringsWrapper));
        typ.tp_getattro = @ptrCast(&strings_getattro);
    }

    wrap_strings_bound(root);
}

fn wrap_counts_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a new Zig fabll Counts literal instance",
            .args_def = struct {
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const literal = faebryk.fabll.Node.bind_typegraph(fabll.literals.Counts, tg_ptr).create_instance(g_ptr);
            return wrap_counts_obj(literal);
        }
    };
}

fn wrap_counts_bind_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_instance",
            .doc = "Bind an existing node instance as a Zig fabll Counts literal",
            .args_def = struct {
                instance: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .instance = bind.ARG{ .Wrapper = graph_py.BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const literal = faebryk.fabll.Node.bind_instance(fabll.literals.Counts, kwarg_obj.instance.*);
            return wrap_counts_obj(literal);
        }
    };
}

fn wrap_counts_get_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_instance",
            .doc = "Get bound node instance for this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.node.instance);
        }
    };
}

fn wrap_counts_setup_from_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "setup_from_values",
            .doc = "Populate this Counts literal set from provided values",
            .args_def = struct {
                values: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (py.PySequence_Check(kwarg_obj.values) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "values must be a sequence of integers");
                return null;
            }

            const size = py.PySequence_Size(kwarg_obj.values);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed(i64).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(kwarg_obj.values, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                py.PyErr_Clear();
                const value_raw = py.PyLong_AsLongLong(item);
                if (py.PyErr_Occurred() != null) {
                    py.PyErr_Clear();
                    py.PyErr_SetString(py.PyExc_ValueError, "Expected integer value");
                    return null;
                }
                values.append(@intCast(value_raw)) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            _ = wrapper.data.setup_from_values(values.items);
            const self_obj = self orelse return null;
            py.Py_INCREF(self_obj);
            return self_obj;
        }
    };
}

fn wrap_counts_get_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_values",
            .doc = "Return all count values in this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const values = wrapper.data.get_values(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to retrieve values");
                return null;
            };
            defer allocator.free(values);

            const out_list = py.PyList_New(@intCast(values.len));
            if (out_list == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (values, 0..) |value, idx| {
                const py_value = py.PyLong_FromLongLong(@intCast(value));
                if (py_value == null) {
                    py.Py_DECREF(out_list.?);
                    return null;
                }
                if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value.?);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
            }

            return out_list;
        }
    };
}

fn wrap_counts_is_singleton() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_singleton",
            .doc = "Check whether this Counts literal set has exactly one value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const out = wrapper.data.is_singleton(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute singleton check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_counts_get_single() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_single",
            .doc = "Get the single value in this Counts literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const out = wrapper.data.get_single(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected singleton CountSet");
                return null;
            };
            return py.PyLong_FromLongLong(@intCast(out));
        }
    };
}

fn wrap_counts_is_empty() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_empty",
            .doc = "Check whether this Counts literal set is empty",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const out = wrapper.data.is_empty(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute emptiness check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_counts_any() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "any",
            .doc = "Return an arbitrary member of this Counts literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const out = wrapper.data.any(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Cannot select a value from an empty CountSet");
                return null;
            };
            return py.PyLong_FromLongLong(@intCast(out));
        }
    };
}

const CountsBinaryReturnKind = enum {
    bool,
    counts,
    booleans,
};

fn wrap_counts_binary_method(
    comptime method_ident: []const u8,
    comptime method_name: [:0]const u8,
    comptime doc: [:0]const u8,
    comptime return_kind: CountsBinaryReturnKind,
    comptime error_message: [:0]const u8,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = method_name,
            .doc = doc,
            .args_def = struct {
                other: *fabll.literals.Counts,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = CountsWrapper, .storage = &counts_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const method = @field(fabll.literals.Counts, method_ident);

            switch (return_kind) {
                .bool => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return bind.wrap_bool(out);
                },
                .counts => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_counts_obj(out);
                },
                .booleans => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_booleans_obj(out);
                },
            }
        }
    };
}

fn wrap_counts_op_setic_equals() type {
    return wrap_counts_binary_method(
        "op_setic_equals",
        "op_setic_equals",
        "Setic equality for Counts literals",
        .bool,
        "Failed to compare CountSets",
    );
}

fn wrap_counts_op_setic_is_subset_of() type {
    return wrap_counts_binary_method(
        "op_setic_is_subset_of",
        "op_setic_is_subset_of",
        "Setic subset check for Counts literals",
        .bool,
        "Failed to compare CountSets",
    );
}

fn wrap_counts_uncertainty_equals() type {
    return wrap_counts_binary_method(
        "uncertainty_equals",
        "uncertainty_equals",
        "Uncertainty equality for Counts literals",
        .booleans,
        "Failed to compare uncertainty for CountSets",
    );
}

fn wrap_counts_op_intersect_intervals() type {
    return wrap_counts_binary_method(
        "op_intersect_intervals",
        "op_intersect_intervals",
        "Set intersection for Counts literals",
        .counts,
        "Failed to intersect CountSets",
    );
}

fn wrap_counts_op_union_intervals() type {
    return wrap_counts_binary_method(
        "op_union_intervals",
        "op_union_intervals",
        "Set union for Counts literals",
        .counts,
        "Failed to union CountSets",
    );
}

fn wrap_counts_op_symmetric_difference_intervals() type {
    return wrap_counts_binary_method(
        "op_symmetric_difference_intervals",
        "op_symmetric_difference_intervals",
        "Set symmetric difference for Counts literals",
        .counts,
        "Failed to compute symmetric difference for CountSets",
    );
}

fn wrap_counts_serialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "serialize",
            .doc = "Serialize this Counts literal set to API format",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const serialized = wrapper.data.serialize(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to serialize CountSet");
                return null;
            };
            defer allocator.free(serialized.data.values);

            const out = py.PyDict_New();
            if (out == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const type_obj = bind.wrap_str("CountSet") orelse {
                py.Py_DECREF(out.?);
                return null;
            };
            if (py.PyDict_SetItemString(out, "type", type_obj) < 0) {
                py.Py_DECREF(type_obj);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(type_obj);

            const data_obj = py.PyDict_New();
            if (data_obj == null) {
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const values_list = py.PyList_New(@intCast(serialized.data.values.len));
            if (values_list == null) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (serialized.data.values, 0..) |value, idx| {
                const py_value = py.PyLong_FromLongLong(@intCast(value));
                if (py_value == null) {
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                }
                if (py.PyList_SetItem(values_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value.?);
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                }
            }

            if (py.PyDict_SetItemString(data_obj, "values", values_list) < 0) {
                py.Py_DECREF(values_list.?);
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(values_list.?);

            if (py.PyDict_SetItemString(out, "data", data_obj) < 0) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(data_obj.?);

            return out;
        }
    };
}

fn wrap_counts_deserialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "deserialize",
            .doc = "Deserialize a Counts literal set from API format",
            .args_def = struct {
                data: *py.PyObject,
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;

            const type_obj = py.PyDict_GetItemString(kwarg_obj.data, "type") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing required field 'type'");
                return null;
            };

            const type_value = bind.unwrap_str(type_obj) orelse return null;
            if (!std.mem.eql(u8, type_value, "CountSet")) {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected type 'CountSet'");
                return null;
            }

            const data_obj = py.PyDict_GetItemString(kwarg_obj.data, "data") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'data' field");
                return null;
            };

            const values_obj = py.PyDict_GetItemString(data_obj, "values") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            };
            if (py.PySequence_Check(values_obj) == 0) {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            }

            const size = py.PySequence_Size(values_obj);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed(i64).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(values_obj, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                py.PyErr_Clear();
                const value_raw = py.PyLong_AsLongLong(item);
                if (py.PyErr_Occurred() != null) {
                    py.PyErr_Clear();
                    py.PyErr_SetString(py.PyExc_ValueError, "Expected integer value");
                    return null;
                }
                values.append(@intCast(value_raw)) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            const serialized = fabll.literals.CountsSerialized{
                .@"type" = "CountSet",
                .data = .{ .values = values.items },
            };
            const out = fabll.literals.Counts.deserialize(serialized, g_ptr, tg_ptr) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to deserialize CountSet");
                return null;
            };
            return wrap_counts_obj(out);
        }
    };
}

fn wrap_counts_type_identifier() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "_type_identifier",
            .doc = "Return Zig type identifier for this literal type",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            return bind.wrap_str(@typeName(fabll.literals.Counts));
        }
    };
}

fn wrap_counts_bind_typegraph() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_typegraph",
            .doc = "Bind Counts type to a Zig TypeGraph",
            .args_def = struct {
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const bound = faebryk.fabll.Node.bind_typegraph(fabll.literals.Counts, tg_ptr);
            return wrap_counts_bound_obj(bound);
        }
    };
}

fn wrap_counts_bound_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a Counts instance from a bound Zig type",
            .args_def = struct {
                g: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(
                "CountsBoundType",
                &counts_bound_type,
                CountsBoundWrapper,
                self,
            ) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            return wrap_counts_obj(wrapper.data.create_instance(g_ptr));
        }
    };
}

fn wrap_counts_bound_get_or_create_type() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_or_create_type",
            .doc = "Get or create the Zig type node for this bound Counts type",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(
                "CountsBoundType",
                &counts_bound_type,
                CountsBoundWrapper,
                self,
            ) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.get_or_create_type());
        }
    };
}

fn wrap_counts_bound(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_counts_bound_create_instance(),
        wrap_counts_bound_get_or_create_type(),
    };
    bind.wrap_namespace_struct(root, CountsBoundType, extra_methods);
    counts_bound_type = type_registry.getRegisteredTypeObject(
        util.shortTypeName(CountsBoundType),
    );

    if (counts_bound_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(CountsBoundWrapper));
    }
}

fn wrap_counts(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_counts_create_instance(),
        wrap_counts_bind_instance(),
        wrap_counts_bind_typegraph(),
        wrap_counts_type_identifier(),
        wrap_counts_get_instance(),
        wrap_counts_setup_from_values(),
        wrap_counts_get_values(),
        wrap_counts_is_singleton(),
        wrap_counts_get_single(),
        wrap_counts_is_empty(),
        wrap_counts_any(),
        wrap_counts_op_setic_equals(),
        wrap_counts_op_setic_is_subset_of(),
        wrap_counts_uncertainty_equals(),
        wrap_counts_op_intersect_intervals(),
        wrap_counts_op_union_intervals(),
        wrap_counts_op_symmetric_difference_intervals(),
        wrap_counts_serialize(),
        wrap_counts_deserialize(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.Counts, extra_methods);
    counts_type = type_registry.getRegisteredTypeObject("Counts");

    if (counts_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(CountsWrapper));
    }

    wrap_counts_bound(root);
}

fn wrap_booleans_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a new Zig fabll Booleans literal instance",
            .args_def = struct {
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const literal = fabll.literals.Booleans.create_instance(g_ptr, tg_ptr);
            return wrap_booleans_obj(literal);
        }
    };
}

fn wrap_booleans_bind_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_instance",
            .doc = "Bind an existing node instance as a Zig fabll Booleans literal",
            .args_def = struct {
                instance: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .instance = bind.ARG{ .Wrapper = graph_py.BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const literal = faebryk.fabll.Node.bind_instance(fabll.literals.Booleans, kwarg_obj.instance.*);
            return wrap_booleans_obj(literal);
        }
    };
}

fn wrap_booleans_get_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_instance",
            .doc = "Get bound node instance for this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.node.instance);
        }
    };
}

fn wrap_booleans_setup_from_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "setup_from_values",
            .doc = "Populate this Booleans literal set from provided values",
            .args_def = struct {
                values: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (py.PySequence_Check(kwarg_obj.values) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "values must be a sequence of booleans");
                return null;
            }

            const size = py.PySequence_Size(kwarg_obj.values);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed(bool).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(kwarg_obj.values, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                const is_true = py.PyObject_IsTrue(item);
                if (is_true < 0) {
                    return null;
                }
                values.append(is_true != 0) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            _ = wrapper.data.setup_from_values(values.items);
            const self_obj = self orelse return null;
            py.Py_INCREF(self_obj);
            return self_obj;
        }
    };
}

fn wrap_booleans_get_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_values",
            .doc = "Return all boolean values in this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const values = wrapper.data.get_values(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to retrieve values");
                return null;
            };
            defer allocator.free(values);

            const out_list = py.PyList_New(@intCast(values.len));
            if (out_list == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            var has_true = false;
            var has_false = false;
            for (values) |value| {
                if (value) has_true = true else has_false = true;
            }

            if (has_true and has_false) {
                const py_true = py.Py_True();
                const py_false = py.Py_False();
                py.Py_INCREF(py_true);
                py.Py_INCREF(py_false);
                if (py.PyList_SetItem(out_list, 0, py_true) < 0) {
                    py.Py_DECREF(py_true);
                    py.Py_DECREF(py_false);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
                if (py.PyList_SetItem(out_list, 1, py_false) < 0) {
                    py.Py_DECREF(py_false);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
                return out_list;
            }

            for (values, 0..) |value, idx| {
                const py_value = if (value) py.Py_True() else py.Py_False();
                py.Py_INCREF(py_value);
                if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
            }

            return out_list;
        }
    };
}

fn wrap_booleans_is_singleton() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_singleton",
            .doc = "Check whether this Booleans literal set has exactly one value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const out = wrapper.data.is_singleton(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute singleton check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_booleans_get_single() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_single",
            .doc = "Get the single value in this Booleans literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const out = wrapper.data.get_single(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected singleton BooleanSet");
                return null;
            };
            const py_value = if (out) py.Py_True() else py.Py_False();
            py.Py_INCREF(py_value);
            return py_value;
        }
    };
}

fn wrap_booleans_is_empty() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_empty",
            .doc = "Check whether this Booleans literal set is empty",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const out = wrapper.data.is_empty(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute emptiness check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_booleans_any() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "any",
            .doc = "Return an arbitrary member of this Booleans literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const out = wrapper.data.any(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Cannot select a value from an empty BooleanSet");
                return null;
            };
            const py_value = if (out) py.Py_True() else py.Py_False();
            py.Py_INCREF(py_value);
            return py_value;
        }
    };
}

const BooleansBinaryReturnKind = enum {
    bool,
    booleans,
};

fn wrap_booleans_binary_method(
    comptime method_ident: []const u8,
    comptime method_name: [:0]const u8,
    comptime doc: [:0]const u8,
    comptime return_kind: BooleansBinaryReturnKind,
    comptime error_message: [:0]const u8,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = method_name,
            .doc = doc,
            .args_def = struct {
                other: *fabll.literals.Booleans,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = BooleansWrapper, .storage = &booleans_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const method = @field(fabll.literals.Booleans, method_ident);

            switch (return_kind) {
                .bool => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return bind.wrap_bool(out);
                },
                .booleans => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_booleans_obj(out);
                },
            }
        }
    };
}

fn wrap_booleans_op_setic_equals() type {
    return wrap_booleans_binary_method(
        "op_setic_equals",
        "op_setic_equals",
        "Setic equality for Booleans literals",
        .bool,
        "Failed to compare BooleanSets",
    );
}

fn wrap_booleans_op_setic_is_subset_of() type {
    return wrap_booleans_binary_method(
        "op_setic_is_subset_of",
        "op_setic_is_subset_of",
        "Setic subset check for Booleans literals",
        .bool,
        "Failed to compare BooleanSets",
    );
}

fn wrap_booleans_uncertainty_equals() type {
    return wrap_booleans_binary_method(
        "uncertainty_equals",
        "uncertainty_equals",
        "Uncertainty equality for Booleans literals",
        .booleans,
        "Failed to compare uncertainty for BooleanSets",
    );
}

fn wrap_booleans_op_intersect_intervals() type {
    return wrap_booleans_binary_method(
        "op_intersect_intervals",
        "op_intersect_intervals",
        "Set intersection for Booleans literals",
        .booleans,
        "Failed to intersect BooleanSets",
    );
}

fn wrap_booleans_op_union_intervals() type {
    return wrap_booleans_binary_method(
        "op_union_intervals",
        "op_union_intervals",
        "Set union for Booleans literals",
        .booleans,
        "Failed to union BooleanSets",
    );
}

fn wrap_booleans_op_symmetric_difference_intervals() type {
    return wrap_booleans_binary_method(
        "op_symmetric_difference_intervals",
        "op_symmetric_difference_intervals",
        "Set symmetric difference for Booleans literals",
        .booleans,
        "Failed to compute symmetric difference for BooleanSets",
    );
}

fn wrap_booleans_serialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "serialize",
            .doc = "Serialize this Booleans literal set to API format",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const serialized = wrapper.data.serialize(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to serialize BooleanSet");
                return null;
            };
            defer allocator.free(serialized.data.values);

            const out = py.PyDict_New();
            if (out == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const type_obj = bind.wrap_str("BooleanSet") orelse {
                py.Py_DECREF(out.?);
                return null;
            };
            if (py.PyDict_SetItemString(out, "type", type_obj) < 0) {
                py.Py_DECREF(type_obj);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(type_obj);

            const data_obj = py.PyDict_New();
            if (data_obj == null) {
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const values_list = py.PyList_New(@intCast(serialized.data.values.len));
            if (values_list == null) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (serialized.data.values, 0..) |value, idx| {
                const py_value = if (value) py.Py_True() else py.Py_False();
                py.Py_INCREF(py_value);
                if (py.PyList_SetItem(values_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value);
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                }
            }

            if (py.PyDict_SetItemString(data_obj, "values", values_list) < 0) {
                py.Py_DECREF(values_list.?);
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(values_list.?);

            if (py.PyDict_SetItemString(out, "data", data_obj) < 0) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(data_obj.?);

            return out;
        }
    };
}

fn wrap_booleans_deserialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "deserialize",
            .doc = "Deserialize a Booleans literal set from API format",
            .args_def = struct {
                data: *py.PyObject,
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;

            const type_obj = py.PyDict_GetItemString(kwarg_obj.data, "type") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing required field 'type'");
                return null;
            };

            const type_value = bind.unwrap_str(type_obj) orelse return null;
            if (!std.mem.eql(u8, type_value, "BooleanSet")) {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected type 'BooleanSet'");
                return null;
            }

            const data_obj = py.PyDict_GetItemString(kwarg_obj.data, "data") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'data' field");
                return null;
            };

            const values_obj = py.PyDict_GetItemString(data_obj, "values") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            };
            if (py.PySequence_Check(values_obj) == 0) {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            }

            const size = py.PySequence_Size(values_obj);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed(bool).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(values_obj, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                if (item == py.Py_True()) {
                    values.append(true) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                        return null;
                    };
                    continue;
                }
                if (item == py.Py_False()) {
                    values.append(false) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                        return null;
                    };
                    continue;
                }
                py.PyErr_SetString(py.PyExc_ValueError, "Expected boolean value");
                return null;
            }

            const serialized = fabll.literals.BooleansSerialized{
                .@"type" = "BooleanSet",
                .data = .{ .values = values.items },
            };
            const out = fabll.literals.Booleans.deserialize(serialized, g_ptr, tg_ptr) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to deserialize BooleanSet");
                return null;
            };
            return wrap_booleans_obj(out);
        }
    };
}

fn wrap_booleans_type_identifier() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "_type_identifier",
            .doc = "Return Zig type identifier for this literal type",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            return bind.wrap_str(@typeName(fabll.literals.Booleans));
        }
    };
}

fn wrap_booleans_bind_typegraph() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_typegraph",
            .doc = "Bind Booleans type to a Zig TypeGraph",
            .args_def = struct {
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const bound = faebryk.fabll.Node.bind_typegraph(fabll.literals.Booleans, tg_ptr);
            return wrap_booleans_bound_obj(bound);
        }
    };
}

fn wrap_booleans_bound_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a Booleans instance from a bound Zig type",
            .args_def = struct {
                g: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(
                "BooleansBoundType",
                &booleans_bound_type,
                BooleansBoundWrapper,
                self,
            ) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            return wrap_booleans_obj(wrapper.data.create_instance(g_ptr));
        }
    };
}

fn wrap_booleans_bound_get_or_create_type() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_or_create_type",
            .doc = "Get or create the Zig type node for this bound Booleans type",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(
                "BooleansBoundType",
                &booleans_bound_type,
                BooleansBoundWrapper,
                self,
            ) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.get_or_create_type());
        }
    };
}

fn wrap_booleans_bound(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_booleans_bound_create_instance(),
        wrap_booleans_bound_get_or_create_type(),
    };
    bind.wrap_namespace_struct(root, BooleansBoundType, extra_methods);
    booleans_bound_type = type_registry.getRegisteredTypeObject(
        util.shortTypeName(BooleansBoundType),
    );

    if (booleans_bound_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(BooleansBoundWrapper));
    }
}

fn wrap_booleans(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_booleans_create_instance(),
        wrap_booleans_bind_instance(),
        wrap_booleans_bind_typegraph(),
        wrap_booleans_type_identifier(),
        wrap_booleans_get_instance(),
        wrap_booleans_setup_from_values(),
        wrap_booleans_get_values(),
        wrap_booleans_is_singleton(),
        wrap_booleans_get_single(),
        wrap_booleans_is_empty(),
        wrap_booleans_any(),
        wrap_booleans_op_setic_equals(),
        wrap_booleans_op_setic_is_subset_of(),
        wrap_booleans_uncertainty_equals(),
        wrap_booleans_op_intersect_intervals(),
        wrap_booleans_op_union_intervals(),
        wrap_booleans_op_symmetric_difference_intervals(),
        wrap_booleans_serialize(),
        wrap_booleans_deserialize(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.Booleans, extra_methods);
    booleans_type = type_registry.getRegisteredTypeObject("Booleans");

    if (booleans_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(BooleansWrapper));
    }

    wrap_booleans_bound(root);
}

fn wrap_literals(root: *py.PyObject) void {
    wrap_string(root);
    wrap_strings_child_field(root);
    wrap_strings(root);
    wrap_counts(root);
    wrap_booleans(root);

    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.literals.Interval, extra_methods);
    bind.wrap_namespace_struct(root, fabll.literals.Numbers, extra_methods);
}

fn wrap_parameters(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.parameters.can_be_operand, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.is_parameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.is_parameter_operatable, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.NumericParameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.StringParameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.BooleanParameter, extra_methods);
}

fn wrap_expressions(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.expressions.is_expression, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Add, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Subtract, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Multiply, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Divide, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Power, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Sqrt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Log, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Sin, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Cos, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Negate, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Round, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Abs, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Floor, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Ceil, extra_methods);
}

fn wrap_units(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.units.IsUnit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.has_unit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.has_display_unit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Meter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Second, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Hour, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ampere, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Kelvin, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.DegreeCelsius, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Volt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.MilliVolt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ohm, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Radian, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Steradian, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Bit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Percent, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ppm, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Dimensionless, extra_methods);
}

var main_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

var main_module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "fabll",
    .m_doc = "Auto-generated Python extension for fabll Zig types",
    .m_size = -1,
    .m_methods = &main_methods,
};

fn add_file_module(
    root: *py.PyObject,
    comptime name: [:0]const u8,
    comptime wrap_fn: fn (*py.PyObject) void,
) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, py.PYTHON_API_VERSION);
    if (module == null) {
        return null;
    }

    wrap_fn(module.?);

    if (py.PyModule_AddObject(root, name, module) < 0) {
        return null;
    }

    return module;
}

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, py.PYTHON_API_VERSION);
    if (module == null) {
        return null;
    }

    _ = add_file_module(module.?, "literals", wrap_literals);
    _ = add_file_module(module.?, "parameters", wrap_parameters);
    _ = add_file_module(module.?, "expressions", wrap_expressions);
    _ = add_file_module(module.?, "units", wrap_units);

    return module;
}
