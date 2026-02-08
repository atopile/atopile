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

        pub fn create_instance(self: @This(), g: *graph.GraphView) T {
            const type_node = self.get_or_create_type();
            if (type_node.g != g) {
                @panic("create_instance graph must match the bound typegraph graph");
            }

            const result = self.tg.instantiate_node(type_node);
            const instance = switch (result) {
                .ok => |n| n,
                .err => |err| {
                    std.debug.print("fabll instantiate failed: {s}\n", .{err.message});
                    @panic("fabll instantiate failed");
                },
            };

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

pub const ChildFieldOptions = struct {
    identifier: ?str = null,
    trait_owner_is_self: bool = false,
};

pub const ChildAttribute = struct {
    key: str,
    value: graph.Literal,
};

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

    pub fn MakeChild(val: f64) type {
        return Node.MakeChildWithAttrs(
            @This(),
            &.{.{ .key = "number", .value = .{ .Float = val } }},
        );
    }
};

pub const NumberContainer = struct {
    node: Node,

    n: Number.MakeChild(3.14),
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

    const num_attr = number.node.instance.node.get("number") orelse
        @panic("missing number attr on Number");
    try std.testing.expectApproxEqAbs(@as(f64, 3.14), num_attr.Float, 1e-9);
}
