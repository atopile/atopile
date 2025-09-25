const std = @import("std");
const faebryk = @import("faebryk");
const pyzig = @import("pyzig");

pub fn make_pyi(allocator: std.mem.Allocator, output_dir: []const u8, source_dir: []const u8) !void {
    std.fs.cwd().makePath(output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "composition", faebryk.composition, output_dir, source_dir);
}
