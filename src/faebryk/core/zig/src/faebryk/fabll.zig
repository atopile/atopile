const std = @import("std");
const graph_mod = @import("graph");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const faebryk = @import("faebryk");
const str = []const u8;

fn is_child_field_type(comptime MaybeChildField: type) bool {
    return @typeInfo(MaybeChildField) == .@"struct" and
        @hasField(MaybeChildField, "field") and
        @hasField(MaybeChildField, "T");
}

fn visit_fields(
    comptime T: type,
    comptime R: type,
    ctx: *anyopaque,
    comptime f: fn (*anyopaque, []const u8, ChildField) visitor.VisitResult(R),
) visitor.VisitResult(R) {
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

    pub fn MakeChild(comptime T: type) ChildField {
        return ChildField{
            .field = .{
                .identifier = null,
                .locator = null,
            },
            .T = T,
        };
    }

    pub fn MakeChildNamed(comptime T: type, comptime identifier: []const u8) ChildField {
        return ChildField{
            .field = .{
                .identifier = identifier,
                .locator = null,
            },
            .T = T,
        };
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

                fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, value: ChildField) visitor.VisitResult(void) {
                    const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                    const child_bound = Node.bind_typegraph(value.T, ctx.self.tg);
                    const child_type = child_bound.get_or_create_type();
                    const child_identifier = field_identifier(decl_name, value);
                    _ = ctx.self.tg.add_make_child(ctx.type_node, child_type, child_identifier, null, false) catch
                        @panic("failed to add make child");

                    if (value.trait_owner_is_self) {
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

    if (comptime @hasDecl(T, "__fabll_bind")) {
        return T.__fabll_bind(instance);
    }

    return .{
        .node = .{
            .instance = instance,
        },
    };
}

fn field_identifier(decl_name: []const u8, field: ChildField) []const u8 {
    return field.field.identifier orelse decl_name;
}

pub fn InstanceChildBoundInstance(comptime T: type) type {
    return struct {
        parent_instance: graph.BoundNodeReference,
        identifier: []const u8,

        pub fn get(self: @This()) T {
            const child = faebryk.composition.EdgeComposition.get_child_by_identifier(
                self.parent_instance,
                self.identifier,
            ) orelse @panic("child not found");
            return wrap_instance(T, child);
        }
    };
}

pub const Field = struct {
    identifier: ?str,
    locator: ?str,
};

pub const FieldE = union(enum) {
    ChildField: ChildField,
    EdgeField: EdgeField,
};

pub const ChildField = struct {
    field: Field,
    T: type,
    trait_owner_is_self: bool = false,

    pub fn add_dependant(self: *@This(), dependant: FieldE) void {
        _ = self;
        _ = dependant;
    }

    pub fn add_as_dependant(self: *@This(), to: *ChildField) void {
        _ = self;
        _ = to;
    }
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

    pub fn MakeEdge(traitchildfield: ChildField, owner: ?RefPath) ChildField {
        _ = owner;
        var out = traitchildfield;
        out.trait_owner_is_self = true;
        return out;
    }

    pub fn MakeChild() ChildField {
        return Node.MakeChild(@This());
    }
};

pub const is_interface = struct {
    node: Node,
    pub const _is_trait = is_trait.MakeChild();

    pub fn MakeConnectionEdge(n1: RefPath, n2: RefPath, shallow: bool) void {
        _ = n1;
        _ = n2;
        _ = shallow;
    }

    pub fn MakeChild() ChildField {
        return Node.MakeChild(@This());
    }
};

pub const Electrical = struct {
    node: Node,

    pub const _is_interface = is_trait.MakeEdge(is_interface.MakeChild(), null);

    pub fn MakeChild() ChildField {
        return Node.MakeChild(@This());
    }
};

pub const ElectricPower = struct {
    node: Node,

    hv: InstanceChildBoundInstance(Electrical),
    lv: InstanceChildBoundInstance(Electrical),

    pub const hv_recipe = Node.MakeChildNamed(Electrical, "hv");
    pub const lv_recipe = Node.MakeChildNamed(Electrical, "lv");

    pub fn __fabll_bind(instance: graph.BoundNodeReference) @This() {
        return .{
            .node = .{
                .instance = instance,
            },
            .hv = .{
                .parent_instance = instance,
                .identifier = "hv",
            },
            .lv = .{
                .parent_instance = instance,
                .identifier = "lv",
            },
        };
    }
};

fn comptime_child_field_count(comptime T: type) usize {
    const Ctx = struct {
        count: usize = 0,

        fn visit(ctx_ptr: *anyopaque, _: []const u8, _: ChildField) visitor.VisitResult(void) {
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

        fn visit(ctx_ptr: *anyopaque, decl_name: []const u8, field: ChildField) visitor.VisitResult([]const u8) {
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
