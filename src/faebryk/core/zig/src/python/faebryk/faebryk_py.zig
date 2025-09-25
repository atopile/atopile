const std = @import("std");
const pyzig = @import("pyzig");
const faebryk = @import("faebryk");

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
            // TODO
            _ = self;
            _ = args;
            _ = kwargs;
            return null;
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
            // TODO
            _ = self;
            _ = args;
            _ = kwargs;
            return null;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "is_instance",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_STATIC,
                .ml_doc = "Check if the object is an instance of EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_visit_children_edges() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            // TODO
            _ = self;
            _ = args;
            _ = kwargs;
            return null;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "visit_children_edges",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_STATIC,
                .ml_doc = "Visit the children edges of the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_get_parent_edge() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            // TODO
            _ = self;
            _ = args;
            return null;
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
            // TODO
            _ = self;
            _ = args;
            _ = kwargs;
            return null;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "add_child",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_STATIC,
                .ml_doc = "Add a child to the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_get_name() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            // TODO
            _ = self;
            _ = args;
            return null;
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
            // TODO
            _ = self;
            _ = args;
            return null;
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
