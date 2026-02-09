const graph_mod = @import("graph");
const graph = graph_mod.graph;
const std = @import("std");
const faebryk = @import("faebryk");
const fabll = @import("fabll.zig");
const units = @import("units.zig");

pub const can_be_operand = struct {
    node: fabll.Node,

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

pub const is_parameter_operatable = struct {
    node: fabll.Node,

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }
};

pub const NumericParameter = struct {
    node: fabll.Node,
    is_parameter_operatable: is_parameter_operatable.MakeChild(),
    can_be_operand: can_be_operand.MakeChild(),
    unit_trait: units.has_unit.MakeChild(),
    display_unit_trait: units.has_display_unit.MakeChild(),

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
