const std = @import("std");
const pyzig = @import("pyzig");
const sexp = @import("sexp");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;

// Generic module generation function
fn generateModule(
    comptime name: []const u8,
    comptime module_name: [:0]const u8,
    comptime T: type,
    comptime FileType: type,
    comptime has_loads_dumps: bool,
) type {
    return struct {
        // Store reference to the registered File type  
        var registered_file_type: ?*py.PyTypeObject = null;
        
        // Create a custom module binding that uses the correct module name prefix
        const ModuleBinding = struct {
            pub fn register_all(py_module: ?*py.PyObject) c_int {
                // Process each declaration in the module T
                const module_info = @typeInfo(T);
                if (module_info != .@"struct") {
                    return -1;
                }
                
                inline for (module_info.@"struct".decls) |decl| {
                    const decl_value = @field(T, decl.name);
                    const decl_type = @TypeOf(decl_value);
                    const decl_info = @typeInfo(decl_type);

                    // Check if it's a type (struct)
                    if (decl_info == .type) {
                        const inner_type = decl_value;
                        const inner_info = @typeInfo(inner_type);
                        if (inner_info == .@"struct") {
                            // Check if it's a data struct (starts with uppercase, convention for types)
                            const is_type_name = decl.name[0] >= 'A' and decl.name[0] <= 'Z';

                            if (is_type_name) {
                                // Generate bindings for this struct with the correct module name
                                const full_name = module_name ++ "." ++ decl.name;
                                const name_z = full_name ++ "\x00";
                                const binding = bind.wrap_in_python(inner_type, name_z);

                                // Register with Python
                                if (py.PyType_Ready(&binding.type_object) < 0) {
                                    return -1;
                                }

                                binding.type_object.ob_base.ob_base.ob_refcnt += 1;
                                const reg_name = decl.name ++ "\x00";
                                if (py.PyModule_AddObject(py_module, reg_name, @ptrCast(&binding.type_object)) < 0) {
                                    binding.type_object.ob_base.ob_base.ob_refcnt -= 1;
                                    return -1;
                                }
                                
                                // Store reference to the File type if it matches
                                if (has_loads_dumps and inner_type == FileType) {
                                    registered_file_type = &binding.type_object;
                                }
                            }
                        }
                    }
                }
                return 0;
            }
        };

        // Only generate File bindings if loads/dumps are needed
        const FileBinding = if (has_loads_dumps) blk: {
            // Get the type name of FileType (e.g., "PcbFile", "FootprintFile")
            const type_info = @typeInfo(FileType);
            const type_simple_name = if (type_info == .@"struct")
                @typeName(FileType)
            else
                "File";
            
            // Find the last dot to get just the struct name
            const last_dot = blk2: {
                var idx: ?usize = null;
                for (type_simple_name, 0..) |c, i| {
                    if (c == '.') idx = i;
                }
                break :blk2 idx;
            };
            
            const struct_name = if (last_dot) |idx|
                type_simple_name[idx + 1 ..]
            else
                type_simple_name;
            
            // Create full type name like "pyzig.pcb.PcbFile"
            const full_type_name = module_name ++ "." ++ struct_name;
            break :blk bind.wrap_in_python(FileType, full_type_name);
        } else void;

        // Module methods - loads/dumps if applicable
        var methods = if (has_loads_dumps) blk: {
            break :blk [_]py.PyMethodDef{
                .{
                    .ml_name = "loads",
                    .ml_meth = @ptrCast(&py_loads),
                    .ml_flags = py.METH_O,
                    .ml_doc = "Parse file from S-expression string",
                },
                .{
                    .ml_name = "dumps",
                    .ml_meth = @ptrCast(&py_dumps),
                    .ml_flags = py.METH_O,
                    .ml_doc = "Serialize file to S-expression string",
                },
                py.ML_SENTINEL,
            };
        } else [_]py.PyMethodDef{
            py.ML_SENTINEL,
        };

        // Module definition
        var module_def = py.PyModuleDef{
            .m_base = .{},
            .m_name = module_name,
            .m_doc = "Python bindings module",
            .m_size = -1,
            .m_methods = &methods,
        };

        // Python wrapper for loads function
        fn py_loads(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;

            if (!has_loads_dumps) {
                py.PyErr_SetString(py.PyExc_NotImplementedError, "loads not implemented for this module");
                return null;
            }

            // Parse the string argument
            const str_ptr = py.PyUnicode_AsUTF8(args);
            if (str_ptr == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "loads() requires a string argument");
                return null;
            }
            const input_str = std.mem.span(str_ptr.?);

            // Create persistent allocator for the data
            const persistent_allocator = std.heap.c_allocator;

            // Parse the S-expression string
            const file = FileType.loads(persistent_allocator, .{ .string = input_str }) catch |err| {
                // Get the error context for better diagnostics
                const error_context = sexp.structure.getErrorContext();
                
                var error_msg: [1024]u8 = undefined;
                const msg = if (error_context) |ctx| blk: {
                    if (err == error.MissingField) {
                        if (ctx.line) |line| {
                            break :blk std.fmt.bufPrintZ(&error_msg, "Missing required field '{s}' in struct '{s}' (near line {})", .{ 
                                ctx.field_name orelse "unknown",
                                ctx.path,
                                line,
                            }) catch {
                                break :blk std.fmt.bufPrintZ(&error_msg, "Missing required field '{s}' in struct '{s}'", .{
                                    ctx.field_name orelse "unknown",
                                    ctx.path,
                                }) catch "Failed to parse file";
                            };
                        } else {
                            break :blk std.fmt.bufPrintZ(&error_msg, "Missing required field '{s}' in struct '{s}'", .{ 
                                ctx.field_name orelse "unknown",
                                ctx.path,
                            }) catch "Failed to parse file";
                        }
                    } else if (err == error.UnexpectedValue) {
                        if (ctx.sexp_preview) |preview| {
                            break :blk std.fmt.bufPrintZ(&error_msg, "Unexpected value in '{s}': got '{s}'", .{ 
                                ctx.path,
                                preview,
                            }) catch {
                                break :blk std.fmt.bufPrintZ(&error_msg, "Unexpected value in '{s}'", .{ctx.path}) catch "Failed to parse file";
                            };
                        } else {
                            break :blk std.fmt.bufPrintZ(&error_msg, "Unexpected value in '{s}'", .{ctx.path}) catch "Failed to parse file";
                        }
                    } else {
                        break :blk std.fmt.bufPrintZ(&error_msg, "Error in '{s}': {}", .{ 
                            ctx.path,
                            err,
                        }) catch {
                            break :blk std.fmt.bufPrintZ(&error_msg, "Failed to parse: {}", .{err}) catch "Failed to parse file";
                        };
                    }
                } else blk: {
                    break :blk std.fmt.bufPrintZ(&error_msg, "Failed to parse: {}", .{err}) catch "Failed to parse file";
                };
                
                py.PyErr_SetString(py.PyExc_ValueError, msg);
                return null;
            };

            // Use the registered File type that was stored during module registration
            const type_obj = registered_file_type orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "File type not registered in module");
                return null;
            };

            // Type is already initialized when registered with the module

            // Allocate Python object
            const pyobj = py.PyType_GenericAlloc(type_obj, 0);
            if (pyobj == null) return null;

            // Set the data
            const wrapper = @as(*bind.PyObjectWrapper(FileType), @ptrCast(@alignCast(pyobj)));
            wrapper.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };

            // Allocate persistent memory for the data
            wrapper.data = persistent_allocator.create(FileType) catch return null;
            wrapper.data.* = file;

            return pyobj;
        }

        // Python wrapper for dumps function
        fn py_dumps(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;

            if (!has_loads_dumps) {
                py.PyErr_SetString(py.PyExc_NotImplementedError, "dumps not implemented for this module");
                return null;
            }

            // args should be a File object
            if (args == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "dumps() requires a file argument");
                return null;
            }

            // Get the File from the argument
            const wrapper = @as(*bind.PyObjectWrapper(FileType), @ptrCast(@alignCast(args)));

            // Serialize to string
            var arena = std.heap.ArenaAllocator.init(std.heap.c_allocator);
            defer arena.deinit();
            const allocator = arena.allocator();

            var serialized: ?[]const u8 = null;
            wrapper.data.*.dumps(allocator, .{ .string = &serialized }) catch |err| {
                var error_msg: [256]u8 = undefined;
                const msg = std.fmt.bufPrintZ(&error_msg, "Failed to serialize: {}", .{err}) catch {
                    py.PyErr_SetString(py.PyExc_ValueError, "Failed to serialize file");
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

        pub fn createModule() ?*py.PyObject {
            // Create the module
            const module = py.PyModule_Create2(&module_def, 1013);
            if (module == null) {
                py.PyErr_SetString(py.PyExc_ValueError, std.fmt.comptimePrint("Failed to create {s} module", .{name}));
                return null;
            }

            // Register all structs in the module
            if (ModuleBinding.register_all(module) < 0) {
                py.PyErr_SetString(py.PyExc_ValueError, std.fmt.comptimePrint("Failed to register {s} types", .{name}));
                return null;
            }

            return module;
        }
    };
}

// Generate modules using the generic function
const PcbModule = generateModule("pcb", "pyzig.pcb", sexp.kicad.pcb, sexp.kicad.pcb.PcbFile, true);
const FootprintModule = generateModule("footprint", "pyzig.footprint", sexp.kicad.footprint, sexp.kicad.footprint.FootprintFile, true);
const NetlistModule = generateModule("netlist", "pyzig.netlist", sexp.kicad.netlist, sexp.kicad.netlist.NetlistFile, true);
const FpLibTableModule = generateModule("fp_lib_table", "pyzig.fp_lib_table", sexp.kicad.fp_lib_table, sexp.kicad.fp_lib_table.FpLibTableFile, true);
// Add more modules as needed

// Main module methods
var main_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

// Main module definition
var main_module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "pyzig",
    .m_doc = "Auto-generated Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &main_methods,
};

// Module initialization function
export fn PyInit_pyzig() ?*py.PyObject {
    // Create the main module
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    // Create and add the pcb submodule
    const pcb_module = PcbModule.createModule();
    if (pcb_module == null) {
        return null;
    }
    if (py.PyModule_AddObject(module, "pcb", pcb_module) < 0) {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to add pcb submodule");
        return null;
    }

    // Create and add the footprint submodule
    const footprint_module = FootprintModule.createModule();
    if (footprint_module == null) {
        return null;
    }
    if (py.PyModule_AddObject(module, "footprint", footprint_module) < 0) {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to add footprint submodule");
        return null;
    }

    // Create and add the netlist submodule
    const netlist_module = NetlistModule.createModule();
    if (netlist_module == null) {
        return null;
    }
    if (py.PyModule_AddObject(module, "netlist", netlist_module) < 0) {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to add netlist submodule");
        return null;
    }

    // Create and add the fp_lib_table submodule
    const fp_lib_table_module = FpLibTableModule.createModule();
    if (fp_lib_table_module == null) {
        return null;
    }
    if (py.PyModule_AddObject(module, "fp_lib_table", fp_lib_table_module) < 0) {
        py.PyErr_SetString(py.PyExc_ValueError, "Failed to add fp_lib_table submodule");
        return null;
    }

    // Add more modules as needed

    return module;
}
