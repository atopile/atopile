const std = @import("std");
const py = @import("pybindings.zig");
const linked_list = @import("linked_list.zig");

fn isLinkedList(comptime T: type) bool {
    return @typeInfo(T) == .@"struct" and @hasField(T, "first") and @hasField(T, "last") and @hasDecl(T, "Node");
}

// Global registry for type objects to avoid creating duplicates
var type_registry = std.HashMap([]const u8, *py.PyTypeObject, std.hash_map.StringContext, std.hash_map.default_max_load_percentage).init(std.heap.c_allocator);
var registry_mutex = std.Thread.Mutex{};

// Global cache to reuse list wrappers per underlying ArrayList pointer
// No global list wrapper cache

// Helper to register a type object in the global registry
pub fn registerTypeObject(type_name: [*:0]const u8, type_obj: *py.PyTypeObject) void {
    registry_mutex.lock();
    defer registry_mutex.unlock();
    const type_name_slice = std.mem.span(type_name);
    // Make a copy of the string to ensure it lives as long as the HashMap
    const owned_key = std.heap.c_allocator.dupe(u8, type_name_slice) catch return;
    type_registry.put(owned_key, type_obj) catch {
        // If put fails, free the allocated key
        std.heap.c_allocator.free(owned_key);
    };
}

// Helper to get a registered type object by name
fn getRegisteredTypeObject(type_name: [*:0]const u8) ?*py.PyTypeObject {
    registry_mutex.lock();
    defer registry_mutex.unlock();
    const type_name_slice = std.mem.span(type_name);
    return type_registry.get(type_name_slice);
}

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

pub fn int_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime is_signed: bool) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            // Check if the wrapper has 'data' field (new style) or 'top' field (old style)
            const has_data = @hasField(struct_type, "data");
            if (is_signed) {
                const v: c_long = @intCast(if (has_data) @field(obj.data.*, field_name_str) else @field(obj.top.*, field_name_str));
                return py.PyLong_FromLong(v);
            } else {
                const v: c_ulonglong = @intCast(if (has_data) @field(obj.data.*, field_name_str) else @field(obj.top.*, field_name_str));
                return py.PyLong_FromUnsignedLongLong(v);
            }
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) {
                return -1;
            }

            // Accept both positive/negative; cast depending on signedness
            const new_val_signed = py.PyLong_AsLongLong(value);
            const new_val_unsigned: c_ulonglong = if (new_val_signed < 0) 0 else @intCast(new_val_signed);
            const has_data = @hasField(struct_type, "data");
            if (has_data) {
                if (is_signed) @field(obj.data.*, field_name_str) = @intCast(new_val_signed) else @field(obj.data.*, field_name_str) = @intCast(new_val_unsigned);
            } else {
                if (is_signed) @field(obj.top.*, field_name_str) = @intCast(new_val_signed) else @field(obj.top.*, field_name_str) = @intCast(new_val_unsigned);
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
            // Use PyUnicode_FromStringAndSize to handle non-null-terminated strings
            return py.PyUnicode_FromStringAndSize(enum_str.ptr, @intCast(enum_str.len));
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

    // For struct types, get the type name for registry lookup
    const child_info = @typeInfo(ChildType);
    const type_name_for_registry = if (child_info == .@"struct")
        @typeName(ChildType) ++ "\x00"
    else
        "";

    // Note: do not precompute a potentially-void NestedBinding at file scope.
    // Create the binding only inside the struct branch to avoid referencing fields on 'void'.

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

                // Try to get the registered type object first
                if (getRegisteredTypeObject(type_name_for_registry)) |registered_obj| {
                    nested_type_obj = registered_obj;
                } else {
                    // Fallback: create a new binding if not found in registry
                    const Binding = wrap_in_python(ChildType, type_name_for_registry);
                    const result = py.PyType_Ready(&Binding.type_object);
                    if (result < 0) {
                        @panic("Failed to initialize optional nested type");
                    }
                    nested_type_obj = &Binding.type_object;
                    // Register the newly created type for future reuse
                    registerTypeObject(type_name_for_registry, nested_type_obj.?);
                }
            }

            return nested_type_obj.?;
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
                        const type_obj = getNestedTypeObj();
                        // Create a new Python object for the nested struct
                        const pyobj = py.PyType_GenericAlloc(type_obj, 0);
                        if (pyobj == null) return null;

                        const NestedWrapper = PyObjectWrapper(ChildType);
                        const wrapper: *NestedWrapper = @ptrCast(@alignCast(pyobj));
                        // Do not overwrite ob_base set by GenericAlloc
                        // Store a pointer to the original value instead of making a copy
                        // This allows mutations to be reflected in the original struct
                        wrapper.data = &@field(obj.data.*, field_name_str).?;

                        return pyobj;
                    },
                    .@"enum" => {
                        // Convert enum to string
                        const enum_str = @tagName(v);
                        // Use PyUnicode_FromStringAndSize to handle non-null-terminated strings
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
                        // CRITICAL FIX: Duplicate Python string instead of storing pointer to Python's buffer
                        // Python can move or free its internal string buffer during GC
                        const str_slice = std.mem.span(new_val.?);
                        const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch return -1;
                        @field(obj.data.*, field_name_str) = str_copy;
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
                    // Update the optional field to point to the new struct data
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

// Property for linked_list fields
pub fn linked_list_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime ChildType: type) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const child_info = @typeInfo(ChildType);

    const getter = struct {
        fn getNestedTypeObj() *py.PyTypeObject {
            if (child_info != .@"struct") unreachable;
            const type_name_for_registry = @typeName(ChildType) ++ "\x00";
            var nested_type_obj: ?*py.PyTypeObject = null;
            if (getRegisteredTypeObject(type_name_for_registry)) |registered_obj| {
                nested_type_obj = registered_obj;
            } else {
                const NestedBinding = wrap_in_python(ChildType, type_name_for_registry);
                const result = py.PyType_Ready(&NestedBinding.type_object);
                if (result < 0) @panic("Failed to initialize linked_list nested type");
                nested_type_obj = &NestedBinding.type_object;
                registerTypeObject(type_name_for_registry, nested_type_obj.?);
            }
            return nested_type_obj.?;
        }
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            const list_ptr = &@field(obj.data.*, field_name_str);
            const element_type_obj = if (child_info == .@"struct") getNestedTypeObj() else null;
            return linked_list.createMutableList(ChildType, list_ptr, element_type_obj);
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) return -1;

            // Generic: accept any Python sequence and build a DoublyLinkedList
            const LL = std.DoublyLinkedList(ChildType);
            const NodeType = LL.Node;
            var ll = LL{ .first = null, .last = null };

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
                        const nested = @as(*PyObjectWrapper(ChildType), @ptrCast(@alignCast(item)));
                        node.* = NodeType{ .data = nested.data.*, .prev = null, .next = null };
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
                        node.* = NodeType{ .data = ev, .prev = null, .next = null };
                    },
                    .int => {
                        const v = py.PyLong_AsLong(item);
                        if (v == -1 and py.PyErr_Occurred() != null) {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        }
                        node.* = NodeType{ .data = @intCast(v), .prev = null, .next = null };
                    },
                    .float => {
                        const v = py.PyFloat_AsDouble(item);
                        if (v == -1.0 and py.PyErr_Occurred() != null) {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        }
                        node.* = NodeType{ .data = @floatCast(v), .prev = null, .next = null };
                    },
                    .bool => {
                        const v = py.PyObject_IsTrue(item);
                        if (v == -1) {
                            std.heap.c_allocator.destroy(node);
                            return -1;
                        }
                        node.* = NodeType{ .data = (v == 1), .prev = null, .next = null };
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
                            node.* = NodeType{ .data = dup, .prev = null, .next = null };
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

                if (ll.last) |last| {
                    last.next = node;
                    node.prev = last;
                } else ll.first = node;
                ll.last = node;
            }

            @field(obj.data.*, field_name_str) = ll;
            return 0;
        }
    }.impl;

    return .{ .name = field_name, .get = getter, .set = setter };
}

// Property for struct fields
pub fn struct_prop(comptime struct_type: type, comptime field_name: [*:0]const u8, comptime FieldType: type) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);

    // Use the type name for registry lookup
    const type_name_for_registry = @typeName(FieldType) ++ "\x00";

    // Generate a Python binding for the nested struct type
    // We need to create this at comptime so it can be properly initialized
    const NestedBinding = wrap_in_python(FieldType, type_name_for_registry);

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

                // Try to get the registered type object first
                if (getRegisteredTypeObject(type_name_for_registry)) |registered_obj| {
                    nested_type_obj = registered_obj;
                } else {
                    // Fallback: create a new binding if not found in registry
                    const result = py.PyType_Ready(&NestedBinding.type_object);
                    if (result < 0) {
                        @panic("Failed to initialize nested type");
                    }
                    nested_type_obj = &NestedBinding.type_object;
                    // Register the newly created type for future reuse
                    registerTypeObject(type_name_for_registry, nested_type_obj.?);
                }
            }

            return nested_type_obj.?;
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
                                            const nested_wrapper = @as(*PyObjectWrapper(ptr.child), @ptrCast(@alignCast(item)));
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
                                                        const nested_wrapper = @as(*PyObjectWrapper(opt.child), @ptrCast(@alignCast(item)));
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
                            if (comptime isLinkedList(field.type)) {
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
                                            const nested = @as(*PyObjectWrapper(ChildType), @ptrCast(@alignCast(item)));
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
                                const nested_wrapper = @as(*PyObjectWrapper(field.type), @ptrCast(@alignCast(value)));
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
            py.PyMethodDef{
                .ml_name = "__zig_address__",
                .ml_meth = @ptrCast(&get_zig_address_func),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the address of the Zig struct",
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

        // Return a stable identifier for the Python-side wrapper
        pub fn get_zig_address_func(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = args; // No arguments needed
            const wrapper_obj: *WrapperType = @ptrCast(@alignCast(self));
            // Use underlying Zig struct address (stable if buffer not reallocated)
            return py.PyLong_FromUnsignedLongLong(@intFromPtr(wrapper_obj.data));
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
        .int => |int_info| return int_prop(WrapperType, field_name, int_info.signedness == .signed),
        .float => return float_prop(WrapperType, field_name),
        .bool => return bool_prop(WrapperType, field_name),
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child == u8 and ptr.is_const) {
                return str_prop(WrapperType, field_name);
            }
            // Temporary: expose unsupported pointer fields as non-accessible properties
            return .{ .name = field_name, .get = null, .set = null };
        },
        .optional => |opt| return optional_prop(WrapperType, field_name, opt.child),
        .@"struct" => if (isLinkedList(FieldType)) {
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

                            // Register the type object globally for reuse
                            const type_name = @typeName(inner_type);
                            const type_name_z = type_name ++ "\x00";
                            registerTypeObject(type_name_z, &binding.type_object);
                        }
                    }
                }
            }
            return 0;
        }
    };
}
