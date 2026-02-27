const std = @import("std");
const pyzig = @import("pyzig");
const graph_mod = @import("graph");
const faebryk = @import("faebryk");
const graph_py = @import("../graph/graph_py.zig");
const common = @import("common.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const graph = graph_mod.graph;

pub const ChildFieldBase = struct {
    identifier: ?[]const u8 = null,
    locator: ?[]const u8 = null,
    type_child: bool = false,
    dependant: bool = false,
};

var child_field_counter: usize = 0;

pub fn next_anon_identifier(suffix: []const u8) ?[]const u8 {
    child_field_counter += 1;
    return std.fmt.allocPrint(std.heap.c_allocator, "anon{d}_{s}", .{ child_field_counter, suffix }) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
}

pub fn alloc_identifier_suffix(base_identifier: []const u8, suffix: []const u8) ?[]const u8 {
    return std.fmt.allocPrint(std.heap.c_allocator, "{s}_{s}", .{ base_identifier, suffix }) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
}

pub fn set_locator(base: *ChildFieldBase, locator_obj: *py.PyObject) ?void {
    if (base.locator) |old| {
        std.heap.c_allocator.free(old);
        base.locator = null;
    }

    if (locator_obj == py.Py_None()) {
        return;
    }

    const locator_copy = bind.unwrap_str_copy(locator_obj) orelse return null;
    base.locator = locator_copy;

    if (base.identifier == null) {
        base.identifier = std.heap.c_allocator.dupe(u8, locator_copy) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return null;
        };
    }
}

pub fn get_identifier_obj(base: *const ChildFieldBase) ?*py.PyObject {
    if (base.identifier) |identifier| {
        return bind.wrap_str(identifier);
    }
    py.Py_INCREF(py.Py_None());
    return py.Py_None();
}

pub fn put_on_type(base: *ChildFieldBase) void {
    base.type_child = true;
}

pub fn mark_dependant(base: *ChildFieldBase) void {
    base.dependant = true;
}

pub fn is_dependant(base: *const ChildFieldBase) bool {
    return base.dependant;
}

pub fn is_type_child(base: *const ChildFieldBase) bool {
    return base.type_child;
}

pub fn deinit_base(base: *ChildFieldBase) void {
    if (base.identifier) |identifier| {
        std.heap.c_allocator.free(identifier);
        base.identifier = null;
    }
    if (base.locator) |locator| {
        std.heap.c_allocator.free(locator);
        base.locator = null;
    }
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

pub const ChildTraversal = faebryk.typegraph.TypeGraph.ChildReferenceNode.EdgeTraversal;

pub const TraversalPath = struct {
    traversals: std.array_list.Managed(ChildTraversal),
    held_refs: std.array_list.Managed(*py.PyObject),

    pub fn init() TraversalPath {
        return .{
            .traversals = std.array_list.Managed(ChildTraversal).init(std.heap.c_allocator),
            .held_refs = std.array_list.Managed(*py.PyObject).init(std.heap.c_allocator),
        };
    }

    pub fn deinit(self: *TraversalPath) void {
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

pub fn add_path_identifier(path: *TraversalPath, identifier: []const u8) bool {
    return traversal_path_append_identifier(path, identifier);
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

pub fn parse_ref_path(ref_obj: *py.PyObject) ?TraversalPath {
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

pub const TypegraphContext = struct {
    tg: *faebryk.typegraph.TypeGraph,
    type_node: graph.BoundNodeReference,
};

pub fn context_from_typebound(t_obj: *py.PyObject) ?TypegraphContext {
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
