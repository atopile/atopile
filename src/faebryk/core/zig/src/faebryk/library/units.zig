const std = @import("std");
const graph_mod = @import("graph");
const graph = graph_mod.graph;
const faebryk = @import("faebryk");
const fabll = faebryk.fabll;
const is_trait = fabll.is_trait;
const collections = @import("collections.zig");
const str = []const u8;

pub const Error = error{
    UnitsNotCommensurable,
    UnitExpressionWithOffset,
    UnitNotFound,
};

pub const BasisVector = struct {
    ampere: i64 = 0,
    second: i64 = 0,
    meter: i64 = 0,
    kilogram: i64 = 0,
    kelvin: i64 = 0,
    mole: i64 = 0,
    candela: i64 = 0,
    radian: i64 = 0,
    steradian: i64 = 0,
    bit: i64 = 0,

    pub fn add(self: @This(), other: @This()) @This() {
        return .{
            .ampere = self.ampere + other.ampere,
            .second = self.second + other.second,
            .meter = self.meter + other.meter,
            .kilogram = self.kilogram + other.kilogram,
            .kelvin = self.kelvin + other.kelvin,
            .mole = self.mole + other.mole,
            .candela = self.candela + other.candela,
            .radian = self.radian + other.radian,
            .steradian = self.steradian + other.steradian,
            .bit = self.bit + other.bit,
        };
    }

    pub fn subtract(self: @This(), other: @This()) @This() {
        return .{
            .ampere = self.ampere - other.ampere,
            .second = self.second - other.second,
            .meter = self.meter - other.meter,
            .kilogram = self.kilogram - other.kilogram,
            .kelvin = self.kelvin - other.kelvin,
            .mole = self.mole - other.mole,
            .candela = self.candela - other.candela,
            .radian = self.radian - other.radian,
            .steradian = self.steradian - other.steradian,
            .bit = self.bit - other.bit,
        };
    }

    pub fn scalar_multiply(self: @This(), scalar: i64) @This() {
        return .{
            .ampere = self.ampere * scalar,
            .second = self.second * scalar,
            .meter = self.meter * scalar,
            .kilogram = self.kilogram * scalar,
            .kelvin = self.kelvin * scalar,
            .mole = self.mole * scalar,
            .candela = self.candela * scalar,
            .radian = self.radian * scalar,
            .steradian = self.steradian * scalar,
            .bit = self.bit * scalar,
        };
    }
};

pub const ORIGIN = BasisVector{};
pub const DIMENSIONLESS_SYMBOL = "";

fn accurate_div(m1: f64, m2: f64) f64 {
    var res = m1 / m2;
    if (@abs(res) > 0.0) {
        const log_res = std.math.log10(@abs(res));
        if (std.math.approxEqAbs(f64, log_res, @round(log_res), 1e-12)) {
            const sign: f64 = if (res > 0) 1.0 else -1.0;
            res = std.math.pow(f64, @as(f64, 10.0), @as(f64, @round(log_res))) * sign;
        }
    }
    return res;
}

pub const UnitInfo = struct {
    basis_vector: BasisVector,
    multiplier: f64,
    offset: f64,

    pub fn op_power(self: @This(), exponent: i64) @This() {
        return .{
            .basis_vector = self.basis_vector.scalar_multiply(exponent),
            .multiplier = std.math.pow(f64, self.multiplier, @as(f64, @floatFromInt(exponent))),
            .offset = self.offset,
        };
    }

    pub fn op_multiply(self: @This(), other: @This()) Error!@This() {
        if (self.offset != 0.0 or other.offset != 0.0) return Error.UnitExpressionWithOffset;
        return .{
            .basis_vector = self.basis_vector.add(other.basis_vector),
            .multiplier = self.multiplier * other.multiplier,
            .offset = self.offset + other.offset,
        };
    }

    pub fn is_commensurable_with(self: @This(), other: @This()) bool {
        return std.meta.eql(self.basis_vector, other.basis_vector);
    }
};

pub const UnitSerialized = struct {
    symbol: str,
    basis_vector: BasisVector,
    multiplier: f64,
    offset: f64,
};

pub const IsUnit = struct {
    node: fabll.Node,

    pub const Attributes = struct {
        basis_p0: i64,
        basis_p1: i64,
        basis_p2: i64,
        multiplier: f64,
        offset: f64,
    };

    const PackedBasis = struct {
        p0: i64,
        p1: i64,
        p2: i64,
    };

    fn i16_bits(x: i64) u16 {
        const x16: i16 = @intCast(x);
        return @bitCast(x16);
    }

    fn from_i16_bits(x: u16) i64 {
        const signed: i16 = @bitCast(x);
        return @as(i64, signed);
    }

    fn pack4(a: i64, b: i64, c: i64, d: i64) i64 {
        const raw: u64 = (@as(u64, i16_bits(a))) |
            (@as(u64, i16_bits(b)) << 16) |
            (@as(u64, i16_bits(c)) << 32) |
            (@as(u64, i16_bits(d)) << 48);
        return @bitCast(raw);
    }

    fn unpack4(word: i64) struct { i64, i64, i64, i64 } {
        const raw: u64 = @bitCast(word);
        return .{
            from_i16_bits(@as(u16, @truncate(raw))),
            from_i16_bits(@as(u16, @truncate(raw >> 16))),
            from_i16_bits(@as(u16, @truncate(raw >> 32))),
            from_i16_bits(@as(u16, @truncate(raw >> 48))),
        };
    }

    fn pack_basis(vector: BasisVector) PackedBasis {
        return .{
            .p0 = pack4(vector.ampere, vector.second, vector.meter, vector.kilogram),
            .p1 = pack4(vector.kelvin, vector.mole, vector.candela, vector.radian),
            .p2 = pack4(vector.steradian, vector.bit, 0, 0),
        };
    }

    fn unpack_basis(packed_basis: PackedBasis) BasisVector {
        const p0 = unpack4(packed_basis.p0);
        const p1 = unpack4(packed_basis.p1);
        const p2 = unpack4(packed_basis.p2);
        return .{
            .ampere = p0[0],
            .second = p0[1],
            .meter = p0[2],
            .kilogram = p0[3],
            .kelvin = p1[0],
            .mole = p1[1],
            .candela = p1[2],
            .radian = p1[3],
            .steradian = p2[0],
            .bit = p2[1],
        };
    }

    fn attrs_from_info(info: UnitInfo) Attributes {
        const packed_basis = pack_basis(info.basis_vector);
        return .{
            .basis_p0 = packed_basis.p0,
            .basis_p1 = packed_basis.p1,
            .basis_p2 = packed_basis.p2,
            .multiplier = info.multiplier,
            .offset = info.offset,
        };
    }

    pub fn MakeChild(comptime info: UnitInfo) type {
        return fabll.MakeChildWithTypedAttrs(@This(), attrs_from_info(info));
    }

    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, symbol: str, info: UnitInfo) @This() {
        const out = fabll.Node.bind_typegraph(@This(), tg).create_instance_with_attrs(g, attrs_from_info(info));
        out.node.instance.node.put("unit_symbol", .{ .String = symbol });
        return out;
    }

    pub fn get_info(self: @This()) UnitInfo {
        const attrs = fabll.get_typed_attributes(self);
        return .{
            .basis_vector = unpack_basis(.{
                .p0 = attrs.basis_p0,
                .p1 = attrs.basis_p1,
                .p2 = attrs.basis_p2,
            }),
            .multiplier = attrs.multiplier,
            .offset = attrs.offset,
        };
    }

    pub fn get_symbol(self: @This()) str {
        if (self.node.instance.node.get("unit_symbol")) |lit| {
            return lit.String;
        }
        if (faebryk.composition.EdgeComposition.get_parent_node_of(self.node.instance)) |owner| {
            if (owner.node.get("unit_symbol")) |lit| {
                return lit.String;
            }
        }
        return "";
    }

    pub fn serialize(self: @This()) UnitSerialized {
        const info = self.get_info();
        return .{
            .symbol = self.get_symbol(),
            .basis_vector = info.basis_vector,
            .multiplier = info.multiplier,
            .offset = info.offset,
        };
    }

    pub fn deserialize(data: UnitSerialized, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() {
        return create_instance(g, tg, data.symbol, .{
            .basis_vector = data.basis_vector,
            .multiplier = data.multiplier,
            .offset = data.offset,
        });
    }
};

pub const is_unit = IsUnit;

pub const has_unit = struct {
    node: fabll.Node,
    _is_trait: is_trait.MakeChild(),
    unit_ptr: collections.PointerOf(is_unit).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn setup(self: @This(), unit: is_unit) @This() {
        self.unit_ptr.get().point(unit);
        return self;
    }

    pub fn try_get_is_unit(self: @This()) ?is_unit {
        return self.unit_ptr.get().try_deref();
    }

    pub fn get_is_unit(self: @This()) is_unit {
        return self.unit_ptr.get().deref();
    }
};

pub const has_display_unit = struct {
    node: fabll.Node,
    _is_trait: is_trait.MakeChild(),
    unit_ptr: collections.PointerOf(is_unit).MakeChild(),

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn setup(self: @This(), unit: is_unit) @This() {
        self.unit_ptr.get().point(unit);
        return self;
    }

    pub fn try_get_is_unit(self: @This()) ?is_unit {
        return self.unit_ptr.get().try_deref();
    }

    pub fn get_is_unit(self: @This()) is_unit {
        return self.unit_ptr.get().deref();
    }
};

pub fn to_is_unit(unit_node: anytype) is_unit {
    const T = @TypeOf(unit_node);
    if (T == is_unit) return unit_node;
    if (comptime @hasField(T, "is_unit")) {
        return unit_node.is_unit.get();
    }
    @compileError("expected is_unit or node type with `is_unit` child field");
}

pub fn info_of(unit: ?is_unit) UnitInfo {
    if (unit) |u| return u.get_info();
    return .{
        .basis_vector = ORIGIN,
        .multiplier = 1.0,
        .offset = 0.0,
    };
}

pub fn symbol_of(unit: ?is_unit) str {
    if (unit) |u| return u.get_symbol();
    return DIMENSIONLESS_SYMBOL;
}

pub fn is_commensurable_with(lhs: ?is_unit, rhs: ?is_unit) bool {
    return info_of(lhs).is_commensurable_with(info_of(rhs));
}

pub fn is_dimensionless(unit: ?is_unit) bool {
    return std.meta.eql(info_of(unit).basis_vector, ORIGIN);
}

pub fn get_conversion_to(from: ?is_unit, to: ?is_unit) Error!struct { scale: f64, offset: f64 } {
    if (!is_commensurable_with(from, to)) return Error.UnitsNotCommensurable;
    const from_info = info_of(from);
    const to_info = info_of(to);
    return .{
        .scale = accurate_div(from_info.multiplier, to_info.multiplier),
        .offset = from_info.offset - to_info.offset,
    };
}

pub fn convert_value(value: f64, from: ?is_unit, to: ?is_unit) Error!f64 {
    if (!is_commensurable_with(from, to)) return Error.UnitsNotCommensurable;
    const conv = try get_conversion_to(from, to);
    return value * conv.scale + conv.offset;
}

pub fn new(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, vector: BasisVector, multiplier: f64, offset: f64, symbol: str) ?is_unit {
    if (std.meta.eql(vector, ORIGIN) and multiplier == 1.0 and offset == 0.0) return null;
    return is_unit.create_instance(g, tg, symbol, .{
        .basis_vector = vector,
        .multiplier = multiplier,
        .offset = offset,
    });
}

pub fn op_multiply(lhs: ?is_unit, rhs: ?is_unit, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) Error!?is_unit {
    const out = try info_of(lhs).op_multiply(info_of(rhs));
    return new(g, tg, out.basis_vector, out.multiplier, out.offset, "");
}

pub fn op_divide(lhs: ?is_unit, rhs: ?is_unit, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) Error!?is_unit {
    const rhs_info = info_of(rhs);
    if (rhs_info.offset != 0.0) return Error.UnitExpressionWithOffset;
    return op_multiply(lhs, try op_invert(rhs, g, tg), g, tg);
}

pub fn op_invert(unit: ?is_unit, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) Error!?is_unit {
    const info = info_of(unit);
    if (info.offset != 0.0) return Error.UnitExpressionWithOffset;
    return new(g, tg, info.basis_vector.scalar_multiply(-1), 1.0 / info.multiplier, 0.0, "");
}

pub fn op_power(unit: ?is_unit, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph, exponent: i64) ?is_unit {
    const out = info_of(unit).op_power(exponent);
    return new(g, tg, out.basis_vector, out.multiplier, out.offset, "");
}

pub fn decode_symbol(symbol: str, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) Error!?is_unit {
    if (std.mem.eql(u8, symbol, "")) return null;
    if (std.mem.eql(u8, symbol, "m")) return to_is_unit(Meter.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "s")) return to_is_unit(Second.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "h")) return to_is_unit(Hour.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "A")) return to_is_unit(Ampere.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "K")) return to_is_unit(Kelvin.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "°C")) return to_is_unit(DegreeCelsius.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "V")) return to_is_unit(Volt.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "mV")) return to_is_unit(MilliVolt.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "Ω")) return to_is_unit(Ohm.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "rad")) return to_is_unit(Radian.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "sr")) return to_is_unit(Steradian.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "bit")) return to_is_unit(Bit.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "%")) return to_is_unit(Percent.create_instance(g, tg));
    if (std.mem.eql(u8, symbol, "ppm")) return to_is_unit(Ppm.create_instance(g, tg));
    return Error.UnitNotFound;
}

fn symbol_for_basis_vector(vector: BasisVector, multiplier: f64) ?str {
    const info = UnitInfo{ .basis_vector = vector, .multiplier = multiplier, .offset = 0.0 };
    if (std.meta.eql(info, UnitInfo{ .basis_vector = .{ .meter = 1 }, .multiplier = 1.0, .offset = 0.0 })) return "m";
    if (std.meta.eql(info, UnitInfo{ .basis_vector = .{ .second = 1 }, .multiplier = 1.0, .offset = 0.0 })) return "s";
    if (std.meta.eql(info, UnitInfo{ .basis_vector = .{ .second = -1 }, .multiplier = 1.0, .offset = 0.0 })) return "Hz";
    if (std.meta.eql(info, UnitInfo{ .basis_vector = .{ .ampere = 1 }, .multiplier = 1.0, .offset = 0.0 })) return "A";
    if (std.meta.eql(info, UnitInfo{ .basis_vector = .{ .kelvin = 1 }, .multiplier = 1.0, .offset = 0.0 })) return "K";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -3, .ampere = -1 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "V";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -3, .ampere = -2 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "Ω";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -3 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "W";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = -1, .meter = -2, .second = 4, .ampere = 2 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "F";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .meter = 1, .second = -2 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "N";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .meter = -1, .second = -2 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "Pa";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -2 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "J";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .ampere = 1, .second = 1 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "C";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = -1, .meter = -2, .second = 3, .ampere = 2 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "S";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -2, .ampere = -1 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "Wb";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .second = -2, .ampere = -1 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "T";
    if (std.meta.eql(info, UnitInfo{
        .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -2, .ampere = -2 },
        .multiplier = 1.0,
        .offset = 0.0,
    })) return "H";
    if (std.meta.eql(info, UnitInfo{ .basis_vector = .{ .radian = 1 }, .multiplier = 1.0, .offset = 0.0 })) return "rad";
    if (std.meta.eql(info, UnitInfo{ .basis_vector = .{ .steradian = 1 }, .multiplier = 1.0, .offset = 0.0 })) return "sr";
    if (std.meta.eql(info, UnitInfo{ .basis_vector = .{ .bit = 1 }, .multiplier = 1.0, .offset = 0.0 })) return "bit";
    return null;
}

fn to_superscript_alloc(allocator: std.mem.Allocator, n: i64) ![]u8 {
    var buf: [32]u8 = undefined;
    const plain = try std.fmt.bufPrint(&buf, "{d}", .{n});
    var out = std.ArrayList(u8).init(allocator);
    errdefer out.deinit();
    for (plain) |ch| {
        const mapped: str = switch (ch) {
            '-' => "⁻",
            '0' => "⁰",
            '1' => "¹",
            '2' => "²",
            '3' => "³",
            '4' => "⁴",
            '5' => "⁵",
            '6' => "⁶",
            '7' => "⁷",
            '8' => "⁸",
            '9' => "⁹",
            else => "",
        };
        try out.appendSlice(mapped);
    }
    return out.toOwnedSlice();
}

fn format_number_alloc(allocator: std.mem.Allocator, value: f64) ![]u8 {
    if (value == @trunc(value)) {
        var int_buf: [64]u8 = undefined;
        const int_s = try std.fmt.bufPrint(&int_buf, "{d}", .{@as(i64, @intFromFloat(value))});
        return allocator.dupe(u8, int_s);
    }
    var float_buf: [64]u8 = undefined;
    const float_s = try std.fmt.bufPrint(&float_buf, "{d}", .{value});
    return allocator.dupe(u8, float_s);
}

fn append_vector_term(out: *std.ArrayList(u8), allocator: std.mem.Allocator, symbol: str, exp: i64) !void {
    if (exp == 0) return;
    if (out.items.len > 0) try out.appendSlice("·");
    try out.appendSlice(symbol);
    if (exp != 1) {
        const sup = try to_superscript_alloc(allocator, exp);
        defer allocator.free(sup);
        try out.appendSlice(sup);
    }
}

pub fn compact_repr(unit: ?is_unit, allocator: std.mem.Allocator) ![]u8 {
    if (unit == null) return allocator.dupe(u8, "");

    const u = unit.?;
    const symbol = u.get_symbol();
    if (symbol.len > 0) return allocator.dupe(u8, symbol);

    const info = info_of(unit);
    const vector = info.basis_vector;
    const multiplier = info.multiplier;
    const offset = info.offset;

    if (offset == 0.0 and multiplier > 0.0) {
        const log_mult = if (multiplier == 0.0) 0.0 else std.math.log10(multiplier);
        if (std.math.approxEqAbs(f64, log_mult, @round(log_mult), 1e-9)) {
            const exp_mult: i64 = @intFromFloat(@round(log_mult));
            if (symbol_for_basis_vector(vector, 1.0)) |base| {
                if (exp_mult == -12) return std.fmt.allocPrint(allocator, "p{s}", .{base});
                if (exp_mult == -9) return std.fmt.allocPrint(allocator, "n{s}", .{base});
                if (exp_mult == -6) return std.fmt.allocPrint(allocator, "µ{s}", .{base});
                if (exp_mult == -3) return std.fmt.allocPrint(allocator, "m{s}", .{base});
                if (exp_mult == 0) return allocator.dupe(u8, base);
                if (exp_mult == 3) return std.fmt.allocPrint(allocator, "k{s}", .{base});
                if (exp_mult == 6) return std.fmt.allocPrint(allocator, "M{s}", .{base});
                if (exp_mult == 9) return std.fmt.allocPrint(allocator, "G{s}", .{base});
                if (exp_mult == 12) return std.fmt.allocPrint(allocator, "T{s}", .{base});
                return std.fmt.allocPrint(allocator, "{d}{s}", .{ multiplier, base });
            }
        }
        if (symbol_for_basis_vector(vector, multiplier)) |exact| {
            return allocator.dupe(u8, exact);
        }
    }

    var out = std.ArrayList(u8).init(allocator);
    errdefer out.deinit();
    try append_vector_term(&out, allocator, "A", vector.ampere);
    try append_vector_term(&out, allocator, "s", vector.second);
    try append_vector_term(&out, allocator, "m", vector.meter);
    try append_vector_term(&out, allocator, "kg", vector.kilogram);
    try append_vector_term(&out, allocator, "K", vector.kelvin);
    try append_vector_term(&out, allocator, "mol", vector.mole);
    try append_vector_term(&out, allocator, "cd", vector.candela);
    try append_vector_term(&out, allocator, "rad", vector.radian);
    try append_vector_term(&out, allocator, "sr", vector.steradian);
    try append_vector_term(&out, allocator, "bit", vector.bit);

    var result = if (out.items.len > 0) try out.toOwnedSlice() else try allocator.dupe(u8, "");
    if (multiplier != 1.0) {
        const m = try format_number_alloc(allocator, multiplier);
        defer allocator.free(m);
        defer allocator.free(result);
        result = if (result.len > 0)
            try std.fmt.allocPrint(allocator, "{s}×{s}", .{ m, result })
        else
            try allocator.dupe(u8, m);
    }
    if (offset != 0.0) {
        const o = try format_number_alloc(allocator, offset);
        defer allocator.free(o);
        defer allocator.free(result);
        return std.fmt.allocPrint(allocator, "({s}+{s})", .{ result, o });
    }
    return result;
}

fn create_concrete_unit_instance(comptime T: type, comptime symbol: str, g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) T {
    const out = fabll.Node.bind_typegraph(T, tg).create_instance(g);
    out.node.instance.node.put("unit_symbol", .{ .String = symbol });
    out.is_unit.get().node.instance.node.put("unit_symbol", .{ .String = symbol });
    return out;
}

pub const Meter = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .meter = 1 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "m", g, tg); }
};
pub const Second = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .second = 1 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "s", g, tg); }
};
pub const Hour = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .second = 1 }, .multiplier = 3600.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "h", g, tg); }
};
pub const Ampere = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .ampere = 1 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "A", g, tg); }
};
pub const Kelvin = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .kelvin = 1 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "K", g, tg); }
};
pub const DegreeCelsius = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .kelvin = 1 }, .multiplier = 1.0, .offset = 273.15 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "°C", g, tg); }
};
pub const Volt = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -3, .ampere = -1 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "V", g, tg); }
};
pub const MilliVolt = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -3, .ampere = -1 }, .multiplier = 1e-3, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "mV", g, tg); }
};
pub const Ohm = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .kilogram = 1, .meter = 2, .second = -3, .ampere = -2 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "Ω", g, tg); }
};
pub const Radian = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .radian = 1 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "rad", g, tg); }
};
pub const Steradian = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .steradian = 1 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "sr", g, tg); }
};
pub const Bit = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = .{ .bit = 1 }, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "bit", g, tg); }
};
pub const Percent = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = ORIGIN, .multiplier = 1e-2, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "%", g, tg); }
};
pub const Ppm = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = ORIGIN, .multiplier = 1e-6, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "ppm", g, tg); }
};
pub const Dimensionless = struct {
    node: fabll.Node,
    is_unit: IsUnit.MakeChild(.{ .basis_vector = ORIGIN, .multiplier = 1.0, .offset = 0.0 }),
    pub fn MakeChild() type { return fabll.Node.MakeChild(@This()); }
    pub fn create_instance(g: *graph.GraphView, tg: *faebryk.typegraph.TypeGraph) @This() { return create_concrete_unit_instance(@This(), "", g, tg); }
};

test "units basis vector arithmetic" {
    const a = BasisVector{ .meter = 1, .second = -2 };
    const b = BasisVector{ .meter = 2, .ampere = 1 };
    const add = a.add(b);
    try std.testing.expectEqual(@as(i64, 3), add.meter);
    try std.testing.expectEqual(@as(i64, -2), add.second);
    try std.testing.expectEqual(@as(i64, 1), add.ampere);
    const sub = add.subtract(b);
    try std.testing.expect(std.meta.eql(a, sub));
}

test "units concrete node types are distinct in typegraph" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    _ = Volt.create_instance(&g, &tg);
    _ = MilliVolt.create_instance(&g, &tg);

    const v_type = tg.get_type_by_name(@typeName(Volt)) orelse @panic("missing Volt type");
    const mv_type = tg.get_type_by_name(@typeName(MilliVolt)) orelse @panic("missing MilliVolt type");
    try std.testing.expect(!v_type.node.is_same(mv_type.node));
}

test "units conversion and commensurability" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const v = to_is_unit(Volt.create_instance(&g, &tg));
    const mv = to_is_unit(MilliVolt.create_instance(&g, &tg));
    try std.testing.expect(is_commensurable_with(v, mv));
    const converted = try convert_value(1000.0, mv, v);
    try std.testing.expectApproxEqAbs(@as(f64, 1.0), converted, 1e-9);
}

test "units symbol fidelity on trait node" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const v = to_is_unit(Volt.create_instance(&g, &tg));
    try std.testing.expect(std.mem.eql(u8, "V", v.get_symbol()));
}

test "units affine conversion" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const c = to_is_unit(DegreeCelsius.create_instance(&g, &tg));
    const k = to_is_unit(Kelvin.create_instance(&g, &tg));
    const kelvin = try convert_value(0.0, c, k);
    try std.testing.expectApproxEqAbs(@as(f64, 273.15), kelvin, 1e-9);
}

test "units expression multiply divide power" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const v = to_is_unit(Volt.create_instance(&g, &tg));
    const a = to_is_unit(Ampere.create_instance(&g, &tg));
    const product = try op_multiply(v, a, &g, &tg);
    try std.testing.expect(product != null);
    try std.testing.expectEqual(@as(i64, 1), info_of(product).basis_vector.kilogram);

    const inv = try op_invert(a, &g, &tg);
    try std.testing.expect(inv != null);

    const squared = op_power(v, &g, &tg, 2);
    try std.testing.expect(squared != null);
    try std.testing.expectEqual(@as(i64, -2), info_of(squared).basis_vector.ampere);
}

test "units decode symbol" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const v = try decode_symbol("V", &g, &tg);
    try std.testing.expect(v != null);
    try std.testing.expect(std.mem.eql(u8, "V", v.?.get_symbol()));
    const ppm = try decode_symbol("ppm", &g, &tg);
    try std.testing.expect(ppm != null);
    try std.testing.expect(std.mem.eql(u8, "ppm", ppm.?.get_symbol()));
    try std.testing.expect((try decode_symbol("", &g, &tg)) == null);
    try std.testing.expectError(Error.UnitNotFound, decode_symbol("not-a-unit", &g, &tg));
}

test "units compact repr" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const v = to_is_unit(Volt.create_instance(&g, &tg));
    const v_repr = try compact_repr(v, std.testing.allocator);
    defer std.testing.allocator.free(v_repr);
    try std.testing.expect(std.mem.eql(u8, "V", v_repr));

    const a = to_is_unit(Ampere.create_instance(&g, &tg));
    const div = try op_divide(v, a, &g, &tg);
    const div_repr = try compact_repr(div, std.testing.allocator);
    defer std.testing.allocator.free(div_repr);
    try std.testing.expect(std.mem.eql(u8, "Ω", div_repr));

    const mul = try op_multiply(v, a, &g, &tg);
    const mul_repr = try compact_repr(mul, std.testing.allocator);
    defer std.testing.allocator.free(mul_repr);
    try std.testing.expect(std.mem.eql(u8, "W", mul_repr));
}

test "units dimensionless scaled compatibility" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const percent = to_is_unit(Percent.create_instance(&g, &tg));
    const ppm = to_is_unit(Ppm.create_instance(&g, &tg));
    try std.testing.expect(is_commensurable_with(percent, ppm));
    const v = try convert_value(1.0, percent, ppm);
    try std.testing.expectApproxEqAbs(@as(f64, 10000.0), v, 1e-9);
}
