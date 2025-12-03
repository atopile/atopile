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
const EdgeCreationAttributes = edgebuilder_mod.EdgeCreationAttributes;
const NodeCreationAttributes = nodebuilder_mod.NodeCreationAttributes;
const Linker = linker_mod.Linker;
const EdgeTrait = trait_mod.EdgeTrait;
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
    };

    pub const MakeLinkInfo = struct {
        make_link: BoundNodeReference,
        lhs_path: []const []const u8,
        rhs_path: []const []const u8,
    };

    const TypeNodeAttributes = struct {
        node: NodeReference,

        pub fn of(node: NodeReference) @This() {
            return .{ .node = node };
        }

        pub const type_identifier = "type_identifier";

        pub fn set_type_name(self: @This(), name: str) void {
            // TODO consider making a put_string that copies the string instead and deallocates it again
            self.node.attributes.dynamic.values.put(type_identifier, .{ .String = name }) catch unreachable;
        }
        pub fn get_type_name(self: @This()) str {
            return self.node.attributes.dynamic.values.get(type_identifier).?.String;
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

            pub fn set_child_identifier(self: @This(), identifier: ?str) void {
                if (identifier) |_identifier| {
                    self.node.node.attributes.dynamic.values.put(child_identifier, .{ .String = _identifier }) catch unreachable;
                }
            }

            pub fn get_child_identifier(self: @This()) ?str {
                if (self.node.node.attributes.dynamic.values.get(child_identifier)) |value| {
                    return value.String;
                }
                return null;
            }

            pub fn set_node_attributes(self: @This(), attributes: NodeCreationAttributes) void {
                if (attributes.dynamic) |d| {
                    d.copy_into(&self.node.node.attributes.dynamic);
                }
            }

            pub fn get_node_attributes(self: @This()) NodeCreationAttributes {
                var dynamic = graph.DynamicAttributes.init(self.node.g.allocator);

                var it = self.node.node.attributes.dynamic.values.iterator();
                while (it.next()) |e| {
                    const key = e.key_ptr.*;
                    if (std.mem.eql(u8, key, "child_identifier")) {
                        continue;
                    }
                    dynamic.values.put(key, e.value_ptr.*) catch unreachable;
                }

                return .{ .dynamic = if (dynamic.values.count() > 0) dynamic else null };
            }
        };

        pub fn get_child_type(node: BoundNodeReference) ?BoundNodeReference {
            if (get_type_reference(node)) |type_ref| {
                return TypeReferenceNode.get_resolved_type(type_ref);
            }
            return null;
        }

        pub fn build(allocator: std.mem.Allocator, value: ?str) NodeCreationAttributes {
            var dynamic: ?graph.DynamicAttributes = null;
            if (value) |v| {
                dynamic = graph.DynamicAttributes.init(allocator);
                dynamic.?.values.put("value", .{ .String = v }) catch unreachable;
            }
            return .{
                .dynamic = if (dynamic) |d| d else null,
            };
        }

        pub fn get_type_reference(node: BoundNodeReference) ?BoundNodeReference {
            return EdgeComposition.get_child_by_identifier(node, "type_ref");
        }

        pub fn get_mount_reference(node: BoundNodeReference) ?BoundNodeReference {
            return EdgeComposition.get_child_by_identifier(node, "mount");
        }
    };

    pub const UnresolvedTypeReference = struct {
        type_node: BoundNodeReference,
        type_reference: BoundNodeReference,
    };

    pub fn collect_unresolved_type_references(
        self: *@This(),
        allocator: std.mem.Allocator,
    ) ![]UnresolvedTypeReference {
        var list = std.ArrayList(UnresolvedTypeReference).init(allocator);
        errdefer list.deinit();

        const VisitMakeChildren = struct {
            type_graph: *TypeGraph,
            type_node: BoundNodeReference,
            list: *std.ArrayList(UnresolvedTypeReference),

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));
                const make_child = edge.g.bind(EdgeComposition.get_child_node(edge.edge));
                const type_reference = MakeChildNode.get_type_reference(make_child) orelse {
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                };

                if (EdgePointer.get_pointed_node_by_identifier(type_reference, "resolved") == null) {
                    ctx.list.append(.{ .type_node = ctx.type_node, .type_reference = type_reference }) catch {
                        return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
                    };
                }

                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        const VisitTypes = struct {
            type_graph: *TypeGraph,
            list: *std.ArrayList(UnresolvedTypeReference),

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));
                const type_node = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                var make_children_ctx = VisitMakeChildren{
                    .type_graph = ctx.type_graph,
                    .type_node = type_node,
                    .list = ctx.list,
                };

                const result = EdgeComposition.visit_children_of_type(
                    type_node,
                    ctx.type_graph.get_MakeChild().node,
                    void,
                    &make_children_ctx,
                    VisitMakeChildren.visit,
                );

                switch (result) {
                    .ERROR => |err| return visitor.VisitResult(void){ .ERROR = err },
                    else => return visitor.VisitResult(void){ .CONTINUE = {} },
                }
            }
        };

        var visit_ctx = VisitTypes{ .type_graph = self, .list = &list };
        const visit_result = EdgeComposition.visit_children_edges(
            self.self_node,
            void,
            &visit_ctx,
            VisitTypes.visit,
        );

        switch (visit_result) {
            .ERROR => |err| switch (err) {
                error.OutOfMemory => return error.OutOfMemory,
                else => return err,
            },
            else => {},
        }

        return list.toOwnedSlice();
    }

    pub const TypeReferenceNode = struct {
        pub const Attributes = struct {
            node: NodeReference,

            pub fn of(node: NodeReference) @This() {
                return .{ .node = node };
            }

            pub const type_identifier = "type_identifier";

            pub fn set_type_identifier(self: @This(), identifier: str) void {
                self.node.attributes.dynamic.values.put(type_identifier, .{ .String = identifier }) catch unreachable;
            }

            pub fn get_type_identifier(self: @This()) str {
                return self.node.attributes.dynamic.values.get(type_identifier).?.String;
            }
        };

        pub fn create_and_insert(tg: *TypeGraph, type_identifier: str) !BoundNodeReference {
            const reference = try tg.instantiate_node(tg.get_TypeReference());
            TypeReferenceNode.Attributes.of(reference.node).set_type_identifier(type_identifier);
            return reference;
        }

        pub fn get_resolved_type(reference: BoundNodeReference) ?BoundNodeReference {
            return EdgePointer.get_pointed_node_by_identifier(reference, "resolved");
        }

        pub fn build(allocator: std.mem.Allocator, value: ?str) NodeCreationAttributes {
            var dynamic: ?graph.DynamicAttributes = null;
            if (value) |v| {
                dynamic = graph.DynamicAttributes.init(allocator);
                dynamic.?.values.put("value", .{ .String = v }) catch unreachable;
            }
            return .{
                .dynamic = if (dynamic) |d| d else null,
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

            pub fn set_child_identifier(self: @This(), identifier: str) void {
                self.node.attributes.dynamic.values.put(child_identifier, .{ .String = identifier }) catch unreachable;
            }

            pub fn get_child_identifier(self: @This()) str {
                return self.node.attributes.dynamic.values.get(child_identifier).?.String;
            }
        };

        pub fn create_and_insert(tg: *TypeGraph, path: []const str) !BoundNodeReference {
            var root: ?BoundNodeReference = null;
            var current_node: ?BoundNodeReference = null;
            for (path) |segment| {
                const reference = try tg.instantiate_node(tg.get_Reference());
                if (current_node) |_current_node| {
                    _ = EdgeNext.add_next(_current_node, reference);
                } else {
                    root = reference;
                }
                ChildReferenceNode.Attributes.of(reference.node).set_child_identifier(segment);
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

        pub fn resolve(reference: BoundNodeReference, instance: BoundNodeReference) ?graph.BoundNodeReference {
            // TODO iterate instead of recursion
            var target = instance;
            const child_identifier = ChildReferenceNode.Attributes.of(reference.node).get_child_identifier();
            const tg = TypeGraph.of_instance(reference).?;

            // TODO: Implement typesafe alternative, escape character just proof of concept
            if (std.mem.startsWith(u8, child_identifier, "<<")) {
                // Parse N after "<<"
                const up_str = child_identifier[2..];
                const type_node = tg.get_type_by_name(up_str);
                if (type_node) |_type_node| {
                    target = _type_node;
                } else {
                    @panic("Type Node not found for enum type");
                }
            } else {
                // if (EdgeTrait.try_get_trait_instance_of_type(instance, tg.get_ImplementsType().node)) |_| {
                //     const make_child = TypeGraph.ChildReferenceNode.get_make_child_node_by_child_identifier(instance, child_identifier);
                //     if (make_child) |_make_child| {
                //         target = _make_child;
                //     }
                // } else {
                const child = EdgeComposition.get_child_by_identifier(instance, child_identifier);
                if (child) |_child| {
                    target = _child;
                }
            }

            const next_reference = EdgeNext.get_next_node_from_node(reference);
            if (next_reference) |_next_reference| {
                const next_ref = reference.g.bind(_next_reference);
                target = ChildReferenceNode.resolve(next_ref, target).?;
            }
            return target;
        }
    };

    pub const MakeLinkNode = struct {
        pub const Attributes = struct {
            node: BoundNodeReference,

            pub fn of(node: BoundNodeReference) @This() {
                return .{ .node = node };
            }

            pub fn set_edge_attributes(self: @This(), attributes: EdgeCreationAttributes) void {
                self.node.node.attributes.dynamic.values.put("edge_type", .{ .Int = attributes.edge_type }) catch unreachable;
                if (attributes.directional) |d| {
                    self.node.node.attributes.dynamic.values.put("directional", .{ .Bool = d }) catch unreachable;
                }
                if (attributes.name) |n| {
                    self.node.node.attributes.dynamic.values.put("name", .{ .String = n }) catch unreachable;
                }
                if (attributes.dynamic) |d| {
                    d.copy_into(&self.node.node.attributes.dynamic);
                }
            }

            pub fn get_edge_attributes(self: @This()) EdgeCreationAttributes {
                const directional = self.node.node.attributes.dynamic.values.get("directional");
                const name = self.node.node.attributes.dynamic.values.get("name");
                var dynamic = graph.DynamicAttributes.init(self.node.g.allocator);

                var it = self.node.node.attributes.dynamic.values.iterator();
                while (it.next()) |e| {
                    const key = e.key_ptr.*;
                    if (std.mem.eql(u8, key, "edge_type") or std.mem.eql(u8, key, "directional") or std.mem.eql(u8, key, "name")) {
                        continue;
                    }
                    dynamic.values.put(key, e.value_ptr.*) catch unreachable;
                }

                const attributes: EdgeCreationAttributes = .{
                    .edge_type = self.node.node.attributes.dynamic.values.get("edge_type").?.Int,
                    .directional = if (directional) |d| d.Bool else null,
                    .name = if (name) |n| n.String else null,
                    .dynamic = if (dynamic.values.count() > 0) dynamic else null,
                };
                return attributes;
            }
        };
    };

    const initialized_identifier = "initialized";

    fn get_initialized(self: *const @This()) bool {
        return self.self_node.node.attributes.dynamic.values.get(initialized_identifier).?.Bool;
    }

    fn set_initialized(self: *@This(), initialized: bool) void {
        self.self_node.node.attributes.put(initialized_identifier, .{ .Bool = initialized });
    }

    // TODO make cache for all these
    fn get_Reference(self: *const @This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "Reference").?;
    }

    fn get_TypeReference(self: *@This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "TypeReference").?;
    }

    fn get_MakeChild(self: *const @This()) BoundNodeReference {
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
        const type_node = TypeNode.create_and_insert(self, identifier);

        // Add type trait
        const trait_implements_type_instance = try self.instantiate_node(self.get_ImplementsType());
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

    pub fn add_make_child(
        self: *@This(),
        target_type: BoundNodeReference,
        child_type_identifier: str,
        identifier: ?str,
        node_attributes: ?*NodeCreationAttributes,
        mount_reference: ?BoundNodeReference,
    ) !BoundNodeReference {
        const make_child = try self.instantiate_node(self.get_MakeChild());
        MakeChildNode.Attributes.of(make_child).set_child_identifier(identifier);
        if (node_attributes) |_node_attributes| {
            MakeChildNode.Attributes.of(make_child).set_node_attributes(_node_attributes.*);
            if (_node_attributes.dynamic) |*d| {
                d.*.deinit();
            }
        }

        const type_reference = try TypeReferenceNode.create_and_insert(self, child_type_identifier);
        _ = EdgeComposition.add_child(make_child, type_reference.node, "type_ref");
        if (mount_reference) |_mount_reference| {
            _ = EdgeComposition.add_child(make_child, _mount_reference.node, "mount");
        }
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
        var attrs = edge_attributes;

        const make_link = try self.instantiate_node(self.get_MakeLink());
        MakeLinkNode.Attributes.of(make_link).set_edge_attributes(attrs);

        // Cleanup dynamic attributes after copying (like add_make_child does)
        if (attrs.dynamic) |*d| {
            d.deinit();
        }

        _ = EdgeComposition.add_child(make_link, lhs_reference.node, "lhs");
        _ = EdgeComposition.add_child(make_link, rhs_reference.node, "rhs");
        _ = EdgeComposition.add_child(target_type, make_link.node, null);

        return make_link;
    }

    fn find_make_child_node(
        self: *@This(),
        type_node: BoundNodeReference,
        identifier: []const u8,
    ) error{ ChildNotFound, OutOfMemory }!BoundNodeReference {
        const FindCtx = struct {
            target: []const u8,

            pub fn visit(
                self_ptr: *anyopaque,
                edge: graph.BoundEdgeReference,
            ) visitor.VisitResult(BoundNodeReference) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));
                const make_child = edge.g.bind(EdgeComposition.get_child_node(edge.edge));
                const child_identifier = MakeChildNode.Attributes.of(make_child).get_child_identifier() orelse {
                    return visitor.VisitResult(BoundNodeReference){ .CONTINUE = {} };
                };

                if (std.mem.eql(u8, child_identifier, ctx.target)) {
                    return visitor.VisitResult(BoundNodeReference){ .OK = make_child };
                }

                return visitor.VisitResult(BoundNodeReference){ .CONTINUE = {} };
            }
        };

        var ctx = FindCtx{ .target = identifier };
        const visit_result = EdgeComposition.visit_children_of_type(
            type_node,
            self.get_MakeChild().node,
            BoundNodeReference,
            &ctx,
            FindCtx.visit,
        );

        switch (visit_result) {
            .OK => |make_child| return make_child,
            .ERROR => |err| switch (err) {
                error.OutOfMemory => return error.OutOfMemory,
                else => unreachable,
            },
            else => return error.ChildNotFound,
        }
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
    ) error{ ChildNotFound, OutOfMemory }!BoundNodeReference {
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

                if (MakeChildNode.get_mount_reference(make_child)) |mount_reference| {
                    if (ctx.type_graph.reference_matches_path(mount_reference, ctx.parent_path)) {
                        return visitor.VisitResult(BoundNodeReference){ .OK = make_child };
                    }
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
                error.OutOfMemory => return error.OutOfMemory,
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
    fn resolve_path_segments(
        self: *@This(),
        type_node: BoundNodeReference,
        path: []const []const u8,
        failure: ?*?PathResolutionFailure,
    ) error{ ChildNotFound, OutOfMemory, UnresolvedTypeReference }!ResolveResult {
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
            make_child = self.find_make_child_node(current_type, segment) catch |err| switch (err) {
                error.ChildNotFound => blk: {
                    const parent_path = path[0..idx];
                    break :blk self.find_make_child_node_with_mount(
                        type_node,
                        segment,
                        parent_path,
                    ) catch |fallback_err| switch (fallback_err) {
                        error.ChildNotFound => {
                            if (failure) |f| {
                                const is_index = segment.len > 0 and ascii.isDigit(segment[0]);
                                f.* = PathResolutionFailure{
                                    .kind = if (is_index and parent_path.len > 0)
                                        PathErrorKind.invalid_index
                                    else
                                        PathErrorKind.missing_child,
                                    .failing_segment_index = idx,
                                    .failing_segment = segment,
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

            const child_type = MakeChildNode.get_child_type(make_child) orelse {
                if (failure) |f| {
                    f.* = PathResolutionFailure{
                        .kind = PathErrorKind.missing_child,
                        .failing_segment_index = idx,
                        .failing_segment = segment,
                        .has_index_value = false,
                    };
                }
                return error.UnresolvedTypeReference;
            };

            current_type = child_type;
        }

        return ResolveResult{ .last_make_child = make_child, .last_child_type = current_type };
    }

    /// Resolve `path` and return the child type node. Pointer-sequence indices
    /// are matched via mount references so callers do not need to duplicate the
    /// pointer semantics on the Python side.
    pub fn resolve_child_type(
        self: *@This(),
        type_node: BoundNodeReference,
        path: []const []const u8,
    ) !BoundNodeReference {
        const result = try self.resolve_path_segments(type_node, path, null);
        return result.last_child_type;
    }

    /// Create or fetch a child reference for `path`, validating via the
    /// mount-aware resolver when requested. This is the public entry point used
    /// by the Python visitor; callers never iterate MakeChild nodes manually.
    pub fn ensure_child_reference(
        self: *@This(),
        type_node: BoundNodeReference,
        path: []const str,
        validate: bool,
    ) !BoundNodeReference {
        return self.ensure_path_reference_mountaware(type_node, path, validate, null);
    }

    /// As above but accepts a slice of `[]const []const u8` so the caller can
    /// pass the exact segments used by `resolve_path_segments` without copying.
    pub fn ensure_path_reference_mountaware(
        self: *@This(),
        type_node: BoundNodeReference,
        path: []const []const u8,
        validate: bool,
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

        var local_failure: ?PathResolutionFailure = null;
        if (validate) {
            _ = self.resolve_path_segments(type_node, path, &local_failure) catch {
                if (failure) |f| f.* = local_failure;
                return error.ChildNotFound;
            };
        }

        const str_path: []const str = path;
        return ChildReferenceNode.create_and_insert(self, str_path) catch |err| switch (err) {
            error.ChildNotFound => {
                if (failure) |f| f.* = local_failure;
                return err;
            },
            else => return err,
        };
    }

    /// Resolve the make-child that represents `container_path[index]` in a
    /// pointer sequence. This ensures the AST visitor does not need to search
    /// through MakeChild nodes or replicate mount matching.
    pub fn resolve_pointer_member(
        self: *@This(),
        type_node: BoundNodeReference,
        container_path: []const []const u8,
        index: usize,
        failure: ?*?PathResolutionFailure,
    ) error{ ChildNotFound, OutOfMemory, UnresolvedTypeReference }!BoundNodeReference {
        var local_failure: ?PathResolutionFailure = null;
        const container_result = self.resolve_path_segments(type_node, container_path, &local_failure) catch |err| switch (err) {
            error.ChildNotFound => {
                if (failure) |f| f.* = local_failure;
                return error.ChildNotFound;
            },
            else => return err,
        };
        _ = container_result;

        var buf: [32]u8 = undefined;
        const identifier = std.fmt.bufPrint(&buf, "{d}", .{index}) catch {
            return error.OutOfMemory;
        };

        return self.find_make_child_node_with_mount(
            type_node,
            identifier,
            container_path,
        ) catch |err| switch (err) {
            error.ChildNotFound => {
                if (failure) |f| {
                    f.* = PathResolutionFailure{
                        .kind = PathErrorKind.invalid_index,
                        .failing_segment_index = container_path.len,
                        .failing_segment = &.{},
                        .has_index_value = true,
                        .index_value = index,
                    };
                }
                return err;
            },
            else => return err,
        };
    }

    /// Return every MakeChild belonging to `type_node` without filtering or
    /// reordering. Python tests consume this instead of manually walking
    /// EdgeComposition edges so Zig stays the single source of truth for which
    /// children exist.
    pub fn iter_make_children(
        self: *@This(),
        allocator: std.mem.Allocator,
        type_node: BoundNodeReference,
    ) error{OutOfMemory}![]MakeChildInfo {
        var list = std.ArrayList(MakeChildInfo).init(allocator);
        errdefer list.deinit();

        const Ctx = struct {
            list: *std.ArrayList(MakeChildInfo),
        };

        var ctx = Ctx{ .list = &list };

        const result = EdgeComposition.visit_children_of_type(
            type_node,
            self.get_MakeChild().node,
            void,
            &ctx,
            struct {
                pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                    const ctx_ptr: *Ctx = @ptrCast(@alignCast(self_ptr));
                    const make_child = edge.g.bind(EdgeComposition.get_child_node(edge.edge));
                    const identifier = MakeChildNode.Attributes.of(make_child).get_child_identifier();
                    ctx_ptr.list.append(MakeChildInfo{
                        .identifier = identifier,
                        .make_child = make_child,
                    }) catch return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            }.visit,
        );

        switch (result) {
            .ERROR => return error.OutOfMemory,
            else => {},
        }

        return list.toOwnedSlice();
    }

    /// Enumerate MakeLink nodes attached to `type_node`. Tests use this to
    /// inspect user-visible connections without reimplementing traversal
    /// against EdgeComposition directly.
    pub fn iter_make_links(
        self: *@This(),
        allocator: std.mem.Allocator,
        type_node: BoundNodeReference,
    ) error{OutOfMemory}![]BoundNodeReference {
        var list = std.ArrayList(BoundNodeReference).init(allocator);
        errdefer list.deinit();

        const VisitCtx = struct {
            list: *std.ArrayList(BoundNodeReference),
        };

        var ctx = VisitCtx{ .list = &list };

        const result = EdgeComposition.visit_children_of_type(
            type_node,
            self.get_MakeLink().node,
            void,
            &ctx,
            struct {
                pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                    const ctx_ptr: *VisitCtx = @ptrCast(@alignCast(self_ptr));
                    const make_link = edge.g.bind(EdgeComposition.get_child_node(edge.edge));
                    ctx_ptr.list.append(make_link) catch return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            }.visit,
        );

        switch (result) {
            .ERROR => return error.OutOfMemory,
            else => {},
        }

        return list.toOwnedSlice();
    }

    /// Walk a Reference chain and return the individual identifiers. Reference
    /// nodes are linked together via EdgeNext; higher layers should not need to
    /// reason about the internals of that representation.
    pub fn get_reference_path(
        self: *@This(),
        allocator: std.mem.Allocator,
        reference: BoundNodeReference,
    ) error{ OutOfMemory, InvalidReference }![]const []const u8 {
        _ = self;

        var segments = std.ArrayList([]const u8).init(allocator);
        errdefer segments.deinit();

        var current = reference;
        while (true) {
            const identifier = ChildReferenceNode.Attributes.of(current.node).get_child_identifier();
            if (identifier.len == 0) {
                return error.InvalidReference;
            }
            try segments.append(identifier);

            const next_node = EdgeNext.get_next_node_from_node(current);
            if (next_node) |_next| {
                current = reference.g.bind(_next);
            } else {
                break;
            }
        }

        if (segments.items.len == 0) {
            return error.InvalidReference;
        }

        return segments.toOwnedSlice();
    }

    fn free_link_paths(allocator: std.mem.Allocator, info: MakeLinkInfo) void {
        allocator.free(info.lhs_path);
        allocator.free(info.rhs_path);
    }

    /// Enumerate MakeLink nodes together with their resolved reference paths so
    /// callers do not need to expand the `lhs`/`rhs` chains manually.
    pub fn iter_make_links_detailed(
        self: *@This(),
        allocator: std.mem.Allocator,
        type_node: BoundNodeReference,
    ) error{ OutOfMemory, InvalidReference }![]MakeLinkInfo {
        var list = std.ArrayList(MakeLinkInfo).init(allocator);
        errdefer {
            for (list.items) |info| {
                free_link_paths(allocator, info);
            }
            list.deinit();
        }

        const VisitCtx = struct {
            type_graph: *TypeGraph,
            allocator: std.mem.Allocator,
            list: *std.ArrayList(MakeLinkInfo),
        };

        var ctx = VisitCtx{
            .type_graph = self,
            .allocator = allocator,
            .list = &list,
        };

        const visit_result = EdgeComposition.visit_children_of_type(
            type_node,
            self.get_MakeLink().node,
            void,
            &ctx,
            struct {
                pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                    const ctx_ptr: *VisitCtx = @ptrCast(@alignCast(self_ptr));
                    const make_link = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                    const lhs_ref = EdgeComposition.get_child_by_identifier(make_link, "lhs");
                    const rhs_ref = EdgeComposition.get_child_by_identifier(make_link, "rhs");
                    if (lhs_ref == null or rhs_ref == null) {
                        return visitor.VisitResult(void){ .CONTINUE = {} };
                    }

                    const lhs_path = ctx_ptr.type_graph.get_reference_path(ctx_ptr.allocator, lhs_ref.?) catch |err| {
                        return visitor.VisitResult(void){ .ERROR = err };
                    };
                    var lhs_keep = true;
                    defer if (lhs_keep) ctx_ptr.allocator.free(lhs_path);

                    const rhs_path = ctx_ptr.type_graph.get_reference_path(ctx_ptr.allocator, rhs_ref.?) catch |err| {
                        if (lhs_keep) ctx_ptr.allocator.free(lhs_path);
                        return visitor.VisitResult(void){ .ERROR = err };
                    };
                    var rhs_keep = true;
                    defer if (rhs_keep) ctx_ptr.allocator.free(rhs_path);

                    ctx_ptr.list.append(MakeLinkInfo{
                        .make_link = make_link,
                        .lhs_path = lhs_path,
                        .rhs_path = rhs_path,
                    }) catch |append_err| {
                        return visitor.VisitResult(void){ .ERROR = append_err };
                    };

                    lhs_keep = false;
                    rhs_keep = false;
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            }.visit,
        );

        switch (visit_result) {
            .ERROR => |err| switch (err) {
                error.OutOfMemory => return error.OutOfMemory,
                error.InvalidReference => return error.InvalidReference,
                else => unreachable,
            },
            else => {},
        }

        return list.toOwnedSlice();
    }

    /// Enumerate pointer-sequence elements mounted under `container_path`. This
    /// keeps mount-matching inside the TypeGraph so higher layers can treat
    /// pointer sequences like ordinary lists of children.
    pub fn iter_pointer_members(
        self: *@This(),
        allocator: std.mem.Allocator,
        type_node: BoundNodeReference,
        container_path: []const []const u8,
        failure: ?*?PathResolutionFailure,
    ) error{ OutOfMemory, UnresolvedTypeReference, ChildNotFound }![]MakeChildInfo {
        var local_failure: ?PathResolutionFailure = null;
        _ = self.resolve_path_segments(type_node, container_path, &local_failure) catch |err| switch (err) {
            error.ChildNotFound => {
                if (failure) |f| f.* = local_failure;
                return err;
            },
            error.UnresolvedTypeReference => {},
            else => return err,
        };

        var list = std.ArrayList(MakeChildInfo).init(allocator);
        errdefer list.deinit();

        const VisitCtx = struct {
            type_graph: *TypeGraph,
            container_path: []const []const u8,
            list: *std.ArrayList(MakeChildInfo),
        };

        var ctx = VisitCtx{
            .type_graph = self,
            .container_path = container_path,
            .list = &list,
        };

        const visit_result = EdgeComposition.visit_children_of_type(
            type_node,
            self.get_MakeChild().node,
            void,
            &ctx,
            struct {
                pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                    const ctx_ptr: *VisitCtx = @ptrCast(@alignCast(self_ptr));
                    const make_child = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                    const identifier = MakeChildNode.Attributes.of(make_child).get_child_identifier() orelse {
                        return visitor.VisitResult(void){ .CONTINUE = {} };
                    };

                    if (MakeChildNode.get_mount_reference(make_child)) |mount_reference| {
                        if (!ctx_ptr.type_graph.reference_matches_path(mount_reference, ctx_ptr.container_path)) {
                            return visitor.VisitResult(void){ .CONTINUE = {} };
                        }

                        ctx_ptr.list.append(MakeChildInfo{
                            .identifier = identifier,
                            .make_child = make_child,
                        }) catch |append_err| {
                            return visitor.VisitResult(void){ .ERROR = append_err };
                        };
                    }

                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            }.visit,
        );

        switch (visit_result) {
            .ERROR => |err| switch (err) {
                error.OutOfMemory => return error.OutOfMemory,
                else => unreachable,
            },
            else => {},
        }

        return list.toOwnedSlice();
    }

    /// Return the mount-reference chain for `make_child` as ordered child
    /// identifiers. Pointer-sequence elements mount under their container and
    /// nested make-children mount under the parent they attach to, so this is
    /// the canonical way to recover "mounts" for debugging and tests.
    pub fn get_mount_chain(
        self: *@This(),
        allocator: std.mem.Allocator,
        make_child: BoundNodeReference,
    ) error{OutOfMemory}![]const []const u8 {
        _ = self;
        var chain = std.ArrayList([]const u8).init(allocator);
        errdefer chain.deinit();

        if (MakeChildNode.get_mount_reference(make_child)) |mount_ref| {
            var current = mount_ref;
            while (true) {
                const identifier = ChildReferenceNode.Attributes.of(current.node).get_child_identifier();
                try chain.append(identifier);

                const next_node = EdgeNext.get_next_node_from_node(current);
                if (next_node) |_next| {
                    current = current.g.bind(_next);
                } else {
                    break;
                }
            }

            if (chain.items.len > 0) {
                if (MakeChildNode.Attributes.of(make_child).get_child_identifier()) |leaf_identifier| {
                    var is_numeric = leaf_identifier.len > 0;
                    var i: usize = 0;
                    while (i < leaf_identifier.len) : (i += 1) {
                        if (!ascii.isDigit(leaf_identifier[i])) {
                            is_numeric = false;
                            break;
                        }
                    }

                    if (!is_numeric) {
                        try chain.append(leaf_identifier);
                    }
                }
            }
        }

        return chain.toOwnedSlice();
    }

    pub fn instantiate_node(tg: *@This(), type_node: BoundNodeReference) !graph.BoundNodeReference {
        // 1) Create instance and connect it to its type
        const new_instance = type_node.g.insert_node(Node.init(type_node.g.allocator));
        _ = EdgeType.add_instance(type_node, new_instance);

        // 2) Visit MakeChild nodes of type_node
        const VisitMakeChildren = struct {
            type_graph: *TypeGraph,
            parent_instance: graph.BoundNodeReference,

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));

                const make_child = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                // 2.1) Resolve child instructions (identifier and type)
                const child_identifier = MakeChildNode.Attributes.of(make_child).get_child_identifier();
                const referenced_type = MakeChildNode.get_child_type(make_child) orelse {
                    return visitor.VisitResult(void){ .ERROR = error.UnresolvedTypeReference };
                };

                var attachment_parent = self.parent_instance;
                if (MakeChildNode.get_mount_reference(make_child)) |mount_reference| {
                    attachment_parent = ChildReferenceNode.resolve(mount_reference, attachment_parent) orelse {
                        return visitor.VisitResult(void){ .ERROR = error.UnresolvedMountReference };
                    };
                }

                // 2.2) Instantiate child
                const child = self.type_graph.instantiate_node(referenced_type) catch |e| {
                    return visitor.VisitResult(void){ .ERROR = e };
                };

                // 2.3) Attach child instance to parent instance with the reference name
                _ = EdgeComposition.add_child(attachment_parent, child.node, child_identifier);

                // 2.4) Copy node attributes from MakeChild node to child instance
                var node_attributes = MakeChildNode.Attributes.of(make_child).get_node_attributes();
                if (node_attributes.dynamic) |d| {
                    d.copy_into(&child.node.attributes.dynamic);
                    node_attributes.dynamic.?.deinit();
                }

                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var make_child_visitor = VisitMakeChildren{
            .type_graph = tg,
            .parent_instance = new_instance,
        };
        _ = EdgeComposition.visit_children_of_type(type_node, tg.get_MakeChild().node, void, &make_child_visitor, VisitMakeChildren.visit);

        // 3) Visit MakeLink nodes of type_node
        const VisitMakeLinks = struct {
            type_graph: *TypeGraph,
            parent_instance: graph.BoundNodeReference,

            pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const self: *@This() = @ptrCast(@alignCast(self_ptr));

                const make_link = edge.g.bind(EdgeComposition.get_child_node(edge.edge));

                // 3.1) Get operand references (lhs and rhs)
                const lhs_reference_node = EdgeComposition.get_child_by_identifier(make_link, "lhs");
                const rhs_reference_node = EdgeComposition.get_child_by_identifier(make_link, "rhs");

                if (lhs_reference_node == null or rhs_reference_node == null) {
                    // TODO: proper error handling - missing operand references
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }

                // 3.2) Resolve operand references to actual instance nodes
                const lhs_resolved = ChildReferenceNode.resolve(lhs_reference_node.?, self.parent_instance).?;
                const rhs_resolved = ChildReferenceNode.resolve(rhs_reference_node.?, self.parent_instance).?;

                // 3.3) Create link between resolved nodes
                const edge_attributes = MakeLinkNode.Attributes.of(make_link).get_edge_attributes();

                // Use the appropriate edge creation function based on link_type
                const link_edge = Edge.init(self.parent_instance.g.allocator, lhs_resolved.node, rhs_resolved.node, edge_attributes.edge_type);
                link_edge.attributes.directional = edge_attributes.directional;
                link_edge.attributes.name = edge_attributes.name;
                if (edge_attributes.dynamic) |d| {
                    d.copy_into(&link_edge.attributes.dynamic);
                }

                _ = self.parent_instance.g.insert_edge(link_edge);

                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        // Only visit make_link children if TypeGraph is fully initialized
        // This avoids circular dependency during TypeGraph initialization
        if (tg.get_initialized()) {
            var make_link_visitor = VisitMakeLinks{
                .type_graph = tg,
                .parent_instance = new_instance,
            };
            const make_link_result = EdgeComposition.visit_children_of_type(type_node, tg.get_MakeLink().node, void, &make_link_visitor, VisitMakeLinks.visit);
            switch (make_link_result) {
                .ERROR => |err| return err,
                else => {},
            }
        }

        return new_instance;
    }

    pub fn get_type_by_name(self: *const @This(), type_identifier: str) ?BoundNodeReference {
        // TODO make trait.zig
        return EdgeComposition.get_child_by_identifier(self.self_node, type_identifier);
    }

    pub fn instantiate(self: *@This(), type_identifier: str) !BoundNodeReference {
        const parent_type_node = self.get_type_by_name(type_identifier) orelse {
            return error.InvalidArgument;
        };
        return try self.instantiate_node(parent_type_node);
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

    pub fn get_type_instance_overview(self: *const @This(), allocator: std.mem.Allocator) std.ArrayList(TypeInstanceCount) {
        var result = std.ArrayList(TypeInstanceCount).init(allocator);

        // Visit all children of self_node (these are type nodes)
        const Counter = struct {
            counts: *std.ArrayList(TypeInstanceCount),

            pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(self_ptr));
                const type_node = bound_edge.g.bind(EdgeComposition.get_child_node(bound_edge.edge));

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
        _ = EdgeComposition.visit_children_edges(self.self_node, void, &counter, Counter.visit);

        return result;
    }

    pub fn get_type_subgraph(self: *@This()) GraphView {
        return get_subgraph_of_node(self.self_node.g.allocator, self.self_node);
    }

    fn _get_bootstrapped_nodes(self: *const @This(), allocator: std.mem.Allocator) std.ArrayList(NodeReference) {
        var result = std.ArrayList(NodeReference).init(allocator);

        result.append(self.get_ImplementsTrait().node) catch @panic("OOM");
        result.append(self.get_ImplementsType().node) catch @panic("OOM");
        result.append(self.get_MakeChild().node) catch @panic("OOM");
        result.append(self.get_MakeLink().node) catch @panic("OOM");
        result.append(self.get_Reference().node) catch @panic("OOM");
        return result;
    }

    pub fn get_subgraph_of_node(allocator: std.mem.Allocator, start_node: BoundNodeReference) GraphView {
        const g = start_node.g;

        var collected_nodes = std.ArrayList(NodeReference).init(allocator);
        defer collected_nodes.deinit();

        // Use a set to track visited nodes
        var visited = graph.NodeRefMap.T(void).init(allocator);
        defer visited.deinit();

        var dont_visit = graph.NodeRefMap.T(void).init(allocator);
        defer dont_visit.deinit();

        // Helper struct with functions to collect nodes
        const Collector = struct {
            nodes: *std.ArrayList(NodeReference),
            visited_set: *graph.NodeRefMap.T(void),
            dont_visit: *graph.NodeRefMap.T(void),

            fn try_add(ctx: *@This(), node: NodeReference) bool {
                if (!ctx.visited_set.contains(node)) {
                    ctx.visited_set.put(node, {}) catch @panic("OOM");
                    ctx.nodes.append(node) catch @panic("OOM");
                    return true;
                }
                return false;
            }

            fn skip_visit(ctx: *@This(), node: NodeReference) void {
                ctx.dont_visit.put(node, {}) catch @panic("OOM");
            }

            // Visitor for EdgeComposition children
            fn visit_composition(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const child = EdgeComposition.get_child_node(bound_edge.edge);
                _ = ctx.try_add(child);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            // Visitor for EdgePointer references
            fn visit_pointer(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                if (EdgePointer.get_referenced_node(bound_edge.edge)) |target| {
                    _ = ctx.try_add(target);
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            // Visitor for EdgeTrait instances
            fn visit_trait(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const trait_instance = EdgeTrait.get_trait_instance_node(bound_edge.edge);
                _ = ctx.try_add(trait_instance);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var collector = Collector{
            .nodes = &collected_nodes,
            .visited_set = &visited,
            .dont_visit = &dont_visit,
        };

        // Start with self_node
        _ = collector.try_add(start_node.node);

        // Process all nodes (queue-style BFS iteration over collected nodes)
        var i: usize = 0;
        while (i < collected_nodes.items.len) : (i += 1) {
            const current = collected_nodes.items[i];
            if (collector.dont_visit.contains(current)) {
                continue;
            }
            const bound_current = g.bind(current);

            // Follow type
            if (EdgeType.get_type_edge(bound_current)) |type_edge| {
                const type_node = EdgeType.get_type_node(type_edge.edge);
                _ = collector.try_add(type_node);

                // Add typegraph core nodes
                const tg = TypeGraph.of_type(g.bind(type_node)).?;
                if (collector.try_add(tg.self_node.node)) {
                    collector.skip_visit(tg.self_node.node);
                    const tg_bootstrap_nodes = tg._get_bootstrapped_nodes(g.allocator);
                    defer tg_bootstrap_nodes.deinit();
                    for (tg_bootstrap_nodes.items) |node| {
                        _ = collector.try_add(node);
                    }
                }
            }

            // Follow children
            _ = EdgeComposition.visit_children_edges(bound_current, void, &collector, Collector.visit_composition);

            // Follow point targets
            _ = EdgePointer.visit_pointed_edges(bound_current, void, &collector, Collector.visit_pointer);

            // Follow to next items in list
            if (EdgeNext.get_next_node_from_node(bound_current)) |next_node| {
                _ = collector.try_add(next_node);
            }

            // Follow owned traits
            _ = EdgeTrait.visit_trait_instance_edges(bound_current, void, &collector, Collector.visit_trait);
        }

        return g.get_subgraph_from_nodes(collected_nodes);
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

//zig test --dep graph -Mroot=src/faebryk/typegraph.zig -Mgraph=src/graph/lib.zig
test "basic instantiation" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();
    var tg = TypeGraph.init(&g);

    // Build type graph
    const Electrical = try tg.add_type("Electrical");
    const Capacitor = try tg.add_type("Capacitor");
    const capacitor_p1 = try tg.add_make_child(Capacitor, "Electrical", "p1", null, null);
    const capacitor_p2 = try tg.add_make_child(Capacitor, "Electrical", "p2", null, null);
    const Resistor = try tg.add_type("Resistor");
    const res_p1_makechild = try tg.add_make_child(Resistor, Electrical, "p1", null);
    std.debug.print("RES_P1_MAKECHILD: {s}\n", .{try EdgeComposition.get_name(EdgeComposition.get_parent_edge(res_p1_makechild).?.edge)});
    _ = try tg.add_make_child(Resistor, Electrical, "p2", null);
    _ = try tg.add_make_child(Resistor, Capacitor, "cap1", null);

    var node_attrs = TypeGraph.MakeChildNode.build(a, "test_string");
    const capacitor_tp = try tg.add_make_child(
        Capacitor,
        "Electrical",
        "tp",
        &node_attrs,
        null,
    );

    try Linker.link_type_reference(&g, TypeGraph.MakeChildNode.get_type_reference(capacitor_p1).?, Electrical);
    try Linker.link_type_reference(&g, TypeGraph.MakeChildNode.get_type_reference(capacitor_p2).?, Electrical);
    try Linker.link_type_reference(&g, TypeGraph.MakeChildNode.get_type_reference(capacitor_tp).?, Electrical);
    try Linker.link_type_reference(&g, TypeGraph.MakeChildNode.get_type_reference(res_p1_makechild).?, Electrical);

    // Build instance graph
    const resistor = try tg.instantiate_node(Resistor);

    // test: instance graph
    std.debug.print("Resistor Instance: {d}\n", .{resistor.node.attributes.uuid});
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

    // print children of resistor
    var resistor_children = std.ArrayList(graph.BoundEdgeReference).init(a);
    defer resistor_children.deinit();
    const resistor_visit_result = EdgeComposition.visit_children_edges(resistor, void, &resistor_children, visitor.collect(graph.BoundEdgeReference).collect_into_list);
    switch (resistor_visit_result) {
        .ERROR => |err| @panic(@errorName(err)),
        else => {},
    }
    std.debug.print("TYPE collected children: {d}\n", .{resistor_children.items.len});

    // Build nested reference
    const cap1p1_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ "cap1", "p1" });
    const cap1p2_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ "cap1", "p2" });

    // test: resolve_instance_reference
    const cap1p1_reference_resolved = TypeGraph.ChildReferenceNode.resolve(cap1p1_reference, resistor).?;
    try std.testing.expect(Node.is_same(cap1p1_reference_resolved.node, cap1p1.node));

    // Build make link
    // TODO: use interface link
    _ = try tg.add_make_link(Resistor, cap1p1_reference, cap1p2_reference, .{
        .edge_type = EdgePointer.tid,
        .directional = true,
        .name = null,
        .dynamic = graph.DynamicAttributes.init(a),
    });

    const instantiated_resistor = try tg.instantiate("Resistor");
    const instantiated_p1 = EdgeComposition.get_child_by_identifier(instantiated_resistor, "p1").?;
    const instantiated_cap = EdgeComposition.get_child_by_identifier(instantiated_resistor, "cap1").?;
    const instantiated_cap_p1 = EdgeComposition.get_child_by_identifier(instantiated_cap, "p1").?;
    const instantiated_cap_p2 = EdgeComposition.get_child_by_identifier(instantiated_cap, "p2").?;
    std.debug.print("Instantiated Resistor Instance: {d}\n", .{instantiated_resistor.node.attributes.uuid});
    std.debug.print("Instantiated P1 Instance: {d}\n", .{instantiated_p1.node.attributes.uuid});

    const cref = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ "<<Resistor", "p1" });
    const result_node = TypeGraph.ChildReferenceNode.resolve(cref, cref);
    std.debug.print("result node: {d}\n", .{result_node.?.node.attributes.uuid});

    // test: check edge created
    const _EdgeVisitor = struct {
        seek: BoundNodeReference,

        pub fn visit(self_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const self: *@This() = @ptrCast(@alignCast(self_ptr));
            std.testing.expect(EdgePointer.is_instance(bound_edge.edge)) catch return visitor.VisitResult(void){ .ERROR = error.InvalidArgument };
            if (EdgePointer.get_referenced_node(bound_edge.edge)) |referenced_node| {
                if (Node.is_same(referenced_node, self.seek.node)) {
                    return visitor.VisitResult(void){ .OK = {} };
                }
            }
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };
    var _visit = _EdgeVisitor{ .seek = instantiated_cap_p2 };
    const result = instantiated_cap_p1.visit_edges_of_type(EdgePointer.tid, void, &_visit, _EdgeVisitor.visit, null);
    try std.testing.expect(result == .OK);
}

test "typegraph iterators and mount chains" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    defer g.deinit();
    var tg = TypeGraph.init(&g);

    const top = try tg.add_type("Top");
    _ = try tg.add_type("Inner");
    _ = try tg.add_type("PointerSequence");

    const members = try tg.add_make_child(top, "PointerSequence", "members", null, null);
    const base = try tg.add_make_child(top, "Inner", "base", null, null);
    _ = base;

    const base_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{"base"});
    const extra = try tg.add_make_child(top, "Inner", "extra", null, base_reference);

    const container_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{"members"});
    const element0 = try tg.add_make_child(top, "Inner", "0", null, container_reference);
    const element1 = try tg.add_make_child(top, "Inner", "1", null, container_reference);
    _ = element1;

    const extra_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{"extra"});

    const link_attrs = EdgeCreationAttributes{
        .edge_type = EdgePointer.tid,
        .directional = true,
        .name = null,
        .dynamic = null,
    };
    _ = try tg.add_make_link(top, base_reference, extra_reference, link_attrs);

    const children = try tg.iter_make_children(a, top);
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

    const links = try tg.iter_make_links(a, top);
    defer a.free(links);
    try std.testing.expectEqual(@as(usize, 1), links.len);

    const lhs = EdgeComposition.get_child_by_identifier(links[0], "lhs").?;
    const rhs = EdgeComposition.get_child_by_identifier(links[0], "rhs").?;
    try std.testing.expect(Node.is_same(lhs.node, base_reference.node));
    try std.testing.expect(Node.is_same(rhs.node, extra_reference.node));

    const detailed_links = try tg.iter_make_links_detailed(a, top);
    defer {
        for (detailed_links) |info| {
            a.free(info.lhs_path);
            a.free(info.rhs_path);
        }
        a.free(detailed_links);
    }
    try std.testing.expectEqual(@as(usize, 1), detailed_links.len);
    try std.testing.expect(Node.is_same(detailed_links[0].make_link.node, links[0].node));
    try std.testing.expectEqual(@as(usize, 1), detailed_links[0].lhs_path.len);
    try std.testing.expectEqualStrings("base", detailed_links[0].lhs_path[0]);
    try std.testing.expectEqual(@as(usize, 1), detailed_links[0].rhs_path.len);
    try std.testing.expectEqualStrings("extra", detailed_links[0].rhs_path[0]);

    const lhs_path = try tg.get_reference_path(a, lhs);
    defer a.free(lhs_path);
    try std.testing.expectEqual(@as(usize, 1), lhs_path.len);
    try std.testing.expectEqualStrings("base", lhs_path[0]);

    const chain_members = try tg.get_mount_chain(a, members);
    defer a.free(chain_members);
    try std.testing.expectEqual(@as(usize, 0), chain_members.len);

    const chain_element0 = try tg.get_mount_chain(a, element0);
    defer a.free(chain_element0);
    try std.testing.expectEqual(@as(usize, 1), chain_element0.len);
    try std.testing.expect(std.mem.eql(u8, chain_element0[0], "members"));

    const chain_extra = try tg.get_mount_chain(a, extra);
    defer a.free(chain_extra);
    try std.testing.expectEqual(@as(usize, 2), chain_extra.len);
    try std.testing.expect(std.mem.eql(u8, chain_extra[0], "base"));
    try std.testing.expect(std.mem.eql(u8, chain_extra[1], "extra"));

    const pointer_members = try tg.iter_pointer_members(a, top, &.{"members"}, null);
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
    _ = try tg.add_make_child(Capacitor, Electrical, "p1", null);
    _ = try tg.add_make_child(Capacitor, Electrical, "p2", null);
    const Resistor = try tg.add_type("Resistor");
    _ = try tg.add_make_child(Resistor, Electrical, "p1", null);
    _ = try tg.add_make_child(Resistor, Electrical, "p2", null);

    // Create some instances
    _ = try tg.instantiate_node(Capacitor);
    _ = try tg.instantiate_node(Capacitor);
    _ = try tg.instantiate_node(Resistor);

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

//zig test --dep graph -Mroot=src/faebryk/typegraph.zig -Mgraph=src/graph/lib.zig
test "get_type_subgraph" {
    const a = std.testing.allocator;
    var g = graph.GraphView.init(a);
    var tg = TypeGraph.init(&g);

    // Build type graph
    const SomeTrait = try tg.add_type("SomeTrait");
    const implements_trait_instance = try tg.instantiate_node(tg.get_ImplementsTrait());
    _ = EdgeTrait.add_trait_instance(SomeTrait, implements_trait_instance.node);
    const Electrical = try tg.add_type("Electrical");
    _ = try tg.add_make_child(Electrical, SomeTrait, "trait", null);
    const trait_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{"trait"});
    const self_reference = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{""});
    _ = try tg.add_make_link(Electrical, trait_reference.node, self_reference.node, EdgeTrait.build());
    const Capacitor = try tg.add_type("Capacitor");
    _ = try tg.add_make_child(Capacitor, Electrical, "p1", null);
    _ = try tg.add_make_child(Capacitor, Electrical, "p2", null);

    // Create some instances (these should NOT be in the type subgraph)
    const capacitor_instance = try tg.instantiate_node(Capacitor);

    // Get the type subgraph
    var type_subgraph = tg.get_type_subgraph();
    defer type_subgraph.deinit();
    defer g.deinit();

    // Type subgraph should contain type nodes
    try std.testing.expect(type_subgraph.contains_node(tg.self_node.node));
    try std.testing.expect(type_subgraph.contains_node(Electrical.node));
    try std.testing.expect(type_subgraph.contains_node(Capacitor.node));

    const old_e_trait = EdgeComposition.get_child_by_identifier(Electrical, "trait");
    try std.testing.expect(old_e_trait != null);
    const e_trait = EdgeComposition.get_child_by_identifier(type_subgraph.bind(Electrical.node), "trait");
    try std.testing.expect(e_trait != null);
    try std.testing.expect(type_subgraph.contains_node(e_trait.?.node));

    try std.testing.expect(type_subgraph.contains_node(implements_trait_instance.node));

    // Type subgraph should NOT contain instance nodes
    try std.testing.expect(!type_subgraph.contains_node(capacitor_instance.node));
    const cap_p1 = EdgeComposition.get_child_by_identifier(capacitor_instance, "p1").?;
    const cap_p2 = EdgeComposition.get_child_by_identifier(capacitor_instance, "p2").?;
    try std.testing.expect(!type_subgraph.contains_node(cap_p1.node));
    try std.testing.expect(!type_subgraph.contains_node(cap_p2.node));

    // Print some stats for debugging
    const g_count = g.get_node_count();
    const type_subgraph_count = type_subgraph.get_node_count();
    std.debug.print("\nType subgraph node count: {d}\n", .{type_subgraph_count});
    std.debug.print("Full graph node count: {d}\n", .{g_count});

    // Nodes NOT in type subgraph:
    // - cap, p1, p2 (instance nodes)
    // - trait on p1, trait on p2
    try std.testing.expectEqual(5, g_count - type_subgraph_count);
}
