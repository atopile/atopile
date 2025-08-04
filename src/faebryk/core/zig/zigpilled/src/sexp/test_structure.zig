const std = @import("std");
const testing = std.testing;
const structure = @import("structure.zig");
const ast = @import("ast.zig");

// Test structures
const SimpleStruct = struct {
    name: []const u8,
    value: i32,
    enabled: bool = true,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = false },
        .value = structure.SexpField{ .positional = false },
        .enabled = structure.SexpField{ .positional = false },
    };
};

const PositionalStruct = struct {
    symbol: []const u8,
    x: i32,
    y: i32,

    pub const fields_meta = .{
        .symbol = structure.SexpField{ .positional = true },
        .x = structure.SexpField{ .positional = false },
        .y = structure.SexpField{ .positional = false },
    };
};

const OptionalStruct = struct {
    required: []const u8,
    optional: ?[]const u8 = null,

    pub const fields_meta = .{
        .required = structure.SexpField{ .positional = false },
        .optional = structure.SexpField{ .positional = false },
    };
};

const MultidictStruct = struct {
    name: []const u8,
    items: []SimpleStruct = &.{},

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = false },
        .items = structure.SexpField{ .positional = false, .multidict = true, .sexp_name = "item" },
    };
};

test "encode simple struct" {
    const allocator = testing.allocator;

    const data = SimpleStruct{
        .name = "test",
        .value = 42,
        .enabled = false,
    };

    const encoded = try structure.dumps(allocator, data);
    defer allocator.free(encoded);

    // Just check that it contains the expected values, not exact formatting
    try testing.expect(std.mem.indexOf(u8, encoded, "(name \"test\")") != null);
    try testing.expect(std.mem.indexOf(u8, encoded, "(value 42)") != null);
    try testing.expect(std.mem.indexOf(u8, encoded, "(enabled no)") != null);
}

test "decode simple struct" {
    const allocator = testing.allocator;

    const sexp_str = "((name \"test\") (value 42) (enabled yes))";

    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    const result = try structure.decode(SimpleStruct, allocator, sexp);
    defer allocator.free(result.name);

    try testing.expectEqualStrings("test", result.name);
    try testing.expectEqual(@as(i32, 42), result.value);
    try testing.expectEqual(true, result.enabled);
}

test "positional fields" {
    const allocator = testing.allocator;

    const data = PositionalStruct{
        .symbol = "SYMBOL",
        .x = 10,
        .y = 20,
    };

    const encoded = try structure.dumps(allocator, data);
    defer allocator.free(encoded);

    // Check content, not exact formatting
    try testing.expect(std.mem.indexOf(u8, encoded, "\"SYMBOL\"") != null);
    try testing.expect(std.mem.indexOf(u8, encoded, "(x 10)") != null);
    try testing.expect(std.mem.indexOf(u8, encoded, "(y 20)") != null);
}

test "optional fields" {
    const allocator = testing.allocator;

    // Test with null optional
    const data1 = OptionalStruct{
        .required = "hello",
        .optional = null,
    };

    const encoded1 = try structure.dumps(allocator, data1);
    defer allocator.free(encoded1);

    // Check content
    try testing.expect(std.mem.indexOf(u8, encoded1, "(required \"hello\")") != null);
    try testing.expect(std.mem.indexOf(u8, encoded1, "optional") == null); // Should not contain optional

    // Test with value
    const data2 = OptionalStruct{
        .required = "hello",
        .optional = "world",
    };

    const encoded2 = try structure.dumps(allocator, data2);
    defer allocator.free(encoded2);

    // Check content
    try testing.expect(std.mem.indexOf(u8, encoded2, "(required \"hello\")") != null);
    try testing.expect(std.mem.indexOf(u8, encoded2, "(optional \"world\")") != null);
}

test "multidict fields" {
    const allocator = testing.allocator;

    var items = try allocator.alloc(SimpleStruct, 2);
    defer allocator.free(items);

    items[0] = .{ .name = "first", .value = 1 };
    items[1] = .{ .name = "second", .value = 2 };

    const data = MultidictStruct{
        .name = "container",
        .items = items,
    };

    const encoded = try structure.dumps(allocator, data);
    defer allocator.free(encoded);

    // Check multidict content
    try testing.expect(std.mem.indexOf(u8, encoded, "(name \"container\")") != null);
    try testing.expect(std.mem.indexOf(u8, encoded, "(item") != null);
    try testing.expect(std.mem.indexOf(u8, encoded, "(name \"first\")") != null);
    try testing.expect(std.mem.indexOf(u8, encoded, "(name \"second\")") != null);
}

test "round trip" {
    const allocator = testing.allocator;

    const original = SimpleStruct{
        .name = "round-trip",
        .value = 123,
        .enabled = false,
    };

    // Encode
    const encoded = try structure.dumps(allocator, original);
    defer allocator.free(encoded);

    // Decode
    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, encoded);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    const decoded = try structure.decode(SimpleStruct, allocator, sexp);
    defer allocator.free(decoded.name);

    try testing.expectEqualStrings(original.name, decoded.name);
    try testing.expectEqual(original.value, decoded.value);
    try testing.expectEqual(original.enabled, decoded.enabled);
}

test "missing required field - name" {
    const allocator = testing.allocator;

    // Missing 'name' field (required)
    const sexp_str = "((value 42) (enabled yes))";

    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    // This should fail with MissingField error
    const result = structure.decode(SimpleStruct, allocator, sexp);
    try testing.expectError(error.MissingField, result);

    // Check error context
    if (structure.getErrorContext()) |ctx| {
        try testing.expectEqualStrings("test_structure.SimpleStruct", ctx.path);
        try testing.expectEqualStrings("name", ctx.field_name.?);
    }
}

test "missing required field - value" {
    const allocator = testing.allocator;

    // Missing 'value' field (required)
    const sexp_str = "((name \"test\") (enabled yes))";

    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    // This should fail with MissingField error
    const result = structure.decode(SimpleStruct, allocator, sexp);
    try testing.expectError(error.MissingField, result);

    // Check error context
    if (structure.getErrorContext()) |ctx| {
        try testing.expectEqualStrings("test_structure.SimpleStruct", ctx.path);
        try testing.expectEqualStrings("value", ctx.field_name.?);
    }
}

test "missing optional field is ok" {
    const allocator = testing.allocator;

    // Missing 'enabled' field (has default value)
    const sexp_str = "((name \"test\") (value 42))";

    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    const result = try structure.decode(SimpleStruct, allocator, sexp);
    defer allocator.free(result.name);

    try testing.expectEqualStrings("test", result.name);
    try testing.expectEqual(@as(i32, 42), result.value);
    try testing.expectEqual(true, result.enabled); // Should use default value
}

test "missing required field in OptionalStruct" {
    const allocator = testing.allocator;

    // Missing 'required' field
    const sexp_str = "((optional \"world\"))";

    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    // This should fail with MissingField error
    const result = structure.decode(OptionalStruct, allocator, sexp);
    try testing.expectError(error.MissingField, result);
}

// Test struct without defaults for testing
const NoDefaultsStruct = struct {
    required1: []const u8,
    required2: i32,

    pub const fields_meta = .{
        .required1 = structure.SexpField{ .positional = false },
        .required2 = structure.SexpField{ .positional = false },
    };
};

test "all fields missing in struct without defaults" {
    const allocator = testing.allocator;

    // Empty s-expression
    const sexp_str = "()";

    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    // This should fail with MissingField error
    const result = structure.decode(NoDefaultsStruct, allocator, sexp);
    try testing.expectError(error.MissingField, result);
}

// Test netlist-like structure to ensure components with missing fields error
const Component = struct {
    ref: []const u8,
    value: []const u8,
    footprint: []const u8,
    tstamps: []const u8,

    pub const fields_meta = .{
        .ref = structure.SexpField{ .positional = false },
        .value = structure.SexpField{ .positional = false },
        .footprint = structure.SexpField{ .positional = false },
        .tstamps = structure.SexpField{ .positional = false },
    };
};

test "netlist component missing required fields" {
    const allocator = testing.allocator;

    // Missing 'footprint' and 'tstamps' fields
    const sexp_str = "((ref \"R1\") (value \"10k\"))";

    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    // This should fail with MissingField error for footprint
    const result = structure.decode(Component, allocator, sexp);
    try testing.expectError(error.MissingField, result);

    // Check error context shows which field is missing
    if (structure.getErrorContext()) |ctx| {
        try testing.expectEqualStrings("test_structure.Component", ctx.path);
        // Should be either footprint or tstamps
        try testing.expect(ctx.field_name != null);
        const field_name = ctx.field_name.?;
        try testing.expect(std.mem.eql(u8, field_name, "footprint") or
            std.mem.eql(u8, field_name, "tstamps"));
    }
}

const A = struct {
    a: i32,
    b: []const u8,

    pub const fields_meta = .{
        .a = structure.SexpField{ .positional = false },
        .b = structure.SexpField{ .positional = false },
    };
};

pub fn main() !void {
    const allocator = std.heap.page_allocator;
    
    // Test different error scenarios
    const test_cases = [_]struct { 
        name: []const u8, 
        sexp: []const u8 
    }{
        .{ .name = "String instead of number", .sexp = "((a \"1\") (b \"10k\"))" },
        .{ .name = "Missing required field", .sexp = "((a 1))" },
        .{ .name = "Invalid number format", .sexp = "((a 1.5) (b \"test\"))" },
        .{ .name = "Unquoted string for b", .sexp = "((a 1) (b hello))" },
        .{ .name = "Number for string field", .sexp = "((a 1) (b 123))" },
        .{ .name = "Correct format", .sexp = "((a 42) (b \"hello world\"))" },
    };
    
    for (test_cases) |test_case| {
        std.debug.print("\n=== Test: {s} ===\n", .{test_case.name});
        std.debug.print("Input: {s}\n", .{test_case.sexp});
        
        testDecode(allocator, test_case.sexp) catch {
            // Error already printed by testDecode
        };
    }
}

fn testDecode(allocator: std.mem.Allocator, sexp_str: []const u8) !void {

    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    // Catch the decode error and print context
    const result = structure.decode(A, allocator, sexp) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        
        // Get and print the error context
        if (structure.getErrorContext()) |ctx| {
            if (ctx.path.len > 0) {
                std.debug.print("  In struct: {s}\n", .{ctx.path});
            }
            if (ctx.field_name) |field| {
                std.debug.print("  Field: {s}\n", .{field});
            }
            if (ctx.sexp_preview) |preview| {
                if (preview.len > 0) {
                    std.debug.print("  Problem: {s}\n", .{preview});
                }
            }
        }
        return err;
    };
    
    defer structure.free(A, allocator, result);
    std.debug.print("Success! a={}, b={s}\n", .{result.a, result.b});
}
