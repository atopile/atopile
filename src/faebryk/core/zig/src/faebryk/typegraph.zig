const graph_mod = @import("graph");
const std = @import("std");
const node_type_mod = @import("node_type.zig");
const composition_mod = @import("composition.zig");
const next_mod = @import("next.zig");
const pointer_mod = @import("pointer.zig");
const edgebuilder_mod = @import("edgebuilder.zig");
const nodebuilder_mod = @import("nodebuilder.zig");
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
const EdgeTrait = trait_mod.EdgeTrait;
const return_first = visitor.return_first;
// TODO: BoundNodeReference and NodeReference used mixed all over the place
// TODO: move add/create functions into respective structs

pub const TypeGraph = struct {
    self_node: BoundNodeReference,

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
        pub fn add_trait_to(target: BoundNodeReference, trait_type: BoundNodeReference) BoundNodeReference {
            const trait_instance = TypeNode.spawn_instance(trait_type);
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
            if (Attributes.of(node).get_child_identifier()) |identifier| {
                if (EdgePointer.get_pointed_node_by_identifier(node, identifier)) |child| {
                    return child;
                }
            }
            return EdgePointer.get_referenced_node_from_node(node);
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
    fn get_Reference(self: *@This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "Reference").?;
    }

    fn get_MakeChild(self: *const @This()) BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.self_node, "MakeChild").?;
    }

    fn get_MakeLink(self: *@This()) BoundNodeReference {
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
        _ = TraitNode.add_trait_to(implements_type_type, implements_type_type);
        _ = TraitNode.add_trait_to(implements_type_type, implements_trait_type);
        _ = TraitNode.add_trait_to(implements_trait_type, implements_type_type);
        _ = TraitNode.add_trait_to(implements_trait_type, implements_trait_type);

        const make_child_type = TypeNode.create_and_insert(&self, "MakeChild");

        _ = TraitNode.add_trait_to(make_child_type, implements_type_type);

        _ = TypeNode.create_and_insert(&self, "MakeLink");
        _ = TypeNode.create_and_insert(&self, "Reference");

        // Mark as fully initialized
        self.set_initialized(true);

        return self;
    }

    pub fn add_type(self: *@This(), identifier: str) !BoundNodeReference {
        const type_node = TypeNode.create_and_insert(self, identifier);

        // Add type trait
        const trait_implements_type_instance = try self.instantiate_node(self.get_ImplementsType());
        _ = EdgeTrait.add_trait_instance(type_node, trait_implements_type_instance.node);

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
        child_type: BoundNodeReference,
        identifier: ?str,
        node_attributes: ?*NodeCreationAttributes,
    ) !BoundNodeReference {
        const make_child = try self.instantiate_node(self.get_MakeChild());
        MakeChildNode.Attributes.of(make_child).set_child_identifier(identifier);
        if (node_attributes) |_node_attributes| {
            MakeChildNode.Attributes.of(make_child).set_node_attributes(_node_attributes.*);
            if (_node_attributes.dynamic) |*d| {
                d.*.deinit();
            }
        }

        _ = EdgePointer.point_to(make_child, child_type.node, identifier, null);
        _ = EdgeComposition.add_child(target_type, make_child.node, identifier);

        return make_child;
    }

    pub fn add_make_link(
        self: *@This(),
        target_type: BoundNodeReference,
        lhs_reference: NodeReference,
        rhs_reference: NodeReference,
        edge_attributes: EdgeCreationAttributes,
    ) !BoundNodeReference {
        var attrs = edge_attributes;

        const make_link = try self.instantiate_node(self.get_MakeLink());
        MakeLinkNode.Attributes.of(make_link).set_edge_attributes(attrs);

        // Cleanup dynamic attributes after copying (like add_make_child does)
        if (attrs.dynamic) |*d| {
            d.deinit();
        }

        _ = EdgeComposition.add_child(make_link, lhs_reference, "lhs");
        _ = EdgeComposition.add_child(make_link, rhs_reference, "rhs");
        _ = EdgeComposition.add_child(target_type, make_link.node, null);

        return make_link;
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
                const referenced_type = MakeChildNode.get_child_type(make_child);
                if (referenced_type == null) {
                    // TODO error?
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }

                // 2.2) Instantiate child
                const child = self.type_graph.instantiate_node(
                    referenced_type.?,
                ) catch |e| {
                    return visitor.VisitResult(void){ .ERROR = e };
                };

                // 2.3) Attach child instance to parent instance with the reference name
                _ = EdgeComposition.add_child(self.parent_instance, child.node, child_identifier);

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
        const FindTypeByName = struct {
            self: *const TypeGraph,
            type_identifier: str,

            pub fn visitTypeEdge(ctx_ptr: *anyopaque, type_edge: graph.BoundEdgeReference) visitor.VisitResult(NodeReference) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const edge = type_edge.edge;

                const implements_type_instance = ctx.self.get_g().bind(EdgeType.get_instance_node(edge).?);
                const owner_type_edge = EdgeTrait.get_owner_edge(implements_type_instance);
                const owner_type_node = EdgeTrait.get_owner_node(owner_type_edge.?.edge);
                const type_node_name = TypeNodeAttributes.of(owner_type_node).get_type_name();
                if (std.mem.eql(u8, type_node_name, ctx.type_identifier)) {
                    return visitor.VisitResult(NodeReference){ .OK = owner_type_node };
                }
                return visitor.VisitResult(NodeReference){ .CONTINUE = {} };
            }
        };

        var finder = FindTypeByName{ .self = self, .type_identifier = type_identifier };
        const result = self.get_ImplementsType().visit_edges_of_type(
            EdgeType.tid,
            NodeReference,
            &finder,
            FindTypeByName.visitTypeEdge,
            null,
        );
        switch (result) {
            .OK => |parent_type_node| {
                return self.get_g().bind(parent_type_node);
            },
            .ERROR => unreachable,
            .CONTINUE => unreachable,
            .STOP => unreachable,
            .EXHAUSTED => return null,
        }
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
        const allocator = self.self_node.g.allocator;
        var collected_nodes = std.ArrayList(NodeReference).init(allocator);
        defer collected_nodes.deinit();

        // Use a set to track visited nodes
        var visited = graph.NodeRefMap.T(void).init(allocator);
        defer visited.deinit();

        // Helper struct with functions to collect nodes
        const Collector = struct {
            nodes: *std.ArrayList(NodeReference),
            visited_set: *graph.NodeRefMap.T(void),

            fn try_add(ctx: *@This(), node: NodeReference) void {
                if (!ctx.visited_set.contains(node)) {
                    ctx.visited_set.put(node, {}) catch @panic("OOM");
                    ctx.nodes.append(node) catch @panic("OOM");
                }
            }

            // Visitor for EdgeComposition children
            fn visit_composition(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const child = EdgeComposition.get_child_node(bound_edge.edge);
                ctx.try_add(child);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            // Visitor for EdgePointer references
            fn visit_pointer(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                if (EdgePointer.get_referenced_node(bound_edge.edge)) |target| {
                    ctx.try_add(target);
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            // Visitor for EdgeTrait instances
            fn visit_trait(ctx_ptr: *anyopaque, bound_edge: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const trait_instance = EdgeTrait.get_trait_instance_node(bound_edge.edge);
                ctx.try_add(trait_instance);
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var collector = Collector{
            .nodes = &collected_nodes,
            .visited_set = &visited,
        };

        // Start with self_node
        collector.try_add(self.self_node.node);

        // Process all nodes (queue-style BFS iteration over collected nodes)
        var i: usize = 0;
        while (i < collected_nodes.items.len) : (i += 1) {
            const current = collected_nodes.items[i];
            const bound_current = self.self_node.g.bind(current);

            // Follow EdgeComposition children
            _ = EdgeComposition.visit_children_edges(bound_current, void, &collector, Collector.visit_composition);

            // Follow EdgePointer references
            _ = EdgePointer.visit_pointed_edges(bound_current, void, &collector, Collector.visit_pointer);

            // Follow EdgeNext sequences
            if (EdgeNext.get_next_node_from_node(bound_current)) |next_node| {
                collector.try_add(next_node);
            }

            // Follow EdgeTrait to trait instances
            _ = EdgeTrait.visit_trait_instance_edges(bound_current, void, &collector, Collector.visit_trait);
        }

        return self.self_node.g.get_subgraph_from_nodes(collected_nodes);
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
    _ = try tg.add_make_child(Capacitor, Electrical, "p1", null);
    _ = try tg.add_make_child(Capacitor, Electrical, "p2", null);
    const Resistor = try tg.add_type("Resistor");
    const res_p1_makechild = try tg.add_make_child(Resistor, Electrical, "p1", null);
    std.debug.print("RES_P1_MAKECHILD: {s}\n", .{try EdgeComposition.get_name(EdgeComposition.get_parent_edge(res_p1_makechild).?.edge)});
    _ = try tg.add_make_child(Resistor, Electrical, "p2", null);
    _ = try tg.add_make_child(Resistor, Capacitor, "cap1", null);

    var node_attrs = TypeGraph.MakeChildNode.build(a, "test_string");
    _ = try tg.add_make_child(
        Capacitor,
        Electrical,
        "tp",
        &node_attrs,
    );

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
    _ = try tg.add_make_link(Resistor, cap1p1_reference.node, cap1p2_reference.node, .{
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
