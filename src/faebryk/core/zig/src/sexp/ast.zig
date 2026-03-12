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
    location: TokenLocation = TokenLocation.none,

    inline fn saturatingAdd(lhs: usize, rhs: usize) usize {
        return std.math.add(usize, lhs, rhs) catch std.math.maxInt(usize);
    }

    fn isShortFormTokenName(token: []const u8) bool {
        return std.mem.eql(u8, token, "font") or
            std.mem.eql(u8, token, "stroke") or
            std.mem.eql(u8, token, "fill") or
            std.mem.eql(u8, token, "teardrop") or
            std.mem.eql(u8, token, "offset") or
            std.mem.eql(u8, token, "rotate") or
            std.mem.eql(u8, token, "scale");
    }

    fn estimatedSerializedLen(self: SExp) usize {
        return switch (self.value) {
            .symbol => |s| s.len,
            .number => |n| n.len,
            .comment => |c| saturatingAdd(1, c.len),
            .string => |s| saturatingAdd(2, saturatingAdd(s.len, s.len)),
            .list => |items| blk: {
                var total: usize = 2; // Opening and closing parenthesis.
                for (items, 0..) |item, i| {
                    if (i > 0) total = saturatingAdd(total, 1);
                    total = saturatingAdd(total, item.estimatedSerializedLen());
                }
                break :blk total;
            },
        };
    }

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

        var formatted = std.array_list.Managed(u8).init(allocator);
        defer formatted.deinit();
        const estimated_out = saturatingAdd(source.len, saturatingAdd(source.len / 3, 64));
        try formatted.ensureTotalCapacity(estimated_out);

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
                while (seek < src.len and std.ascii.isAlphabetic(src[seek])) {
                    seek += 1;
                }
                if (seek <= pos + 1) return false;
                return isShortFormTokenName(src[pos + 1 .. seek]);
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
            .string => |s| try writeEscapedString(s, writer),
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
        var in = std.array_list.Managed(u8).init(allocator);
        defer in.deinit();
        try in.ensureTotalCapacity(self.estimatedSerializedLen());

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

// Helper function to escape special characters in strings for KiCad S-expression output
pub fn writeEscapedString(str: []const u8, writer: anytype) !void {
    try writer.writeByte('"');
    for (str) |c| {
        switch (c) {
            '\\' => try writer.writeAll("\\\\"),
            '"' => try writer.writeAll("\\\""),
            '\n' => try writer.writeAll("\\n"),
            '\r' => try writer.writeAll("\\r"),
            // KiCad writes literal tabs (not \t), so preserve them as-is
            else => try writer.writeByte(c),
        }
    }
    try writer.writeByte('"');
}

fn _unescape_string(allocator: std.mem.Allocator, str: []const u8) ![]const u8 {
    var unescaped = std.array_list.Managed(u8).init(allocator);
    // Pre-allocate with known maximum capacity since unescaping can only shrink the string
    try unescaped.ensureTotalCapacity(str.len);

    var i: usize = 0;
    while (i < str.len) {
        if (str[i] == '\\' and i + 1 < str.len) {
            switch (str[i + 1]) {
                'n' => try unescaped.append('\n'),
                'r' => try unescaped.append('\r'),
                't' => try unescaped.append('\t'),
                '\\' => try unescaped.append('\\'),
                '"' => try unescaped.append('"'),
                else => {
                    // Unknown escape sequence: preserve both characters
                    try unescaped.append(str[i]);
                    try unescaped.append(str[i + 1]);
                },
            }
            i += 2;
        } else {
            try unescaped.append(str[i]);
            i += 1;
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

const ListFrame = struct {
    meta_idx: usize,
    child_count: u32,
};

const OverflowEntry = struct {
    idx: u32,
    count: u32,
};

pub const ListChildCounts = struct {
    counts16: []u16,
    overflow_entries: []OverflowEntry,

    pub fn deinit(self: ListChildCounts, allocator: std.mem.Allocator) void {
        allocator.free(self.counts16);
        allocator.free(self.overflow_entries);
    }
};

fn countListNodes(tokens: []const Token) usize {
    var count: usize = 0;
    for (tokens) |token| {
        if (token.type == .lparen) count += 1;
    }
    return count;
}

fn incrementTopChildCount(stack: *std.array_list.Managed(ListFrame)) void {
    if (stack.items.len == 0) return;
    var top = &stack.items[stack.items.len - 1];
    if (top.child_count != std.math.maxInt(u32)) {
        top.child_count += 1;
    }
}

pub fn buildListChildCounts(allocator: std.mem.Allocator, tokens: []const Token) ParseError!ListChildCounts {
    const list_count = countListNodes(tokens);
    var child_counts16 = try allocator.alloc(u16, list_count);
    errdefer allocator.free(child_counts16);
    @memset(child_counts16, 0);
    var overflow_builder = std.array_list.Managed(OverflowEntry).init(allocator);
    defer overflow_builder.deinit();

    var stack = std.array_list.Managed(ListFrame).init(allocator);
    defer stack.deinit();

    var next_meta: usize = 0;
    for (tokens) |token| {
        switch (token.type) {
            .lparen => {
                incrementTopChildCount(&stack);
                try stack.append(.{
                    .meta_idx = next_meta,
                    .child_count = 0,
                });
                next_meta += 1;
            },
            .rparen => {
                const frame = stack.pop() orelse return error.UnexpectedRightParen;
                if (frame.child_count <= std.math.maxInt(u16)) {
                    child_counts16[frame.meta_idx] = @as(u16, @intCast(frame.child_count));
                } else {
                    child_counts16[frame.meta_idx] = std.math.maxInt(u16);
                    try overflow_builder.append(.{
                        .idx = @as(u32, @intCast(frame.meta_idx)),
                        .count = frame.child_count,
                    });
                }
            },
            else => incrementTopChildCount(&stack),
        }
    }

    if (stack.items.len != 0) return error.UnterminatedList;
    std.sort.pdq(OverflowEntry, overflow_builder.items, {}, struct {
        fn lessThan(_: void, lhs: OverflowEntry, rhs: OverflowEntry) bool {
            return lhs.idx < rhs.idx;
        }
    }.lessThan);
    return .{
        .counts16 = child_counts16,
        .overflow_entries = try overflow_builder.toOwnedSlice(),
    };
}

pub const Parser = struct {
    source: []const u8,
    tokens: []const Token,
    list_child_counts16: []const u16,
    overflow_entries: []const OverflowEntry,
    overflow_cursor: usize,
    list_meta_cursor: usize,
    position: usize,
    list_pool: []SExp,
    list_pool_cursor: usize,
    use_list_pool: bool,
    allocator: std.mem.Allocator,
    copy_atoms: bool,
    track_locations: bool,

    pub fn init(allocator: std.mem.Allocator, source: []const u8, tokens: []const Token, list_child_counts: ListChildCounts) Parser {
        return .{
            .source = source,
            .tokens = tokens,
            .list_child_counts16 = list_child_counts.counts16,
            .overflow_entries = list_child_counts.overflow_entries,
            .overflow_cursor = 0,
            .list_meta_cursor = 0,
            .position = 0,
            .list_pool = &[_]SExp{},
            .list_pool_cursor = 0,
            .use_list_pool = false,
            .allocator = allocator,
            .copy_atoms = true,
            .track_locations = true,
        };
    }

    pub fn initBorrowed(allocator: std.mem.Allocator, source: []const u8, tokens: []const Token, list_child_counts: ListChildCounts) Parser {
        return .{
            .source = source,
            .tokens = tokens,
            .list_child_counts16 = list_child_counts.counts16,
            .overflow_entries = list_child_counts.overflow_entries,
            .overflow_cursor = 0,
            .list_meta_cursor = 0,
            .position = 0,
            .list_pool = &[_]SExp{},
            .list_pool_cursor = 0,
            .use_list_pool = false,
            .allocator = allocator,
            .copy_atoms = false,
            .track_locations = true,
        };
    }

    fn listChildCountAt(self: *Parser, idx: usize) ParseError!usize {
        if (idx >= self.list_child_counts16.len) return error.UnterminatedList;
        const raw = self.list_child_counts16[idx];
        if (raw != std.math.maxInt(u16)) return @as(usize, raw);

        if (self.overflow_cursor >= self.overflow_entries.len) return error.UnterminatedList;
        const entry = self.overflow_entries[self.overflow_cursor];
        if (entry.idx != @as(u32, @intCast(idx))) return error.UnterminatedList;
        self.overflow_cursor += 1;
        return @as(usize, entry.count);
    }

    fn tokenSlice(self: *const Parser, token: Token) []const u8 {
        return token.slice(self.source);
    }

    fn tokenLocation(_: *const Parser, token: Token) TokenLocation {
        return .{
            .start = token.start,
            .end = token.end,
        };
    }

    pub fn parse(self: *Parser) ParseError!?SExp {
        if (self.position >= self.tokens.len) {
            return null;
        }

        const token = self.tokens[self.position];
        self.position += 1;
        const token_location: TokenLocation = if (self.track_locations) self.tokenLocation(token) else TokenLocation.none;
        const token_value = self.tokenSlice(token);

        switch (token.type) {
            .lparen => return try self.parseList(token_location),
            .rparen => return error.UnexpectedRightParen,
            .symbol => {
                if (self.copy_atoms) {
                    // Duplicate symbol to prevent use-after-free.
                    const duped = self.allocator.alloc(u8, token_value.len) catch return error.OutOfMemory;
                    @memcpy(duped, token_value);
                    return SExp{ .value = .{ .symbol = duped }, .location = token_location };
                }
                return SExp{ .value = .{ .symbol = token_value }, .location = token_location };
            },
            .number => {
                if (self.copy_atoms) {
                    // Duplicate number to prevent use-after-free.
                    const duped = self.allocator.alloc(u8, token_value.len) catch return error.OutOfMemory;
                    @memcpy(duped, token_value);
                    return SExp{ .value = .{ .number = duped }, .location = token_location };
                }
                return SExp{ .value = .{ .number = token_value }, .location = token_location };
            },
            .string => {
                // token value points to the input buffer which may be freed later
                const string_inner = if (token_value.len >= 2) token_value[1 .. token_value.len - 1] else token_value;
                if (std.mem.indexOfScalar(u8, string_inner, '\\') == null) {
                    if (self.copy_atoms) {
                        const duped = self.allocator.alloc(u8, string_inner.len) catch return error.OutOfMemory;
                        @memcpy(duped, string_inner);
                        return SExp{ .value = .{ .string = duped }, .location = token_location };
                    }
                    return SExp{ .value = .{ .string = string_inner }, .location = token_location };
                }
                const val = try _unescape_string(self.allocator, string_inner);
                return SExp{ .value = .{ .string = val }, .location = token_location };
            },
            //.string => return SExp{ .value = .{ .string = try _unescape_string(self.allocator, token.value) }, .location = token.location },
            .comment => {
                if (self.copy_atoms) {
                    // Duplicate comment to prevent use-after-free.
                    const duped = self.allocator.alloc(u8, token_value.len) catch return error.OutOfMemory;
                    @memcpy(duped, token_value);
                    return SExp{ .value = .{ .comment = duped }, .location = token_location };
                }
                return SExp{ .value = .{ .comment = token_value }, .location = token_location };
            },
        }
    }

    fn parseList(self: *Parser, start_location: TokenLocation) ParseError!SExp {
        if (self.list_meta_cursor >= self.list_child_counts16.len) {
            return error.UnterminatedList;
        }
        const child_count = try self.listChildCountAt(self.list_meta_cursor);
        self.list_meta_cursor += 1;

        var items: []SExp = undefined;
        if (self.use_list_pool) {
            const next_cursor = std.math.add(usize, self.list_pool_cursor, child_count) catch return error.OutOfMemory;
            if (next_cursor > self.list_pool.len) return error.OutOfMemory;
            items = self.list_pool[self.list_pool_cursor..next_cursor];
            self.list_pool_cursor = next_cursor;
        } else {
            items = try self.allocator.alloc(SExp, child_count);
        }

        var i: usize = 0;
        errdefer if (!self.use_list_pool) {
            var j: usize = 0;
            while (j < i) : (j += 1) {
                items[j].deinit(self.allocator);
            }
            self.allocator.free(items);
        };
        while (i < child_count) : (i += 1) {
            items[i] = (try self.parse()) orelse return error.UnterminatedList;
        }

        if (self.position >= self.tokens.len) {
            return error.UnterminatedList;
        }
        const next_token = self.tokens[self.position];
        if (next_token.type != .rparen) {
            return error.UnterminatedList;
        }
        const end_location = if (self.track_locations) self.tokenLocation(next_token) else TokenLocation.none;
        const list_location: TokenLocation = if (self.track_locations) .{
            .start = start_location.start,
            .end = end_location.end,
        } else TokenLocation.none;
        self.position += 1;
        return SExp{ .value = .{ .list = items }, .location = list_location };
    }
};

// Parse with arena allocator for better performance!
// Parse a single S-expression
pub fn parse(allocator: std.mem.Allocator, source: []const u8, tokens: []const Token) ParseError!SExp {
    const child_counts = try buildListChildCounts(allocator, tokens);
    defer child_counts.deinit(allocator);
    var parser = Parser.init(allocator, source, tokens, child_counts);
    return try parser.parse() orelse return error.EmptyFile;
}

// Parse without duplicating symbol/number/comment atoms.
// Callers must ensure token storage outlives the returned SExp.
pub fn parseBorrowed(allocator: std.mem.Allocator, source: []const u8, tokens: []const Token) ParseError!SExp {
    const child_counts = try buildListChildCounts(allocator, tokens);
    defer child_counts.deinit(allocator);
    var parser = Parser.initBorrowed(allocator, source, tokens, child_counts);
    return try parser.parse() orelse return error.EmptyFile;
}

// Parse without duplicating symbol/number/comment atoms and skip location tracking.
//
// IMPORTANT ownership contract:
// - Returned atoms borrow from `source` and must not outlive `source`.
// - List storage is carved from allocator-owned pool storage and is intended for
//   arena-style lifetime management.
// - Do not call `SExp.deinit()` on the returned tree.
//
// This is the fastest/lower-memory path for decode-only pipelines.
pub fn parseBorrowedFast(allocator: std.mem.Allocator, source: []const u8, tokens: []const Token) ParseError!SExp {
    const child_counts = try buildListChildCounts(allocator, tokens);
    defer child_counts.deinit(allocator);
    var total_child_slots: usize = 0;
    var overflow_idx: usize = 0;
    for (child_counts.counts16) |count16| {
        if (count16 == std.math.maxInt(u16)) {
            const count = child_counts.overflow_entries[overflow_idx].count;
            overflow_idx += 1;
            total_child_slots = std.math.add(usize, total_child_slots, @as(usize, count)) catch return error.OutOfMemory;
        } else {
            total_child_slots = std.math.add(usize, total_child_slots, @as(usize, count16)) catch return error.OutOfMemory;
        }
    }
    const list_pool = try allocator.alloc(SExp, total_child_slots);
    var parser = Parser.initBorrowed(allocator, source, tokens, child_counts);
    parser.track_locations = false;
    parser.use_list_pool = true;
    parser.list_pool = list_pool;
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
