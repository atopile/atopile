const std = @import("std");
const tokenizer = @import("tokenizer.zig");
const ast = @import("ast.zig");

const SExp = ast.SExp;

test "parse empty input" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "");
    defer allocator.free(tokens);

    const sexp = ast.parse(allocator, tokens);
    try std.testing.expectError(error.EmptyFile, sexp);
}

test "parse single symbol" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "foo");
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens);
    defer sexp.deinit(allocator);

    try std.testing.expect(sexp.value == .symbol);
    try std.testing.expectEqualStrings("foo", sexp.value.symbol);
}

test "parse list" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo bar)");
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens);
    defer sexp.deinit(allocator);

    try std.testing.expect(sexp.value == .list);
    const items = ast.getList(sexp).?;
    try std.testing.expectEqual(@as(usize, 2), items.len);
    try std.testing.expectEqualStrings("foo", items[0].value.symbol);
    try std.testing.expectEqualStrings("bar", items[1].value.symbol);
}

test "parse nested list" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo (bar baz))");
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens);
    defer sexp.deinit(allocator);

    try std.testing.expect(sexp.value == .list);
    const items = ast.getList(sexp).?;
    try std.testing.expectEqual(@as(usize, 2), items.len);
    try std.testing.expectEqualStrings("foo", items[0].value.symbol);

    const nested = ast.getList(items[1]).?;
    try std.testing.expectEqual(@as(usize, 2), nested.len);
    try std.testing.expectEqualStrings("bar", nested[0].value.symbol);
    try std.testing.expectEqualStrings("baz", nested[1].value.symbol);
}

test "parse string" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "\"hello world\"");
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens);
    defer sexp.deinit(allocator);

    try std.testing.expect(sexp.value == .string);
    try std.testing.expectEqualStrings("hello world", sexp.value.string);
}

test "isForm" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo bar baz)");
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens);
    defer sexp.deinit(allocator);

    try std.testing.expect(ast.isForm(sexp, "foo"));
    try std.testing.expect(!ast.isForm(sexp, "bar"));
}

test "getSymbol and getList" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo bar)");
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens);
    defer sexp.deinit(allocator);

    // Test getList
    const list = ast.getList(sexp);
    try std.testing.expect(list != null);
    try std.testing.expectEqual(@as(usize, 2), list.?.len);

    // Test getSymbol
    try std.testing.expect(ast.getSymbol(sexp) == null);
    try std.testing.expectEqualStrings("foo", ast.getSymbol(list.?[0]).?);
}

test "mixed types in list" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo 123 \"hello\" (nested))");
    defer allocator.free(tokens);

    var sexp = try ast.parse(allocator, tokens);
    defer sexp.deinit(allocator);

    const items = ast.getList(sexp).?;
    try std.testing.expectEqual(@as(usize, 4), items.len);

    try std.testing.expect(items[0].value == .symbol);
    try std.testing.expectEqualStrings("foo", items[0].value.symbol);

    try std.testing.expect(items[1].value == .number);
    try std.testing.expectEqualStrings("123", items[1].value.number);

    try std.testing.expect(items[2].value == .string);
    try std.testing.expectEqualStrings("hello", items[2].value.string);

    try std.testing.expect(items[3].value == .list);
}
