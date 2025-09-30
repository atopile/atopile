const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

fn list(comptime T: type) type {
    return std.DoublyLinkedList(T);
}

const schematic = @import("schematic.zig");

pub const SymbolLib = struct {
    version: i32,
    generator: str = "",
    symbols: list(schematic.Symbol) = .{},

    pub const fields_meta = .{
        .symbols = structure.SexpField{ .multidict = true, .sexp_name = "symbol" },
    };
};

pub const SymbolFile = struct {
    kicad_sym: SymbolLib,

    const root_symbol = "kicad_symbol_lib";

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
