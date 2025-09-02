const std = @import("std");
const pyzig = @import("pyzig");
const sexp = @import("sexp");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;

// Use wrap_in_python_module to automatically generate bindings for all structs
const PCBBinding = bind.wrap_in_python_module(sexp.kicad.pcb);
const PcbFileBinding = bind.wrap_in_python(sexp.kicad.pcb.PcbFile, "pyzig.PcbFile");

// Python wrapper for loads function - module level
fn py_loads(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    _ = self;

    // Parse the string argument
    const str_ptr = py.PyUnicode_AsUTF8(args);
    if (str_ptr == null) {
        py.PyErr_SetString(py.PyExc_TypeError, "loads() requires a string argument");
        return null;
    }
    const input_str = std.mem.span(str_ptr.?);

    // Create persistent allocator for the PCB data
    const persistent_allocator = std.heap.c_allocator;

    // Parse the S-expression string
    const pcb_file = sexp.kicad.pcb.PcbFile.loads(persistent_allocator, .{ .string = input_str }) catch |err| {
        var error_msg: [256]u8 = undefined;
        const msg = std.fmt.bufPrintZ(&error_msg, "Failed to parse PCB file: {}", .{err}) catch {
            py.PyErr_SetString(py.PyExc_ValueError, "Failed to parse PCB file");
            return null;
        };
        py.PyErr_SetString(py.PyExc_ValueError, msg);
        return null;
    };

    // Create a new PcbFile Python object
    const type_obj = &PcbFileBinding.type_object;

    // Initialize type if needed
    const initialized = struct {
        var done: bool = false;
    };
    if (!initialized.done) {
        _ = py.PyType_Ready(type_obj);
        initialized.done = true;
    }

    // Allocate Python object
    const pyobj = py.PyType_GenericAlloc(type_obj, 0);
    if (pyobj == null) return null;

    // Set the data
    const wrapper = @as(*bind.PyObjectWrapper(sexp.kicad.pcb.PcbFile), @ptrCast(@alignCast(pyobj)));
    wrapper.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };

    // Allocate persistent memory for the PcbFile data
    wrapper.data = persistent_allocator.create(sexp.kicad.pcb.PcbFile) catch return null;
    wrapper.data.* = pcb_file;

    return pyobj;
}

// Python wrapper for dumps function - takes a PcbFile object
fn py_dumps(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    _ = self;

    // args should be a PcbFile object
    if (args == null) {
        py.PyErr_SetString(py.PyExc_TypeError, "dumps() requires a PcbFile argument");
        return null;
    }

    // Get the PcbFile from the argument
    const wrapper = @as(*bind.PyObjectWrapper(sexp.kicad.pcb.PcbFile), @ptrCast(@alignCast(args)));

    // Serialize to string
    var arena = std.heap.ArenaAllocator.init(std.heap.c_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    var serialized: ?[]const u8 = null;
    wrapper.data.*.dumps(allocator, .{ .string = &serialized }) catch |err| {
        var error_msg: [256]u8 = undefined;
        const msg = std.fmt.bufPrintZ(&error_msg, "Failed to serialize PCB file: {}", .{err}) catch {
            py.PyErr_SetString(py.PyExc_ValueError, "Failed to serialize PCB file");
            return null;
        };
        py.PyErr_SetString(py.PyExc_ValueError, msg);
        return null;
    };

    // Convert to Python string
    if (serialized) |s| {
        // Make a null-terminated copy
        const null_terminated = allocator.dupeZ(u8, s) catch return null;
        return py.PyUnicode_FromString(null_terminated);
    }

    py.PyErr_SetString(py.PyExc_ValueError, "Serialization produced no output");
    return null;
}

// Method definitions
var methods = [_]py.PyMethodDef{
    .{
        .ml_name = "loads",
        .ml_meth = @ptrCast(&py_loads),
        .ml_flags = py.METH_O,
        .ml_doc = "Parse a PCB file from S-expression string",
    },
    .{
        .ml_name = "dumps",
        .ml_meth = @ptrCast(&py_dumps),
        .ml_flags = py.METH_O,
        .ml_doc = "Serialize a PcbFile to S-expression string",
    },
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
