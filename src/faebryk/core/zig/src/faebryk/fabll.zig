const std = @import("std");
const graph_mod = @import("graph");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const faebryk = @import("faebryk");
const str = []const u8;

// =============================================================================
// Still missing (vs Python FabLL)
// =============================================================================
// - Full RefPath parity beyond self/owner_child/child_identifier
// - Rich dependant child ergonomics
// - ListField equivalent
// - Type-field / put_on_type semantics
// - Deferred/linked child types (string nodetypes)
// - soft_create semantics
// - Broader Traits API parity
// - Broader Node runtime API parity
// - Better non-panic error surface

// =============================================================================
// Next milestone: dependant parity TODO
// =============================================================================
// 1) Add first-class dependant declaration field type
// 2) Execute declared dependants during type creation
// 3) Keep child-first / edge-after ordering deterministic
// 4) Add tests: dependant child + edge combinations
// 5) Add tests: prepend vs append dependant ordering
// 6) Add tests: interaction with declared edges

// =============================================================================
// Compile-time reflection & utility helpers
// =============================================================================

fn is_child_field_type(comptime MaybeChildField: type) bool {
    return @typeInfo(MaybeChildField) == .@"struct" and
        @hasDecl(MaybeChildField, "ChildType") and
        @hasDecl(MaybeChildField, "Identifier");
}

fn is_dependant_edge_type(comptime MaybeDependant: type) bool {
    return @typeInfo(MaybeDependant) == .@"struct" and
        @hasDecl(MaybeDependant, "DependantKind") and
        @hasDecl(MaybeDependant, "LhsPath") and
        @hasDecl(MaybeDependant, "RhsPath") and
        @hasDecl(MaybeDependant, "EdgeFactory");
}

fn is_dependant_declaration_type(comptime MaybeDependantDecl: type) bool {
    return @typeInfo(MaybeDependantDecl) == .@"struct" and
        @hasDecl(MaybeDependantDecl, "DependantDeclKind") and
        @hasDecl(MaybeDependantDecl, "OwnerChildIdentifier") and
        @hasDecl(MaybeDependantDecl, "Dependant");
}

fn is_edge_declaration_type(comptime MaybeEdgeDecl: type) bool {
    return @typeInfo(MaybeEdgeDecl) == .@"struct" and
        @hasDecl(MaybeEdgeDecl, "EdgeDeclKind") and
        @hasDecl(MaybeEdgeDecl, "LhsPath") and
        @hasDecl(MaybeEdgeDecl, "RhsPath") and
        @hasDecl(MaybeEdgeDecl, "EdgeFactory");
}

fn visit_dependant_declarations(
    comptime T: type,
    comptime R: type,
    ctx: *anyopaque,
    comptime f: anytype,
) visitor.VisitResult(R) {
    inline for (std.meta.fields(T)) |field| {
        if (comptime is_dependant_declaration_type(field.type)) {
            switch (f(ctx, field.name, field.type)) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(R){ .STOP = {} },
                .OK => |result| return visitor.VisitResult(R){ .OK = result },
                .EXHAUSTED => return visitor.VisitResult(R){ .EXHAUSTED = {} },
                .ERROR => |err| return visitor.VisitResult(R){ .ERROR = err },
            }
        }
    }

    const decls = @typeInfo(T).@"struct".decls;
    inline for (decls) |decl| {
        const value = @field(T, decl.name);
        const dep_decl_type = if (@TypeOf(value) == type) value else @TypeOf(value);
        if (comptime is_dependant_declaration_type(dep_decl_type)) {
            switch (f(ctx, decl.name, dep_decl_type)) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(R){ .STOP = {} },
                .OK => |result| return visitor.VisitResult(R){ .OK = result },
                .EXHAUSTED => return visitor.VisitResult(R){ .EXHAUSTED = {} },
                .ERROR => |err| return visitor.VisitResult(R){ .ERROR = err },
            }
        }
    }
    return visitor.VisitResult(R){ .EXHAUSTED = {} };
}

fn append_type(comptime items: []const type, comptime item: type) []const type {
    return comptime blk: {
        var out: [items.len + 1]type = undefined;
        for (items, 0..) |existing, i| {
            out[i] = existing;
        }
        out[items.len] = item;
        const finalized = out;
        break :blk &finalized;
    };
}

fn AttributesType(comptime T: type) type {
    return if (@hasDecl(T, "Attributes")) T.Attributes else struct {};
}

fn requires_attrs(comptime T: type) bool {
    return @hasDecl(T, "Attributes");
}

fn field_identifier(decl_name: []const u8, field_type: type) []const u8 {
    return field_type.Identifier orelse decl_name;
}

fn visit_fields(
    comptime T: type,
    comptime R: type,
    ctx: *anyopaque,
    comptime f: anytype,
) visitor.VisitResult(R) {
    inline for (std.meta.fields(T)) |field| {
        if (comptime is_child_field_type(field.type)) {
            switch (f(ctx, field.name, field.type)) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(R){ .STOP = {} },
                .OK => |result| return visitor.VisitResult(R){ .OK = result },
                .EXHAUSTED => return visitor.VisitResult(R){ .EXHAUSTED = {} },
                .ERROR => |err| return visitor.VisitResult(R){ .ERROR = err },
            }
        }
    }

    const decls = @typeInfo(T).@"struct".decls;
    inline for (decls) |decl| {
        const value = @field(T, decl.name);
        if (comptime is_child_field_type(@TypeOf(value))) {
            switch (f(ctx, decl.name, value)) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(R){ .STOP = {} },
                .OK => |result| return visitor.VisitResult(R){ .OK = result },
                .EXHAUSTED => return visitor.VisitResult(R){ .EXHAUSTED = {} },
                .ERROR => |err| return visitor.VisitResult(R){ .ERROR = err },
            }
        }
    }
    return visitor.VisitResult(R){ .EXHAUSTED = {} };
}

fn visit_edge_declarations(
    comptime T: type,
    comptime R: type,
    ctx: *anyopaque,
    comptime f: anytype,
) visitor.VisitResult(R) {
    inline for (std.meta.fields(T)) |field| {
        if (comptime is_edge_declaration_type(field.type)) {
            switch (f(ctx, field.name, field.type)) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(R){ .STOP = {} },
                .OK => |result| return visitor.VisitResult(R){ .OK = result },
                .EXHAUSTED => return visitor.VisitResult(R){ .EXHAUSTED = {} },
                .ERROR => |err| return visitor.VisitResult(R){ .ERROR = err },
            }
        }
    }

    const decls = @typeInfo(T).@"struct".decls;
    inline for (decls) |decl| {
        const value = @field(T, decl.name);
        const edge_decl_type = if (@TypeOf(value) == type) value else @TypeOf(value);
        if (comptime is_edge_declaration_type(edge_decl_type)) {
            switch (f(ctx, decl.name, edge_decl_type)) {
                .CONTINUE => {},
                .STOP => return visitor.VisitResult(R){ .STOP = {} },
                .OK => |result| return visitor.VisitResult(R){ .OK = result },
                .EXHAUSTED => return visitor.VisitResult(R){ .EXHAUSTED = {} },
                .ERROR => |err| return visitor.VisitResult(R){ .ERROR = err },
            }
        }
    }
    return visitor.VisitResult(R){ .EXHAUSTED = {} };
}

// =============================================================================
// Node binding / typegraph instantiation
// =============================================================================

pub const Node = struct {
    instance: graph.BoundNodeReference,

    pub fn MakeChild(comptime T: type) type {
        if (comptime requires_attrs(T)) {
            @compileError("Type defines `Attributes`; use `T.MakeChild(...)` to provide attributes");
        }
        return ChildField(
            T,
            null,
            &.{},
            &.{},
            &.{},
        );
    }

    pub fn MakeChildWithAttrs(comptime T: type, comptime attributes: []const ChildAttribute) type {
        return ChildField(
            T,
            null,
            attributes,
            &.{},
            &.{},
        );
    }

    pub fn bind_typegraph(comptime T: type, tg: *faebryk.typegraph.TypeGraph) TypeNodeBoundTG(T) {
        return .{ .tg = tg };
    }
};

pub fn TypeNodeBoundTG(comptime T: type) type {
    return struct {
        tg: *faebryk.typegraph.TypeGraph,

        fn instantiate_raw(self: @This(), g: *graph.GraphView) graph.BoundNodeReference {
            const type_node = self.get_or_create_type();
            if (type_node.g != g) {
                @panic("create_instance graph must match the bound typegraph graph");
            }

            const result = self.tg.instantiate_node(type_node);
            return switch (result) {
                .ok => |n| n,
                .err => |err| {
                    std.debug.print("fabll instantiate failed: {s}\n", .{err.message});
                    @panic("fabll instantiate failed");
                },
            };
        }

        pub fn create_instance(self: @This(), g: *graph.GraphView) T {
            if (comptime requires_attrs(T)) {
                @compileError("Type requires explicit attributes: use create_instance_with_attrs(...)");
            }
            const instance = self.instantiate_raw(g);
            return wrap_instance(T, instance);
        }

        pub fn create_instance_with_attrs(
            self: @This(),
            g: *graph.GraphView,
            attrs: AttributesType(T),
        ) T {
            const instance = self.instantiate_raw(g);
            apply_typed_attributes(instance, attrs);
            return wrap_instance(T, instance);
        }

        pub fn get_or_create_type(self: @This()) graph.BoundNodeReference {
            const Self = @This();
            const type_identifier = @typeName(T);
            if (self.tg.get_type_by_name(type_identifier)) |existing| {
                return existing;
            }

            const type_node = self.tg.add_type(type_identifier) catch |err| switch (err) {
                error.TypeAlreadyExists => self.tg.get_type_by_name(type_identifier) orelse unreachable,
                else => @panic("failed to add type"),
            };

            const BuildContext = struct {
                self: Self,
                type_node: graph.BoundNodeReference,

                fn add_child_field(ctx: *@This(), comptime child_field_type: type, child_identifier: []const u8) void {
                    inline for (child_field_type.PrependDependants) |dependant| {
                        ctx.apply_dependant_children_only(child_identifier, dependant);
                    }

                    const child_bound = Node.bind_typegraph(child_field_type.ChildType, ctx.self.tg);
                    const child_type = child_bound.get_or_create_type();
                    var node_attrs: faebryk.nodebuilder.NodeCreationAttributes = .{
                        .dynamic = graph.DynamicAttributes.init_on_stack(),
                    };
                    for (child_field_type.Attributes) |attr| {
                        node_attrs.dynamic.put(attr.key, attr.value);
                    }
                    const node_attrs_ptr: ?*faebryk.nodebuilder.NodeCreationAttributes = if (child_field_type.Attributes.len > 0)
                        &node_attrs
                    else
                        null;
                    _ = ctx.self.tg.add_make_child(
                        ctx.type_node,
                        child_type,
                        child_identifier,
                        node_attrs_ptr,
                        false,
                    ) catch @panic("failed to add make child");

                    inline for (child_field_type.Dependants) |dependant| {
                        ctx.apply_dependant_children_only(child_identifier, dependant);
                    }
                }

                fn build_path(
                    owner_identifier: []const u8,
                    comptime path: RefPath,
                ) [path.segments.len]faebryk.typegraph.TypeGraph.ChildReferenceNode.EdgeTraversal {
                    // Convert high-level refpath segments into TypeGraph traversal edges.
                    // `owner_child` is bound at runtime to the child currently being expanded.
                    var out: [path.segments.len]faebryk.typegraph.TypeGraph.ChildReferenceNode.EdgeTraversal = undefined;
                    inline for (path.segments, 0..) |segment, i| {
                        out[i] = switch (segment) {
                            .self_node => faebryk.composition.EdgeComposition.traverse(""),
                            .owner_child => faebryk.composition.EdgeComposition.traverse(owner_identifier),
                            .child_identifier => |path_identifier| faebryk.composition.EdgeComposition.traverse(path_identifier),
                        };
                    }
                    return out;
                }

                fn apply_dependant_children_only(
                    ctx: *@This(),
                    owner_child_identifier: []const u8,
                    comptime dependant_type: type,
                ) void {
                    // Dependants are compile-time declarations attached to a child field.
                    // They can be either:
                    // 1) additional child fields created before/after the owner child
                    // 2) edges created via make_link with refpaths relative to the owner child
                    if (comptime is_child_field_type(dependant_type)) {
                        const dependant_identifier = dependant_type.Identifier orelse
                            @panic("dependant child field must set explicit identifier");
                        ctx.add_child_field(dependant_type, dependant_identifier);
                        return;
                    }

                    if (comptime is_dependant_edge_type(dependant_type)) {
                        _ = owner_child_identifier;
                        return;
                    }

                    @panic("unsupported dependant type");
                }

                fn apply_dependant_edges_only(
                    ctx: *@This(),
                    owner_child_identifier: []const u8,
                    comptime dependant_type: type,
                ) void {
                    if (comptime is_child_field_type(dependant_type)) {
                        const dependant_identifier = dependant_type.Identifier orelse
                            @panic("dependant child field must set explicit identifier");
                        inline for (dependant_type.PrependDependants) |nested_dependant| {
                            ctx.apply_dependant_edges_only(dependant_identifier, nested_dependant);
                        }
                        inline for (dependant_type.Dependants) |nested_dependant| {
                            ctx.apply_dependant_edges_only(dependant_identifier, nested_dependant);
                        }
                        return;
                    }

                    if (comptime is_dependant_edge_type(dependant_type)) {
                        const edge_attrs = dependant_type.EdgeFactory.build();
                        const lhs_path = build_path(owner_child_identifier, dependant_type.LhsPath);
                        const rhs_path = build_path(owner_child_identifier, dependant_type.RhsPath);
                        const lhs_ref = faebryk.typegraph.TypeGraph.ChildReferenceNode.create_and_insert(
                            ctx.self.tg,
                            &lhs_path,
                        ) catch @panic("failed to build dependant lhs reference");
                        const rhs_ref = faebryk.typegraph.TypeGraph.ChildReferenceNode.create_and_insert(
                            ctx.self.tg,
                            &rhs_path,
                        ) catch @panic("failed to build dependant rhs reference");

                        _ = ctx.self.tg.add_make_link(
                            ctx.type_node,
                            lhs_ref,
                            rhs_ref,
                            edge_attrs,
                        ) catch @panic("failed to add dependant make link");
                        return;
                    }

                    @panic("unsupported dependant type");
                }

                fn add_child_dependant_edges(ctx: *@This(), comptime child_field_type: type, child_identifier: []const u8) void {
                    inline for (child_field_type.PrependDependants) |dependant| {
                        ctx.apply_dependant_edges_only(child_identifier, dependant);
                    }
                    inline for (child_field_type.Dependants) |dependant| {
                        ctx.apply_dependant_edges_only(child_identifier, dependant);
                    }
                }

                fn apply_edge_spec(ctx: *@This(), comptime edge_spec_type: type) void {
                    const edge_attrs = edge_spec_type.EdgeFactory.build();
                    const lhs_path = build_path("", edge_spec_type.LhsPath);
                    const rhs_path = build_path("", edge_spec_type.RhsPath);
                    const lhs_ref = faebryk.typegraph.TypeGraph.ChildReferenceNode.create_and_insert(
                        ctx.self.tg,
                        &lhs_path,
                    ) catch @panic("failed to build edge lhs reference");
                    const rhs_ref = faebryk.typegraph.TypeGraph.ChildReferenceNode.create_and_insert(
                        ctx.self.tg,
                        &rhs_path,
                    ) catch @panic("failed to build edge rhs reference");

                    _ = ctx.self.tg.add_make_link(
                        ctx.type_node,
                        lhs_ref,
                        rhs_ref,
                        edge_attrs,
                    ) catch @panic("failed to add declared make link");
                }

                fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, field_type: type) visitor.VisitResult(void) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    const child_identifier = field_identifier(decl_name, field_type);
                    ctx.add_child_field(field_type, child_identifier);
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            };

            var build_ctx = BuildContext{
                .self = self,
                .type_node = type_node,
            };
            switch (visit_fields(T, void, &build_ctx, BuildContext.visit)) {
                .ERROR => @panic("visit_fields failed"),
                else => {},
            }

            const ChildDependantDeclContext = struct {
                build_ctx: *BuildContext,

                fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, dependant_decl: anytype) visitor.VisitResult(void) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    _ = decl_name;
                    const dependant_decl_type = if (@TypeOf(dependant_decl) == type) dependant_decl else @TypeOf(dependant_decl);
                    ctx.build_ctx.apply_dependant_children_only(
                        dependant_decl_type.OwnerChildIdentifier,
                        dependant_decl_type.Dependant,
                    );
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            };
            var child_dependant_decl_ctx: ChildDependantDeclContext = .{ .build_ctx = &build_ctx };
            switch (visit_dependant_declarations(T, void, &child_dependant_decl_ctx, ChildDependantDeclContext.visit)) {
                .ERROR => @panic("visit_dependant_declarations (children pass) failed"),
                else => {},
            }

            const DependantEdgeContext = struct {
                build_ctx: *BuildContext,

                fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, field_type: type) visitor.VisitResult(void) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    const child_identifier = field_identifier(decl_name, field_type);
                    ctx.build_ctx.add_child_dependant_edges(field_type, child_identifier);
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            };
            var dependant_edge_ctx: DependantEdgeContext = .{ .build_ctx = &build_ctx };
            switch (visit_fields(T, void, &dependant_edge_ctx, DependantEdgeContext.visit)) {
                .ERROR => @panic("visit_fields dependant-edge pass failed"),
                else => {},
            }

            const EdgeDependantDeclContext = struct {
                build_ctx: *BuildContext,

                fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, dependant_decl: anytype) visitor.VisitResult(void) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    _ = decl_name;
                    const dependant_decl_type = if (@TypeOf(dependant_decl) == type) dependant_decl else @TypeOf(dependant_decl);
                    ctx.build_ctx.apply_dependant_edges_only(
                        dependant_decl_type.OwnerChildIdentifier,
                        dependant_decl_type.Dependant,
                    );
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            };
            var edge_dependant_decl_ctx: EdgeDependantDeclContext = .{ .build_ctx = &build_ctx };
            switch (visit_dependant_declarations(T, void, &edge_dependant_decl_ctx, EdgeDependantDeclContext.visit)) {
                .ERROR => @panic("visit_dependant_declarations (edges pass) failed"),
                else => {},
            }

            const EdgeDeclContext = struct {
                build_ctx: *BuildContext,

                fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, edge_decl: anytype) visitor.VisitResult(void) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    _ = decl_name;
                    const edge_decl_type = if (@TypeOf(edge_decl) == type) edge_decl else @TypeOf(edge_decl);
                    ctx.build_ctx.apply_edge_spec(edge_decl_type);
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            };
            var edge_decl_ctx: EdgeDeclContext = .{ .build_ctx = &build_ctx };
            switch (visit_edge_declarations(T, void, &edge_decl_ctx, EdgeDeclContext.visit)) {
                .ERROR => @panic("visit_edge_declarations failed"),
                else => {},
            }

            return type_node;
        }
    };
}

// =============================================================================
// Typed attribute encoding/decoding
// =============================================================================

fn attribute_value_to_literal(comptime V: type, value: V) graph.Literal {
    return switch (@typeInfo(V)) {
        .float => .{ .Float = @as(f64, value) },
        .int => .{ .Int = @as(i64, value) },
        .comptime_int => .{ .Int = value },
        .bool => .{ .Bool = value },
        .pointer => |ptr| blk: {
            if (ptr.size == .slice and ptr.child == u8) {
                break :blk .{ .String = value };
            }
            @compileError("Unsupported pointer attribute type");
        },
        else => @compileError("Unsupported attribute value type"),
    };
}

fn literal_to_attribute_value(comptime V: type, lit: graph.Literal) V {
    return switch (@typeInfo(V)) {
        .float => @as(V, @floatCast(lit.Float)),
        .int => @as(V, @intCast(lit.Int)),
        .comptime_int => @as(V, @intCast(lit.Int)),
        .bool => lit.Bool,
        .pointer => |ptr| blk: {
            if (ptr.size == .slice and ptr.child == u8) {
                break :blk lit.String;
            }
            @compileError("Unsupported pointer attribute type");
        },
        else => @compileError("Unsupported attribute value type"),
    };
}

fn apply_typed_attributes(instance: graph.BoundNodeReference, attrs: anytype) void {
    const A = @TypeOf(attrs);
    inline for (std.meta.fields(A)) |field| {
        instance.node.put(field.name, attribute_value_to_literal(field.type, @field(attrs, field.name)));
    }
}

pub fn get_typed_attributes(node: anytype) AttributesType(@TypeOf(node)) {
    // TODO: benchmark with real types whether attrvisitor is faster than inline loop with get
    const T = @TypeOf(node);
    const A = AttributesType(T);
    if (comptime std.meta.fields(A).len == 0) {
        @compileError("Type does not define `Attributes`");
    }
    const fields = std.meta.fields(A);
    const field_count = fields.len;

    var out: A = undefined;
    var seen: [field_count]bool = [_]bool{false} ** field_count;

    const AttrVisitor = struct {
        out: *A,
        seen: *[field_count]bool,

        pub fn visit(ctx: *anyopaque, key: str, lit: graph.Literal, dynamic: bool) void {
            if (!dynamic) return;
            const self: *@This() = @ptrCast(@alignCast(ctx));
            inline for (fields, 0..) |field, i| {
                if (std.mem.eql(u8, key, field.name)) {
                    @field(self.out.*, field.name) = literal_to_attribute_value(field.type, lit);
                    self.seen[i] = true;
                    return;
                }
            }
        }
    };
    var visitor_ctx = AttrVisitor{
        .out = &out,
        .seen = &seen,
    };
    node.node.instance.node.visit_attributes(&visitor_ctx, AttrVisitor.visit);

    inline for (fields, 0..) |field, i| {
        if (!seen[i]) {
            std.debug.print("missing typed attribute on node: {s}\n", .{field.name});
            @panic("missing typed attribute on node");
        }
    }
    return out;
}

pub const ChildAttribute = struct {
    key: str,
    value: graph.Literal,
};

fn child_attributes_from_struct(comptime S: type, comptime attrs: S) []const ChildAttribute {
    const fields = std.meta.fields(S);
    return comptime blk: {
        var out: [fields.len]ChildAttribute = undefined;
        for (fields, 0..) |field, i| {
            out[i] = .{
                .key = field.name,
                .value = attribute_value_to_literal(field.type, @field(attrs, field.name)),
            };
        }
        const finalized = out;
        break :blk &finalized;
    };
}

pub fn MakeChildWithTypedAttrs(comptime T: type, comptime attrs: anytype) type {
    return Node.MakeChildWithAttrs(T, child_attributes_from_struct(@TypeOf(attrs), attrs));
}

// =============================================================================
// Child field model & dependant model
// =============================================================================

pub fn ChildField(
    comptime T: type,
    comptime identifier: ?str,
    comptime attributes: []const ChildAttribute,
    comptime prepend_dependants: []const type,
    comptime dependants: []const type,
) type {
    return struct {
        // Compile-time metadata of the declared child field (stage-0/type side).
        pub const ChildType = T;
        pub const Identifier = identifier;
        pub const Attributes = attributes;
        pub const PrependDependants = prepend_dependants;
        pub const Dependants = dependants;
        parent_instance: ?graph.BoundNodeReference = null,
        locator: ?str = null,

        pub fn get(self: @This()) T {
            const parent = self.parent_instance orelse @panic("child field is not bound");
            const child_identifier = Identifier orelse self.locator orelse
                @panic("child field has no identifier or locator");
            const child = faebryk.composition.EdgeComposition.get_child_by_identifier(
                parent,
                child_identifier,
            ) orelse @panic("child not found");
            return wrap_instance(T, child);
        }

        pub fn add_dependant(comptime dependant: type) type {
            return ChildField(
                T,
                identifier,
                attributes,
                prepend_dependants,
                append_type(dependants, dependant),
            );
        }

        pub fn add_dependant_before(comptime dependant: type) type {
            return ChildField(
                T,
                identifier,
                attributes,
                append_type(prepend_dependants, dependant),
                dependants,
            );
        }

        pub fn add_as_dependant(comptime to: type) type {
            return to.add_dependant(@This());
        }
    };
}

pub fn MakeDependantEdge(
    comptime lhs_path: RefPath,
    comptime rhs_path: RefPath,
    comptime edge_factory: type,
) type {
    if (comptime !@hasDecl(edge_factory, "build")) {
        @compileError("MakeDependantEdge edge_factory must provide build()");
    }
    return struct {
        pub const DependantKind = .edge;
        pub const LhsPath = lhs_path;
        pub const RhsPath = rhs_path;
        pub const EdgeFactory = edge_factory;
    };
}

pub fn MakeDependantDeclaration(
    comptime owner_child_identifier: str,
    comptime dependant: type,
) type {
    if (comptime !(is_child_field_type(dependant) or is_dependant_edge_type(dependant))) {
        @compileError("MakeDependantDeclaration dependant must be ChildField(...) or MakeDependantEdge(...)");
    }

    return struct {
        pub const DependantDeclKind = .dependant;
        pub const OwnerChildIdentifier = owner_child_identifier;
        pub const Dependant = dependant;
    };
}

pub fn MakeEdgeDeclaration(
    comptime lhs_path: RefPath,
    comptime rhs_path: RefPath,
    comptime edge_factory: type,
) type {
    if (comptime !@hasDecl(edge_factory, "build")) {
        @compileError("MakeEdgeDeclaration edge_factory must provide build()");
    }
    return struct {
        pub const EdgeDeclKind = .edge;
        pub const LhsPath = lhs_path;
        pub const RhsPath = rhs_path;
        pub const EdgeFactory = edge_factory;
    };
}

pub const Field = struct {
    identifier: ?str,
    locator: ?str,
};

pub const EdgeField = struct {
    lhs: RefPath,
    rhs: RefPath,
    edge: faebryk.edgebuilder.EdgeCreationAttributes,
    identifier: ?str,
};

pub const RefPath = struct {
    // A tiny compile-time path language to address nodes relative to a dependant owner.
    pub const Segment = union(enum) {
        self_node: void,
        owner_child: void,
        child_identifier: str,
    };

    segments: []const Segment,

    pub fn self() @This() {
        return .{
            .segments = &.{.{ .self_node = {} }},
        };
    }

    pub fn owner_child() @This() {
        return .{
            .segments = &.{.{ .owner_child = {} }},
        };
    }

    pub fn child_identifier(comptime identifier: str) @This() {
        return .{
            .segments = &.{.{ .child_identifier = identifier }},
        };
    }

};

fn wrap_instance(comptime T: type, instance: graph.BoundNodeReference) T {
    comptime if (!@hasField(T, "node")) {
        @compileError("FabLL Zig node types must have a `node: Node` field");
    };

    var out: T = undefined;

    inline for (std.meta.fields(T)) |field| {
        // TODO: make less hacky
        if (comptime std.mem.eql(u8, field.name, "node")) {
            @field(out, field.name) = .{ .instance = instance };
            continue;
        }
        if (comptime is_child_field_type(field.type)) {
            var child: field.type = .{};
            child.parent_instance = instance;
            child.locator = field.name;
            @field(out, field.name) = child;
            continue;
        }
        if (field.default_value_ptr) |ptr| {
            const typed_ptr: *const field.type = @ptrCast(@alignCast(ptr));
            @field(out, field.name) = typed_ptr.*;
            continue;
        }
        @compileError("Non-child fields must have default values");
    }

    return out;
}

// =============================================================================
// Test fixtures and tests
// =============================================================================

// TESTING ====================================================================

const is_trait = struct {
    node: Node,

    pub fn MakeEdge(comptime traitchildfield: type, comptime owner: ?RefPath) type {
        const owner_path = owner orelse RefPath.self();
        return traitchildfield.add_dependant(
            MakeDependantEdge(
                owner_path,
                RefPath.owner_child(),
                faebryk.trait.EdgeTrait,
            ),
        );
    }

    pub fn MakeChild() type {
        return Node.MakeChild(@This());
    }
};

const is_interface = struct {
    node: Node,
    _is_trait: is_trait.MakeChild(),

    pub fn MakeConnectionEdge(comptime n1: RefPath, comptime n2: RefPath, comptime shallow: bool) type {
        const EdgeFactory = struct {
            pub fn build() faebryk.edgebuilder.EdgeCreationAttributes {
                return faebryk.interface.EdgeInterfaceConnection.build(shallow) catch
                    @panic("failed to build interface connection edge attributes");
            }
        };
        return MakeDependantEdge(n1, n2, EdgeFactory);
    }

    pub fn MakeChild() type {
        return Node.MakeChild(@This());
    }
};

const Electrical = struct {
    node: Node,

    _is_interface: is_trait.MakeEdge(is_interface.MakeChild(), null),

    pub fn MakeChild() type {
        return Node.MakeChild(@This());
    }
};

const ElectricPower = struct {
    node: Node,

    hv: Electrical.MakeChild(),
    lv: Electrical.MakeChild(),
};

const Number = struct {
    node: Node,

    pub const Attributes = struct {
        number: f64,
    };

    pub fn MakeChild(comptime attrs: Attributes) type {
        return MakeChildWithTypedAttrs(@This(), attrs);
    }

    pub fn attributes(self: @This()) Attributes {
        return get_typed_attributes(self);
    }
};

const NumberContainer = struct {
    node: Node,

    n: Number.MakeChild(.{ .number = 3.14 }),
};

const InterfaceConnectionEdgeFactoryFalse = struct {
    pub fn build() faebryk.edgebuilder.EdgeCreationAttributes {
        return faebryk.interface.EdgeInterfaceConnection.build(false) catch
            @panic("failed to build interface connection edge attributes");
    }
};

const ElectricPowerDeclaredConnected = struct {
    node: Node,
    hv: Electrical.MakeChild(),
    lv: Electrical.MakeChild(),

    _hv_lv: MakeEdgeDeclaration(
        RefPath.child_identifier("hv"),
        RefPath.child_identifier("lv"),
        InterfaceConnectionEdgeFactoryFalse,
    ) = .{},
};

const ElectricPowerDeclaredNestedConnected = struct {
    node: Node,
    hv: Electrical.MakeChild(),
    lv: Electrical.MakeChild(),

    _hv_iface_to_lv_iface: MakeEdgeDeclaration(
        .{
            .segments = &.{
                .{ .child_identifier = "hv" },
                .{ .child_identifier = "_is_interface" },
            },
        },
        .{
            .segments = &.{
                .{ .child_identifier = "lv" },
                .{ .child_identifier = "_is_interface" },
            },
        },
        InterfaceConnectionEdgeFactoryFalse,
    ) = .{},
};

const ElectricPowerMixedEdges = struct {
    node: Node,
    hv: Electrical.MakeChild().add_dependant(
        is_interface.MakeConnectionEdge(
            RefPath.owner_child(),
            RefPath.child_identifier("lv"),
            false,
        ),
    ),
    lv: Electrical.MakeChild(),

    _hv_iface_to_lv_iface: MakeEdgeDeclaration(
        .{
            .segments = &.{
                .{ .child_identifier = "hv" },
                .{ .child_identifier = "_is_interface" },
            },
        },
        .{
            .segments = &.{
                .{ .child_identifier = "lv" },
                .{ .child_identifier = "_is_interface" },
            },
        },
        InterfaceConnectionEdgeFactoryFalse,
    ) = .{},
};

const ElectricPowerDeclaredDependantEdge = struct {
    node: Node,
    hv: Electrical.MakeChild(),
    lv: Electrical.MakeChild(),

    _dep_hv_to_lv: MakeDependantDeclaration(
        "hv",
        is_interface.MakeConnectionEdge(
            RefPath.owner_child(),
            RefPath.child_identifier("lv"),
            false,
        ),
    ) = .{},
};

const ElectricPowerDeclaredDependantChildThenEdge = struct {
    node: Node,
    hv: Electrical.MakeChild(),
    lv: Electrical.MakeChild(),

    _dep_add_sense: MakeDependantDeclaration(
        "hv",
        ChildField(Electrical, "sense", &.{}, &.{}, &.{}),
    ) = .{},

    _sense_to_lv: MakeEdgeDeclaration(
        RefPath.child_identifier("sense"),
        RefPath.child_identifier("lv"),
        InterfaceConnectionEdgeFactoryFalse,
    ) = .{},
};

fn print_type_overview(tg: *faebryk.typegraph.TypeGraph, allocator: std.mem.Allocator, label: []const u8) void {
    var overview = tg.get_type_instance_overview(allocator);
    defer overview.deinit();

    std.debug.print("\nType overview ({s}):\n", .{label});
    for (overview.items) |item| {
        std.debug.print("  {s}: {d} instances\n", .{ item.type_name, item.instance_count });
    }
}

test "comptime child field discovery" {
    const F = struct {
        fn comptime_child_field_count(comptime T: type) usize {
            const Ctx = struct {
                count: usize = 0,

                fn visit(ctx_ptr: *anyopaque, _: []const u8, _: anytype) visitor.VisitResult(void) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    ctx.count += 1;
                    return visitor.VisitResult(void){ .CONTINUE = {} };
                }
            };

            var ctx: Ctx = .{};
            switch (visit_fields(T, void, &ctx, Ctx.visit)) {
                .ERROR => @panic("count visit failed"),
                else => {},
            }
            return ctx.count;
        }

        fn comptime_child_field_name(comptime T: type, comptime idx: usize) []const u8 {
            const Ctx = struct {
                i: usize = 0,
                target: usize,

                fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, field: type) visitor.VisitResult([]const u8) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    if (ctx.i == ctx.target) {
                        return visitor.VisitResult([]const u8){ .OK = field_identifier(decl_name, field) };
                    }
                    ctx.i += 1;
                    return visitor.VisitResult([]const u8){ .CONTINUE = {} };
                }
            };

            var ctx: Ctx = .{ .target = idx };
            return switch (visit_fields(T, []const u8, &ctx, Ctx.visit)) {
                .OK => |name| name,
                else => @panic("child field index out of bounds"),
            };
        }
    };

    try std.testing.expectEqual(@as(usize, 2), F.comptime_child_field_count(ElectricPower));
    try std.testing.expect(std.mem.eql(u8, F.comptime_child_field_name(ElectricPower, 0), "hv"));
    try std.testing.expect(std.mem.eql(u8, F.comptime_child_field_name(ElectricPower, 1), "lv"));
}

test "basic fabll" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const bound = Node.bind_typegraph(Electrical, &tg);
    const e1 = bound.create_instance(&g);
    _ = e1;

    print_type_overview(&tg, std.testing.allocator, "basic fabll");
}

test "basic+1 fabll" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const electrical_bound = Node.bind_typegraph(Electrical, &tg);
    _ = electrical_bound.create_instance(&g);

    const power_bound = Node.bind_typegraph(ElectricPower, &tg);
    _ = power_bound.create_instance(&g);

    print_type_overview(&tg, std.testing.allocator, "basic+1 fabll");
}

test "basic+2 fabll trait edges" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const power_bound = Node.bind_typegraph(ElectricPower, &tg);
    const power_instance = power_bound.create_instance(&g).node.instance;

    const hv = faebryk.composition.EdgeComposition.get_child_by_identifier(power_instance, "hv") orelse
        @panic("missing hv child");
    const lv = faebryk.composition.EdgeComposition.get_child_by_identifier(power_instance, "lv") orelse
        @panic("missing lv child");

    const is_interface_type = tg.get_type_by_name(@typeName(is_interface)) orelse
        @panic("missing is_interface type");

    const hv_trait = faebryk.trait.EdgeTrait.try_get_trait_instance_of_type(hv, is_interface_type.node);
    const lv_trait = faebryk.trait.EdgeTrait.try_get_trait_instance_of_type(lv, is_interface_type.node);

    try std.testing.expect(hv_trait != null);
    try std.testing.expect(lv_trait != null);

    print_type_overview(&tg, std.testing.allocator, "basic+2 fabll trait edges");
}

test "basic+3 field accessor" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const power_bound = Node.bind_typegraph(ElectricPower, &tg);
    const power = power_bound.create_instance(&g);

    const hv_from_accessor = power.hv.get().node.instance;
    const hv_from_graph = faebryk.composition.EdgeComposition.get_child_by_identifier(power.node.instance, "hv") orelse
        @panic("missing hv child");

    try std.testing.expect(hv_from_accessor.node.is_same(hv_from_graph.node));
}

test "basic+4 child attributes" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const bound = Node.bind_typegraph(NumberContainer, &tg);
    const container = bound.create_instance(&g);
    const number = container.n.get();

    const attrs = get_typed_attributes(number);
    try std.testing.expectApproxEqAbs(@as(f64, 3.14), attrs.number, 1e-9);
}

test "basic+5 instance attributes" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const bound = Node.bind_typegraph(Number, &tg);
    const number = bound.create_instance_with_attrs(&g, .{
        .number = 4.2,
    });

    const attrs = number.attributes();
    try std.testing.expectApproxEqAbs(@as(f64, 4.2), attrs.number, 1e-9);
}

test "basic+6 interface connection edge dependant" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const ElectricPowerConnected = struct {
        node: Node,

        hv: Electrical.MakeChild().add_dependant(
            is_interface.MakeConnectionEdge(
                RefPath.owner_child(),
                RefPath.child_identifier("lv"),
                false,
            ),
        ),
        lv: Electrical.MakeChild(),
    };

    const bound = Node.bind_typegraph(ElectricPowerConnected, &tg);
    const power_instance = bound.create_instance(&g);

    const hv = power_instance.hv.get();
    const lv = power_instance.lv.get();

    const Ctx = struct {
        hv: graph.BoundNodeReference,
        lv: graph.BoundNodeReference,
        found: bool = false,
        shallow_is_false: bool = false,

        fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            if (!faebryk.interface.EdgeInterfaceConnection.is_instance(be.edge)) {
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            const other = faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(be.edge, ctx.hv.node) orelse
                return visitor.VisitResult(void){ .CONTINUE = {} };
            if (!other.is_same(ctx.lv.node)) {
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }

            const shallow = be.edge.get(faebryk.interface.EdgeInterfaceConnection.shallow_attribute) orelse
                @panic("missing shallow attribute");
            ctx.found = true;
            ctx.shallow_is_false = !shallow.Bool;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var ctx: Ctx = .{
        .hv = hv.node.instance,
        .lv = lv.node.instance,
    };
    switch (faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(hv.node.instance, &ctx, Ctx.visit)) {
        .ERROR => @panic("visit_connected_edges failed"),
        else => {},
    }

    try std.testing.expect(ctx.found);
    try std.testing.expect(ctx.shallow_is_false);
}

test "basic+7 two-segment refpath dependant edge" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const ElectricPowerNestedConnected = struct {
        node: Node,

        hv: Electrical.MakeChild().add_dependant(
            is_interface.MakeConnectionEdge(
                .{
                    .segments = &.{
                        .{ .owner_child = {} },
                        .{ .child_identifier = "_is_interface" },
                    },
                },
                .{
                    .segments = &.{
                        .{ .child_identifier = "lv" },
                        .{ .child_identifier = "_is_interface" },
                    },
                },
                false,
            ),
        ),
        lv: Electrical.MakeChild(),
    };

    const bound = Node.bind_typegraph(ElectricPowerNestedConnected, &tg);
    const power_instance = bound.create_instance(&g);

    const hv_iface = power_instance.hv.get()._is_interface.get();
    const lv_iface = power_instance.lv.get()._is_interface.get();

    const Ctx = struct {
        hv_iface: graph.BoundNodeReference,
        lv_iface: graph.BoundNodeReference,
        found: bool = false,

        fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            if (!faebryk.interface.EdgeInterfaceConnection.is_instance(be.edge)) {
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
            const other = faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(be.edge, ctx.hv_iface.node) orelse
                return visitor.VisitResult(void){ .CONTINUE = {} };
            if (other.is_same(ctx.lv_iface.node)) {
                ctx.found = true;
            }
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var ctx: Ctx = .{
        .hv_iface = hv_iface.node.instance,
        .lv_iface = lv_iface.node.instance,
    };
    switch (faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(hv_iface.node.instance, &ctx, Ctx.visit)) {
        .ERROR => @panic("visit_connected_edges failed"),
        else => {},
    }

    try std.testing.expect(ctx.found);
}

test "basic+8 declared edge sibling path" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const bound = Node.bind_typegraph(ElectricPowerDeclaredConnected, &tg);
    const power = bound.create_instance(&g);
    const hv = power.hv.get().node.instance;
    const lv = power.lv.get().node.instance;

    const Ctx = struct {
        hv: graph.BoundNodeReference,
        lv: graph.BoundNodeReference,
        found: bool = false,

        fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            if (!faebryk.interface.EdgeInterfaceConnection.is_instance(be.edge)) return visitor.VisitResult(void){ .CONTINUE = {} };
            const other = faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(be.edge, ctx.hv.node) orelse
                return visitor.VisitResult(void){ .CONTINUE = {} };
            if (other.is_same(ctx.lv.node)) ctx.found = true;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var ctx: Ctx = .{ .hv = hv, .lv = lv };
    switch (faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(hv, &ctx, Ctx.visit)) {
        .ERROR => @panic("visit_connected_edges failed"),
        else => {},
    }
    try std.testing.expect(ctx.found);
}

test "basic+9 declared edge two-segment path" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const bound = Node.bind_typegraph(ElectricPowerDeclaredNestedConnected, &tg);
    const power = bound.create_instance(&g);
    const hv_iface = power.hv.get()._is_interface.get().node.instance;
    const lv_iface = power.lv.get()._is_interface.get().node.instance;

    const Ctx = struct {
        hv_iface: graph.BoundNodeReference,
        lv_iface: graph.BoundNodeReference,
        found: bool = false,

        fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            if (!faebryk.interface.EdgeInterfaceConnection.is_instance(be.edge)) return visitor.VisitResult(void){ .CONTINUE = {} };
            const other = faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(be.edge, ctx.hv_iface.node) orelse
                return visitor.VisitResult(void){ .CONTINUE = {} };
            if (other.is_same(ctx.lv_iface.node)) ctx.found = true;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var ctx: Ctx = .{ .hv_iface = hv_iface, .lv_iface = lv_iface };
    switch (faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(hv_iface, &ctx, Ctx.visit)) {
        .ERROR => @panic("visit_connected_edges failed"),
        else => {},
    }
    try std.testing.expect(ctx.found);
}

test "basic+10 declared and dependant edge interaction" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const bound = Node.bind_typegraph(ElectricPowerMixedEdges, &tg);
    const power = bound.create_instance(&g);

    const hv = power.hv.get().node.instance;
    const lv = power.lv.get().node.instance;
    const hv_iface = power.hv.get()._is_interface.get().node.instance;
    const lv_iface = power.lv.get()._is_interface.get().node.instance;

    const Ctx = struct {
        hv: graph.BoundNodeReference,
        lv: graph.BoundNodeReference,
        hv_iface: graph.BoundNodeReference,
        lv_iface: graph.BoundNodeReference,
        found_hv_lv: bool = false,
        found_iface_iface: bool = false,

        fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            if (!faebryk.interface.EdgeInterfaceConnection.is_instance(be.edge)) return visitor.VisitResult(void){ .CONTINUE = {} };

            if (faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(be.edge, ctx.hv.node)) |other| {
                if (other.is_same(ctx.lv.node)) ctx.found_hv_lv = true;
            }
            if (faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(be.edge, ctx.hv_iface.node)) |other| {
                if (other.is_same(ctx.lv_iface.node)) ctx.found_iface_iface = true;
            }
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var ctx: Ctx = .{
        .hv = hv,
        .lv = lv,
        .hv_iface = hv_iface,
        .lv_iface = lv_iface,
    };
    switch (faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(hv, &ctx, Ctx.visit)) {
        .ERROR => @panic("visit_connected_edges failed"),
        else => {},
    }
    switch (faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(hv_iface, &ctx, Ctx.visit)) {
        .ERROR => @panic("visit_connected_edges failed"),
        else => {},
    }

    try std.testing.expect(ctx.found_hv_lv);
    try std.testing.expect(ctx.found_iface_iface);
}

test "basic+11 declared dependant edge" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const bound = Node.bind_typegraph(ElectricPowerDeclaredDependantEdge, &tg);
    const power = bound.create_instance(&g);
    const hv = power.hv.get().node.instance;
    const lv = power.lv.get().node.instance;

    const Ctx = struct {
        hv: graph.BoundNodeReference,
        lv: graph.BoundNodeReference,
        found: bool = false,

        fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            if (!faebryk.interface.EdgeInterfaceConnection.is_instance(be.edge)) return visitor.VisitResult(void){ .CONTINUE = {} };
            const other = faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(be.edge, ctx.hv.node) orelse
                return visitor.VisitResult(void){ .CONTINUE = {} };
            if (other.is_same(ctx.lv.node)) ctx.found = true;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var ctx: Ctx = .{ .hv = hv, .lv = lv };
    switch (faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(hv, &ctx, Ctx.visit)) {
        .ERROR => @panic("visit_connected_edges failed"),
        else => {},
    }
    try std.testing.expect(ctx.found);
}

test "basic+12 declared dependant child then declared edge" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const bound = Node.bind_typegraph(ElectricPowerDeclaredDependantChildThenEdge, &tg);
    const power = bound.create_instance(&g);

    const lv = power.lv.get().node.instance;
    const sense = faebryk.composition.EdgeComposition.get_child_by_identifier(power.node.instance, "sense") orelse
        @panic("missing sense child");

    const Ctx = struct {
        sense: graph.BoundNodeReference,
        lv: graph.BoundNodeReference,
        found: bool = false,

        fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            if (!faebryk.interface.EdgeInterfaceConnection.is_instance(be.edge)) return visitor.VisitResult(void){ .CONTINUE = {} };
            const other = faebryk.interface.EdgeInterfaceConnection.get_other_connected_node(be.edge, ctx.sense.node) orelse
                return visitor.VisitResult(void){ .CONTINUE = {} };
            if (other.is_same(ctx.lv.node)) ctx.found = true;
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var ctx: Ctx = .{ .sense = sense, .lv = lv };
    switch (faebryk.interface.EdgeInterfaceConnection.visit_connected_edges(sense, &ctx, Ctx.visit)) {
        .ERROR => @panic("visit_connected_edges failed"),
        else => {},
    }
    try std.testing.expect(ctx.found);
}
