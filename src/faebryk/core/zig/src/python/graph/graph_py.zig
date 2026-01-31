const std = @import("std");
const graph = @import("graph");
const visitor = graph.visitor;
const pyzig = @import("pyzig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const type_registry = pyzig.type_registry;
const method_descr = bind.method_descr;

// Some wrappers (notably BoundNodeReference/BoundEdgeReference) are sometimes created as
// "borrowed views" by auto-generated struct wrappers (e.g. get/set code) where `wrapper.data`
// may point into non-owned memory (including stack temporaries). For objects we create here, we
// want to own+free the payload; for borrowed views we must NOT free.
//
// We tag owned payload allocations with a magic header so tp_dealloc can distinguish them.
const owned_magic_bound_node: u64 = 0x424E4F44455F4F57; // "BNODE_OW"
const owned_magic_bound_edge: u64 = 0x42454447455F4F57; // "BEDGE_OW"
const owned_magic_node: u64 = 0x4E4F44455F5F4F57; // "NODE__OW"
const owned_magic_edge: u64 = 0x454447455F5F4F57; // "EDGE__OW"

const OwnedBoundNodePayload = struct {
    magic: u64,
    payload: graph.graph.BoundNodeReference,
};

const OwnedBoundEdgePayload = struct {
    magic: u64,
    payload: graph.graph.BoundEdgeReference,
};

const OwnedNodePayload = struct {
    magic: u64,
    payload: graph.graph.NodeReference,
};

const OwnedEdgePayload = struct {
    magic: u64,
    payload: graph.graph.EdgeReference,
};

pub fn makeBoundNodePyObject(value: graph.graph.BoundNodeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const owned = allocator.create(OwnedBoundNodePayload) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    owned.* = .{ .magic = owned_magic_bound_node, .payload = value };

    const pyobj = bind.wrap_obj("BoundNodeReference", &bound_node_type, BoundNodeWrapper, &owned.payload);
    if (pyobj == null) {
        allocator.destroy(owned);
    }
    return pyobj;
}

pub fn makeBoundEdgePyObject(value: graph.graph.BoundEdgeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const owned = allocator.create(OwnedBoundEdgePayload) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    owned.* = .{ .magic = owned_magic_bound_edge, .payload = value };

    const pyobj = bind.wrap_obj("BoundEdgeReference", &bound_edge_type, BoundEdgeWrapper, &owned.payload);
    if (pyobj == null) {
        allocator.destroy(owned);
    }
    return pyobj;
}

pub fn makeNodePyObject(value: graph.graph.NodeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const owned = allocator.create(OwnedNodePayload) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    owned.* = .{ .magic = owned_magic_node, .payload = value };

    const pyobj = bind.wrap_obj("NodeReference", &node_type, NodeWrapper, &owned.payload);
    if (pyobj == null) {
        allocator.destroy(owned);
    }
    return pyobj;
}

pub fn makeEdgePyObject(value: graph.graph.EdgeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const owned = allocator.create(OwnedEdgePayload) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    owned.* = .{ .magic = owned_magic_edge, .payload = value };

    const pyobj = bind.wrap_obj("EdgeReference", &edge_type, EdgeWrapper, &owned.payload);
    if (pyobj == null) {
        allocator.destroy(owned);
    }
    return pyobj;
}

pub fn makeBFSPathPyObject(path: *graph.graph.BFSPath) ?*py.PyObject {
    // Transfer ownership of the BFSPath to Python
    // Python will call deinit() when the object is garbage collected
    const pyobj = bind.wrap_obj("BFSPath", &bfs_path_type, BFSPathWrapper, path);
    if (pyobj == null) {
        path.deinit();
    }
    return pyobj;
}

const VisitResultVoid = visitor.VisitResult(void);

pub const BoundEdgeVisitor = struct {
    py_ctx: ?*py.PyObject,
    callable: ?*py.PyObject,
    had_error: bool = false,

    pub fn call(ctx_ptr: *anyopaque, bound_edge: graph.graph.BoundEdgeReference) VisitResultVoid {
        const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));

        const edge_obj = makeBoundEdgePyObject(bound_edge) orelse {
            ctx.had_error = true;
            return VisitResultVoid{ .ERROR = error.Callback };
        };

        const args_tuple = py.PyTuple_New(2) orelse {
            ctx.had_error = true;
            py.Py_DECREF(edge_obj);
            return VisitResultVoid{ .ERROR = error.Callback };
        };

        const ctx_handle: *py.PyObject = if (ctx.py_ctx) |c| c else py.Py_None();
        py.Py_INCREF(ctx_handle);
        if (py.PyTuple_SetItem(args_tuple, 0, ctx_handle) < 0) {
            ctx.had_error = true;
            py.Py_DECREF(edge_obj);
            py.Py_DECREF(args_tuple);
            return VisitResultVoid{ .ERROR = error.Callback };
        }

        if (py.PyTuple_SetItem(args_tuple, 1, edge_obj) < 0) {
            ctx.had_error = true;
            py.Py_DECREF(args_tuple);
            py.Py_DECREF(edge_obj);
            return VisitResultVoid{ .ERROR = error.Callback };
        }

        const result = py.PyObject_Call(ctx.callable, args_tuple, null);
        if (result == null) {
            ctx.had_error = true;
            py.Py_DECREF(args_tuple);
            return VisitResultVoid{ .ERROR = error.Callback };
        }

        py.Py_DECREF(result.?);
        py.Py_DECREF(args_tuple);
        return VisitResultVoid{ .CONTINUE = {} };
    }
};

pub const GraphViewWrapper = bind.PyObjectWrapper(graph.graph.GraphView);
pub const NodeWrapper = bind.PyObjectWrapper(graph.graph.NodeReference);
pub const EdgeWrapper = bind.PyObjectWrapper(graph.graph.EdgeReference);
pub const BoundNodeWrapper = bind.PyObjectWrapper(graph.graph.BoundNodeReference);
pub const BoundEdgeWrapper = bind.PyObjectWrapper(graph.graph.BoundEdgeReference);
pub const BFSPathWrapper = bind.PyObjectWrapper(graph.graph.BFSPath);

pub var graph_view_type: ?*py.PyTypeObject = null;
pub var node_type: ?*py.PyTypeObject = null;
pub var edge_type: ?*py.PyTypeObject = null;
pub var bound_node_type: ?*py.PyTypeObject = null;
pub var bound_edge_type: ?*py.PyTypeObject = null;
pub var bfs_path_type: ?*py.PyTypeObject = null;

const Literal = graph.graph.Literal;

fn bound_node_dealloc(self: *py.PyObject) callconv(.C) void {
    const wrapper = @as(*BoundNodeWrapper, @ptrCast(@alignCast(self)));
    // Only free if this payload was allocated by makeBoundNodePyObject().
    const owned: *OwnedBoundNodePayload = @fieldParentPtr("payload", wrapper.data);
    if (owned.magic == owned_magic_bound_node) {
        std.heap.c_allocator.destroy(owned);
    }

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.C) void, @ptrCast(@alignCast(free_fn_any)));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn bound_edge_dealloc(self: *py.PyObject) callconv(.C) void {
    const wrapper = @as(*BoundEdgeWrapper, @ptrCast(@alignCast(self)));
    // Only free if this payload was allocated by makeBoundEdgePyObject().
    const owned: *OwnedBoundEdgePayload = @fieldParentPtr("payload", wrapper.data);
    if (owned.magic == owned_magic_bound_edge) {
        std.heap.c_allocator.destroy(owned);
    }

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.C) void, @ptrCast(@alignCast(free_fn_any)));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn node_dealloc(self: *py.PyObject) callconv(.C) void {
    const wrapper = @as(*NodeWrapper, @ptrCast(@alignCast(self)));
    // Only free if this payload was allocated by makeNodePyObject().
    const owned: *OwnedNodePayload = @alignCast(@fieldParentPtr("payload", wrapper.data));
    if (owned.magic == owned_magic_node) {
        std.heap.c_allocator.destroy(owned);
    }

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.C) void, @ptrCast(@alignCast(free_fn_any)));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn edge_dealloc(self: *py.PyObject) callconv(.C) void {
    const wrapper = @as(*EdgeWrapper, @ptrCast(@alignCast(self)));
    // Only free if this payload was allocated by makeEdgePyObject().
    const owned: *OwnedEdgePayload = @alignCast(@fieldParentPtr("payload", wrapper.data));
    if (owned.magic == owned_magic_edge) {
        std.heap.c_allocator.destroy(owned);
    }

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.C) void, @ptrCast(@alignCast(free_fn_any)));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn freeLiteral(literal: Literal) void {
    switch (literal) {
        .String => |value| {
            std.heap.c_allocator.free(@constCast(value));
        },
        else => {},
    }
}

fn pyObjectToLiteral(obj: ?*py.PyObject) !Literal {
    if (obj == null) return error.UnsupportedType;

    if (obj == py.Py_True()) return Literal{ .Bool = true };
    if (obj == py.Py_False()) return Literal{ .Bool = false };

    py.PyErr_Clear();
    const int_val = py.PyLong_AsLongLong(obj);
    if (py.PyErr_Occurred() == null) {
        const coerced: i64 = @intCast(int_val);
        return Literal{ .Int = coerced };
    }

    py.PyErr_Clear();
    const float_val = py.PyFloat_AsDouble(obj);
    if (py.PyErr_Occurred() == null) {
        return Literal{ .Float = float_val };
    }

    const str_ptr = py.PyUnicode_AsUTF8(obj);
    if (str_ptr != null) {
        const slice = std.mem.span(str_ptr.?);
        const copy = std.heap.c_allocator.dupe(u8, slice) catch return error.OutOfMemory;
        py.PyErr_Clear();
        return Literal{ .String = copy };
    }

    py.PyErr_Clear();
    return error.UnsupportedType;
}

fn literalToPyObject(literal: Literal) ?*py.PyObject {
    return switch (literal) {
        .Int => |value| blk: {
            const casted: c_longlong = @intCast(value);
            break :blk py.PyLong_FromLongLong(casted);
        },
        .Uint => |value| py.PyLong_FromUnsignedLongLong(value),
        .Float => |value| py.PyFloat_FromDouble(value),
        .String => |value| blk: {
            const ptr: [*c]const u8 = if (value.len == 0)
                ""
            else
                @ptrCast(value.ptr);
            const length: isize = @intCast(value.len);
            break :blk py.PyUnicode_FromStringAndSize(ptr, length);
        },
        .Bool => |value| blk: {
            const py_bool = if (value) py.Py_True() else py.Py_False();
            py.Py_INCREF(py_bool);
            break :blk py_bool;
        },
    };
}

fn literalMapToPyDict(map: std.StringHashMap(Literal)) ?*py.PyObject {
    const py_map = py.PyDict_New();
    if (py_map == null) {
        return null;
    }
    var it = map.iterator();
    while (it.next()) |e| {
        // Avoid allocating a 0-terminated copy for the key (that would leak).
        const key_slice = e.key_ptr.*;
        const key_ptr: [*c]const u8 = if (key_slice.len == 0) "" else @ptrCast(key_slice.ptr);
        const key_obj = py.PyUnicode_FromStringAndSize(key_ptr, @intCast(key_slice.len)) orelse return null;
        const val_obj = literalToPyObject(e.value_ptr.*) orelse {
            py.Py_DECREF(key_obj);
            return null;
        };
        if (py.PyDict_SetItem(py_map.?, key_obj, val_obj) < 0) {
            py.Py_DECREF(val_obj);
            py.Py_DECREF(key_obj);
            return null;
        }
        py.Py_DECREF(val_obj);
        py.Py_DECREF(key_obj);
    }
    return py_map.?;
}

fn shouldSkip(key: []const u8, skip: []const []const u8) bool {
    for (skip) |k| {
        if (std.mem.eql(u8, key, k)) return true;
    }
    return false;
}

fn applyAttributes(dynamic: *graph.graph.DynamicAttributes, kwargs: ?*py.PyObject, skip: []const []const u8) !void {
    if (kwargs == null or kwargs == py.Py_None()) return;

    var pos: isize = 0;
    var key_obj: ?*py.PyObject = null;
    var value_obj: ?*py.PyObject = null;

    while (py.PyDict_Next(kwargs, &pos, &key_obj, &value_obj) != 0) {
        const key_c = py.PyUnicode_AsUTF8(key_obj);
        if (key_c == null) {
            py.PyErr_SetString(py.PyExc_TypeError, "Attribute names must be str");
            return error.InvalidKey;
        }
        const key_slice = std.mem.span(key_c.?);
        if (shouldSkip(key_slice, skip)) {
            continue;
        }

        const key_copy = std.heap.c_allocator.dupe(u8, key_slice) catch {
            py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
            return error.OutOfMemory;
        };

        const literal = pyObjectToLiteral(value_obj) catch |err| {
            std.heap.c_allocator.free(key_copy);
            switch (err) {
                error.OutOfMemory => py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory"),
                error.UnsupportedType => py.PyErr_SetString(py.PyExc_TypeError, "Unsupported attribute literal"),
            }
            return err;
        };

        dynamic.put(key_copy, literal);
    }
}

fn nodeAttributesToPyDict(node: graph.graph.NodeReference) ?*py.PyObject {
    const dict = py.PyDict_New() orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate attribute dict");
        return null;
    };

    const Visitor = struct {
        dict: *py.PyObject,
        had_error: bool = false,

        pub fn visit(ctx_ptr: *anyopaque, key: []const u8, literal: Literal, _: bool) void {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            if (ctx.had_error) return;

            const key_ptr: [*c]const u8 = if (key.len == 0)
                ""
            else
                @ptrCast(key.ptr);

            const key_obj = py.PyUnicode_FromStringAndSize(key_ptr, @intCast(key.len)) orelse {
                ctx.had_error = true;
                return;
            };

            const value_obj = literalToPyObject(literal) orelse {
                ctx.had_error = true;
                py.Py_DECREF(key_obj);
                return;
            };

            if (py.PyDict_SetItem(ctx.dict, key_obj, value_obj) < 0) {
                ctx.had_error = true;
            }

            py.Py_DECREF(value_obj);
            py.Py_DECREF(key_obj);
        }
    };

    var visitor_ctx = Visitor{ .dict = dict };
    node.visit_attributes(&visitor_ctx, Visitor.visit);

    if (visitor_ctx.had_error) {
        py.Py_DECREF(dict);
        return null;
    }

    return dict;
}

// ====================================================================================================================

fn wrap_node_get_attr() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_attr",
            .doc = "Return attribute value for the given key",
            .args_def = struct {
                key: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("NodeReference", &node_type, NodeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const key_slice = bind.unwrap_str(kwarg_obj.key) orelse return null;

            if (wrapper.data.get(key_slice)) |value| {
                return literalToPyObject(value) orelse null;
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_node_get_dynamic_attrs() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_dynamic_attrs",
            .doc = "Return a dictionary of dynamic attributes",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("NodeReference", &node_type, NodeWrapper, self) orelse return null;

            var map = std.StringHashMap(Literal).init(std.heap.c_allocator);
            defer map.deinit();

            const Visitor = struct {
                map: std.StringHashMap(Literal),

                pub fn visit(ctx_ptr: *anyopaque, key: []const u8, literal: Literal, dynamic: bool) void {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    if (!dynamic) return;
                    ctx.map.put(key, literal) catch @panic("OOM dynamic attributes put");
                }
            };

            var visitor_ctx = Visitor{ .map = map };
            wrapper.data.visit_attributes(&visitor_ctx, Visitor.visit);

            return literalMapToPyDict(visitor_ctx.map) orelse return null;
        }
    };
}

fn wrap_node_get_uuid() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_uuid",
            .doc = "Return the unique identifier of the node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("NodeReference", &node_type, NodeWrapper, self) orelse return null;
            const uuid = wrapper.data.get_uuid();
            return py.PyLong_FromUnsignedLongLong(uuid);
        }
    };
}

fn wrap_node_is_same() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_same",
            .doc = "Compare two Node instances",
            .args_def = struct {
                other: *graph.graph.NodeReference,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = NodeWrapper, .storage = &node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("NodeReference", &node_type, NodeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const same = wrapper.data.is_same(kwarg_obj.other.*);
            return bind.wrap_bool(same);
        }
    };
}

fn wrap_node_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new Node",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const node_ref = graph.graph.NodeReference.init();
            return makeNodePyObject(node_ref);
        }
    };
}

fn wrap_node(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_node_create(),
        wrap_node_get_attr(),
        wrap_node_get_dynamic_attrs(),
        wrap_node_get_uuid(),
        wrap_node_is_same(),
    };
    bind.wrap_namespace_struct(root, graph.graph.NodeReference, extra_methods);
    node_type = type_registry.getRegisteredTypeObject("NodeReference");

    if (node_type) |typ| {
        typ.tp_dealloc = @ptrCast(&node_dealloc);
    }
}

fn wrap_edge_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new Edge",
            .args_def = struct {
                source: *graph.graph.NodeReference,
                target: *graph.graph.NodeReference,
                edge_type: *py.PyObject,
                directional: ?*py.PyObject = null,
                name: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .source = bind.ARG{ .Wrapper = NodeWrapper, .storage = &node_type },
                    .target = bind.ARG{ .Wrapper = NodeWrapper, .storage = &node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const edge_type_value: graph.graph.Edge.EdgeType = bind.unwrap_int(graph.graph.Edge.EdgeType, kwarg_obj.edge_type) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Edge type out of range");
                return null;
            } orelse return null;

            var directional_value: ?bool = null;
            if (kwarg_obj.directional) |directional_obj| {
                if (directional_obj != py.Py_None()) {
                    const truth = py.PyObject_IsTrue(directional_obj);
                    if (truth == -1) return null;
                    directional_value = truth == 1;
                }
            }

            var name_copy: ?[]const u8 = null;
            if (kwarg_obj.name) |name_obj| {
                if (name_obj != py.Py_None()) {
                    name_copy = bind.unwrap_str_copy(name_obj) orelse return null;
                }
            }

            const edge_ref = graph.graph.EdgeReference.init(kwarg_obj.source.*, kwarg_obj.target.*, edge_type_value);

            var success = false;
            defer if (!success) {
                if (name_copy) |n| std.heap.c_allocator.free(@constCast(n));
                // EdgeReference is a value type, no deinit needed
            };

            if (directional_value) |d| {
                edge_ref.set_attribute_directional(d);
            }
            edge_ref.set_attribute_name(name_copy);

            const skip = &.{ "source", "target", "edge_type", "directional", "name" };
            var dynamic = graph.graph.DynamicAttributes.init_on_stack();
            applyAttributes(&dynamic, kwargs, skip) catch {
                return null;
            };
            edge_ref.copy_dynamic_attributes_into(&dynamic);

            success = true;
            return makeEdgePyObject(edge_ref);
        }
    };
}

fn wrap_edge_get_attr() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_attr",
            .doc = "Return attribute value for the given key",
            .args_def = struct {
                key: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("EdgeReference", &edge_type, EdgeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const key_slice = bind.unwrap_str(kwarg_obj.key) orelse return null;
            if (wrapper.data.get(key_slice)) |value| {
                return literalToPyObject(value) orelse null;
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_is_same() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_same",
            .doc = "Compare two Edge instances",
            .args_def = struct {
                other: *graph.graph.EdgeReference,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &edge_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("EdgeReference", &edge_type, EdgeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const same = wrapper.data.is_same(kwarg_obj.other.*);
            return bind.wrap_bool(same);
        }
    };
}

fn wrap_edge_get_source() type {
    return struct {
        pub const descr = method_descr{
            .name = "source",
            .doc = "Return the source Node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("EdgeReference", &edge_type, EdgeWrapper, self) orelse return null;
            return makeNodePyObject(wrapper.data.get_source_node());
        }
    };
}

fn wrap_edge_get_target() type {
    return struct {
        pub const descr = method_descr{
            .name = "target",
            .doc = "Return the target Node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("EdgeReference", &edge_type, EdgeWrapper, self) orelse return null;
            return makeNodePyObject(wrapper.data.get_target_node());
        }
    };
}

fn wrap_edge_get_edge_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "edge_type",
            .doc = "Return the edge type identifier",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("EdgeReference", &edge_type, EdgeWrapper, self) orelse return null;
            return bind.wrap_int(wrapper.data.get_attribute_edge_type());
        }
    };
}

fn wrap_edge_get_directional() type {
    return struct {
        pub const descr = method_descr{
            .name = "directional",
            .doc = "Return whether the edge is directional",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("EdgeReference", &edge_type, EdgeWrapper, self) orelse return null;
            return bind.wrap_bool(wrapper.data.get_attribute_directional());
        }
    };
}

fn wrap_edge_get_name() type {
    return struct {
        pub const descr = method_descr{
            .name = "name",
            .doc = "Return the edge name if present",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("EdgeReference", &edge_type, EdgeWrapper, self) orelse return null;
            return bind.wrap_str(wrapper.data.get_attribute_name());
        }
    };
}

fn wrap_edge(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_create(),
        wrap_edge_get_attr(),
        wrap_edge_is_same(),
        wrap_edge_get_source(),
        wrap_edge_get_target(),
        wrap_edge_get_edge_type(),
        wrap_edge_get_directional(),
        wrap_edge_get_name(),
    };
    bind.wrap_namespace_struct(root, graph.graph.EdgeReference, extra_methods);
    edge_type = type_registry.getRegisteredTypeObject("EdgeReference");

    if (edge_type) |typ| {
        typ.tp_dealloc = @ptrCast(&edge_dealloc);
    }
}

fn wrap_bound_node_get_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "node",
            .doc = "Return the underlying Node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BoundNodeReference", &bound_node_type, BoundNodeWrapper, self) orelse return null;
            return makeNodePyObject(wrapper.data.node);
        }
    };
}

fn wrap_bound_node_get_graph() type {
    return struct {
        pub const descr = method_descr{
            .name = "g",
            .doc = "Return the owning GraphView",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BoundNodeReference", &bound_node_type, BoundNodeWrapper, self) orelse return null;
            return bind.wrap_obj("GraphView", &graph_view_type, GraphViewWrapper, wrapper.data.g);
        }
    };
}

fn wrap_bound_node_visit_edges_of_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_edges_of_type",
            .doc = "Visit edges of a specific type",
            .args_def = struct {
                edge_type: *py.PyObject,
                ctx: *py.PyObject,
                f: *py.PyObject,
                directed: ?*py.PyObject = null,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BoundNodeReference", &bound_node_type, BoundNodeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const edge_type_value: graph.graph.Edge.EdgeType = bind.unwrap_int(graph.graph.Edge.EdgeType, kwarg_obj.edge_type) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Edge type out of range");
                return null;
            } orelse return null;

            var directed_value: ?bool = null;
            if (kwarg_obj.directed) |directed_obj| {
                if (directed_obj != py.Py_None()) {
                    directed_value = bind.unwrap_bool(directed_obj);
                }
            }

            py.Py_INCREF(kwarg_obj.ctx);
            py.Py_INCREF(kwarg_obj.f);

            var visit_ctx = BoundEdgeVisitor{ .py_ctx = kwarg_obj.ctx, .callable = kwarg_obj.f };
            const result = wrapper.data.g.visit_edges_of_type(wrapper.data.node, edge_type_value, void, @ptrCast(&visit_ctx), BoundEdgeVisitor.call, directed_value);

            py.Py_DECREF(kwarg_obj.ctx);
            py.Py_DECREF(kwarg_obj.f);

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_edges_of_type failed");
                    return null;
                },
                else => {},
            }

            return bind.wrap_none();
        }
    };
}

fn bound_node_hash(self: *py.PyObject) callconv(.C) isize {
    const wrapper = @as(*BoundNodeWrapper, @ptrCast(@alignCast(self)));
    const bound_node = wrapper.data;
    // Use the node's UUID as the hash
    const uuid: usize = bound_node.node.get_uuid();
    return @intCast(uuid);
}

fn bound_node_repr(self: *py.PyObject) callconv(.C) ?*py.PyObject {
    const wrapper = @as(*BoundNodeWrapper, @ptrCast(@alignCast(self)));
    const bound_node = wrapper.data;

    var buf: [128]u8 = undefined;
    const str = std.fmt.bufPrintZ(&buf, "BoundNode(node=0x{x}, graph=0x{x})", .{
        bound_node.node.get_uuid(),
        bound_node.g.get_self_node().node.get_uuid(),
    }) catch {
        return null;
    };

    return py.PyUnicode_FromString(str);
}

fn bound_node_richcompare(self: *py.PyObject, other: *py.PyObject, op: c_int) callconv(.C) ?*py.PyObject {
    // Only support equality (op == Py_EQ = 2) and inequality (op == Py_NE = 3)
    if (op != 2 and op != 3) {
        py.Py_INCREF(py.Py_NotImplemented());
        return py.Py_NotImplemented();
    }

    const self_wrapper = @as(*BoundNodeWrapper, @ptrCast(@alignCast(self)));

    // Check if other is also a BoundNodeReference
    if (py.Py_TYPE(other) != py.Py_TYPE(self)) {
        const result = if (op == 2) py.Py_False() else py.Py_True();
        py.Py_INCREF(result);
        return result;
    }

    const other_wrapper = @as(*BoundNodeWrapper, @ptrCast(@alignCast(other)));

    // Use the same comparison logic as NodeReference.is_same()
    const same = self_wrapper.data.node.is_same(other_wrapper.data.node);
    const result = if ((op == 2 and same) or (op == 3 and !same)) py.Py_True() else py.Py_False();
    py.Py_INCREF(result);
    return result;
}

fn wrap_bound_node(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_bound_node_get_node(),
        wrap_bound_node_get_graph(),
        wrap_bound_node_visit_edges_of_type(),
    };
    bind.wrap_namespace_struct(root, graph.graph.BoundNodeReference, extra_methods);
    bound_node_type = type_registry.getRegisteredTypeObject("BoundNodeReference");

    if (bound_node_type) |typ| {
        // Add hash and comparison support for dictionary keys
        typ.tp_hash = @ptrCast(@constCast(&bound_node_hash));
        typ.tp_richcompare = @ptrCast(@constCast(&bound_node_richcompare));
        typ.tp_dealloc = @ptrCast(&bound_node_dealloc);
        typ.tp_repr = @ptrCast(&bound_node_repr);

        typ.ob_base.ob_base.ob_refcnt += 1;
        if (py.PyModule_AddObject(root, "BoundNode", @ptrCast(typ)) < 0) {
            typ.ob_base.ob_base.ob_refcnt -= 1;
        }
    }
}

fn wrap_bound_edge_get_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "edge",
            .doc = "Return the underlying Edge",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BoundEdgeReference", &bound_edge_type, BoundEdgeWrapper, self) orelse return null;
            return makeEdgePyObject(wrapper.data.edge);
        }
    };
}

fn wrap_bound_edge_get_graph() type {
    return struct {
        pub const descr = method_descr{
            .name = "g",
            .doc = "Return the owning GraphView",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BoundEdgeReference", &bound_edge_type, BoundEdgeWrapper, self) orelse return null;
            return bind.wrap_obj("GraphView", &graph_view_type, GraphViewWrapper, wrapper.data.g);
        }
    };
}

fn bound_edge_repr(self: *py.PyObject) callconv(.C) ?*py.PyObject {
    const wrapper = @as(*BoundEdgeWrapper, @ptrCast(@alignCast(self)));
    const bound_edge = wrapper.data;

    var buf: [128]u8 = undefined;
    const str = std.fmt.bufPrintZ(&buf, "BoundEdge(src=0x{x}, tgt=0x{x}, graph=0x{x})", .{
        bound_edge.edge.get_source_node().get_uuid(),
        bound_edge.edge.get_target_node().get_uuid(),
        bound_edge.g.get_self_node().node.get_uuid(),
    }) catch {
        return null;
    };

    return py.PyUnicode_FromString(str);
}

fn wrap_bound_edge(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_bound_edge_get_edge(),
        wrap_bound_edge_get_graph(),
    };
    bind.wrap_namespace_struct(root, graph.graph.BoundEdgeReference, extra_methods);
    bound_edge_type = type_registry.getRegisteredTypeObject("BoundEdgeReference");

    if (bound_edge_type) |typ| {
        typ.tp_dealloc = @ptrCast(&bound_edge_dealloc);
        typ.tp_repr = @ptrCast(&bound_edge_repr);
        typ.ob_base.ob_base.ob_refcnt += 1;
        if (py.PyModule_AddObject(root, "BoundEdge", @ptrCast(typ)) < 0) {
            typ.ob_base.ob_base.ob_refcnt -= 1;
        }
    }
}

fn wrap_bfs_path_get_length() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_length",
            .doc = "Get the number of edges in the path",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BFSPath", &bfs_path_type, BFSPathWrapper, self) orelse return null;
            const path = wrapper.data;
            return py.PyLong_FromLongLong(@intCast(path.traversed_edges.items.len));
        }
    };
}

fn wrap_bfs_path_get_start_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_start_node",
            .doc = "Get the start node of the path",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BFSPath", &bfs_path_type, BFSPathWrapper, self) orelse return null;
            const path = wrapper.data;
            return makeBoundNodePyObject(path.start_node);
        }
    };
}

fn wrap_bfs_path_get_end_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_end_node",
            .doc = "Get the end node of the path",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BFSPath", &bfs_path_type, BFSPathWrapper, self) orelse return null;
            const path = wrapper.data;
            return makeBoundNodePyObject(path.get_last_node());
        }
    };
}

fn wrap_bfs_path_get_edges() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_edges",
            .doc = "Get all edges in the path as a list",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BFSPath", &bfs_path_type, BFSPathWrapper, self) orelse return null;
            const path = wrapper.data;

            const edges_list = py.PyList_New(@intCast(path.traversed_edges.items.len));
            if (edges_list == null) return null;

            for (path.traversed_edges.items, 0..) |traversed_edge, i| {
                const py_edge = makeEdgePyObject(traversed_edge.edge);
                if (py_edge == null or py.PyList_SetItem(edges_list, @intCast(i), py_edge) < 0) {
                    if (py_edge != null) py.Py_DECREF(py_edge.?);
                    py.Py_DECREF(edges_list.?);
                    return null;
                }
            }

            return edges_list;
        }
    };
}

fn bfs_path_dealloc(self: *py.PyObject) callconv(.C) void {
    const wrapper = @as(*BFSPathWrapper, @ptrCast(@alignCast(self)));
    const path = wrapper.data;

    // Clean up the BFSPath
    path.deinit();

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.C) void, @ptrCast(@alignCast(free_fn_any)));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn wrap_bfs_path(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_bfs_path_get_length(),
        wrap_bfs_path_get_start_node(),
        wrap_bfs_path_get_end_node(),
        wrap_bfs_path_get_edges(),
    };
    bind.wrap_namespace_struct(root, graph.graph.BFSPath, extra_methods);
    bfs_path_type = type_registry.getRegisteredTypeObject("BFSPath");

    if (bfs_path_type) |typ| {
        typ.tp_dealloc = @ptrCast(&bfs_path_dealloc);
        typ.ob_base.ob_base.ob_refcnt += 1;
        if (py.PyModule_AddObject(root, "BFSPath", @ptrCast(typ)) < 0) {
            typ.ob_base.ob_base.ob_refcnt -= 1;
        }
    }
}

fn wrap_graphview_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new GraphView",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = self;
            _ = args;
            const allocator = std.heap.c_allocator;

            const graph_ptr = allocator.create(graph.graph.GraphView) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate GraphView");
                return null;
            };

            graph_ptr.* = graph.graph.GraphView.init(allocator);

            const pyobj = bind.wrap_obj("GraphView", &graph_view_type, GraphViewWrapper, graph_ptr);
            if (pyobj == null) {
                graph_ptr.deinit();
                allocator.destroy(graph_ptr);
            }

            return pyobj;
        }
    };
}

fn wrap_graphview_insert_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "insert_node",
            .doc = "Insert a Node into the graph",
            .args_def = struct {
                node: *graph.graph.NodeReference,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound = wrapper.data.insert_node(kwarg_obj.node.*);

            return makeBoundNodePyObject(bound);
        }
    };
}

fn wrap_graphview_insert_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "insert_edge",
            .doc = "Insert an Edge into the graph",
            .args_def = struct {
                edge: *graph.graph.EdgeReference,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &edge_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound = wrapper.data.insert_edge(kwarg_obj.edge.*) catch |err| {
                const msg = switch (err) {
                    error.SourceNodeNotInGraph => "Edge source node not in graph",
                    error.TargetNodeNotInGraph => "Edge target node not in graph",
                };
                py.PyErr_SetString(py.PyExc_ValueError, msg);
                return null;
            };

            return makeBoundEdgePyObject(bound);
        }
    };
}

fn wrap_graphview_bind() type {
    return struct {
        pub const descr = method_descr{
            .name = "bind",
            .doc = "Bind an existing Node to the graph",
            .args_def = struct {
                node: *graph.graph.NodeReference,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound = wrapper.data.bind(kwarg_obj.node.*);
            return makeBoundNodePyObject(bound);
        }
    };
}

fn wrap_graphview_get_node_count() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_node_count",
            .doc = "Get the number of nodes in the graph",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const count = wrapper.data.get_node_count();
            return py.PyLong_FromUnsignedLongLong(count);
        }
    };
}

fn wrap_graphview_get_subgraph_from_nodes() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_subgraph_from_nodes",
            .doc = "Create a subgraph containing only the specified nodes and their connecting edges",
            .args_def = struct {
                nodes: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            // Convert Python list to ArrayList of NodeReferences
            if (py.PyList_Check(kwarg_obj.nodes) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "nodes must be a list");
                return null;
            }

            const list_size = py.PyList_Size(kwarg_obj.nodes);
            var node_list = std.ArrayList(graph.graph.NodeReference).init(std.heap.c_allocator);
            defer node_list.deinit();

            var i: isize = 0;
            while (i < list_size) : (i += 1) {
                const item = py.PyList_GetItem(kwarg_obj.nodes, i);
                if (item == null) {
                    py.PyErr_SetString(py.PyExc_ValueError, "Failed to get list item");
                    return null;
                }

                // Unwrap the BoundNode to get the Node
                const bound_wrapper = bind.castWrapper("BoundNodeReference", &bound_node_type, BoundNodeWrapper, item) orelse {
                    py.PyErr_SetString(py.PyExc_TypeError, "nodes must be a list of BoundNode");
                    return null;
                };

                node_list.append(bound_wrapper.data.node) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Failed to append node");
                    return null;
                };
            }

            // Allocate memory for the result GraphView
            const allocator = std.heap.c_allocator;
            const result_ptr = allocator.create(graph.graph.GraphView) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate GraphView");
                return null;
            };

            result_ptr.* = wrapper.data.get_subgraph_from_nodes(node_list);

            const pyobj = bind.wrap_obj("GraphView", &graph_view_type, GraphViewWrapper, result_ptr);
            if (pyobj == null) {
                result_ptr.deinit();
                allocator.destroy(result_ptr);
            }

            return pyobj;
        }
    };
}

fn wrap_graphview_insert_subgraph() type {
    return struct {
        pub const descr = method_descr{
            .name = "insert_subgraph",
            .doc = "Insert all nodes and edges from a subgraph into this graph",
            .args_def = struct {
                subgraph: *graph.graph.GraphView,

                pub const fields_meta = .{
                    .subgraph = bind.ARG{ .Wrapper = GraphViewWrapper, .storage = &graph_view_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            wrapper.data.insert_subgraph(kwarg_obj.subgraph);

            return bind.wrap_none();
        }
    };
}

fn wrap_graphview_get_nodes() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_nodes",
            .doc = "Get all nodes in the graph as a list of BoundNode",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;

            // Count nodes first
            const node_count = wrapper.data.nodes.count();
            const nodes_list = py.PyList_New(@intCast(node_count));
            if (nodes_list == null) return null;

            // Iterate over nodes in the graph
            var i: usize = 0;
            var key_it = wrapper.data.nodes.keyIterator();
            while (key_it.next()) |node_ptr| {
                const bound_node = graph.graph.BoundNodeReference{
                    .node = node_ptr.*,
                    .g = wrapper.data,
                };
                const py_node = makeBoundNodePyObject(bound_node);
                if (py_node == null or py.PyList_SetItem(nodes_list, @intCast(i), py_node) < 0) {
                    if (py_node != null) py.Py_DECREF(py_node.?);
                    py.Py_DECREF(nodes_list.?);
                    return null;
                }
                i += 1;
            }

            return nodes_list;
        }
    };
}

fn wrap_graphview_get_self_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_self_node",
            .doc = "Get the self-referential node of the graph",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const bound = wrapper.data.get_self_node();
            return makeBoundNodePyObject(bound);
        }
    };
}

fn wrap_graphview_destroy() type {
    return struct {
        pub const descr = method_descr{
            .name = "destroy",
            .doc = "Destroy the GraphView and free all resources. The object should not be used after calling this.",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            wrapper.data.deinit();
            allocator.destroy(wrapper.data);
            return bind.wrap_none();
        }
    };
}

fn wrap_graphview_create_and_insert_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "create_and_insert_node",
            .doc = "Create a new Node and insert it into the graph",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const bound = wrapper.data.create_and_insert_node();
            return makeBoundNodePyObject(bound);
        }
    };
}

fn graphview_repr(self: ?*py.PyObject) callconv(.C) ?*py.PyObject {
    const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
    const node_count = wrapper.data.get_node_count();
    const edge_count = wrapper.data.get_edge_count();

    var buf: [64]u8 = undefined;
    const str = std.fmt.bufPrintZ(&buf, "GraphView(id=0x{x}, |V|={d}, |E|={d})", .{
        wrapper.data.get_self_node().node.get_uuid(),
        node_count,
        edge_count,
    }) catch {
        return null;
    };

    return py.PyUnicode_FromString(str);
}

fn wrap_graphview(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_graphview_create(),
        wrap_graphview_insert_node(),
        wrap_graphview_insert_edge(),
        wrap_graphview_bind(),
        wrap_graphview_get_node_count(),
        wrap_graphview_get_nodes(),
        wrap_graphview_get_self_node(),
        wrap_graphview_get_subgraph_from_nodes(),
        wrap_graphview_insert_subgraph(),
        wrap_graphview_destroy(),
        wrap_graphview_create_and_insert_node(),
    };
    bind.wrap_namespace_struct(root, graph.graph.GraphView, extra_methods);
    graph_view_type = type_registry.getRegisteredTypeObject("GraphView");

    if (graph_view_type) |typ| {
        typ.tp_repr = @ptrCast(&graphview_repr);
    }
}

fn wrap_graph_module(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, py.PYTHON_API_VERSION);
    if (module == null) {
        return null;
    }

    wrap_node(module.?);
    wrap_edge(module.?);
    wrap_bound_node(module.?);
    wrap_bound_edge(module.?);
    wrap_bfs_path(module.?);
    wrap_graphview(module.?);

    if (py.PyModule_AddObject(root, "graph", module) < 0) {
        return null;
    }

    return module;
}

// ====================================================================================================================

// Main module methods
var main_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

// Main module definition
var main_module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "graph",
    .m_doc = "Auto-generated Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &main_methods,
};

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, py.PYTHON_API_VERSION);
    if (module == null) {
        return null;
    }

    _ = wrap_graph_module(module.?);
    return module;
}
