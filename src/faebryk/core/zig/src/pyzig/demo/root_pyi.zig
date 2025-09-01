const std = @import("std");
const root = @import("root.zig");
const pyzig = @import("pyzig");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var generator = pyzig.pyi.PyiGenerator.init(allocator);
    defer generator.deinit();

    const content = try generator.generate(root);
    defer allocator.free(content);

    // Write to stdout so build.zig can capture it
    const stdout = std.io.getStdOut().writer();
    try stdout.writeAll(content);
}
