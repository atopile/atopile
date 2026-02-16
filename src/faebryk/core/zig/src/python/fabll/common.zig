const std = @import("std");
const pyzig = @import("pyzig");
const graph_mod = @import("graph");
const graph_py = @import("../graph/graph_py.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const graph = graph_mod.graph;

pub fn wrap_owned_obj(
    comptime py_name: [:0]const u8,
    comptime T: type,
    comptime Wrapper: type,
    storage: *?*py.PyTypeObject,
    value: T,
) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const out_ptr = allocator.create(T) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    out_ptr.* = value;

    const out_obj = bind.wrap_obj(py_name, storage, Wrapper, out_ptr);
    if (out_obj == null) {
        allocator.destroy(out_ptr);
        return null;
    }
    return out_obj;
}

pub fn unwrap_zig_address_ptr(comptime T: type, obj: *py.PyObject) ?*T {
    const zig_address = py.PyObject_GetAttrString(obj, "__zig_address__");
    if (zig_address == null) {
        py.PyErr_SetString(py.PyExc_TypeError, "Expected Zig-backed object with __zig_address__");
        return null;
    }
    defer py.Py_DECREF(zig_address.?);

    const empty_args = py.PyTuple_New(0) orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate argument tuple");
        return null;
    };
    defer py.Py_DECREF(empty_args);

    const address_obj = py.PyObject_Call(zig_address, empty_args, null);
    if (address_obj == null) {
        return null;
    }
    defer py.Py_DECREF(address_obj.?);

    const address_raw = py.PyLong_AsLongLong(address_obj);
    if (py.PyErr_Occurred() != null) {
        return null;
    }
    if (address_raw <= 0) {
        py.PyErr_SetString(py.PyExc_TypeError, "Invalid Zig object address");
        return null;
    }

    const address_usize: usize = @intCast(address_raw);
    return @ptrFromInt(address_usize);
}

pub fn owned_dealloc(comptime Wrapper: type) *const fn (*py.PyObject) callconv(.c) void {
    return &struct {
        fn impl(self: *py.PyObject) callconv(.c) void {
            const wrapper = @as(*Wrapper, @ptrCast(@alignCast(self)));
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
    }.impl;
}

pub fn ensure_python_type_node(
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
