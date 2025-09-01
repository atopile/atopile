const std = @import("std");
const sexp = @import("sexp");

pub fn main() !void {
    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    // This is what the Effects decoder receives when parsing from Property
    const font_only_sexp = 
        \\(font
        \\  (size 1.524 1.524)
        \\  (thickness 0.3)
        \\)
    ;

    std.debug.print("Parsing what Effects receives from Property:\n{s}\n", .{font_only_sexp});
    
    // Parse to tokens and AST
    const tokens = try sexp.tokenizer.tokenize(allocator, font_only_sexp);
    defer allocator.free(tokens);
    
    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);
    
    // Debug: print the AST structure
    std.debug.print("\nAST structure:\n", .{});
    try printSexp(sexp_ast, 0);
    
    // Try to decode this as Effects - this should fail
    std.debug.print("\nTrying to decode as Effects struct...\n", .{});
    const effects = sexp.structure.decode(sexp.kicad.pcb.Effects, allocator, sexp_ast) catch |err| {
        std.debug.print("Failed as expected: {}\n", .{err});
        if (sexp.structure.getErrorContext()) |ctx| {
            std.debug.print("Error context: {}\n", .{ctx});
        }
        
        // Now let's see if we can work around this
        std.debug.print("\nTrying workaround: wrapping in a list to simulate Effects structure\n", .{});
        
        // Create a wrapped version that looks like (effects (font ...))
        var wrapped_items = [_]sexp.ast.SExp{ sexp_ast };
        const wrapped_sexp = sexp.ast.SExp{
            .value = .{ .list = &wrapped_items },
            .location = null,
        };
        
        const effects2 = sexp.structure.decode(sexp.kicad.pcb.Effects, allocator, wrapped_sexp) catch |err2| {
            std.debug.print("Workaround also failed: {}\n", .{err2});
            return err2;
        };
        
        std.debug.print("Workaround succeeded! font.size.w={d}\n", .{effects2.font.size.w});
        return;
    };
    
    std.debug.print("Unexpectedly succeeded! font.size.w={d}\n", .{effects.font.size.w});
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