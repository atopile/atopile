const std = @import("std");
const sexp = @import("sexp");
const prettytable = @import("prettytable");

const Result = struct {
    tokenize_time: u64,
    parse_time: u64,
    structure_time: u64,
};

const TestRun = struct {
    par: Result,
    token_count: usize,
};

const TEMPLATE_DIR = "test/resources/v9/pcb/modular";
const TEMPLATE_HEADER_PATH = TEMPLATE_DIR ++ "/header";
const TEMPLATE_FOOTER_PATH = TEMPLATE_DIR ++ "/footer";
const TEMPLATE_BLOCK_PATH = TEMPLATE_DIR ++ "/block";

pub fn bench(allocator: std.mem.Allocator, content: std.ArrayList(u8), cnt: usize) !TestRun {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();
    const arena_allocator = arena.allocator();
    var timer = try std.time.Timer.start();

    timer.reset();
    const tokens = try sexp.tokenizer.tokenize(allocator, content.items);
    defer allocator.free(tokens);
    const token_time = timer.read();

    timer.reset();
    var sexp_ast = try sexp.ast.parse(arena_allocator, tokens);
    defer sexp_ast.deinit(arena_allocator);
    const parse_time = timer.read();

    timer.reset();
    var pcbfile = try sexp.kicad.pcb.PcbFile.loads(arena_allocator, .{ .sexp = sexp_ast });
    defer pcbfile.free(arena_allocator);
    const structure_time = timer.read();

    const pcb = pcbfile.kicad_pcb;
    if (pcb.footprints.len != cnt) {
        std.debug.print("WARNING: Component count doesn't match! Expected: {}, Got: {}\n", .{ cnt, pcb.footprints.len });
    }

    const par_result = Result{
        .tokenize_time = token_time,
        .parse_time = parse_time,
        .structure_time = structure_time,
    };

    return TestRun{
        .par = par_result,
        .token_count = tokens.len,
    };
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("🚀 S-Expression Tokenizer Performance Test\n", .{});
    std.debug.print("🖥️  CPU count: {}\n\n", .{try std.Thread.getCpuCount()});

    // Load template files
    const header_content = try std.fs.cwd().readFileAlloc(allocator, TEMPLATE_HEADER_PATH, 1024 * 1024);
    defer allocator.free(header_content);

    const footer_content = try std.fs.cwd().readFileAlloc(allocator, TEMPLATE_FOOTER_PATH, 1024 * 1024);
    defer allocator.free(footer_content);

    const block_content = try std.fs.cwd().readFileAlloc(allocator, TEMPLATE_BLOCK_PATH, 1024 * 1024);
    defer allocator.free(block_content);

    // No need to load files now, we're using inline templates

    // Create performance results table
    var table = prettytable.Table.init(allocator);
    defer table.deinit();

    try table.setTitle(&.{
        "Test #",
        "Input Size",
        "Tokens",
        "Lexical",
        "Syntactic",
        "Semantic",
    });
    // bug?
    //table.setAlign(prettytable.Alignment.right);

    const C = 10;

    var cell_buffers: [C][6][32]u8 = undefined;

    for (0..C) |i| {
        const factor = (i + 1) * (i + 1) * (i + 1);
        std.debug.print("{}/{}\n", .{ i, C });

        // Create a medium-sized test content
        var content = std.ArrayList(u8).init(allocator);
        defer content.deinit();

        // Generate about 5MB of S-expression data
        const total = 10 * factor;
        try content.appendSlice(header_content);
        for (0..total) |_| {
            try content.appendSlice(block_content);
        }
        try content.appendSlice(footer_content);

        const result = try bench(allocator, content, total);

        const tokenize_time_par_ms = @as(f64, @floatFromInt(result.par.tokenize_time)) / 1_000_000.0;
        const ast_time_ms = @as(f64, @floatFromInt(result.par.parse_time)) / 1_000_000.0;
        const structure_time_ms = @as(f64, @floatFromInt(result.par.structure_time)) / 1_000_000.0;
        const mb = @as(f64, @floatFromInt(content.items.len)) / (1024.0 * 1024.0);

        const test_num = try std.fmt.bufPrint(&cell_buffers[i][0], "{}", .{i + 1});
        const size = try std.fmt.bufPrint(&cell_buffers[i][1], "{d:.2} MB", .{mb});
        const tokens = try std.fmt.bufPrint(&cell_buffers[i][2], "{}", .{result.token_count});
        const par = try std.fmt.bufPrint(&cell_buffers[i][3], "{d:.2} ms ({d:.2} MB/s)", .{ tokenize_time_par_ms, mb / tokenize_time_par_ms * 1000 });
        const ast_time = try std.fmt.bufPrint(&cell_buffers[i][4], "{d:.2} ms ({d:.2} MB/s)", .{ ast_time_ms, mb / ast_time_ms * 1000 });
        const structure_time = try std.fmt.bufPrint(&cell_buffers[i][5], "{d:.2} ms ({d:.2} MB/s)", .{ structure_time_ms, mb / structure_time_ms * 1000 });

        try table.addRow(&.{
            test_num,
            size,
            tokens,
            par,
            ast_time,
            structure_time,
        });
    }

    try table.print(std.io.getStdOut().writer());

    std.debug.print("\n✅ Test completed successfully!\n", .{});
}
