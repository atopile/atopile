const std = @import("std");
const dataclass_sexp = @import("dataclass_sexp.zig");
const ast = @import("ast.zig");
const tokenizer = @import("tokenizer.zig");

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

pub fn loadsFpLibTable(allocator: std.mem.Allocator, content: []const u8) !FpLibTable {
    // Tokenize
    const tokens = try tokenizer.tokenize(allocator, content);
    defer allocator.free(tokens);

    // Parse to AST using arena allocator for performance
    var parse_arena = std.heap.ArenaAllocator.init(allocator);
    defer parse_arena.deinit();

    var sexp = try ast.parse(parse_arena.allocator(), tokens) orelse return error.EmptyFile;
    defer sexp.deinit(parse_arena.allocator());

    // The file structure is (fp_lib_table ...)
    const fp_lib_table_list = ast.getList(sexp) orelse return error.UnexpectedType;
    if (fp_lib_table_list.len < 1) return error.UnexpectedType;

    const symbol = ast.getSymbol(fp_lib_table_list[0]) orelse return error.UnexpectedType;
    if (!std.mem.eql(u8, symbol, "fp_lib_table")) return error.UnexpectedType;

    // Create a new list without the symbol for decoding
    const contents = fp_lib_table_list[1..];
    const table_sexp = ast.SExp{ .list = contents };

    // Decode
    return try dataclass_sexp.decode(FpLibTable, allocator, table_sexp);
}

pub fn dumpsFpLibTable(table: FpLibTable, allocator: std.mem.Allocator) ![]u8 {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    // Encode the table
    const encoded = try dataclass_sexp.encode(arena.allocator(), table);

    // The encoded result is a list of key-value pairs
    // We need to prepend the fp_lib_table symbol
    const encoded_items = ast.getList(encoded).?;

    var items = try arena.allocator().alloc(ast.SExp, encoded_items.len + 1);
    items[0] = ast.SExp{ .symbol = "fp_lib_table" };

    // Copy the encoded items
    for (encoded_items, 0..) |item, i| {
        items[i + 1] = item;
    }

    const wrapped = ast.SExp{ .list = items };

    // Write to string
    var buffer = std.ArrayList(u8).init(allocator);
    const writer = buffer.writer();

    try writeSexp(writer, wrapped);

    return try buffer.toOwnedSlice();
}

fn writeSexp(writer: anytype, sexp: ast.SExp) !void {
    switch (sexp) {
        .symbol => |s| try writer.print("{s}", .{s}),
        .number => |n| try writer.print("{s}", .{n}),
        .string => |s| try writer.print("\"{s}\"", .{s}),
        .comment => |c| try writer.print(";{s}", .{c}),
        .list => |items| {
            try writer.writeAll("(");
            for (items, 0..) |item, i| {
                if (i > 0) try writer.writeAll(" ");
                try writeSexp(writer, item);
            }
            try writer.writeAll(")");
        },
    }
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

    // Serialize to S-expression
    const sexp_str = try dumpsFpLibTable(table, allocator);
    defer allocator.free(sexp_str);

    std.debug.print("Generated S-expression:\n{s}\n", .{sexp_str});

    // Parse it back
    const parsed = try loadsFpLibTable(allocator, sexp_str);
    defer if (parsed.libs.len > 0) allocator.free(parsed.libs);

    std.debug.print("Loaded: {}\n", .{parsed});

    //std.debug.print("Successfully round-tripped!\n", .{});
    //std.debug.print("  Version: {?}\n", .{parsed.version});
    //std.debug.print("  Libraries: {}\n", .{parsed.libs.len});

    //for (parsed.libs) |lib| {
    //    std.debug.print("    - {s}: {s}\n", .{ lib.name, lib.descr });
    //}
}
