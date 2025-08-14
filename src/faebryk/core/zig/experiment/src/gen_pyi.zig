const std = @import("std");
const root = @import("root.zig");

pub fn get_pyi_content() []const u8 {
    const T = root.Top;
    // print hello
    std.debug.print("Hello, world!\n", .{});
    inline for (@typeInfo(T).@"struct".decls) |decl| {
        std.debug.print("{s}\n", .{decl.name});
        //const f = @field(root, decl.name);
        //std.debug.print("{}\n", .{@TypeOf(f)});
    }
    inline for (@typeInfo(T).@"struct".fields) |field| {
        std.debug.print("{s}\n", .{field.name});
        //const f = @field(T, field.name);
        //std.debug.print("{}\n", .{@TypeOf(f)});
    }

    return 
    \\class Nested:
    \\    x: int
    \\    y: str
    \\
    \\    def __init__(self, x: int, y: str) -> None: ...
    \\    def __repr__(self) -> str: ...
    \\
    \\class Top:
    \\    a: int
    \\    b: int
    \\    c: Nested
    \\
    \\    def __init__(self, a: int, b: int, c: Nested) -> None: ...
    \\    def __repr__(self) -> str: ...
    \\    def sum(self) -> int: ...
    \\
    \\def add(*, a: int, b: int) -> int: ...
    \\def get_default_top() -> Top: ...
    ;
}
pub fn main() !void {
    const content = get_pyi_content();

    // Write to stdout so build.zig can capture it
    const stdout = std.io.getStdOut().writer();
    try stdout.writeAll(content);
}
