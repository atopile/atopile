const std = @import("std");

/// STEP Part 21 Tokenizer
/// Tokenizes ISO 10303-21 format files into a stream of tokens.

pub const TokenType = enum {
    // Structural
    lparen, // (
    rparen, // )
    semicolon, // ;
    equals, // =
    comma, // ,
    slash, // /

    // Values
    entity_id, // #123
    keyword, // UPPERCASE_WITH_UNDERSCORES (type names, keywords)
    string, // 'single quoted'
    integer, // 123, -456
    real, // 1.23, -4.56E-07
    enumeration, // .ENUM_VALUE.
    undefined, // *
    omitted, // $

    // Comments
    comment, // /* ... */
};

pub const LocationInfo = struct {
    line: usize,
    column: usize,
};

pub const TokenLocation = struct {
    start: LocationInfo,
    end: LocationInfo,
};

pub const Token = struct {
    type: TokenType,
    value: []const u8,
    location: TokenLocation,
};

pub const TokenizeError = error{
    UnterminatedString,
    UnterminatedComment,
    InvalidCharacter,
    InvalidEntityId,
    InvalidNumber,
    InvalidEnumeration,
    OutOfMemory,
};

pub const Tokenizer = struct {
    input: []const u8,
    position: usize,
    location: LocationInfo,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator, input: []const u8) Tokenizer {
        return .{
            .input = input,
            .position = 0,
            .location = .{ .line = 1, .column = 1 },
            .allocator = allocator,
        };
    }

    // Lookup tables for fast character classification
    const whitespace_table = blk: {
        var table = [_]bool{false} ** 256;
        table[' '] = true;
        table['\t'] = true;
        table['\n'] = true;
        table['\r'] = true;
        break :blk table;
    };

    const keyword_start_table = blk: {
        var table = [_]bool{false} ** 256;
        var i: u8 = 'A';
        while (i <= 'Z') : (i += 1) table[i] = true;
        table['_'] = true;
        break :blk table;
    };

    const keyword_char_table = blk: {
        var table = [_]bool{false} ** 256;
        var i: u8 = 'A';
        while (i <= 'Z') : (i += 1) table[i] = true;
        i = 'a';
        while (i <= 'z') : (i += 1) table[i] = true;
        i = '0';
        while (i <= '9') : (i += 1) table[i] = true;
        table['_'] = true;
        break :blk table;
    };

    const digit_table = blk: {
        var table = [_]bool{false} ** 256;
        var i: u8 = '0';
        while (i <= '9') : (i += 1) table[i] = true;
        break :blk table;
    };

    inline fn isWhitespace(c: u8) bool {
        return whitespace_table[c];
    }

    inline fn isKeywordStart(c: u8) bool {
        return keyword_start_table[c];
    }

    inline fn isKeywordChar(c: u8) bool {
        return keyword_char_table[c];
    }

    inline fn isDigit(c: u8) bool {
        return digit_table[c];
    }

    fn skipWhitespace(self: *Tokenizer) void {
        const input = self.input;
        const len = input.len;
        var pos = self.position;
        var line = self.location.line;
        var column = self.location.column;

        while (pos < len) {
            const c = input[pos];
            if (c == ' ' or c == '\t') {
                pos += 1;
                column += 1;
            } else if (c == '\n') {
                pos += 1;
                line += 1;
                column = 1;
            } else if (c == '\r') {
                pos += 1;
                // Handle \r\n as single newline
                if (pos < len and input[pos] == '\n') {
                    pos += 1;
                }
                line += 1;
                column = 1;
            } else {
                break;
            }
        }

        self.position = pos;
        self.location = .{ .line = line, .column = column };
    }

    fn readString(self: *Tokenizer) TokenizeError!Token {
        const start_location = self.location;
        const start = self.position;
        var pos = self.position + 1; // skip opening quote
        var column = self.location.column + 1;
        var line = self.location.line;
        const input = self.input;
        const len = input.len;

        while (pos < len) {
            const c = input[pos];
            if (c == '\'') {
                // Check for escaped quote ('')
                if (pos + 1 < len and input[pos + 1] == '\'') {
                    pos += 2;
                    column += 2;
                    continue;
                }
                // End of string
                self.position = pos + 1;
                self.location.column = column + 1;
                self.location.line = line;
                return Token{
                    .type = .string,
                    .value = input[start + 1 .. pos], // exclude quotes
                    .location = .{
                        .start = start_location,
                        .end = self.location,
                    },
                };
            }
            if (c == '\n') {
                line += 1;
                column = 1;
            } else {
                column += 1;
            }
            pos += 1;
        }
        return error.UnterminatedString;
    }

    fn readComment(self: *Tokenizer) TokenizeError!Token {
        const start_location = self.location;
        const start = self.position;
        var pos = self.position + 2; // skip /*
        var column = self.location.column + 2;
        var line = self.location.line;
        const input = self.input;
        const len = input.len;

        while (pos + 1 < len) {
            if (input[pos] == '*' and input[pos + 1] == '/') {
                self.position = pos + 2;
                self.location.column = column + 2;
                self.location.line = line;
                return Token{
                    .type = .comment,
                    .value = input[start + 2 .. pos], // exclude /* and */
                    .location = .{
                        .start = start_location,
                        .end = self.location,
                    },
                };
            }
            if (input[pos] == '\n') {
                line += 1;
                column = 1;
            } else {
                column += 1;
            }
            pos += 1;
        }
        return error.UnterminatedComment;
    }

    fn readEntityId(self: *Tokenizer) TokenizeError!Token {
        const start_location = self.location;
        const start = self.position;
        var pos = self.position + 1; // skip #
        const input = self.input;
        const len = input.len;

        // Read digits
        while (pos < len and isDigit(input[pos])) {
            pos += 1;
        }

        if (pos == start + 1) {
            return error.InvalidEntityId;
        }

        self.location.column += pos - self.position;
        self.position = pos;

        return Token{
            .type = .entity_id,
            .value = input[start + 1 .. pos], // exclude #
            .location = .{
                .start = start_location,
                .end = self.location,
            },
        };
    }

    fn readKeyword(self: *Tokenizer) Token {
        const start_location = self.location;
        const start = self.position;
        var pos = self.position;
        const input = self.input;
        const len = input.len;

        while (pos < len and isKeywordChar(input[pos])) {
            pos += 1;
        }

        self.location.column += pos - self.position;
        self.position = pos;

        return Token{
            .type = .keyword,
            .value = input[start..pos],
            .location = .{
                .start = start_location,
                .end = self.location,
            },
        };
    }

    fn readNumber(self: *Tokenizer) TokenizeError!Token {
        const start_location = self.location;
        const start = self.position;
        var pos = self.position;
        const input = self.input;
        const len = input.len;
        var is_real = false;

        // Handle optional sign
        if (pos < len and (input[pos] == '-' or input[pos] == '+')) {
            pos += 1;
        }

        // Read integer part
        while (pos < len and isDigit(input[pos])) {
            pos += 1;
        }

        // Check for decimal point
        if (pos < len and input[pos] == '.') {
            is_real = true;
            pos += 1;
            // Read fractional part
            while (pos < len and isDigit(input[pos])) {
                pos += 1;
            }
        }

        // Check for exponent
        if (pos < len and (input[pos] == 'E' or input[pos] == 'e')) {
            is_real = true;
            pos += 1;
            // Handle optional sign in exponent
            if (pos < len and (input[pos] == '-' or input[pos] == '+')) {
                pos += 1;
            }
            // Read exponent digits
            while (pos < len and isDigit(input[pos])) {
                pos += 1;
            }
        }

        self.location.column += pos - self.position;
        self.position = pos;

        return Token{
            .type = if (is_real) .real else .integer,
            .value = input[start..pos],
            .location = .{
                .start = start_location,
                .end = self.location,
            },
        };
    }

    fn readEnumeration(self: *Tokenizer) TokenizeError!Token {
        const start_location = self.location;
        const start = self.position;
        var pos = self.position + 1; // skip leading .
        const input = self.input;
        const len = input.len;

        // Read enumeration name
        while (pos < len and (isKeywordChar(input[pos]) or input[pos] == '.')) {
            if (input[pos] == '.') {
                // End of enumeration
                self.position = pos + 1;
                self.location.column += pos + 1 - start;
                return Token{
                    .type = .enumeration,
                    .value = input[start + 1 .. pos], // exclude dots
                    .location = .{
                        .start = start_location,
                        .end = self.location,
                    },
                };
            }
            pos += 1;
        }

        return error.InvalidEnumeration;
    }

    pub fn nextToken(self: *Tokenizer) TokenizeError!?Token {
        self.skipWhitespace();

        if (self.position >= self.input.len) {
            return null;
        }

        const c = self.input[self.position];
        const start_location = self.location;

        switch (c) {
            '(' => {
                self.position += 1;
                self.location.column += 1;
                return Token{
                    .type = .lparen,
                    .value = "(",
                    .location = .{ .start = start_location, .end = self.location },
                };
            },
            ')' => {
                self.position += 1;
                self.location.column += 1;
                return Token{
                    .type = .rparen,
                    .value = ")",
                    .location = .{ .start = start_location, .end = self.location },
                };
            },
            ';' => {
                self.position += 1;
                self.location.column += 1;
                return Token{
                    .type = .semicolon,
                    .value = ";",
                    .location = .{ .start = start_location, .end = self.location },
                };
            },
            '=' => {
                self.position += 1;
                self.location.column += 1;
                return Token{
                    .type = .equals,
                    .value = "=",
                    .location = .{ .start = start_location, .end = self.location },
                };
            },
            ',' => {
                self.position += 1;
                self.location.column += 1;
                return Token{
                    .type = .comma,
                    .value = ",",
                    .location = .{ .start = start_location, .end = self.location },
                };
            },
            '/' => {
                // Check for comment
                if (self.position + 1 < self.input.len and self.input[self.position + 1] == '*') {
                    return try self.readComment();
                }
                self.position += 1;
                self.location.column += 1;
                return Token{
                    .type = .slash,
                    .value = "/",
                    .location = .{ .start = start_location, .end = self.location },
                };
            },
            '\'' => return try self.readString(),
            '#' => return try self.readEntityId(),
            '*' => {
                self.position += 1;
                self.location.column += 1;
                return Token{
                    .type = .undefined,
                    .value = "*",
                    .location = .{ .start = start_location, .end = self.location },
                };
            },
            '$' => {
                self.position += 1;
                self.location.column += 1;
                return Token{
                    .type = .omitted,
                    .value = "$",
                    .location = .{ .start = start_location, .end = self.location },
                };
            },
            '.' => return try self.readEnumeration(),
            '-', '+', '0'...'9' => return try self.readNumber(),
            else => {
                if (isKeywordStart(c)) {
                    return self.readKeyword();
                }
                return error.InvalidCharacter;
            },
        }
    }

    pub fn tokenize(self: *Tokenizer) TokenizeError![]Token {
        var tokens = std.ArrayList(Token).init(self.allocator);
        errdefer tokens.deinit();

        while (try self.nextToken()) |token| {
            try tokens.append(token);
        }

        return tokens.toOwnedSlice();
    }
};

/// Tokenize a STEP file into tokens
pub fn tokenize(allocator: std.mem.Allocator, input: []const u8) TokenizeError![]Token {
    var tokenizer = Tokenizer.init(allocator, input);
    return tokenizer.tokenize();
}

// Tests
test "tokenize simple entity" {
    const allocator = std.testing.allocator;
    const input = "#1 = CARTESIAN_POINT ( 'NONE', ( 0.0, 1.0, 2.0 ) ) ;";
    const tokens = try tokenize(allocator, input);
    defer allocator.free(tokens);

    // Tokens: #1, =, CARTESIAN_POINT, (, 'NONE', ,, (, 0.0, ,, 1.0, ,, 2.0, ), ), ;
    try std.testing.expect(tokens.len >= 15);
    try std.testing.expectEqual(TokenType.entity_id, tokens[0].type);
    try std.testing.expectEqualStrings("1", tokens[0].value);
    try std.testing.expectEqual(TokenType.equals, tokens[1].type);
    try std.testing.expectEqual(TokenType.keyword, tokens[2].type);
    try std.testing.expectEqualStrings("CARTESIAN_POINT", tokens[2].value);
}

test "tokenize enumeration" {
    const allocator = std.testing.allocator;
    const input = ".T. .F. .MILLI. .METRE.";
    const tokens = try tokenize(allocator, input);
    defer allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 4), tokens.len);
    try std.testing.expectEqual(TokenType.enumeration, tokens[0].type);
    try std.testing.expectEqualStrings("T", tokens[0].value);
    try std.testing.expectEqual(TokenType.enumeration, tokens[3].type);
    try std.testing.expectEqualStrings("METRE", tokens[3].value);
}

test "tokenize scientific notation" {
    const allocator = std.testing.allocator;
    const input = "1.23E-05 -4.56E+10 7.89e12";
    const tokens = try tokenize(allocator, input);
    defer allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 3), tokens.len);
    try std.testing.expectEqual(TokenType.real, tokens[0].type);
    try std.testing.expectEqualStrings("1.23E-05", tokens[0].value);
}

test "tokenize string with escaped quote" {
    const allocator = std.testing.allocator;
    const input = "'hello''world'";
    const tokens = try tokenize(allocator, input);
    defer allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 1), tokens.len);
    try std.testing.expectEqual(TokenType.string, tokens[0].type);
    try std.testing.expectEqualStrings("hello''world", tokens[0].value);
}

test "tokenize special values" {
    const allocator = std.testing.allocator;
    const input = "* $ *";
    const tokens = try tokenize(allocator, input);
    defer allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 3), tokens.len);
    try std.testing.expectEqual(TokenType.undefined, tokens[0].type);
    try std.testing.expectEqual(TokenType.omitted, tokens[1].type);
}
