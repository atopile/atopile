const std = @import("std");
const sexp = @import("lib.zig");
const compat = @import("compat");
comptime {
    _ = compat;
}

const tokenizer = sexp.tokenizer;
const ast = sexp.ast;
const structure = sexp.structure;
const pcb = sexp.kicad.pcb;

const Options = struct {
    input_file: []const u8,
    warmup: usize = 0,
    samples: usize = 1,
};

const StageResult = struct {
    mean_ms: f64,
    mean_mem_delta_kib: f64,
    mean_peak_increment_kib: f64,
};

const TrackingAllocator = struct {
    child: std.mem.Allocator,
    current_bytes: usize = 0,
    peak_bytes: usize = 0,

    const Self = @This();

    fn init(child: std.mem.Allocator) Self {
        return .{ .child = child };
    }

    fn allocator(self: *Self) std.mem.Allocator {
        return .{
            .ptr = self,
            .vtable = &.{
                .alloc = alloc,
                .resize = resize,
                .remap = remap,
                .free = free,
            },
        };
    }

    fn alloc(ctx: *anyopaque, len: usize, alignment: std.mem.Alignment, ra: usize) ?[*]u8 {
        const self: *Self = @ptrCast(@alignCast(ctx));
        const mem = self.child.rawAlloc(len, alignment, ra) orelse return null;
        self.current_bytes += len;
        if (self.current_bytes > self.peak_bytes) self.peak_bytes = self.current_bytes;
        return mem;
    }

    fn resize(ctx: *anyopaque, buf: []u8, alignment: std.mem.Alignment, new_len: usize, ra: usize) bool {
        const self: *Self = @ptrCast(@alignCast(ctx));
        const old_len = buf.len;
        if (!self.child.rawResize(buf, alignment, new_len, ra)) return false;
        if (new_len >= old_len) {
            self.current_bytes += new_len - old_len;
        } else {
            self.current_bytes -= old_len - new_len;
        }
        if (self.current_bytes > self.peak_bytes) self.peak_bytes = self.current_bytes;
        return true;
    }

    fn remap(ctx: *anyopaque, buf: []u8, alignment: std.mem.Alignment, new_len: usize, ra: usize) ?[*]u8 {
        const self: *Self = @ptrCast(@alignCast(ctx));
        const old_len = buf.len;
        const mem = self.child.rawRemap(buf, alignment, new_len, ra) orelse return null;
        if (new_len >= old_len) {
            self.current_bytes += new_len - old_len;
        } else {
            self.current_bytes -= old_len - new_len;
        }
        if (self.current_bytes > self.peak_bytes) self.peak_bytes = self.current_bytes;
        return mem;
    }

    fn free(ctx: *anyopaque, buf: []u8, alignment: std.mem.Alignment, ra: usize) void {
        const self: *Self = @ptrCast(@alignCast(ctx));
        self.child.rawFree(buf, alignment, ra);
        self.current_bytes -= buf.len;
    }
};

fn nsToMs(ns: u64) f64 {
    return @as(f64, @floatFromInt(ns)) / 1_000_000.0;
}

fn bytesToKiB(bytes: usize) f64 {
    return @as(f64, @floatFromInt(bytes)) / 1024.0;
}

fn parseArgs(allocator: std.mem.Allocator) !Options {
    var args = try std.process.argsWithAllocator(allocator);
    defer args.deinit();

    _ = args.next();

    var opts = Options{ .input_file = "" };
    while (args.next()) |arg| {
        if (std.mem.eql(u8, arg, "--input-file")) {
            opts.input_file = try allocator.dupe(u8, args.next() orelse return error.MissingValue);
        } else if (std.mem.eql(u8, arg, "--warmup")) {
            opts.warmup = try std.fmt.parseInt(usize, args.next() orelse return error.MissingValue, 10);
        } else if (std.mem.eql(u8, arg, "--samples")) {
            opts.samples = try std.fmt.parseInt(usize, args.next() orelse return error.MissingValue, 10);
        } else {
            return error.InvalidArgument;
        }
    }

    if (opts.input_file.len == 0) return error.MissingInput;
    if (opts.samples == 0) return error.InvalidArgument;
    return opts;
}

fn parseForBenchmark(allocator: std.mem.Allocator, input: []const u8, tokens: []const tokenizer.Token) !ast.SExp {
    if (@hasDecl(ast, "parseBorrowedFast")) {
        return ast.parseBorrowedFast(allocator, input, tokens);
    }

    if (@hasDecl(ast, "parseBorrowed")) {
        const fn_info = @typeInfo(@TypeOf(ast.parseBorrowed)).@"fn";
        if (fn_info.params.len == 3) {
            return ast.parseBorrowed(allocator, input, tokens);
        }
        return ast.parseBorrowed(allocator, tokens);
    }

    const parse_info = @typeInfo(@TypeOf(ast.parse)).@"fn";
    if (parse_info.params.len == 3) {
        return ast.parse(allocator, input, tokens);
    }
    return ast.parse(allocator, tokens);
}

fn encodeToWriterForBenchmark(model: pcb.PcbFile, allocator: std.mem.Allocator, writer: anytype) !void {
    if (@hasDecl(structure, "encodeWrappedStreamForBenchmark")) {
        return structure.encodeWrappedStreamForBenchmark(model.kicad_pcb, allocator, "kicad_pcb", writer);
    }

    const encoded = try structure.encodeWrappedForBenchmark(model.kicad_pcb, allocator, "kicad_pcb");
    try encoded.str(writer);
}

fn benchmarkTokenizer(allocator: std.mem.Allocator, input: []const u8, warmup: usize, samples: usize) !StageResult {
    var total_ms: f64 = 0;
    var total_delta_kib: f64 = 0;
    var total_peak_inc_kib: f64 = 0;

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();

        const start_current = tracker.current_bytes;
        const start_peak = tracker.peak_bytes;
        var timer = try std.time.Timer.start();
        _ = try tokenizer._tokenize(arena.allocator(), input);
        const elapsed_ms = nsToMs(timer.read());

        if (i >= warmup) {
            total_ms += elapsed_ms;
            total_delta_kib += bytesToKiB(tracker.current_bytes) - bytesToKiB(start_current);
            total_peak_inc_kib += bytesToKiB(if (tracker.peak_bytes > start_peak) tracker.peak_bytes - start_peak else 0);
        }
    }

    const denom = @as(f64, @floatFromInt(samples));
    return .{
        .mean_ms = total_ms / denom,
        .mean_mem_delta_kib = total_delta_kib / denom,
        .mean_peak_increment_kib = total_peak_inc_kib / denom,
    };
}

fn benchmarkAst(allocator: std.mem.Allocator, input: []const u8, tokens: []const tokenizer.Token, warmup: usize, samples: usize) !StageResult {
    var total_ms: f64 = 0;
    var total_delta_kib: f64 = 0;
    var total_peak_inc_kib: f64 = 0;

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();

        const start_current = tracker.current_bytes;
        const start_peak = tracker.peak_bytes;
        var timer = try std.time.Timer.start();
        _ = try parseForBenchmark(arena.allocator(), input, tokens);
        const elapsed_ms = nsToMs(timer.read());

        if (i >= warmup) {
            total_ms += elapsed_ms;
            total_delta_kib += bytesToKiB(tracker.current_bytes) - bytesToKiB(start_current);
            total_peak_inc_kib += bytesToKiB(if (tracker.peak_bytes > start_peak) tracker.peak_bytes - start_peak else 0);
        }
    }

    const denom = @as(f64, @floatFromInt(samples));
    return .{
        .mean_ms = total_ms / denom,
        .mean_mem_delta_kib = total_delta_kib / denom,
        .mean_peak_increment_kib = total_peak_inc_kib / denom,
    };
}

fn benchmarkParser(allocator: std.mem.Allocator, parsed: ast.SExp, warmup: usize, samples: usize) !StageResult {
    var total_ms: f64 = 0;
    var total_delta_kib: f64 = 0;
    var total_peak_inc_kib: f64 = 0;

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();

        const start_current = tracker.current_bytes;
        const start_peak = tracker.peak_bytes;
        var timer = try std.time.Timer.start();
        _ = try pcb.PcbFile.loads(arena.allocator(), .{ .sexp = parsed });
        const elapsed_ms = nsToMs(timer.read());

        if (i >= warmup) {
            total_ms += elapsed_ms;
            total_delta_kib += bytesToKiB(tracker.current_bytes) - bytesToKiB(start_current);
            total_peak_inc_kib += bytesToKiB(if (tracker.peak_bytes > start_peak) tracker.peak_bytes - start_peak else 0);
        }
    }

    const denom = @as(f64, @floatFromInt(samples));
    return .{
        .mean_ms = total_ms / denom,
        .mean_mem_delta_kib = total_delta_kib / denom,
        .mean_peak_increment_kib = total_peak_inc_kib / denom,
    };
}

fn benchmarkEncode(allocator: std.mem.Allocator, model: pcb.PcbFile, warmup: usize, samples: usize) !StageResult {
    var total_ms: f64 = 0;
    var total_delta_kib: f64 = 0;
    var total_peak_inc_kib: f64 = 0;

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();

        const start_current = tracker.current_bytes;
        const start_peak = tracker.peak_bytes;
        var timer = try std.time.Timer.start();
        try encodeToWriterForBenchmark(model, arena.allocator(), std.io.null_writer);
        const elapsed_ms = nsToMs(timer.read());

        if (i >= warmup) {
            total_ms += elapsed_ms;
            total_delta_kib += bytesToKiB(tracker.current_bytes) - bytesToKiB(start_current);
            total_peak_inc_kib += bytesToKiB(if (tracker.peak_bytes > start_peak) tracker.peak_bytes - start_peak else 0);
        }
    }

    const denom = @as(f64, @floatFromInt(samples));
    return .{
        .mean_ms = total_ms / denom,
        .mean_mem_delta_kib = total_delta_kib / denom,
        .mean_peak_increment_kib = total_peak_inc_kib / denom,
    };
}

fn benchmarkPretty(allocator: std.mem.Allocator, model: pcb.PcbFile, warmup: usize, samples: usize) !StageResult {
    var prep_arena = std.heap.ArenaAllocator.init(allocator);
    defer prep_arena.deinit();
    var raw = std.array_list.Managed(u8).init(prep_arena.allocator());
    try encodeToWriterForBenchmark(model, prep_arena.allocator(), raw.writer());
    const source = raw.items;

    var total_ms: f64 = 0;
    var total_delta_kib: f64 = 0;
    var total_peak_inc_kib: f64 = 0;

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();

        const start_current = tracker.current_bytes;
        const start_peak = tracker.peak_bytes;
        var timer = try std.time.Timer.start();
        _ = try ast.SExp.prettify_sexp_string(arena.allocator(), source);
        const elapsed_ms = nsToMs(timer.read());

        if (i >= warmup) {
            total_ms += elapsed_ms;
            total_delta_kib += bytesToKiB(tracker.current_bytes) - bytesToKiB(start_current);
            total_peak_inc_kib += bytesToKiB(if (tracker.peak_bytes > start_peak) tracker.peak_bytes - start_peak else 0);
        }
    }

    const denom = @as(f64, @floatFromInt(samples));
    return .{
        .mean_ms = total_ms / denom,
        .mean_mem_delta_kib = total_delta_kib / denom,
        .mean_peak_increment_kib = total_peak_inc_kib / denom,
    };
}

fn printStage(name: []const u8, result: StageResult) void {
    std.debug.print("{s}: mean_ms={d:.3}, mean_mem_delta_kib={d:.3}, mean_peak_increment_kib={d:.3}\n", .{
        name,
        result.mean_ms,
        result.mean_mem_delta_kib,
        result.mean_peak_increment_kib,
    });
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const opts = parseArgs(allocator) catch |err| {
        std.debug.print("Usage: panel_file_bench --input-file <path> [--warmup N] [--samples N]\nError: {}\n", .{err});
        return err;
    };

    const input = try std.fs.cwd().readFileAlloc(allocator, opts.input_file, 512 * 1024 * 1024);
    defer allocator.free(input);

    std.debug.print("input_file={s}\nbytes={}\n", .{ opts.input_file, input.len });

    const tokenizer_res = try benchmarkTokenizer(allocator, input, opts.warmup, opts.samples);

    var parse_arena = std.heap.ArenaAllocator.init(allocator);
    defer parse_arena.deinit();
    const parse_alloc = parse_arena.allocator();
    const tokens = try tokenizer._tokenize(parse_alloc, input);
    const parsed = try parseForBenchmark(parse_alloc, input, tokens);
    const model = try pcb.PcbFile.loads(parse_alloc, .{ .sexp = parsed });

    const ast_res = try benchmarkAst(allocator, input, tokens, opts.warmup, opts.samples);
    const parser_res = try benchmarkParser(allocator, parsed, opts.warmup, opts.samples);
    const encode_res = try benchmarkEncode(allocator, model, opts.warmup, opts.samples);
    const pretty_res = try benchmarkPretty(allocator, model, opts.warmup, opts.samples);

    printStage("tokenizer", tokenizer_res);
    printStage("ast", ast_res);
    printStage("parser", parser_res);
    printStage("encode", encode_res);
    printStage("pretty", pretty_res);
}
