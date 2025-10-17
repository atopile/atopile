const std = @import("std");
const Bool_Set = @import("./bool_sets.zig").Bool_Set;

pub const _Continious = struct {
    min: f64,
    max: f64,

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

    pub fn init(min: f64, max: f64) Error!_Continious {
        if (std.math.isNan(min)) return error.NaNMin;
        if (std.math.isNan(max)) return error.NaNMax;
        if (!std.math.isFinite(min)) return error.InfiniteMin;
        if (!std.math.isFinite(max)) return error.InfiniteMax;
        if (min > max) return error.InvalidBounds;

        return _Continious{
            .min = min,
            .max = max,
        };
    }

    pub fn is_empty() bool {
        return false;
    }

    pub fn is_unbounded(self: _Continious) bool {
        return self.min == -std.math.inf(f64) and self.max == std.math.inf(f64);
    }

    pub fn is_finite(self: _Continious) bool {
        if (self.is_empty()) {
            return true;
        }

        return self.min != -std.math.inf(f64) and self.max != std.math.inf(f64);
    }

    pub fn is_integer(self: _Continious) bool {
        return self.is_single_element() and @mod(self.min, 1.0) == 0.0;
    }

    pub fn as_center_rel(self: _Continious) CenterRel {
        if (self.is_single_element()) {
            return .{ .center = self.min, .relative = 0.0 };
        }
        if (!self.is_finite()) {
            return .{ .center = self.min, .relative = std.math.inf(f64) };
        }
        const center = (self.min + self.max) / 2.0;
        const rel = (self.max - self.min) / (2.0 * center);
        return .{ .center = center, .relative = rel };
    }

    pub const CenterRel = struct {
        center: f64,
        relative: f64,
    };

    pub fn is_subset_of(self: _Continious, other: _Continious) bool {
        return self.min >= other.min and self.max <= other.max;
    }

    pub fn op_add(self: _Continious, other: _Continious) _Continious {
        return _Continious{
            .min = self.min + other.min,
            .max = self.max + other.max,
        };
    }

    pub fn op_negate(self: _Continious) _Continious {
        return _Continious{
            .min = -self.max,
            .max = -self.min,
        };
    }

    pub fn op_subtract(self: _Continious, other: _Continious) _Continious {
        return self.op_add(other.op_negate());
    }

    pub fn op_multiply(
        self: _Continious,
        other: _Continious,
    ) _Continious {
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

        const prod_a = GuardedMul.op(self.min, other.min);
        const prod_b = GuardedMul.op(self.min, other.max);
        const prod_c = GuardedMul.op(self.max, other.min);
        const prod_d = GuardedMul.op(self.max, other.max);

        var min_val = prod_a;
        min_val = @min(min_val, prod_b);
        min_val = @min(min_val, prod_c);
        min_val = @min(min_val, prod_d);

        var max_val = prod_a;
        max_val = @max(max_val, prod_b);
        max_val = @max(max_val, prod_c);
        max_val = @max(max_val, prod_d);

        return _Continious{
            .min = min_val,
            .max = max_val,
        };
    }

    pub fn op_power(
        self: _Continious,
        allocator: std.mem.Allocator,
        exponent: _Continious,
    ) !Numeric_Set {
        if (exponent.max < 0.0) {
            return OperationError.NegativeExponentUnsupported;
        }

        const base_min = self.min;
        const base_max = self.max;
        const exp_min = exponent.min;
        const exp_max = exponent.max;

        if (exp_min < 0.0) {
            return OperationError.ExponentCrossesZero;
        }
        if (base_min < 0.0 and self.max > 0.0 and @mod(exp_max, 1.0) != 0.0) {
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

        return try Numeric_Set.init_from_single(allocator, try _Continious.init(min_val, max_val));
    }

    pub fn op_invert(self: _Continious, allocator: std.mem.Allocator) !Numeric_Set {
        const neg_inf = -std.math.inf(f64);
        const pos_inf = std.math.inf(f64);

        if (self.min == 0.0 and self.max == 0.0) {
            return try Numeric_Set.init_empty(allocator);
        }

        if (self.min < 0.0 and self.max > 0.0) {
            return Numeric_Set.init(allocator, &[_]_Continious{
                _Continious{ .min = neg_inf, .max = 1.0 / self.min },
                _Continious{ .min = 1.0 / self.max, .max = pos_inf },
            }, &[_]Numeric_Set{});
        }

        if (self.min < 0.0 and self.max == 0.0) {
            return Numeric_Set.init(allocator, &[_]_Continious{
                _Continious{ .min = neg_inf, .max = 1.0 / self.min },
            }, &[_]Numeric_Set{});
        }

        if (self.min == 0.0 and self.max > 0.0) {
            return Numeric_Set.init(allocator, &[_]_Continious{
                _Continious{ .min = 1.0 / self.max, .max = pos_inf },
            }, &[_]Numeric_Set{});
        }

        return Numeric_Set.init(allocator, &[_]_Continious{
            _Continious{ .min = 1.0 / self.max, .max = 1.0 / self.min },
        }, &[_]Numeric_Set{});
    }

    pub fn op_divide(self: _Continious, allocator: std.mem.Allocator, other: _Continious) !Numeric_Set {
        var inverse_other = try other.op_invert(allocator);
        defer inverse_other.deinit();

        var products = std.ArrayList(_Continious).init(allocator);
        defer products.deinit();

        for (inverse_other.intervals.items) |r| {
            try products.append(self.op_multiply(r));
        }

        return try Numeric_Set.init(allocator, products.items, &[_]Numeric_Set{});
    }

    pub fn op_intersect(self: _Continious, other: _Continious) Error!_Continious {
        const lower = @max(self.min, other.min);
        const upper = @min(self.max, other.max);

        if (lower <= upper) {
            return _Continious{
                .min = lower,
                .max = upper,
            };
        }

        return Error.Empty;
    }

    pub fn op_difference(self: @This(), allocator: std.mem.Allocator, other: _Continious) !Numeric_Set {

        // case: no overlap
        if (self.max <= other.min or self.min >= other.max) {
            return try Numeric_Set.init_from_single(allocator, self);
        }

        // case: other completely covers self
        if (other.min <= self.min and other.max >= self.max) {
            return try Numeric_Set.init_empty(allocator);
        }

        // case: other is in the middle, splitting self into two pieces
        if (self.min < other.min and self.max > other.max) {
            return try Numeric_Set.init(allocator, &[_]_Continious{
                _Continious{ .min = self.min, .max = other.min },
                _Continious{ .min = other.max, .max = self.max },
            }, &[_]Numeric_Set{});
        }

        // case: overlap on right side
        if (self.min < other.min) {
            return try Numeric_Set.init_from_interval(allocator, self.min, other.min);
        }

        // case: overlap on left side
        return try Numeric_Set.init_from_interval(allocator, other.max, self.max);
    }

    pub fn op_round(self: _Continious, ndigits: i32) Error!_Continious {
        const factor = std.math.pow(f64, 10.0, @as(f64, @floatFromInt(ndigits)));
        return _Continious{
            .min = std.math.round(self.min * factor) / factor,
            .max = std.math.round(self.max * factor) / factor,
        };
    }

    pub fn op_abs(self: _Continious) !_Continious {
        if (self.min < 0.0 and self.max > 0.0) {
            return _Continious.init(0.0, self.max);
        }
        if (self.min < 0.0 and self.max < 0.0) {
            return _Continious.init(-self.max, -self.min);
        }
        if (self.min < 0.0 and self.max == 0.0) {
            return _Continious.init(0.0, -self.min);
        }
        if (self.min == 0.0 and self.max < 0.0) {
            return _Continious.init(self.max, 0.0);
        }
        return self;
    }

    pub fn op_log(self: _Continious) Error!_Continious {
        if (self.min <= 0.0) return Error.NonPositiveLog;
        return _Continious{ .min = std.math.log(f64, std.math.e, self.min), .max = std.math.log(f64, std.math.e, self.max) };
    }

    pub fn op_sin(self: _Continious) Error!_Continious {
        // The extrema of sin(x) on an interval occur at the endpoints or at the
        // turning points x = π/2 + π·k that fall within the interval. For
        // intervals wider than a full period or containing infinities we can
        // shortcut to [-1, 1].
        const pi = std.math.pi;
        const interval_width = self.max - self.min;

        if (!std.math.isFinite(interval_width) or interval_width > 2.0 * pi) {
            return _Continious{ .min = -1.0, .max = 1.0 };
        }

        const start_sin = std.math.sin(self.min);
        const end_sin = std.math.sin(self.max);

        var min_val = @min(start_sin, end_sin);
        var max_val = @max(start_sin, end_sin);

        const half_pi = pi / 2.0;
        const k_start_f = std.math.ceil((self.min - half_pi) / pi);
        const k_end_f = std.math.floor((self.max - half_pi) / pi);

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

        return _Continious{ .min = min_val, .max = max_val };
    }

    pub fn is_single_element(self: _Continious) bool {
        return self.min == self.max;
    }

    pub fn isInteger(self: _Continious) bool {
        return self.is_single_element() and is_integer(self.min);
    }

    fn intervalLess(_: void, a: _Continious, b: _Continious) bool {
        return a.min < b.min;
    }
};

pub const Numeric_Set = struct {
    intervals: std.ArrayList(_Continious),

    pub const Error = error{
        Empty,
    };

    pub fn init_empty(allocator: std.mem.Allocator) !Numeric_Set {
        return try Numeric_Set.init(allocator, &[_]_Continious{}, &[_]Numeric_Set{});
    }

    pub fn init_from_single(allocator: std.mem.Allocator, input: _Continious) !Numeric_Set {
        return try Numeric_Set.init(allocator, &[_]_Continious{input}, &[_]Numeric_Set{});
    }

    pub fn init_from_interval(allocator: std.mem.Allocator, min: f64, max: f64) !Numeric_Set {
        return try Numeric_Set.init_from_single(allocator, try _Continious.init(min, max));
    }

    pub fn init(allocator: std.mem.Allocator, continuous_inputs: []const _Continious, set_inputs: []const Numeric_Set) !Numeric_Set {
        var total_capacity = continuous_inputs.len;
        for (set_inputs) |set| {
            total_capacity += set.intervals.items.len;
        }

        var out = Numeric_Set{
            .intervals = try std.ArrayList(_Continious).initCapacity(allocator, total_capacity),
        };

        var temp = std.ArrayList(_Continious).init(allocator);
        defer temp.deinit();

        // flatten
        for (continuous_inputs) |r| {
            try temp.append(r);
        }

        for (set_inputs) |d| {
            for (d.intervals.items) |r| {
                try temp.append(r);
            }
        }

        if (temp.items.len == 0) {
            return out;
        }

        // sort by min element
        std.mem.sort(
            _Continious,
            temp.items,
            {},
            _Continious.intervalLess,
        );

        // merge
        var cur_min = temp.items[0].min;
        var cur_max = temp.items[0].max;

        for (temp.items[1..]) |r| {
            if (cur_max >= r.min) {
                cur_max = @max(cur_max, r.max);
            } else {
                out.intervals.appendAssumeCapacity(_Continious{ .min = cur_min, .max = cur_max });
                cur_min = r.min;
                cur_max = r.max;
            }
        }
        out.intervals.appendAssumeCapacity(_Continious{ .min = cur_min, .max = cur_max });

        return out;
    }

    pub fn deinit(self: *const Numeric_Set) void {
        self.intervals.deinit();
    }

    pub fn is_empty(self: *const Numeric_Set) bool {
        return self.intervals.items.len == 0;
    }

    pub fn is_unbounded(self: *const Numeric_Set) bool {
        if (self.is_empty()) {
            return false;
        }
        return self.intervals.items[0].is_unbounded();
    }

    pub fn is_finite(self: *const Numeric_Set) bool {
        if (self.is_empty()) {
            return true;
        }
        return self.intervals.items[0].is_finite() and self.intervals.items[self.intervals.items.len - 1].is_finite();
    }

    pub fn closest_elem(self: *const Numeric_Set, target: f64) !f64 {
        if (self.is_empty()) {
            return Error.Empty;
        }

        const intervals = self.intervals.items;

        // Locate the first interval whose minimum exceeds the target. This mirrors
        // bisect() in the Python implementation to find the insertion point.
        var left: usize = 0;
        var right: usize = intervals.len;
        while (left < right) {
            const mid = left + (right - left) / 2;
            if (intervals[mid].min <= target) {
                left = mid + 1;
            } else {
                right = mid;
            }
        }
        const index = left;

        var left_bound: ?f64 = null;
        if (index > 0) {
            const candidate = intervals[index - 1];
            if (target >= candidate.min and target <= candidate.max) {
                return target;
            }
            left_bound = candidate.max;
        }

        const right_bound: ?f64 = if (index < intervals.len) intervals[index].min else null;

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

    pub fn is_superset_of(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) bool {
        const intersection = self.op_intersect_intervals(allocator, other) catch return false;
        defer intersection.deinit();

        const a = intersection.intervals.items;
        const b = other.intervals.items;

        if (a.len != b.len) {
            return false;
        }

        for (a, b) |lhs, rhs| {
            if (lhs.min != rhs.min or lhs.max != rhs.max) {
                return false;
            }
        }

        return true;
    }

    pub fn is_subset_of(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) bool {
        return other.is_superset_of(allocator, self);
    }

    pub fn op_intersect_interval(self: *const Numeric_Set, allocator: std.mem.Allocator, other: _Continious) !Numeric_Set {
        var intersections = std.ArrayList(_Continious).init(allocator);
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

    pub fn op_intersect_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var result = std.ArrayList(_Continious).init(allocator);
        defer result.deinit();

        var s: usize = 0;
        var o: usize = 0;
        while (s < self.intervals.items.len and o < other.intervals.items.len) {
            const rs = self.intervals.items[s];
            const ro = other.intervals.items[o];

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
        return try Numeric_Set.init(allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_union_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var combined = std.ArrayList(_Continious).init(allocator);
        defer combined.deinit();

        try combined.appendSlice(self.intervals.items);
        try combined.appendSlice(other.intervals.items);

        return Numeric_Set.init(allocator, combined.items, &[_]Numeric_Set{});
    }

    pub fn op_difference_interval(self: *const Numeric_Set, allocator: std.mem.Allocator, other: _Continious) !Numeric_Set {
        var pieces = std.ArrayList(_Continious).init(allocator);
        defer pieces.deinit();

        for (self.intervals.items) |candidate| {
            var diff = try candidate.op_difference(allocator, other);
            defer diff.deinit();

            try pieces.appendSlice(diff.intervals.items);
        }

        return Numeric_Set.init(allocator, pieces.items, &[_]Numeric_Set{});
    }

    pub fn op_difference_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var result = try Numeric_Set.init(allocator, self.intervals.items, &[_]Numeric_Set{});
        errdefer result.deinit();

        for (other.intervals.items) |interval| {
            const next = try result.op_difference_interval(allocator, interval);
            result.deinit();
            result = next;
        }

        return result;
    }

    pub fn op_symmetric_difference_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var union_result = try self.op_union_intervals(allocator, other);
        defer union_result.deinit();

        var intersection_result = try self.op_intersect_intervals(allocator, other);
        defer intersection_result.deinit();

        return union_result.op_difference_intervals(allocator, &intersection_result);
    }

    pub fn op_add_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var result = std.ArrayList(_Continious).init(allocator);
        defer result.deinit();

        for (self.intervals.items) |r| {
            for (other.intervals.items) |o| {
                try result.append(r.op_add(o));
            }
        }

        return Numeric_Set.init(allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_negate(self: *const Numeric_Set, allocator: std.mem.Allocator) !Numeric_Set {
        var result = std.ArrayList(_Continious).init(allocator);
        defer result.deinit();

        for (self.intervals.items) |interval| {
            try result.append(interval.op_negate());
        }

        return Numeric_Set.init(allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_subtract_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var negated = try other.op_negate(allocator);
        defer negated.deinit();

        return self.op_add_intervals(allocator, &negated);
    }

    pub fn op_multiply_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var result = std.ArrayList(_Continious).init(allocator);
        defer result.deinit();

        for (self.intervals.items) |r| {
            for (other.intervals.items) |o| {
                try result.append(r.op_multiply(o));
            }
        }

        return Numeric_Set.init(allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_invert(self: *const Numeric_Set, allocator: std.mem.Allocator) !Numeric_Set {
        var components = std.ArrayList(Numeric_Set).init(allocator);
        defer components.deinit();

        for (self.intervals.items) |interval| {
            const inverted = try interval.op_invert(allocator);
            try components.append(inverted);
        }

        const result = try Numeric_Set.init(
            allocator,
            &[_]_Continious{},
            components.items,
        );

        for (components.items) |*set_ptr| {
            set_ptr.deinit();
        }

        return result;
    }

    pub fn op_divide_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        var inverted = try other.op_invert(allocator);
        defer inverted.deinit();

        return self.op_multiply_intervals(allocator, &inverted);
    }

    pub fn op_power_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Numeric_Set {
        const exponents = other.intervals.items;

        var components = std.ArrayList(Numeric_Set).init(allocator);
        defer components.deinit();

        for (self.intervals.items) |base_interval| {
            for (exponents) |exp_interval| {
                const powered = try base_interval.op_power(allocator, exp_interval);
                try components.append(powered);
            }
        }

        const result = try Numeric_Set.init(
            allocator,
            &[_]_Continious{},
            components.items,
        );

        for (components.items) |*set_ptr| {
            set_ptr.deinit();
        }

        return result;
    }

    pub fn min_elem(self: *const Numeric_Set) f64 {
        return self.intervals.items[0].min;
    }

    pub fn max_elem(self: *const Numeric_Set) f64 {
        return self.intervals.items[self.intervals.items.len - 1].max;
    }

    pub fn op_ge_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Bool_Set {
        if (self.is_empty() or other.is_empty()) {
            return Bool_Set.init(allocator, &[_]bool{});
        }
        if (self.min_elem() >= other.max_elem()) {
            return Bool_Set.init(allocator, &[_]bool{true});
        }
        if (self.max_elem() < other.min_elem()) {
            return Bool_Set.init(allocator, &[_]bool{false});
        }
        return Bool_Set.init(allocator, &[_]bool{ true, false });
    }

    pub fn op_gt_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Bool_Set {
        if (self.is_empty() or other.is_empty()) {
            return Bool_Set.init(allocator, &[_]bool{});
        }
        if (self.min_elem() > other.max_elem()) {
            return Bool_Set.init(allocator, &[_]bool{true});
        }
        if (self.max_elem() <= other.min_elem()) {
            return Bool_Set.init(allocator, &[_]bool{false});
        }
        return Bool_Set.init(allocator, &[_]bool{ true, false });
    }

    pub fn op_le_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Bool_Set {
        if (self.is_empty() or other.is_empty()) {
            return Bool_Set.init(allocator, &[_]bool{});
        }
        if (self.max_elem() <= other.min_elem()) {
            return Bool_Set.init(allocator, &[_]bool{true});
        }
        if (self.min_elem() > other.max_elem()) {
            return Bool_Set.init(allocator, &[_]bool{false});
        }
        return Bool_Set.init(allocator, &[_]bool{ true, false });
    }

    pub fn op_lt_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, other: *const Numeric_Set) !Bool_Set {
        if (self.is_empty() or other.is_empty()) {
            return Bool_Set.init(allocator, &[_]bool{});
        }
        if (self.max_elem() < other.min_elem()) {
            return Bool_Set.init(allocator, &[_]bool{true});
        }
        if (self.min_elem() >= other.max_elem()) {
            return Bool_Set.init(allocator, &[_]bool{false});
        }
        return Bool_Set.init(allocator, &[_]bool{ true, false });
    }

    pub fn op_round_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator, ndigits: i32) !Numeric_Set {
        var result = std.ArrayList(_Continious).init(allocator);
        defer result.deinit();

        for (self.intervals.items) |interval| {
            const rounded = try interval.op_round(ndigits);
            try result.append(rounded);
        }

        return Numeric_Set.init(allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_abs_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator) !Numeric_Set {
        var result = std.ArrayList(_Continious).init(allocator);
        defer result.deinit();

        for (self.intervals.items) |interval| {
            const abs = try interval.op_abs();
            try result.append(abs);
        }

        return Numeric_Set.init(allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_log_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator) !Numeric_Set {
        var result = std.ArrayList(_Continious).init(allocator);
        defer result.deinit();

        for (self.intervals.items) |interval| {
            try result.append(try interval.op_log());
        }

        return Numeric_Set.init(allocator, result.items, &[_]Numeric_Set{});
    }

    pub fn op_sin_intervals(self: *const Numeric_Set, allocator: std.mem.Allocator) !Numeric_Set {
        var result = std.ArrayList(_Continious).init(allocator);
        defer result.deinit();

        for (self.intervals.items) |interval| {
            try result.append(try interval.op_sin());
        }

        return Numeric_Set.init(allocator, result.items, &[_]Numeric_Set{});
    }
};

test "_Continious.init rejects inverted bounds" {
    try std.testing.expectError(
        _Continious.Error.InvalidBounds,
        _Continious.init(2.0, 1.0),
    );
}

test "_Continious.add adds interval bounds" {
    const lhs = try _Continious.init(1.5, 3.0);
    const rhs = try _Continious.init(0.5, 2.0);
    const result = lhs.op_add(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.max, 1e-12);
}

test "_Continious.negate flips bounds" {
    const original = try _Continious.init(-2.5, 4.0);
    const result = original.op_negate();

    try std.testing.expectApproxEqRel(@as(f64, -4.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.5), result.max, 1e-12);
}

test "_Continious.subtract subtracts interval bounds" {
    const lhs = try _Continious.init(2.0, 4.0);
    const rhs = try _Continious.init(0.5, 1.5);
    const result = lhs.op_subtract(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 0.5), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.5), result.max, 1e-12);
}

test "_Continious.multiply handles mixed signs" {
    const lhs = try _Continious.init(-2.0, 3.0);
    const rhs = try _Continious.init(-1.0, 4.0);
    const result = lhs.op_multiply(rhs);

    try std.testing.expectApproxEqRel(@as(f64, -8.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 12.0), result.max, 1e-12);
}

test "_Continious.op_power raises interval to positive exponent" {
    const base = try _Continious.init(1.0, 3.0);
    const exponent = try _Continious.init(2.0, 3.0);
    const result = try base.op_power(std.testing.allocator, exponent);
    defer result.deinit();

    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 27.0), result.intervals.items[0].max, 1e-12);
}

test "_Continious.op_power rejects negative exponent intervals" {
    const base = try _Continious.init(1.0, 2.0);
    const exponent = try _Continious.init(-2.0, -1.0);
    const allocator = std.testing.allocator;

    try std.testing.expectError(
        _Continious.OperationError.NegativeExponentUnsupported,
        base.op_power(allocator, exponent),
    );
}

test "_Continious.op_power rejects exponent crossing zero" {
    const base = try _Continious.init(1.0, 2.0);
    const exponent = try _Continious.init(-1.0, 1.0);

    try std.testing.expectError(
        _Continious.OperationError.ExponentCrossesZero,
        base.op_power(std.testing.allocator, exponent),
    );
}

test "_Continious.op_power rejects fractional exponent on negative base interval" {
    const base = try _Continious.init(-2.0, 3.0);
    const exponent = try _Continious.init(1.5, 1.5);

    try std.testing.expectError(
        _Continious.OperationError.FractionalExponentRequiresIntegerExponent,
        base.op_power(std.testing.allocator, exponent),
    );
}

test "_Continious.op_sin handles interval within single period" {
    const interval = try _Continious.init(0.0, std.math.pi);
    const result = try interval.op_sin();

    try std.testing.expectApproxEqRel(@as(f64, 0.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.max, 1e-12);
}

test "_Continious.op_sin returns full range for wide intervals" {
    const interval = try _Continious.init(0.0, 10.0);
    const result = try interval.op_sin();

    try std.testing.expectApproxEqRel(@as(f64, -1.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.max, 1e-12);
}

test "_Continious.op_sin captures local extrema inside interval" {
    const interval = try _Continious.init(-std.math.pi / 2.0, std.math.pi / 2.0);
    const result = try interval.op_sin();

    try std.testing.expectApproxEqRel(@as(f64, -1.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.max, 1e-12);
}

test "_Continious.op_sin handles fraction of a period" {
    const interval = try _Continious.init(std.math.pi / 6.0, std.math.pi / 3.0);
    const result = try interval.op_sin();

    try std.testing.expectApproxEqRel(@as(f64, 0.5), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, std.math.sqrt(3.0) / 2.0), result.max, 1e-12);
}

test "_Continious.op_invert returns empty for zero interval" {
    const zero_interval = try _Continious.init(0.0, 0.0);
    var result = try zero_interval.op_invert(std.testing.allocator);
    defer result.deinit();
    try std.testing.expect(result.is_empty());
}

test "_Continious.op_invert returns empty disjoint for zero interval" {
    const allocator = std.testing.allocator;
    const interval = try _Continious.init(0.0, 0.0);
    const result = try interval.op_invert(allocator);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 0), result.intervals.items.len);
}

test "_Continious.op_invert splits interval crossing zero" {
    const allocator = std.testing.allocator;
    const interval = try _Continious.init(-2.0, 4.0);
    const result = try interval.op_invert(allocator);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);
    try std.testing.expect(result.intervals.items[0].min == -std.math.inf(f64));
    try std.testing.expectApproxEqRel(@as(f64, -0.5), result.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 0.25), result.intervals.items[1].min, 1e-12);
    try std.testing.expect(result.intervals.items[1].max == std.math.inf(f64));
}

test "_Continious.op_invert handles negative-only intervals" {
    const allocator = std.testing.allocator;
    const interval = try _Continious.init(-5.0, -1.0);
    const result = try interval.op_invert(allocator);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, -1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -0.2), result.intervals.items[0].max, 1e-12);
}

test "_Continious.op_invert handles positive-only intervals" {
    const allocator = std.testing.allocator;
    const interval = try _Continious.init(2.0, 5.0);
    const result = try interval.op_invert(allocator);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 0.2), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 0.5), result.intervals.items[0].max, 1e-12);
}

test "_Continious.op_invert handles negative-to-zero interval" {
    const allocator = std.testing.allocator;
    const interval = try _Continious.init(-4.0, 0.0);
    const result = try interval.op_invert(allocator);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expect(result.intervals.items[0].min == -std.math.inf(f64));
    try std.testing.expectApproxEqRel(@as(f64, -0.25), result.intervals.items[0].max, 1e-12);
}

test "_Continious.op_invert handles zero-to-positive interval" {
    const allocator = std.testing.allocator;
    const interval = try _Continious.init(0.0, 4.0);
    const result = try interval.op_invert(allocator);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 0.25), result.intervals.items[0].min, 1e-12);
    try std.testing.expect(result.intervals.items[0].max == std.math.inf(f64));
}
test "_Continious.op_divide divides interval by positive interval" {
    const lhs = try _Continious.init(2.0, 4.0);
    const rhs = try _Continious.init(1.0, 2.0);
    const result = try lhs.op_divide(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), result.intervals.items[0].max, 1e-12);
}

test "_Continious.op_divide splits when denominator spans zero" {
    const lhs = try _Continious.init(1.0, 2.0);
    const rhs = try _Continious.init(-1.0, 1.0);
    var result = try lhs.op_divide(std.testing.allocator, rhs);
    defer result.deinit();

    // Python implementation returns two semi-infinite ranges; mirror that shape here.
    try std.testing.expect(!result.is_empty());
    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);

    const neg_branch = result.intervals.items[0];
    const pos_branch = result.intervals.items[1];

    try std.testing.expect(std.math.isInf(neg_branch.min));
    try std.testing.expectApproxEqRel(@as(f64, -1.0), neg_branch.max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), pos_branch.min, 1e-12);
    try std.testing.expect(std.math.isInf(pos_branch.max));
}

test "_Continious.init rejects NaN bounds" {
    const qnan = std.math.nan(f64);
    try std.testing.expectError(
        _Continious.Error.NaNMin,
        _Continious.init(qnan, 1.0),
    );
    try std.testing.expectError(
        _Continious.Error.NaNMax,
        _Continious.init(0.0, qnan),
    );
}

test "_Continious.op_intersect returns overlap interval" {
    const lhs = try _Continious.init(1.0, 5.0);
    const rhs = try _Continious.init(3.0, 7.0);
    const result = try lhs.op_intersect(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.max, 1e-12);
}

test "_Continious.op_intersect returns single point when touching" {
    const lhs = try _Continious.init(1.0, 3.0);
    const rhs = try _Continious.init(3.0, 4.0);
    const result = try lhs.op_intersect(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.max, 1e-12);
}

test "_Continious.op_intersect returns empty when disjoint" {
    const lhs = try _Continious.init(1.0, 2.0);
    const rhs = try _Continious.init(3.0, 4.0);
    try std.testing.expectError(_Continious.Error.Empty, lhs.op_intersect(rhs));
}

test "_Continious.op_difference returns original when disjoint" {
    const lhs = try _Continious.init(1.0, 3.0);
    const rhs = try _Continious.init(4.0, 5.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.intervals.items[0].max, 1e-12);
}

test "_Continious.op_difference returns empty when fully covered" {
    const lhs = try _Continious.init(1.0, 3.0);
    const rhs = try _Continious.init(0.0, 5.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 0), result.intervals.items.len);
}

test "_Continious.op_difference returns single segment when overlapping right" {
    const lhs = try _Continious.init(1.0, 5.0);
    const rhs = try _Continious.init(3.0, 6.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.intervals.items[0].max, 1e-12);
}

test "_Continious.op_difference returns single segment when overlapping left" {
    const lhs = try _Continious.init(1.0, 5.0);
    const rhs = try _Continious.init(-1.0, 2.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.intervals.items[0].max, 1e-12);
}

test "_Continious.op_difference returns two segments when other is inside" {
    const lhs = try _Continious.init(1.0, 6.0);
    const rhs = try _Continious.init(2.0, 4.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);
    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), result.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 6.0), result.intervals.items[1].max, 1e-12);
}

test "Numeric_Set.init basic case" {
    const intervals = [2]_Continious{
        try _Continious.init(1.0, 3.0),
        try _Continious.init(5.0, 7.0),
    };

    const disjoint = try Numeric_Set.init(std.testing.allocator, &intervals, &[_]Numeric_Set{});
    defer disjoint.deinit();

    try std.testing.expectEqual(@as(usize, 2), disjoint.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), disjoint.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), disjoint.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), disjoint.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), disjoint.intervals.items[1].max, 1e-12);
}

test "Numeric_Set.init merges and sorts intervals" {
    const nested_disjoint = try Numeric_Set.init(std.testing.allocator, &[_]_Continious{
        try _Continious.init(6.0, 8.0),
        try _Continious.init(10.0, 12.0),
    }, &[_]Numeric_Set{});
    defer nested_disjoint.deinit();

    const intervals = [_]_Continious{
        try _Continious.init(1.0, 3.0),
        try _Continious.init(4.0, 7.0),
        try _Continious.init(9.0, 11.0),
    };
    const disjoint = try Numeric_Set.init(std.testing.allocator, &intervals, &[_]Numeric_Set{nested_disjoint});
    defer disjoint.deinit();

    try std.testing.expectEqual(@as(usize, 3), disjoint.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), disjoint.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), disjoint.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), disjoint.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), disjoint.intervals.items[1].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 9.0), disjoint.intervals.items[2].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 12.0), disjoint.intervals.items[2].max, 1e-12);
}

test "Numeric_Set.closest_elem handles relative positions" {
    const interval_a = try _Continious.init(1.0, 3.0);
    const interval_b = try _Continious.init(5.0, 7.0);
    var set = try Numeric_Set.init(std.testing.allocator, &[_]_Continious{ interval_a, interval_b }, &[_]Numeric_Set{});
    defer set.deinit();

    const below = try set.closest_elem(0.2);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), below, 1e-12);

    const inside = try set.closest_elem(2.4);
    try std.testing.expectApproxEqRel(@as(f64, 2.4), inside, 1e-12);

    const between = try set.closest_elem(4.2);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), between, 1e-12);

    const above = try set.closest_elem(9.5);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), above, 1e-12);
}

test "Numeric_Set.is_superset_of handles various cases" {
    const outer_intervals = [_]_Continious{
        try _Continious.init(1.0, 3.5),
        try _Continious.init(5.0, 7.5),
    };
    const inner_intervals = [_]_Continious{
        try _Continious.init(1.5, 2.0),
        try _Continious.init(6.0, 6.8),
    };
    const partial_intervals = [_]_Continious{
        try _Continious.init(0.5, 2.0),
    };

    var outer = try Numeric_Set.init(std.testing.allocator, &outer_intervals, &[_]Numeric_Set{});
    defer outer.deinit();

    var inner = try Numeric_Set.init(std.testing.allocator, &inner_intervals, &[_]Numeric_Set{});
    defer inner.deinit();

    var partial = try Numeric_Set.init(std.testing.allocator, &partial_intervals, &[_]Numeric_Set{});
    defer partial.deinit();

    var empty = try Numeric_Set.init_empty(std.testing.allocator);
    defer empty.deinit();

    const allocator = std.testing.allocator;

    try std.testing.expect(outer.is_superset_of(allocator, &inner));
    try std.testing.expect(outer.is_superset_of(allocator, &empty));
    try std.testing.expect(outer.is_superset_of(allocator, &outer));

    try std.testing.expect(!inner.is_superset_of(allocator, &outer));
    try std.testing.expect(!partial.is_superset_of(allocator, &outer));
}

test "Numeric_Set.is_subset_of handles various cases" {
    const outer_intervals = [_]_Continious{
        try _Continious.init(1.0, 3.5),
        try _Continious.init(5.0, 7.5),
    };
    const inner_intervals = [_]_Continious{
        try _Continious.init(1.5, 2.0),
        try _Continious.init(6.0, 6.8),
    };
    const partial_intervals = [_]_Continious{
        try _Continious.init(0.5, 2.0),
    };

    var outer = try Numeric_Set.init(std.testing.allocator, &outer_intervals, &[_]Numeric_Set{});
    defer outer.deinit();

    var inner = try Numeric_Set.init(std.testing.allocator, &inner_intervals, &[_]Numeric_Set{});
    defer inner.deinit();

    var partial = try Numeric_Set.init(std.testing.allocator, &partial_intervals, &[_]Numeric_Set{});
    defer partial.deinit();

    var empty = try Numeric_Set.init_empty(std.testing.allocator);
    defer empty.deinit();

    const allocator = std.testing.allocator;

    try std.testing.expect(inner.is_subset_of(allocator, &outer));
    try std.testing.expect(empty.is_subset_of(allocator, &outer));
    try std.testing.expect(outer.is_subset_of(allocator, &outer));

    try std.testing.expect(!outer.is_subset_of(allocator, &inner));
    try std.testing.expect(!partial.is_subset_of(allocator, &outer));
}

test "Numeric_Set.op_union_intervals handles various cases" {
    const lhs = try Numeric_Set.init(std.testing.allocator, &[_]_Continious{
        try _Continious.init(1.0, 3.0),
        try _Continious.init(5.0, 7.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();

    const rhs = try Numeric_Set.init(std.testing.allocator, &[_]_Continious{
        try _Continious.init(2.0, 4.0),
        try _Continious.init(6.0, 8.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();

    const result = try lhs.op_union_intervals(std.testing.allocator, &rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), result.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), result.intervals.items[1].max, 1e-12);
}

test "Numeric_Set.op_difference_interval handles overlap" {
    const allocator = std.testing.allocator;

    var base = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 4.0),
        try _Continious.init(6.0, 8.0),
    }, &[_]Numeric_Set{});
    defer base.deinit();

    const subtract = try _Continious.init(2.0, 7.0);

    var result = try base.op_difference_interval(allocator, subtract);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), result.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), result.intervals.items[1].max, 1e-12);
}

test "Numeric_Set.op_difference_intervals handles multiple subtractions" {
    const allocator = std.testing.allocator;

    var base = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(0.0, 5.0),
        try _Continious.init(6.0, 10.0),
    }, &[_]Numeric_Set{});
    defer base.deinit();

    var subtract = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
        try _Continious.init(7.0, 9.0),
    }, &[_]Numeric_Set{});
    defer subtract.deinit();

    var result = try base.op_difference_intervals(allocator, &subtract);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 4), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 0.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.intervals.items[1].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 6.0), result.intervals.items[2].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), result.intervals.items[2].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 9.0), result.intervals.items[3].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 10.0), result.intervals.items[3].max, 1e-12);
}

test "Numeric_Set.op_add_intervals sums pairwise intervals" {
    const allocator = std.testing.allocator;

    var lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
        try _Continious.init(4.0, 5.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();

    var rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(10.0, 11.0),
        try _Continious.init(20.0, 22.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();

    var result = try lhs.op_add_intervals(allocator, &rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 3), result.intervals.items.len);

    try std.testing.expectApproxEqRel(@as(f64, 11.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 13.0), result.intervals.items[0].max, 1e-12);

    try std.testing.expectApproxEqRel(@as(f64, 14.0), result.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 16.0), result.intervals.items[1].max, 1e-12);

    try std.testing.expectApproxEqRel(@as(f64, 21.0), result.intervals.items[2].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 27.0), result.intervals.items[2].max, 1e-12);
}

test "Numeric_Set.op_negate flips all intervals" {
    const allocator = std.testing.allocator;

    var original = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 3.0),
        try _Continious.init(5.0, 6.0),
    }, &[_]Numeric_Set{});
    defer original.deinit();

    var negated = try original.op_negate(allocator);
    defer negated.deinit();

    try std.testing.expectEqual(@as(usize, 2), negated.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, -6.0), negated.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -5.0), negated.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -3.0), negated.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -1.0), negated.intervals.items[1].max, 1e-12);
}

test "Numeric_Set.op_subtract_intervals subtracts via negation and add" {
    const allocator = std.testing.allocator;

    var lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(5.0, 7.0),
        try _Continious.init(10.0, 12.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();

    var rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(2.0, 3.0),
        try _Continious.init(1.0, 1.5),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();

    var negated_rhs = try rhs.op_negate(allocator);
    defer negated_rhs.deinit();

    var difference = try lhs.op_subtract_intervals(allocator, &rhs);
    defer difference.deinit();

    var manual = try lhs.op_add_intervals(allocator, &negated_rhs);
    defer manual.deinit();

    try std.testing.expectEqual(@as(usize, manual.intervals.items.len), difference.intervals.items.len);

    for (manual.intervals.items, difference.intervals.items) |expected, actual| {
        try std.testing.expectApproxEqRel(expected.min, actual.min, 1e-12);
        try std.testing.expectApproxEqRel(expected.max, actual.max, 1e-12);
    }
}

test "Numeric_Set.op_multiply_intervals multiplies pairwise intervals" {
    const allocator = std.testing.allocator;

    var lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(-2.0, -1.0),
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();

    var rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(0.5, 1.5),
        try _Continious.init(2.0, 3.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();

    var result = try lhs.op_multiply_intervals(allocator, &rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);

    try std.testing.expectApproxEqRel(@as(f64, -6.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -0.5), result.intervals.items[0].max, 1e-12);

    try std.testing.expectApproxEqRel(@as(f64, 1.5), result.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 12.0), result.intervals.items[1].max, 1e-12);
}

test "Numeric_Set.op_divide_intervals divides pairwise intervals" {
    const allocator = std.testing.allocator;

    var numerator = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(6.0, 8.0),
        try _Continious.init(-4.0, -2.0),
    }, &[_]Numeric_Set{});
    defer numerator.deinit();

    var denominator = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(2.0, 3.0),
        try _Continious.init(-1.5, -0.5),
    }, &[_]Numeric_Set{});
    defer denominator.deinit();

    var div_result = try numerator.op_divide_intervals(allocator, &denominator);
    defer div_result.deinit();

    try std.testing.expectEqual(@as(usize, 3), div_result.intervals.items.len);

    const first = div_result.intervals.items[0];
    try std.testing.expectApproxEqRel(@as(f64, -16.0), first.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -4.0), first.max, 1e-12);

    const second = div_result.intervals.items[1];
    try std.testing.expectApproxEqRel(@as(f64, -2.0), second.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -2.0 / 3.0), second.max, 1e-12);

    const third = div_result.intervals.items[2];
    try std.testing.expectApproxEqRel(@as(f64, 4.0 / 3.0), third.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), third.max, 1e-12);
}

test "Numeric_Set.op_power_intervals raises pairwise combinations" {
    const allocator = std.testing.allocator;

    var bases = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer bases.deinit();

    var exponents = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(2.0, 2.5),
        try _Continious.init(3.0, 3.5),
    }, &[_]Numeric_Set{});
    defer exponents.deinit();

    var result = try bases.op_power_intervals(allocator, &exponents);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);

    const combined = result.intervals.items[0];
    try std.testing.expectApproxEqRel(@as(f64, std.math.pow(f64, 1.0, 2.0)), combined.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, std.math.pow(f64, 4.0, 3.5)), combined.max, 1e-12);
}

test "Numeric_Set.op_round_intervals rounds each interval" {
    const allocator = std.testing.allocator;

    var set = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.2345, 2.3456),
        try _Continious.init(-3.8765, -1.2345),
    }, &[_]Numeric_Set{});
    defer set.deinit();

    var rounded = try set.op_round_intervals(allocator, 2);
    defer rounded.deinit();

    try std.testing.expectEqual(@as(usize, 2), rounded.intervals.items.len);

    const negative = rounded.intervals.items[0];
    try std.testing.expectApproxEqRel(@as(f64, -3.88), negative.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, -1.23), negative.max, 1e-12);

    const positive = rounded.intervals.items[1];
    try std.testing.expectApproxEqRel(@as(f64, 1.23), positive.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.35), positive.max, 1e-12);
}

test "Numeric_Set.op_abs_intervals takes absolute value of each interval" {
    const allocator = std.testing.allocator;

    var set = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(-4.5, -2.5),
        try _Continious.init(-1.0, 3.0),
    }, &[_]Numeric_Set{});
    defer set.deinit();

    var abs_set = try set.op_abs_intervals(allocator);
    defer abs_set.deinit();

    try std.testing.expectEqual(@as(usize, 1), abs_set.intervals.items.len);

    const first = abs_set.intervals.items[0];
    try std.testing.expectApproxEqRel(@as(f64, 0.0), first.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.5), first.max, 1e-12);
}

test "Numeric_Set.op_log_intervals takes natural log of each interval" {
    const allocator = std.testing.allocator;

    var set = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 3.0),
        try _Continious.init(5.0, 8.0),
    }, &[_]Numeric_Set{});
    defer set.deinit();

    var logged = try set.op_log_intervals(allocator);
    defer logged.deinit();

    try std.testing.expectEqual(@as(usize, 2), logged.intervals.items.len);

    const first = logged.intervals.items[0];
    try std.testing.expectApproxEqRel(@as(f64, std.math.log(f64, std.math.e, 1.0)), first.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, std.math.log(f64, std.math.e, 3.0)), first.max, 1e-12);

    const second = logged.intervals.items[1];
    try std.testing.expectApproxEqRel(@as(f64, std.math.log(f64, std.math.e, 5.0)), second.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, std.math.log(f64, std.math.e, 8.0)), second.max, 1e-12);
}

test "Numeric_Set.op_sin_intervals applies sine envelope" {
    const allocator = std.testing.allocator;

    var set = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(0.0, std.math.pi / 2.0),
        try _Continious.init(std.math.pi, 3.0 * std.math.pi / 2.0),
    }, &[_]Numeric_Set{});
    defer set.deinit();

    var sinus = try set.op_sin_intervals(allocator);
    defer sinus.deinit();

    try std.testing.expectEqual(@as(usize, 1), sinus.intervals.items.len);

    const combined = sinus.intervals.items[0];
    try std.testing.expectApproxEqRel(@as(f64, -1.0), combined.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), combined.max, 1e-12);
}

test "Numeric_Set.op_ge_intervals returns false when lhs is less than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();

    const result = try lhs.op_ge_intervals(allocator, &rhs);
    defer result.deinit();
    try std.testing.expectEqual(@as(usize, 1), result.elements.items.len);
    try std.testing.expect(!result.elements.items[0]);
}

test "Numeric_Set.op_ge_intervals returns true when lhs is greater than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
    const result = try lhs.op_ge_intervals(allocator, &rhs);
    defer result.deinit();
    try std.testing.expectEqual(@as(usize, 1), result.elements.items.len);
    try std.testing.expect(result.elements.items[0]);
}
test "Numeric_Set.op_ge_intervals returns true and false when lhs is both greater and less than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 5.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
    const result = try lhs.op_ge_intervals(allocator, &rhs);
    defer result.deinit();
    try std.testing.expectEqual(@as(usize, 2), result.elements.items.len);
    try std.testing.expect(result.elements.items[0]);
    try std.testing.expect(!result.elements.items[1]);
}

test "Numeric_Set.op_gt_intervals returns false when lhs is less than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_gt_intervals returns false when lhs is equal to rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_gt_intervals returns true when lhs is greater than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_gt_intervals returns true and false when lhs is both greater and less than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 5.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_le_intervals returns false when lhs is greater than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_le_intervals returns false when lhs is equal to rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_le_intervals returns true and false when lhs is both less and greater than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 3.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(2.0, 4.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
    const result = try lhs.op_le_intervals(allocator, &rhs);
    defer result.deinit();
    try std.testing.expectEqual(@as(usize, 2), result.elements.items.len);
    try std.testing.expect(result.elements.items[0]);
    try std.testing.expect(!result.elements.items[1]);
}

test "Numeric_Set.op_lt_intervals returns false when lhs is greater than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_lt_intervals returns false when lhs is equal to rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_lt_intervals returns true when lhs is less than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 2.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(3.0, 4.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}

test "Numeric_Set.op_lt_intervals returns true and false when lhs is both less and greater than rhs" {
    const allocator = std.testing.allocator;
    const lhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(1.0, 3.0),
    }, &[_]Numeric_Set{});
    defer lhs.deinit();
    const rhs = try Numeric_Set.init(allocator, &[_]_Continious{
        try _Continious.init(2.0, 4.0),
    }, &[_]Numeric_Set{});
    defer rhs.deinit();
}
