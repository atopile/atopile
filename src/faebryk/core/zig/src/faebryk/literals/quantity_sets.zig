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
const Units = @import("units.zig");
const IsUnit = Units.IsUnit;

// TODO: to fabll
// TODO:
pub const _ContinuousQuantity = struct {
    node: BoundNodeReference,
    const numeric_set_identifier = "numeric_set";
    const unit_identifier = "unit";

    pub fn init(magnitude_set: MagnitudeSet, unit: BoundNodeReference) !_ContinuousQuantity {
        _ = EdgeComposition.add_child(node, magnitude_set.set_node.node, numeric_set_identifier);
        _ = EdgePointer.point_to(node, unit.node.node, unit_identifier, null);

        // Return the quantity set
        return _ContinuousQuantity.of(node);
    }

    pub fn init_from_center(g: *GraphView, allocator: std.mem.Allocator, center: f64, abs_tol: f64, unit: BoundNodeReference) !_ContinuousQuantity {
        const left = center - abs_tol;
        const right = center + abs_tol;
        const magnitude_set = try MagnitudeSet.init_from_interval(g, allocator, left, right);

        return try _ContinuousQuantity.init(magnitude_set, unit);
    }

    pub fn init_from_center_rel(g: *GraphView, allocator: std.mem.Allocator, center: f64, rel_tol: f64, unit: BoundNodeReference) !_ContinuousQuantity {
        const left = center - center * rel_tol;
        const right = center + center * rel_tol;
        const magnitude_set = try MagnitudeSet.init_from_interval(g, allocator, left, right);

        return try _ContinuousQuantity.init(magnitude_set, unit);
    }

    pub fn init_from_range(g: *GraphView, allocator: std.mem.Allocator, min: f64, max: f64, unit: BoundNodeReference) !_ContinuousQuantity {
        const magnitude_set = try MagnitudeSet.init_from_interval(g, allocator, min, max);
        return try _ContinuousQuantity.init(magnitude_set, unit);
    }

    pub fn get_magnitude_set(self: _ContinuousQuantity) MagnitudeSet {
        const child = EdgeComposition.get_child_by_identifier(self.node, numeric_set_identifier).?;
        return MagnitudeSet.of(child);
    }

    pub fn get_min(self: _ContinuousQuantity, allocator: std.mem.Allocator) !f64 {
        const magnitude_set = self.get_magnitude_set();
        return magnitude_set.min_elem(allocator);
    }

    pub fn get_max(self: _ContinuousQuantity, allocator: std.mem.Allocator) !f64 {
        const magnitude_set = self.get_magnitude_set();
        return magnitude_set.max_elem(allocator);
    }

    pub fn is_empty(self: _ContinuousQuantity, allocator: std.mem.Allocator) !bool {
        const magnitude_set = self.get_magnitude_set();
        return magnitude_set.is_empty(allocator);
    }

    pub fn is_unbounded(self: _ContinuousQuantity, allocator: std.mem.Allocator) !bool {
        const magnitude_set = self.get_magnitude_set();
        const intervals = try magnitude_set.get_intervals(allocator);
        defer allocator.free(intervals);

        if (intervals.len == 0) {
            return false;
        }

        return intervals[0].is_unbounded();
    }

    pub fn is_finite(self: _ContinuousQuantity, allocator: std.mem.Allocator) !bool {
        const magnitude_set = self.get_magnitude_set();
        const intervals = try magnitude_set.get_intervals(allocator);
        defer allocator.free(intervals);

        if (intervals.len == 0) {
            return true;
        }

        return intervals[0].is_finite() and intervals[intervals.len - 1].is_finite();
    }

    pub fn is_integer(self: _ContinuousQuantity, allocator: std.mem.Allocator) !bool {
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

    pub fn is_subset_of(self: _ContinuousQuantity, other: _ContinuousQuantity) bool {
        const magnitude_set = self.get_magnitude_set();
        return magnitude_set.is_subset_of(other.get_magnitude_set());
    }

    pub fn get_unit(self: _ContinuousQuantity) BoundNodeReference {
        return EdgePointer.get_pointed_node_by_identifier(self.node, unit_identifier).?;
    }

    pub fn of(node: BoundNodeReference) _ContinuousQuantity {
        return _ContinuousQuantity{ .node = node };
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
    const continuous_quantity = try _ContinuousQuantity.init(magnitude_set, unit.node);

    // get the numeric set and unit
    var retrieved_magnitude = continuous_quantity.get_magnitude_set();

    // check the numeric set and unit
    const intervals = try retrieved_magnitude.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);
    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectEqual(intervals[0].get_min(), min_value);
    try std.testing.expectEqual(intervals[0].get_max(), max_value);
}

test "QuantitySet.init_empty" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const unit = IsUnit._test_init(&g, "test");
    const quantity_set = try _ContiniousQuantity.init_empty(&g, std.testing.allocator, unit);
    const magnitude_set = quantity_set.get_magnitude_set();
    const intervals = try magnitude_set.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);
    try std.testing.expectEqual(@as(usize, 0), intervals.len);
}

test "QuantitySet.from_center" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const center = 1.0;
    const abs_tol = 0.1;
    const unit = IsUnit._test_init(&g, "test");
    const quantity_set = try _ContinuousQuantity.from_center(&g, std.testing.allocator, center, abs_tol, unit.node);

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
    const quantity_set = try _ContinuousQuantity.from_center_rel(&g, std.testing.allocator, center, rel_tol, unit.node);

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
    const quantity_set = try _ContinuousQuantity.from_center(&g, std.testing.allocator, center, abs_tol, unit.node);
    const min_value = try quantity_set.get_min(std.testing.allocator);
    try std.testing.expectEqual(min_value, center - abs_tol);
}

test "QuantitySet.get_max" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const center = 1.0;
    const abs_tol = 0.1;
    const unit = IsUnit._test_init(&g, "test");
    const quantity_set = try _ContinuousQuantity.from_center(&g, std.testing.allocator, center, abs_tol, unit.node);
    const max_value = try quantity_set.get_max(std.testing.allocator);
    try std.testing.expectEqual(max_value, center + abs_tol);
}

test "QuantitySet.is_empty false" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, 0.0, 1.0);
    const quantity_set = try _ContinuousQuantity.init(magnitude_set, unit.node);

    const is_empty = try quantity_set.is_empty(std.testing.allocator);
    try std.testing.expect(!is_empty);
}

test "QuantitySet.is_empty true" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_empty(&g, std.testing.allocator);
    const quantity_set = try _ContinuousQuantity.init(magnitude_set, unit.node);

    const is_empty = try quantity_set.is_empty(std.testing.allocator);
    try std.testing.expect(is_empty);
}

test "QuantitySet.is_unbounded false" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, -1.0, 1.0);
    const quantity_set = try _ContinuousQuantity.init(magnitude_set, unit.node);

    const is_unbounded = try quantity_set.is_unbounded(std.testing.allocator);
    try std.testing.expect(!is_unbounded);
}

test "QuantitySet.is_unbounded true" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const inf = std.math.inf(f64);
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, -inf, inf);
    const quantity_set = try _ContinuousQuantity.init(magnitude_set, unit.node);

    const is_unbounded = try quantity_set.is_unbounded(std.testing.allocator);
    try std.testing.expect(is_unbounded);
}

test "QuantitySet.is_finite false" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const inf = std.math.inf(f64);
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, -inf, inf);
    const quantity_set = try _ContinuousQuantity.init(magnitude_set, unit.node);

    const is_finite = try quantity_set.is_finite(std.testing.allocator);
    try std.testing.expect(!is_finite);
}

test "QuantitySet.is_finite true" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, 0.0, 2.0);
    const quantity_set = try _ContinuousQuantity.init(magnitude_set, unit.node);

    const is_finite = try quantity_set.is_finite(std.testing.allocator);
    try std.testing.expect(is_finite);
}

test "QuantitySet.is_integer false" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, 0.0, 1.0);
    const quantity_set = try _ContinuousQuantity.init(magnitude_set, unit.node);

    const is_integer = try quantity_set.is_integer(std.testing.allocator);
    try std.testing.expect(!is_integer);
}

test "QuantitySet.is_integer true" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();

    const unit = IsUnit._test_init(&g, "unit");
    const magnitude_set = try MagnitudeSet.init_from_interval(&g, std.testing.allocator, 2.0, 2.0);
    const quantity_set = try _ContinuousQuantity.init(magnitude_set, unit.node);

    const is_integer = try quantity_set.is_integer(std.testing.allocator);
    try std.testing.expect(is_integer);
}

// TODO: to fabll
pub const QuantitySet = struct {
    node: BoundNodeReference,

    pub fn of(node: BoundNodeReference) QuantitySet {
        return QuantitySet{ .node = node };
    }
};
