const std = @import("std");
const testing = std.testing;
const dataclass_sexp = @import("dataclass_sexp.zig");
const ast = @import("ast.zig");

// Test structures
const SimpleStruct = struct {
    name: []const u8,
    value: i32,
    enabled: bool = true,
    
    pub const sexp_metadata = .{
        .name = .{ .positional = false },
        .value = .{ .positional = false },
        .enabled = .{ .positional = false },
    };
};

const PositionalStruct = struct {
    symbol: []const u8,
    x: i32,
    y: i32,
    
    pub const sexp_metadata = .{
        .symbol = .{ .positional = true },
        .x = .{ .positional = false },
        .y = .{ .positional = false },
    };
};

const OptionalStruct = struct {
    required: []const u8,
    optional: ?[]const u8 = null,
    
    pub const sexp_metadata = .{
        .required = .{ .positional = false },
        .optional = .{ .positional = false },
    };
};

const MultidictStruct = struct {
    name: []const u8,
    items: []SimpleStruct = &.{},
    
    pub const sexp_metadata = .{
        .name = .{ .positional = false },
        .items = .{ .positional = false, .multidict = true, .sexp_name = "item" },
    };
};

test "encode simple struct" {
    const allocator = testing.allocator;
    
    const data = SimpleStruct{
        .name = "test",
        .value = 42,
        .enabled = false,
    };
    
    const encoded = try dataclass_sexp.dumps(allocator, data);
    defer allocator.free(encoded);
    
    try testing.expectEqualStrings("((name \"test\") (value 42) (enabled no))", encoded);
}

test "decode simple struct" {
    const allocator = testing.allocator;
    
    const sexp_str = "((name \"test\") (value 42) (enabled yes))";
    
    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, sexp_str);
    defer allocator.free(tokens);
    
    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);
    
    const result = try dataclass_sexp.decode(SimpleStruct, allocator, sexp);
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
    
    const encoded = try dataclass_sexp.dumps(allocator, data);
    defer allocator.free(encoded);
    
    try testing.expectEqualStrings("(\"SYMBOL\" (x 10) (y 20))", encoded);
}

test "optional fields" {
    const allocator = testing.allocator;
    
    // Test with null optional
    const data1 = OptionalStruct{
        .required = "hello",
        .optional = null,
    };
    
    const encoded1 = try dataclass_sexp.dumps(allocator, data1);
    defer allocator.free(encoded1);
    
    try testing.expectEqualStrings("((required \"hello\"))", encoded1);
    
    // Test with value
    const data2 = OptionalStruct{
        .required = "hello",
        .optional = "world",
    };
    
    const encoded2 = try dataclass_sexp.dumps(allocator, data2);
    defer allocator.free(encoded2);
    
    try testing.expectEqualStrings("((required \"hello\") (optional \"world\"))", encoded2);
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
    
    const encoded = try dataclass_sexp.dumps(allocator, data);
    defer allocator.free(encoded);
    
    const expected = "((name \"container\") (item (name \"first\") (value 1) (enabled yes)) (item (name \"second\") (value 2) (enabled yes)))";
    try testing.expectEqualStrings(expected, encoded);
}

test "round trip" {
    const allocator = testing.allocator;
    
    const original = SimpleStruct{
        .name = "round-trip",
        .value = 123,
        .enabled = false,
    };
    
    // Encode
    const encoded = try dataclass_sexp.dumps(allocator, original);
    defer allocator.free(encoded);
    
    // Decode
    const tokenizer = @import("tokenizer.zig");
    const tokens = try tokenizer.tokenize(allocator, encoded);
    defer allocator.free(tokens);
    
    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);
    
    const decoded = try dataclass_sexp.decode(SimpleStruct, allocator, sexp);
    defer allocator.free(decoded.name);
    
    try testing.expectEqualStrings(original.name, decoded.name);
    try testing.expectEqual(original.value, decoded.value);
    try testing.expectEqual(original.enabled, decoded.enabled);
}