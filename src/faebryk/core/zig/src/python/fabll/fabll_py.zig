const std = @import("std");
const pyzig = @import("pyzig");
const fabll = @import("fabll");
const graph_mod = @import("graph");
const faebryk = @import("faebryk");
const graph_py = @import("../graph/graph_py.zig");
const common = @import("common.zig");
const child_field_helpers = @import("child_field.zig");
const strings_utils = @import("strings_utils.zig");

const py = pyzig.pybindings;
const bind = pyzig.pyzig;
const type_registry = pyzig.type_registry;
const util = pyzig.util;
const graph = graph_mod.graph;

const StringWrapper = bind.PyObjectWrapper(fabll.literals.String);
const StringsWrapper = bind.PyObjectWrapper(fabll.literals.Strings);
const ChildField = strings_utils.ChildField;
const ChildFieldWrapper = strings_utils.ChildFieldWrapper;
const CountsWrapper = bind.PyObjectWrapper(fabll.literals.Counts);
const BooleansWrapper = bind.PyObjectWrapper(fabll.literals.Booleans);
const StringsBoundType = faebryk.fabll.TypeNodeBoundTG(fabll.literals.Strings);
const StringsBoundWrapper = bind.PyObjectWrapper(StringsBoundType);
const CountsBoundType = faebryk.fabll.TypeNodeBoundTG(fabll.literals.Counts);
const CountsBoundWrapper = bind.PyObjectWrapper(CountsBoundType);
const BooleansBoundType = faebryk.fabll.TypeNodeBoundTG(fabll.literals.Booleans);
const BooleansBoundWrapper = bind.PyObjectWrapper(BooleansBoundType);

var string_type: ?*py.PyTypeObject = null;
var strings_type: ?*py.PyTypeObject = null;
var counts_type: ?*py.PyTypeObject = null;
var booleans_type: ?*py.PyTypeObject = null;
var strings_child_field_type: ?*py.PyTypeObject = null;
var strings_bound_type: ?*py.PyTypeObject = null;
var counts_bound_type: ?*py.PyTypeObject = null;
var booleans_bound_type: ?*py.PyTypeObject = null;

fn wrap_node_create_instance(
    comptime NodeType: type,
    comptime NodeWrapper: type,
    comptime node_py_name: [:0]const u8,
    node_storage: *?*py.PyTypeObject,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a new Zig fabll node instance",
            .args_def = struct {
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const instance = faebryk.fabll.Node.bind_typegraph(NodeType, tg_ptr).create_instance(g_ptr);
            return common.wrap_owned_obj(
                node_py_name,
                NodeType,
                NodeWrapper,
                node_storage,
                instance,
            );
        }
    };
}

fn wrap_node_bind_instance(
    comptime NodeType: type,
    comptime NodeWrapper: type,
    comptime node_py_name: [:0]const u8,
    node_storage: *?*py.PyTypeObject,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_instance",
            .doc = "Bind an existing node instance as a Zig fabll node",
            .args_def = struct {
                instance: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .instance = bind.ARG{ .Wrapper = graph_py.BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const bound = faebryk.fabll.Node.bind_instance(NodeType, kwarg_obj.instance.*);
            return common.wrap_owned_obj(
                node_py_name,
                NodeType,
                NodeWrapper,
                node_storage,
                bound,
            );
        }
    };
}

fn wrap_node_get_instance(
    comptime node_py_name: [:0]const u8,
    comptime NodeWrapper: type,
    node_storage: *?*py.PyTypeObject,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_instance",
            .doc = "Get bound node instance for this node",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(node_py_name, node_storage, NodeWrapper, self) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.node.instance);
        }
    };
}

fn wrap_node_type_identifier(comptime NodeType: type) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "_type_identifier",
            .doc = "Return Zig type identifier for this node type",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            return bind.wrap_str(@typeName(NodeType));
        }
    };
}

fn wrap_node_bind_typegraph(
    comptime NodeType: type,
    comptime BoundType: type,
    comptime wrap_bound_obj: fn (BoundType) ?*py.PyObject,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_typegraph",
            .doc = "Bind node type to a Zig TypeGraph",
            .args_def = struct {
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const bound = faebryk.fabll.Node.bind_typegraph(NodeType, tg_ptr);
            return wrap_bound_obj(bound);
        }
    };
}

fn wrap_bound_create_instance(
    comptime BoundWrapper: type,
    comptime bound_py_name: [:0]const u8,
    bound_storage: *?*py.PyTypeObject,
    comptime NodeType: type,
    comptime NodeWrapper: type,
    comptime node_py_name: [:0]const u8,
    node_storage: *?*py.PyTypeObject,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create an instance from a bound Zig type",
            .args_def = struct {
                g: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(
                bound_py_name,
                bound_storage,
                BoundWrapper,
                self,
            ) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            return common.wrap_owned_obj(
                node_py_name,
                NodeType,
                NodeWrapper,
                node_storage,
                wrapper.data.create_instance(g_ptr),
            );
        }
    };
}

fn wrap_bound_get_or_create_type(
    comptime BoundWrapper: type,
    comptime bound_py_name: [:0]const u8,
    bound_storage: *?*py.PyTypeObject,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_or_create_type",
            .doc = "Get or create the Zig type node for this bound type",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper(
                bound_py_name,
                bound_storage,
                BoundWrapper,
                self,
            ) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.get_or_create_type());
        }
    };
}

fn wrap_node_contract(
    comptime NodeType: type,
    comptime NodeWrapper: type,
    comptime node_py_name: [:0]const u8,
    node_storage: *?*py.PyTypeObject,
    comptime BoundType: type,
    comptime wrap_bound_obj: fn (BoundType) ?*py.PyObject,
) [5]type {
    return .{
        wrap_node_create_instance(
            NodeType,
            NodeWrapper,
            node_py_name,
            node_storage,
        ),
        wrap_node_bind_instance(
            NodeType,
            NodeWrapper,
            node_py_name,
            node_storage,
        ),
        wrap_node_bind_typegraph(NodeType, BoundType, wrap_bound_obj),
        wrap_node_type_identifier(NodeType),
        wrap_node_get_instance(
            node_py_name,
            NodeWrapper,
            node_storage,
        ),
    };
}

fn wrap_bound_contract(
    comptime BoundWrapper: type,
    comptime bound_py_name: [:0]const u8,
    bound_storage: *?*py.PyTypeObject,
    comptime NodeType: type,
    comptime NodeWrapper: type,
    comptime node_py_name: [:0]const u8,
    node_storage: *?*py.PyTypeObject,
) [2]type {
    return .{
        wrap_bound_create_instance(
            BoundWrapper,
            bound_py_name,
            bound_storage,
            NodeType,
            NodeWrapper,
            node_py_name,
            node_storage,
        ),
        wrap_bound_get_or_create_type(
            BoundWrapper,
            bound_py_name,
            bound_storage,
        ),
    };
}

fn wrap_strings_obj(value: fabll.literals.Strings) ?*py.PyObject {
    return common.wrap_owned_obj(
        "Strings",
        fabll.literals.Strings,
        StringsWrapper,
        &strings_type,
        value,
    );
}

fn wrap_strings_child_field_obj(value: ChildField) ?*py.PyObject {
    return common.wrap_owned_obj(
        "ChildField",
        ChildField,
        ChildFieldWrapper,
        &strings_child_field_type,
        value,
    );
}

fn wrap_booleans_obj(value: fabll.literals.Booleans) ?*py.PyObject {
    return common.wrap_owned_obj(
        "Booleans",
        fabll.literals.Booleans,
        BooleansWrapper,
        &booleans_type,
        value,
    );
}

fn wrap_counts_obj(value: fabll.literals.Counts) ?*py.PyObject {
    return common.wrap_owned_obj(
        "Counts",
        fabll.literals.Counts,
        CountsWrapper,
        &counts_type,
        value,
    );
}

fn wrap_strings_bound_obj(value: StringsBoundType) ?*py.PyObject {
    return common.wrap_owned_obj(
        "StringsBoundType",
        StringsBoundType,
        StringsBoundWrapper,
        &strings_bound_type,
        value,
    );
}

fn wrap_counts_bound_obj(value: CountsBoundType) ?*py.PyObject {
    return common.wrap_owned_obj(
        "CountsBoundType",
        CountsBoundType,
        CountsBoundWrapper,
        &counts_bound_type,
        value,
    );
}

fn wrap_booleans_bound_obj(value: BooleansBoundType) ?*py.PyObject {
    return common.wrap_owned_obj(
        "BooleansBoundType",
        BooleansBoundType,
        BooleansBoundWrapper,
        &booleans_bound_type,
        value,
    );
}

fn make_bound_child_accessor(
    instance: graph.BoundNodeReference,
    module_name: [:0]const u8,
    nodetype_name: [:0]const u8,
    identifier: [:0]const u8,
) ?*py.PyObject {
    const node_mod = py.PyImport_ImportModule("faebryk.core.node") orelse return null;
    defer py.Py_DECREF(node_mod);
    const accessor_cls = py.PyObject_GetAttrString(node_mod, "InstanceChildBoundInstance") orelse return null;
    defer py.Py_DECREF(accessor_cls);

    const trait_mod = py.PyImport_ImportModule(module_name) orelse return null;
    defer py.Py_DECREF(trait_mod);
    const nodetype = py.PyObject_GetAttrString(trait_mod, nodetype_name) orelse return null;
    defer py.Py_DECREF(nodetype);

    const instance_obj = graph_py.makeBoundNodePyObject(instance) orelse return null;
    defer py.Py_DECREF(instance_obj);

    const identifier_obj = bind.wrap_str(identifier) orelse return null;
    defer py.Py_DECREF(identifier_obj);

    const kwargs = py.PyDict_New() orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    defer py.Py_DECREF(kwargs);

    if (py.PyDict_SetItemString(kwargs, "nodetype", nodetype) < 0) {
        return null;
    }
    if (py.PyDict_SetItemString(kwargs, "identifier", identifier_obj) < 0) {
        return null;
    }
    if (py.PyDict_SetItemString(kwargs, "instance", instance_obj) < 0) {
        return null;
    }

    const empty_args = py.PyTuple_New(0) orelse {
        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
        return null;
    };
    defer py.Py_DECREF(empty_args);

    return py.PyObject_Call(accessor_cls, empty_args, kwargs);
}

fn strings_getattro(self: ?*py.PyObject, attr: ?*py.PyObject) callconv(.c) ?*py.PyObject {
    const base = py.PyObject_GenericGetAttr(self, attr);
    if (base != null) {
        return base;
    }
    if (py.PyErr_Occurred() == null) {
        return null;
    }
    py.PyErr_Clear();

    const attr_name = bind.unwrap_str(attr) orelse return null;
    if (!std.mem.eql(u8, attr_name, "is_literal")) {
        py.PyErr_SetString(py.PyExc_AttributeError, "attribute not found");
        return null;
    }

    const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
    return make_bound_child_accessor(
        wrapper.data.node.instance,
        "faebryk.library.Literals",
        "is_literal",
        "is_literal",
    );
}

fn wrap_strings_child_field_set_locator() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "_set_locator",
            .doc = "Set field locator for Strings child field",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            _ = kwargs;
            const wrapper = bind.castWrapper("ChildField", &strings_child_field_type, ChildFieldWrapper, self) orelse return null;

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count != 1) {
                py.PyErr_SetString(py.PyExc_TypeError, "_set_locator expects exactly one argument");
                return null;
            }
            const locator_obj = py.PyTuple_GetItem(args, 0) orelse return null;

            child_field_helpers.set_locator(&wrapper.data.base, locator_obj) orelse return null;

            if (wrapper.data.base.identifier == null) {
                wrapper.data.base.identifier = if (wrapper.data.ref_path != null)
                    strings_utils.next_is_subset_identifier()
                else
                    strings_utils.next_strings_anon_identifier() orelse return null;
            }

            py.Py_INCREF(self.?);
            return self;
        }
    };
}

fn wrap_strings_child_field_get_identifier() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_identifier",
            .doc = "Get identifier for Strings child field",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("ChildField", &strings_child_field_type, ChildFieldWrapper, self) orelse return null;
            return child_field_helpers.get_identifier_obj(&wrapper.data.base);
        }
    };
}

fn wrap_strings_child_field_get_nodetype() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_nodetype",
            .doc = "Return nodetype for this child field",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("ChildField", &strings_child_field_type, ChildFieldWrapper, self) orelse return null;
            if (wrapper.data.ref_path != null) {
                py.Py_INCREF(py.Py_None());
                return py.Py_None();
            }

            const cls = strings_type orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "Strings type is not registered");
                return null;
            };
            const out = @as(*py.PyObject, @ptrCast(@alignCast(cls)));
            py.Py_INCREF(out);
            return out;
        }
    };
}

fn wrap_strings_child_field_put_on_type() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "put_on_type",
            .doc = "Mark this child field as type-level",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("ChildField", &strings_child_field_type, ChildFieldWrapper, self) orelse return null;
            child_field_helpers.put_on_type(&wrapper.data.base);
            py.Py_INCREF(self.?);
            return self;
        }
    };
}

fn wrap_strings_child_field_mark_dependant() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "mark_dependant",
            .doc = "Mark this child field as dependant",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("ChildField", &strings_child_field_type, ChildFieldWrapper, self) orelse return null;
            child_field_helpers.mark_dependant(&wrapper.data.base);
            py.Py_INCREF(py.Py_None());
            return py.Py_None();
        }
    };
}

fn wrap_strings_child_field_is_dependant() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_dependant",
            .doc = "Return whether this child field is marked as dependant",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("ChildField", &strings_child_field_type, ChildFieldWrapper, self) orelse return null;
            return bind.wrap_bool(child_field_helpers.is_dependant(&wrapper.data.base));
        }
    };
}

fn wrap_strings_child_field_is_type_child() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_type_child",
            .doc = "Return whether this field is marked put_on_type",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("ChildField", &strings_child_field_type, ChildFieldWrapper, self) orelse return null;
            return bind.wrap_bool(child_field_helpers.is_type_child(&wrapper.data.base));
        }
    };
}

fn wrap_strings_child_field_exec_to_typegraph() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "_exec_to_typegraph",
            .doc = "Materialize this Strings child field into the target typegraph",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("ChildField", &strings_child_field_type, ChildFieldWrapper, self) orelse return null;

            var t_obj: ?*py.PyObject = null;
            var type_field = false;

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }
            if (positional_count >= 1) {
                t_obj = py.PyTuple_GetItem(args, 0);
            }
            if (positional_count >= 2) {
                type_field = bind.unwrap_bool(py.PyTuple_GetItem(args, 1));
            }

            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "t")) |kw_t| {
                    if (t_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "_exec_to_typegraph received duplicate 't' argument");
                        return null;
                    }
                    t_obj = kw_t;
                }
                if (py.PyDict_GetItemString(kw, "type_field")) |kw_type_field| {
                    type_field = bind.unwrap_bool(kw_type_field);
                }
            }

            const t = t_obj orelse {
                py.PyErr_SetString(py.PyExc_TypeError, "_exec_to_typegraph requires t");
                return null;
            };

            return strings_utils.child_field_exec(
                wrapper,
                t,
                type_field or wrapper.data.base.type_child,
            );
        }
    };
}

fn wrap_strings_child_field(root: *py.PyObject) void {
    const methods = [_]type{
        wrap_strings_child_field_set_locator(),
        wrap_strings_child_field_get_identifier(),
        wrap_strings_child_field_get_nodetype(),
        wrap_strings_child_field_put_on_type(),
        wrap_strings_child_field_mark_dependant(),
        wrap_strings_child_field_is_dependant(),
        wrap_strings_child_field_is_type_child(),
        wrap_strings_child_field_exec_to_typegraph(),
    };
    bind.wrap_namespace_struct(root, ChildField, methods);
    strings_child_field_type = type_registry.getRegisteredTypeObject(util.shortTypeName(ChildField));

    if (strings_child_field_type) |typ| {
        typ.tp_dealloc = @ptrCast(&strings_utils.child_field_dealloc);
    }
}

fn wrap_strings_make_child() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "MakeChild",
            .doc = "Create a Strings child field with optional values",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const values = strings_utils.parse_strings_makechild_values(args, kwargs, 0) orelse return null;
            return wrap_strings_child_field_obj(.{ .values = values }) orelse {
                for (values) |value| std.heap.c_allocator.free(value);
                std.heap.c_allocator.free(values);
                return null;
            };
        }
    };
}

fn wrap_strings_make_child_set_superset() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "MakeChild_SetSuperset",
            .doc = "Create an asserted IsSubset child linking a ref to a Strings literal",
            .args_def = struct {},
            .static = true,
        };

        pub fn impl(_: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }

            var ref_obj: ?*py.PyObject = null;
            if (positional_count >= 1) {
                ref_obj = py.PyTuple_GetItem(args, 0);
            }
            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "ref")) |kw_ref| {
                    if (ref_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "MakeChild_SetSuperset received duplicate 'ref' argument");
                        return null;
                    }
                    ref_obj = kw_ref;
                }
            }
            if (ref_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "MakeChild_SetSuperset requires ref");
                return null;
            }

            const values = strings_utils.parse_strings_makechild_values(args, kwargs, 1) orelse return null;
            py.Py_INCREF(ref_obj.?);
            return wrap_strings_child_field_obj(.{
                .values = values,
                .ref_path = ref_obj.?,
            }) orelse {
                py.Py_DECREF(ref_obj.?);
                for (values) |value| std.heap.c_allocator.free(value);
                std.heap.c_allocator.free(values);
                return null;
            };
        }
    };
}

fn wrap_string_create_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "create_instance",
            .doc = "Create a new Zig fabll String literal instance",
            .args_def = struct {
                g: *py.PyObject,
                tg: *py.PyObject,
                value: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;
            const value_copy = bind.unwrap_str_copy(kwarg_obj.value) orelse return null;

            const literal = fabll.literals.String.create_instance(g_ptr, tg_ptr, value_copy);
            return common.wrap_owned_obj(
                "String",
                fabll.literals.String,
                StringWrapper,
                &string_type,
                literal,
            );
        }
    };
}

fn wrap_string_bind_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "bind_instance",
            .doc = "Bind an existing node instance as a Zig fabll String",
            .args_def = struct {
                instance: *graph.BoundNodeReference,

                pub const fields_meta = .{
                    .instance = bind.ARG{ .Wrapper = graph_py.BoundNodeWrapper, .storage = &graph_py.bound_node_type },
                };
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const literal = faebryk.fabll.Node.bind_instance(fabll.literals.String, kwarg_obj.instance.*);
            return common.wrap_owned_obj(
                "String",
                fabll.literals.String,
                StringWrapper,
                &string_type,
                literal,
            );
        }
    };
}

fn wrap_string_get_value() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_value",
            .doc = "Get literal string value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("String", &string_type, StringWrapper, self) orelse return null;
            return bind.wrap_str(wrapper.data.get_value());
        }
    };
}

fn wrap_string_get_instance() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_instance",
            .doc = "Get bound node instance for this literal",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("String", &string_type, StringWrapper, self) orelse return null;
            return graph_py.makeBoundNodePyObject(wrapper.data.node.instance);
        }
    };
}

fn wrap_string(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_string_create_instance(),
        wrap_string_bind_instance(),
        wrap_string_get_value(),
        wrap_string_get_instance(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.String, extra_methods);
    string_type = type_registry.getRegisteredTypeObject("String");

    if (string_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(StringWrapper));
    }
}

fn wrap_strings_setup_from_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "setup_from_values",
            .doc = "Populate this Strings literal set from provided values",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const values_obj: *py.PyObject = blk: {
                if (kwargs) |kw| {
                    if (py.PyDict_GetItemString(kw, "values")) |kw_values| {
                        if (args != null and py.PyTuple_Size(args) != 0) {
                            py.PyErr_SetString(py.PyExc_TypeError, "Use either positional values or keyword 'values', not both");
                            return null;
                        }
                        break :blk kw_values;
                    }
                }

                const pos_args = args orelse {
                    py.PyErr_SetString(py.PyExc_TypeError, "Missing values");
                    return null;
                };
                break :blk pos_args;
            };

            if (py.PySequence_Check(values_obj) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "values must be a sequence of strings");
                return null;
            }

            const size = py.PySequence_Size(values_obj);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed([]const u8).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(values_obj, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                const value_copy = bind.unwrap_str_copy(item) orelse return null;
                values.append(value_copy) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            _ = wrapper.data.setup_from_values(values.items);
            const self_obj = self orelse return null;
            py.Py_INCREF(self_obj);
            return self_obj;
        }
    };
}

fn wrap_strings_get_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_values",
            .doc = "Return all string values in this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const values = wrapper.data.get_values(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to retrieve values");
                return null;
            };
            defer allocator.free(values);

            const out_list = py.PyList_New(@intCast(values.len));
            if (out_list == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (values, 0..) |value, idx| {
                const py_value = bind.wrap_str(value) orelse {
                    py.Py_DECREF(out_list.?);
                    return null;
                };
                if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
            }

            return out_list;
        }
    };
}

fn wrap_strings_is_singleton() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_singleton",
            .doc = "Check whether this Strings literal set has exactly one value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const out = wrapper.data.is_singleton(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute singleton check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_strings_get_single() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_single",
            .doc = "Get the single value in this Strings literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const out = wrapper.data.get_single(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected singleton StringSet");
                return null;
            };
            return bind.wrap_str(out);
        }
    };
}

fn wrap_strings_is_empty() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_empty",
            .doc = "Check whether this Strings literal set is empty",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const out = wrapper.data.is_empty(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute emptiness check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_strings_any() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "any",
            .doc = "Return an arbitrary member of this Strings literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const out = wrapper.data.any(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Cannot select a value from an empty StringSet");
                return null;
            };
            return bind.wrap_str(out);
        }
    };
}

fn strings_parse_binary_other(args: ?*py.PyObject, kwargs: ?*py.PyObject) ?*fabll.literals.Strings {
    var other_obj: ?*py.PyObject = null;

    const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
    if (positional_count < 0) {
        return null;
    }
    if (positional_count > 1) {
        py.PyErr_SetString(py.PyExc_TypeError, "Expected at most one positional argument for 'other'");
        return null;
    }
    if (positional_count == 1) {
        other_obj = py.PyTuple_GetItem(args, 0);
    }

    if (kwargs) |kw| {
        if (py.PyDict_GetItemString(kw, "other")) |kw_other| {
            if (other_obj != null) {
                py.PyErr_SetString(py.PyExc_TypeError, "Received both positional and keyword argument for 'other'");
                return null;
            }
            other_obj = kw_other;
        }
    }

    if (other_obj == null) {
        py.PyErr_SetString(py.PyExc_TypeError, "Missing required argument 'other'");
        return null;
    }

    const other_wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, other_obj) orelse return null;
    return other_wrapper.data;
}

const StringsBinaryReturnKind = enum {
    bool,
    strings,
    booleans,
};

fn wrap_strings_binary_method(
    comptime method_ident: []const u8,
    comptime method_name: [:0]const u8,
    comptime doc: [:0]const u8,
    comptime return_kind: StringsBinaryReturnKind,
    comptime error_message: [:0]const u8,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = method_name,
            .doc = doc,
            .args_def = struct {
                other: *fabll.literals.Strings,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = StringsWrapper, .storage = &strings_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const other = strings_parse_binary_other(args, kwargs) orelse return null;
            const method = @field(fabll.literals.Strings, method_ident);

            switch (return_kind) {
                .bool => {
                    const out = method(wrapper.data.*, other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return bind.wrap_bool(out);
                },
                .strings => {
                    const out = method(wrapper.data.*, other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_strings_obj(out);
                },
                .booleans => {
                    const out = method(wrapper.data.*, other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_booleans_obj(out);
                },
            }
        }
    };
}

fn wrap_strings_op_setic_equals() type {
    return wrap_strings_binary_method(
        "op_setic_equals",
        "op_setic_equals",
        "Setic equality for Strings literals",
        .bool,
        "Failed to compare StringSets",
    );
}

fn wrap_strings_op_setic_is_subset_of() type {
    return wrap_strings_binary_method(
        "op_setic_is_subset_of",
        "op_setic_is_subset_of",
        "Setic subset check for Strings literals",
        .bool,
        "Failed to compare StringSets",
    );
}

fn wrap_strings_uncertainty_equals() type {
    return wrap_strings_binary_method(
        "uncertainty_equals",
        "uncertainty_equals",
        "Uncertainty equality for Strings literals",
        .booleans,
        "Failed to compare uncertainty for StringSets",
    );
}

fn wrap_strings_nary_method(
    comptime method_ident: []const u8,
    comptime method_name: [:0]const u8,
    comptime doc: [:0]const u8,
    comptime error_message: [:0]const u8,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = method_name,
            .doc = doc,
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const method = @field(fabll.literals.Strings, method_ident);

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }

            var collected = std.array_list.Managed(*fabll.literals.Strings).init(std.heap.c_allocator);
            defer collected.deinit();

            var i: isize = 0;
            while (i < positional_count) : (i += 1) {
                const item = py.PyTuple_GetItem(args, i);
                const other = bind.castWrapper("Strings", &strings_type, StringsWrapper, item) orelse return null;
                collected.append(other.data) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "other")) |kw_other| {
                    const other = bind.castWrapper("Strings", &strings_type, StringsWrapper, kw_other) orelse return null;
                    collected.append(other.data) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                        return null;
                    };
                }
            }

            if (collected.items.len == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "Expected at least one other Strings operand");
                return null;
            }

            var acc = wrapper.data.*;
            for (collected.items) |other| {
                acc = method(acc, other.*, std.heap.c_allocator) catch {
                    py.PyErr_SetString(py.PyExc_ValueError, error_message);
                    return null;
                };
            }
            return wrap_strings_obj(acc);
        }
    };
}

fn wrap_strings_op_intersect_intervals() type {
    return wrap_strings_nary_method(
        "op_intersect_intervals",
        "op_intersect_intervals",
        "Set intersection for Strings literals",
        "Failed to intersect StringSets",
    );
}

fn wrap_strings_op_union_intervals() type {
    return wrap_strings_nary_method(
        "op_union_intervals",
        "op_union_intervals",
        "Set union for Strings literals",
        "Failed to union StringSets",
    );
}

fn wrap_strings_op_symmetric_difference_intervals() type {
    return wrap_strings_binary_method(
        "op_symmetric_difference_intervals",
        "op_symmetric_difference_intervals",
        "Set symmetric difference for Strings literals",
        .strings,
        "Failed to compute symmetric difference for StringSets",
    );
}

fn wrap_strings_pretty_str() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "pretty_str",
            .doc = "Pretty-print this Strings literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const out = wrapper.data.pretty_str(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to pretty-print StringSet");
                return null;
            };
            defer allocator.free(out);
            return bind.wrap_str(out);
        }
    };
}

fn wrap_strings_serialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "serialize",
            .doc = "Serialize this Strings literal set to API format",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Strings", &strings_type, StringsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const values = wrapper.data.get_values(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to serialize StringSet");
                return null;
            };
            defer allocator.free(values);

            const out = py.PyDict_New();
            if (out == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const type_obj = bind.wrap_str("StringSet") orelse {
                py.Py_DECREF(out.?);
                return null;
            };
            if (py.PyDict_SetItemString(out, "type", type_obj) < 0) {
                py.Py_DECREF(type_obj);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(type_obj);

            const data_obj = py.PyDict_New();
            if (data_obj == null) {
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const values_list = py.PyList_New(@intCast(values.len));
            if (values_list == null) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (values, 0..) |value, idx| {
                const py_value = bind.wrap_str(value) orelse {
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                };
                if (py.PyList_SetItem(values_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value);
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                }
            }

            if (py.PyDict_SetItemString(data_obj, "values", values_list) < 0) {
                py.Py_DECREF(values_list.?);
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(values_list.?);

            if (py.PyDict_SetItemString(out, "data", data_obj) < 0) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(data_obj.?);

            return out;
        }
    };
}

fn wrap_strings_deserialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "deserialize",
            .doc = "Deserialize a Strings literal set from API format",
            .args_def = struct {
                data: *py.PyObject,
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            _ = self;
            var data_obj: ?*py.PyObject = null;
            var g_obj: ?*py.PyObject = null;
            var tg_obj: ?*py.PyObject = null;

            const positional_count: isize = if (args) |a| py.PyTuple_Size(a) else 0;
            if (positional_count < 0) {
                return null;
            }
            if (positional_count > 3) {
                py.PyErr_SetString(py.PyExc_TypeError, "deserialize accepts at most three positional arguments: data, g, tg");
                return null;
            }
            if (positional_count >= 1) data_obj = py.PyTuple_GetItem(args, 0);
            if (positional_count >= 2) g_obj = py.PyTuple_GetItem(args, 1);
            if (positional_count >= 3) tg_obj = py.PyTuple_GetItem(args, 2);

            if (kwargs) |kw| {
                if (py.PyDict_GetItemString(kw, "data")) |kw_data| {
                    if (data_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "deserialize received duplicate 'data' argument");
                        return null;
                    }
                    data_obj = kw_data;
                }
                if (py.PyDict_GetItemString(kw, "g")) |kw_g| {
                    if (g_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "deserialize received duplicate 'g' argument");
                        return null;
                    }
                    g_obj = kw_g;
                }
                if (py.PyDict_GetItemString(kw, "tg")) |kw_tg| {
                    if (tg_obj != null) {
                        py.PyErr_SetString(py.PyExc_TypeError, "deserialize received duplicate 'tg' argument");
                        return null;
                    }
                    tg_obj = kw_tg;
                }
            }

            if (data_obj == null or g_obj == null or tg_obj == null) {
                py.PyErr_SetString(py.PyExc_TypeError, "deserialize requires data, g, and tg");
                return null;
            }

            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, g_obj.?) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, tg_obj.?) orelse return null;

            const type_obj = py.PyDict_GetItemString(data_obj.?, "type") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing required field 'type'");
                return null;
            };

            const type_value = bind.unwrap_str(type_obj) orelse return null;
            if (!std.mem.eql(u8, type_value, "StringSet")) {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected type 'StringSet'");
                return null;
            }

            const payload_obj = py.PyDict_GetItemString(data_obj.?, "data") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'data' field");
                return null;
            };

            const values_obj = py.PyDict_GetItemString(payload_obj, "values") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            };
            if (py.PySequence_Check(values_obj) == 0) {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            }

            const size = py.PySequence_Size(values_obj);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed([]const u8).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(values_obj, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                const value_copy = bind.unwrap_str_copy(item) orelse return null;
                values.append(value_copy) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            const serialized = fabll.literals.StringsSerialized{
                .type = "StringSet",
                .data = .{ .values = values.items },
            };
            const out = fabll.literals.Strings.deserialize(serialized, g_ptr, tg_ptr) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to deserialize StringSet");
                return null;
            };
            return wrap_strings_obj(out);
        }
    };
}

fn wrap_strings_bound(root: *py.PyObject) void {
    const extra_methods = wrap_bound_contract(
        StringsBoundWrapper,
        "StringsBoundType",
        &strings_bound_type,
        fabll.literals.Strings,
        StringsWrapper,
        "Strings",
        &strings_type,
    );
    bind.wrap_namespace_struct(root, StringsBoundType, extra_methods);
    strings_bound_type = type_registry.getRegisteredTypeObject(
        util.shortTypeName(StringsBoundType),
    );

    if (strings_bound_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(StringsBoundWrapper));
    }
}

fn wrap_strings(root: *py.PyObject) void {
    const extra_methods = [_]type{
        wrap_strings_make_child(),
        wrap_strings_make_child_set_superset(),
    } ++ wrap_node_contract(
        fabll.literals.Strings,
        StringsWrapper,
        "Strings",
        &strings_type,
        StringsBoundType,
        wrap_strings_bound_obj,
    ) ++ [_]type{
        wrap_strings_setup_from_values(),
        wrap_strings_get_values(),
        wrap_strings_is_singleton(),
        wrap_strings_get_single(),
        wrap_strings_is_empty(),
        wrap_strings_any(),
        wrap_strings_op_setic_equals(),
        wrap_strings_op_setic_is_subset_of(),
        wrap_strings_uncertainty_equals(),
        wrap_strings_op_intersect_intervals(),
        wrap_strings_op_union_intervals(),
        wrap_strings_op_symmetric_difference_intervals(),
        wrap_strings_pretty_str(),
        wrap_strings_serialize(),
        wrap_strings_deserialize(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.Strings, extra_methods);
    strings_type = type_registry.getRegisteredTypeObject("Strings");

    if (strings_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(StringsWrapper));
        typ.tp_getattro = @ptrCast(&strings_getattro);
    }

    wrap_strings_bound(root);
}

fn wrap_counts_setup_from_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "setup_from_values",
            .doc = "Populate this Counts literal set from provided values",
            .args_def = struct {
                values: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (py.PySequence_Check(kwarg_obj.values) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "values must be a sequence of integers");
                return null;
            }

            const size = py.PySequence_Size(kwarg_obj.values);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed(i64).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(kwarg_obj.values, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                py.PyErr_Clear();
                const value_raw = py.PyLong_AsLongLong(item);
                if (py.PyErr_Occurred() != null) {
                    py.PyErr_Clear();
                    py.PyErr_SetString(py.PyExc_ValueError, "Expected integer value");
                    return null;
                }
                values.append(@intCast(value_raw)) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            _ = wrapper.data.setup_from_values(values.items);
            const self_obj = self orelse return null;
            py.Py_INCREF(self_obj);
            return self_obj;
        }
    };
}

fn wrap_counts_get_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_values",
            .doc = "Return all count values in this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const values = wrapper.data.get_values(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to retrieve values");
                return null;
            };
            defer allocator.free(values);

            const out_list = py.PyList_New(@intCast(values.len));
            if (out_list == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (values, 0..) |value, idx| {
                const py_value = py.PyLong_FromLongLong(@intCast(value));
                if (py_value == null) {
                    py.Py_DECREF(out_list.?);
                    return null;
                }
                if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value.?);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
            }

            return out_list;
        }
    };
}

fn wrap_counts_is_singleton() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_singleton",
            .doc = "Check whether this Counts literal set has exactly one value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const out = wrapper.data.is_singleton(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute singleton check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_counts_get_single() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_single",
            .doc = "Get the single value in this Counts literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const out = wrapper.data.get_single(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected singleton CountSet");
                return null;
            };
            return py.PyLong_FromLongLong(@intCast(out));
        }
    };
}

fn wrap_counts_is_empty() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_empty",
            .doc = "Check whether this Counts literal set is empty",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const out = wrapper.data.is_empty(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute emptiness check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_counts_any() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "any",
            .doc = "Return an arbitrary member of this Counts literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const out = wrapper.data.any(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Cannot select a value from an empty CountSet");
                return null;
            };
            return py.PyLong_FromLongLong(@intCast(out));
        }
    };
}

const CountsBinaryReturnKind = enum {
    bool,
    counts,
    booleans,
};

fn wrap_counts_binary_method(
    comptime method_ident: []const u8,
    comptime method_name: [:0]const u8,
    comptime doc: [:0]const u8,
    comptime return_kind: CountsBinaryReturnKind,
    comptime error_message: [:0]const u8,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = method_name,
            .doc = doc,
            .args_def = struct {
                other: *fabll.literals.Counts,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = CountsWrapper, .storage = &counts_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const method = @field(fabll.literals.Counts, method_ident);

            switch (return_kind) {
                .bool => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return bind.wrap_bool(out);
                },
                .counts => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_counts_obj(out);
                },
                .booleans => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_booleans_obj(out);
                },
            }
        }
    };
}

fn wrap_counts_op_setic_equals() type {
    return wrap_counts_binary_method(
        "op_setic_equals",
        "op_setic_equals",
        "Setic equality for Counts literals",
        .bool,
        "Failed to compare CountSets",
    );
}

fn wrap_counts_op_setic_is_subset_of() type {
    return wrap_counts_binary_method(
        "op_setic_is_subset_of",
        "op_setic_is_subset_of",
        "Setic subset check for Counts literals",
        .bool,
        "Failed to compare CountSets",
    );
}

fn wrap_counts_uncertainty_equals() type {
    return wrap_counts_binary_method(
        "uncertainty_equals",
        "uncertainty_equals",
        "Uncertainty equality for Counts literals",
        .booleans,
        "Failed to compare uncertainty for CountSets",
    );
}

fn wrap_counts_op_intersect_intervals() type {
    return wrap_counts_binary_method(
        "op_intersect_intervals",
        "op_intersect_intervals",
        "Set intersection for Counts literals",
        .counts,
        "Failed to intersect CountSets",
    );
}

fn wrap_counts_op_union_intervals() type {
    return wrap_counts_binary_method(
        "op_union_intervals",
        "op_union_intervals",
        "Set union for Counts literals",
        .counts,
        "Failed to union CountSets",
    );
}

fn wrap_counts_op_symmetric_difference_intervals() type {
    return wrap_counts_binary_method(
        "op_symmetric_difference_intervals",
        "op_symmetric_difference_intervals",
        "Set symmetric difference for Counts literals",
        .counts,
        "Failed to compute symmetric difference for CountSets",
    );
}

fn wrap_counts_serialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "serialize",
            .doc = "Serialize this Counts literal set to API format",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Counts", &counts_type, CountsWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const serialized = wrapper.data.serialize(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to serialize CountSet");
                return null;
            };
            defer allocator.free(serialized.data.values);

            const out = py.PyDict_New();
            if (out == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const type_obj = bind.wrap_str("CountSet") orelse {
                py.Py_DECREF(out.?);
                return null;
            };
            if (py.PyDict_SetItemString(out, "type", type_obj) < 0) {
                py.Py_DECREF(type_obj);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(type_obj);

            const data_obj = py.PyDict_New();
            if (data_obj == null) {
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const values_list = py.PyList_New(@intCast(serialized.data.values.len));
            if (values_list == null) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (serialized.data.values, 0..) |value, idx| {
                const py_value = py.PyLong_FromLongLong(@intCast(value));
                if (py_value == null) {
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                }
                if (py.PyList_SetItem(values_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value.?);
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                }
            }

            if (py.PyDict_SetItemString(data_obj, "values", values_list) < 0) {
                py.Py_DECREF(values_list.?);
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(values_list.?);

            if (py.PyDict_SetItemString(out, "data", data_obj) < 0) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(data_obj.?);

            return out;
        }
    };
}

fn wrap_counts_deserialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "deserialize",
            .doc = "Deserialize a Counts literal set from API format",
            .args_def = struct {
                data: *py.PyObject,
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;

            const type_obj = py.PyDict_GetItemString(kwarg_obj.data, "type") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing required field 'type'");
                return null;
            };

            const type_value = bind.unwrap_str(type_obj) orelse return null;
            if (!std.mem.eql(u8, type_value, "CountSet")) {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected type 'CountSet'");
                return null;
            }

            const data_obj = py.PyDict_GetItemString(kwarg_obj.data, "data") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'data' field");
                return null;
            };

            const values_obj = py.PyDict_GetItemString(data_obj, "values") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            };
            if (py.PySequence_Check(values_obj) == 0) {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            }

            const size = py.PySequence_Size(values_obj);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed(i64).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(values_obj, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                py.PyErr_Clear();
                const value_raw = py.PyLong_AsLongLong(item);
                if (py.PyErr_Occurred() != null) {
                    py.PyErr_Clear();
                    py.PyErr_SetString(py.PyExc_ValueError, "Expected integer value");
                    return null;
                }
                values.append(@intCast(value_raw)) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            const serialized = fabll.literals.CountsSerialized{
                .type = "CountSet",
                .data = .{ .values = values.items },
            };
            const out = fabll.literals.Counts.deserialize(serialized, g_ptr, tg_ptr) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to deserialize CountSet");
                return null;
            };
            return wrap_counts_obj(out);
        }
    };
}

fn wrap_counts_bound(root: *py.PyObject) void {
    const extra_methods = wrap_bound_contract(
        CountsBoundWrapper,
        "CountsBoundType",
        &counts_bound_type,
        fabll.literals.Counts,
        CountsWrapper,
        "Counts",
        &counts_type,
    );
    bind.wrap_namespace_struct(root, CountsBoundType, extra_methods);
    counts_bound_type = type_registry.getRegisteredTypeObject(
        util.shortTypeName(CountsBoundType),
    );

    if (counts_bound_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(CountsBoundWrapper));
    }
}

fn wrap_counts(root: *py.PyObject) void {
    const extra_methods = wrap_node_contract(
        fabll.literals.Counts,
        CountsWrapper,
        "Counts",
        &counts_type,
        CountsBoundType,
        wrap_counts_bound_obj,
    ) ++ [_]type{
        wrap_counts_setup_from_values(),
        wrap_counts_get_values(),
        wrap_counts_is_singleton(),
        wrap_counts_get_single(),
        wrap_counts_is_empty(),
        wrap_counts_any(),
        wrap_counts_op_setic_equals(),
        wrap_counts_op_setic_is_subset_of(),
        wrap_counts_uncertainty_equals(),
        wrap_counts_op_intersect_intervals(),
        wrap_counts_op_union_intervals(),
        wrap_counts_op_symmetric_difference_intervals(),
        wrap_counts_serialize(),
        wrap_counts_deserialize(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.Counts, extra_methods);
    counts_type = type_registry.getRegisteredTypeObject("Counts");

    if (counts_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(CountsWrapper));
    }

    wrap_counts_bound(root);
}

fn wrap_booleans_setup_from_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "setup_from_values",
            .doc = "Populate this Booleans literal set from provided values",
            .args_def = struct {
                values: *py.PyObject,
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;

            if (py.PySequence_Check(kwarg_obj.values) == 0) {
                py.PyErr_SetString(py.PyExc_TypeError, "values must be a sequence of booleans");
                return null;
            }

            const size = py.PySequence_Size(kwarg_obj.values);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed(bool).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(kwarg_obj.values, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                const is_true = py.PyObject_IsTrue(item);
                if (is_true < 0) {
                    return null;
                }
                values.append(is_true != 0) catch {
                    py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                    return null;
                };
            }

            _ = wrapper.data.setup_from_values(values.items);
            const self_obj = self orelse return null;
            py.Py_INCREF(self_obj);
            return self_obj;
        }
    };
}

fn wrap_booleans_get_values() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_values",
            .doc = "Return all boolean values in this literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const values = wrapper.data.get_values(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to retrieve values");
                return null;
            };
            defer allocator.free(values);

            const out_list = py.PyList_New(@intCast(values.len));
            if (out_list == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            var has_true = false;
            var has_false = false;
            for (values) |value| {
                if (value) has_true = true else has_false = true;
            }

            if (has_true and has_false) {
                const py_true = py.Py_True();
                const py_false = py.Py_False();
                py.Py_INCREF(py_true);
                py.Py_INCREF(py_false);
                if (py.PyList_SetItem(out_list, 0, py_true) < 0) {
                    py.Py_DECREF(py_true);
                    py.Py_DECREF(py_false);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
                if (py.PyList_SetItem(out_list, 1, py_false) < 0) {
                    py.Py_DECREF(py_false);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
                return out_list;
            }

            for (values, 0..) |value, idx| {
                const py_value = if (value) py.Py_True() else py.Py_False();
                py.Py_INCREF(py_value);
                if (py.PyList_SetItem(out_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value);
                    py.Py_DECREF(out_list.?);
                    return null;
                }
            }

            return out_list;
        }
    };
}

fn wrap_booleans_is_singleton() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_singleton",
            .doc = "Check whether this Booleans literal set has exactly one value",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const out = wrapper.data.is_singleton(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute singleton check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_booleans_get_single() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "get_single",
            .doc = "Get the single value in this Booleans literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const out = wrapper.data.get_single(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected singleton BooleanSet");
                return null;
            };
            const py_value = if (out) py.Py_True() else py.Py_False();
            py.Py_INCREF(py_value);
            return py_value;
        }
    };
}

fn wrap_booleans_is_empty() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "is_empty",
            .doc = "Check whether this Booleans literal set is empty",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const out = wrapper.data.is_empty(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to compute emptiness check");
                return null;
            };
            return bind.wrap_bool(out);
        }
    };
}

fn wrap_booleans_any() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "any",
            .doc = "Return an arbitrary member of this Booleans literal set",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const out = wrapper.data.any(std.heap.c_allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Cannot select a value from an empty BooleanSet");
                return null;
            };
            const py_value = if (out) py.Py_True() else py.Py_False();
            py.Py_INCREF(py_value);
            return py_value;
        }
    };
}

const BooleansBinaryReturnKind = enum {
    bool,
    booleans,
};

fn wrap_booleans_binary_method(
    comptime method_ident: []const u8,
    comptime method_name: [:0]const u8,
    comptime doc: [:0]const u8,
    comptime return_kind: BooleansBinaryReturnKind,
    comptime error_message: [:0]const u8,
) type {
    return struct {
        pub const descr = bind.method_descr{
            .name = method_name,
            .doc = doc,
            .args_def = struct {
                other: *fabll.literals.Booleans,

                pub const fields_meta = .{
                    .other = bind.ARG{ .Wrapper = BooleansWrapper, .storage = &booleans_type },
                };
            },
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const method = @field(fabll.literals.Booleans, method_ident);

            switch (return_kind) {
                .bool => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return bind.wrap_bool(out);
                },
                .booleans => {
                    const out = method(wrapper.data.*, kwarg_obj.other.*, std.heap.c_allocator) catch {
                        py.PyErr_SetString(py.PyExc_ValueError, error_message);
                        return null;
                    };
                    return wrap_booleans_obj(out);
                },
            }
        }
    };
}

fn wrap_booleans_op_setic_equals() type {
    return wrap_booleans_binary_method(
        "op_setic_equals",
        "op_setic_equals",
        "Setic equality for Booleans literals",
        .bool,
        "Failed to compare BooleanSets",
    );
}

fn wrap_booleans_op_setic_is_subset_of() type {
    return wrap_booleans_binary_method(
        "op_setic_is_subset_of",
        "op_setic_is_subset_of",
        "Setic subset check for Booleans literals",
        .bool,
        "Failed to compare BooleanSets",
    );
}

fn wrap_booleans_uncertainty_equals() type {
    return wrap_booleans_binary_method(
        "uncertainty_equals",
        "uncertainty_equals",
        "Uncertainty equality for Booleans literals",
        .booleans,
        "Failed to compare uncertainty for BooleanSets",
    );
}

fn wrap_booleans_op_intersect_intervals() type {
    return wrap_booleans_binary_method(
        "op_intersect_intervals",
        "op_intersect_intervals",
        "Set intersection for Booleans literals",
        .booleans,
        "Failed to intersect BooleanSets",
    );
}

fn wrap_booleans_op_union_intervals() type {
    return wrap_booleans_binary_method(
        "op_union_intervals",
        "op_union_intervals",
        "Set union for Booleans literals",
        .booleans,
        "Failed to union BooleanSets",
    );
}

fn wrap_booleans_op_symmetric_difference_intervals() type {
    return wrap_booleans_binary_method(
        "op_symmetric_difference_intervals",
        "op_symmetric_difference_intervals",
        "Set symmetric difference for Booleans literals",
        .booleans,
        "Failed to compute symmetric difference for BooleanSets",
    );
}

fn wrap_booleans_serialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "serialize",
            .doc = "Serialize this Booleans literal set to API format",
            .args_def = struct {},
            .static = false,
        };

        pub fn impl(self: ?*py.PyObject, _: ?*py.PyObject, _: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const wrapper = bind.castWrapper("Booleans", &booleans_type, BooleansWrapper, self) orelse return null;
            const allocator = std.heap.c_allocator;
            const serialized = wrapper.data.serialize(allocator) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to serialize BooleanSet");
                return null;
            };
            defer allocator.free(serialized.data.values);

            const out = py.PyDict_New();
            if (out == null) {
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const type_obj = bind.wrap_str("BooleanSet") orelse {
                py.Py_DECREF(out.?);
                return null;
            };
            if (py.PyDict_SetItemString(out, "type", type_obj) < 0) {
                py.Py_DECREF(type_obj);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(type_obj);

            const data_obj = py.PyDict_New();
            if (data_obj == null) {
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            const values_list = py.PyList_New(@intCast(serialized.data.values.len));
            if (values_list == null) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                return null;
            }

            for (serialized.data.values, 0..) |value, idx| {
                const py_value = if (value) py.Py_True() else py.Py_False();
                py.Py_INCREF(py_value);
                if (py.PyList_SetItem(values_list, @intCast(idx), py_value) < 0) {
                    py.Py_DECREF(py_value);
                    py.Py_DECREF(values_list.?);
                    py.Py_DECREF(data_obj.?);
                    py.Py_DECREF(out.?);
                    return null;
                }
            }

            if (py.PyDict_SetItemString(data_obj, "values", values_list) < 0) {
                py.Py_DECREF(values_list.?);
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(values_list.?);

            if (py.PyDict_SetItemString(out, "data", data_obj) < 0) {
                py.Py_DECREF(data_obj.?);
                py.Py_DECREF(out.?);
                return null;
            }
            py.Py_DECREF(data_obj.?);

            return out;
        }
    };
}

fn wrap_booleans_deserialize() type {
    return struct {
        pub const descr = bind.method_descr{
            .name = "deserialize",
            .doc = "Deserialize a Booleans literal set from API format",
            .args_def = struct {
                data: *py.PyObject,
                g: *py.PyObject,
                tg: *py.PyObject,
            },
            .static = true,
        };

        pub fn impl(self: ?*py.PyObject, args: ?*py.PyObject, kwargs: ?*py.PyObject) callconv(.c) ?*py.PyObject {
            const kwarg_obj = bind.parse_kwargs(self, args, kwargs, descr.args_def) orelse return null;
            const g_ptr = common.unwrap_zig_address_ptr(graph.GraphView, kwarg_obj.g) orelse return null;
            const tg_ptr = common.unwrap_zig_address_ptr(faebryk.typegraph.TypeGraph, kwarg_obj.tg) orelse return null;

            const type_obj = py.PyDict_GetItemString(kwarg_obj.data, "type") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing required field 'type'");
                return null;
            };

            const type_value = bind.unwrap_str(type_obj) orelse return null;
            if (!std.mem.eql(u8, type_value, "BooleanSet")) {
                py.PyErr_SetString(py.PyExc_ValueError, "Expected type 'BooleanSet'");
                return null;
            }

            const data_obj = py.PyDict_GetItemString(kwarg_obj.data, "data") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'data' field");
                return null;
            };

            const values_obj = py.PyDict_GetItemString(data_obj, "values") orelse {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            };
            if (py.PySequence_Check(values_obj) == 0) {
                py.PyErr_SetString(py.PyExc_ValueError, "Missing or invalid 'values' field");
                return null;
            }

            const size = py.PySequence_Size(values_obj);
            if (size < 0) {
                return null;
            }

            const allocator = std.heap.c_allocator;
            var values = std.array_list.Managed(bool).init(allocator);
            defer values.deinit();

            var i: isize = 0;
            while (i < size) : (i += 1) {
                const item = py.PySequence_GetItem(values_obj, i);
                if (item == null) {
                    return null;
                }
                defer py.Py_DECREF(item.?);

                if (item == py.Py_True()) {
                    values.append(true) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                        return null;
                    };
                    continue;
                }
                if (item == py.Py_False()) {
                    values.append(false) catch {
                        py.PyErr_SetString(py.PyExc_MemoryError, "Out of memory");
                        return null;
                    };
                    continue;
                }
                py.PyErr_SetString(py.PyExc_ValueError, "Expected boolean value");
                return null;
            }

            const serialized = fabll.literals.BooleansSerialized{
                .type = "BooleanSet",
                .data = .{ .values = values.items },
            };
            const out = fabll.literals.Booleans.deserialize(serialized, g_ptr, tg_ptr) catch {
                py.PyErr_SetString(py.PyExc_ValueError, "Failed to deserialize BooleanSet");
                return null;
            };
            return wrap_booleans_obj(out);
        }
    };
}

fn wrap_booleans_bound(root: *py.PyObject) void {
    const extra_methods = wrap_bound_contract(
        BooleansBoundWrapper,
        "BooleansBoundType",
        &booleans_bound_type,
        fabll.literals.Booleans,
        BooleansWrapper,
        "Booleans",
        &booleans_type,
    );
    bind.wrap_namespace_struct(root, BooleansBoundType, extra_methods);
    booleans_bound_type = type_registry.getRegisteredTypeObject(
        util.shortTypeName(BooleansBoundType),
    );

    if (booleans_bound_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(BooleansBoundWrapper));
    }
}

fn wrap_booleans(root: *py.PyObject) void {
    const extra_methods = wrap_node_contract(
        fabll.literals.Booleans,
        BooleansWrapper,
        "Booleans",
        &booleans_type,
        BooleansBoundType,
        wrap_booleans_bound_obj,
    ) ++ [_]type{
        wrap_booleans_setup_from_values(),
        wrap_booleans_get_values(),
        wrap_booleans_is_singleton(),
        wrap_booleans_get_single(),
        wrap_booleans_is_empty(),
        wrap_booleans_any(),
        wrap_booleans_op_setic_equals(),
        wrap_booleans_op_setic_is_subset_of(),
        wrap_booleans_uncertainty_equals(),
        wrap_booleans_op_intersect_intervals(),
        wrap_booleans_op_union_intervals(),
        wrap_booleans_op_symmetric_difference_intervals(),
        wrap_booleans_serialize(),
        wrap_booleans_deserialize(),
    };
    bind.wrap_namespace_struct(root, fabll.literals.Booleans, extra_methods);
    booleans_type = type_registry.getRegisteredTypeObject("Booleans");

    if (booleans_type) |typ| {
        typ.tp_dealloc = @ptrCast(common.owned_dealloc(BooleansWrapper));
    }

    wrap_booleans_bound(root);
}

fn wrap_literals(root: *py.PyObject) void {
    wrap_string(root);
    wrap_strings_child_field(root);
    wrap_strings(root);
    wrap_counts(root);
    wrap_booleans(root);

    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.literals.Interval, extra_methods);
    bind.wrap_namespace_struct(root, fabll.literals.Numbers, extra_methods);
}

fn wrap_parameters(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.parameters.can_be_operand, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.is_parameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.is_parameter_operatable, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.NumericParameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.StringParameter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.parameters.BooleanParameter, extra_methods);
}

fn wrap_expressions(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.expressions.is_expression, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Add, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Subtract, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Multiply, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Divide, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Power, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Sqrt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Log, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Sin, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Cos, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Negate, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Round, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Abs, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Floor, extra_methods);
    bind.wrap_namespace_struct(root, fabll.expressions.Ceil, extra_methods);
}

fn wrap_units(root: *py.PyObject) void {
    const extra_methods = [_]type{};
    bind.wrap_namespace_struct(root, fabll.units.IsUnit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.has_unit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.has_display_unit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Meter, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Second, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Hour, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ampere, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Kelvin, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.DegreeCelsius, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Volt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.MilliVolt, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ohm, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Radian, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Steradian, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Bit, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Percent, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Ppm, extra_methods);
    bind.wrap_namespace_struct(root, fabll.units.Dimensionless, extra_methods);
}

var main_methods = [_]py.PyMethodDef{
    py.ML_SENTINEL,
};

var main_module_def = py.PyModuleDef{
    .m_base = .{},
    .m_name = "fabll",
    .m_doc = "Auto-generated Python extension for fabll Zig types",
    .m_size = -1,
    .m_methods = &main_methods,
};

fn add_file_module(
    root: *py.PyObject,
    comptime name: [:0]const u8,
    comptime wrap_fn: fn (*py.PyObject) void,
) ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, py.PYTHON_API_VERSION);
    if (module == null) {
        return null;
    }

    wrap_fn(module.?);

    if (py.PyModule_AddObject(root, name, module) < 0) {
        return null;
    }

    return module;
}

pub fn make_python_module() ?*py.PyObject {
    const module = py.PyModule_Create2(&main_module_def, py.PYTHON_API_VERSION);
    if (module == null) {
        return null;
    }

    _ = add_file_module(module.?, "literals", wrap_literals);
    _ = add_file_module(module.?, "parameters", wrap_parameters);
    _ = add_file_module(module.?, "expressions", wrap_expressions);
    _ = add_file_module(module.?, "units", wrap_units);

    return module;
}
