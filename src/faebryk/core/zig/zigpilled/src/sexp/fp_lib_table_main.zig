const fp_lib_table = @import("kicad/fp_lib_table.zig");

pub fn main() !void {
    try fp_lib_table.main();
}