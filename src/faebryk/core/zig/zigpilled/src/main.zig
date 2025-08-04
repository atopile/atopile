const std = @import("std");

const Bottom = struct {
    int_field: i32,
};

const Top = struct {
    int_field: i32,
    float_field: f32,
    string_field: []const u8,
    bottom: Bottom,
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const stdout_file = std.io.getStdOut().writer();
    var bw = std.io.bufferedWriter(stdout_file);
    const stdout = bw.writer();

    // Create a struct instance
    const top = Top{
        .int_field = 1,
        .float_field = 2.5,
        .string_field = "Hello, JSON!",
        .bottom = Bottom{
            .int_field = 42,
        },
    };

    // Serialize to JSON
    const json_string = try std.json.stringifyAlloc(allocator, top, .{ .whitespace = .indent_2 });
    defer allocator.free(json_string);

    try stdout.print("Serialized JSON:\n{s}\n\n", .{json_string});

    // Parse JSON back to struct
    const json_input =
        \\{
        \\  "int_field": 100,
        \\  "float_field": 3.14,
        \\  "string_field": "Parsed from JSON",
        \\  "bottom": {
        \\    "int_field": 999
        \\  }
        \\}
    ;

    const parsed = try std.json.parseFromSlice(Top, allocator, json_input, .{});
    defer parsed.deinit();

    try stdout.print("Parsed struct: {}\n", .{parsed.value});
    //try stdout.print("  int_field: {}\n", .{parsed.value.int_field});
    //try stdout.print("  float_field: {d}\n", .{parsed.value.float_field});
    //try stdout.print("  string_field: {s}\n", .{parsed.value.string_field});
    //try stdout.print("  bottom.int_field: {}\n", .{parsed.value.bottom.int_field});

    try bw.flush();
}

test "simple test" {
    var list = std.ArrayList(i32).init(std.testing.allocator);
    defer list.deinit(); // try commenting this out and see if zig detects the memory leak!
    try list.append(42);
    try std.testing.expectEqual(@as(i32, 42), list.pop());
}

test "json serialization and parsing" {
    const allocator = std.testing.allocator;

    // Create test data
    const original = Top{
        .int_field = 123,
        .float_field = 45.67,
        .string_field = "test string",
        .bottom = Bottom{
            .int_field = 789,
        },
    };

    // Serialize to JSON
    const json_string = try std.json.stringifyAlloc(allocator, original, .{});
    defer allocator.free(json_string);

    // Parse back from JSON
    const parsed = try std.json.parseFromSlice(Top, allocator, json_string, .{});
    defer parsed.deinit();

    // Verify the values match
    try std.testing.expectEqual(original.int_field, parsed.value.int_field);
    try std.testing.expectEqual(original.float_field, parsed.value.float_field);
    try std.testing.expectEqualStrings(original.string_field, parsed.value.string_field);
    try std.testing.expectEqual(original.bottom.int_field, parsed.value.bottom.int_field);
}
