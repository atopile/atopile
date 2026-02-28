const std = @import("std");
const ast = @import("ast.zig");
const tokenizer = @import("tokenizer.zig");
pub const SExp = ast.SExp;

// Type trait helpers
fn isOptional(comptime T: type) bool {
    return @typeInfo(T) == .optional;
}

fn isLinkedList(comptime T: type) bool {
    return @typeInfo(T) == .@"struct" and @hasField(T, "first") and @hasField(T, "last") and @hasDecl(T, "Node");
}

fn isSimpleType(comptime T: type) bool {
    return switch (@typeInfo(T)) {
        .int, .float, .bool, .@"enum" => true,
        // Don't consider strings as simple - they need to be freed
        else => false,
    };
}

pub const BooleanEncoding = enum {
    yes_no,
    symbol,
    parantheses_symbol,
};

// Simplified field metadata
pub const SexpField = struct {
    positional: bool = false,
    multidict: bool = false,
    sexp_name: ?[]const u8 = null,
    order: i32 = 0,
    symbol: ?bool = null, // If true, encode strings as symbols (no quotes)
    boolean_encoding: BooleanEncoding = .symbol,
};

fn _print_indent(writer: anytype, indent: usize) !void {
    var k: usize = 0;
    while (k < indent) : (k += 1) {
        try writer.print(" ", .{});
    }
}

// Error context for better diagnostics
pub const ErrorContext = struct {
    path: []const u8,
    field_name: ?[]const u8 = null,
    message: ?[]const u8 = null,
    line: ?usize = null,
    column: ?usize = null,
    end_line: ?usize = null,
    end_column: ?usize = null,
    start_offset: ?usize = null,
    end_offset: ?usize = null,
    sexp: ?SExp = null,

    source: ?[]const u8 = null,
    indent: usize = 0,

    const LineCol = struct {
        line: usize,
        column: usize,
    };

    fn offsetToLineCol(source: []const u8, offset: usize) LineCol {
        var line: usize = 1;
        var column: usize = 1;
        const capped = @min(offset, source.len);
        var i: usize = 0;
        while (i < capped) : (i += 1) {
            if (source[i] == '\n') {
                line += 1;
                column = 1;
            } else {
                column += 1;
            }
        }
        return .{ .line = line, .column = column };
    }

    pub fn print_source(self: ErrorContext, source: []const u8, writer: anytype, indent: usize) !void {
        var line_opt = self.line;
        var col_opt = self.column;
        var end_line_opt = self.end_line;
        var end_col_opt = self.end_column;
        if ((line_opt == null or col_opt == null or end_line_opt == null or end_col_opt == null) and
            self.start_offset != null and self.end_offset != null)
        {
            const start_lc = offsetToLineCol(source, self.start_offset.?);
            const end_lc = offsetToLineCol(source, self.end_offset.?);
            line_opt = start_lc.line;
            col_opt = start_lc.column;
            end_line_opt = end_lc.line;
            end_col_opt = end_lc.column;
        }

        const line_no = line_opt orelse return;
        var line_iter = std.mem.tokenizeScalar(u8, source, '\n');
        var current_line: usize = 1;
        while (line_iter.next()) |line_text| {
            if (current_line == line_no) {
                // Print indentation
                try _print_indent(writer, indent);
                try writer.print("Source: {s}\n", .{line_text});

                // Show cursor position with indentation
                try _print_indent(writer, indent);
                try writer.print("        ", .{});

                var i: usize = 1;
                if (col_opt) |col| {
                    while (i < col) : (i += 1) {
                        try writer.print(" ", .{});
                    }
                    if (end_col_opt) |end_col| {
                        const len = if (end_line_opt == line_opt) end_col - col else line_text.len - col + 1;
                        var j: usize = 0;
                        while (j < len) : (j += 1) {
                            try writer.print("^", .{});
                        }
                    } else {
                        try writer.print("^", .{});
                    }
                }
                try writer.print("\n", .{});
                break;
            }
            current_line += 1;
        }
    }

    pub fn format(self: ErrorContext, comptime fmt: []const u8, options: std.fmt.FormatOptions, writer: anytype) !void {
        _ = fmt;
        _ = options;
        try writer.print("ErrorContext(\n  Struct: {s},\n  Field: {?s},\n  Problem: {?s},\n  Location: {?d}:{?d} to {?d}:{?d},\n  Offsets: {?d}..{?d}", .{
            self.path,
            self.field_name,
            self.message,
            self.line,
            self.column,
            self.end_line,
            self.end_column,
            self.start_offset,
            self.end_offset,
        });
        if (self.source) |source| {
            try writer.print("\n", .{});
            try self.print_source(source, writer, self.indent + 2);
        }
    }
};

// Error types
pub const DecodeError = error{
    UnexpectedType,
    MissingField,
    DuplicateKey,
    InvalidValue,
    AssertionFailed,
    OutOfMemory,
};

// Error context
// NOTE: Using non-threadlocal due to Python 3.14 incompatibility with Zig's threadlocal storage
// This may cause issues in multi-threaded scenarios but the Python GIL typically prevents that
var current_error_context: ?ErrorContext = null;

pub fn getErrorContext() ?ErrorContext {
    return current_error_context;
}

pub fn printError(source: []const u8, err: anytype) void {
    std.debug.print("Error parsing: {}\n", .{err});

    if (getErrorContext()) |ctx| {
        var ctx_with_source = ctx;
        ctx_with_source.source = source;
        std.debug.print("{}\n", .{ctx_with_source});
    } else {
        std.debug.print("No error context\n", .{});
    }
}

pub fn clearErrorContext() void {
    current_error_context = null;
}

// Helper to set error context with location from SExp
fn setErrorContext(base_ctx: ErrorContext, sexp: SExp) void {
    var ctx = base_ctx;

    if (sexp.location.isSet()) {
        const location = sexp.location;
        ctx.start_offset = @as(usize, location.start);
        ctx.end_offset = @as(usize, location.end);
    }
    ctx.sexp = sexp;

    current_error_context = ctx;
}

// Lightweight helpers to cut boilerplate when setting error context
inline fn _baseCtx(comptime T: type, field_name: ?[]const u8) ErrorContext {
    if (getErrorContext()) |c| {
        return .{ .path = c.path, .field_name = field_name orelse c.field_name };
    }
    return .{ .path = @typeName(T), .field_name = field_name };
}

inline fn setCtx(comptime T: type, sexp: SExp, field_name: ?[]const u8, msg: ?[]const u8) void {
    var ctx = _baseCtx(T, field_name);
    ctx.message = msg;
    setErrorContext(ctx, sexp);
}

inline fn setCtxFromCurrent(comptime T: type, sexp: SExp, msg: []const u8) void {
    setCtx(T, sexp, null, msg);
}

inline fn setCtxPath(comptime path: []const u8, sexp: SExp, field_name: ?[]const u8, msg: ?[]const u8) void {
    const ctx: ErrorContext = .{ .path = path, .field_name = field_name, .message = msg };
    setErrorContext(ctx, sexp);
}

// Helper to format S-expression preview
fn formatSexpPreview(allocator: std.mem.Allocator, sexp: SExp) ![]u8 {
    var buf = std.array_list.Managed(u8).init(allocator);
    defer buf.deinit();

    try formatSexpPreviewInternal(sexp, &buf, 0, 50); // max 50 chars
    return try buf.toOwnedSlice();
}

fn formatSexpPreviewInternal(sexp: SExp, buf: *std.array_list.Managed(u8), depth: usize, max_len: usize) !void {
    if (buf.items.len >= max_len) {
        try buf.appendSlice("...");
        return;
    }

    switch (sexp.value) {
        .symbol => |s| try buf.appendSlice(s),
        .string => |s| {
            try buf.append('"');
            // Compute safe budget for content (avoid underflow)
            const budget = if (max_len > buf.items.len) max_len - buf.items.len else 0;
            const reserve_for_tail: usize = 2; // closing quote and potential ellipsis
            const content_budget = if (budget > reserve_for_tail) budget - reserve_for_tail else 0;
            const preview_len = @min(s.len, content_budget);
            if (preview_len > 0) try buf.appendSlice(s[0..preview_len]);
            // Append ellipsis only if we have room
            if (preview_len < s.len and content_budget >= 3) try buf.appendSlice("...");
            try buf.append('"');
        },
        .number => |n| try buf.appendSlice(n),
        .comment => |c| {
            try buf.appendSlice("; ");
            const budget = if (max_len > buf.items.len) max_len - buf.items.len else 0;
            const content_budget = budget;
            const preview_len = @min(c.len, content_budget);
            if (preview_len > 0) try buf.appendSlice(c[0..preview_len]);
            if (preview_len < c.len and content_budget >= 3) try buf.appendSlice("...");
        },
        .list => |items| {
            try buf.append('(');
            for (items, 0..) |item, i| {
                if (i > 0) try buf.append(' ');
                if (buf.items.len >= max_len) {
                    try buf.appendSlice("...");
                    break;
                }
                try formatSexpPreviewInternal(item, buf, depth + 1, max_len);
            }
            try buf.append(')');
        },
    }
}

pub const EncodeError = error{
    OutOfMemory,
    InvalidType,
};

// Helper to get sexp metadata for a field
fn getSexpMetadata(comptime T: type, comptime field_name: []const u8) SexpField {
    if (@hasDecl(T, "fields_meta")) {
        if (@hasField(@TypeOf(T.fields_meta), field_name)) {
            const meta = @field(T.fields_meta, field_name);
            // Convert anonymous struct to SexpField
            var result = SexpField{};
            if (@hasField(@TypeOf(meta), "positional")) result.positional = meta.positional;
            if (@hasField(@TypeOf(meta), "multidict")) result.multidict = meta.multidict;
            if (@hasField(@TypeOf(meta), "sexp_name")) result.sexp_name = meta.sexp_name;
            if (@hasField(@TypeOf(meta), "order")) result.order = meta.order;
            if (@hasField(@TypeOf(meta), "symbol")) result.symbol = meta.symbol;
            if (@hasField(@TypeOf(meta), "boolean_encoding")) result.boolean_encoding = meta.boolean_encoding;
            return result;
        }
    }
    return SexpField{};
}

// Main decode function
pub fn decode(comptime T: type, allocator: std.mem.Allocator, sexp: SExp) DecodeError!T {
    return decodeWithMetadata(T, allocator, sexp, SexpField{});
}

// Main decode function with metadata
pub fn decodeWithMetadata(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, metadata: SexpField) DecodeError!T {
    const type_info = @typeInfo(T);

    // Check if type has a custom decode method (only for types that support declarations)
    switch (type_info) {
        .@"struct", .@"enum", .@"union", .@"opaque" => {
            if (comptime @hasDecl(T, "decode")) {
                return try T.decode(allocator, sexp);
            }
        },
        else => {},
    }

    switch (type_info) {
        .@"struct" => if (comptime isLinkedList(T)) {
            return try decodeLinkedList(T, allocator, sexp, metadata);
        } else {
            return try decodeStruct(T, allocator, sexp, metadata);
        },
        .optional => |opt| return try decodeOptional(opt.child, allocator, sexp, metadata),
        .pointer => |ptr| {
            if (ptr.size == .slice) {
                return try decodeSlice(T, allocator, sexp, metadata);
            }
            setCtx(T, sexp, null, "unsupported pointer type (only slices are supported)");
            return error.UnexpectedType;
        },
        .int => return try decodeInt(T, sexp, metadata),
        .float => return try decodeFloat(T, sexp, metadata),
        .bool => return try decodeBool(sexp, metadata),
        .@"enum" => return try decodeEnum(T, sexp, metadata),
        .@"union" => {
            // If no custom decode, unions need custom decoders
            setCtx(T, sexp, null, "union types require custom decode method");
            return error.UnexpectedType;
        },
        else => {
            setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "unsupported type: {s}", .{@typeName(T)}) catch "unsupported type");
            return error.UnexpectedType;
        },
    }
}

fn decodeStruct(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata;
    @setEvalBranchQuota(15000);
    const flds = std.meta.fields(T);
    var result: T = undefined;

    const items = ast.getList(sexp) orelse {
        setCtx(T, sexp, null, "expected list for struct");
        return error.UnexpectedType;
    };

    var fields_set = std.StaticBitSet(flds.len).initEmpty();
    errdefer {
        inline for (flds, 0..) |field, idx| if (fields_set.isSet(idx)) free(field.type, allocator, @field(result, field.name));
    }

    try handlePositionalFields(T, allocator, items, &result, &fields_set);
    try handleKeyValuesAndBooleans(T, allocator, items, &result, &fields_set);
    try finalizeUnsetFields(T, allocator, items, sexp, &result, &fields_set);

    return result;
}

// Determine start index for positional parsing (skip lowercase type symbol if present)
fn positionalStart(comptime T: type, items: []const SExp) usize {
    if (items.len == 0) return 0;
    if (ast.getSymbol(items[0])) |sym| {
        const type_name = @typeName(T);
        var last_dot: usize = 0;
        for (type_name, 0..) |c, i| {
            if (c == '.') last_dot = i + 1;
        }
        const short_name = type_name[last_dot..];
        var lower_buf: [128]u8 = undefined;
        if (short_name.len <= lower_buf.len) {
            for (short_name, 0..) |c, i| lower_buf[i] = std.ascii.toLower(c);
            const lower_name = lower_buf[0..short_name.len];
            if (std.mem.eql(u8, sym, lower_name)) return 1;
        }
    }
    return 0;
}

fn hasAnyPositionalFields(comptime T: type) bool {
    const fields = std.meta.fields(T);
    inline for (fields) |field| {
        const fm = comptime getSexpMetadata(T, field.name);
        if (fm.positional) return true;
    }
    return false;
}

fn allFieldsPositional(comptime T: type) bool {
    const fields = std.meta.fields(T);
    var has_fields = false;
    inline for (fields) |field| {
        has_fields = true;
        const fm = comptime getSexpMetadata(T, field.name);
        if (!fm.positional) return false;
    }
    return has_fields;
}

fn handlePositionalFields(comptime T: type, allocator: std.mem.Allocator, items: []const SExp, result: *T, fields_set: anytype) DecodeError!void {
    const fields = std.meta.fields(T);
    if (!comptime hasAnyPositionalFields(T)) return;

    var idx: usize = if (comptime allFieldsPositional(T)) positionalStart(T, items) else 0;

    inline for (fields, 0..) |field, field_idx| {
        const fm = comptime getSexpMetadata(T, field.name);
        if (fm.positional) {
            while (idx < items.len and ast.isList(items[idx])) idx += 1;

            if (idx >= items.len) {
                if (comptime isOptional(field.type)) {
                    @field(result.*, field.name) = null;
                    fields_set.set(field_idx);
                }
            } else {
                const has_default = comptime isOptional(field.type) or field.default_value_ptr != null;
                var consumed = false;

                if (has_default) {
                    const actual_type = if (comptime isOptional(field.type)) @typeInfo(field.type).optional.child else field.type;
                    if (@typeInfo(actual_type) == .@"enum") {
                        if (ast.getSymbol(items[idx])) |sym| {
                            var ok = false;
                            inline for (std.meta.fields(actual_type)) |ef| {
                                if (std.mem.eql(u8, sym, ef.name)) ok = true;
                                if (@hasDecl(actual_type, "fields_meta") and @hasField(@TypeOf(actual_type.fields_meta), ef.name)) {
                                    const em = @field(actual_type.fields_meta, ef.name);
                                    if (@hasField(@TypeOf(em), "sexp_name")) {
                                        const sn = em.sexp_name;
                                        if (@typeInfo(@TypeOf(sn)) == .optional) {
                                            if (sn) |name| {
                                                if (std.mem.eql(u8, sym, name)) ok = true;
                                            }
                                        }
                                    }
                                }
                            }
                            if (ok) {
                                setCtx(T, items[idx], field.name, null);
                                @field(result.*, field.name) = try decodeWithMetadata(field.type, allocator, items[idx], fm);
                                fields_set.set(field_idx);
                                idx += 1;
                                consumed = true;
                            } else {
                                if (comptime isOptional(field.type)) @field(result.*, field.name) = null;
                                fields_set.set(field_idx);
                            }
                        } else {
                            if (comptime isOptional(field.type)) @field(result.*, field.name) = null;
                            fields_set.set(field_idx);
                        }
                    }

                    if (!consumed and @typeInfo(actual_type) != .@"enum") {
                        const saved = getErrorContext();
                        clearErrorContext();
                        if (decodeWithMetadata(field.type, allocator, items[idx], fm)) |val| {
                            @field(result.*, field.name) = val;
                            fields_set.set(field_idx);
                            idx += 1;
                            consumed = true;
                        } else |_| {
                            current_error_context = saved;
                            if (comptime isOptional(field.type)) @field(result.*, field.name) = null;
                            fields_set.set(field_idx);
                        }
                    }
                }

                if (!has_default) {
                    setCtx(T, items[idx], field.name, null);
                    @field(result.*, field.name) = try decodeWithMetadata(field.type, allocator, items[idx], fm);
                    fields_set.set(field_idx);
                    idx += 1;
                }
            }
        }
    }
}

fn handleKeyValuesAndBooleans(comptime T: type, allocator: std.mem.Allocator, items: []const SExp, result: *T, fields_set: anytype) DecodeError!void {
    const fields = std.meta.fields(T);
    var i: usize = 0;
    while (i < items.len) : (i += 1) {
        if (ast.getSymbol(items[i])) |sym| {
            inline for (fields, 0..) |field, field_idx| {
                if (!fields_set.isSet(field_idx) and @typeInfo(field.type) == .bool) {
                    const fm = comptime getSexpMetadata(T, field.name);
                    const fname = fm.sexp_name orelse field.name;
                    if (std.mem.eql(u8, sym, fname)) {
                        @field(result.*, field.name) = true;
                        fields_set.set(field_idx);
                    }
                }
                if (!fields_set.isSet(field_idx) and comptime isOptional(field.type)) {
                    const child = @typeInfo(field.type).optional.child;
                    if (@typeInfo(child) == .bool) {
                        const fm = comptime getSexpMetadata(T, field.name);
                        const fname = fm.sexp_name orelse field.name;
                        if (std.mem.eql(u8, sym, fname)) {
                            @field(result.*, field.name) = true;
                            fields_set.set(field_idx);
                        }
                    }
                }
            }
        }

        if (!ast.isList(items[i])) continue;
        const kv_items = ast.getList(items[i]).?;
        if (kv_items.len == 0) continue; // Skip empty lists to prevent segfault
        const key = ast.getSymbol(kv_items[0]) orelse continue;

        inline for (fields, 0..) |field, field_idx| {
            const fm = comptime getSexpMetadata(T, field.name);
            const fname = fm.sexp_name orelse field.name;
            if (std.mem.eql(u8, key, fname)) {
                if (fm.multidict) {
                    if (comptime isSlice(field.type, false)) {
                        if (!fields_set.isSet(field_idx)) {
                            const ChildType = std.meta.Child(field.type);
                            var values = std.array_list.Managed(ChildType).initCapacity(allocator, items.len + 8) catch return error.OutOfMemory;
                            var scan_idx: usize = i;
                            while (scan_idx < items.len) : (scan_idx += 1) {
                                if (!ast.isList(items[scan_idx])) continue;
                                const scan_kv = ast.getList(items[scan_idx]).?;
                                if (scan_kv.len < 2) continue;
                                const scan_key = ast.getSymbol(scan_kv[0]) orelse continue;
                                if (!std.mem.eql(u8, fname, scan_key)) continue;
                                setCtx(T, items[scan_idx], field.name, null);
                                const scan_struct_sexp = SExp{ .value = .{ .list = scan_kv[1..] }, .location = tokenizer.TokenLocation.none };
                                try values.append(try decodeWithMetadata(ChildType, allocator, scan_struct_sexp, fm));
                            }
                            @field(result.*, field.name) = try values.toOwnedSlice();
                            fields_set.set(field_idx);
                        }
                    } else if (comptime isLinkedList(field.type)) {
                        if (!fields_set.isSet(field_idx)) {
                            const NodeType = field.type.Node;
                            const ChildType = @FieldType(NodeType, "data");
                            var ll = field.type{};
                            var scan_idx: usize = i;
                            while (scan_idx < items.len) : (scan_idx += 1) {
                                if (!ast.isList(items[scan_idx])) continue;
                                const scan_kv = ast.getList(items[scan_idx]).?;
                                if (scan_kv.len < 2) continue;
                                const scan_key = ast.getSymbol(scan_kv[0]) orelse continue;
                                if (!std.mem.eql(u8, fname, scan_key)) continue;
                                setCtx(T, items[scan_idx], field.name, null);
                                const scan_struct_sexp = SExp{ .value = .{ .list = scan_kv[1..] }, .location = tokenizer.TokenLocation.none };
                                const val = try decodeWithMetadata(ChildType, allocator, scan_struct_sexp, fm);
                                const node = try allocator.create(NodeType);
                                node.* = NodeType{ .data = val };
                                ll.append(node);
                            }
                            @field(result.*, field.name) = ll;
                            fields_set.set(field_idx);
                        }
                    }
                } else {
                    // Handle parantheses_symbol boolean encoding: (power) means power=true
                    if (!fields_set.isSet(field_idx) and kv_items.len == 1 and @typeInfo(field.type) == .bool and fm.boolean_encoding == .parantheses_symbol) {
                        @field(result.*, field.name) = true;
                        fields_set.set(field_idx);
                    }
                    // Only process if field is not set AND we have at least key+value (len >= 2)
                    // Skip key-only entries (e.g., "(stroke)") that have no values to prevent segfault
                    else if (!fields_set.isSet(field_idx) and kv_items.len >= 2) {
                        setCtx(T, items[i], field.name, null);
                        @field(result.*, field.name) = if (@typeInfo(field.type) == .@"struct" or (@typeInfo(field.type) == .optional and @typeInfo(@typeInfo(field.type).optional.child) == .@"struct"))
                            try decodeWithMetadata(field.type, allocator, SExp{ .value = .{ .list = kv_items[1..] }, .location = tokenizer.TokenLocation.none }, fm)
                        else if (kv_items.len == 2 and !isSlice(field.type, true))
                            try decodeWithMetadata(field.type, allocator, kv_items[1], fm)
                        else
                            try decodeWithMetadata(field.type, allocator, SExp{ .value = .{ .list = kv_items[1..] }, .location = tokenizer.TokenLocation.none }, fm);
                        fields_set.set(field_idx);
                    }
                }
            }
        }
    }
}

fn finalizeUnsetFields(comptime T: type, allocator: std.mem.Allocator, items: []const SExp, sexp: SExp, result: *T, fields_set: anytype) DecodeError!void {
    const fields = std.meta.fields(T);
    inline for (fields, 0..) |field, field_idx| {
        if (!fields_set.isSet(field_idx)) {
            const fm = comptime getSexpMetadata(T, field.name);
            const fname = fm.sexp_name orelse field.name;

            var found_nested = false;
            for (items) |item| {
                if (!ast.isList(item)) continue;
                const nested_items = ast.getList(item).?;
                if (nested_items.len == 0) continue;
                const sym = ast.getSymbol(nested_items[0]) orelse continue;
                if (!std.mem.eql(u8, sym, fname)) continue;
                if (nested_items.len == 1 and field.default_value_ptr != null) {
                    // Apply the default value when we have a key-only entry like "(stroke)"
                    const default_ptr = field.default_value_ptr.?;
                    const default_bytes = @as([*]const u8, @ptrCast(default_ptr))[0..@sizeOf(field.type)];
                    @memcpy(@as([*]u8, @ptrCast(&@field(result.*, field.name)))[0..@sizeOf(field.type)], default_bytes);
                    fields_set.set(field_idx);
                    found_nested = true;
                    break;
                }
                setCtx(T, item, field.name, null);
                @field(result.*, field.name) = try decodeWithMetadata(field.type, allocator, item, fm);
                fields_set.set(field_idx);
                found_nested = true;
                break;
            }

            if (!found_nested) {
                for (items, 0..) |item, idx| {
                    const sym = ast.getSymbol(item) orelse continue;
                    if (!std.mem.eql(u8, sym, fname)) continue;
                    if (idx + 1 >= items.len) {
                        if (field.default_value_ptr) |default_ptr| {
                            // Apply the default value when we have a key at end of list
                            const default_bytes = @as([*]const u8, @ptrCast(default_ptr))[0..@sizeOf(field.type)];
                            @memcpy(@as([*]u8, @ptrCast(&@field(result.*, field.name)))[0..@sizeOf(field.type)], default_bytes);
                            fields_set.set(field_idx);
                            found_nested = true;
                        }
                        break;
                    }
                    var looks_like_value = true;
                    if (ast.getSymbol(items[idx + 1])) |next_sym| {
                        inline for (fields) |check_field| {
                            const cm = comptime getSexpMetadata(T, check_field.name);
                            const cn = cm.sexp_name orelse check_field.name;
                            if (std.mem.eql(u8, next_sym, cn)) looks_like_value = false;
                        }
                    }
                    if (looks_like_value and field.default_value_ptr == null) {
                        const value_items = items[idx + 1 ..];
                        const value_sexp = if (value_items.len == 1) value_items[0] else SExp{ .value = .{ .list = @constCast(value_items) }, .location = tokenizer.TokenLocation.none };
                        setCtx(T, value_sexp, field.name, null);
                        @field(result.*, field.name) = try decodeWithMetadata(field.type, allocator, value_sexp, fm);
                        fields_set.set(field_idx);
                        found_nested = true;
                    } else if (field.default_value_ptr) |default_ptr| {
                        // Apply the default value when we have a key that looks like it has no value
                        const default_bytes = @as([*]const u8, @ptrCast(default_ptr))[0..@sizeOf(field.type)];
                        @memcpy(@as([*]u8, @ptrCast(&@field(result.*, field.name)))[0..@sizeOf(field.type)], default_bytes);
                        fields_set.set(field_idx);
                        found_nested = true;
                    }
                    break;
                }
            }

            if (!found_nested) {
                if (comptime isOptional(field.type)) {
                    @field(result.*, field.name) = null;
                    fields_set.set(field_idx);
                } else if (comptime isSlice(field.type, false)) {
                    if (fm.multidict) {
                        @field(result.*, field.name) = try allocator.alloc(std.meta.Child(field.type), 0);
                        fields_set.set(field_idx);
                    }
                } else if (field.default_value_ptr) |default_ptr| {
                    const default_bytes = @as([*]const u8, @ptrCast(default_ptr))[0..@sizeOf(field.type)];
                    @memcpy(@as([*]u8, @ptrCast(&@field(result.*, field.name)))[0..@sizeOf(field.type)], default_bytes);
                    fields_set.set(field_idx);
                } else {
                    const preview = formatSexpPreview(std.heap.page_allocator, sexp) catch null;
                    setCtx(T, sexp, field.name, preview);
                    return error.MissingField;
                }
            }
        }
    }
}

fn isSlice(comptime T: type, optional: bool) bool {
    return switch (@typeInfo(T)) {
        .pointer => |ptr| ptr.size == .slice and ptr.child != u8,
        .optional => |opt| optional and isSlice(opt.child, false),
        else => false,
    };
}

fn decodeOptional(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, metadata: SexpField) DecodeError!?T {
    if (ast.isList(sexp)) {
        const items = ast.getList(sexp).?;
        if (items.len == 0) return null;
    }
    return try decodeWithMetadata(T, allocator, sexp, metadata);
}

fn decodeLinkedList(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata;
    const NodeType = T.Node;
    const child_type = @FieldType(NodeType, "data");
    const items = ast.getList(sexp) orelse {
        setCtx(T, sexp, null, "expected list for linked list");
        return error.UnexpectedType;
    };
    var ll = T{};
    for (items) |item| {
        const val = try decodeWithMetadata(child_type, allocator, item, .{});
        const node = try allocator.create(NodeType);
        node.* = NodeType{ .data = val };
        ll.append(node);
    }
    return ll;
}

fn decodeSlice(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, metadata: SexpField) DecodeError!T {
    const child_type = std.meta.Child(T);

    // Special handling for strings ([]const u8)
    if (child_type == u8) {
        switch (sexp.value) {
            .string => |str| {
                // Duplicate strings to ensure proper memory ownership
                const duped = try allocator.alloc(u8, str.len);
                @memcpy(duped, str);
                return duped;
            },
            .symbol => |sym| {
                // Allow symbols as strings for KiCad compatibility
                const duped = try allocator.alloc(u8, sym.len);
                @memcpy(duped, sym);
                return duped;
            },
            .number => |num| {
                // Allow numbers as strings for KiCad compatibility
                const duped = try allocator.alloc(u8, num.len);
                @memcpy(duped, num);
                return duped;
            },
            else => {},
        }
    }

    // TODO: remove support for non-u8 slices (should be ArrayList)

    // For non-u8 slices, check if we have a list
    const items = ast.getList(sexp) orelse return error.UnexpectedType;

    var result = try allocator.alloc(child_type, items.len);
    for (items, 0..) |item, idx| {
        result[idx] = try decodeWithMetadata(child_type, allocator, item, metadata);
    }

    return result;
}

fn decodeInt(comptime T: type, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata; // metadata not used for basic types

    const str = switch (sexp.value) {
        .number => |n| n,
        .string => |s| {
            // More helpful error for common mistake of quoting numbers
            setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "got string \"{s}\" but expected unquoted number", .{s}) catch "string instead of number");
            return error.UnexpectedType;
        },
        .symbol => |s| {
            setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "got symbol '{s}' but expected number", .{s}) catch "symbol instead of number");
            return error.UnexpectedType;
        },
        else => {
            setCtx(T, sexp, null, "expected number for integer");
            return error.UnexpectedType;
        },
    };
    return std.fmt.parseInt(T, str, 10) catch {
        setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "failed to parse \"{s}\" as {s}", .{ str, @typeName(T) }) catch str);
        return error.InvalidValue;
    };
}

fn decodeFloat(comptime T: type, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata; // metadata not used for basic types

    const str = switch (sexp.value) {
        .number => |n| n,
        .string => |s| {
            setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "got string \"{s}\" but expected unquoted number", .{s}) catch "string instead of number");
            return error.UnexpectedType;
        },
        .symbol => |s| {
            setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "got symbol '{s}' but expected number", .{s}) catch "symbol instead of number");
            return error.UnexpectedType;
        },
        .list => |l| {
            _ = l; // list value not needed for error message
            setCtx(T, sexp, null, "got list but expected number");
            return error.UnexpectedType;
        },
        else => {
            setCtx(T, sexp, null, "expected number for float");
            return error.UnexpectedType;
        },
    };
    return std.fmt.parseFloat(T, str) catch {
        setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "failed to parse \"{s}\" as {s}", .{ str, @typeName(T) }) catch str);
        return error.InvalidValue;
    };
}

fn decodeBool(sexp: SExp, metadata: SexpField) DecodeError!bool {
    if (metadata.boolean_encoding == .parantheses_symbol) {
        if (ast.getList(sexp)) |list| {
            if (list.len == 0) return true;
        }
        setCtxPath("bool", sexp, null, "expected list for parantheses boolean");
        return error.UnexpectedType;
    }
    const sym = ast.getSymbol(sexp) orelse {
        setCtxPath("bool", sexp, null, "expected symbol for boolean");
        return error.UnexpectedType;
    };
    if (std.mem.eql(u8, sym, "yes")) return true;
    if (std.mem.eql(u8, sym, "no")) return false;
    if (std.mem.eql(u8, sym, "true")) return true;
    if (std.mem.eql(u8, sym, "false")) return false;

    setCtxPath("bool", sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "invalid boolean value '{s}' (expected yes/no/true/false)", .{sym}) catch "invalid boolean value");
    return error.InvalidValue;
}

fn decodeEnum(comptime T: type, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata; // metadata not used for basic enums (could be used for custom sexp_name in future)
    // Try to get the enum value as either a symbol, string, or number
    const enum_str = switch (sexp.value) {
        .symbol => |s| s,
        .string => |s| s,
        .number => |s| s,
        else => {
            setCtx(T, sexp, null, "expected symbol, string, or number for enum");
            return error.UnexpectedType;
        },
    };

    const enum_info = @typeInfo(T).@"enum";
    const tag_type_info = @typeInfo(enum_info.tag_type);
    const is_i32_backed = switch (tag_type_info) {
        .int => |int_info| int_info.signedness == .signed and int_info.bits == 32,
        else => false,
    };

    if (is_i32_backed) {
        // For i32 enums, first try parsing as integer value
        if (std.fmt.parseInt(enum_info.tag_type, enum_str, 0)) |enum_int| {
            // Find the enum field with this integer value
            inline for (std.meta.fields(T)) |field| {
                if (field.value == enum_int) {
                    return @field(T, field.name);
                }
            }
        } else |_| {
            // If parsing as integer failed, try matching as string name
        }

        // Fall back to string name matching
        inline for (std.meta.fields(T)) |field| {
            if (std.mem.eql(u8, enum_str, field.name)) {
                return @field(T, field.name);
            }
        }

        setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "invalid enum value '{s}' for type {s}", .{ enum_str, @typeName(T) }) catch "invalid enum value");
        return error.InvalidValue;
    } else {
        // For non-i32 enums, only match by string name
        inline for (std.meta.fields(T)) |field| {
            if (std.mem.eql(u8, enum_str, field.name)) {
                return @field(T, field.name);
            }
        }

        setCtx(T, sexp, null, std.fmt.allocPrint(std.heap.page_allocator, "invalid enum value '{s}' for type {s}", .{ enum_str, @typeName(T) }) catch "invalid enum value");
        return error.InvalidValue;
    }
}

// Main encode function with metadata
pub fn encode(allocator: std.mem.Allocator, value: anytype, metadata: SexpField, name: []const u8) EncodeError!SExp {
    const T = @TypeOf(value);
    const type_info = @typeInfo(T);

    // Special handling for enums
    if (type_info == .@"enum") {
        const enum_info = @typeInfo(T).@"enum";
        const tag_type_info = @typeInfo(enum_info.tag_type);
        const is_i32_backed = switch (tag_type_info) {
            .int => |int_info| int_info.signedness == .signed and int_info.bits == 32,
            else => false,
        };

        inline for (std.meta.fields(T)) |field| {
            if (@intFromEnum(value) == field.value) {
                if (is_i32_backed) {
                    // For i32 enums, output as number
                    var buf: [20]u8 = undefined;
                    const num_str = std.fmt.bufPrint(&buf, "{d}", .{@intFromEnum(value)}) catch unreachable;
                    return SExp{ .value = .{ .number = allocator.dupe(u8, num_str) catch unreachable }, .location = tokenizer.TokenLocation.none };
                } else {
                    // For other enums, use symbol/string as before
                    if (metadata.symbol orelse true) {
                        return SExp{ .value = .{ .symbol = field.name }, .location = tokenizer.TokenLocation.none };
                    } else {
                        return SExp{ .value = .{ .string = field.name }, .location = tokenizer.TokenLocation.none };
                    }
                }
            }
        }
        unreachable;
    }

    // Special handling for strings that should be encoded as symbols
    if (type_info == .pointer) {
        if (type_info.pointer.size == .slice and type_info.pointer.child == u8 and metadata.symbol orelse false) {
            // Encode as symbol instead of string
            return SExp{ .value = .{ .symbol = value }, .location = tokenizer.TokenLocation.none };
        }

        // Special handling for slices of strings that should be encoded as symbols
        if (type_info.pointer.size == .slice and metadata.symbol orelse false) {
            const child_type = type_info.pointer.child;
            if (@typeInfo(child_type) == .pointer and
                @typeInfo(child_type).pointer.size == .slice and
                @typeInfo(child_type).pointer.child == u8)
            {
                // This is [][]const u8 with symbol flag - encode each string as a symbol
                var items = try allocator.alloc(SExp, value.len);
                for (value, 0..) |str_val, i| {
                    items[i] = SExp{ .value = .{ .symbol = str_val }, .location = tokenizer.TokenLocation.none };
                }
                return SExp{ .value = .{ .list = items }, .location = tokenizer.TokenLocation.none };
            }
        }
    }

    switch (type_info) {
        .@"struct" => if (comptime isLinkedList(T)) {
            return try encodeLinkedList(allocator, value, metadata, name);
        } else {
            return try encodeStruct(allocator, value, metadata);
        },
        .optional => {
            if (value) |v| return try encode(allocator, v, metadata, name);
            return SExp{ .value = .{ .list = try allocator.alloc(SExp, 0) }, .location = tokenizer.TokenLocation.none };
        },
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child == u8) {
                // Handle strings
                return SExp{ .value = .{ .string = value }, .location = tokenizer.TokenLocation.none };
            } else if (ptr.size == .slice) {
                return try encodeSlice(allocator, value, metadata, name);
            }
            return error.InvalidType;
        },
        .int => {
            var buf: [32]u8 = undefined;
            const str = std.fmt.bufPrint(&buf, "{d}", .{value}) catch return error.OutOfMemory;
            const duped = try allocator.alloc(u8, str.len);
            @memcpy(duped, str);
            return SExp{ .value = .{ .number = duped }, .location = tokenizer.TokenLocation.none };
        },
        .float => {
            var buf: [32]u8 = undefined;
            // round float to 6 decimal places
            const rounded = std.math.round(value * 10e6) / 10e6;
            const fucked = std.mem.eql(u8, name, "dashed_line_dash_ratio") or std.mem.eql(u8, name, "dashed_line_gap_ratio") or std.mem.eql(u8, name, "hpglpendiameter");
            const is_whole = rounded == @trunc(rounded);
            const needs_six_decimals = fucked and !is_whole;
            const str = if (needs_six_decimals)
                std.fmt.bufPrint(&buf, "{d:.6}", .{rounded}) catch return error.OutOfMemory
            else
                std.fmt.bufPrint(&buf, "{d}", .{rounded}) catch return error.OutOfMemory;
            const duped = try allocator.alloc(u8, str.len);
            @memcpy(duped, str);
            return SExp{ .value = .{ .number = duped }, .location = tokenizer.TokenLocation.none };
        },
        .bool => {
            // Already handled by encodeStruct
            if (metadata.boolean_encoding == .parantheses_symbol) unreachable;
            return SExp{ .value = .{ .symbol = if (value) "yes" else "no" }, .location = tokenizer.TokenLocation.none };
        },
        .@"enum" => {
            inline for (std.meta.fields(T)) |field| {
                if (@intFromEnum(value) == field.value) {
                    return SExp{ .value = .{ .symbol = field.name }, .location = tokenizer.TokenLocation.none };
                }
            }
            unreachable;
        },
        else => return error.UnexpectedType,
    }
}

// Helper to sort field indices at compile time
fn sortFieldIndices(comptime T: type) [std.meta.fields(T).len]usize {
    @setEvalBranchQuota(15000); // Increase branch quota for compile-time sorting

    const fields = std.meta.fields(T);
    var indices: [fields.len]usize = undefined;

    // Initialize indices
    for (&indices, 0..) |*idx, i| {
        idx.* = i;
    }

    // Simple bubble sort at compile time
    var i: usize = 0;
    while (i < indices.len) : (i += 1) {
        var j: usize = 0;
        while (j < indices.len - 1) : (j += 1) {
            const lhs_metadata = comptime getSexpMetadata(T, fields[indices[j]].name);
            const rhs_metadata = comptime getSexpMetadata(T, fields[indices[j + 1]].name);
            if (lhs_metadata.order > rhs_metadata.order) {
                const temp = indices[j];
                indices[j] = indices[j + 1];
                indices[j + 1] = temp;
            }
        }
    }

    return indices;
}

inline fn saturatingAddUsize(lhs: usize, rhs: usize) usize {
    return std.math.add(usize, lhs, rhs) catch std.math.maxInt(usize);
}

fn encodeStruct(allocator: std.mem.Allocator, value: anytype, metadata: SexpField) EncodeError!SExp {
    _ = metadata;
    const T = @TypeOf(value);
    const fields = std.meta.fields(T);
    const sorted_indices = comptime sortFieldIndices(T);
    var estimated_items: usize = 8;

    inline for (sorted_indices) |idx| {
        const f = fields[idx];
        const fm = comptime getSexpMetadata(T, f.name);
        const fv = @field(value, f.name);

        if (fm.positional) {
            if (comptime isOptional(f.type)) {
                if (fv != null) estimated_items = saturatingAddUsize(estimated_items, 1);
            } else if (!((comptime isSlice(f.type, false)) and fv.len == 0)) {
                estimated_items = saturatingAddUsize(estimated_items, 1);
            }
            continue;
        }

        if (fm.multidict) {
            if (comptime isSlice(@TypeOf(fv), false)) {
                estimated_items = saturatingAddUsize(estimated_items, fv.len);
            } else if (comptime isLinkedList(@TypeOf(fv))) {
                var n = fv.first;
                while (n) |node| : (n = node.next) {
                    estimated_items = saturatingAddUsize(estimated_items, 1);
                }
            }
            continue;
        }

        if (comptime isOptional(@TypeOf(fv))) {
            if (fv != null) estimated_items = saturatingAddUsize(estimated_items, 1);
            continue;
        }

        if (comptime @TypeOf(fv) == bool and fm.boolean_encoding == .parantheses_symbol) {
            if (fv) estimated_items = saturatingAddUsize(estimated_items, 1);
            continue;
        }

        estimated_items = saturatingAddUsize(estimated_items, 1);
    }

    var items = try std.array_list.Managed(SExp).initCapacity(allocator, estimated_items);
    defer items.deinit();

    // Positional fields
    inline for (sorted_indices) |idx| {
        const f = fields[idx];
        const fm = comptime getSexpMetadata(T, f.name);
        if (!fm.positional) continue;
        const fv = @field(value, f.name);
        if (comptime isOptional(f.type)) {
            if (fv) |vv| try items.append(try encode(allocator, vv, fm, f.name));
        } else if (!((comptime isSlice(f.type, false)) and fv.len == 0)) {
            try items.append(try encode(allocator, fv, fm, f.name));
        }
    }

    // Non-positional fields
    inline for (sorted_indices) |idx| {
        const f = fields[idx];
        const fm = comptime getSexpMetadata(T, f.name);
        if (fm.positional) continue;
        const fname = fm.sexp_name orelse f.name;
        const fv = @field(value, f.name);

        if (fm.multidict) {
            if (comptime isSlice(@TypeOf(fv), false)) {
                for (fv) |elem| try appendKeyValue(allocator, &items, fname, try encode(allocator, elem, fm, f.name));
            } else if (comptime isLinkedList(@TypeOf(fv))) {
                var n = fv.first;
                while (n) |node| : (n = node.next) {
                    try appendKeyValue(allocator, &items, fname, try encode(allocator, node.data, fm, f.name));
                }
            }
            continue;
        }

        if (comptime isOptional(@TypeOf(fv))) {
            if (fv) |vv| try appendKeyValue(allocator, &items, fname, try encode(allocator, vv, fm, f.name));
            continue;
        }

        if (comptime @TypeOf(fv) == bool and fm.boolean_encoding == .parantheses_symbol) {
            if (fv) try items.append(SExp{ .value = .{ .symbol = fname }, .location = tokenizer.TokenLocation.none });
            continue;
        }

        try appendKeyValue(allocator, &items, fname, try encode(allocator, fv, fm, f.name));
    }

    const out = try items.toOwnedSlice();
    return SExp{ .value = .{ .list = out }, .location = tokenizer.TokenLocation.none };
}

fn appendKeyValue(allocator: std.mem.Allocator, items: *std.array_list.Managed(SExp), key: []const u8, encoded: SExp) EncodeError!void {
    if (ast.getList(encoded)) |lst| {
        if (lst.len == 0) return; // omit empty list fields entirely
        var kv = try allocator.alloc(SExp, lst.len + 1);
        kv[0] = SExp{ .value = .{ .symbol = key }, .location = tokenizer.TokenLocation.none };
        for (lst, 0..) |it, i| kv[i + 1] = it;
        try items.append(SExp{ .value = .{ .list = kv }, .location = tokenizer.TokenLocation.none });
    } else {
        var kv2 = try allocator.alloc(SExp, 2);
        kv2[0] = SExp{ .value = .{ .symbol = key }, .location = tokenizer.TokenLocation.none };
        kv2[1] = encoded;
        try items.append(SExp{ .value = .{ .list = kv2 }, .location = tokenizer.TokenLocation.none });
    }
}

fn encodeSlice(allocator: std.mem.Allocator, value: anytype, metadata: SexpField, name: []const u8) EncodeError!SExp {
    // TODO: remove (only used for non-str slices)
    var items = try allocator.alloc(SExp, value.len);
    for (value, 0..) |item, i| {
        items[i] = try encode(allocator, item, metadata, name);
    }
    return SExp{ .value = .{ .list = items }, .location = tokenizer.TokenLocation.none };
}

fn encodeLinkedList(allocator: std.mem.Allocator, value: anytype, metadata: SexpField, name: []const u8) EncodeError!SExp {
    // Count nodes first
    var count: usize = 0;
    var it = value.first;
    while (it) |n| : (it = n.next) count += 1;

    var items = try allocator.alloc(SExp, count);
    var i: usize = 0;
    it = value.first;
    while (it) |n| : (it = n.next) {
        items[i] = try encode(allocator, n.data, metadata, name);
        i += 1;
    }
    return SExp{ .value = .{ .list = items }, .location = tokenizer.TokenLocation.none };
}

pub const input = union(enum) {
    path: []const u8,
    string: []const u8,
    sexp: SExp,
};

pub const output = union(enum) {
    path: []const u8,
    string: *?[]const u8,
    sexp: *?SExp,
};

fn writeEscapedString(writer: anytype, str: []const u8) !void {
    try writer.writeByte('"');
    var last_char: u8 = 0;
    for (str) |c| {
        if (c == '"' and last_char != '\\') try writer.writeByte('\\');
        try writer.writeByte(c);
        last_char = c;
    }
    try writer.writeByte('"');
}

fn valueEncodesAsList(value: anytype, metadata: SexpField, name: []const u8) bool {
    const T = @TypeOf(value);
    const type_info = @typeInfo(T);

    return switch (type_info) {
        .optional => if (value) |v| valueEncodesAsList(v, metadata, name) else true,
        .@"struct" => true,
        .pointer => |ptr| ptr.size == .slice and ptr.child != u8,
        else => false,
    };
}

fn listWouldWriteAnyItems(value: anytype, metadata: SexpField, name: []const u8) bool {
    const T = @TypeOf(value);
    const type_info = @typeInfo(T);

    switch (type_info) {
        .optional => {
            if (value) |v| return listWouldWriteAnyItems(v, metadata, name);
            return false;
        },
        .@"struct" => {
            if (comptime isLinkedList(T)) {
                return value.first != null;
            }
            return structBodyWouldWriteAnyItems(value);
        },
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child != u8) {
                return value.len > 0;
            }
            return false;
        },
        else => return false,
    }
}

fn keyValueWouldWrite(value: anytype, metadata: SexpField, name: []const u8) bool {
    if (valueEncodesAsList(value, metadata, name)) {
        return listWouldWriteAnyItems(value, metadata, name);
    }
    return true;
}

fn structBodyWouldWriteAnyItems(value: anytype) bool {
    const T = @TypeOf(value);
    const fields = std.meta.fields(T);
    const sorted_indices = comptime sortFieldIndices(T);

    inline for (sorted_indices) |idx| {
        const f = fields[idx];
        const fm = comptime getSexpMetadata(T, f.name);
        const fv = @field(value, f.name);

        if (fm.positional) {
            if (comptime isOptional(f.type)) {
                if (fv != null) return true;
            } else if (!((comptime isSlice(f.type, false)) and fv.len == 0)) {
                return true;
            }
            continue;
        }

        if (fm.multidict) {
            if (comptime isSlice(@TypeOf(fv), false)) {
                if (fv.len > 0) return true;
            } else if (comptime isLinkedList(@TypeOf(fv))) {
                if (fv.first != null) return true;
            }
            continue;
        }

        if (comptime isOptional(@TypeOf(fv))) {
            if (fv) |vv| {
                if (keyValueWouldWrite(vv, fm, f.name)) return true;
            }
            continue;
        }

        if (comptime @TypeOf(fv) == bool and fm.boolean_encoding == .parantheses_symbol) {
            if (fv) return true;
            continue;
        }

        if (keyValueWouldWrite(fv, fm, f.name)) return true;
    }

    return false;
}

fn writeEncodedListItemsToWriter(
    allocator: std.mem.Allocator,
    writer: anytype,
    value: anytype,
    metadata: SexpField,
    name: []const u8,
    emit_leading_space: bool,
) !bool {
    const T = @TypeOf(value);
    const type_info = @typeInfo(T);

    switch (type_info) {
        .optional => {
            if (value) |v| {
                return try writeEncodedListItemsToWriter(allocator, writer, v, metadata, name, emit_leading_space);
            }
            return false;
        },
        .@"struct" => {
            if (comptime isLinkedList(T)) {
                var wrote_any = false;
                var it = value.first;
                while (it) |node| : (it = node.next) {
                    if (wrote_any or emit_leading_space) try writer.writeByte(' ');
                    try writeEncodedValueToWriter(allocator, writer, node.data, metadata, name);
                    wrote_any = true;
                }
                return wrote_any;
            }
            return writeStructBodyStreamed(allocator, writer, value, emit_leading_space);
        },
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child != u8) {
                var wrote_any = false;
                for (value) |item| {
                    if (wrote_any or emit_leading_space) try writer.writeByte(' ');
                    try writeEncodedValueToWriter(allocator, writer, item, metadata, name);
                    wrote_any = true;
                }
                return wrote_any;
            }
            return false;
        },
        else => return false,
    }
}

fn writeEncodedValueToWriter(
    allocator: std.mem.Allocator,
    writer: anytype,
    value: anytype,
    metadata: SexpField,
    name: []const u8,
) !void {
    const T = @TypeOf(value);
    const type_info = @typeInfo(T);

    if (type_info == .@"enum") {
        const enum_info = @typeInfo(T).@"enum";
        const tag_type_info = @typeInfo(enum_info.tag_type);
        const is_i32_backed = switch (tag_type_info) {
            .int => |int_info| int_info.signedness == .signed and int_info.bits == 32,
            else => false,
        };

        inline for (std.meta.fields(T)) |field| {
            if (@intFromEnum(value) == field.value) {
                if (is_i32_backed) {
                    var enum_buf: [20]u8 = undefined;
                    const enum_num = std.fmt.bufPrint(&enum_buf, "{d}", .{@intFromEnum(value)}) catch return error.OutOfMemory;
                    try writer.writeAll(enum_num);
                } else if (metadata.symbol orelse true) {
                    try writer.writeAll(field.name);
                } else {
                    try writeEscapedString(writer, field.name);
                }
                return;
            }
        }
        unreachable;
    }

    if (type_info == .pointer) {
        if (type_info.pointer.size == .slice and type_info.pointer.child == u8 and metadata.symbol orelse false) {
            try writer.writeAll(value);
            return;
        }
    }

    switch (type_info) {
        .@"struct" => {
            if (comptime isLinkedList(T)) {
                try writer.writeByte('(');
                var wrote_any = false;
                var it = value.first;
                while (it) |node| : (it = node.next) {
                    if (wrote_any) try writer.writeByte(' ');
                    try writeEncodedValueToWriter(allocator, writer, node.data, metadata, name);
                    wrote_any = true;
                }
                try writer.writeByte(')');
            } else {
                try writer.writeByte('(');
                _ = try writeStructBodyStreamed(allocator, writer, value, false);
                try writer.writeByte(')');
            }
        },
        .optional => {
            if (value) |v| {
                try writeEncodedValueToWriter(allocator, writer, v, metadata, name);
            } else {
                try writer.writeAll("()");
            }
        },
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child == u8) {
                try writeEscapedString(writer, value);
            } else if (ptr.size == .slice) {
                try writer.writeByte('(');
                for (value, 0..) |item, i| {
                    if (i > 0) try writer.writeByte(' ');
                    try writeEncodedValueToWriter(allocator, writer, item, metadata, name);
                }
                try writer.writeByte(')');
            } else {
                return error.InvalidType;
            }
        },
        .int => {
            var int_buf: [32]u8 = undefined;
            const int_str = std.fmt.bufPrint(&int_buf, "{d}", .{value}) catch return error.OutOfMemory;
            try writer.writeAll(int_str);
        },
        .float => {
            var float_buf: [32]u8 = undefined;
            const rounded = std.math.round(value * 10e6) / 10e6;
            const needs_fixed_precision = (std.mem.eql(u8, name, "dashed_line_dash_ratio") or
                std.mem.eql(u8, name, "dashed_line_gap_ratio") or
                std.mem.eql(u8, name, "hpglpendiameter")) and rounded != @trunc(rounded);
            const float_str = if (needs_fixed_precision)
                std.fmt.bufPrint(&float_buf, "{d:.6}", .{rounded}) catch return error.OutOfMemory
            else
                std.fmt.bufPrint(&float_buf, "{d}", .{rounded}) catch return error.OutOfMemory;
            try writer.writeAll(float_str);
        },
        .bool => {
            if (metadata.boolean_encoding == .parantheses_symbol) unreachable;
            try writer.writeAll(if (value) "yes" else "no");
        },
        .@"enum" => unreachable,
        else => return error.UnexpectedType,
    }
}

fn writeEncodedKeyValueToWriter(
    allocator: std.mem.Allocator,
    writer: anytype,
    key: []const u8,
    value: anytype,
    metadata: SexpField,
    name: []const u8,
    prepend_space: bool,
) !bool {
    if (!keyValueWouldWrite(value, metadata, name)) return false;

    if (prepend_space) try writer.writeByte(' ');
    try writer.writeByte('(');
    try writer.writeAll(key);
    if (valueEncodesAsList(value, metadata, name)) {
        _ = try writeEncodedListItemsToWriter(allocator, writer, value, metadata, name, true);
    } else {
        try writer.writeByte(' ');
        try writeEncodedValueToWriter(allocator, writer, value, metadata, name);
    }
    try writer.writeByte(')');
    return true;
}

fn writeStructBodyStreamed(allocator: std.mem.Allocator, writer: anytype, value: anytype, emit_leading_space: bool) !bool {
    const T = @TypeOf(value);
    const fields = std.meta.fields(T);
    const sorted_indices = comptime sortFieldIndices(T);

    var wrote_any: bool = false;

    inline for (sorted_indices) |idx| {
        const f = fields[idx];
        const fm = comptime getSexpMetadata(T, f.name);
        if (!fm.positional) continue;
        const fv = @field(value, f.name);

        if (comptime isOptional(f.type)) {
            if (fv) |vv| {
                if (wrote_any or emit_leading_space) try writer.writeByte(' ');
                try writeEncodedValueToWriter(allocator, writer, vv, fm, f.name);
                wrote_any = true;
            }
        } else if (!((comptime isSlice(f.type, false)) and fv.len == 0)) {
            if (wrote_any or emit_leading_space) try writer.writeByte(' ');
            try writeEncodedValueToWriter(allocator, writer, fv, fm, f.name);
            wrote_any = true;
        }
    }

    inline for (sorted_indices) |idx| {
        const f = fields[idx];
        const fm = comptime getSexpMetadata(T, f.name);
        if (fm.positional) continue;
        const fname = fm.sexp_name orelse f.name;
        const fv = @field(value, f.name);

        if (fm.multidict) {
            if (comptime isSlice(@TypeOf(fv), false)) {
                for (fv) |elem| {
                    const wrote = try writeEncodedKeyValueToWriter(
                        allocator,
                        writer,
                        fname,
                        elem,
                        fm,
                        f.name,
                        wrote_any or emit_leading_space,
                    );
                    if (wrote) wrote_any = true;
                }
                continue;
            } else if (comptime isLinkedList(@TypeOf(fv))) {
                var n = fv.first;
                while (n) |node| : (n = node.next) {
                    const wrote = try writeEncodedKeyValueToWriter(
                        allocator,
                        writer,
                        fname,
                        node.data,
                        fm,
                        f.name,
                        wrote_any or emit_leading_space,
                    );
                    if (wrote) wrote_any = true;
                }
                continue;
            }
        }

        if (comptime isOptional(@TypeOf(fv))) {
            if (fv) |vv| {
                if (try writeEncodedKeyValueToWriter(
                    allocator,
                    writer,
                    fname,
                    vv,
                    fm,
                    f.name,
                    wrote_any or emit_leading_space,
                )) {
                    wrote_any = true;
                }
            }
            continue;
        }

        if (comptime @TypeOf(fv) == bool and fm.boolean_encoding == .parantheses_symbol) {
            if (fv) {
                if (wrote_any or emit_leading_space) try writer.writeByte(' ');
                try writer.writeAll(fname);
                wrote_any = true;
            }
            continue;
        }

        const wrote = try writeEncodedKeyValueToWriter(
            allocator,
            writer,
            fname,
            fv,
            fm,
            f.name,
            wrote_any or emit_leading_space,
        );
        if (wrote) wrote_any = true;
    }
    return wrote_any;
}

pub fn encodeWrappedStreamForBenchmark(
    data: anytype,
    allocator: std.mem.Allocator,
    symbol_name: []const u8,
    writer: anytype,
) !void {
    try writer.writeByte('(');
    try writer.writeAll(symbol_name);
    if (try writeStructBodyStreamed(allocator, writer, data, true)) {
        // Body already emitted with separators.
    }
    try writer.writeByte(')');
}

// Encode data into a wrapped S-expression without prettifying.
//
// The returned SExp is intended for allocator/lifetime-managed usage (e.g. arena
// allocators). It may contain symbol slices that are not individually owned.
pub fn encodeWrappedForBenchmark(data: anytype, allocator: std.mem.Allocator, symbol_name: []const u8) !ast.SExp {
    // Encode the data into the struct body list
    const encoded = try encode(allocator, data, SexpField{}, symbol_name);
    const encoded_items = ast.getList(encoded).?;

    // Prepend root symbol
    var items = try allocator.alloc(ast.SExp, encoded_items.len + 1);
    items[0] = ast.SExp{ .value = .{ .symbol = symbol_name }, .location = tokenizer.TokenLocation.none };
    for (encoded_items, 0..) |item, i| {
        items[i + 1] = item;
    }

    // encoded's top-level list container is no longer needed after the copy.
    allocator.free(encoded_items);

    return ast.SExp{ .value = .{ .list = items }, .location = tokenizer.TokenLocation.none };
}

// Load a struct from an S-expression string with a wrapping symbol
fn decodeWrappedWithExpectedSymbol(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, expected_symbol: []const u8) !T {
    // The file structure is (symbol_name ...)
    const file_list = ast.getList(sexp) orelse {
        setCtx(T, sexp, null, "expected list at top level");
        return error.UnexpectedType;
    };
    if (file_list.len < 1) {
        setCtx(T, sexp, null, "empty top-level list");
        return error.UnexpectedType;
    }

    const symbol = ast.getSymbol(file_list[0]) orelse {
        setCtx(T, file_list[0], null, "expected symbol as first element");
        return error.UnexpectedType;
    };
    if (!std.mem.eql(u8, symbol, expected_symbol)) {
        setCtx(T, file_list[0], null, std.fmt.allocPrint(std.heap.page_allocator, "expected symbol '{s}' but got '{s}'", .{ expected_symbol, symbol }) catch "wrong symbol");
        return error.UnexpectedType;
    }

    // Create a new list without the symbol for decoding
    const contents = file_list[1..];
    const table_sexp = ast.SExp{ .value = .{ .list = contents }, .location = tokenizer.TokenLocation.none };

    // Decode
    return try decodeWithMetadata(T, allocator, table_sexp, SexpField{});
}

pub fn loads(comptime T: type, allocator: std.mem.Allocator, in: input, expected_symbol: []const u8) !T {
    switch (in) {
        .path => {
            const file_content = try std.fs.cwd().readFileAlloc(allocator, in.path, 200 * 1024 * 1024);
            defer allocator.free(file_content);
            const tokens = try tokenizer.tokenize(allocator, file_content);
            defer allocator.free(tokens);

            var fast_parse_arena = std.heap.ArenaAllocator.init(allocator);
            defer fast_parse_arena.deinit();
            const fast_sexp = try ast.parseBorrowedFast(fast_parse_arena.allocator(), file_content, tokens);
            if (decodeWrappedWithExpectedSymbol(T, allocator, fast_sexp, expected_symbol)) |decoded| {
                return decoded;
            } else |err| {
                if (err == error.OutOfMemory) return err;

                // Retry with location tracking for rich diagnostics.
                clearErrorContext();
                var diag_parse_arena = std.heap.ArenaAllocator.init(allocator);
                defer diag_parse_arena.deinit();
                const diag_sexp = try ast.parseBorrowed(diag_parse_arena.allocator(), file_content, tokens);
                return decodeWrappedWithExpectedSymbol(T, allocator, diag_sexp, expected_symbol);
            }
        },
        .string => {
            const tokens = try tokenizer.tokenize(allocator, in.string);
            defer allocator.free(tokens);

            var fast_parse_arena = std.heap.ArenaAllocator.init(allocator);
            defer fast_parse_arena.deinit();
            const fast_sexp = try ast.parseBorrowedFast(fast_parse_arena.allocator(), in.string, tokens);
            if (decodeWrappedWithExpectedSymbol(T, allocator, fast_sexp, expected_symbol)) |decoded| {
                return decoded;
            } else |err| {
                if (err == error.OutOfMemory) return err;

                // Retry with location tracking for rich diagnostics.
                clearErrorContext();
                var diag_parse_arena = std.heap.ArenaAllocator.init(allocator);
                defer diag_parse_arena.deinit();
                const diag_sexp = try ast.parseBorrowed(diag_parse_arena.allocator(), in.string, tokens);
                return decodeWrappedWithExpectedSymbol(T, allocator, diag_sexp, expected_symbol);
            }
        },
        .sexp => |s| {
            // When given a pre-parsed SExp, check if it's already unwrapped
            // (i.e., if it's the contents without the symbol wrapper)
            return decodeWrappedWithExpectedSymbol(T, allocator, s, expected_symbol);
            // for now dont support that
            //if (ast.isList(s)) {
            //    const items = ast.getList(s).?;
            //    if (items.len > 0) {
            //        if (ast.getSymbol(items[0])) |sym| {
            //            if (std.mem.eql(u8, sym, expected_symbol)) {
            //                // It has the wrapper, proceed normally
            //                sexp = s;
            //            } else {
            //                // Different symbol, error
            //                setErrorContext(.{
            //                    .path = @typeName(T),
            //                    .field_name = null,
            //                    .message = std.fmt.allocPrint(std.heap.page_allocator, "expected symbol '{s}' but got '{s}'", .{ expected_symbol, sym }) catch "wrong symbol",
            //                }, s);
            //                return error.UnexpectedType;
            //            }
            //        } else {
            //            // First item is not a symbol, assume it's already unwrapped
            //            return try decode(T, allocator, s);
            //        }
            //    } else {
            //        // Empty list, can't be a wrapped structure
            //        setErrorContext(.{
            //            .path = @typeName(T),
            //            .field_name = null,
            //            .message = "empty list cannot be a wrapped structure",
            //        }, s);
            //        return error.UnexpectedType;
            //    }
            //} else {
            //    // Not a list, can't be a wrapped structure
            //    setErrorContext(.{
            //        .path = @typeName(T),
            //        .field_name = null,
            //        .message = "expected list for wrapped structure",
            //    }, s);
            //    return error.UnexpectedType;
            //}
        },
    }
}

// Dump a struct to an S-expression string with a wrapping symbol
pub fn dumps(data: anytype, allocator: std.mem.Allocator, symbol_name: []const u8, out: output) !void {
    switch (out) {
        .sexp => |sexp| {
            var arena = std.heap.ArenaAllocator.init(allocator);
            defer arena.deinit();

            // Encode the data
            const encoded = try encode(arena.allocator(), data, SexpField{}, symbol_name);

            // The encoded result is a list of key-value pairs
            // We need to prepend the symbol name
            const encoded_items = ast.getList(encoded).?;

            var items = try arena.allocator().alloc(ast.SExp, encoded_items.len + 1);
            items[0] = ast.SExp{ .value = .{ .symbol = symbol_name }, .location = tokenizer.TokenLocation.none };

            // Copy the encoded items
            for (encoded_items, 0..) |item, i| {
                items[i + 1] = item;
            }

            const wrapped = ast.SExp{ .value = .{ .list = items }, .location = tokenizer.TokenLocation.none };
            sexp.* = wrapped;
        },
        .string, .path => {
            var raw = std.array_list.Managed(u8).init(allocator);
            defer raw.deinit();
            try encodeWrappedStreamForBenchmark(data, allocator, symbol_name, raw.writer());
            const out_str = try ast.SExp.prettify_sexp_string(allocator, raw.items);
            switch (out) {
                .string => |s| {
                    s.* = out_str;
                },
                .path => |p| {
                    defer allocator.free(out_str);
                    const file = try std.fs.cwd().createFile(p, .{ .truncate = true });
                    defer file.close();
                    try file.writeAll(out_str);
                },
                .sexp => unreachable,
            }
        },
    }
}

// Generic free function for structs decoded by this library
pub fn free(comptime T: type, allocator: std.mem.Allocator, value: T) void {
    const type_info = @typeInfo(T);

    switch (type_info) {
        .@"struct" => freeStruct(T, allocator, value),
        .pointer => |ptr| {
            if (ptr.size == .slice) {
                freeSlice(T, allocator, value);
            }
        },
        .optional => |opt| {
            if (value) |v| {
                free(opt.child, allocator, v);
            }
        },
        else => {},
    }
}

fn freeStruct(comptime T: type, allocator: std.mem.Allocator, value: T) void {
    const fields = std.meta.fields(T);

    inline for (fields) |field| {
        const field_value = @field(value, field.name);
        free(field.type, allocator, field_value);
    }
}

fn freeSlice(comptime T: type, allocator: std.mem.Allocator, value: T) void {
    const child_type = std.meta.Child(T);

    // Free each element in the slice
    if (comptime !isSimpleType(child_type)) {
        for (value) |item| {
            free(child_type, allocator, item);
        }
    }

    // Free the slice itself
    if (value.len > 0) {
        allocator.free(value);
    }
}
