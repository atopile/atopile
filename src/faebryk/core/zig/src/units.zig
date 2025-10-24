const std = @import("std");
const graph_mod = @import("graph");
const GraphView = graph_mod.graph.GraphView;
const BoundNodeReference = graph_mod.graph.BoundNodeReference;
const Trait = @import("faebryk/trait.zig").Trait;
const EdgeComposition = @import("faebryk/composition.zig").EdgeComposition;
const TypeGraph = @import("faebryk/typegraph.zig").TypeGraph;
const EdgeOperand = @import("faebryk/operand.zig").EdgeOperand;
const Numeric = @import("numeric_sets.zig").Numeric;
const EdgeType = @import("faebryk/node_type.zig").EdgeType;

// ato units example
// is_base_unit: type {
//     _: ImplementsTrait
//     symbol: Parameter
//     exponent: Parameter
// }

// Ampere: type {
//     Units.A := @Self
//     base_unit: is_base_unit {
//         name is! "A"
//     }
//     _: is_unit
// }

// kgA: type {
//     ampere: Ampere {
//         base_unit.exponent is! 1
//     }
//     kg: Kilogram {
//         base_unit.exponent is! 1
//     }
//     _: is_unit
// }

// Ohm: type {
//     Units.Ohm := @Self

//     _: Kilogram { base_unit.exponent is! 1 }
//     _: Meter { base_unit.exponent is! 2 }
//     _: Second { base_unit.exponent is! -3 }
//     _: Ampere { base_unit.exponent is! -2 }

//     _: is_unit
// }

pub const Parameter = struct {
    instance: BoundNodeReference,

    pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
        const type_node = try tg.get_or_create_type("Parameter");
        return type_node;
    }

    pub fn constrain_to_literal(tg: *TypeGraph, param: BoundNodeReference, literal: BoundNodeReference) !void {
        try AliasIs.alias_is(tg, param, literal);
    }

    pub fn try_extract_constrained_literal(tg: *TypeGraph, param: BoundNodeReference) !Numeric {

        EdgeOperand.visit_operands_of_type()
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
        const exponent_literal = Numeric.init(self.instance.g, @bitCast(exponent));

        var tg = TypeGraph.of_instance(self.instance) orelse return error.TypeGraphNotFound;
        try AliasIs.alias_is(&tg, exponent_param, exponent_literal);
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

    // Get the edge from the exponent param to the aliasis literal
    const param_alias_is_edge = EdgeOperand.get_expression_edge(exponent_node) orelse return error.ParamAliasIsEdgeNotFound;

    const alias = EdgeOperand.get_operand_node(param_alias_is_edge);

    // try std.testing.expectEqual(exponent, exponent_value);
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

// pub const Meter = struct {
//     instance: BoundNodeReference,

//     pub fn get_or_create_type(tg: *TypeGraph, exponent: i64) !BoundNodeReference {
//         const type_node = try tg.get_or_create_type("Meter");
//         _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg, exponent), null);
//         return type_node;
//     }

//     pub fn create_instance(tg: *TypeGraph) !Meter {
//         const type_node = try get_or_create_type(tg);
//         const instance = try tg.instantiate_node(type_node);
//         return of(instance);
//     }

//     pub fn of(node: BoundNodeReference) !Meter {
//         return Meter{
//             .instance = node,
//         };
//     }
// };

// test "units.Meter.create_instance creates an instance" {
//     var g = GraphView.init(std.testing.allocator);
//     defer g.deinit();
//     var tg = TypeGraph.init(&g);
//     try Meter.get_or_create_type(&tg, 1);
//     _ = try Meter.create_instance(&tg);
// }

// pub const Kilogram = struct {
//     instance: BoundNodeReference,

//     pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
//         const type_node = try tg.get_or_create_type("Kilogram");
//         _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), null);
//         return type_node;
//     }

//     pub fn create_instance(tg: *TypeGraph) !Kilogram {
//         const type_node = try get_or_create_type(tg);
//         const instance = try tg.instantiate_node(type_node);
//         return of(instance);
//     }

//     pub fn of(node: BoundNodeReference) !Kilogram {
//         return Kilogram{
//             .instance = node,
//         };
//     }
// };

// test "units.Kilogram.create_instance creates an instance" {
//     var g = GraphView.init(std.testing.allocator);
//     defer g.deinit();
//     var tg = TypeGraph.init(&g);
//     _ = try Kilogram.create_instance(&tg);
// }

// pub const Second = struct {
//     instance: BoundNodeReference,

//     pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
//         const type_node = try tg.get_or_create_type("Second");
//         _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), null);
//         return type_node;
//     }
//     pub fn create_instance(tg: *TypeGraph) !Second {
//         const type_node = try get_or_create_type(tg);
//         const instance = try tg.instantiate_node(type_node);
//         return of(instance);
//     }

//     pub fn of(node: BoundNodeReference) !Second {
//         return Second{
//             .instance = node,
//         };
//     }
// };

// test "units.Second.create_instance creates an instance" {
//     var g = GraphView.init(std.testing.allocator);
//     defer g.deinit();
//     var tg = TypeGraph.init(&g);
//     _ = try Second.create_instance(&tg);
// }

// pub const Ampere = struct {
//     instance: BoundNodeReference,

//     pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
//         const type_node = try tg.get_or_create_type("Ampere");
//         _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), null);
//         return type_node;
//     }
//     pub fn create_instance(tg: *TypeGraph) !Ampere {
//         const type_node = try get_or_create_type(tg);
//         const instance = try tg.instantiate_node(type_node);
//         return of(instance);
//     }

//     pub fn of(node: BoundNodeReference) !Ampere {
//         return Ampere{
//             .instance = node,
//         };
//     }
// };

// test "units.Ampere.create_instance creates an instance" {
//     var g = GraphView.init(std.testing.allocator);
//     defer g.deinit();
//     var tg = TypeGraph.init(&g);
//     _ = try Ampere.create_instance(&tg);
// }

// pub const Kelvin = struct {
//     instance: BoundNodeReference,

//     pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
//         const type_node = try tg.get_or_create_type("Kelvin");
//         _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), null);
//         return type_node;
//     }
//     pub fn create_instance(tg: *TypeGraph) !Kelvin {
//         const type_node = try get_or_create_type(tg);
//         const instance = try tg.instantiate_node(type_node);
//         return of(instance);
//     }

//     pub fn of(node: BoundNodeReference) !Kelvin {
//         return Kelvin{
//             .instance = node,
//         };
//     }
// };

// test "units.Kelvin.create_instance creates an instance" {
//     var g = GraphView.init(std.testing.allocator);
//     defer g.deinit();
//     var tg = TypeGraph.init(&g);
//     _ = try Kelvin.create_instance(&tg);
// }

// pub const Mole = struct {
//     instance: BoundNodeReference,

//     pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
//         const type_node = try tg.get_or_create_type("Mole");
//         _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(tg), null);
//         return type_node;
//     }
//     pub fn create_instance(tg: *TypeGraph) !Mole {
//         const type_node = try get_or_create_type(tg);
//         const instance = try tg.instantiate_node(type_node);
//         return of(instance);
//     }

//     pub fn of(node: BoundNodeReference) !Mole {
//         return Mole{
//             .instance = node,
//         };
//     }
// };

// test "units.Mole.create_instance creates an instance" {
//     var g = GraphView.init(std.testing.allocator);
//     defer g.deinit();
//     var tg = TypeGraph.init(&g);
//     _ = try Mole.create_instance(&tg);
// }

// pub const Candela = struct {
//     instance: BoundNodeReference,

//     pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
//         const type_node = try tg.get_or_create_type("Candela");
//         _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try is_base_unit.get_or_create_type(
//             tg,
//         ), null);
//         return type_node;
//     }
//     pub fn create_instance(tg: *TypeGraph) !Candela {
//         const type_node = try get_or_create_type(tg);
//         const instance = try tg.instantiate_node(type_node);
//         return of(instance);
//     }

//     pub fn of(node: BoundNodeReference) !Candela {
//         return Candela{
//             .instance = node,
//         };
//     }
// };

// test "units.Candela.create_instance creates an instance" {
//     var g = GraphView.init(std.testing.allocator);
//     defer g.deinit();
//     var tg = TypeGraph.init(&g);
//     _ = try Candela.create_instance(&tg);
// }

// pub const Ohm = struct {
//     instance: BoundNodeReference,

//     pub fn get_or_create_type(tg: *TypeGraph) !BoundNodeReference {
//         const type_node = try tg.get_or_create_type("Ohm");
//         _ = try tg.add_make_child(type_node, try is_unit.get_or_create_type(
//             tg,
//         ), null);
//         _ = try tg.add_make_child(type_node, try Kilogram.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try Meter.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try Second.get_or_create_type(tg), null);
//         _ = try tg.add_make_child(type_node, try Ampere.get_or_create_type(tg), null);
//         return type_node;
//     }
//     pub fn create_instance(tg: *TypeGraph) !Ohm {
//         const type_node = try get_or_create_type(tg);
//         const instance = try tg.instantiate_node(type_node);
//         return of(instance);
//     }

//     pub fn of(node: BoundNodeReference) !Ohm {
//         return Ohm{
//             .instance = node,
//         };
//     }
// };

// test "units.Ohm.create_instance creates an instance" {
//     var g = GraphView.init(std.testing.allocator);
//     defer g.deinit();
//     var tg = TypeGraph.init(&g);
//     _ = try Ohm.create_instance(&tg);
// }
