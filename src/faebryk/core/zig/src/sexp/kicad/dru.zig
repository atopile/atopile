const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

fn list(comptime T: type) type {
    return std.DoublyLinkedList(T);
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

pub const Constraint = struct {
    constraint_type: E_constraint_type,
    min: ?f64 = null,
    opt: ?f64 = null,
    max: ?f64 = null,

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

    const root_symbol = "kicad_dru";

    pub fn loads(allocator: std.mem.Allocator, in: structure.input) !DruFile {
        const dru = try structure.loads(KicadDru, allocator, in, root_symbol);
        return DruFile{
            .kicad_dru = dru,
        };
    }

    pub fn dumps(self: DruFile, allocator: std.mem.Allocator, out: structure.output) !void {
        try structure.dumps(self.kicad_dru, allocator, root_symbol, out);
    }

    pub fn free(self: *DruFile, allocator: std.mem.Allocator) void {
        structure.free(KicadDru, allocator, self.kicad_dru);
    }
};
