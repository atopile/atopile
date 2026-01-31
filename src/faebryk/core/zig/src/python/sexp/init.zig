const pyzig = @import("pyzig");
const sexp = @import("sexp_py.zig");

const py = pyzig.pybindings;

// Dedicated entrypoint for the sexp-only Python extension.
export fn PyInit_pyzig_sexp() ?*py.PyObject {
    return sexp.make_python_module();
}
