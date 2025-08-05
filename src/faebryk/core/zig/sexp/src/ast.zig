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

    pub fn repr(
        self: SExp,
        writer: anytype,
    ) !void {
        switch (self.value) {
            .symbol => |s| try writer.print("Symbol({s})", .{s}),
            .number => |n| try writer.print("Number({s})", .{n}),
            .string => |s| try writer.print("String({s})", .{s}),
            .comment => |c| try writer.print("Comment({s})", .{c}),
            .list => |items| {
                try writer.writeAll("List(");
                for (items, 0..) |item, i| {
                    if (i > 0) try writer.writeAll(" ");
                    try item.repr(writer);
                }
                try writer.writeAll(")");
            },
        }
    }

    pub fn str(self: SExp, writer: anytype) !void {
        try self.strDepth(writer, 0, true);
    }

    fn strDepth(self: SExp, writer: anytype, depth: usize, pretty: bool) !void {
        switch (self.value) {
            .symbol => |s| try writer.print("{s}", .{s}),
            .number => |n| try writer.print("{s}", .{n}),
            .string => |s| try writer.print("\"{s}\"", .{s}),
            .comment => |c| try writer.print(";{s}", .{c}),
            .list => |items| {
                // Check if this is a leaf expression (contains only non-list elements)
                var is_leaf = true;
                for (items) |item| {
                    if (item.value == .list) {
                        is_leaf = false;
                        break;
                    }
                }

                try writer.writeAll("(");

                if (pretty and !is_leaf and items.len > 0) {
                    // Non-leaf expression with pretty printing
                    for (items, 0..) |item, i| {
                        if (i > 0) {
                            // Add newline and indentation before non-first elements
                            try writer.writeAll("\n");
                            // 4 spaces per depth level
                            for (0..(depth + 1) * 4) |_| {
                                try writer.writeAll(" ");
                            }
                        }
                        try item.strDepth(writer, depth + 1, pretty);
                    }
                    if (items.len > 1) {
                        // Add newline and indentation before closing paren
                        try writer.writeAll("\n");
                        for (0..depth * 4) |_| {
                            try writer.writeAll(" ");
                        }
                    }
                } else {
                    // Leaf expression or non-pretty mode
                    for (items, 0..) |item, i| {
                        if (i > 0) try writer.writeAll(" ");
                        try item.strDepth(writer, depth + 1, pretty);
                    }
                }

                try writer.writeAll(")");
            },
        }
    }

    pub fn format(
        self: SExp,
        comptime fmt: []const u8,
        options: std.fmt.FormatOptions,
        writer: anytype,
    ) !void {
        _ = fmt;
        _ = options;

        try self.repr(writer);
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
