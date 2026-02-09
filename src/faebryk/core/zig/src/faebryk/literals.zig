const std = @import("std");
const graph_mod = @import("graph");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const faebryk = @import("faebryk");
const fabll = @import("fabll.zig");
const str = []const u8;

pub const REL_DIGITS: usize = 7;
pub const ABS_DIGITS: usize = 15;
pub const EPSILON_REL: f64 = std.math.pow(f64, 10.0, -@as(f64, REL_DIGITS - 1));
pub const EPSILON_ABS: f64 = std.math.pow(f64, 10.0, -@as(f64, ABS_DIGITS));
pub const PRINT_DIGITS: usize = 3;

pub const Error = error{
    NotSingleton,
    IncompatibleTypes,
    InvalidInterval,
    InvalidSerializedType,
};

fn typegraph_of(instance: graph.BoundNodeReference) faebryk.typegraph.TypeGraph {
    return faebryk.typegraph.TypeGraph.of_instance(instance) orelse
        @panic("instance is not attached to a typegraph");
}

fn collect_child_values(
    parent: graph.BoundNodeReference,
    comptime T: type,
    allocator: std.mem.Allocator,
    comptime getter: fn (graph.BoundNodeReference, std.mem.Allocator) anyerror!T,
) ![]T {
    const Ctx = struct {
        allocator: std.mem.Allocator,
        out: std.ArrayList(T),

        fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
            const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
            const child = be.g.bind(faebryk.composition.EdgeComposition.get_child_node(be.edge));
            const value = getter(child, ctx.allocator) catch |err| return visitor.VisitResult(void){ .ERROR = err };
            ctx.out.append(value) catch return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
            return visitor.VisitResult(void){ .CONTINUE = {} };
        }
    };

    var ctx: Ctx = .{
        .allocator = allocator,
        .out = std.ArrayList(T).init(allocator),
    };
    errdefer ctx.out.deinit();

    switch (faebryk.composition.EdgeComposition.visit_children_edges(parent, void, &ctx, Ctx.visit)) {
        .ERROR => |err| return err,
        else => {},
    }

    return ctx.out.toOwnedSlice();
}

fn dedup_sort_strings(values: []str, allocator: std.mem.Allocator) ![]str {
    var map = std.StringHashMap(void).init(allocator);
    defer map.deinit();

    for (values) |v| {
        try map.put(v, {});
    }

    var out = std.ArrayList(str).init(allocator);
    errdefer out.deinit();

    var it = map.iterator();
    while (it.next()) |entry| {
        try out.append(entry.key_ptr.*);
    }

    std.sort.block(str, out.items, {}, struct {
        fn lessThan(_: void, lhs: str, rhs: str) bool {
            return std.mem.lessThan(u8, lhs, rhs);
        }
    }.lessThan);

    return out.toOwnedSlice();
}

fn dedup_sort_ints(values: []i64, allocator: std.mem.Allocator) ![]i64 {
    var map = std.AutoHashMap(i64, void).init(allocator);
    defer map.deinit();

    for (values) |v| {
        try map.put(v, {});
    }

    var out = std.ArrayList(i64).init(allocator);
    errdefer out.deinit();

    var it = map.iterator();
    while (it.next()) |entry| {
        try out.append(entry.key_ptr.*);
    }

    std.sort.block(i64, out.items, {}, std.sort.asc(i64));
    return out.toOwnedSlice();
}

fn dedup_sort_bools(values: []bool, allocator: std.mem.Allocator) ![]bool {
    var seen_false = false;
    var seen_true = false;
    for (values) |v| {
        if (v) seen_true = true else seen_false = true;
    }

    var out = std.ArrayList(bool).init(allocator);
    errdefer out.deinit();
    if (seen_false) try out.append(false);
    if (seen_true) try out.append(true);
    return out.toOwnedSlice();
}

fn eql_string_slices(a: []const str, b: []const str) bool {
    if (a.len != b.len) return false;
    for (a, 0..) |av, i| {
        if (!std.mem.eql(u8, av, b[i])) return false;
    }
    return true;
}

fn eql_intervals(a: []const Interval, b: []const Interval) bool {
    if (a.len != b.len) return false;
    for (a, 0..) |av, i| {
        const bv = b[i];
        if (av.min != bv.min or av.max != bv.max) return false;
    }
    return true;
}

pub const String = struct {
    node: fabll.Node,

    pub const Attributes = struct {
        value: str,
    };

    pub fn MakeChild(comptime value: str) type {
        return fabll.MakeChildWithTypedAttrs(@This(), .{ .value = value });
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, value: str) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance_with_attrs(g, .{ .value = value });
    }

    pub fn get_value(self: @This()) str {
        return fabll.get_typed_attributes(self).value;
    }
};

pub const StringsSerialized = struct {
    @"type": str,
    data: struct {
        values: []str,
    },
};

pub const Strings = struct {
    node: fabll.Node,

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn setup_from_values(self: @This(), values: []const str) @This() {
        var tg = typegraph_of(self.node.instance);
        const g = self.node.instance.g;

        for (values) |value| {
            const lit = String.create_instance(g, &tg, value);
            _ = faebryk.composition.EdgeComposition.add_child(self.node.instance, lit.node.instance.node, null) catch
                @panic("failed to add String literal child");
        }
        return self;
    }

    fn get_child_value(child: graph.BoundNodeReference, _: std.mem.Allocator) !str {
        const lit = child.node.get("value") orelse return error.InvalidArgument;
        return lit.String;
    }

    pub fn get_values(self: @This(), allocator: std.mem.Allocator) ![]str {
        const raw = try collect_child_values(self.node.instance, str, allocator, get_child_value);
        defer allocator.free(raw);
        return dedup_sort_strings(raw, allocator);
    }

    pub fn is_singleton(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        return values.len == 1;
    }

    pub fn get_single(self: @This(), allocator: std.mem.Allocator) !str {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len != 1) return Error.NotSingleton;
        return values[0];
    }

    pub fn is_empty(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        return values.len == 0;
    }

    pub fn any(self: @This(), allocator: std.mem.Allocator) !str {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len == 0) return error.InvalidArgument;
        return values[0];
    }

    pub fn op_setic_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);
        return eql_string_slices(a, b);
    }

    pub fn op_setic_is_subset_of(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var bset = std.StringHashMap(void).init(allocator);
        defer bset.deinit();
        for (b) |v| try bset.put(v, {});

        for (a) |v| {
            if (!bset.contains(v)) return false;
        }
        return true;
    }

    pub fn uncertainty_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = Booleans.create_instance(g, &tg);

        var a_set = std.StringHashMap(void).init(allocator);
        defer a_set.deinit();
        for (a) |v| try a_set.put(v, {});

        var overlap = false;
        for (b) |v| {
            if (a_set.contains(v)) {
                overlap = true;
                break;
            }
        }

        var vals = std.ArrayList(bool).init(allocator);
        defer vals.deinit();
        if (!(a.len == 1 and b.len == 1 and overlap)) try vals.append(false);
        if (overlap) try vals.append(true);

        return out.setup_from_values(vals.items);
    }

    pub fn op_intersect_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var bset = std.StringHashMap(void).init(allocator);
        defer bset.deinit();
        for (b) |v| try bset.put(v, {});

        var inter = std.ArrayList(str).init(allocator);
        defer inter.deinit();
        for (a) |v| {
            if (bset.contains(v)) try inter.append(v);
        }

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);
        return out.setup_from_values(inter.items);
    }

    pub fn op_union_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var vals = std.ArrayList(str).init(allocator);
        defer vals.deinit();
        try vals.appendSlice(a);
        try vals.appendSlice(b);

        const merged = try dedup_sort_strings(vals.items, allocator);
        defer allocator.free(merged);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);
        return out.setup_from_values(merged);
    }

    pub fn op_symmetric_difference_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const unioned = try self.op_union_intervals(other, allocator);
        const inter = try self.op_intersect_intervals(other, allocator);

        const u = try unioned.get_values(allocator);
        defer allocator.free(u);
        const i = try inter.get_values(allocator);
        defer allocator.free(i);

        var iset = std.StringHashMap(void).init(allocator);
        defer iset.deinit();
        for (i) |v| try iset.put(v, {});

        var outvals = std.ArrayList(str).init(allocator);
        defer outvals.deinit();
        for (u) |v| {
            if (!iset.contains(v)) try outvals.append(v);
        }

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);
        return out.setup_from_values(outvals.items);
    }

    pub fn pretty_str(self: @This(), allocator: std.mem.Allocator) ![]const u8 {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len == 1) {
            return std.fmt.allocPrint(allocator, "'{s}'", .{values[0]});
        }
        return std.fmt.allocPrint(allocator, "{any}", .{values});
    }

    pub fn serialize(self: @This(), allocator: std.mem.Allocator) !StringsSerialized {
        const values = try self.get_values(allocator);
        return .{
            .@"type" = "StringSet",
            .data = .{ .values = values },
        };
    }

    pub fn deserialize(data: StringsSerialized, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) !@This() {
        if (!std.mem.eql(u8, data.@"type", "StringSet")) return Error.InvalidSerializedType;
        var out = fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
        return out.setup_from_values(data.data.values);
    }
};

pub const Numeric = struct {
    node: fabll.Node,

    pub const Attributes = struct {
        value: f64,
    };

    pub fn MakeChild(comptime value: f64) type {
        return fabll.MakeChildWithTypedAttrs(@This(), .{ .value = value });
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, value: f64) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance_with_attrs(g, .{ .value = value });
    }

    pub fn get_value(self: @This()) f64 {
        return fabll.get_typed_attributes(self).value;
    }

    pub fn float_round(value: f64, digits: usize) f64 {
        if (std.math.isInf(value)) return value;
        const multiplier = std.math.pow(f64, 10.0, @as(f64, @floatFromInt(digits)));
        return @floor(value * multiplier + 0.5) / multiplier;
    }
};

pub const NumericInterval = struct {
    node: fabll.Node,

    pub const Attributes = struct {
        min: f64,
        max: f64,
    };

    pub fn validate_bounds(min: f64, max: f64) bool {
        return min <= max;
    }

    pub fn MakeChild(comptime min: f64, comptime max: f64) type {
        if (!validate_bounds(min, max)) {
            @compileError("Invalid interval bounds");
        }
        return fabll.MakeChildWithTypedAttrs(@This(), .{ .min = min, .max = max });
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, min: f64, max: f64) !@This() {
        if (!validate_bounds(min, max)) return Error.InvalidInterval;
        return fabll.Node.bind_typegraph(@This(), tg).create_instance_with_attrs(g, .{ .min = min, .max = max });
    }

    pub fn get_min_value(self: @This()) f64 {
        return fabll.get_typed_attributes(self).min;
    }

    pub fn get_max_value(self: @This()) f64 {
        return fabll.get_typed_attributes(self).max;
    }

    pub fn is_singleton(self: @This()) bool {
        const attrs = fabll.get_typed_attributes(self);
        return attrs.min == attrs.max;
    }

    pub fn get_single(self: @This()) !f64 {
        if (!self.is_singleton()) return Error.NotSingleton;
        return self.get_min_value();
    }
};

pub const Interval = struct {
    min: f64,
    max: f64,
};

fn normalize_intervals(intervals: []const Interval, allocator: std.mem.Allocator) ![]Interval {
    if (intervals.len == 0) return allocator.alloc(Interval, 0);

    const sorted = try allocator.dupe(Interval, intervals);
    errdefer allocator.free(sorted);
    std.sort.block(Interval, sorted, {}, struct {
        fn lessThan(_: void, lhs: Interval, rhs: Interval) bool {
            if (lhs.min == rhs.min) return lhs.max < rhs.max;
            return lhs.min < rhs.min;
        }
    }.lessThan);

    var out = std.ArrayList(Interval).init(allocator);
    errdefer out.deinit();

    var current = sorted[0];
    var i: usize = 1;
    while (i < sorted.len) : (i += 1) {
        const next = sorted[i];
        if (next.min <= current.max + EPSILON_ABS) {
            if (next.max > current.max) current.max = next.max;
        } else {
            try out.append(current);
            current = next;
        }
    }
    try out.append(current);

    allocator.free(sorted);
    return out.toOwnedSlice();
}

pub const NumericSetSerialized = struct {
    @"type": str,
    data: struct {
        intervals: []Interval,
    },
};

pub const NumericSet = struct {
    node: fabll.Node,

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup_from_values(self: @This(), values: []const Interval, allocator: std.mem.Allocator) !@This() {
        var tg = typegraph_of(self.node.instance);
        const g = self.node.instance.g;

        const normalized = try normalize_intervals(values, allocator);
        defer allocator.free(normalized);

        for (normalized) |interval| {
            const child = try NumericInterval.create_instance(g, &tg, interval.min, interval.max);
            _ = faebryk.composition.EdgeComposition.add_child(self.node.instance, child.node.instance.node, null) catch
                @panic("failed to add NumericInterval child");
        }
        return self;
    }

    fn get_child_interval(child: graph.BoundNodeReference, _: std.mem.Allocator) !Interval {
        const min_l = child.node.get("min") orelse return error.InvalidArgument;
        const max_l = child.node.get("max") orelse return error.InvalidArgument;
        return .{ .min = min_l.Float, .max = max_l.Float };
    }

    pub fn get_intervals(self: @This(), allocator: std.mem.Allocator) ![]Interval {
        const raw = try collect_child_values(self.node.instance, Interval, allocator, get_child_interval);
        defer allocator.free(raw);
        return normalize_intervals(raw, allocator);
    }

    pub fn is_empty(self: @This(), allocator: std.mem.Allocator) !bool {
        const intervals = try self.get_intervals(allocator);
        defer allocator.free(intervals);
        return intervals.len == 0;
    }

    pub fn is_singleton(self: @This(), allocator: std.mem.Allocator) !bool {
        const intervals = try self.get_intervals(allocator);
        defer allocator.free(intervals);
        if (intervals.len != 1) return false;
        return intervals[0].min == intervals[0].max;
    }

    pub fn get_min_value(self: @This(), allocator: std.mem.Allocator) !f64 {
        const intervals = try self.get_intervals(allocator);
        defer allocator.free(intervals);
        if (intervals.len == 0) return error.InvalidArgument;
        return intervals[0].min;
    }

    pub fn get_max_value(self: @This(), allocator: std.mem.Allocator) !f64 {
        const intervals = try self.get_intervals(allocator);
        defer allocator.free(intervals);
        if (intervals.len == 0) return error.InvalidArgument;
        return intervals[intervals.len - 1].max;
    }

    pub fn contains(self: @This(), allocator: std.mem.Allocator, value: f64) !bool {
        const intervals = try self.get_intervals(allocator);
        defer allocator.free(intervals);
        for (intervals) |interval| {
            if (value >= interval.min and value <= interval.max) return true;
        }
        return false;
    }

    pub fn op_setic_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_intervals(allocator);
        defer allocator.free(a);
        const b = try other.get_intervals(allocator);
        defer allocator.free(b);
        return eql_intervals(a, b);
    }

    pub fn is_subset_of(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_intervals(allocator);
        defer allocator.free(a);
        const b = try other.get_intervals(allocator);
        defer allocator.free(b);

        var bi: usize = 0;
        for (a) |iv| {
            while (bi < b.len and b[bi].max < iv.min - EPSILON_ABS) : (bi += 1) {}
            if (bi >= b.len) return false;
            if (b[bi].min > iv.min + EPSILON_ABS or b[bi].max < iv.max - EPSILON_ABS) {
                return false;
            }
        }
        return true;
    }

    pub fn is_superset_of(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        return other.is_subset_of(self, allocator);
    }

    pub fn op_intersect_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_intervals(allocator);
        defer allocator.free(a);
        const b = try other.get_intervals(allocator);
        defer allocator.free(b);

        var outvals = std.ArrayList(Interval).init(allocator);
        defer outvals.deinit();

        var i: usize = 0;
        var j: usize = 0;
        while (i < a.len and j < b.len) {
            const lo = @max(a[i].min, b[j].min);
            const hi = @min(a[i].max, b[j].max);
            if (lo <= hi) try outvals.append(.{ .min = lo, .max = hi });

            if (a[i].max < b[j].max) {
                i += 1;
            } else {
                j += 1;
            }
        }

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        return out.setup_from_values(outvals.items, allocator);
    }

    pub fn op_union(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_intervals(allocator);
        defer allocator.free(a);
        const b = try other.get_intervals(allocator);
        defer allocator.free(b);

        var all = std.ArrayList(Interval).init(allocator);
        defer all.deinit();
        try all.appendSlice(a);
        try all.appendSlice(b);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        return out.setup_from_values(all.items, allocator);
    }

    pub fn op_symmetric_difference_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const unioned = try self.op_union(other, allocator);
        const inter = try self.op_intersect_intervals(other, allocator);

        const u = try unioned.get_intervals(allocator);
        defer allocator.free(u);
        const i = try inter.get_intervals(allocator);
        defer allocator.free(i);

        var outvals = std.ArrayList(Interval).init(allocator);
        defer outvals.deinit();

        var cursor: usize = 0;
        while (cursor < u.len) : (cursor += 1) {
            const current = u[cursor];
            var fragments = std.ArrayList(Interval).init(allocator);
            defer fragments.deinit();
            try fragments.append(current);

            for (i) |cut| {
                var next_frags = std.ArrayList(Interval).init(allocator);
                defer next_frags.deinit();
                for (fragments.items) |frag| {
                    if (cut.max < frag.min or cut.min > frag.max) {
                        try next_frags.append(frag);
                        continue;
                    }
                    if (cut.min > frag.min) {
                        try next_frags.append(.{ .min = frag.min, .max = cut.min });
                    }
                    if (cut.max < frag.max) {
                        try next_frags.append(.{ .min = cut.max, .max = frag.max });
                    }
                }
                fragments.clearRetainingCapacity();
                try fragments.appendSlice(next_frags.items);
            }

            for (fragments.items) |frag| {
                if (frag.min <= frag.max) try outvals.append(frag);
            }
        }

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        return out.setup_from_values(outvals.items, allocator);
    }

    pub fn uncertainty_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = Booleans.create_instance(g, &tg);

        const inter = try self.op_intersect_intervals(other, allocator);
        const has_inter = !(try inter.is_empty(allocator));
        const same_single = (try self.is_singleton(allocator)) and (try other.is_singleton(allocator)) and (try self.op_setic_equals(other, allocator));

        var vals = std.ArrayList(bool).init(allocator);
        defer vals.deinit();
        if (!same_single) try vals.append(false);
        if (has_inter) try vals.append(true);
        return out.setup_from_values(vals.items);
    }

    pub fn serialize(self: @This(), allocator: std.mem.Allocator) !NumericSetSerialized {
        const intervals = try self.get_intervals(allocator);
        return .{
            .@"type" = "Numeric_Interval_Disjoint",
            .data = .{ .intervals = intervals },
        };
    }

    pub fn deserialize(data: NumericSetSerialized, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, allocator: std.mem.Allocator) !@This() {
        if (!std.mem.eql(u8, data.@"type", "Numeric_Interval_Disjoint")) return Error.InvalidSerializedType;
        const out = create_instance(g, tg);
        return out.setup_from_values(data.data.intervals, allocator);
    }
};

pub const NumbersSerialized = struct {
    @"type": str,
    data: struct {
        intervals: []Interval,
    },
};

pub const Numbers = struct {
    node: fabll.Node,

    pub fn MakeChild(comptime min: f64, comptime max: f64) type {
        const numeric_set_child = NumericSet.MakeChild().add_dependant_before(
            NumericInterval.MakeChild(min, max),
        );
        return fabll.ChildField(@This(), null, &.{}, &.{numeric_set_child}, &.{});
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup_from_min_max(self: @This(), min: f64, max: f64, allocator: std.mem.Allocator) !@This() {
        var tg = typegraph_of(self.node.instance);
        var numeric_set = NumericSet.create_instance(self.node.instance.g, &tg);
        const intervals = [_]Interval{.{ .min = min, .max = max }};
        numeric_set = try numeric_set.setup_from_values(&intervals, allocator);
        _ = faebryk.composition.EdgeComposition.add_child(self.node.instance, numeric_set.node.instance.node, "numeric_set") catch
            @panic("failed to add numeric_set child");
        return self;
    }

    pub fn setup_from_singleton(self: @This(), value: f64, allocator: std.mem.Allocator) !@This() {
        return self.setup_from_min_max(value, value, allocator);
    }

    pub fn setup_from_singletons(self: @This(), values: []const f64, allocator: std.mem.Allocator) !@This() {
        var intervals = std.ArrayList(Interval).init(allocator);
        defer intervals.deinit();
        for (values) |v| {
            try intervals.append(.{ .min = v, .max = v });
        }

        var tg = typegraph_of(self.node.instance);
        var numeric_set = NumericSet.create_instance(self.node.instance.g, &tg);
        numeric_set = try numeric_set.setup_from_values(intervals.items, allocator);
        _ = faebryk.composition.EdgeComposition.add_child(self.node.instance, numeric_set.node.instance.node, "numeric_set") catch
            @panic("failed to add numeric_set child");
        return self;
    }

    pub fn get_numeric_set(self: @This()) NumericSet {
        const child = faebryk.composition.EdgeComposition.get_child_by_identifier(self.node.instance, "numeric_set") orelse
            @panic("missing numeric_set child");
        return .{ .node = .{ .instance = child } };
    }

    pub fn is_empty(self: @This(), allocator: std.mem.Allocator) !bool {
        return self.get_numeric_set().is_empty(allocator);
    }

    pub fn is_singleton(self: @This(), allocator: std.mem.Allocator) !bool {
        return self.get_numeric_set().is_singleton(allocator);
    }

    pub fn get_single(self: @This(), allocator: std.mem.Allocator) !f64 {
        if (!(try self.is_singleton(allocator))) return Error.NotSingleton;
        return self.get_numeric_set().get_min_value(allocator);
    }

    pub fn get_min_value(self: @This(), allocator: std.mem.Allocator) !f64 {
        return self.get_numeric_set().get_min_value(allocator);
    }

    pub fn get_max_value(self: @This(), allocator: std.mem.Allocator) !f64 {
        return self.get_numeric_set().get_max_value(allocator);
    }

    pub fn op_setic_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        return self.get_numeric_set().op_setic_equals(other.get_numeric_set(), allocator);
    }

    pub fn op_setic_is_subset_of(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        return self.get_numeric_set().is_subset_of(other.get_numeric_set(), allocator);
    }

    pub fn op_setic_is_superset_of(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        return self.get_numeric_set().is_superset_of(other.get_numeric_set(), allocator);
    }

    pub fn op_intersect_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const out_set = try self.get_numeric_set().op_intersect_intervals(other.get_numeric_set(), allocator);
        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        _ = faebryk.composition.EdgeComposition.add_child(out.node.instance, out_set.node.instance.node, "numeric_set") catch
            @panic("failed to add numeric_set child");
        return out;
    }

    pub fn op_union_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const out_set = try self.get_numeric_set().op_union(other.get_numeric_set(), allocator);
        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        _ = faebryk.composition.EdgeComposition.add_child(out.node.instance, out_set.node.instance.node, "numeric_set") catch
            @panic("failed to add numeric_set child");
        return out;
    }

    pub fn op_symmetric_difference_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const out_set = try self.get_numeric_set().op_symmetric_difference_intervals(other.get_numeric_set(), allocator);
        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        _ = faebryk.composition.EdgeComposition.add_child(out.node.instance, out_set.node.instance.node, "numeric_set") catch
            @panic("failed to add numeric_set child");
        return out;
    }

    pub fn uncertainty_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        return self.get_numeric_set().uncertainty_equals(other.get_numeric_set(), allocator);
    }

    fn from_intervals_like(self: @This(), intervals: []const Interval, allocator: std.mem.Allocator) !@This() {
        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        var set = NumericSet.create_instance(g, &tg);
        set = try set.setup_from_values(intervals, allocator);
        _ = faebryk.composition.EdgeComposition.add_child(out.node.instance, set.node.instance.node, "numeric_set") catch
            @panic("failed to add numeric_set child");
        return out;
    }

    pub fn setup_from_center_rel(self: @This(), center: f64, rel: f64, allocator: std.mem.Allocator) !@This() {
        return self.setup_from_min_max(center - rel * center, center + rel * center, allocator);
    }

    pub fn unbounded(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, allocator: std.mem.Allocator) !@This() {
        const out = create_instance(g, tg);
        return out.setup_from_min_max(-std.math.inf(f64), std.math.inf(f64), allocator);
    }

    pub fn try_get_single(self: @This(), allocator: std.mem.Allocator) !?f64 {
        if (!(try self.is_singleton(allocator))) return null;
        return self.get_min_value(allocator);
    }

    pub fn contains_value(self: @This(), value: f64, allocator: std.mem.Allocator) !bool {
        return self.get_numeric_set().contains(allocator, value);
    }

    pub fn contains(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const single = try other.get_single(allocator);
        return self.contains_value(single, allocator);
    }

    pub fn min_elem(self: @This(), allocator: std.mem.Allocator) !@This() {
        const min = try self.get_min_value(allocator);
        return self.from_intervals_like(&.{.{ .min = min, .max = min }}, allocator);
    }

    pub fn max_elem(self: @This(), allocator: std.mem.Allocator) !@This() {
        const max = try self.get_max_value(allocator);
        return self.from_intervals_like(&.{.{ .min = max, .max = max }}, allocator);
    }

    pub fn as_gapless(self: @This(), allocator: std.mem.Allocator) !@This() {
        const min = try self.get_min_value(allocator);
        const max = try self.get_max_value(allocator);
        return self.from_intervals_like(&.{.{ .min = min, .max = max }}, allocator);
    }

    pub fn is_unbounded(self: @This(), allocator: std.mem.Allocator) !bool {
        const min = try self.get_min_value(allocator);
        const max = try self.get_max_value(allocator);
        return std.math.isInf(min) or std.math.isInf(max);
    }

    pub fn is_finite(self: @This(), allocator: std.mem.Allocator) !bool {
        return !(try self.is_unbounded(allocator));
    }

    pub fn is_integer(self: @This(), allocator: std.mem.Allocator) !bool {
        const intervals = try self.get_numeric_set().get_intervals(allocator);
        defer allocator.free(intervals);
        for (intervals) |i| {
            if (@floor(i.min) != i.min or @floor(i.max) != i.max) return false;
        }
        return true;
    }

    pub fn op_total_span(self: @This(), allocator: std.mem.Allocator) !@This() {
        const intervals = try self.get_numeric_set().get_intervals(allocator);
        defer allocator.free(intervals);
        var total: f64 = 0.0;
        for (intervals) |i| total += @abs(i.max - i.min);
        return self.from_intervals_like(&.{.{ .min = total, .max = total }}, allocator);
    }

    pub fn op_deviation_to(self: @This(), other: @This(), relative: bool, allocator: std.mem.Allocator) !@This() {
        const sym = try self.op_symmetric_difference_intervals(other, allocator);
        const abs = try sym.op_total_span(allocator);
        if (!relative) return abs;

        const self_abs = try self.op_abs(allocator);
        const other_abs = try other.op_abs(allocator);
        const self_max = try self_abs.get_max_value(allocator);
        const other_max = try other_abs.get_max_value(allocator);
        const denom = @max(self_max, other_max);
        if (denom == 0.0) return self.from_intervals_like(&.{.{ .min = 0.0, .max = 0.0 }}, allocator);

        const div = try self.from_intervals_like(&.{.{ .min = denom, .max = denom }}, allocator);
        return op_div_intervals(abs, div, allocator);
    }

    pub fn op_ge(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        const self_min = try self.get_min_value(allocator);
        const self_max = try self.get_max_value(allocator);
        const other_min = try other.get_min_value(allocator);
        const other_max = try other.get_max_value(allocator);

        var tg = typegraph_of(self.node.instance);
        const b = Booleans.create_instance(self.node.instance.g, &tg);
        const definitely_true = self_min >= other_max;
        const definitely_false = self_max < other_min;
        if (definitely_true) return b.setup_from_values(&.{true});
        if (definitely_false) return b.setup_from_values(&.{false});
        return b.setup_from_values(&.{ false, true });
    }

    pub fn op_gt(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        const self_min = try self.get_min_value(allocator);
        const self_max = try self.get_max_value(allocator);
        const other_min = try other.get_min_value(allocator);
        const other_max = try other.get_max_value(allocator);

        var tg = typegraph_of(self.node.instance);
        const b = Booleans.create_instance(self.node.instance.g, &tg);
        const definitely_true = self_min > other_max;
        const definitely_false = self_max <= other_min;
        if (definitely_true) return b.setup_from_values(&.{true});
        if (definitely_false) return b.setup_from_values(&.{false});
        return b.setup_from_values(&.{ false, true });
    }

    pub fn op_le(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        return other.op_ge(self, allocator);
    }

    pub fn op_lt(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        return other.op_gt(self, allocator);
    }

    pub fn op_neg(self: @This(), allocator: std.mem.Allocator) !@This() {
        const min = try self.get_min_value(allocator);
        const max = try self.get_max_value(allocator);
        return self.from_intervals_like(&.{.{ .min = -max, .max = -min }}, allocator);
    }

    pub fn op_abs(self: @This(), allocator: std.mem.Allocator) !@This() {
        const intervals = try self.get_numeric_set().get_intervals(allocator);
        defer allocator.free(intervals);
        var outvals = std.ArrayList(Interval).init(allocator);
        defer outvals.deinit();

        for (intervals) |i| {
            if (i.max < 0) {
                try outvals.append(.{ .min = @abs(i.max), .max = @abs(i.min) });
            } else if (i.min > 0) {
                try outvals.append(i);
            } else {
                try outvals.append(.{ .min = 0.0, .max = @max(@abs(i.min), i.max) });
            }
        }
        return self.from_intervals_like(outvals.items, allocator);
    }

    pub fn op_round(self: @This(), ndigits: i32, allocator: std.mem.Allocator) !@This() {
        const min = try self.get_min_value(allocator);
        const max = try self.get_max_value(allocator);
        const digits: usize = if (ndigits < 0) 0 else @as(usize, @intCast(ndigits));
        return self.from_intervals_like(&.{.{
            .min = Numeric.float_round(min, digits),
            .max = Numeric.float_round(max, digits),
        }}, allocator);
    }

    pub fn op_floor(self: @This(), allocator: std.mem.Allocator) !@This() {
        const min = try self.get_min_value(allocator);
        const max = try self.get_max_value(allocator);
        return self.from_intervals_like(&.{.{
            .min = @floor(min),
            .max = @floor(max),
        }}, allocator);
    }

    pub fn op_ceil(self: @This(), allocator: std.mem.Allocator) !@This() {
        const min = try self.get_min_value(allocator);
        const max = try self.get_max_value(allocator);
        return self.from_intervals_like(&.{.{
            .min = @ceil(min),
            .max = @ceil(max),
        }}, allocator);
    }

    pub fn op_add_intervals(a: @This(), b: @This(), allocator: std.mem.Allocator) !@This() {
        return a.from_intervals_like(&.{.{
            .min = (try a.get_min_value(allocator)) + (try b.get_min_value(allocator)),
            .max = (try a.get_max_value(allocator)) + (try b.get_max_value(allocator)),
        }}, allocator);
    }

    pub fn op_sub_intervals(a: @This(), b: @This(), allocator: std.mem.Allocator) !@This() {
        return a.from_intervals_like(&.{.{
            .min = (try a.get_min_value(allocator)) - (try b.get_max_value(allocator)),
            .max = (try a.get_max_value(allocator)) - (try b.get_min_value(allocator)),
        }}, allocator);
    }

    pub fn op_mul_intervals(a: @This(), b: @This(), allocator: std.mem.Allocator) !@This() {
        const a0 = try a.get_min_value(allocator);
        const a1 = try a.get_max_value(allocator);
        const b0 = try b.get_min_value(allocator);
        const b1 = try b.get_max_value(allocator);
        const p = [_]f64{ a0 * b0, a0 * b1, a1 * b0, a1 * b1 };
        var min = p[0];
        var max = p[0];
        for (p[1..]) |v| {
            min = @min(min, v);
            max = @max(max, v);
        }
        return a.from_intervals_like(&.{.{ .min = min, .max = max }}, allocator);
    }

    pub fn op_div_intervals(a: @This(), b: @This(), allocator: std.mem.Allocator) !@This() {
        const b0 = try b.get_min_value(allocator);
        const b1 = try b.get_max_value(allocator);
        if (b0 <= 0 and b1 >= 0) {
            return a.from_intervals_like(&.{.{ .min = -std.math.inf(f64), .max = std.math.inf(f64) }}, allocator);
        }
        const inv = try b.from_intervals_like(&.{.{ .min = 1.0 / b1, .max = 1.0 / b0 }}, allocator);
        return op_mul_intervals(a, inv, allocator);
    }

    pub fn op_pow_intervals(a: @This(), exponent: f64, allocator: std.mem.Allocator) !@This() {
        const min = try a.get_min_value(allocator);
        const max = try a.get_max_value(allocator);
        const p0 = std.math.pow(f64, min, exponent);
        const p1 = std.math.pow(f64, max, exponent);
        return a.from_intervals_like(&.{.{ .min = @min(p0, p1), .max = @max(p0, p1) }}, allocator);
    }

    pub fn get_values(self: @This(), allocator: std.mem.Allocator) ![]f64 {
        const min = try self.get_min_value(allocator);
        const max = try self.get_max_value(allocator);
        var out = try allocator.alloc(f64, 2);
        out[0] = min;
        out[1] = max;
        return out;
    }

    pub fn any(self: @This(), allocator: std.mem.Allocator) !f64 {
        return self.get_min_value(allocator);
    }

    pub fn serialize(self: @This(), allocator: std.mem.Allocator) !NumbersSerialized {
        const intervals = try self.get_numeric_set().get_intervals(allocator);
        const discrete = blk: {
            for (intervals) |i| {
                if (i.min != i.max) break :blk false;
            }
            break :blk true;
        };

        return .{
            .@"type" = if (discrete) "Quantity_Set_Discrete" else "Quantity_Interval_Disjoint",
            .data = .{ .intervals = intervals },
        };
    }

    pub fn deserialize(data: NumbersSerialized, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, allocator: std.mem.Allocator) !@This() {
        const is_discrete = std.mem.eql(u8, data.@"type", "Quantity_Set_Discrete");
        const is_interval = std.mem.eql(u8, data.@"type", "Quantity_Interval_Disjoint");
        if (!(is_discrete or is_interval)) return Error.InvalidSerializedType;

        const out = create_instance(g, tg);
        var set = NumericSet.create_instance(g, tg);
        set = try set.setup_from_values(data.data.intervals, allocator);
        _ = faebryk.composition.EdgeComposition.add_child(out.node.instance, set.node.instance.node, "numeric_set") catch
            @panic("failed to add numeric_set child");
        return out;
    }
};

pub const Count = struct {
    node: fabll.Node,

    pub const Attributes = struct {
        value: i64,
    };

    pub fn MakeChild(comptime value: i64) type {
        return fabll.MakeChildWithTypedAttrs(@This(), .{ .value = value });
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, value: i64) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance_with_attrs(g, .{ .value = value });
    }

    pub fn get_value(self: @This()) i64 {
        return fabll.get_typed_attributes(self).value;
    }
};

pub const CountsSerialized = struct {
    @"type": str,
    data: struct { values: []i64 },
};

pub const Counts = struct {
    node: fabll.Node,

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn setup_from_values(self: @This(), values: []const i64) @This() {
        var tg = typegraph_of(self.node.instance);
        const g = self.node.instance.g;

        for (values) |value| {
            const lit = Count.create_instance(g, &tg, value);
            _ = faebryk.composition.EdgeComposition.add_child(self.node.instance, lit.node.instance.node, null) catch
                @panic("failed to add Count literal child");
        }
        return self;
    }

    fn get_child_value(child: graph.BoundNodeReference, _: std.mem.Allocator) !i64 {
        const lit = child.node.get("value") orelse return error.InvalidArgument;
        return lit.Int;
    }

    pub fn get_values(self: @This(), allocator: std.mem.Allocator) ![]i64 {
        const raw = try collect_child_values(self.node.instance, i64, allocator, get_child_value);
        defer allocator.free(raw);
        return dedup_sort_ints(raw, allocator);
    }

    pub fn is_singleton(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        return values.len == 1;
    }

    pub fn get_single(self: @This(), allocator: std.mem.Allocator) !i64 {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len != 1) return Error.NotSingleton;
        return values[0];
    }

    pub fn is_empty(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        return values.len == 0;
    }

    pub fn any(self: @This(), allocator: std.mem.Allocator) !i64 {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len == 0) return error.InvalidArgument;
        return values[0];
    }

    pub fn op_setic_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);
        return std.mem.eql(i64, a, b);
    }

    pub fn op_setic_is_subset_of(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var bset = std.AutoHashMap(i64, void).init(allocator);
        defer bset.deinit();
        for (b) |v| try bset.put(v, {});

        for (a) |v| {
            if (!bset.contains(v)) return false;
        }
        return true;
    }

    pub fn uncertainty_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = Booleans.create_instance(g, &tg);

        var aset = std.AutoHashMap(i64, void).init(allocator);
        defer aset.deinit();
        for (a) |v| try aset.put(v, {});

        var overlap = false;
        for (b) |v| {
            if (aset.contains(v)) {
                overlap = true;
                break;
            }
        }

        var vals = std.ArrayList(bool).init(allocator);
        defer vals.deinit();
        if (!(a.len == 1 and b.len == 1 and overlap)) try vals.append(false);
        if (overlap) try vals.append(true);
        return out.setup_from_values(vals.items);
    }

    pub fn op_intersect_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var bset = std.AutoHashMap(i64, void).init(allocator);
        defer bset.deinit();
        for (b) |v| try bset.put(v, {});

        var outvals = std.ArrayList(i64).init(allocator);
        defer outvals.deinit();
        for (a) |v| if (bset.contains(v)) try outvals.append(v);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);
        return out.setup_from_values(outvals.items);
    }

    pub fn op_union_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var vals = std.ArrayList(i64).init(allocator);
        defer vals.deinit();
        try vals.appendSlice(a);
        try vals.appendSlice(b);

        const merged = try dedup_sort_ints(vals.items, allocator);
        defer allocator.free(merged);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);
        return out.setup_from_values(merged);
    }

    pub fn op_symmetric_difference_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const unioned = try self.op_union_intervals(other, allocator);
        const inter = try self.op_intersect_intervals(other, allocator);

        const u = try unioned.get_values(allocator);
        defer allocator.free(u);
        const i = try inter.get_values(allocator);
        defer allocator.free(i);

        var iset = std.AutoHashMap(i64, void).init(allocator);
        defer iset.deinit();
        for (i) |v| try iset.put(v, {});

        var outvals = std.ArrayList(i64).init(allocator);
        defer outvals.deinit();
        for (u) |v| if (!iset.contains(v)) try outvals.append(v);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);
        return out.setup_from_values(outvals.items);
    }

    pub fn serialize(self: @This(), allocator: std.mem.Allocator) !CountsSerialized {
        const values = try self.get_values(allocator);
        return .{ .@"type" = "CountSet", .data = .{ .values = values } };
    }

    pub fn deserialize(data: CountsSerialized, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) !@This() {
        if (!std.mem.eql(u8, data.@"type", "CountSet")) return Error.InvalidSerializedType;
        var out = fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
        return out.setup_from_values(data.data.values);
    }
};

pub const Boolean = struct {
    node: fabll.Node,

    pub const Attributes = struct {
        value: bool,
    };

    pub fn MakeChild(comptime value: bool) type {
        return fabll.MakeChildWithTypedAttrs(@This(), .{ .value = value });
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, value: bool) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance_with_attrs(g, .{ .value = value });
    }

    pub fn get_value(self: @This()) bool {
        return fabll.get_typed_attributes(self).value;
    }
};

pub const BooleansSerialized = struct {
    @"type": str,
    data: struct { values: []bool },
};

pub const Booleans = struct {
    node: fabll.Node,

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance(g);
    }

    pub fn setup_from_values(self: @This(), values: []const bool) @This() {
        var tg = typegraph_of(self.node.instance);
        const g = self.node.instance.g;

        for (values) |value| {
            const lit = Boolean.create_instance(g, &tg, value);
            _ = faebryk.composition.EdgeComposition.add_child(self.node.instance, lit.node.instance.node, null) catch
                @panic("failed to add Boolean literal child");
        }
        return self;
    }

    fn get_child_value(child: graph.BoundNodeReference, _: std.mem.Allocator) !bool {
        const lit = child.node.get("value") orelse return error.InvalidArgument;
        return lit.Bool;
    }

    pub fn get_values(self: @This(), allocator: std.mem.Allocator) ![]bool {
        const raw = try collect_child_values(self.node.instance, bool, allocator, get_child_value);
        defer allocator.free(raw);
        return dedup_sort_bools(raw, allocator);
    }

    pub fn is_singleton(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        return values.len == 1;
    }

    pub fn get_single(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len != 1) return Error.NotSingleton;
        return values[0];
    }

    pub fn is_empty(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        return values.len == 0;
    }

    pub fn any(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len == 0) return error.InvalidArgument;
        return values[0];
    }

    pub fn op_setic_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);
        return std.mem.eql(bool, a, b);
    }

    pub fn op_setic_is_subset_of(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var has_false = false;
        var has_true = false;
        for (b) |v| {
            if (v) has_true = true else has_false = true;
        }

        for (a) |v| {
            if (v and !has_true) return false;
            if (!v and !has_false) return false;
        }
        return true;
    }

    pub fn uncertainty_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var overlap = false;
        for (a) |av| {
            for (b) |bv| {
                if (av == bv) {
                    overlap = true;
                    break;
                }
            }
            if (overlap) break;
        }

        var vals = std.ArrayList(bool).init(allocator);
        defer vals.deinit();
        if (!(a.len == 1 and b.len == 1 and overlap)) try vals.append(false);
        if (overlap) try vals.append(true);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        return out.setup_from_values(vals.items);
    }

    pub fn op_intersect_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var outvals = std.ArrayList(bool).init(allocator);
        defer outvals.deinit();
        for (a) |v| {
            for (b) |o| {
                if (v == o) {
                    try outvals.append(v);
                    break;
                }
            }
        }

        const dedup = try dedup_sort_bools(outvals.items, allocator);
        defer allocator.free(dedup);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        return out.setup_from_values(dedup);
    }

    pub fn op_union_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var vals = std.ArrayList(bool).init(allocator);
        defer vals.deinit();
        try vals.appendSlice(a);
        try vals.appendSlice(b);

        const dedup = try dedup_sort_bools(vals.items, allocator);
        defer allocator.free(dedup);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        return out.setup_from_values(dedup);
    }

    pub fn op_symmetric_difference_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const unioned = try self.op_union_intervals(other, allocator);
        const inter = try self.op_intersect_intervals(other, allocator);

        const u = try unioned.get_values(allocator);
        defer allocator.free(u);
        const i = try inter.get_values(allocator);
        defer allocator.free(i);

        var outvals = std.ArrayList(bool).init(allocator);
        defer outvals.deinit();
        for (u) |v| {
            var found = false;
            for (i) |iv| {
                if (v == iv) {
                    found = true;
                    break;
                }
            }
            if (!found) try outvals.append(v);
        }

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        const out = create_instance(g, &tg);
        return out.setup_from_values(outvals.items);
    }

    pub fn serialize(self: @This(), allocator: std.mem.Allocator) !BooleansSerialized {
        const values = try self.get_values(allocator);
        return .{ .@"type" = "BooleanSet", .data = .{ .values = values } };
    }

    pub fn deserialize(data: BooleansSerialized, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) !@This() {
        if (!std.mem.eql(u8, data.@"type", "BooleanSet")) return Error.InvalidSerializedType;
        const out = create_instance(g, tg);
        return out.setup_from_values(data.data.values);
    }
};

pub const EnumValue = struct {
    node: fabll.Node,

    pub const Attributes = struct {
        name: str,
        value: str,
    };

    pub fn MakeChild(comptime name: str, comptime value: str) type {
        return fabll.MakeChildWithTypedAttrs(@This(), .{ .name = name, .value = value });
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, name: str, value: str) @This() {
        return fabll.Node.bind_typegraph(@This(), tg).create_instance_with_attrs(g, .{ .name = name, .value = value });
    }
};

pub const EnumEntry = struct {
    name: str,
    value: str,
};

pub const AbstractEnumsSerialized = struct {
    @"type": str,
    data: struct { values: []str },
};

pub const AbstractEnums = struct {
    node: fabll.Node,

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn setup_from_values(self: @This(), values: []const EnumEntry) @This() {
        var tg = typegraph_of(self.node.instance);
        const g = self.node.instance.g;

        for (values) |value| {
            const lit = EnumValue.create_instance(g, &tg, value.name, value.value);
            _ = faebryk.composition.EdgeComposition.add_child(self.node.instance, lit.node.instance.node, null) catch
                @panic("failed to add EnumValue child");
        }
        return self;
    }

    fn get_child_value(child: graph.BoundNodeReference, _: std.mem.Allocator) !str {
        const lit = child.node.get("value") orelse return error.InvalidArgument;
        return lit.String;
    }

    pub fn get_values(self: @This(), allocator: std.mem.Allocator) ![]str {
        const raw = try collect_child_values(self.node.instance, str, allocator, get_child_value);
        defer allocator.free(raw);
        return dedup_sort_strings(raw, allocator);
    }

    pub fn is_singleton(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        return values.len == 1;
    }

    pub fn get_single(self: @This(), allocator: std.mem.Allocator) !str {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len != 1) return Error.NotSingleton;
        return values[0];
    }

    pub fn is_empty(self: @This(), allocator: std.mem.Allocator) !bool {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        return values.len == 0;
    }

    pub fn any(self: @This(), allocator: std.mem.Allocator) !str {
        const values = try self.get_values(allocator);
        defer allocator.free(values);
        if (values.len == 0) return error.InvalidArgument;
        return values[0];
    }

    pub fn op_setic_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);
        return eql_string_slices(a, b);
    }

    pub fn op_setic_is_subset_of(self: @This(), other: @This(), allocator: std.mem.Allocator) !bool {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var bset = std.StringHashMap(void).init(allocator);
        defer bset.deinit();
        for (b) |v| try bset.put(v, {});

        for (a) |v| {
            if (!bset.contains(v)) return false;
        }
        return true;
    }

    pub fn uncertainty_equals(self: @This(), other: @This(), allocator: std.mem.Allocator) !Booleans {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = Booleans.create_instance(g, &tg);

        var aset = std.StringHashMap(void).init(allocator);
        defer aset.deinit();
        for (a) |v| try aset.put(v, {});

        var overlap = false;
        for (b) |v| {
            if (aset.contains(v)) {
                overlap = true;
                break;
            }
        }

        var vals = std.ArrayList(bool).init(allocator);
        defer vals.deinit();
        if (!(a.len == 1 and b.len == 1 and overlap)) try vals.append(false);
        if (overlap) try vals.append(true);
        return out.setup_from_values(vals.items);
    }

    pub fn op_intersect_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var bset = std.StringHashMap(void).init(allocator);
        defer bset.deinit();
        for (b) |v| try bset.put(v, {});

        var outvals = std.ArrayList(str).init(allocator);
        defer outvals.deinit();
        for (a) |v| if (bset.contains(v)) try outvals.append(v);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);

        var entries = std.ArrayList(EnumEntry).init(allocator);
        defer entries.deinit();
        for (outvals.items) |v| try entries.append(.{ .name = v, .value = v });
        return out.setup_from_values(entries.items);
    }

    pub fn op_union_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const a = try self.get_values(allocator);
        defer allocator.free(a);
        const b = try other.get_values(allocator);
        defer allocator.free(b);

        var vals = std.ArrayList(str).init(allocator);
        defer vals.deinit();
        try vals.appendSlice(a);
        try vals.appendSlice(b);

        const dedup = try dedup_sort_strings(vals.items, allocator);
        defer allocator.free(dedup);

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);

        var entries = std.ArrayList(EnumEntry).init(allocator);
        defer entries.deinit();
        for (dedup) |v| try entries.append(.{ .name = v, .value = v });
        return out.setup_from_values(entries.items);
    }

    pub fn op_symmetric_difference_intervals(self: @This(), other: @This(), allocator: std.mem.Allocator) !@This() {
        const unioned = try self.op_union_intervals(other, allocator);
        const inter = try self.op_intersect_intervals(other, allocator);

        const u = try unioned.get_values(allocator);
        defer allocator.free(u);
        const i = try inter.get_values(allocator);
        defer allocator.free(i);

        var iset = std.StringHashMap(void).init(allocator);
        defer iset.deinit();
        for (i) |v| try iset.put(v, {});

        var entries = std.ArrayList(EnumEntry).init(allocator);
        defer entries.deinit();
        for (u) |v| {
            if (!iset.contains(v)) try entries.append(.{ .name = v, .value = v });
        }

        const g = self.node.instance.g;
        var tg = typegraph_of(self.node.instance);
        var out = fabll.Node.bind_typegraph(@This(), &tg).create_instance(g);
        return out.setup_from_values(entries.items);
    }

    pub fn serialize(self: @This(), allocator: std.mem.Allocator) !AbstractEnumsSerialized {
        const values = try self.get_values(allocator);
        return .{ .@"type" = "EnumSet", .data = .{ .values = values } };
    }

    pub fn deserialize(data: AbstractEnumsSerialized, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, allocator: std.mem.Allocator) !@This() {
        if (!std.mem.eql(u8, data.@"type", "EnumSet")) return Error.InvalidSerializedType;
        var out = fabll.Node.bind_typegraph(@This(), tg).create_instance(g);

        var entries = std.ArrayList(EnumEntry).init(allocator);
        defer entries.deinit();
        for (data.data.values) |value| {
            try entries.append(.{ .name = value, .value = value });
        }
        return out.setup_from_values(entries.items);
    }
};

// TESTS ============================================================================================

test "literals string set api" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const s = fabll.Node.bind_typegraph(Strings, &tg).create_instance(&g).setup_from_values(&.{ "a", "b", "b" });
    const values = try s.get_values(std.testing.allocator);
    defer std.testing.allocator.free(values);

    try std.testing.expectEqual(@as(usize, 2), values.len);
    try std.testing.expect(std.mem.eql(u8, "a", values[0]));
    try std.testing.expect(std.mem.eql(u8, "b", values[1]));
    try std.testing.expect(!(try s.is_empty(std.testing.allocator)));
}

test "literals strings set operations" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const s1 = fabll.Node.bind_typegraph(Strings, &tg).create_instance(&g).setup_from_values(&.{ "a", "b" });
    const s2 = fabll.Node.bind_typegraph(Strings, &tg).create_instance(&g).setup_from_values(&.{ "b", "c" });

    const inter = try s1.op_intersect_intervals(s2, std.testing.allocator);
    const inter_vals = try inter.get_values(std.testing.allocator);
    defer std.testing.allocator.free(inter_vals);

    try std.testing.expectEqual(@as(usize, 1), inter_vals.len);
    try std.testing.expect(std.mem.eql(u8, "b", inter_vals[0]));

    const sym = try s1.op_symmetric_difference_intervals(s2, std.testing.allocator);
    const sym_vals = try sym.get_values(std.testing.allocator);
    defer std.testing.allocator.free(sym_vals);
    try std.testing.expectEqual(@as(usize, 2), sym_vals.len);
}

test "literals numeric interval and set" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    var set = NumericSet.create_instance(&g, &tg);
    set = try set.setup_from_values(&.{
        .{ .min = 0.0, .max = 1.0 },
        .{ .min = 0.5, .max = 3.0 },
    }, std.testing.allocator);

    const intervals = try set.get_intervals(std.testing.allocator);
    defer std.testing.allocator.free(intervals);

    try std.testing.expectEqual(@as(usize, 1), intervals.len);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), intervals[0].min, 1e-9);
    try std.testing.expectApproxEqAbs(@as(f64, 3.0), intervals[0].max, 1e-9);
}

test "literals numbers api parity core" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    var n1 = Numbers.create_instance(&g, &tg);
    n1 = try n1.setup_from_min_max(0.0, 10.0, std.testing.allocator);
    try std.testing.expect(!(try n1.is_empty(std.testing.allocator)));
    try std.testing.expect(!(try n1.is_singleton(std.testing.allocator)));

    var n2 = Numbers.create_instance(&g, &tg);
    n2 = try n2.setup_from_singleton(5.0, std.testing.allocator);
    try std.testing.expect(try n2.is_singleton(std.testing.allocator));
    try std.testing.expectApproxEqAbs(@as(f64, 5.0), try n2.get_single(std.testing.allocator), 1e-9);

    try std.testing.expect(try n2.op_setic_is_subset_of(n1, std.testing.allocator));
}

test "literals numbers set operations" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    var n1 = Numbers.create_instance(&g, &tg);
    n1 = try n1.setup_from_min_max(0.0, 10.0, std.testing.allocator);

    var n2 = Numbers.create_instance(&g, &tg);
    n2 = try n2.setup_from_min_max(5.0, 20.0, std.testing.allocator);

    const inter = try n1.op_intersect_intervals(n2, std.testing.allocator);
    try std.testing.expectApproxEqAbs(@as(f64, 5.0), try inter.get_min_value(std.testing.allocator), 1e-9);
    try std.testing.expectApproxEqAbs(@as(f64, 10.0), try inter.get_max_value(std.testing.allocator), 1e-9);

    const unioned = try n1.op_union_intervals(n2, std.testing.allocator);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), try unioned.get_min_value(std.testing.allocator), 1e-9);
    try std.testing.expectApproxEqAbs(@as(f64, 20.0), try unioned.get_max_value(std.testing.allocator), 1e-9);
}

test "literals numbers extended api (non-unit)" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    var n = Numbers.create_instance(&g, &tg);
    n = try n.setup_from_center_rel(10.0, 0.1, std.testing.allocator);
    try std.testing.expectApproxEqAbs(@as(f64, 9.0), try n.get_min_value(std.testing.allocator), 1e-9);
    try std.testing.expectApproxEqAbs(@as(f64, 11.0), try n.get_max_value(std.testing.allocator), 1e-9);

    const abs = try n.op_abs(std.testing.allocator);
    try std.testing.expect(try abs.is_finite(std.testing.allocator));
    try std.testing.expect(!(try abs.is_unbounded(std.testing.allocator)));

    const rounded = try n.op_round(0, std.testing.allocator);
    try std.testing.expectApproxEqAbs(@as(f64, 9.0), try rounded.get_min_value(std.testing.allocator), 1e-9);

    var denom = Numbers.create_instance(&g, &tg);
    denom = try denom.setup_from_singleton(2.0, std.testing.allocator);
    const div = try Numbers.op_div_intervals(n, denom, std.testing.allocator);
    try std.testing.expectApproxEqAbs(@as(f64, 4.5), try div.get_min_value(std.testing.allocator), 1e-9);

    const ge = try n.op_ge(denom, std.testing.allocator);
    const ge_vals = try ge.get_values(std.testing.allocator);
    defer std.testing.allocator.free(ge_vals);
    try std.testing.expectEqual(@as(usize, 1), ge_vals.len);
    try std.testing.expect(ge_vals[0]);
}

test "literals counts api" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const c = fabll.Node.bind_typegraph(Counts, &tg).create_instance(&g).setup_from_values(&.{ 1, 2, 2, 3 });
    const values = try c.get_values(std.testing.allocator);
    defer std.testing.allocator.free(values);

    try std.testing.expectEqual(@as(usize, 3), values.len);
    try std.testing.expectEqual(@as(i64, 1), values[0]);
    try std.testing.expectEqual(@as(i64, 3), values[2]);
}

test "literals booleans api" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const b = Booleans.create_instance(&g, &tg).setup_from_values(&.{ true, false, true });
    const values = try b.get_values(std.testing.allocator);
    defer std.testing.allocator.free(values);

    try std.testing.expectEqual(@as(usize, 2), values.len);
    try std.testing.expect(values[0] == false);
    try std.testing.expect(values[1] == true);
}

test "literals enum api" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    var e = fabll.Node.bind_typegraph(AbstractEnums, &tg).create_instance(&g);
    e = e.setup_from_values(&.{
        .{ .name = "A", .value = "A" },
        .{ .name = "B", .value = "B" },
    });

    const values = try e.get_values(std.testing.allocator);
    defer std.testing.allocator.free(values);
    try std.testing.expectEqual(@as(usize, 2), values.len);
}

test "literals serialize deserialize parity (non-unit)" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const s = fabll.Node.bind_typegraph(Strings, &tg).create_instance(&g).setup_from_values(&.{ "x", "y" });
    const s_ser = try s.serialize(std.testing.allocator);
    defer std.testing.allocator.free(s_ser.data.values);
    const s2 = try Strings.deserialize(s_ser, &g, &tg);
    try std.testing.expect(try s.op_setic_equals(s2, std.testing.allocator));

    var n = Numbers.create_instance(&g, &tg);
    n = try n.setup_from_min_max(1.0, 2.0, std.testing.allocator);
    const n_ser = try n.serialize(std.testing.allocator);
    defer std.testing.allocator.free(n_ser.data.intervals);
    const n2 = try Numbers.deserialize(n_ser, &g, &tg, std.testing.allocator);
    try std.testing.expect(try n.op_setic_equals(n2, std.testing.allocator));

    const c = fabll.Node.bind_typegraph(Counts, &tg).create_instance(&g).setup_from_values(&.{ 1, 4 });
    const c_ser = try c.serialize(std.testing.allocator);
    defer std.testing.allocator.free(c_ser.data.values);
    const c2 = try Counts.deserialize(c_ser, &g, &tg);
    try std.testing.expect(try c.op_setic_equals(c2, std.testing.allocator));

    const b = Booleans.create_instance(&g, &tg).setup_from_values(&.{ true });
    const b_ser = try b.serialize(std.testing.allocator);
    defer std.testing.allocator.free(b_ser.data.values);
    const b2 = try Booleans.deserialize(b_ser, &g, &tg);
    try std.testing.expect(try b.op_setic_equals(b2, std.testing.allocator));
}
