const std = @import("std");
const pyzig = @import("pyzig");
const pcb = @import("kicad/pcb.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;

// Use wrap_in_python_module to automatically generate bindings for all structs
const PCBBinding = bind.wrap_in_python_module(pcb);

// Method definitions
var methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

// Module definition
var module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "pyzig",
    .m_doc = "Auto-generated Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &methods,
};

// Module initialization function
export fn PyInit_pyzig() ?*py.PyObject {
    // Create the module
    const module = py.PyModule_Create2(&module_def, 1013);
    if (module == null) {
        return null;
    }

    // Use wrap_in_python_module to register all structs from root
    if (PCBBinding.register_all(module) < 0) {
        return null;
    }

    return module;
}
