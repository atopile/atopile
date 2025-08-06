const std = @import("std");
const sexp = @import("sexp");

const TokenCounts = struct {
    lparen: usize = 0,
    rparen: usize = 0,
    symbols: usize = 0,
    numbers: usize = 0,
    strings: usize = 0,
    comments: usize = 0,
};

fn countTokenTypes(tokens: []const sexp.tokenizer.Token) TokenCounts {
    var counts = TokenCounts{};

    for (tokens) |token| {
        switch (token.type) {
            .lparen => counts.lparen += 1,
            .rparen => counts.rparen += 1,
            .symbol => counts.symbols += 1,
            .number => counts.numbers += 1,
            .string => counts.strings += 1,
            .comment => counts.comments += 1,
        }
    }

    return counts;
}

const SExpCounts = struct {
    lists: usize = 0,
    atoms: usize = 0,
};

fn countSExpElements(sexp_ast: ?sexp.ast.SExp) SExpCounts {
    var counts = SExpCounts{};

    if (sexp_ast) |s| {
        countSExpRecursive(s, &counts);
    }

    return counts;
}

fn countSExpRecursive(sexp_ast: sexp.ast.SExp, counts: *SExpCounts) void {
    switch (sexp_ast.value) {
        .list => |items| {
            counts.lists += 1;
            for (items) |item| {
                countSExpRecursive(item, counts);
            }
        },
        .symbol, .number, .string, .comment => counts.atoms += 1,
    }
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();
    const arena_allocator = arena.allocator();

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    if (args.len != 2) {
        std.debug.print("Usage: {s} <file.kicad_pcb>\n", .{args[0]});
        std.process.exit(1);
    }

    const file_path = args[1];

    // Get CPU count
    const cpu_count = try std.Thread.getCpuCount();
    std.debug.print("CPU count: {}\n", .{cpu_count});

    var timer = try std.time.Timer.start();

    // Read file size
    const file = try std.fs.cwd().openFile(file_path, .{});
    const file_size = try file.getEndPos();
    file.close();

    std.debug.print("File size: {} bytes ({d:.2} MB)\n", .{ file_size, @as(f64, @floatFromInt(file_size)) / (1024.0 * 1024.0) });
    std.debug.print("\n", .{});

    // Test1: Read file content
    const file_content = try std.fs.cwd().readFileAlloc(allocator, file_path, 100 * 1024 * 1024);
    defer allocator.free(file_content);
    const read_time = timer.read();
    std.debug.print("Read time: {d:.3} ms\n", .{@as(f64, @floatFromInt(read_time)) / 1_000_000.0});
    std.debug.print("Speed: {d:.2} MB/s\n", .{@as(f64, @floatFromInt(file_size)) / (@as(f64, @floatFromInt(read_time)) / 1_000_000_000.0) / (1024.0 * 1024.0)});

    // Test2: File tokenization
    std.debug.print("=== Tokenization ===\n", .{});
    timer.reset();

    const tokens = try sexp.tokenizer.tokenize(allocator, file_content);
    defer allocator.free(tokens);

    const token_time = timer.read();
    std.debug.print("Time: {d:.3} ms\n", .{@as(f64, @floatFromInt(token_time)) / 1_000_000.0});
    std.debug.print("Tokens: {}\n", .{tokens.len});
    std.debug.print("Speed: {d:.2} MB/s\n", .{@as(f64, @floatFromInt(file_size)) / (@as(f64, @floatFromInt(token_time)) / 1_000_000_000.0) / (1024.0 * 1024.0)});
    std.debug.print("\n", .{});

    // Test 3: Full parsing with arena allocator
    std.debug.print("=== Full Parsing (Arena Allocator) ===\n", .{});

    timer.reset();
    const sexp_ast = try sexp.ast.parse(arena_allocator, tokens);
    const parse_time = timer.read();

    timer.reset();
    var structure_time: u64 = 0;
    // Only perform structure decoding if the file is a .net file
    if (std.mem.endsWith(u8, file_path, ".net")) {
        var netlistfile = try sexp.kicad.netlist.NetlistFile.loads(arena_allocator, .{ .sexp = sexp_ast });
        defer netlistfile.free(arena_allocator);
        structure_time = timer.read();
    } else if (std.mem.endsWith(u8, file_path, ".kicad_pcb")) {
        var pcb_file = try sexp.kicad.pcb.PcbFile.loads(arena_allocator, .{ .sexp = sexp_ast });
        defer pcb_file.free(arena_allocator);
        structure_time = timer.read();
        std.debug.print("{}\n", .{pcb_file.kicad_pcb.footprints.len});
    }

    std.debug.print("Tokenize time: {d:.3} ms\n", .{@as(f64, @floatFromInt(token_time)) / 1_000_000.0});
    std.debug.print("Parse time: {d:.3} ms\n", .{@as(f64, @floatFromInt(parse_time)) / 1_000_000.0});
    std.debug.print("Structure time: {d:.3} ms\n", .{@as(f64, @floatFromInt(structure_time)) / 1_000_000.0});
    std.debug.print("Total time (tokenize + parse + structure): {d:.3} ms\n", .{@as(f64, @floatFromInt(token_time + parse_time + structure_time)) / 1_000_000.0});
    std.debug.print("Speed: {d:.2} MB/s\n", .{@as(f64, @floatFromInt(file_size)) / (@as(f64, @floatFromInt(token_time + parse_time + structure_time)) / 1_000_000_000.0) / (1024.0 * 1024.0)});

    // Output in format expected by Python script
    const counts = countTokenTypes(tokens);
    const sexp_counts = countSExpElements(sexp_ast);
    const tokenize_time_ms = @divFloor(token_time, 1_000_000);
    const parse_time_ms = @divFloor(parse_time, 1_000_000);
    const structure_time_ms = @divFloor(structure_time, 1_000_000);

    // RESULT:file_size:tokenize_time:parse_time:total_tokens:lparen:rparen:symbols:numbers:strings:comments:balanced:sexp_count:list_count:atom_count:cpu_count
    std.debug.print("RESULT:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}\n", .{
        file_size,
        tokenize_time_ms,
        parse_time_ms,
        structure_time_ms,
        tokens.len,
        counts.lparen,
        counts.rparen,
        counts.symbols,
        counts.numbers,
        counts.strings,
        counts.comments,
        counts.lparen == counts.rparen,
        //if (sexp != null) @as(usize, 1) else @as(usize, 0),
        @as(usize, 1),
        sexp_counts.lists,
        sexp_counts.atoms,
        cpu_count,
    });
}
