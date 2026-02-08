const std = @import("std");
const graph_mod = @import("graph");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const faebryk = @import("faebryk");
const str = []const u8;

fn is_child_field_type(comptime MaybeChildField: type) bool {
    return @typeInfo(MaybeChildField) == .@"struct" and
        @hasDecl(MaybeChildField, "ChildType") and
        @hasDecl(MaybeChildField, "Options");
}

fn AttributesType(comptime T: type) type {
    return if (@hasDecl(T, "Attributes")) T.Attributes else struct {};
}

fn requires_instance_attrs(comptime T: type) bool {
    if (@hasDecl(T, "RequireCreateInstanceAttrs")) {
        return T.RequireCreateInstanceAttrs;
    }
    return false;
}

pub const CreateInstanceMode = enum {
    generic,
    requires_attrs,
};

fn create_instance_mode(comptime T: type) CreateInstanceMode {
    if (@hasDecl(T, "CreateInstanceMode")) {
        return T.CreateInstanceMode;
    }
    if (@hasDecl(T, "Attributes")) {
        return .requires_attrs;
    }
    if (requires_instance_attrs(T)) {
        return .requires_attrs;
    }
    return .generic;
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

pub const Node = struct {
    instance: graph.BoundNodeReference,

    pub fn MakeChild(comptime T: type) type {
        return ChildField(T, .{}, &.{});
    }

    pub fn MakeChildWith(comptime T: type, comptime options: ChildFieldOptions) type {
        return ChildField(T, options, &.{});
    }

    pub fn MakeChildWithAttrs(comptime T: type, comptime attributes: []const ChildAttribute) type {
        return ChildField(T, .{}, attributes);
    }

    pub fn MakeChildNamed(comptime T: type, comptime identifier: []const u8) type {
        return ChildField(T, .{ .identifier = identifier }, &.{});
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
            if (comptime create_instance_mode(T) == .requires_attrs) {
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
            const identifier = @typeName(T);
            if (self.tg.get_type_by_name(identifier)) |existing| {
                return existing;
            }

            const type_node = self.tg.add_type(identifier) catch |err| switch (err) {
                error.TypeAlreadyExists => self.tg.get_type_by_name(identifier) orelse unreachable,
                else => @panic("failed to add type"),
            };

            const BuildContext = struct {
                self: Self,
                type_node: graph.BoundNodeReference,

                fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, field_type: type) visitor.VisitResult(void) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    const child_bound = Node.bind_typegraph(field_type.ChildType, ctx.self.tg);
                    const child_type = child_bound.get_or_create_type();
                    const child_identifier = field_identifier(decl_name, field_type);
                    var node_attrs: faebryk.nodebuilder.NodeCreationAttributes = .{
                        .dynamic = graph.DynamicAttributes.init_on_stack(),
                    };
                    for (field_type.Attributes) |attr| {
                        node_attrs.dynamic.put(attr.key, attr.value);
                    }
                    const node_attrs_ptr: ?*faebryk.nodebuilder.NodeCreationAttributes = if (field_type.Attributes.len > 0)
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

                    if (field_type.Options.trait_owner_is_self) {
                        const lhs_ref = faebryk.typegraph.TypeGraph.ChildReferenceNode.create_and_insert(
                            ctx.self.tg,
                            &.{faebryk.composition.EdgeComposition.traverse("")},
                        ) catch @panic("failed to build trait lhs reference");
                        const rhs_ref = faebryk.typegraph.TypeGraph.ChildReferenceNode.create_and_insert(
                            ctx.self.tg,
                            &.{faebryk.composition.EdgeComposition.traverse(child_identifier)},
                        ) catch @panic("failed to build trait rhs reference");

                        _ = ctx.self.tg.add_make_link(
                            ctx.type_node,
                            lhs_ref,
                            rhs_ref,
                            faebryk.trait.EdgeTrait.build(),
                        ) catch @panic("failed to add trait make link");
                    }

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

            return type_node;
        }
    };
}

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

fn field_identifier(decl_name: []const u8, field_type: type) []const u8 {
    return field_type.Options.identifier orelse decl_name;
}

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

pub const ChildFieldOptions = struct {
    identifier: ?str = null,
    trait_owner_is_self: bool = false,
};

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

pub fn ChildField(
    comptime T: type,
    comptime options: ChildFieldOptions,
    comptime attributes: []const ChildAttribute,
) type {
    return struct {
        pub const ChildType = T;
        pub const Options = options;
        pub const Attributes = attributes;
        parent_instance: ?graph.BoundNodeReference = null,
        locator: ?str = null,

        pub fn get(self: @This()) T {
            const parent = self.parent_instance orelse @panic("child field is not bound");
            const identifier = Options.identifier orelse self.locator orelse
                @panic("child field has no identifier or locator");
            const child = faebryk.composition.EdgeComposition.get_child_by_identifier(
                parent,
                identifier,
            ) orelse @panic("child not found");
            return wrap_instance(T, child);
        }

        pub fn add_dependant(self: *@This(), dependant: anytype) void {
            _ = self;
            _ = dependant;
        }

        pub fn add_as_dependant(self: *@This(), to: anytype) void {
            _ = self;
            _ = to;
        }
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
    pub const Element = enum {};
    path: std.ArrayList(Element),
};

// TESTING ====================================================================

pub const is_trait = struct {
    node: Node,

    pub fn MakeEdge(comptime traitchildfield: type, owner: ?RefPath) type {
        _ = owner;
        return ChildField(
            traitchildfield.ChildType,
            // TODO: remove hack with trait_owner_is_self as soon as dependant logic works
            .{
                .identifier = traitchildfield.Options.identifier,
                .trait_owner_is_self = true,
            },
            traitchildfield.Attributes,
        );
    }

    pub fn MakeChild() type {
        return Node.MakeChild(@This());
    }

    pub fn MakeChildWith(comptime options: ChildFieldOptions) type {
        return Node.MakeChildWith(@This(), options);
    }
};

pub const is_interface = struct {
    node: Node,
    _is_trait: is_trait.MakeChild(),

    pub fn MakeConnectionEdge(n1: RefPath, n2: RefPath, shallow: bool) void {
        _ = n1;
        _ = n2;
        _ = shallow;
    }

    pub fn MakeChild() type {
        return Node.MakeChild(@This());
    }
};

pub const Electrical = struct {
    node: Node,

    _is_interface: is_trait.MakeEdge(is_interface.MakeChild(), null),

    pub fn MakeChild() type {
        return Node.MakeChild(@This());
    }
};

pub const ElectricPower = struct {
    node: Node,

    hv: Electrical.MakeChild(),
    lv: Electrical.MakeChild(),
};

pub const Number = struct {
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

pub const NumberContainer = struct {
    node: Node,

    n: Number.MakeChild(.{ .number = 3.14 }),
};

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

fn print_type_overview(tg: *faebryk.typegraph.TypeGraph, allocator: std.mem.Allocator, label: []const u8) void {
    var overview = tg.get_type_instance_overview(allocator);
    defer overview.deinit();

    std.debug.print("\nType overview ({s}):\n", .{label});
    for (overview.items) |item| {
        std.debug.print("  {s}: {d} instances\n", .{ item.type_name, item.instance_count });
    }
}

test "comptime child field discovery" {
    try std.testing.expectEqual(@as(usize, 2), comptime_child_field_count(ElectricPower));
    try std.testing.expect(std.mem.eql(u8, comptime_child_field_name(ElectricPower, 0), "hv"));
    try std.testing.expect(std.mem.eql(u8, comptime_child_field_name(ElectricPower, 1), "lv"));
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
