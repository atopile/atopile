const py = @import("pybindings.zig");
const std = @import("std");
const linked_list = @import("linked_list.zig");
const util = @import("util.zig");
const pyzig = @import("pyzig.zig");

inline fn castSelf(comptime T: type, obj: ?*py.PyObject) *T {
    return @ptrCast(@alignCast(obj.?));
}

fn sentinelToSlice(comptime name: [*:0]const u8) []const u8 {
    return std.mem.sliceTo(name, 0);
}

inline fn wrapperStoragePointerType(comptime Wrapper: type) type {
    const info = @typeInfo(Wrapper);
    if (info != .@"struct") {
        @compileError("Wrapper must be a struct: " ++ @typeName(Wrapper));
    }
    inline for (info.@"struct".fields) |field| {
        if (std.mem.eql(u8, field.name, "data") or std.mem.eql(u8, field.name, "top")) {
            return field.type;
        }
    }
    @compileError("Wrapper type missing data/top field: " ++ @typeName(Wrapper));
}

inline fn getWrapperStoragePtr(comptime Wrapper: type, wrapper: *Wrapper) wrapperStoragePointerType(Wrapper) {
    if (@hasField(Wrapper, "data")) {
        return wrapper.data;
    } else if (@hasField(Wrapper, "top")) {
        return wrapper.top;
    } else {
        @compileError("Wrapper type missing data/top field: " ++ @typeName(Wrapper));
    }
}

inline fn wrapperFieldPtr(comptime Wrapper: type, comptime FieldType: type, comptime field_name: []const u8, wrapper: *Wrapper) *FieldType {
    const storage = getWrapperStoragePtr(Wrapper, wrapper);
    return &@field(storage.*, field_name);
}

inline fn wrapperFieldValue(comptime Wrapper: type, comptime FieldType: type, comptime field_name: []const u8, wrapper: *Wrapper) FieldType {
    return wrapperFieldPtr(Wrapper, FieldType, field_name, wrapper).*;
}

inline fn wrapperDataValue(comptime Wrapper: type, wrapper: *Wrapper) wrapperPayloadType(Wrapper) {
    const storage = getWrapperStoragePtr(Wrapper, wrapper);
    return storage.*;
}

fn wrapperPayloadType(comptime Wrapper: type) type {
    const ptr_type = wrapperStoragePointerType(Wrapper);
    const ptr_info = @typeInfo(ptr_type);
    if (ptr_info != .pointer) {
        @compileError("Wrapper storage field must be a pointer type");
    }
    return ptr_info.pointer.child;
}

fn wrapperFieldType(comptime Wrapper: type, comptime field_name: []const u8) type {
    const payload = wrapperPayloadType(Wrapper);
    inline for (std.meta.fields(payload)) |field| {
        if (std.mem.eql(u8, field.name, field_name)) {
            return field.type;
        }
    }
    @compileError("Field not found on wrapper payload: " ++ @typeName(Wrapper) ++ "." ++ field_name);
}

// === Properties =====================================================================================================

fn int_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime FieldType: type) py.PyGetSetDef {
    const field_name_slice = comptime sentinelToSlice(field_name);
    const info = @typeInfo(FieldType).int;
    const is_signed = info.signedness == .signed;

    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const value = wrapperFieldValue(struct_type, FieldType, field_name_slice, obj);
            if (is_signed) {
                const v: c_long = @intCast(value);
                return py.PyLong_FromLong(v);
            }
            const v: c_ulonglong = @intCast(value);
            return py.PyLong_FromUnsignedLongLong(v);
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            if (value == null) return -1;

            const new_val_signed = py.PyLong_AsLongLong(value);
            const field_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);

            if (is_signed) {
                field_ptr.* = @intCast(new_val_signed);
            } else {
                const new_val_unsigned: c_ulonglong = if (new_val_signed < 0) 0 else @intCast(new_val_signed);
                field_ptr.* = @intCast(new_val_unsigned);
            }
            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

fn enum_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime EnumType: type) py.PyGetSetDef {
    const field_name_slice = comptime sentinelToSlice(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const val = wrapperFieldValue(struct_type, EnumType, field_name_slice, obj);
            const enum_str = @tagName(val);
            return py.PyUnicode_FromStringAndSize(enum_str.ptr, @intCast(enum_str.len));
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            if (value == null) return -1;

            const str_val = py.PyUnicode_AsUTF8(value);
            if (str_val == null) return -1;

            const enum_str = std.mem.span(str_val.?);
            const enum_val = std.meta.stringToEnum(EnumType, enum_str) orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Invalid enum value");
                return -1;
            };

            const field_ptr = wrapperFieldPtr(struct_type, EnumType, field_name_slice, obj);
            field_ptr.* = enum_val;
            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

fn str_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime FieldType: type) py.PyGetSetDef {
    const field_name_slice = comptime sentinelToSlice(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const val = wrapperFieldValue(struct_type, FieldType, field_name_slice, obj);
            return py.PyUnicode_FromStringAndSize(val.ptr, @intCast(val.len));
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            if (value == null) return -1;

            const new_val = py.PyUnicode_AsUTF8(value);
            if (new_val == null) return -1;

            const str_slice = std.mem.span(new_val.?);
            const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch return -1;

            const field_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);
            field_ptr.* = str_copy;
            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

fn obj_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime PType: type, type_obj: *py.PyTypeObject) py.PyGetSetDef {
    const field_name_slice = comptime sentinelToSlice(field_name);
    const FieldType = wrapperFieldType(struct_type, field_name_slice);

    // create thin python object wrapper around the zig object
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const zigval_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);

            const pyobj = py.PyType_GenericAlloc(type_obj, 0);
            if (pyobj == null) return null;

            const typed_obj: *PType = @ptrCast(@alignCast(pyobj));
            typed_obj.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };

            if (@hasField(PType, "data")) {
                typed_obj.data = zigval_ptr;
            } else if (@hasField(PType, "top")) {
                typed_obj.top = zigval_ptr;
            } else {
                @compileError("Nested wrapper missing data/top pointer");
            }

            return pyobj;
        }
    }.impl;

    // copy the value from the python object to the zig object
    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            if (value == null) return -1;

            const pyval: *PType = @ptrCast(@alignCast(value));
            const field_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);
            field_ptr.* = wrapperDataValue(PType, pyval);
            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

// Property for float fields
fn float_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime FieldType: type) py.PyGetSetDef {
    const field_name_slice = comptime sentinelToSlice(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const value = wrapperFieldValue(struct_type, FieldType, field_name_slice, obj);
            return py.PyFloat_FromDouble(@floatCast(value));
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            if (value == null) return -1;
            const new_val = py.PyFloat_AsDouble(value);
            const field_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);
            field_ptr.* = @floatCast(new_val);
            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

// Property for bool fields
fn bool_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime FieldType: type) py.PyGetSetDef {
    const field_name_slice = comptime sentinelToSlice(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const val = wrapperFieldValue(struct_type, FieldType, field_name_slice, obj);
            if (val) return py.Py_True() else return py.Py_False();
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            if (value == null) return -1;
            const is_true = py.PyObject_IsTrue(value);
            const field_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);
            field_ptr.* = is_true == 1;
            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

// Property for optional fields
fn optional_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime ChildType: type) py.PyGetSetDef {
    @setEvalBranchQuota(100000);
    const field_name_slice = comptime sentinelToSlice(field_name);

    const child_info = @typeInfo(ChildType);
    const OptionalFieldType = ?ChildType;
    const type_name_for_registry = if (child_info == .@"struct")
        @typeName(ChildType) ++ "\x00"
    else
        "";

    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const field_ptr = wrapperFieldPtr(struct_type, OptionalFieldType, field_name_slice, obj);
            const val = field_ptr.*;
            if (val) |v| {
                switch (child_info) {
                    .int => return py.PyLong_FromLong(@intCast(v)),
                    .float => return py.PyFloat_FromDouble(@floatCast(v)),
                    .bool => if (v) return py.Py_True() else return py.Py_False(),
                    .pointer => |ptr| {
                        if (ptr.size == .slice and ptr.child == u8) {
                            return py.PyUnicode_FromStringAndSize(v.ptr, @intCast(v.len));
                        }
                    },
                    .@"struct" => {
                        const type_obj = pyzig.ensureTypeObject(ChildType, type_name_for_registry, "Failed to initialize optional nested type");
                        const pyobj = py.PyType_GenericAlloc(type_obj, 0);
                        if (pyobj == null) return null;

                        const NestedWrapper = pyzig.PyObjectWrapper(ChildType);
                        const wrapper: *NestedWrapper = @ptrCast(@alignCast(pyobj));
                        wrapper.data = &field_ptr.*.?;
                        return pyobj;
                    },
                    .@"enum" => {
                        const enum_str = @tagName(v);
                        return py.PyUnicode_FromStringAndSize(enum_str.ptr, @intCast(enum_str.len));
                    },
                    else => {},
                }
            }
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            const field_ptr = wrapperFieldPtr(struct_type, OptionalFieldType, field_name_slice, obj);

            if (value == null or value == py.Py_None()) {
                field_ptr.* = null;
                return 0;
            }

            switch (child_info) {
                .int => {
                    const new_val = py.PyLong_AsLong(value);
                    field_ptr.* = @intCast(new_val);
                },
                .float => {
                    const new_val = py.PyFloat_AsDouble(value);
                    field_ptr.* = @floatCast(new_val);
                },
                .bool => {
                    const is_true = py.PyObject_IsTrue(value);
                    field_ptr.* = is_true == 1;
                },
                .pointer => |ptr| {
                    if (ptr.size == .slice and ptr.child == u8) {
                        const new_val = py.PyUnicode_AsUTF8(value);
                        if (new_val == null) return -1;
                        const str_slice = std.mem.span(new_val.?);
                        const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch return -1;
                        field_ptr.* = str_copy;
                    }
                },
                .@"enum" => {
                    const str_val = py.PyUnicode_AsUTF8(value);
                    if (str_val == null) return -1;
                    const enum_str = std.mem.span(str_val.?);
                    field_ptr.* = std.meta.stringToEnum(ChildType, enum_str) orelse {
                        py.PyErr_SetString(py.PyExc_ValueError, "Invalid enum value");
                        return -1;
                    };
                },
                .@"struct" => {
                    const WrapperType = pyzig.PyObjectWrapper(ChildType);
                    const wrapper_obj: *WrapperType = @ptrCast(@alignCast(value));
                    field_ptr.* = wrapper_obj.data.*;
                },
                else => {
                    py.PyErr_SetString(py.PyExc_TypeError, "Unsupported field type for optional property");
                    return -1;
                },
            }
            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

// Property for linked_list fields
fn linked_list_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime ChildType: type) py.PyGetSetDef {
    const field_name_slice = comptime sentinelToSlice(field_name);
    const child_info = @typeInfo(ChildType);
    const FieldType = std.DoublyLinkedList(ChildType);
    const type_name_for_registry = if (child_info == .@"struct")
        @typeName(ChildType) ++ "\x00"
    else
        "";

    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const list_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);
            const element_type_obj = if (child_info == .@"struct")
                pyzig.ensureTypeObject(ChildType, type_name_for_registry, "Failed to initialize linked_list nested type")
            else
                null;
            return linked_list.createMutableList(ChildType, list_ptr, element_type_obj);
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            if (value == null) return -1;

            // Generic: accept any Python sequence and build a DoublyLinkedList
            const LL = std.DoublyLinkedList(ChildType);
            const NodeType = LL.Node;
            var ll = LL{};

            const seq_len = py.PySequence_Size(value);
            if (seq_len < 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "Expected a sequence for linked list field");
                return -1;
            }

            var i: isize = 0;
            while (i < seq_len) : (i += 1) {
                const item = py.PySequence_GetItem(value, i);
                if (item == null) return -1;
                defer py.Py_DECREF(item.?);

                const node = std.heap.c_allocator.create(NodeType) catch return -1;
                // convert
                const child_ti = @typeInfo(ChildType);
                switch (child_ti) {
                    .@"struct" => {
                        const nested = @as(*pyzig.PyObjectWrapper(ChildType), @ptrCast(@alignCast(item)));
                        node.* = NodeType{ .data = nested.data.* };
                    },
                    .@"enum" => {
                        const s = py.PyUnicode_AsUTF8(item);
                        if (s == null) {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        }
                        const enum_str = std.mem.span(s.?);
                        const ev = std.meta.stringToEnum(ChildType, enum_str) orelse {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        };
                        node.* = NodeType{ .data = ev };
                    },
                    .int => {
                        const v = py.PyLong_AsLong(item);
                        if (v == -1 and py.PyErr_Occurred() != null) {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        }
                        node.* = NodeType{ .data = @intCast(v) };
                    },
                    .float => {
                        const v = py.PyFloat_AsDouble(item);
                        if (v == -1.0 and py.PyErr_Occurred() != null) {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        }
                        node.* = NodeType{ .data = @floatCast(v) };
                    },
                    .bool => {
                        const v = py.PyObject_IsTrue(item);
                        if (v == -1) {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        }
                        node.* = NodeType{ .data = (v == 1) };
                    },
                    .pointer => |p| {
                        if (p.size == .slice and p.child == u8) {
                            const s = py.PyUnicode_AsUTF8(item);
                            if (s == null) {
                                std.heap.c_allocator.destroy(node);
                                return -1;
                            }
                            const slice = std.mem.span(s.?);
                            const dup = std.heap.c_allocator.dupe(u8, slice) catch {
                                std.heap.c_allocator.destroy(node);
                                return -1;
                            };
                            node.* = NodeType{ .data = dup };
                        } else {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        }
                    },
                    else => {
                        std.heap.c_allocator.destroy(node);
                        return -1;
                    },
                }

                ll.append(node);
            }

            const list_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);
            list_ptr.* = ll;
            return 0;
        }
    }.impl;

    return .{ .name = field_name, .get = getter, .set = setter };
}

// Property for struct fields
fn struct_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime FieldType: type) py.PyGetSetDef {
    const field_name_slice = comptime sentinelToSlice(field_name);
    const type_name_for_registry = @typeName(FieldType) ++ "\x00";

    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj = castSelf(struct_type, self);
            const nested_data = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);
            const type_obj = pyzig.ensureTypeObject(FieldType, type_name_for_registry, "Failed to initialize nested type");

            const pyobj = py.PyType_GenericAlloc(type_obj, 0);
            if (pyobj == null) return null;

            const NestedWrapper = pyzig.PyObjectWrapper(FieldType);
            const wrapper: *NestedWrapper = @ptrCast(@alignCast(pyobj));
            wrapper.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };
            wrapper.data = nested_data;
            return pyobj;
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj = castSelf(struct_type, self);
            if (value == null) return -1;

            const NestedWrapper = pyzig.PyObjectWrapper(FieldType);
            const nested_wrapper = @as(*NestedWrapper, @ptrCast(@alignCast(value)));
            const field_ptr = wrapperFieldPtr(struct_type, FieldType, field_name_slice, obj);
            field_ptr.* = nested_wrapper.data.*;

            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

// =====================================================================================================================

// Generate property getter/setter based on field type
pub fn genProp(comptime WrapperType: type, comptime FieldType: type, comptime field_name: [*:0]const u8) py.PyGetSetDef {
    const info = @typeInfo(FieldType);

    switch (info) {
        .int => return int_prop(WrapperType, field_name, FieldType),
        .float => return float_prop(WrapperType, field_name, FieldType),
        .bool => return bool_prop(WrapperType, field_name, FieldType),
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child == u8 and ptr.is_const) {
                return str_prop(WrapperType, field_name, FieldType);
            }
            // Temporary: expose unsupported pointer fields as non-accessible properties
            return .{ .name = field_name, .get = null, .set = null };
        },
        .optional => |opt| return optional_prop(WrapperType, field_name, opt.child),
        .@"struct" => if (linked_list.isLinkedList(FieldType)) {
            const NodeType = FieldType.Node;
            const child_t = std.meta.FieldType(NodeType, .data);
            return linked_list_prop(WrapperType, field_name, child_t);
        } else {
            return struct_prop(WrapperType, field_name, FieldType);
        },
        .@"enum" => return enum_prop(WrapperType, field_name, FieldType), // Enums are strings in Python
        else => {
            @compileLog(field_name);
            @compileError("Unsupported field type: " ++ @typeName(FieldType));
        },
    }
}
