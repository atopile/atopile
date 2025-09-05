const std = @import("std");
const py = @import("pybindings.zig");

const Method = fn (_: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject;

pub fn module_method(comptime method: Method, comptime name: [*:0]const u8) py.PyMethodDef {
    return .{
        .ml_name = name,
        .ml_meth = @ptrCast(&method),
        .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
    };
}

pub fn printStruct(value: anytype, buf: []u8) ![:0]u8 {
    const T = @TypeOf(value);
    const info = @typeInfo(T);

    switch (info) {
        .@"struct" => |s| {
            var pos: usize = 0;

            // Write struct name and opening brace
            const header = try std.fmt.bufPrintZ(buf[pos..], "{s} {{\n", .{@typeName(T)});
            pos += header.len;

            // Write each field
            inline for (s.fields) |field| {
                const field_value = @field(value, field.name);
                const field_type = @TypeOf(field_value);
                const field_type_info = @typeInfo(field_type);

                // Check field type for special handling
                const is_string = switch (field_type_info) {
                    .pointer => |ptr| ptr.size == .slice and ptr.child == u8 and ptr.is_const,
                    else => false,
                };

                const is_struct = switch (field_type_info) {
                    .@"struct" => true,
                    else => false,
                };

                if (is_string) {
                    // Handle string fields
                    const field_str = try std.fmt.bufPrintZ(buf[pos..], "  {s}: \"{s}\"\n", .{ field.name, field_value });
                    pos += field_str.len;
                } else if (is_struct) {
                    // Handle struct fields recursively
                    const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: ", .{field.name});
                    pos += field_header.len;

                    // Recursively print the struct, adjusting indentation
                    var temp_buf: [4096]u8 = undefined; // Increased for nested structs
                    const struct_str = try printStruct(field_value, &temp_buf);

                    // Add indentation to each line of the struct output
                    var line_iter = std.mem.splitScalar(u8, struct_str, '\n');
                    var first_line = true;
                    while (line_iter.next()) |line| {
                        if (line.len == 0) continue; // Skip empty lines

                        const indented_line = if (first_line) blk: {
                            first_line = false;
                            break :blk try std.fmt.bufPrintZ(buf[pos..], "{s}\n", .{line});
                        } else try std.fmt.bufPrintZ(buf[pos..], "  {s}\n", .{line});
                        pos += indented_line.len;
                    }
                } else {
                    // Handle other field types including optionals and slices
                    const field_str = switch (field_type_info) {
                        .optional => |opt| blk: {
                            // Check what type is inside the optional
                            const child_info = @typeInfo(opt.child);

                            // Check if the optional contains a struct
                            if (child_info == .@"struct") {
                                if (field_value) |val| {
                                    // Handle optional struct recursively
                                    const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: ", .{field.name});
                                    pos += field_header.len;

                                    // Recursively print the struct
                                    var temp_buf: [4096]u8 = undefined; // Increased for nested structs
                                    const struct_str = try printStruct(val, &temp_buf);

                                    // Add indentation to each line of the struct output
                                    var line_iter = std.mem.splitScalar(u8, struct_str, '\n');
                                    var first_line = true;
                                    while (line_iter.next()) |line| {
                                        if (line.len == 0) continue; // Skip empty lines

                                        const indented_line = if (first_line) blk2: {
                                            first_line = false;
                                            break :blk2 try std.fmt.bufPrintZ(buf[pos..], "{s}\n", .{line});
                                        } else try std.fmt.bufPrintZ(buf[pos..], "  {s}\n", .{line});
                                        pos += indented_line.len;
                                    }
                                    // Return empty string to indicate we've already handled output
                                    break :blk "";
                                } else {
                                    break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: null\n", .{field.name});
                                }
                            } else if (child_info == .pointer and child_info.pointer.size == .slice) {
                                // Optional slice - use {?s} for optional strings
                                if (child_info.pointer.child == u8) {
                                    if (field_value == null) {
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: None\n", .{field.name});
                                    } else {
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: \"{?s}\"\n", .{ field.name, field_value });
                                    }
                                } else {
                                    break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {?any}\n", .{ field.name, field_value });
                                }
                            } else {
                                break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {?}\n", .{ field.name, field_value });
                            }
                        },
                        .pointer => |ptr| blk: {
                            if (ptr.size == .slice) {
                                if (ptr.child == u8) {
                                    // String slice - print with quotes
                                    const str_slice: []const u8 = field_value;
                                    // Check if string is printable
                                    var is_printable = true;
                                    for (str_slice) |c| {
                                        if (c < 32 or c > 126) {
                                            is_printable = false;
                                            break;
                                        }
                                    }
                                    if (is_printable and str_slice.len > 0) {
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: \"{s}\"\n", .{ field.name, str_slice });
                                    } else {
                                        // Non-printable or empty, show as byte array
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {any}\n", .{ field.name, field_value });
                                    }
                                } else {
                                    // Check if it's a slice of structs
                                    const child_info = @typeInfo(ptr.child);
                                    if (child_info == .@"struct") {
                                        // Slice of structs - format them nicely with line breaks
                                        const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: [\n", .{field.name});
                                        pos += field_header.len;

                                        // Print each struct in the slice with proper indentation
                                        for (field_value, 0..) |item, i| {
                                            // Add indentation for array items
                                            const indent = try std.fmt.bufPrintZ(buf[pos..], "    ", .{});
                                            pos += indent.len;

                                            // Recursively print the struct
                                            var item_buf: [8192]u8 = undefined;
                                            const item_str = try printStruct(item, &item_buf);

                                            // Add extra indentation to each line of the nested struct
                                            var line_iter = std.mem.splitScalar(u8, item_str, '\n');
                                            var first_line = true;
                                            while (line_iter.next()) |line| {
                                                if (line.len == 0) continue;

                                                if (!first_line) {
                                                    const nested_indent = try std.fmt.bufPrintZ(buf[pos..], "    ", .{});
                                                    pos += nested_indent.len;
                                                }
                                                first_line = false;

                                                const line_out = try std.fmt.bufPrintZ(buf[pos..], "{s}\n", .{line});
                                                pos += line_out.len;
                                            }

                                            if (i < field_value.len - 1) {
                                                // Add comma between items
                                                const comma = try std.fmt.bufPrintZ(buf[pos..], "    ,\n", .{});
                                                pos += comma.len;
                                            }
                                        }

                                        const closer = try std.fmt.bufPrintZ(buf[pos..], "  ]\n", .{});
                                        pos += closer.len;
                                        // Return empty string to indicate we've already handled output
                                        break :blk "";
                                    } else if (child_info == .pointer and child_info.pointer.size == .slice and child_info.pointer.child == u8) {
                                        // Slice of strings ([][]const u8)
                                        const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: [", .{field.name});
                                        pos += field_header.len;

                                        // Print each string in the slice
                                        for (field_value, 0..) |item, i| {
                                            if (i > 0) {
                                                const comma = try std.fmt.bufPrintZ(buf[pos..], ", ", .{});
                                                pos += comma.len;
                                            }

                                            const str_item: []const u8 = item;
                                            // Check if string is printable
                                            var is_printable = true;
                                            for (str_item) |c| {
                                                if (c < 32 or c > 126) {
                                                    is_printable = false;
                                                    break;
                                                }
                                            }

                                            if (is_printable and str_item.len > 0) {
                                                const str_out = try std.fmt.bufPrintZ(buf[pos..], "\"{s}\"", .{str_item});
                                                pos += str_out.len;
                                            } else {
                                                // Show as byte array
                                                const bytes_out = try std.fmt.bufPrintZ(buf[pos..], "{any}", .{str_item});
                                                pos += bytes_out.len;
                                            }
                                        }

                                        const closer = try std.fmt.bufPrintZ(buf[pos..], "]\n", .{});
                                        pos += closer.len;
                                        // Return empty string to indicate we've already handled output
                                        break :blk "";
                                    } else {
                                        // Other non-struct slice types
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {any}\n", .{ field.name, field_value });
                                    }
                                }
                            } else {
                                break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {any}\n", .{ field.name, field_value });
                            }
                        },
                        else => try std.fmt.bufPrintZ(buf[pos..], "  {s}: {any}\n", .{ field.name, field_value }),
                    };
                    // Only add to pos if we didn't already handle it (optional struct case returns empty string)
                    if (field_str.len > 0) {
                        pos += field_str.len;
                    }
                }
            }

            // Write closing brace
            const footer = try std.fmt.bufPrintZ(buf[pos..], "}}\n", .{});
            pos += footer.len;

            // Null-terminate the string
            if (pos >= buf.len) return error.BufferTooSmall;
            buf[pos] = 0;

            return buf[0..pos :0];
        },
        else => @compileError("Not a struct"),
    }
}

pub fn gen_repr(comptime struct_type: type) ?*const fn (?*py.PyObject) callconv(.C) ?*py.PyObject {
    const repr = struct {
        fn impl(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            var buf: [8192]u8 = undefined; // Increased buffer size
            const out = printStruct(obj.top.*, &buf) catch |err| {
                // Set a proper Python exception when printStruct fails
                const err_msg = switch (err) {
                    error.NoSpaceLeft => "Buffer overflow: Structure too large to print",
                    else => "Failed to format structure for printing",
                };
                _ = py.PyErr_SetString(py.PyExc_ValueError, err_msg);
                return null;
            };
            // PyUnicode_FromStringAndSize copies the data, so we don't need to worry about buf going out of scope
            return py.PyUnicode_FromStringAndSize(out.ptr, @intCast(out.len));
        }
    }.impl;

    return repr;
}

pub fn int_prop(comptime struct_type: type, comptime field_name: [*:0]const u8) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            // Check if the wrapper has 'data' field (new style) or 'top' field (old style)
            const has_data = @hasField(struct_type, "data");
            if (has_data) {
                return py.PyLong_FromLong(@field(obj.data.*, field_name_str));
            } else {
                return py.PyLong_FromLong(@field(obj.top.*, field_name_str));
            }
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) {
                return -1;
            }

            const new_val = py.PyLong_AsLong(value);
            const has_data = @hasField(struct_type, "data");
            if (has_data) {
                @field(obj.data.*, field_name_str) = @intCast(new_val);
            } else {
                @field(obj.top.*, field_name_str) = @intCast(new_val);
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

pub fn enum_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime EnumType: type) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            const has_data = @hasField(struct_type, "data");
            const val: EnumType = if (has_data)
                @field(obj.data.*, field_name_str)
            else
                @field(obj.top.*, field_name_str);
            // Convert enum to string
            const enum_str = @tagName(val);
            return py.PyUnicode_FromString(enum_str.ptr);
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) {
                return -1;
            }

            const str_val = py.PyUnicode_AsUTF8(value);
            if (str_val == null) {
                return -1;
            }

            const enum_str = std.mem.span(str_val.?);
            const enum_val = std.meta.stringToEnum(EnumType, enum_str) orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Invalid enum value");
                return -1;
            };

            const has_data = @hasField(struct_type, "data");
            if (has_data) {
                @field(obj.data.*, field_name_str) = enum_val;
            } else {
                @field(obj.top.*, field_name_str) = enum_val;
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

pub fn str_prop(comptime struct_type: type, comptime field_name: [*:0]const u8) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            const has_data = @hasField(struct_type, "data");
            const val: []const u8 = if (has_data)
                @field(obj.data.*, field_name_str)
            else
                @field(obj.top.*, field_name_str);
            // Use PyUnicode_FromStringAndSize to handle non-null-terminated strings
            return py.PyUnicode_FromStringAndSize(val.ptr, @intCast(val.len));
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) {
                return -1;
            }

            const new_val = py.PyUnicode_AsUTF8(value);
            if (new_val == null) {
                return -1;
            }

            // Duplicate the string data - Python's buffer can be freed/moved
            const str_slice = std.mem.span(new_val.?);
            const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch return -1;

            const has_data = @hasField(struct_type, "data");
            if (has_data) {
                // Free the old string if it exists
                // Note: This assumes we always allocate strings, which we do now
                @field(obj.data.*, field_name_str) = str_copy;
            } else {
                @field(obj.top.*, field_name_str) = str_copy;
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

pub fn obj_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime PType: type, type_obj: *py.PyTypeObject) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);

    // create thin python object wrapper around the zig object
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));

            // Get a pointer to the nested field data
            const has_data = @hasField(struct_type, "data");
            const zigval_ptr = if (has_data)
                &@field(obj.data.*, field_name_str)
            else
                &@field(obj.top.*, field_name_str);

            // Create a simple Python object wrapper
            const pyobj = py.PyType_GenericAlloc(type_obj, 0);
            if (pyobj == null) return null;

            const typed_obj: *PType = @ptrCast(@alignCast(pyobj));

            // Initialize the Python object header
            typed_obj.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };

            // Store the pointer to the nested data
            const has_data_inner = @hasField(PType, "data");
            if (has_data_inner) {
                typed_obj.data = zigval_ptr;
            } else {
                typed_obj.top = zigval_ptr;
            }

            return pyobj;
        }
    }.impl;

    // copy the value from the python object to the zig object
    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) {
                return -1;
            }

            // Cast the PyObject to PType and extract the underlying Zig data
            const pyval: *PType = @ptrCast(@alignCast(value));
            const has_data = @hasField(struct_type, "data");
            const has_data_inner = @hasField(PType, "data");

            if (has_data) {
                if (has_data_inner) {
                    @field(obj.data.*, field_name_str) = pyval.data.*;
                } else {
                    @field(obj.data.*, field_name_str) = pyval.top.*;
                }
            } else {
                if (has_data_inner) {
                    @field(obj.top.*, field_name_str) = pyval.data.*;
                } else {
                    @field(obj.top.*, field_name_str) = pyval.top.*;
                }
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

// Property for float fields
pub fn float_prop(comptime struct_type: type, comptime field_name: [*:0]const u8) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            return py.PyFloat_FromDouble(@field(obj.data.*, field_name_str));
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) return -1;
            const new_val = py.PyFloat_AsDouble(value);
            @field(obj.data.*, field_name_str) = @floatCast(new_val);
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
pub fn bool_prop(comptime struct_type: type, comptime field_name: [*:0]const u8) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            const val = @field(obj.data.*, field_name_str);
            if (val) return py.Py_True() else return py.Py_False();
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) return -1;
            const is_true = py.PyObject_IsTrue(value);
            @field(obj.data.*, field_name_str) = is_true == 1;
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
pub fn optional_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime ChildType: type) py.PyGetSetDef {
    @setEvalBranchQuota(100000);
    const field_name_str = std.mem.span(field_name);

    // For struct types, we need to generate the binding at comptime
    const child_info = @typeInfo(ChildType);
    const type_name = if (child_info == .@"struct")
        std.fmt.comptimePrint("{s}.{s}", .{ @typeName(ChildType), field_name_str })
    else
        field_name;
    const NestedBinding = if (child_info == .@"struct") wrap_in_python(ChildType, type_name) else void;

    const getter = struct {
        var nested_type_obj: ?*py.PyTypeObject = null;
        var init_mutex = false;

        fn getNestedTypeObj() *py.PyTypeObject {
            if (child_info != .@"struct") unreachable;

            if (nested_type_obj) |obj| {
                return obj;
            }

            if (!init_mutex) {
                init_mutex = true;
                const result = py.PyType_Ready(&NestedBinding.type_object);
                if (result < 0) {
                    @panic("Failed to initialize optional nested type");
                }
                nested_type_obj = &NestedBinding.type_object;
            }

            return &NestedBinding.type_object;
        }

        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            const val = @field(obj.data.*, field_name_str);
            if (val) |v| {
                // Handle the non-null case based on child type
                switch (child_info) {
                    .int => return py.PyLong_FromLong(@intCast(v)),
                    .float => return py.PyFloat_FromDouble(@floatCast(v)),
                    .bool => if (v) return py.Py_True() else return py.Py_False(),
                    .pointer => |ptr| {
                        if (ptr.size == .slice and ptr.child == u8) {
                            // Use PyUnicode_FromStringAndSize to handle non-null-terminated strings
                            return py.PyUnicode_FromStringAndSize(v.ptr, @intCast(v.len));
                        }
                    },
                    .@"struct" => {
                        // Create a new Python object for the nested struct
                        const type_obj = getNestedTypeObj();
                        const pyobj = py.PyType_GenericAlloc(type_obj, 0);
                        if (pyobj == null) return null;

                        const NestedWrapper = PyObjectWrapper(ChildType);
                        const wrapper: *NestedWrapper = @ptrCast(@alignCast(pyobj));
                        wrapper.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };
                        // Store a pointer to the value - we need to make a copy
                        // since v is a local value, we allocate it in the wrapper
                        wrapper.data = std.heap.c_allocator.create(ChildType) catch return null;
                        wrapper.data.* = v;

                        return pyobj;
                    },
                    .@"enum" => {
                        // Convert enum to string
                        const enum_str = @tagName(v);
                        return py.PyUnicode_FromString(enum_str.ptr);
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
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null or value == py.Py_None()) {
                @field(obj.data.*, field_name_str) = null;
                return 0;
            }
            // Handle setting based on child type
            switch (child_info) {
                .int => {
                    const new_val = py.PyLong_AsLong(value);
                    @field(obj.data.*, field_name_str) = @intCast(new_val);
                },
                .float => {
                    const new_val = py.PyFloat_AsDouble(value);
                    @field(obj.data.*, field_name_str) = @floatCast(new_val);
                },
                .bool => {
                    const is_true = py.PyObject_IsTrue(value);
                    @field(obj.data.*, field_name_str) = is_true == 1;
                },
                .pointer => |ptr| {
                    if (ptr.size == .slice and ptr.child == u8) {
                        const new_val = py.PyUnicode_AsUTF8(value);
                        if (new_val == null) return -1;
                        @field(obj.data.*, field_name_str) = std.mem.span(new_val.?);
                    }
                },
                .@"enum" => {
                    // Convert string to enum
                    const str_val = py.PyUnicode_AsUTF8(value);
                    if (str_val == null) return -1;
                    const enum_str = std.mem.span(str_val.?);
                    @field(obj.data.*, field_name_str) = std.meta.stringToEnum(ChildType, enum_str) orelse {
                        py.PyErr_SetString(py.PyExc_ValueError, "Invalid enum value");
                        return -1;
                    };
                },
                .@"struct" => {
                    // Handle struct type - extract data from wrapped Python object
                    const WrapperType = PyObjectWrapper(ChildType);
                    const wrapper_obj: *WrapperType = @ptrCast(@alignCast(value));
                    // Copy the struct data
                    @field(obj.data.*, field_name_str) = wrapper_obj.data.*;
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

// Property for slice fields
pub fn slice_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime ChildType: type) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);

    // For struct types, we need to generate the binding at comptime
    const child_info = @typeInfo(ChildType);
    const type_name = if (child_info == .@"struct")
        std.fmt.comptimePrint("{s}.{s}", .{ @typeName(ChildType), field_name_str })
    else
        field_name;
    const NestedBinding = if (child_info == .@"struct") wrap_in_python(ChildType, type_name) else void;

    const getter = struct {
        var nested_type_obj: ?*py.PyTypeObject = null;
        var init_mutex = false;

        fn getNestedTypeObj() *py.PyTypeObject {
            if (child_info != .@"struct") unreachable;

            if (nested_type_obj) |obj| {
                return obj;
            }

            if (!init_mutex) {
                init_mutex = true;
                const result = py.PyType_Ready(&NestedBinding.type_object);
                if (result < 0) {
                    @panic("Failed to initialize slice nested type");
                }
                nested_type_obj = &NestedBinding.type_object;
            }

            return &NestedBinding.type_object;
        }

        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            const slice = @field(obj.data.*, field_name_str);

            // Create a Python list
            const list = py.PyList_New(@intCast(slice.len));
            if (list == null) return null;

            for (slice, 0..) |item, i| {
                // Create Python object for each item
                const wrapped = wrap_value(item) orelse {
                    py.Py_DECREF(list.?);
                    return null;
                };
                _ = py.PyList_SetItem(list, @intCast(i), wrapped);
            }

            return list;
        }

        fn wrap_value(value: ChildType) ?*py.PyObject {
            switch (child_info) {
                .@"struct" => {
                    // Create a new Python object for the struct
                    const type_obj = getNestedTypeObj();
                    const pyobj = py.PyType_GenericAlloc(type_obj, 0);
                    if (pyobj == null) return null;

                    const NestedWrapper = PyObjectWrapper(ChildType);
                    const wrapper: *NestedWrapper = @ptrCast(@alignCast(pyobj));
                    wrapper.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };
                    wrapper.data = std.heap.c_allocator.create(ChildType) catch return null;
                    wrapper.data.* = value;

                    return pyobj;
                },
                .int => return py.PyLong_FromLong(@intCast(value)),
                .float => return py.PyFloat_FromDouble(@floatCast(value)),
                .bool => if (value) return py.Py_True() else return py.Py_False(),
                .pointer => |ptr| {
                    if (ptr.size == .slice and ptr.child == u8) {
                        // String slice - use PyUnicode_FromStringAndSize to handle non-null-terminated strings
                        return py.PyUnicode_FromStringAndSize(value.ptr, @intCast(value.len));
                    }
                    // Other pointer types not yet supported
                    const none = py.Py_None();
                    py.Py_INCREF(none);
                    return none;
                },
                else => {
                    // Unsupported type - return None
                    const none = py.Py_None();
                    py.Py_INCREF(none);
                    return none;
                },
            }
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "Cannot delete slice attribute");
                return -1;
            }

            // Check if value is a list
            if (py.PyList_Check(value) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "Expected a list");
                return -1;
            }

            const list_size = py.PyList_Size(value);
            if (list_size < 0) {
                return -1;
            }

            // Allocate new slice
            const new_slice = std.heap.c_allocator.alloc(ChildType, @intCast(list_size)) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate memory for slice");
                return -1;
            };

            // Convert each Python object to the child type
            for (0..@intCast(list_size)) |i| {
                const item = py.PyList_GetItem(value, @intCast(i));
                if (item == null) {
                    std.heap.c_allocator.free(new_slice);
                    return -1;
                }

                // Convert Python object to child type
                switch (child_info) {
                    .@"struct" => {
                        // Extract struct data from Python wrapper
                        const NestedWrapper = PyObjectWrapper(ChildType);
                        const wrapper: *NestedWrapper = @ptrCast(@alignCast(item));
                        new_slice[i] = wrapper.data.*;
                    },
                    .int => {
                        const int_val = py.PyLong_AsLong(item);
                        if (int_val == -1 and py.PyErr_Occurred() != null) {
                            std.heap.c_allocator.free(new_slice);
                            return -1;
                        }
                        new_slice[i] = @intCast(int_val);
                    },
                    .float => {
                        const float_val = py.PyFloat_AsDouble(item);
                        if (py.PyErr_Occurred() != null) {
                            std.heap.c_allocator.free(new_slice);
                            return -1;
                        }
                        new_slice[i] = @floatCast(float_val);
                    },
                    .bool => {
                        const is_true = py.PyObject_IsTrue(item);
                        if (is_true == -1) {
                            std.heap.c_allocator.free(new_slice);
                            return -1;
                        }
                        new_slice[i] = is_true == 1;
                    },
                    .pointer => |ptr| {
                        if (ptr.size == .slice and ptr.child == u8) {
                            // String slice
                            const str_val = py.PyUnicode_AsUTF8(item);
                            if (str_val == null) {
                                std.heap.c_allocator.free(new_slice);
                                return -1;
                            }
                            // Duplicate the string
                            const str_span = std.mem.span(str_val.?);
                            const str_copy = std.heap.c_allocator.dupe(u8, str_span) catch {
                                std.heap.c_allocator.free(new_slice);
                                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to duplicate string");
                                return -1;
                            };
                            new_slice[i] = str_copy;
                        } else {
                            std.heap.c_allocator.free(new_slice);
                            py.PyErr_SetString(py.PyExc_TypeError, "Unsupported pointer type in slice");
                            return -1;
                        }
                    },
                    else => {
                        std.heap.c_allocator.free(new_slice);
                        py.PyErr_SetString(py.PyExc_TypeError, "Unsupported type in slice");
                        return -1;
                    },
                }
            }

            // Free old slice if needed (be careful about memory management)
            // For now, we'll just replace it (potential memory leak of old data)
            @field(obj.data.*, field_name_str) = new_slice;

            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

// Property for struct fields
pub fn struct_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime FieldType: type) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);

    // Generate a unique type name for the nested struct
    const type_name = std.fmt.comptimePrint("{s}.{s}", .{ @typeName(FieldType), field_name_str });

    // Generate a Python binding for the nested struct type
    // We need to create this at comptime so it can be properly initialized
    const NestedBinding = wrap_in_python(FieldType, type_name);

    const getter = struct {
        // Store the type object statically and initialize it lazily
        var nested_type_obj: ?*py.PyTypeObject = null;
        var init_mutex = false; // Simple mutex for single-threaded init

        fn getNestedTypeObj() *py.PyTypeObject {
            if (nested_type_obj) |obj| {
                return obj;
            }

            // Initialize the type if not done yet
            if (!init_mutex) {
                init_mutex = true;

                // Set up the type properly
                const result = py.PyType_Ready(&NestedBinding.type_object);
                if (result < 0) {
                    @panic("Failed to initialize nested type");
                }

                nested_type_obj = &NestedBinding.type_object;
            }

            return &NestedBinding.type_object;
        }

        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));

            // Get pointer to the nested struct field
            const nested_data = &@field(obj.data.*, field_name_str);

            // Get the type object for the nested struct
            const type_obj = getNestedTypeObj();

            // Allocate a new Python object for the nested struct
            const pyobj = py.PyType_GenericAlloc(type_obj, 0);
            if (pyobj == null) return null;

            const NestedWrapper = PyObjectWrapper(FieldType);
            const wrapper: *NestedWrapper = @ptrCast(@alignCast(pyobj));
            wrapper.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };
            wrapper.data = nested_data;

            return pyobj;
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) return -1;

            // Try to extract the nested struct from the Python object
            const NestedWrapper = PyObjectWrapper(FieldType);
            const nested_wrapper = @as(*NestedWrapper, @ptrCast(@alignCast(value)));
            @field(obj.data.*, field_name_str) = nested_wrapper.data.*;

            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

// Main comptime function to wrap a struct in Python bindings
pub fn wrap_in_python(comptime T: type, comptime name: [*:0]const u8) type {
    @setEvalBranchQuota(100000);
    const info = @typeInfo(T);
    if (info != .@"struct") {
        @compileError("wrap_in_python only supports structs");
    }

    const WrapperType = PyObjectWrapper(T);
    const struct_info = info.@"struct";

    // Build the getset array at comptime (without field_names property)
    const getset_array = comptime blk: {
        var getset: [struct_info.fields.len + 1]py.PyGetSetDef = undefined; // +1 for sentinel only
        for (struct_info.fields, 0..) |field, i| {
            const field_name_z = field.name ++ "\x00";
            getset[i] = genProp(WrapperType, field.type, field_name_z);
        }
        getset[struct_info.fields.len] = py.GS_SENTINEL;
        break :blk getset;
    };

    return struct {
        // Generate the __init__ function using a truly generic approach
        pub fn generated_init(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) c_int {
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
                    // Check if field has a default value
                    if (field.default_value_ptr) |default_ptr| {
                        // Use the default value from the Zig struct
                        const default_value = @as(*const field.type, @ptrCast(@alignCast(default_ptr))).*;
                        @field(wrapper_obj.data.*, field.name) = default_value;
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
                                            const nested_wrapper = @as(*PyObjectWrapper(ptr.child), @ptrCast(@alignCast(item)));
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
                                            py.PyErr_SetString(py.PyExc_TypeError, "Unsupported list item type");
                                            return -1;
                                        },
                                    }
                                }

                                @field(wrapper_obj.data.*, field.name) = slice;
                            } else {
                                // Other pointer types not yet supported
                                @field(wrapper_obj.data.*, field.name) = &.{};
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
                                        const nested_wrapper = @as(*PyObjectWrapper(opt.child), @ptrCast(@alignCast(value)));
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
                            // Check if it's the correct type
                            const nested_wrapper = @as(*PyObjectWrapper(field.type), @ptrCast(@alignCast(value)));
                            @field(wrapper_obj.data.*, field.name) = nested_wrapper.data.*;
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
                            // Unsupported type - use default
                            @field(wrapper_obj.data.*, field.name) = std.mem.zeroInit(field.type, .{});
                        },
                    }
                }
            }

            return 0;
        }

        // Store the comptime-generated getset array as a var to ensure it persists
        pub var generated_getset = getset_array;

        // Create methods array with __field_names__ static method
        pub var generated_methods = [_]py.PyMethodDef{
            py.PyMethodDef{
                .ml_name = "__field_names__",
                .ml_meth = @ptrCast(&get_field_names_func),
                .ml_flags = py.METH_NOARGS | py.METH_STATIC,
                .ml_doc = "Return list of field names in this struct",
            },
            py.ML_SENTINEL,
        };

        // Generate the repr function
        pub fn generated_repr(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper_obj: *WrapperType = @ptrCast(@alignCast(self));
            var buf: [65536]u8 = undefined; // 64KB buffer for very large structs
            const out = printStruct(wrapper_obj.data.*, &buf) catch |err| {
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

        // Static function to get field names
        pub fn get_field_names_func(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
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

        // The actual PyTypeObject
        pub var type_object = py.PyTypeObject{
            .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
            .tp_name = name,
            .tp_basicsize = @sizeOf(WrapperType),
            .tp_repr = generated_repr,
            .tp_flags = py.Py_TPFLAGS_DEFAULT | py.Py_TPFLAGS_BASETYPE,
            .tp_getset = @as([*]py.PyGetSetDef, @ptrCast(@constCast(&generated_getset))),
            .tp_methods = @as([*]py.PyMethodDef, @ptrCast(@constCast(&generated_methods))),
            .tp_init = generated_init,
        };
    };
}
// Auto-generated Python wrapper for a Zig struct
pub fn PyObjectWrapper(comptime T: type) type {
    return struct {
        ob_base: py.PyObject_HEAD,
        data: *T,
    };
}

// Generate format string for PyArg_ParseTupleAndKeywords based on field type
fn getFormatChar(comptime T: type) u8 {
    const info = @typeInfo(T);
    return switch (info) {
        .int => 'i',
        .float => 'd',
        .bool => 'p',
        .pointer => |ptr| if (ptr.size == .slice and ptr.child == u8) 's' else 'O',
        .optional => |opt| switch (@typeInfo(opt.child)) {
            .pointer => 'O',
            else => getFormatChar(opt.child),
        },
        .@"struct" => 'O',
        else => 'O',
    };
}

// Generate property getter/setter based on field type
fn genProp(comptime WrapperType: type, comptime FieldType: type, comptime field_name: [*:0]const u8) py.PyGetSetDef {
    const info = @typeInfo(FieldType);

    switch (info) {
        .int => return int_prop(WrapperType, field_name),
        .float => return float_prop(WrapperType, field_name),
        .bool => return bool_prop(WrapperType, field_name),
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child == u8 and ptr.is_const) {
                return str_prop(WrapperType, field_name);
            }
            // Handle slices of structs
            return slice_prop(WrapperType, field_name, ptr.child);
        },
        .optional => |opt| return optional_prop(WrapperType, field_name, opt.child),
        .@"struct" => return struct_prop(WrapperType, field_name, FieldType),
        .@"enum" => return enum_prop(WrapperType, field_name, FieldType), // Enums are strings in Python
        else => @compileError("Unsupported field type: " ++ @typeName(FieldType)),
    }
}

// Wrap an entire module worth of structs
pub fn wrap_in_python_module(comptime module: type) type {
    @setEvalBranchQuota(100000);
    const module_info = @typeInfo(module);
    if (module_info != .@"struct") {
        @compileError("wrap_in_python_module expects a module (struct)");
    }

    return struct {
        // Count how many structs we'll wrap
        const struct_count = blk: {
            var count: usize = 0;
            for (module_info.@"struct".decls) |decl| {
                const decl_value = @field(module, decl.name);
                const decl_type = @TypeOf(decl_value);
                const decl_info = @typeInfo(decl_type);

                if (decl_info == .type) {
                    const inner_type = decl_value;
                    const inner_info = @typeInfo(inner_type);
                    if (inner_info == .@"struct") {
                        // Check if it's a data struct (starts with uppercase)
                        const is_type_name = decl.name[0] >= 'A' and decl.name[0] <= 'Z';
                        if (is_type_name) {
                            count += 1;
                        }
                    }
                }
            }
            break :blk count;
        };

        // Register all bindings with Python
        pub fn register_all(py_module: ?*py.PyObject) c_int {
            // Process each declaration
            inline for (module_info.@"struct".decls) |decl| {
                const decl_value = @field(module, decl.name);
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
                            // Generate bindings for this struct
                            const full_name = "pyzig." ++ decl.name;
                            const name_z = full_name ++ "\x00";
                            const binding = wrap_in_python(inner_type, name_z);

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
                        }
                    }
                }
            }
            return 0;
        }
    };
}
