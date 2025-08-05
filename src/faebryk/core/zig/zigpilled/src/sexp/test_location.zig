const std = @import("std");
const ast = @import("ast.zig");
const structure = @import("structure.zig");
const tokenizer = @import("tokenizer.zig");

const TestStruct = struct {
    name: []const u8,
    value: i32,
};

pub fn main() !void {
    const allocator = std.heap.page_allocator;

    // Test case with multiline input to show location tracking
    const input =
        \\(
        \\  (name "test")
        \\  (value "not a number")  ; This should error on line 3
        \\)
    ;

    std.debug.print("Input:\n{s}\n\n", .{input});

    // Tokenize
    const tokens = try tokenizer.tokenize(allocator, input);
    defer allocator.free(tokens);

    // Parse to AST
    var sexp = try ast.parse(allocator, tokens) orelse return error.EmptyFile;
    defer sexp.deinit(allocator);

    // Try to decode
    const result = structure.decode(TestStruct, allocator, sexp) catch |err| {
        std.debug.print("Error: {}\n", .{err});

        if (structure.getErrorContext()) |ctx| {
            var ctx_with_source = ctx;
            ctx_with_source.source = input;
            std.debug.print("{}\n", .{ctx_with_source});
        }

        return err;
    };

    std.debug.print("Success! name={s}, value={}\n", .{ result.name, result.value });
}
