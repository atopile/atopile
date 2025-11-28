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
const EdgeOperandWrapper = bind.PyObjectWrapper(faebryk.operand.EdgeOperand);
const EdgeTypeWrapper = bind.PyObjectWrapper(faebryk.node_type.EdgeType);
const EdgeNextWrapper = bind.PyObjectWrapper(faebryk.next.EdgeNext);
const EdgePointerWrapper = bind.PyObjectWrapper(faebryk.pointer.EdgePointer);
const EdgeCreationAttributesWrapper = bind.PyObjectWrapper(faebryk.edgebuilder.EdgeCreationAttributes);
const NodeCreationAttributesWrapper = bind.PyObjectWrapper(faebryk.nodebuilder.NodeCreationAttributes);
const TypeGraphWrapper = bind.PyObjectWrapper(faebryk.typegraph.TypeGraph);

var edge_composition_type: ?*py.PyTypeObject = null;
var edge_operand_type: ?*py.PyTypeObject = null;
var edge_type_type: ?*py.PyTypeObject = null;
var edge_next_type: ?*py.PyTypeObject = null;
var edge_pointer_type: ?*py.PyTypeObject = null;
var edge_creation_attributes_type: ?*py.PyTypeObject = null;
var node_creation_attributes_type: ?*py.PyTypeObject = null;
var type_graph_type: ?*py.PyTypeObject = null;
var make_child_node_type: ?*py.PyTypeObject = null;

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
            );

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

fn wrap_edge_composition_build() type {
    return struct {
        pub const descr = method_descr{
            .name = "build",
            .doc = "Return creation attributes for an EdgeComposition",
            .args_def = struct {
                child_identifier: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const identifier_copy = bind.unwrap_str_copy(kwarg_obj.child_identifier) orelse return null;

            const allocator = std.heap.c_allocator;
            const attributes = allocator.create(faebryk.edgebuilder.EdgeCreationAttributes) catch {
                allocator.free(identifier_copy);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };

            attributes.* = faebryk.composition.EdgeComposition.build(identifier_copy);
            return bind.wrap_obj("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, attributes);
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

fn wrap_edge_composition_get_parent_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_parent_node",
            .doc = "Get the parent node associated with the edge",
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

            const node_ref = faebryk.composition.EdgeComposition.get_parent_node(kwarg_obj.edge);
            return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
        }
    };
}

fn wrap_edge_composition_get_child_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_child_node",
            .doc = "Get the child node associated with the edge",
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

            const node_ref = faebryk.composition.EdgeComposition.get_child_node(kwarg_obj.edge);
            return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
        }
    };
}

fn wrap_edge_composition_get_child_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_child_of",
            .doc = "Get the child node of the edge relative to a node",
            .args_def = struct {
                edge: *graph.Edge,
                node: *graph.Node,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.composition.EdgeComposition.get_child_of(kwarg_obj.edge, kwarg_obj.node)) |node_ref| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_composition_get_parent_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_parent_of",
            .doc = "Get the parent node of the edge relative to a node",
            .args_def = struct {
                edge: *graph.Edge,
                node: *graph.Node,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.composition.EdgeComposition.get_parent_of(kwarg_obj.edge, kwarg_obj.node)) |node_ref| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_composition_get_parent_node_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_parent_node_of",
            .doc = "Get the parent node of a bound node within the composition",
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

            if (faebryk.composition.EdgeComposition.get_parent_node_of(kwarg_obj.bound_node.*)) |parent| {
                return graph_py.makeBoundNodePyObject(parent);
            }

            return bind.wrap_none();
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
            );

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
                bound_node: *graph.BoundNodeReference,
                child_identifier: *py.PyObject,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.child_identifier) orelse return null;

            const child = faebryk.composition.EdgeComposition.get_child_by_identifier(kwarg_obj.bound_node.*, identifier);
            if (child) |_child| {
                return graph_py.makeBoundNodePyObject(_child);
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_composition_visit_children_of_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_children_of_type",
            .doc = "Visit children edges of the given type",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                child_type: *graph.Node,
                f: *py.PyObject,
                ctx: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .child_type = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
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

            const result = faebryk.composition.EdgeComposition.visit_children_of_type(
                kwarg_obj.bound_node.*,
                kwarg_obj.child_type,
                void,
                @ptrCast(&visit_ctx),
                graph_py.BoundEdgeVisitor.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_children_of_type failed");
                    return null;
                },
                else => {},
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_composition_try_get_single_child_of_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "try_get_single_child_of_type",
            .doc = "Return the single child of the specified type if it exists",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                child_type: *graph.Node,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .child_type = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.composition.EdgeComposition.try_get_single_child_of_type(kwarg_obj.bound_node.*, kwarg_obj.child_type)) |child| {
                return graph_py.makeBoundNodePyObject(child);
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_composition(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_composition_create(),
        wrap_edge_composition_build(),
        wrap_edge_composition_is_instance(),
        wrap_edge_composition_visit_children_edges(),
        wrap_edge_composition_get_parent_edge(),
        wrap_edge_composition_get_parent_node(),
        wrap_edge_composition_get_child_node(),
        wrap_edge_composition_get_child_of(),
        wrap_edge_composition_get_parent_of(),
        wrap_edge_composition_get_parent_node_of(),
        wrap_edge_composition_add_child(),
        wrap_edge_composition_get_name(),
        wrap_edge_composition_get_tid(),
        wrap_edge_composition_get_child_by_identifier(),
        wrap_edge_composition_visit_children_of_type(),
        wrap_edge_composition_try_get_single_child_of_type(),
    };
    bind.wrap_namespace_struct(root, faebryk.composition.EdgeComposition, extra_methods);
    edge_composition_type = type_registry.getRegisteredTypeObject("EdgeComposition");
}

fn wrap_edge_operand_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new EdgeOperand",
            .args_def = struct {
                expression: *graph.Node,
                operand: *graph.Node,
                operand_identifier: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .expression = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .operand = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            var identifier_const: ?[]const u8 = null;
            if (kwarg_obj.operand_identifier) |identifier_obj| {
                if (identifier_obj != py.Py_None()) {
                    identifier_const = bind.unwrap_str_copy(identifier_obj) orelse return null;
                }
            }

            const edge_ref = faebryk.operand.EdgeOperand.init(
                std.heap.c_allocator,
                kwarg_obj.expression,
                kwarg_obj.operand,
                identifier_const,
            );

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                if (identifier_const) |identifier| {
                    std.heap.c_allocator.free(identifier);
                }
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_operand_build() type {
    return struct {
        pub const descr = method_descr{
            .name = "build",
            .doc = "Return creation attributes for an EdgeOperand",
            .args_def = struct {
                operand_identifier: ?*py.PyObject = null,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            var identifier_copy: ?[]u8 = null;
            if (kwarg_obj.operand_identifier) |identifier_obj| {
                if (identifier_obj != py.Py_None()) {
                    identifier_copy = bind.unwrap_str_copy(identifier_obj) orelse return null;
                }
            }

            const allocator = std.heap.c_allocator;
            const attributes = allocator.create(faebryk.edgebuilder.EdgeCreationAttributes) catch {
                if (identifier_copy) |identifier| {
                    allocator.free(identifier);
                }
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };

            attributes.* = faebryk.operand.EdgeOperand.build(identifier_copy);
            return bind.wrap_obj("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, attributes);
        }
    };
}

fn wrap_edge_operand_is_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_instance",
            .doc = "Check if the object is an instance of EdgeOperand",
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

            const is_match = faebryk.operand.EdgeOperand.is_instance(kwarg_obj.edge);
            return bind.wrap_bool(is_match);
        }
    };
}

fn wrap_edge_operand_visit_operand_edges() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_operand_edges",
            .doc = "Visit the operand edges attached to an expression node",
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

            const result = faebryk.operand.EdgeOperand.visit_operand_edges(
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
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_operand_edges failed");
                    return null;
                },
                else => {},
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_operand_visit_operands_of_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_operands_of_type",
            .doc = "Invoke a callback for operands of the requested type on an expression node",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                operand_type: *graph.Node,
                f: *py.PyObject,
                ctx: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .operand_type = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
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

            const result = faebryk.operand.EdgeOperand.visit_operands_of_type(
                kwarg_obj.bound_node.*,
                kwarg_obj.operand_type,
                void,
                @ptrCast(&visit_ctx),
                graph_py.BoundEdgeVisitor.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_operands_of_type failed");
                    return null;
                },
                else => {},
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_operand_visit_expression_edges() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_expression_edges",
            .doc = "Visit the expression edges attached to an operand node",
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

            const result = faebryk.operand.EdgeOperand.visit_expression_edges(
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
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_expression_edges failed");
                    return null;
                },
                else => {},
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_operand_get_expression_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_expression_edge",
            .doc = "Get the inbound EdgeOperand edge for an operand node",
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

            const expression_edge = faebryk.operand.EdgeOperand.get_expression_edge(kwarg_obj.bound_node.*);
            if (expression_edge) |edge_ref| {
                return graph_py.makeBoundEdgePyObject(edge_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_operand_get_expression_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_expression_node",
            .doc = "Get the expression node associated with an EdgeOperand edge",
            .args_def = struct {
                bound_edge: *graph.BoundEdgeReference,

                pub const fields_meta = .{
                    .bound_edge = bind.ARG{ .Wrapper = BoundEdgeWrapper, .storage = &graph_py.bound_edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const node_ref = faebryk.operand.EdgeOperand.get_expression_node(kwarg_obj.bound_edge.*);
            return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
        }
    };
}

fn wrap_edge_operand_get_operand_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_operand_node",
            .doc = "Return the operand node referenced by the EdgeOperand edge",
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

            const node_ref = faebryk.operand.EdgeOperand.get_operand_node(kwarg_obj.edge);
            return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
        }
    };
}

fn wrap_edge_operand_get_operand_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_operand_of",
            .doc = "Return the operand node reachable from the provided node via the edge, if any",
            .args_def = struct {
                edge: *graph.Edge,
                node: *graph.Node,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.operand.EdgeOperand.get_operand_of(kwarg_obj.edge, kwarg_obj.node)) |operand| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, operand);
            }
            return bind.wrap_none();
        }
    };
}

fn wrap_edge_operand_get_expression_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_expression_of",
            .doc = "Return the expression node reachable from the provided operand via the edge, if any",
            .args_def = struct {
                bound_edge: *graph.BoundEdgeReference,
                node: *graph.Node,

                pub const fields_meta = .{
                    .bound_edge = bind.ARG{ .Wrapper = BoundEdgeWrapper, .storage = &graph_py.bound_edge_type },
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.operand.EdgeOperand.get_expression_of(kwarg_obj.bound_edge.*, kwarg_obj.node)) |expression| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, expression);
            }
            return bind.wrap_none();
        }
    };
}

fn wrap_edge_operand_add_operand() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_operand",
            .doc = "Attach an operand node to an expression via EdgeOperand",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                operand: *graph.Node,
                operand_identifier: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .operand = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const allocator = kwarg_obj.bound_node.g.allocator;
            var identifier_copy: ?[]u8 = null;
            if (kwarg_obj.operand_identifier) |identifier_obj| {
                if (identifier_obj != py.Py_None()) {
                    const identifier_c = py.PyUnicode_AsUTF8(identifier_obj);
                    if (identifier_c == null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "operand_identifier must be a string");
                        return null;
                    }
                    const identifier_slice = std.mem.span(identifier_c.?);
                    identifier_copy = allocator.dupe(u8, identifier_slice) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate operand_identifier");
                        return null;
                    };
                }
            }

            const bound_edge = faebryk.operand.EdgeOperand.add_operand(
                kwarg_obj.bound_node.*,
                kwarg_obj.operand,
                identifier_copy,
            );

            return graph_py.makeBoundEdgePyObject(bound_edge);
        }
    };
}

fn wrap_edge_operand_get_name() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_name",
            .doc = "Get the operand identifier stored on the EdgeOperand",
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

            const name = faebryk.operand.EdgeOperand.get_name(kwarg_obj.edge) catch |err| {
                switch (err) {
                    error.InvalidEdgeType => {
                        py.PyErr_SetString(py.PyExc_TypeError, "edge is not an EdgeOperand edge");
                    },
                }
                return null;
            };

            if (name == null) {
                return bind.wrap_none();
            }

            const value = name.?;
            const ptr: [*c]const u8 = if (value.len == 0) "" else @ptrCast(value.ptr);
            const py_str = py.PyUnicode_FromStringAndSize(ptr, @intCast(value.len));
            if (py_str == null) {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create Python string");
                return null;
            }

            return py_str;
        }
    };
}

fn wrap_edge_operand_visit_expression_edges_of_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_expression_edges_of_type",
            .doc = "Visit expression edges of the given type attached to an operand node",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                expression_type: *graph.Node,
                f: *py.PyObject,
                ctx: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .expression_type = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
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

            const result = faebryk.operand.EdgeOperand.visit_expression_edges_of_type(
                kwarg_obj.bound_node.*,
                kwarg_obj.expression_type,
                void,
                @ptrCast(&visit_ctx),
                graph_py.BoundEdgeVisitor.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_expression_edges_of_type failed");
                    return null;
                },
                else => {},
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_edge_operand_get_tid() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_tid",
            .doc = "Get the tid of the EdgeOperand",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const tid = faebryk.operand.EdgeOperand.tid;
            return py.PyLong_FromLongLong(@intCast(tid));
        }
    };
}

fn wrap_edge_operand_get_operand_by_identifier() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_operand_by_identifier",
            .doc = "Get the operand node bound to an expression by identifier",
            .args_def = struct {
                node: *graph.BoundNodeReference,
                operand_identifier: *py.PyObject,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.operand_identifier) orelse return null;

            const operand = faebryk.operand.EdgeOperand.get_operand_by_identifier(kwarg_obj.node.*, identifier);
            if (operand) |_operand| {
                return graph_py.makeBoundNodePyObject(_operand);
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_operand(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_operand_create(),
        wrap_edge_operand_build(),
        wrap_edge_operand_is_instance(),
        wrap_edge_operand_visit_operand_edges(),
        wrap_edge_operand_visit_operands_of_type(),
        wrap_edge_operand_visit_expression_edges(),
        wrap_edge_operand_visit_expression_edges_of_type(),
        wrap_edge_operand_get_expression_edge(),
        wrap_edge_operand_get_expression_node(),
        wrap_edge_operand_get_operand_node(),
        wrap_edge_operand_get_operand_of(),
        wrap_edge_operand_get_expression_of(),
        wrap_edge_operand_add_operand(),
        wrap_edge_operand_get_name(),
        wrap_edge_operand_get_tid(),
        wrap_edge_operand_get_operand_by_identifier(),
    };
    bind.wrap_namespace_struct(root, faebryk.operand.EdgeOperand, extra_methods);
    edge_operand_type = type_registry.getRegisteredTypeObject("EdgeOperand");
}

fn wrap_edge_interface_connection_get_tid() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_tid",
            .doc = "Return the edge type identifier used for interface connection edges",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            _ = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const tid = faebryk.interface.EdgeInterfaceConnection.get_tid();
            return py.PyLong_FromLongLong(@intCast(tid));
        }
    };
}

fn wrap_edge_interface_connection_is_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_instance",
            .doc = "Check if an edge is an interface connection edge",
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
            const is_match = faebryk.interface.EdgeInterfaceConnection.is_instance(kwarg_obj.edge);
            return bind.wrap_bool(is_match);
        }
    };
}

fn wrap_edge_interface_connection_get_other_connected_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_other_connected_node",
            .doc = "Get the other node connected by this edge",
            .args_def = struct {
                edge: *graph.Edge,
                node: *graph.Node,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(kwarg_obj.edge, kwarg_obj.node)) |other| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, other);
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_interface_connection_connect() type {
    return struct {
        pub const descr = method_descr{
            .name = "connect",
            .doc = "Connect two interface nodes",
            .args_def = struct {
                bn1: *graph.BoundNodeReference,
                bn2: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .bn1 = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .bn2 = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound_edge = faebryk.interface.EdgeInterfaceConnection.connect(kwarg_obj.bn1.*, kwarg_obj.bn2.*) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to connect interface nodes");
                return null;
            };

            return graph_py.makeBoundEdgePyObject(bound_edge);
        }
    };
}

fn wrap_edge_interface_connection_connect_shallow() type {
    return struct {
        pub const descr = method_descr{
            .name = "connect_shallow",
            .doc = "Connect two interface nodes with a shallow edge",
            .args_def = struct {
                bn1: *graph.BoundNodeReference,
                bn2: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .bn1 = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .bn2 = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const bound_edge = faebryk.interface.EdgeInterfaceConnection.connect_shallow(kwarg_obj.bn1.*, kwarg_obj.bn2.*) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create shallow connection");
                return null;
            };

            return graph_py.makeBoundEdgePyObject(bound_edge);
        }
    };
}

fn wrap_edge_interface_connection_visit_connected_edges() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_connected_edges",
            .doc = "Visit all interface connection edges for a node",
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

            const result = faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(
                kwarg_obj.bound_node.*,
                @ptrCast(&visit_ctx),
                graph_py.BoundEdgeVisitor.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_connected_edges failed");
                    return null;
                },
                else => {},
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_interface_connection_is_connected_to() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_connected_to",
            .doc = "Find all paths connecting source to target nodes",
            .args_def = struct {
                source: *graph.BoundNodeReference,
                target: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .source = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .target = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const path = faebryk.interface.EdgeInterfaceConnection.is_connected_to(
                kwarg_obj.source.g.allocator,
                kwarg_obj.source.*,
                kwarg_obj.target.*,
            ) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to find paths");
                return null;
            };
            const py_path = graph_py.makeBFSPathPyObject(path) orelse @panic("OOM");
            return py_path;
        }
    };
}

fn wrap_edge_interface_connection_get_connected() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_connected",
            .doc = "Get all nodes connected to the source node",
            .args_def = struct {
                source: *graph.BoundNodeReference,
                include_self: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .source = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            // Parse include_self parameter (default to true for backwards compatibility)
            const include_self = if (kwarg_obj.include_self) |obj|
                if (obj == py.Py_None()) true else py.PyObject_IsTrue(obj) == 1
            else
                true;

            var paths_map = faebryk.interface.EdgeInterfaceConnection.get_connected(
                kwarg_obj.source.g.allocator,
                kwarg_obj.source.*,
                include_self,
            ) catch @panic("OOM");
            defer paths_map.deinit(); // Only clean up the HashMap structure, not the paths (Python takes ownership)

            const dict_obj = py.PyDict_New() orelse @panic("OOM");

            var iter = paths_map.iterator();
            while (iter.next()) |entry| {
                const node = entry.key_ptr.*;
                const path = entry.value_ptr.*;

                const bound_node = kwarg_obj.source.g.bind(node);
                const py_node = graph_py.makeBoundNodePyObject(bound_node) orelse @panic("OOM");
                const py_path = graph_py.makeBFSPathPyObject(path) orelse @panic("OOM");

                _ = py.PyDict_SetItem(dict_obj, py_node, py_path);

                py.Py_DECREF(py_path);
                py.Py_DECREF(py_node);
            }

            return dict_obj;
        }
    };
}

fn wrap_interface(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_interface_connection_get_tid(),
        wrap_edge_interface_connection_is_instance(),
        wrap_edge_interface_connection_get_other_connected_node(),
        wrap_edge_interface_connection_connect(),
        wrap_edge_interface_connection_connect_shallow(),
        wrap_edge_interface_connection_visit_connected_edges(),
        wrap_edge_interface_connection_is_connected_to(),
        wrap_edge_interface_connection_get_connected(),
    };
    bind.wrap_namespace_struct(root, faebryk.interface.EdgeInterfaceConnection, extra_methods);
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
            );

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_type_build() type {
    return struct {
        pub const descr = method_descr{
            .name = "build",
            .doc = "Return creation attributes for a type edge",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const allocator = std.heap.c_allocator;
            const attributes = allocator.create(faebryk.edgebuilder.EdgeCreationAttributes) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            attributes.* = faebryk.node_type.EdgeType.build();
            return bind.wrap_obj("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, attributes);
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
            );

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
        wrap_edge_type_build(),
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
            );

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_next_build() type {
    return struct {
        pub const descr = method_descr{
            .name = "build",
            .doc = "Return creation attributes for a next edge",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const allocator = std.heap.c_allocator;
            const attributes = allocator.create(faebryk.edgebuilder.EdgeCreationAttributes) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            attributes.* = faebryk.next.EdgeNext.build();
            return bind.wrap_obj("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, attributes);
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
            );

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
        wrap_edge_next_build(),
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
                identifier: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .from_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .to_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            var identifier_copy: ?[]u8 = null;
            if (kwarg_obj.identifier) |identifier_obj| {
                if (identifier_obj != py.Py_None()) {
                    identifier_copy = bind.unwrap_str_copy(identifier_obj) orelse return null;
                }
            }

            const edge_ref = faebryk.pointer.EdgePointer.init(
                std.heap.c_allocator,
                kwarg_obj.from_node,
                kwarg_obj.to_node,
                if (identifier_copy) |copy| copy else null,
                null,
            );

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                if (identifier_copy) |copy| std.heap.c_allocator.free(copy);
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_pointer_build() type {
    return struct {
        pub const descr = method_descr{
            .name = "build",
            .doc = "Build a pointer edge creation attributes",
            .args_def = struct {
                identifier: ?*py.PyObject = null,
                order: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            var identifier_copy: ?[]u8 = null;
            if (kwarg_obj.identifier) |identifier_obj| {
                if (identifier_obj != py.Py_None()) {
                    identifier_copy = bind.unwrap_str_copy(identifier_obj) orelse return null;
                }
            }

            var order: ?u32 = null;
            if (kwarg_obj.order != py.Py_None()) {
                order = bind.unwrap_int(u32, kwarg_obj.order) orelse return null;
            }

            const allocator = std.heap.c_allocator;
            const attributes = allocator.create(faebryk.edgebuilder.EdgeCreationAttributes) catch {
                if (identifier_copy) |copy| std.heap.c_allocator.free(copy);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            attributes.* = faebryk.pointer.EdgePointer.build(std.heap.c_allocator, if (identifier_copy) |copy| copy else null, order);
            return bind.wrap_obj("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, attributes);
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

fn wrap_edge_pointer_get_referenced_node_from_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_referenced_node_from_node",
            .doc = "Return the bound node referenced by the pointer edge attached to a bound node",
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

            if (faebryk.pointer.EdgePointer.get_referenced_node_from_node(kwarg_obj.node.*)) |node| {
                return graph_py.makeBoundNodePyObject(node);
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

fn wrap_edge_pointer_get_order() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_order",
            .doc = "Return the order of the pointer edge",
            .args_def = struct {
                edge: graph.EdgeReference,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const order = faebryk.pointer.EdgePointer.get_order(kwarg_obj.edge);

            if (order == null) {
                return bind.wrap_none();
            }

            return bind.wrap_int(order.?);
        }
    };
}

fn wrap_edge_pointer_point_to() type {
    return struct {
        pub const descr = method_descr{
            .name = "point_to",
            .doc = "Create a pointer edge from the bound node to the target node",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                target_node: *graph.Node,
                identifier: ?*py.PyObject = null,
                order: *py.PyObject,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .target_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const allocator = kwarg_obj.bound_node.g.allocator;
            var identifier_copy: ?[]u8 = null;
            if (kwarg_obj.identifier) |identifier_obj| {
                if (identifier_obj != py.Py_None()) {
                    const identifier_str = bind.unwrap_str(identifier_obj) orelse return null;
                    identifier_copy = allocator.dupe(u8, identifier_str) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate identifier");
                        return null;
                    };
                }
            }

            var order: ?u32 = null;
            if (kwarg_obj.order != py.Py_None()) {
                order = bind.unwrap_int(u32, kwarg_obj.order) orelse return null;
            }

            const bound_edge = faebryk.pointer.EdgePointer.point_to(
                kwarg_obj.bound_node.*,
                kwarg_obj.target_node,
                if (identifier_copy) |copy| copy else null,
                order,
            );
            return graph_py.makeBoundEdgePyObject(bound_edge);
        }
    };
}

fn wrap_edge_pointer_visit_pointed_edges() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_pointed_edges",
            .doc = "Invoke a callback for each pointer edge starting from the bound node",
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

            const result = faebryk.pointer.EdgePointer.visit_pointed_edges(
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
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_pointed_edges failed");
                    return null;
                },
                else => {},
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_pointer_visit_pointed_edges_with_identifier() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_pointed_edges_with_identifier",
            .doc = "Invoke a callback for each pointer edge with the given identifier",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                identifier: *py.PyObject,
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

            const identifier = bind.unwrap_str(kwarg_obj.identifier) orelse return null;

            var visit_ctx = graph_py.BoundEdgeVisitor{
                .py_ctx = kwarg_obj.ctx,
                .callable = kwarg_obj.f,
            };

            const result = faebryk.pointer.EdgePointer.visit_pointed_edges_with_identifier(
                kwarg_obj.bound_node.*,
                identifier,
                void,
                @ptrCast(&visit_ctx),
                graph_py.BoundEdgeVisitor.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_pointed_edges_with_identifier failed");
                    return null;
                },
                else => {},
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_pointer_get_pointed_node_by_identifier() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_pointed_node_by_identifier",
            .doc = "Return the bound node pointed to by the given identifier",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                identifier: *py.PyObject,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.identifier) orelse return null;

            if (faebryk.pointer.EdgePointer.get_pointed_node_by_identifier(kwarg_obj.bound_node.*, identifier)) |node| {
                return graph_py.makeBoundNodePyObject(node);
            }

            return bind.wrap_none();
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
        wrap_edge_pointer_build(),
        wrap_edge_pointer_is_instance(),
        wrap_edge_pointer_get_referenced_node(),
        wrap_edge_pointer_get_referenced_node_from_node(),
        wrap_edge_pointer_get_tid(),
        wrap_edge_pointer_get_order(),
        wrap_edge_pointer_visit_pointed_edges(),
        wrap_edge_pointer_visit_pointed_edges_with_identifier(),
        wrap_edge_pointer_get_pointed_node_by_identifier(),
        wrap_edge_pointer_point_to(),
    };
    bind.wrap_namespace_struct(root, faebryk.pointer.EdgePointer, extra_methods);
    edge_pointer_type = type_registry.getRegisteredTypeObject("EdgePointer");
}

fn wrap_nodebuilder_init() type {
    return struct {
        pub const descr = method_descr{
            .name = "init",
            .doc = "Create a new NodeCreationAttributes",
            .args_def = struct {
                dynamic: ?*py.PyObject = null,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const allocator = std.heap.c_allocator;
            const dynamic_obj: *py.PyObject = if (kwarg_obj.dynamic) |obj| obj else py.Py_None();

            var dynamic_attrs = _unwrap_literal_str_dict(dynamic_obj, allocator) catch return null;

            const attributes = allocator.create(faebryk.nodebuilder.NodeCreationAttributes) catch {
                if (dynamic_attrs) |*attrs| attrs.deinit();
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            attributes.* = .{ .dynamic = dynamic_attrs };
            dynamic_attrs = null;

            const wrapped = bind.wrap_obj("NodeCreationAttributes", &node_creation_attributes_type, NodeCreationAttributesWrapper, attributes);
            if (wrapped == null) {
                if (attributes.*.dynamic) |*dynamic_value| {
                    dynamic_value.deinit();
                }
                allocator.destroy(attributes);
                return null;
            }

            return wrapped;
        }
    };
}

fn wrap_nodebuilder_apply_to() type {
    return struct {
        pub const descr = method_descr{
            .name = "apply_to",
            .doc = "Apply the attributes to a node",
            .args_def = struct {
                node: *graph.Node,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const attributes = bind.castWrapper("NodeCreationAttributes", &node_creation_attributes_type, NodeCreationAttributesWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            attributes.data.apply_to(kwarg_obj.node);
            return bind.wrap_none();
        }
    };
}

fn wrap_nodebuilder(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_nodebuilder_init(),
        wrap_nodebuilder_apply_to(),
    };
    bind.wrap_namespace_struct(root, faebryk.nodebuilder.NodeCreationAttributes, extra_methods);
    node_creation_attributes_type = type_registry.getRegisteredTypeObject("NodeCreationAttributes");
}

fn wrap_edgebuilder_init() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new EdgeCreationAttributes",
            .args_def = struct {
                edge_type: *py.PyObject,
                directional: *py.PyObject,
                name: *py.PyObject,
                dynamic: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const edge_type_raw = py.PyLong_AsLongLong(kwarg_obj.edge_type);
            if (py.PyErr_Occurred() != null) {
                py.PyErr_SetString(py.PyExc_TypeError, "edge_type must be an integer");
                return null;
            }

            const edge_type: graph.Edge.EdgeType = @intCast(edge_type_raw);
            const edge_directional: ?bool = if (kwarg_obj.directional == py.Py_None()) null else bind.unwrap_bool(kwarg_obj.directional);
            const edge_name: ?[]u8 = if (kwarg_obj.name == py.Py_None()) null else bind.unwrap_str_copy(kwarg_obj.name) orelse return null;

            const allocator = std.heap.c_allocator;

            const dynamic = _unwrap_literal_str_dict(kwarg_obj.dynamic, allocator) catch return null;

            const attributes = allocator.create(faebryk.edgebuilder.EdgeCreationAttributes) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            attributes.* = .{
                .edge_type = edge_type,
                .directional = edge_directional,
                .name = edge_name,
                .dynamic = dynamic,
            };
            return bind.wrap_obj("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, attributes);
        }
    };
}

fn wrap_edgebuilder_apply_to() type {
    return struct {
        pub const descr = method_descr{
            .name = "apply_to",
            .doc = "Apply the attributes to an edge",
            .args_def = struct {
                edge: graph.EdgeReference,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                };
            },
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const attributes = bind.castWrapper("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            attributes.data.apply_to(kwarg_obj.edge);
            return bind.wrap_none();
        }
    };
}

fn wrap_edgebuilder_create_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "create_edge",
            .doc = "Create an edge with these attributes between source and target nodes",
            .args_def = struct {
                source: *graph.Node,
                target: *graph.Node,

                pub const fields_meta = .{
                    .source = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .target = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const attributes = bind.castWrapper("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const edge = attributes.data.create_edge(std.heap.c_allocator, kwarg_obj.source, kwarg_obj.target);
            return bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge);
        }
    };
}

fn wrap_edgebuilder_insert_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "insert_edge",
            .doc = "Create and insert an edge with these attributes into the graph",
            .args_def = struct {
                g: *graph.GraphView,
                source: *graph.Node,
                target: *graph.Node,

                pub const fields_meta = .{
                    .g = bind.ARG{ .Wrapper = graph_py.GraphViewWrapper, .storage = &graph_py.graph_view_type },
                    .source = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .target = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const attributes = bind.castWrapper("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            var edge = attributes.data.insert_edge(kwarg_obj.g, kwarg_obj.source, kwarg_obj.target);
            return bind.wrap_obj("BoundEdge", &graph_py.bound_edge_type, BoundEdgeWrapper, &edge);
        }
    };
}

fn wrap_edgebuilder_get_tid() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_tid",
            .doc = "Return the edge type identifier",
            .args_def = struct {},
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const attributes = bind.castWrapper("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, self) orelse return null;
            _ = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const tid = attributes.data.get_tid();
            return py.PyLong_FromLongLong(@intCast(tid));
        }
    };
}

fn wrap_edgebuilder(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edgebuilder_init(),
        wrap_edgebuilder_apply_to(),
        wrap_edgebuilder_create_edge(),
        wrap_edgebuilder_insert_edge(),
        wrap_edgebuilder_get_tid(),
    };
    bind.wrap_namespace_struct(root, faebryk.edgebuilder.EdgeCreationAttributes, extra_methods);
    edge_creation_attributes_type = type_registry.getRegisteredTypeObject("EdgeCreationAttributes");
}

fn make_typegraph_pyobject(value: faebryk.typegraph.TypeGraph) ?*py.PyObject {
    const allocator = std.heap.c_allocator;
    const ptr = allocator.create(faebryk.typegraph.TypeGraph) catch {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    ptr.* = value;

    const obj = bind.wrap_obj("TypeGraph", &type_graph_type, TypeGraphWrapper, ptr);
    if (obj == null) {
        allocator.destroy(ptr);
        return null;
    }

    return obj;
}

fn wrap_typegraph_init() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a new TypeGraph from a GraphView",
            .args_def = struct {
                g: *graph.GraphView,

                pub const fields_meta = .{
                    .g = bind.ARG{ .Wrapper = graph_py.GraphViewWrapper, .storage = &graph_py.graph_view_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const typegraph = faebryk.typegraph.TypeGraph.init(kwarg_obj.g);
            return make_typegraph_pyobject(typegraph);
        }
    };
}

fn wrap_typegraph_of_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "of_type",
            .doc = "Return the TypeGraph that owns the provided type node",
            .args_def = struct {
                type_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.typegraph.TypeGraph.of_type(kwarg_obj.type_node.*)) |tg| {
                return make_typegraph_pyobject(tg);
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_typegraph_of_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "of_instance",
            .doc = "Return the TypeGraph that owns the provided instance node",
            .args_def = struct {
                instance_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .instance_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (faebryk.typegraph.TypeGraph.of_instance(kwarg_obj.instance_node.*)) |tg| {
                return make_typegraph_pyobject(tg);
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_typegraph_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "of",
            .doc = "Create a TypeGraph view from an existing bound node",
            .args_def = struct {
                node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            // _ = self;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const tg_value = faebryk.typegraph.TypeGraph.of(kwarg_obj.node.*);

            const allocator = std.heap.c_allocator;
            const ptr = allocator.create(faebryk.typegraph.TypeGraph) catch {
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

fn wrap_typegraph_make_child_node_build() type {
    return struct {
        pub const descr = method_descr{
            .name = "build",
            .doc = "Return NodeCreationAttributes for a MakeChild node",
            .args_def = struct {
                value: ?*py.PyObject = null,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const allocator = std.heap.c_allocator;

            var value_copy: ?[]u8 = null;
            if (kwarg_obj.value) |value_obj| {
                if (value_obj != py.Py_None()) {
                    value_copy = bind.unwrap_str_copy(value_obj) orelse return null;
                }
            }

            const attributes = allocator.create(faebryk.nodebuilder.NodeCreationAttributes) catch {
                if (value_copy) |copy| allocator.free(copy);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };

            attributes.* = faebryk.typegraph.TypeGraph.MakeChildNode.build(
                allocator,
                if (value_copy) |copy| @as([]const u8, copy) else null,
            );

            const wrapped = bind.wrap_obj("NodeCreationAttributes", &node_creation_attributes_type, NodeCreationAttributesWrapper, attributes);
            if (wrapped == null) {
                if (attributes.*.dynamic) |*dynamic_value| {
                    dynamic_value.deinit();
                }
                allocator.destroy(attributes);
                if (value_copy) |copy| allocator.free(copy);
                return null;
            }

            value_copy = null;
            return wrapped;
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
                child_type_node: *graph.BoundNodeReference,
                identifier: *py.PyObject,
                node_attributes: ?*py.PyObject = null,

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

            const allocator = kwarg_obj.type_node.g.allocator;
            var identifier_copy: ?[]u8 = null;
            if (kwarg_obj.identifier != py.Py_None()) {
                const identifier_slice = bind.unwrap_str(kwarg_obj.identifier) orelse return null;
                identifier_copy = allocator.dupe(u8, identifier_slice) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "failed to allocate identifier");
                    return null;
                };
            }
            const resolved_child_type = kwarg_obj.child_type_node;

            const node_attrs_obj: *py.PyObject = if (kwarg_obj.node_attributes) |obj| obj else py.Py_None();
            var node_attributes: ?*faebryk.nodebuilder.NodeCreationAttributes = null;
            if (node_attrs_obj != py.Py_None()) {
                const attrs_wrapper = bind.castWrapper("NodeCreationAttributes", &node_creation_attributes_type, NodeCreationAttributesWrapper, node_attrs_obj) orelse {
                    if (identifier_copy) |copy| allocator.free(copy);
                    return null;
                };
                node_attributes = attrs_wrapper.data;
            }

            const bnode = faebryk.typegraph.TypeGraph.add_make_child(
                wrapper.data,
                kwarg_obj.type_node.*,
                resolved_child_type.*,
                if (identifier_copy) |copy| copy else null,
                node_attributes,
            ) catch {
                if (identifier_copy) |copy| allocator.free(copy);
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
                edge_attributes: *faebryk.edgebuilder.EdgeCreationAttributes,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .lhs_reference_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .rhs_reference_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .edge_attributes = bind.ARG{ .Wrapper = EdgeCreationAttributesWrapper, .storage = &edge_creation_attributes_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const type_node = kwarg_obj.type_node.*;
            const edge_attributes = kwarg_obj.edge_attributes.*;

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

fn wrap_typegraph_instantiate_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "instantiate_node",
            .doc = "Instantiate the given type node into a graph",
            .args_def = struct {
                type_node: *graph.BoundNodeReference,
                attributes: *py.PyObject,

                pub const fields_meta = .{
                    .type_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            var attributes = _unwrap_literal_str_dict(kwarg_obj.attributes, std.heap.c_allocator) catch return null;
            defer if (attributes != null) attributes.?.deinit();

            const bnode = faebryk.typegraph.TypeGraph.instantiate_node(wrapper.data, kwarg_obj.type_node.*) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "instantiate_node failed");
                return null;
            };

            if (attributes) |attrs| {
                attrs.copy_into(&bnode.node.attributes.dynamic);
            }

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
            );

            if (resolved) |node| {
                return graph_py.makeBoundNodePyObject(node);
            }
            return py.Py_None();
        }
    };
}

fn wrap_typegraph_get_graph_view() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_graph_view",
            .doc = "Return the underlying GraphView",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;
            _ = kwargs;

            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const gv = faebryk.typegraph.TypeGraph.get_graph_view(wrapper.data);
            return bind.wrap_obj("GraphView", &graph_py.graph_view_type, graph_py.GraphViewWrapper, gv);
        }
    };
}

fn wrap_typegraph_get_self_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_self_node",
            .doc = "Return the underlying BoundNode representing this TypeGraph",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;
            _ = kwargs;

            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const bnode = faebryk.typegraph.TypeGraph.get_self_node(wrapper.data);
            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_typegraph_get_type_by_name() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_type_by_name",
            .args_def = struct {
                type_identifier: *py.PyObject,
            },
            .doc = "Get a type node by name",
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.type_identifier) orelse return null;

            const bnode = faebryk.typegraph.TypeGraph.get_type_by_name(wrapper.data, identifier);
            if (bnode == null) {
                return py.Py_None();
            }

            return graph_py.makeBoundNodePyObject(bnode.?);
        }
    };
}

fn wrap_typegraph_get_or_create_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_or_create_type",
            .args_def = struct {
                type_identifier: *py.PyObject,
            },
            .doc = "Get or create a type node by name",
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const identifier = bind.unwrap_str(kwarg_obj.type_identifier) orelse return null;

            const bnode = faebryk.typegraph.TypeGraph.get_or_create_type(wrapper.data, identifier) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "get_or_create_type failed");
                return null;
            };

            return graph_py.makeBoundNodePyObject(bnode);
        }
    };
}

fn wrap_typegraph_get_type_subgraph() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_type_subgraph",
            .doc = "Return a subgraph containing only the type nodes and their edges",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;
            _ = kwargs;

            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;

            // Allocate memory for the result GraphView
            const allocator = std.heap.c_allocator;
            const result_ptr = allocator.create(graph.GraphView) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate GraphView");
                return null;
            };

            result_ptr.* = faebryk.typegraph.TypeGraph.get_type_subgraph(wrapper.data);

            const pyobj = bind.wrap_obj("GraphView", &graph_py.graph_view_type, graph_py.GraphViewWrapper, result_ptr);
            if (pyobj == null) {
                result_ptr.deinit();
                allocator.destroy(result_ptr);
            }

            return pyobj;
        }
    };
}

fn wrap_typegraph_get_type_instance_overview() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_type_instance_overview",
            .doc = "Return a list of tuples (type_name, instance_count) for all types in the TypeGraph",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.check_no_positional_args(self, args)) return null;
            _ = kwargs;

            const wrapper = bind.castWrapper("TypeGraph", &type_graph_type, TypeGraphWrapper, self) orelse return null;

            const allocator = std.heap.c_allocator;

            // Get the type instance overview from Zig
            var overview = faebryk.typegraph.TypeGraph.get_type_instance_overview(wrapper.data, allocator);
            defer overview.deinit();

            // Create a Python list
            const py_list = py.PyList_New(@intCast(overview.items.len)) orelse {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to create list");
                return null;
            };

            // Populate the list with tuples
            for (overview.items, 0..) |item, i| {
                // Create tuple (type_name, instance_count)
                const py_tuple = py.PyTuple_New(2) orelse {
                    py.Py_DECREF(py_list);
                    py.PyErr_SetString(py.PyExc_MemoryError, "Failed to create tuple");
                    return null;
                };

                // Create Python string for type_name
                const py_name = py.PyUnicode_FromStringAndSize(item.type_name.ptr, @intCast(item.type_name.len)) orelse {
                    py.Py_DECREF(py_tuple);
                    py.Py_DECREF(py_list);
                    py.PyErr_SetString(py.PyExc_MemoryError, "Failed to create string");
                    return null;
                };

                // Create Python int for instance_count
                const py_count = py.PyLong_FromSize_t(item.instance_count) orelse {
                    py.Py_DECREF(py_name);
                    py.Py_DECREF(py_tuple);
                    py.Py_DECREF(py_list);
                    py.PyErr_SetString(py.PyExc_MemoryError, "Failed to create int");
                    return null;
                };

                // Set tuple items (steals references)
                if (py.PyTuple_SetItem(py_tuple, 0, py_name) < 0) {
                    py.Py_DECREF(py_count);
                    py.Py_DECREF(py_tuple);
                    py.Py_DECREF(py_list);
                    return null;
                }
                if (py.PyTuple_SetItem(py_tuple, 1, py_count) < 0) {
                    py.Py_DECREF(py_tuple);
                    py.Py_DECREF(py_list);
                    return null;
                }

                // Set list item (steals reference)
                if (py.PyList_SetItem(py_list, @intCast(i), py_tuple) < 0) {
                    py.Py_DECREF(py_tuple);
                    py.Py_DECREF(py_list);
                    return null;
                }
            }

            return py_list;
        }
    };
}

fn wrap_typegraph_get_subgraph_of_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_subgraph_of_node",
            .doc = "Return a subgraph containing the node and all its descendants (children, traits, pointers, etc.)",
            .args_def = struct {
                start_node: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .start_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            // Allocate memory for the result GraphView
            const allocator = std.heap.c_allocator;
            const result_ptr = allocator.create(graph.GraphView) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate GraphView");
                return null;
            };

            result_ptr.* = faebryk.typegraph.TypeGraph.get_subgraph_of_node(allocator, kwarg_obj.start_node.*);

            const pyobj = bind.wrap_obj("GraphView", &graph_py.graph_view_type, graph_py.GraphViewWrapper, result_ptr);
            if (pyobj == null) {
                result_ptr.deinit();
                allocator.destroy(result_ptr);
            }

            return pyobj;
        }
    };
}

fn wrap_typegraph_make_child_node(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_typegraph_make_child_node_build(),
    };
    bind.wrap_namespace_struct(root, faebryk.typegraph.TypeGraph.MakeChildNode, extra_methods);
    make_child_node_type = type_registry.getRegisteredTypeObject("MakeChildNode");
}

fn typegraph_dealloc(self: *py.PyObject) callconv(.C) void {
    const allocator = std.heap.c_allocator;
    const wrapper = @as(*TypeGraphWrapper, @ptrCast(@alignCast(self)));
    const tg_ptr = wrapper.data;

    // Don't destroy GraphView - it's managed by Python caller
    allocator.destroy(tg_ptr);

    if (py.Py_TYPE(self)) |type_obj| {
        if (type_obj.tp_free) |free_fn_any| {
            const free_fn = @as(*const fn (?*py.PyObject) callconv(.C) void, @ptrCast(@alignCast(free_fn_any)));
            free_fn(self);
            return;
        }
    }
    py._Py_Dealloc(self);
}

fn wrap_typegraph(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_typegraph_init(),
        wrap_typegraph_of(),
        wrap_typegraph_of_type(),
        wrap_typegraph_of_instance(),
        wrap_typegraph_add_type(),
        wrap_typegraph_add_make_child(),
        wrap_typegraph_add_make_link(),
        wrap_typegraph_instantiate(),
        wrap_typegraph_instantiate_node(),
        wrap_typegraph_reference_create(),
        wrap_typegraph_reference_resolve(),
        wrap_typegraph_get_type_by_name(),
        wrap_typegraph_get_or_create_type(),
        wrap_typegraph_get_graph_view(),
        wrap_typegraph_get_self_node(),
        wrap_typegraph_get_type_subgraph(),
        wrap_typegraph_get_type_instance_overview(),
        wrap_typegraph_get_subgraph_of_node(),
    };
    bind.wrap_namespace_struct(root, faebryk.typegraph.TypeGraph, extra_methods);
    wrap_typegraph_make_child_node(root);

    type_graph_type = type_registry.getRegisteredTypeObject("TypeGraph");
    if (type_graph_type) |tg_type| {
        tg_type.tp_dealloc = @ptrCast(&typegraph_dealloc);
        if (make_child_node_type == null) {
            make_child_node_type = type_registry.getRegisteredTypeObject("MakeChildNode");
        }
        if (make_child_node_type) |mc_type| {
            if (tg_type.tp_dict) |dict_obj| {
                const mc_obj = @as(*py.PyObject, @ptrCast(@alignCast(mc_type)));
                py.Py_INCREF(mc_obj);
                if (py.PyDict_SetItemString(dict_obj, "MakeChildNode", mc_obj) != 0) {
                    py.Py_DECREF(mc_obj);
                    py.PyErr_Clear();
                } else {
                    py.Py_DECREF(mc_obj);
                }
            }
        }
    } else {
        make_child_node_type = type_registry.getRegisteredTypeObject("MakeChildNode");
    }
}

fn wrap_trait_add_trait_to() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_trait_to",
            .doc = "Instantiate the trait on the target node and attach it as a child instance",
            .args_def = struct {
                target: *graph.BoundNodeReference,
                trait_type: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .target = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .trait_type = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const trait_instance = faebryk.trait.Trait.add_trait_to(kwarg_obj.target.*, kwarg_obj.trait_type.*) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "add_trait_to failed");
                return null;
            };
            return graph_py.makeBoundNodePyObject(trait_instance);
        }
    };
}

fn wrap_trait_add_trait_instance_to() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_trait_instance_to",
            .doc = "Attach an existing trait instance to the target node",
            .args_def = struct {
                target: *graph.BoundNodeReference,
                trait_instance: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .target = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .trait_instance = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const trait_instance = faebryk.trait.Trait.add_trait_instance_to(kwarg_obj.target.*, kwarg_obj.trait_instance.*) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "add_trait_instance_to failed");
                return null;
            };
            return graph_py.makeBoundNodePyObject(trait_instance);
        }
    };
}

fn wrap_trait_mark_as_trait() type {
    return struct {
        pub const descr = method_descr{
            .name = "mark_as_trait",
            .doc = "Mark the provided node as a trait",
            .args_def = struct {
                trait_type: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .trait_type = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            faebryk.trait.Trait.mark_as_trait(kwarg_obj.trait_type.*) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "mark_as_trait failed");
                return null;
            };
            return bind.wrap_none();
        }
    };
}

fn wrap_trait_try_get_trait() type {
    return struct {
        pub const descr = method_descr{
            .name = "try_get_trait",
            .doc = "Return the trait instance attached to the target node if it exists",
            .args_def = struct {
                target: *graph.BoundNodeReference,
                trait_type: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .target = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .trait_type = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            if (faebryk.trait.Trait.try_get_trait(kwarg_obj.target.*, kwarg_obj.trait_type.*)) |trait_instance| {
                return graph_py.makeBoundNodePyObject(trait_instance);
            }
            return bind.wrap_none();
        }
    };
}

fn wrap_trait_visit_implementers() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_implementers",
            .doc = "Invoke a callback for every node implementing the given trait",
            .args_def = struct {
                trait_type: *graph.BoundNodeReference,
                f: *py.PyObject,
                ctx: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .trait_type = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const VisitCtx = struct {
                py_ctx: ?*py.PyObject,
                callable: ?*py.PyObject,
                had_error: bool = false,

                pub fn call(ctx_ptr: *anyopaque, bound_node: graph.BoundNodeReference) visitor.VisitResult(void) {
                    const inner_self: *@This() = @ptrCast(@alignCast(ctx_ptr));

                    const node_obj = graph_py.makeBoundNodePyObject(bound_node) orelse {
                        inner_self.had_error = true;
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    };

                    const args_tuple = py.PyTuple_New(2) orelse {
                        inner_self.had_error = true;
                        py.Py_DECREF(node_obj);
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    };

                    const ctx_obj: *py.PyObject = if (inner_self.py_ctx) |c| c else py.Py_None();
                    py.Py_INCREF(ctx_obj);
                    if (py.PyTuple_SetItem(args_tuple, 0, ctx_obj) < 0) {
                        inner_self.had_error = true;
                        py.Py_DECREF(node_obj);
                        py.Py_DECREF(args_tuple);
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    }

                    if (py.PyTuple_SetItem(args_tuple, 1, node_obj) < 0) {
                        inner_self.had_error = true;
                        py.Py_DECREF(args_tuple);
                        py.Py_DECREF(node_obj);
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    }

                    const result = py.PyObject_Call(inner_self.callable, args_tuple, null);
                    if (result == null) {
                        inner_self.had_error = true;
                        py.Py_DECREF(args_tuple);
                        return visitor.VisitResult(void){ .ERROR = error.Callback };
                    }

                    py.Py_DECREF(result.?);
                    py.Py_DECREF(args_tuple);
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            };

            var visit_ctx = VisitCtx{
                .py_ctx = kwarg_obj.ctx,
                .callable = kwarg_obj.f,
            };

            const result = faebryk.trait.Trait.visit_implementers(
                kwarg_obj.trait_type.*,
                void,
                @ptrCast(&visit_ctx),
                VisitCtx.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_implementers failed");
                    return null;
                },
                else => {},
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_trait(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_trait_add_trait_to(),
        wrap_trait_add_trait_instance_to(),
        wrap_trait_mark_as_trait(),
        wrap_trait_try_get_trait(),
        wrap_trait_visit_implementers(),
    };
    bind.wrap_namespace_struct(root, faebryk.trait.Trait, extra_methods);
}

fn wrap_edge_trait_create() type {
    return struct {
        pub const descr = method_descr{
            .name = "create",
            .doc = "Create a trait edge between the owner node and an existing trait instance",
            .args_def = struct {
                owner_node: *graph.Node,
                trait_instance: *graph.Node,

                pub const fields_meta = .{
                    .owner_node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                    .trait_instance = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const edge_ref = faebryk.trait.EdgeTrait.init(
                std.heap.c_allocator,
                kwarg_obj.owner_node,
                kwarg_obj.trait_instance,
            );

            const edge_obj = bind.wrap_obj("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                edge_ref.deinit();
                return null;
            }

            return edge_obj;
        }
    };
}

fn wrap_edge_trait_build() type {
    return struct {
        pub const descr = method_descr{
            .name = "build",
            .doc = "Return creation attributes for trait edges",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const allocator = std.heap.c_allocator;
            const attributes = allocator.create(faebryk.edgebuilder.EdgeCreationAttributes) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            };
            attributes.* = faebryk.trait.EdgeTrait.build();
            return bind.wrap_obj("EdgeCreationAttributes", &edge_creation_attributes_type, EdgeCreationAttributesWrapper, attributes);
        }
    };
}

fn wrap_edge_trait_is_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "is_instance",
            .doc = "Return True if the edge is a trait edge",
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
            const is_match = faebryk.trait.EdgeTrait.is_instance(kwarg_obj.edge);
            return bind.wrap_bool(is_match);
        }
    };
}

fn wrap_edge_trait_get_owner_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_owner_node",
            .doc = "Return the owner node referenced by the edge",
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
            const node_ref = faebryk.trait.EdgeTrait.get_owner_node(kwarg_obj.edge);
            return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
        }
    };
}

fn wrap_edge_trait_get_trait_instance_node() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_trait_instance_node",
            .doc = "Return the trait instance node referenced by the edge",
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
            const node_ref = faebryk.trait.EdgeTrait.get_trait_instance_node(kwarg_obj.edge);
            return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, node_ref);
        }
    };
}

fn wrap_edge_trait_get_trait_instance_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_trait_instance_of",
            .doc = "Return the trait instance reachable from the provided node via the edge, if any",
            .args_def = struct {
                edge: *graph.Edge,
                node: *graph.Node,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            if (faebryk.trait.EdgeTrait.get_trait_instance_of(kwarg_obj.edge, kwarg_obj.node)) |trait_instance| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, trait_instance);
            }
            return bind.wrap_none();
        }
    };
}

fn wrap_edge_trait_get_owner_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_owner_of",
            .doc = "Return the owner node reachable from the provided node via the edge, if any",
            .args_def = struct {
                edge: *graph.Edge,
                node: *graph.Node,

                pub const fields_meta = .{
                    .edge = bind.ARG{ .Wrapper = EdgeWrapper, .storage = &graph_py.edge_type },
                    .node = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            if (faebryk.trait.EdgeTrait.get_owner_of(kwarg_obj.edge, kwarg_obj.node)) |owner| {
                return bind.wrap_obj("Node", &graph_py.node_type, NodeWrapper, owner);
            }
            return bind.wrap_none();
        }
    };
}

fn wrap_edge_trait_visit_trait_instance_edges() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_trait_instance_edges",
            .doc = "Invoke a callback for each trait edge attached to the bound node",
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

            const result = faebryk.trait.EdgeTrait.visit_trait_instance_edges(
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
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_trait_instance_edges failed");
                    return null;
                },
                else => {},
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_trait_get_owner_edge() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_owner_edge",
            .doc = "Return the bound edge pointing from the trait instance back to its owner, if any",
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
            if (faebryk.trait.EdgeTrait.get_owner_edge(kwarg_obj.bound_node.*)) |edge_ref| {
                return graph_py.makeBoundEdgePyObject(edge_ref);
            }
            return bind.wrap_none();
        }
    };
}

fn wrap_edge_trait_get_owner_node_of() type {
    return struct {
        pub const descr = method_descr{
            .name = "get_owner_node_of",
            .doc = "Return the owner node bound to the provided trait instance, if any",
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
            if (faebryk.trait.EdgeTrait.get_owner_node_of(kwarg_obj.bound_node.*)) |owner| {
                return graph_py.makeBoundNodePyObject(owner);
            }
            return bind.wrap_none();
        }
    };
}

fn wrap_edge_trait_add_trait_instance() type {
    return struct {
        pub const descr = method_descr{
            .name = "add_trait_instance",
            .doc = "Attach an existing trait instance to the bound node",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                trait_instance: *graph.Node,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .trait_instance = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const bound_edge = faebryk.trait.EdgeTrait.add_trait_instance(
                kwarg_obj.bound_node.*,
                kwarg_obj.trait_instance,
            );
            return graph_py.makeBoundEdgePyObject(bound_edge);
        }
    };
}

fn wrap_edge_trait_visit_trait_instances_of_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "visit_trait_instances_of_type",
            .doc = "Invoke a callback for each trait edge whose target matches the requested type",
            .args_def = struct {
                owner: *graph.BoundNodeReference,
                trait_type: *graph.Node,
                f: *py.PyObject,
                ctx: ?*py.PyObject = null,

                pub const fields_meta = .{
                    .owner = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .trait_type = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
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

            const result = faebryk.trait.EdgeTrait.visit_trait_instances_of_type(
                kwarg_obj.owner.*,
                kwarg_obj.trait_type,
                void,
                @ptrCast(&visit_ctx),
                graph_py.BoundEdgeVisitor.call,
            );

            if (visit_ctx.had_error) {
                return null;
            }

            switch (result) {
                .ERROR => {
                    py.PyErr_SetString(py.PyExc_ValueError, "visit_trait_instances_of_type failed");
                    return null;
                },
                else => {},
            }

            return bind.wrap_none();
        }
    };
}

fn wrap_edge_trait_try_get_trait_instance_of_type() type {
    return struct {
        pub const descr = method_descr{
            .name = "try_get_trait_instance_of_type",
            .doc = "Return the trait instance node bound to the requested type, if any",
            .args_def = struct {
                bound_node: *graph.BoundNodeReference,
                trait_type: *graph.Node,

                pub const fields_meta = .{
                    .bound_node = bind.ARG{ .Wrapper = BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                    .trait_type = bind.ARG{ .Wrapper = NodeWrapper, .storage = &graph_py.node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            if (faebryk.trait.EdgeTrait.try_get_trait_instance_of_type(
                kwarg_obj.bound_node.*,
                kwarg_obj.trait_type,
            )) |trait_instance| {
                return graph_py.makeBoundNodePyObject(trait_instance);
            }
            return bind.wrap_none();
        }
    };
}

fn wrap_edge_trait(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_edge_trait_create(),
        wrap_edge_trait_build(),
        wrap_edge_trait_is_instance(),
        wrap_edge_trait_get_owner_node(),
        wrap_edge_trait_get_trait_instance_node(),
        wrap_edge_trait_get_trait_instance_of(),
        wrap_edge_trait_get_owner_of(),
        wrap_edge_trait_visit_trait_instance_edges(),
        wrap_edge_trait_get_owner_edge(),
        wrap_edge_trait_get_owner_node_of(),
        wrap_edge_trait_add_trait_instance(),
        wrap_edge_trait_visit_trait_instances_of_type(),
        wrap_edge_trait_try_get_trait_instance_of_type(),
    };
    bind.wrap_namespace_struct(root, faebryk.trait.EdgeTrait, extra_methods);
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
    wrap_edge_trait(module.?);

    if (py.PyModule_AddObject(root, "trait", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_nodebuilder_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_nodebuilder(module.?);

    if (py.PyModule_AddObject(root, "nodebuilder", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_edgebuilder_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_edgebuilder(module.?);

    if (py.PyModule_AddObject(root, "edgebuilder", module) < 0) {
        return null;
    }

    return module;
}

fn wrap_operand_file(root: *py.PyObject) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, 1013);
    if (module == null) {
        return null;
    }

    wrap_edge_operand(module.?);

    if (py.PyModule_AddObject(root, "operand", module) < 0) {
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
    _ = wrap_nodebuilder_file(module.?);
    _ = wrap_edgebuilder_file(module.?);
    _ = wrap_trait_file(module.?);
    _ = wrap_operand_file(module.?);
    return module;
}
