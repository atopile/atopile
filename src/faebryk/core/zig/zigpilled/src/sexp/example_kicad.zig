const std = @import("std");
const fp_lib_table = @import("kicad/fp_lib_table.zig");
const netlist = @import("kicad/netlist.zig");

pub fn main() !void {
    std.debug.print("=== Running fp_lib_table example ===\n", .{});
    try fp_lib_table.main();
    
    std.debug.print("\n=== Running netlist example ===\n", .{});
    try netlist.main();
}