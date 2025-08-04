const std = @import("std");
const kicad = @import("kicad.zig");
const dataclass_sexp = @import("../dataclass_sexp.zig");

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

const FpLibTableFile = struct {
    fn loads(allocator: std.mem.Allocator, content: []const u8) !FpLibTable {
        return try kicad.loadsKicadFile(FpLibTable, allocator, content, "fp_lib_table");
    }

    fn dumps(table: FpLibTable, allocator: std.mem.Allocator) ![]u8 {
        return try kicad.dumpsKicadFile(table, allocator, "fp_lib_table");
    }

    fn write(table: FpLibTable, file_path: []const u8, allocator: std.mem.Allocator) !void {
        return try kicad.writeKicadFile(table, file_path, "fp_lib_table", allocator);
    }

    fn free(allocator: std.mem.Allocator, table: FpLibTable) void {
        dataclass_sexp.free(FpLibTable, allocator, table);
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

    // Serialize to S-expression (normal)
    const sexp_str = try FpLibTableFile.dumps(table, allocator);
    defer allocator.free(sexp_str);

    std.debug.print("Generated S-expression (normal):\n{s}\n\n", .{sexp_str});

    // Parse it back
    const parsed = try FpLibTableFile.loads(allocator, sexp_str);
    defer FpLibTableFile.free(allocator, parsed);

    std.debug.print("Loaded: {}\n", .{parsed});
}
