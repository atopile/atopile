const std = @import("std");
const tokenizer = @import("tokenizer.zig");
const prettytable = @import("prettytable");
const ast = @import("ast.zig");
const netlist = @import("kicad/netlist.zig");

const Result = struct {
    tokenize_time: u64,
    parse_time: u64,
    structure_time: u64,
};

const TestRun = struct {
    seq: Result,
    par: Result,
    token_count: usize,
};

const TEMPLATE_HEADER =
    \\(export (version "E")
    \\  (design
    \\    (source "/home/needspeed/workspace/atopile/src/faebryk/core/zig/zigpilled/src/sexp/test_files/v9/sch/test.kicad_sch")
    \\    (date "2025-08-04T14:24:57-0700")
    \\    (tool "Eeschema 9.0.3")
    \\    (sheet (number "1") (name "/") (tstamps "/")
    \\      (title_block
    \\        (title)
    \\        (company)
    \\        (rev)
    \\        (date)
    \\        (source "test.kicad_sch")
    \\        (comment (number "1") (value ""))
    \\        (comment (number "2") (value ""))
    \\        (comment (number "3") (value ""))
    \\        (comment (number "4") (value ""))
    \\        (comment (number "5") (value ""))
    \\        (comment (number "6") (value ""))
    \\        (comment (number "7") (value ""))
    \\        (comment (number "8") (value ""))
    \\        (comment (number "9") (value ""))))
    \\    (sheet (number "2") (name "/Untitled Sheet/") (tstamps "/31d516f5-159a-4a07-a519-7bf941d8afe2/")
    \\      (title_block
    \\        (title)
    \\        (company)
    \\        (rev)
    \\        (date)
    \\        (source "untitled.kicad_sch")
    \\        (comment (number "1") (value ""))
    \\        (comment (number "2") (value ""))
    \\        (comment (number "3") (value ""))
    \\        (comment (number "4") (value ""))
    \\        (comment (number "5") (value ""))
    \\        (comment (number "6") (value ""))
    \\        (comment (number "7") (value ""))
    \\        (comment (number "8") (value ""))
    \\        (comment (number "9") (value "")))))
    \\  (components
    \\)
;

const TEMPLATE_ENTRY =
    \\    (comp (ref "D4")
    \\      (value "LED2")
    \\      (footprint "Resistor_SMD:R_0603_1608Metric")
    \\      (datasheet "~")
    \\      (fields
    \\        (field (name "Footprint") "Resistor_SMD:R_0603_1608Metric")
    \\        (field (name "Datasheet") "~")
    \\        (field (name "Description")))
    \\      (libsource (lib "Device") (part "LED") (description "Light emitting diode"))
    \\      (property (name "Sheetname") (value "Root"))
    \\      (property (name "Sheetfile") (value "test.kicad_sch"))
    \\      (property (name "ki_keywords") (value "LED diode"))
    \\      (property (name "ki_fp_filters") (value "LED* LED_SMD:* LED_THT:*"))
    \\      (sheetpath (names "/") (tstamps "/"))
    \\      (tstamps "64269ac3-771b-4c0d-91e0-eafc3dc4a07f")
    \\    )
;

const TEMPLATE_FOOTER =
    \\  )
    \\  (libparts)
    \\  (libraries)
    \\  (nets)
    \\)
;

pub fn bench(allocator: std.mem.Allocator, content: std.ArrayList(u8)) !TestRun {
    // Warm up
    {
        const tokens = try tokenizer.tokenize(allocator, content.items);
        allocator.free(tokens);
    }

    // Benchmark sequential tokenization
    var timer = try std.time.Timer.start();
    const tokens_seq = try tokenizer._tokenize(allocator, content.items);
    defer allocator.free(tokens_seq);
    const seq_token_time = timer.read();

    timer.reset();
    var sexp = try ast.parse(allocator, tokens_seq);
    const seq_parse_time = timer.read();
    defer sexp.deinit(allocator);

    timer.reset();
    var netlistfile = try netlist.NetlistFile.loads(allocator, .{ .sexp = sexp });
    defer netlistfile.free(allocator);
    const seq_structure_time = timer.read();

    const seq_result = Result{
        .tokenize_time = seq_token_time,
        .parse_time = seq_parse_time,
        .structure_time = seq_structure_time,
    };

    // Benchmark parallel tokenization
    timer.reset();
    const tokens_par = try tokenizer.tokenize(allocator, content.items);
    defer allocator.free(tokens_par);
    const par_time = timer.read();

    const par_result = Result{
        .tokenize_time = par_time,
        .parse_time = 0,
        .structure_time = 0,
    };

    // Verify results match
    if (tokens_seq.len != tokens_par.len) {
        std.debug.print("\nWARNING: Token counts don't match! Sequential: {}, Parallel: {}\n", .{ tokens_seq.len, tokens_par.len });
    }

    return TestRun{
        .seq = seq_result,
        .par = par_result,
        .token_count = tokens_seq.len,
    };
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("🚀 S-Expression Tokenizer Performance Test\n", .{});
    std.debug.print("🖥️  CPU count: {}\n\n", .{try std.Thread.getCpuCount()});

    // Create performance results table
    var table = prettytable.Table.init(allocator);
    defer table.deinit();

    try table.setTitle(&.{
        "Test #",
        "Input Size",
        "Tokens",
        "Tok Seq",
        "Tok Par",
        "AST",
        "Structure",
        "Speedup",
        "Throughput",
    });
    // bug?
    //table.setAlign(prettytable.Alignment.right);

    const C = 5;

    var cell_buffers: [C][9][32]u8 = undefined;

    for (0..C) |i| {
        const factor = (i + 1) * (i + 1) * (i + 1);
        std.debug.print("{}/{}\n", .{ i, C });

        // Create a medium-sized test content
        var content = std.ArrayList(u8).init(allocator);
        defer content.deinit();

        // Generate about 5MB of S-expression data
        try content.appendSlice(TEMPLATE_HEADER);
        for (0..5 * factor) |_| {
            try content.appendSlice(TEMPLATE_ENTRY);
        }
        try content.appendSlice(TEMPLATE_FOOTER);

        const result = try bench(allocator, content);

        const tokenize_time_seq_ms = @as(f64, @floatFromInt(result.seq.tokenize_time)) / 1_000_000.0;
        const tokenize_time_par_ms = @as(f64, @floatFromInt(result.par.tokenize_time)) / 1_000_000.0;
        const ast_time_ms = @as(f64, @floatFromInt(result.seq.parse_time)) / 1_000_000.0;
        const structure_time_ms = @as(f64, @floatFromInt(result.seq.structure_time)) / 1_000_000.0;
        const speedup = tokenize_time_seq_ms / tokenize_time_par_ms;
        const mb = @as(f64, @floatFromInt(content.items.len)) / (1024.0 * 1024.0);
        const mb_s = mb / tokenize_time_par_ms * 1000;

        const test_num = try std.fmt.bufPrint(&cell_buffers[i][0], "{}", .{i + 1});
        const size = try std.fmt.bufPrint(&cell_buffers[i][1], "{d:.2} MB", .{mb});
        const tokens = try std.fmt.bufPrint(&cell_buffers[i][2], "{}", .{result.token_count});
        const seq = try std.fmt.bufPrint(&cell_buffers[i][3], "{d:.2} ms", .{tokenize_time_seq_ms});
        const par = try std.fmt.bufPrint(&cell_buffers[i][4], "{d:.2} ms", .{tokenize_time_par_ms});
        const ast_time = try std.fmt.bufPrint(&cell_buffers[i][5], "{d:.2} ms", .{ast_time_ms});
        const structure_time = try std.fmt.bufPrint(&cell_buffers[i][6], "{d:.2} ms", .{structure_time_ms});
        const speedup_str = try std.fmt.bufPrint(&cell_buffers[i][7], "{d:.2}x", .{speedup});
        const throughput = try std.fmt.bufPrint(&cell_buffers[i][8], "{d:.2} MB/s", .{mb_s});

        try table.addRow(&.{
            test_num,
            size,
            tokens,
            seq,
            par,
            ast_time,
            structure_time,
            speedup_str,
            throughput,
        });
    }

    try table.print(std.io.getStdOut().writer());

    std.debug.print("\n✅ Test completed successfully!\n", .{});
}
