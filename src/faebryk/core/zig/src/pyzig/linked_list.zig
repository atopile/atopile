const std = @import("std");
const py = @import("pybindings.zig");
const pyzig_mod = @import("pyzig.zig");

pub fn MutableLinkedList(comptime T: type) type {
    return struct {
        const Self = @This();
        ob_base: py.PyObject_HEAD,
        list: *std.DoublyLinkedList(T),
        element_type_obj: ?*py.PyTypeObject,

        fn create(list_ptr: *std.DoublyLinkedList(T), element_type_obj: ?*py.PyTypeObject) ?*py.PyObject {
            const obj = py.PyType_GenericAlloc(&type_object, 0);
            if (obj == null) return null;
            const self: *Self = @ptrCast(@alignCast(obj));
            self.list = list_ptr;
            self.element_type_obj = element_type_obj;
            return obj;
        }

        fn count(self: *Self) usize {
            return self.list.len;
        }
        fn nodeAt(self: *Self, idx: usize) ?*std.DoublyLinkedList(T).Node {
            var i: usize = 0;
            var it = self.list.first;
            while (it) |n| : (it = n.next) {
                if (i == idx) return n;
                i += 1;
            }
            return null;
        }

        fn sq_length(self: ?*py.PyObject) callconv(.C) isize {
            const s: *Self = @ptrCast(@alignCast(self));
            return @intCast(s.count());
        }
        fn sq_item(self: ?*py.PyObject, index: isize) callconv(.C) ?*py.PyObject {
            const s: *Self = @ptrCast(@alignCast(self));
            const len: isize = @intCast(s.count());
            const actual = if (index < 0) len + index else index;
            if (actual < 0 or actual >= len) {
                py.PyErr_SetString(py.PyExc_IndexError, "list index out of range");
                return null;
            }
            const n = s.nodeAt(@intCast(actual)) orelse return null;
            return s.convertZigToPython(&n.data);
        }
        fn list_getitem(self: ?*py.PyObject, index: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const idx = py.PyLong_AsLong(index);
            if (py.PyErr_Occurred() != null) return null;
            return sq_item(self, idx);
        }

        fn list_append(self: ?*py.PyObject, value: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const s: *Self = @ptrCast(@alignCast(self));
            const Node = std.DoublyLinkedList(T).Node;
            const node = std.heap.c_allocator.create(Node) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "append failed");
                return null;
            };
            node.* = Node{ .data = undefined };
            if (!s.convertPythonToZig(value, &node.data)) {
                std.heap.c_allocator.destroy(node);
                return null;
            }
            s.list.append(node);
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
        fn list_insert(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const s: *Self = @ptrCast(@alignCast(self));
            var index: isize = 0;
            var item: ?*py.PyObject = null;
            if (py.PyArg_ParseTuple(args, "iO", &index, &item) == 0) return null;
            const len: isize = @intCast(s.count());
            var actual: isize = if (index < 0) len + index else index;
            if (actual < 0) actual = 0;
            if (actual > len) actual = len;
            const Node = std.DoublyLinkedList(T).Node;
            const node = std.heap.c_allocator.create(Node) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "insert failed");
                return null;
            };
            node.* = Node{ .data = undefined };
            if (!s.convertPythonToZig(item, &node.data)) {
                std.heap.c_allocator.destroy(node);
                return null;
            }
            if (actual == len) {
                s.list.append(node);
            } else if (actual == 0) {
                s.list.prepend(node);
            } else {
                const before = s.nodeAt(@intCast(actual)) orelse {
                    std.heap.c_allocator.destroy(node);
                    py.PyErr_SetString(py.PyExc_IndexError, "index out of range");
                    return null;
                };
                s.list.insertBefore(before, node);
            }
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
        fn list_clear(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = args;
            const s: *Self = @ptrCast(@alignCast(self));
            while (s.list.pop()) |node| {
                std.heap.c_allocator.destroy(node);
            }
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
        fn list_remove(self: ?*py.PyObject, item: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const s: *Self = @ptrCast(@alignCast(self));
            const Wrap = pyzig_mod.PyObjectWrapper(T);
            const w: *Wrap = @ptrCast(@alignCast(item));
            var it = s.list.first;
            while (it) |n| : (it = n.next) {
                if (&n.data == w.data) {
                    s.list.remove(n);
                    std.heap.c_allocator.destroy(n);
                    const none = py.Py_None();
                    py.Py_INCREF(none);
                    return none;
                }
            }
            py.PyErr_SetString(py.PyExc_ValueError, "list.remove(x): x not in list");
            return null;
        }
        fn list_len(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const s: *Self = @ptrCast(@alignCast(self));
            return py.PyLong_FromLong(@intCast(s.count()));
        }
        fn list_iter(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const s: *Self = @ptrCast(@alignCast(self));
            const py_list = py.PyList_New(@intCast(s.count()));
            if (py_list == null) return null;
            var i: usize = 0;
            var it = s.list.first;
            while (it) |n| : (it = n.next) {
                const py_item = s.convertZigToPython(&n.data);
                if (py_item == null) {
                    py.Py_DECREF(py_list.?);
                    return null;
                }
                _ = py.PyList_SetItem(py_list, @intCast(i), py_item);
                i += 1;
            }
            const itobj = py.PyObject_GetIter(py_list);
            py.Py_DECREF(py_list.?);
            return itobj;
        }
        fn list_pop(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const s: *Self = @ptrCast(@alignCast(self));
            var index: isize = 0;
            if (py.PyArg_ParseTuple(args, "i", &index) == 0) return null;
            const len: isize = @intCast(s.count());
            var actual: isize = if (index < 0) len + index else index;
            if (actual < 0) actual = 0;
            if (actual >= len) actual = len - 1;
            const n = s.nodeAt(@intCast(actual)) orelse {
                py.PyErr_SetString(py.PyExc_IndexError, "index out of range");
                return null;
            };
            s.list.remove(n);
            std.heap.c_allocator.destroy(n);
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }

        fn convertZigToPython(self: *Self, item: *T) ?*py.PyObject {
            const ti = @typeInfo(T);
            switch (ti) {
                .int => return py.PyLong_FromLong(@intCast(item.*)),
                .float => return py.PyFloat_FromDouble(@floatCast(item.*)),
                .bool => {
                    const r = if (item.*) py.Py_True() else py.Py_False();
                    py.Py_INCREF(r);
                    return r;
                },
                .pointer => |p| if (p.size == .slice and p.child == u8) return py.PyUnicode_FromStringAndSize(item.*.ptr, @intCast(item.*.len)) else {},
                .@"struct" => if (self.element_type_obj) |type_obj| {
                    const pyobj = py.PyType_GenericAlloc(type_obj, 0);
                    if (pyobj == null) return null;
                    const Wrap = pyzig_mod.PyObjectWrapper(T);
                    const w: *Wrap = @ptrCast(@alignCast(pyobj));
                    w.data = item;
                    return pyobj;
                },
                .@"enum" => {
                    const name = @tagName(item.*);
                    return py.PyUnicode_FromString(name.ptr);
                },
                else => {},
            }
            py.PyErr_SetString(py.PyExc_TypeError, "Unsupported type conversion");
            return null;
        }
        fn convertPythonToZig(self: *Self, pyobj: ?*py.PyObject, out: *T) bool {
            _ = self;
            const ti = @typeInfo(T);
            switch (ti) {
                .int => {
                    const v = py.PyLong_AsLong(pyobj);
                    if (py.PyErr_Occurred() != null) return false;
                    out.* = @intCast(v);
                    return true;
                },
                .float => {
                    const v = py.PyFloat_AsDouble(pyobj);
                    if (py.PyErr_Occurred() != null) return false;
                    out.* = @floatCast(v);
                    return true;
                },
                .bool => {
                    const v = py.PyObject_IsTrue(pyobj);
                    if (v == -1) return false;
                    out.* = v == 1;
                    return true;
                },
                .pointer => |p| if (p.size == .slice and p.child == u8) {
                    const sv = py.PyUnicode_AsUTF8(pyobj);
                    if (sv == null) return false;
                    const sl = std.mem.span(sv.?);
                    const cp = std.heap.c_allocator.dupe(u8, sl) catch return false;
                    out.* = cp;
                    return true;
                } else {},
                .@"struct" => {
                    const Wrap = pyzig_mod.PyObjectWrapper(T);
                    const w: *Wrap = @ptrCast(@alignCast(pyobj));
                    out.* = w.data.*;
                    return true;
                },
                else => return false,
            }
            return false;
        }

        var sequence_methods = py.PySequenceMethods{ .sq_length = sq_length, .sq_item = sq_item };
        var list_methods = [_]py.PyMethodDef{ .{ .ml_name = "append", .ml_meth = @ptrCast(&list_append), .ml_flags = py.METH_O, .ml_doc = "Append item" }, .{ .ml_name = "insert", .ml_meth = @ptrCast(&list_insert), .ml_flags = py.METH_VARARGS, .ml_doc = "Insert item at index" }, .{ .ml_name = "clear", .ml_meth = @ptrCast(&list_clear), .ml_flags = py.METH_VARARGS, .ml_doc = "Clear list" }, .{ .ml_name = "remove", .ml_meth = @ptrCast(&list_remove), .ml_flags = py.METH_O, .ml_doc = "Remove value" }, .{ .ml_name = "__len__", .ml_meth = @ptrCast(&list_len), .ml_flags = py.METH_NOARGS, .ml_doc = "len" }, .{ .ml_name = "__getitem__", .ml_meth = @ptrCast(&list_getitem), .ml_flags = py.METH_O, .ml_doc = "getitem" }, .{ .ml_name = "pop", .ml_meth = @ptrCast(&list_pop), .ml_flags = py.METH_VARARGS, .ml_doc = "pop" }, py.ML_SENTINEL };
        fn list_richcompare(self: ?*py.PyObject, other: ?*py.PyObject, op: c_int) callconv(.C) ?*py.PyObject {
            // Support equality/inequality against any Python sequence
            // Only Py_EQ is defined in our bindings; treat all other ops as NE
            const s: *Self = @ptrCast(@alignCast(self));
            const len_self: isize = @intCast(s.count());
            const len_other = py.PySequence_Size(other);
            if (len_other < 0) return py.Py_False();
            var equal = len_self == len_other;
            if (equal) {
                var i: isize = 0;
                while (i < len_self) : (i += 1) {
                    const n = s.nodeAt(@intCast(i)) orelse return py.Py_False();
                    const a = s.convertZigToPython(&n.data) orelse return null;
                    defer py.Py_DECREF(a);
                    const b = py.PySequence_GetItem(other, i);
                    if (b == null) return null;
                    defer py.Py_DECREF(b.?);
                    const eq = py.PyObject_RichCompareBool(a, b, py.Py_EQ);
                    if (eq != 1) {
                        equal = false;
                        break;
                    }
                }
            }
            if (op == py.Py_EQ) {
                const r = if (equal) py.Py_True() else py.Py_False();
                py.Py_INCREF(r);
                return r;
            } else {
                const r = if (!equal) py.Py_True() else py.Py_False();
                py.Py_INCREF(r);
                return r;
            }
        }

        var type_object = py.PyTypeObject{ .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 }, .tp_name = "pyzig.MutableList", .tp_basicsize = @sizeOf(Self), .tp_flags = py.Py_TPFLAGS_DEFAULT, .tp_as_sequence = &sequence_methods, .tp_iter = @ptrCast(@constCast(&list_iter)), .tp_methods = @as([*]py.PyMethodDef, @ptrCast(&list_methods)), .tp_richcompare = @ptrCast(@constCast(&list_richcompare)) };
    };
}

pub fn createMutableList(comptime T: type, list_ptr: *std.DoublyLinkedList(T), element_type_obj: ?*py.PyTypeObject) ?*py.PyObject {
    const L = MutableLinkedList(T);
    if (py.PyType_Ready(&L.type_object) < 0) return null;
    return L.create(list_ptr, element_type_obj);
}
