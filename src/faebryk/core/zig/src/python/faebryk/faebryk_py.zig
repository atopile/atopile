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
const TypeGraphWrapper = bind.PyObjectWrapper(faebryk.typegraph.TypeGraph);

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
                void,
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

fn wrap_edge_composition_get_child_by_identifier() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_child_by_identifier",
            .doc = "Get the child of the EdgeComposition by identifier",
            .args_def = struct {
                node: *graph.BoundNodeReference,
                child_identifier: *py.PyObject,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.child_identifier) orelse return null;

            const child = faebryk.composition.EdgeComposition.get_child_by_identifier(kwarg_obj.node.*, identifier);
            if (child) |_child| {
                return graph_py.makeBoundNodePyObject(_child);
            }

            return bind.wrap_none();
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
        wrap_edge_composition_get_child_by_identifier(),
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

            const edge_ref = faebryk.pointer.EdgePointer.init(std.heap.c_allocator, kwarg_obj.from_node, kwarg_obj.to_node) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create pointer edge");
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

fn wrap_edge_pointer_get_tid() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_tid",
            .doc = "Return the tid of the pointer edge",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            return py.PyLong_FromLongLong(@intCast(faebryk.pointer.EdgePointer.tid));
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
        wrap_edge_pointer_get_tid(),
    };
    bind.wrap_namespace_struct(root, faebryk.pointer.EdgePointer, extra_methods);
    edge_pointer_type = type_registry.getRegisteredTypeObject("EdgePointer");
}

fn wrap_typegraph_init() type {
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

            const allocator = std.heap.c_allocator;
            const graph_ptr = allocator.create(graph.GraphView) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            graph_ptr.* = graph.GraphView.init(allocator);

            const ptr = allocator.create(faebryk.typegraph.TypeGraph) catch {
                graph_ptr.deinit();
                allocator.destroy(graph_ptr);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            ptr.* = faebryk.typegraph.TypeGraph.init(graph_ptr) catch {
                graph_ptr.deinit();
                allocator.destroy(graph_ptr);
                allocator.destroy(ptr);
                py.PyErr_SetString(py.PyExc_ValueError, "init failed");
                return null;
            };

            const obj = bind.wrap_obj("TypeGraph", &type_graph_type, TypeGraphWrapper, ptr);
            if (obj == null) {
                graph_ptr.deinit();
                allocator.destroy(graph_ptr);
                allocator.destroy(ptr);
                return null;
            }

            return obj;
        }
    };
}

fn wrap_typegraph_add_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_type",
            .doc = "Create and register a new type node",
            .args_def = struct {
                identifier: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.identifier) orelse return null;

            const bnode = faebryk.typegraph.TypeGraph.add_type(wrapper.data, identifier) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "add_type failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_typegraph_add_trait() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_trait",
            .doc = "Create and register a new trait node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;

            _ = kwargs;

            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;

            const bnode = faebryk.typegraph.TypeGraph.add_trait(wrapper.data) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "add_trait failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_typegraph_add_make_child() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_make_child",
            .doc = "Create a MakeChild node referencing the provided type",
            .args_def = struct {
                type_node: *graph.BoundNodeReference,
                child_type_node: ?*graph.BoundNodeReference = null,
                identifier: *py.PyObject,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .child_type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.identifier) orelse return null;
            const resolved_child_type = kwarg_obj.child_type_node orelse kwarg_obj.type_node;

            const bnode = faebryk.typegraph.TypeGraph.add_make_child(
                wrapper.data,
                kwarg_obj.type_node.*,
                resolved_child_type.*,
                identifier,
            ) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "add_make_child failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn _unwrap_literal(value_obj: *py.PyObject) !graph.Literal {
    if (value_obj == py.Py_None()) {
        return error.UnsupportedValue;
    }

    if (value_obj == py.Py_True()) {
        return graph.Literal{ .Bool = true };
    }
    if (value_obj == py.Py_False()) {
        return graph.Literal{ .Bool = false };
    }
    py.PyErr_Clear();

    if (py.PyUnicode_AsUTF8(value_obj) != null) {
        const str = bind.unwrap_str_copy(value_obj) orelse return error.UnsupportedValue;
        return graph.Literal{ .String = str };
    }
    py.PyErr_Clear();

    const float_value = py.PyFloat_AsDouble(value_obj);
    if (py.PyErr_Occurred() == null) {
        return graph.Literal{ .Float = float_value };
    }
    py.PyErr_Clear();

    const int_value = py.PyLong_AsLongLong(value_obj);
    if (py.PyErr_Occurred() == null) {
        return graph.Literal{ .Int = int_value };
    }
    py.PyErr_Clear();

    return error.UnsupportedValue;
}

fn _unwrap_literal_str_dict(dict_obj: *py.PyObject, allocator: std.mem.Allocator) !?graph.DynamicAttributes {
    if (dict_obj == py.Py_None()) {
        return null;
    }

    //if (py.PyDict_Check(dict_obj) != 1) {
    //    return error.UnsupportedValue;
    //}

    var attrs = graph.DynamicAttributes.init(allocator);
    var success = false;
    defer if (!success) attrs.deinit();

    var pos: isize = 0;
    var key_obj: ?*py.PyObject = null;
    var value_obj: ?*py.PyObject = null;

    while (py.PyDict_Next(dict_obj, &pos, &key_obj, &value_obj) == 1) {
        if (key_obj == null or value_obj == null) {
            continue;
        }
        const key = bind.unwrap_str_copy(key_obj) orelse return null;

        const literal = _unwrap_literal(value_obj.?) catch {
            allocator.free(key);
            py.PyErr_SetString(py.PyExc_TypeError, "edge_attributes values must be bool, int, float, or str");
            return null;
        };
        attrs.values.put(key, literal) catch {
            allocator.free(key);
            py.PyErr_SetString(py.PyExc_MemoryError, "failed to store edge attribute");
            return null;
        };
    }

    if (py.PyErr_Occurred() != null) {
        return null;
    }

    success = true;
    return attrs;
}

fn wrap_typegraph_add_make_link() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_make_link",
            .doc = "Create a MakeLink node",
            .args_def = struct {
                type_node: *graph.BoundNodeReference,
                lhs_reference_node: *graph.Node,
                rhs_reference_node: *graph.Node,
                edge_type: *py.PyObject,
                edge_directional: *py.PyObject,
                edge_name: *py.PyObject,
                edge_attributes: *py.PyObject,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .lhs_reference_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .rhs_reference_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const edge_type_raw = py.PyLong_AsLongLong(kwarg_obj.edge_type);
            if (py.PyErr_Occurred() != null) {
                py.PyErr_SetString(py.PyExc_TypeError, "edge_type must be an integer");
                return null;
            }

            const type_node = kwarg_obj.type_node.*;
            const edge_type: graph.Edge.EdgeType = @intCast(edge_type_raw);
            const edge_directional: ?bool = if (kwarg_obj.edge_directional == py.Py_None()) null else bind.unwrap_bool(kwarg_obj.edge_directional);
            const edge_name: ?[]u8 = if (kwarg_obj.edge_name == py.Py_None()) null else bind.unwrap_str_copy(kwarg_obj.edge_name) orelse return null;

            const allocator = type_node.g.allocator;

            var dynamic = _unwrap_literal_str_dict(kwarg_obj.edge_attributes, allocator) catch return null;
            defer if (dynamic != null) dynamic.?.deinit();

            const edge_attributes = faebryk.typegraph.TypeGraph.MakeLinkNode.Attributes.EdgeCreationAttributes{
                .edge_type = edge_type,
                .directional = edge_directional,
                .name = edge_name,
                .dynamic = dynamic,
            };

            const make_link = faebryk.typegraph.TypeGraph.add_make_link(
                wrapper.data,
                type_node,
                kwarg_obj.lhs_reference_node,
                kwarg_obj.rhs_reference_node,
                edge_attributes,
            ) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "add_make_link failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(make_link);
        }
    };
}

fn wrap_typegraph_instantiate() type {
    return struct {
        pub const descr = method_descr{
            .name = "instantiate",
            .doc = "Instantiate the given type node into a graph",
            .args_def = struct {
                type_identifier: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.type_identifier) orelse return null;

            const bnode = faebryk.typegraph.TypeGraph.instantiate(wrapper.data, identifier) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "instantiate failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_typegraph_reference_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_reference",
            .doc = "Create a Reference node chain from a sequence of child identifiers",
            .args_def = struct {
                type_node: *graph.BoundNodeReference,
                path: *py.PyObject,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const path_obj = kwarg_obj.path;
            if (py.PySequence_Check(path_obj) != 1) {
                py.PyErr_SetString(py.PyExc_TypeError, "path must be a sequence of strings");
                return null;
            }

            const path_len = py.PySequence_Size(path_obj);
            if (path_len < 0) {
                return null;
            }

            var segments = std.ArrayList([]const u8).init(std.heap.c_allocator);
            defer segments.deinit();

            var idx: usize = 0;
            const path_len_int: usize = @intCast(path_len);
            while (idx < path_len_int) : (idx += 1) {
                const item = py.PySequence_GetItem(path_obj, @intCast(idx));
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                const segment = bind.unwrap_str_copy(item) orelse return null;
                segments.append(segment) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "failed to build path");
                    return null;
                };
            }

            const bnode = faebryk.typegraph.TypeGraph.ChildReferenceNode.create_and_insert(wrapper.data, segments.items) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "add_reference failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_typegraph_reference_resolve() type {
    return struct {
        pub const descr = method_descr{
            .name = "reference_resolve",
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
            _ = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const resolved = faebryk.typegraph.TypeGraph.ChildReferenceNode.resolve(
                kwarg_obj.reference_node.*,
                kwarg_obj.base_node.*,
            ) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "reference_resolve failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(resolved);
        }
    };
}

fn typegraph_dealloc(self: *py.PyObject) callconv(.C) void {
    const allocator = std.heap.c_allocator;
    const wrapper = @as(*TypeGraphWrapper, @ptrCast(@alignCast(self)));
    const tg_ptr = wrapper.data;

    const graph_ptr = tg_ptr.g;
    graph_ptr.deinit();
    allocator.destroy(graph_ptr);
    allocator.destroy(tg_ptr);

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.C) void, @ptrCast(free_fn_any));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn wrap_typegraph(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_typegraph_init(),
        wrap_typegraph_add_type(),
        wrap_typegraph_add_trait(),
        wrap_typegraph_add_make_child(),
        wrap_typegraph_add_make_link(),
        wrap_typegraph_instantiate(),
        wrap_typegraph_reference_create(),
        wrap_typegraph_reference_resolve(),
    };
    bind.wrap_namespace_struct(root, faebryk.typegraph.TypeGraph, extra_methods);
    type_graph_type = type_registry.getRegisteredTypeObject("TypeGraph");
    if (type_graph_type) |tg_type| {
        tg_type.tp_dealloc = @ptrCast(&typegraph_dealloc);
    }
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

fn wrap_typegraph_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_typegraph(module.?);

    if (py.PyModule_AddObject(root, "typegraph", module) < 0) {
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
    _ = wrap_typegraph_file(module.?);
    _ = wrap_next_file(module.?);
    _ = wrap_pointer_file(module.?);
    _ = wrap_trait_file(module.?);
    return module;
}
