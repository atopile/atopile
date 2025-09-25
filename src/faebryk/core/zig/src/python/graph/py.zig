const std = @import("std");
const graph = @import("graph");
const pyzig = @import("pyzig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;

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

// ====================================================================================================================

fn wrap_graphview_create() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;
            _ = args;

            //
            return null;
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

fn wrap_graphview(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_graphview_create(),
        // TODO add more methods
    };
    bind.wrap_namespace_struct(root, graph.graph.GraphView, extra_methods);
}

fn wrap_graph_module(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    // TODO register types (GraphView, Node, Edge, ...)
    wrap_graphview(module.?);

    if (py.PyModule_AddObject(root, "graph", module) < 0) {
        return null;
    }

    return module;
}

// ====================================================================================================================

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    _ = wrap_graph_module(module.?);
    // _ = add_composition_module(module.?);
    // _ = add_pathfinder_module(module.?);
    // ...

    return module;
}
