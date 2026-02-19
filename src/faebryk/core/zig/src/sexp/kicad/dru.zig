const std = @import("std");
const compat = @import("compat");
const structure = @import("../structure.zig");
const ast = @import("../ast.zig");

const str = []const u8;
const SExp = structure.SExp;

fn list(comptime T: type) type {
    return compat.DoublyLinkedList(T);
}

// https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html#custom-design-rules

pub const E_severity = enum {
    @"error",
    warning,
    ignore,
    exclusion,
};

pub const E_constraint_type = enum {
    annular_width,
    assertion,
    bridged_mask,
    clearance,
    connection_width,
    courtyard_clearance,
    creepage,
    diff_pair_gap,
    diff_pair_uncoupled,
    disallow,
    edge_clearance,
    hole_clearance,
    hole_size,
    hole_to_hole,
    length,
    min_resolved_spokes,
    physical_clearance,
    physical_hole_clearance,
    silk_clearance,
    skew,
    solder_mask_expansion,
    solder_paste_abs_margin,
    solder_paste_rel_margin,
    text_height,
    text_thickness,
    thermal_relief_gap,
    thermal_spoke_width,
    track_angle,
    track_segment_length,
    track_width,
    via_count,
    via_dangling,
    via_diameter,
    zone_connection,
};

pub const E_zone_connection_type = enum {
    solid,
    thermal_reliefs,
    none,
};

pub const E_disallow_type = enum {
    track,
    via,
    through_via,
    blind_via,
    micro_via,
    buried_via,
    pad,
    zone,
    text,
    graphic,
    hole,
    footprint,
};

pub const Expression = struct {
    expression: str,

    pub const fields_meta = .{
        .expression = structure.SexpField{ .positional = true },
    };
};

pub const ValueWithUnit = struct {
    value: f64,
    unit: ?str = null,

    pub const fields_meta = .{
        .value = structure.SexpField{ .positional = true },
        .unit = structure.SexpField{ .positional = true, .symbol = true },
    };

    // Custom encode: concatenate value and unit into a single symbol (e.g., "0.4mm")
    pub fn encode(self: ValueWithUnit, allocator: std.mem.Allocator) structure.EncodeError!SExp {
        var buf: [32]u8 = undefined;
        const rounded = std.math.round(self.value * 10e6) / 10e6;
        const val_str = std.fmt.bufPrint(&buf, "{d}", .{rounded}) catch return error.OutOfMemory;
        if (self.unit) |unit| {
            const combined = std.fmt.allocPrint(allocator, "{s}{s}", .{ val_str, unit }) catch return error.OutOfMemory;
            return SExp{ .value = .{ .symbol = combined }, .location = null };
        } else {
            const duped = std.fmt.allocPrint(allocator, "{s}", .{val_str}) catch return error.OutOfMemory;
            return SExp{ .value = .{ .number = duped }, .location = null };
        }
    }
};

// Decode a ValueWithUnit from the items after the key symbol (e.g., from [0.4mm] or [0.4, mm] or [45])
fn decodeValueWithUnit(allocator: std.mem.Allocator, items: []const SExp) structure.DecodeError!ValueWithUnit {
    if (items.len == 0) return error.MissingField;

    // The tokenizer splits "0.4mm" into [0.4, mm] (two tokens),
    // but unitless values like "45" come as a single number token.
    // Try to decode using the standard struct decoder which handles positional fields.
    // We need to wrap items back into a list for the struct decoder.
    const list_items = allocator.alloc(SExp, items.len) catch return error.OutOfMemory;
    @memcpy(list_items, items);
    const wrapper = SExp{ .value = .{ .list = list_items }, .location = null };
    return try structure.decode(ValueWithUnit, allocator, wrapper);
}

pub const Constraint = struct {
    constraint_type: E_constraint_type,
    // Standard min/opt/max (most constraints)
    min: ?ValueWithUnit = null,
    opt: ?ValueWithUnit = null,
    max: ?ValueWithUnit = null,
    // Disallow-specific: positional list of item types
    disallow_types: []const E_disallow_type = &.{},
    // Zone connection-specific: positional enum
    zone_connection_type: ?E_zone_connection_type = null,
    // Assertion-specific: positional quoted expression
    assertion_expr: ?str = null,
    // Min resolved spokes: bare positional integer
    spokes_count: ?i32 = null,
    // Skew option flag
    within_diff_pairs: bool = false,

    pub fn decode(allocator: std.mem.Allocator, sexp: SExp) structure.DecodeError!Constraint {
        const items = ast.getList(sexp) orelse return error.UnexpectedType;
        if (items.len < 1) return error.MissingField;

        // First positional: skip lists to find constraint_type symbol
        var idx: usize = 0;
        while (idx < items.len and ast.isList(items[idx])) idx += 1;
        if (idx >= items.len) return error.MissingField;

        const ct_sym = ast.getSymbol(items[idx]) orelse return error.UnexpectedType;
        const constraint_type = std.meta.stringToEnum(E_constraint_type, ct_sym) orelse return error.InvalidValue;
        idx += 1;

        var result = Constraint{ .constraint_type = constraint_type };

        switch (constraint_type) {
            .disallow => {
                // Remaining positional symbols are disallow item types
                var types = std.array_list.Managed(E_disallow_type).init(allocator);
                while (idx < items.len) : (idx += 1) {
                    if (ast.isList(items[idx])) continue;
                    const sym = ast.getSymbol(items[idx]) orelse continue;
                    const dt = std.meta.stringToEnum(E_disallow_type, sym) orelse return error.InvalidValue;
                    types.append(dt) catch return error.OutOfMemory;
                }
                result.disallow_types = types.toOwnedSlice() catch return error.OutOfMemory;
            },
            .zone_connection => {
                // One positional symbol: zone connection type
                while (idx < items.len and ast.isList(items[idx])) idx += 1;
                if (idx < items.len) {
                    const sym = ast.getSymbol(items[idx]) orelse return error.UnexpectedType;
                    result.zone_connection_type = std.meta.stringToEnum(E_zone_connection_type, sym) orelse return error.InvalidValue;
                }
            },
            .assertion => {
                // One positional quoted string
                while (idx < items.len and ast.isList(items[idx])) idx += 1;
                if (idx < items.len) {
                    switch (items[idx].value) {
                        .string => |s| {
                            result.assertion_expr = (allocator.alloc(u8, s.len) catch return error.OutOfMemory);
                            @memcpy(@constCast(result.assertion_expr.?), s);
                        },
                        else => return error.UnexpectedType,
                    }
                }
            },
            .min_resolved_spokes => {
                // One positional bare integer
                while (idx < items.len and ast.isList(items[idx])) idx += 1;
                if (idx < items.len) {
                    const num_str = switch (items[idx].value) {
                        .number => |n| n,
                        else => return error.UnexpectedType,
                    };
                    result.spokes_count = std.fmt.parseInt(i32, num_str, 10) catch return error.InvalidValue;
                }
            },
            .via_dangling, .bridged_mask => {
                // Parameterless — nothing more to parse
            },
            else => {
                // Standard min/opt/max pattern + optional within_diff_pairs
                var i: usize = idx;
                while (i < items.len) : (i += 1) {
                    if (!ast.isList(items[i])) {
                        // Check for within_diff_pairs bare symbol
                        if (ast.getSymbol(items[i])) |sym| {
                            if (std.mem.eql(u8, sym, "within_diff_pairs")) {
                                result.within_diff_pairs = true;
                            }
                        }
                        continue;
                    }
                    const kv_items = ast.getList(items[i]).?;
                    if (kv_items.len < 1) continue;
                    const key = ast.getSymbol(kv_items[0]) orelse continue;
                    if (std.mem.eql(u8, key, "min")) {
                        result.min = try decodeValueWithUnit(allocator, kv_items[1..]);
                    } else if (std.mem.eql(u8, key, "opt")) {
                        result.opt = try decodeValueWithUnit(allocator, kv_items[1..]);
                    } else if (std.mem.eql(u8, key, "max")) {
                        result.max = try decodeValueWithUnit(allocator, kv_items[1..]);
                    } else if (std.mem.eql(u8, key, "within_diff_pairs")) {
                        result.within_diff_pairs = true;
                    }
                }
            },
        }

        return result;
    }

    pub fn encode(self: Constraint, allocator: std.mem.Allocator) structure.EncodeError!SExp {
        var items = std.array_list.Managed(SExp).init(allocator);

        // First: constraint_type as symbol
        inline for (std.meta.fields(E_constraint_type)) |field| {
            if (@intFromEnum(self.constraint_type) == field.value) {
                items.append(SExp{ .value = .{ .symbol = field.name }, .location = null }) catch return error.OutOfMemory;
            }
        }

        switch (self.constraint_type) {
            .disallow => {
                for (self.disallow_types) |dt| {
                    inline for (std.meta.fields(E_disallow_type)) |field| {
                        if (@intFromEnum(dt) == field.value) {
                            items.append(SExp{ .value = .{ .symbol = field.name }, .location = null }) catch return error.OutOfMemory;
                        }
                    }
                }
            },
            .zone_connection => {
                if (self.zone_connection_type) |zct| {
                    inline for (std.meta.fields(E_zone_connection_type)) |field| {
                        if (@intFromEnum(zct) == field.value) {
                            items.append(SExp{ .value = .{ .symbol = field.name }, .location = null }) catch return error.OutOfMemory;
                        }
                    }
                }
            },
            .assertion => {
                if (self.assertion_expr) |expr| {
                    items.append(SExp{ .value = .{ .string = expr }, .location = null }) catch return error.OutOfMemory;
                }
            },
            .min_resolved_spokes => {
                if (self.spokes_count) |count| {
                    var buf: [20]u8 = undefined;
                    const num_str = std.fmt.bufPrint(&buf, "{d}", .{count}) catch return error.OutOfMemory;
                    const duped = allocator.alloc(u8, num_str.len) catch return error.OutOfMemory;
                    @memcpy(duped, num_str);
                    items.append(SExp{ .value = .{ .number = duped }, .location = null }) catch return error.OutOfMemory;
                }
            },
            .via_dangling, .bridged_mask => {
                // Parameterless — nothing to encode
            },
            else => {
                // Standard min/opt/max
                if (self.min) |min_val| {
                    const encoded = try ValueWithUnit.encode(min_val, allocator);
                    var kv = allocator.alloc(SExp, 2) catch return error.OutOfMemory;
                    kv[0] = SExp{ .value = .{ .symbol = "min" }, .location = null };
                    kv[1] = encoded;
                    items.append(SExp{ .value = .{ .list = kv }, .location = null }) catch return error.OutOfMemory;
                }
                if (self.opt) |opt_val| {
                    const encoded = try ValueWithUnit.encode(opt_val, allocator);
                    var kv = allocator.alloc(SExp, 2) catch return error.OutOfMemory;
                    kv[0] = SExp{ .value = .{ .symbol = "opt" }, .location = null };
                    kv[1] = encoded;
                    items.append(SExp{ .value = .{ .list = kv }, .location = null }) catch return error.OutOfMemory;
                }
                if (self.max) |max_val| {
                    const encoded = try ValueWithUnit.encode(max_val, allocator);
                    var kv = allocator.alloc(SExp, 2) catch return error.OutOfMemory;
                    kv[0] = SExp{ .value = .{ .symbol = "max" }, .location = null };
                    kv[1] = encoded;
                    items.append(SExp{ .value = .{ .list = kv }, .location = null }) catch return error.OutOfMemory;
                }
                if (self.within_diff_pairs) {
                    var kv = allocator.alloc(SExp, 1) catch return error.OutOfMemory;
                    kv[0] = SExp{ .value = .{ .symbol = "within_diff_pairs" }, .location = null };
                    items.append(SExp{ .value = .{ .list = kv }, .location = null }) catch return error.OutOfMemory;
                }
            },
        }

        const out = items.toOwnedSlice() catch return error.OutOfMemory;
        return SExp{ .value = .{ .list = out }, .location = null };
    }
};

pub const Rule = struct {
    name: str,
    severity: ?E_severity = null,
    layer: ?str = null,
    condition: ?Expression = null,
    constraints: list(Constraint) = .{},

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .constraints = structure.SexpField{ .multidict = true, .sexp_name = "constraint" },
    };
};

pub const KicadDru = struct {
    version: i32 = 1,
    rules: list(Rule) = .{},

    pub const fields_meta = .{
        .rules = structure.SexpField{ .multidict = true, .sexp_name = "rule" },
    };
};

pub const DruFile = struct {
    kicad_dru: KicadDru,

    pub fn loads(allocator: std.mem.Allocator, in: structure.input) !DruFile {
        const dru = try structure.loadsFlat(KicadDru, allocator, in);
        return DruFile{
            .kicad_dru = dru,
        };
    }

    pub fn dumps(self: DruFile, allocator: std.mem.Allocator, out: structure.output) !void {
        try structure.dumpsFlat(self.kicad_dru, allocator, out);
    }

    pub fn free(self: *DruFile, allocator: std.mem.Allocator) void {
        structure.free(KicadDru, allocator, self.kicad_dru);
    }
};
