pub const std = @import("std");

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
pub extern fn PyModule_GetDict(module: ?*PyObject) ?*PyObject;
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
pub extern fn PyLong_FromUnsignedLongLong(value: c_ulonglong) ?*PyObject;
pub extern fn PyLong_AsLong(obj: ?*PyObject) c_long;
pub extern fn PyLong_AsLongLong(obj: ?*PyObject) c_longlong;
pub extern fn PyUnicode_FromString(str: [*:0]const u8) ?*PyObject;
pub extern fn PyUnicode_FromStringAndSize(str: [*c]const u8, size: isize) ?*PyObject;
pub extern fn PyUnicode_AsUTF8(obj: ?*PyObject) ?[*:0]const u8;

// Python constants
pub extern var _Py_NoneStruct: PyObject;

pub fn Py_None() *PyObject {
    return &_Py_NoneStruct;
}

// Reference counting - these are macros in Python, so we implement them inline
pub inline fn Py_INCREF(obj: *PyObject) void {
    // In CPython, Py_INCREF is a macro that increments ob_refcnt
    // Since PyObject is opaque, we can't directly access ob_refcnt
    // Instead, just don't increment for now - Python manages the refcount
    _ = obj;
}

pub inline fn Py_DECREF(obj: *PyObject) void {
    // Similarly for DECREF
    _ = obj;
}

// List type for inheritance
pub extern var PyList_Type: PyTypeObject;

// Object type checking - Py_TYPE is a macro, so we need to implement it
// In CPython, Py_TYPE(o) is defined as (((PyObject*)(o))->ob_type)
pub fn Py_TYPE(obj: ?*PyObject) ?*PyTypeObject {
    if (obj == null) return null;

    // Cast to a struct that matches PyObject's layout to access ob_type
    const PyObjectLayout = extern struct {
        ob_refcnt: isize,
        ob_type: ?*PyTypeObject,
    };

    const obj_layout: *PyObjectLayout = @ptrCast(@alignCast(obj));
    return obj_layout.ob_type;
}

// Error handling
pub extern fn PyErr_SetString(exception: *PyObject, message: [*:0]const u8) void;
pub extern fn PyErr_Clear() void;
pub extern fn PyErr_Occurred() ?*PyObject;

// System functions
pub extern fn PySys_WriteStderr(format: [*:0]const u8, ...) c_int;

// Common exception types
pub extern var PyExc_TypeError: *PyObject;
pub extern var PyExc_ValueError: *PyObject;
pub extern var PyExc_NotImplementedError: *PyObject;
pub extern var PyExc_ImportError: *PyObject;
pub extern var PyExc_MemoryError: *PyObject;
pub extern var PyExc_AttributeError: *PyObject;

// Additional Python C API functions for generic init
pub extern fn PyTuple_Size(tuple: ?*PyObject) isize;
pub extern fn PyTuple_New(size: isize) ?*PyObject;
// PyTuple_SET_ITEM is a macro, so we use SetItem instead
pub extern fn PyTuple_SetItem(tuple: ?*PyObject, pos: isize, item: ?*PyObject) c_int;
pub extern fn PyTuple_GetItem(tuple: ?*PyObject, pos: isize) ?*PyObject;
pub extern fn PyDict_GetItemString(dict: ?*PyObject, key: [*:0]const u8) ?*PyObject;
pub extern fn PyDict_New() ?*PyObject;
pub extern fn PyDict_SetItemString(dict: ?*PyObject, key: [*:0]const u8, value: ?*PyObject) c_int;
pub extern fn PyFloat_FromDouble(value: f64) ?*PyObject;
pub extern fn PyFloat_AsDouble(obj: ?*PyObject) f64;
pub extern fn PyObject_IsTrue(obj: ?*PyObject) c_int;
pub extern fn PyList_New(size: isize) ?*PyObject;
pub extern fn PyList_SetItem(list: ?*PyObject, index: isize, item: ?*PyObject) c_int;
pub extern fn PyList_Size(list: ?*PyObject) isize;
pub extern fn PyList_GetItem(list: ?*PyObject, index: isize) ?*PyObject;

// PyList_Check is a macro in Python's C API, we need to implement it ourselves
// We can use PyObject_IsInstance or just check with PyList_Size
pub fn PyList_Check(obj: ?*PyObject) c_int {
    if (obj == null) return 0;
    // A simple way to check if it's a list is to try PyList_Size
    // If it returns >= 0, it's a list. If it returns -1, it's not.
    const size = PyList_Size(obj);
    if (size >= 0) return 1;
    // Clear the error that PyList_Size set
    PyErr_Clear();
    return 0;
}
pub extern fn PyImport_GetModuleDict() ?*PyObject;
pub extern fn PyImport_AddModule(name: [*:0]const u8) ?*PyObject;
pub extern fn PyImport_ImportModule(name: [*:0]const u8) ?*PyObject;
pub extern fn PyObject_GetAttrString(obj: ?*PyObject, name: [*:0]const u8) ?*PyObject;
pub extern fn PyObject_SetAttrString(obj: ?*PyObject, name: [*:0]const u8, value: ?*PyObject) c_int;
pub extern fn PyObject_Call(callable: ?*PyObject, args: ?*PyObject, kwargs: ?*PyObject) ?*PyObject;
// Python booleans are singleton objects
pub extern var _Py_TrueStruct: PyObject;
pub extern var _Py_FalseStruct: PyObject;

pub fn Py_True() *PyObject {
    return &_Py_TrueStruct;
}

pub fn Py_False() *PyObject {
    return &_Py_FalseStruct;
}

// Exception types
pub extern var PyExc_IndexError: *PyObject;

// Rich comparison
pub extern fn PyObject_RichCompareBool(o1: ?*PyObject, o2: ?*PyObject, opid: c_int) c_int;
pub const Py_EQ: c_int = 2;

// Sequence protocol for lists
pub const PySequenceMethods = extern struct {
    sq_length: ?*const fn (?*PyObject) callconv(.C) isize = null,
    sq_concat: ?*const fn (?*PyObject, ?*PyObject) callconv(.C) ?*PyObject = null,
    sq_repeat: ?*const fn (?*PyObject, isize) callconv(.C) ?*PyObject = null,
    sq_item: ?*const fn (?*PyObject, isize) callconv(.C) ?*PyObject = null,
    sq_ass_item: ?*const fn (?*PyObject, isize, ?*PyObject) callconv(.C) c_int = null,
    sq_contains: ?*const fn (?*PyObject, ?*PyObject) callconv(.C) c_int = null,
    sq_inplace_concat: ?*const fn (?*PyObject, ?*PyObject) callconv(.C) ?*PyObject = null,
    sq_inplace_repeat: ?*const fn (?*PyObject, isize) callconv(.C) ?*PyObject = null,
};

// Additional Python ABC registration functions
pub extern fn PyObject_IsInstance(obj: ?*PyObject, cls: ?*PyObject) c_int;
pub extern fn PyObject_GetIter(obj: ?*PyObject) ?*PyObject;

// Sequence protocol functions
pub extern fn PySequence_Size(obj: ?*PyObject) isize;
pub extern fn PySequence_GetItem(obj: ?*PyObject, index: isize) ?*PyObject;
