const std = @import("std");
const pyzig = @import("pyzig");
const sexp = @import("sexp");
const graph = @import("graph");

const sexp_py = @import("sexp/py.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;

// Main module methods
var main_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

// Main module definition
var main_module_def = py.PyModuleDef{
    .m_base = .{},
    // name not used here
    .m_name = "zig",
    .m_doc = "Auto-generated Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &main_methods,
};

var nested_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

// Main module definition
var nested_module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "gen",
    .m_doc = "Auto-generated Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &main_methods,
};

export fn PyInit_pyzig() ?*py.PyObject {
    const root = py.PyModule_Create2(&main_module_def, 1013) orelse return null;
    const nested = py.PyModule_Create2(&nested_module_def, 1013) orelse return null;
    if (py.PyModule_AddObject(root, "gen", nested) < 0) {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to add gen submodule");
        return null;
    }

    const sexp_module = sexp_py.make_python_module() orelse return null;
    if (py.PyModule_AddObject(nested, "sexp", sexp_module) < 0) {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to add sexp submodule");
        return null;
    }

    //const graph_module = graph_py.make_python_module() orelse return null;
    //if (py.PyModule_AddObject(root, "graph", graph_module) < 0) {
    //    py.PyErr_SetString(py.PyExc_ValueError, "Failed to add graph submodule");
    //    return null;
    //}

    return root;
}
