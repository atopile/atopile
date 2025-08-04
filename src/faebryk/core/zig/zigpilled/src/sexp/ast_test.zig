const std = @import("std");
const tokenizer = @import("tokenizer.zig");
const ast = @import("ast.zig");

const SExp = ast.SExp;

test "parse empty input" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer allocator.free(sexps);
    
    try std.testing.expectEqual(@as(usize, 0), sexps.len);
}

test "parse single symbol" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "foo");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer allocator.free(sexps);
    
    try std.testing.expectEqual(@as(usize, 1), sexps.len);
    try std.testing.expect(sexps[0] == .symbol);
    try std.testing.expectEqualStrings("foo", sexps[0].symbol);
}

test "parse single number" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "42");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer allocator.free(sexps);
    
    try std.testing.expectEqual(@as(usize, 1), sexps.len);
    try std.testing.expect(sexps[0] == .number);
    try std.testing.expectEqualStrings("42", sexps[0].number);
}

test "parse single string" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "\"hello world\"");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer allocator.free(sexps);
    
    try std.testing.expectEqual(@as(usize, 1), sexps.len);
    try std.testing.expect(sexps[0] == .string);
    try std.testing.expectEqualStrings("hello world", sexps[0].string);
}

test "parse empty list" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "()");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    try std.testing.expectEqual(@as(usize, 1), sexps.len);
    try std.testing.expect(sexps[0] == .list);
    try std.testing.expectEqual(@as(usize, 0), sexps[0].list.len);
}

test "parse simple list" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo bar 42)");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    try std.testing.expectEqual(@as(usize, 1), sexps.len);
    try std.testing.expect(sexps[0] == .list);
    
    const list = sexps[0].list;
    try std.testing.expectEqual(@as(usize, 3), list.len);
    try std.testing.expectEqualStrings("foo", list[0].symbol);
    try std.testing.expectEqualStrings("bar", list[1].symbol);
    try std.testing.expectEqualStrings("42", list[2].number);
}

test "parse nested lists" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(a (b c) d)");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    try std.testing.expectEqual(@as(usize, 1), sexps.len);
    const outer = sexps[0].list;
    try std.testing.expectEqual(@as(usize, 3), outer.len);
    
    try std.testing.expectEqualStrings("a", outer[0].symbol);
    try std.testing.expect(outer[1] == .list);
    try std.testing.expectEqualStrings("d", outer[2].symbol);
    
    const inner = outer[1].list;
    try std.testing.expectEqual(@as(usize, 2), inner.len);
    try std.testing.expectEqualStrings("b", inner[0].symbol);
    try std.testing.expectEqualStrings("c", inner[1].symbol);
}

test "parse multiple expressions" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo) (bar) baz");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    try std.testing.expectEqual(@as(usize, 3), sexps.len);
    try std.testing.expect(sexps[0] == .list);
    try std.testing.expect(sexps[1] == .list);
    try std.testing.expect(sexps[2] == .symbol);
}

test "parse with comments" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "; comment\n(foo bar)");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    try std.testing.expectEqual(@as(usize, 2), sexps.len);
    try std.testing.expect(sexps[0] == .comment);
    try std.testing.expect(sexps[1] == .list);
}

test "parse KiCad-style expression" {
    const allocator = std.testing.allocator;
    const input = "(gr_text \"Hello\" (at 10.5 20.3) (layer F.SilkS) (effects (font (size 1 1) (thickness 0.15))))";
    const tokens = try tokenizer.tokenize(allocator, input);
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    try std.testing.expectEqual(@as(usize, 1), sexps.len);
    const root = sexps[0];
    try std.testing.expect(ast.isForm(root, "gr_text"));
    
    const items = root.list;
    try std.testing.expectEqualStrings("Hello", items[1].string);
    try std.testing.expect(ast.isForm(items[2], "at"));
    try std.testing.expect(ast.isForm(items[3], "layer"));
    try std.testing.expect(ast.isForm(items[4], "effects"));
}

test "error on unmatched right paren" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, ")");
    defer allocator.free(tokens);
    
    const result = ast.parse(allocator, tokens);
    try std.testing.expectError(error.UnexpectedRightParen, result);
}

test "error on unterminated list" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo bar");
    defer allocator.free(tokens);
    
    const result = ast.parse(allocator, tokens);
    try std.testing.expectError(error.UnterminatedList, result);
}

test "helper functions" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo bar 42)");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    const root = sexps[0];
    
    // Test isList and isAtom
    try std.testing.expect(ast.isList(root));
    try std.testing.expect(!ast.isAtom(root));
    try std.testing.expect(ast.isAtom(root.list[0]));
    
    // Test listLen
    try std.testing.expectEqual(@as(?usize, 3), ast.listLen(root));
    try std.testing.expectEqual(@as(?usize, null), ast.listLen(root.list[0]));
    
    // Test getSymbol
    try std.testing.expectEqual(@as(?[]const u8, null), ast.getSymbol(root));
    try std.testing.expectEqualStrings("foo", ast.getSymbol(root.list[0]).?);
    
    // Test first and rest
    try std.testing.expectEqualStrings("foo", ast.first(root).?.symbol);
    try std.testing.expectEqual(@as(usize, 2), ast.rest(root).?.len);
}

test "findValue in property list" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(layer F.Cu thickness 0.15 color red)");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    const root = sexps[0];
    
    // Find existing values
    const thickness = ast.findValue(root, "thickness");
    try std.testing.expect(thickness != null);
    try std.testing.expectEqualStrings("0.15", thickness.?.number);
    
    const color = ast.findValue(root, "color");
    try std.testing.expect(color != null);
    try std.testing.expectEqualStrings("red", color.?.symbol);
    
    // Non-existent key
    try std.testing.expectEqual(@as(?*const SExp, null), ast.findValue(root, "width"));
}

test "format S-expressions" {
    const allocator = std.testing.allocator;
    const tokens = try tokenizer.tokenize(allocator, "(foo \"bar\" 42 (nested list))");
    defer allocator.free(tokens);
    
    const sexps = try ast.parse(allocator, tokens);
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    var buffer = std.ArrayList(u8).init(allocator);
    defer buffer.deinit();
    
    try sexps[0].format("", .{}, buffer.writer());
    try std.testing.expectEqualStrings("(foo \"bar\" 42 (nested list))", buffer.items);
}