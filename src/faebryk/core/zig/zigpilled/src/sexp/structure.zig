const std = @import("std");
const ast = @import("ast.zig");
const tokenizer = @import("tokenizer.zig");
const SExp = ast.SExp;

// Type trait helpers
fn isOptional(comptime T: type) bool {
    return @typeInfo(T) == .optional;
}

fn isSlice(comptime T: type) bool {
    return switch (@typeInfo(T)) {
        .pointer => |ptr| ptr.size == .slice,
        else => false,
    };
}

// Simplified field metadata
pub const SexpField = struct {
    positional: bool = false,
    multidict: bool = false,
    sexp_name: ?[]const u8 = null,
    order: i32 = 0,
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
    sexp_preview: ?[]const u8 = null,
    line: ?usize = null,
    column: ?usize = null,
    end_line: ?usize = null,
    end_column: ?usize = null,

    source: ?[]const u8 = null,
    indent: usize = 0,

    pub fn print_source(self: ErrorContext, source: []const u8, writer: anytype, indent: usize) !void {
        var line_iter = std.mem.tokenizeScalar(u8, source, '\n');
        var current_line: usize = 1;
        while (line_iter.next()) |line_text| {
            if (current_line == self.line) {
                // Print indentation
                try _print_indent(writer, indent);
                try writer.print("Source: {s}\n", .{line_text});

                // Show cursor position with indentation
                try _print_indent(writer, indent);
                try writer.print("        ", .{});

                var i: usize = 1;
                if (self.column) |col| {
                    while (i < col) : (i += 1) {
                        try writer.print(" ", .{});
                    }
                    if (self.end_column) |end_col| {
                        const len = if (self.end_line == self.line) end_col - col else line_text.len - col + 1;
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
        try writer.print("ErrorContext(\n  Struct: {s},\n  Field: {?s},\n  Problem: {?s},\n  Location: {?d}:{?d} to {?d}:{?d}", .{ self.path, self.field_name, self.sexp_preview, self.line, self.column, self.end_line, self.end_column });
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

// Thread-local error context
threadlocal var current_error_context: ?ErrorContext = null;

pub fn getErrorContext() ?ErrorContext {
    return current_error_context;
}

fn clearErrorContext() void {
    current_error_context = null;
}

// Helper to set error context with location from SExp
fn setErrorContext(base_ctx: ErrorContext, sexp: SExp) void {
    var ctx = base_ctx;

    if (sexp.location) |location| {
        ctx.line = location.start.line;
        ctx.column = location.start.column;
        ctx.end_line = location.end.line;
        ctx.end_column = location.end.column;
    }

    current_error_context = ctx;
}

// Helper to format S-expression preview
fn formatSexpPreview(allocator: std.mem.Allocator, sexp: SExp) ![]u8 {
    var buf = std.ArrayList(u8).init(allocator);
    defer buf.deinit();

    try formatSexpPreviewInternal(sexp, &buf, 0, 50); // max 50 chars
    return try buf.toOwnedSlice();
}

fn formatSexpPreviewInternal(sexp: SExp, buf: *std.ArrayList(u8), depth: usize, max_len: usize) !void {
    if (buf.items.len >= max_len) {
        try buf.appendSlice("...");
        return;
    }

    switch (sexp.value) {
        .symbol => |s| try buf.appendSlice(s),
        .string => |s| {
            try buf.append('"');
            const preview_len = @min(s.len, max_len - buf.items.len - 2);
            try buf.appendSlice(s[0..preview_len]);
            if (preview_len < s.len) try buf.appendSlice("...");
            try buf.append('"');
        },
        .number => |n| try buf.appendSlice(n),
        .comment => |c| {
            try buf.appendSlice("; ");
            const preview_len = @min(c.len, max_len - buf.items.len - 2);
            try buf.appendSlice(c[0..preview_len]);
            if (preview_len < c.len) try buf.appendSlice("...");
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
            return result;
        }
    }
    return SexpField{};
}

// Main decode function
pub fn decode(comptime T: type, allocator: std.mem.Allocator, sexp: SExp) DecodeError!T {
    const type_info = @typeInfo(T);

    switch (type_info) {
        .@"struct" => return try decodeStruct(T, allocator, sexp),
        .optional => |opt| return try decodeOptional(opt.child, allocator, sexp),
        .pointer => |ptr| {
            if (ptr.size == .slice) {
                return try decodeSlice(T, allocator, sexp);
            }
            setErrorContext(.{
                .path = @typeName(T),
                .field_name = null,
                .sexp_preview = "unsupported pointer type (only slices are supported)",
            }, sexp);
            return error.InvalidType;
        },
        .int => return try decodeInt(T, sexp),
        .float => return try decodeFloat(T, sexp),
        .bool => return try decodeBool(sexp),
        .@"enum" => return try decodeEnum(T, sexp),
        else => {
            setErrorContext(.{
                .path = @typeName(T),
                .field_name = null,
                .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "unsupported type: {s}", .{@typeName(T)}) catch "unsupported type",
            }, sexp);
            return error.InvalidType;
        },
    }
}

fn decodeStruct(comptime T: type, allocator: std.mem.Allocator, sexp: SExp) DecodeError!T {
    const fields = std.meta.fields(T);
    var result: T = std.mem.zeroInit(T, .{});

    const items = ast.getList(sexp) orelse {
        setErrorContext(.{
            .path = @typeName(T),
            .field_name = null,
            .sexp_preview = "expected list for struct",
        }, sexp);
        return error.UnexpectedType;
    };

    // Track which fields have been set
    var fields_set = std.StaticBitSet(fields.len).initEmpty();

    // Add errdefer to clean up partial allocations on error
    errdefer {
        // Free any fields that were already allocated
        inline for (fields, 0..) |field, idx| {
            if (fields_set.isSet(idx)) {
                free(field.type, allocator, @field(result, field.name));
            }
        }
    }

    // First, count how many key-value pairs we have
    var kv_count: usize = 0;
    for (items) |item| {
        if (ast.isList(item)) {
            const kv_items = ast.getList(item).?;
            if (kv_items.len >= 2) {
                if (ast.getSymbol(kv_items[0]) != null) {
                    kv_count += 1;
                }
            }
        }
    }

    // Process positional fields based on order
    inline for (fields, 0..) |field, field_idx| {
        const metadata = comptime getSexpMetadata(T, field.name);
        if (metadata.positional) {
            // If order > 0, it means this positional field comes after named fields
            const pos_start = if (metadata.order > 0) kv_count else 0;
            const pos_idx = pos_start + @as(usize, @intCast(@max(0, metadata.order - 1)));

            if (pos_idx < items.len and !ast.isList(items[pos_idx])) {
                // Set context for positional fields too
                setErrorContext(.{
                    .path = @typeName(T),
                    .field_name = field.name,
                    .sexp_preview = null,
                }, items[pos_idx]);
                @field(result, field.name) = try decode(field.type, allocator, items[pos_idx]);
                fields_set.set(field_idx);
            }
        }
    }

    // Process key-value pairs
    var i: usize = 0;
    while (i < items.len) : (i += 1) {
        if (ast.isList(items[i])) {
            const kv_items = ast.getList(items[i]).?;
            if (kv_items.len < 2) continue;

            const key = ast.getSymbol(kv_items[0]) orelse continue;

            // Find matching field
            inline for (fields, 0..) |field, field_idx| {
                const metadata = comptime getSexpMetadata(T, field.name);
                const field_name = metadata.sexp_name orelse field.name;

                if (std.mem.eql(u8, key, field_name)) {
                    if (metadata.multidict) {
                        // Handle multidict fields
                        if (comptime isSlice(field.type)) {
                            // Check if we already started collecting values for this field
                            if (!fields_set.isSet(field_idx)) {
                                const ChildType = std.meta.Child(field.type);
                                var values = std.ArrayList(ChildType).init(allocator);

                                // Collect all matching entries from the entire list
                                var scan_idx: usize = i;
                                while (scan_idx < items.len) : (scan_idx += 1) {
                                    if (ast.isList(items[scan_idx])) {
                                        const scan_kv = ast.getList(items[scan_idx]).?;
                                        if (scan_kv.len >= 2) {
                                            const scan_key = ast.getSymbol(scan_kv[0]) orelse continue;
                                            if (std.mem.eql(u8, field_name, scan_key)) {
                                                // Set context for multidict items
                                                setErrorContext(.{
                                                    .path = @typeName(T),
                                                    .field_name = field.name,
                                                    .sexp_preview = null,
                                                }, items[scan_idx]);
                                                // For multidict entries, decode the rest as struct fields
                                                const scan_struct_sexp = SExp{ .value = .{ .list = scan_kv[1..] }, .location = null };
                                                const scan_val = try decode(ChildType, allocator, scan_struct_sexp);
                                                try values.append(scan_val);
                                            }
                                        }
                                    }
                                }

                                @field(result, field.name) = try values.toOwnedSlice();
                                fields_set.set(field_idx);
                            }
                        }
                    } else {
                        // Single value
                        if (!fields_set.isSet(field_idx)) {
                            // Set context before decoding so errors have proper context
                            setErrorContext(.{
                                .path = @typeName(T),
                                .field_name = field.name,
                                .sexp_preview = null,
                            }, items[i]);
                            @field(result, field.name) = if (kv_items.len == 2)
                                try decode(field.type, allocator, kv_items[1])
                            else
                                try decode(field.type, allocator, SExp{ .value = .{ .list = kv_items[1..] }, .location = null });
                            fields_set.set(field_idx);
                        }
                    }
                    break;
                }
            }
        }
    }

    // Check required fields and set defaults
    inline for (fields, 0..) |field, field_idx| {
        if (!fields_set.isSet(field_idx)) {
            const metadata = comptime getSexpMetadata(T, field.name);

            // Handle different field types
            if (comptime isOptional(field.type)) {
                @field(result, field.name) = null;
            } else if (comptime isSlice(field.type) and metadata.multidict) {
                // Empty slice for multidict
                @field(result, field.name) = try allocator.alloc(std.meta.Child(field.type), 0);
            } else {
                // Use default if available
                const default_instance = std.mem.zeroInit(T, .{});
                const zero_value = std.mem.zeroes(field.type);
                if (!std.meta.eql(@field(default_instance, field.name), zero_value)) {
                    @field(result, field.name) = @field(default_instance, field.name);
                } else if (field.default_value_ptr) |default_ptr| {
                    // Use field default value
                    const default_bytes = @as([*]const u8, @ptrCast(default_ptr))[0..@sizeOf(field.type)];
                    @memcpy(@as([*]u8, @ptrCast(&@field(result, field.name)))[0..@sizeOf(field.type)], default_bytes);
                } else {
                    // Set error context before returning error
                    // Use page allocator for preview since error context is global
                    const preview = formatSexpPreview(std.heap.page_allocator, sexp) catch null;
                    setErrorContext(.{
                        .path = @typeName(T),
                        .field_name = field.name,
                        .sexp_preview = preview,
                    }, sexp);
                    return error.MissingField;
                }
            }
        }
    }

    return result;
}

fn decodeOptional(comptime T: type, allocator: std.mem.Allocator, sexp: SExp) DecodeError!?T {
    if (ast.isList(sexp)) {
        const items = ast.getList(sexp).?;
        if (items.len == 0) return null;
    }
    return try decode(T, allocator, sexp);
}

fn decodeSlice(comptime T: type, allocator: std.mem.Allocator, sexp: SExp) DecodeError!T {
    const child_type = std.meta.Child(T);

    // Special handling for strings ([]const u8)
    if (child_type == u8) {
        switch (sexp.value) {
            .string => |str| {
                const duped = try allocator.alloc(u8, str.len);
                @memcpy(duped, str);
                return duped;
            },
            .symbol, .number => {
                // Get current context to preserve field name
                const ctx = getErrorContext();
                setErrorContext(.{
                    .path = if (ctx) |c| c.path else @typeName(T),
                    .field_name = if (ctx) |c| c.field_name else null,
                    .sexp_preview = "expected quoted string, got unquoted value",
                }, sexp);
                return error.UnexpectedType;
            },
            else => {},
        }
    }

    const items = ast.getList(sexp) orelse {
        // Get current context to preserve field name
        const ctx = getErrorContext();
        setErrorContext(.{
            .path = if (ctx) |c| c.path else @typeName(T),
            .field_name = if (ctx) |c| c.field_name else null,
            .sexp_preview = "expected list for slice",
        }, sexp);
        return error.UnexpectedType;
    };

    var result = try allocator.alloc(child_type, items.len);
    for (items, 0..) |item, idx| {
        result[idx] = try decode(child_type, allocator, item);
    }

    return result;
}

fn decodeInt(comptime T: type, sexp: SExp) DecodeError!T {
    // Get current context to preserve field name
    const ctx = getErrorContext();

    const str = switch (sexp.value) {
        .number => |n| n,
        .string => |s| {
            // More helpful error for common mistake of quoting numbers
            setErrorContext(.{
                .path = if (ctx) |c| c.path else @typeName(T),
                .field_name = if (ctx) |c| c.field_name else null,
                .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "got string \"{s}\" but expected unquoted number", .{s}) catch "string instead of number",
            }, sexp);
            return error.UnexpectedType;
        },
        .symbol => |s| {
            setErrorContext(.{
                .path = if (ctx) |c| c.path else @typeName(T),
                .field_name = if (ctx) |c| c.field_name else null,
                .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "got symbol '{s}' but expected number", .{s}) catch "symbol instead of number",
            }, sexp);
            return error.UnexpectedType;
        },
        else => {
            setErrorContext(.{
                .path = if (ctx) |c| c.path else @typeName(T),
                .field_name = if (ctx) |c| c.field_name else null,
                .sexp_preview = "expected number for integer",
            }, sexp);
            return error.UnexpectedType;
        },
    };
    return std.fmt.parseInt(T, str, 10) catch {
        setErrorContext(.{
            .path = if (ctx) |c| c.path else @typeName(T),
            .field_name = if (ctx) |c| c.field_name else null,
            .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "failed to parse \"{s}\" as {s}", .{ str, @typeName(T) }) catch str,
        }, sexp);
        return error.InvalidValue;
    };
}

fn decodeFloat(comptime T: type, sexp: SExp) DecodeError!T {
    // Get current context to preserve field name
    const ctx = getErrorContext();

    const str = switch (sexp.value) {
        .number => |n| n,
        .string => |s| {
            setErrorContext(.{
                .path = if (ctx) |c| c.path else @typeName(T),
                .field_name = if (ctx) |c| c.field_name else null,
                .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "got string \"{s}\" but expected unquoted number", .{s}) catch "string instead of number",
            }, sexp);
            return error.UnexpectedType;
        },
        .symbol => |s| {
            setErrorContext(.{
                .path = if (ctx) |c| c.path else @typeName(T),
                .field_name = if (ctx) |c| c.field_name else null,
                .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "got symbol '{s}' but expected number", .{s}) catch "symbol instead of number",
            }, sexp);
            return error.UnexpectedType;
        },
        else => {
            setErrorContext(.{
                .path = if (ctx) |c| c.path else @typeName(T),
                .field_name = if (ctx) |c| c.field_name else null,
                .sexp_preview = "expected number for float",
            }, sexp);
            return error.UnexpectedType;
        },
    };
    return std.fmt.parseFloat(T, str) catch {
        setErrorContext(.{
            .path = if (ctx) |c| c.path else @typeName(T),
            .field_name = if (ctx) |c| c.field_name else null,
            .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "failed to parse \"{s}\" as {s}", .{ str, @typeName(T) }) catch str,
        }, sexp);
        return error.InvalidValue;
    };
}

fn decodeBool(sexp: SExp) DecodeError!bool {
    const sym = ast.getSymbol(sexp) orelse {
        // Get current context to preserve field name
        const ctx = getErrorContext();
        setErrorContext(.{
            .path = if (ctx) |c| c.path else "bool",
            .field_name = if (ctx) |c| c.field_name else null,
            .sexp_preview = "expected symbol for boolean",
        }, sexp);
        return error.UnexpectedType;
    };
    if (std.mem.eql(u8, sym, "yes")) return true;
    if (std.mem.eql(u8, sym, "no")) return false;
    if (std.mem.eql(u8, sym, "true")) return true;
    if (std.mem.eql(u8, sym, "false")) return false;

    // Get current context to preserve field name
    const ctx = getErrorContext();
    setErrorContext(.{
        .path = if (ctx) |c| c.path else "bool",
        .field_name = if (ctx) |c| c.field_name else null,
        .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "invalid boolean value '{s}' (expected yes/no/true/false)", .{sym}) catch "invalid boolean value",
    }, sexp);
    return error.InvalidValue;
}

fn decodeEnum(comptime T: type, sexp: SExp) DecodeError!T {
    const sym = ast.getSymbol(sexp) orelse {
        // Get current context to preserve field name
        const ctx = getErrorContext();
        setErrorContext(.{
            .path = if (ctx) |c| c.path else @typeName(T),
            .field_name = if (ctx) |c| c.field_name else null,
            .sexp_preview = "expected symbol for enum",
        }, sexp);
        return error.UnexpectedType;
    };
    inline for (std.meta.fields(T)) |field| {
        if (std.mem.eql(u8, sym, field.name)) {
            return @field(T, field.name);
        }
    }

    // Get current context to preserve field name
    const ctx = getErrorContext();
    setErrorContext(.{
        .path = if (ctx) |c| c.path else @typeName(T),
        .field_name = if (ctx) |c| c.field_name else null,
        .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "invalid enum value '{s}' for type {s}", .{ sym, @typeName(T) }) catch "invalid enum value",
    }, sexp);
    return error.InvalidValue;
}

// Main encode function
pub fn encode(allocator: std.mem.Allocator, value: anytype) EncodeError!SExp {
    const T = @TypeOf(value);
    const type_info = @typeInfo(T);

    switch (type_info) {
        .@"struct" => return try encodeStruct(allocator, value),
        .optional => {
            if (value) |v| return try encode(allocator, v);
            return SExp{ .value = .{ .list = try allocator.alloc(SExp, 0) }, .location = null };
        },
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child == u8) {
                // Handle strings
                return SExp{ .value = .{ .string = value }, .location = null };
            } else if (ptr.size == .slice) {
                return try encodeSlice(allocator, value);
            }
            return error.InvalidType;
        },
        .int => {
            var buf: [32]u8 = undefined;
            const str = std.fmt.bufPrint(&buf, "{d}", .{value}) catch return error.OutOfMemory;
            const duped = try allocator.alloc(u8, str.len);
            @memcpy(duped, str);
            return SExp{ .value = .{ .number = duped }, .location = null };
        },
        .float => {
            var buf: [32]u8 = undefined;
            const str = std.fmt.bufPrint(&buf, "{d}", .{value}) catch return error.OutOfMemory;
            const duped = try allocator.alloc(u8, str.len);
            @memcpy(duped, str);
            return SExp{ .value = .{ .number = duped }, .location = null };
        },
        .bool => return SExp{ .value = .{ .symbol = if (value) "yes" else "no" }, .location = null },
        .@"enum" => {
            inline for (std.meta.fields(T)) |field| {
                if (@intFromEnum(value) == field.value) {
                    return SExp{ .value = .{ .symbol = field.name }, .location = null };
                }
            }
            unreachable;
        },
        else => return error.InvalidType,
    }
}

fn encodeStruct(allocator: std.mem.Allocator, value: anytype) EncodeError!SExp {
    const T = @TypeOf(value);
    var items = std.ArrayList(SExp).init(allocator);
    defer items.deinit();

    const fields = std.meta.fields(T);

    // Process positional fields first
    inline for (fields) |field| {
        const metadata = getSexpMetadata(T, field.name);
        if (metadata.positional) {
            const field_value = @field(value, field.name);
            const encoded = try encode(allocator, field_value);
            try items.append(encoded);
        }
    }

    // Then process non-positional fields
    inline for (fields) |field| {
        const metadata = getSexpMetadata(T, field.name);
        if (!metadata.positional) {
            const field_value = @field(value, field.name);
            const field_name = metadata.sexp_name orelse field.name;

            if (metadata.multidict) {
                // Handle multidict
                if (comptime isSlice(@TypeOf(field_value))) {
                    for (field_value) |item| {
                        // Encode the item
                        const encoded_item = try encode(allocator, item);

                        // For multidict structs, we want to unwrap the struct encoding
                        // and prepend the field name
                        if (ast.getList(encoded_item)) |item_contents| {
                            // Create a new list with the field name prepended
                            var kv_items = try allocator.alloc(SExp, item_contents.len + 1);
                            kv_items[0] = SExp{ .value = .{ .symbol = field_name }, .location = null };
                            for (item_contents, 0..) |content, idx| {
                                kv_items[idx + 1] = content;
                            }
                            try items.append(SExp{ .value = .{ .list = kv_items }, .location = null });
                        } else {
                            // Not a list, encode normally
                            var kv_items = try allocator.alloc(SExp, 2);
                            kv_items[0] = SExp{ .value = .{ .symbol = field_name }, .location = null };
                            kv_items[1] = encoded_item;
                            try items.append(SExp{ .value = .{ .list = kv_items }, .location = null });
                        }
                    }
                }
            } else {
                // Handle optional values
                if (comptime isOptional(@TypeOf(field_value))) {
                    if (field_value) |val| {
                        var kv_items = try allocator.alloc(SExp, 2);
                        kv_items[0] = SExp{ .value = .{ .symbol = field_name }, .location = null };
                        kv_items[1] = try encode(allocator, val);
                        try items.append(SExp{ .value = .{ .list = kv_items }, .location = null });
                    }
                } else {
                    var kv_items = try allocator.alloc(SExp, 2);
                    kv_items[0] = SExp{ .value = .{ .symbol = field_name }, .location = null };
                    kv_items[1] = try encode(allocator, field_value);
                    try items.append(SExp{ .value = .{ .list = kv_items }, .location = null });
                }
            }
        }
    }

    return SExp{ .value = .{ .list = try items.toOwnedSlice() }, .location = null };
}

fn encodeSlice(allocator: std.mem.Allocator, value: anytype) EncodeError!SExp {
    var items = try allocator.alloc(SExp, value.len);
    for (value, 0..) |item, i| {
        items[i] = try encode(allocator, item);
    }
    return SExp{ .value = .{ .list = items }, .location = null };
}

pub const input = union(enum) {
    path: []const u8,
    string: []const u8,
    sexp: SExp,
};

pub const output = union(enum) {
    path: []const u8,
    string: []const u8,
};

// Load a struct from an S-expression string with a wrapping symbol
pub fn loads(comptime T: type, allocator: std.mem.Allocator, in: input, expected_symbol: []const u8) !T {
    // Parse S-expression from input
    var sexp: SExp = undefined;
    var should_deinit = false;

    switch (in) {
        .path => {
            const file_content = try std.fs.cwd().readFileAlloc(allocator, in.path, 200 * 1024 * 1024);
            defer allocator.free(file_content);
            const tokens = try tokenizer.tokenize(allocator, file_content);
            defer allocator.free(tokens);
            sexp = try ast.parse(allocator, tokens);
            should_deinit = true;
        },
        .string => {
            const tokens = try tokenizer.tokenize(allocator, in.string);
            defer allocator.free(tokens);
            sexp = try ast.parse(allocator, tokens);
            should_deinit = true;
        },
        .sexp => |s| {
            // When given a pre-parsed SExp, check if it's already unwrapped
            // (i.e., if it's the contents without the symbol wrapper)
            sexp = s;
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
            //                    .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "expected symbol '{s}' but got '{s}'", .{ expected_symbol, sym }) catch "wrong symbol",
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
            //            .sexp_preview = "empty list cannot be a wrapped structure",
            //        }, s);
            //        return error.UnexpectedType;
            //    }
            //} else {
            //    // Not a list, can't be a wrapped structure
            //    setErrorContext(.{
            //        .path = @typeName(T),
            //        .field_name = null,
            //        .sexp_preview = "expected list for wrapped structure",
            //    }, s);
            //    return error.UnexpectedType;
            //}
        },
    }
    defer if (should_deinit) sexp.deinit(allocator);

    // The file structure is (symbol_name ...)
    const file_list = ast.getList(sexp) orelse {
        setErrorContext(.{
            .path = @typeName(T),
            .field_name = null,
            .sexp_preview = "expected list at top level",
        }, sexp);
        return error.UnexpectedType;
    };
    if (file_list.len < 1) {
        setErrorContext(.{
            .path = @typeName(T),
            .field_name = null,
            .sexp_preview = "empty top-level list",
        }, sexp);
        return error.UnexpectedType;
    }

    const symbol = ast.getSymbol(file_list[0]) orelse {
        setErrorContext(.{
            .path = @typeName(T),
            .field_name = null,
            .sexp_preview = "expected symbol as first element",
        }, file_list[0]);
        return error.UnexpectedType;
    };
    if (!std.mem.eql(u8, symbol, expected_symbol)) {
        setErrorContext(.{
            .path = @typeName(T),
            .field_name = null,
            .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "expected symbol '{s}' but got '{s}'", .{ expected_symbol, symbol }) catch "wrong symbol",
        }, file_list[0]);
        return error.UnexpectedType;
    }

    // Create a new list without the symbol for decoding
    const contents = file_list[1..];
    const table_sexp = ast.SExp{ .value = .{ .list = contents }, .location = null };

    // Decode
    return try decode(T, allocator, table_sexp);
}

// Dump a struct to an S-expression string with a wrapping symbol
pub fn dumps(data: anytype, allocator: std.mem.Allocator, symbol_name: []const u8, out: ?output) ![]u8 {
    if (out != null) {
        //TODO
    }

    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    // Encode the data
    const encoded = try encode(arena.allocator(), data);

    // The encoded result is a list of key-value pairs
    // We need to prepend the symbol name
    const encoded_items = ast.getList(encoded).?;

    var items = try arena.allocator().alloc(ast.SExp, encoded_items.len + 1);
    items[0] = ast.SExp{ .value = .{ .symbol = symbol_name }, .location = null };

    // Copy the encoded items
    for (encoded_items, 0..) |item, i| {
        items[i + 1] = item;
    }

    const wrapped = ast.SExp{ .value = .{ .list = items }, .location = null };

    // Write to string
    var buffer = std.ArrayList(u8).init(allocator);
    const writer = buffer.writer();

    try wrapped.str(writer);

    return try buffer.toOwnedSlice();
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

fn isSimpleType(comptime T: type) bool {
    return switch (@typeInfo(T)) {
        .int, .float, .bool, .@"enum" => true,
        // Don't consider strings as simple - they need to be freed
        else => false,
    };
}
