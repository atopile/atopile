const graph_mod = @import("graph");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const std = @import("std");
const faebryk = @import("faebryk");
const fabll = faebryk.fabll;
const units = @import("units.zig");
const literals = @import("literals.zig");

pub const is_trait = struct {
    node: fabll.Node,

    pub fn MakeEdge(comptime traitchildfield: type, comptime owner: ?fabll.RefPath) type {
        const owner_path = owner orelse fabll.RefPath.self();
        return traitchildfield.add_dependant(
            fabll.MakeDependantEdge(
                owner_path,
                fabll.RefPath.owner_child(),
                faebryk.trait.EdgeTrait,
            ),
        );
    }

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }
};

pub const can_be_operand = struct {
    node: fabll.Node,
    _is_trait: is_trait.MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn get_owner_node(self: @This()) ?graph.BoundNodeReference {
        if (faebryk.composition.EdgeComposition.get_parent_node_of(self.node.instance)) |parent| {
            return parent;
        }
        return faebryk.trait.EdgeTrait.get_owner_node_of(self.node.instance);
    }
};

pub const is_parameter = struct {
    node: fabll.Node,
    _is_trait: is_trait.MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }
};

pub const is_parameter_operatable = struct {
    node: fabll.Node,
    _is_trait: is_trait.MakeChild(),
    const superset_identifier = "superset";

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    fn next_superset_index(self: @This()) u15 {
        const Ctx = struct {
            max_idx: u15 = 0,
            seen: bool = false,

            fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const idx = faebryk.pointer.EdgePointer.get_index(be.edge) orelse 0;
                if (!ctx.seen or idx > ctx.max_idx) {
                    ctx.max_idx = idx;
                    ctx.seen = true;
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var ctx = Ctx{};
        _ = faebryk.pointer.EdgePointer.visit_pointed_edges_with_identifier(self.node.instance, superset_identifier, void, &ctx, Ctx.visit);
        return if (ctx.seen) std.math.add(u15, ctx.max_idx, 1) catch @panic("superset pointer index overflow") else 0;
    }

    pub fn set_superset_node(self: @This(), value: graph.BoundNodeReference) void {
        const idx = self.next_superset_index();
        _ = faebryk.pointer.EdgePointer.point_to(self.node.instance, value.node, superset_identifier, idx) catch
            @panic("failed to point superset");
    }

    pub fn try_get_superset_node(self: @This()) ?graph.BoundNodeReference {
        const Ctx = struct {
            best_idx: u15 = 0,
            best: ?graph.BoundNodeReference = null,

            fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const idx = faebryk.pointer.EdgePointer.get_index(be.edge) orelse 0;
                if (ctx.best == null or idx >= ctx.best_idx) {
                    ctx.best_idx = idx;
                    ctx.best = be.g.bind(faebryk.pointer.EdgePointer.get_referenced_node(be.edge));
                }
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var ctx = Ctx{};
        switch (faebryk.pointer.EdgePointer.visit_pointed_edges_with_identifier(self.node.instance, superset_identifier, void, &ctx, Ctx.visit)) {
            .ERROR => return null,
            else => {},
        }
        return ctx.best;
    }

    pub fn try_extract_superset(self: @This(), comptime LitType: type) ?LitType {
        const superset = self.try_get_superset_node() orelse return null;
        var tg = self.node.typegraph();
        const lit_type = tg.get_type_by_name(@typeName(LitType)) orelse return null;
        if (!faebryk.node_type.EdgeType.is_node_instance_of(superset, lit_type.node)) return null;
        return fabll.Node.bind_instance(LitType, superset);
    }

    pub fn force_extract_superset(self: @This(), comptime LitType: type) LitType {
        return self.try_extract_superset(LitType) orelse
            @panic("parameter superset is missing or has wrong literal type");
    }
};

pub const NumericParameter = struct {
    node: fabll.Node,
    is_parameter: is_trait.MakeEdge(is_parameter.MakeChild(), null),
    is_parameter_operatable: is_trait.MakeEdge(is_parameter_operatable.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(can_be_operand.MakeChild(), null),
    unit_trait: is_trait.MakeEdge(units.has_unit.MakeChild(), null),
    display_unit_trait: is_trait.MakeEdge(units.has_display_unit.MakeChild(), null),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup_units(self: @This(), unit: ?units.is_unit, display_unit: ?units.is_unit) @This() {
        if (unit) |u| {
            _ = self.unit_trait.get().setup(u);
        }
        if (display_unit) |du| {
            _ = self.display_unit_trait.get().setup(du);
        }
        return self;
    }

    pub fn try_get_units(self: @This()) ?units.is_unit {
        return self.unit_trait.get().try_get_is_unit();
    }

    pub fn force_get_units(self: @This()) units.is_unit {
        return self.unit_trait.get().get_is_unit();
    }

    pub fn try_get_display_units(self: @This()) ?units.is_unit {
        if (self.display_unit_trait.get().try_get_is_unit()) |du| return du;
        return self.try_get_units();
    }

    pub fn force_get_display_units(self: @This()) units.is_unit {
        return self.try_get_display_units() orelse self.force_get_units();
    }
};

pub const StringParameter = struct {
    node: fabll.Node,
    is_parameter: is_trait.MakeEdge(is_parameter.MakeChild(), null),
    is_parameter_operatable: is_trait.MakeEdge(is_parameter_operatable.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(can_be_operand.MakeChild(), null),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn set_superset(self: @This(), values: []const []const u8) @This() {
        var tg = self.node.typegraph();
        const lit = fabll.Node.bind_typegraph(literals.Strings, &tg).create_instance(self.node.instance.g).setup_from_values(values);
        self.is_parameter_operatable.get().set_superset_node(lit.node.instance);
        return self;
    }

    pub fn set_singleton(self: @This(), value: []const u8) @This() {
        return self.set_superset(&.{value});
    }

    pub fn try_extract_superset(self: @This()) ?literals.Strings {
        return self.is_parameter_operatable.get().try_extract_superset(literals.Strings);
    }

    pub fn force_extract_superset(self: @This()) literals.Strings {
        return self.is_parameter_operatable.get().force_extract_superset(literals.Strings);
    }

    pub fn try_extract_singleton(self: @This(), allocator: std.mem.Allocator) !?[]const u8 {
        const superset = self.try_extract_superset() orelse return null;
        if (!try superset.is_singleton(allocator)) return null;
        return try superset.get_single(allocator);
    }

    pub fn extract_singleton(self: @This(), allocator: std.mem.Allocator) ![]const u8 {
        return (try self.try_extract_singleton(allocator)) orelse error.NotSingleton;
    }
};

pub const BooleanParameter = struct {
    node: fabll.Node,
    is_parameter: is_trait.MakeEdge(is_parameter.MakeChild(), null),
    is_parameter_operatable: is_trait.MakeEdge(is_parameter_operatable.MakeChild(), null),
    can_be_operand: is_trait.MakeEdge(can_be_operand.MakeChild(), null),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn set_superset(self: @This(), values: []const bool) @This() {
        var tg = self.node.typegraph();
        const lit = literals.Booleans.create_instance(self.node.instance.g, &tg).setup_from_values(values);
        self.is_parameter_operatable.get().set_superset_node(lit.node.instance);
        return self;
    }

    pub fn set_singleton(self: @This(), value: bool) @This() {
        return self.set_superset(&.{value});
    }

    pub fn try_extract_superset(self: @This()) ?literals.Booleans {
        return self.is_parameter_operatable.get().try_extract_superset(literals.Booleans);
    }

    pub fn force_extract_superset(self: @This()) literals.Booleans {
        return self.is_parameter_operatable.get().force_extract_superset(literals.Booleans);
    }

    pub fn try_extract_singleton(self: @This(), allocator: std.mem.Allocator) !?bool {
        const superset = self.try_extract_superset() orelse return null;
        if (!try superset.is_singleton(allocator)) return null;
        return try superset.get_single(allocator);
    }

    pub fn force_extract_singleton(self: @This(), allocator: std.mem.Allocator) !bool {
        return (try self.try_extract_singleton(allocator)) orelse error.NotSingleton;
    }
};

test "parameters numeric parameter unit traits" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p = NumericParameter.create_instance(&g, &tg);
    try std.testing.expect(p.try_get_units() == null);

    const base_v = units.to_is_unit(units.Volt.create_instance(&g, &tg));
    const display_mv = units.to_is_unit(units.MilliVolt.create_instance(&g, &tg));
    _ = p.setup_units(base_v, display_mv);

    try std.testing.expect(p.try_get_units() != null);
    try std.testing.expect(p.try_get_display_units() != null);
    try std.testing.expect(std.mem.eql(u8, p.force_get_units().get_symbol(), "V"));
    try std.testing.expect(std.mem.eql(u8, p.force_get_display_units().get_symbol(), "mV"));
}

test "parameters string parameter superset and singleton" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p = StringParameter.create_instance(&g, &tg);
    try std.testing.expect(p.try_extract_superset() == null);

    _ = p.set_superset(&.{ "A", "B" });
    try std.testing.expect(p.try_extract_superset() != null);
    try std.testing.expect((try p.try_extract_singleton(std.testing.allocator)) == null);

    _ = p.set_singleton("ONLY");
    const single = try p.extract_singleton(std.testing.allocator);
    try std.testing.expect(std.mem.eql(u8, single, "ONLY"));
}

test "parameters boolean parameter superset and singleton" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const p = BooleanParameter.create_instance(&g, &tg);
    try std.testing.expect(p.try_extract_superset() == null);

    _ = p.set_superset(&.{ true, false });
    try std.testing.expect(p.try_extract_superset() != null);
    try std.testing.expect((try p.try_extract_singleton(std.testing.allocator)) == null);

    _ = p.set_singleton(true);
    try std.testing.expect(try p.force_extract_singleton(std.testing.allocator));
}
