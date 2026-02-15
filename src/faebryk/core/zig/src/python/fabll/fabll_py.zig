const std = @import("std");
const pyzig = @import("pyzig");
const fabll = @import("fabll");
const graph_mod = @import("graph");
const faebryk = @import("faebryk");
const graph_py = @import("../graph/graph_py.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const type_registry = pyzig.type_registry;
const graph = graph_mod.graph;

const StringWrapper = bind.PyObjectWrapper(fabll.literals.String);

var string_type: ?*py.PyTypeObject = null;

fn unwrap_zig_address_ptr(comptime T: type, obj: *py.PyObject) ?*T {
    const zig_address = py.PyObject_GetAttrString(obj, "__zig_address__");
    if (zig_address == null) {
        py.PyErr_SetString(py.PyExc_TypeError, "Expected Zig-backed object with __zig_address__");
        return null;
    }
    defer py.Py_DECREF(zig_address.?);

    const empty_args = py.PyTuple_New(0) orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate argument tuple");
        return null;
    };
    defer py.Py_DECREF(empty_args);

    const address_obj = py.PyObject_Call(zig_address, empty_args, null);
    if (address_obj == null) {
        return null;
    }
    defer py.Py_DECREF(address_obj.?);

    const address_raw = py.PyLong_AsLongLong(address_obj);
    if (py.PyErr_Occurred() != null) {
        return null;
    }
    if (address_raw <= 0) {
        py.PyErr_SetString(py.PyExc_TypeError, "Invalid Zig object address");
        return null;
    }

    const address_usize: usize = @intCast(address_raw);
    return @ptrFromInt(address_usize);
}

fn string_dealloc(self: *py.PyObject) callconv(.c) void {
    const wrapper = @as(*StringWrapper, @ptrCast(@alignCast(self)));
    std.heap.c_allocator.destroy(wrapper.data);

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.c) void, @ptrCast(@alignCast(free_fn_any)));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn wrap_string_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a new Zig fabll String literal instance",
            .args_def = struct {
                g: *py.PyObject,
                tg: *py.PyObject,
                value: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const g_ptr = unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const value_copy = bind.unwrap_str_copy(kwarg_obj.value) orelse return null;

            const literal = fabll.literals.String.create_instance(g_ptr, tg_ptr, value_copy);

            const allocator = std.heap.c_allocator;
            const literal_ptr = allocator.create(fabll.literals.String) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            literal_ptr.* = literal;

            const pyobj = bind.wrap_obj("String", &string_type, StringWrapper, literal_ptr);
            if (pyobj == null) {
                allocator.destroy(literal_ptr);
                return null;
            }

            return pyobj;
        }
    };
}

fn wrap_string_get_value() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_value",
            .doc = "Get literal string value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("String", &string_type, StringWrapper, self) orelse return null;
            return bind.wrap_str(wrapper.data.get_value());
        }
    };
}

fn wrap_string_get_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_instance",
            .doc = "Get bound node instance for this literal",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("String", &string_type, StringWrapper, self) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.node.instance);
        }
    };
}

fn wrap_string(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_string_create_instance(),
        wrap_string_get_value(),
        wrap_string_get_instance(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.String, extra_methods);
    string_type = type_registry.getRegisteredTypeObject("String");

    if (string_type) |typ| {
        typ.tp_dealloc = @ptrCast(&string_dealloc);
    }
}

fn wrap_literals(root: *py.PyObject) void {
    wrap_string(root);

    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.literals.Strings, extra_methods);
    bind.wrap_namespace_struct(root, fabll.literals.Interval, extra_methods);
    bind.wrap_namespace_struct(root, fabll.literals.Numbers, extra_methods);
    bind.wrap_namespace_struct(root, fabll.literals.Booleans, extra_methods);
}

fn wrap_parameters(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.parameters.can_be_operand, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.is_parameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.is_parameter_operatable, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.NumericParameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.StringParameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.BooleanParameter, extra_methods);
}

fn wrap_expressions(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.expressions.is_expression, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Add, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Subtract, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Multiply, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Divide, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Power, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Sqrt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Log, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Sin, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Cos, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Negate, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Round, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Abs, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Floor, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Ceil, extra_methods);
}

fn wrap_units(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.units.IsUnit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.has_unit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.has_display_unit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Meter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Second, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Hour, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ampere, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Kelvin, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.DegreeCelsius, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Volt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.MilliVolt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ohm, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Radian, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Steradian, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Bit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Percent, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ppm, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Dimensionless, extra_methods);
}

var main_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

var main_module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "fabll",
    .m_doc = "Auto-generated Python extension for fabll Zig types",
    .m_size = -1,
    .m_methods = &main_methods,
};

fn add_file_module(
    root: *py.PyObject,
    comptime name: [:0]const u8,
    comptime wrap_fn: fn (*py.PyObject) void,
) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, py.PYTHON_API_VERSION);
    if (module == null) {
        return null;
    }

    wrap_fn(module.?);

    if (py.PyModule_AddObject(root, name, module) < 0) {
        return null;
    }

    return module;
}

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, py.PYTHON_API_VERSION);
    if (module == null) {
        return null;
    }

    _ = add_file_module(module.?, "literals", wrap_literals);
    _ = add_file_module(module.?, "parameters", wrap_parameters);
    _ = add_file_module(module.?, "expressions", wrap_expressions);
    _ = add_file_module(module.?, "units", wrap_units);

    return module;
}
