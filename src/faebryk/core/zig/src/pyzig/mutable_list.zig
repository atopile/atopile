const std = @import("std");
const py = @import("pybindings.zig");

/// A Python object that wraps a Zig slice and provides mutable list operations
/// This allows direct mutation of the underlying Zig data from Python
pub fn MutableList(comptime T: type) type {
    return struct {
        const Self = @This();
        
        // Python object header
        ob_base: py.PyObject_HEAD,
        
        // Pointer to the slice we're wrapping (in parent struct)
        slice_ptr: *[]T,
        
        // Type information for element conversion
        element_type_obj: ?*py.PyTypeObject,
        
        // Allocator for growing/shrinking the slice
        allocator: std.mem.Allocator,
        
        /// Create a new mutable list wrapper around a Zig slice
        pub fn create(slice_ptr: *[]T, element_type_obj: ?*py.PyTypeObject) ?*py.PyObject {
            const type_obj = getTypeObject();
            const pyobj = py.PyType_GenericAlloc(type_obj, 0);
            if (pyobj == null) return null;
            
            const list: *Self = @ptrCast(@alignCast(pyobj));
            list.ob_base = py.PyObject_HEAD{ .ob_refcnt = 1, .ob_type = type_obj };
            list.slice_ptr = slice_ptr;
            list.element_type_obj = element_type_obj;
            list.allocator = std.heap.c_allocator;
            
            return pyobj;
        }
        
        /// Get the type object for this mutable list type
        fn getTypeObject() *py.PyTypeObject {
            // TODO: Initialize type object with sequence methods
            // For now, return a basic type object
            return &type_object;
        }
        
        // ===== Python Sequence Protocol Methods =====
        
        /// sq_length: Return length of the list
        fn sq_length(self: ?*py.PyObject) callconv(.C) isize {
            const list: *Self = @ptrCast(@alignCast(self));
            return @as(isize, @intCast(list.slice_ptr.len));
        }
        
        /// sq_item: Get item at index (like list[i])
        fn sq_item(self: ?*py.PyObject, index: isize) callconv(.C) ?*py.PyObject {
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Handle negative indices
            const len: isize = @as(isize, @intCast(list.slice_ptr.len));
            const actual_index = if (index < 0) len + index else index;
            
            if (actual_index < 0 or actual_index >= len) {
                py.PyErr_SetString(py.PyExc_IndexError, "list index out of range");
                return null;
            }
            
            // Convert Zig element to Python object
            return convertZigToPython(&list.slice_ptr.*[@intCast(actual_index)]);
        }
        
        /// sq_ass_item: Set item at index (like list[i] = value)
        fn sq_ass_item(self: ?*py.PyObject, index: isize, value: ?*py.PyObject) callconv(.C) c_int {
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Handle negative indices
            const len: isize = @as(isize, @intCast(list.slice_ptr.len));
            const actual_index = if (index < 0) len + index else index;
            
            if (actual_index < 0 or actual_index >= len) {
                py.PyErr_SetString(py.PyExc_IndexError, "list assignment index out of range");
                return -1;
            }
            
            // Convert Python object to Zig element
            if (convertPythonToZig(value, &list.slice_ptr.*[@intCast(actual_index)])) {
                return 0;
            } else {
                return -1;
            }
        }
        
        /// sq_contains: Check if item is in list (like item in list)
        fn sq_contains(self: ?*py.PyObject, value: ?*py.PyObject) callconv(.C) c_int {
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Linear search through the list
            for (list.slice_ptr.*) |*item| {
                const py_item = convertZigToPython(item) orelse continue;
                defer if (py_item != py.Py_None()) {}; // TODO: Add proper DECREF
                
                // Use Python's rich comparison
                const cmp_result = py.PyObject_RichCompareBool(py_item, value, py.Py_EQ);
                if (cmp_result == -1) {
                    return -1; // Error occurred
                }
                if (cmp_result == 1) {
                    return 1; // Found
                }
            }
            return 0; // Not found
        }
        
        /// sq_concat: Concatenate two lists (like list1 + list2)
        fn sq_concat(self: ?*py.PyObject, other: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;
            _ = other;
            // TODO: Implement list concatenation
            py.PyErr_SetString(py.PyExc_NotImplementedError, "List concatenation not yet implemented");
            return null;
        }
        
        /// sq_repeat: Repeat list n times (like list * n)
        fn sq_repeat(self: ?*py.PyObject, count: isize) callconv(.C) ?*py.PyObject {
            _ = self;
            _ = count;
            // TODO: Implement list repetition
            py.PyErr_SetString(py.PyExc_NotImplementedError, "List repetition not yet implemented");
            return null;
        }
        
        // ===== List Methods =====
        
        /// append(item): Add item to end of list
        fn list_append(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = kwargs;
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Parse single argument
            var item: ?*py.PyObject = null;
            if (py.PyArg_ParseTuple(args, "O", &item) == 0) {
                return null;
            }
            
            // Grow the slice by 1
            const old_len = list.slice_ptr.len;
            const new_slice = list.allocator.realloc(list.slice_ptr.*, old_len + 1) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to grow list");
                return null;
            };
            list.slice_ptr.* = new_slice;
            
            // Convert and store the new item
            if (!convertPythonToZig(item, &list.slice_ptr.*[old_len])) {
                // Revert on conversion failure
                list.slice_ptr.* = list.allocator.realloc(list.slice_ptr.*, old_len) catch list.slice_ptr.*;
                return null;
            }
            
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
        
        /// pop(index=-1): Remove and return item at index
        fn list_pop(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = kwargs;
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Parse optional index argument (default -1)
            var index: isize = -1;
            if (py.PyArg_ParseTuple(args, "|i", &index) == 0) {
                return null;
            }
            
            const len: isize = @intCast(list.slice_ptr.len);
            if (len == 0) {
                py.PyErr_SetString(py.PyExc_IndexError, "pop from empty list");
                return null;
            }
            
            // Handle negative indices
            const actual_index = if (index < 0) len + index else index;
            if (actual_index < 0 or actual_index >= len) {
                py.PyErr_SetString(py.PyExc_IndexError, "pop index out of range");
                return null;
            }
            
            // Get the item to return
            const item_to_return = convertZigToPython(&list.slice_ptr.*[@intCast(actual_index)]);
            
            // Shift elements left to remove the item
            const ui_index = @as(usize, @intCast(actual_index));
            std.mem.copyForwards(T, list.slice_ptr.*[ui_index..list.slice_ptr.len-1], list.slice_ptr.*[ui_index+1..]);
            
            // Shrink the slice
            list.slice_ptr.* = list.allocator.realloc(list.slice_ptr.*, list.slice_ptr.len - 1) catch list.slice_ptr.*[0..list.slice_ptr.len-1];
            
            return item_to_return;
        }
        
        /// insert(index, item): Insert item at index
        fn list_insert(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = kwargs;
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Parse arguments
            var index: isize = 0;
            var item: ?*py.PyObject = null;
            if (py.PyArg_ParseTuple(args, "iO", &index, &item) == 0) {
                return null;
            }
            
            // Clamp index to valid range
            const len: isize = @intCast(list.slice_ptr.len);
            const actual_index = std.math.clamp(if (index < 0) len + index else index, 0, len);
            
            // Grow the slice by 1
            const new_slice = list.allocator.realloc(list.slice_ptr.*, list.slice_ptr.len + 1) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to grow list");
                return null;
            };
            list.slice_ptr.* = new_slice;
            
            // Shift elements right to make space
            const ui_index = @as(usize, @intCast(actual_index));
            std.mem.copyBackwards(T, list.slice_ptr.*[ui_index+1..], list.slice_ptr.*[ui_index..list.slice_ptr.len-1]);
            
            // Convert and store the new item
            if (!convertPythonToZig(item, &list.slice_ptr.*[ui_index])) {
                // Revert on conversion failure
                list.slice_ptr.* = list.allocator.realloc(list.slice_ptr.*, list.slice_ptr.len - 1) catch list.slice_ptr.*;
                return null;
            }
            
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
        
        /// remove(item): Remove first occurrence of item
        fn list_remove(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = kwargs;
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Parse single argument
            var item: ?*py.PyObject = null;
            if (py.PyArg_ParseTuple(args, "O", &item) == 0) {
                return null;
            }
            
            // Find the item to remove
            for (list.slice_ptr.*, 0..) |*zig_item, i| {
                const py_item = convertZigToPython(zig_item) orelse continue;
                defer if (py_item != py.Py_None()) {}; // TODO: Add proper DECREF
                
                const cmp_result = py.PyObject_RichCompareBool(py_item, item, py.Py_EQ);
                if (cmp_result == -1) {
                    return null; // Error occurred
                }
                if (cmp_result == 1) {
                    // Found the item, remove it
                    std.mem.copyForwards(T, list.slice_ptr.*[i..list.slice_ptr.len-1], list.slice_ptr.*[i+1..]);
                    list.slice_ptr.* = list.allocator.realloc(list.slice_ptr.*, list.slice_ptr.len - 1) catch list.slice_ptr.*[0..list.slice_ptr.len-1];
                    
                    const none = py.Py_None();
                    py.Py_INCREF(none);
                    return none;
                }
            }
            
            // Item not found
            py.PyErr_SetString(py.PyExc_ValueError, "list.remove(x): x not in list");
            return null;
        }
        
        /// clear(): Remove all items from the list
        fn list_clear(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = args;
            _ = kwargs;
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Free the slice and replace with empty slice
            if (list.slice_ptr.len > 0) {
                list.allocator.free(list.slice_ptr.*);
                list.slice_ptr.* = &[_]T{};
            }
            
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
        
        /// extend(iterable): Extend list by appending elements from iterable
        fn list_extend(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = kwargs;
            const list: *Self = @ptrCast(@alignCast(self));
            
            // Parse single argument
            var iterable: ?*py.PyObject = null;
            if (py.PyArg_ParseTuple(args, "O", &iterable) == 0) {
                return null;
            }
            
            // Check if it's a list for now (extend to support other iterables later)
            if (py.PyList_Check(iterable) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "extend() argument must be a list (for now)");
                return null;
            }
            
            const other_size = py.PyList_Size(iterable);
            if (other_size < 0) {
                return null;
            }
            
            if (other_size == 0) {
                const none = py.Py_None();
                py.Py_INCREF(none);
                return none;
            }
            
            // Grow the slice
            const old_len = list.slice_ptr.len;
            const new_len = old_len + @as(usize, @intCast(other_size));
            const new_slice = list.allocator.realloc(list.slice_ptr.*, new_len) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to grow list");
                return null;
            };
            list.slice_ptr.* = new_slice;
            
            // Copy items from the other list
            for (0..@intCast(other_size)) |i| {
                const item = py.PyList_GetItem(iterable, @intCast(i));
                if (item == null) {
                    // Revert on failure
                    list.slice_ptr.* = list.allocator.realloc(list.slice_ptr.*, old_len) catch list.slice_ptr.*[0..old_len];
                    return null;
                }
                
                if (!convertPythonToZig(item, &list.slice_ptr.*[old_len + i])) {
                    // Revert on conversion failure
                    list.slice_ptr.* = list.allocator.realloc(list.slice_ptr.*, old_len) catch list.slice_ptr.*[0..old_len];
                    return null;
                }
            }
            
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
        
        // ===== Helper Functions =====
        
        /// Convert a Zig element to a Python object
        fn convertZigToPython(item: *T) ?*py.PyObject {
            const type_info = @typeInfo(T);
            switch (type_info) {
                .int => return py.PyLong_FromLong(@intCast(item.*)),
                .float => return py.PyFloat_FromDouble(@floatCast(item.*)),
                .bool => if (item.*) return py.Py_True() else return py.Py_False(),
                .pointer => |ptr| {
                    if (ptr.size == .slice and ptr.child == u8) {
                        return py.PyUnicode_FromStringAndSize(item.*.ptr, @intCast(item.*.len));
                    }
                },
                .@"struct" => {
                    // TODO: Handle struct conversion using the element_type_obj
                    // For now, return None
                    const none = py.Py_None();
                    py.Py_INCREF(none);
                    return none;
                },
                .@"enum" => {
                    const enum_str = @tagName(item.*);
                    return py.PyUnicode_FromStringAndSize(enum_str.ptr, @intCast(enum_str.len));
                },
                else => {
                    const none = py.Py_None();
                    py.Py_INCREF(none);
                    return none;
                },
            }
            
            const none = py.Py_None();
            py.Py_INCREF(none);
            return none;
        }
        
        /// Convert a Python object to a Zig element
        fn convertPythonToZig(pyobj: ?*py.PyObject, zig_item: *T) bool {
            if (pyobj == null) return false;
            
            const type_info = @typeInfo(T);
            switch (type_info) {
                .int => {
                    const val = py.PyLong_AsLong(pyobj);
                    if (val == -1 and py.PyErr_Occurred() != null) return false;
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
                    // TODO: Handle struct conversion
                    return false;
                },
                .@"enum" => {
                    const str_val = py.PyUnicode_AsUTF8(pyobj);
                    if (str_val == null) return false;
                    const enum_str = std.mem.span(str_val.?);
                    zig_item.* = std.meta.stringToEnum(T, enum_str) orelse return false;
                    return true;
                },
                else => return false,
            }
            
            return false;
        }
        
        // ===== Python Type Object =====
        
        var sequence_methods = py.PySequenceMethods{
            .sq_length = sq_length,
            .sq_item = sq_item,
            .sq_ass_item = sq_ass_item,
            .sq_contains = sq_contains,
            .sq_concat = sq_concat,
            .sq_repeat = sq_repeat,
            // In-place operations not implemented yet
            .sq_inplace_concat = null,
            .sq_inplace_repeat = null,
        };
        
        var list_methods = [_]py.PyMethodDef{
            .{
                .ml_name = "append",
                .ml_meth = @ptrCast(&list_append),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Append item to the end of the list",
            },
            .{
                .ml_name = "pop",
                .ml_meth = @ptrCast(&list_pop),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Remove and return item at index (default last)",
            },
            .{
                .ml_name = "insert",
                .ml_meth = @ptrCast(&list_insert),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Insert item at index",
            },
            .{
                .ml_name = "remove",
                .ml_meth = @ptrCast(&list_remove),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Remove first occurrence of item",
            },
            .{
                .ml_name = "clear",
                .ml_meth = @ptrCast(&list_clear),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Remove all items from the list",
            },
            .{
                .ml_name = "extend",
                .ml_meth = @ptrCast(&list_extend),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS,
                .ml_doc = "Extend list by appending elements from iterable",
            },
            py.ML_SENTINEL,
        };
        
        var type_object = py.PyTypeObject{
            .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
            .tp_name = "pyzig.MutableList",
            .tp_basicsize = @sizeOf(Self),
            .tp_flags = py.Py_TPFLAGS_DEFAULT,
            .tp_as_sequence = &sequence_methods,
            .tp_methods = @as([*]py.PyMethodDef, @ptrCast(&list_methods)),
            // TODO: Add tp_repr, tp_dealloc, etc.
        };
    };
}

/// Create a mutable list wrapper for a specific element type
pub fn createMutableList(comptime T: type, slice_ptr: *[]T, element_type_obj: ?*py.PyTypeObject) ?*py.PyObject {
    const ListType = MutableList(T);
    
    // Initialize type object if not done yet
    if (py.PyType_Ready(&ListType.type_object) < 0) {
        return null;
    }
    
    return ListType.create(slice_ptr, element_type_obj);
}