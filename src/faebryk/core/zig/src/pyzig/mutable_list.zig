const std = @import("std");
const py = @import("pybindings.zig");

/// Python-compatible mutable list wrapper around ArrayList
pub fn MutableList(comptime T: type) type {
    return struct {
        const Self = @This();

        // Python object header
        ob_base: py.PyObject_HEAD,

        // ArrayList for dynamic storage
        array_list: *std.ArrayList(T),

        // Optional type object for struct elements
        element_type_obj: ?*py.PyTypeObject,

        fn create(array_list_ptr: *std.ArrayList(T), element_type_obj: ?*py.PyTypeObject) ?*py.PyObject {
            const obj = py.PyType_GenericAlloc(&type_object, 0);
            if (obj == null) return null;
            const self: *Self = @ptrCast(@alignCast(obj));
            self.array_list = array_list_ptr;
            self.element_type_obj = element_type_obj;
            return obj;
        }

        pub fn py_init(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) c_int {
            var items_list: ?*py.PyObject = null;
            if (py.PyArg_ParseTuple(args, "O", &items_list) == 0) {
                return -1;
            }

            if (py.PyList_Check(items_list) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "Expected a list");
                return -1;
            }

            // TODO: check all items are of the same type?
            const element_type_obj = py.Py_TYPE(py.PyList_GetItem(items_list, 0));
            if (element_type_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "Expected a list of items");
                return -1;
            }

            const array_list = std.ArrayList(T).init(std.heap.c_allocator);
            defer array_list.deinit();

            var i: isize = 0;
            while (i < py.PyList_Size(items_list)) : (i += 1) {
                const item = py.PyList_GetItem(items_list, i);
                if (item == null) return -1;
                defer py.Py_DECREF(item.?);

                array_list.append(undefined) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Failed to append item");
                    return -1;
                };

                if (!convertPythonToZig(item, &array_list.items[i])) {
                    py.PyErr_SetString(py.PyExc_TypeError, "Failed to convert item");
                    return -1;
                }
            }

            const list: *Self = @ptrCast(@alignCast(self));
            list.array_list = &array_list;
            list.element_type_obj = element_type_obj;

            return 0;
        }

        // ===== Python Sequence Protocol =====

        fn sq_length(self: ?*py.PyObject) callconv(.C) isize {
            const list: *Self = @ptrCast(@alignCast(self));
            return @intCast(list.array_list.items.len);
        }

        fn sq_item(self: ?*py.PyObject, index: isize) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            // Handle negative indexing
            const len: isize = @intCast(list.array_list.items.len);
            const actual_index = if (index < 0) len + index else index;

            // Check bounds - provide more detailed error message
            if (actual_index < 0 or actual_index >= len) {
                const msg = std.fmt.allocPrint(std.heap.c_allocator, "list index out of range: index={d}, len={d}, actual_index={d}", .{ index, len, actual_index }) catch "list index out of range";
                defer if (!std.mem.eql(u8, msg, "list index out of range")) std.heap.c_allocator.free(msg);
                py.PyErr_SetString(py.PyExc_IndexError, @ptrCast(msg));
                return null;
            }

            return list.convertZigToPython(&list.array_list.items[@intCast(actual_index)]);
        }

        fn sq_ass_item(self: ?*py.PyObject, index: isize, value: ?*py.PyObject) callconv(.C) c_int {
            const list: *Self = @ptrCast(@alignCast(self));

            if (value == null) {
                // Deletion - remove item at index
                const len: isize = @intCast(list.array_list.items.len);
                const actual_index = if (index < 0) len + index else index;

                if (actual_index < 0 or actual_index >= len) {
                    py.PyErr_SetString(py.PyExc_IndexError, "list assignment index out of range");
                    return -1;
                }

                _ = list.array_list.orderedRemove(@intCast(actual_index));
                list.syncToOriginalSlice();
                return 0;
            } else {
                // Assignment - set item at index
                const len: isize = @intCast(list.array_list.items.len);
                const actual_index = if (index < 0) len + index else index;

                if (actual_index < 0 or actual_index >= len) {
                    py.PyErr_SetString(py.PyExc_IndexError, "list assignment index out of range");
                    return -1;
                }

                if (!list.convertPythonToZig(value, &list.array_list.items[@intCast(actual_index)])) {
                    return -1;
                }

                return 0;
            }
        }

        fn sq_contains(self: ?*py.PyObject, item: ?*py.PyObject) callconv(.C) c_int {
            const list: *Self = @ptrCast(@alignCast(self));

            // Compare with each element
            for (list.array_list.items) |*zig_item| {
                const py_item = list.convertZigToPython(zig_item);
                if (py_item == null) continue;
                defer py.Py_DECREF(py_item.?);

                const result = py.PyObject_RichCompareBool(item, py_item, py.Py_EQ);
                if (result == -1) return -1; // Error occurred
                if (result == 1) return 1; // Found it
            }

            return 0; // Not found
        }

        fn sq_concat(self: ?*py.PyObject, other: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            // Create a new list with combined items
            var new_list = std.ArrayList(T).init(std.heap.c_allocator);
            defer new_list.deinit();

            // Add items from self
            new_list.appendSlice(list.array_list.items) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to concatenate lists");
                return null;
            };

            // Add items from other (if it's a sequence)
            const other_len = py.PySequence_Size(other);
            if (other_len < 0) return null;

            var i: isize = 0;
            while (i < other_len) : (i += 1) {
                const item = py.PySequence_GetItem(other, i);
                if (item == null) return null;
                defer py.Py_DECREF(item.?);

                new_list.append(undefined) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Failed to concatenate lists");
                    return null;
                };

                const last_idx = new_list.items.len - 1;
                if (!list.convertPythonToZig(item, &new_list.items[last_idx])) {
                    _ = new_list.pop();
                    return null;
                }
            }

            // Create new MutableList with combined data
            return createMutableList(T, new_list.items, null, list.element_type_obj);
        }

        fn sq_repeat(self: ?*py.PyObject, count: isize) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            if (count <= 0) {
                // Return empty list
                const empty_slice: []const T = &[_]T{};
                return createMutableList(T, empty_slice, null, list.element_type_obj);
            }

            var new_list = std.ArrayList(T).init(std.heap.c_allocator);
            defer new_list.deinit();

            // Repeat the list contents
            var i: isize = 0;
            while (i < count) : (i += 1) {
                new_list.appendSlice(list.array_list.items) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Failed to repeat list");
                    return null;
                };
            }

            return createMutableList(T, new_list.items, list.element_type_obj);
        }

        // ===== Python Methods =====

        fn list_append(self: ?*py.PyObject, value: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            // Grow the list
            list.array_list.append(undefined) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to append to list");
                return null;
            };

            // Convert and store the value
            const last_index = list.array_list.items.len - 1;
            if (!list.convertPythonToZig(value, &list.array_list.items[last_index])) {
                _ = list.array_list.pop(); // Remove the added item on error
                return null;
            }

            list.syncToOriginalSlice();

            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }

        fn list_pop(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            if (list.array_list.items.len == 0) {
                py.PyErr_SetString(py.PyExc_IndexError, "pop from empty list");
                return null;
            }

            // Parse optional index argument
            var index: isize = -1; // Default to last item
            if (args != null and py.PyTuple_Size(args) > 0) {
                if (py.PyArg_ParseTuple(args, "|i", &index) == 0) {
                    return null;
                }
            }

            // Handle negative indexing
            const len: isize = @intCast(list.array_list.items.len);
            const actual_index = if (index < 0) len + index else index;

            // Check bounds
            if (actual_index < 0 or actual_index >= len) {
                py.PyErr_SetString(py.PyExc_IndexError, "pop index out of range");
                return null;
            }

            // Get the item to return
            const item_to_return = list.convertZigToPython(&list.array_list.items[@intCast(actual_index)]);
            if (item_to_return == null) return null;

            // Remove the item
            _ = list.array_list.orderedRemove(@intCast(actual_index));

            list.syncToOriginalSlice();

            return item_to_return;
        }

        fn list_clear(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = args;
            const list: *Self = @ptrCast(@alignCast(self));

            list.array_list.clearAndFree();

            list.syncToOriginalSlice();

            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }

        fn list_insert(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            // Parse arguments: index, item
            var index: isize = 0;
            var item: ?*py.PyObject = null;
            if (py.PyArg_ParseTuple(args, "iO", &index, &item) == 0) {
                return null;
            }

            // Handle negative indexing - Python's insert never raises IndexError
            const len: isize = @intCast(list.array_list.items.len);
            var actual_index: isize = index;

            // Handle negative indexing
            if (actual_index < 0) {
                actual_index = @max(0, len + actual_index);
            }

            // Clamp to valid range - insert at end if index too large
            if (actual_index > len) {
                actual_index = len;
            }

            // Insert at the specified position
            list.array_list.insert(@intCast(actual_index), undefined) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to insert item");
                return null;
            };

            // Convert and store the item
            if (!list.convertPythonToZig(item, &list.array_list.items[@intCast(actual_index)])) {
                _ = list.array_list.orderedRemove(@intCast(actual_index));
                return null;
            }

            list.syncToOriginalSlice();

            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }

        fn list_count(self: ?*py.PyObject, item: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            var count: isize = 0;
            for (list.array_list.items) |*zig_item| {
                const py_item = list.convertZigToPython(zig_item);
                if (py_item == null) continue;
                defer py.Py_DECREF(py_item.?);

                const result = py.PyObject_RichCompareBool(item, py_item, py.Py_EQ);
                if (result == -1) return null;
                if (result == 1) count += 1;
            }

            return py.PyLong_FromLong(count);
        }

        fn list_index(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            var item: ?*py.PyObject = null;
            var start: isize = 0;
            var stop: isize = @intCast(list.array_list.items.len);

            if (py.PyArg_ParseTuple(args, "O|ii", &item, &start, &stop) == 0) {
                return null;
            }

            // Handle negative indices and clamp
            const len: isize = @intCast(list.array_list.items.len);
            if (start < 0) start += len;
            if (stop < 0) stop += len;
            start = std.math.clamp(start, 0, len);
            stop = std.math.clamp(stop, 0, len);

            // Search for the item
            var i: isize = start;
            while (i < stop) : (i += 1) {
                const zig_item = &list.array_list.items[@intCast(i)];
                const py_item = list.convertZigToPython(zig_item);
                if (py_item == null) continue;
                defer py.Py_DECREF(py_item.?);

                const result = py.PyObject_RichCompareBool(item, py_item, py.Py_EQ);
                if (result == -1) return null;
                if (result == 1) return py.PyLong_FromLong(i);
            }

            py.PyErr_SetString(py.PyExc_ValueError, "item is not in list");
            return null;
        }

        fn list_getitem(self: ?*py.PyObject, index: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const idx = py.PyLong_AsLong(index);
            if (py.PyErr_Occurred() != null) {
                return null; // Error already set by PyLong_AsLong
            }
            return sq_item(self, idx);
        }

        fn list_contains(self: ?*py.PyObject, item: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const result = sq_contains(self, item);
            if (result == -1) return null;
            return if (result == 1) py.Py_True() else py.Py_False();
        }

        fn list_reversed(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            // Create a reversed Python list for iteration
            const py_list = py.PyList_New(@intCast(list.array_list.items.len));
            if (py_list == null) return null;

            const len = list.array_list.items.len;
            for (0..len) |i| {
                const rev_idx = len - 1 - i;
                const py_item = list.convertZigToPython(&list.array_list.items[rev_idx]);
                if (py_item == null) {
                    py.Py_DECREF(py_list.?);
                    return null;
                }
                _ = py.PyList_SetItem(py_list, @intCast(i), py_item);
            }

            return py.PyObject_GetIter(py_list);
        }

        fn list_len(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));
            return py.PyLong_FromLong(@intCast(list.array_list.items.len));
        }

        fn list_iter(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));

            // Create a Python list for iteration (simple approach)
            const py_list = py.PyList_New(@intCast(list.array_list.items.len));
            if (py_list == null) return null;

            for (list.array_list.items, 0..) |*item, i| {
                const py_item = list.convertZigToPython(item);
                if (py_item == null) {
                    py.Py_DECREF(py_list.?);
                    return null;
                }
                _ = py.PyList_SetItem(py_list, @intCast(i), py_item);
            }

            return py.PyObject_GetIter(py_list);
        }

        // ===== Conversion Helpers =====

        fn convertZigToPython(self: *Self, item: *T) ?*py.PyObject {
            const type_info = @typeInfo(T);
            switch (type_info) {
                .int => return py.PyLong_FromLong(@intCast(item.*)),
                .float => return py.PyFloat_FromDouble(@floatCast(item.*)),
                .bool => if (item.*) return py.Py_True() else return py.Py_False(),
                .pointer => |ptr| {
                    if (ptr.size == .slice and ptr.child == u8) {
                        return py.PyUnicode_FromStringAndSize(item.*.ptr, @intCast(item.*.len));
                    } else if (ptr.size == .one and ptr.child == u8) {
                        return py.PyUnicode_FromString(item.*);
                    }
                },
                .@"struct" => {
                    if (self.element_type_obj) |type_obj| {
                        const pyobj = py.PyType_GenericAlloc(type_obj, 0);
                        if (pyobj == null) return null;

                        const SimpleWrapper = struct {
                            ob_base: py.PyObject_HEAD,
                            data: *T,
                        };

                        const wrapper: *SimpleWrapper = @ptrCast(@alignCast(pyobj));
                        wrapper.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };
                        wrapper.data = item;

                        return pyobj;
                    }
                },
                .@"enum" => {
                    const enum_name = @tagName(item.*);
                    return py.PyUnicode_FromString(enum_name.ptr);
                },
                else => {},
            }

            py.PyErr_SetString(py.PyExc_TypeError, "Unsupported type conversion");
            return null;
        }

        fn convertPythonToZig(self: *Self, pyobj: ?*py.PyObject, zig_item: *T) bool {
            _ = self;
            const type_info = @typeInfo(T);
            switch (type_info) {
                .int => {
                    const val = py.PyLong_AsLong(pyobj);
                    if (py.PyErr_Occurred() != null) return false;
                    zig_item.* = @intCast(val);
                    return true;
                },
                .float => {
                    const val = py.PyFloat_AsDouble(pyobj);
                    if (py.PyErr_Occurred() != null) return false;
                    zig_item.* = @floatCast(val);
                    return true;
                },
                .bool => {
                    const val = py.PyObject_IsTrue(pyobj);
                    if (val == -1) return false;
                    zig_item.* = val == 1;
                    return true;
                },
                .pointer => |ptr| {
                    if (ptr.size == .slice and ptr.child == u8) {
                        const str_val = py.PyUnicode_AsUTF8(pyobj);
                        if (str_val == null) return false;
                        const str_slice = std.mem.span(str_val.?);
                        const str_copy = std.heap.c_allocator.dupe(u8, str_slice) catch return false;
                        zig_item.* = str_copy;
                        return true;
                    }
                },
                .@"struct" => {
                    // Handle struct conversion from Python wrapper to Zig struct
                    const SimpleWrapper = struct {
                        ob_base: py.PyObject_HEAD,
                        data: *T,
                    };
                    const wrapper: *SimpleWrapper = @ptrCast(@alignCast(pyobj));
                    zig_item.* = wrapper.data.*;
                    return true;
                },
                else => return false,
            }

            return false;
        }

        // ===== Python Type Definition =====

        var sequence_methods = py.PySequenceMethods{
            .sq_length = sq_length,
            .sq_item = sq_item,
            .sq_ass_item = sq_ass_item,
            .sq_contains = sq_contains,
            .sq_concat = sq_concat,
            .sq_repeat = sq_repeat,
        };

        var list_methods = [_]py.PyMethodDef{
            .{
                .ml_name = "append",
                .ml_meth = @ptrCast(&list_append),
                .ml_flags = py.METH_O,
                .ml_doc = "Append item to the end of the list",
            },
            .{
                .ml_name = "pop",
                .ml_meth = @ptrCast(&list_pop),
                .ml_flags = py.METH_VARARGS,
                .ml_doc = "Remove and return item at index (default last)",
            },
            .{
                .ml_name = "insert",
                .ml_meth = @ptrCast(&list_insert),
                .ml_flags = py.METH_VARARGS,
                .ml_doc = "Insert item at index",
            },
            .{
                .ml_name = "clear",
                .ml_meth = @ptrCast(&list_clear),
                .ml_flags = py.METH_VARARGS,
                .ml_doc = "Remove all items from the list",
            },
            .{
                .ml_name = "count",
                .ml_meth = @ptrCast(&list_count),
                .ml_flags = py.METH_O,
                .ml_doc = "Return number of occurrences of value",
            },
            .{
                .ml_name = "index",
                .ml_meth = @ptrCast(&list_index),
                .ml_flags = py.METH_VARARGS,
                .ml_doc = "Return first index of value",
            },
            .{
                .ml_name = "__len__",
                .ml_meth = @ptrCast(&list_len),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return the length of the list",
            },
            .{
                .ml_name = "__getitem__",
                .ml_meth = @ptrCast(&list_getitem),
                .ml_flags = py.METH_O,
                .ml_doc = "Get item at index",
            },
            .{
                .ml_name = "__contains__",
                .ml_meth = @ptrCast(&list_contains),
                .ml_flags = py.METH_O,
                .ml_doc = "Return True if item is in the list",
            },
            .{
                .ml_name = "__reversed__",
                .ml_meth = @ptrCast(&list_reversed),
                .ml_flags = py.METH_NOARGS,
                .ml_doc = "Return a reverse iterator over the list",
            },
            py.ML_SENTINEL,
        };

        var type_object = py.PyTypeObject{
            .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
            .tp_name = "pyzig.MutableList",
            .tp_basicsize = @sizeOf(Self),
            .tp_flags = py.Py_TPFLAGS_DEFAULT,
            .tp_as_sequence = &sequence_methods,
            .tp_iter = @ptrCast(@constCast(&list_iter)),
            .tp_methods = @as([*]py.PyMethodDef, @ptrCast(&list_methods)),
            .tp_init = @ptrCast(&py_init),
        };
    };
}

/// Create a mutable list wrapper
pub fn createMutableList(comptime T: type, array_list_ptr: *std.ArrayList(T), element_type_obj: ?*py.PyTypeObject) ?*py.PyObject {
    const ListType = MutableList(T);

    // Initialize type object if not done yet
    if (py.PyType_Ready(&ListType.type_object) < 0) {
        return null;
    }

    return ListType.create(array_list_ptr, element_type_obj);
}
