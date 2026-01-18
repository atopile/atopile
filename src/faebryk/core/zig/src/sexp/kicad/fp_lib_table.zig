const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

// KiCad footprint library table entry
pub const FpLibEntry = struct {
    name: str,
    type: str,
    uri: str,
    options: str,
    descr: str,
};

fn list(comptime T: type) type {
    return std.DoublyLinkedList(T);
}

pub const FpLibTable = struct {
    version: ?i32 = null,
    libs: list(FpLibEntry) = .{},

    pub const fields_meta = .{
        .libs = structure.SexpField{ .multidict = true, .sexp_name = "lib" },
    };
};

pub const FpLibTableFile = struct {
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
