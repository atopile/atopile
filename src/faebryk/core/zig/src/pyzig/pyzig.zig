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

fn return_none(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    _ = self;
    _ = args;
    // return None
    return py.Py_None();
}

fn raise_not_implemented(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    _ = self;
    _ = args;
    py.PyErr_SetString(py.PyExc_NotImplementedError, "Not implemented");
    return null;
}

pub fn check_no_positional_args(self: ?*py.PyObject, args: ?*py.PyObject) bool {
    _ = self;
    if (args != null and py.PyTuple_Size(args) != 0) {
        py.PyErr_SetString(py.PyExc_TypeError, "This function does not take positional arguments");
        return false;
    }
    return true;
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

pub fn wrap_in_python_simple(comptime T: type, comptime UseWrapperType: ?type, comptime extra_methods: anytype) type {
    @setEvalBranchQuota(100000);
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("wrap_in_python only supports structs");
    }
    const exported_name = @typeName(T) ++ "\x00";

    const WrapperType = UseWrapperType orelse PyObjectWrapper(T);

    const genStruct = @import("genstruct.zig");

    return struct {
        // store generated struct here, so function pointers to them persist
        pub const generated_repr = genStruct.genStructRepr(WrapperType, T);
        pub const generated_zig_address = genZigAddress(WrapperType, T);
        pub const passed_methods = extra_methods;

        pub const generated_methods = blk: {
            var buf: [extra_methods.len + 2]py.PyMethodDef = undefined;
            for (passed_methods, 0..) |method, i| {
                buf[i] = py.PyMethodDef{
                    .ml_name = method.descr.name,
                    .ml_meth = @ptrCast(&method.impl),
                    .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | (if (method.descr.static) py.METH_STATIC else 0),
                    .ml_doc = method.descr.doc,
                };
            }
            buf[extra_methods.len] = generated_zig_address.method();
            buf[extra_methods.len + 1] = py.ML_SENTINEL;
            break :blk buf;
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

pub fn wrap_namespace_struct(root: *py.PyObject, comptime T: type, extra_methods: anytype) void {
    const type_name = util.shortTypeName(T);

    const binding = wrap_in_python_simple(T, null, extra_methods);
    if (py.PyType_Ready(&binding.type_object) < 0) {
        @panic("Failed to ready type object");
    }

    binding.type_object.ob_base.ob_base.ob_refcnt += 1;
    if (py.PyModule_AddObject(root, type_name, @ptrCast(&binding.type_object)) < 0) {
        binding.type_object.ob_base.ob_base.ob_refcnt -= 1;
        @panic("Failed to add type object to module");
    }
    type_registry.registerTypeObject(type_name, &binding.type_object);
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

pub fn ensureType(comptime name: [:0]const u8, storage: *?*py.PyTypeObject) ?*py.PyTypeObject {
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

pub fn castWrapper(
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

pub fn is_pyobject(comptime T: type) bool {
    return @typeInfo(T) == .@"opaque" or (@typeInfo(T) == .pointer and is_pyobject(@typeInfo(T).pointer.child)) or (@typeInfo(T) == .optional and is_pyobject(@typeInfo(T).optional.child));
}

pub const ARG = struct {
    Wrapper: type,
    storage: *?*py.PyTypeObject,
};

pub const method_descr = struct {
    name: [:0]const u8,
    doc: [:0]const u8,
    args_def: type,
    static: bool = false,
};

pub fn parse_kwargs(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject, comptime T: type) ?T {
    // iterate through fields of T
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("parse_kwargs only supports structs");
    }
    const struct_info = info.@"struct";

    if (!check_no_positional_args(self, args)) return null;

    if (struct_info.fields.len == 0) {
        return .{};
    }

    const kw = kwargs orelse {
        py.PyErr_SetString(py.PyExc_TypeError, "keyword arguments are required");
        return null;
    };

    var data: T = undefined;
    inline for (struct_info.fields) |field| {
        const field_name_z = field.name ++ "\x00";
        const value = py.PyDict_GetItemString(kw, field_name_z);
        if (value) |v| {
            if (comptime is_pyobject(field.type)) {
                @field(data, field.name) = v;
            } else {
                const meta = @field(T, "fields_meta");
                const inner_type = @typeInfo(field.type).pointer.child;
                const meta_name = comptime util.shortTypeName(inner_type);
                const arg: ARG = @field(meta, field.name);
                const wrapper_type = arg.Wrapper;
                const storage = arg.storage;
                const obj = castWrapper(meta_name, storage, wrapper_type, v);
                if (obj == null) {
                    py.PyErr_SetString(py.PyExc_TypeError, "Invalid object");
                    return null;
                }
                @field(data, field.name) = obj.?.data;
            }
        } else {
            if (@typeInfo(field.type) == .optional) {
                @field(data, field.name) = null;
            } else {
                py.PyErr_SetString(py.PyExc_TypeError, "keyword argument is required");
                return null;
            }
        }
    }
    return data;
}

pub fn wrap_none() ?*py.PyObject {
    const out = py.Py_None();
    py.Py_INCREF(out);
    return out;
}

pub fn wrap_bool(value: ?bool) ?*py.PyObject {
    const out = if (value == null) py.Py_None() else if (value.?) py.Py_True() else py.Py_False();
    py.Py_INCREF(out);
    return out;
}

pub fn wrap_str(value: ?[]const u8) ?*py.PyObject {
    if (value == null) {
        const out = py.Py_None();
        py.Py_INCREF(out);
        return out;
    }
    const ptr: [*c]const u8 = if (value.?.len == 0) "" else @ptrCast(value.?.ptr);
    const length: isize = @intCast(value.?.len);
    const out = py.PyUnicode_FromStringAndSize(ptr, length);
    if (out == null) {
        return null;
    }
    py.Py_INCREF(out.?);
    return out.?;
}

pub fn unwrap_str(obj: ?*py.PyObject) ?[]const u8 {
    const ptr = py.PyUnicode_AsUTF8(obj);
    if (ptr == null) {
        py.PyErr_SetString(py.PyExc_TypeError, "Expected a string");
        return null;
    }
    const slice = std.mem.span(ptr.?);
    return slice;
}

pub fn unwrap_str_copy(obj: ?*py.PyObject) ?[]u8 {
    const slice = unwrap_str(obj) orelse return null;
    const copy = std.heap.c_allocator.dupe(u8, slice) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate string");
        return null;
    };
    return copy;
}

pub fn wrap_int(value: anytype) ?*py.PyObject {
    const out = py.PyLong_FromLongLong(@intCast(value));
    if (out == null) {
        return null;
    }
    py.Py_INCREF(out.?);
    return out.?;
}

pub fn unwrap_int(comptime T: type, obj: ?*py.PyObject) ?T {
    const raw = py.PyLong_AsLongLong(obj);
    if (py.PyErr_Occurred() != null) return null;
    const value: T = @intCast(raw);
    return value;
}

pub fn wrap_obj(
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
