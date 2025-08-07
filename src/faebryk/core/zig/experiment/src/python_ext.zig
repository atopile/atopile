const std = @import("std");
const py = @import("pybindings.zig");
const root = @import("root.zig");
const bind = @import("pyzig.zig");

const TopObject = struct {
    ob_base: py.PyObject_HEAD,
    top: *root.Top,
};

const NestedObject = struct {
    ob_base: py.PyObject_HEAD,
    top: *root.Nested,
};

fn Top_init(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) c_int {
    var a: c_int = undefined;
    var b: c_int = undefined;
    var c: ?*py.PyObject = null;

    var keywords = [_]?[*:0]const u8{ "a", "b", "c", null };

    if (py.PyArg_ParseTupleAndKeywords(args, kwargs, "iiO", &keywords, &a, &b, &c) == 0) {
        return -1;
    }

    const nested_obj: *NestedObject = @ptrCast(@alignCast(c));
    const nested = nested_obj.top.*;

    const top_obj: *TopObject = @ptrCast(@alignCast(self));

    // Allocate memory for the Top data
    const top_data = std.heap.c_allocator.create(root.Top) catch return -1;
    top_data.* = root.Top{ .a = a, .b = b, .c = nested };
    top_obj.top = top_data;

    return 0;
}

fn Nested_init(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) c_int {
    var x: c_int = undefined;
    var y: [*:0]const u8 = undefined;

    var keywords = [_]?[*:0]const u8{ "x", "y", null };

    if (py.PyArg_ParseTupleAndKeywords(args, kwargs, "is", &keywords, &x, &y) == 0) {
        return -1;
    }

    const nested_obj: *NestedObject = @ptrCast(@alignCast(self));

    // Allocate memory for the Nested data
    const nested_data = std.heap.c_allocator.create(root.Nested) catch return -1;
    nested_data.* = root.Nested{ .x = x, .y = std.mem.span(y) };
    nested_obj.top = nested_data;

    return 0;
}

fn Top_sum(self: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    const top_obj: *TopObject = @ptrCast(@alignCast(self));
    const result = top_obj.top.sum();
    return py.PyLong_FromLong(result);
}

// Methods for Top class
var Top_methods = [_]py.PyMethodDef{
    .{
        .ml_name = "sum",
        .ml_meth = @ptrCast(&Top_sum),
        .ml_flags = py.METH_NOARGS,
        .ml_doc = "Return the sum of a and b",
    },
    py.ML_SENTINEL,
};

var Nested_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

// Properties (getters/setters) for Top class
var Top_getset = [_]py.PyGetSetDef{
    bind.int_prop(TopObject, "a"),
    bind.int_prop(TopObject, "b"),
    bind.obj_prop(TopObject, "c", NestedObject, &NestedType),
    py.GS_SENTINEL,
};

var Nested_getset = [_]py.PyGetSetDef{
    bind.int_prop(NestedObject, "x"),
    bind.str_prop(NestedObject, "y"),
    py.GS_SENTINEL,
};

// Type object for Top
var TopType = py.PyTypeObject{
    .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
    .tp_name = "pyzig.Top",
    .tp_basicsize = @sizeOf(TopObject),
    .tp_repr = bind.gen_repr(TopObject),
    .tp_flags = py.Py_TPFLAGS_DEFAULT | py.Py_TPFLAGS_BASETYPE,
    .tp_methods = &Top_methods,
    .tp_getset = &Top_getset,
    .tp_init = Top_init,
};

var NestedType = py.PyTypeObject{
    .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
    .tp_name = "pyzig.Nested",
    .tp_basicsize = @sizeOf(NestedObject),
    .tp_repr = bind.gen_repr(NestedObject),
    .tp_flags = py.Py_TPFLAGS_DEFAULT | py.Py_TPFLAGS_BASETYPE,
    .tp_methods = &Nested_methods,
    .tp_getset = &Nested_getset,
    .tp_init = Nested_init,
};

fn root_add(_: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    var a: c_int = undefined;
    var b: c_int = undefined;

    // Keywords array for argument parsing (must be null-terminated)
    var keywords = [_]?[*:0]const u8{ "a", "b", null };

    // Parse keyword-only arguments: "$ii" means all args are keyword-only
    // The "$" means no positional arguments are allowed
    if (py.PyArg_ParseTupleAndKeywords(args, kwargs, "$ii", &keywords, &a, &b) == 0) {
        return null; // Python will raise TypeError
    }

    // Call the Zig function
    const result = root.add(a, b);

    // Return Python integer
    return py.PyLong_FromLong(result);
}

fn root_get_default_top(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    const top = root.get_default_top(std.heap.c_allocator) catch return null;

    const pyobj = py.PyType_GenericAlloc(&TopType, 0);
    if (pyobj == null) return null;

    const typed_obj: *TopObject = @ptrCast(@alignCast(pyobj));
    typed_obj.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = &TopType };
    typed_obj.top = top;

    return pyobj;
}

// Method definitions
var methods = [_]py.PyMethodDef{
    bind.module_method(root_add, "add"),
    bind.module_method(root_get_default_top, "get_default_top"),
    py.ML_SENTINEL,
};

// =====================================================================================

// Module definition
var module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "pyzig",
    .m_doc = "Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &methods,
};

//const _TopType = gen_type(TopObject, &.{ "a", "b" }, "pyzig.Top");

// Module initialization function
export fn PyInit_pyzig() ?*py.PyObject {
    const T = root.Top;
    // print hello
    std.debug.print("Hello, world!\n", .{});
    inline for (@typeInfo(T).@"struct".decls) |decl| {
        std.debug.print("{s}\n", .{decl.name});
        //const f = @field(root, decl.name);
        //std.debug.print("{}\n", .{@TypeOf(f)});
    }
    inline for (@typeInfo(T).@"struct".fields) |field| {
        std.debug.print("{s}\n", .{field.name});
        //const f = @field(T, field.name);
        //std.debug.print("{}\n", .{@TypeOf(f)});
    }
    //std.debug.print("{}\n", .{@typeInfo(@TypeOf(add)).@"fn"});
    //switch (@typeInfo(root)) {
    //    .Struct => {
    //        std.debug.print("Struct\n", .{});
    //    },
    //    else => {
    //        std.debug.print("Not a struct\n", .{});
    //    },
    //}
    //for (@typeInfo(root).decls) |decl| {
    //    std.debug.print("{}\n", .{decl.name});
    //}

    // Create the module
    const module = py.PyModule_Create2(&module_def, 1013);
    if (module == null) {
        return null;
    }

    // Initialize the Top type
    if (py.PyType_Ready(&TopType) < 0) {
        return null;
    }

    if (py.PyType_Ready(&NestedType) < 0) {
        return null;
    }

    // Add the Top class to the module
    // Increment reference count since PyModule_AddObject steals a reference
    TopType.ob_base.ob_base.ob_refcnt += 1;
    if (py.PyModule_AddObject(module, "Top", @ptrCast(&TopType)) < 0) {
        TopType.ob_base.ob_base.ob_refcnt -= 1;
        return null;
    }

    NestedType.ob_base.ob_base.ob_refcnt += 1;
    if (py.PyModule_AddObject(module, "Nested", @ptrCast(&NestedType)) < 0) {
        NestedType.ob_base.ob_base.ob_refcnt -= 1;
        return null;
    }

    return module;
}
