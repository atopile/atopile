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

// Error types
pub const DecodeError = error{
    UnexpectedType,
    MissingField,
    DuplicateKey,
    InvalidValue,
    AssertionFailed,
    OutOfMemory,
};

pub const EncodeError = error{
    OutOfMemory,
    InvalidType,
};

// Helper to get sexp metadata for a field
fn getSexpMetadata(comptime T: type, comptime field_name: []const u8) SexpField {
    if (@hasDecl(T, "sexp_metadata")) {
        if (@hasField(@TypeOf(T.sexp_metadata), field_name)) {
            const meta = @field(T.sexp_metadata, field_name);
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
            return error.InvalidType;
        },
        .int => return try decodeInt(T, sexp),
        .float => return try decodeFloat(T, sexp),
        .bool => return try decodeBool(sexp),
        .@"enum" => return try decodeEnum(T, sexp),
        else => return error.InvalidType,
    }
}

fn decodeStruct(comptime T: type, allocator: std.mem.Allocator, sexp: SExp) DecodeError!T {
    const fields = std.meta.fields(T);
    var result: T = std.mem.zeroInit(T, .{});

    const items = ast.getList(sexp) orelse return error.UnexpectedType;

    // Track which fields have been set
    var fields_set = std.StaticBitSet(fields.len).initEmpty();

    // Process positional fields first
    var pos_index: usize = 0;
    inline for (fields, 0..) |field, field_idx| {
        const metadata = comptime getSexpMetadata(T, field.name);
        if (metadata.positional) {
            if (pos_index < items.len) {
                @field(result, field.name) = try decode(field.type, allocator, items[pos_index]);
                fields_set.set(field_idx);
                pos_index += 1;
            }
        }
    }

    // Process key-value pairs
    var i = pos_index;
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
                                                // For multidict entries, decode the rest as struct fields
                                                const scan_struct_sexp = SExp{ .list = scan_kv[1..] };
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
                            @field(result, field.name) = if (kv_items.len == 2)
                                try decode(field.type, allocator, kv_items[1])
                            else
                                try decode(field.type, allocator, SExp{ .list = kv_items[1..] });
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
        switch (sexp) {
            .string => |str| {
                const duped = try allocator.alloc(u8, str.len);
                @memcpy(duped, str);
                return duped;
            },
            .symbol => |sym| {
                const duped = try allocator.alloc(u8, sym.len);
                @memcpy(duped, sym);
                return duped;
            },
            .number => |num| {
                const duped = try allocator.alloc(u8, num.len);
                @memcpy(duped, num);
                return duped;
            },
            else => {},
        }
    }

    const items = ast.getList(sexp) orelse return error.UnexpectedType;

    var result = try allocator.alloc(child_type, items.len);
    for (items, 0..) |item, idx| {
        result[idx] = try decode(child_type, allocator, item);
    }

    return result;
}

fn decodeInt(comptime T: type, sexp: SExp) DecodeError!T {
    const str = switch (sexp) {
        .number => |n| n,
        .symbol => |s| s,
        else => return error.UnexpectedType,
    };
    return std.fmt.parseInt(T, str, 10) catch return error.InvalidValue;
}

fn decodeFloat(comptime T: type, sexp: SExp) DecodeError!T {
    const str = switch (sexp) {
        .number => |n| n,
        .symbol => |s| s,
        else => return error.UnexpectedType,
    };
    return std.fmt.parseFloat(T, str) catch return error.InvalidValue;
}

fn decodeBool(sexp: SExp) DecodeError!bool {
    const sym = ast.getSymbol(sexp) orelse return error.UnexpectedType;
    if (std.mem.eql(u8, sym, "yes")) return true;
    if (std.mem.eql(u8, sym, "no")) return false;
    if (std.mem.eql(u8, sym, "true")) return true;
    if (std.mem.eql(u8, sym, "false")) return false;
    return error.InvalidValue;
}

fn decodeEnum(comptime T: type, sexp: SExp) DecodeError!T {
    const sym = ast.getSymbol(sexp) orelse return error.UnexpectedType;
    inline for (std.meta.fields(T)) |field| {
        if (std.mem.eql(u8, sym, field.name)) {
            return @field(T, field.name);
        }
    }
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
            return SExp{ .list = try allocator.alloc(SExp, 0) };
        },
        .pointer => |ptr| {
            if (ptr.size == .slice and ptr.child == u8) {
                // Handle strings
                return SExp{ .string = value };
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
            return SExp{ .number = duped };
        },
        .float => {
            var buf: [32]u8 = undefined;
            const str = std.fmt.bufPrint(&buf, "{d}", .{value}) catch return error.OutOfMemory;
            const duped = try allocator.alloc(u8, str.len);
            @memcpy(duped, str);
            return SExp{ .number = duped };
        },
        .bool => return SExp{ .symbol = if (value) "yes" else "no" },
        .@"enum" => {
            inline for (std.meta.fields(T)) |field| {
                if (@intFromEnum(value) == field.value) {
                    return SExp{ .symbol = field.name };
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
                            kv_items[0] = SExp{ .symbol = field_name };
                            for (item_contents, 0..) |content, idx| {
                                kv_items[idx + 1] = content;
                            }
                            try items.append(SExp{ .list = kv_items });
                        } else {
                            // Not a list, encode normally
                            var kv_items = try allocator.alloc(SExp, 2);
                            kv_items[0] = SExp{ .symbol = field_name };
                            kv_items[1] = encoded_item;
                            try items.append(SExp{ .list = kv_items });
                        }
                    }
                }
            } else {
                // Handle optional values
                if (comptime isOptional(@TypeOf(field_value))) {
                    if (field_value) |val| {
                        var kv_items = try allocator.alloc(SExp, 2);
                        kv_items[0] = SExp{ .symbol = field_name };
                        kv_items[1] = try encode(allocator, val);
                        try items.append(SExp{ .list = kv_items });
                    }
                } else {
                    var kv_items = try allocator.alloc(SExp, 2);
                    kv_items[0] = SExp{ .symbol = field_name };
                    kv_items[1] = try encode(allocator, field_value);
                    try items.append(SExp{ .list = kv_items });
                }
            }
        }
    }

    return SExp{ .list = try items.toOwnedSlice() };
}

fn encodeSlice(allocator: std.mem.Allocator, value: anytype) EncodeError!SExp {
    var items = try allocator.alloc(SExp, value.len);
    for (value, 0..) |item, i| {
        items[i] = try encode(allocator, item);
    }
    return SExp{ .list = items };
}

// File I/O helpers
pub fn loads(comptime T: type, allocator: std.mem.Allocator, sexp: SExp) DecodeError!T {
    // For top-level files, decode directly
    return try decode(T, allocator, sexp);
}

pub fn dumps(allocator: std.mem.Allocator, value: anytype) EncodeError![]u8 {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    const sexp = try encode(arena.allocator(), value);

    var buffer = std.ArrayList(u8).init(allocator);
    const writer = buffer.writer();

    try sexp.str(writer);

    return try buffer.toOwnedSlice();
}

// Load a struct from an S-expression string
pub fn loadsString(comptime T: type, allocator: std.mem.Allocator, content: []const u8) !T {
    // Tokenize
    const tokens = try tokenizer.tokenize(allocator, content);
    defer allocator.free(tokens);

    // Parse to AST using arena allocator for performance
    var parse_arena = std.heap.ArenaAllocator.init(allocator);
    defer parse_arena.deinit();

    var sexp = try ast.parse(parse_arena.allocator(), tokens) orelse return error.EmptyFile;
    defer sexp.deinit(parse_arena.allocator());

    // Decode
    return try decode(T, allocator, sexp);
}

// Load a struct from an S-expression string with a wrapping symbol
pub fn loadsStringWithSymbol(comptime T: type, allocator: std.mem.Allocator, content: []const u8, expected_symbol: []const u8) !T {
    // Tokenize
    const tokens = try tokenizer.tokenize(allocator, content);
    defer allocator.free(tokens);

    // Parse to AST using arena allocator for performance
    var parse_arena = std.heap.ArenaAllocator.init(allocator);
    defer parse_arena.deinit();

    var sexp = try ast.parse(parse_arena.allocator(), tokens) orelse return error.EmptyFile;
    defer sexp.deinit(parse_arena.allocator());

    // The file structure is (symbol_name ...)
    const file_list = ast.getList(sexp) orelse return error.UnexpectedType;
    if (file_list.len < 1) return error.UnexpectedType;

    const symbol = ast.getSymbol(file_list[0]) orelse return error.UnexpectedType;
    if (!std.mem.eql(u8, symbol, expected_symbol)) return error.UnexpectedType;

    // Create a new list without the symbol for decoding
    const contents = file_list[1..];
    const table_sexp = ast.SExp{ .list = contents };

    // Decode
    return try decode(T, allocator, table_sexp);
}

// Dump a struct to an S-expression string with a wrapping symbol
pub fn dumpsStringWithSymbol(data: anytype, allocator: std.mem.Allocator, symbol_name: []const u8) ![]u8 {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    // Encode the data
    const encoded = try encode(arena.allocator(), data);

    // The encoded result is a list of key-value pairs
    // We need to prepend the symbol name
    const encoded_items = ast.getList(encoded).?;

    var items = try arena.allocator().alloc(ast.SExp, encoded_items.len + 1);
    items[0] = ast.SExp{ .symbol = symbol_name };

    // Copy the encoded items
    for (encoded_items, 0..) |item, i| {
        items[i + 1] = item;
    }

    const wrapped = ast.SExp{ .list = items };

    // Write to string
    var buffer = std.ArrayList(u8).init(allocator);
    const writer = buffer.writer();

    try wrapped.str(writer);

    return try buffer.toOwnedSlice();
}

// Write S-expression with symbol to file
pub fn writeFileWithSymbol(data: anytype, file_path: []const u8, symbol_name: []const u8, allocator: std.mem.Allocator) !void {
    const content = try dumpsStringWithSymbol(data, allocator, symbol_name);
    defer allocator.free(content);

    const file = try std.fs.cwd().createFile(file_path, .{});
    defer file.close();

    try file.writeAll(content);
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
        .pointer => |ptr| ptr.size == .slice and ptr.child == u8, // Consider strings as simple
        else => false,
    };
}
