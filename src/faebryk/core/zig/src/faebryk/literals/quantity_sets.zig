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

pub const _ContiniousQuantity = struct {
    node: BoundNodeReference,
    const numeric_set_identifier = "numeric_set";
    const unit_identifier = "unit";

    pub fn init(magnitude_set: MagnitudeSet, unit: BoundNodeReference) !_ContiniousQuantity {

        // Get the instance graph from the numeric set
        const instance_graph = magnitude_set.set_node.g;

        // Create a new node representing the quantity set
        const node = instance_graph.create_and_insert_node();

        // Add the numeric set and unit to the node
        _ = EdgeComposition.add_child(node, magnitude_set.set_node.node, numeric_set_identifier);

        // Add a pointer to the unit trait
        _ = EdgePointer.point_to(node, unit.node, unit_identifier, null);

        // Return the quantity set
        return _ContiniousQuantity.of(node);
    }

    pub fn from_center(g: *GraphView, allocator: std.mem.Allocator, center: f64, abs_tol: f64, unit: BoundNodeReference) !_ContiniousQuantity {
        const left = center - abs_tol;
        const right = center + abs_tol;
        const magnitude_set = try MagnitudeSet.init_from_interval(g, allocator, left, right);

        return try _ContiniousQuantity.init(magnitude_set, unit);
    }

    pub fn from_center_rel(g: *GraphView, allocator: std.mem.Allocator, center: f64, rel_tol: f64, unit: BoundNodeReference) !_ContiniousQuantity {
        const left = center - center * rel_tol;
        const right = center + center * rel_tol;
        const magnitude_set = try MagnitudeSet.init_from_interval(g, allocator, left, right);

        return try _ContiniousQuantity.init(magnitude_set, unit);
    }

    pub fn get_magnitude_set(self: _ContiniousQuantity) MagnitudeSet {
        const child = EdgeComposition.get_child_by_identifier(self.node, numeric_set_identifier).?;
        return MagnitudeSet.of(child);
    }

    pub fn get_min(self: _ContiniousQuantity, allocator: std.mem.Allocator) !f64 {
        const magnitude_set = self.get_magnitude_set();
        return magnitude_set.min_elem(allocator);
    }

    pub fn get_max(self: _ContiniousQuantity, allocator: std.mem.Allocator) !f64 {
        const magnitude_set = self.get_magnitude_set();
        return magnitude_set.max_elem(allocator);
    }

    pub fn is_empty(self: _ContiniousQuantity, allocator: std.mem.Allocator) !bool {
        const magnitude_set = self.get_magnitude_set();
        return magnitude_set.is_empty(allocator);
    }

    pub fn is_unbounded(self: _ContiniousQuantity, allocator: std.mem.Allocator) !bool {
        const magnitude_set = self.get_magnitude_set();
        const intervals = try magnitude_set.get_intervals(allocator);
        defer allocator.free(intervals);

        if (intervals.len == 0) {
            return false;
        }

        return intervals[0].is_unbounded();
    }

    pub fn is_finite(self: _ContiniousQuantity, allocator: std.mem.Allocator) !bool {
        const magnitude_set = self.get_magnitude_set();
        const intervals = try magnitude_set.get_intervals(allocator);
        defer allocator.free(intervals);

        if (intervals.len == 0) {
            return true;
        }

        return intervals[0].is_finite() and intervals[intervals.len - 1].is_finite();
    }

    pub fn is_integer(self: _ContiniousQuantity, allocator: std.mem.Allocator) !bool {
        const magnitude_set = self.get_magnitude_set();
        const intervals = try magnitude_set.get_intervals(allocator);
        defer allocator.free(intervals);

        if (intervals.len == 0) {
            return false;
        }

        for (intervals) |interval| {
            if (!interval.is_integer()) {
                return false;
            }
        }

        return true;
    }

    pub fn is_subset_of(self: _ContiniousQuantity, other: _ContiniousQuantity) bool {
        const magnitude_set = self.get_magnitude_set();
        return magnitude_set.is_subset_of(other.get_magnitude_set());
    }

    pub fn get_unit(self: _ContiniousQuantity) BoundNodeReference {
        return EdgePointer.get_pointed_node_by_identifier(self.node, unit_identifier).?;
    }

    pub fn of(node: BoundNodeReference) _ContiniousQuantity {
        return _ContiniousQuantity{ .node = node };
    }
};

pub const IsUnit = struct {
    node: BoundNodeReference,

    const name_identifier = "IsUnit";

    pub fn _test_init(g: *GraphView, name: []const u8) IsUnit {
        const node = g.create_and_insert_node();
        node.node.attributes.put(name_identifier, .{ .String = name });
        return IsUnit.of(node);
    }

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

pub const IsBaseUnit = struct {
    node: BoundNodeReference,

    const base_unit_identifier = "base_unit";

    pub fn init(g: *GraphView, symbol: []const u8) IsBaseUnit {
        const node = g.create_and_insert_node();
        node.node.attributes.put(base_unit_identifier, .{ .String = symbol }); // TODO: as parameter
        // try Trait.mark_as_trait(IsBaseUnit.of(node).node);  // FIXME
        return IsBaseUnit.of(node);
    }

    pub fn of(node: BoundNodeReference) IsBaseUnit {
        return IsBaseUnit{ .node = node };
    }
};

test "QuantitySet.init" {
    const allocator = std.testing.allocator;
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    // Expected values
    const min_value = 1.0;
    const max_value = 3.0;
    const unit_name = "test";

    // Create a quantity set from a _ContinuousNumeric
    const continuous_interval = try _ContinuousNumeric.init(&g, min_value, max_value);
    const magnitude_set = try MagnitudeSet.init_from_single(&g, allocator, continuous_interval);
    const unit = IsUnit._test_init(&g, unit_name);
    const continuous_quantity = try _ContiniousQuantity.init(magnitude_set, unit.node);

    // get the numeric set and unit
    var retrieved_magnitude = continuous_quantity.get_magnitude_set();

    // check the numeric set and unit
    const intervals = try retrieved_magnitude.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);
    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectEqual(intervals[0].get_min(), min_value);
    try std.testing.expectEqual(intervals[0].get_max(), max_value);
}

test "QuantitySet.from_center" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const center = 1.0;
    const abs_tol = 0.1;
    const unit = IsUnit._test_init(&g, "test");
    const quantity_set = try _ContiniousQuantity.from_center(&g, std.testing.allocator, center, abs_tol, unit.node);

    const magnitude_set = quantity_set.get_magnitude_set();
    const intervals = try magnitude_set.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);
    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectEqual(intervals[0].get_min(), center - abs_tol);
    try std.testing.expectEqual(intervals[0].get_max(), center + abs_tol);
}

test "QuantitySet.from_center_rel" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const center = 1.0;
    const rel_tol = 0.1;
    const unit = IsUnit._test_init(&g, "test");
    const quantity_set = try _ContiniousQuantity.from_center_rel(&g, std.testing.allocator, center, rel_tol, unit.node);

    const magnitude_set = quantity_set.get_magnitude_set();
    const intervals = try magnitude_set.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);
    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectEqual(intervals[0].get_min(), center - center * rel_tol);
    try std.testing.expectEqual(intervals[0].get_max(), center + center * rel_tol);
}

test "QuantitySet.get_min" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const center = 1.0;
    const abs_tol = 0.1;
    const unit = IsUnit._test_init(&g, "test");
    const quantity_set = try _ContiniousQuantity.from_center(&g, std.testing.allocator, center, abs_tol, unit.node);
    const min_value = try quantity_set.get_min(std.testing.allocator);
    try std.testing.expectEqual(min_value, center - abs_tol);
}

test "QuantitySet.get_max" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const center = 1.0;
    const abs_tol = 0.1;
    const unit = IsUnit._test_init(&g, "test");
    const quantity_set = try _ContiniousQuantity.from_center(&g, std.testing.allocator, center, abs_tol, unit.node);
    const max_value = try quantity_set.get_max(std.testing.allocator);
    try std.testing.expectEqual(max_value, center + abs_tol);
}

test "QuantitySet.is_empty false" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, 0.0, 1.0);
    const quantity_set = try _ContiniousQuantity.init(magnitude_set, unit.node);

    const is_empty = try quantity_set.is_empty(std.testing.allocator);
    try std.testing.expect(!is_empty);
}

test "QuantitySet.is_empty true" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_empty(&g, std.testing.allocator);
    const quantity_set = try _ContiniousQuantity.init(magnitude_set, unit.node);

    const is_empty = try quantity_set.is_empty(std.testing.allocator);
    try std.testing.expect(is_empty);
}

test "QuantitySet.is_unbounded false" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, -1.0, 1.0);
    const quantity_set = try _ContiniousQuantity.init(magnitude_set, unit.node);

    const is_unbounded = try quantity_set.is_unbounded(std.testing.allocator);
    try std.testing.expect(!is_unbounded);
}

test "QuantitySet.is_unbounded true" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const inf = std.math.inf(f64);
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, -inf, inf);
    const quantity_set = try _ContiniousQuantity.init(magnitude_set, unit.node);

    const is_unbounded = try quantity_set.is_unbounded(std.testing.allocator);
    try std.testing.expect(is_unbounded);
}

test "QuantitySet.is_finite false" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const inf = std.math.inf(f64);
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, -inf, inf);
    const quantity_set = try _ContiniousQuantity.init(magnitude_set, unit.node);

    const is_finite = try quantity_set.is_finite(std.testing.allocator);
    try std.testing.expect(!is_finite);
}

test "QuantitySet.is_finite true" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, 0.0, 2.0);
    const quantity_set = try _ContiniousQuantity.init(magnitude_set, unit.node);

    const is_finite = try quantity_set.is_finite(std.testing.allocator);
    try std.testing.expect(is_finite);
}

test "QuantitySet.is_integer false" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, 0.0, 1.0);
    const quantity_set = try _ContiniousQuantity.init(magnitude_set, unit.node);

    const is_integer = try quantity_set.is_integer(std.testing.allocator);
    try std.testing.expect(!is_integer);
}

test "QuantitySet.is_integer true" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, 2.0, 2.0);
    const quantity_set = try _ContiniousQuantity.init(magnitude_set, unit.node);

    const is_integer = try quantity_set.is_integer(std.testing.allocator);
    try std.testing.expect(is_integer);
}

test "IsUnit.get_base_units" {
    const a = std.testing.allocator;
    var g = GraphView.init(a);
    defer g.deinit();

    var tg = TypeGraph.init(&g);

    const meter_type = try tg.add_type("Meter");

    const is_base_unit = try tg.add_type("IsBaseUnit");
    Trait.mark_as_trait(is_base_unit) catch return error.FailedToMarkAsTrait;

    const is_unit = try tg.add_type("IsUnit");
    Trait.mark_as_trait(is_unit) catch return error.FailedToMarkAsTrait;

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

pub const QuantitySet = struct {
    node: BoundNodeReference,

    pub fn of(node: BoundNodeReference) QuantitySet {
        return QuantitySet{ .node = node };
    }
};
