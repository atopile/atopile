const std = @import("std");
const structure = @import("../../structure.zig");
const schematic = @import("../schematic.zig");
const pcb = @import("../pcb.zig");

const str = []const u8;

pub const Arc = struct {
    start: pcb.Xy,
    mid: pcb.Xy,
    end: pcb.Xy,
    width: f64,
    layer: str,
};

pub const Circle = struct {
    center: pcb.Xy,
    radius: f64,
    end: pcb.Xy = .{ .x = 0, .y = 0 },
    stroke: schematic.Stroke,
    fill: schematic.Fill,
};

pub const SymbolUnit = struct {
    name: str,
    polylines: []schematic.Polyline = &.{},
    circles: []Circle = &.{},
    rectangles: []schematic.Rect = &.{},
    arcs: []schematic.Arc = &.{},
    pins: []schematic.SymbolPin = &.{},

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .polylines = structure.SexpField{ .multidict = true, .sexp_name = "polyline" },
        .circles = structure.SexpField{ .multidict = true, .sexp_name = "circle" },
        .rectangles = structure.SexpField{ .multidict = true, .sexp_name = "rectangle" },
        .arcs = structure.SexpField{ .multidict = true, .sexp_name = "arc" },
        .pins = structure.SexpField{ .multidict = true, .sexp_name = "pin" },
    };
};

pub const SymbolLib = struct {
    version: i32,
    generator: []const u8,
    symbols: []SymbolUnit = &.{},
};

pub const SymbolFile = struct {
    kicad_sym: SymbolLib,

    const root_symbol = "kicad_sym";

    pub fn loads(allocator: std.mem.Allocator, in: structure.input) !SymbolFile {
        const kicad_sym = try structure.loads(SymbolLib, allocator, in, root_symbol);
        return SymbolFile{
            .kicad_sym = kicad_sym,
        };
    }

    pub fn dumps(self: SymbolFile, allocator: std.mem.Allocator, out: structure.output) !void {
        try structure.dumps(self.kicad_sym, allocator, root_symbol, out);
    }

    pub fn free(self: *SymbolFile, allocator: std.mem.Allocator) void {
        structure.free(SymbolLib, allocator, self.symbol);
    }
};
