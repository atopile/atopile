const std = @import("std");
const tokenizer_parallel = @import("tokenizer_parallel.zig");
const ast = @import("ast.zig");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    if (args.len != 2) {
        std.debug.print("Usage: {s} <file.kicad_pcb>\n", .{args[0]});
        std.process.exit(1);
    }

    const file_path = args[1];
    
    // Get CPU count
    const cpu_count = try std.Thread.getCpuCount();
    
    // Tokenize with timing
    const tokenize_start = std.time.milliTimestamp();
    const tokens = try tokenizer_parallel.tokenizeFileParallel(allocator, file_path);
    defer allocator.free(tokens);
    const tokenize_end = std.time.milliTimestamp();
    
    // Parse AST with timing
    const parse_start = std.time.milliTimestamp();
    const sexps = try ast.parse(allocator, tokens);
    const parse_end = std.time.milliTimestamp();
    defer {
        for (sexps) |*sexp| {
            sexp.deinit(allocator);
        }
        allocator.free(sexps);
    }
    
    // Get file size
    const file = try std.fs.cwd().openFile(file_path, .{});
    defer file.close();
    const file_size = try file.getEndPos();

    // Count token types
    var lparen_count: usize = 0;
    var rparen_count: usize = 0;
    var symbol_count: usize = 0;
    var number_count: usize = 0;
    var string_count: usize = 0;
    var comment_count: usize = 0;

    for (tokens) |token| {
        switch (token.type) {
            .lparen => lparen_count += 1,
            .rparen => rparen_count += 1,
            .symbol => symbol_count += 1,
            .number => number_count += 1,
            .string => string_count += 1,
            .comment => comment_count += 1,
        }
    }
    
    // Count S-expression types
    var list_count: usize = 0;
    var atom_count: usize = 0;
    
    const Counter = struct {
        list_count: *usize,
        atom_count: *usize,
        
        fn countSExp(self: @This(), sexp: ast.SExp) void {
            switch (sexp) {
                .list => |items| {
                    self.list_count.* += 1;
                    for (items) |item| {
                        self.countSExp(item);
                    }
                },
                .symbol, .number, .string => self.atom_count.* += 1,
                .comment => {},
            }
        }
    };
    
    const counter = Counter{ .list_count = &list_count, .atom_count = &atom_count };
    for (sexps) |sexp| {
        counter.countSExp(sexp);
    }

    // Output in parseable format
    std.debug.print("RESULT:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}\n", .{
        file_size,
        tokenize_end - tokenize_start,
        parse_end - parse_start,
        tokens.len,
        lparen_count,
        rparen_count,
        symbol_count,
        number_count,
        string_count,
        comment_count,
        lparen_count == rparen_count,
        sexps.len,
        list_count,
        atom_count,
        cpu_count,
    });
}