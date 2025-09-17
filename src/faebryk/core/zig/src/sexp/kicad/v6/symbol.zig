const std = @import("std");
const structure = @import("../../structure.zig");
const schematic = @import("../schematic.zig");
const pcb = @import("../pcb.zig");

const str = []const u8;

fn list(comptime T: type) type {
    return std.DoublyLinkedList(T);
}

pub const Circle = struct {
    center: pcb.Xy,
    radius: f64,
    stroke: schematic.Stroke,
    fill: schematic.Fill,
};

pub const SymbolUnit = struct {
    name: str,
    polylines: list(schematic.Polyline) = .{},
    circles: list(Circle) = .{},
    rectangles: list(schematic.Rect) = .{},
    arcs: list(schematic.Arc) = .{},
    pins: list(schematic.SymbolPin) = .{},

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .polylines = structure.SexpField{ .multidict = true, .sexp_name = "polyline" },
        .circles = structure.SexpField{ .multidict = true, .sexp_name = "circle" },
        .rectangles = structure.SexpField{ .multidict = true, .sexp_name = "rectangle" },
        .arcs = structure.SexpField{ .multidict = true, .sexp_name = "arc" },
        .pins = structure.SexpField{ .multidict = true, .sexp_name = "pin" },
    };
};

pub const Symbol = struct {
    name: str,
    power: bool = false,
    propertys: list(schematic.Property) = .{},
    pin_numbers: ?schematic.E_hide = null,
    pin_names: ?schematic.PinNames = null,
    in_bom: ?bool = null,
    on_board: ?bool = null,
    symbols: list(SymbolUnit) = .{},
    convert: ?i32 = null,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .propertys = structure.SexpField{ .multidict = true, .sexp_name = "property" },
        .symbols = structure.SexpField{ .multidict = true, .sexp_name = "symbol" },
        .power = structure.SexpField{ .boolean_encoding = .parantheses_symbol },
    };
};

pub const SymbolLib = struct {
    version: i32,
    generator: str,
    symbols: list(Symbol) = .{},

    pub const fields_meta = .{
        .symbols = structure.SexpField{ .multidict = true, .sexp_name = "symbol" },
    };
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
