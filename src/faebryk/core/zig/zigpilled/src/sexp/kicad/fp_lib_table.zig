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
    version: ?i32 = null,
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

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    try example(allocator);
}

// Example usage
pub fn example(allocator: std.mem.Allocator) !void {
    // Create a library table
    var libs = try allocator.alloc(FpLibEntry, 2);
    defer allocator.free(libs);
    libs[0] = .{
        .name = "faebryk",
        .type = "KiCad",
        .uri = "${KIPRJMOD}/faebryk.pretty",
        .options = "",
        .descr = "Faebryk generated footprints",
    };
    libs[1] = .{
        .name = "KiCad",
        .type = "KiCad",
        .uri = "$(KICAD7_FOOTPRINT_DIR)/Connector_PinHeader_2.54mm.pretty",
        .options = "",
        .descr = "KiCad builtin footprints",
    };

    const table = FpLibTable{
        .version = 7,
        .libs = libs,
    };

    // Create wrapper
    const file = FpLibTableFile{
        .fp_lib_table = table,
    };

    // Serialize to S-expression (normal)
    const sexp_str = try file.dumps(allocator);
    defer allocator.free(sexp_str);

    std.debug.print("Generated S-expression (normal):\n{s}\n\n", .{sexp_str});

    // Parse it back
    var parsed = try FpLibTableFile.loads(allocator, sexp_str);
    defer parsed.free(allocator);

    std.debug.print("Loaded: {?}\n", .{parsed.fp_lib_table});
}
