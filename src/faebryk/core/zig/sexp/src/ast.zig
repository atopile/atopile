const std = @import("std");
const tokenizer = @import("tokenizer.zig");

const Token = tokenizer.Token;
const TokenType = tokenizer.TokenType;
pub const TokenLocation = tokenizer.TokenLocation;

// S-Expression value type
pub const SExpValue = union(enum) {
    // Atom types
    symbol: []const u8,
    number: []const u8,
    string: []const u8,

    // List type
    list: []SExp,

    // Special type for comments (optional - can be ignored)
    comment: []const u8,
};

// S-Expression with location
pub const SExp = struct {
    value: SExpValue,
    location: ?TokenLocation = null,

    pub fn deinit(self: *SExp, allocator: std.mem.Allocator) void {
        switch (self.value) {
            .list => |children| {
                for (children) |*child| {
                    child.deinit(allocator);
                }
                allocator.free(children);
            },
            else => {},
        }
    }

    pub fn prettify_sexp_string(allocator: std.mem.Allocator, sexp_raw: []const u8) ![]const u8 {
        var out = std.ArrayList(u8).init(allocator);
        defer out.deinit();

        var level: usize = 0;
        var in_quotes = false;
        var in_leaf_expr = true;

        for (sexp_raw) |c| {
            if (c == '"') {
                in_quotes = !in_quotes;
            }

            if (in_quotes) {
                // When in quotes, preserve everything as-is
                try out.append(c);
            } else if (c == '\n') {
                // Skip newlines when not in quotes
                continue;
            } else if (c == ' ' and out.items.len > 0 and out.items[out.items.len - 1] == ' ') {
                // Skip consecutive spaces
                continue;
            } else if (c == '(') {
                in_leaf_expr = true;
                if (level != 0) {
                    // Remove trailing space if any
                    if (out.items.len > 0 and out.items[out.items.len - 1] == ' ') {
                        _ = out.pop();
                    }
                    // Add newline and indentation
                    try out.append('\n');
                    for (0..level * 4) |_| {
                        try out.append(' ');
                    }
                }
                level += 1;
                try out.append(c);
            } else if (c == ')') {
                // Remove trailing space if any
                if (out.items.len > 0 and out.items[out.items.len - 1] == ' ') {
                    _ = out.pop();
                }
                level -= 1;
                if (!in_leaf_expr) {
                    // Add newline and indentation before closing paren
                    try out.append('\n');
                    for (0..level * 4) |_| {
                        try out.append(' ');
                    }
                }
                in_leaf_expr = false;
                try out.append(c);
            } else {
                try out.append(c);
            }
        }

        // Convert to string and process lines (similar to Python's final step)
        const result_str = try out.toOwnedSlice();

        // Split into lines and trim (except first line - KiCad workaround)
        var lines = std.ArrayList([]const u8).init(allocator);
        defer {
            for (lines.items) |line| {
                allocator.free(line);
            }
            lines.deinit();
        }

        var line_start: usize = 0;
        var i: usize = 0;
        while (i <= result_str.len) : (i += 1) {
            if (i == result_str.len or result_str[i] == '\n') {
                const line = result_str[line_start..i];
                const trimmed_line = if (lines.items.len > 0)
                    std.mem.trimRight(u8, line, " \t")
                else
                    line;
                const owned_line = try allocator.dupe(u8, trimmed_line);
                try lines.append(owned_line);
                line_start = i + 1;
            }
        }

        // Join lines with newlines
        var final_result = std.ArrayList(u8).init(allocator);
        defer final_result.deinit();

        for (lines.items, 0..) |line, idx| {
            if (idx > 0) {
                try final_result.append('\n');
            }
            try final_result.appendSlice(line);
        }

        allocator.free(result_str);
        return try final_result.toOwnedSlice();
    }

    pub fn str(self: SExp, writer: anytype) !void {
        switch (self.value) {
            .symbol => |s| try writer.print("{s}", .{s}),
            .number => |n| try writer.print("{s}", .{n}),
            .string => |s| try writer.print("\"{s}\"", .{s}),
            .comment => |c| try writer.print(";{s}", .{c}),
            .list => |items| {
                try writer.writeAll("(");
                for (items, 0..) |item, i| {
                    if (i > 0) try writer.writeAll(" ");
                    try item.str(writer);
                }
                try writer.writeAll(")");
            },
        }
    }

    pub fn pretty(self: SExp, allocator: std.mem.Allocator) ![]const u8 {
        var in = std.ArrayList(u8).init(allocator);
        defer in.deinit();

        try self.str(in.writer());
        const out = try prettify_sexp_string(allocator, in.items);
        return out;
    }

    pub fn format(
        self: SExp,
        comptime fmt: []const u8,
        options: std.fmt.FormatOptions,
        writer: anytype,
    ) !void {
        _ = fmt;
        _ = options;

        // TODO pretty
        try self.str(writer);
    }
};

pub const ParseError = error{
    UnexpectedRightParen,
    UnterminatedList,
    OutOfMemory,
    EmptyFile,
};

pub const Parser = struct {
    tokens: []const Token,
    position: usize,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator, tokens: []const Token) Parser {
        return .{
            .tokens = tokens,
            .position = 0,
            .allocator = allocator,
        };
    }

    pub fn parse(self: *Parser) ParseError!?SExp {
        if (self.position >= self.tokens.len) {
            return null;
        }

        const token = self.tokens[self.position];
        self.position += 1;

        switch (token.type) {
            .lparen => return try self.parseList(token.location),
            .rparen => return error.UnexpectedRightParen,
            .symbol => return SExp{ .value = .{ .symbol = token.value }, .location = token.location },
            .number => return SExp{ .value = .{ .number = token.value }, .location = token.location },
            .string => return SExp{ .value = .{ .string = token.value }, .location = token.location },
            .comment => return SExp{ .value = .{ .comment = token.value }, .location = token.location },
        }
    }

    fn parseList(self: *Parser, start_location: TokenLocation) ParseError!SExp {
        var items = std.ArrayList(SExp).init(self.allocator);
        defer items.deinit();

        while (self.position < self.tokens.len) {
            const next_token = self.tokens[self.position];

            if (next_token.type == .rparen) {
                const end_location = next_token.location;
                self.position += 1;
                return SExp{ .value = .{ .list = try items.toOwnedSlice() }, .location = .{
                    .start = start_location.start,
                    .end = end_location.end,
                } };
            }

            if (try self.parse()) |sexp| {
                try items.append(sexp);
            } else {
                break;
            }
        }

        return error.UnterminatedList;
    }
};

// Parse with arena allocator for better performance!
// Parse a single S-expression
pub fn parse(allocator: std.mem.Allocator, tokens: []const Token) ParseError!SExp {
    var parser = Parser.init(allocator, tokens);
    return try parser.parse() orelse return error.EmptyFile;
}

// Helper functions for working with S-expressions -------------------------------------
pub fn isList(sexp: SExp) bool {
    return switch (sexp.value) {
        .list => true,
        else => false,
    };
}

pub fn isAtom(sexp: SExp) bool {
    return switch (sexp.value) {
        .symbol, .number, .string => true,
        else => false,
    };
}

pub fn listLen(sexp: SExp) ?usize {
    return switch (sexp.value) {
        .list => |items| items.len,
        else => null,
    };
}

pub fn getSymbol(sexp: SExp) ?[]const u8 {
    return switch (sexp.value) {
        .symbol => |s| s,
        else => null,
    };
}

pub fn getList(sexp: SExp) ?[]SExp {
    return switch (sexp.value) {
        .list => |items| items,
        else => null,
    };
}

// Helper to get the first element of a list (car in Lisp terms)
pub fn first(sexp: SExp) ?*const SExp {
    return switch (sexp.value) {
        .list => |items| if (items.len > 0) &items[0] else null,
        else => null,
    };
}

// Helper to get the rest of a list (cdr in Lisp terms)
pub fn rest(sexp: SExp) ?[]const SExp {
    return switch (sexp.value) {
        .list => |items| if (items.len > 1) items[1..] else &[_]SExp{},
        else => null,
    };
}

// Find a specific key-value pair in a property list
pub fn findValue(sexp: SExp, key: []const u8) ?*const SExp {
    const items = getList(sexp) orelse return null;

    var i: usize = 0;
    while (i + 1 < items.len) : (i += 2) {
        if (getSymbol(items[i])) |sym| {
            if (std.mem.eql(u8, sym, key)) {
                return &items[i + 1];
            }
        }
    }

    return null;
}

// Check if a list starts with a specific symbol
pub fn isForm(sexp: SExp, name: []const u8) bool {
    const items = getList(sexp) orelse return false;
    if (items.len == 0) return false;
    const sym = getSymbol(items[0]) orelse return false;
    return std.mem.eql(u8, sym, name);
}
