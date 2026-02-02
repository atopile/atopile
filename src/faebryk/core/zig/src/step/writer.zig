const std = @import("std");
const ast = @import("ast.zig");

const Parameter = ast.Parameter;
const TypedParameter = ast.TypedParameter;
const Entity = ast.Entity;
const Header = ast.Header;
const StepFile = ast.StepFile;

pub const WriteError = error{
    OutOfMemory,
};

/// Write a STEP file to a string
pub fn write(allocator: std.mem.Allocator, step_file: *const StepFile) WriteError![]u8 {
    var buffer = std.ArrayList(u8).init(allocator);
    errdefer buffer.deinit();

    const writer = buffer.writer();

    // Write header
    try writer.writeAll("ISO-10303-21;\n");
    try writer.writeAll("HEADER;\n");

    // FILE_DESCRIPTION
    try writer.writeAll("FILE_DESCRIPTION (( ");
    for (step_file.header.file_description.description, 0..) |desc, i| {
        if (i > 0) try writer.writeAll(", ");
        try writer.print("'{s}'", .{desc});
    }
    if (step_file.header.file_description.description.len == 0) {
        try writer.writeAll("''");
    }
    try writer.writeAll(" ),\n    '1' );\n");

    // FILE_NAME
    try writer.print("FILE_NAME ('{s}',\n", .{step_file.header.file_name.name});
    try writer.print("    '{s}',\n", .{step_file.header.file_name.time_stamp});
    try writer.writeAll("    ( '' ),\n");
    try writer.writeAll("    ( '' ),\n");
    try writer.print("    '{s}',\n", .{step_file.header.file_name.preprocessor_version});
    try writer.print("    '{s}',\n", .{step_file.header.file_name.originating_system});
    try writer.print("    '{s}' );\n", .{step_file.header.file_name.authorization});

    // FILE_SCHEMA
    try writer.writeAll("FILE_SCHEMA (( ");
    for (step_file.header.file_schema.schemas, 0..) |schema, i| {
        if (i > 0) try writer.writeAll(", ");
        try writer.print("'{s}'", .{schema});
    }
    if (step_file.header.file_schema.schemas.len == 0) {
        try writer.writeAll("'AUTOMOTIVE_DESIGN'");
    }
    try writer.writeAll(" ));\n");

    try writer.writeAll("ENDSEC;\n\n");

    // DATA section
    try writer.writeAll("DATA;\n");

    // Write entities in original order
    for (step_file.entity_order.items) |id| {
        if (step_file.entities.get(id)) |entity| {
            try writeEntity(writer, &entity);
            try writer.writeAll("\n");
        }
    }

    try writer.writeAll("ENDSEC;\n");
    try writer.writeAll("END-ISO-10303-21;\n");

    return buffer.toOwnedSlice();
}

fn writeEntity(writer: anytype, entity: *const Entity) @TypeOf(writer).Error!void {
    try writer.print("#{d} = ", .{entity.id});

    if (entity.complex_types) |types| {
        try writer.writeAll("( ");
        for (types, 0..) |typed, i| {
            if (i > 0) try writer.writeAll(" ");
            try writer.print("{s} ( ", .{typed.type_name});
            try writeParameterList(writer, typed.parameters);
            try writer.writeAll(" )");
        }
        try writer.writeAll(" )");
    } else {
        try writer.print("{s} ( ", .{entity.type_name});
        try writeParameterList(writer, entity.parameters);
        try writer.writeAll(" )");
    }

    try writer.writeAll(" ;");
}

fn writeParameterList(writer: anytype, params: []const Parameter) @TypeOf(writer).Error!void {
    for (params, 0..) |param, i| {
        if (i > 0) try writer.writeAll(", ");
        try writeParameter(writer, &param);
    }
}

fn writeParameter(writer: anytype, param: *const Parameter) @TypeOf(writer).Error!void {
    switch (param.*) {
        .entity_ref => |id| try writer.print("#{d}", .{id}),
        .integer => |i| try writer.print("{d}", .{i}),
        .real => |r| try writer.writeAll(r),
        .string => |s| try writer.print("'{s}'", .{s}),
        .enumeration => |e| try writer.print(".{s}.", .{e}),
        .list => |l| {
            try writer.writeAll("( ");
            for (l, 0..) |item, i| {
                if (i > 0) try writer.writeAll(", ");
                try writeParameter(writer, &item);
            }
            try writer.writeAll(" )");
        },
        .typed => |t| {
            try writer.print("{s} ( ", .{t.type_name});
            try writeParameterList(writer, t.parameters);
            try writer.writeAll(" )");
        },
        .undefined => try writer.writeAll("*"),
        .omitted => try writer.writeAll("$"),
    }
}

/// Serialize a StepFile to string (alias for write)
pub fn dumps(allocator: std.mem.Allocator, step_file: *const StepFile) WriteError![]u8 {
    return write(allocator, step_file);
}
