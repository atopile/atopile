const std = @import("std");
const faebryk = @import("faebryk");
const pyzig = @import("pyzig");

pub fn make_pyi(allocator: std.mem.Allocator, output_dir: []const u8, source_dir: []const u8) !void {
    std.fs.cwd().makePath(output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "composition", faebryk.composition, output_dir, source_dir);
    //try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "interface ", faebryk.interface, output_dir, source_dir);
    //try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "module", faebryk.module, output_dir, source_dir);
    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "node_type", faebryk.node_type, output_dir, source_dir);
    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "next", faebryk.next, output_dir, source_dir);
    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "typegraph", faebryk.typegraph, output_dir, source_dir);
    //try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "parameter", faebryk.parameter, output_dir, source_dir);
    try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "pointer", faebryk.pointer, output_dir, source_dir);
    //try pyzig.pyi.PyiGenerator.manualModuleStub(allocator, "trait", faebryk.trait, output_dir, source_dir);
}
