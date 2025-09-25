const std = @import("std");
const pyzig = @import("pyzig");
const faebryk = @import("faebryk");
const graph_mod = @import("graph");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const type_registry = pyzig.type_registry;
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

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

const NodeWrapper = bind.PyObjectWrapper(graph.Node);
const EdgeWrapper = bind.PyObjectWrapper(graph.Edge);
const BoundNodeWrapper = bind.PyObjectWrapper(graph.BoundNodeReference);
const BoundEdgeWrapper = bind.PyObjectWrapper(graph.BoundEdgeReference);

var node_type: ?*py.PyTypeObject = null;
var edge_type: ?*py.PyTypeObject = null;
var bound_node_type: ?*py.PyTypeObject = null;
var bound_edge_type: ?*py.PyTypeObject = null;

fn makeBoundEdgePyObject(value: graph.BoundEdgeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const ptr = allocator.create(graph.BoundEdgeReference) catch {
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

const EdgeCompositionWrapper = bind.PyObjectWrapper(faebryk.composition.EdgeComposition);

var edge_composition_type: ?*py.PyTypeObject = null;

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

// ====================================================================================================================

fn wrap_edge_composition_create() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "keyword arguments are required");
                return null;
            };

            const parent_obj = py.PyDict_GetItemString(kw, "parent");
            if (parent_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "parent is required");
                return null;
            }
            const parent = castWrapper("Node\x00", &node_type, NodeWrapper, parent_obj) orelse return null;

            const child_obj = py.PyDict_GetItemString(kw, "child");
            if (child_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child is required");
                return null;
            }
            const child = castWrapper("Node\x00", &node_type, NodeWrapper, child_obj) orelse return null;

            const identifier_obj = py.PyDict_GetItemString(kw, "child_identifier");
            if (identifier_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child_identifier is required");
                return null;
            }
            const identifier_c = py.PyUnicode_AsUTF8(identifier_obj);
            if (identifier_c == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child_identifier must be a string");
                return null;
            }
            const identifier_slice = std.mem.span(identifier_c.?);

            const allocator = std.heap.c_allocator;
            const identifier_copy = allocator.dupe(u8, identifier_slice) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate child_identifier");
                return null;
            };
            const identifier_const: []const u8 = identifier_copy;

            const edge_ref = faebryk.composition.EdgeComposition.init(
                allocator,
                parent.data,
                child.data,
                identifier_const,
            ) catch {
                allocator.free(identifier_copy);
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create EdgeComposition edge");
                return null;
            };

            const edge_obj = makeWrapperPyObject("Edge\x00", &edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                allocator.free(identifier_copy);
                edge_ref.deinit() catch {};
                return null;
            }

            return edge_obj;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "create",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Create a new EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_is_instance() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;

            var edge_obj: ?*py.PyObject = null;
            if (args != null) {
                const arg_count = py.PyTuple_Size(args);
                if (arg_count < 0) {
                    return null;
                }
                if (arg_count > 1) {
                    py.PyErr_SetString(py.PyExc_TypeError, "is_instance takes exactly one argument");
                    return null;
                }
                if (arg_count == 1) {
                    edge_obj = py.PyTuple_GetItem(args, 0);
                }
            }

            if (edge_obj == null and kwargs != null) {
                edge_obj = py.PyDict_GetItemString(kwargs, "edge");
            }

            if (edge_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "edge is required");
                return null;
            }

            const edge = castWrapper("Edge\x00", &edge_type, EdgeWrapper, edge_obj) orelse return null;
            const is_match = faebryk.composition.EdgeComposition.is_instance(edge.data);
            const py_bool = if (is_match) py.Py_True() else py.Py_False();
            py.Py_INCREF(py_bool);
            return py_bool;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "is_instance",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Check if the object is an instance of EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_visit_children_edges() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "keyword arguments are required");
                return null;
            };

            const bound_node_obj = py.PyDict_GetItemString(kw, "bound_node");
            if (bound_node_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "bound_node is required");
                return null;
            }
            const bound_node = castWrapper("BoundNodeReference\x00", &bound_node_type, BoundNodeWrapper, bound_node_obj) orelse return null;

            const callable_obj = py.PyDict_GetItemString(kw, "f");
            if (callable_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "f is required");
                return null;
            }
            const ctx_obj = py.PyDict_GetItemString(kw, "ctx");

            const VisitCtx = struct {
                py_ctx: ?*py.PyObject,
                callable: *py.PyObject,
                had_error: bool = false,

                pub fn call(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                    const visit_self: *@This() = @ptrCast(@alignCast(ctx_ptr));

                    const edge_obj = makeBoundEdgePyObject(bound_edge) orelse {
                        visit_self.had_error = true;
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    };

                    const args_tuple = py.PyTuple_New(2) orelse {
                        visit_self.had_error = true;
                        py.Py_DECREF(edge_obj);
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    };

                    const ctx_handle = if (visit_self.py_ctx) |ctx| ctx else py.Py_None();
                    py.Py_INCREF(ctx_handle);
                    if (py.PyTuple_SetItem(args_tuple, 0, ctx_handle) < 0) {
                        visit_self.had_error = true;
                        py.Py_DECREF(edge_obj);
                        py.Py_DECREF(args_tuple);
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    }

                    if (py.PyTuple_SetItem(args_tuple, 1, edge_obj) < 0) {
                        visit_self.had_error = true;
                        py.Py_DECREF(args_tuple);
                        py.Py_DECREF(edge_obj);
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    }

                    const result = py.PyObject_Call(visit_self.callable, args_tuple, null);
                    if (result == null) {
                        visit_self.had_error = true;
                        py.Py_DECREF(args_tuple);
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    }

                    py.Py_DECREF(result.?);
                    py.Py_DECREF(args_tuple);
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            };

            var visit_ctx = VisitCtx{
                .py_ctx = if (ctx_obj == null) null else ctx_obj,
                .callable = callable_obj.?,
            };

            const result = faebryk.composition.EdgeComposition.visit_children_edges(
                bound_node.data.*,
                @ptrCast(&visit_ctx),
                VisitCtx.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_children_edges failed");
                    return null;
                },
                else => {},
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "visit_children_edges",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Visit the children edges of the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_get_parent_edge() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;

            if (args == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "bound_node is required");
                return null;
            }

            const arg_count = py.PyTuple_Size(args);
            if (arg_count < 0) {
                return null;
            }
            if (arg_count != 1) {
                py.PyErr_SetString(py.PyExc_TypeError, "get_parent_edge expects exactly one argument");
                return null;
            }

            const bound_node_obj = py.PyTuple_GetItem(args, 0);
            const bound_node = castWrapper("BoundNodeReference\x00", &bound_node_type, BoundNodeWrapper, bound_node_obj) orelse return null;

            const parent_edge = faebryk.composition.EdgeComposition.get_parent_edge(bound_node.data.*);
            if (parent_edge) |edge_ref| {
                return makeBoundEdgePyObject(edge_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "get_parent_edge",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_STATIC,
                .ml_doc = "Get the parent edge of the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_add_child() type {
    // TODO
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            const kw = kwargs orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "keyword arguments are required");
                return null;
            };

            const bound_node_obj = py.PyDict_GetItemString(kw, "bound_node");
            if (bound_node_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "bound_node is required");
                return null;
            }
            const bound_node = castWrapper("BoundNodeReference\x00", &bound_node_type, BoundNodeWrapper, bound_node_obj) orelse return null;

            const child_obj = py.PyDict_GetItemString(kw, "child");
            if (child_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child is required");
                return null;
            }
            const child = castWrapper("Node\x00", &node_type, NodeWrapper, child_obj) orelse return null;

            const identifier_obj = py.PyDict_GetItemString(kw, "child_identifier");
            if (identifier_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child_identifier is required");
                return null;
            }
            const identifier_c = py.PyUnicode_AsUTF8(identifier_obj);
            if (identifier_c == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child_identifier must be a string");
                return null;
            }
            const identifier_slice = std.mem.span(identifier_c.?);

            const allocator = bound_node.data.g.allocator;
            const identifier_copy = allocator.dupe(u8, identifier_slice) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate child_identifier");
                return null;
            };

            const bound_edge = faebryk.composition.EdgeComposition.add_child(
                bound_node.data.*,
                child.data,
                identifier_copy,
            ) catch {
                allocator.free(identifier_copy);
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to add child edge");
                return null;
            };

            return makeBoundEdgePyObject(bound_edge);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "add_child",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Add a child to the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_get_name() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;

            if (args == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "edge is required");
                return null;
            }

            const arg_count = py.PyTuple_Size(args);
            if (arg_count < 0) {
                return null;
            }
            if (arg_count != 1) {
                py.PyErr_SetString(py.PyExc_TypeError, "get_name expects exactly one argument");
                return null;
            }

            const edge_obj = py.PyTuple_GetItem(args, 0);
            const edge = castWrapper("Edge\x00", &edge_type, EdgeWrapper, edge_obj) orelse return null;

            const name = faebryk.composition.EdgeComposition.get_name(edge.data) catch |err| {
                switch (err) {
                    error.InvalidEdgeType => {
                        py.PyErr_SetString(py.PyExc_TypeError, "edge is not an EdgeComposition edge");
                    },
                }
                return null;
            };

            const ptr: [*c]const u8 = if (name.len == 0) "" else @ptrCast(name.ptr);
            const py_str = py.PyUnicode_FromStringAndSize(ptr, @intCast(name.len));
            if (py_str == null) {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create Python string");
                return null;
            }

            return py_str;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "get_name",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_STATIC,
                .ml_doc = "Get the name of the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_get_tid() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;

            if (args != null and py.PyTuple_Size(args) != 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "get_tid takes no arguments");
                return null;
            }

            const tid = faebryk.composition.EdgeComposition.get_tid();
            return py.PyLong_FromLongLong(@intCast(tid));
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "get_tid",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_STATIC,
                .ml_doc = "Get the tid of the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_composition_create(),
        wrap_edge_composition_is_instance(),
        wrap_edge_composition_visit_children_edges(),
        wrap_edge_composition_get_parent_edge(),
        wrap_edge_composition_add_child(),
        wrap_edge_composition_get_name(),
        wrap_edge_composition_get_tid(),
    };
    bind.wrap_namespace_struct(root, faebryk.composition.EdgeComposition, extra_methods);
    edge_composition_type = type_registry.getRegisteredTypeObject("EdgeComposition");
}

fn wrap_interface(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_module(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_node_type(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_pointer(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_trait(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_composition_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_edge_composition(module.?);

    if (py.PyModule_AddObject(root, "composition", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_interface_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_interface(module.?);

    if (py.PyModule_AddObject(root, "interface", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_module_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_module(module.?);

    if (py.PyModule_AddObject(root, "module", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_node_type_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_node_type(module.?);

    if (py.PyModule_AddObject(root, "node_type", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_pointer_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_pointer(module.?);

    if (py.PyModule_AddObject(root, "pointer", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_trait_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_trait(module.?);

    if (py.PyModule_AddObject(root, "trait", module) < 0) {
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
    .m_name = "faebryk",
    .m_doc = "Auto-generated Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &main_methods,
};

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    _ = wrap_composition_file(module.?);
    _ = wrap_interface_file(module.?);
    _ = wrap_module_file(module.?);
    _ = wrap_node_type_file(module.?);
    _ = wrap_pointer_file(module.?);
    _ = wrap_trait_file(module.?);
    return module;
}
