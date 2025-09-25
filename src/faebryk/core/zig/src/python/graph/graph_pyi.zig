const std = @import("std");
const graph = @import("graph");
const pyzig = @import("pyzig");

pub fn make_pyi(allocator: std.mem.Allocator, output_dir: []const u8, source_dir: []const u8) !void {
    std.fs.cwd().makePath(output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "graph", graph.graph, output_dir, source_dir);
}
