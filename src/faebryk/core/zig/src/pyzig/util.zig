const std = @import("std");

pub fn printStruct(value: anytype, buf: []u8) ![:0]u8 {
    const T = @TypeOf(value);
    const info = @typeInfo(T);

    switch (info) {
        .@"struct" => |s| {
            var pos: usize = 0;

            // Write struct name and opening brace
            const header = try std.fmt.bufPrintZ(buf[pos..], "{s} {{\n", .{@typeName(T)});
            pos += header.len;

            // Write each field
            inline for (s.fields) |field| {
                const field_value = @field(value, field.name);
                const field_type = @TypeOf(field_value);
                const field_type_info = @typeInfo(field_type);

                // Check field type for special handling
                const is_string = switch (field_type_info) {
                    .pointer => |ptr| ptr.size == .slice and ptr.child == u8 and ptr.is_const,
                    else => false,
                };

                const is_struct = switch (field_type_info) {
                    .@"struct" => true,
                    else => false,
                };

                if (is_string) {
                    // Handle string fields
                    const field_str = try std.fmt.bufPrintZ(buf[pos..], "  {s}: \"{s}\"\n", .{ field.name, field_value });
                    pos += field_str.len;
                } else if (is_struct) {
                    // Handle struct fields recursively
                    const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: ", .{field.name});
                    pos += field_header.len;

                    // Recursively print the struct, adjusting indentation
                    var temp_buf: [4096]u8 = undefined; // Increased for nested structs
                    const struct_str = try printStruct(field_value, &temp_buf);

                    // Add indentation to each line of the struct output
                    var line_iter = std.mem.splitScalar(u8, struct_str, '\n');
                    var first_line = true;
                    while (line_iter.next()) |line| {
                        if (line.len == 0) continue; // Skip empty lines

                        const indented_line = if (first_line) blk: {
                            first_line = false;
                            break :blk try std.fmt.bufPrintZ(buf[pos..], "{s}\n", .{line});
                        } else try std.fmt.bufPrintZ(buf[pos..], "  {s}\n", .{line});
                        pos += indented_line.len;
                    }
                } else {
                    // Handle other field types including optionals and slices
                    const field_str = switch (field_type_info) {
                        .optional => |opt| blk: {
                            // Check what type is inside the optional
                            const child_info = @typeInfo(opt.child);

                            // Check if the optional contains a struct
                            if (child_info == .@"struct") {
                                if (field_value) |val| {
                                    // Handle optional struct recursively
                                    const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: ", .{field.name});
                                    pos += field_header.len;

                                    // Recursively print the struct
                                    var temp_buf: [4096]u8 = undefined; // Increased for nested structs
                                    const struct_str = try printStruct(val, &temp_buf);

                                    // Add indentation to each line of the struct output
                                    var line_iter = std.mem.splitScalar(u8, struct_str, '\n');
                                    var first_line = true;
                                    while (line_iter.next()) |line| {
                                        if (line.len == 0) continue; // Skip empty lines

                                        const indented_line = if (first_line) blk2: {
                                            first_line = false;
                                            break :blk2 try std.fmt.bufPrintZ(buf[pos..], "{s}\n", .{line});
                                        } else try std.fmt.bufPrintZ(buf[pos..], "  {s}\n", .{line});
                                        pos += indented_line.len;
                                    }
                                    // Return empty string to indicate we've already handled output
                                    break :blk "";
                                } else {
                                    break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: null\n", .{field.name});
                                }
                            } else if (child_info == .pointer and child_info.pointer.size == .slice) {
                                // Optional slice - use {?s} for optional strings
                                if (child_info.pointer.child == u8) {
                                    if (field_value == null) {
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: None\n", .{field.name});
                                    } else {
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: \"{?s}\"\n", .{ field.name, field_value });
                                    }
                                } else {
                                    break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {?any}\n", .{ field.name, field_value });
                                }
                            } else {
                                break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {?}\n", .{ field.name, field_value });
                            }
                        },
                        .pointer => |ptr| blk: {
                            if (ptr.size == .slice) {
                                if (ptr.child == u8) {
                                    // String slice - print with quotes
                                    const str_slice: []const u8 = field_value;
                                    // Check if string is printable
                                    var is_printable = true;
                                    for (str_slice) |c| {
                                        if (c < 32 or c > 126) {
                                            is_printable = false;
                                            break;
                                        }
                                    }
                                    if (is_printable and str_slice.len > 0) {
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: \"{s}\"\n", .{ field.name, str_slice });
                                    } else {
                                        // Non-printable or empty, show as byte array
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {any}\n", .{ field.name, field_value });
                                    }
                                } else {
                                    // Check if it's a slice of structs
                                    const child_info = @typeInfo(ptr.child);
                                    if (child_info == .@"struct") {
                                        // Slice of structs - format them nicely with line breaks
                                        const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: [\n", .{field.name});
                                        pos += field_header.len;

                                        // Print each struct in the slice with proper indentation
                                        for (field_value, 0..) |item, i| {
                                            // Add indentation for array items
                                            const indent = try std.fmt.bufPrintZ(buf[pos..], "    ", .{});
                                            pos += indent.len;

                                            // Recursively print the struct
                                            var item_buf: [8192]u8 = undefined;
                                            const item_str = try printStruct(item, &item_buf);

                                            // Add extra indentation to each line of the nested struct
                                            var line_iter = std.mem.splitScalar(u8, item_str, '\n');
                                            var first_line = true;
                                            while (line_iter.next()) |line| {
                                                if (line.len == 0) continue;

                                                if (!first_line) {
                                                    const nested_indent = try std.fmt.bufPrintZ(buf[pos..], "    ", .{});
                                                    pos += nested_indent.len;
                                                }
                                                first_line = false;

                                                const line_out = try std.fmt.bufPrintZ(buf[pos..], "{s}\n", .{line});
                                                pos += line_out.len;
                                            }

                                            if (i < field_value.len - 1) {
                                                // Add comma between items
                                                const comma = try std.fmt.bufPrintZ(buf[pos..], "    ,\n", .{});
                                                pos += comma.len;
                                            }
                                        }

                                        const closer = try std.fmt.bufPrintZ(buf[pos..], "  ]\n", .{});
                                        pos += closer.len;
                                        // Return empty string to indicate we've already handled output
                                        break :blk "";
                                    } else if (child_info == .pointer and child_info.pointer.size == .slice and child_info.pointer.child == u8) {
                                        // Slice of strings ([][]const u8)
                                        const field_header = try std.fmt.bufPrintZ(buf[pos..], "  {s}: [", .{field.name});
                                        pos += field_header.len;

                                        // Print each string in the slice
                                        for (field_value, 0..) |item, i| {
                                            if (i > 0) {
                                                const comma = try std.fmt.bufPrintZ(buf[pos..], ", ", .{});
                                                pos += comma.len;
                                            }

                                            const str_item: []const u8 = item;
                                            // Check if string is printable
                                            var is_printable = true;
                                            for (str_item) |c| {
                                                if (c < 32 or c > 126) {
                                                    is_printable = false;
                                                    break;
                                                }
                                            }

                                            if (is_printable and str_item.len > 0) {
                                                const str_out = try std.fmt.bufPrintZ(buf[pos..], "\"{s}\"", .{str_item});
                                                pos += str_out.len;
                                            } else {
                                                // Show as byte array
                                                const bytes_out = try std.fmt.bufPrintZ(buf[pos..], "{any}", .{str_item});
                                                pos += bytes_out.len;
                                            }
                                        }

                                        const closer = try std.fmt.bufPrintZ(buf[pos..], "]\n", .{});
                                        pos += closer.len;
                                        // Return empty string to indicate we've already handled output
                                        break :blk "";
                                    } else {
                                        // Other non-struct slice types
                                        break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {any}\n", .{ field.name, field_value });
                                    }
                                }
                            } else {
                                break :blk try std.fmt.bufPrintZ(buf[pos..], "  {s}: {any}\n", .{ field.name, field_value });
                            }
                        },
                        else => try std.fmt.bufPrintZ(buf[pos..], "  {s}: {any}\n", .{ field.name, field_value }),
                    };
                    // Only add to pos if we didn't already handle it (optional struct case returns empty string)
                    if (field_str.len > 0) {
                        pos += field_str.len;
                    }
                }
            }

            // Write closing brace
            const footer = try std.fmt.bufPrintZ(buf[pos..], "}}\n", .{});
            pos += footer.len;

            // Null-terminate the string
            if (pos >= buf.len) return error.BufferTooSmall;
            buf[pos] = 0;

            return buf[0..pos :0];
        },
        else => @compileError("Not a struct"),
    }
}
