const std = @import("std");

const graph_mod = @import("graph");
const GraphView = graph_mod.graph.GraphView;
const BoundNodeReference = graph_mod.graph.BoundNodeReference;

const Bool_Node = @import("bool_sets.zig").Bool_Node;
const Bool_Set = @import("bool_sets.zig").Bool_Set;
const faebryk = @import("faebryk/lib.zig");
const EdgeComposition = faebryk.composition.EdgeComposition;
const EdgeNext = faebryk.next.EdgeNext;

pub const Numeric = struct {
    node: BoundNodeReference,

    const value_identifier = "value";

    pub fn init(g: *GraphView, value: f64) Numeric {
        const node = g.create_and_insert_node();
        node.node.attributes.put(value_identifier, .{ .Float = value });
        return of(node);
    }

    pub fn of(node: BoundNodeReference) Numeric {
        return Numeric{
            .node = node,
        };
    }
    pub fn get_value(self: Numeric) !f64 {
        const literal = self.node.node.attributes.dynamic.values.get(value_identifier) orelse return error.ValueNotFound;
        return literal.Float;
    }
};

pub const _Continuous = struct {
    node: BoundNodeReference,

    const min_identifier = "min";
    const max_identifier = "max";

    pub const Error = error{
        InvalidBounds,
        NaNMin,
        NaNMax,
        InfiniteMin,
        InfiniteMax,
        Empty,
        NonPositiveLog,
    };

    pub const OperationError = error{
        NegativeExponentUnsupported,
        ExponentCrossesZero,
        FractionalExponentRequiresIntegerExponent,
    };

    pub fn init(g: *GraphView, min: f64, max: f64) Error!_Continuous {
        if (std.math.isNan(min)) return error.NaNMin;
        if (std.math.isNan(max)) return error.NaNMax;
        if (min > max) return error.InvalidBounds;

        const node = g.create_and_insert_node();
        const min_node = Numeric.init(g, min);
        const max_node = Numeric.init(g, max);

        _ = EdgeComposition.add_child(node, min_node.node.node, min_identifier);
        _ = EdgeComposition.add_child(node, max_node.node.node, max_identifier);

        return of(node);
    }

    pub fn get_min(self: _Continuous) f64 {
        return Numeric.of(EdgeComposition.get_child_by_identifier(self.node, min_identifier).?).get_value();
    }

    pub fn get_max(self: _Continuous) f64 {
        return Numeric.of(EdgeComposition.get_child_by_identifier(self.node, max_identifier).?).get_value();
    }

    pub fn of(node: BoundNodeReference) _Continuous {
        return _Continuous{
            .node = node,
        };
    }

    pub fn is_empty() bool {
        return false;
    }

    pub fn is_unbounded(self: _Continuous) bool {
        return self.min == -std.math.inf(f64) and self.max == std.math.inf(f64);
    }

    pub fn is_finite(self: _Continuous) bool {
        if (self.is_empty()) {
            return true;
        }

        return self.min != -std.math.inf(f64) and self.max != std.math.inf(f64);
    }

    pub fn is_integer(self: _Continuous) bool {
        return self.is_single_element() and @mod(self.get_min(), 1.0) == 0.0;
    }

    pub fn as_center_rel(self: _Continuous) CenterRel {
        const min = self.get_min();
        const max = self.get_max();
        if (self.is_single_element()) {
            return .{ .center = self.min, .relative = 0.0 };
        }
        if (!self.is_finite()) {
            return .{ .center = self.min, .relative = std.math.inf(f64) };
        }
        const center = (min + max) / 2.0;
        const rel = (max - min) / (2.0 * center);
        return .{ .center = center, .relative = rel };
    }

    pub const CenterRel = struct {
        center: f64,
        relative: f64,
    };

    pub fn is_subset_of(self: _Continuous, other: _Continuous) bool {
        return self.min >= other.min and self.max <= other.max;
    }

    pub fn op_add(self: _Continuous, g: *GraphView, other: _Continuous) !_Continuous {
        const node = try _Continuous.init(g, self.get_min() + other.get_min(), self.get_max() + other.get_max());
        return node;
    }

    pub fn op_negate(self: _Continuous, g: *GraphView) !_Continuous {
        return _Continuous.init(g, -self.get_max(), -self.get_min());
    }

    pub fn op_subtract(self: _Continuous, g: *GraphView, other: _Continuous) !_Continuous {
        return try self.op_add(g, try other.op_negate(g));
    }

    pub fn op_multiply(
        self: _Continuous,
        g: *GraphView,
        other: _Continuous,
    ) !_Continuous {
        const GuardedMul = struct {
            fn op(a: f64, b: f64) f64 {
                if (a == 0.0 or b == 0.0) {
                    return 0.0;
                }
                const result = a * b;
                std.debug.assert(!std.math.isNan(result));
                return result;
            }
        };

        const prod_a = GuardedMul.op(self.get_min(), other.get_min());
        const prod_b = GuardedMul.op(self.get_min(), other.get_max());
        const prod_c = GuardedMul.op(self.get_max(), other.get_min());
        const prod_d = GuardedMul.op(self.get_max(), other.get_max());

        var min_val = prod_a;
        min_val = @min(min_val, prod_b);
        min_val = @min(min_val, prod_c);
        min_val = @min(min_val, prod_d);

        var max_val = prod_a;
        max_val = @max(max_val, prod_b);
        max_val = @max(max_val, prod_c);
        max_val = @max(max_val, prod_d);

        return _Continuous.init(g, min_val, max_val);
    }

    pub fn op_power(
        self: _Continuous,
        g: *GraphView,
        allocator: std.mem.Allocator,
        exponent: _Continuous,
    ) !Numeric_Set {
        if (exponent.get_max() < 0.0) {
            return OperationError.NegativeExponentUnsupported;
        }

        const base_min = self.get_min();
        const base_max = self.get_max();
        const exp_min = exponent.get_min();
        const exp_max = exponent.get_max();

        if (exp_max < 0.0) {
            const negated = try exponent.op_negate(g);
            const powered = try self.op_power(g, allocator, negated);
            return try powered.op_invert(g, allocator);
        }
        if (exp_min < 0.0) {
            return OperationError.ExponentCrossesZero;
        }
        if (base_min < 0.0 and !exponent.is_integer()) {
            return OperationError.FractionalExponentRequiresIntegerExponent;
        }

        const pow_a = std.math.pow(f64, base_min, exp_min);
        const pow_b = std.math.pow(f64, base_min, exp_max);
        const pow_c = std.math.pow(f64, base_max, exp_min);
        const pow_d = std.math.pow(f64, base_max, exp_max);

        var min_val = pow_a;
        min_val = @min(min_val, pow_b);
        min_val = @min(min_val, pow_c);
        min_val = @min(min_val, pow_d);

        var max_val = pow_a;
        max_val = @max(max_val, pow_b);
        max_val = @max(max_val, pow_c);
        max_val = @max(max_val, pow_d);

        return try Numeric_Set.init_from_interval(g, allocator, min_val, max_val);
    }

    pub fn op_invert(self: _Continuous, g: *GraphView, allocator: std.mem.Allocator) !Numeric_Set {
        const neg_inf = -std.math.inf(f64);
        const pos_inf = std.math.inf(f64);

        if (self.get_min() == 0.0 and self.get_max() == 0.0) {
            return try Numeric_Set.init_empty(g, g.allocator);
        }

        if (self.get_min() < 0.0 and self.get_max() > 0.0) {
            return Numeric_Set.init(g, allocator, &[_]_Continuous{
                try _Continuous.init(g, neg_inf, 1.0 / self.get_min()),
                try _Continuous.init(g, 1.0 / self.get_max(), pos_inf),
            }, &[_]Numeric_Set{});
        }

        if (self.get_min() < 0.0 and self.get_max() == 0.0) {
            return Numeric_Set.init(g, allocator, &[_]_Continuous{
                try _Continuous.init(g, neg_inf, 1.0 / self.get_min()),
            }, &[_]Numeric_Set{});
        }

        if (self.get_min() == 0.0 and self.get_max() > 0.0) {
            return Numeric_Set.init(g, allocator, &[_]_Continuous{
                try _Continuous.init(g, 1.0 / self.get_max(), pos_inf),
            }, &[_]Numeric_Set{});
        }

        return Numeric_Set.init(g, allocator, &[_]_Continuous{
            try _Continuous.init(g, 1.0 / self.get_max(), 1.0 / self.get_min()),
        }, &[_]Numeric_Set{});
    }

    pub fn op_divide(self: _Continuous, g: *GraphView, allocator: std.mem.Allocator, other: _Continuous) !Numeric_Set {
        var inverse_other = try other.op_invert(g, allocator);

        const inverse_intervals = try inverse_other.get_intervals(allocator);
        defer allocator.free(inverse_intervals);

        var products = std.ArrayList(_Continuous).init(allocator);
        defer products.deinit();

        for (inverse_intervals) |r| {
            try products.append(try self.op_multiply(g, r));
        }

        return try Numeric_Set.init(g, allocator, products.items, &[_]Numeric_Set{});
    }

    pub fn op_intersect(self: _Continuous, g: *GraphView, other: _Continuous) !_Continuous {
        const lower = @max(self.get_min(), other.get_min());
        const upper = @min(self.get_max(), other.get_max());

        if (lower <= upper) {
            return try _Continuous.init(g, lower, upper);
        }

        return Error.Empty;
    }

    pub fn op_difference(self: _Continuous, g: *GraphView, allocator: std.mem.Allocator, other: _Continuous) !Numeric_Set {
        const self_min = self.get_min();
        const self_max = self.get_max();
        const other_min = other.get_min();
        const other_max = other.get_max();

        // case: no overlap
        if (self_max <= other_min or self_min >= other_max) {
            return try Numeric_Set.init_from_single(g, allocator, self);
        }

        // case: other completely covers self
        if (other_min <= self_min and other_max >= self_max) {
            return try Numeric_Set.init_empty(g, allocator);
        }

        // case: other is in the middle, splitting self into two pieces
        if (self_min < other_min and self_max > other_max) {
            return try Numeric_Set.init(g, allocator, &[_]_Continuous{
                try _Continuous.init(g, self_min, other_min),
                try _Continuous.init(g, other_max, self_max),
            }, &[_]Numeric_Set{});
        }

        // case: overlap on right side
        if (self_min < other_min) {
            return try Numeric_Set.init_from_interval(g, allocator, self_min, other_min);
        }

        // case: overlap on left side
        return try Numeric_Set.init_from_interval(g, allocator, other_max, self_max);
    }

    pub fn op_round(self: _Continuous, g: *GraphView, ndigits: i32) !_Continuous {
        const factor = std.math.pow(f64, 10.0, @as(f64, @floatFromInt(ndigits)));
        return try _Continuous.init(g, std.math.round(self.get_min() * factor) / factor, std.math.round(self.get_max() * factor) / factor);
    }

    pub fn op_abs(self: _Continuous, g: *GraphView) !_Continuous {
        const min = self.get_min();
        const max = self.get_max();

        if (min < 0.0 and max > 0.0) {
            return _Continuous.init(g, 0.0, max);
        }
        if (min < 0.0 and max < 0.0) {
            return _Continuous.init(g, -max, -min);
        }
        if (min < 0.0 and max == 0.0) {
            return _Continuous.init(g, 0.0, -min);
        }
        if (min == 0.0 and max < 0.0) {
            return _Continuous.init(g, max, 0.0);
        }
        return self;
    }

    pub fn op_log(self: _Continuous, g: *GraphView) !_Continuous {
        const min = self.get_min();
        const max = self.get_max();
        if (min <= 0.0) return Error.NonPositiveLog;
        return _Continuous.init(g, std.math.log(f64, std.math.e, min), std.math.log(f64, std.math.e, max));
    }

    pub fn op_sin(
        self: _Continuous,
        g: *GraphView,
    ) !_Continuous {
        // The extrema of sin(x) on an interval occur at the endpoints or at the
        // turning points x = π/2 + π·k that fall within the interval. For
        // intervals wider than a full period or containing infinities we can
        // shortcut to [-1, 1].
        const min = self.get_min();
        const max = self.get_max();
        const pi = std.math.pi;
        const interval_width = max - min;

        if (!std.math.isFinite(interval_width) or interval_width > 2.0 * pi) {
            return try _Continuous.init(g, -1.0, 1.0);
        }

        const start_sin = std.math.sin(min);
        const end_sin = std.math.sin(max);

        var min_val = @min(start_sin, end_sin);
        var max_val = @max(start_sin, end_sin);

        const half_pi = pi / 2.0;
        const k_start_f = std.math.ceil((min - half_pi) / pi);
        const k_end_f = std.math.floor((max - half_pi) / pi);

        if (k_start_f <= k_end_f) {
            var k = @as(i64, @intFromFloat(k_start_f));
            const k_end = @as(i64, @intFromFloat(k_end_f));

            while (k <= k_end) : (k += 1) {
                const turning_point = half_pi + pi * @as(f64, @floatFromInt(k));
                // sin is ±1 at these turning points, but we evaluate explicitly to
                // capture any future changes if we adjust the function.
                const value = std.math.sin(turning_point);
                min_val = @min(min_val, value);
                max_val = @max(max_val, value);
            }
        }

        return try _Continuous.init(g, min_val, max_val);
    }

    pub fn is_single_element(self: _Continuous) bool {
        return self.get_min() == self.get_max();
    }

    pub fn isInteger(self: _Continuous) bool {
        return self.is_single_element() and is_integer(self.min);
    }

    fn intervalLess(_: void, a: _Continuous, b: _Continuous) bool {
        return a.get_min() < b.get_min();
    }
};

pub const Numeric_Set = struct {
    set_node: BoundNodeReference,

    const set_identifier = "set";
    const head_identifier = "head";

    pub const Error = error{
        Empty,
    };

    pub fn init_empty(g: *GraphView, allocator: std.mem.Allocator) !Numeric_Set {
        return try Numeric_Set.init(g, allocator, &[_]_Continuous{}, &[_]Numeric_Set{});
    }

    pub fn init_from_single(g: *GraphView, allocator: std.mem.Allocator, input: _Continuous) !Numeric_Set {
        return try Numeric_Set.init(g, allocator, &[_]_Continuous{input}, &[_]Numeric_Set{});
    }

    pub fn init_from_interval(g: *GraphView, allocator: std.mem.Allocator, min: f64, max: f64) !Numeric_Set {
        return try Numeric_Set.init_from_single(g, allocator, try _Continuous.init(g, min, max));
    }

    pub fn init(g: *GraphView, allocator: std.mem.Allocator, continuous_inputs: []const _Continuous, set_inputs: []const Numeric_Set) !Numeric_Set {
        // Create a new node representing the numeric set
        const node = g.create_and_insert_node();

        // Create a temporary list to sort and merge the intervals
        var temp = std.ArrayList(_Continuous).init(allocator);
        defer temp.deinit();

        // flatten
        for (continuous_inputs) |r| {
            try temp.append(r);
        }

        // Add the intervals from the set inputs
        for (set_inputs) |d| {
            const set_intervals = try d.get_intervals(allocator);
            for (set_intervals) |r| {
                try temp.append(r);
            }
            allocator.free(set_intervals);
        }

        // If there are no intervals, return the new node
        if (temp.items.len == 0) {
            return of(node);
        }

        // Sort the intervals by min element
        std.mem.sort(
            _Continuous,
            temp.items,
            {},
            _Continuous.intervalLess,
        );

        // Merge overlapping intervals and materialize the merged ranges so we only add
        // a single `_Continuous` node per disjoint interval.
        var cur_min = temp.items[0].get_min();
        var cur_max = temp.items[0].get_max();

        const Interval = struct {
            min: f64,
            max: f64,
        };
        var merged = std.ArrayList(Interval).init(allocator);
        defer merged.deinit();

        for (temp.items[1..]) |interval| {
            if (cur_max >= interval.get_min()) {
                cur_max = @max(cur_max, interval.get_max());
            } else {
                try merged.append(.{ .min = cur_min, .max = cur_max });
                cur_min = interval.get_min();
                cur_max = interval.get_max();
            }
        }
        try merged.append(.{ .min = cur_min, .max = cur_max });

        const head_interval = merged.items[0];
        const head_node = try _Continuous.init(g, head_interval.min, head_interval.max);
        _ = EdgeComposition.add_child(node, head_node.node.node, head_identifier);

        var previous_node = head_node.node;
        for (merged.items[1..]) |segment| {
            const new_node = try _Continuous.init(g, segment.min, segment.max);
            _ = EdgeNext.add_next(previous_node, new_node.node);
            previous_node = new_node.node;
        }

        return of(node);
    }

    pub fn of(node: BoundNodeReference) Numeric_Set {
        return Numeric_Set{
            .set_node = node,
        };
    }

    pub fn get_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator) ![]const _Continuous {
        // if there is no head node, return an empty array
        if (EdgeComposition.get_child_by_identifier(self.set_node, head_identifier) == null) {
            return &[_]_Continuous{};
        }

        var intervals = std.ArrayList(_Continuous).init(allocator);

        // get the head node and add it to the intervals
        var bound_current = EdgeComposition.get_child_by_identifier(self.set_node, head_identifier) orelse return error.Empty;
        try intervals.append(_Continuous.of(bound_current));

        // traverse the 'next' edges and collect the _Continuous nodes
        while (EdgeNext.get_next_node_from_node(bound_current)) |node_ref| {
            bound_current = bound_current.g.bind(node_ref);
            try intervals.append(_Continuous.of(bound_current));
        }

        const owned = try intervals.toOwnedSlice();
        return owned;
    }

    pub fn get_intervals_len(self: *const Numeric_Set, allocator: std.mem.Allocator) !usize {
        const intervals = try self.get_intervals(allocator);
        defer allocator.free(intervals);
        return intervals.len;
    }

    pub fn is_empty(self: *const Numeric_Set, allocator: std.mem.Allocator) !bool {
        return (try self.get_intervals_len(allocator)) == 0;
    }

    pub fn is_unbounded(self: *const Numeric_Set, allocator: std.mem.Allocator) bool {
        if (self.is_empty(allocator)) {
            return false;
        }
        return self.get_intervals(allocator)[0].is_unbounded();
    }

    pub fn is_finite(self: *const Numeric_Set) bool {
        if (self.is_empty()) {
            return true;
        }
        return self.get_intervals()[0].is_finite() and self.get_intervals()[self.get_intervals().len - 1].is_finite();
    }

    pub fn closest_elem(self: *const Numeric_Set, allocator: std.mem.Allocator, target: f64) !f64 {
        if (try self.is_empty(allocator)) {
            return error.Empty;
        }

        // Locate the first interval whose minimum exceeds the target. This mirrors
        // bisect() in the Python implementation to find the insertion point.
        const intervals = try self.get_intervals(allocator);
        defer allocator.free(intervals);
        var left: usize = 0;
        var right: usize = intervals.len;
        while (left < right) {
            const mid = left + (right - left) / 2;
            if (intervals[mid].get_min() <= target) {
                left = mid + 1;
            } else {
                right = mid;
            }
        }
        const index = left;

        var left_bound: ?f64 = null;
        if (index > 0) {
            const candidate = intervals[index - 1];
            if (target >= candidate.get_min() and target <= candidate.get_max()) {
                return target;
            }
            left_bound = candidate.get_max();
        }

        const right_bound: ?f64 = if (index < intervals.len) intervals[index].get_min() else null;

        // Exactly one neighbor exists (before the first interval or after the last).
        if (left_bound) |lb| {
            if (right_bound) |rb| {
                if (target - lb < rb - target) {
                    return lb;
                }
                return rb;
            }
            return lb;
        }

        if (right_bound) |rb| {
            return rb;
        }

        // The set is non-empty, so at least one boundary must exist.
        unreachable;
    }

    pub fn is_superset_of(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) bool {
        _ = g;

        const other_empty = other.is_empty(allocator) catch return false;
        if (other_empty != false) {
            return true;
        }

        const self_intervals = self.get_intervals(allocator) catch return false;
        defer allocator.free(self_intervals);

        const other_intervals = other.get_intervals(allocator) catch return false;
        defer allocator.free(other_intervals);

        var s: usize = 0;
        var o: usize = 0;

        while (o < other_intervals.len) {
            if (s >= self_intervals.len) {
                return false;
            }

            const sup = self_intervals[s];
            const sub = other_intervals[o];

            if (sub.get_min() < sup.get_min()) {
                return false;
            }

            if (sub.get_max() <= sup.get_max()) {
                o += 1;
            } else {
                s += 1;
            }
        }

        return true;
    }

    pub fn is_subset_of(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) bool {
        return other.is_superset_of(g, allocator, self);
    }

    pub fn op_intersect_interval(self: *const Numeric_Set, allocator: std.mem.Allocator, other: _Continuous) !Numeric_Set {
        var intersections = std.ArrayList(_Continuous).init(allocator);
        defer intersections.deinit();

        for (self.intervals.items) |candidate| {
            const overlap = candidate.op_intersect(other) catch |err| {
                if (err == error.Empty) continue;
                return err;
            };

            try intersections.append(overlap);
        }

        return Numeric_Set.init(allocator, intersections.items, &[_]Numeric_Set{});
    }

    pub fn op_intersect_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var result = std.ArrayList(_Continuous).init(allocator);
        defer result.deinit();

        var s: usize = 0;
        var o: usize = 0;
        while (s < self.get_intervals_len(allocator) and o < other.get_intervals_len(allocator)) {
            const rs = try self.get_intervals(allocator)[s];
            defer allocator.free(rs);
            const ro = other.get_intervals()[o];
            defer allocator.free(rs);

            if (rs.op_intersect(ro)) |overlap| {
                try result.append(overlap);
            } else |err| switch (err) {
                error.Empty => {},
                else => return err,
            }

            if (rs.max <= ro.min) {
                s += 1;
            } else if (ro.max < rs.min) {
                o += 1;
            } else if (rs.max < ro.max) {
                s += 1;
            } else if (ro.max < rs.max) {
                o += 1;
            } else {
                s += 1;
                o += 1;
            }
        }
        return try Numeric_Set.init(g, allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_union_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var combined = std.ArrayList(_Continuous).init(allocator);
        defer combined.deinit();
        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);
        const other_intervals = try other.get_intervals(allocator);
        defer allocator.free(other_intervals);
        try combined.appendSlice(self_intervals);
        try combined.appendSlice(other_intervals);

        return Numeric_Set.init(g, allocator, combined.items, &[_]Numeric_Set{});
    }

    pub fn op_difference_interval(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: _Continuous) !Numeric_Set {
        var pieces = std.ArrayList(_Continuous).init(allocator);
        defer pieces.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        for (self_intervals) |candidate| {
            var diff = try candidate.op_difference(g, allocator, other);
            const diff_intervals = try diff.get_intervals(allocator);
            defer allocator.free(diff_intervals);

            try pieces.appendSlice(diff_intervals);
        }

        return Numeric_Set.init(g, allocator, pieces.items, &[_]Numeric_Set{});
    }

    pub fn op_difference_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        const base_intervals = try self.get_intervals(allocator);
        defer allocator.free(base_intervals);

        var temp = try Numeric_Set.init(g, allocator, base_intervals, &[_]Numeric_Set{});

        const other_intervals = try other.get_intervals(allocator);
        defer allocator.free(other_intervals);

        for (other_intervals) |interval| {
            temp = try temp.op_difference_interval(g, allocator, interval);
        }

        return temp;
    }

    pub fn op_symmetric_difference_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var union_result = try self.op_union_intervals(allocator, other);
        defer union_result.deinit();

        var intersection_result = try self.op_intersect_intervals(allocator, other);
        defer intersection_result.deinit();

        return union_result.op_difference_intervals(allocator, &intersection_result);
    }

    pub fn op_add_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var result = std.ArrayList(_Continuous).init(allocator);
        defer result.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);
        const other_intervals = try other.get_intervals(allocator);
        defer allocator.free(other_intervals);

        for (self_intervals) |r| {
            for (other_intervals) |o| {
                try result.append(try r.op_add(g, o));
            }
        }

        return Numeric_Set.init(g, allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_negate(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator) !Numeric_Set {
        var result = std.ArrayList(_Continuous).init(allocator);
        defer result.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        for (self_intervals) |interval| {
            try result.append(try interval.op_negate(g));
        }

        return Numeric_Set.init(g, allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_subtract_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var negated = try other.op_negate(g, allocator);

        return self.op_add_intervals(g, allocator, &negated);
    }

    pub fn op_multiply_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var result = std.ArrayList(_Continuous).init(allocator);
        defer result.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);
        const other_intervals = try other.get_intervals(allocator);
        defer allocator.free(other_intervals);

        for (self_intervals) |r| {
            for (other_intervals) |o| {
                try result.append(try r.op_multiply(g, o));
            }
        }

        return Numeric_Set.init(g, allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_invert(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator) !Numeric_Set {
        var components = std.ArrayList(Numeric_Set).init(allocator);
        defer components.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        for (self_intervals) |interval| {
            const inverted = try interval.op_invert(g, allocator);
            try components.append(inverted);
        }

        return try Numeric_Set.init(
            g,
            allocator,
            &[_]_Continuous{},
            components.items,
        );
    }

    pub fn op_divide_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var inverted = try other.op_invert(g, allocator);

        return self.op_multiply_intervals(g, allocator, &inverted);
    }

    pub fn op_power_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        const exponents = try other.get_intervals(allocator);
        defer allocator.free(exponents);

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        var components = std.ArrayList(Numeric_Set).init(allocator);
        defer components.deinit();

        for (self_intervals) |base_interval| {
            for (exponents) |exp_interval| {
                const powered = try base_interval.op_power(g, allocator, exp_interval);
                try components.append(powered);
            }
        }

        return try Numeric_Set.init(g, allocator, &[_]_Continuous{}, components.items);
    }

    pub fn min_elem(self: *const Numeric_Set, allocator: std.mem.Allocator) !f64 {
        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        return self_intervals[0].get_min();
    }

    pub fn max_elem(self: *const Numeric_Set, allocator: std.mem.Allocator) !f64 {
        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        return self_intervals[self_intervals.len - 1].get_max();
    }

    pub fn op_ge_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Bool_Set {
        const min = try self.min_elem(allocator);
        const max = try self.max_elem(allocator);
        const other_min = try other.min_elem(allocator);
        const other_max = try other.max_elem(allocator);

        if (try self.is_empty(allocator) or try other.is_empty(allocator)) {
            return Bool_Set.init_empty(g);
        }
        if (min >= other_max) {
            return Bool_Set.init_from_single(g, true);
        }
        if (max < other_min) {
            return Bool_Set.init_from_single(g, false);
        }
        return Bool_Set.init_from_bools(g, allocator, &[_]bool{ true, false });
    }

    pub fn op_gt_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Bool_Set {
        const min = try self.min_elem(allocator);
        const max = try self.max_elem(allocator);
        const other_min = try other.min_elem(allocator);
        const other_max = try other.max_elem(allocator);

        if (try self.is_empty(allocator) or try other.is_empty(allocator)) {
            return Bool_Set.init_empty(g);
        }
        if (min > other_max) {
            return Bool_Set.init_from_single(g, true);
        }
        if (max <= other_min) {
            return Bool_Set.init_from_single(g, false);
        }
        return Bool_Set.init_from_bools(g, allocator, &[_]bool{ true, false });
    }

    pub fn op_le_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Bool_Set {
        const min = try self.min_elem(allocator);
        const max = try self.max_elem(allocator);
        const other_min = try other.min_elem(allocator);
        const other_max = try other.max_elem(allocator);

        if (try self.is_empty(allocator) or try other.is_empty(allocator)) {
            return Bool_Set.init_empty(g);
        }
        if (max <= other_min) {
            return Bool_Set.init_from_single(g, true);
        }
        if (min > other_max) {
            return Bool_Set.init_from_single(g, false);
        }
        return Bool_Set.init_from_bools(g, allocator, &[_]bool{ true, false });
    }

    pub fn op_lt_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, other: *const Numeric_Set) !Bool_Set {
        const min = try self.min_elem(allocator);
        const max = try self.max_elem(allocator);
        const other_min = try other.min_elem(allocator);
        const other_max = try other.max_elem(allocator);

        if (try self.is_empty(allocator) or try other.is_empty(allocator)) {
            return Bool_Set.init_empty(g);
        }
        if (max < other_min) {
            return Bool_Set.init_from_single(g, true);
        }
        if (min >= other_max) {
            return Bool_Set.init_from_single(g, false);
        }
        return Bool_Set.init_from_bools(g, allocator, &[_]bool{ true, false });
    }

    pub fn op_round_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator, ndigits: i32) !Numeric_Set {
        var result = std.ArrayList(_Continuous).init(allocator);
        defer result.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        for (self_intervals) |interval| {
            const rounded = try interval.op_round(g, ndigits);
            try result.append(rounded);
        }

        return Numeric_Set.init(g, allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_abs_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator) !Numeric_Set {
        var result = std.ArrayList(_Continuous).init(allocator);
        defer result.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        for (self_intervals) |interval| {
            const abs = try interval.op_abs(g);
            try result.append(abs);
        }

        return Numeric_Set.init(g, allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_log_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator) !Numeric_Set {
        var result = std.ArrayList(_Continuous).init(allocator);
        defer result.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        for (self_intervals) |interval| {
            try result.append(try interval.op_log(g));
        }

        return Numeric_Set.init(g, allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_sin_intervals(self: *const Numeric_Set, g: *GraphView, allocator: std.mem.Allocator) !Numeric_Set {
        var result = std.ArrayList(_Continuous).init(allocator);
        defer result.deinit();

        const self_intervals = try self.get_intervals(allocator);
        defer allocator.free(self_intervals);

        for (self_intervals) |interval| {
            try result.append(try interval.op_sin(g));
        }

        return Numeric_Set.init(g, allocator, result.items, &[_]Numeric_Set{});
    }
};

test "_Continuous.init initializes interval bounds" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const numeric_set = try _Continuous.init(&g, 0.0, 1.0);
    try std.testing.expectEqual(0.0, numeric_set.get_min());
    try std.testing.expectEqual(1.0, numeric_set.get_max());
}

test "_Continuous.add adds interval bounds" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.5, 3.0);
    const rhs = try _Continuous.init(&g, 0.5, 2.0);
    const result = try lhs.op_add(&g, rhs);

    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.get_max(), 1e-12);
}

test "_Continuous.negate flips bounds" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const original = try _Continuous.init(&g, -2.5, 4.0);
    const result = try original.op_negate(&g);

    try std.testing.expectApproxEqRel(@as(f64, -4.0), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.5), result.get_max(), 1e-12);
}

test "_Continuous.subtract subtracts interval bounds" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 2.0, 4.0);
    const rhs = try _Continuous.init(&g, 0.5, 1.5);
    const result = try lhs.op_subtract(&g, rhs);

    try std.testing.expectApproxEqRel(@as(f64, 0.5), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.5), result.get_max(), 1e-12);
}

test "_Continuous.multiply handles mixed signs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, -2.0, 3.0);
    const rhs = try _Continuous.init(&g, -1.0, 4.0);
    const result = try lhs.op_multiply(&g, rhs);
    try std.testing.expectApproxEqRel(@as(f64, -8.0), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 12.0), result.get_max(), 1e-12);
}

test "_Continuous.op_power raises interval to positive exponent" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const base = try _Continuous.init(&g, 1.0, 3.0);
    const exponent = try _Continuous.init(&g, 2.0, 3.0);
    const result = try base.op_power(&g, std.testing.allocator, exponent);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectApproxEqRel(@as(f64, 1.0), intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 27.0), intervals[0].get_max(), 1e-12);
}

test "_Continuous.op_power rejects negative exponent intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const base = try _Continuous.init(&g, 1.0, 2.0);
    const exponent = try _Continuous.init(&g, -2.0, -1.0);
    const result = base.op_power(&g, std.testing.allocator, exponent);

    try std.testing.expectError(_Continuous.OperationError.NegativeExponentUnsupported, result);
}

test "_Continuous.op_power rejects exponent crossing zero" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const base = try _Continuous.init(&g, 1.0, 2.0);
    const exponent = try _Continuous.init(&g, -1.0, 1.0);
    const result = base.op_power(&g, std.testing.allocator, exponent);

    try std.testing.expectError(
        _Continuous.OperationError.ExponentCrossesZero,
        result,
    );
}

test "_Continuous.op_power rejects fractional exponent on negative base interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const base = try _Continuous.init(&g, -2.0, 3.0);
    const exponent = try _Continuous.init(&g, 1.5, 1.5);

    try std.testing.expectError(
        _Continuous.OperationError.FractionalExponentRequiresIntegerExponent,
        base.op_power(&g, std.testing.allocator, exponent),
    );
}

test "_Continuous.op_sin handles interval within single period" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const interval = try _Continuous.init(&g, 0.0, std.math.pi);
    const result = try interval.op_sin(&g);

    try std.testing.expectApproxEqRel(@as(f64, 0.0), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.get_max(), 1e-12);
}

test "_Continuous.op_sin returns full range for wide intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const interval = try _Continuous.init(&g, 0.0, 10.0);
    const result = try interval.op_sin(&g);

    try std.testing.expectApproxEqRel(@as(f64, -1.0), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.get_max(), 1e-12);
}

test "_Continuous.op_sin captures local extrema inside interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const interval = try _Continuous.init(&g, -std.math.pi / 2.0, std.math.pi / 2.0);
    const result = try interval.op_sin(&g);

    try std.testing.expectApproxEqRel(@as(f64, -1.0), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.get_max(), 1e-12);
}

test "_Continuous.op_sin handles fraction of a period" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const interval = try _Continuous.init(&g, std.math.pi / 6.0, std.math.pi / 3.0);
    const result = try interval.op_sin(&g);

    try std.testing.expectApproxEqRel(@as(f64, 0.5), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, std.math.sqrt(3.0) / 2.0), result.get_max(), 1e-12);
}

test "_Continuous.op_invert returns empty for zero interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const zero_interval = try _Continuous.init(&g, 0.0, 0.0);
    var result = try zero_interval.op_invert(&g, std.testing.allocator);
    try std.testing.expect((try result.is_empty(std.testing.allocator)));
}

test "_Continuous.op_invert returns empty disjoint for zero interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const interval = try _Continuous.init(&g, 0.0, 0.0);
    const result = try interval.op_invert(&g, std.testing.allocator);

    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 0), intervals.len);
}

test "_Continuous.op_invert splits interval crossing zero" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const interval = try _Continuous.init(&g, -2.0, 4.0);
    const result = try interval.op_invert(&g, std.testing.allocator);

    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 2), intervals.len);
    try std.testing.expect(intervals[0].get_min() == -std.math.inf(f64));
    try std.testing.expectApproxEqRel(@as(f64, -0.5), intervals[0].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 0.25), intervals[1].get_min(), 1e-12);
    try std.testing.expect(intervals[1].get_max() == std.math.inf(f64));
}

test "_Continuous.op_invert handles negative-only intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const interval = try _Continuous.init(&g, -5.0, -1.0);
    const result = try interval.op_invert(&g, allocator);

    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, -1.0), intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -0.2), intervals[0].get_max(), 1e-12);
}

test "_Continuous.op_invert handles positive-only intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const interval = try _Continuous.init(&g, 2.0, 5.0);
    const result = try interval.op_invert(&g, allocator);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 0.2), intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 0.5), intervals[0].get_max(), 1e-12);
}

test "_Continuous.op_invert handles negative-to-zero interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const interval = try _Continuous.init(&g, -4.0, 0.0);
    const result = try interval.op_invert(&g, allocator);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expect(intervals[0].get_min() == -std.math.inf(f64));
    try std.testing.expectApproxEqRel(@as(f64, -0.25), intervals[0].get_max(), 1e-12);
}

test "_Continuous.op_invert handles zero-to-positive interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const interval = try _Continuous.init(&g, 0.0, 4.0);
    const result = try interval.op_invert(&g, allocator);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 0.25), intervals[0].get_min(), 1e-12);
    try std.testing.expect(intervals[0].get_max() == std.math.inf(f64));
}
test "_Continuous.op_divide divides interval by positive interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 2.0, 4.0);
    const rhs = try _Continuous.init(&g, 1.0, 2.0);
    const result = try lhs.op_divide(&g, std.testing.allocator, rhs);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectApproxEqRel(@as(f64, 1.0), intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), intervals[0].get_max(), 1e-12);
}

test "_Continuous.op_divide splits when denominator spans zero" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 2.0);
    const rhs = try _Continuous.init(&g, -1.0, 1.0);
    var result = try lhs.op_divide(&g, std.testing.allocator, rhs);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    // Python implementation returns two semi-infinite ranges; mirror that shape here.
    try std.testing.expect(!(try result.is_empty(std.testing.allocator)));
    try std.testing.expectEqual(@as(usize, 2), intervals.len);

    const neg_branch = intervals[0];
    const pos_branch = intervals[1];

    try std.testing.expect(std.math.isInf(neg_branch.get_min()));
    try std.testing.expectApproxEqRel(@as(f64, -1.0), neg_branch.get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), pos_branch.get_min(), 1e-12);
    try std.testing.expect(std.math.isInf(pos_branch.get_max()));
}

test "_Continuous.init rejects NaN bounds" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const qnan = std.math.nan(f64);
    try std.testing.expectError(_Continuous.Error.NaNMin, _Continuous.init(&g, qnan, 1.0));
    try std.testing.expectError(_Continuous.Error.NaNMax, _Continuous.init(&g, 1.0, qnan));
    try std.testing.expectError(
        _Continuous.Error.NaNMin,
        _Continuous.init(&g, qnan, 1.0),
    );
    try std.testing.expectError(
        _Continuous.Error.NaNMax,
        _Continuous.init(&g, 0.0, qnan),
    );
}

test "_Continuous.op_intersect returns overlap interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 5.0);
    const rhs = try _Continuous.init(&g, 3.0, 7.0);
    const result = try lhs.op_intersect(&g, rhs);

    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.get_max(), 1e-12);
}

test "_Continuous.op_intersect returns single point when touching" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 3.0);
    const rhs = try _Continuous.init(&g, 3.0, 4.0);
    const result = try lhs.op_intersect(&g, rhs);

    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.get_max(), 1e-12);
}

test "_Continuous.op_intersect returns empty when disjoint" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 2.0);
    const rhs = try _Continuous.init(&g, 3.0, 4.0);
    try std.testing.expectError(_Continuous.Error.Empty, lhs.op_intersect(&g, rhs));
}

test "_Continuous.op_difference returns original when disjoint" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 3.0);
    const rhs = try _Continuous.init(&g, 4.0, 5.0);
    const result = try lhs.op_difference(&g, std.testing.allocator, rhs);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), intervals[0].get_max(), 1e-12);
}

test "_Continuous.op_difference returns empty when fully covered" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 3.0);
    const rhs = try _Continuous.init(&g, 0.0, 5.0);
    const result = try lhs.op_difference(&g, std.testing.allocator, rhs);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 0), intervals.len);
}

test "_Continuous.op_difference returns single segment when overlapping right" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 5.0);
    const rhs = try _Continuous.init(&g, 3.0, 6.0);
    const result = try lhs.op_difference(&g, std.testing.allocator, rhs);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), intervals[0].get_max(), 1e-12);
}

test "_Continuous.op_difference returns single segment when overlapping left" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 5.0);
    const rhs = try _Continuous.init(&g, -1.0, 2.0);
    const result = try lhs.op_difference(&g, std.testing.allocator, rhs);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), intervals[0].get_max(), 1e-12);
}

test "_Continuous.op_difference returns two segments when other is inside" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try _Continuous.init(&g, 1.0, 6.0);
    const rhs = try _Continuous.init(&g, 2.0, 4.0);
    const result = try lhs.op_difference(&g, std.testing.allocator, rhs);
    const intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 2), intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), intervals[0].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 6.0), intervals[1].get_max(), 1e-12);
}

test "Numeric_Set.init_empty" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const numeric_set = try Numeric_Set.init_empty(&g, std.testing.allocator);
    try std.testing.expectEqual(0, try numeric_set.get_intervals_len(std.testing.allocator));
}

test "Numeric_Set.init_from_single" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const numeric_set = try Numeric_Set.init_from_single(&g, std.testing.allocator, try _Continuous.init(&g, 1.0, 3.0));
    try std.testing.expectEqual(1, try numeric_set.get_intervals_len(std.testing.allocator));
    const intervals = try numeric_set.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);
    try std.testing.expectEqual(1.0, intervals[0].get_min());
    try std.testing.expectEqual(3.0, intervals[0].get_max());
}

test "Numeric_Set.init with 3 intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const numeric_set = try Numeric_Set.init(&g, std.testing.allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.0),
        try _Continuous.init(&g, 5.0, 7.0),
        try _Continuous.init(&g, 9.0, 11.0),
    }, &[_]Numeric_Set{});
    try std.testing.expectEqual(3, try numeric_set.get_intervals_len(std.testing.allocator));
    const result_intervals = try numeric_set.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);
    try std.testing.expectEqual(1.0, result_intervals[0].get_min());
    try std.testing.expectEqual(3.0, result_intervals[0].get_max());
    try std.testing.expectEqual(5.0, result_intervals[1].get_min());
    try std.testing.expectEqual(7.0, result_intervals[1].get_max());
    try std.testing.expectEqual(9.0, result_intervals[2].get_min());
    try std.testing.expectEqual(11.0, result_intervals[2].get_max());
}
test "Numeric_Set.init basic case" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const intervals = [2]_Continuous{
        try _Continuous.init(&g, 1.0, 3.0),
        try _Continuous.init(&g, 5.0, 7.0),
    };

    const disjoint = try Numeric_Set.init(&g, std.testing.allocator, &intervals, &[_]Numeric_Set{});
    const result_intervals = try disjoint.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    try std.testing.expectEqual(@as(usize, 2), result_intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result_intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result_intervals[0].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result_intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), result_intervals[1].get_max(), 1e-12);
}

test "Numeric_Set.init merges and sorts intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const nested_disjoint = try Numeric_Set.init(&g, std.testing.allocator, &[_]_Continuous{
        try _Continuous.init(&g, 6.0, 8.0),
        try _Continuous.init(&g, 10.0, 12.0),
    }, &[_]Numeric_Set{});

    const intervals = [_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.0),
        try _Continuous.init(&g, 4.0, 7.0),
        try _Continuous.init(&g, 9.0, 11.0),
    };
    const disjoint = try Numeric_Set.init(&g, std.testing.allocator, &intervals, &[_]Numeric_Set{nested_disjoint});
    const result_intervals = try disjoint.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    try std.testing.expectEqual(@as(usize, 3), result_intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result_intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result_intervals[0].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), result_intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), result_intervals[1].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 9.0), result_intervals[2].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 12.0), result_intervals[2].get_max(), 1e-12);
}

test "Numeric_Set.closest_elem handles relative positions" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const interval_a = try _Continuous.init(&g, 1.0, 3.0);
    const interval_b = try _Continuous.init(&g, 5.0, 7.0);
    var set = try Numeric_Set.init(&g, std.testing.allocator, &[_]_Continuous{ interval_a, interval_b }, &[_]Numeric_Set{});
    const result_intervals = try set.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    const below = try set.closest_elem(std.testing.allocator, 0.2);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), below, 1e-12);

    const inside = try set.closest_elem(std.testing.allocator, 2.4);
    try std.testing.expectApproxEqRel(@as(f64, 2.4), inside, 1e-12);

    const between = try set.closest_elem(std.testing.allocator, 4.2);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), between, 1e-12);

    const above = try set.closest_elem(std.testing.allocator, 9.5);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), above, 1e-12);
}

test "Numeric_Set.is_superset_of handles various cases" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const outer_intervals = [_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.5),
        try _Continuous.init(&g, 5.0, 7.5),
    };
    const inner_intervals = [_]_Continuous{
        try _Continuous.init(&g, 1.5, 2.0),
        try _Continuous.init(&g, 6.0, 6.8),
    };
    const partial_intervals = [_]_Continuous{
        try _Continuous.init(&g, 0.5, 2.0),
    };

    var outer = try Numeric_Set.init(&g, std.testing.allocator, &outer_intervals, &[_]Numeric_Set{});
    var inner = try Numeric_Set.init(&g, std.testing.allocator, &inner_intervals, &[_]Numeric_Set{});
    var partial = try Numeric_Set.init(&g, std.testing.allocator, &partial_intervals, &[_]Numeric_Set{});
    var empty = try Numeric_Set.init_empty(&g, std.testing.allocator);

    const allocator = std.testing.allocator;

    try std.testing.expect(outer.is_superset_of(&g, allocator, &inner));
    try std.testing.expect(outer.is_superset_of(&g, allocator, &empty));
    try std.testing.expect(outer.is_superset_of(&g, allocator, &outer));

    try std.testing.expect(!inner.is_superset_of(&g, allocator, &outer));
    try std.testing.expect(!partial.is_superset_of(&g, allocator, &outer));
}

test "Numeric_Set.is_subset_of handles various cases" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const outer_intervals = [_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.5),
        try _Continuous.init(&g, 5.0, 7.5),
    };
    const inner_intervals = [_]_Continuous{
        try _Continuous.init(&g, 1.5, 2.0),
        try _Continuous.init(&g, 6.0, 6.8),
    };
    const partial_intervals = [_]_Continuous{
        try _Continuous.init(&g, 0.5, 2.0),
    };

    var outer = try Numeric_Set.init(&g, std.testing.allocator, &outer_intervals, &[_]Numeric_Set{});
    var inner = try Numeric_Set.init(&g, std.testing.allocator, &inner_intervals, &[_]Numeric_Set{});
    var partial = try Numeric_Set.init(&g, std.testing.allocator, &partial_intervals, &[_]Numeric_Set{});
    var empty = try Numeric_Set.init_empty(&g, std.testing.allocator);
    const allocator = std.testing.allocator;

    try std.testing.expect(inner.is_subset_of(&g, allocator, &outer));
    try std.testing.expect(empty.is_subset_of(&g, allocator, &outer));
    try std.testing.expect(outer.is_subset_of(&g, allocator, &outer));

    try std.testing.expect(!outer.is_subset_of(&g, allocator, &inner));
    try std.testing.expect(!partial.is_subset_of(&g, allocator, &outer));
}

test "Numeric_Set.op_union_intervals handles various cases" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const lhs = try Numeric_Set.init(&g, std.testing.allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.0),
        try _Continuous.init(&g, 5.0, 7.0),
    }, &[_]Numeric_Set{});

    const rhs = try Numeric_Set.init(&g, std.testing.allocator, &[_]_Continuous{
        try _Continuous.init(&g, 2.0, 4.0),
        try _Continuous.init(&g, 6.0, 8.0),
    }, &[_]Numeric_Set{});

    const result = try lhs.op_union_intervals(&g, std.testing.allocator, &rhs);
    const result_intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    try std.testing.expectEqual(@as(usize, 2), result_intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result_intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), result_intervals[0].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result_intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), result_intervals[1].get_max(), 1e-12);
}

test "Numeric_Set.op_difference_interval handles overlap" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var base = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 4.0),
        try _Continuous.init(&g, 6.0, 8.0),
    }, &[_]Numeric_Set{});

    const subtract = try _Continuous.init(&g, 2.0, 7.0);

    var result = try base.op_difference_interval(&g, allocator, subtract);
    const result_intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    try std.testing.expectEqual(@as(usize, 2), result_intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result_intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), result_intervals[0].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), result_intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), result_intervals[1].get_max(), 1e-12);
}

test "Numeric_Set.op_difference_intervals handles multiple subtractions" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var base = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 0.0, 5.0),
        try _Continuous.init(&g, 6.0, 10.0),
    }, &[_]Numeric_Set{});

    var subtract = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
        try _Continuous.init(&g, 7.0, 9.0),
    }, &[_]Numeric_Set{});

    var result = try base.op_difference_intervals(&g, allocator, &subtract);
    const result_intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    try std.testing.expectEqual(@as(usize, 4), result_intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, 0.0), result_intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result_intervals[0].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), result_intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result_intervals[1].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 6.0), result_intervals[2].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), result_intervals[2].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 9.0), result_intervals[3].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 10.0), result_intervals[3].get_max(), 1e-12);
}

test "Numeric_Set.op_add_intervals sums pairwise intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
        try _Continuous.init(&g, 4.0, 5.0),
    }, &[_]Numeric_Set{});

    var rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 10.0, 11.0),
        try _Continuous.init(&g, 20.0, 22.0),
    }, &[_]Numeric_Set{});

    const result = try lhs.op_add_intervals(&g, allocator, &rhs);
    const result_intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    try std.testing.expectEqual(@as(usize, 3), result_intervals.len);

    try std.testing.expectApproxEqRel(@as(f64, 11.0), result_intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 13.0), result_intervals[0].get_max(), 1e-12);

    try std.testing.expectApproxEqRel(@as(f64, 14.0), result_intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 16.0), result_intervals[1].get_max(), 1e-12);

    try std.testing.expectApproxEqRel(@as(f64, 21.0), result_intervals[2].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 27.0), result_intervals[2].get_max(), 1e-12);
}

test "Numeric_Set.op_negate flips all intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var original = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.0),
        try _Continuous.init(&g, 5.0, 6.0),
    }, &[_]Numeric_Set{});

    const negated = try original.op_negate(&g, allocator);
    const negated_intervals = try negated.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(negated_intervals);

    try std.testing.expectEqual(@as(usize, 2), negated_intervals.len);
    try std.testing.expectApproxEqRel(@as(f64, -6.0), negated_intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -5.0), negated_intervals[0].get_max(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -3.0), negated_intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -1.0), negated_intervals[1].get_max(), 1e-12);
}

test "Numeric_Set.op_subtract_intervals subtracts via negation and add" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 5.0, 7.0),
        try _Continuous.init(&g, 10.0, 12.0),
    }, &[_]Numeric_Set{});

    var rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 2.0, 3.0),
        try _Continuous.init(&g, 1.0, 1.5),
    }, &[_]Numeric_Set{});

    var negated_rhs = try rhs.op_negate(&g, allocator);
    const negated_rhs_intervals = try negated_rhs.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(negated_rhs_intervals);

    var difference = try lhs.op_subtract_intervals(&g, allocator, &rhs);
    const difference_intervals = try difference.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(difference_intervals);

    var manual = try lhs.op_add_intervals(&g, allocator, &negated_rhs);
    const manual_intervals = try manual.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(manual_intervals);

    try std.testing.expectEqual(@as(usize, manual_intervals.len), difference_intervals.len);

    for (manual_intervals, difference_intervals) |expected, actual| {
        try std.testing.expectApproxEqRel(expected.get_min(), actual.get_min(), 1e-12);
        try std.testing.expectApproxEqRel(expected.get_max(), actual.get_max(), 1e-12);
    }
}

test "Numeric_Set.op_multiply_intervals multiplies pairwise intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, -2.0, -1.0),
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});

    var rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 0.5, 1.5),
        try _Continuous.init(&g, 2.0, 3.0),
    }, &[_]Numeric_Set{});

    var result = try lhs.op_multiply_intervals(&g, allocator, &rhs);
    const result_intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    try std.testing.expectEqual(@as(usize, 2), result_intervals.len);

    try std.testing.expectApproxEqRel(@as(f64, -6.0), result_intervals[0].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -0.5), result_intervals[0].get_max(), 1e-12);

    try std.testing.expectApproxEqRel(@as(f64, 1.5), result_intervals[1].get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 12.0), result_intervals[1].get_max(), 1e-12);
}

test "Numeric_Set.op_divide_intervals divides pairwise intervals" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var numerator = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 6.0, 8.0),
        try _Continuous.init(&g, -4.0, -2.0),
    }, &[_]Numeric_Set{});

    var denominator = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 2.0, 3.0),
        try _Continuous.init(&g, -1.5, -0.5),
    }, &[_]Numeric_Set{});

    var div_result = try numerator.op_divide_intervals(&g, allocator, &denominator);
    const div_result_intervals = try div_result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(div_result_intervals);

    try std.testing.expectEqual(@as(usize, 3), div_result_intervals.len);

    const first = div_result_intervals[0];
    try std.testing.expectApproxEqRel(@as(f64, -16.0), first.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -4.0), first.get_max(), 1e-12);

    const second = div_result_intervals[1];
    try std.testing.expectApproxEqRel(@as(f64, -2.0), second.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -2.0 / 3.0), second.get_max(), 1e-12);

    const third = div_result_intervals[2];
    try std.testing.expectApproxEqRel(@as(f64, 4.0 / 3.0), third.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), third.get_max(), 1e-12);
}

test "Numeric_Set.op_power_intervals raises pairwise combinations" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var bases = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});

    var exponents = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 2.0, 2.5),
        try _Continuous.init(&g, 3.0, 3.5),
    }, &[_]Numeric_Set{});

    var result = try bases.op_power_intervals(&g, allocator, &exponents);
    const result_intervals = try result.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(result_intervals);

    try std.testing.expectEqual(@as(usize, 1), result_intervals.len);

    const combined = result_intervals[0];
    try std.testing.expectApproxEqRel(@as(f64, std.math.pow(f64, 1.0, 2.0)), combined.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, std.math.pow(f64, 4.0, 3.5)), combined.get_max(), 1e-12);
}

test "Numeric_Set.op_round_intervals rounds each interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var set = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.2345, 2.3456),
        try _Continuous.init(&g, -3.8765, -1.2345),
    }, &[_]Numeric_Set{});

    var rounded = try set.op_round_intervals(&g, allocator, 2);
    const rounded_intervals = try rounded.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(rounded_intervals);

    try std.testing.expectEqual(@as(usize, 2), rounded_intervals.len);

    const negative = rounded_intervals[0];
    try std.testing.expectApproxEqRel(@as(f64, -3.88), negative.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -1.23), negative.get_max(), 1e-12);

    const positive = rounded_intervals[1];
    try std.testing.expectApproxEqRel(@as(f64, 1.23), positive.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.35), positive.get_max(), 1e-12);
}

test "Numeric_Set.op_abs_intervals takes absolute value of each interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var set = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, -4.5, -2.5),
        try _Continuous.init(&g, -1.0, 3.0),
    }, &[_]Numeric_Set{});

    const abs_set = try set.op_abs_intervals(&g, allocator);
    const abs_set_intervals = try abs_set.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(abs_set_intervals);

    try std.testing.expectEqual(@as(usize, 1), abs_set_intervals.len);

    const first = abs_set_intervals[0];
    try std.testing.expectApproxEqRel(@as(f64, 0.0), first.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.5), first.get_max(), 1e-12);
}

test "Numeric_Set.op_log_intervals takes natural log of each interval" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var set = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.0),
        try _Continuous.init(&g, 5.0, 8.0),
    }, &[_]Numeric_Set{});

    var logged = try set.op_log_intervals(&g, allocator);
    const logged_intervals = try logged.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(logged_intervals);

    try std.testing.expectEqual(@as(usize, 2), logged_intervals.len);

    const first = logged_intervals[0];
    try std.testing.expectApproxEqRel(@as(f64, std.math.log(f64, std.math.e, 1.0)), first.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, std.math.log(f64, std.math.e, 3.0)), first.get_max(), 1e-12);

    const second = logged_intervals[1];
    try std.testing.expectApproxEqRel(@as(f64, std.math.log(f64, std.math.e, 5.0)), second.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, std.math.log(f64, std.math.e, 8.0)), second.get_max(), 1e-12);
}

test "Numeric_Set.op_sin_intervals applies sine envelope" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    var set = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 0.0, std.math.pi / 2.0),
        try _Continuous.init(&g, std.math.pi, 3.0 * std.math.pi / 2.0),
    }, &[_]Numeric_Set{});

    var sin = try set.op_sin_intervals(&g, allocator);
    const sin_intervals = try sin.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(sin_intervals);

    try std.testing.expectEqual(@as(usize, 1), sin_intervals.len);

    const combined = sin_intervals[0];
    try std.testing.expectApproxEqRel(@as(f64, -1.0), combined.get_min(), 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), combined.get_max(), 1e-12);
}

test "Numeric_Set.get_min_elem returns the minimum element of the set" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    const set = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});

    const min = try set.min_elem(std.testing.allocator);

    try std.testing.expectApproxEqRel(@as(f64, 1.0), min, 1e-12);
}

test "Numeric_Set.get_max_elem returns the maximum element of the set" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    const set = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});

    const max = try set.max_elem(std.testing.allocator);

    try std.testing.expectApproxEqRel(@as(f64, 2.0), max, 1e-12);
}

test "Numeric_Set.op_ge_intervals returns false when lhs is less than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;

    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});

    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});

    const result = try lhs.op_ge_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);

    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(!result_bools[0].get_value());
}

test "Numeric_Set.op_ge_intervals returns true when lhs is greater than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_ge_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(result_bools[0].get_value());
}

test "Numeric_Set.op_gt_intervals returns false when lhs is less than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_gt_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(!result_bools[0].get_value());
}

test "Numeric_Set.op_gt_intervals returns false when lhs is equal to rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const val = 1.0;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, val, val),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, val, val),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_gt_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(!result_bools[0].get_value());
}

test "Numeric_Set.op_gt_intervals returns true when lhs is greater than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_gt_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(result_bools[0].get_value());
}

test "Numeric_Set.op_gt_intervals returns true and false when lhs is both greater and less than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 5.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_gt_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 2), result_bools.len);
    try std.testing.expect(result_bools[0].get_value());
    try std.testing.expect(!result_bools[1].get_value());
}

test "Numeric_Set.op_le_intervals returns false when lhs is greater than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_le_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(!result_bools[0].get_value());
}

test "Numeric_Set.op_le_intervals returns true when lhs is equal to rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const val = 1.0;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, val, val),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, val, val),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_le_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(result_bools[0].get_value());
}

test "Numeric_Set.op_le_intervals returns true and false when lhs is both less and greater than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 2.0, 4.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_le_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 2), result_bools.len);
    try std.testing.expect(result_bools[0].get_value());
    try std.testing.expect(!result_bools[1].get_value());
}

test "Numeric_Set.op_lt_intervals returns false when lhs is greater than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_lt_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(!result_bools[0].get_value());
}

test "Numeric_Set.op_lt_intervals returns false when lhs is equal to rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_lt_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(!result_bools[0].get_value());
}

test "Numeric_Set.op_lt_intervals returns true when lhs is less than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 2.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 3.0, 4.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_lt_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 1), result_bools.len);
    try std.testing.expect(result_bools[0].get_value());
}

test "Numeric_Set.op_lt_intervals returns true and false when lhs is both less and greater than rhs" {
    var g = GraphView.init(std.testing.allocator);
    defer g.deinit();
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 1.0, 3.0),
    }, &[_]Numeric_Set{});
    const rhs = try Numeric_Set.init(&g, allocator, &[_]_Continuous{
        try _Continuous.init(&g, 2.0, 4.0),
    }, &[_]Numeric_Set{});
    const result = try lhs.op_lt_intervals(&g, allocator, &rhs);
    const result_bools = try result.get_bools(std.testing.allocator);
    defer std.testing.allocator.free(result_bools);
    try std.testing.expectEqual(@as(usize, 2), result_bools.len);
    try std.testing.expect(result_bools[0].get_value());
    try std.testing.expect(!result_bools[1].get_value());
}
