pub const std = @import("std");
pub const root = @import("root.zig");

/// Python C API declarations
pub const PyObject = opaque {};

/// Defines a single method in the module
pub const PyMethodDef = extern struct {
    /// Method name as it appears in Python
    ml_name: ?[*:0]const u8,
    /// Pointer to the C function implementing the method
    ml_meth: ?*const anyopaque,
    /// How Python should call the function (METH_VARARGS = accepts args tuple)
    /// Possible values for ml_flags:
    /// - METH_VARARGS: Function accepts positional arguments.
    /// - METH_KEYWORDS: Function accepts keyword arguments.
    /// - METH_NOARGS: Function does not accept any arguments.
    /// - METH_O: Function accepts a single object argument.
    /// - METH_CLASS: Function is a class method.
    /// - METH_STATIC: Function is a static method.
    /// - METH_COEXIST: Function can coexist with other methods of the same name.
    ml_flags: c_int,
    /// Docstring for the method
    ml_doc: ?[*:0]const u8 = null,
};

// Method flags
pub const METH_VARARGS = 0x0001; // Function accepts positional arguments
pub const METH_KEYWORDS = 0x0002; // Function accepts keyword arguments
pub const METH_NOARGS = 0x0004; // Function does not accept any arguments
pub const METH_O = 0x0008; // Function accepts a single object argument
pub const METH_CLASS = 0x0010; // Function is a class method
pub const METH_STATIC = 0x0020; // Function is a static method
pub const METH_COEXIST = 0x0040; // Function can coexist with other methods of the same name

/// Defines the module itself
pub const PyModuleDef = extern struct {
    /// Required header with refcount and type info
    m_base: PyModuleDef_HEAD_INIT,
    /// Module name (what you import in Python)
    m_name: [*:0]const u8,
    /// Module-level docstring
    m_doc: [*:0]const u8,
    /// Per-module state size (-1 = no state)
    m_size: isize,
    /// Array of methods this module provides
    m_methods: [*]PyMethodDef,
    /// Advanced features (usually null)
    m_slots: ?*anyopaque = null,
    /// Advanced features (usually null)
    m_traverse: ?*anyopaque = null,
    /// Advanced features (usually null)
    m_clear: ?*anyopaque = null,
    /// Advanced features (usually null)
    m_free: ?*anyopaque = null,
};

pub const PyModuleDef_HEAD_INIT = extern struct {
    ob_base: PyObject_HEAD = .{},
    m_init: ?*anyopaque = null,
    m_index: isize = 0,
    m_copy: ?*anyopaque = null,
};

pub const PyObject_HEAD = extern struct {
    ob_refcnt: isize = 1,
    ob_type: ?*anyopaque = null,
};

// External Python C API functions

/// Parses arguments from Python into C types
/// Format string characters:
///   "i" = int (c_int)
///   "l" = long (c_long)
///   "f" = float (c_float)
///   "d" = double (c_double)
///   "s" = string (const char*)
///   "b" = bool/byte (unsigned char)
///   "O" = PyObject* (any Python object)
///   "|" = following args are optional
///   "$" = following args are keyword-only (no positional)
///   ":" = function name follows (for error messages)
/// Example: "ii" = two required integers
/// Example: "$ii" = two required keyword-only integers
pub extern fn PyArg_ParseTuple(args: ?*PyObject, format: [*:0]const u8, ...) c_int;

/// Parses both positional and keyword arguments from Python
/// args: positional arguments tuple
/// kwargs: keyword arguments dictionary
/// format: format string for arguments
/// keywords: null-terminated array of keyword names
pub extern fn PyArg_ParseTupleAndKeywords(args: ?*PyObject, kwargs: ?*PyObject, format: [*:0]const u8, keywords: [*]?[*:0]const u8, ...) c_int;

/// Creates a new module object
/// apiver: Python API version (1013 for Python 3.13)
pub extern fn PyModule_Create2(def: *const PyModuleDef, apiver: c_int) ?*PyObject;

/// Type-related functions
pub extern fn PyType_Ready(type: *PyTypeObject) c_int;
pub extern fn PyModule_AddObject(module: ?*PyObject, name: [*:0]const u8, value: ?*PyObject) c_int;
pub extern fn _Py_Dealloc(op: *PyObject) void;
pub extern fn PyObject_GenericGetAttr(obj: ?*PyObject, name: ?*PyObject) ?*PyObject;
pub extern fn PyObject_GenericSetAttr(obj: ?*PyObject, name: ?*PyObject, value: ?*PyObject) c_int;
pub extern fn PyType_GenericAlloc(type: *PyTypeObject, nitems: isize) ?*PyObject;
pub extern fn PyType_GenericNew(type: *PyTypeObject, args: ?*PyObject, kwargs: ?*PyObject) ?*PyObject;

/// Member descriptor for struct fields
pub const PyMemberDef = extern struct {
    name: ?[*:0]const u8,
    type: c_int,
    offset: isize,
    flags: c_int,
    doc: ?[*:0]const u8,
};

/// Getter/Setter descriptor for properties
pub const PyGetSetDef = extern struct {
    name: ?[*:0]const u8,
    get: ?*const fn (?*PyObject, ?*anyopaque) callconv(.C) ?*PyObject,
    set: ?*const fn (?*PyObject, ?*PyObject, ?*anyopaque) callconv(.C) c_int,
    doc: ?[*:0]const u8 = null,
    closure: ?*anyopaque = null,
};

/// Member types
pub const T_INT = 1;
pub const T_LONG = 2;
pub const T_FLOAT = 3;
pub const T_DOUBLE = 4;

/// Member flags
pub const READONLY = 1;

/// Python type object structure (simplified)
pub const PyTypeObject = extern struct {
    ob_base: PyVarObject,
    tp_name: [*:0]const u8,
    tp_basicsize: isize,
    tp_itemsize: isize = 0,
    tp_dealloc: ?*const fn (*PyObject) callconv(.C) void = null,
    tp_vectorcall_offset: isize = 0,
    tp_getattr: ?*anyopaque = null,
    tp_setattr: ?*anyopaque = null,
    tp_as_async: ?*anyopaque = null,
    tp_repr: ?*const fn (?*PyObject) callconv(.C) ?*PyObject = null,
    tp_as_number: ?*anyopaque = null,
    tp_as_sequence: ?*anyopaque = null,
    tp_as_mapping: ?*anyopaque = null,
    tp_hash: ?*anyopaque = null,
    tp_call: ?*anyopaque = null,
    tp_str: ?*const fn (?*PyObject) callconv(.C) ?*PyObject = null,
    tp_getattro: ?*const fn (?*PyObject, ?*PyObject) callconv(.C) ?*PyObject = null,
    tp_setattro: ?*const fn (?*PyObject, ?*PyObject, ?*PyObject) callconv(.C) c_int = null,
    tp_as_buffer: ?*anyopaque = null,
    tp_flags: c_ulong,
    tp_doc: ?[*:0]const u8 = null,
    tp_traverse: ?*anyopaque = null,
    tp_clear: ?*anyopaque = null,
    tp_richcompare: ?*anyopaque = null,
    tp_weaklistoffset: isize = 0,
    tp_iter: ?*anyopaque = null,
    tp_iternext: ?*anyopaque = null,
    tp_methods: ?[*]PyMethodDef = null,
    tp_members: ?[*]PyMemberDef = null,
    tp_getset: ?[*]PyGetSetDef = null,
    tp_base: ?*PyTypeObject = null,
    tp_dict: ?*PyObject = null,
    tp_descr_get: ?*anyopaque = null,
    tp_descr_set: ?*anyopaque = null,
    tp_dictoffset: isize = 0,
    tp_init: ?*const fn (?*PyObject, ?*PyObject, ?*PyObject) callconv(.C) c_int = null,
    tp_alloc: ?*const fn (*PyTypeObject, isize) callconv(.C) ?*PyObject = PyType_GenericAlloc,
    tp_new: ?*const fn (*PyTypeObject, ?*PyObject, ?*PyObject) callconv(.C) ?*PyObject = PyType_GenericNew,
    tp_free: ?*anyopaque = null,
    tp_is_gc: ?*anyopaque = null,
    tp_bases: ?*PyObject = null,
    tp_mro: ?*PyObject = null,
    tp_cache: ?*PyObject = null,
    tp_subclasses: ?*anyopaque = null,
    tp_weaklist: ?*anyopaque = null,
    tp_del: ?*anyopaque = null,
    tp_version_tag: c_uint = 0,
    tp_finalize: ?*anyopaque = null,
    tp_vectorcall: ?*anyopaque = null,
};

pub const PyVarObject = extern struct {
    ob_base: PyObject_HEAD,
    ob_size: isize,
};

/// Type flags
pub const Py_TPFLAGS_DEFAULT = 1 << 0;
pub const Py_TPFLAGS_BASETYPE = 1 << 10;
pub const Py_TPFLAGS_HAVE_GC = 1 << 14;

pub const ML_SENTINEL = PyMethodDef{
    .ml_name = null,
    .ml_meth = null,
    .ml_flags = 0,
    .ml_doc = null,
};

pub const GS_SENTINEL = PyGetSetDef{
    .name = null,
    .get = null,
    .set = null,
};

// PyObject conversions
pub extern fn PyLong_FromLong(value: c_long) ?*PyObject;
pub extern fn PyLong_AsLong(obj: ?*PyObject) c_long;
pub extern fn PyLong_AsLongLong(obj: ?*PyObject) c_longlong;
pub extern fn PyUnicode_FromString(str: [*:0]const u8) ?*PyObject;
pub extern fn PyUnicode_AsUTF8(obj: ?*PyObject) ?[*:0]const u8;
