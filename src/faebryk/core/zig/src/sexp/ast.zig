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
            .string => |string_val| {
                // Free the duplicated string
                if (string_val.len > 0) {
                    allocator.free(string_val);
                }
            },
            .symbol => |sym| {
                // Free the duplicated symbol
                if (sym.len > 0) {
                    allocator.free(sym);
                }
            },
            .number => |num| {
                // Free the duplicated number
                if (num.len > 0) {
                    allocator.free(num);
                }
            },
            .comment => |comment| {
                // Free the duplicated comment
                if (comment.len > 0) {
                    allocator.free(comment);
                }
            },
        }
    }

    pub fn prettify_sexp_string(allocator: std.mem.Allocator, sexp_raw: []const u8) ![]const u8 {
        return prettify_sexp_string_kicad(allocator, sexp_raw, false);
    }

    pub fn prettify_sexp_string_kicad(allocator: std.mem.Allocator, source: []const u8, compact_save: bool) ![]const u8 {
        // Configuration - matching KiCad exactly
        const quote_char: u8 = '"';
        const indent_char: u8 = '\t';
        const indent_size: usize = 1;

        // Special case limits from KiCad
        const xy_special_case_column_limit: usize = 99;
        const consecutive_token_wrap_threshold: usize = 72;

        var formatted = std.ArrayList(u8).init(allocator);
        defer formatted.deinit();
        try formatted.ensureTotalCapacity(source.len);

        var cursor: usize = 0;
        var list_depth: usize = 0;
        var last_non_whitespace: u8 = 0;
        var in_quote = false;
        var has_inserted_space = false;
        var in_multi_line_list = false;
        var in_xy = false;
        var in_short_form = false;
        var short_form_depth: usize = 0;
        var column: usize = 0;
        var backslash_count: usize = 0;

        const isWhitespace = struct {
            fn call(char: u8) bool {
                return char == ' ' or char == '\t' or char == '\n' or char == '\r';
            }
        }.call;

        const nextNonWhitespace = struct {
            fn call(src: []const u8, pos: usize) u8 {
                var seek = pos;
                while (seek < src.len and isWhitespace(src[seek])) {
                    seek += 1;
                }
                if (seek >= src.len) return 0;
                return src[seek];
            }
        }.call;

        const isXY = struct {
            fn call(src: []const u8, pos: usize) bool {
                if (pos + 3 >= src.len) return false;
                return src[pos + 1] == 'x' and src[pos + 2] == 'y' and src[pos + 3] == ' ';
            }
        }.call;

        const isShortFormToken = struct {
            fn call(src: []const u8, pos: usize) bool {
                var seek = pos + 1;
                var token = std.ArrayList(u8).init(std.heap.page_allocator);
                defer token.deinit();

                while (seek < src.len and std.ascii.isAlphabetic(src[seek])) {
                    token.append(src[seek]) catch return false;
                    seek += 1;
                }

                const token_str = token.items;
                return std.mem.eql(u8, token_str, "font") or
                    std.mem.eql(u8, token_str, "stroke") or
                    std.mem.eql(u8, token_str, "fill") or
                    std.mem.eql(u8, token_str, "teardrop") or
                    std.mem.eql(u8, token_str, "offset") or
                    std.mem.eql(u8, token_str, "rotate") or
                    std.mem.eql(u8, token_str, "scale");
            }
        }.call;

        while (cursor < source.len) {
            const next = nextNonWhitespace(source, cursor);

            if (isWhitespace(source[cursor]) and !in_quote) {
                if (!has_inserted_space and // Only permit one space between chars
                    list_depth > 0 and // Do not permit spaces in outer list
                    last_non_whitespace != '(' and // Remove extra space after start of list
                    next != ')' and // Remove extra space before end of list
                    next != '(') // Remove extra space before newline
                {
                    if (in_xy or column < consecutive_token_wrap_threshold) {
                        // Note that we only insert spaces here, no matter what kind of whitespace is
                        // in the input. Newlines will be inserted as needed by the logic below.
                        try formatted.append(' ');
                        column += 1;
                    } else if (in_short_form) {
                        try formatted.append(' ');
                    } else {
                        try formatted.append('\n');
                        for (0..list_depth * indent_size) |_| {
                            try formatted.append(indent_char);
                        }
                        column = list_depth * indent_size;
                        in_multi_line_list = true;
                    }
                    has_inserted_space = true;
                }
            } else {
                has_inserted_space = false;

                if (source[cursor] == '(' and !in_quote) {
                    const current_is_xy = isXY(source, cursor);
                    const current_is_short_form = compact_save and isShortFormToken(source, cursor);

                    if (formatted.items.len == 0) {
                        try formatted.append('(');
                        column += 1;
                    } else if (in_xy and current_is_xy and column < xy_special_case_column_limit) {
                        // List-of-points special case
                        try formatted.appendSlice(" (");
                        column += 2;
                    } else if (in_short_form) {
                        try formatted.appendSlice(" (");
                        column += 2;
                    } else {
                        try formatted.append('\n');
                        for (0..list_depth * indent_size) |_| {
                            try formatted.append(indent_char);
                        }
                        try formatted.append('(');
                        column = list_depth * indent_size + 1;
                    }

                    in_xy = current_is_xy;

                    if (current_is_short_form) {
                        in_short_form = true;
                        short_form_depth = list_depth;
                    }

                    list_depth += 1;
                } else if (source[cursor] == ')' and !in_quote) {
                    if (list_depth > 0) {
                        list_depth -= 1;
                    }

                    if (in_short_form) {
                        try formatted.append(')');
                        column += 1;
                    } else if (last_non_whitespace == ')' or in_multi_line_list) {
                        try formatted.append('\n');
                        for (0..list_depth * indent_size) |_| {
                            try formatted.append(indent_char);
                        }
                        try formatted.append(')');
                        column = list_depth * indent_size + 1;
                        in_multi_line_list = false;
                    } else {
                        try formatted.append(')');
                        column += 1;
                    }

                    if (short_form_depth == list_depth) {
                        in_short_form = false;
                        short_form_depth = 0;
                    }
                } else {
                    // The output formatter escapes double-quotes (like \")
                    // But a corner case is a sequence like \\"
                    // therefore a '\' is attached to a '"' if a odd number of '\' is detected
                    if (source[cursor] == '\\') {
                        backslash_count += 1;
                    } else if (source[cursor] == quote_char and (backslash_count & 1) == 0) {
                        in_quote = !in_quote;
                    }

                    if (source[cursor] != '\\') {
                        backslash_count = 0;
                    }

                    try formatted.append(source[cursor]);
                    column += 1;
                }

                last_non_whitespace = source[cursor];
            }

            cursor += 1;
        }

        // newline required at end of line / file for POSIX compliance. Keeps git diffs clean.
        try formatted.append('\n');

        return try formatted.toOwnedSlice();
    }

    pub fn str(self: SExp, writer: anytype) !void {
        switch (self.value) {
            .symbol => |s| try writer.print("{s}", .{s}),
            .number => |n| try writer.print("{s}", .{n}),
            .string => |s| try _write_escaped_string(s, writer),
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

// TODO: string escaping is super slow, consider using single quotes instead in the params

// Helper function to escape quotes in strings
fn _write_escaped_string(str: []const u8, writer: anytype) !void {
    // Count the number of quotes to determine the required size
    try writer.writeByte('"');
    var last_char: u8 = 0;
    for (str) |c| {
        if (c == '"' and last_char != '\\') try writer.writeByte('\\');
        try writer.writeByte(c);
        last_char = c;
    }
    try writer.writeByte('"');
}

fn _unescape_string(allocator: std.mem.Allocator, str: []const u8) ![]const u8 {
    var unescaped = std.ArrayList(u8).init(allocator);
    // Pre-allocate with known maximum capacity since unescaping can only remove characters
    try unescaped.ensureTotalCapacity(str.len);

    for (str) |c| {
        if (c != '\\') {
            try unescaped.append(c);
        }
    }
    return try unescaped.toOwnedSlice();
}

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
            .symbol => {
                // CRITICAL FIX: Duplicate symbol to prevent use-after-free
                const duped = self.allocator.alloc(u8, token.value.len) catch return error.OutOfMemory;
                @memcpy(duped, token.value);
                return SExp{ .value = .{ .symbol = duped }, .location = token.location };
            },
            .number => {
                // CRITICAL FIX: Duplicate number to prevent use-after-free
                const duped = self.allocator.alloc(u8, token.value.len) catch return error.OutOfMemory;
                @memcpy(duped, token.value);
                return SExp{ .value = .{ .number = duped }, .location = token.location };
            },
            .string => {
                // CRITICAL FIX: Duplicate string to prevent use-after-free
                // token.value points to the input buffer which may be freed later
                const val = try _unescape_string(self.allocator, token.value);
                const duped = self.allocator.alloc(u8, val.len) catch return error.OutOfMemory;
                @memcpy(duped, val);
                return SExp{ .value = .{ .string = duped }, .location = token.location };
            },
            //.string => return SExp{ .value = .{ .string = try _unescape_string(self.allocator, token.value) }, .location = token.location },
            .comment => {
                // CRITICAL FIX: Duplicate comment to prevent use-after-free
                const duped = self.allocator.alloc(u8, token.value.len) catch return error.OutOfMemory;
                @memcpy(duped, token.value);
                return SExp{ .value = .{ .comment = duped }, .location = token.location };
            },
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

// Check if a list is an XY coordinate (starts with "xy")
pub fn isXYForm(sexp: SExp) bool {
    return isForm(sexp, "xy");
}

// Check if a list is a short-form type (font, stroke, fill, etc.)
pub fn isShortForm(sexp: SExp) bool {
    const items = getList(sexp) orelse return false;
    if (items.len == 0) return false;
    const sym = getSymbol(items[0]) orelse return false;

    return std.mem.eql(u8, sym, "font") or
        std.mem.eql(u8, sym, "stroke") or
        std.mem.eql(u8, sym, "fill") or
        std.mem.eql(u8, sym, "teardrop") or
        std.mem.eql(u8, sym, "offset") or
        std.mem.eql(u8, sym, "rotate") or
        std.mem.eql(u8, sym, "scale");
}
