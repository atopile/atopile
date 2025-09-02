const std = @import("std");
const pyzig = @import("pyzig");

pub fn main() !void {
    const root = @import("kicad/pcb.zig");
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

    try stdout.writeAll("\n");
    try stdout.writeAll("def loads(arg_0: str) -> PcbFile: ...\n");
    try stdout.writeAll("def dumps(arg_0: PcbFile) -> str: ...\n");
}
