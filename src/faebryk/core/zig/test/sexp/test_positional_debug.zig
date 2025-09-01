const std = @import("std");
const sexp = @import("sexp");

pub fn main() !void {
    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    const property_sexp =
        \\ (property "Reference" "G***"
        \\   (at 0 0 0)
        \\   (hide yes)
        \\   (uuid "13bc68c1-7d1e-4abb-88c2-bf2277ec8354")
        \\   (effects
        \\     (font
        \\       (size 1.524 1.524)
        \\       (thickness 0.3)
        \\     )
        \\   )
        \\ )
    ;

    // Parse to AST
    const tokens = try sexp.tokenizer.tokenize(allocator, property_sexp);
    defer allocator.free(tokens);
    
    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);
    
    // Debug: print the AST structure
    std.debug.print("AST structure:\n", .{});
    try printSexp(sexp_ast, 0);
    
    // Now try to decode
    const property = sexp.structure.loads(sexp.kicad.pcb.Property, allocator, .{ .sexp = sexp_ast }, "property") catch |err| {
        sexp.structure.printError(property_sexp, err);
        return err;
    };
    
    std.debug.print("\nSuccess! name={s}, value={s}\n", .{ property.name, property.value });
}

fn printSexp(sexp_ast: sexp.ast.SExp, indent: usize) !void {
    for (0..indent) |_| {
        std.debug.print("  ", .{});
    }
    
    switch (sexp_ast.value) {
        .symbol => |s| std.debug.print("Symbol: {s}\n", .{s}),
        .string => |s| std.debug.print("String: \"{s}\"\n", .{s}),
        .number => |n| std.debug.print("Number: {s}\n", .{n}),
        .comment => |c| std.debug.print("Comment: {s}\n", .{c}),
        .list => |items| {
            std.debug.print("List ({} items):\n", .{items.len});
            for (items) |item| {
                try printSexp(item, indent + 1);
            }
        },
    }
}