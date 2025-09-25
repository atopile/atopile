const std = @import("std");
const graph = @import("graph");
const visitor = graph.visitor;
const pyzig = @import("pyzig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const type_registry = pyzig.type_registry;

fn ensureType(comptime name: [:0]const u8, storage: *?*py.PyTypeObject) ?*py.PyTypeObject {
    if (storage.*) |t| {
        return t;
    }

    if (type_registry.getRegisteredTypeObject(name)) |t| {
        storage.* = t;
        return t;
    }

    var err_buf: [64]u8 = undefined;
    const msg = std.fmt.bufPrintZ(&err_buf, "{s} type not registered", .{name}) catch "Type not registered";
    py.PyErr_SetString(py.PyExc_ValueError, msg);
    return null;
}

fn makeWrapperPyObject(
    comptime name: [:0]const u8,
    storage: *?*py.PyTypeObject,
    comptime Wrapper: type,
    data_ptr: anytype,
) ?*py.PyObject {
    const type_obj = ensureType(name, storage) orelse return null;

    const pyobj = py.PyType_GenericAlloc(type_obj, 0);
    if (pyobj == null) {
        return null;
    }

    const wrapper = @as(*Wrapper, @ptrCast(@alignCast(pyobj)));
    wrapper.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };
    wrapper.data = data_ptr;
    return pyobj;
}

fn makeBoundNodePyObject(value: graph.graph.BoundNodeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const ptr = allocator.create(graph.graph.BoundNodeReference) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    ptr.* = value;

    const pyobj = makeWrapperPyObject("BoundNodeReference\x00", &bound_node_type, BoundNodeWrapper, ptr);
    if (pyobj == null) {
        allocator.destroy(ptr);
    }
    return pyobj;
}

fn makeBoundEdgePyObject(value: graph.graph.BoundEdgeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const ptr = allocator.create(graph.graph.BoundEdgeReference) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    ptr.* = value;

    const pyobj = makeWrapperPyObject("BoundEdgeReference\x00", &bound_edge_type, BoundEdgeWrapper, ptr);
    if (pyobj == null) {
        allocator.destroy(ptr);
    }
    return pyobj;
}

const VisitResultVoid = visitor.VisitResult(void);

const VisitCallbackCtx = struct {
    py_ctx: ?*py.PyObject,
    callable: ?*py.PyObject,
    had_error: bool = false,
};

fn visitEdgesCallback(ctx_ptr: *anyopaque, bound_edge: graph.graph.BoundEdgeReference) VisitResultVoid {
    const ctx = @as(*VisitCallbackCtx, @ptrCast(@alignCast(ctx_ptr)));

    const edge_obj = makeBoundEdgePyObject(bound_edge) orelse {
        ctx.had_error = true;
        return VisitResultVoid{ .ERROR = error.Callback };
    };

    const args = py.PyTuple_New(2) orelse {
        ctx.had_error = true;
        return VisitResultVoid{ .ERROR = error.Callback };
    };

    const ctx_handle: *py.PyObject = if (ctx.py_ctx) |c| c else py.Py_None();
    py.Py_INCREF(ctx_handle);
    if (py.PyTuple_SetItem(args, 0, ctx_handle) < 0) {
        ctx.had_error = true;
        py.Py_DECREF(args);
        return VisitResultVoid{ .ERROR = error.Callback };
    }

    if (py.PyTuple_SetItem(args, 1, edge_obj) < 0) {
        ctx.had_error = true;
        py.Py_DECREF(args);
        return VisitResultVoid{ .ERROR = error.Callback };
    }

    const result = py.PyObject_Call(ctx.callable, args, null);
    if (result == null) {
        ctx.had_error = true;
        py.Py_DECREF(args);
        return VisitResultVoid{ .ERROR = error.Callback };
    }

    py.Py_DECREF(result.?);
    py.Py_DECREF(args);
    return VisitResultVoid{ .CONTINUE = {} };
}

const GraphViewWrapper = bind.PyObjectWrapper(graph.graph.GraphView);
const NodeWrapper = bind.PyObjectWrapper(graph.graph.Node);
const EdgeWrapper = bind.PyObjectWrapper(graph.graph.Edge);
const BoundNodeWrapper = bind.PyObjectWrapper(graph.graph.BoundNodeReference);
const BoundEdgeWrapper = bind.PyObjectWrapper(graph.graph.BoundEdgeReference);

var graph_view_type: ?*py.PyTypeObject = null;
var node_type: ?*py.PyTypeObject = null;
var edge_type: ?*py.PyTypeObject = null;
var bound_node_type: ?*py.PyTypeObject = null;
var bound_edge_type: ?*py.PyTypeObject = null;

const Literal = graph.graph.Literal;

fn freeLiteral(literal: Literal) void {
    switch (literal) {
        .String => |value| {
            std.heap.c_allocator.free(@constCast(value));
        },
        else => {},
    }
}

fn pyObjectToLiteral(obj: ?*py.PyObject) !Literal {
    if (obj == null) return error.UnsupportedType;

    if (obj == py.Py_True()) return Literal{ .Bool = true };
    if (obj == py.Py_False()) return Literal{ .Bool = false };

    py.PyErr_Clear();
    const int_val = py.PyLong_AsLongLong(obj);
    if (py.PyErr_Occurred() == null) {
        const coerced: i64 = @intCast(int_val);
        return Literal{ .Int = coerced };
    }

    py.PyErr_Clear();
    const float_val = py.PyFloat_AsDouble(obj);
    if (py.PyErr_Occurred() == null) {
        return Literal{ .Float = float_val };
    }

    const str_ptr = py.PyUnicode_AsUTF8(obj);
    if (str_ptr != null) {
        const slice = std.mem.span(str_ptr.?);
        const copy = std.heap.c_allocator.dupe(u8, slice) catch return error.OutOfMemory;
        py.PyErr_Clear();
        return Literal{ .String = copy };
    }

    py.PyErr_Clear();
    return error.UnsupportedType;
}

fn literalToPyObject(literal: Literal) ?*py.PyObject {
    return switch (literal) {
        .Int => |value| blk: {
            const casted: c_longlong = @intCast(value);
            break :blk py.PyLong_FromLongLong(casted);
        },
        .Uint => |value| py.PyLong_FromUnsignedLongLong(value),
        .Float => |value| py.PyFloat_FromDouble(value),
        .String => |value| blk: {
            const ptr: [*c]const u8 = if (value.len == 0)
                ""
            else
                @ptrCast(value.ptr);
            const length: isize = @intCast(value.len);
            break :blk py.PyUnicode_FromStringAndSize(ptr, length);
        },
        .Bool => |value| blk: {
            const py_bool = if (value) py.Py_True() else py.Py_False();
            py.Py_INCREF(py_bool);
            break :blk py_bool;
        },
    };
}

fn castWrapper(
    comptime name: [:0]const u8,
    storage: *?*py.PyTypeObject,
    comptime Wrapper: type,
    obj: ?*py.PyObject,
) ?*Wrapper {
    const type_obj = ensureType(name, storage) orelse return null;
    if (obj == null) {
        var err_buf: [64]u8 = undefined;
        const msg = std.fmt.bufPrintZ(&err_buf, "Expected {s}", .{name}) catch "Invalid object";
        py.PyErr_SetString(py.PyExc_TypeError, msg);
        return null;
    }

    const obj_type = py.Py_TYPE(obj);
    if (obj_type == null or obj_type.? != type_obj) {
        var err_buf: [64]u8 = undefined;
        const msg = std.fmt.bufPrintZ(&err_buf, "Expected {s}", .{name}) catch "Invalid object";
        py.PyErr_SetString(py.PyExc_TypeError, msg);
        return null;
    }

    return @as(*Wrapper, @ptrCast(@alignCast(obj.?)));
}

fn shouldSkip(key: []const u8, skip: []const []const u8) bool {
    for (skip) |k| {
        if (std.mem.eql(u8, key, k)) return true;
    }
    return false;
}

fn applyAttributes(dynamic: *graph.graph.DynamicAttributes, kwargs: ?*py.PyObject, skip: []const []const u8) !void {
    if (kwargs == null or kwargs == py.Py_None()) return;

    var pos: isize = 0;
    var key_obj: ?*py.PyObject = null;
    var value_obj: ?*py.PyObject = null;

    while (py.PyDict_Next(kwargs, &pos, &key_obj, &value_obj) != 0) {
        const key_c = py.PyUnicode_AsUTF8(key_obj);
        if (key_c == null) {
            py.PyErr_SetString(py.PyExc_TypeError, "Attribute names must be str");
            return error.InvalidKey;
        }
        const key_slice = std.mem.span(key_c.?);
        if (shouldSkip(key_slice, skip)) {
            continue;
        }

        const key_copy = std.heap.c_allocator.dupe(u8, key_slice) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return error.OutOfMemory;
        };

        const literal = pyObjectToLiteral(value_obj) catch |err| {
            std.heap.c_allocator.free(key_copy);
            switch (err) {
                error.OutOfMemory => py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory"),
                error.UnsupportedType => py.PyErr_SetString(py.PyExc_TypeError, "Unsupported attribute literal"),
            }
            return err;
        };

        dynamic.values.put(key_copy, literal) catch {
            std.heap.c_allocator.free(key_copy);
            freeLiteral(literal);
            py.PyErr_SetString(py.PyExc_MemoryError, "Failed to store attribute");
            return error.OutOfMemory;
        };
    }
}

// ====================================================================================================================

fn wrap_node_create() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            const allocator = std.heap.c_allocator;
            const node = graph.graph.Node.init(allocator) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate Node");
                return null;
            };

            var success = false;
            defer if (!success) {
                _ = node.deinit() catch {};
            };

            applyAttributes(&node.dynamic, kwargs, &.{}) catch {
                return null;
            };

            success = true;
            return makeWrapperPyObject("Node\x00", &node_type, NodeWrapper, node);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "create",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Create a new Node",
            };
        }
    };
}

fn wrap_node_get_attr() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Node\x00", &node_type, NodeWrapper, self) orelse return null;
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "key is required");
                return null;
            };

            const key_obj = py.PyDict_GetItemString(kw, "key");
            if (key_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "key is required");
                return null;
            }
            const key_c = py.PyUnicode_AsUTF8(key_obj);
            if (key_c == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "Attribute key must be str");
                return null;
            }

            const key_slice = std.mem.span(key_c.?);
            if (wrapper.data.dynamic.values.get(key_slice)) |value| {
                return literalToPyObject(value) orelse null;
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "get_attr",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Return attribute value for the given key",
            };
        }
    };
}

fn wrap_node_is_same() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Node\x00", &node_type, NodeWrapper, self) orelse return null;
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "other is required");
                return null;
            };

            const other_obj = py.PyDict_GetItemString(kw, "other");
            if (other_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "other is required");
                return null;
            }
            const other = castWrapper("Node\x00", &node_type, NodeWrapper, other_obj) orelse return null;
            const same = graph.graph.Node.is_same(wrapper.data, other.data);

            const result = if (same) py.Py_True() else py.Py_False();
            py.Py_INCREF(result);
            return result;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "is_same",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Compare two Node instances",
            };
        }
    };
}

fn wrap_node(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_node_create(),
        wrap_node_get_attr(),
        wrap_node_is_same(),
    };
    bind.wrap_namespace_struct(root, graph.graph.Node, extra_methods);
    node_type = type_registry.getRegisteredTypeObject("Node");
}

fn wrap_edge_create() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "keyword arguments are required");
                return null;
            };

            const source_obj = py.PyDict_GetItemString(kw, "source");
            if (source_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "source is required");
                return null;
            }
            const source = castWrapper("Node\x00", &node_type, NodeWrapper, source_obj) orelse return null;

            const target_obj = py.PyDict_GetItemString(kw, "target");
            if (target_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "target is required");
                return null;
            }
            const target = castWrapper("Node\x00", &node_type, NodeWrapper, target_obj) orelse return null;

            const edge_type_obj = py.PyDict_GetItemString(kw, "edge_type");
            if (edge_type_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "edge_type is required");
                return null;
            }
            const edge_type_raw = py.PyLong_AsLongLong(edge_type_obj);
            if (py.PyErr_Occurred() != null) return null;
            const edge_type_value: graph.graph.Edge.Type = @intCast(edge_type_raw);

            const directional_obj = py.PyDict_GetItemString(kw, "directional");
            var directional_value: ?bool = null;
            if (directional_obj != null and directional_obj != py.Py_None()) {
                const truth = py.PyObject_IsTrue(directional_obj);
                if (truth == -1) return null;
                directional_value = truth == 1;
            }

            const name_obj = py.PyDict_GetItemString(kw, "name");
            var name_copy: ?[]const u8 = null;
            if (name_obj != null and name_obj != py.Py_None()) {
                const name_c = py.PyUnicode_AsUTF8(name_obj);
                if (name_c == null) {
                    py.PyErr_SetString(py.PyExc_TypeError, "name must be a string");
                    return null;
                }
                const name_slice = std.mem.span(name_c.?);
                name_copy = std.heap.c_allocator.dupe(u8, name_slice) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            const allocator = std.heap.c_allocator;
            const edge_ptr = graph.graph.Edge.init(allocator, source.data, target.data, edge_type_value) catch {
                if (name_copy) |n| std.heap.c_allocator.free(@constCast(n));
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate Edge");
                return null;
            };

            var success = false;
            defer if (!success) {
                if (name_copy) |n| std.heap.c_allocator.free(@constCast(n));
                _ = edge_ptr.deinit() catch {};
            };

            edge_ptr.directional = directional_value;
            edge_ptr.name = name_copy;

            const skip = &.{ "source", "target", "edge_type", "directional", "name" };
            applyAttributes(&edge_ptr.dynamic, kw, skip) catch {
                return null;
            };

            success = true;
            return makeWrapperPyObject("Edge\x00", &edge_type, EdgeWrapper, edge_ptr);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "create",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Create a new Edge",
            };
        }
    };
}

fn wrap_edge_get_attr() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Edge\x00", &edge_type, EdgeWrapper, self) orelse return null;
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "key is required");
                return null;
            };

            const key_obj = py.PyDict_GetItemString(kw, "key");
            if (key_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "key is required");
                return null;
            }
            const key_c = py.PyUnicode_AsUTF8(key_obj);
            if (key_c == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "Attribute key must be str");
                return null;
            }

            const key_slice = std.mem.span(key_c.?);
            if (wrapper.data.dynamic.values.get(key_slice)) |value| {
                return literalToPyObject(value) orelse null;
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "get_attr",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Return attribute value for the given key",
            };
        }
    };
}

fn wrap_edge_is_same() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Edge\x00", &edge_type, EdgeWrapper, self) orelse return null;
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "other is required");
                return null;
            };

            const other_obj = py.PyDict_GetItemString(kw, "other");
            if (other_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "other is required");
                return null;
            }
            const other = castWrapper("Edge\x00", &edge_type, EdgeWrapper, other_obj) orelse return null;

            const same = graph.graph.Edge.is_same(wrapper.data, other.data);
            const result = if (same) py.Py_True() else py.Py_False();
            py.Py_INCREF(result);
            return result;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "is_same",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Compare two Edge instances",
            };
        }
    };
}

fn wrap_edge_get_source() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Edge\x00", &edge_type, EdgeWrapper, self) orelse return null;
            return makeWrapperPyObject("Node\x00", &node_type, NodeWrapper, wrapper.data.source);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "source",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the source Node",
            };
        }
    };
}

fn wrap_edge_get_target() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Edge\x00", &edge_type, EdgeWrapper, self) orelse return null;
            return makeWrapperPyObject("Node\x00", &node_type, NodeWrapper, wrapper.data.target);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "target",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the target Node",
            };
        }
    };
}

fn wrap_edge_get_edge_type() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Edge\x00", &edge_type, EdgeWrapper, self) orelse return null;
            const val: c_longlong = @intCast(wrapper.data.edge_type);
            return py.PyLong_FromLongLong(val);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "edge_type",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the edge type identifier",
            };
        }
    };
}

fn wrap_edge_get_directional() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Edge\x00", &edge_type, EdgeWrapper, self) orelse return null;
            if (wrapper.data.directional) |value| {
                const py_bool = if (value) py.Py_True() else py.Py_False();
                py.Py_INCREF(py_bool);
                return py_bool;
            }
            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "directional",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return whether the edge is directional",
            };
        }
    };
}

fn wrap_edge_get_name() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("Edge\x00", &edge_type, EdgeWrapper, self) orelse return null;
            if (wrapper.data.name) |value| {
                const ptr: [*c]const u8 = if (value.len == 0) "" else @ptrCast(value.ptr);
                const length: isize = @intCast(value.len);
                return py.PyUnicode_FromStringAndSize(ptr, length);
            }
            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "name",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the edge name if present",
            };
        }
    };
}

fn wrap_edge(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_create(),
        wrap_edge_get_attr(),
        wrap_edge_is_same(),
        wrap_edge_get_source(),
        wrap_edge_get_target(),
        wrap_edge_get_edge_type(),
        wrap_edge_get_directional(),
        wrap_edge_get_name(),
    };
    bind.wrap_namespace_struct(root, graph.graph.Edge, extra_methods);
    edge_type = type_registry.getRegisteredTypeObject("Edge");
}

fn wrap_bound_node_get_node() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("BoundNodeReference\x00", &bound_node_type, BoundNodeWrapper, self) orelse return null;
            return makeWrapperPyObject("Node\x00", &node_type, NodeWrapper, wrapper.data.node);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "node",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the underlying Node",
            };
        }
    };
}

fn wrap_bound_node_get_graph() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("BoundNodeReference\x00", &bound_node_type, BoundNodeWrapper, self) orelse return null;
            return makeWrapperPyObject("GraphView\x00", &graph_view_type, GraphViewWrapper, wrapper.data.g);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "g",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the owning GraphView",
            };
        }
    };
}

fn wrap_bound_node_visit_edges_of_type() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("BoundNodeReference\x00", &bound_node_type, BoundNodeWrapper, self) orelse return null;

            if (!bind.check_no_positional_args(self, args)) return null;
            if (kwargs == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "visit_edges_of_type requires keyword arguments");
                return null;
            }

            const edge_type_obj = py.PyDict_GetItemString(kwargs, "edge_type");
            if (edge_type_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "edge_type is required");
                return null;
            }
            const edge_type_raw = py.PyLong_AsLongLong(edge_type_obj);
            if (py.PyErr_Occurred() != null) return null;
            const edge_type_value: graph.graph.Edge.Type = @intCast(edge_type_raw);

            const ctx_obj = blk: {
                if (py.PyDict_GetItemString(kwargs, "ctx")) |c| break :blk c;
                py.PyErr_SetString(py.PyExc_TypeError, "ctx is required");
                return null;
            };

            const callable_obj = blk: {
                if (py.PyDict_GetItemString(kwargs, "f")) |c| break :blk c;
                py.PyErr_SetString(py.PyExc_TypeError, "f is required");
                return null;
            };

            py.Py_INCREF(ctx_obj);
            py.Py_INCREF(callable_obj);

            var visit_ctx = VisitCallbackCtx{ .py_ctx = ctx_obj, .callable = callable_obj };
            const result = wrapper.data.visit_edges_of_type(edge_type_value, void, @ptrCast(&visit_ctx), visitEdgesCallback);

            py.Py_DECREF(ctx_obj);
            py.Py_DECREF(callable_obj);

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_edges_of_type failed");
                    return null;
                },
                else => {},
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "visit_edges_of_type",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Visit edges of a specific type",
            };
        }
    };
}

fn wrap_bound_node(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_bound_node_get_node(),
        wrap_bound_node_get_graph(),
        wrap_bound_node_visit_edges_of_type(),
    };
    bind.wrap_namespace_struct(root, graph.graph.BoundNodeReference, extra_methods);
    bound_node_type = type_registry.getRegisteredTypeObject("BoundNodeReference");

    if (bound_node_type) |typ| {
        typ.ob_base.ob_base.ob_refcnt += 1;
        if (py.PyModule_AddObject(root, "BoundNode\x00", @ptrCast(typ)) < 0) {
            typ.ob_base.ob_base.ob_refcnt -= 1;
        }
    }
}

fn wrap_bound_edge_get_edge() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("BoundEdgeReference\x00", &bound_edge_type, BoundEdgeWrapper, self) orelse return null;
            return makeWrapperPyObject("Edge\x00", &edge_type, EdgeWrapper, wrapper.data.edge);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "edge",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the underlying Edge",
            };
        }
    };
}

fn wrap_bound_edge_get_graph() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("BoundEdgeReference\x00", &bound_edge_type, BoundEdgeWrapper, self) orelse return null;
            return makeWrapperPyObject("GraphView\x00", &graph_view_type, GraphViewWrapper, wrapper.data.g);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "g",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the owning GraphView",
            };
        }
    };
}

fn wrap_bound_edge(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_bound_edge_get_edge(),
        wrap_bound_edge_get_graph(),
    };
    bind.wrap_namespace_struct(root, graph.graph.BoundEdgeReference, extra_methods);
    bound_edge_type = type_registry.getRegisteredTypeObject("BoundEdgeReference");

    if (bound_edge_type) |typ| {
        typ.ob_base.ob_base.ob_refcnt += 1;
        if (py.PyModule_AddObject(root, "BoundEdge\x00", @ptrCast(typ)) < 0) {
            typ.ob_base.ob_base.ob_refcnt -= 1;
        }
    }
}

fn wrap_graphview_create() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;
            _ = args;
            const allocator = std.heap.c_allocator;

            const graph_ptr = allocator.create(graph.graph.GraphView) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate GraphView");
                return null;
            };

            graph_ptr.* = graph.graph.GraphView.init(allocator);

            const pyobj = makeWrapperPyObject("GraphView\x00", &graph_view_type, GraphViewWrapper, graph_ptr);
            if (pyobj == null) {
                graph_ptr.deinit();
                allocator.destroy(graph_ptr);
            }

            return pyobj;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "create",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_NOARGS | py.METH_STATIC,
                .ml_doc = "Create a new GraphView",
            };
        }
    };
}

fn wrap_graphview_insert_node() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("GraphView\x00", &graph_view_type, GraphViewWrapper, self) orelse return null;
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "node is required");
                return null;
            };

            const node_obj = py.PyDict_GetItemString(kw, "node");
            if (node_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "node is required");
                return null;
            }
            const node = castWrapper("Node\x00", &node_type, NodeWrapper, node_obj) orelse return null;

            const bound = wrapper.data.insert_node(node.data) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to insert node");
                return null;
            };

            return makeBoundNodePyObject(bound);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "insert_node",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Insert a Node into the graph",
            };
        }
    };
}

fn wrap_graphview_insert_edge() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("GraphView\x00", &graph_view_type, GraphViewWrapper, self) orelse return null;
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "edge is required");
                return null;
            };

            const edge_obj = py.PyDict_GetItemString(kw, "edge");
            if (edge_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "edge is required");
                return null;
            }
            const edge = castWrapper("Edge\x00", &edge_type, EdgeWrapper, edge_obj) orelse return null;

            const bound = wrapper.data.insert_edge(edge.data) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to insert edge");
                return null;
            };

            return makeBoundEdgePyObject(bound);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "insert_edge",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Insert an Edge into the graph",
            };
        }
    };
}

fn wrap_graphview_bind() type {
    const FnType = fn (?*py.PyObject, ?*py.PyObject, ?*py.PyObject) callconv(.C) ?*py.PyObject;
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = castWrapper("GraphView\x00", &graph_view_type, GraphViewWrapper, self) orelse return null;
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "node is required");
                return null;
            };

            const node_obj = py.PyDict_GetItemString(kw, "node");
            if (node_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "node is required");
                return null;
            }
            const node = castWrapper("Node\x00", &node_type, NodeWrapper, node_obj) orelse return null;

            const bound = wrapper.data.bind(node.data);
            return makeBoundNodePyObject(bound);
        }

        pub fn method(impl_fn: *const FnType) py.PyMethodDef {
            return .{
                .ml_name = "bind",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Bind an existing Node to the graph",
            };
        }
    };
}

fn wrap_graphview(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_graphview_create(),
        wrap_graphview_insert_node(),
        wrap_graphview_insert_edge(),
        wrap_graphview_bind(),
    };
    bind.wrap_namespace_struct(root, graph.graph.GraphView, extra_methods);
    graph_view_type = type_registry.getRegisteredTypeObject("GraphView");
}

fn wrap_graph_module(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_node(module.?);
    wrap_edge(module.?);
    wrap_bound_node(module.?);
    wrap_bound_edge(module.?);
    wrap_graphview(module.?);

    if (py.PyModule_AddObject(root, "graph", module) < 0) {
        return null;
    }

    return module;
}

// ====================================================================================================================

// Main module methods
var main_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

// Main module definition
var main_module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "graph",
    .m_doc = "Auto-generated Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &main_methods,
};

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    _ = wrap_graph_module(module.?);
    return module;
}
