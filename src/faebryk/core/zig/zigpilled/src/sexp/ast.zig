const std = @import("std");
const tokenizer = @import("tokenizer.zig");

const Token = tokenizer.Token;
const TokenType = tokenizer.TokenType;

// S-Expression AST Node
pub const SExp = union(enum) {
    // Atom types
    symbol: []const u8,
    number: []const u8,
    string: []const u8,

    // List type
    list: []SExp,

    // Special type for comments (optional - can be ignored)
    comment: []const u8,

    pub fn deinit(self: *SExp, allocator: std.mem.Allocator) void {
        switch (self.*) {
            .list => |children| {
                for (children) |*child| {
                    child.deinit(allocator);
                }
                allocator.free(children);
            },
            else => {},
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

        switch (self) {
            .symbol => |s| try writer.print("{s}", .{s}),
            .number => |n| try writer.print("{s}", .{n}),
            .string => |s| try writer.print("\"{s}\"", .{s}),
            .comment => |c| try writer.print(";{s}", .{c}),
            .list => |items| {
                try writer.writeAll("(");
                for (items, 0..) |item, i| {
                    if (i > 0) try writer.writeAll(" ");
                    try item.format("", .{}, writer);
                }
                try writer.writeAll(")");
            },
        }
    }
};

pub const ParseError = error{
    UnexpectedRightParen,
    UnterminatedList,
    OutOfMemory,
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
            .lparen => return try self.parseList(),
            .rparen => return error.UnexpectedRightParen,
            .symbol => return SExp{ .symbol = token.value },
            .number => return SExp{ .number = token.value },
            .string => return SExp{ .string = token.value },
            .comment => return SExp{ .comment = token.value },
        }
    }

    fn parseList(self: *Parser) ParseError!SExp {
        var items = std.ArrayList(SExp).init(self.allocator);
        defer items.deinit();

        while (self.position < self.tokens.len) {
            const next_token = self.tokens[self.position];

            if (next_token.type == .rparen) {
                self.position += 1;
                return SExp{ .list = try items.toOwnedSlice() };
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

// Parse a single S-expression
pub fn parse(allocator: std.mem.Allocator, tokens: []const Token) ParseError!?SExp {
    var parser = Parser.init(allocator, tokens);
    return parser.parse();
}

// Helper functions for working with S-expressions -------------------------------------
pub fn isList(sexp: SExp) bool {
    return switch (sexp) {
        .list => true,
        else => false,
    };
}

pub fn isAtom(sexp: SExp) bool {
    return switch (sexp) {
        .symbol, .number, .string => true,
        else => false,
    };
}

pub fn listLen(sexp: SExp) ?usize {
    return switch (sexp) {
        .list => |items| items.len,
        else => null,
    };
}

pub fn getSymbol(sexp: SExp) ?[]const u8 {
    return switch (sexp) {
        .symbol => |s| s,
        else => null,
    };
}

pub fn getList(sexp: SExp) ?[]SExp {
    return switch (sexp) {
        .list => |items| items,
        else => null,
    };
}

// Helper to get the first element of a list (car in Lisp terms)
pub fn first(sexp: SExp) ?*const SExp {
    return switch (sexp) {
        .list => |items| if (items.len > 0) &items[0] else null,
        else => null,
    };
}

// Helper to get the rest of a list (cdr in Lisp terms)
pub fn rest(sexp: SExp) ?[]const SExp {
    return switch (sexp) {
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
