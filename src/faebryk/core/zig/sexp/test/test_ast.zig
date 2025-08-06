const std = @import("std");
const sexp = @import("sexp");

const SExp = sexp.ast.SExp;

const RESOURCES_ROOT = "test/resources/v9";

test "parse empty input" {
    const allocator = std.testing.allocator;
    const tokens = try sexp.tokenizer.tokenize(allocator, "");
    defer allocator.free(tokens);

    const sexp_ast = sexp.ast.parse(allocator, tokens);
    try std.testing.expectError(error.EmptyFile, sexp_ast);
}

test "parse single symbol" {
    const allocator = std.testing.allocator;
    const tokens = try sexp.tokenizer.tokenize(allocator, "foo");
    defer allocator.free(tokens);

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    try std.testing.expect(sexp_ast.value == .symbol);
    try std.testing.expectEqualStrings("foo", sexp_ast.value.symbol);
}

test "parse list" {
    const allocator = std.testing.allocator;
    const tokens = try sexp.tokenizer.tokenize(allocator, "(foo bar)");
    defer allocator.free(tokens);

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    try std.testing.expect(sexp_ast.value == .list);
    const items = sexp.ast.getList(sexp_ast).?;
    try std.testing.expectEqual(@as(usize, 2), items.len);
    try std.testing.expectEqualStrings("foo", items[0].value.symbol);
    try std.testing.expectEqualStrings("bar", items[1].value.symbol);
}

test "parse nested list" {
    const allocator = std.testing.allocator;
    const tokens = try sexp.tokenizer.tokenize(allocator, "(foo (bar baz))");
    defer allocator.free(tokens);

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    try std.testing.expect(sexp_ast.value == .list);
    const items = sexp.ast.getList(sexp_ast).?;
    try std.testing.expectEqual(@as(usize, 2), items.len);
    try std.testing.expectEqualStrings("foo", items[0].value.symbol);

    const nested = sexp.ast.getList(items[1]).?;
    try std.testing.expectEqual(@as(usize, 2), nested.len);
    try std.testing.expectEqualStrings("bar", nested[0].value.symbol);
    try std.testing.expectEqualStrings("baz", nested[1].value.symbol);
}

test "parse string" {
    const allocator = std.testing.allocator;
    const tokens = try sexp.tokenizer.tokenize(allocator, "\"hello world\"");
    defer allocator.free(tokens);

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    try std.testing.expect(sexp_ast.value == .string);
    try std.testing.expectEqualStrings("hello world", sexp_ast.value.string);
}

test "isForm" {
    const allocator = std.testing.allocator;
    const tokens = try sexp.tokenizer.tokenize(allocator, "(foo bar baz)");
    defer allocator.free(tokens);

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    try std.testing.expect(sexp.ast.isForm(sexp_ast, "foo"));
    try std.testing.expect(!sexp.ast.isForm(sexp_ast, "bar"));
}

test "getSymbol and getList" {
    const allocator = std.testing.allocator;
    const tokens = try sexp.tokenizer.tokenize(allocator, "(foo bar)");
    defer allocator.free(tokens);

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    // Test getList
    const list = sexp.ast.getList(sexp_ast);
    try std.testing.expect(list != null);
    try std.testing.expectEqual(@as(usize, 2), list.?.len);

    // Test getSymbol
    try std.testing.expect(sexp.ast.getSymbol(sexp_ast) == null);
    try std.testing.expectEqualStrings("foo", sexp.ast.getSymbol(list.?[0]).?);
}

test "mixed types in list" {
    const allocator = std.testing.allocator;
    const tokens = try sexp.tokenizer.tokenize(allocator, "(foo 123 \"hello\" (nested))");
    defer allocator.free(tokens);

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    const items = sexp.ast.getList(sexp_ast).?;
    try std.testing.expectEqual(@as(usize, 4), items.len);

    try std.testing.expect(items[0].value == .symbol);
    try std.testing.expectEqualStrings("foo", items[0].value.symbol);

    try std.testing.expect(items[1].value == .number);
    try std.testing.expectEqualStrings("123", items[1].value.number);

    try std.testing.expect(items[2].value == .string);
    try std.testing.expectEqualStrings("hello", items[2].value.string);

    try std.testing.expect(items[3].value == .list);
}

test "round-trip pcb ast" {
    const FILE_PATH = RESOURCES_ROOT ++ "/pcb/top.kicad_pcb";

    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    const file_content = try std.fs.cwd().readFileAlloc(allocator, FILE_PATH, 1024 * 1024);

    const tokens = try sexp.tokenizer.tokenize(allocator, file_content);
    defer allocator.free(tokens);

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    const output = try sexp_ast.pretty(allocator);
    defer allocator.free(output);

    // Debug: write actual output to see the difference
    if (!std.mem.eql(u8, file_content, output)) {
        const debug_file = try std.fs.cwd().createFile("test_ast_output_debug.txt", .{});
        defer debug_file.close();
        try debug_file.writeAll(output);
    }

    try std.testing.expectEqualStrings(file_content, output);
}
