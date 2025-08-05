const std = @import("std");
const tokenizer = @import("tokenizer.zig");
const ast = @import("ast.zig");
const netlist = @import("kicad/netlist.zig");

const TokenCounts = struct {
    lparen: usize = 0,
    rparen: usize = 0,
    symbols: usize = 0,
    numbers: usize = 0,
    strings: usize = 0,
    comments: usize = 0,
};

fn countTokenTypes(tokens: []const tokenizer.Token) TokenCounts {
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

fn countSExpElements(sexp: ?ast.SExp) SExpCounts {
    var counts = SExpCounts{};

    if (sexp) |s| {
        countSExpRecursive(s, &counts);
    }

    return counts;
}

fn countSExpRecursive(sexp: ast.SExp, counts: *SExpCounts) void {
    switch (sexp.value) {
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

    // Read file content
    const file_content = try std.fs.cwd().readFileAlloc(allocator, file_path, 100 * 1024 * 1024);
    defer allocator.free(file_content);
    const read_time = timer.read();
    std.debug.print("Read time: {d:.3} ms\n", .{@as(f64, @floatFromInt(read_time)) / 1_000_000.0});
    std.debug.print("Speed: {d:.2} MB/s\n", .{@as(f64, @floatFromInt(file_size)) / (@as(f64, @floatFromInt(read_time)) / 1_000_000_000.0) / (1024.0 * 1024.0)});

    // Test 1: Sequential tokenization
    std.debug.print("=== Sequential Tokenization ===\n", .{});

    timer.reset();
    const tokens_seq = try tokenizer._tokenize(allocator, file_content);
    defer {
        allocator.free(tokens_seq);
    } // No need for deinitTokens - tokens point to file_content

    const seq_time = timer.read();
    std.debug.print("Time: {d:.3} ms\n", .{@as(f64, @floatFromInt(seq_time)) / 1_000_000.0});
    std.debug.print("Tokens: {}\n", .{tokens_seq.len});
    std.debug.print("Speed: {d:.2} MB/s\n", .{@as(f64, @floatFromInt(file_size)) / (@as(f64, @floatFromInt(seq_time)) / 1_000_000_000.0) / (1024.0 * 1024.0)});
    std.debug.print("\n", .{});

    // Test 2: File tokenization (with duplication)
    std.debug.print("=== Parallel Tokenization ===\n", .{});
    timer.reset();

    const tokens_par = try tokenizer.tokenize(allocator, file_content);
    defer allocator.free(tokens_par);

    const par_time = timer.read();
    std.debug.print("Time: {d:.3} ms\n", .{@as(f64, @floatFromInt(par_time)) / 1_000_000.0});
    std.debug.print("Tokens: {}\n", .{tokens_par.len});
    std.debug.print("Speed: {d:.2} MB/s\n", .{@as(f64, @floatFromInt(file_size)) / (@as(f64, @floatFromInt(par_time)) / 1_000_000_000.0) / (1024.0 * 1024.0)});
    std.debug.print("Speedup: {d:.2}x\n", .{@as(f64, @floatFromInt(seq_time)) / @as(f64, @floatFromInt(par_time))});
    std.debug.print("\n", .{});

    // Test 3: Full parsing with arena allocator
    std.debug.print("=== Full Parsing (Arena Allocator) ===\n", .{});

    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();

    timer.reset();
    var sexp = try ast.parse(arena.allocator(), tokens_seq);
    defer sexp.deinit(arena.allocator());
    const parse_time = timer.read();

    timer.reset();
    var structure_time: u64 = 0;
    // Only perform structure decoding if the file is a .net file
    if (std.mem.endsWith(u8, file_path, ".net")) {
        // The parsed sexp should be the (export ...) expression
        // Remove debug output and just pass it directly

        var netlistfile = try netlist.NetlistFile.loads(arena.allocator(), .{ .sexp = sexp });
        defer netlistfile.free(arena.allocator());
        structure_time = timer.read();
    }

    std.debug.print("Tokenize time: {d:.3} ms\n", .{@as(f64, @floatFromInt(par_time)) / 1_000_000.0});
    std.debug.print("Parse time: {d:.3} ms\n", .{@as(f64, @floatFromInt(parse_time)) / 1_000_000.0});
    std.debug.print("Structure time: {d:.3} ms\n", .{@as(f64, @floatFromInt(structure_time)) / 1_000_000.0});
    std.debug.print("Total time (tokenize + parse + structure): {d:.3} ms\n", .{@as(f64, @floatFromInt(par_time + parse_time + structure_time)) / 1_000_000.0});
    std.debug.print("Speed: {d:.2} MB/s\n", .{@as(f64, @floatFromInt(file_size)) / (@as(f64, @floatFromInt(par_time + parse_time + structure_time)) / 1_000_000_000.0) / (1024.0 * 1024.0)});

    // Verify results match
    std.debug.print("\n=== Verification ===\n", .{});
    if (tokens_seq.len != tokens_par.len) {
        std.debug.print("WARNING: Token counts don't match! Sequential: {}, File: {}\n", .{ tokens_seq.len, tokens_par.len });
    } else {
        std.debug.print("✓ Token counts match\n", .{});
    }

    // Output in format expected by Python script
    const counts = countTokenTypes(tokens_seq);
    const sexp_counts = countSExpElements(sexp);
    const tokenize_time_ms = @divFloor(seq_time, 1_000_000);
    const parse_time_ms = @divFloor(parse_time, 1_000_000);
    const structure_time_ms = @divFloor(structure_time, 1_000_000);

    // RESULT:file_size:tokenize_time:parse_time:total_tokens:lparen:rparen:symbols:numbers:strings:comments:balanced:sexp_count:list_count:atom_count:cpu_count
    std.debug.print("RESULT:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}:{}\n", .{
        file_size,
        tokenize_time_ms,
        parse_time_ms,
        structure_time_ms,
        tokens_seq.len,
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
