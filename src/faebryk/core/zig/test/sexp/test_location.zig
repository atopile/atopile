const std = @import("std");
const sexp = @import("sexp");

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
    const tokens = try sexp.tokenizer.tokenize(allocator, input);
    defer allocator.free(tokens);

    // Parse to AST
    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    // Try to decode
    const result = sexp.structure.decode(TestStruct, allocator, sexp_ast) catch |err| {
        std.debug.print("Error: {}\n", .{err});

        if (sexp.structure.getErrorContext()) |ctx| {
            var ctx_with_source = ctx;
            ctx_with_source.source = input;
            std.debug.print("{}\n", .{ctx_with_source});
        }

        return err;
    };

    std.debug.print("Success! name={s}, value={}\n", .{ result.name, result.value });
}
