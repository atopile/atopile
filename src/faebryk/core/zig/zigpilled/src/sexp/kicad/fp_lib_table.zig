const std = @import("std");
const kicad = @import("kicad.zig");

// KiCad footprint library table entry
pub const FpLibEntry = struct {
    name: []const u8,
    type: []const u8,
    uri: []const u8,
    options: []const u8,
    descr: []const u8,

    // Metadata for SEXP serialization
    pub const sexp_metadata = .{
        .name = .{ .positional = false, .order = 0 },
        .type = .{ .positional = false, .order = 1 },
        .uri = .{ .positional = false, .order = 2 },
        .options = .{ .positional = false, .order = 3 },
        .descr = .{ .positional = false, .order = 4 },
    };
};

// KiCad footprint library table
pub const FpLibTable = struct {
    version: ?i32 = null,
    libs: []FpLibEntry = &.{},

    // Metadata for SEXP serialization
    pub const sexp_metadata = .{
        .version = .{ .positional = false, .order = -1 },
        .libs = .{ .positional = false, .multidict = true, .sexp_name = "lib", .order = 0 },
    };
};

// For KiCad files, the top-level structure IS the table itself
// with a symbol name of "fp_lib_table"
pub const FpLibTableFile = FpLibTable;

// Helper function to free a FpLibEntry
pub fn freeFpLibEntry(allocator: std.mem.Allocator, entry: FpLibEntry) void {
    allocator.free(entry.name);
    allocator.free(entry.type);
    allocator.free(entry.uri);
    allocator.free(entry.options);
    allocator.free(entry.descr);
}

// Helper function to free a FpLibTable
pub fn freeFpLibTable(allocator: std.mem.Allocator, table: FpLibTable) void {
    for (table.libs) |entry| {
        freeFpLibEntry(allocator, entry);
    }
    if (table.libs.len > 0) {
        allocator.free(table.libs);
    }
}

pub fn loadsFpLibTable(allocator: std.mem.Allocator, content: []const u8) !FpLibTable {
    return try kicad.loadsKicadFile(FpLibTable, allocator, content, "fp_lib_table");
}

pub fn dumpsFpLibTable(table: FpLibTable, allocator: std.mem.Allocator) ![]u8 {
    return try kicad.dumpsKicadFile(table, allocator, "fp_lib_table");
}

pub fn dumpsPrettyFpLibTable(table: FpLibTable, allocator: std.mem.Allocator) ![]u8 {
    return try kicad.dumpsPrettyKicadFile(table, allocator, "fp_lib_table");
}

pub fn writeFpLibTable(table: FpLibTable, file_path: []const u8, allocator: std.mem.Allocator) !void {
    return try kicad.writeKicadFile(table, file_path, "fp_lib_table", allocator);
}

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

    // Serialize to S-expression (normal)
    const sexp_str = try dumpsFpLibTable(table, allocator);
    defer allocator.free(sexp_str);

    std.debug.print("Generated S-expression (normal):\n{s}\n\n", .{sexp_str});

    // Parse it back
    const parsed = try loadsFpLibTable(allocator, sexp_str);
    defer freeFpLibTable(allocator, parsed);

    std.debug.print("Loaded: {}\n", .{parsed});
}
