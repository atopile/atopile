const py = @import("pybindings.zig");
const std = @import("std");
const getset = @import("getset.zig");
const pyzig = @import("pyzig.zig");
const util = @import("util.zig");
const linked_list = @import("linked_list.zig");

pub fn genStructInit(comptime WrapperType: type, comptime T: type) type {
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("genStructInit only supports structs");
    }
    const struct_info = info.@"struct";
    return struct {
        // Generate the __init__ function using a truly generic approach
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) c_int {
            const wrapper_obj: *WrapperType = @ptrCast(@alignCast(self));
            wrapper_obj.data = std.heap.c_allocator.create(T) catch return -1;

            // Use a generic approach inspired by ziggy-pydust
            // Parse arguments directly from the Python tuple and dict

            // Get the number of positional arguments
            const num_pos = if (args != null) py.PyTuple_Size(args) else 0;
            const has_kwargs = kwargs != null and kwargs != py.Py_None();

            // For keyword-only arguments (like dataclasses), all args must be keywords
            if (num_pos > 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "__init__() takes 0 positional arguments");
                std.heap.c_allocator.destroy(wrapper_obj.data);
                return -1;
            }

            // Extract values from kwargs dict for each field (generic approach)
            inline for (struct_info.fields) |field| {
                const field_name_z = field.name ++ "\x00";

                // Get the value from kwargs
                var value: ?*py.PyObject = null;
                if (has_kwargs) {
                    value = py.PyDict_GetItemString(kwargs, field_name_z);
                }

                if (value == null) {
                    // Check if field has a default value or is optional
                    const field_info = @typeInfo(field.type);
                    const is_optional = field_info == .optional;

                    if (field.default_value_ptr) |default_ptr| {
                        // Use the default value from the Zig struct
                        const default_value = @as(*const field.type, @ptrCast(@alignCast(default_ptr))).*;
                        @field(wrapper_obj.data.*, field.name) = default_value;
                    } else if (is_optional) {
                        // Optional field without explicit default - set to null
                        @field(wrapper_obj.data.*, field.name) = null;
                    } else {
                        // Field is required but not provided and has no default
                        var error_msg: [256]u8 = undefined;
                        const msg = std.fmt.bufPrintZ(&error_msg, "__init__() missing required keyword-only argument: '{s}'", .{field.name}) catch {
                            py.PyErr_SetString(py.PyExc_TypeError, "__init__() missing required argument");
                            std.heap.c_allocator.destroy(wrapper_obj.data);
                            return -1;
                        };
                        py.PyErr_SetString(py.PyExc_TypeError, msg);
                        std.heap.c_allocator.destroy(wrapper_obj.data);
                        return -1;
                    }
                } else {
                    // Convert the Python value to the Zig field type
                    const field_info = @typeInfo(field.type);
                    switch (field_info) {
                        .int => {
                            const int_val = py.PyLong_AsLong(value);
                            if (int_val == -1 and py.PyErr_Occurred() != null) {
                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                return -1;
                            }
                            @field(wrapper_obj.data.*, field.name) = @intCast(int_val);
                        },
                        .float => {
                            const float_val = py.PyFloat_AsDouble(value);
                            if (float_val == -1.0 and py.PyErr_Occurred() != null) {
                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                return -1;
                            }
                            @field(wrapper_obj.data.*, field.name) = @floatCast(float_val);
                        },
                        .bool => {
                            const bool_val = py.PyObject_IsTrue(value);
                            if (bool_val == -1) {
                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                return -1;
                            }
                            @field(wrapper_obj.data.*, field.name) = bool_val == 1;
                        },
                        .pointer => |ptr| {
                            if (ptr.size == .slice and ptr.child == u8 and ptr.is_const) {
                                const str_val = py.PyUnicode_AsUTF8(value);
                                if (str_val == null) {
                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                    return -1;
                                }
                                // IMPORTANT: Duplicate the string data!
                                // The Python string buffer can be moved or freed by Python's GC.
                                // We need our own copy that lives as long as the struct.
                                const str_slice = std.mem.span(str_val.?);
                                const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch {
                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                    return -1;
                                };
                                @field(wrapper_obj.data.*, field.name) = str_copy;
                            } else if (ptr.size == .slice) {
                                // Handle slices (lists)
                                if (py.PyList_Check(value) == 0) {
                                    py.PyErr_SetString(py.PyExc_TypeError, "Expected a list");
                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                    return -1;
                                }

                                const list_size = py.PyList_Size(value);
                                if (list_size < 0) {
                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                    return -1;
                                }

                                // Allocate memory for the slice
                                const slice = std.heap.c_allocator.alloc(ptr.child, @intCast(list_size)) catch {
                                    py.PyErr_SetString(py.PyExc_ValueError, "Failed to allocate memory for list");
                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                    return -1;
                                };

                                // Convert each list item
                                for (0..@intCast(list_size)) |i| {
                                    const item = py.PyList_GetItem(value, @intCast(i));
                                    if (item == null) {
                                        std.heap.c_allocator.free(slice);
                                        std.heap.c_allocator.destroy(wrapper_obj.data);
                                        return -1;
                                    }

                                    // Convert based on child type
                                    const child_info = @typeInfo(ptr.child);
                                    switch (child_info) {
                                        .@"struct" => {
                                            // Handle struct items
                                            const nested_wrapper = @as(*pyzig.PyObjectWrapper(ptr.child), @ptrCast(@alignCast(item)));
                                            slice[i] = nested_wrapper.data.*;
                                        },
                                        .@"enum" => {
                                            // Handle enum items as strings
                                            const str_val = py.PyUnicode_AsUTF8(item);
                                            if (str_val == null) {
                                                std.heap.c_allocator.free(slice);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            const enum_str = std.mem.span(str_val.?);
                                            slice[i] = std.meta.stringToEnum(ptr.child, enum_str) orelse {
                                                std.heap.c_allocator.free(slice);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                py.PyErr_SetString(py.PyExc_ValueError, "Invalid enum value in list");
                                                return -1;
                                            };
                                        },
                                        .optional => |opt| {
                                            // Handle optional items
                                            if (item == py.Py_None()) {
                                                slice[i] = null;
                                            } else {
                                                // Convert based on child type of optional
                                                const opt_child_info = @typeInfo(opt.child);
                                                switch (opt_child_info) {
                                                    .@"struct" => {
                                                        const nested_wrapper = @as(*pyzig.PyObjectWrapper(opt.child), @ptrCast(@alignCast(item)));
                                                        slice[i] = nested_wrapper.data.*;
                                                    },
                                                    .int => {
                                                        const int_val = py.PyLong_AsLong(item);
                                                        if (int_val == -1 and py.PyErr_Occurred() != null) {
                                                            std.heap.c_allocator.free(slice);
                                                            std.heap.c_allocator.destroy(wrapper_obj.data);
                                                            return -1;
                                                        }
                                                        slice[i] = @intCast(int_val);
                                                    },
                                                    .pointer => |p| {
                                                        if (p.size == .slice and p.child == u8) {
                                                            const str_val = py.PyUnicode_AsUTF8(item);
                                                            if (str_val == null) {
                                                                std.heap.c_allocator.free(slice);
                                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                                return -1;
                                                            }
                                                            const str_slice = std.mem.span(str_val.?);
                                                            const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch {
                                                                std.heap.c_allocator.free(slice);
                                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                                return -1;
                                                            };
                                                            slice[i] = str_copy;
                                                        } else {
                                                            slice[i] = null;
                                                        }
                                                    },
                                                    else => {
                                                        slice[i] = null;
                                                    },
                                                }
                                            }
                                        },
                                        .int => {
                                            const int_val = py.PyLong_AsLong(item);
                                            if (int_val == -1 and py.PyErr_Occurred() != null) {
                                                std.heap.c_allocator.free(slice);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            slice[i] = @intCast(int_val);
                                        },
                                        .float => {
                                            const float_val = py.PyFloat_AsDouble(item);
                                            if (float_val == -1.0 and py.PyErr_Occurred() != null) {
                                                std.heap.c_allocator.free(slice);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            slice[i] = @floatCast(float_val);
                                        },
                                        .bool => {
                                            const bool_val = py.PyObject_IsTrue(item);
                                            if (bool_val == -1) {
                                                std.heap.c_allocator.free(slice);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            slice[i] = bool_val == 1;
                                        },
                                        .pointer => |p| {
                                            if (p.size == .slice and p.child == u8) {
                                                const str_val = py.PyUnicode_AsUTF8(item);
                                                if (str_val == null) {
                                                    std.heap.c_allocator.free(slice);
                                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                                    return -1;
                                                }
                                                const str_slice = std.mem.span(str_val.?);
                                                const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch {
                                                    std.heap.c_allocator.free(slice);
                                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                                    return -1;
                                                };
                                                slice[i] = str_copy;
                                            } else {
                                                // Unsupported nested pointer type
                                                std.heap.c_allocator.free(slice);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                py.PyErr_SetString(py.PyExc_TypeError, "Unsupported list pointer item type");
                                                return -1;
                                            }
                                        },
                                        else => {
                                            // Unsupported type
                                            std.heap.c_allocator.free(slice);
                                            std.heap.c_allocator.destroy(wrapper_obj.data);
                                            py.PyErr_SetString(py.PyExc_TypeError, "Unsupported list item type (unknown)");
                                            return -1;
                                        },
                                    }
                                }

                                @field(wrapper_obj.data.*, field.name) = slice;
                            } else {
                                // Other pointer types not yet supported; leave at default
                            }
                        },
                        .optional => |opt| {
                            if (value == py.Py_None()) {
                                @field(wrapper_obj.data.*, field.name) = null;
                            } else {
                                // Convert based on child type
                                const child_info = @typeInfo(opt.child);
                                switch (child_info) {
                                    .int => {
                                        const int_val = py.PyLong_AsLong(value);
                                        if (int_val == -1 and py.PyErr_Occurred() != null) {
                                            std.heap.c_allocator.destroy(wrapper_obj.data);
                                            return -1;
                                        }
                                        @field(wrapper_obj.data.*, field.name) = @intCast(int_val);
                                    },
                                    .float => {
                                        const float_val = py.PyFloat_AsDouble(value);
                                        if (float_val == -1.0 and py.PyErr_Occurred() != null) {
                                            std.heap.c_allocator.destroy(wrapper_obj.data);
                                            return -1;
                                        }
                                        @field(wrapper_obj.data.*, field.name) = @floatCast(float_val);
                                    },
                                    .bool => {
                                        const bool_val = py.PyObject_IsTrue(value);
                                        if (bool_val == -1) {
                                            std.heap.c_allocator.destroy(wrapper_obj.data);
                                            return -1;
                                        }
                                        @field(wrapper_obj.data.*, field.name) = bool_val == 1;
                                    },
                                    .pointer => |p| {
                                        if (p.size == .slice and p.child == u8) {
                                            const str_val = py.PyUnicode_AsUTF8(value);
                                            if (str_val == null) {
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            // IMPORTANT: Duplicate the string data for optional strings too!
                                            const str_slice = std.mem.span(str_val.?);
                                            const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch {
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            };
                                            @field(wrapper_obj.data.*, field.name) = str_copy;
                                        } else {
                                            @field(wrapper_obj.data.*, field.name) = null;
                                        }
                                    },
                                    .@"struct" => {
                                        // Handle optional struct fields
                                        const nested_wrapper = @as(*pyzig.PyObjectWrapper(opt.child), @ptrCast(@alignCast(value)));
                                        @field(wrapper_obj.data.*, field.name) = nested_wrapper.data.*;
                                    },
                                    .@"enum" => {
                                        // Handle optional enum as string
                                        const str_val = py.PyUnicode_AsUTF8(value);
                                        if (str_val == null) {
                                            std.heap.c_allocator.destroy(wrapper_obj.data);
                                            return -1;
                                        }
                                        const enum_str = std.mem.span(str_val.?);
                                        @field(wrapper_obj.data.*, field.name) = std.meta.stringToEnum(opt.child, enum_str) orelse {
                                            py.PyErr_SetString(py.PyExc_ValueError, "Invalid enum value");
                                            std.heap.c_allocator.destroy(wrapper_obj.data);
                                            return -1;
                                        };
                                    },
                                    else => @field(wrapper_obj.data.*, field.name) = null,
                                }
                            }
                        },
                        .@"struct" => {
                            if (comptime linked_list.isLinkedList(field.type)) {
                                // Convert any Python sequence into a DoublyLinkedList of child elements
                                const NodeType = field.type.Node;
                                const ChildType = @TypeOf(@as(NodeType, undefined).data);

                                const seq_len = py.PySequence_Size(value);
                                if (seq_len < 0) {
                                    py.PyErr_SetString(py.PyExc_TypeError, "Expected a sequence for linked list field");
                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                    return -1;
                                }

                                var ll = field.type{ .first = null, .last = null };

                                var i: isize = 0;
                                while (i < seq_len) : (i += 1) {
                                    const item = py.PySequence_GetItem(value, i);
                                    if (item == null) {
                                        // clean not needed: constructed nodes owned by struct allocator lifetime
                                        std.heap.c_allocator.destroy(wrapper_obj.data);
                                        return -1;
                                    }

                                    const node = std.heap.c_allocator.create(NodeType) catch {
                                        py.Py_DECREF(item.?);
                                        std.heap.c_allocator.destroy(wrapper_obj.data);
                                        return -1;
                                    };
                                    // Fill node.data by converting Python item → ChildType
                                    const child_info = @typeInfo(ChildType);
                                    switch (child_info) {
                                        .@"struct" => {
                                            const nested = @as(*pyzig.PyObjectWrapper(ChildType), @ptrCast(@alignCast(item)));
                                            node.* = NodeType{ .data = nested.data.*, .prev = null, .next = null };
                                        },
                                        .@"enum" => {
                                            const s = py.PyUnicode_AsUTF8(item);
                                            if (s == null) {
                                                py.Py_DECREF(item.?);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            const enum_str = std.mem.span(s.?);
                                            const ev = std.meta.stringToEnum(ChildType, enum_str) orelse {
                                                py.Py_DECREF(item.?);
                                                std.heap.c_allocator.destroy(node);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                py.PyErr_SetString(py.PyExc_ValueError, "Invalid enum value in list");
                                                return -1;
                                            };
                                            node.* = NodeType{ .data = ev, .prev = null, .next = null };
                                        },
                                        .int => {
                                            const v = py.PyLong_AsLong(item);
                                            if (v == -1 and py.PyErr_Occurred() != null) {
                                                py.Py_DECREF(item.?);
                                                std.heap.c_allocator.destroy(node);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            node.* = NodeType{ .data = @intCast(v), .prev = null, .next = null };
                                        },
                                        .float => {
                                            const v = py.PyFloat_AsDouble(item);
                                            if (v == -1.0 and py.PyErr_Occurred() != null) {
                                                py.Py_DECREF(item.?);
                                                std.heap.c_allocator.destroy(node);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            node.* = NodeType{ .data = @floatCast(v), .prev = null, .next = null };
                                        },
                                        .bool => {
                                            const v = py.PyObject_IsTrue(item);
                                            if (v == -1) {
                                                py.Py_DECREF(item.?);
                                                std.heap.c_allocator.destroy(node);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                return -1;
                                            }
                                            node.* = NodeType{ .data = (v == 1), .prev = null, .next = null };
                                        },
                                        .pointer => |p| {
                                            if (p.size == .slice and p.child == u8) {
                                                const s = py.PyUnicode_AsUTF8(item);
                                                if (s == null) {
                                                    py.Py_DECREF(item.?);
                                                    std.heap.c_allocator.destroy(node);
                                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                                    return -1;
                                                }
                                                const slice = std.mem.span(s.?);
                                                const dup = std.heap.c_allocator.dupe(u8, slice) catch {
                                                    py.Py_DECREF(item.?);
                                                    std.heap.c_allocator.destroy(node);
                                                    std.heap.c_allocator.destroy(wrapper_obj.data);
                                                    return -1;
                                                };
                                                node.* = NodeType{ .data = dup, .prev = null, .next = null };
                                            } else {
                                                py.Py_DECREF(item.?);
                                                std.heap.c_allocator.destroy(node);
                                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                                py.PyErr_SetString(py.PyExc_TypeError, "Unsupported linked-list child pointer type");
                                                return -1;
                                            }
                                        },
                                        else => {
                                            py.Py_DECREF(item.?);
                                            std.heap.c_allocator.destroy(node);
                                            std.heap.c_allocator.destroy(wrapper_obj.data);
                                            py.PyErr_SetString(py.PyExc_TypeError, "Unsupported linked-list child type");
                                            return -1;
                                        },
                                    }
                                    py.Py_DECREF(item.?);

                                    if (ll.last) |last| {
                                        last.next = node;
                                        node.prev = last;
                                    } else ll.first = node;
                                    ll.last = node;
                                }

                                @field(wrapper_obj.data.*, field.name) = ll;
                            } else {
                                // Treat as nested struct
                                const nested_wrapper = @as(*pyzig.PyObjectWrapper(field.type), @ptrCast(@alignCast(value)));
                                @field(wrapper_obj.data.*, field.name) = nested_wrapper.data.*;
                            }
                        },
                        .@"enum" => {
                            // Handle enum as string
                            const str_val = py.PyUnicode_AsUTF8(value);
                            if (str_val == null) {
                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                return -1;
                            }
                            const enum_str = std.mem.span(str_val.?);
                            @field(wrapper_obj.data.*, field.name) = std.meta.stringToEnum(field.type, enum_str) orelse {
                                py.PyErr_SetString(py.PyExc_ValueError, "Invalid enum value");
                                std.heap.c_allocator.destroy(wrapper_obj.data);
                                return -1;
                            };
                        },
                        else => {
                            // Unsupported type - set a sane empty default
                            const FT = field.type;
                            const fti = @typeInfo(FT);
                            switch (fti) {
                                .pointer => |p| {
                                    if (p.size == .slice) {
                                        // Assign empty slice of the correct child type
                                        const empty: []p.child = &[_]p.child{};
                                        @field(wrapper_obj.data.*, field.name) = empty;
                                    } else {
                                        // Other pointers: leave at default (no assignment)
                                    }
                                },
                                else => {
                                    @field(wrapper_obj.data.*, field.name) = std.mem.zeroInit(FT, .{});
                                },
                            }
                        },
                    }
                }
            }

            return 0;
        }
    };
}

pub fn genStructGetSet(comptime WrapperType: type, comptime T: type) type {
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("genStructGetSet only supports structs");
    }
    const struct_info = info.@"struct";
    // Build the getset array at comptime (without field_names property)
    const getset_array = comptime blk: {
        var _getset: [struct_info.fields.len + 1]py.PyGetSetDef = undefined; // +1 for sentinel only
        for (struct_info.fields, 0..) |field, i| {
            const field_name_z = field.name ++ "\x00";
            _getset[i] = getset.genProp(WrapperType, field.type, field_name_z);
        }
        _getset[struct_info.fields.len] = py.GS_SENTINEL;
        break :blk _getset;
    };

    return struct {
        // Store the comptime-generated getset array as a var to ensure it persists
        pub var getset = getset_array;
    };
}

pub fn genStructRepr(comptime WrapperType: type, comptime T: type) type {
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("genStructRepr only supports structs");
    }
    return struct {
        // Generate the repr function
        pub fn impl(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper_obj: *WrapperType = @ptrCast(@alignCast(self));
            var buf: [65536]u8 = undefined; // 64KB buffer for very large structs
            const out = util.printStruct(wrapper_obj.data.*, &buf) catch |err| {
                // If even 64KB is not enough, fall back to simple representation
                if (err == error.NoSpaceLeft) {
                    const type_name = @typeName(T);
                    const simple_repr = std.fmt.allocPrintZ(std.heap.c_allocator, "<{s} object at 0x{x}>", .{ type_name, @intFromPtr(wrapper_obj) }) catch {
                        _ = py.PyErr_SetString(py.PyExc_ValueError, "Failed to allocate memory for repr");
                        return null;
                    };
                    defer std.heap.c_allocator.free(simple_repr);
                    return py.PyUnicode_FromStringAndSize(simple_repr.ptr, @intCast(simple_repr.len));
                }
                // Other errors
                _ = py.PyErr_SetString(py.PyExc_ValueError, "Failed to format structure for printing");
                return null;
            };
            // PyUnicode_FromStringAndSize copies the data, so we don't need to worry about buf going out of scope
            return py.PyUnicode_FromStringAndSize(out.ptr, @intCast(out.len));
        }
    };
}

pub fn genStructFieldNames(comptime T: type) type {
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("genStructFieldNames only supports structs");
    }
    const struct_info = info.@"struct";

    return struct {

        // Static function to get field names
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self; // Static method, don't need instance
            _ = args; // No arguments needed

            // Create a Python list with all field names
            const list = py.PyList_New(@intCast(struct_info.fields.len));
            if (list == null) return null;

            inline for (struct_info.fields, 0..) |field, i| {
                const field_name_str = py.PyUnicode_FromString(field.name.ptr);
                if (field_name_str == null) {
                    if (list) |l| py.Py_DECREF(l);
                    return null;
                }
                // PyList_SetItem steals the reference, so we don't need to DECREF field_name_str
                if (py.PyList_SetItem(list, @intCast(i), field_name_str) != 0) {
                    if (list) |l| py.Py_DECREF(l);
                    return null;
                }
            }

            return list;
        }

        pub fn method() py.PyMethodDef {
            return .{
                .ml_name = "__field_names__",
                .ml_meth = @ptrCast(&impl),
                .ml_flags = py.METH_NOARGS | py.METH_STATIC,
                .ml_doc = "Return list of field names in this struct",
            };
        }
    };
}
