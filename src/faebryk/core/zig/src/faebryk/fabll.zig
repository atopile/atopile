const std = @import("std");
const graph_mod = @import("graph");
const graph = graph_mod.graph;
const faebryk = @import("faebryk");
const str = []const u8;

fn is_child_field_type(comptime MaybeChildField: type) bool {
    return @typeInfo(MaybeChildField) == .@"struct" and
        @hasField(MaybeChildField, "field") and
        @hasField(MaybeChildField, "T");
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
            const identifier = @typeName(T);
            if (self.tg.get_type_by_name(identifier)) |existing| {
                return existing;
            }

            const type_node = self.tg.add_type(identifier) catch |err| switch (err) {
                error.TypeAlreadyExists => self.tg.get_type_by_name(identifier) orelse unreachable,
                else => @panic("failed to add type"),
            };

            const decls = @typeInfo(T).@"struct".decls;
            inline for (decls) |decl| {
                const value = @field(T, decl.name);
                if (comptime is_child_field_type(@TypeOf(value))) {
                    const child_bound = Node.bind_typegraph(value.T, self.tg);
                    const child_type = child_bound.get_or_create_type();
                    const child_identifier = value.field.identifier orelse decl.name;
                    _ = self.tg.add_make_child(type_node, child_type, child_identifier, null, false) catch
                        @panic("failed to add make child");
                }
            }

            return type_node;
        }
    };
}

fn wrap_instance(comptime T: type, instance: graph.BoundNodeReference) T {
    comptime if (!@hasField(T, "node")) {
        @compileError("FabLL Zig node types must have a `node: Node` field");
    };

    return .{
        .node = .{
            .instance = instance,
        },
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

pub const is_trait = struct {
    node: Node,

    pub fn MakeEdge(traitchildfield: ChildField, owner: ?RefPath) ChildField {
        _ = owner;
        return traitchildfield;
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

    pub const hv = Electrical.MakeChild();
    pub const lv = Electrical.MakeChild();
};

fn comptime_child_field_count(comptime T: type) usize {
    comptime var count: usize = 0;
    const decls = @typeInfo(T).@"struct".decls;
    inline for (decls) |decl| {
        if (comptime is_child_field_type(@TypeOf(@field(T, decl.name)))) {
            count += 1;
        }
    }
    return count;
}

fn comptime_child_field_name(comptime T: type, comptime idx: usize) []const u8 {
    comptime var i: usize = 0;
    const decls = @typeInfo(T).@"struct".decls;
    inline for (decls) |decl| {
        if (comptime is_child_field_type(@TypeOf(@field(T, decl.name)))) {
            if (i == idx) return decl.name;
            i += 1;
        }
    }
    @compileError("child field index out of bounds");
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
    try std.testing.expect(std.mem.eql(u8, comptime_child_field_name(ElectricPower, 0), "hv_lowlevel"));
    try std.testing.expect(std.mem.eql(u8, comptime_child_field_name(ElectricPower, 1), "hv_highlevel"));
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
