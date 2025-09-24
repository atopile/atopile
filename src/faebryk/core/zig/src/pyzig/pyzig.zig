const std = @import("std");
const py = @import("pybindings.zig");
const type_registry = @import("type_registry.zig");
const util = @import("util.zig");

// Auto-generated Python wrapper for a Zig struct
pub fn PyObjectWrapper(comptime T: type) type {
    return struct {
        ob_base: py.PyObject_HEAD,
        data: *T,
    };
}

fn genZigAddress(comptime WrapperType: type, comptime T: type) type {
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("genStructZigAddress only supports structs");
    }

    return struct {
        // Return a stable identifier for the Python-side wrapper
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = args; // No arguments needed
            const wrapper_obj: *WrapperType = @ptrCast(@alignCast(self));
            // Use underlying Zig struct address (stable if buffer not reallocated)
            return py.PyLong_FromUnsignedLongLong(@intFromPtr(wrapper_obj.data));
        }

        pub fn method() py.PyMethodDef {
            return .{
                .ml_name = "__zig_address__",
                .ml_meth = @ptrCast(&impl),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the address of the Zig struct",
            };
        }
    };
}

/// static init function that raises a typeerror
fn initRaise(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    _ = self;
    _ = args;
    py.PyErr_SetString(py.PyExc_TypeError, "Don't call __init__ on this type");
    return null;
}

// Main comptime function to wrap a struct in Python bindings
pub fn wrap_in_python(comptime T: type, comptime override_name: ?[*:0]const u8) type {
    @setEvalBranchQuota(100000);
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("wrap_in_python only supports structs");
    }
    const exported_name = override_name orelse @typeName(T) ++ "\x00";

    const WrapperType = PyObjectWrapper(T);

    const genStruct = @import("genstruct.zig");

    return struct {
        // store generated struct here, so function pointers to them persist
        pub const generated_getset = genStruct.genStructGetSet(WrapperType, T);
        pub const generated_init = genStruct.genStructInit(WrapperType, T);
        pub const generated_repr = genStruct.genStructRepr(WrapperType, T);
        pub const generated_field_names = genStruct.genStructFieldNames(T);
        pub const generated_zig_address = genZigAddress(WrapperType, T);

        pub const generated_methods = [_]py.PyMethodDef{
            generated_field_names.method(),
            generated_zig_address.method(),
            py.ML_SENTINEL,
        };

        // The actual PyTypeObject
        pub var type_object = py.PyTypeObject{
            .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
            .tp_name = exported_name,
            .tp_basicsize = @sizeOf(WrapperType),
            .tp_repr = @ptrCast(&generated_repr.impl),
            .tp_flags = py.Py_TPFLAGS_DEFAULT | py.Py_TPFLAGS_BASETYPE,
            .tp_getset = @as([*]py.PyGetSetDef, @ptrCast(@constCast(&generated_getset.getset))),
            .tp_methods = @as([*]py.PyMethodDef, @ptrCast(@constCast(&generated_methods))),
            .tp_init = @ptrCast(&generated_init.impl),
        };
    };
}

pub fn wrap_in_python_simple(comptime T: type) type {
    @setEvalBranchQuota(100000);
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("wrap_in_python only supports structs");
    }
    const exported_name = @typeName(T) ++ "\x00";

    const WrapperType = PyObjectWrapper(T);

    const genStruct = @import("genstruct.zig");

    return struct {
        // store generated struct here, so function pointers to them persist
        pub const generated_repr = genStruct.genStructRepr(WrapperType, T);
        pub const generated_zig_address = genZigAddress(WrapperType, T);

        pub const generated_methods = [_]py.PyMethodDef{
            generated_zig_address.method(),
            py.ML_SENTINEL,
        };

        // The actual PyTypeObject
        pub var type_object = py.PyTypeObject{
            .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
            .tp_name = exported_name,
            .tp_basicsize = @sizeOf(WrapperType),
            .tp_repr = @ptrCast(&generated_repr.impl),
            .tp_flags = py.Py_TPFLAGS_DEFAULT | py.Py_TPFLAGS_BASETYPE,
            .tp_methods = @as([*]py.PyMethodDef, @ptrCast(@constCast(&generated_methods))),
            .tp_init = @ptrCast(&initRaise),
        };
    };
}

pub fn ensureTypeObject(
    comptime FieldType: type,
    comptime type_name_for_registry: [*:0]const u8,
    comptime panic_msg: []const u8,
) *py.PyTypeObject {
    if (type_registry.getRegisteredTypeObject(type_name_for_registry)) |registered| {
        return registered;
    }

    const Binding = wrap_in_python(FieldType, type_name_for_registry);
    if (py.PyType_Ready(&Binding.type_object) < 0) {
        @panic(panic_msg);
    }
    type_registry.registerTypeObject(type_name_for_registry, &Binding.type_object);
    return &Binding.type_object;
}
