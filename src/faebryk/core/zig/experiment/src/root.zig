//! By convention, root.zig is the root source file when making a library. If
//! you are making an executable, the convention is to delete this file and
//! start with main.zig instead.
const std = @import("std");
const testing = std.testing;

const string = []const u8;

pub const Nested = struct {
    x: i32,
    y: string,
};

pub const Top = struct {
    a: i32,
    b: i32,
    c: Nested,

    pub fn sum(self: *const Top) i32 {
        return self.a + self.b;
    }
};

pub fn get_default_top(allocator: std.mem.Allocator) !*Top {
    const top = try allocator.create(Top);
    top.* = Top{ .a = 1, .b = 2, .c = .{ .x = 3, .y = "default" } };
    return top;
}

pub fn add(a: i32, b: i32) i32 {
    return a + b;
}

test "basic add functionality" {
    try testing.expect(add(3, 7) == 10);
}
