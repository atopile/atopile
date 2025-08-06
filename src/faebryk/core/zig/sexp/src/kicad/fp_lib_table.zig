const std = @import("std");
const structure = @import("../structure.zig");

// KiCad footprint library table entry
pub const FpLibEntry = struct {
    name: []const u8,
    type: []const u8,
    uri: []const u8,
    options: []const u8,
    descr: []const u8,
};

pub const FpLibTable = struct {
    version: ?[]const u8 = null,
    libs: []FpLibEntry = &.{},

    pub const fields_meta = .{
        .libs = structure.SexpField{ .multidict = true, .sexp_name = "lib" },
    };
};

const FpLibTableFile = struct {
    fp_lib_table: FpLibTable,

    const root_symbol = "fp_lib_table";

    pub fn loads(allocator: std.mem.Allocator, in: structure.input) !FpLibTableFile {
        const table = try structure.loads(FpLibTable, allocator, in, root_symbol);
        return FpLibTableFile{
            .fp_lib_table = table,
        };
    }

    pub fn dumps(self: FpLibTableFile, allocator: std.mem.Allocator, out: structure.output) !void {
        try structure.dumps(self.fp_lib_table, allocator, root_symbol, out);
    }

    pub fn free(self: *FpLibTableFile, allocator: std.mem.Allocator) void {
        structure.free(FpLibTable, allocator, self.fp_lib_table);
    }
};
