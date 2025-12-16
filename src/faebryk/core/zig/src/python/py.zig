const std = @import("std");
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

fn add_module(root: *py.PyObject, comptime name: [:0]const u8, comptime T: type) ?*py.PyObject {
    const module = T.make_python_module() orelse return null;
    if (py.PyModule_AddObject(root, name, module) < 0) {
        py.PyErr_SetString(py.PyExc_ValueError, std.fmt.comptimePrint("Failed to add submodule {s}", .{name}));
        return null;
    }
    return module;
}

export fn PyInit_pyzig() ?*py.PyObject {
    const root = py.PyModule_Create2(&main_module_def, 1013) orelse return null;
    const nested = py.PyModule_Create2(&nested_module_def, 1013) orelse return null;
    if (py.PyModule_AddObject(root, "gen", nested) < 0) {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to add gen submodule");
        return null;
    }

    const graph_py = @import("graph/graph_py.zig");
    _ = add_module(nested, "graph", graph_py) orelse return null;
    const faebryk_py = @import("faebryk/faebryk_py.zig");
    _ = add_module(nested, "faebryk", faebryk_py) orelse return null;

    return root;
}
