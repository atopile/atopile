const std = @import("std");
const root = @import("root.zig");
const py = @import("pybindings.zig");

const Method = fn (_: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject;

pub fn module_method(comptime method: Method, comptime name: [*:0]const u8) py.PyMethodDef {
    return .{
        .ml_name = name,
        .ml_meth = @ptrCast(&method),
        .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
    };
}

pub fn printStruct(comptime T: type, value: T) void {
    const info = @typeInfo(T);

    switch (info) {
        .Struct => |s| {
            std.debug.print("{} {{\n", .{@typeName(T)});
            inline for (s.fields) |field| {
                const field_value = @field(value, field.name);
                std.debug.print("  {}: {}\n", .{ field.name, field_value });
            }
            std.debug.print("}}\n", .{});
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
            const str = std.fmt.bufPrintZ(&buf, "{}", .{obj.top}) catch {
                return null;
            };
            return py.PyUnicode_FromString(str.ptr);
        }
    }.impl;

    return repr;
}

pub fn int_prop(comptime struct_type: type, comptime field_name: [*:0]const u8) py.PyGetSetDef {
    const field_name_str = std.mem.span(field_name);
    const getter = struct {
        fn impl(self: ?*py.PyObject, _: ?*anyopaque) callconv(.C) ?*py.PyObject {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            return py.PyLong_FromLong(@field(obj.top, field_name_str));
        }
    }.impl;

    const setter = struct {
        fn impl(self: ?*py.PyObject, value: ?*py.PyObject, _: ?*anyopaque) callconv(.C) c_int {
            const obj: *struct_type = @ptrCast(@alignCast(self));
            if (value == null) {
                // TODO: set proper error - for now just return error
                return -1;
            }

            const new_val = py.PyLong_AsLong(value);
            @field(obj.top, field_name_str) = @intCast(new_val);
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
