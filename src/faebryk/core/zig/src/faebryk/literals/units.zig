const std = @import("std");
const graph_mod = @import("graph");
const GraphView = graph_mod.graph.GraphView;
const BoundNodeReference = graph_mod.graph.BoundNodeReference;

const faebryk = @import("faebryk");
const Trait = faebryk.trait.Trait;
const EdgeComposition = faebryk.composition.EdgeComposition;
const TypeGraph = faebryk.typegraph.TypeGraph;
const EdgeOperand = faebryk.operand.EdgeOperand;
const EdgeType = faebryk.node_type.EdgeType;

const Numeric = @import("magnitude_sets.zig").Numeric;
const visitor = graph_mod.visitor;

pub const Parameter = struct {
    instance: BoundNodeReference,

    pub const Error = error{
        TypeGraphNotFound,
    };

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Parameter");
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Parameter {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn of(node: BoundNodeReference) Parameter {
        return .{ .instance = node };
    }

    pub fn constrain_to_literal(self: Parameter, literal: BoundNodeReference) !void {
        var tg = TypeGraph.of_instance(self.instance) orelse return Error.TypeGraphNotFound;
        try AliasIs.alias_is(&tg, self.instance, literal);
    }

    pub fn try_extract_constrained_literal(self: Parameter) !?Numeric {
        const inbound_expr_edge = EdgeOperand.get_expression_edge(self.instance) orelse return null;
        const expr_node_ref = EdgeOperand.get_expression_node(inbound_expr_edge.edge);
        const expr_node = graph_mod.graph.BoundNodeReference{ .g = inbound_expr_edge.g, .node = expr_node_ref };

        var found: ?Numeric = null;
        const Finder = struct {
            target: *?Numeric,
            pub fn visit(self_ptr: *anyopaque, operand_edge: graph_mod.graph.BoundEdgeReference) visitor.VisitResult(void) {
                const finder: *@This() = @ptrCast(@alignCast(self_ptr));
                const operand_ref = EdgeOperand.get_operand_node(operand_edge.edge);
                const operand_graph = operand_edge.g;
                const bound_operand = graph_mod.graph.BoundNodeReference{ .g = operand_graph, .node = operand_ref };
                const numeric = Numeric.of(bound_operand);
                _ = numeric.get_value() catch return visitor.VisitResult(void){ .CONTINUE = {} };
                finder.target.* = numeric;
                return visitor.VisitResult(void){ .STOP = {} };
            }
        };

        var finder = Finder{ .target = &found };
        _ = EdgeOperand.visit_operand_edges(expr_node, void, &finder, Finder.visit);
        return found;
    }
};

pub const AliasIs = struct {
    instance: BoundNodeReference,

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("AliasIs");
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !AliasIs {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn of(node: BoundNodeReference) !AliasIs {
        return AliasIs{
            .instance = node,
        };
    }

    pub fn alias_is(tg: *TypeGraph, param: BoundNodeReference, literal: BoundNodeReference) !void {
        const alias_is_node = try create_instance(tg);
        _ = EdgeOperand.add_operand(alias_is_node.instance, param.node, null);
        _ = EdgeOperand.add_operand(alias_is_node.instance, literal.node, null);
    }
};

pub const is_base_unit = struct {
    instance: BoundNodeReference,

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("is_base_unit");
        const parameter_type = try Parameter.get_or_create_type(tg);

        try Trait.mark_as_trait(type_node);
        _ = try tg.add_make_child(type_node, parameter_type, "symbol");
        _ = try tg.add_make_child(type_node, parameter_type, "exponent");

        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !is_base_unit {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn get_exponent_param(self: *@This()) !BoundNodeReference {
        return EdgeComposition.get_child_by_identifier(self.instance, "exponent") orelse return error.ExponentNotFound;
    }

    pub fn setup(self: *@This(), exponent: i64) !void {
        const exponent_param = try self.get_exponent_param();
        const exponent_literal = Numeric.init(self.instance.g, @floatFromInt(exponent));

        var tg = TypeGraph.of_instance(self.instance) orelse return error.TypeGraphNotFound;
        try AliasIs.alias_is(&tg, exponent_param, exponent_literal.node);
    }

    pub fn of(node: BoundNodeReference) !is_base_unit {
        return is_base_unit{
            .instance = node,
        };
    }
};

test "units.is_base_unit.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    var base_unit = try is_base_unit.create_instance(&tg);
    const exponent = 2;
    try base_unit.setup(exponent);

    // Get the exponent node
    const exponent_node = try base_unit.get_exponent_param();
    const parameter = Parameter.of(exponent_node);

    const literal_numeric = try parameter.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    const exponent_value = try literal_numeric.get_value();
    try std.testing.expectEqual(@as(f64, @floatFromInt(exponent)), exponent_value);
}

pub const is_unit = struct {
    instance: BoundNodeReference,

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("is_unit");
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !is_unit {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn of(node: BoundNodeReference) !is_unit {
        return is_unit{
            .instance = node,
        };
    }
};

test "units.is_unit.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    _ = try is_unit.create_instance(&tg);
}

pub const Meter = struct {
    instance: BoundNodeReference,

    const base_unit_identifier = "base_unit";

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Meter");
        if (EdgeComposition.get_child_by_identifier(type_node, base_unit_identifier) == null) {
            _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), "unit");
            _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), base_unit_identifier);
        }
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Meter {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn setup(self: @This(), exponent: i64) !void {
        const base_unit_node = EdgeComposition.get_child_by_identifier(self.instance, base_unit_identifier) orelse return error.BaseUnitNotFound;
        var base_unit = try is_base_unit.of(base_unit_node);
        try base_unit.setup(exponent);
    }

    pub fn of(node: BoundNodeReference) Meter {
        return Meter{
            .instance = node,
        };
    }
};

test "units.Meter.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    const exponent = 1;
    var meter = try Meter.create_instance(&tg);
    try meter.setup(exponent);

    const base_unit_node = EdgeComposition.get_child_by_identifier(meter.instance, Meter.base_unit_identifier) orelse return error.BaseUnitNotFound;
    var base_unit = try is_base_unit.of(base_unit_node);
    const exponent_param = try base_unit.get_exponent_param();
    const parameter = Parameter.of(exponent_param);
    const literal_numeric = try parameter.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    const exponent_value = try literal_numeric.get_value();
    try std.testing.expectEqual(@as(f64, @floatFromInt(exponent)), exponent_value);
}

pub const Kilogram = struct {
    instance: BoundNodeReference,

    const base_unit_identifier = "base_unit";

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Kilogram");
        if (EdgeComposition.get_child_by_identifier(type_node, base_unit_identifier) == null) {
            _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), "unit");
            _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), base_unit_identifier);
        }
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Kilogram {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn setup(self: @This(), exponent: i64) !void {
        const base_unit_node = EdgeComposition.get_child_by_identifier(self.instance, base_unit_identifier) orelse return error.BaseUnitNotFound;
        var base_unit = try is_base_unit.of(base_unit_node);
        try base_unit.setup(exponent);
    }

    pub fn of(node: BoundNodeReference) Kilogram {
        return Kilogram{
            .instance = node,
        };
    }
};

test "units.Kilogram.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    const exponent = 1;
    var kilogram = try Kilogram.create_instance(&tg);
    try kilogram.setup(exponent);

    const base_unit_node = EdgeComposition.get_child_by_identifier(kilogram.instance, Kilogram.base_unit_identifier) orelse return error.BaseUnitNotFound;
    var base_unit = try is_base_unit.of(base_unit_node);
    const exponent_param = try base_unit.get_exponent_param();
    const parameter = Parameter.of(exponent_param);
    const literal_numeric = try parameter.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    const exponent_value = try literal_numeric.get_value();
    try std.testing.expectEqual(@as(f64, @floatFromInt(exponent)), exponent_value);
}

pub const Second = struct {
    instance: BoundNodeReference,

    const base_unit_identifier = "base_unit";

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Second");
        if (EdgeComposition.get_child_by_identifier(type_node, base_unit_identifier) == null) {
            _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), "unit");
            _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), base_unit_identifier);
        }
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Second {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn setup(self: @This(), exponent: i64) !void {
        const base_unit_node = EdgeComposition.get_child_by_identifier(self.instance, base_unit_identifier) orelse return error.BaseUnitNotFound;
        var base_unit = try is_base_unit.of(base_unit_node);
        try base_unit.setup(exponent);
    }

    pub fn of(node: BoundNodeReference) Second {
        return Second{
            .instance = node,
        };
    }
};

test "units.Second.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    const exponent = 1;
    var second = try Second.create_instance(&tg);
    try second.setup(exponent);

    const base_unit_node = EdgeComposition.get_child_by_identifier(second.instance, Second.base_unit_identifier) orelse return error.BaseUnitNotFound;
    var base_unit = try is_base_unit.of(base_unit_node);
    const exponent_param = try base_unit.get_exponent_param();
    const parameter = Parameter.of(exponent_param);
    const literal_numeric = try parameter.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    const exponent_value = try literal_numeric.get_value();
    try std.testing.expectEqual(@as(f64, @floatFromInt(exponent)), exponent_value);
}

pub const Ampere = struct {
    instance: BoundNodeReference,

    const base_unit_identifier = "base_unit";

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Ampere");
        if (EdgeComposition.get_child_by_identifier(type_node, base_unit_identifier) == null) {
            _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), "unit");
            _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), base_unit_identifier);
        }
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Ampere {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn setup(self: @This(), exponent: i64) !void {
        const base_unit_node = EdgeComposition.get_child_by_identifier(self.instance, base_unit_identifier) orelse return error.BaseUnitNotFound;
        var base_unit = try is_base_unit.of(base_unit_node);
        try base_unit.setup(exponent);
    }

    pub fn of(node: BoundNodeReference) Ampere {
        return Ampere{
            .instance = node,
        };
    }
};

test "units.Ampere.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    const exponent = 1;
    var ampere = try Ampere.create_instance(&tg);
    try ampere.setup(exponent);

    const base_unit_node = EdgeComposition.get_child_by_identifier(ampere.instance, Ampere.base_unit_identifier) orelse return error.BaseUnitNotFound;
    var base_unit = try is_base_unit.of(base_unit_node);
    const exponent_param = try base_unit.get_exponent_param();
    const parameter = Parameter.of(exponent_param);
    const literal_numeric = try parameter.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    const exponent_value = try literal_numeric.get_value();
    try std.testing.expectEqual(@as(f64, @floatFromInt(exponent)), exponent_value);
}

pub const Kelvin = struct {
    instance: BoundNodeReference,

    const base_unit_identifier = "base_unit";

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Kelvin");
        if (EdgeComposition.get_child_by_identifier(type_node, base_unit_identifier) == null) {
            _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), "unit");
            _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), base_unit_identifier);
        }
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Kelvin {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn setup(self: @This(), exponent: i64) !void {
        const base_unit_node = EdgeComposition.get_child_by_identifier(self.instance, base_unit_identifier) orelse return error.BaseUnitNotFound;
        var base_unit = try is_base_unit.of(base_unit_node);
        try base_unit.setup(exponent);
    }

    pub fn of(node: BoundNodeReference) Kelvin {
        return Kelvin{
            .instance = node,
        };
    }
};

test "units.Kelvin.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    const exponent = 1;
    var kelvin = try Kelvin.create_instance(&tg);
    try kelvin.setup(exponent);

    const base_unit_node = EdgeComposition.get_child_by_identifier(kelvin.instance, Kelvin.base_unit_identifier) orelse return error.BaseUnitNotFound;
    var base_unit = try is_base_unit.of(base_unit_node);
    const exponent_param = try base_unit.get_exponent_param();
    const parameter = Parameter.of(exponent_param);
    const literal_numeric = try parameter.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    const exponent_value = try literal_numeric.get_value();
    try std.testing.expectEqual(@as(f64, @floatFromInt(exponent)), exponent_value);
}

pub const Mole = struct {
    instance: BoundNodeReference,

    const base_unit_identifier = "base_unit";

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Mole");
        if (EdgeComposition.get_child_by_identifier(type_node, base_unit_identifier) == null) {
            _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), "unit");
            _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), base_unit_identifier);
        }
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Mole {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn setup(self: @This(), exponent: i64) !void {
        const base_unit_node = EdgeComposition.get_child_by_identifier(self.instance, base_unit_identifier) orelse return error.BaseUnitNotFound;
        var base_unit = try is_base_unit.of(base_unit_node);
        try base_unit.setup(exponent);
    }

    pub fn of(node: BoundNodeReference) Mole {
        return Mole{
            .instance = node,
        };
    }
};

test "units.Mole.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    const exponent = 1;
    var mole = try Mole.create_instance(&tg);
    try mole.setup(exponent);

    const base_unit_node = EdgeComposition.get_child_by_identifier(mole.instance, Mole.base_unit_identifier) orelse return error.BaseUnitNotFound;
    var base_unit = try is_base_unit.of(base_unit_node);
    const exponent_param = try base_unit.get_exponent_param();
    const parameter = Parameter.of(exponent_param);
    const literal_numeric = try parameter.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    const exponent_value = try literal_numeric.get_value();
    try std.testing.expectEqual(@as(f64, @floatFromInt(exponent)), exponent_value);
}

pub const Candela = struct {
    instance: BoundNodeReference,

    const base_unit_identifier = "base_unit";

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Candela");
        if (EdgeComposition.get_child_by_identifier(type_node, base_unit_identifier) == null) {
            _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), "unit");
            _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), base_unit_identifier);
        }
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Candela {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn setup(self: @This(), exponent: i64) !void {
        const base_unit_node = EdgeComposition.get_child_by_identifier(self.instance, base_unit_identifier) orelse return error.BaseUnitNotFound;
        var base_unit = try is_base_unit.of(base_unit_node);
        try base_unit.setup(exponent);
    }

    pub fn of(node: BoundNodeReference) Candela {
        return Candela{
            .instance = node,
        };
    }
};

test "units.Candela.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    const exponent = 1;
    var candela = try Candela.create_instance(&tg);
    try candela.setup(exponent);

    const base_unit_node = EdgeComposition.get_child_by_identifier(candela.instance, Candela.base_unit_identifier) orelse return error.BaseUnitNotFound;
    var base_unit = try is_base_unit.of(base_unit_node);
    const exponent_param = try base_unit.get_exponent_param();
    const parameter = Parameter.of(exponent_param);
    const literal_numeric = try parameter.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    const exponent_value = try literal_numeric.get_value();
    try std.testing.expectEqual(@as(f64, @floatFromInt(exponent)), exponent_value);
}

pub const Ohm = struct {
    instance: BoundNodeReference,

    const unit_identifier = "unit";
    const kilogram_identifier = "kilogram";
    const meter_identifier = "meter";
    const second_identifier = "second";
    const ampere_identifier = "ampere";

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Ohm");
        _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), unit_identifier);
        _ = try tg.add_make_child(type_node, try Kilogram.get_or_create_type(tg), kilogram_identifier);
        _ = try tg.add_make_child(type_node, try Meter.get_or_create_type(tg), meter_identifier);
        _ = try tg.add_make_child(type_node, try Second.get_or_create_type(tg), second_identifier);
        _ = try tg.add_make_child(type_node, try Ampere.get_or_create_type(tg), ampere_identifier);
        return type_node;
    }

    pub fn create_instance(tg: *TypeGraph) !Ohm {
        const type_node = try get_or_create_type(tg);
        const instance = try tg.instantiate_node(type_node);
        return of(instance);
    }

    pub fn setup(self: *@This()) !void {
        const kilogram = Kilogram.of(EdgeComposition.get_child_by_identifier(self.instance, kilogram_identifier) orelse return error.KilogramNotFound);
        try kilogram.setup(1);

        const meter = Meter.of(EdgeComposition.get_child_by_identifier(self.instance, meter_identifier) orelse return error.MeterNotFound);
        try meter.setup(2);

        const second = Second.of(EdgeComposition.get_child_by_identifier(self.instance, second_identifier) orelse return error.SecondNotFound);
        try second.setup(-3);

        const ampere = Ampere.of(EdgeComposition.get_child_by_identifier(self.instance, ampere_identifier) orelse return error.AmpereNotFound);
        try ampere.setup(-2);
    }

    pub fn of(node: BoundNodeReference) Ohm {
        return Ohm{
            .instance = node,
        };
    }
};

test "units.Ohm.create_instance creates an instance" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = TypeGraph.init(&g);
    var ohm = try Ohm.create_instance(&tg);
    try ohm.setup();

    const kg_node = EdgeComposition.get_child_by_identifier(ohm.instance, Ohm.kilogram_identifier) orelse return error.KilogramNotFound;
    const kilogram = Kilogram.of(kg_node);
    const kg_exponent_param = try (try is_base_unit.of(EdgeComposition.get_child_by_identifier(kilogram.instance, Kilogram.base_unit_identifier) orelse return error.BaseUnitNotFound)).get_exponent_param();
    const kg_param = Parameter.of(kg_exponent_param);
    const kg_literal = try kg_param.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    try std.testing.expectEqual(@as(f64, 1.0), try kg_literal.get_value());

    const m_node = EdgeComposition.get_child_by_identifier(ohm.instance, Ohm.meter_identifier) orelse return error.MeterNotFound;
    const meter = Meter.of(m_node);
    const m_exponent_param = try (try is_base_unit.of(EdgeComposition.get_child_by_identifier(meter.instance, Meter.base_unit_identifier) orelse return error.BaseUnitNotFound)).get_exponent_param();
    const m_param = Parameter.of(m_exponent_param);
    const m_literal = try m_param.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    try std.testing.expectEqual(@as(f64, 2.0), try m_literal.get_value());

    const s_node = EdgeComposition.get_child_by_identifier(ohm.instance, Ohm.second_identifier) orelse return error.SecondNotFound;
    const second = Second.of(s_node);
    const s_exponent_param = try (try is_base_unit.of(EdgeComposition.get_child_by_identifier(second.instance, Second.base_unit_identifier) orelse return error.BaseUnitNotFound)).get_exponent_param();
    const s_param = Parameter.of(s_exponent_param);
    const s_literal = try s_param.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    try std.testing.expectEqual(@as(f64, -3.0), try s_literal.get_value());

    const a_node = EdgeComposition.get_child_by_identifier(ohm.instance, Ohm.ampere_identifier) orelse return error.AmpereNotFound;
    const ampere = Ampere.of(a_node);
    const a_exponent_param = try (try is_base_unit.of(EdgeComposition.get_child_by_identifier(ampere.instance, Ampere.base_unit_identifier) orelse return error.BaseUnitNotFound)).get_exponent_param();
    const a_param = Parameter.of(a_exponent_param);
    const a_literal = try a_param.try_extract_constrained_literal() orelse return error.LiteralNotFound;
    try std.testing.expectEqual(@as(f64, -2.0), try a_literal.get_value());
}
