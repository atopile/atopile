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
    fp_lib_table: ?FpLibTable = null,

    const root_symbol = "fp_lib_table";

    pub fn loads(allocator: std.mem.Allocator, content: []const u8) !FpLibTableFile {
        const table = try structure.loadsStringWithSymbol(FpLibTable, allocator, content, root_symbol);
        return FpLibTableFile{
            .fp_lib_table = table,
        };
    }

    pub fn dumps(self: FpLibTableFile, allocator: std.mem.Allocator) ![]u8 {
        if (self.fp_lib_table) |table| {
            return try structure.dumpsStringWithSymbol(table, allocator, root_symbol);
        }
        return error.NoTable;
    }

    pub fn write(self: FpLibTableFile, file_path: []const u8, allocator: std.mem.Allocator) !void {
        if (self.fp_lib_table) |table| {
            return try structure.writeFileWithSymbol(table, file_path, root_symbol, allocator);
        }
        return error.NoTable;
    }

    pub fn free(self: *FpLibTableFile, allocator: std.mem.Allocator) void {
        if (self.fp_lib_table) |table| {
            structure.free(FpLibTable, allocator, table);
        }
    }
};
