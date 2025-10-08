const std = @import("std");
const pyzig = @import("pyzig");
const faebryk = @import("faebryk");
const graph_mod = @import("graph");
const graph_py = @import("../graph/graph_py.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const type_registry = pyzig.type_registry;
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeWrapper = graph_py.NodeWrapper;
const EdgeWrapper = graph_py.EdgeWrapper;
const BoundNodeWrapper = graph_py.BoundNodeWrapper;
const BoundEdgeWrapper = graph_py.BoundEdgeWrapper;

const EdgeCompositionWrapper = bind.PyObjectWrapper(faebryk.composition.EdgeComposition);
const EdgeTypeWrapper = bind.PyObjectWrapper(faebryk.node_type.EdgeType);
const EdgeNextWrapper = bind.PyObjectWrapper(faebryk.next.EdgeNext);
const EdgePointerWrapper = bind.PyObjectWrapper(faebryk.pointer.EdgePointer);
const TypeGraphWrapper = bind.PyObjectWrapper(faebryk.type.TypeGraph);

var edge_composition_type: ?*py.PyTypeObject = null;
var edge_type_type: ?*py.PyTypeObject = null;
var edge_next_type: ?*py.PyTypeObject = null;
var edge_pointer_type: ?*py.PyTypeObject = null;
var type_graph_type: ?*py.PyTypeObject = null;

pub const method_descr = bind.method_descr;

// ====================================================================================================================

fn wrap_edge_composition_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new EdgeComposition",
            .args_def = struct {
                parent: *graph.Node,
                child: *graph.Node,
                child_identifier: *py.PyObject,

                pub const fields_meta = .{
                    .parent = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .child = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier_const: []const u8 = bind.unwrap_str_copy(kwarg_obj.child_identifier) orelse return null;

            const edge_ref = faebryk.composition.EdgeComposition.init(
                std.heap.c_allocator,
                kwarg_obj.parent,
                kwarg_obj.child,
                identifier_const,
            ) catch {
                std.heap.c_allocator.free(identifier_const);
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create EdgeComposition edge");
                return null;
            };

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                std.heap.c_allocator.free(identifier_const);
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_composition_is_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_instance",
            .doc = "Check if the object is an instance of EdgeComposition",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const is_match = faebryk.composition.EdgeComposition.is_instance(kwarg_obj.edge);
            return bind.wrap_bool(is_match);
        }
    };
}

fn wrap_edge_composition_visit_children_edges() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_children_edges",
            .doc = "Visit the children edges of the EdgeComposition",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                f: *py.PyObject,
                ctx: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            var visit_ctx = graph_py.BoundEdgeVisitor{
                .py_ctx = kwarg_obj.ctx,
                .callable = kwarg_obj.f,
            };

            const result = faebryk.composition.EdgeComposition.visit_children_edges(
                kwarg_obj.bound_node.*,
                @ptrCast(&visit_ctx),
                graph_py.BoundEdgeVisitor.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_children_edges failed");
                    return null;
                },
                else => {},
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_composition_get_parent_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_parent_edge",
            .doc = "Get the parent edge of the EdgeComposition",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const parent_edge = faebryk.composition.EdgeComposition.get_parent_edge(kwarg_obj.bound_node.*);
            if (parent_edge) |edge_ref| {
                return graph_py.makeBoundEdgePyObject(edge_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_composition_add_child() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_child",
            .doc = "Add a child to the EdgeComposition",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                child: *graph.Node,
                child_identifier: *py.PyObject,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .child = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier_c = py.PyUnicode_AsUTF8(kwarg_obj.child_identifier);
            if (identifier_c == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child_identifier must be a string");
                return null;
            }
            const identifier_slice = std.mem.span(identifier_c.?);

            const allocator = kwarg_obj.bound_node.g.allocator;
            const identifier_copy = allocator.dupe(u8, identifier_slice) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate child_identifier");
                return null;
            };

            const bound_edge = faebryk.composition.EdgeComposition.add_child(
                kwarg_obj.bound_node.*,
                kwarg_obj.child,
                identifier_copy,
            ) catch {
                allocator.free(identifier_copy);
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to add child edge");
                return null;
            };

            return graph_py.makeBoundEdgePyObject(bound_edge);
        }
    };
}

fn wrap_edge_composition_get_name() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_name",
            .doc = "Get the name of the EdgeComposition",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const name = faebryk.composition.EdgeComposition.get_name(kwarg_obj.edge) catch |err| {
                switch (err) {
                    error.InvalidEdgeType => {
                        py.PyErr_SetString(py.PyExc_TypeError, "edge is not an EdgeComposition edge");
                    },
                }
                return null;
            };

            const ptr: [*c]const u8 = if (name.len == 0) "" else @ptrCast(name.ptr);
            const py_str = py.PyUnicode_FromStringAndSize(ptr, @intCast(name.len));
            if (py_str == null) {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create Python string");
                return null;
            }

            return py_str;
        }
    };
}

fn wrap_edge_composition_get_tid() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_tid",
            .doc = "Get the tid of the EdgeComposition",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const tid = faebryk.composition.EdgeComposition.tid;
            return py.PyLong_FromLongLong(@intCast(tid));
        }
    };
}

fn wrap_edge_composition(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_composition_create(),
        wrap_edge_composition_is_instance(),
        wrap_edge_composition_visit_children_edges(),
        wrap_edge_composition_get_parent_edge(),
        wrap_edge_composition_add_child(),
        wrap_edge_composition_get_name(),
        wrap_edge_composition_get_tid(),
    };
    bind.wrap_namespace_struct(root, faebryk.composition.EdgeComposition, extra_methods);
    edge_composition_type = type_registry.getRegisteredTypeObject("EdgeComposition");
}

fn wrap_interface(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_edge_type_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new edge connecting a type node to an instance node",
            .args_def = struct {
                type_node: *graph.Node,
                instance_node: *graph.Node,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .instance_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const edge_ref = faebryk.node_type.EdgeType.init(
                std.heap.c_allocator,
                kwarg_obj.type_node,
                kwarg_obj.instance_node,
            ) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create edge");
                return null;
            };

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_type_is_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_instance",
            .doc = "Return True if the edge represents a type-instance relationship",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const is_match = faebryk.node_type.EdgeType.is_instance(kwarg_obj.edge);
            return bind.wrap_bool(is_match);
        }
    };
}

fn wrap_edge_type_visit_instance_edges() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_instance_edges",
            .doc = "Invoke a callback for each instance edge attached to the type node",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                f: *py.PyObject,
                ctx: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            var visit_ctx = graph_py.BoundEdgeVisitor{
                .py_ctx = kwarg_obj.ctx,
                .callable = kwarg_obj.f,
            };

            const result = faebryk.node_type.EdgeType.visit_instance_edges(
                kwarg_obj.bound_node.*,
                @ptrCast(&visit_ctx),
                graph_py.BoundEdgeVisitor.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_instance_edges failed");
                    return null;
                },
                else => {},
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_type_get_type_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_type_node",
            .doc = "Return the type node associated with the edge",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const node_ref = faebryk.node_type.EdgeType.get_type_node(kwarg_obj.edge);
            return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
        }
    };
}

fn wrap_edge_type_get_instance_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_instance_node",
            .doc = "Return the instance node associated with the edge, if any",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.node_type.EdgeType.get_instance_node(kwarg_obj.edge)) |instance| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, instance);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_type_get_type_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_type_edge",
            .doc = "Return the bound edge that links the instance to its type",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.node_type.EdgeType.get_type_edge(kwarg_obj.bound_node.*)) |edge_ref| {
                return graph_py.makeBoundEdgePyObject(edge_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_type_add_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_instance",
            .doc = "Insert a type-instance edge into the graph",
            .args_def = struct {
                bound_type_node: *graph.BoundNodeReference,
                bound_instance_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .bound_type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .bound_instance_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound_edge = faebryk.node_type.EdgeType.add_instance(
                kwarg_obj.bound_type_node.*,
                kwarg_obj.bound_instance_node.*,
            ) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to add instance edge");
                return null;
            };

            return graph_py.makeBoundEdgePyObject(bound_edge);
        }
    };
}

fn wrap_edge_type_get_tid() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_tid",
            .doc = "Return the edge type identifier used for type-instance edges",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const tid = faebryk.node_type.EdgeType.tid;
            return py.PyLong_FromLongLong(@intCast(tid));
        }
    };
}

fn wrap_edge_type_is_node_instance_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_node_instance_of",
            .doc = "Return True if the bound node represents an instance of the given type",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                node_type: *graph.Node,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .node_type = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const is_instance = faebryk.node_type.EdgeType.is_node_instance_of(
                kwarg_obj.bound_node.*,
                kwarg_obj.node_type,
            );
            return bind.wrap_bool(is_instance);
        }
    };
}

fn wrap_node_type(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_type_create(),
        wrap_edge_type_is_instance(),
        wrap_edge_type_visit_instance_edges(),
        wrap_edge_type_get_type_node(),
        wrap_edge_type_get_instance_node(),
        wrap_edge_type_get_type_edge(),
        wrap_edge_type_add_instance(),
        wrap_edge_type_get_tid(),
        wrap_edge_type_is_node_instance_of(),
    };
    bind.wrap_namespace_struct(root, faebryk.node_type.EdgeType, extra_methods);
    edge_type_type = type_registry.getRegisteredTypeObject("EdgeType");
}

fn wrap_edge_next_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a directional edge linking a node to its successor",
            .args_def = struct {
                previous_node: *graph.Node,
                next_node: *graph.Node,

                pub const fields_meta = .{
                    .previous_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .next_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const edge_ref = faebryk.next.EdgeNext.init(
                std.heap.c_allocator,
                kwarg_obj.previous_node,
                kwarg_obj.next_node,
            ) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create edge");
                return null;
            };

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_next_add_next() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_next",
            .doc = "Insert a next edge between two bound nodes",
            .args_def = struct {
                previous_node: *graph.BoundNodeReference,
                next_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .previous_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .next_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound_edge = faebryk.next.EdgeNext.add_next(
                kwarg_obj.previous_node.*,
                kwarg_obj.next_node.*,
            ) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to add next edge");
                return null;
            };

            return graph_py.makeBoundEdgePyObject(bound_edge);
        }
    };
}

fn wrap_edge_next_is_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_instance",
            .doc = "Return True if the edge is a Next edge",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const is_match = faebryk.next.EdgeNext.is_instance(kwarg_obj.edge);
            return bind.wrap_bool(is_match);
        }
    };
}

fn wrap_edge_next_get_previous_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_previous_node",
            .doc = "Return the source node of the next edge",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.next.EdgeNext.get_previous_node(kwarg_obj.edge)) |node_ref| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_next_get_next_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_next_node",
            .doc = "Return the target node of the next edge",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.next.EdgeNext.get_next_node(kwarg_obj.edge)) |node_ref| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_next_get_previous_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_previous_edge",
            .doc = "Return the incoming next edge for a bound node",
            .args_def = struct {
                node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.next.EdgeNext.get_previous_edge(kwarg_obj.node.*)) |edge_ref| {
                return graph_py.makeBoundEdgePyObject(edge_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_next_get_next_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_next_edge",
            .doc = "Return the outgoing next edge for a bound node",
            .args_def = struct {
                node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.next.EdgeNext.get_next_edge(kwarg_obj.node.*)) |edge_ref| {
                return graph_py.makeBoundEdgePyObject(edge_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_next_get_previous_node_from_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_previous_node_from_node",
            .doc = "Return the previous node connected via a next edge",
            .args_def = struct {
                node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.next.EdgeNext.get_previous_node_from_node(kwarg_obj.node.*)) |node_ref| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_next_get_next_node_from_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_next_node_from_node",
            .doc = "Return the next node connected via a next edge",
            .args_def = struct {
                node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.next.EdgeNext.get_next_node_from_node(kwarg_obj.node.*)) |node_ref| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_next(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_next_create(),
        wrap_edge_next_add_next(),
        wrap_edge_next_is_instance(),
        wrap_edge_next_get_previous_node(),
        wrap_edge_next_get_next_node(),
        wrap_edge_next_get_previous_edge(),
        wrap_edge_next_get_next_edge(),
        wrap_edge_next_get_previous_node_from_node(),
        wrap_edge_next_get_next_node_from_node(),
    };
    bind.wrap_namespace_struct(root, faebryk.next.EdgeNext, extra_methods);
    edge_next_type = type_registry.getRegisteredTypeObject("EdgeNext");
}

fn wrap_edge_pointer_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a pointer edge between two nodes",
            .args_def = struct {
                from_node: *graph.Node,
                to_node: *graph.Node,
                identifier: *py.PyObject,

                pub const fields_meta = .{
                    .from_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .to_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier_copy = bind.unwrap_str_copy(kwarg_obj.identifier) orelse return null;

            const edge_ref = faebryk.pointer.EdgePointer.init(
                std.heap.c_allocator,
                kwarg_obj.from_node,
                kwarg_obj.to_node,
                identifier_copy,
            ) catch {
                std.heap.c_allocator.free(identifier_copy);
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create pointer edge");
                return null;
            };

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                std.heap.c_allocator.free(identifier_copy);
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_pointer_is_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_instance",
            .doc = "Return True if the edge is a pointer edge",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const is_match = faebryk.pointer.EdgePointer.is_instance(kwarg_obj.edge);
            return bind.wrap_bool(is_match);
        }
    };
}

fn wrap_edge_pointer_get_referenced_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_referenced_node",
            .doc = "Return the node referenced by the pointer edge",
            .args_def = struct {
                edge: *graph.Edge,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.pointer.EdgePointer.get_referenced_node(kwarg_obj.edge)) |node_ref| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_pointer_resolve_reference() type {
    return struct {
        pub const descr = method_descr{
            .name = "resolve_reference",
            .doc = "Resolve the pointer relative to a base node",
            .args_def = struct {
                reference_node: *graph.Node,
                base_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .reference_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .base_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.pointer.EdgePointer.resolve_reference(
                kwarg_obj.reference_node,
                kwarg_obj.base_node.*,
            )) |node_ref| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_module(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_pointer(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_pointer_create(),
        wrap_edge_pointer_is_instance(),
        wrap_edge_pointer_get_referenced_node(),
        wrap_edge_pointer_resolve_reference(),
    };
    bind.wrap_namespace_struct(root, faebryk.pointer.EdgePointer, extra_methods);
    edge_pointer_type = type_registry.getRegisteredTypeObject("EdgePointer");
}

fn wrap_type_graph_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new TypeGraph",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            _ = kwargs;

            const tg_value = faebryk.type.TypeGraph.create_typegraph() catch {
                py.PyErr_SetString(py.PyExc_RuntimeError, "create_typegraph failed");
                return null;
            };

            const allocator = std.heap.c_allocator;
            const ptr = allocator.create(faebryk.type.TypeGraph) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            ptr.* = tg_value;

            const obj = bind.wrap_obj("TypeGraph", &type_graph_type, TypeGraphWrapper, ptr);
            if (obj == null) {
                allocator.destroy(ptr);
                return null;
            }

            return obj;
        }
    };
}

fn wrap_type_graph_init_type_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "init_type_node",
            .doc = "Create and register a new type node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            _ = kwargs;

            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;

            const bnode = faebryk.type.TypeGraph.init_type_node(wrapper.data) catch {
                py.PyErr_SetString(py.PyExc_RuntimeError, "init_type_node failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_type_graph_init_trait_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "init_trait_node",
            .doc = "Create and register a new trait node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            _ = kwargs;

            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;

            const bnode = faebryk.type.TypeGraph.init_trait_node(wrapper.data) catch {
                py.PyErr_SetString(py.PyExc_RuntimeError, "init_trait_node failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_type_graph_init_make_child_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "init_make_child_node",
            .doc = "Create a MakeChild node referencing the provided type",
            .args_def = struct {
                type_node: *graph.BoundNodeReference,
                identifier: *py.PyObject,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.identifier) orelse return null;

            const bnode = faebryk.type.TypeGraph.init_make_child_node(wrapper.data, kwarg_obj.type_node.*, identifier) catch {
                py.PyErr_SetString(py.PyExc_RuntimeError, "init_make_child_node failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_type_graph_init_reference_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "init_reference_node",
            .doc = "Create a Reference node optionally pointing to a type",
            .args_def = struct {
                type_node: ?*graph.BoundNodeReference = null,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            var maybe_bnode: ?graph.BoundNodeReference = null;
            if (kwarg_obj.type_node) |tb|
                maybe_bnode = tb.*;

            const bnode = faebryk.type.TypeGraph.init_reference_node(wrapper.data, maybe_bnode) catch {
                py.PyErr_SetString(py.PyExc_RuntimeError, "init_reference_node failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_type_graph_init_make_link_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "init_make_link_node",
            .doc = "Create a MakeLink node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            _ = kwargs;

            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;

            const bnode = faebryk.type.TypeGraph.init_make_link_node(wrapper.data) catch {
                py.PyErr_SetString(py.PyExc_RuntimeError, "init_make_link_node failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_type_graph_instantiate() type {
    return struct {
        pub const descr = method_descr{
            .name = "instantiate",
            .doc = "Instantiate the given type node into a graph",
            .args_def = struct {
                type_node: *graph.Node,
                graph_view: ?*graph.GraphView = null,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .graph_view = bind.ARG{ .Wrapper = graph_py.GraphViewWrapper, .storage = &graph_py.graph_view_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const graph_view = if (kwarg_obj.graph_view) |gv| gv else &wrapper.data.type_graph_view;

            const bnode = faebryk.type.TypeGraph.instantiate(wrapper.data, kwarg_obj.type_node, graph_view) catch {
                py.PyErr_SetString(py.PyExc_RuntimeError, "instantiate failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_type_graph_resolve_instance_reference() type {
    return struct {
        pub const descr = method_descr{
            .name = "resolve_instance_reference",
            .doc = "Resolve a reference node within the instance graph",
            .args_def = struct {
                reference_node: *graph.BoundNodeReference,
                base_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .reference_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .base_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.type.TypeGraph.resolve_instance_reference(kwarg_obj.reference_node.*, kwarg_obj.base_node.*)) |resolved| {
                return graph_py.makeBoundNodePyObject(resolved);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_type(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_type_graph_create(),
        wrap_type_graph_init_type_node(),
        wrap_type_graph_init_trait_node(),
        wrap_type_graph_init_make_child_node(),
        wrap_type_graph_init_reference_node(),
        wrap_type_graph_init_make_link_node(),
        wrap_type_graph_instantiate(),
        wrap_type_graph_resolve_instance_reference(),
    };
    bind.wrap_namespace_struct(root, faebryk.type.TypeGraph, extra_methods);
    type_graph_type = type_registry.getRegisteredTypeObject("TypeGraph");
}

fn wrap_trait(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_composition_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_edge_composition(module.?);

    if (py.PyModule_AddObject(root, "composition", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_interface_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_interface(module.?);

    if (py.PyModule_AddObject(root, "interface", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_module_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_module(module.?);

    if (py.PyModule_AddObject(root, "module", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_node_type_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_node_type(module.?);

    if (py.PyModule_AddObject(root, "node_type", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_next_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_edge_next(module.?);

    if (py.PyModule_AddObject(root, "next", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_pointer_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_pointer(module.?);

    if (py.PyModule_AddObject(root, "pointer", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_type_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_type(module.?);

    if (py.PyModule_AddObject(root, "type", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_trait_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_trait(module.?);

    if (py.PyModule_AddObject(root, "trait", module) < 0) {
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
    .m_name = "faebryk",
    .m_doc = "Auto-generated Python extension for Zig functions",
    .m_size = -1,
    .m_methods = &main_methods,
};

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    _ = wrap_composition_file(module.?);
    _ = wrap_interface_file(module.?);
    _ = wrap_module_file(module.?);
    _ = wrap_node_type_file(module.?);
    _ = wrap_type_file(module.?);
    _ = wrap_next_file(module.?);
    _ = wrap_pointer_file(module.?);
    _ = wrap_trait_file(module.?);
    return module;
}
