const std = @import("std");
const graph = @import("graph");
const visitor = graph.visitor;
const pyzig = @import("pyzig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const type_registry = pyzig.type_registry;
const method_descr = bind.method_descr;

pub fn makeBoundNodePyObject(value: graph.graph.BoundNodeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const ptr = allocator.create(graph.graph.BoundNodeReference) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    ptr.* = value;

    const pyobj = bind.wrap_obj("BoundNodeReference", &bound_node_type, BoundNodeWrapper, ptr);
    if (pyobj == null) {
        allocator.destroy(ptr);
    }
    return pyobj;
}

pub fn makeBoundEdgePyObject(value: graph.graph.BoundEdgeReference) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const ptr = allocator.create(graph.graph.BoundEdgeReference) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    ptr.* = value;

    const pyobj = bind.wrap_obj("BoundEdgeReference", &bound_edge_type, BoundEdgeWrapper, ptr);
    if (pyobj == null) {
        allocator.destroy(ptr);
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
pub const NodeWrapper = bind.PyObjectWrapper(graph.graph.Node);
pub const EdgeWrapper = bind.PyObjectWrapper(graph.graph.Edge);
pub const BoundNodeWrapper = bind.PyObjectWrapper(graph.graph.BoundNodeReference);
pub const BoundEdgeWrapper = bind.PyObjectWrapper(graph.graph.BoundEdgeReference);

pub var graph_view_type: ?*py.PyTypeObject = null;
pub var node_type: ?*py.PyTypeObject = null;
pub var edge_type: ?*py.PyTypeObject = null;
pub var bound_node_type: ?*py.PyTypeObject = null;
pub var bound_edge_type: ?*py.PyTypeObject = null;

const Literal = graph.graph.Literal;

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
        // Ensure the key is 0-terminated before passing to Python C API
        const key_slice = e.key_ptr.*;
        const key_str = pyzig.util.terminateString(std.heap.c_allocator, key_slice) catch return null;
        if (py.PyDict_SetItemString(py_map.?, key_str, literalToPyObject(e.value_ptr.*)) < 0) {
            return null;
        }
    }
    py.Py_INCREF(py_map.?);
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

        dynamic.values.put(key_copy, literal) catch {
            std.heap.c_allocator.free(key_copy);
            freeLiteral(literal);
            py.PyErr_SetString(py.PyExc_MemoryError, "Failed to store attribute");
            return error.OutOfMemory;
        };
    }
}

// ====================================================================================================================

fn wrap_node_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new Node",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            const allocator = std.heap.c_allocator;
            const node = graph.graph.Node.init(allocator) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate Node");
                return null;
            };

            var success = false;
            defer if (!success) {
                node.deinit();
            };

            applyAttributes(&node.attributes.dynamic, kwargs, &.{}) catch {
                return null;
            };

            success = true;
            return bind.wrap_obj("Node", &node_type, NodeWrapper, node);
        }
    };
}

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
            const wrapper = bind.castWrapper("Node", &node_type, NodeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const key_slice = bind.unwrap_str(kwarg_obj.key) orelse return null;

            if (wrapper.data.attributes.dynamic.values.get(key_slice)) |value| {
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
            const wrapper = bind.castWrapper("Node", &node_type, NodeWrapper, self) orelse return null;

            const zig_map = wrapper.data.attributes.dynamic.values;

            const py_map = literalMapToPyDict(zig_map) orelse return null;
            return py_map;
        }
    };
}
fn wrap_node_is_same() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_same",
            .doc = "Compare two Node instances",
            .args_def = struct {
                other: *graph.graph.Node,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = NodeWrapper, .storage = &node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("Node", &node_type, NodeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const same = graph.graph.Node.is_same(wrapper.data, kwarg_obj.other);
            return bind.wrap_bool(same);
        }
    };
}

fn wrap_node(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_node_create(),
        wrap_node_get_attr(),
        wrap_node_get_dynamic_attrs(),
        wrap_node_is_same(),
    };
    bind.wrap_namespace_struct(root, graph.graph.Node, extra_methods);
    node_type = type_registry.getRegisteredTypeObject("Node");
}

fn wrap_edge_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new Edge",
            .args_def = struct {
                source: *graph.graph.Node,
                target: *graph.graph.Node,
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

            const edge_type_value: graph.graph.Edge.EdgeType = bind.unwrap_int(graph.graph.Edge.EdgeType, kwarg_obj.edge_type) orelse return null;

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

            const allocator = std.heap.c_allocator;
            const edge_ptr = graph.graph.Edge.init(allocator, kwarg_obj.source, kwarg_obj.target, edge_type_value) catch {
                if (name_copy) |n| std.heap.c_allocator.free(@constCast(n));
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate Edge");
                return null;
            };

            var success = false;
            defer if (!success) {
                if (name_copy) |n| std.heap.c_allocator.free(@constCast(n));
                edge_ptr.deinit();
            };

            edge_ptr.attributes.directional = directional_value;
            edge_ptr.attributes.name = name_copy;

            const skip = &.{ "source", "target", "edge_type", "directional", "name" };
            applyAttributes(&edge_ptr.attributes.dynamic, kwargs, skip) catch {
                return null;
            };

            success = true;
            return bind.wrap_obj("Edge", &edge_type, EdgeWrapper, edge_ptr);
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
            const wrapper = bind.castWrapper("Edge", &edge_type, EdgeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const key_slice = bind.unwrap_str(kwarg_obj.key) orelse return null;
            if (wrapper.data.attributes.dynamic.values.get(key_slice)) |value| {
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
                other: *graph.graph.Edge,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &edge_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("Edge", &edge_type, EdgeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const same = graph.graph.Edge.is_same(wrapper.data, kwarg_obj.other);
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
            const wrapper = bind.castWrapper("Edge", &edge_type, EdgeWrapper, self) orelse return null;
            return bind.wrap_obj("Node", &node_type, NodeWrapper, wrapper.data.source);
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
            const wrapper = bind.castWrapper("Edge", &edge_type, EdgeWrapper, self) orelse return null;
            return bind.wrap_obj("Node", &node_type, NodeWrapper, wrapper.data.target);
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
            const wrapper = bind.castWrapper("Edge", &edge_type, EdgeWrapper, self) orelse return null;
            return bind.wrap_int(wrapper.data.attributes.edge_type);
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
            const wrapper = bind.castWrapper("Edge", &edge_type, EdgeWrapper, self) orelse return null;
            return bind.wrap_bool(wrapper.data.attributes.directional.?);
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
            const wrapper = bind.castWrapper("Edge", &edge_type, EdgeWrapper, self) orelse return null;
            return bind.wrap_str(wrapper.data.attributes.name);
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
    bind.wrap_namespace_struct(root, graph.graph.Edge, extra_methods);
    edge_type = type_registry.getRegisteredTypeObject("Edge");
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
            return bind.wrap_obj("Node", &node_type, NodeWrapper, wrapper.data.node);
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
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("BoundNodeReference", &bound_node_type, BoundNodeWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const edge_type_value: graph.graph.Edge.EdgeType = bind.unwrap_int(graph.graph.Edge.EdgeType, kwarg_obj.edge_type) orelse return null;

            py.Py_INCREF(kwarg_obj.ctx);
            py.Py_INCREF(kwarg_obj.f);

            var visit_ctx = BoundEdgeVisitor{ .py_ctx = kwarg_obj.ctx, .callable = kwarg_obj.f };
            const result = wrapper.data.visit_edges_of_type(edge_type_value, void, @ptrCast(&visit_ctx), BoundEdgeVisitor.call);

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

fn wrap_bound_node(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_bound_node_get_node(),
        wrap_bound_node_get_graph(),
        wrap_bound_node_visit_edges_of_type(),
    };
    bind.wrap_namespace_struct(root, graph.graph.BoundNodeReference, extra_methods);
    bound_node_type = type_registry.getRegisteredTypeObject("BoundNodeReference");

    if (bound_node_type) |typ| {
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
            return bind.wrap_obj("Edge", &edge_type, EdgeWrapper, wrapper.data.edge);
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

fn wrap_bound_edge(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_bound_edge_get_edge(),
        wrap_bound_edge_get_graph(),
    };
    bind.wrap_namespace_struct(root, graph.graph.BoundEdgeReference, extra_methods);
    bound_edge_type = type_registry.getRegisteredTypeObject("BoundEdgeReference");

    if (bound_edge_type) |typ| {
        typ.ob_base.ob_base.ob_refcnt += 1;
        if (py.PyModule_AddObject(root, "BoundEdge", @ptrCast(typ)) < 0) {
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
                node: *graph.graph.Node,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound = wrapper.data.insert_node(kwarg_obj.node) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to insert node");
                return null;
            };

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
                edge: *graph.graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &edge_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound = wrapper.data.insert_edge(kwarg_obj.edge) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to insert edge");
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
                node: *graph.graph.Node,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("GraphView", &graph_view_type, GraphViewWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound = wrapper.data.bind(kwarg_obj.node);
            return makeBoundNodePyObject(bound);
        }
    };
}

fn wrap_graphview(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_graphview_create(),
        wrap_graphview_insert_node(),
        wrap_graphview_insert_edge(),
        wrap_graphview_bind(),
    };
    bind.wrap_namespace_struct(root, graph.graph.GraphView, extra_methods);
    graph_view_type = type_registry.getRegisteredTypeObject("GraphView");
}

fn wrap_graph_module(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_node(module.?);
    wrap_edge(module.?);
    wrap_bound_node(module.?);
    wrap_bound_edge(module.?);
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
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    _ = wrap_graph_module(module.?);
    return module;
}
