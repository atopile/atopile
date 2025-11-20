const std = @import("std");

const graph_mod = @import("graph");
const GraphView = graph_mod.graph.GraphView;
const BoundNodeReference = graph_mod.graph.BoundNodeReference;

const _ContinuousNumeric = @import("magnitude_sets.zig")._ContinuousNumeric;
const MagnitudeSet = @import("magnitude_sets.zig").MagnitudeSet;
const visitor = @import("graph").visitor;

const faebryk = @import("faebryk");
const EdgeComposition = faebryk.composition.EdgeComposition;
const EdgePointer = faebryk.pointer.EdgePointer;
const Trait = faebryk.trait.Trait;
const EdgeTrait = faebryk.trait.EdgeTrait;
const TypeGraph = faebryk.typegraph.TypeGraph;
const graph = @import("graph").graph;

const num_base_units = 8;

pub const UnitVector: type = @Vector(num_base_units, u8);

// TODO: to fabll
pub const IsBaseUnit = struct {
    node: BoundNodeReference,
    const type_name = "IsBaseUnit";

    pub fn init_type(tg: *TypeGraph) !BoundNodeReference {
        var self_type = try tg.get_type_by_name(type_name);

        if (self_type == null) {
            self_type = try tg.add_type(type_name);
            _ = Trait.mark_as_trait(self_type.node);
        }

        return self_type;
    }

    pub fn of(node: BoundNodeReference) IsBaseUnit {
        return IsBaseUnit{ .node = node };
    }
};

// TODO: to fabll
pub const IsUnit = struct {
    node: BoundNodeReference,
    const type_name = "IsUnit";

    pub fn init_type(tg: *TypeGraph) !BoundNodeReference {
        var self_type = try tg.get_type_by_name(type_name);

        if (self_type == null) {
            self_type = try tg.add_type(type_name);
            _ = Trait.mark_as_trait(self_type.node);

            // TODO: add symbol make_child
            // TODO: add base_units (PointerSet) make_child
        }

        return self_type;
    }

    // pub fn init(g: *GraphView, name: []const u8) IsUnit {
    //     const node = g.create_and_insert_node();
    //     node.node.attributes.put(name_identifier, .{ .String = name });
    //     return IsUnit.of(node);
    // }

    pub fn of(node: BoundNodeReference) IsUnit {
        return IsUnit{ .node = node };
    }

    pub fn is_compatible_with(self: IsUnit, other: IsUnit) bool {
        _ = other;
        _ = self;
        // TODO: implement
        return true;
    }

    pub fn get_base_units(self: IsUnit, tg: *TypeGraph, allocator: std.mem.Allocator) ![]const IsBaseUnit { // TODO: return full vector
        const is_base_unit_type = try tg.get_type_by_name("IsBaseUnit") orelse return error.IsBaseUnitTypeNotFound;

        // Get the parent node (the unit)
        const parent_node = EdgeComposition.get_parent_node_of(self.node).?;
        const base_unit_trait = EdgeTrait.try_get_trait_instance_of_type(parent_node, is_base_unit_type.node);

        // Case 1: parent is a derived unit
        if (base_unit_trait == null) {
            const Finder = struct {
                base_units: std.ArrayList(IsBaseUnit),

                pub fn init(allocator_: std.mem.Allocator) @This() {
                    return .{ .base_units = std.ArrayList(IsBaseUnit).init(allocator_) };
                }

                pub fn visit(self_ptr: *anyopaque, edge: graph.BoundEdgeReference) visitor.VisitResult(graph.BoundNodeReference) {
                    const self_: *@This() = @ptrCast(@alignCast(self_ptr));

                    const component = edge.g.bind(EdgeComposition.get_child_node(edge.edge));
                    const base_unit = EdgeComposition.get_child_by_identifier(component, "base_unit").?; // TODO: UnitVectorComponent type in zig?
                    const component_base_unit_trait = EdgeTrait.try_get_trait_instance_by_identifier(base_unit, "IsBaseUnit") orelse return visitor.VisitResult(graph.BoundNodeReference){ .ERROR = error.FailedToGetBaseUnits };
                    self_.base_units.append(IsBaseUnit.of(component_base_unit_trait)) catch return visitor.VisitResult(graph.BoundNodeReference){ .ERROR = error.FailedToGetBaseUnits };
                    return .CONTINUE;
                }
            };

            var finder = Finder.init(allocator);

            const result = EdgePointer.visit_pointed_edges(self.node, BoundNodeReference, &finder.base_units, Finder.visit);
            switch (result) {
                .OK => |_| {
                    defer allocator.free(finder.base_units.items);
                    return finder.base_units.items;
                },
                .CONTINUE => unreachable,
                .STOP => unreachable,
                .ERROR => |err| return err,
                .EXHAUSTED => return error.FailedToGetBaseUnits,
            }
        } else {
            // Case 2: parent is a base unit
            const is_base_unit = IsBaseUnit.of(base_unit_trait.?);
            return &[_]IsBaseUnit{is_base_unit};
        }

        return error.FailedToGetBaseUnits;
    }
};

test "IsUnit.get_base_units" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);

    const meter_type = try tg.add_type("Meter");

    const is_base_unit = try IsBaseUnit.init_type(tg);
    const is_unit = try IsUnit.init_type(tg);

    _ = tg.add_make_child(meter_type, is_base_unit, "_is_base_unit", null) catch return error.FailedToAddMakeChild;
    _ = tg.add_make_child(meter_type, is_unit, "_is_unit", null) catch return error.FailedToAddMakeChild;

    const meter_ref = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{"meter"});
    const is_base_unit_ref = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ "meter", "_is_base_unit" });
    const is_unit_ref = try TypeGraph.ChildReferenceNode.create_and_insert(&tg, &.{ "meter", "_is_unit" });

    _ = tg.add_make_link(meter_type, meter_ref.node, is_base_unit_ref.node, EdgeTrait.build()) catch return error.FailedToAddMakeLink;
    _ = tg.add_make_link(meter_type, meter_ref.node, is_unit_ref.node, EdgeTrait.build()) catch return error.FailedToAddMakeLink;

    const meter_node = try tg.instantiate_node(meter_type);
    const meter_is_unit = EdgeTrait.try_get_trait_instance_of_type(meter_node, is_unit.node).?;

    const base_units = try IsUnit.get_base_units(IsUnit.of(meter_is_unit), &tg, a); // FIXME fn signature

    try std.testing.expectEqual(base_units.len, 1);
    // try std.testing.expectEqual(base_units[0].get_symbol(), "m");

    // TODO: add test for derived unit
}

const _unit_definition_is_base_unit_identifier = "_is_base_unit";
const _unit_definition_is_unit_identifier = "_is_unit";

// TODO: to fabll
pub const Ampere = struct {
    node: BoundNodeReference,
    const type_name = "Ampere";

    pub fn init_type(tg: *TypeGraph) !BoundNodeReference {
        var self_type = try tg.get_type_by_name(type_name);

        if (self_type == null) {
            self_type = try tg.add_type(type_name);
            _ = tg.add_make_child(self_type, IsBaseUnit.init_type(tg), _unit_definition_is_base_unit_identifier, null);

            // TODO: set symbol
            // TODO: set base_units
            _ = tg.add_make_child(self_type, IsUnit.init_type(tg), _unit_definition_is_unit_identifier, null);
        }

        return self_type;
    }

    pub fn of(node: BoundNodeReference) Ampere {
        return Ampere{ .node = node };
    }
};
