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

fn wrap_graphview_create(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    _ = self;
    _ = args;

    //
    return null;
}

fn wrap_graphview(root: *py.PyObject) void {
    const extra_methods = [_]py.PyMethodDef{
        .{
            .ml_name = "create",
            .ml_meth = @ptrCast(&wrap_graphview_create),
            .ml_flags = py.METH_NOARGS | py.METH_STATIC,
            .ml_doc = "Create a new GraphView",
        },
    };

    const graphview_binding = bind.wrap_in_python_simple(graph.graph.GraphView, null, extra_methods);
    if (py.PyType_Ready(&graphview_binding.type_object) < 0) {
        return;
    }

    graphview_binding.type_object.ob_base.ob_base.ob_refcnt += 1;
    if (py.PyModule_AddObject(root, "GraphView", @ptrCast(&graphview_binding.type_object)) < 0) {
        graphview_binding.type_object.ob_base.ob_base.ob_refcnt -= 1;
        return;
    }
    pyzig.type_registry.registerTypeObject("GraphView", &graphview_binding.type_object);
}

fn wrap_graph_module(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    // TODO register types (GraphView, Node, Edge, ...)
    _ = wrap_graphview(module.?);

    if (py.PyModule_AddObject(root, "graph", module) < 0) {
        return null;
    }

    return module;
}

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
