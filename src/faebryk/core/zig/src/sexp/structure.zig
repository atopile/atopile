const std = @import("std");
const ast = @import("ast.zig");
const tokenizer = @import("tokenizer.zig");
pub const SExp = ast.SExp;

// Type trait helpers
fn isOptional(comptime T: type) bool {
    return @typeInfo(T) == .optional;
}

fn isArrayList(comptime T: type) bool {
    return @typeInfo(T) == .@"struct" and @hasField(T, "items");
}

fn isLinkedList(comptime T: type) bool {
    return @typeInfo(T) == .@"struct" and @hasField(T, "first") and @hasField(T, "last") and @hasDecl(T, "Node");
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
        .@"struct" => if (comptime isArrayList(T)) {
            return try decodeArrayList(T, allocator, sexp, metadata);
        } else if (comptime isLinkedList(T)) {
            return try decodeLinkedList(T, allocator, sexp, metadata);
        } else {
            return try decodeStruct(T, allocator, sexp, metadata);
        },
        .optional => |opt| return try decodeOptional(opt.child, allocator, sexp, metadata),
        .pointer => |ptr| {
            if (ptr.size == .slice) {
                return try decodeSlice(T, allocator, sexp, metadata);
            }
            setErrorContext(.{
                .path = @typeName(T),
                .field_name = null,
                .sexp_preview = "unsupported pointer type (only slices are supported)",
            }, sexp);
            return error.UnexpectedType;
        },
        .int => return try decodeInt(T, sexp, metadata),
        .float => return try decodeFloat(T, sexp, metadata),
        .bool => return try decodeBool(sexp, metadata),
        .@"enum" => return try decodeEnum(T, sexp, metadata),
        .@"union" => {
            // If no custom decode, unions need custom decoders
            setErrorContext(.{
                .path = @typeName(T),
                .field_name = null,
                .sexp_preview = "union types require custom decode method",
            }, sexp);
            return error.UnexpectedType;
        },
        else => {
            setErrorContext(.{
                .path = @typeName(T),
                .field_name = null,
                .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "unsupported type: {s}", .{@typeName(T)}) catch "unsupported type",
            }, sexp);
            return error.UnexpectedType;
        },
    }
}

fn decodeStruct(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata; // metadata not used at struct level, only for individual fields
    @setEvalBranchQuota(15000);
    const fields = std.meta.fields(T);
    var result: T = undefined;

    const items = ast.getList(sexp) orelse {
        setErrorContext(.{
            .path = @typeName(T),
            .field_name = null,
            .sexp_preview = "expected list for struct",
        }, sexp);
        return error.UnexpectedType;
    };

    // Special case: if the struct has exactly one non-optional, non-default field and the sexp
    // is a single nested structure matching that field, treat the entire sexp as that field's value
    // This handles cases like (font ...) being passed to Effects{font: Font}
    comptime var non_optional_non_default_count: usize = 0;
    comptime var single_field_name: ?[]const u8 = null;
    comptime {
        for (fields) |field| {
            if (!isOptional(field.type)) {
                // Check if field has a default value
                const has_default = field.default_value_ptr != null;

                if (!has_default) {
                    non_optional_non_default_count += 1;
                    single_field_name = field.name;
                }
            }
        }
    }

    // Check if struct has any positional fields
    comptime var has_positional_fields = false;
    comptime {
        for (fields) |field| {
            const field_metadata = getSexpMetadata(T, field.name);
            if (field_metadata.positional) {
                has_positional_fields = true;
                break;
            }
        }
    }

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

    // Check if this is a struct with only positional fields
    const all_positional = comptime blk: {
        var all_pos = true;
        var has_fields = false;
        for (fields) |field| {
            const field_metadata_inner = getSexpMetadata(T, field.name);
            has_fields = true;
            if (!field_metadata_inner.positional) {
                all_pos = false;
                break;
            }
        }
        break :blk all_pos and has_fields;
    };

    // For structs with only positional fields, check if we need to skip a type symbol
    // This handles cases like (xyz 0 0 0) where "xyz" is the type name
    // But NOT cases like (edge 0.5) where "edge" is actual data
    var positional_start: usize = 0;
    if (all_positional and items.len > 0) {
        if (ast.getSymbol(items[0])) |sym| {
            // Only skip if the symbol looks like a type name (lowercase version of struct name)
            const type_name = @typeName(T);
            var last_dot: usize = 0;
            for (type_name, 0..) |c, i| {
                if (c == '.') last_dot = i + 1;
            }
            const short_name = type_name[last_dot..];

            // Create lowercase version for comparison
            var lower_buf: [128]u8 = undefined;
            if (short_name.len <= lower_buf.len) {
                for (short_name, 0..) |c, i| {
                    lower_buf[i] = std.ascii.toLower(c);
                }
                const lower_name = lower_buf[0..short_name.len];

                if (std.mem.eql(u8, sym, lower_name)) {
                    positional_start = 1;
                }
            }
        }
    }

    // Process positional fields based on order
    var positional_idx: usize = positional_start;
    inline for (fields, 0..) |field, field_idx| {
        const field_metadata = comptime getSexpMetadata(T, field.name);
        if (field_metadata.positional) {
            // For positional fields, we need to find the next non-list item
            while (positional_idx < items.len and ast.isList(items[positional_idx])) {
                positional_idx += 1;
            }

            if (positional_idx < items.len) {
                // Check if this field has a default value (either optional or has default_value_ptr)
                const has_default = comptime isOptional(field.type) or field.default_value_ptr != null;

                // For positional fields with defaults, check if the current item matches the expected type
                // This handles cases like PadDrill where shape has a default and might be skipped
                if (has_default) {
                    const actual_type = if (comptime isOptional(field.type))
                        @typeInfo(field.type).optional.child
                    else
                        field.type;
                    const type_info = @typeInfo(actual_type);

                    // For enum fields with defaults, check if current item is a matching symbol
                    if (type_info == .@"enum") {
                        if (ast.getSymbol(items[positional_idx])) |sym| {
                            // Check if this symbol is a valid enum value
                            var is_valid_enum = false;
                            inline for (std.meta.fields(actual_type)) |enum_field| {
                                // Check both the field name and any custom sexp_name
                                if (std.mem.eql(u8, sym, enum_field.name)) {
                                    is_valid_enum = true;
                                    break;
                                }
                                // Also check if enum has custom sexp_name metadata
                                if (@hasDecl(actual_type, "fields_meta")) {
                                    if (@hasField(@TypeOf(actual_type.fields_meta), enum_field.name)) {
                                        const enum_meta = @field(actual_type.fields_meta, enum_field.name);
                                        if (@hasField(@TypeOf(enum_meta), "sexp_name")) {
                                            const sexp_name = enum_meta.sexp_name;
                                            if (@typeInfo(@TypeOf(sexp_name)) == .optional) {
                                                if (sexp_name) |name| {
                                                    if (std.mem.eql(u8, sym, name)) {
                                                        is_valid_enum = true;
                                                        break;
                                                    }
                                                }
                                            } else {
                                                if (std.mem.eql(u8, sym, sexp_name)) {
                                                    is_valid_enum = true;
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            if (is_valid_enum) {
                                // This is a valid enum value, decode it
                                setErrorContext(.{
                                    .path = @typeName(T),
                                    .field_name = field.name,
                                    .sexp_preview = null,
                                }, items[positional_idx]);
                                @field(result, field.name) = try decodeWithMetadata(field.type, allocator, items[positional_idx], field_metadata);
                                fields_set.set(field_idx);
                                positional_idx += 1;
                            } else {
                                // Not a valid enum value, skip this field (use default/null)
                                if (comptime isOptional(field.type)) {
                                    @field(result, field.name) = null;
                                }
                                // For non-optional with default, the default was already set by zeroInit
                                fields_set.set(field_idx);
                                // Don't advance positional_idx - let next field try this item
                            }
                        } else {
                            // Not a symbol, skip this enum field (use default/null)
                            if (comptime isOptional(field.type)) {
                                @field(result, field.name) = null;
                            }
                            // For non-optional with default, the default was already set by zeroInit
                            fields_set.set(field_idx);
                            // Don't advance positional_idx - let next field try this item
                        }
                    } else {
                        // For other types with defaults, try to decode and handle errors
                        // Save the current error context in case decode fails
                        const saved_ctx = getErrorContext();
                        clearErrorContext();

                        // Try to decode this field
                        if (decodeWithMetadata(field.type, allocator, items[positional_idx], field_metadata)) |value| {
                            @field(result, field.name) = value;
                            fields_set.set(field_idx);
                            positional_idx += 1;
                        } else |_| {
                            // Decode failed, this item doesn't match this field type
                            // Restore context and skip this field
                            current_error_context = saved_ctx;
                            if (comptime isOptional(field.type)) {
                                @field(result, field.name) = null;
                            }
                            // For non-optional with default, the default was already set by zeroInit
                            fields_set.set(field_idx);
                            // Don't advance positional_idx - let next field try this item
                        }
                    }
                } else {
                    // Required positional field - decode normally
                    setErrorContext(.{
                        .path = @typeName(T),
                        .field_name = field.name,
                        .sexp_preview = null,
                    }, items[positional_idx]);
                    @field(result, field.name) = try decodeWithMetadata(field.type, allocator, items[positional_idx], field_metadata);
                    fields_set.set(field_idx);
                    positional_idx += 1;
                }
            } else if (comptime isOptional(field.type)) {
                // No more items, set optional field to null
                @field(result, field.name) = null;
                fields_set.set(field_idx);
            }
        }
    }

    // Process key-value pairs and standalone boolean fields
    var i: usize = 0;
    while (i < items.len) : (i += 1) {
        // First check if this is a standalone symbol (potential boolean field)
        if (ast.getSymbol(items[i])) |sym| {
            // Check if this matches a boolean field
            inline for (fields, 0..) |field, field_idx| {
                // Only process boolean fields that haven't been set
                if (!fields_set.isSet(field_idx) and @typeInfo(field.type) == .bool) {
                    const field_metadata = comptime getSexpMetadata(T, field.name);
                    const field_name = field_metadata.sexp_name orelse field.name;
                    if (std.mem.eql(u8, sym, field_name)) {
                        // Found a matching boolean field - set it to true
                        @field(result, field.name) = true;
                        fields_set.set(field_idx);
                        break;
                    }
                }
                // Also handle optional boolean fields
                if (!fields_set.isSet(field_idx) and comptime isOptional(field.type)) {
                    const child = @typeInfo(field.type).optional.child;
                    if (@typeInfo(child) == .bool) {
                        const field_metadata = comptime getSexpMetadata(T, field.name);
                        const field_name = field_metadata.sexp_name orelse field.name;
                        if (std.mem.eql(u8, sym, field_name)) {
                            // Found a matching optional boolean field - set it to true
                            @field(result, field.name) = true;
                            fields_set.set(field_idx);
                            break;
                        }
                    }
                }
            }
        }

        if (ast.isList(items[i])) {
            const kv_items = ast.getList(items[i]).?;
            const key = ast.getSymbol(kv_items[0]) orelse continue;

            // Find matching field
            inline for (fields, 0..) |field, field_idx| {
                const field_metadata = comptime getSexpMetadata(T, field.name);
                const field_name = field_metadata.sexp_name orelse field.name;

                if (std.mem.eql(u8, key, field_name)) {
                    if (field_metadata.multidict) {
                        // Handle multidict fields
                        if (comptime isSlice(field.type, false)) {
                            if (!fields_set.isSet(field_idx)) {
                                const ChildType = std.meta.Child(field.type);
                                var values = std.ArrayList(ChildType).initCapacity(allocator, items.len + 8) catch return error.OutOfMemory;
                                var scan_idx: usize = i;
                                while (scan_idx < items.len) : (scan_idx += 1) {
                                    if (ast.isList(items[scan_idx])) {
                                        const scan_kv = ast.getList(items[scan_idx]).?;
                                        if (scan_kv.len >= 2) {
                                            const scan_key = ast.getSymbol(scan_kv[0]) orelse continue;
                                            if (std.mem.eql(u8, field_name, scan_key)) {
                                                setErrorContext(.{ .path = @typeName(T), .field_name = field.name, .sexp_preview = null }, items[scan_idx]);
                                                const scan_struct_sexp = SExp{ .value = .{ .list = scan_kv[1..] }, .location = null };
                                                const scan_val = try decodeWithMetadata(ChildType, allocator, scan_struct_sexp, field_metadata);
                                                try values.append(scan_val);
                                            }
                                        }
                                    }
                                }
                                @field(result, field.name) = try values.toOwnedSlice();
                                fields_set.set(field_idx);
                            }
                        } else if (comptime isArrayList(field.type)) {
                            if (!fields_set.isSet(field_idx)) {
                                const ChildType = std.meta.Child(std.meta.FieldType(field.type, .items));
                                var values = std.ArrayList(ChildType).initCapacity(allocator, items.len + 8) catch return error.OutOfMemory;
                                var scan_idx: usize = i;
                                while (scan_idx < items.len) : (scan_idx += 1) {
                                    if (ast.isList(items[scan_idx])) {
                                        const scan_kv = ast.getList(items[scan_idx]).?;
                                        if (scan_kv.len >= 2) {
                                            const scan_key = ast.getSymbol(scan_kv[0]) orelse continue;
                                            if (std.mem.eql(u8, field_name, scan_key)) {
                                                setErrorContext(.{ .path = @typeName(T), .field_name = field.name, .sexp_preview = null }, items[scan_idx]);
                                                const scan_struct_sexp = SExp{ .value = .{ .list = scan_kv[1..] }, .location = null };
                                                const scan_val = try decodeWithMetadata(ChildType, allocator, scan_struct_sexp, field_metadata);
                                                try values.append(scan_val);
                                            }
                                        }
                                    }
                                }
                                @field(result, field.name) = values;
                                fields_set.set(field_idx);
                            }
                        } else if (comptime isLinkedList(field.type)) {
                            if (!fields_set.isSet(field_idx)) {
                                const NodeType = field.type.Node;
                                const ChildType = std.meta.FieldType(NodeType, .data);
                                var ll = field.type{ .first = null, .last = null };
                                var scan_idx: usize = i;
                                while (scan_idx < items.len) : (scan_idx += 1) {
                                    if (ast.isList(items[scan_idx])) {
                                        const scan_kv = ast.getList(items[scan_idx]).?;
                                        if (scan_kv.len >= 2) {
                                            const scan_key = ast.getSymbol(scan_kv[0]) orelse continue;
                                            if (std.mem.eql(u8, field_name, scan_key)) {
                                                setErrorContext(.{ .path = @typeName(T), .field_name = field.name, .sexp_preview = null }, items[scan_idx]);
                                                const scan_struct_sexp = SExp{ .value = .{ .list = scan_kv[1..] }, .location = null };
                                                const val = try decodeWithMetadata(ChildType, allocator, scan_struct_sexp, field_metadata);
                                                const node = try allocator.create(NodeType);
                                                node.* = NodeType{ .data = val, .prev = null, .next = null };
                                                if (ll.last) |last| { last.next = node; node.prev = last; } else ll.first = node;
                                                ll.last = node;
                                            }
                                        }
                                    }
                                }
                                @field(result, field.name) = ll;
                                fields_set.set(field_idx);
                            }
                        }
                    } else {
                        // Single value (non-multidict)
                        if (!fields_set.isSet(field_idx)) {
                            setErrorContext(.{ .path = @typeName(T), .field_name = field.name, .sexp_preview = null }, items[i]);
                            @field(result, field.name) = if (@typeInfo(field.type) == .@"struct" or (@typeInfo(field.type) == .optional and @typeInfo(@typeInfo(field.type).optional.child) == .@"struct"))
                                try decodeWithMetadata(field.type, allocator, SExp{ .value = .{ .list = kv_items[1..] }, .location = null }, field_metadata)
                            else if (kv_items.len == 2 and !isSlice(field.type, true))
                                try decodeWithMetadata(field.type, allocator, kv_items[1], field_metadata)
                            else
                                try decodeWithMetadata(field.type, allocator, SExp{ .value = .{ .list = kv_items[1..] }, .location = null }, field_metadata);
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
            const field_metadata = comptime getSexpMetadata(T, field.name);
            const field_name = field_metadata.sexp_name orelse field.name;

            // Before giving up, check if there's a single nested structure that matches this field
            // This handles cases like (effects (font ...)) where font is the only content
            var found_nested = false;

            for (items) |item| {
                if (ast.isList(item)) {
                    const nested_items = ast.getList(item).?;
                    if (nested_items.len > 0) {
                        if (ast.getSymbol(nested_items[0])) |sym| {
                            if (std.mem.eql(u8, sym, field_name)) {
                                // Check if this is just (field_name) with no value
                                if (nested_items.len == 1 and field.default_value_ptr != null) {
                                    // Use default value
                                    fields_set.set(field_idx);
                                    found_nested = true;
                                    break;
                                } else {
                                    // Found a nested structure that matches this field
                                    setErrorContext(.{
                                        .path = @typeName(T),
                                        .field_name = field.name,
                                        .sexp_preview = null,
                                    }, item);
                                    // Parse the entire nested structure as the field value
                                    @field(result, field.name) = try decodeWithMetadata(field.type, allocator, item, field_metadata);
                                    fields_set.set(field_idx);
                                    found_nested = true;
                                    break;
                                }
                            }
                        }
                    }
                }
            }

            // Also check if we have a symbol followed by other items that form the value
            // This handles cases like: font (size ...) (thickness ...)
            if (!found_nested) {
                for (items, 0..) |item, idx| {
                    if (ast.getSymbol(item)) |sym| {
                        if (std.mem.eql(u8, sym, field_name)) {
                            if (idx + 1 < items.len) {
                                // Check if next items could be values (not other field names)
                                var looks_like_value = true;
                                if (ast.getSymbol(items[idx + 1])) |next_sym| {
                                    // Check if next symbol is another field name
                                    inline for (fields) |check_field| {
                                        const check_meta = comptime getSexpMetadata(T, check_field.name);
                                        const check_name = check_meta.sexp_name orelse check_field.name;
                                        if (std.mem.eql(u8, next_sym, check_name)) {
                                            looks_like_value = false;
                                            break;
                                        }
                                    }
                                }

                                if (looks_like_value and field.default_value_ptr == null) {
                                    // Found the field name as a symbol with values following
                                    const value_items = items[idx + 1 ..];
                                    const value_sexp = if (value_items.len == 1)
                                        // Single item: pass directly
                                        value_items[0]
                                    else
                                        // Multiple items: wrap in a list
                                        SExp{ .value = .{ .list = value_items }, .location = null };

                                    setErrorContext(.{
                                        .path = @typeName(T),
                                        .field_name = field.name,
                                        .sexp_preview = null,
                                    }, value_sexp);
                                    @field(result, field.name) = try decodeWithMetadata(field.type, allocator, value_sexp, field_metadata);
                                    fields_set.set(field_idx);
                                    found_nested = true;
                                    break;
                                } else if (field.default_value_ptr != null) {
                                    // Standalone field name with default - use default
                                    fields_set.set(field_idx);
                                    found_nested = true;
                                    break;
                                }
                            } else if (field.default_value_ptr != null) {
                                // Standalone field name at end with default - use default
                                fields_set.set(field_idx);
                                found_nested = true;
                                break;
                            }
                        }
                    }
                }
            }

            if (!found_nested) {
                // Handle different field types
                if (comptime isOptional(field.type)) {
                    @field(result, field.name) = null;
                } else if (comptime isSlice(field.type, false)) {
                    const field_metadata_check = comptime getSexpMetadata(T, field.name);
                    if (field_metadata_check.multidict) {
                        // Empty slice for multidict
                        @field(result, field.name) = try allocator.alloc(std.meta.Child(field.type), 0);
                    } else {
                        // Use explicit default if available
                        if (field.default_value_ptr) |default_ptr| {
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
                } else {
                    // Use explicit default if available
                    if (field.default_value_ptr) |default_ptr| {
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
    }

    return result;
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

fn decodeArrayList(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, metadata: SexpField) DecodeError!T {
    const child_type = std.meta.Child(std.meta.FieldType(T, .items));
    const items = ast.getList(sexp).?;
    // Pre-reserve headroom to keep existing element addresses stable when appending
    // Important: tests expect appending not to invalidate references
    const reserve: usize = if (items.len < 8) items.len + 8 else items.len + items.len / 2;
    var result = std.ArrayList(child_type).initCapacity(allocator, reserve) catch return error.OutOfMemory;
    for (items) |item| {
        try result.append(try decodeWithMetadata(child_type, allocator, item, metadata));
    }
    return result;
}

fn decodeLinkedList(comptime T: type, allocator: std.mem.Allocator, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata;
    const NodeType = T.Node;
    const child_type = std.meta.FieldType(NodeType, .data);
    const items = ast.getList(sexp).?;
    var ll = T{ .first = null, .last = null };
    for (items) |item| {
        const val = try decodeWithMetadata(child_type, allocator, item, .{});
        const node = try allocator.create(NodeType);
        node.* = NodeType{ .data = val, .prev = null, .next = null };
        if (ll.last) |last| { last.next = node; node.prev = last; } else ll.first = node;
        ll.last = node;
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

fn decodeFloat(comptime T: type, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata; // metadata not used for basic types
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
        .list => |l| {
            setErrorContext(.{
                .path = if (ctx) |c| c.path else @typeName(T),
                .field_name = if (ctx) |c| c.field_name else null,
                .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "got list '{s}' but expected number", .{l}) catch "list instead of number",
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

fn decodeBool(sexp: SExp, metadata: SexpField) DecodeError!bool {
    if (metadata.boolean_encoding == .parantheses_symbol) {
        if (ast.getList(sexp)) |list| {
            if (list.len == 0) return true;
        }
        const ctx = getErrorContext();
        setErrorContext(.{
            .path = if (ctx) |c| c.path else "bool",
            .field_name = if (ctx) |c| c.field_name else null,
            .sexp_preview = "expected list for parantheses boolean",
        }, sexp);
        return error.UnexpectedType;
    }
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

fn decodeEnum(comptime T: type, sexp: SExp, metadata: SexpField) DecodeError!T {
    _ = metadata; // metadata not used for basic enums (could be used for custom sexp_name in future)
    // Try to get the enum value as either a symbol or a string
    const enum_str = switch (sexp.value) {
        .symbol => |s| s,
        .string => |s| s,
        else => {
            // Get current context to preserve field name
            const ctx = getErrorContext();
            setErrorContext(.{
                .path = if (ctx) |c| c.path else @typeName(T),
                .field_name = if (ctx) |c| c.field_name else null,
                .sexp_preview = "expected symbol or string for enum",
            }, sexp);
            return error.UnexpectedType;
        },
    };

    inline for (std.meta.fields(T)) |field| {
        if (std.mem.eql(u8, enum_str, field.name)) {
            return @field(T, field.name);
        }
    }

    // Get current context to preserve field name
    const ctx = getErrorContext();
    setErrorContext(.{
        .path = if (ctx) |c| c.path else @typeName(T),
        .field_name = if (ctx) |c| c.field_name else null,
        .sexp_preview = std.fmt.allocPrint(std.heap.page_allocator, "invalid enum value '{s}' for type {s}", .{ enum_str, @typeName(T) }) catch "invalid enum value",
    }, sexp);
    return error.InvalidValue;
}

// Main encode function with metadata
pub fn encode(allocator: std.mem.Allocator, value: anytype, metadata: SexpField, name: []const u8) EncodeError!SExp {
    const T = @TypeOf(value);
    const type_info = @typeInfo(T);

    // Special handling for enums with symbol flag
    if (type_info == .@"enum") {
        inline for (std.meta.fields(T)) |field| {
            if (@intFromEnum(value) == field.value) {
                if (metadata.symbol orelse true) {
                    return SExp{ .value = .{ .symbol = field.name }, .location = null };
                } else {
                    return SExp{ .value = .{ .string = field.name }, .location = null };
                }
            }
        }
        unreachable;
    }

    // Special handling for strings that should be encoded as symbols
    if (type_info == .pointer) {
        if (type_info.pointer.size == .slice and type_info.pointer.child == u8 and metadata.symbol orelse false) {
            // Encode as symbol instead of string
            return SExp{ .value = .{ .symbol = value }, .location = null };
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
                    items[i] = SExp{ .value = .{ .symbol = str_val }, .location = null };
                }
                return SExp{ .value = .{ .list = items }, .location = null };
            }
        }
    }

    switch (type_info) {
        .@"struct" => if (comptime isArrayList(T)) {
            return try encodeArrayList(allocator, value, metadata, name);
        } else if (comptime isLinkedList(T)) {
            return try encodeLinkedList(allocator, value, metadata, name);
        } else {
            return try encodeStruct(allocator, value, metadata);
        },
        .optional => {
            if (value) |v| return try encode(allocator, v, metadata, name);
            return SExp{ .value = .{ .list = try allocator.alloc(SExp, 0) }, .location = null };
        },
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child == u8) {
                // Handle strings
                return SExp{ .value = .{ .string = value }, .location = null };
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
            return SExp{ .value = .{ .number = duped }, .location = null };
        },
        .float => {
            var buf: [32]u8 = undefined;
            // round float to 6 decimal places
            const rounded = std.math.round(value * 10e6) / 10e6;
            const fucked = std.mem.eql(u8, name, "dashed_line_dash_ratio") or std.mem.eql(u8, name, "dashed_line_gap_ratio") or std.mem.eql(u8, name, "hpglpendiameter");
            const str = if (fucked)
                std.fmt.bufPrint(&buf, "{d:.6}", .{rounded}) catch return error.OutOfMemory
            else
                std.fmt.bufPrint(&buf, "{d}", .{rounded}) catch return error.OutOfMemory;
            const duped = try allocator.alloc(u8, str.len);
            @memcpy(duped, str);
            return SExp{ .value = .{ .number = duped }, .location = null };
        },
        .bool => {
            if (metadata.boolean_encoding == .parantheses_symbol) {
                if (!value) {
                    return SExp{ .value = .{ .list = try allocator.alloc(SExp, 0) }, .location = null };
                }
                const field_name = metadata.sexp_name orelse name;
                var items = try allocator.alloc(SExp, 1);
                items[0] = SExp{ .value = .{ .symbol = field_name }, .location = null };
                return SExp{ .value = .{ .list = items }, .location = null };
            }
            return SExp{ .value = .{ .symbol = if (value) "yes" else "no" }, .location = null };
        },
        .@"enum" => {
            inline for (std.meta.fields(T)) |field| {
                if (@intFromEnum(value) == field.value) {
                    return SExp{ .value = .{ .symbol = field.name }, .location = null };
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

fn encodeStruct(allocator: std.mem.Allocator, value: anytype, metadata: SexpField) EncodeError!SExp {
    _ = metadata;
    const T = @TypeOf(value);
    var items = std.ArrayList(SExp).init(allocator);
    defer items.deinit();

    const fields = std.meta.fields(T);
    const sorted_indices = comptime sortFieldIndices(T);

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
            } else if (comptime isArrayList(@TypeOf(fv))) {
                for (fv.items) |elem| try appendKeyValue(allocator, &items, fname, try encode(allocator, elem, fm, f.name));
            } else if (comptime isLinkedList(@TypeOf(fv))) {
                var n = fv.first; while (n) |node| : (n = node.next) {
                    try appendKeyValue(allocator, &items, fname, try encode(allocator, node.data, fm, f.name));
                }
            }
            continue;
        }

        if (comptime isOptional(@TypeOf(fv))) {
            if (fv) |vv| try appendKeyValue(allocator, &items, fname, try encode(allocator, vv, fm, f.name));
            continue;
        }

        try appendKeyValue(allocator, &items, fname, try encode(allocator, fv, fm, f.name));
    }

    const out = try items.toOwnedSlice();
    return SExp{ .value = .{ .list = out }, .location = null };
}

fn appendKeyValue(allocator: std.mem.Allocator, items: *std.ArrayList(SExp), key: []const u8, encoded: SExp) EncodeError!void {
    if (ast.getList(encoded)) |lst| {
        if (lst.len == 0) return; // omit empty list fields entirely
        var kv = try allocator.alloc(SExp, lst.len + 1);
        kv[0] = SExp{ .value = .{ .symbol = key }, .location = null };
        for (lst, 0..) |it, i| kv[i + 1] = it;
        try items.append(SExp{ .value = .{ .list = kv }, .location = null });
    } else {
        var kv2 = try allocator.alloc(SExp, 2);
        kv2[0] = SExp{ .value = .{ .symbol = key }, .location = null };
        kv2[1] = encoded;
        try items.append(SExp{ .value = .{ .list = kv2 }, .location = null });
    }
}

fn encodeSlice(allocator: std.mem.Allocator, value: anytype, metadata: SexpField, name: []const u8) EncodeError!SExp {
    // TODO: remove (only used for non-str slices)
    var items = try allocator.alloc(SExp, value.len);
    for (value, 0..) |item, i| {
        items[i] = try encode(allocator, item, metadata, name);
    }
    return SExp{ .value = .{ .list = items }, .location = null };
}

fn encodeArrayList(allocator: std.mem.Allocator, value: anytype, metadata: SexpField, name: []const u8) EncodeError!SExp {
    var items = try allocator.alloc(SExp, value.items.len);
    for (value.items, 0..) |item, i| {
        items[i] = try encode(allocator, item, metadata, name);
    }
    return SExp{ .value = .{ .list = items }, .location = null };
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
    return SExp{ .value = .{ .list = items }, .location = null };
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

// Load a struct from an S-expression string with a wrapping symbol
pub fn loads(comptime T: type, allocator: std.mem.Allocator, in: input, expected_symbol: []const u8) !T {
    // Parse S-expression from input
    var sexp: SExp = undefined;
    var should_deinit = false;

    switch (in) {
        .path => {
            const file_content = try std.fs.cwd().readFileAlloc(allocator, in.path, 200 * 1024 * 1024);
            const tokens = try tokenizer.tokenize(allocator, file_content);
            defer allocator.free(tokens);
            sexp = try ast.parse(allocator, tokens);
            // Don't free file_content here - it's referenced by sexp!
            // The caller is responsible for using an arena allocator
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
    return try decodeWithMetadata(T, allocator, table_sexp, SexpField{});
}

// Dump a struct to an S-expression string with a wrapping symbol
pub fn dumps(data: anytype, allocator: std.mem.Allocator, symbol_name: []const u8, out: output) !void {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    // Encode the data
    const encoded = try encode(arena.allocator(), data, SexpField{}, symbol_name);

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
    switch (out) {
        .sexp => |sexp| {
            sexp.* = wrapped;
        },
        .string, .path => {
            const out_str = try wrapped.pretty(allocator);
            switch (out) {
                .string => |s| {
                    s.* = out_str;
                },
                .path => |p| {
                    defer allocator.free(out_str);
                    const file = try std.fs.cwd().createFile(p, .{ .truncate = true });
                    defer file.close();

                    const writer = file.writer();
                    try writer.writeAll(out_str);
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

fn isSimpleType(comptime T: type) bool {
    return switch (@typeInfo(T)) {
        .int, .float, .bool, .@"enum" => true,
        // Don't consider strings as simple - they need to be freed
        else => false,
    };
}
