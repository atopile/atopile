const std = @import("std");

pub fn shortTypeName(comptime T: type) [:0]const u8 {
    const full = @typeName(T);
    var last: usize = 0;
    for (full, 0..) |c, i| {
        if (c == '.') last = i + 1;
    }
    return full[last..];
}

const indent_step = 2;

fn isSimpleValueType(comptime T: type) bool {
    return switch (@typeInfo(T)) {
        .bool, .int, .float, .comptime_int, .comptime_float => true,
        .@"enum" => true,
        .optional => |opt| isSimpleValueType(opt.child),
        .pointer => |ptr| ptr.size == .slice and ptr.child == u8,
        else => false,
    };
}

pub fn printStruct(value: anytype, buf: []u8) ![:0]u8 {
    const T = @TypeOf(value);
    comptime if (@typeInfo(T) != .@"struct") @compileError("printStruct expects a struct");

    if (buf.len == 0) return error.BufferTooSmall;
    var stream = std.io.fixedBufferStream(buf[0 .. buf.len - 1]);
    {
        const writer = stream.writer();
        try printStructInline(writer, value, 0);
        try writer.writeByte('\n');
    }
    const written = stream.pos;
    buf[written] = 0;
    return buf[0..written :0];
}

fn printStructInline(writer: anytype, value: anytype, indent: usize) anyerror!void {
    const T = @TypeOf(value);
    const info = @typeInfo(T).@"struct";

    try writer.print("{s} {{\n", .{@typeName(T)});
    inline for (info.fields) |field| {
        const field_value = @field(value, field.name);
        try printField(writer, field.name, field_value, indent);
    }
    try writeIndent(writer, indent);
    try writer.writeAll("}");
}

fn isSimpleInline(value: anytype) bool {
    const T = @TypeOf(value);
    if (isAllocatorType(T)) return true;
    if (comptime isSimpleValueType(T)) return true;
    return switch (@typeInfo(T)) {
        .optional => value == null,
        else => false,
    };
}

fn printField(writer: anytype, comptime name: []const u8, value: anytype, parent_indent: usize) anyerror!void {
    const field_indent = parent_indent + indent_step;
    const simple_type = isSimpleInline(value);
    try writeIndent(writer, field_indent);
    try writer.print("{s}:", .{name});
    if (simple_type) {
        try writer.writeByte(' ');
        try printValue(writer, value, field_indent);
        try writer.writeByte('\n');
        return;
    }

    try writer.writeByte('\n');
    try writeIndent(writer, field_indent + indent_step);
    try printValue(writer, value, field_indent + indent_step);
    try writer.writeByte('\n');
}

fn printValue(writer: anytype, value: anytype, indent: usize) anyerror!void {
    const T = @TypeOf(value);

    if (isAllocatorType(T)) {
        try writer.writeAll("<allocator>");
        return;
    }

    if (comptime isArrayListType(T)) {
        try printArrayList(writer, value, indent);
        return;
    }

    if (comptime isHashMapType(T)) {
        try printHashMap(writer, value, indent);
        return;
    }

    switch (@typeInfo(T)) {
        .optional => {
            if (value) |some| {
                try printValue(writer, some, indent);
            } else {
                try writer.writeAll("null");
            }
        },
        .pointer => |ptr| {
            if (ptr.size == .slice) {
                if (ptr.child == u8) {
                    try printString(writer, value);
                } else {
                    try printSlice(writer, value, indent);
                }
            } else if (ptr.size == .one and comptime isArrayListType(ptr.child)) {
                try printArrayList(writer, value.*, indent);
            } else if (ptr.size == .one and comptime isHashMapType(ptr.child)) {
                try printHashMap(writer, value.*, indent);
            } else if (ptr.size == .one and @typeInfo(ptr.child) == .@"struct") {
                if (ptr.is_allowzero and value == null) {
                    try writer.writeAll("null");
                } else {
                    try printStructInline(writer, value.*, indent);
                }
            } else if (ptr.size == .one and ptr.child == u8 and ptr.is_const) {
                try printString(writer, std.mem.span(value));
            } else if (ptr.size == .one) {
                try writer.print("{any}", .{value});
            } else {
                try writer.print("{any}", .{value});
            }
        },
        .array => |arr| {
            if (arr.child == u8) {
                try printString(writer, &value);
            } else {
                try printSlice(writer, value[0..], indent);
            }
        },
        .vector => {
            try printSlice(writer, value[0..], indent);
        },
        .@"struct" => {
            try printStructInline(writer, value, indent);
        },
        .@"union", .@"enum", .error_union, .error_set, .float, .int, .bool, .comptime_float, .comptime_int => {
            try writer.print("{any}", .{value});
        },
        else => {
            try writer.print("{any}", .{value});
        },
    }
}

fn writeIndent(writer: anytype, indent: usize) anyerror!void {
    try writer.writeByteNTimes(' ', indent);
}

fn isAllocatorType(comptime T: type) bool {
    if (T == std.mem.Allocator) return true;
    return switch (@typeInfo(T)) {
        .pointer => |ptr| isAllocatorType(ptr.child),
        .optional => |opt| isAllocatorType(opt.child),
        else => false,
    };
}

fn isArrayListType(comptime T: type) bool {
    if (@typeInfo(T) != .@"struct") return false;
    return @hasField(T, "items") and (@hasField(T, "capacity") or @hasField(T, "list"));
}

fn isHashMapType(comptime T: type) bool {
    if (@typeInfo(T) != .@"struct") return false;
    return @hasField(T, "unmanaged") and @hasField(T, "allocator") and @hasDecl(T, "iterator");
}

fn printString(writer: anytype, slice: []const u8) anyerror!void {
    try writer.writeByte('"');
    try writer.print("{}", .{std.fmt.fmtSliceEscapeLower(slice)});
    try writer.writeByte('"');
}

fn printSlice(writer: anytype, slice: anytype, indent: usize) anyerror!void {
    try writer.writeAll("[");
    if (slice.len == 0) {
        try writer.writeAll("]");
        return;
    }
    try writer.writeByte('\n');
    for (slice, 0..) |item, index| {
        try writeIndent(writer, indent + indent_step);
        try printValue(writer, item, indent + indent_step);
        if (index + 1 < slice.len) {
            try writer.writeByte('\n');
        }
    }
    try writer.writeByte('\n');
    try writeIndent(writer, indent);
    try writer.writeAll("]");
}

fn printArrayList(writer: anytype, list_value: anytype, indent: usize) anyerror!void {
    const T = @TypeOf(list_value);
    switch (@typeInfo(T)) {
        .pointer => |ptr| {
            if (ptr.size == .one) {
                try printArrayList(writer, list_value.*, indent);
                return;
            }
        },
        else => {},
    }

    if (!comptime @hasField(T, "items")) {
        try writer.print("{any}", .{list_value});
        return;
    }

    const items = list_value.items;
    try writer.writeAll("[");
    if (items.len == 0) {
        try writer.writeAll("]");
        return;
    }
    try writer.writeByte('\n');
    for (items, 0..) |item, index| {
        try writeIndent(writer, indent + indent_step);
        try printValue(writer, item, indent + indent_step);
        if (index + 1 < items.len) {
            try writer.writeByte('\n');
        }
    }
    try writer.writeByte('\n');
    try writeIndent(writer, indent);
    try writer.writeAll("]");
}

fn printHashMap(writer: anytype, map_value: anytype, indent: usize) anyerror!void {
    const T = @TypeOf(map_value);
    switch (@typeInfo(T)) {
        .pointer => |ptr| {
            if (ptr.size == .one) {
                try printHashMap(writer, map_value.*, indent);
                return;
            }
        },
        else => {},
    }

    var map_copy = map_value;
    const map_ptr = &map_copy;

    try writer.print("{s} {{", .{@typeName(T)});
    var it = map_ptr.iterator();
    var first = true;
    while (it.next()) |entry| {
        if (first) {
            first = false;
            try writer.writeByte('\n');
        } else {
            try writer.writeByte('\n');
        }
        try writeIndent(writer, indent + indent_step);
        try printValue(writer, entry.key_ptr.*, indent + indent_step);
        try writer.writeAll(": ");
        try printValue(writer, entry.value_ptr.*, indent + indent_step);
    }
    if (!first) {
        try writer.writeByte('\n');
        try writeIndent(writer, indent);
    }
    try writer.writeAll("}");
}

pub fn terminateString(allocator: std.mem.Allocator, str: []const u8) ![:0]const u8 {
    var buf = try allocator.alloc(u8, str.len + 1);
    @memcpy(buf[0..str.len], str);
    buf[str.len] = 0;
    return @ptrCast(buf);
}
