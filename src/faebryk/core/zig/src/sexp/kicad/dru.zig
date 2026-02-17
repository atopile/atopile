const std = @import("std");
const compat = @import("compat");
const structure = @import("../structure.zig");

const str = []const u8;

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
    clearance,
    connection_width,
    courtyard_clearance,
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
    text_height,
    text_thickness,
    thermal_relief_gap,
    thermal_spoke_width,
    track_width,
    via_count,
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
    unit: str,

    pub const fields_meta = .{
        .value = structure.SexpField{ .positional = true },
        .unit = structure.SexpField{ .positional = true, .symbol = true },
    };

    // Custom encode: concatenate value and unit into a single symbol (e.g., "0.4mm")
    pub fn encode(self: ValueWithUnit, allocator: std.mem.Allocator) structure.EncodeError!structure.SExp {
        var buf: [32]u8 = undefined;
        const rounded = std.math.round(self.value * 10e6) / 10e6;
        const val_str = std.fmt.bufPrint(&buf, "{d}", .{rounded}) catch return error.OutOfMemory;
        const combined = std.fmt.allocPrint(allocator, "{s}{s}", .{ val_str, self.unit }) catch return error.OutOfMemory;
        return structure.SExp{ .value = .{ .symbol = combined }, .location = null };
    }
};

pub const Constraint = struct {
    constraint_type: E_constraint_type,
    min: ?ValueWithUnit = null,
    opt: ?ValueWithUnit = null,
    max: ?ValueWithUnit = null,

    pub const fields_meta = .{
        .constraint_type = structure.SexpField{ .positional = true },
    };
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
