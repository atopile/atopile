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

// ====================================================================================================================

fn wrap_edge_composition_create() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const arg_def = struct {
                parent: *py.PyObject,
                child: *py.PyObject,
                child_identifier: *py.PyObject,
            };

            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, arg_def) orelse return null;

            const parent = graph_py.castWrapper("Node", &graph_py.node_type, NodeWrapper, kwarg_obj.parent) orelse return null;
            const child = graph_py.castWrapper("Node", &graph_py.node_type, NodeWrapper, kwarg_obj.child) orelse return null;

            const identifier_c = py.PyUnicode_AsUTF8(kwarg_obj.child_identifier);
            if (identifier_c == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child_identifier must be a string");
                return null;
            }
            const identifier_slice = std.mem.span(identifier_c.?);

            const allocator = std.heap.c_allocator;
            const identifier_copy = allocator.dupe(u8, identifier_slice) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate child_identifier");
                return null;
            };
            const identifier_const: []const u8 = identifier_copy;

            const edge_ref = faebryk.composition.EdgeComposition.init(
                allocator,
                parent.data,
                child.data,
                identifier_const,
            ) catch {
                allocator.free(identifier_copy);
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to create EdgeComposition edge");
                return null;
            };

            const edge_obj = graph_py.makeWrapperPyObject("Edge", &graph_py.edge_type, EdgeWrapper, edge_ref);
            if (edge_obj == null) {
                allocator.free(identifier_copy);
                edge_ref.deinit() catch {};
                return null;
            }

            return edge_obj;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "create",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Create a new EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_is_instance() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const arg_def = struct {
                edge: *py.PyObject,
            };

            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, arg_def) orelse return null;

            const edge = graph_py.castWrapper("Edge", &graph_py.edge_type, EdgeWrapper, kwarg_obj.edge) orelse return null;
            const is_match = faebryk.composition.EdgeComposition.is_instance(edge.data);
            const py_bool = if (is_match) py.Py_True() else py.Py_False();
            py.Py_INCREF(py_bool);
            return py_bool;
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "is_instance",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Check if the object is an instance of EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_visit_children_edges() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const arg_def = struct {
                bound_node: *py.PyObject,
                f: *py.PyObject,
                ctx: ?*py.PyObject = null,
            };

            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, arg_def) orelse return null;

            const bound_node = graph_py.castWrapper("BoundNodeReference", &graph_py.bound_node_type, BoundNodeWrapper, kwarg_obj.bound_node) orelse return null;

            var visit_ctx = graph_py.BoundEdgeVisitor{
                .py_ctx = kwarg_obj.ctx,
                .callable = kwarg_obj.f,
            };

            const result = faebryk.composition.EdgeComposition.visit_children_edges(
                bound_node.data.*,
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

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "visit_children_edges",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Visit the children edges of the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_get_parent_edge() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const arg_def = struct {
                bound_node: *py.PyObject,
            };

            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, arg_def) orelse return null;

            const bound_node = graph_py.castWrapper("BoundNodeReference", &graph_py.bound_node_type, BoundNodeWrapper, kwarg_obj.bound_node) orelse return null;

            const parent_edge = faebryk.composition.EdgeComposition.get_parent_edge(bound_node.data.*);
            if (parent_edge) |edge_ref| {
                return graph_py.makeBoundEdgePyObject(edge_ref);
            }

            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "get_parent_edge",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Get the parent edge of the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_add_child() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const arg_def = struct {
                bound_node: *py.PyObject,
                child: *py.PyObject,
                child_identifier: *py.PyObject,
            };

            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, arg_def) orelse return null;

            const bound_node = graph_py.castWrapper(
                "BoundNodeReference",
                &graph_py.bound_node_type,
                BoundNodeWrapper,
                kwarg_obj.bound_node,
            ) orelse return null;
            const child = graph_py.castWrapper(
                "Node",
                &graph_py.node_type,
                NodeWrapper,
                kwarg_obj.child,
            ) orelse return null;

            const identifier_c = py.PyUnicode_AsUTF8(kwarg_obj.child_identifier);
            if (identifier_c == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "child_identifier must be a string");
                return null;
            }
            const identifier_slice = std.mem.span(identifier_c.?);

            const allocator = bound_node.data.g.allocator;
            const identifier_copy = allocator.dupe(u8, identifier_slice) catch {
                py.PyErr_SetString(py.PyExc_MemoryError, "Failed to allocate child_identifier");
                return null;
            };

            const bound_edge = faebryk.composition.EdgeComposition.add_child(
                bound_node.data.*,
                child.data,
                identifier_copy,
            ) catch {
                allocator.free(identifier_copy);
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to add child edge");
                return null;
            };

            return graph_py.makeBoundEdgePyObject(bound_edge);
        }

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "add_child",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Add a child to the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_get_name() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            const arg_def = struct {
                edge: *py.PyObject,
            };

            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, arg_def) orelse return null;

            const edge = graph_py.castWrapper("Edge", &graph_py.edge_type, EdgeWrapper, kwarg_obj.edge) orelse return null;

            const name = faebryk.composition.EdgeComposition.get_name(edge.data) catch |err| {
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

        pub fn method(impl_fn: *const py.PyMethodDefFnKW) py.PyMethodDef {
            return .{
                .ml_name = "get_name",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_KEYWORDS | py.METH_STATIC,
                .ml_doc = "Get the name of the EdgeComposition",
            };
        }
    };
}

fn wrap_edge_composition_get_tid() type {
    return struct {
        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject) callconv(.C) ?*py.PyObject {
            if (!bind.parse_static_property(self, args, null)) return null;

            const tid = faebryk.composition.EdgeComposition.get_tid();
            return py.PyLong_FromLongLong(@intCast(tid));
        }

        pub fn method(impl_fn: *const py.PyMethodDefFn) py.PyMethodDef {
            return .{
                .ml_name = "get_tid",
                .ml_meth = @ptrCast(impl_fn),
                .ml_flags = py.METH_VARARGS | py.METH_STATIC,
                .ml_doc = "Get the tid of the EdgeComposition",
            };
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
