const std = @import("std");
const sexp = @import("sexp");

const tokenizer = sexp.tokenizer;
const ast = sexp.ast;
const structure = sexp.structure;
const pcb = sexp.kicad.pcb;

const KiB: usize = 1024;
const MiB: usize = 1024 * KiB;

const DepthProfile = enum {
    shallow_tracks_like,
    deep_footprint_like,
};

const SizeLabel = enum {
    small,
    medium,
    large,
    xlarge,
};

const Layer = enum {
    tokenizer,
    ast,
    parser,
    encode,
    pretty,
};

const BucketSpec = struct {
    label: SizeLabel,
    target_bytes: usize,
    min_bytes: usize,
    max_exclusive: usize,
};

const bucket_specs = [_]BucketSpec{
    .{ .label = .small, .target_bytes = 48 * KiB, .min_bytes = 0, .max_exclusive = 64 * KiB },
    .{ .label = .medium, .target_bytes = 512 * KiB, .min_bytes = 64 * KiB, .max_exclusive = 1 * MiB },
    .{ .label = .large, .target_bytes = 5 * MiB, .min_bytes = 1 * MiB, .max_exclusive = 10 * MiB },
    .{ .label = .xlarge, .target_bytes = 12 * MiB, .min_bytes = 10 * MiB, .max_exclusive = 100 * MiB },
};

const profiles = [_]DepthProfile{
    .shallow_tracks_like,
    .deep_footprint_like,
};

const Options = struct {
    output_json: []const u8 = "artifacts/sexp-benchmark.json",
    warmup: usize = 1,
    samples: usize = 3,
    max_size_label: SizeLabel = .large,
};

const Dataset = struct {
    id: []u8,
    profile: DepthProfile,
    size_label: SizeLabel,
    bytes: usize,
    max_depth: usize,
    input: []u8,

    fn deinit(self: Dataset, allocator: std.mem.Allocator) void {
        allocator.free(self.id);
        allocator.free(self.input);
    }
};

const Metrics = struct {
    mean_ms: f64,
    median_ms: f64,
    p80_ms: f64,
    min_ms: f64,
    max_ms: f64,
};

const LayerSamples = struct {
    times_ms: []f64,
    peak_kib: []f64,
    mem_before_kib: []f64,
    mem_after_kib: []f64,
    mem_delta_kib: []f64,
    peak_increment_kib: []f64,
};

const StageMemorySamples = struct {
    mem_before_kib: []f64,
    mem_after_kib: []f64,
    mem_delta_kib: []f64,
    peak_increment_kib: []f64,
    cumulative_peak_kib: []f64,
    cumulative_peak_over_start_kib: []f64,

    fn deinit(self: StageMemorySamples, allocator: std.mem.Allocator) void {
        allocator.free(self.mem_before_kib);
        allocator.free(self.mem_after_kib);
        allocator.free(self.mem_delta_kib);
        allocator.free(self.peak_increment_kib);
        allocator.free(self.cumulative_peak_kib);
        allocator.free(self.cumulative_peak_over_start_kib);
    }
};

const PipelineCumulativeSamples = struct {
    tokenizer: StageMemorySamples,
    ast: StageMemorySamples,
    parser: StageMemorySamples,
    encode: StageMemorySamples,
    pretty: StageMemorySamples,

    fn deinit(self: PipelineCumulativeSamples, allocator: std.mem.Allocator) void {
        self.tokenizer.deinit(allocator);
        self.ast.deinit(allocator);
        self.parser.deinit(allocator);
        self.encode.deinit(allocator);
        self.pretty.deinit(allocator);
    }
};

const ResultRow = struct {
    dataset_id: []const u8,
    depth_profile: []const u8,
    size_label: []const u8,
    max_depth: usize,
    bytes: usize,
    layer: []const u8,
    samples: usize,
    mean_ms: f64,
    median_ms: f64,
    p80_ms: f64,
    min_ms: f64,
    max_ms: f64,
    mean_peak_kib: f64,
    median_peak_kib: f64,
    p80_peak_kib: f64,
    min_peak_kib: f64,
    max_peak_kib: f64,
    delta_mean_peak_kib_from_prev: f64,
    mean_stage_mem_before_kib: f64,
    mean_stage_mem_after_kib: f64,
    mean_stage_mem_delta_kib: f64,
    mean_stage_peak_increment_kib: f64,
    mean_cumulative_pipeline_peak_kib: f64,
    median_cumulative_pipeline_peak_kib: f64,
    p80_cumulative_pipeline_peak_kib: f64,
    min_cumulative_pipeline_peak_kib: f64,
    max_cumulative_pipeline_peak_kib: f64,
    delta_mean_cumulative_pipeline_peak_kib_from_prev: f64,
    mean_cumulative_pipeline_peak_over_start_kib: f64,
    delta_mean_cumulative_pipeline_peak_over_start_kib_from_prev: f64,
};

const OutputMetadata = struct {
    generated_unix_s: i64,
    warmup: usize,
    samples: usize,
    max_size_label: []const u8,
    dataset_count: usize,
    row_count: usize,
};

const OutputPayload = struct {
    metadata: OutputMetadata,
    rows: []const ResultRow,
};

const parse_errors = error{
    MissingValue,
    InvalidArgument,
    InvalidBucketSize,
};

fn printUsage() void {
    std.debug.print(
        "Usage: sexp_bench [--output-json <path>] [--warmup <n>] [--samples <n>] [--max-size-label <small|medium|large|xlarge>]\n",
        .{},
    );
}

fn parsePositiveInt(value: []const u8) !usize {
    const parsed = try std.fmt.parseInt(usize, value, 10);
    if (parsed == 0) {
        return parse_errors.InvalidArgument;
    }
    return parsed;
}

fn parseArgs(allocator: std.mem.Allocator) !Options {
    var options = Options{};
    var args = try std.process.argsWithAllocator(allocator);
    defer args.deinit();

    _ = args.next(); // executable name

    while (args.next()) |arg| {
        if (std.mem.eql(u8, arg, "--output-json")) {
            const value = args.next() orelse return parse_errors.MissingValue;
            options.output_json = try allocator.dupe(u8, value);
            continue;
        }
        if (std.mem.eql(u8, arg, "--warmup")) {
            const value = args.next() orelse return parse_errors.MissingValue;
            options.warmup = try parsePositiveInt(value);
            continue;
        }
        if (std.mem.eql(u8, arg, "--samples")) {
            const value = args.next() orelse return parse_errors.MissingValue;
            options.samples = try parsePositiveInt(value);
            continue;
        }
        if (std.mem.eql(u8, arg, "--max-size-label")) {
            const value = args.next() orelse return parse_errors.MissingValue;
            options.max_size_label = if (std.mem.eql(u8, value, "small"))
                .small
            else if (std.mem.eql(u8, value, "medium"))
                .medium
            else if (std.mem.eql(u8, value, "large"))
                .large
            else if (std.mem.eql(u8, value, "xlarge"))
                .xlarge
            else
                return parse_errors.InvalidArgument;
            continue;
        }
        return parse_errors.InvalidArgument;
    }

    return options;
}

fn nsToMs(ns: u64) f64 {
    return @as(f64, @floatFromInt(ns)) / 1_000_000.0;
}

fn bytesToKiB(bytes: usize) f64 {
    return @as(f64, @floatFromInt(bytes)) / 1024.0;
}

const TrackingAllocator = struct {
    child: std.mem.Allocator,
    current_bytes: usize = 0,
    peak_bytes: usize = 0,

    const Self = @This();

    pub fn init(child: std.mem.Allocator) Self {
        return .{ .child = child };
    }

    pub fn allocator(self: *Self) std.mem.Allocator {
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

    fn accountAlloc(self: *Self, len: usize) void {
        self.current_bytes += len;
        if (self.current_bytes > self.peak_bytes) {
            self.peak_bytes = self.current_bytes;
        }
    }

    fn accountFree(self: *Self, len: usize) void {
        if (len >= self.current_bytes) {
            self.current_bytes = 0;
        } else {
            self.current_bytes -= len;
        }
    }

    fn alloc(ctx: *anyopaque, len: usize, alignment: std.mem.Alignment, ret_addr: usize) ?[*]u8 {
        const self: *Self = @ptrCast(@alignCast(ctx));
        const out = self.child.rawAlloc(len, alignment, ret_addr) orelse return null;
        self.accountAlloc(len);
        return out;
    }

    fn resize(ctx: *anyopaque, memory: []u8, alignment: std.mem.Alignment, new_len: usize, ret_addr: usize) bool {
        const self: *Self = @ptrCast(@alignCast(ctx));
        const ok = self.child.rawResize(memory, alignment, new_len, ret_addr);
        if (!ok) return false;

        if (new_len >= memory.len) {
            self.accountAlloc(new_len - memory.len);
        } else {
            self.accountFree(memory.len - new_len);
        }
        return true;
    }

    fn remap(ctx: *anyopaque, memory: []u8, alignment: std.mem.Alignment, new_len: usize, ret_addr: usize) ?[*]u8 {
        const self: *Self = @ptrCast(@alignCast(ctx));
        const out = self.child.rawRemap(memory, alignment, new_len, ret_addr) orelse return null;
        if (new_len >= memory.len) {
            self.accountAlloc(new_len - memory.len);
        } else {
            self.accountFree(memory.len - new_len);
        }
        return out;
    }

    fn free(ctx: *anyopaque, memory: []u8, alignment: std.mem.Alignment, ret_addr: usize) void {
        const self: *Self = @ptrCast(@alignCast(ctx));
        self.accountFree(memory.len);
        self.child.rawFree(memory, alignment, ret_addr);
    }
};

fn lessThanF64(_: void, lhs: f64, rhs: f64) bool {
    return lhs < rhs;
}

fn calculateMetrics(allocator: std.mem.Allocator, samples_ms: []const f64) !Metrics {
    const sorted = try allocator.dupe(f64, samples_ms);
    defer allocator.free(sorted);
    std.sort.block(f64, sorted, {}, lessThanF64);

    var sum: f64 = 0;
    var min_v = sorted[0];
    var max_v = sorted[0];
    for (sorted) |v| {
        sum += v;
        if (v < min_v) min_v = v;
        if (v > max_v) max_v = v;
    }

    const n = sorted.len;
    const mid = n / 2;
    const median = if (n % 2 == 0)
        (sorted[mid - 1] + sorted[mid]) / 2.0
    else
        sorted[mid];

    const p80_idx = @min(n - 1, ((n - 1) * 80) / 100);

    return Metrics{
        .mean_ms = sum / @as(f64, @floatFromInt(n)),
        .median_ms = median,
        .p80_ms = sorted[p80_idx],
        .min_ms = min_v,
        .max_ms = max_v,
    };
}

fn allocStageMemorySamples(allocator: std.mem.Allocator, samples: usize) !StageMemorySamples {
    const mem_before_kib = try allocator.alloc(f64, samples);
    errdefer allocator.free(mem_before_kib);
    const mem_after_kib = try allocator.alloc(f64, samples);
    errdefer allocator.free(mem_after_kib);
    const mem_delta_kib = try allocator.alloc(f64, samples);
    errdefer allocator.free(mem_delta_kib);
    const peak_increment_kib = try allocator.alloc(f64, samples);
    errdefer allocator.free(peak_increment_kib);
    const cumulative_peak_kib = try allocator.alloc(f64, samples);
    errdefer allocator.free(cumulative_peak_kib);
    const cumulative_peak_over_start_kib = try allocator.alloc(f64, samples);
    errdefer allocator.free(cumulative_peak_over_start_kib);

    return .{
        .mem_before_kib = mem_before_kib,
        .mem_after_kib = mem_after_kib,
        .mem_delta_kib = mem_delta_kib,
        .peak_increment_kib = peak_increment_kib,
        .cumulative_peak_kib = cumulative_peak_kib,
        .cumulative_peak_over_start_kib = cumulative_peak_over_start_kib,
    };
}

fn storeStageMemorySample(
    out: *StageMemorySamples,
    idx: usize,
    stage_start_current: usize,
    stage_end_current: usize,
    stage_peak: usize,
    pipeline_start_peak: usize,
) void {
    const stage_peak_increment = if (stage_peak > stage_start_current)
        stage_peak - stage_start_current
    else
        0;
    const cumulative_peak_over_start = if (stage_peak > pipeline_start_peak)
        stage_peak - pipeline_start_peak
    else
        0;

    out.mem_before_kib[idx] = bytesToKiB(stage_start_current);
    out.mem_after_kib[idx] = bytesToKiB(stage_end_current);
    out.mem_delta_kib[idx] = bytesToKiB(stage_end_current) - bytesToKiB(stage_start_current);
    out.peak_increment_kib[idx] = bytesToKiB(stage_peak_increment);
    out.cumulative_peak_kib[idx] = bytesToKiB(stage_peak);
    out.cumulative_peak_over_start_kib[idx] = bytesToKiB(cumulative_peak_over_start);
}

fn bucketForBytes(bytes: usize) SizeLabel {
    if (bytes < 64 * KiB) return .small;
    if (bytes < 1 * MiB) return .medium;
    if (bytes < 10 * MiB) return .large;
    return .xlarge;
}

fn computeMaxDepth(text: []const u8) usize {
    var depth: usize = 0;
    var max_depth: usize = 0;
    for (text) |c| {
        switch (c) {
            '(' => {
                depth += 1;
                if (depth > max_depth) max_depth = depth;
            },
            ')' => {
                if (depth > 0) depth -= 1;
            },
            else => {},
        }
    }
    return max_depth;
}

fn appendBoardHeader(buf: *std.array_list.Managed(u8)) !void {
    try buf.appendSlice(
        "(kicad_pcb\n" ++
            "  (version 20241229)\n" ++
            "  (generator \"sexp_bench\")\n" ++
            "  (generator_version \"1\")\n" ++
            "  (layers\n" ++
            "    (0 \"F.Cu\" signal)\n" ++
            "    (31 \"B.Cu\" signal)\n" ++
            "  )\n" ++
            "  (setup\n" ++
            "    (pad_to_mask_clearance 0)\n" ++
            "    (allow_soldermask_bridges_in_footprints no)\n" ++
            "    (tenting front back)\n" ++
            "    (pcbplotparams\n" ++
            "      (layerselection 0x00000000_00000000_000010fc_ffffffff)\n" ++
            "      (plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)\n" ++
            "      (dashed_line_dash_ratio 12)\n" ++
            "      (dashed_line_gap_ratio 3)\n" ++
            "      (svgprecision 4)\n" ++
            "      (mode 1)\n" ++
            "      (hpglpennumber 1)\n" ++
            "      (hpglpenspeed 20)\n" ++
            "      (hpglpendiameter 15)\n" ++
            "      (outputformat 1)\n" ++
            "      (drillshape 1)\n" ++
            "      (scaleselection 1)\n" ++
            "      (outputdirectory \"\")\n" ++
            "    )\n" ++
            "  )\n" ++
            "  (net 0 \"\")\n" ++
            "  (net 1 \"N1\")\n",
    );
}

fn appendBoardFooter(buf: *std.array_list.Managed(u8)) !void {
    try buf.appendSlice(")\n");
}

fn appendShallowBlock(writer: anytype, idx: usize) !void {
    const x1 = idx % 200;
    const y1 = (idx / 200) % 200;
    const x2 = x1 + 1;
    const y2 = y1 + 1;
    try writer.print(
        "  (segment (start {d} {d}) (end {d} {d}) (width 0.25) (layer \"F.Cu\") (net 1))\n" ++
            "  (via (at {d} {d}) (size 0.8) (drill 0.4) (layers \"F.Cu\" \"B.Cu\") (net 1))\n",
        .{ x1, y1, x2, y2, x1, y1 },
    );
}

fn appendDeepBlock(writer: anytype, idx: usize) !void {
    const x = idx % 300;
    const y = (idx / 300) % 300;
    try writer.print(
        "  (footprint \"BENCH:FP_{d}\"\n" ++
            "    (at {d} {d} 0)\n" ++
            "    (bench_deep (a (b (c (d (e (f {d})))))))\n" ++
            "  )\n",
        .{ idx, x, y, idx },
    );
}

fn synthesizeDatasetInput(
    allocator: std.mem.Allocator,
    profile: DepthProfile,
    target_bytes: usize,
) ![]u8 {
    var buf = std.array_list.Managed(u8).init(allocator);
    errdefer buf.deinit();
    try appendBoardHeader(&buf);

    var idx: usize = 0;
    while (buf.items.len + 2 < target_bytes) : (idx += 1) {
        const writer = buf.writer();
        switch (profile) {
            .shallow_tracks_like => try appendShallowBlock(writer, idx),
            .deep_footprint_like => try appendDeepBlock(writer, idx),
        }
    }

    try appendBoardFooter(&buf);
    return try buf.toOwnedSlice();
}

fn makeDatasets(allocator: std.mem.Allocator, max_size_label: SizeLabel) ![]Dataset {
    var datasets = std.array_list.Managed(Dataset).init(allocator);
    errdefer {
        for (datasets.items) |dataset| dataset.deinit(allocator);
        datasets.deinit();
    }

    for (profiles) |profile| {
        for (bucket_specs) |bucket| {
            if (@intFromEnum(bucket.label) > @intFromEnum(max_size_label)) {
                continue;
            }
            const input = try synthesizeDatasetInput(allocator, profile, bucket.target_bytes);
            const actual_bucket = bucketForBytes(input.len);
            if (actual_bucket != bucket.label) {
                return parse_errors.InvalidBucketSize;
            }
            if (input.len < bucket.min_bytes or input.len >= bucket.max_exclusive) {
                return parse_errors.InvalidBucketSize;
            }

            const id = try std.fmt.allocPrint(
                allocator,
                "{s}-{s}",
                .{ @tagName(profile), @tagName(bucket.label) },
            );
            const max_depth = computeMaxDepth(input);

            try datasets.append(.{
                .id = id,
                .profile = profile,
                .size_label = bucket.label,
                .bytes = input.len,
                .max_depth = max_depth,
                .input = input,
            });
        }
    }

    return datasets.toOwnedSlice();
}

fn measureTokenizer(
    allocator: std.mem.Allocator,
    input: []const u8,
    warmup: usize,
    samples: usize,
) !LayerSamples {
    var times_out = try allocator.alloc(f64, samples);
    var peak_out = try allocator.alloc(f64, samples);
    var mem_before_out = try allocator.alloc(f64, samples);
    var mem_after_out = try allocator.alloc(f64, samples);
    var mem_delta_out = try allocator.alloc(f64, samples);
    var peak_increment_out = try allocator.alloc(f64, samples);
    errdefer allocator.free(times_out);
    errdefer allocator.free(peak_out);
    errdefer allocator.free(mem_before_out);
    errdefer allocator.free(mem_after_out);
    errdefer allocator.free(mem_delta_out);
    errdefer allocator.free(peak_increment_out);

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();
        const stage_start_current = tracker.current_bytes;
        const stage_start_peak = tracker.peak_bytes;

        var timer = try std.time.Timer.start();
        _ = try tokenizer._tokenize(arena.allocator(), input);
        const elapsed_ms = nsToMs(timer.read());
        const stage_end_current = tracker.current_bytes;
        const stage_peak = tracker.peak_bytes;
        if (i >= warmup) {
            const idx = i - warmup;
            times_out[idx] = elapsed_ms;
            peak_out[idx] = bytesToKiB(stage_peak);
            mem_before_out[idx] = bytesToKiB(stage_start_current);
            mem_after_out[idx] = bytesToKiB(stage_end_current);
            mem_delta_out[idx] = mem_after_out[idx] - mem_before_out[idx];
            peak_increment_out[idx] = bytesToKiB(if (stage_peak > stage_start_peak) stage_peak - stage_start_peak else 0);
        }
    }
    return .{
        .times_ms = times_out,
        .peak_kib = peak_out,
        .mem_before_kib = mem_before_out,
        .mem_after_kib = mem_after_out,
        .mem_delta_kib = mem_delta_out,
        .peak_increment_kib = peak_increment_out,
    };
}

fn measureAst(
    allocator: std.mem.Allocator,
    tokens: []const tokenizer.Token,
    warmup: usize,
    samples: usize,
) !LayerSamples {
    var times_out = try allocator.alloc(f64, samples);
    var peak_out = try allocator.alloc(f64, samples);
    var mem_before_out = try allocator.alloc(f64, samples);
    var mem_after_out = try allocator.alloc(f64, samples);
    var mem_delta_out = try allocator.alloc(f64, samples);
    var peak_increment_out = try allocator.alloc(f64, samples);
    errdefer allocator.free(times_out);
    errdefer allocator.free(peak_out);
    errdefer allocator.free(mem_before_out);
    errdefer allocator.free(mem_after_out);
    errdefer allocator.free(mem_delta_out);
    errdefer allocator.free(peak_increment_out);

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();
        const stage_start_current = tracker.current_bytes;
        const stage_start_peak = tracker.peak_bytes;

        var timer = try std.time.Timer.start();
        _ = try ast.parse(arena.allocator(), tokens);
        const elapsed_ms = nsToMs(timer.read());
        const stage_end_current = tracker.current_bytes;
        const stage_peak = tracker.peak_bytes;
        if (i >= warmup) {
            const idx = i - warmup;
            times_out[idx] = elapsed_ms;
            peak_out[idx] = bytesToKiB(stage_peak);
            mem_before_out[idx] = bytesToKiB(stage_start_current);
            mem_after_out[idx] = bytesToKiB(stage_end_current);
            mem_delta_out[idx] = mem_after_out[idx] - mem_before_out[idx];
            peak_increment_out[idx] = bytesToKiB(if (stage_peak > stage_start_peak) stage_peak - stage_start_peak else 0);
        }
    }
    return .{
        .times_ms = times_out,
        .peak_kib = peak_out,
        .mem_before_kib = mem_before_out,
        .mem_after_kib = mem_after_out,
        .mem_delta_kib = mem_delta_out,
        .peak_increment_kib = peak_increment_out,
    };
}

fn measureParser(
    allocator: std.mem.Allocator,
    parsed: ast.SExp,
    warmup: usize,
    samples: usize,
) !LayerSamples {
    var times_out = try allocator.alloc(f64, samples);
    var peak_out = try allocator.alloc(f64, samples);
    var mem_before_out = try allocator.alloc(f64, samples);
    var mem_after_out = try allocator.alloc(f64, samples);
    var mem_delta_out = try allocator.alloc(f64, samples);
    var peak_increment_out = try allocator.alloc(f64, samples);
    errdefer allocator.free(times_out);
    errdefer allocator.free(peak_out);
    errdefer allocator.free(mem_before_out);
    errdefer allocator.free(mem_after_out);
    errdefer allocator.free(mem_delta_out);
    errdefer allocator.free(peak_increment_out);

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();
        const stage_start_current = tracker.current_bytes;
        const stage_start_peak = tracker.peak_bytes;

        var timer = try std.time.Timer.start();
        _ = try pcb.PcbFile.loads(arena.allocator(), .{ .sexp = parsed });
        const elapsed_ms = nsToMs(timer.read());
        const stage_end_current = tracker.current_bytes;
        const stage_peak = tracker.peak_bytes;
        if (i >= warmup) {
            const idx = i - warmup;
            times_out[idx] = elapsed_ms;
            peak_out[idx] = bytesToKiB(stage_peak);
            mem_before_out[idx] = bytesToKiB(stage_start_current);
            mem_after_out[idx] = bytesToKiB(stage_end_current);
            mem_delta_out[idx] = mem_after_out[idx] - mem_before_out[idx];
            peak_increment_out[idx] = bytesToKiB(if (stage_peak > stage_start_peak) stage_peak - stage_start_peak else 0);
        }
    }
    return .{
        .times_ms = times_out,
        .peak_kib = peak_out,
        .mem_before_kib = mem_before_out,
        .mem_after_kib = mem_after_out,
        .mem_delta_kib = mem_delta_out,
        .peak_increment_kib = peak_increment_out,
    };
}

fn measureEncode(
    allocator: std.mem.Allocator,
    model: pcb.PcbFile,
    warmup: usize,
    samples: usize,
) !LayerSamples {
    var times_out = try allocator.alloc(f64, samples);
    var peak_out = try allocator.alloc(f64, samples);
    var mem_before_out = try allocator.alloc(f64, samples);
    var mem_after_out = try allocator.alloc(f64, samples);
    var mem_delta_out = try allocator.alloc(f64, samples);
    var peak_increment_out = try allocator.alloc(f64, samples);
    errdefer allocator.free(times_out);
    errdefer allocator.free(peak_out);
    errdefer allocator.free(mem_before_out);
    errdefer allocator.free(mem_after_out);
    errdefer allocator.free(mem_delta_out);
    errdefer allocator.free(peak_increment_out);

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();
        const stage_start_current = tracker.current_bytes;
        const stage_start_peak = tracker.peak_bytes;

        var timer = try std.time.Timer.start();
        try structure.encodeWrappedStreamForBenchmark(
            model.kicad_pcb,
            arena.allocator(),
            "kicad_pcb",
            std.io.null_writer,
        );
        const elapsed_ms = nsToMs(timer.read());
        const stage_end_current = tracker.current_bytes;
        const stage_peak = tracker.peak_bytes;
        if (i >= warmup) {
            const idx = i - warmup;
            times_out[idx] = elapsed_ms;
            peak_out[idx] = bytesToKiB(stage_peak);
            mem_before_out[idx] = bytesToKiB(stage_start_current);
            mem_after_out[idx] = bytesToKiB(stage_end_current);
            mem_delta_out[idx] = mem_after_out[idx] - mem_before_out[idx];
            peak_increment_out[idx] = bytesToKiB(if (stage_peak > stage_start_peak) stage_peak - stage_start_peak else 0);
        }
    }
    return .{
        .times_ms = times_out,
        .peak_kib = peak_out,
        .mem_before_kib = mem_before_out,
        .mem_after_kib = mem_after_out,
        .mem_delta_kib = mem_delta_out,
        .peak_increment_kib = peak_increment_out,
    };
}

fn measurePretty(
    allocator: std.mem.Allocator,
    model: pcb.PcbFile,
    warmup: usize,
    samples: usize,
) !LayerSamples {
    var encode_arena = std.heap.ArenaAllocator.init(allocator);
    defer encode_arena.deinit();
    const encoded = try structure.encodeWrappedForBenchmark(
        model.kicad_pcb,
        encode_arena.allocator(),
        "kicad_pcb",
    );

    var times_out = try allocator.alloc(f64, samples);
    var peak_out = try allocator.alloc(f64, samples);
    var mem_before_out = try allocator.alloc(f64, samples);
    var mem_after_out = try allocator.alloc(f64, samples);
    var mem_delta_out = try allocator.alloc(f64, samples);
    var peak_increment_out = try allocator.alloc(f64, samples);
    errdefer allocator.free(times_out);
    errdefer allocator.free(peak_out);
    errdefer allocator.free(mem_before_out);
    errdefer allocator.free(mem_after_out);
    errdefer allocator.free(mem_delta_out);
    errdefer allocator.free(peak_increment_out);

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var output_arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer output_arena.deinit();
        const stage_start_current = tracker.current_bytes;
        const stage_start_peak = tracker.peak_bytes;

        var timer = try std.time.Timer.start();
        _ = try encoded.pretty(output_arena.allocator());
        const elapsed_ms = nsToMs(timer.read());
        const stage_end_current = tracker.current_bytes;
        const stage_peak = tracker.peak_bytes;
        if (i >= warmup) {
            const idx = i - warmup;
            times_out[idx] = elapsed_ms;
            peak_out[idx] = bytesToKiB(stage_peak);
            mem_before_out[idx] = bytesToKiB(stage_start_current);
            mem_after_out[idx] = bytesToKiB(stage_end_current);
            mem_delta_out[idx] = mem_after_out[idx] - mem_before_out[idx];
            peak_increment_out[idx] = bytesToKiB(if (stage_peak > stage_start_peak) stage_peak - stage_start_peak else 0);
        }
    }
    return .{
        .times_ms = times_out,
        .peak_kib = peak_out,
        .mem_before_kib = mem_before_out,
        .mem_after_kib = mem_after_out,
        .mem_delta_kib = mem_delta_out,
        .peak_increment_kib = peak_increment_out,
    };
}

fn measureCumulativePipelinePeaks(
    allocator: std.mem.Allocator,
    input: []const u8,
    warmup: usize,
    samples: usize,
) !PipelineCumulativeSamples {
    var tok = try allocStageMemorySamples(allocator, samples);
    errdefer tok.deinit(allocator);
    var ast_out = try allocStageMemorySamples(allocator, samples);
    errdefer ast_out.deinit(allocator);
    var parser_out = try allocStageMemorySamples(allocator, samples);
    errdefer parser_out.deinit(allocator);
    var encode_out = try allocStageMemorySamples(allocator, samples);
    errdefer encode_out.deinit(allocator);
    var pretty_out = try allocStageMemorySamples(allocator, samples);
    errdefer pretty_out.deinit(allocator);

    var i: usize = 0;
    while (i < warmup + samples) : (i += 1) {
        var tracker = TrackingAllocator.init(allocator);
        var arena = std.heap.ArenaAllocator.init(tracker.allocator());
        defer arena.deinit();
        const a = arena.allocator();
        const pipeline_start_peak = tracker.peak_bytes;

        const tok_start = tracker.current_bytes;
        const tokens = try tokenizer._tokenize(a, input);
        const tok_end = tracker.current_bytes;
        const tok_peak = tracker.peak_bytes;

        const ast_start = tracker.current_bytes;
        const parsed = try ast.parse(a, tokens);
        const ast_end = tracker.current_bytes;
        const ast_peak = tracker.peak_bytes;

        const parser_start = tracker.current_bytes;
        const model = try pcb.PcbFile.loads(a, .{ .sexp = parsed });
        const parser_end = tracker.current_bytes;
        const parser_peak = tracker.peak_bytes;

        const encode_start = tracker.current_bytes;
        const encoded = try structure.encodeWrappedForBenchmark(model.kicad_pcb, a, "kicad_pcb");
        const encode_end = tracker.current_bytes;
        const encode_peak = tracker.peak_bytes;

        const pretty_start = tracker.current_bytes;
        _ = try encoded.pretty(a);
        const pretty_end = tracker.current_bytes;
        const pretty_peak = tracker.peak_bytes;

        if (i >= warmup) {
            const idx = i - warmup;
            storeStageMemorySample(&tok, idx, tok_start, tok_end, tok_peak, pipeline_start_peak);
            storeStageMemorySample(&ast_out, idx, ast_start, ast_end, ast_peak, pipeline_start_peak);
            storeStageMemorySample(&parser_out, idx, parser_start, parser_end, parser_peak, pipeline_start_peak);
            storeStageMemorySample(&encode_out, idx, encode_start, encode_end, encode_peak, pipeline_start_peak);
            storeStageMemorySample(&pretty_out, idx, pretty_start, pretty_end, pretty_peak, pipeline_start_peak);
        }
    }

    return .{
        .tokenizer = tok,
        .ast = ast_out,
        .parser = parser_out,
        .encode = encode_out,
        .pretty = pretty_out,
    };
}

fn appendLayerResult(
    allocator: std.mem.Allocator,
    rows: *std.array_list.Managed(ResultRow),
    dataset: Dataset,
    layer: Layer,
    layer_samples: LayerSamples,
    stage_mem_samples: StageMemorySamples,
) !f64 {
    const metrics = try calculateMetrics(allocator, layer_samples.times_ms);
    const peak_metrics = try calculateMetrics(allocator, layer_samples.peak_kib);
    const stage_mem_before_metrics = try calculateMetrics(allocator, layer_samples.mem_before_kib);
    const stage_mem_after_metrics = try calculateMetrics(allocator, layer_samples.mem_after_kib);
    const stage_mem_delta_metrics = try calculateMetrics(allocator, layer_samples.mem_delta_kib);
    const stage_peak_increment_metrics = try calculateMetrics(allocator, layer_samples.peak_increment_kib);
    const cumulative_peak_metrics = try calculateMetrics(allocator, stage_mem_samples.cumulative_peak_kib);
    const cumulative_peak_over_start_metrics = try calculateMetrics(allocator, stage_mem_samples.cumulative_peak_over_start_kib);
    const prev_peak_mean = if (rows.items.len > 0) blk: {
        const prev = rows.items[rows.items.len - 1];
        if (std.mem.eql(u8, prev.dataset_id, dataset.id)) {
            break :blk prev.mean_peak_kib;
        }
        break :blk 0.0;
    } else 0.0;
    const prev_cumulative_peak_mean = if (rows.items.len > 0) blk: {
        const prev = rows.items[rows.items.len - 1];
        if (std.mem.eql(u8, prev.dataset_id, dataset.id)) {
            break :blk prev.mean_cumulative_pipeline_peak_kib;
        }
        break :blk 0.0;
    } else 0.0;
    const prev_cumulative_peak_over_start_mean = if (rows.items.len > 0) blk: {
        const prev = rows.items[rows.items.len - 1];
        if (std.mem.eql(u8, prev.dataset_id, dataset.id)) {
            break :blk prev.mean_cumulative_pipeline_peak_over_start_kib;
        }
        break :blk 0.0;
    } else 0.0;

    const delta_peak_mean = peak_metrics.mean_ms - prev_peak_mean;
    const delta_cumulative_peak_mean = cumulative_peak_metrics.mean_ms - prev_cumulative_peak_mean;
    const delta_cumulative_peak_over_start_mean = cumulative_peak_over_start_metrics.mean_ms - prev_cumulative_peak_over_start_mean;
    try rows.append(.{
        .dataset_id = dataset.id,
        .depth_profile = @tagName(dataset.profile),
        .size_label = @tagName(dataset.size_label),
        .max_depth = dataset.max_depth,
        .bytes = dataset.bytes,
        .layer = @tagName(layer),
        .samples = layer_samples.times_ms.len,
        .mean_ms = metrics.mean_ms,
        .median_ms = metrics.median_ms,
        .p80_ms = metrics.p80_ms,
        .min_ms = metrics.min_ms,
        .max_ms = metrics.max_ms,
        .mean_peak_kib = peak_metrics.mean_ms,
        .median_peak_kib = peak_metrics.median_ms,
        .p80_peak_kib = peak_metrics.p80_ms,
        .min_peak_kib = peak_metrics.min_ms,
        .max_peak_kib = peak_metrics.max_ms,
        .delta_mean_peak_kib_from_prev = delta_peak_mean,
        .mean_stage_mem_before_kib = stage_mem_before_metrics.mean_ms,
        .mean_stage_mem_after_kib = stage_mem_after_metrics.mean_ms,
        .mean_stage_mem_delta_kib = stage_mem_delta_metrics.mean_ms,
        .mean_stage_peak_increment_kib = stage_peak_increment_metrics.mean_ms,
        .mean_cumulative_pipeline_peak_kib = cumulative_peak_metrics.mean_ms,
        .median_cumulative_pipeline_peak_kib = cumulative_peak_metrics.median_ms,
        .p80_cumulative_pipeline_peak_kib = cumulative_peak_metrics.p80_ms,
        .min_cumulative_pipeline_peak_kib = cumulative_peak_metrics.min_ms,
        .max_cumulative_pipeline_peak_kib = cumulative_peak_metrics.max_ms,
        .delta_mean_cumulative_pipeline_peak_kib_from_prev = delta_cumulative_peak_mean,
        .mean_cumulative_pipeline_peak_over_start_kib = cumulative_peak_over_start_metrics.mean_ms,
        .delta_mean_cumulative_pipeline_peak_over_start_kib_from_prev = delta_cumulative_peak_over_start_mean,
    });
    return peak_metrics.mean_ms;
}

fn benchmarkDataset(
    allocator: std.mem.Allocator,
    rows: *std.array_list.Managed(ResultRow),
    dataset: Dataset,
    warmup: usize,
    samples: usize,
) !void {
    var parse_arena = std.heap.ArenaAllocator.init(allocator);
    defer parse_arena.deinit();
    const parse_alloc = parse_arena.allocator();

    const tokens = try tokenizer._tokenize(parse_alloc, dataset.input);
    const parsed = try ast.parse(parse_alloc, tokens);
    const model = try pcb.PcbFile.loads(parse_alloc, .{ .sexp = parsed });
    const cumulative = try measureCumulativePipelinePeaks(allocator, dataset.input, warmup, samples);
    defer cumulative.deinit(allocator);

    const tokenizer_samples = try measureTokenizer(allocator, dataset.input, warmup, samples);
    defer allocator.free(tokenizer_samples.times_ms);
    defer allocator.free(tokenizer_samples.peak_kib);
    defer allocator.free(tokenizer_samples.mem_before_kib);
    defer allocator.free(tokenizer_samples.mem_after_kib);
    defer allocator.free(tokenizer_samples.mem_delta_kib);
    defer allocator.free(tokenizer_samples.peak_increment_kib);
    _ = try appendLayerResult(allocator, rows, dataset, .tokenizer, tokenizer_samples, cumulative.tokenizer);

    const ast_samples = try measureAst(allocator, tokens, warmup, samples);
    defer allocator.free(ast_samples.times_ms);
    defer allocator.free(ast_samples.peak_kib);
    defer allocator.free(ast_samples.mem_before_kib);
    defer allocator.free(ast_samples.mem_after_kib);
    defer allocator.free(ast_samples.mem_delta_kib);
    defer allocator.free(ast_samples.peak_increment_kib);
    _ = try appendLayerResult(allocator, rows, dataset, .ast, ast_samples, cumulative.ast);

    const parser_samples = try measureParser(allocator, parsed, warmup, samples);
    defer allocator.free(parser_samples.times_ms);
    defer allocator.free(parser_samples.peak_kib);
    defer allocator.free(parser_samples.mem_before_kib);
    defer allocator.free(parser_samples.mem_after_kib);
    defer allocator.free(parser_samples.mem_delta_kib);
    defer allocator.free(parser_samples.peak_increment_kib);
    _ = try appendLayerResult(allocator, rows, dataset, .parser, parser_samples, cumulative.parser);

    const encode_samples = try measureEncode(allocator, model, warmup, samples);
    defer allocator.free(encode_samples.times_ms);
    defer allocator.free(encode_samples.peak_kib);
    defer allocator.free(encode_samples.mem_before_kib);
    defer allocator.free(encode_samples.mem_after_kib);
    defer allocator.free(encode_samples.mem_delta_kib);
    defer allocator.free(encode_samples.peak_increment_kib);
    _ = try appendLayerResult(allocator, rows, dataset, .encode, encode_samples, cumulative.encode);

    const pretty_samples = try measurePretty(allocator, model, warmup, samples);
    defer allocator.free(pretty_samples.times_ms);
    defer allocator.free(pretty_samples.peak_kib);
    defer allocator.free(pretty_samples.mem_before_kib);
    defer allocator.free(pretty_samples.mem_after_kib);
    defer allocator.free(pretty_samples.mem_delta_kib);
    defer allocator.free(pretty_samples.peak_increment_kib);
    _ = try appendLayerResult(allocator, rows, dataset, .pretty, pretty_samples, cumulative.pretty);
}

fn writeOutputJson(
    allocator: std.mem.Allocator,
    output_path: []const u8,
    warmup: usize,
    samples: usize,
    max_size_label: SizeLabel,
    dataset_count: usize,
    rows: []const ResultRow,
) !void {
    if (std.fs.path.dirname(output_path)) |dirname| {
        if (dirname.len > 0) {
            try std.fs.cwd().makePath(dirname);
        }
    }

    const payload = OutputPayload{
        .metadata = .{
            .generated_unix_s = std.time.timestamp(),
            .warmup = warmup,
            .samples = samples,
            .max_size_label = @tagName(max_size_label),
            .dataset_count = dataset_count,
            .row_count = rows.len,
        },
        .rows = rows,
    };

    const file = try std.fs.cwd().createFile(output_path, .{ .truncate = true });
    defer file.close();
    const serialized = try std.fmt.allocPrint(
        allocator,
        "{f}\n",
        .{std.json.fmt(payload, .{ .whitespace = .indent_2 })},
    );
    defer allocator.free(serialized);
    try file.writeAll(serialized);
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const options = parseArgs(allocator) catch |err| {
        printUsage();
        return err;
    };

    const datasets = try makeDatasets(allocator, options.max_size_label);
    defer {
        for (datasets) |dataset| dataset.deinit(allocator);
        allocator.free(datasets);
    }

    var rows = std.array_list.Managed(ResultRow).init(allocator);
    defer rows.deinit();

    for (datasets) |dataset| {
        std.debug.print(
            "Benchmarking {s} ({s}, {s}, {d} bytes, depth {d})\n",
            .{
                dataset.id,
                @tagName(dataset.profile),
                @tagName(dataset.size_label),
                dataset.bytes,
                dataset.max_depth,
            },
        );
        try benchmarkDataset(allocator, &rows, dataset, options.warmup, options.samples);
    }

    try writeOutputJson(
        allocator,
        options.output_json,
        options.warmup,
        options.samples,
        options.max_size_label,
        datasets.len,
        rows.items,
    );

    std.debug.print("Wrote benchmark report to {s}\n", .{options.output_json});
}
