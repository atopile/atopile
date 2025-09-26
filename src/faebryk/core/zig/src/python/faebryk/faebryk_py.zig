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

var edge_composition_type: ?*py.PyTypeObject = null;

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
                edge_ref.deinit() catch {};
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

            const tid = faebryk.composition.EdgeComposition.get_tid();
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

fn wrap_module(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_node_type(root: *py.PyObject) void {
    _ = root;
    // TODO
}

fn wrap_pointer(root: *py.PyObject) void {
    _ = root;
    // TODO
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
    _ = wrap_pointer_file(module.?);
    _ = wrap_trait_file(module.?);
    return module;
}
