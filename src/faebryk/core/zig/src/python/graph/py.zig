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

fn add_graph_module(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    // TODO register types (GraphView, Node, Edge, ...)
    const graphview_binding = bind.wrap_in_python_simple(graph.graph.GraphView);
    if (py.PyType_Ready(&graphview_binding.type_object) < 0) {
        return null;
    }

    graphview_binding.type_object.ob_base.ob_base.ob_refcnt += 1;
    if (py.PyModule_AddObject(module, "GraphView", @ptrCast(&graphview_binding.type_object)) < 0) {
        graphview_binding.type_object.ob_base.ob_base.ob_refcnt -= 1;
        return null;
    }

    if (py.PyModule_AddObject(root, "graph", module) < 0) {
        return null;
    }
    pyzig.type_registry.registerTypeObject("GraphView", &graphview_binding.type_object);

    return module;
}

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    _ = add_graph_module(module.?);
    // _ = add_composition_module(module.?);
    // _ = add_pathfinder_module(module.?);
    // ...

    return module;
}
