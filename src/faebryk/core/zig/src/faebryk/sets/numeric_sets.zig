const std = @import("std");

// TODO parity tracker for Numeric_Interval vs Python implementation
// | Operation                        | Function stubbed? | Tests? |
// |----------------------------------|--------------------|--------|
// | intersection                     | implemented        | yes    |
// | difference                       | pending            | pending|
// | rounding                         | pending            | pending|
// | absolute value                   | pending            | pending|
// | logarithm                        | pending            | pending|
// | sine                             | pending            | pending|
// | interval merge (maybe_merge)     | pending            | pending|

pub const Numeric_Interval = struct {
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

    pub fn init(min: f64, max: f64) Error!Numeric_Interval {
        if (std.math.isNan(min)) return error.NaNMin;
        if (std.math.isNan(max)) return error.NaNMax;
        if (!std.math.isFinite(min)) return error.InfiniteMin;
        if (!std.math.isFinite(max)) return error.InfiniteMax;
        if (min > max) return error.InvalidBounds;

        return Numeric_Interval{
            .min = min,
            .max = max,
        };
    }

    pub fn is_empty() bool {
        return false;
    }

    pub fn is_unbounded(self: Numeric_Interval) bool {
        return self.min == -std.math.inf(f64) and self.max == std.math.inf(f64);
    }

    pub fn is_finite(self: Numeric_Interval) bool {
        if (self.is_empty()) {
            return true;
        }

        return self.min != -std.math.inf(f64) and self.max != std.math.inf(f64);
    }

    pub fn is_integer(self: Numeric_Interval) bool {
        return self.is_single_element() and @mod(self.min, 1.0) == 0.0;
    }

    pub fn as_center_rel(self: Numeric_Interval) CenterRel {
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

    pub fn is_subset_of(self: Numeric_Interval, other: Numeric_Interval) bool {
        return self.min >= other.min and self.max <= other.max;
    }

    pub fn op_add(self: Numeric_Interval, other: Numeric_Interval) Numeric_Interval {
        return Numeric_Interval{
            .min = self.min + other.min,
            .max = self.max + other.max,
        };
    }

    pub fn op_negate(self: Numeric_Interval) Numeric_Interval {
        return Numeric_Interval{
            .min = -self.max,
            .max = -self.min,
        };
    }

    pub fn op_subtract(self: Numeric_Interval, other: Numeric_Interval) Numeric_Interval {
        return self.op_add(other.op_negate());
    }

    pub fn op_multiply(
        self: Numeric_Interval,
        other: Numeric_Interval,
    ) Numeric_Interval {
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

        return Numeric_Interval{
            .min = min_val,
            .max = max_val,
        };
    }

    pub fn op_power(
        self: Numeric_Interval,
        exponent: Numeric_Interval,
    ) OperationError!Numeric_Interval {
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

        return Numeric_Interval{
            .min = min_val,
            .max = max_val,
        };
    }

    pub fn op_inverse(self: Numeric_Interval) Error!Numeric_Interval {
        const neg_inf = -std.math.inf(f64);
        const pos_inf = std.math.inf(f64);

        if (self.min == 0.0 and self.max == 0.0) {
            return Error.Empty;
        }

        if (self.min < 0.0 and self.max > 0.0) {
            return Error.Empty;
        }

        if (self.min < 0.0 and self.max == 0.0) {
            return Numeric_Interval{
                .min = neg_inf,
                .max = 1.0 / self.min,
            };
        }

        if (self.min == 0.0 and self.max > 0.0) {
            return Numeric_Interval{
                .min = 1.0 / self.max,
                .max = pos_inf,
            };
        }

        const inv_min = 1.0 / self.max;
        const inv_max = 1.0 / self.min;

        var lower = inv_min;
        var upper = inv_max;
        if (lower > upper) {
            const tmp = lower;
            lower = upper;
            upper = tmp;
        }

        return Numeric_Interval{
            .min = lower,
            .max = upper,
        };
    }

    pub fn op_divide(self: Numeric_Interval, other: Numeric_Interval) Error!Numeric_Interval {
        const inverse_other = try other.op_inverse();
        return self.op_multiply(inverse_other);
    }

    pub fn op_intersect(self: Numeric_Interval, other: Numeric_Interval) Error!Numeric_Interval {
        const lower = @max(self.min, other.min);
        const upper = @min(self.max, other.max);

        if (lower <= upper) {
            return Numeric_Interval{
                .min = lower,
                .max = upper,
            };
        }

        return Error.Empty;
    }

    pub fn op_difference(self: @This(), allocator: std.mem.Allocator, other: Numeric_Interval) !Numeric_Interval_Disjoint {

        // case: no overlap
        if (self.max <= other.min or self.min >= other.max) {
            return try Numeric_Interval_Disjoint.init_from_single(allocator, self);
        }

        // case: other completely covers self
        if (other.min <= self.min and other.max >= self.max) {
            return try Numeric_Interval_Disjoint.init_empty(allocator);
        }

        // case: other is in the middle, splitting self into two pieces
        if (self.min < other.min and self.max > other.max) {
            return try Numeric_Interval_Disjoint.init(allocator, &[_]Numeric_Interval{
                Numeric_Interval{ .min = self.min, .max = other.min },
                Numeric_Interval{ .min = other.max, .max = self.max },
            }, &[_]Numeric_Interval_Disjoint{});
        }

        // case: overlap on right side
        if (self.min < other.min) {
            return try Numeric_Interval_Disjoint.init_from_interval(allocator, self.min, other.min);
        }

        // case: overlap on left side
        return try Numeric_Interval_Disjoint.init_from_interval(allocator, other.max, self.max);
    }

    pub fn op_round(self: Numeric_Interval, ndigits: i32) Error!Numeric_Interval {
        return Numeric_Interval{ .min = std.math.round(self.min, ndigits), .max = std.math.round(self.max, ndigits) };
    }

    pub fn op_abs(self: Numeric_Interval) Error!Numeric_Interval {
        return Numeric_Interval{ .min = std.math.abs(self.min), .max = std.math.abs(self.max) };
    }

    pub fn op_log(self: Numeric_Interval) Error!Numeric_Interval {
        if (self.min <= 0.0) return Error.NonPositiveLog;
        return Numeric_Interval{ .min = std.math.log(self.min), .max = std.math.log(self.max) };
    }

    pub fn op_sin(self: Numeric_Interval) Error!Numeric_Interval {
        // The extrema of sin(x) on an interval occur at the endpoints or at the
        // turning points x = π/2 + π·k that fall within the interval. For
        // intervals wider than a full period or containing infinities we can
        // shortcut to [-1, 1].
        const pi = std.math.pi;
        const interval_width = self.max - self.min;

        if (!std.math.isFinite(interval_width) or interval_width > 2.0 * pi) {
            return Numeric_Interval{ .min = -1.0, .max = 1.0 };
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

        return Numeric_Interval{ .min = min_val, .max = max_val };
    }

    pub fn is_single_element(self: Numeric_Interval) bool {
        return self.min == self.max;
    }

    pub fn isInteger(self: Numeric_Interval) bool {
        return self.is_single_element() and is_integer(self.min);
    }
};

fn intervalLess(_: void, a: Numeric_Interval, b: Numeric_Interval) bool {
    return a.min < b.min;
}

pub const Numeric_Interval_Disjoint = struct {
    intervals: std.ArrayList(Numeric_Interval),

    pub fn init_empty(allocator: std.mem.Allocator) !Numeric_Interval_Disjoint {
        return try Numeric_Interval_Disjoint.init(allocator, &[_]Numeric_Interval{}, &[_]Numeric_Interval_Disjoint{});
    }

    pub fn init_from_single(allocator: std.mem.Allocator, input: Numeric_Interval) !Numeric_Interval_Disjoint {
        return try Numeric_Interval_Disjoint.init(allocator, &[_]Numeric_Interval{input}, &[_]Numeric_Interval_Disjoint{});
    }

    pub fn init_from_interval(allocator: std.mem.Allocator, min: f64, max: f64) !Numeric_Interval_Disjoint {
        return try Numeric_Interval_Disjoint.init_from_single(allocator, try Numeric_Interval.init(min, max));
    }

    pub fn init(allocator: std.mem.Allocator, inputs: []const Numeric_Interval, disjoint_inputs: []const Numeric_Interval_Disjoint) !Numeric_Interval_Disjoint {
        var out = Numeric_Interval_Disjoint{
            .intervals = try std.ArrayList(Numeric_Interval).initCapacity(allocator, inputs.len),
        };

        var temp = std.ArrayList(Numeric_Interval).init(allocator);
        defer temp.deinit();

        // flatten
        for (inputs) |r| {
            try temp.append(r);
        }

        for (disjoint_inputs) |d| {
            for (d.intervals.items) |r| {
                try temp.append(r);
            }
        }

        if (temp.items.len == 0) {
            return out;
        }

        // sort by min element
        std.mem.sort(
            Numeric_Interval,
            temp.items,
            {},
            intervalLess,
        );

        // merge
        var cur_min = temp.items[0].min;
        var cur_max = temp.items[0].max;

        for (temp.items[1..]) |r| {
            if (cur_max >= r.min) {
                cur_max = @max(cur_max, r.max);
            } else {
                out.intervals.appendAssumeCapacity(Numeric_Interval{ .min = cur_min, .max = cur_max });
                cur_min = r.min;
                cur_max = r.max;
            }
        }
        out.intervals.appendAssumeCapacity(Numeric_Interval{ .min = cur_min, .max = cur_max });

        return out;
    }

    pub fn deinit(self: *const Numeric_Interval_Disjoint) void {
        self.intervals.deinit();
    }

    pub fn slice(self: *const Numeric_Interval_Disjoint) ![]Numeric_Interval {
        return self.intervals[0..self.len];
    }
};

test "Numeric_Interval.init rejects inverted bounds" {
    try std.testing.expectError(
        Numeric_Interval.Error.InvalidBounds,
        Numeric_Interval.init(2.0, 1.0),
    );
}

test "Numeric_Interval.add adds interval bounds" {
    const lhs = try Numeric_Interval.init(1.5, 3.0);
    const rhs = try Numeric_Interval.init(0.5, 2.0);
    const result = lhs.op_add(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.max, 1e-12);
}

test "Numeric_Interval.negate flips bounds" {
    const original = try Numeric_Interval.init(-2.5, 4.0);
    const result = original.op_negate();

    try std.testing.expectApproxEqRel(@as(f64, -4.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.5), result.max, 1e-12);
}

test "Numeric_Interval.subtract subtracts interval bounds" {
    const lhs = try Numeric_Interval.init(2.0, 4.0);
    const rhs = try Numeric_Interval.init(0.5, 1.5);
    const result = lhs.op_subtract(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 0.5), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.5), result.max, 1e-12);
}

test "Numeric_Interval.multiply handles mixed signs" {
    const lhs = try Numeric_Interval.init(-2.0, 3.0);
    const rhs = try Numeric_Interval.init(-1.0, 4.0);
    const result = lhs.op_multiply(rhs);

    try std.testing.expectApproxEqRel(@as(f64, -8.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 12.0), result.max, 1e-12);
}

test "Numeric_Interval.op_power raises interval to positive exponent" {
    const base = try Numeric_Interval.init(1.0, 3.0);
    const exponent = try Numeric_Interval.init(2.0, 3.0);
    const result = try base.op_power(exponent);

    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 27.0), result.max, 1e-12);
}

test "Numeric_Interval.op_power rejects negative exponent intervals" {
    const base = try Numeric_Interval.init(1.0, 2.0);
    const exponent = try Numeric_Interval.init(-2.0, -1.0);

    try std.testing.expectError(
        Numeric_Interval.OperationError.NegativeExponentUnsupported,
        base.op_power(exponent),
    );
}

test "Numeric_Interval.op_power rejects exponent crossing zero" {
    const base = try Numeric_Interval.init(1.0, 2.0);
    const exponent = try Numeric_Interval.init(-1.0, 1.0);

    try std.testing.expectError(
        Numeric_Interval.OperationError.ExponentCrossesZero,
        base.op_power(exponent),
    );
}

test "Numeric_Interval.op_power rejects fractional exponent on negative base interval" {
    const base = try Numeric_Interval.init(-2.0, 3.0);
    const exponent = try Numeric_Interval.init(1.5, 1.5);

    try std.testing.expectError(
        Numeric_Interval.OperationError.FractionalExponentRequiresIntegerExponent,
        base.op_power(exponent),
    );
}

test "Numeric_Interval.op_sin handles interval within single period" {
    const interval = try Numeric_Interval.init(0.0, std.math.pi);
    const result = try interval.op_sin();

    try std.testing.expectApproxEqRel(@as(f64, 0.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.max, 1e-12);
}

test "Numeric_Interval.op_sin returns full range for wide intervals" {
    const interval = try Numeric_Interval.init(0.0, 10.0);
    const result = try interval.op_sin();

    try std.testing.expectApproxEqRel(@as(f64, -1.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.max, 1e-12);
}

test "Numeric_Interval.op_sin captures local extrema inside interval" {
    const interval = try Numeric_Interval.init(-std.math.pi / 2.0, std.math.pi / 2.0);
    const result = try interval.op_sin();

    try std.testing.expectApproxEqRel(@as(f64, -1.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.max, 1e-12);
}

test "Numeric_Interval.op_inverse returns empty for zero interval" {
    const zero_interval = try Numeric_Interval.init(0.0, 0.0);
    try std.testing.expectError(Numeric_Interval.Error.Empty, zero_interval.op_inverse());
}

test "Numeric_Interval.op_divide divides interval by positive interval" {
    const lhs = try Numeric_Interval.init(2.0, 4.0);
    const rhs = try Numeric_Interval.init(1.0, 2.0);
    const result = try lhs.op_divide(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), result.max, 1e-12);
}

test "Numeric_Interval.op_divide returns empty when denominator spans zero" {
    const lhs = try Numeric_Interval.init(1.0, 2.0);
    const rhs = try Numeric_Interval.init(-1.0, 1.0);
    try std.testing.expectError(Numeric_Interval.Error.Empty, lhs.op_divide(rhs));
}

test "Numeric_Interval.init rejects NaN bounds" {
    const qnan = std.math.nan(f64);
    try std.testing.expectError(
        Numeric_Interval.Error.NaNMin,
        Numeric_Interval.init(qnan, 1.0),
    );
    try std.testing.expectError(
        Numeric_Interval.Error.NaNMax,
        Numeric_Interval.init(0.0, qnan),
    );
}

test "Numeric_Interval.op_intersect returns overlap interval" {
    const lhs = try Numeric_Interval.init(1.0, 5.0);
    const rhs = try Numeric_Interval.init(3.0, 7.0);
    const result = try lhs.op_intersect(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.max, 1e-12);
}

test "Numeric_Interval.op_intersect returns single point when touching" {
    const lhs = try Numeric_Interval.init(1.0, 3.0);
    const rhs = try Numeric_Interval.init(3.0, 4.0);
    const result = try lhs.op_intersect(rhs);

    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.max, 1e-12);
}

test "Numeric_Interval.op_intersect returns empty when disjoint" {
    const lhs = try Numeric_Interval.init(1.0, 2.0);
    const rhs = try Numeric_Interval.init(3.0, 4.0);
    try std.testing.expectError(Numeric_Interval.Error.Empty, lhs.op_intersect(rhs));
}

test "Numeric_Interval.op_difference returns original when disjoint" {
    const lhs = try Numeric_Interval.init(1.0, 3.0);
    const rhs = try Numeric_Interval.init(4.0, 5.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.intervals.items[0].max, 1e-12);
}

test "Numeric_Interval.op_difference returns empty when fully covered" {
    const lhs = try Numeric_Interval.init(1.0, 3.0);
    const rhs = try Numeric_Interval.init(0.0, 5.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 0), result.intervals.items.len);
}

test "Numeric_Interval.op_difference returns single segment when overlapping right" {
    const lhs = try Numeric_Interval.init(1.0, 5.0);
    const rhs = try Numeric_Interval.init(3.0, 6.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), result.intervals.items[0].max, 1e-12);
}

test "Numeric_Interval.op_difference returns single segment when overlapping left" {
    const lhs = try Numeric_Interval.init(1.0, 5.0);
    const rhs = try Numeric_Interval.init(-1.0, 2.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 1), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), result.intervals.items[0].max, 1e-12);
}

test "Numeric_Interval.op_difference returns two segments when other is inside" {
    const lhs = try Numeric_Interval.init(1.0, 6.0);
    const rhs = try Numeric_Interval.init(2.0, 4.0);
    const result = try lhs.op_difference(std.testing.allocator, rhs);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);
    try std.testing.expectEqual(@as(usize, 2), result.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), result.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 2.0), result.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), result.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 6.0), result.intervals.items[1].max, 1e-12);
}

test "Numeric_Interval_Disjoint.init basic case" {
    const intervals = [2]Numeric_Interval{
        try Numeric_Interval.init(1.0, 3.0),
        try Numeric_Interval.init(5.0, 7.0),
    };

    const disjoint = try Numeric_Interval_Disjoint.init(std.testing.allocator, &intervals, &[_]Numeric_Interval_Disjoint{});
    defer disjoint.deinit();

    try std.testing.expectEqual(@as(usize, 2), disjoint.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), disjoint.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), disjoint.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 5.0), disjoint.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 7.0), disjoint.intervals.items[1].max, 1e-12);
}

test "Numeric_Interval_Disjoint.init merges and sorts intervals" {
    const nested_disjoint = try Numeric_Interval_Disjoint.init(std.testing.allocator, &[_]Numeric_Interval{
        try Numeric_Interval.init(6.0, 8.0),
        try Numeric_Interval.init(10.0, 12.0),
    }, &[_]Numeric_Interval_Disjoint{});
    defer nested_disjoint.deinit();

    const intervals = [_]Numeric_Interval{
        try Numeric_Interval.init(1.0, 3.0),
        try Numeric_Interval.init(4.0, 7.0),
        try Numeric_Interval.init(9.0, 11.0),
    };
    const disjoint = try Numeric_Interval_Disjoint.init(std.testing.allocator, &intervals, &[_]Numeric_Interval_Disjoint{nested_disjoint});
    defer disjoint.deinit();

    try std.testing.expectEqual(@as(usize, 3), disjoint.intervals.items.len);
    try std.testing.expectApproxEqRel(@as(f64, 1.0), disjoint.intervals.items[0].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 3.0), disjoint.intervals.items[0].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 4.0), disjoint.intervals.items[1].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 8.0), disjoint.intervals.items[1].max, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 9.0), disjoint.intervals.items[2].min, 1e-12);
    try std.testing.expectApproxEqRel(@as(f64, 12.0), disjoint.intervals.items[2].max, 1e-12);
}
