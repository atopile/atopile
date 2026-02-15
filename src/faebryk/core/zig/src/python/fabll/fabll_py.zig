const pyzig = @import("pyzig");
const fabll = @import("fabll");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;

fn wrap_literals(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.literals.String, extra_methods);
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
