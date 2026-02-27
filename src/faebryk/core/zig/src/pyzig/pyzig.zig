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
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.c) ?*py.PyObject {
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
fn initRaise(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.c) ?*py.PyObject {
    _ = self;
    _ = args;
    py.PyErr_SetString(py.PyExc_TypeError, "Don't call __init__ on this type");
    return null;
}

fn return_none(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.c) ?*py.PyObject {
    _ = self;
    _ = args;
    // return None
    return py.Py_None();
}

fn raise_not_implemented(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.c) ?*py.PyObject {
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

pub fn parse_args_kwargs(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject, comptime T: type) ?T {
    _ = self;

    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("parse_args_kwargs only supports structs");
    }
    const struct_info = info.@"struct";

    const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
    if (positional_count < 0) {
        return null;
    }
    if (positional_count > @as(isize, @intCast(struct_info.fields.len))) {
        py.PyErr_SetString(py.PyExc_TypeError, "too many positional arguments");
        return null;
    }

    var data: T = undefined;
    var assigned: [struct_info.fields.len]bool = [_]bool{false} ** struct_info.fields.len;
    const positional_count_usize: usize = @intCast(positional_count);

    inline for (struct_info.fields, 0..) |field, idx| {
        if (idx < positional_count_usize) {
            const tuple_args = args orelse unreachable;
            const value = py.PyTuple_GetItem(tuple_args, @intCast(idx)) orelse return null;

            if (comptime is_pyobject(field.type)) {
                @field(data, field.name) = value;
            } else {
                const meta = @field(T, "fields_meta");
                const inner_type = @typeInfo(field.type).pointer.child;
                const meta_name = comptime util.shortTypeName(inner_type);
                const arg: ARG = @field(meta, field.name);
                const wrapper_type = arg.Wrapper;
                const storage = arg.storage;
                const obj = castWrapper(meta_name, storage, wrapper_type, value);
                if (obj == null) {
                    py.PyErr_SetString(py.PyExc_TypeError, "Invalid object");
                    return null;
                }
                @field(data, field.name) = obj.?.data;
            }
            assigned[idx] = true;
        }
    }

    if (kwargs) |kw| {
        inline for (struct_info.fields, 0..) |field, idx| {
            const field_name_z = field.name ++ "\x00";
            const value = py.PyDict_GetItemString(kw, field_name_z);
            if (value) |v| {
                if (assigned[idx]) {
                    py.PyErr_SetString(py.PyExc_TypeError, "received duplicate argument");
                    return null;
                }

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
                assigned[idx] = true;
            }
        }
    }

    inline for (struct_info.fields, 0..) |field, idx| {
        if (!assigned[idx]) {
            if (@typeInfo(field.type) == .optional) {
                @field(data, field.name) = null;
            } else {
                py.PyErr_SetString(py.PyExc_TypeError, "required argument is missing");
                return null;
            }
        }
    }

    return data;
}

pub fn tuple_positional_count(args: ?*py.PyObject) ?usize {
    const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
    if (positional_count < 0) {
        return null;
    }
    return @intCast(positional_count);
}

pub fn leading_arg_or_kw(
    args: ?*py.PyObject,
    kwargs: ?*py.PyObject,
    comptime kw_name: []const u8,
    comptime position: usize,
    comptime duplicate_error: [:0]const u8,
    comptime missing_error: [:0]const u8,
) ?*py.PyObject {
    const positional_count = tuple_positional_count(args) orelse return null;

    var value_obj: ?*py.PyObject = null;
    if (positional_count > position) {
        const tuple_args = args orelse unreachable;
        value_obj = py.PyTuple_GetItem(tuple_args, @intCast(position));
        if (value_obj == null) {
            return null;
        }
    }

    if (kwargs) |kw| {
        if (py.PyDict_GetItemString(kw, kw_name ++ "\x00")) |kw_value| {
            if (value_obj != null) {
                py.PyErr_SetString(py.PyExc_TypeError, duplicate_error);
                return null;
            }
            value_obj = kw_value;
        }
    }

    if (value_obj == null) {
        py.PyErr_SetString(py.PyExc_TypeError, missing_error);
        return null;
    }
    return value_obj.?;
}

pub fn sequence_varargs_or_kw(
    args: ?*py.PyObject,
    kwargs: ?*py.PyObject,
    comptime kw_name: []const u8,
    comptime duplicate_error: [:0]const u8,
    comptime missing_error: [:0]const u8,
) ?*py.PyObject {
    if (kwargs) |kw| {
        if (py.PyDict_GetItemString(kw, kw_name ++ "\x00")) |kw_values| {
            const positional_count = tuple_positional_count(args) orelse return null;
            if (positional_count != 0) {
                py.PyErr_SetString(py.PyExc_TypeError, duplicate_error);
                return null;
            }
            return kw_values;
        }
    }

    if (args) |a| {
        return a;
    }

    py.PyErr_SetString(py.PyExc_TypeError, missing_error);
    return null;
}

pub fn append_wrapped_from_args_and_optional_kw(
    comptime type_name: [:0]const u8,
    storage: *?*py.PyTypeObject,
    comptime Wrapper: type,
    args: ?*py.PyObject,
    kwargs: ?*py.PyObject,
    comptime kw_name: []const u8,
    out: anytype,
) bool {
    const positional_count = tuple_positional_count(args) orelse return false;

    var i: usize = 0;
    while (i < positional_count) : (i += 1) {
        const tuple_args = args orelse unreachable;
        const item = py.PyTuple_GetItem(tuple_args, @intCast(i));
        const wrapped = castWrapper(type_name, storage, Wrapper, item) orelse return false;
        out.append(wrapped.data) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return false;
        };
    }

    if (kwargs) |kw| {
        if (py.PyDict_GetItemString(kw, kw_name ++ "\x00")) |kw_value| {
            const wrapped = castWrapper(type_name, storage, Wrapper, kw_value) orelse return false;
            out.append(wrapped.data) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return false;
            };
        }
    }

    return true;
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

pub fn unwrap_bool(obj: ?*py.PyObject) bool {
    return py.PyObject_IsTrue(obj) == 1;
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
    return out.?;
}

pub fn unwrap_int(comptime T: type, obj: ?*py.PyObject) error{IntegerOutOfRange}!?T {
    const raw = py.PyLong_AsLongLong(obj);
    if (py.PyErr_Occurred() != null) return null;
    if (raw < std.math.minInt(T) or raw > std.math.maxInt(T)) {
        return error.IntegerOutOfRange;
    }
    const value: T = @intCast(raw);
    return value;
}

pub fn sequence_size(values_obj: *py.PyObject, comptime type_error: [:0]const u8) ?usize {
    if (py.PySequence_Check(values_obj) == 0) {
        py.PyErr_SetString(py.PyExc_TypeError, type_error);
        return null;
    }
    const size = py.PySequence_Size(values_obj);
    if (size < 0) {
        return null;
    }
    return @intCast(size);
}

pub fn append_strings_from_sequence(
    values_obj: *py.PyObject,
    out: *std.array_list.Managed([]const u8),
    comptime type_error: [:0]const u8,
) bool {
    const size = sequence_size(values_obj, type_error) orelse return false;
    var i: usize = 0;
    while (i < size) : (i += 1) {
        const item = py.PySequence_GetItem(values_obj, @intCast(i));
        if (item == null) {
            return false;
        }
        defer py.Py_DECREF(item.?);

        const value_copy = unwrap_str_copy(item) orelse return false;
        out.append(value_copy) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return false;
        };
    }
    return true;
}

pub fn append_ints_from_sequence(
    comptime T: type,
    values_obj: *py.PyObject,
    out: *std.array_list.Managed(T),
    comptime type_error: [:0]const u8,
    comptime value_error: [:0]const u8,
) bool {
    comptime if (@typeInfo(T) != .int) @compileError("append_ints_from_sequence expects an int type");

    const size = sequence_size(values_obj, type_error) orelse return false;
    var i: usize = 0;
    while (i < size) : (i += 1) {
        const item = py.PySequence_GetItem(values_obj, @intCast(i));
        if (item == null) {
            return false;
        }
        defer py.Py_DECREF(item.?);

        py.PyErr_Clear();
        const raw = py.PyLong_AsLongLong(item);
        if (py.PyErr_Occurred() != null or raw < std.math.minInt(T) or raw > std.math.maxInt(T)) {
            py.PyErr_Clear();
            py.PyErr_SetString(py.PyExc_ValueError, value_error);
            return false;
        }
        out.append(@intCast(raw)) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return false;
        };
    }
    return true;
}

pub fn append_bools_from_sequence(
    values_obj: *py.PyObject,
    out: *std.array_list.Managed(bool),
    comptime type_error: [:0]const u8,
) bool {
    const size = sequence_size(values_obj, type_error) orelse return false;
    var i: usize = 0;
    while (i < size) : (i += 1) {
        const item = py.PySequence_GetItem(values_obj, @intCast(i));
        if (item == null) {
            return false;
        }
        defer py.Py_DECREF(item.?);

        const is_true = py.PyObject_IsTrue(item);
        if (is_true < 0) {
            return false;
        }
        out.append(is_true != 0) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return false;
        };
    }
    return true;
}

pub fn append_strict_bools_from_sequence(
    values_obj: *py.PyObject,
    out: *std.array_list.Managed(bool),
    comptime type_error: [:0]const u8,
    comptime value_error: [:0]const u8,
) bool {
    const size = sequence_size(values_obj, type_error) orelse return false;
    var i: usize = 0;
    while (i < size) : (i += 1) {
        const item = py.PySequence_GetItem(values_obj, @intCast(i));
        if (item == null) {
            return false;
        }
        defer py.Py_DECREF(item.?);

        if (item == py.Py_True()) {
            out.append(true) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return false;
            };
            continue;
        }
        if (item == py.Py_False()) {
            out.append(false) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return false;
            };
            continue;
        }
        py.PyErr_SetString(py.PyExc_ValueError, value_error);
        return false;
    }
    return true;
}

pub fn list_from_string_values(values: []const []const u8) ?*py.PyObject {
    const out_list = py.PyList_New(@intCast(values.len));
    if (out_list == null) {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    }

    for (values, 0..) |value, idx| {
        const py_value = wrap_str(value) orelse {
            py.Py_DECREF(out_list.?);
            return null;
        };
        if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
            py.Py_DECREF(py_value);
            py.Py_DECREF(out_list.?);
            return null;
        }
    }

    return out_list;
}

pub fn list_from_int_values(values: []const i64) ?*py.PyObject {
    const out_list = py.PyList_New(@intCast(values.len));
    if (out_list == null) {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    }

    for (values, 0..) |value, idx| {
        const py_value = py.PyLong_FromLongLong(value);
        if (py_value == null) {
            py.Py_DECREF(out_list.?);
            return null;
        }
        if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
            py.Py_DECREF(py_value.?);
            py.Py_DECREF(out_list.?);
            return null;
        }
    }

    return out_list;
}

pub fn list_from_bool_values(values: []const bool) ?*py.PyObject {
    const out_list = py.PyList_New(@intCast(values.len));
    if (out_list == null) {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    }

    for (values, 0..) |value, idx| {
        const py_value = if (value) py.Py_True() else py.Py_False();
        py.Py_INCREF(py_value);
        if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
            py.Py_DECREF(py_value);
            py.Py_DECREF(out_list.?);
            return null;
        }
    }

    return out_list;
}

pub fn make_typed_values_payload(comptime type_name: []const u8, values_list: *py.PyObject) ?*py.PyObject {
    const out = py.PyDict_New();
    if (out == null) {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    }

    const type_obj = wrap_str(type_name) orelse {
        py.Py_DECREF(out.?);
        return null;
    };
    if (py.PyDict_SetItemString(out, "type", type_obj) < 0) {
        py.Py_DECREF(type_obj);
        py.Py_DECREF(out.?);
        return null;
    }
    py.Py_DECREF(type_obj);

    const data_obj = py.PyDict_New();
    if (data_obj == null) {
        py.Py_DECREF(out.?);
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    }

    if (py.PyDict_SetItemString(data_obj, "values", values_list) < 0) {
        py.Py_DECREF(data_obj.?);
        py.Py_DECREF(out.?);
        return null;
    }

    if (py.PyDict_SetItemString(out, "data", data_obj) < 0) {
        py.Py_DECREF(data_obj.?);
        py.Py_DECREF(out.?);
        return null;
    }
    py.Py_DECREF(data_obj.?);

    return out;
}

pub fn extract_typed_values_sequence(
    data_obj: *py.PyObject,
    comptime expected_type: []const u8,
    comptime expected_type_error: [:0]const u8,
) ?*py.PyObject {
    const type_obj = py.PyDict_GetItemString(data_obj, "type") orelse {
        py.PyErr_SetString(py.PyExc_ValueError, "Missing required field 'type'");
        return null;
    };

    const type_value = unwrap_str(type_obj) orelse return null;
    if (!std.mem.eql(u8, type_value, expected_type)) {
        py.PyErr_SetString(py.PyExc_ValueError, expected_type_error);
        return null;
    }

    const payload_obj = py.PyDict_GetItemString(data_obj, "data") orelse {
        py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'data' field");
        return null;
    };

    const values_obj = py.PyDict_GetItemString(payload_obj, "values") orelse {
        py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
        return null;
    };
    if (py.PySequence_Check(values_obj) == 0) {
        py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
        return null;
    }

    return values_obj;
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
