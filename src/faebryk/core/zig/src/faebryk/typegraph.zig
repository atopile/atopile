// TypeGraph owns the structural description of types, including pointer
// sequences. All path lookups (e.g. "items[0].connection") must flow through
// this file so the semantics of mounts and pointer-sequence indices stay
// consistent across language bindings. The AST visitor performs lexical checks
// only; the logic below is the single source of truth for mapping hierarchical
// field references onto MakeChild nodes.

const graph_mod = @import("graph");
const std = @import("std");
const node_type_mod = @import("node_type.zig");
const composition_mod = @import("composition.zig");
const next_mod = @import("next.zig");
const pointer_mod = @import("pointer.zig");
const edgebuilder_mod = @import("edgebuilder.zig");
const operand_mod = @import("operand.zig");
const nodebuilder_mod = @import("nodebuilder.zig");
const linker_mod = @import("linker.zig");
const ascii = std.ascii;
const trait_mod = @import("trait.zig");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;

const NodeReference = graph.NodeReference;
const EdgeReference = graph.EdgeReference;
const Edge = graph.Edge;
const Node = graph.Node;
const GraphView = graph.GraphView;
const BoundNodeReference = graph.BoundNodeReference;
const str = graph.str;
const EdgeType = node_type_mod.EdgeType;
const EdgeComposition = composition_mod.EdgeComposition;
const EdgePointer = pointer_mod.EdgePointer;
const EdgeNext = next_mod.EdgeNext;
const EdgeOperand = operand_mod.EdgeOperand;
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;
const NodeCreationAttributes = nodebuilder_mod.NodeCreationAttributes;
const Linker = linker_mod.Linker;
const EdgeTrait = trait_mod.EdgeTrait;
const Trait = trait_mod.Trait;
const return_first = visitor.return_first;
// TODO: BoundNodeReference and NodeReference used mixed all over the place
// TODO: move add/create functions into respective structs

pub const TypeGraph = struct {
    self_node: BoundNodeReference,

    pub const PathErrorKind = enum {
        missing_parent,
        missing_child,
        invalid_index,
    };

    pub const PathResolutionFailure = struct {
        kind: PathErrorKind,
        /// Index of the segment that could not be resolved (0-based).
        failing_segment_index: usize,
        failing_segment: []const u8,
        has_index_value: bool = false,
        index_value: usize = 0,
    };

    pub const MakeChildInfo = struct {
        identifier: ?[]const u8,
        make_child: BoundNodeReference,
        order: u7 = 0,
        edge_specific: ?u16 = null,
    };

    pub const MakeLinkInfo = struct {
        make_link: BoundNodeReference,
        lhs_path: []const ChildReferenceNode.EdgeTraversal,
        rhs_path: []const ChildReferenceNode.EdgeTraversal,
    };

    pub const ValidationError = struct {
        node: BoundNodeReference,
        message: []const u8,
    };

    /// Error returned when instantiation fails, containing the failing node
    /// (MakeChild or MakeLink) and an error message for rich error reporting.
    pub const InstantiationError = struct {
        node: BoundNodeReference,
        message: []const u8,
        kind: InstantiationErrorKind,
        identifier: []const u8 = "",
    };

    pub const InstantiationErrorKind = enum {
        unresolved_type_reference,
        unresolved_reference,
        missing_operand_reference,
        invalid_argument,
        other,
    };

    /// Error returned when path resolution fails, containing the failing reference node
    /// and an error message for rich error reporting via DSLRichException.
    pub const ResolveError = struct {
        node: BoundNodeReference,
        message: []const u8,
        kind: ResolveErrorKind,
        identifier: []const u8 = "",
    };

    pub const ResolveErrorKind = enum {
        type_not_found,
        composition_child_not_found,
        trait_type_not_found,
        trait_instance_not_found,
        pointer_dereference_failed,
        operand_not_found,
        unknown_edge_type,
        typegraph_not_found,
    };

    pub const ChildResolveResult = union(enum) {
        ok: graph.BoundNodeReference,
        err: ResolveError,
    };

    pub const TypeNodeAttributes = struct {
        node: NodeReference,

        pub fn of(node: NodeReference) @This() {
            return .{ .node = node };
        }

        pub const type_identifier = "type_identifier";

        pub fn set_type_name(self: @This(), name: str) void {
            // TODO consider making a put_string that copies the string instead and deallocates it again
            self.node.put(type_identifier, .{ .String = name });
        }
        pub fn get_type_name(self: @This()) str {
            return self.node.get(type_identifier).?.String;
        }
    };

    // Bootstrap helpers
    pub const TypeNode = struct {
        pub fn create_and_insert(tg: *TypeGraph, type_identifier: str) BoundNodeReference {
            const implements_type_type_node = tg.self_node.g.create_and_insert_node();
            TypeNodeAttributes.of(implements_type_type_node.node).set_type_name(type_identifier);
            _ = EdgeComposition.add_child(tg.self_node, implements_type_type_node.node, type_identifier);
            return implements_type_type_node;
        }

        pub fn spawn_instance(bound_type_node: BoundNodeReference) BoundNodeReference {
            const instance_node = bound_type_node.g.create_and_insert_node();
            _ = EdgeType.add_instance(bound_type_node, instance_node);
            return instance_node;
        }
    };

    pub const TraitNode = struct {
        pub fn add_trait_as_child_to(target: BoundNodeReference, trait_type: BoundNodeReference) BoundNodeReference {
            const trait_instance = TypeNode.spawn_instance(trait_type);
            _ = EdgeComposition.add_child(target, trait_instance.node, null);
            _ = EdgeTrait.add_trait_instance(target, trait_instance.node);
            return trait_instance;
        }
    };

    pub const MakeChildNode = struct {
        pub const Attributes = struct {
            node: BoundNodeReference,

            pub fn of(node: BoundNodeReference) @This() {
                return .{ .node = node };
            }

            pub const child_identifier = "child_identifier";
            pub const child_literal_value = "child_literal_value";
            pub const soft_create_key = "soft_create";

            pub fn init(self: @This(), identifier: ?str, soft: bool) void {
                if (identifier) |id| {
                    self.node.node.put(child_identifier, .{ .String = id });
                }
                if (soft) {
                    self.node.node.put(soft_create_key, .{ .Bool = true });
                }
            }

            pub fn soft_create(self: @This()) bool {
                if (self.node.node.get(soft_create_key)) |value| {
                    return value.Bool;
                }
                return false; // default to not soft-created
            }

            pub fn get_child_identifier(self: @This()) ?str {
                if (self.node.node.get(child_identifier)) |value| {
                    return value.String;
                }
                return null;
            }

            pub fn store_node_attributes(self: @This(), attributes: NodeCreationAttributes) void {
                // TODO different API
                self.node.node.copy_dynamic_attributes_into(&attributes.dynamic);
            }

            pub fn load_node_attributes(self: @This(), node: NodeReference) void {
                var dynamic = graph.DynamicAttributes.init_on_stack();

                const AttrVisitor = struct {
                    dynamic: *graph.DynamicAttributes,

                    pub fn visit(ctx: *anyopaque, key: str, value: graph.Literal, _dynamic: bool) void {
                        const s: *@This() = @ptrCast(@alignCast(ctx));
                        if (!_dynamic) return;
                        if (std.mem.eql(u8, key, "child_identifier")) {
                            return;
                        }
                        s.dynamic.put(key, value);
                    }
                };
                var visit = AttrVisitor{ .dynamic = &dynamic };
                self.node.node.visit_attributes(&visit, AttrVisitor.visit);

                // TODO different API
                node.copy_dynamic_attributes_into(&dynamic);
            }

            /// Extract dynamic attributes from this MakeChild into a NodeCreationAttributes struct.
            /// Used when copying MakeChild nodes during inheritance.
            pub fn extract_node_attributes(self: @This()) NodeCreationAttributes {
                var dynamic = graph.DynamicAttributes.init_on_stack();

                const AttrVisitor = struct {
                    dynamic: *graph.DynamicAttributes,

                    pub fn visit(ctx: *anyopaque, key: str, value: graph.Literal, _dynamic: bool) void {
                        const s: *@This() = @ptrCast(@alignCast(ctx));
                        if (!_dynamic) return;
                        // Skip internal MakeChild attributes
                        if (std.mem.eql(u8, key, "child_identifier")) return;
                        if (std.mem.eql(u8, key, soft_create_key)) return;
                        s.dynamic.put(key, value);
                    }
                };
                var visit = AttrVisitor{ .dynamic = &dynamic };
                self.node.node.visit_attributes(&visit, AttrVisitor.visit);

                return .{ .dynamic = dynamic };
            }
        };

        pub fn build(value: ?str) NodeCreationAttributes {
            var dynamic = graph.DynamicAttributes.init_on_stack();

            if (value) |v| {
                dynamic.put("value", .{ .String = v });
            }
            return .{
                .dynamic = dynamic,
            };
        }

        pub fn get_child_type(mc_node: BoundNodeReference) ?BoundNodeReference {
            const type_ref = get_type_reference(mc_node);
            return TypeReferenceNode.get_resolved_type(type_ref);
        }

        const type_reference_identifier = "type_ref";

        pub fn set_type_reference(mc_node: BoundNodeReference, type_reference: BoundNodeReference) void {
            _ = EdgeComposition.add_child(mc_node, type_reference.node, type_reference_identifier);
        }

        pub fn get_type_reference(mc_node: BoundNodeReference) BoundNodeReference {
            return EdgeComposition.get_child_by_identifier(mc_node, type_reference_identifier).?;
        }
    };

    pub const TypeReferenceNode = struct {
        pub const Attributes = struct {
            node: NodeReference,

            pub fn of(node: NodeReference) @This() {
                return .{ .node = node };
            }

            pub const type_identifier = "type_identifier";

            pub fn set_type_identifier(self: @This(), identifier: str) void {
                self.node.put(type_identifier, .{ .String = identifier });
            }

            pub fn get_type_identifier(self: @This()) str {
                return self.node.get(type_identifier).?.String;
            }
        };

        pub fn create_and_insert(tg: *TypeGraph, type_identifier: str) !BoundNodeReference {
            const reference = switch (tg.instantiate_node(tg.get_TypeReference())) {
                .ok => |n| n,
                .err => return error.InstantiationFailed,
            };
            TypeReferenceNode.Attributes.of(reference.node).set_type_identifier(type_identifier);
            return reference;
        }

        pub fn get_resolved_type(reference: BoundNodeReference) ?BoundNodeReference {
            return Linker.try_get_resolved_type(reference);
        }

        pub fn get_type_identifier(reference: BoundNodeReference) str {
            return Attributes.of(reference.node).get_type_identifier();
        }

        pub fn build(value: ?str) NodeCreationAttributes {
            var dynamic = graph.DynamicAttributes.init_on_stack();
            if (value) |v| {
                dynamic.put("value", .{ .String = v });
            }
            return .{
                .dynamic = dynamic,
            };
        }
    };

    pub const ChildReferenceNode = struct {
        pub const Attributes = struct {
            node: NodeReference,

            pub fn of(node: NodeReference) @This() {
                return .{ .node = node };
            }

            pub const child_identifier = "child_identifier";
            pub const edge_type_tid_key = "edge_type_tid";

            pub fn set_child_identifier(self: @This(), identifier: str) void {
                self.node.put(child_identifier, .{ .String = identifier });
            }

            pub fn get_child_identifier(self: @This()) str {
                return self.node.get(child_identifier).?.String;
            }

            /// Set the edge type to traverse for this reference segment.
            /// If not set, defaults to EdgeComposition.tid.
            pub fn set_edge_type(self: @This(), tid: Edge.EdgeType) void {
                self.node.put(edge_type_tid_key, .{ .Int = tid });
            }

            /// Get the edge type to traverse for this reference segment.
            /// Returns EdgeComposition.tid if not explicitly set.
            pub fn get_edge_type(self: @This()) Edge.EdgeType {
                if (self.node.get(edge_type_tid_key)) |val| {
                    return @intCast(val.Int);
                }
                return EdgeComposition.tid; // default to composition edges
            }
        };

        /// EdgeTraversal specifies how to traverse a single path segment.
        /// It pairs an identifier (the edge name to match) with an edge type
        /// (Composition, Trait, or Pointer) to determine the traversal method.
        ///
        /// Use the traverse() methods on the edge types to create these:
        /// - EdgeComposition.traverse(identifier) - follow a Composition edge by name
        /// - EdgeTrait.traverse(trait_type_name) - find a trait instance by type name
        /// - EdgePointer.traverse() - dereference the current Pointer node
        pub const EdgeTraversal = struct {
            identifier: str,
            edge_type: Edge.EdgeType,
        };

        /// Create a reference chain where each segment specifies both an identifier
        /// and the edge type to traverse (Composition, Trait, or Pointer).
        /// This enables paths like: resistor -> can_bridge (Trait) -> in_ (Pointer)
        pub fn create_and_insert(tg: *TypeGraph, path: []const EdgeTraversal) !BoundNodeReference {
            if (path.len == 0) {
                return error.EmptyPath;
            }

            var root: ?BoundNodeReference = null;
            var current_node: ?BoundNodeReference = null;

            for (path) |segment| {
                const reference = switch (tg.instantiate_node(tg.get_Reference())) {
                    .ok => |n| n,
                    .err => return error.InstantiationFailed,
                };
                if (current_node) |_current_node| {
                    _ = EdgeNext.add_next(_current_node, reference);
                } else {
                    root = reference;
                }

                ChildReferenceNode.Attributes.of(reference.node).set_child_identifier(segment.identifier);
                // Only set edge type if not the default (Composition)
                if (segment.edge_type != EdgeComposition.tid) {
                    ChildReferenceNode.Attributes.of(reference.node).set_edge_type(segment.edge_type);
                }
                current_node = reference;
            }

            return root.?;
        }

        pub fn get_make_child_node_by_child_identifier(bound_node: BoundNodeReference, child_identifier: str) ?BoundNodeReference {
            const Finder = struct {
                identifier: str,

                pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(graph.BoundNodeReference) {
                    const self: *@This() = @ptrCast(@alignCast(self_ptr));
                    const make_child = EdgeComposition.get_child_node(bound_edge.edge);
                    const make_child_child_identifier = TypeGraph.MakeChildNode.Attributes.of(make_child).get_child_identifier();
                    if (make_child_child_identifier) |_make_child_child_identifier| {
                        if (std.mem.eql(u8, _make_child_child_identifier, self.identifier)) {
                            return visitor.VisitResult(graph.BoundNodeReference){ .OK = bound_edge };
                        }
                    }
                    return visitor.VisitResult(graph.BoundNodeReference){ .CONTINUE = {} };
                }
            };

            const tg = TypeGraph.of_type_or_instance(bound_node).?;
            const make_child_type_node = tg.get_MakeChild();
            var finder = Finder{ .identifier = child_identifier };
            const result = EdgeComposition.visit_children_of_type(bound_node, make_child_type_node.node, graph.BoundEdgeReference, &finder, return_first(graph.BoundEdgeReference).visit);
            switch (result) {
                .OK => |found| return found.g.bind(EdgeComposition.get_child_node(found.edge)),
                .CONTINUE => unreachable,
                .STOP => unreachable,
                .ERROR => return null, // Convert error to null since function returns optional
                .EXHAUSTED => return null,
            }
        }

        pub fn resolve(reference: BoundNodeReference, instance: BoundNodeReference) ChildResolveResult {
            // TODO iterate instead of recursion
            var target = instance;
            const child_identifier = ChildReferenceNode.Attributes.of(reference.node).get_child_identifier();
            const edge_type = ChildReferenceNode.Attributes.of(reference.node).get_edge_type();
            const tg = TypeGraph.of_instance(reference) orelse {
                return ChildResolveResult{ .err = ResolveError{
                    .node = reference,
                    .message = "Failed to get TypeGraph from reference node",
                    .kind = .typegraph_not_found,
                } };
            };

            // TODO: Implement typesafe alternative, escape character just proof of concept
            if (std.mem.startsWith(u8, child_identifier, "<<")) {
                // Parse N after "<<"
                const up_str = child_identifier[2..];
                const type_node = tg.get_type_by_name(up_str);
                if (type_node) |_type_node| {
                    target = _type_node;
                } else {
                    return ChildResolveResult{ .err = ResolveError{
                        .node = reference,
                        .message = "Type node not found for enum type",
                        .kind = .type_not_found,
                        .identifier = up_str,
                    } };
                }
            } else {
                // Dispatch based on edge type to traverse different edge kinds
                if (edge_type == EdgeComposition.tid) {
                    // Traverse composition (parent-child) edges
                    // Use `target` (not `instance`) so chained paths work correctly
                    const child = EdgeComposition.get_child_by_identifier(target, child_identifier);
                    if (child) |_child| {
                        target = _child;
                    } else if (child_identifier.len > 0) {
                        // Only fail if identifier is non-empty - empty identifier means "self"
                        return ChildResolveResult{ .err = ResolveError{
                            .node = reference,
                            .message = "Child not found",
                            .kind = .composition_child_not_found,
                            .identifier = child_identifier,
                        } };
                    }
                    // Empty identifier with composition = self-reference, keep target unchanged
                } else if (edge_type == EdgeTrait.tid) {
                    // Traverse trait edges by looking up the trait type, then finding an instance.
                    const trait_type = tg.get_type_by_name(child_identifier) orelse {
                        return ChildResolveResult{ .err = ResolveError{
                            .node = reference,
                            .message = "trait type not found in TypeGraph",
                            .kind = .trait_type_not_found,
                            .identifier = child_identifier,
                        } };
                    };
                    const trait_instance = EdgeTrait.try_get_trait_instance_of_type(target, trait_type.node) orelse {
                        return ChildResolveResult{ .err = ResolveError{
                            .node = reference,
                            .message = "trait not found on",
                            .kind = .trait_instance_not_found,
                            .identifier = child_identifier,
                        } };
                    };
                    target = trait_instance;
                } else if (edge_type == EdgePointer.tid) {
                    // Pointer traversal: dereference the current node.
                    // The current node should be a Pointer node - follow its EdgePointer edge.
                    // No identifier needed - we just dereference whatever the current node points to.
                    const dereferenced = EdgePointer.get_referenced_node_from_node(target) orelse {
                        return ChildResolveResult{ .err = ResolveError{
                            .node = reference,
                            .message = "pointer dereference failed from node",
                            .kind = .pointer_dereference_failed,
                            .identifier = child_identifier,
                        } };
                    };
                    target = dereferenced;
                } else if (edge_type == EdgeOperand.tid) {
                    // Operand traversal: find operand by identifier (e.g., "lhs", "rhs")
                    const operand = EdgeOperand.get_operand_by_identifier(target, child_identifier) orelse {
                        return ChildResolveResult{ .err = ResolveError{
                            .node = reference,
                            .message = "operand not found on node",
                            .kind = .operand_not_found,
                            .identifier = child_identifier,
                        } };
                    };
                    target = operand;
                } else {
                    return ChildResolveResult{ .err = ResolveError{
                        .node = reference,
                        .message = "Unknown edge type",
                        .kind = .unknown_edge_type,
                        .identifier = child_identifier,
                    } };
                }
            }

            const next_reference = EdgeNext.get_next_node_from_node(reference);
            if (next_reference) |_next_reference| {
                const next_ref = reference.g.bind(_next_reference);
                const next_result = ChildReferenceNode.resolve(next_ref, target);
                switch (next_result) {
                    .ok => |resolved| target = resolved,
                    .err => return next_result, // Propagate error from recursive call
                }
            }
            return ChildResolveResult{ .ok = target };
        }
    };

    pub const MakeLinkNode = struct {
        pub const Attributes = struct {
            node: BoundNodeReference,

            pub fn of(node: BoundNodeReference) @This() {
                return .{ .node = node };
            }

            pub fn store_edge_attributes(self: @This(), attributes: EdgeCreationAttributes) void {
                self.node.node.put("edge_type", .{ .Int = attributes.edge_type });
                if (attributes.directional) |d| {
                    self.node.node.put("directional", .{ .Bool = d });
                }
                if (attributes.name) |n| {
                    self.node.node.put("name", .{ .String = n });
                }
                self.node.node.put("order", .{ .Int = attributes.order });
                if (attributes.edge_specific) |edge_specific| {
                    self.node.node.put("edge_specific", .{ .Uint = edge_specific });
                }
                // TODO different API
                self.node.node.copy_dynamic_attributes_into(&attributes.dynamic);
            }

            pub fn get_order(self: @This()) u7 {
                return @intCast(self.node.node.get("order").?.Int);
            }

            pub fn get_edge_type(self: @This()) Edge.EdgeType {
                return @intCast(self.node.node.get("edge_type").?.Int);
            }

            pub fn load_edge_attributes(self: @This(), source: NodeReference, target: NodeReference) EdgeReference {
                const directional = self.node.node.get("directional");
                const name = self.node.node.get("name");
                const edge_type: Edge.EdgeType = @intCast(self.node.node.get("edge_type").?.Int);
                const order: u7 = @intCast(self.node.node.get("order").?.Int);
                const edge_specific = if (self.node.node.get("edge_specific")) |e| e.Uint else null;
                var dynamic = graph.DynamicAttributes.init_on_stack();

                const AttrVisitor = struct {
                    dynamic: *graph.DynamicAttributes,

                    pub fn visit(ctx: *anyopaque, key: str, value: graph.Literal, _dynamic: bool) void {
                        const s: *@This() = @ptrCast(@alignCast(ctx));
                        if (!_dynamic) return;
                        s.dynamic.put(key, value);
                    }
                };
                var visit = AttrVisitor{ .dynamic = &dynamic };
                self.node.node.visit_attributes(&visit, AttrVisitor.visit);

                // Use the appropriate edge creation function based on link_type
                const link_edge = EdgeReference.init(source, target, edge_type);
                if (directional) |d| {
                    link_edge.set_attribute_directional(d.Bool);
                }
                link_edge.set_attribute_name(if (name) |n| n.String else null);
                link_edge.set_order(order);
                if (edge_specific) |es| {
                    link_edge.set_edge_specific(@intCast(es));
                }
                // TODO different API
                link_edge.copy_dynamic_attributes_into(&dynamic);

                return link_edge;
            }
        };
    };

    const initialized_identifier = "initialized";

    fn get_initialized(self: *const @This()) bool {
        const is_set = self.self_node.node.get(initialized_identifier);
        if (is_set) |_is_set| {
            return _is_set.Bool;
        }
        return false;
    }

    fn set_initialized(self: *@This(), initialized: bool) void {
        if (self.get_initialized() and !initialized) {
            @panic("TypeGraph is already initialized");
        }
        if (initialized) {
            self.self_node.node.put(initialized_identifier, .{ .Bool = initialized });
        }
    }

    // TODO make cache for all these
    fn get_Reference(self: *const @This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "Reference").?;
    }

    fn get_TypeReference(self: *const @This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "TypeReference").?;
    }

    pub fn get_MakeChild(self: *const @This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "MakeChild").?;
    }

    fn get_MakeLink(self: *const @This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "MakeLink").?;
    }

    pub fn get_ImplementsType(self: *const @This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "ImplementsType").?;
    }

    pub fn get_ImplementsTrait(self: *const @This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "ImplementsTrait").?;
    }

    pub fn get_g(self: *const @This()) *GraphView {
        return self.self_node.g;
    }

    pub fn get_self_node(self: *const @This()) BoundNodeReference {
        return self.self_node;
    }

    pub fn of(self_node: BoundNodeReference) @This() {
        return .{ .self_node = self_node };
    }

    pub fn of_type(type_node: BoundNodeReference) ?@This() {
        const g = type_node.g;
        const typegraph_edge = EdgeComposition.get_parent_edge(type_node);
        if (typegraph_edge == null) {
            return null;
        }
        const typegraph_node = g.bind(EdgeComposition.get_parent_node(typegraph_edge.?.edge));
        return TypeGraph.of(typegraph_node);
    }

    pub fn of_instance(instance: BoundNodeReference) ?@This() {
        const g = instance.g;

        const type_edge = EdgeType.get_type_edge(instance);
        if (type_edge == null) {
            return null;
        }
        const type_node = g.bind(EdgeType.get_type_node(type_edge.?.edge));

        return TypeGraph.of_type(type_node);
    }

    pub fn of_type_or_instance(node: BoundNodeReference) ?@This() {
        if (TypeGraph.of_instance(node)) |tg| {
            return tg;
        }
        // TODO: check it's actually a type node
        return TypeGraph.of_type(node);
    }

    pub fn init(g: *GraphView) TypeGraph {
        const self_node = g.create_and_insert_node();
        var self = TypeGraph.of(self_node);
        self.set_initialized(false);

        // Bootstrap first type and trait type-nodes and instance-nodes
        const implements_type_type = TypeNode.create_and_insert(&self, "ImplementsType");
        const implements_trait_type = TypeNode.create_and_insert(&self, "ImplementsTrait");

        // Assign the traits to the type-nodes
        _ = TraitNode.add_trait_as_child_to(implements_type_type, implements_type_type);
        _ = TraitNode.add_trait_as_child_to(implements_type_type, implements_trait_type);
        _ = TraitNode.add_trait_as_child_to(implements_trait_type, implements_type_type);
        _ = TraitNode.add_trait_as_child_to(implements_trait_type, implements_trait_type);

        const make_child_type = TypeNode.create_and_insert(&self, "MakeChild");

        _ = TraitNode.add_trait_as_child_to(make_child_type, implements_type_type);

        _ = TypeNode.create_and_insert(&self, "MakeLink");
        _ = TypeNode.create_and_insert(&self, "Reference");
        _ = TypeNode.create_and_insert(&self, "TypeReference");

        // Mark as fully initialized
        self.set_initialized(true);

        return self;
    }

    pub fn add_type(self: *@This(), identifier: str) !BoundNodeReference {
        if (self.get_type_by_name(identifier) != null) {
            return error.TypeAlreadyExists;
        }
        const type_node = TypeNode.create_and_insert(self, identifier);

        // Add type trait
        const trait_implements_type_instance = switch (self.instantiate_node(self.get_ImplementsType())) {
            .ok => |n| n,
            .err => return error.InstantiationFailed,
        };
        _ = EdgeTrait.add_trait_instance(type_node, trait_implements_type_instance.node);
        _ = EdgeComposition.add_child(type_node, trait_implements_type_instance.node, null);

        return type_node;
    }

    // TODO this should live in zig fabll
    //pub fn add_trait_type(self: *@This(), identifier: str) !BoundNodeReference {
    //    const trait_type = try self.add_type(identifier);

    //    // Add trait trait
    //    const implements_trait_instance_node = try self.instantiate_node(self.get_ImplementsTrait());
    //    _ = EdgeType.add_instance(trait_type, implements_trait_instance_node);

    //    return trait_type;
    //}

    /// Create a MakeChild node with the child type linked immediately.
    /// soft_create: if true, this MakeChild can be discarded if a non-soft-created one exists for the same identifier
    pub fn add_make_child(
        self: *@This(),
        target_type: BoundNodeReference,
        child_type: BoundNodeReference,
        identifier: ?str,
        node_attributes: ?*NodeCreationAttributes,
        soft_create: bool,
    ) !BoundNodeReference {
        const child_type_identifier = TypeNodeAttributes.of(child_type.node).get_type_name();
        const make_child = try self.add_make_child_deferred(
            target_type,
            child_type_identifier,
            identifier,
            node_attributes,
            soft_create,
        );
        const type_reference = MakeChildNode.get_type_reference(make_child);
        try linker_mod.Linker.link_type_reference(self.self_node.g, type_reference, child_type);
        return make_child;
    }

    /// Create a MakeChild node without linking the type reference.
    /// Use this when the child type node is not yet available (e.g., external imports).
    /// Caller must call Linker.link_type_reference() later.
    /// soft_create: if true, this MakeChild can be discarded if a non-soft-created one exists for the same identifier
    pub fn add_make_child_deferred(
        self: *@This(),
        target_type: BoundNodeReference,
        child_type_identifier: str,
        identifier: ?str,
        node_attributes: ?*NodeCreationAttributes,
        soft_create: bool,
    ) !BoundNodeReference {
        const make_child = switch (self.instantiate_node(self.get_MakeChild())) {
            .ok => |n| n,
            .err => return error.InstantiationFailed,
        };
        MakeChildNode.Attributes.of(make_child).init(identifier, soft_create);
        if (node_attributes) |_node_attributes| {
            MakeChildNode.Attributes.of(make_child).store_node_attributes(_node_attributes.*);
        }

        const type_reference = try TypeReferenceNode.create_and_insert(self, child_type_identifier);
        MakeChildNode.set_type_reference(make_child, type_reference);
        _ = EdgePointer.point_to(make_child, type_reference.node, identifier, null);
        _ = EdgeComposition.add_child(target_type, make_child.node, identifier);

        return make_child;
    }

    pub fn add_make_link(
        self: *@This(),
        target_type: BoundNodeReference,
        lhs_reference: BoundNodeReference,
        rhs_reference: BoundNodeReference,
        edge_attributes: EdgeCreationAttributes,
    ) !BoundNodeReference {
        const attrs = edge_attributes;

        const make_link = switch (self.instantiate_node(self.get_MakeLink())) {
            .ok => |n| n,
            .err => return error.InstantiationFailed,
        };
        MakeLinkNode.Attributes.of(make_link).store_edge_attributes(attrs);

        _ = EdgeComposition.add_child(make_link, lhs_reference.node, "lhs");
        _ = EdgeComposition.add_child(make_link, rhs_reference.node, "rhs");
        _ = EdgeComposition.add_child(target_type, make_link.node, null);

        return make_link;
    }

    pub const CopyTypeError = error{ChildAlreadyExists};

    /// Copy MakeChild and MakeLink nodes from source_type into target_type.
    /// Handles soft-created MakeChild semantics:
    /// - If target has a soft-created MakeChild and source has the same identifier, source wins
    /// - If target has a non-soft-created MakeChild and source has the same identifier, returns error
    /// Used for inheritance: flattens parent structure into derived type.
    pub fn copy_type_structure(
        self: *@This(),
        target_type: BoundNodeReference,
        source_type: BoundNodeReference,
        skip_identifiers: []const []const u8,
    ) CopyTypeError!void {
        const allocator = self.self_node.g.allocator;

        // Collect existing non-soft-created children on target (for conflict detection)
        var non_soft_existing = std.StringHashMap(void).init(allocator);
        defer non_soft_existing.deinit();

        const target_children = self.collect_make_children(allocator, target_type);
        defer allocator.free(target_children);
        for (target_children) |info| {
            if (info.identifier) |id| {
                if (!MakeChildNode.Attributes.of(info.make_child).soft_create()) {
                    non_soft_existing.put(id, {}) catch @panic("OOM");
                }
            }
        }

        // Copy MakeChild nodes from source
        const source_children = self.collect_make_children(allocator, source_type);
        defer allocator.free(source_children);

        for (source_children) |info| {
            if (info.identifier) |id| {
                // Check if should skip (explicit skip list)
                var should_skip = false;
                for (skip_identifiers) |skip_id| {
                    if (std.mem.eql(u8, id, skip_id)) {
                        should_skip = true;
                        break;
                    }
                }
                if (should_skip) continue;

                // Conflict: two non-soft-created declarations with same identifier
                if (non_soft_existing.contains(id)) {
                    return error.ChildAlreadyExists;
                }

                // Soft-created children with the same id will be filtered out by
                // visit_make_children when the inherited non-soft-created child is added
            }
            const child_type = MakeChildNode.get_child_type(info.make_child) orelse continue;
            // Extract attributes from source MakeChild (e.g., literal values)
            var attrs = MakeChildNode.Attributes.of(info.make_child).extract_node_attributes();
            // Inherited children are not soft-created (they become authoritative)
            _ = self.add_make_child(target_type, child_type, info.identifier, &attrs, false) catch continue;
        }

        // Copy MakeLink nodes from source
        const source_links = self.collect_make_links(allocator, source_type) catch return;
        defer {
            for (source_links) |link_info| {
                allocator.free(link_info.lhs_path);
                allocator.free(link_info.rhs_path);
            }
            allocator.free(source_links);
        }

        for (source_links) |link_info| {
            const self_ref_path = [_]ChildReferenceNode.EdgeTraversal{EdgeComposition.traverse("")};
            const lhs_path = if (link_info.lhs_path.len == 0) &self_ref_path else link_info.lhs_path;
            const rhs_path = if (link_info.rhs_path.len == 0) &self_ref_path else link_info.rhs_path;

            const lhs_ref = ChildReferenceNode.create_and_insert(self, lhs_path) catch continue;
            const rhs_ref = ChildReferenceNode.create_and_insert(self, rhs_path) catch continue;

            const attrs = MakeLinkNode.Attributes.of(link_info.make_link);
            const edge_attrs = EdgeCreationAttributes{
                .edge_type = attrs.get_edge_type(),
                .directional = if (link_info.make_link.node.get("directional")) |d| d.Bool else null,
                .name = if (link_info.make_link.node.get("name")) |n| n.String else null,
                .order = attrs.get_order(),
                .edge_specific = if (link_info.make_link.node.get("edge_specific")) |e| @as(u16, @intCast(e.Uint)) else null,
                .dynamic = graph.DynamicAttributes.init_on_stack(),
            };

            _ = self.add_make_link(target_type, lhs_ref, rhs_ref, edge_attrs) catch continue;
        }
    }

    fn find_make_child_node(
        self: *@This(),
        type_node: BoundNodeReference,
        identifier: []const u8,
    ) error{ChildNotFound}!BoundNodeReference {
        _ = self;
        return EdgeComposition.get_child_by_identifier(type_node, identifier) orelse error.ChildNotFound;
    }

    pub fn get_make_child_type_reference_by_identifier(
        self: *@This(),
        type_node: BoundNodeReference,
        identifier: str,
    ) ?BoundNodeReference {
        const make_child = self.find_make_child_node(type_node, identifier) catch return null;
        return MakeChildNode.get_type_reference(make_child);
    }

    /// Walk a path of child identifiers through the type graph, resolving each
    /// type reference via the Linker. Returns the resolved type node for the
    /// final segment, or null if any step fails to resolve.
    ///
    /// For path ["inner"] starting at App:
    ///   1. Find "inner" child on App, get its type reference
    ///   2. Resolve type reference to Inner type node via Linker
    ///   3. Return Inner type node
    ///
    /// Returns null if path is empty, any child not found, or any type fails to resolve.
    pub fn resolve_child_path(
        self: *@This(),
        start_type: BoundNodeReference,
        path: []const []const u8,
    ) ?BoundNodeReference {
        if (path.len == 0) return start_type;

        var current_type = start_type;

        for (path) |segment| {
            const type_ref = self.get_make_child_type_reference_by_identifier(current_type, segment) orelse return null;
            const resolved = Linker.try_get_resolved_type(type_ref) orelse return null;
            current_type = resolved;
        }

        return current_type;
    }

    /// Validate all reference paths in a type node and its children.
    /// Returns a list of validation errors (empty if valid).
    /// Validates:
    /// - MakeLink endpoints (lhs and rhs paths)
    /// - Duplicate non-soft-created MakeChild declarations (same identifier)
    pub fn validate_type(
        self: *@This(),
        allocator: std.mem.Allocator,
        type_node: BoundNodeReference,
    ) []ValidationError {
        var errors = std.ArrayList(ValidationError).init(allocator);

        // Soft-created resolution is handled dynamically by visit_make_children,
        // so collect_make_children already returns only the "winning" nodes.
        const make_children = self.collect_make_children(allocator, type_node);
        defer allocator.free(make_children);

        // Duplicate non-soft-created MakeChild detection
        var i: usize = 0;
        while (i < make_children.len) : (i += 1) {
            const child_info = make_children[i];
            const id = child_info.identifier orelse continue;

            // Skip if this child is soft-created
            if (MakeChildNode.Attributes.of(child_info.make_child).soft_create()) continue;

            // Look for duplicates in the rest of the list
            var j: usize = i + 1;
            while (j < make_children.len) : (j += 1) {
                const other_info = make_children[j];
                const other_id = other_info.identifier orelse continue;

                // Skip if the other is soft
                if (MakeChildNode.Attributes.of(other_info.make_child).soft_create()) continue;

                // Check if identifiers match
                if (std.mem.eql(u8, id, other_id)) {
                    const message = std.fmt.allocPrint(allocator, "Field `{s}` is already defined", .{id}) catch continue;
                    errors.append(.{
                        .node = other_info.make_child,
                        .message = message,
                    }) catch {
                        allocator.free(message);
                    };
                }
            }
        }

        // Validate MakeLink endpoints
        const make_links = self.collect_make_links(allocator, type_node) catch {
            // If we can't collect make_links, there's likely an internal error
            // This shouldn't happen in normal operation
            return errors.toOwnedSlice() catch &[_]ValidationError{};
        };
        defer {
            for (make_links) |info| {
                allocator.free(info.lhs_path);
                allocator.free(info.rhs_path);
            }
            allocator.free(make_links);
        }

        for (make_links) |link_info| {
            // Validate lhs path (skip paths that can't be type-level validated)
            if (link_info.lhs_path.len > 0 and self.isValidatablePath(link_info.lhs_path)) {
                const lhs_result = self.resolve_path_segments(type_node, link_info.lhs_path, null);
                if (lhs_result) |_| {} else |_| {
                    if (self.format_path(allocator, link_info.lhs_path)) |path_str| {
                        const message = std.fmt.allocPrint(allocator, "Field `{s}` could not be resolved", .{path_str}) catch continue;
                        errors.append(.{
                            .node = link_info.make_link,
                            .message = message,
                        }) catch {
                            allocator.free(message);
                        };
                    }
                }
            }

            // Validate rhs path (skip paths that can't be type-level validated)
            if (link_info.rhs_path.len > 0 and self.isValidatablePath(link_info.rhs_path)) {
                const rhs_result = self.resolve_path_segments(type_node, link_info.rhs_path, null);
                if (rhs_result) |_| {} else |_| {
                    if (self.format_path(allocator, link_info.rhs_path)) |path_str| {
                        const message = std.fmt.allocPrint(allocator, "Field `{s}` could not be resolved", .{path_str}) catch continue;
                        errors.append(.{
                            .node = link_info.make_link,
                            .message = message,
                        }) catch {
                            allocator.free(path_str);
                        };
                    }
                }
            }
        }

        return errors.toOwnedSlice() catch &[_]ValidationError{};
    }

    fn isValidatablePath(self: *@This(), path: []const ChildReferenceNode.EdgeTraversal) bool {
        _ = self;
        if (path.len == 0) return false;

        // Check all segments for validation exclusions
        for (path, 0..) |traversal, idx| {
            const segment = traversal.identifier;

            // Skip paths with special prefixes (trait syntax like <<)
            if (segment.len >= 2 and segment[0] == '<' and segment[1] == '<') {
                return false;
            }

            // Skip paths where first segment is numeric (shouldn't happen normally)
            if (idx == 0 and segment.len > 0 and ascii.isDigit(segment[0])) {
                return false;
            }
        }

        return true;
    }

    fn format_path(self: *@This(), allocator: std.mem.Allocator, path: []const ChildReferenceNode.EdgeTraversal) ?[]const u8 {
        _ = self;
        if (path.len == 0) {
            return allocator.dupe(u8, "") catch return null;
        }

        var total_len: usize = 0;
        for (path, 0..) |traversal, i| {
            total_len += traversal.identifier.len;
            if (i < path.len - 1) total_len += 1; // for '.'
        }

        const result = allocator.alloc(u8, total_len) catch return null;
        var pos: usize = 0;
        for (path, 0..) |traversal, i| {
            const segment = traversal.identifier;
            @memcpy(result[pos .. pos + segment.len], segment);
            pos += segment.len;
            if (i < path.len - 1) {
                result[pos] = '.';
                pos += 1;
            }
        }
        return result;
    }

    /// Format a path with bracket notation for numeric indices (e.g., "members.5" -> "members[5]")
    fn formatPathWithBrackets(self: *@This(), allocator: std.mem.Allocator, path: []const []const u8) ?[]const u8 {
        _ = self;
        if (path.len == 0) {
            return allocator.dupe(u8, "") catch return null;
        }

        // Build the formatted path
        var buf = std.ArrayList(u8).init(allocator);
        for (path, 0..) |segment, i| {
            // Check if segment is purely numeric (array index)
            const is_numeric = blk: {
                if (segment.len == 0) break :blk false;
                for (segment) |c| {
                    if (c < '0' or c > '9') break :blk false;
                }
                break :blk true;
            };

            if (is_numeric and i > 0) {
                // Format as array index: [N]
                buf.append('[') catch return null;
                buf.appendSlice(segment) catch return null;
                buf.append(']') catch return null;
            } else {
                // Regular field access
                if (i > 0) buf.append('.') catch return null;
                buf.appendSlice(segment) catch return null;
            }
        }

        return buf.toOwnedSlice() catch return null;
    }

    fn reference_matches_path(
        self: *@This(),
        reference: BoundNodeReference,
        expected_path: []const []const u8,
    ) bool {
        _ = self;
        if (expected_path.len == 0) {
            return false;
        }

        var current = reference;
        var index: usize = 0;

        while (true) {
            if (index >= expected_path.len) {
                return false;
            }

            const identifier = ChildReferenceNode.Attributes.of(current.node).get_child_identifier();
            if (!std.mem.eql(u8, identifier, expected_path[index])) {
                return false;
            }

            index += 1;

            const next_node = EdgeNext.get_next_node_from_node(current);
            if (next_node) |_next_node| {
                current = reference.g.bind(_next_node);
            } else {
                break;
            }
        }

        return index == expected_path.len;
    }

    /// MakeChild nodes can be mounted under an arbitrary path. Pointer-sequence
    /// elements mount under their container (e.g. `items`), and are identified
    /// by index strings. This helper finds the matching make-child by verifying
    /// the mount path as well as the identifier.
    fn find_make_child_node_with_mount(
        self: *@This(),
        root_type: BoundNodeReference,
        identifier: []const u8,
        parent_path: []const []const u8,
    ) error{ChildNotFound}!BoundNodeReference {
        const FindCtx = struct {
            identifier: []const u8,
            parent_path: []const []const u8,
            type_graph: *TypeGraph,

            pub fn visit(
                self_ptr: *anyopaque,
                edge: graph.BoundEdgeReference,
            ) visitor.VisitResult(BoundNodeReference) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));
                const make_child = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                const child_identifier = MakeChildNode.Attributes.of(make_child).get_child_identifier() orelse {
                    return visitor.VisitResult(BoundNodeReference){ .CONTINUE = {} };
                };

                if (!std.mem.eql(u8, child_identifier, ctx.identifier)) {
                    return visitor.VisitResult(BoundNodeReference){ .CONTINUE = {} };
                }

                if (ctx.parent_path.len == 0) {
                    return visitor.VisitResult(BoundNodeReference){ .OK = make_child };
                }

                return visitor.VisitResult(BoundNodeReference){ .CONTINUE = {} };
            }
        };

        var ctx = FindCtx{
            .identifier = identifier,
            .parent_path = parent_path,
            .type_graph = self,
        };

        const visit_result = EdgeComposition.visit_children_of_type(
            root_type,
            self.get_MakeChild().node,
            BoundNodeReference,
            &ctx,
            FindCtx.visit,
        );

        switch (visit_result) {
            .OK => |make_child| return make_child,
            .ERROR => |err| switch (err) {
                error.OutOfMemory => @panic("OOM"),
                else => unreachable,
            },
            else => return error.ChildNotFound,
        }
    }

    const ResolveResult = struct {
        last_make_child: BoundNodeReference,
        last_child_type: BoundNodeReference,
    };

    /// Resolve `path` against `type_node`, following mounts for pointer-sequence
    /// indices. Returns the final make-child and its child type. Centralising
    /// this logic avoids duplicating mount semantics in higher layers.
    /// Accepts EdgeTraversals to support different edge types:
    /// - Composition: Looks up MakeChild nodes (validates child exists)
    /// - Trait: Validates trait type exists on current type (returns trait type)
    /// - Pointer: Skips type-level validation (pointers are instance-level)
    fn resolve_path_segments(
        self: *@This(),
        type_node: BoundNodeReference,
        path: []const ChildReferenceNode.EdgeTraversal,
        failure: ?*?PathResolutionFailure,
    ) error{ ChildNotFound, UnresolvedTypeReference }!ResolveResult {
        // TODO get base allocator passed
        const allocator = std.heap.c_allocator;

        if (failure) |f| f.* = null;
        if (path.len == 0) {
            if (failure) |f| {
                f.* = PathResolutionFailure{
                    .kind = PathErrorKind.missing_child,
                    .failing_segment_index = 0,
                    .failing_segment = &.{},
                };
            }
            return error.ChildNotFound;
        }

        var current_type = type_node;
        var make_child: BoundNodeReference = undefined;

        for (path, 0..) |segment, idx| {
            const edge_type = segment.edge_type;
            const identifier = segment.identifier;

            if (edge_type == EdgeComposition.tid) {
                // Composition edge: look up MakeChild node
                make_child = self.find_make_child_node(current_type, identifier) catch |err| switch (err) {
                    error.ChildNotFound => blk: {
                        // Extract parent path identifiers for mount lookup
                        var parent_identifiers = std.ArrayList([]const u8).init(allocator);
                        defer parent_identifiers.deinit();
                        for (path[0..idx]) |p| {
                            parent_identifiers.append(p.identifier) catch return error.ChildNotFound;
                        }
                        break :blk self.find_make_child_node_with_mount(
                            type_node,
                            identifier,
                            parent_identifiers.items,
                        ) catch |fallback_err| switch (fallback_err) {
                            error.ChildNotFound => {
                                if (failure) |f| {
                                    const is_index = identifier.len > 0 and ascii.isDigit(identifier[0]);
                                    f.* = PathResolutionFailure{
                                        .kind = if (is_index and idx > 0)
                                            PathErrorKind.invalid_index
                                        else
                                            PathErrorKind.missing_child,
                                        .failing_segment_index = idx,
                                        .failing_segment = identifier,
                                        .has_index_value = false,
                                    };
                                }
                                return error.ChildNotFound;
                            },
                            else => return fallback_err,
                        };
                    },
                    else => return err,
                };

                const child_type = MakeChildNode.get_child_type(make_child) orelse null;
                // FIXME: restore this check?
                // if (failure) |f| {
                //     f.* = PathResolutionFailure{
                //         .kind = PathErrorKind.missing_child,
                //         .failing_segment_index = idx,
                //         .failing_segment = identifier,
                //         .has_index_value = false,
                //     };
                // }
                // return error.UnresolvedTypeReference;
                // make oresle null and update if not null
                if (child_type) |_child_type| {
                    current_type = _child_type;
                }
                // current_type = child_type;
            } else if (edge_type == EdgeTrait.tid) {
                // Trait edge: look up trait type by identifier
                // For type-level validation, we check if a trait with this name exists
                const trait_type = self.get_type_by_name(identifier);
                if (trait_type == null) {
                    if (failure) |f| {
                        f.* = PathResolutionFailure{
                            .kind = PathErrorKind.missing_child,
                            .failing_segment_index = idx,
                            .failing_segment = identifier,
                            .has_index_value = false,
                        };
                    }
                    return error.ChildNotFound;
                }
                // Continue with the trait type as current type
                current_type = trait_type.?;
                make_child = current_type; // For trait edges, use the type as the "make_child"
            } else if (edge_type == EdgePointer.tid) {
                // Pointer edge: skip type-level validation
                // Pointers are resolved at instance level, not type level
                // Keep current_type unchanged and continue
                continue;
            } else {
                // Unknown edge type - skip validation
                continue;
            }
        }

        return ResolveResult{ .last_make_child = make_child, .last_child_type = current_type };
    }

    /// Resolve `path` and return the child type node. Pointer-sequence indices
    /// are matched via mount references so callers do not need to duplicate the
    /// pointer semantics on the Python side.
    pub fn resolve_child_type(
        self: *@This(),
        type_node: BoundNodeReference,
        path: []const ChildReferenceNode.EdgeTraversal,
    ) !BoundNodeReference {
        const result = try self.resolve_path_segments(type_node, path, null);
        return result.last_child_type;
    }

    /// Create a child reference for `path` using EdgeTraversals.
    /// This is the main entry point for creating reference paths that can
    /// traverse different edge types (Composition, Trait, Pointer).
    pub fn ensure_child_reference(
        self: *@This(),
        type_node: BoundNodeReference,
        path: []const ChildReferenceNode.EdgeTraversal,
        validate: bool,
    ) !BoundNodeReference {
        return self.ensure_path_reference_mountaware(type_node, path, validate, null);
    }

    /// Create a child reference with optional validation and failure reporting.
    pub fn ensure_path_reference_mountaware(
        self: *@This(),
        path: []const ChildReferenceNode.EdgeTraversal,
        failure: ?*?PathResolutionFailure,
    ) !BoundNodeReference {
        if (path.len == 0) {
            if (failure) |f| {
                f.* = PathResolutionFailure{
                    .kind = PathErrorKind.missing_child,
                    .failing_segment_index = 0,
                    .failing_segment = &.{},
                    .has_index_value = false,
                };
            }
            return error.ChildNotFound;
        }

        return ChildReferenceNode.create_and_insert(self, path);
    }

    /// Visit MakeChild nodes with soft-created filtering.
    /// Soft-created nodes are skipped if a non-soft-created node with the same identifier exists.
    /// If multiple soft-created nodes exist for the same identifier, only the first is visited.
    pub fn visit_make_children(
        self: *@This(),
        type_node: BoundNodeReference,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, MakeChildInfo) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const allocator = self.self_node.g.allocator;

        // First, collect all MakeChild nodes
        var all_children = std.ArrayList(MakeChildInfo).init(allocator);
        defer all_children.deinit();

        const RawCollector = struct {
            list_ptr: *std.ArrayList(MakeChildInfo),

            pub fn collect(ctx_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const collector: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const make_child = edge.g.bind(EdgeComposition.get_child_node(edge.edge));
                const identifier = MakeChildNode.Attributes.of(make_child).get_child_identifier();
                collector.list_ptr.append(.{
                    .identifier = identifier,
                    .make_child = make_child,
                }) catch return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };
        var raw_collector = RawCollector{ .list_ptr = &all_children };
        const collect_result = EdgeComposition.visit_children_of_type(
            type_node,
            self.get_MakeChild().node,
            void,
            &raw_collector,
            RawCollector.collect,
        );
        switch (collect_result) {
            .ERROR => |err| return visitor.VisitResult(T){ .ERROR = err },
            else => {},
        }

        // Build set of non-soft-created identifiers
        var non_soft_ids = std.StringHashMap(void).init(allocator);
        defer non_soft_ids.deinit();
        for (all_children.items) |info| {
            if (info.identifier) |id| {
                if (!MakeChildNode.Attributes.of(info.make_child).soft_create()) {
                    non_soft_ids.put(id, {}) catch continue;
                }
            }
        }

        // Track first soft-created for each identifier (to skip duplicates)
        var first_soft_ids = std.StringHashMap(void).init(allocator);
        defer first_soft_ids.deinit();

        // Iterate with filtering
        for (all_children.items) |info| {
            if (info.identifier) |id| {
                if (MakeChildNode.Attributes.of(info.make_child).soft_create()) {
                    // Skip if a non-soft-created exists for this identifier
                    if (non_soft_ids.contains(id)) continue;
                    // Skip if we've already seen a soft-created for this identifier
                    if (first_soft_ids.contains(id)) continue;
                    first_soft_ids.put(id, {}) catch continue;
                }
            }
            // Visit this node
            switch (f(ctx, info)) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(T){ .STOP = {} },
                .OK => |result| return visitor.VisitResult(T){ .OK = result },
                .EXHAUSTED => return visitor.VisitResult(T){ .EXHAUSTED = {} },
                .ERROR => |err| return visitor.VisitResult(T){ .ERROR = err },
            }
        }

        return visitor.VisitResult(T){ .EXHAUSTED = {} };
    }

    /// Return every MakeChild belonging to `type_node` without filtering or
    /// reordering. Python tests consume this instead of manually walking
    /// EdgeComposition edges so Zig stays the single source of truth for which
    /// children exist.
    pub fn collect_make_children(
        self: *@This(),
        allocator: std.mem.Allocator,
        type_node: BoundNodeReference,
    ) []MakeChildInfo {
        var list = std.ArrayList(MakeChildInfo).init(allocator);

        const Collector = struct {
            list_ptr: *std.ArrayList(MakeChildInfo),

            pub fn collect(ctx_ptr: *anyopaque, info: MakeChildInfo) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                ctx.list_ptr.append(info) catch @panic("OOM");
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var collector = Collector{ .list_ptr = &list };
        const result = self.visit_make_children(type_node, void, &collector, Collector.collect);

        switch (result) {
            .ERROR => |err| switch (err) {
                error.OutOfMemory => @panic("OOM"),
                else => unreachable,
            },
            else => {},
        }

        return list.toOwnedSlice() catch @panic("OOM");
    }

    /// Walk a Reference chain and return the individual identifiers. Reference
    /// nodes are linked together via EdgeNext; higher layers should not need to
    /// reason about the internals of that representation.
    /// An empty identifier with Composition edge type and no successor is treated
    /// as a self-reference and returns an empty path.
    /// Pointer edges have empty identifiers but are valid path segments.
    /// Returns EdgeTraversal segments preserving both identifier and edge type.
    pub fn get_reference_path(
        self: *@This(),
        allocator: std.mem.Allocator,
        reference: BoundNodeReference,
    ) error{InvalidReference}![]const ChildReferenceNode.EdgeTraversal {
        _ = self;

        var segments = std.ArrayList(ChildReferenceNode.EdgeTraversal).init(allocator);
        errdefer segments.deinit();

        var current = reference;
        while (true) {
            const attrs = ChildReferenceNode.Attributes.of(current.node);
            const identifier = attrs.get_child_identifier();
            const edge_type = attrs.get_edge_type();
            const next_node = EdgeNext.get_next_node_from_node(current);

            if (identifier.len == 0) {
                // Empty identifier is valid for Pointer edges (dereference operation)
                if (edge_type == EdgePointer.tid) {
                    // Pointer dereference - append the segment with empty identifier
                    segments.append(.{ .identifier = identifier, .edge_type = edge_type }) catch @panic("OOM");
                } else if (next_node == null) {
                    // Self-reference (empty identifier, Composition edge, no successor) - return empty path
                    return segments.toOwnedSlice() catch @panic("OOM");
                } else {
                    // Empty identifier in middle of chain for non-Pointer edge is invalid
                    return error.InvalidReference;
                }
            } else {
                segments.append(.{ .identifier = identifier, .edge_type = edge_type }) catch @panic("OOM");
            }

            if (next_node) |_next| {
                current = reference.g.bind(_next);
            } else {
                break;
            }
        }

        return segments.toOwnedSlice() catch @panic("OOM");
    }

    pub fn visit_make_links(
        self: *@This(),
        type_node: BoundNodeReference,
        allocator: std.mem.Allocator,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, MakeLinkInfo) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            type_graph: *TypeGraph,
            allocator: std.mem.Allocator,
            ctx: *anyopaque,
            cb: *const fn (*anyopaque, MakeLinkInfo) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(T) {
                const visitor_: *@This() = @ptrCast(@alignCast(self_ptr));
                const make_link = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                const lhs_ref = EdgeComposition.get_child_by_identifier(make_link, "lhs");
                const rhs_ref = EdgeComposition.get_child_by_identifier(make_link, "rhs");
                if (lhs_ref == null or rhs_ref == null) {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }

                const lhs_path = visitor_.type_graph.get_reference_path(visitor_.allocator, lhs_ref.?) catch |err| {
                    return visitor.VisitResult(T){ .ERROR = err };
                };
                var lhs_keep = true;
                defer if (lhs_keep) visitor_.allocator.free(lhs_path);

                const rhs_path = visitor_.type_graph.get_reference_path(visitor_.allocator, rhs_ref.?) catch |err| {
                    return visitor.VisitResult(T){ .ERROR = err };
                };
                var rhs_keep = true;
                defer if (rhs_keep) visitor_.allocator.free(rhs_path);

                const result = visitor_.cb(visitor_.ctx, MakeLinkInfo{
                    .make_link = make_link,
                    .lhs_path = lhs_path,
                    .rhs_path = rhs_path,
                });

                switch (result) {
                    .CONTINUE => {
                        lhs_keep = false;
                        rhs_keep = false;
                    },
                    .OK => {
                        lhs_keep = false;
                        rhs_keep = false;
                    },
                    else => {},
                }

                return result;
            }
        };
        var visitor_ = Visit{
            .type_graph = self,
            .allocator = allocator,
            .ctx = ctx,
            .cb = f,
        };
        return EdgeComposition.visit_children_of_type(type_node, self.get_MakeLink().node, T, &visitor_, Visit.visit);
    }

    /// Enumerate MakeLink nodes together with their resolved reference paths so
    /// callers do not need to expand the `lhs`/`rhs` chains manually.
    pub fn collect_make_links(
        self: *@This(),
        allocator: std.mem.Allocator,
        type_node: BoundNodeReference,
    ) error{InvalidReference}![]MakeLinkInfo {
        var list = std.ArrayList(MakeLinkInfo).init(allocator);
        errdefer {
            for (list.items) |info| {
                allocator.free(info.lhs_path);
                allocator.free(info.rhs_path);
            }
            list.deinit();
        }

        const Collector = struct {
            list_ptr: *std.ArrayList(MakeLinkInfo),

            pub fn collect(ctx_ptr: *anyopaque, info: MakeLinkInfo) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                ctx.list_ptr.append(info) catch @panic("OOM");
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var collector = Collector{ .list_ptr = &list };
        const visit_result = self.visit_make_links(type_node, allocator, void, &collector, Collector.collect);

        switch (visit_result) {
            .ERROR => |err| switch (err) {
                error.InvalidReference => return error.InvalidReference,
                else => @panic("OOM"),
            },
            else => {},
        }

        return list.toOwnedSlice() catch @panic("OOM");
    }

    /// Visit pointer-sequence elements by scanning MakeLink nodes from the type.
    /// For each MakeLink where lhs_path matches container_path and edge type is
    /// EdgePointer, yields the element's MakeChildInfo with its order.
    pub fn visit_pointer_members(
        self: *@This(),
        type_node: BoundNodeReference,
        container_path: []const []const u8,
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, MakeChildInfo) visitor.VisitResult(T),
        failure: ?*?PathResolutionFailure,
    ) error{ UnresolvedTypeReference, ChildNotFound }!visitor.VisitResult(T) {
        // TODO get base allocator passed
        const allocator = std.heap.c_allocator;

        // Convert string path to EdgeTraversals (all Composition edges)
        var traversals = std.ArrayList(ChildReferenceNode.EdgeTraversal).init(allocator);
        defer traversals.deinit();
        for (container_path) |segment| {
            traversals.append(EdgeComposition.traverse(segment)) catch return error.ChildNotFound;
        }

        var local_failure: ?PathResolutionFailure = null;
        _ = self.resolve_path_segments(type_node, traversals.items, &local_failure) catch |err| switch (err) {
            error.ChildNotFound => {
                if (failure) |f_ptr| f_ptr.* = local_failure;
                return err;
            },
            error.UnresolvedTypeReference => {},
            else => return err,
        };

        const Visit = struct {
            type_graph: *TypeGraph,
            type_node_: BoundNodeReference,
            container_path_: []const []const u8,
            ctx: *anyopaque,
            cb: *const fn (*anyopaque, MakeChildInfo) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, info: MakeLinkInfo) visitor.VisitResult(T) {
                const visitor_: *@This() = @ptrCast(@alignCast(self_ptr));

                // Check if lhs_path identifiers match container_path
                if (info.lhs_path.len != visitor_.container_path_.len) {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }
                for (info.lhs_path, visitor_.container_path_) |lhs_traversal, container_seg| {
                    if (!std.mem.eql(u8, lhs_traversal.identifier, container_seg)) {
                        return visitor.VisitResult(T){ .CONTINUE = {} };
                    }
                }

                // Check if this is an EdgePointer link
                const attrs = MakeLinkNode.Attributes.of(info.make_link);
                const edge_type = attrs.get_edge_type();
                if (edge_type != EdgePointer.tid) {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }

                // Element identifier is in rhs_path (e.g., "items[0]" -> single element)
                if (info.rhs_path.len != 1) {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                }
                const element_id = info.rhs_path[0].identifier;

                const make_child = visitor_.type_graph.find_make_child_node(
                    visitor_.type_node_,
                    element_id,
                ) catch {
                    return visitor.VisitResult(T){ .CONTINUE = {} };
                };

                const edge_specific_val: ?u16 = if (info.make_link.node.get("edge_specific")) |e| @as(u16, @intCast(e.Uint)) else null;

                return visitor_.cb(visitor_.ctx, MakeChildInfo{
                    .identifier = element_id,
                    .make_child = make_child,
                    .order = attrs.get_order(),
                    .edge_specific = edge_specific_val,
                });
            }
        };

        var visitor_ = Visit{
            .type_graph = self,
            .type_node_ = type_node,
            .container_path_ = container_path,
            .ctx = ctx,
            .cb = f,
        };

        const result = self.visit_make_links(type_node, allocator, T, &visitor_, Visit.visit);
        switch (result) {
            .ERROR => |err| switch (err) {
                error.InvalidReference => return error.ChildNotFound,
                else => return error.ChildNotFound,
            },
            else => return result,
        }
    }

    /// Enumerate pointer-sequence elements mounted under `container_path`. This
    /// keeps mount-matching inside the TypeGraph so higher layers can treat
    /// pointer sequences like ordinary lists of children.
    pub fn collect_pointer_members(
        self: *@This(),
        allocator: std.mem.Allocator,
        type_node: BoundNodeReference,
        container_path: []const []const u8,
        failure: ?*?PathResolutionFailure,
    ) error{ UnresolvedTypeReference, ChildNotFound }![]MakeChildInfo {
        var list = std.ArrayList(MakeChildInfo).init(allocator);

        const Collector = struct {
            list_ptr: *std.ArrayList(MakeChildInfo),

            pub fn collect(ctx_ptr: *anyopaque, info: MakeChildInfo) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                ctx.list_ptr.append(info) catch @panic("OOM");
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var collector = Collector{ .list_ptr = &list };
        const visit_result = try self.visit_pointer_members(type_node, container_path, void, &collector, Collector.collect, failure);

        switch (visit_result) {
            .ERROR => |err| switch (err) {
                error.OutOfMemory => @panic("OOM"),
                else => unreachable,
            },
            else => {},
        }

        return list.toOwnedSlice() catch @panic("OOM");
    }

    pub const InstantiateResult = union(enum) {
        ok: graph.BoundNodeReference,
        err: InstantiationError,
    };

    pub fn instantiate_node(tg: *@This(), type_node: BoundNodeReference) InstantiateResult {
        // FIXME: restore
        // type_node may be linked from another TypeGraph
        // std.debug.print("OG TG {any}\n", .{tg.get_MakeChild().node});
        // var type_owner_tg_val = TypeGraph.of_type(type_node) orelse tg.*;
        // const type_owner_tg: *TypeGraph = &type_owner_tg_val;
        // std.debug.print("NEW TG {any}\n", .{type_owner_tg_val.get_MakeChild().node});

        // 1) Create instance and connect it to its type
        const new_instance = type_node.g.create_and_insert_node();
        _ = EdgeType.add_instance(type_node, new_instance);

        // 2) Visit MakeChild nodes of type_node
        const VisitMakeChildren = struct {
            type_graph: *TypeGraph,
            parent_instance: graph.BoundNodeReference,
            /// Captures the failing node for rich error reporting
            failing_node: ?BoundNodeReference = null,
            error_kind: InstantiationErrorKind = .other,
            error_message: []const u8 = "",
            /// The identifier that was being looked up when the error occurred
            error_identifier: []const u8 = "",

            pub fn visit(self_ptr: *anyopaque, info: MakeChildInfo) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));

                // 2.1) Resolve child instructions (identifier and type)
                const referenced_type = MakeChildNode.get_child_type(info.make_child) orelse {
                    self.failing_node = info.make_child;
                    self.error_kind = .unresolved_type_reference;
                    self.error_message = "Unresolved type reference (linking required)";
                    return visitor.VisitResult(void){ .ERROR = error.UnresolvedTypeReference };
                };

                // 2.2) Instantiate child (recursive)
                const child_result = self.type_graph.instantiate_node(referenced_type);
                switch (child_result) {
                    .ok => |child| {
                        // 2.3) Attach child instance to parent instance with the reference name
                        _ = EdgeComposition.add_child(self.parent_instance, child.node, info.identifier);

                        // 2.4) Copy node attributes from MakeChild node to child instance
                        MakeChildNode.Attributes.of(info.make_child).load_node_attributes(child.node);

                        // 2.5) If MakeChild has a has_source_chunk trait, copy it onto the child instance
                        if (self.type_graph.get_type_by_name("has_source_chunk")) |has_source_chunk_type| {
                            if (Trait.try_get_trait(info.make_child, has_source_chunk_type)) |source_trait| {
                                // Extract the source chunk node from the MakeChild trait pointer
                                if (EdgeComposition.get_child_by_identifier(source_trait, "source_ptr")) |source_ptr| {
                                    if (EdgePointer.get_pointed_node_by_identifier(source_ptr, "source")) |source_chunk| {
                                        // Instantiate the trait on the child instance
                                        switch (self.type_graph.instantiate_node(has_source_chunk_type)) {
                                            .ok => |trait_instance| {
                                                // Attach trait to the child instance
                                                const trait_edge = EdgeTrait.add_trait_instance(child, trait_instance.node);
                                                trait_edge.edge.set_attribute_name("has_source_chunk");

                                                // TODO: remove hardcoded source pointer and pointer edge identifiers
                                                // Find the source_ptr child of the trait and point it to the source chunk
                                                if (EdgeComposition.get_child_by_identifier(trait_instance, "source_ptr")) |trait_source_ptr| {
                                                    _ = EdgePointer.point_to(trait_source_ptr, source_chunk.node, "source", null);
                                                }
                                            },
                                            .err => {
                                                std.debug.print("Failed to instantiate has_source_chunk trait while executing MakeChild\n", .{});
                                                return visitor.VisitResult(void){ .ERROR = error.InstantiationFailed };
                                            },
                                        }
                                    }
                                }
                            }
                        }
                    },
                    .err => |err_info| {
                        // Propagate the error with the original failing node and identifier
                        self.failing_node = err_info.node;
                        self.error_kind = err_info.kind;
                        self.error_message = err_info.message;
                        self.error_identifier = err_info.identifier;
                        return visitor.VisitResult(void){ .ERROR = error.UnresolvedTypeReference };
                    },
                }

                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var make_child_visitor = VisitMakeChildren{
            .type_graph = tg,
            .parent_instance = new_instance,
        };
        const make_child_result = tg.visit_make_children(type_node, void, &make_child_visitor, VisitMakeChildren.visit);
        // FIXME: restore
        // const make_child_result = type_owner_tg.visit_make_children(type_node, void, &make_child_visitor, VisitMakeChildren.visit);
        switch (make_child_result) {
            .ERROR => {
                if (make_child_visitor.failing_node) |failing| {
                    return InstantiateResult{ .err = InstantiationError{
                        .node = failing,
                        .message = make_child_visitor.error_message,
                        .kind = make_child_visitor.error_kind,
                        .identifier = make_child_visitor.error_identifier,
                    } };
                }
                // Fallback if no failing node captured
                return InstantiateResult{ .err = InstantiationError{
                    .node = type_node,
                    .message = "MakeChild instantiation failed",
                    .kind = .other,
                } };
            },
            else => {},
        }

        // 3) Visit MakeLink nodes of type_node
        const VisitMakeLinks = struct {
            type_graph: *TypeGraph,
            parent_instance: graph.BoundNodeReference,
            /// Captures the failing MakeLink node for rich error reporting
            failing_node: ?BoundNodeReference = null,
            error_kind: InstantiationErrorKind = .other,
            error_message: []const u8 = "",
            /// The identifier that was being looked up when the error occurred
            error_identifier: []const u8 = "",

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));

                const make_link = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                // 3.1) Get operand references (lhs and rhs)
                const lhs_reference_node = EdgeComposition.get_child_by_identifier(make_link, "lhs");
                const rhs_reference_node = EdgeComposition.get_child_by_identifier(make_link, "rhs");

                if (lhs_reference_node == null or rhs_reference_node == null) {
                    self.failing_node = make_link;
                    self.error_kind = .missing_operand_reference;
                    self.error_message = "Missing operand reference in MakeLink";
                    return visitor.VisitResult(void){ .ERROR = error.MissingOperandReference };
                }

                // 3.2) Resolve operand references to actual instance nodes
                const lhs_result = ChildReferenceNode.resolve(lhs_reference_node.?, self.parent_instance);
                const lhs_resolved = switch (lhs_result) {
                    .ok => |resolved| resolved,
                    .err => |resolve_err| {
                        // Use the make_link node (not the reference) since it has the source chunk
                        self.failing_node = make_link;
                        self.error_kind = .unresolved_reference;
                        self.error_message = resolve_err.message;
                        self.error_identifier = resolve_err.identifier;
                        return visitor.VisitResult(void){ .ERROR = error.UnresolvedReference };
                    },
                };
                const rhs_result = ChildReferenceNode.resolve(rhs_reference_node.?, self.parent_instance);
                const rhs_resolved = switch (rhs_result) {
                    .ok => |resolved| resolved,
                    .err => |resolve_err| {
                        // Use the make_link node (not the reference) since it has the source chunk
                        self.failing_node = make_link;
                        self.error_kind = .unresolved_reference;
                        self.error_message = resolve_err.message;
                        self.error_identifier = resolve_err.identifier;
                        return visitor.VisitResult(void){ .ERROR = error.UnresolvedReference };
                    },
                };

                // 3.3) Create link between resolved nodes
                const link_edge = MakeLinkNode.Attributes.of(make_link).load_edge_attributes(lhs_resolved.node, rhs_resolved.node);
                _ = self.parent_instance.g.insert_edge(link_edge);

                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        // Only visit make_link children if TypeGraph is fully initialized
        // This avoids circular dependency during TypeGraph initialization
        if (tg.get_initialized()) {
            // FIXME: restore
            // if (type_owner_tg.get_initialized()) {
            var make_link_visitor = VisitMakeLinks{
                .type_graph = tg,
                .parent_instance = new_instance,
            };
            const make_link_result = EdgeComposition.visit_children_of_type(type_node, tg.get_MakeLink().node, void, &make_link_visitor, VisitMakeLinks.visit);
            // FIXME: restore
            // const make_link_result = EdgeComposition.visit_children_of_type(type_node, type_owner_tg.get_MakeLink().node, void, &make_link_visitor, VisitMakeLinks.visit);
            switch (make_link_result) {
                .ERROR => {
                    if (make_link_visitor.failing_node) |failing| {
                        return InstantiateResult{ .err = InstantiationError{
                            .node = failing,
                            .message = make_link_visitor.error_message,
                            .kind = make_link_visitor.error_kind,
                            .identifier = make_link_visitor.error_identifier,
                        } };
                    }
                    // Fallback if no failing node captured
                    return InstantiateResult{ .err = InstantiationError{
                        .node = type_node,
                        .message = "MakeLink instantiation failed",
                        .kind = .other,
                    } };
                },
                else => {},
            }
        }

        return InstantiateResult{ .ok = new_instance };
    }

    pub fn get_type_by_name(self: *const @This(), type_identifier: str) ?BoundNodeReference {
        // TODO make trait.zig
        return EdgeComposition.get_child_by_identifier(self.self_node, type_identifier);
    }

    pub fn instantiate(self: *@This(), type_identifier: str) InstantiateResult {
        const parent_type_node = self.get_type_by_name(type_identifier) orelse {
            return InstantiateResult{
                .err = InstantiationError{
                    .node = self.self_node, // Use typegraph node as fallback
                    .message = "Type not found",
                    .kind = .invalid_argument,
                },
            };
        };
        return self.instantiate_node(parent_type_node);
    }

    pub fn get_or_create_type(self: *@This(), type_identifier: str) !BoundNodeReference {
        if (self.get_type_by_name(type_identifier)) |type_node| {
            return type_node;
        }
        return try self.add_type(type_identifier);
    }

    pub fn get_graph_view(self: *@This()) *GraphView {
        return self.self_node.g;
    }

    pub const TypeInstanceCount = struct {
        type_name: str,
        instance_count: usize,
    };

    /// Visit all type nodes in the typegraph.
    /// Each type node is a direct child of the typegraph's self_node.
    pub fn visit_types(
        self: *const @This(),
        comptime T: type,
        ctx: *anyopaque,
        f: *const fn (*anyopaque, BoundNodeReference) visitor.VisitResult(T),
    ) visitor.VisitResult(T) {
        const Visit = struct {
            ctx: *anyopaque,
            cb: *const fn (*anyopaque, BoundNodeReference) visitor.VisitResult(T),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(T) {
                const visitor_: *@This() = @ptrCast(@alignCast(self_ptr));
                const type_node = bound_edge.g.bind(EdgeComposition.get_child_node(bound_edge.edge));
                return visitor_.cb(visitor_.ctx, type_node);
            }
        };
        var visitor_ = Visit{ .ctx = ctx, .cb = f };
        return EdgeComposition.visit_children_edges(self.self_node, T, &visitor_, Visit.visit);
    }

    pub fn get_type_instance_overview(self: *const @This(), allocator: std.mem.Allocator) std.ArrayList(TypeInstanceCount) {
        var result = std.ArrayList(TypeInstanceCount).init(allocator);

        const Counter = struct {
            counts: *std.ArrayList(TypeInstanceCount),

            pub fn visit(self_ptr: *anyopaque, type_node: BoundNodeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));

                // Get type name
                const type_name = TypeNodeAttributes.of(type_node.node).get_type_name();

                // Count instances of this type
                var count: usize = 0;
                const InstanceCounter = struct {
                    count_ptr: *usize,

                    pub fn count_instance(counter_ptr: *anyopaque, _: graph.BoundEdgeReference) visitor.VisitResult(void) {
                        const counter: *@This() = @ptrCast(@alignCast(counter_ptr));
                        counter.count_ptr.* += 1;
                        return visitor.VisitResult(void){ .CONTINUE = {} };
                    }
                };
                var instance_counter = InstanceCounter{ .count_ptr = &count };
                _ = EdgeType.visit_instance_edges(type_node, &instance_counter, InstanceCounter.count_instance);

                ctx.counts.append(.{ .type_name = type_name, .instance_count = count }) catch |e| {
                    return visitor.VisitResult(void){ .ERROR = e };
                };

                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var counter = Counter{ .counts = &result };
        const visit_result = self.visit_types(void, &counter, Counter.visit);
        switch (visit_result) {
            .ERROR => |err| switch (err) {
                error.OutOfMemory => @panic("OOM"),
                else => {},
            },
            else => {},
        }

        return result;
    }

    fn _get_bootstrapped_nodes(self: *const @This()) [6]NodeReference {
        const out: [6]NodeReference = .{
            self.get_ImplementsTrait().node,
            self.get_ImplementsType().node,
            self.get_MakeChild().node,
            self.get_MakeLink().node,
            self.get_Reference().node,
            self.get_TypeReference().node,
        };
        return out;
    }

    pub fn copy_into(self: *@This(), dst: *GraphView, minimal: bool) @This() {
        // minimal = tg node + bootstrap nodes only
        const start_node = if (minimal) self.get_MakeChild() else self.self_node;
        copy_node_into(start_node, dst, !minimal);
        // Return a TypeGraph wrapping the copied self_node in the destination graph
        return TypeGraph.of(dst.bind(self.self_node.node));
    }

    /// Get a map of all type names to their corresponding type nodes.
    pub fn get_type_names(self: *const @This(), type_names: *std.StringHashMap(NodeReference)) void {
        const Collector = struct {
            names: *std.StringHashMap(NodeReference),

            pub fn visit(self_ptr: *anyopaque, type_node: BoundNodeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));
                const type_name = TypeNodeAttributes.of(type_node.node).get_type_name();
                ctx.names.put(type_name, type_node.node) catch @panic("OOM");
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var collector = Collector{ .names = type_names };
        _ = self.visit_types(void, &collector, Collector.visit);
    }

    pub fn copy_node_into(start_node: BoundNodeReference, dst: *GraphView, force_descent: bool) void {
        const g = start_node.g;
        var arena = std.heap.ArenaAllocator.init(dst.base_allocator);
        const allocator = arena.allocator();
        defer arena.deinit();

        var queue = std.ArrayList(NodeReference).init(allocator);
        defer queue.deinit();

        var node_collect = std.ArrayList(NodeReference).init(allocator);
        defer node_collect.deinit();
        var edge_collect = std.ArrayList(EdgeReference).init(allocator);
        defer edge_collect.deinit();
        const node_uuid_set = &dst.node_set;
        const edge_uuid_set = &dst.edge_set;

        var type_map = graph.NodeRefMap.T(NodeReference).init(allocator);
        defer type_map.deinit();

        // Helper struct with functions to collect nodes
        const Collector = struct {
            allocator: std.mem.Allocator,
            queue: *std.ArrayList(NodeReference),
            dst: *GraphView,
            node_collect: *std.ArrayList(NodeReference),
            edge_collect: *std.ArrayList(EdgeReference),
            node_uuid_set: *graph.UUIDBitSet,
            edge_uuid_set: *graph.UUIDBitSet,
            type_map: *graph.NodeRefMap.T(NodeReference),
            existing_tg: ?bool,

            fn raw_add_node(ctx: *@This(), node: NodeReference) void {
                if (!ctx.node_uuid_set.get_or_set(node.get_uuid())) {
                    ctx.node_collect.append(node) catch @panic("OOM");
                }
            }

            fn raw_add_edge(ctx: *@This(), edge: EdgeReference) void {
                if (!ctx.edge_uuid_set.get_or_set(edge.get_uuid())) {
                    ctx.edge_collect.append(edge) catch @panic("OOM");
                }
            }

            fn contains_node(ctx: *@This(), node: NodeReference) bool {
                return ctx.node_uuid_set.contains(node.get_uuid());
            }

            fn contains_edge(ctx: *@This(), edge: EdgeReference) bool {
                return ctx.edge_uuid_set.contains(edge.get_uuid());
            }

            fn add_node(ctx: *@This(), node: NodeReference) bool {
                if (ctx.contains_node(node)) {
                    return false;
                }
                ctx.raw_add_node(node);
                ctx.queue.append(node) catch @panic("OOM");
                return true;
            }

            fn add_edge(ctx: *@This(), edge: EdgeReference, target: NodeReference) void {
                if (ctx.contains_edge(edge)) {
                    return;
                }
                _ = ctx.add_node(target);
                ctx.raw_add_edge(edge);
            }

            fn visit_typegraph(ctx: *@This(), tg: TypeGraph) void {
                if (ctx.contains_node(tg.self_node.node)) {
                    if (ctx.existing_tg != null) {
                        @branchHint(.likely);
                        return;
                    }
                    // if tg already in other graph before copy
                    // we need to make sure to merge the type names
                    // prepping old type->new type mapping here
                    // merging done in visit_type_node
                    ctx.existing_tg = true;
                    const tg_dst = TypeGraph.of(ctx.dst.bind(tg.self_node.node));

                    var old_type_names = std.StringHashMap(NodeReference).init(ctx.allocator);
                    var new_type_names = std.StringHashMap(NodeReference).init(ctx.allocator);
                    tg.get_type_names(&old_type_names);
                    tg_dst.get_type_names(&new_type_names);
                    var iter = old_type_names.iterator();
                    while (iter.next()) |entry| {
                        const type_name = entry.key_ptr.*;
                        const old_type_node = entry.value_ptr.*;
                        if (new_type_names.get(type_name)) |new_type_node| {
                            if (old_type_node.is_same(new_type_node)) {
                                continue;
                            }
                            ctx.type_map.put(old_type_node, new_type_node) catch @panic("OOM");
                        }
                    }
                    return;
                }

                ctx.existing_tg = false;
                // needs special treatment because it has all types as children
                // so we dont want to put it in the queue
                ctx.raw_add_node(tg.self_node.node);
                const tg_bootstrap_nodes = tg._get_bootstrapped_nodes();
                for (tg_bootstrap_nodes) |node| {
                    const parent_edge = EdgeComposition.get_parent_edge(tg.get_g().bind(node)).?;
                    _ = ctx.add_node(node);
                    // manually add parent edge, because tg will not walk its children edges
                    ctx.raw_add_edge(parent_edge.edge);
                }
            }

            fn visit_type(ctx: *@This(), bound_node: graph.BoundNodeReference) void {
                // type node - check if node actually has type_identifier attribute
                const is_type_node = bound_node.node.get(TypeNodeAttributes.type_identifier) != null;
                if (is_type_node) {
                    if (TypeGraph.of_type(bound_node)) |tg| {
                        if (ctx.existing_tg == null) {
                            ctx.visit_typegraph(tg);
                        } else if (ctx.existing_tg == true) {
                            const collision = ctx.type_map.get(bound_node.node);
                            // type already exists, for now just yield
                            if (collision != null) {
                                return;
                            }
                        }
                        const parent_edge = EdgeComposition.get_parent_edge(bound_node).?.edge;
                        ctx.raw_add_edge(parent_edge);
                    }
                }

                // instance node
                if (EdgeType.get_type_edge(bound_node)) |type_edge| {
                    const type_node = bound_node.g.bind(EdgeType.get_type_node(type_edge.edge));

                    // tg not visited yet, visit it
                    if (ctx.existing_tg == null) {
                        const tg = TypeGraph.of_type(type_node).?;
                        ctx.visit_typegraph(tg);
                    }

                    // type already exists, add our instance edge and call it a day
                    if (ctx.node_uuid_set.contains(type_node.node.get_uuid())) {
                        ctx.raw_add_edge(type_edge.edge);
                        return;
                    }

                    const collision = ctx.type_map.get(type_node.node);

                    if (ctx.existing_tg == true and collision != null) {
                        // name collision, make instance edge to the existing type node
                        ctx.raw_add_edge(EdgeType.init(collision.?, bound_node.node));
                        return;
                    }

                    // dst graph didn't have it's own tg yet => no name collisions possible
                    // or no collision found
                    const new_type_node = ctx.add_node(type_node.node);

                    // if type node wasn't in the dst graph before, we need to add the composition edge to the typegraph
                    if (new_type_node) {
                        const parent_edge = EdgeComposition.get_parent_edge(type_node).?.edge;
                        ctx.raw_add_edge(parent_edge);
                    }

                    ctx.raw_add_edge(type_edge.edge);
                }
            }

            // Visitor for EdgeComposition children
            fn visit_composition(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const child = EdgeComposition.get_child_node(bound_edge.edge);
                ctx.add_edge(bound_edge.edge, child);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            // Visitor for EdgePointer references
            fn visit_pointer(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const target = EdgePointer.get_referenced_node(bound_edge.edge);
                ctx.add_edge(bound_edge.edge, target);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            // Visitor for EdgeTrait instances or owner
            fn visit_trait_instance_or_owner(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                // Skip "has_source_chunk" trait edges - these point to source chunk nodes
                // in the type graph and should not be copied (they would cause the entire
                // source chunk subgraph to be copied, leading to issues during solver bootstrap).
                // Check the trait instance's type name to identify has_source_chunk traits
                const trait_instance = EdgeTrait.get_trait_instance_node(bound_edge.edge);
                const bound_trait = bound_edge.g.bind(trait_instance);
                if (EdgeType.get_type_edge(bound_trait)) |type_edge| {
                    const type_node = EdgeType.get_type_node(type_edge.edge);
                    const type_name = TypeNodeAttributes.of(type_node).get_type_name();
                    if (std.mem.eql(u8, type_name, "has_source_chunk")) {
                        return visitor.VisitResult(void){ .CONTINUE = {} };
                    }
                }
                const owner = bound_edge.edge.get_source_node();
                _ = ctx.add_node(owner);
                const instance = bound_edge.edge.get_target_node();
                ctx.add_edge(bound_edge.edge, instance);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            // Visitor for EdgeOperand references
            fn visit_operand(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const target = bound_edge.edge.get_target_node();
                ctx.add_edge(bound_edge.edge, target);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            fn visit_next(ctx: *@This(), bound_node: graph.BoundNodeReference) void {
                if (EdgeNext.get_next_edge(bound_node)) |next_edge| {
                    ctx.add_edge(next_edge.edge, EdgeNext.get_next_node(next_edge.edge).?);
                }
            }

            fn visit_node(ctx: *@This(), bound_node: graph.BoundNodeReference) void {
                ctx.visit_type(bound_node);
                _ = EdgeComposition.visit_children_edges(bound_node, void, ctx, visit_composition);
                _ = EdgePointer.visit_pointed_edges(bound_node, void, ctx, visit_pointer);
                ctx.visit_next(bound_node);
                _ = bound_node.g.visit_edges_of_type(bound_node.node, EdgeTrait.tid, void, ctx, visit_trait_instance_or_owner, null);
                _ = EdgeOperand.visit_operand_edges(bound_node, void, ctx, visit_operand);
            }
        };

        var collector = Collector{
            .allocator = allocator,
            .queue = &queue,
            .dst = dst,
            .node_collect = &node_collect,
            .edge_collect = &edge_collect,
            .node_uuid_set = node_uuid_set,
            .edge_uuid_set = edge_uuid_set,
            .type_map = &type_map,
            .existing_tg = null,
        };

        const root_new = collector.add_node(start_node.node);
        if (force_descent and !root_new) {
            queue.append(start_node.node) catch @panic("OOM");
        }

        var i: usize = 0;
        while (i < queue.items.len) : (i += 1) {
            const current = queue.items[i];
            const bound_current = g.bind(current);
            collector.visit_node(bound_current);
        }

        dst.nodes.ensureUnusedCapacity(@intCast(node_collect.items.len)) catch @panic("OOM");
        for (node_collect.items) |node| {
            dst.nodes.put(node, graph.EdgeTypeMap.T(std.ArrayList(EdgeReference)).init(dst.allocator)) catch @panic("OOM");
        }
        for (edge_collect.items) |edge| {
            dst.insert_edge_unchecked(edge);
        }
    }
};

test "basic typegraph" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    var tg = TypeGraph.init(&g);

    defer g.deinit();

    const Example = try tg.add_type("Example");
    var children = std.ArrayList(graph.BoundEdgeReference).init(a);
    defer children.deinit();
    const visit_result = EdgeComposition.visit_children_edges(Example, void, &children, visitor.collect(graph.BoundEdgeReference).collect_into_list);
    switch (visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }
    std.debug.print("TYPE collected children: {d}\n", .{children.items.len});
}

test "add_type returns error on duplicate name" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();
    var tg = TypeGraph.init(&g);

    // First add_type should succeed
    _ = try tg.add_type("DuplicateTest");

    // Second add_type with same name should return TypeAlreadyExists error
    const result = tg.add_type("DuplicateTest");
    try std.testing.expectError(error.TypeAlreadyExists, result);
}

//zig test --dep graph -Mroot=src/faebryk/typegraph.zig -Mgraph=src/graph/lib.zig
test "basic instantiation" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();
    var tg = TypeGraph.init(&g);

    // Build type graph
    const Electrical = try tg.add_type("Electrical");
    const Capacitor = try tg.add_type("Capacitor");
    _ = try tg.add_make_child(Capacitor, Electrical, "p1", null, false);
    _ = try tg.add_make_child(Capacitor, Electrical, "p2", null, false);
    const Resistor = try tg.add_type("Resistor");
    // Test: add node attributes to p1 MakeChild
    var res_p1_attrs = TypeGraph.MakeChildNode.build(null);
    res_p1_attrs.dynamic.put("test_attr", .{ .String = "test_value" });
    res_p1_attrs.dynamic.put("pin_number", .{ .Int = 42 });
    const res_p1_makechild = try tg.add_make_child(Resistor, Electrical, "p1", &res_p1_attrs, false);
    std.debug.print("RES_P1_MAKECHILD: {s}\n", .{try EdgeComposition.get_name(EdgeComposition.get_parent_edge(res_p1_makechild).?.edge)});
    _ = try tg.add_make_child(Resistor, Electrical, "p2", null, false);
    _ = try tg.add_make_child(Resistor, Capacitor, "cap1", null, false);

    var node_attrs = TypeGraph.MakeChildNode.build("test_string");
    _ = try tg.add_make_child(Capacitor, Electrical, "tp", &node_attrs, false);

    // Build instance graph
    const resistor = switch (tg.instantiate_node(Resistor)) {
        .ok => |n| n,
        .err => |e| {
            std.debug.print("Instantiation failed: {s}\n", .{e.message});
            return error.InstantiationFailed;
        },
    };

    // test: instance graph
    std.debug.print("Resistor Instance: {d}\n", .{resistor.node.get_uuid()});
    const p1 = EdgeComposition.get_child_by_identifier(resistor, "p1").?;
    const p2 = EdgeComposition.get_child_by_identifier(resistor, "p2").?;
    const cap1 = EdgeComposition.get_child_by_identifier(resistor, "cap1").?;
    const cap1p1 = EdgeComposition.get_child_by_identifier(cap1, "p1").?;
    const cap1p2 = EdgeComposition.get_child_by_identifier(cap1, "p2").?;
    try std.testing.expect(EdgeType.is_node_instance_of(p1, Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(p2, Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1, Capacitor.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1p1, Electrical.node));
    try std.testing.expect(EdgeType.is_node_instance_of(cap1p2, Electrical.node));

    // Test: verify node attributes were copied from MakeChild to instance
    const p1_test_attr = p1.node.get("test_attr");
    try std.testing.expect(p1_test_attr != null);
    try std.testing.expect(p1_test_attr.? == .String);
    try std.testing.expect(std.mem.eql(u8, p1_test_attr.?.String, "test_value"));
    const p1_pin_number = p1.node.get("pin_number");
    try std.testing.expect(p1_pin_number != null);
    try std.testing.expect(p1_pin_number.? == .Int);
    try std.testing.expectEqual(@as(i64, 42), p1_pin_number.?.Int);
    std.debug.print("Node attributes copied successfully: test_attr={s}, pin_number={d}\n", .{ p1_test_attr.?.String, p1_pin_number.?.Int });

    // print children of resistor
    var resistor_children = std.ArrayList(graph.BoundEdgeReference).init(a);
    defer resistor_children.deinit();
    const resistor_visit_result = EdgeComposition.visit_children_edges(resistor, void, &resistor_children, visitor.collect(graph.BoundEdgeReference).collect_into_list);
    switch (resistor_visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }
    std.debug.print("TYPE collected children: {d}\n", .{resistor_children.items.len});

    // Build nested reference using EdgeTraversal
    const cap1p1_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ EdgeComposition.traverse("cap1"), EdgeComposition.traverse("p1") });
    const cap1p2_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ EdgeComposition.traverse("cap1"), EdgeComposition.traverse("p2") });

    // test: resolve_instance_reference
    const cap1p1_reference_resolved = switch (TypeGraph.ChildReferenceNode.resolve(cap1p1_reference, resistor)) {
        .ok => |resolved| resolved,
        .err => |e| {
            std.debug.print("Resolve failed: {s}\n", .{e.message});
            return error.ResolveFailed;
        },
    };
    try std.testing.expect(cap1p1_reference_resolved.node.is_same(cap1p1.node));

    // Build make link
    // TODO: use interface link
    _ = try tg.add_make_link(Resistor, cap1p1_reference, cap1p2_reference, .{
        .edge_type = EdgePointer.tid,
        .directional = true,
        .name = null,
        .dynamic = graph.DynamicAttributes.init_on_stack(),
    });

    const instantiated_resistor = switch (tg.instantiate("Resistor")) {
        .ok => |n| n,
        .err => |e| {
            std.debug.print("Instantiation failed: {s}\n", .{e.message});
            return error.InstantiationFailed;
        },
    };
    const instantiated_p1 = EdgeComposition.get_child_by_identifier(instantiated_resistor, "p1").?;
    const instantiated_cap = EdgeComposition.get_child_by_identifier(instantiated_resistor, "cap1").?;
    const instantiated_cap_p1 = EdgeComposition.get_child_by_identifier(instantiated_cap, "p1").?;
    const instantiated_cap_p2 = EdgeComposition.get_child_by_identifier(instantiated_cap, "p2").?;
    std.debug.print("Instantiated Resistor Instance: {d}\n", .{instantiated_resistor.node.get_uuid()});
    std.debug.print("Instantiated P1 Instance: {d}\n", .{instantiated_p1.node.get_uuid()});

    const cref = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ EdgeComposition.traverse("<<Resistor"), EdgeComposition.traverse("p1") });
    const result_node = switch (TypeGraph.ChildReferenceNode.resolve(cref, cref)) {
        .ok => |resolved| resolved,
        .err => |e| {
            std.debug.print("Resolve failed: {s}\n", .{e.message});
            return error.ResolveFailed;
        },
    };
    std.debug.print("result node: {d}\n", .{result_node.node.get_uuid()});

    // test: check edge created
    const _EdgeVisitor = struct {
        seek: BoundNodeReference,

        pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(self_ptr));
            std.testing.expect(EdgePointer.is_instance(bound_edge.edge)) catch return visitor.VisitResult(void){ .ERROR = error.InvalidArgument };
            const referenced_node = EdgePointer.get_referenced_node(bound_edge.edge);
            if (referenced_node.is_same(self.seek.node)) {
                return visitor.VisitResult(void){ .OK = {} };
            }
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };
    var _visit = _EdgeVisitor{ .seek = instantiated_cap_p2 };
    const result = instantiated_cap_p1.g.visit_edges_of_type(instantiated_cap_p1.node, EdgePointer.tid, void, &_visit, _EdgeVisitor.visit, null);
    try std.testing.expect(result == .OK);
}

test "typegraph iterators and mount chains" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();
    var tg = TypeGraph.init(&g);

    const top = try tg.add_type("Top");
    const Inner = try tg.add_type("Inner");
    const PointerSequence = try tg.add_type("PointerSequence");

    const members = try tg.add_make_child(top, PointerSequence, "members", null, false);
    _ = try tg.add_make_child(top, Inner, "base", null, false);
    const extra = try tg.add_make_child(top, Inner, "extra", null, false);
    _ = members;
    _ = extra;
    _ = try tg.add_make_child(top, Inner, "0", null, false);
    _ = try tg.add_make_child(top, Inner, "1", null, false);
    const base_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{EdgeComposition.traverse("base")});
    const extra_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{EdgeComposition.traverse("extra")});
    const link_attrs = EdgeCreationAttributes{
        .edge_type = EdgePointer.tid,
        .directional = true,
        .name = null,
        .dynamic = graph.DynamicAttributes.init_on_stack(),
    };
    _ = try tg.add_make_link(top, base_reference, extra_reference, link_attrs);

    const container_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{EdgeComposition.traverse("members")});
    const element0_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{EdgeComposition.traverse("0")});
    const element1_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{EdgeComposition.traverse("1")});
    const ptr_link_attrs_0 = EdgePointer.build(null, 0);
    _ = try tg.add_make_link(top, container_reference, element0_reference, ptr_link_attrs_0);
    const ptr_link_attrs_1 = EdgePointer.build(null, 1);
    _ = try tg.add_make_link(top, container_reference, element1_reference, ptr_link_attrs_1);

    const children = tg.collect_make_children(a, top);
    defer a.free(children);
    try std.testing.expectEqual(@as(usize, 5), children.len);

    var seen_members = false;
    var seen_base = false;
    var seen_extra = false;
    var seen_zero = false;
    var seen_one = false;
    for (children) |child_info| {
        const identifier = child_info.identifier orelse "";
        if (std.mem.eql(u8, identifier, "members")) seen_members = true;
        if (std.mem.eql(u8, identifier, "base")) seen_base = true;
        if (std.mem.eql(u8, identifier, "extra")) seen_extra = true;
        if (std.mem.eql(u8, identifier, "0")) seen_zero = true;
        if (std.mem.eql(u8, identifier, "1")) seen_one = true;
    }
    try std.testing.expect(seen_members);
    try std.testing.expect(seen_base);
    try std.testing.expect(seen_extra);
    try std.testing.expect(seen_zero);
    try std.testing.expect(seen_one);

    const detailed_links = try tg.collect_make_links(a, top);
    defer {
        for (detailed_links) |info| {
            a.free(info.lhs_path);
            a.free(info.rhs_path);
        }
        a.free(detailed_links);
    }
    try std.testing.expectEqual(@as(usize, 3), detailed_links.len);

    // Find the base->extra link for specific validation
    var base_extra_link: ?TypeGraph.MakeLinkInfo = null;
    for (detailed_links) |info| {
        if (info.lhs_path.len == 1 and std.mem.eql(u8, info.lhs_path[0].identifier, "base")) {
            base_extra_link = info;
            break;
        }
    }
    try std.testing.expect(base_extra_link != null);
    try std.testing.expectEqual(@as(usize, 1), base_extra_link.?.rhs_path.len);
    try std.testing.expectEqualStrings("extra", base_extra_link.?.rhs_path[0].identifier);

    const lhs = EdgeComposition.get_child_by_identifier(base_extra_link.?.make_link, "lhs").?;
    const rhs = EdgeComposition.get_child_by_identifier(base_extra_link.?.make_link, "rhs").?;
    try std.testing.expect(lhs.node.is_same(base_reference.node));
    try std.testing.expect(rhs.node.is_same(extra_reference.node));

    const lhs_path = try tg.get_reference_path(a, lhs);
    defer a.free(lhs_path);
    try std.testing.expectEqual(@as(usize, 1), lhs_path.len);
    try std.testing.expectEqualStrings("base", lhs_path[0].identifier);

    const pointer_members = try tg.collect_pointer_members(a, top, &.{"members"}, null);
    defer a.free(pointer_members);
    try std.testing.expectEqual(@as(usize, 2), pointer_members.len);
    try std.testing.expect(pointer_members[0].identifier != null);
    try std.testing.expect(pointer_members[1].identifier != null);
    try std.testing.expectEqualStrings("0", pointer_members[0].identifier.?);
    try std.testing.expectEqualStrings("1", pointer_members[1].identifier.?);
}

//zig test --dep graph -Mroot=src/faebryk/typegraph.zig -Mgraph=src/graph/lib.zig
test "get_type_instance_overview" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);

    // Build type graph with some types
    const Electrical = try tg.add_type("Electrical");
    const Capacitor = try tg.add_type("Capacitor");
    _ = try tg.add_make_child(Capacitor, Electrical, "p1", null, false);
    _ = try tg.add_make_child(Capacitor, Electrical, "p2", null, false);
    const Resistor = try tg.add_type("Resistor");
    _ = try tg.add_make_child(Resistor, Electrical, "p1", null, false);
    _ = try tg.add_make_child(Resistor, Electrical, "p2", null, false);

    // Create some instances
    _ = switch (tg.instantiate_node(Capacitor)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    _ = switch (tg.instantiate_node(Capacitor)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    _ = switch (tg.instantiate_node(Resistor)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };

    // Get the overview
    var overview = tg.get_type_instance_overview(a);
    defer overview.deinit();

    // Find counts for our types
    var capacitor_count: ?usize = null;
    var resistor_count: ?usize = null;
    var electrical_count: ?usize = null;

    for (overview.items) |item| {
        if (std.mem.eql(u8, item.type_name, "Capacitor")) {
            capacitor_count = item.instance_count;
        } else if (std.mem.eql(u8, item.type_name, "Resistor")) {
            resistor_count = item.instance_count;
        } else if (std.mem.eql(u8, item.type_name, "Electrical")) {
            electrical_count = item.instance_count;
        }
    }

    // Capacitor has 2 direct instances, Resistor has 1 direct instance
    // Electrical has more instances because of the children of Capacitor/Resistor
    try std.testing.expect(capacitor_count != null);
    try std.testing.expect(resistor_count != null);
    try std.testing.expect(electrical_count != null);
    try std.testing.expectEqual(capacitor_count.?, 2);
    try std.testing.expectEqual(resistor_count.?, 1);
    // Each Capacitor has 2 Electrical children (p1, p2), each Resistor has 2 Electrical children
    // 2 Capacitors * 2 = 4, 1 Resistor * 2 = 2, total = 6
    try std.testing.expectEqual(electrical_count.?, 6);

    std.debug.print("\nType instance overview:\n", .{});
    for (overview.items) |item| {
        std.debug.print("  {s}: {d} instances\n", .{ item.type_name, item.instance_count });
    }
}

test "resolve path through trait and pointer edges" {
    // Test that EdgeTraversal allows resolving paths through different edge types:
    // TopModule -> resistor (Composition) -> can_bridge (Trait) -> in_ (Pointer) -> p1
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();
    var tg = TypeGraph.init(&g);

    // 1. Build type graph: Electrical, CanBridge trait, Resistor
    const Electrical = try tg.add_type("Electrical");
    const CanBridge = try tg.add_type("CanBridge");

    // Mark CanBridge as a trait type
    const implements_trait_instance = switch (tg.instantiate_node(tg.get_ImplementsTrait())) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    _ = EdgeTrait.add_trait_instance(CanBridge, implements_trait_instance.node);

    const Resistor = try tg.add_type("Resistor");
    _ = try tg.add_make_child(Resistor, Electrical, "p1", null, false);
    _ = try tg.add_make_child(Resistor, Electrical, "p2", null, false);

    // 2. Create a Resistor instance with p1, p2 children
    const resistor_instance = switch (tg.instantiate_node(Resistor)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    const p1_instance = EdgeComposition.get_child_by_identifier(resistor_instance, "p1").?;
    const p2_instance = EdgeComposition.get_child_by_identifier(resistor_instance, "p2").?;

    std.debug.print("\nResistor instance: {d}\n", .{resistor_instance.node.get_uuid()});
    std.debug.print("p1 instance: {d}\n", .{p1_instance.node.get_uuid()});
    std.debug.print("p2 instance: {d}\n", .{p2_instance.node.get_uuid()});

    // 3. Create a can_bridge trait instance and attach to resistor
    const can_bridge_instance = switch (tg.instantiate_node(CanBridge)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    _ = EdgeTrait.add_trait_instance(resistor_instance, can_bridge_instance.node);
    // Set edge name so we can find it by identifier
    const trait_edge = EdgeTrait.get_owner_edge(can_bridge_instance).?;
    trait_edge.edge.set_attribute_name("can_bridge");

    std.debug.print("can_bridge instance: {d}\n", .{can_bridge_instance.node.get_uuid()});

    // 4. Add Pointer nodes as composition children of can_bridge, then point them to p1/p2
    // Create Pointer type if not exists
    const PointerType = tg.get_type_by_name("Pointer") orelse try tg.add_type("Pointer");
    const in_ptr = switch (tg.instantiate_node(PointerType)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    const out_ptr = switch (tg.instantiate_node(PointerType)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };

    // Add as composition children of can_bridge (must use add_child to insert into graph index)
    _ = EdgeComposition.add_child(can_bridge_instance, in_ptr.node, "in_");
    _ = EdgeComposition.add_child(can_bridge_instance, out_ptr.node, "out_");

    // Point the Pointer nodes to p1 and p2
    _ = EdgePointer.point_to(in_ptr, p1_instance.node, null, null);
    _ = EdgePointer.point_to(out_ptr, p2_instance.node, null, null);

    // 5. Create reference path using EdgeTraversal:
    //    can_bridge (Trait edge) -> in_ (Composition) -> dereference (Pointer)
    const path = [_]TypeGraph.ChildReferenceNode.EdgeTraversal{
        EdgeTrait.traverse("CanBridge"),
        EdgeComposition.traverse("in_"),
        EdgePointer.traverse(),
    };

    const reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &path);

    // 6. Resolve the reference starting from resistor_instance
    const resolved = switch (TypeGraph.ChildReferenceNode.resolve(reference, resistor_instance)) {
        .ok => |r| r,
        .err => |e| {
            std.debug.print("Resolve failed: {s}\n", .{e.message});
            return error.ResolveFailed;
        },
    };
    std.debug.print("Resolved node: {d}\n", .{resolved.node.get_uuid()});

    // 7. Verify we resolved to p1_instance
    try std.testing.expect(resolved.node.is_same(p1_instance.node));

    // 8. Test the out_ path as well
    const ET = TypeGraph.ChildReferenceNode.EdgeTraversal;
    const path_out = [_]ET{
        EdgeTrait.traverse("CanBridge"),
        EdgeComposition.traverse("out_"),
        EdgePointer.traverse(),
    };
    const reference_out = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &path_out);
    const resolved_out = switch (TypeGraph.ChildReferenceNode.resolve(reference_out, resistor_instance)) {
        .ok => |r| r,
        .err => |e| {
            std.debug.print("Resolve failed: {s}\n", .{e.message});
            return error.ResolveFailed;
        },
    };
    try std.testing.expect(resolved_out.node.is_same(p2_instance.node));

    std.debug.print("EdgeTraversal test passed: resolved can_bridge->in_ to p1, can_bridge->out_ to p2\n", .{});

    // ===== MIXED PATH TEST =====
    // Test that mixing Composition with Trait/Pointer works
    // Create a TopModule that contains the resistor as a child

    const TopModule = try tg.add_type("TopModule");
    _ = try tg.add_make_child(TopModule, Resistor, "resistor", null, false);

    // Create TopModule instance - this will auto-create resistor child
    const top_instance = switch (tg.instantiate_node(TopModule)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    const resistor_child = EdgeComposition.get_child_by_identifier(top_instance, "resistor").?;

    // The resistor_child needs its own can_bridge trait with pointers
    const child_p1 = EdgeComposition.get_child_by_identifier(resistor_child, "p1").?;
    const child_p2 = EdgeComposition.get_child_by_identifier(resistor_child, "p2").?;

    const child_can_bridge = switch (tg.instantiate_node(CanBridge)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    _ = EdgeTrait.add_trait_instance(resistor_child, child_can_bridge.node);

    // Add Pointer nodes as composition children of child_can_bridge
    const child_in_ptr = switch (tg.instantiate_node(PointerType)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    const child_out_ptr = switch (tg.instantiate_node(PointerType)) {
        .ok => |n| n,
        .err => return error.InstantiationFailed,
    };
    _ = EdgeComposition.add_child(child_can_bridge, child_in_ptr.node, "in_");
    _ = EdgeComposition.add_child(child_can_bridge, child_out_ptr.node, "out_");
    _ = EdgePointer.point_to(child_in_ptr, child_p1.node, null, null);
    _ = EdgePointer.point_to(child_out_ptr, child_p2.node, null, null);

    std.debug.print("\nMixed path test:\n", .{});
    std.debug.print("TopModule instance: {d}\n", .{top_instance.node.get_uuid()});
    std.debug.print("resistor child: {d}\n", .{resistor_child.node.get_uuid()});
    std.debug.print("child_p1: {d}\n", .{child_p1.node.get_uuid()});

    // 9. Test MIXED path: resistor (Composition) -> can_bridge (Trait) -> in_ (Composition) -> dereference (Pointer)
    const mixed_path = [_]ET{
        EdgeComposition.traverse("resistor"),
        EdgeTrait.traverse("CanBridge"),
        EdgeComposition.traverse("in_"),
        EdgePointer.traverse(),
    };

    const mixed_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &mixed_path);
    const mixed_resolved = switch (TypeGraph.ChildReferenceNode.resolve(mixed_reference, top_instance)) {
        .ok => |r| r,
        .err => |e| {
            std.debug.print("Resolve failed: {s}\n", .{e.message});
            return error.ResolveFailed;
        },
    };

    std.debug.print("Mixed path resolved to: {d}\n", .{mixed_resolved.node.get_uuid()});
    try std.testing.expect(mixed_resolved.node.is_same(child_p1.node));

    // 10. Test composition-only path
    const comp_path = [_]ET{ EdgeComposition.traverse("resistor"), EdgeComposition.traverse("p1") };
    const comp_ref = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &comp_path);
    const comp_resolved = switch (TypeGraph.ChildReferenceNode.resolve(comp_ref, top_instance)) {
        .ok => |r| r,
        .err => |e| {
            std.debug.print("Resolve failed: {s}\n", .{e.message});
            return error.ResolveFailed;
        },
    };

    std.debug.print("Composition path 'resistor.p1' resolved to: {d}\n", .{comp_resolved.node.get_uuid()});
    try std.testing.expect(comp_resolved.node.is_same(child_p1.node));

    std.debug.print("All EdgeTraversal tests passed!\n", .{});
    std.debug.print("  - Trait->Composition->Pointer path works\n", .{});
    std.debug.print("  - Mixed Composition->Trait->Composition->Pointer path works\n", .{});
    std.debug.print("  - Composition-only path works\n", .{});
}
