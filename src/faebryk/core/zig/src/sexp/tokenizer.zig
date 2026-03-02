const std = @import("std");

// S-Expression Tokenizer
//
// This module is responsible for tokenizing S-Expressions.
// It is used to convert the input string into a list of tokens.
// The tokens are then used to parse the S-Expression into a tree of nodes.

pub const TokenType = enum {
    lparen,
    rparen,
    symbol,
    number,
    string,
    comment,
};

const LocationScalar = u32;

pub const TokenLocation = struct {
    start: LocationScalar,
    end: LocationScalar,

    pub const none = TokenLocation{
        .start = std.math.maxInt(LocationScalar),
        .end = std.math.maxInt(LocationScalar),
    };

    pub inline fn isSet(self: TokenLocation) bool {
        return self.start != std.math.maxInt(LocationScalar) and self.end != std.math.maxInt(LocationScalar);
    }
};

pub const LocationInfo = struct {
    line: LocationScalar,
    column: LocationScalar,
};

pub const Token = struct {
    type: TokenType,
    start: LocationScalar,
    end: LocationScalar,

    pub inline fn slice(self: Token, input: []const u8) []const u8 {
        return input[@as(usize, self.start)..@as(usize, self.end)];
    }
};

inline fn narrowLocation(value: usize) LocationScalar {
    return std.math.cast(LocationScalar, value) orelse std.math.maxInt(LocationScalar);
}

pub const Tokenizer = struct {
    input: []const u8,
    position: usize,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator, input: []const u8) Tokenizer {
        return .{
            .input = input,
            .position = 0,
            .allocator = allocator,
        };
    }

    // Optimized with lookup table for faster character classification
    const whitespace_table = blk: {
        var table = [_]bool{false} ** 256;
        table[' '] = true;
        table['\t'] = true;
        table['\n'] = true;
        table['\r'] = true;
        break :blk table;
    };

    const symbol_char_table = blk: {
        var table = [_]bool{false} ** 256;
        // Letters
        var i: u8 = 'a';
        while (i <= 'z') : (i += 1) table[i] = true;
        i = 'A';
        while (i <= 'Z') : (i += 1) table[i] = true;
        // Digits
        i = '0';
        while (i <= '9') : (i += 1) table[i] = true;
        // Special chars
        table['_'] = true;
        table['-'] = true;
        table['.'] = true;
        table['/'] = true;
        table[':'] = true;
        table['+'] = true;
        table['='] = true;
        table['*'] = true;
        table['!'] = true;
        table['?'] = true;
        table['%'] = true;
        table['@'] = true;
        table['#'] = true;
        table['$'] = true;
        table['&'] = true;
        table['<'] = true;
        table['>'] = true;
        table['|'] = true;
        table['^'] = true;
        table['~'] = true;
        table['\''] = true;
        break :blk table;
    };

    const number_char_table = blk: {
        var table = [_]bool{false} ** 256;
        var i: u8 = '0';
        while (i <= '9') : (i += 1) table[i] = true;
        table['.'] = true;
        table['e'] = true;
        table['E'] = true;
        table['-'] = true;
        table['+'] = true;
        // Hex support
        i = 'a';
        while (i <= 'f') : (i += 1) table[i] = true;
        i = 'A';
        while (i <= 'F') : (i += 1) table[i] = true;
        table['x'] = true; // For 0x prefix
        table['_'] = true; // For underscores in numbers
        break :blk table;
    };

    inline fn isWhitespace(c: u8) bool {
        return whitespace_table[c];
    }

    inline fn isSymbolChar(c: u8) bool {
        return symbol_char_table[c];
    }

    inline fn isDigit(c: u8) bool {
        return c >= '0' and c <= '9';
    }

    inline fn isNumberStart(c: u8) bool {
        return isDigit(c) or c == '-' or c == '+';
    }

    inline fn isNumberChar(c: u8) bool {
        return number_char_table[c];
    }

    fn skipWhitespace(self: *Tokenizer) void {
        const input = self.input;
        const len = input.len;
        var pos = self.position;

        // Unroll common case of spaces/tabs
        while (pos < len) {
            const c = input[pos];
            if (isWhitespace(c)) {
                pos += 1;
            } else {
                break;
            }
        }

        self.position = pos;
    }

    fn readString(self: *Tokenizer) !Token {
        const start = self.position;
        var pos = self.position + 1; // skip opening quote
        const input = self.input;
        const len = input.len;

        while (pos < len) {
            const c = input[pos];
            if (c == '"') {
                self.position = pos + 1;
                return Token{
                    .type = .string,
                    .start = narrowLocation(start),
                    .end = narrowLocation(pos + 1),
                };
            }
            if (c == '\\' and pos + 1 < len) {
                pos += 2; // skip escape sequence
            } else {
                pos += 1;
            }
        }
        return error.UnterminatedString;
    }

    fn readNumber(self: *Tokenizer) Token {
        const start = self.position;
        var pos = self.position;
        const input = self.input;
        const len = input.len;

        // Handle sign
        if (pos < len and (input[pos] == '-' or input[pos] == '+')) {
            pos += 1;
        }

        // Read number chars - optimized inner loop
        while (pos < len and isNumberChar(input[pos])) {
            pos += 1;
        }

        self.position = pos;

        return Token{
            .type = .number,
            .start = narrowLocation(start),
            .end = narrowLocation(pos),
        };
    }

    fn readSymbol(self: *Tokenizer) Token {
        const start = self.position;
        var pos = self.position;
        const input = self.input;
        const len = input.len;

        // Optimized inner loop
        while (pos < len and isSymbolChar(input[pos])) {
            pos += 1;
        }

        self.position = pos;

        return Token{
            .type = .symbol,
            .start = narrowLocation(start),
            .end = narrowLocation(pos),
        };
    }

    fn readComment(self: *Tokenizer) Token {
        const start = self.position;
        var pos = self.position + 1; // skip semicolon
        const input = self.input;
        const len = input.len;

        // Read until newline or end of input
        while (pos < len and input[pos] != '\n') {
            pos += 1;
        }

        self.position = pos;

        return Token{
            .type = .comment,
            .start = narrowLocation(start),
            .end = narrowLocation(pos),
        };
    }

    pub fn nextToken(self: *Tokenizer) !?Token {
        self.skipWhitespace();

        if (self.position >= self.input.len) {
            return null;
        }

        const c = self.input[self.position];

        switch (c) {
            '(' => {
                const start = self.position;
                self.position += 1;
                return Token{
                    .type = .lparen,
                    .start = narrowLocation(start),
                    .end = narrowLocation(self.position),
                };
            },
            ')' => {
                const start = self.position;
                self.position += 1;
                return Token{
                    .type = .rparen,
                    .start = narrowLocation(start),
                    .end = narrowLocation(self.position),
                };
            },
            '"' => {
                return try self.readString();
            },
            ';' => {
                return self.readComment();
            },
            else => {
                // Check if it's a number
                if (isNumberStart(c)) {
                    // Look ahead to see if this is actually a number
                    if (c == '-' or c == '+') {
                        if (self.position + 1 < self.input.len and isDigit(self.input[self.position + 1])) {
                            return self.readNumber();
                        }
                    } else {
                        return self.readNumber();
                    }
                }

                // Otherwise treat as symbol
                if (isSymbolChar(c)) {
                    return self.readSymbol();
                }

                return error.InvalidCharacter;
            },
        }
    }

    pub fn tokenize(self: *Tokenizer) ![]Token {
        // First pass: count tokens exactly to avoid ArrayList growth overhead with arenas.
        var counter = Tokenizer.init(self.allocator, self.input);
        var token_count: usize = 0;
        while (try counter.nextToken()) |_| {
            token_count += 1;
        }

        var tokens = try self.allocator.alloc(Token, token_count);
        var i: usize = 0;
        while (try self.nextToken()) |token| {
            tokens[i] = token;
            i += 1;
        }
        return tokens;
    }
};

pub fn _tokenize(allocator: std.mem.Allocator, input: []const u8) ![]Token {
    var tokenizer = Tokenizer.init(allocator, input);
    return tokenizer.tokenize();
}

const WorkerContext = struct {
    data: []const u8,
    base_offset: LocationScalar = 0,
    allocator: std.mem.Allocator,
    result: ?[]Token = null,
    err: ?anyerror = null,
};

fn tokenizeWorker(context: *WorkerContext) void {
    var t = Tokenizer.init(context.allocator, context.data);
    context.result = t.tokenize() catch |err| {
        context.err = err;
        return;
    };

    if (context.base_offset == 0) return;
    for (context.result.?) |*token| {
        token.start = std.math.add(LocationScalar, token.start, context.base_offset) catch std.math.maxInt(LocationScalar);
        token.end = std.math.add(LocationScalar, token.end, context.base_offset) catch std.math.maxInt(LocationScalar);
    }
}

// Simple parallel tokenizer path
pub fn tokenize(allocator: std.mem.Allocator, data: []const u8) ![]Token {
    const cpu_count = try std.Thread.getCpuCount();

    const DATA_PER_THREAD_THRESOLD = 256 * 1024; // 128kB
    const thread_count = @max(1, @min(cpu_count, @divFloor(data.len, DATA_PER_THREAD_THRESOLD)));

    if (thread_count == 1) {
        return _tokenize(allocator, data);
    }

    // Split data into chunks
    var chunks = try allocator.alloc([]const u8, thread_count);
    defer allocator.free(chunks);
    var chunk_starts = try allocator.alloc(usize, thread_count);
    defer allocator.free(chunk_starts);
    const chunk_size = data.len / thread_count;

    var start: usize = 0;
    for (0..thread_count) |i| {
        chunk_starts[i] = start;
        const target_end = @min(start + chunk_size, data.len);
        var end = target_end;

        // Find split boundary at newline to reduce cross-chunk token breakage.
        while (end < data.len and data[end] != '\n') : (end += 1) {}

        chunks[i] = data[start..end];
        start = end;
    }

    // Create contexts and threads
    var contexts = try allocator.alloc(WorkerContext, thread_count);
    defer allocator.free(contexts);

    var threads = try allocator.alloc(std.Thread, thread_count);
    defer allocator.free(threads);

    for (0..thread_count) |i| {
        contexts[i] = .{
            .data = chunks[i],
            .base_offset = narrowLocation(chunk_starts[i]),
            .allocator = allocator,
        };
        threads[i] = try std.Thread.spawn(.{}, tokenizeWorker, .{&contexts[i]});
    }

    // Wait for completion
    for (threads) |thread| {
        thread.join();
    }

    // Check errors and count tokens
    var total_tokens: usize = 0;
    var chunk_error: ?anyerror = null;
    for (contexts) |ctx| {
        if (ctx.err) |err| {
            chunk_error = err;
            continue;
        }
        total_tokens += ctx.result.?.len;
    }

    if (chunk_error != null) {
        // Recover by falling back to single-thread tokenization.
        // This handles edge cases like chunk boundaries inside quoted strings.
        for (contexts) |ctx| {
            if (ctx.result) |tokens| allocator.free(tokens);
        }
        return _tokenize(allocator, data);
    }

    // Merge results
    var result = try allocator.alloc(Token, total_tokens);
    var offset: usize = 0;

    for (contexts) |ctx| {
        const tokens = ctx.result.?;
        @memcpy(result[offset..][0..tokens.len], tokens);
        offset += tokens.len;
        allocator.free(tokens);
    }

    return result;
}
