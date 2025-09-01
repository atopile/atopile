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
                    const field_str = try std.fmt.bufPrintZ(buf[pos..], "  {s}: {s}\n", .{ field.name, field_value });
                    pos += field_str.len;
                } else if (is_struct) {
                    // Handle struct fields recursively
                    const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: ", .{field.name});
                    pos += field_header.len;

                    // Recursively print the struct, adjusting indentation
                    var temp_buf: [1024]u8 = undefined;
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
                    // Handle other field types
                    const field_str = try std.fmt.bufPrintZ(buf[pos..], "  {s}: {}\n", .{ field.name, field_value });
                    pos += field_str.len;
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

pub fn gen_type(comptime struct_type: type, comptime field_names: []const [*:0]const u8, comptime name: [*:0]const u8) TX {
    const tx: TX = .{
        .getset = .{
            int_prop(struct_type, field_names[0]),
            int_prop(struct_type, field_names[1]),
            py.GS_SENTINEL,
        },
        .typeobj = undefined,
    };

    tx.typeobj = py.PyTypeObject{
        .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
        .tp_name = name,
        .tp_basicsize = @sizeOf(struct_type),
        .tp_repr = gen_repr(struct_type),
        .tp_flags = py.Py_TPFLAGS_DEFAULT | py.Py_TPFLAGS_BASETYPE,
        //.tp_methods = &Top_methods,
        .tp_getset = &tx.getset,
        //.tp_init = Top_init,
    };

    return tx;
}

pub fn gen_repr(comptime struct_type: type) ?*const fn (?*py.PyObject) callconv(.C) ?*py.PyObject {
    const repr = struct {
        fn impl(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            var buf: [256]u8 = undefined;
            const out = printStruct(obj.top.*, &buf) catch {
                return null;
            };
            return py.PyUnicode_FromString(out);
        }
    }.impl;

    return repr;
}

pub fn int_prop(comptime struct_type: type, comptime field_name: [*:0]const u8) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            return py.PyLong_FromLong(@field(obj.top.*, field_name_str));
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) {
                return -1;
            }

            const new_val = py.PyLong_AsLong(value);
            @field(obj.top.*, field_name_str) = @intCast(new_val);
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
            const val: []const u8 = @field(obj.top.*, field_name_str);
            // FIXME: this assumes zig literal (0-terminated), be careful!
            const cstr: [*:0]const u8 = @ptrCast(val.ptr);
            return py.PyUnicode_FromString(cstr);
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

            @field(obj.top.*, field_name_str) = std.mem.span(new_val.?);
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
            const zigval_ptr = &@field(obj.top.*, field_name_str);

            // Create a simple Python object wrapper
            const pyobj = py.PyType_GenericAlloc(type_obj, 0);
            if (pyobj == null) return null;

            const typed_obj: *PType = @ptrCast(@alignCast(pyobj));

            // Initialize the Python object header
            typed_obj.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };

            // Store the pointer to the nested data
            typed_obj.top = zigval_ptr;

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
            @field(obj.top.*, field_name_str) = pyval.top.*;
            return 0;
        }
    }.impl;

    return .{
        .name = field_name,
        .get = getter,
        .set = setter,
    };
}

const TX = struct {
    getset: [3]py.PyGetSetDef,
    typeobj: ?py.PyTypeObject,
};
