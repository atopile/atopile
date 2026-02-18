const std = @import("std");
const fabll = @import("fabll");
const pyzig = @import("pyzig");

pub fn make_pyi(allocator: std.mem.Allocator, output_dir: []const u8, source_dir: []const u8) !void {
    std.fs.cwd().makePath(output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "literals", fabll.literals, output_dir, source_dir);
    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "parameters", fabll.parameters, output_dir, source_dir);
    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "expressions", fabll.expressions, output_dir, source_dir);
    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "units", fabll.units, output_dir, source_dir);
}
