const std = @import("std");
const sexp = @import("sexp");

test "tokenize string literal" {
    const input = "\"Hello, world!\"";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 1), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.string, tokens[0].type);
    try std.testing.expectEqualStrings("Hello, world!", tokens[0].value);
}

test "tokenize symbol" {
    const input = "kicad_pcb";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 1), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[0].type);
    try std.testing.expectEqualStrings("kicad_pcb", tokens[0].value);
}

test "tokenize number" {
    const input = "42.5";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 1), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[0].type);
    try std.testing.expectEqualStrings("42.5", tokens[0].value);
}

test "tokenize negative number" {
    const input = "-3.14";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 1), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[0].type);
    try std.testing.expectEqualStrings("-3.14", tokens[0].value);
}

test "tokenize parentheses" {
    const input = "()";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 2), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[0].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[1].type);
}

test "tokenize simple s-expression" {
    const input = "(hello world)";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 4), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[0].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[1].type);
    try std.testing.expectEqualStrings("hello", tokens[1].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[2].type);
    try std.testing.expectEqualStrings("world", tokens[2].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[3].type);
}

test "tokenize nested s-expression" {
    const input = "(foo (bar 123))";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 7), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[0].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[1].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[2].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[3].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[4].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[5].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[6].type);
}

test "tokenize kicad-style expression" {
    const input = "(property \"Reference\" \"C1\" (at 0 -4 0))";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 11), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[0].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[1].type);
    try std.testing.expectEqualStrings("property", tokens[1].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.string, tokens[2].type);
    try std.testing.expectEqualStrings("Reference", tokens[2].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.string, tokens[3].type);
    try std.testing.expectEqualStrings("C1", tokens[3].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[4].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[5].type);
    try std.testing.expectEqualStrings("at", tokens[5].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[6].type);
    try std.testing.expectEqualStrings("0", tokens[6].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[7].type);
    try std.testing.expectEqualStrings("-4", tokens[7].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[8].type);
    try std.testing.expectEqualStrings("0", tokens[8].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[9].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[10].type);
}

test "tokenize multiline expression" {
    const input =
        \\(general
        \\    (thickness 1.6)
        \\    (legacy_teardrops no))
    ;
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 11), tokens.len);

    // First line: (general
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[0].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[1].type);
    try std.testing.expectEqualStrings("general", tokens[1].value);

    // Second line: (thickness 1.6)
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[2].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[3].type);
    try std.testing.expectEqualStrings("thickness", tokens[3].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[4].type);
    try std.testing.expectEqualStrings("1.6", tokens[4].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[5].type);

    // Third line: (legacy_teardrops no))
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[6].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[7].type);
    try std.testing.expectEqualStrings("legacy_teardrops", tokens[7].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[8].type);
    try std.testing.expectEqualStrings("no", tokens[8].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[9].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[10].type);
}

test "tokenize hexadecimal-like strings" {
    const input = "(layerselection \"0x00010fc_ffffffff\")";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 4), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[0].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[1].type);
    try std.testing.expectEqualStrings("layerselection", tokens[1].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.string, tokens[2].type);
    try std.testing.expectEqualStrings("0x00010fc_ffffffff", tokens[2].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[3].type);
}

test "tokenize scientific notation" {
    const input = "2.5e0";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 1), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[0].type);
    try std.testing.expectEqualStrings("2.5e0", tokens[0].value);
}

test "tokenize empty string" {
    const input = "\"\"";
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 1), tokens.len);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.string, tokens[0].type);
    try std.testing.expectEqualStrings("", tokens[0].value);
}

test "tokenize ato.kicad_pcb excerpt" {
    const input =
        \\(kicad_pcb 
        \\    (version 20240108)
        \\    (generator "atopile")
        \\    (generator_version "0.3.15-dev0"))
    ;
    const tokens = try sexp.tokenizer.tokenize(std.testing.allocator, input);
    defer std.testing.allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 15), tokens.len);

    // Check specific tokens
    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[0].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[1].type);
    try std.testing.expectEqualStrings("kicad_pcb", tokens[1].value);

    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[2].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[3].type);
    try std.testing.expectEqualStrings("version", tokens[3].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.number, tokens[4].type);
    try std.testing.expectEqualStrings("20240108", tokens[4].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[5].type);

    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[6].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[7].type);
    try std.testing.expectEqualStrings("generator", tokens[7].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.string, tokens[8].type);
    try std.testing.expectEqualStrings("atopile", tokens[8].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[9].type);

    try std.testing.expectEqual(sexp.tokenizer.TokenType.lparen, tokens[10].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.symbol, tokens[11].type);
    try std.testing.expectEqualStrings("generator_version", tokens[11].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.string, tokens[12].type);
    try std.testing.expectEqualStrings("0.3.15-dev0", tokens[12].value);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[13].type);
    try std.testing.expectEqual(sexp.tokenizer.TokenType.rparen, tokens[14].type);
}
