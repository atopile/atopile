const std = @import("std");

const MAX_LIMIT = 128;

const ResistorRow = struct {
    lcsc_id: u32,
    package_id: u16,
    stock: i32,
    is_basic: bool,
    is_preferred: bool,
    resistance_min_ohm: f64,
    resistance_max_ohm: f64,
    tolerance_pct: ?f64,
    max_voltage_v: ?f64,
};

const CapacitorRow = struct {
    lcsc_id: u32,
    package_id: u16,
    stock: i32,
    is_basic: bool,
    is_preferred: bool,
    capacitance_min_f: f64,
    capacitance_max_f: f64,
    tolerance_pct: ?f64,
    max_voltage_v: ?f64,
    tempco_id: u16,
};

const NumericBounds = struct {
    minimum: ?f64 = null,
    maximum: ?f64 = null,
};

const ResistorQuery = struct {
    name: []const u8,
    weight: usize,
    limit: usize,
    package: ?[]const u8 = null,
    resistance: NumericBounds = .{},
    tolerance_pct: NumericBounds = .{},
    max_voltage_v: NumericBounds = .{},
};

const CapacitorQuery = struct {
    name: []const u8,
    weight: usize,
    limit: usize,
    package: ?[]const u8 = null,
    exact_tempco: ?[]const u8 = null,
    capacitance: NumericBounds = .{},
    tolerance_pct: NumericBounds = .{},
    max_voltage_v: NumericBounds = .{},
};

const QueryKind = enum { resistor, capacitor };

const QueryCase = union(QueryKind) {
    resistor: ResistorQuery,
    capacitor: CapacitorQuery,

    pub fn name(self: QueryCase) []const u8 {
        return switch (self) {
            .resistor => |q| q.name,
            .capacitor => |q| q.name,
        };
    }

    pub fn weight(self: QueryCase) usize {
        return switch (self) {
            .resistor => |q| q.weight,
            .capacitor => |q| q.weight,
        };
    }
};

const CASES = [_]QueryCase{
    .{ .resistor = .{
        .name = "r_10k_5pct_pkg",
        .weight = 20,
        .limit = 50,
        .package = "R0402",
        .resistance = .{ .minimum = 9_500.0, .maximum = 10_500.0 },
        .tolerance_pct = .{ .maximum = 5.0 },
    } },
    .{ .resistor = .{
        .name = "r_10k_20pct_pkg",
        .weight = 14,
        .limit = 50,
        .package = "R0402",
        .resistance = .{ .minimum = 8_000.0, .maximum = 12_000.0 },
        .tolerance_pct = .{ .maximum = 20.0 },
    } },
    .{ .resistor = .{
        .name = "r_10k_1pct_unpkg",
        .weight = 8,
        .limit = 50,
        .resistance = .{ .minimum = 9_900.0, .maximum = 10_100.0 },
        .tolerance_pct = .{ .maximum = 1.0 },
    } },
    .{ .resistor = .{
        .name = "r_5k1_1pct_pkg",
        .weight = 6,
        .limit = 30,
        .package = "R0402",
        .resistance = .{ .minimum = 5_050.0, .maximum = 5_150.0 },
        .tolerance_pct = .{ .maximum = 1.0 },
    } },
    .{ .resistor = .{
        .name = "r_120r_1pct_pkg",
        .weight = 5,
        .limit = 30,
        .package = "R0603",
        .resistance = .{ .minimum = 118.0, .maximum = 122.0 },
        .tolerance_pct = .{ .maximum = 1.0 },
    } },
    .{ .resistor = .{
        .name = "r_50k_10pct_unpkg",
        .weight = 4,
        .limit = 30,
        .resistance = .{ .minimum = 45_000.0, .maximum = 55_000.0 },
        .tolerance_pct = .{ .maximum = 10.0 },
    } },
    .{ .capacitor = .{
        .name = "c_100n_20pct_pkg",
        .weight = 20,
        .limit = 50,
        .package = "C0402",
        .exact_tempco = "X7R",
        .capacitance = .{ .minimum = 80e-9, .maximum = 120e-9 },
        .tolerance_pct = .{ .maximum = 20.0 },
        .max_voltage_v = .{ .minimum = 10.0 },
    } },
    .{ .capacitor = .{
        .name = "c_100n_10pct_unpkg",
        .weight = 8,
        .limit = 50,
        .capacitance = .{ .minimum = 90e-9, .maximum = 110e-9 },
        .tolerance_pct = .{ .maximum = 10.0 },
        .max_voltage_v = .{ .minimum = 16.0 },
    } },
    .{ .capacitor = .{
        .name = "c_2u2_20pct_pkg",
        .weight = 10,
        .limit = 40,
        .package = "C0402",
        .exact_tempco = "X5R",
        .capacitance = .{ .minimum = 1.8e-6, .maximum = 2.6e-6 },
        .tolerance_pct = .{ .maximum = 20.0 },
        .max_voltage_v = .{ .minimum = 6.3 },
    } },
    .{ .capacitor = .{
        .name = "c_22pf_5pct_pkg",
        .weight = 4,
        .limit = 20,
        .package = "C0402",
        .exact_tempco = "C0G",
        .capacitance = .{ .minimum = 21e-12, .maximum = 23e-12 },
        .tolerance_pct = .{ .maximum = 5.0 },
        .max_voltage_v = .{ .minimum = 16.0 },
    } },
};

const CliArgs = struct {
    resistors_tsv: []const u8,
    capacitors_tsv: []const u8,
    iterations: usize = 50_000,
    warmup: usize = 5_000,
    seed: u64 = 0,
};

const LatencySummary = struct {
    p50_ms: f64,
    p95_ms: f64,
    p99_ms: f64,
    mean_ms: f64,
};

const CaseSummary = struct {
    name: []const u8,
    component_type: []const u8,
    runs: usize,
    p95_ms: f64,
    avg_candidates: f64,
};

const BenchmarkSummary = struct {
    rows_resistors: usize,
    rows_capacitors: usize,
    iterations: usize,
    warmup_iterations: usize,
    load_time_s: f64,
    index_time_s: f64,
    total_time_s: f64,
    qps: f64,
    overall: LatencySummary,
    per_case: []CaseSummary,
};

const Interner = struct {
    map: std.StringHashMap(u16),
    values: std.ArrayList([]const u8),
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) Interner {
        return .{
            .map = std.StringHashMap(u16).init(allocator),
            .values = std.ArrayList([]const u8).init(allocator),
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Interner) void {
        for (self.values.items) |value| {
            self.allocator.free(value);
        }
        self.map.deinit();
        self.values.deinit();
    }

    pub fn intern(self: *Interner, value: []const u8) !u16 {
        if (self.map.get(value)) |id| return id;
        const owned = try self.allocator.dupe(u8, value);
        const next_id: u16 = @intCast(self.values.items.len + 1);
        try self.values.append(owned);
        try self.map.put(owned, next_id);
        return next_id;
    }

    pub fn get(self: *const Interner, value: []const u8) ?u16 {
        return self.map.get(value);
    }
};

const CaseAccum = struct {
    runs: usize = 0,
    candidate_sum: usize = 0,
    latencies: std.ArrayList(u64),
};

const ResistorTopK = struct {
    limit: usize,
    len: usize = 0,
    items: [MAX_LIMIT]u32 = undefined,

    fn init(limit: usize) ResistorTopK {
        return .{ .limit = @min(limit, MAX_LIMIT) };
    }

    fn consider(self: *ResistorTopK, rows: []const ResistorRow, row_index: u32) void {
        if (self.limit == 0) return;
        if (self.len < self.limit) {
            self.items[self.len] = row_index;
            self.len += 1;
            return;
        }
        var worst_idx: usize = 0;
        var i: usize = 1;
        while (i < self.len) : (i += 1) {
            if (betterResistor(rows, self.items[worst_idx], self.items[i])) {
                worst_idx = i;
            }
        }
        if (betterResistor(rows, row_index, self.items[worst_idx])) {
            self.items[worst_idx] = row_index;
        }
    }

    fn finalize(self: *ResistorTopK, rows: []const ResistorRow) void {
        var i: usize = 1;
        while (i < self.len) : (i += 1) {
            const value = self.items[i];
            var j = i;
            while (j > 0 and betterResistor(rows, value, self.items[j - 1])) : (j -= 1) {
                self.items[j] = self.items[j - 1];
            }
            self.items[j] = value;
        }
    }
};

const CapacitorTopK = struct {
    limit: usize,
    len: usize = 0,
    items: [MAX_LIMIT]u32 = undefined,

    fn init(limit: usize) CapacitorTopK {
        return .{ .limit = @min(limit, MAX_LIMIT) };
    }

    fn consider(self: *CapacitorTopK, rows: []const CapacitorRow, row_index: u32) void {
        if (self.limit == 0) return;
        if (self.len < self.limit) {
            self.items[self.len] = row_index;
            self.len += 1;
            return;
        }
        var worst_idx: usize = 0;
        var i: usize = 1;
        while (i < self.len) : (i += 1) {
            if (betterCapacitor(rows, self.items[worst_idx], self.items[i])) {
                worst_idx = i;
            }
        }
        if (betterCapacitor(rows, row_index, self.items[worst_idx])) {
            self.items[worst_idx] = row_index;
        }
    }

    fn finalize(self: *CapacitorTopK, rows: []const CapacitorRow) void {
        var i: usize = 1;
        while (i < self.len) : (i += 1) {
            const value = self.items[i];
            var j = i;
            while (j > 0 and betterCapacitor(rows, value, self.items[j - 1])) : (j -= 1) {
                self.items[j] = self.items[j - 1];
            }
            self.items[j] = value;
        }
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = try parseCliArgs(allocator);

    var package_interner = Interner.init(allocator);
    defer package_interner.deinit();
    var tempco_interner = Interner.init(allocator);
    defer tempco_interner.deinit();

    const load_start_ns = std.time.nanoTimestamp();
    var resistors = try loadResistors(
        allocator,
        args.resistors_tsv,
        &package_interner,
    );
    defer resistors.deinit();
    var capacitors = try loadCapacitors(
        allocator,
        args.capacitors_tsv,
        &package_interner,
        &tempco_interner,
    );
    defer capacitors.deinit();
    const load_elapsed_ns: i128 = std.time.nanoTimestamp() - load_start_ns;

    const index_start_ns = std.time.nanoTimestamp();
    const resistor_index = try buildResistorIndex(
        allocator,
        resistors.items,
        package_interner.values.items.len,
    );
    defer resistor_index.deinit(allocator);
    const capacitor_index = try buildCapacitorIndex(
        allocator,
        capacitors.items,
        package_interner.values.items.len,
    );
    defer capacitor_index.deinit(allocator);
    const index_elapsed_ns: i128 = std.time.nanoTimestamp() - index_start_ns;

    const summary = try runBenchmark(
        allocator,
        resistors.items,
        capacitors.items,
        resistor_index,
        capacitor_index,
        &package_interner,
        &tempco_interner,
        args.iterations,
        args.warmup,
        args.seed,
    );
    defer allocator.free(summary.per_case);

    const full_summary = BenchmarkSummary{
        .rows_resistors = resistors.items.len,
        .rows_capacitors = capacitors.items.len,
        .iterations = summary.iterations,
        .warmup_iterations = summary.warmup_iterations,
        .load_time_s = @as(f64, @floatFromInt(load_elapsed_ns)) / 1e9,
        .index_time_s = @as(f64, @floatFromInt(index_elapsed_ns)) / 1e9,
        .total_time_s = summary.total_time_s,
        .qps = summary.qps,
        .overall = summary.overall,
        .per_case = summary.per_case,
    };

    try std.json.stringify(full_summary, .{}, std.io.getStdOut().writer());
    try std.io.getStdOut().writer().writeByte('\n');
}

const TableRows = struct {
    items: []ResistorRow,

    fn deinit(self: *TableRows) void {
        self.allocator.free(self.items);
    }
};

const LoadedResistors = struct {
    items: []ResistorRow,
    allocator: std.mem.Allocator,

    fn deinit(self: *LoadedResistors) void {
        self.allocator.free(self.items);
    }
};

const LoadedCapacitors = struct {
    items: []CapacitorRow,
    allocator: std.mem.Allocator,

    fn deinit(self: *LoadedCapacitors) void {
        self.allocator.free(self.items);
    }
};

fn loadResistors(
    allocator: std.mem.Allocator,
    path: []const u8,
    package_interner: *Interner,
) !LoadedResistors {
    const file = try std.fs.cwd().openFile(path, .{ .mode = .read_only });
    defer file.close();

    var buffered = std.io.bufferedReader(file.reader());
    var reader = buffered.reader();
    var rows = std.ArrayList(ResistorRow).init(allocator);
    defer rows.deinit();

    while (try reader.readUntilDelimiterOrEofAlloc(allocator, '\n', 1024 * 1024)) |line| {
        defer allocator.free(line);
        if (line.len == 0) continue;

        var split = std.mem.splitScalar(u8, line, '\t');
        const lcsc_id = try parseU32(requiredField(&split));
        const package = requiredField(&split);
        const stock = try parseI32(requiredField(&split));
        const is_basic = (try parseI32(requiredField(&split))) != 0;
        const is_preferred = (try parseI32(requiredField(&split))) != 0;
        const resistance_min_ohm = try parseF64(requiredField(&split));
        const resistance_max_ohm = try parseF64(requiredField(&split));
        const tolerance_pct = try parseOptionalF64(optionalField(&split));
        _ = optionalField(&split); // max_power_w not used in current benchmark filters
        const max_voltage_v = try parseOptionalF64(optionalField(&split));

        try rows.append(.{
            .lcsc_id = lcsc_id,
            .package_id = try package_interner.intern(package),
            .stock = stock,
            .is_basic = is_basic,
            .is_preferred = is_preferred,
            .resistance_min_ohm = resistance_min_ohm,
            .resistance_max_ohm = resistance_max_ohm,
            .tolerance_pct = tolerance_pct,
            .max_voltage_v = max_voltage_v,
        });
    }

    return .{ .items = try rows.toOwnedSlice(), .allocator = allocator };
}

fn loadCapacitors(
    allocator: std.mem.Allocator,
    path: []const u8,
    package_interner: *Interner,
    tempco_interner: *Interner,
) !LoadedCapacitors {
    const file = try std.fs.cwd().openFile(path, .{ .mode = .read_only });
    defer file.close();

    var buffered = std.io.bufferedReader(file.reader());
    var reader = buffered.reader();
    var rows = std.ArrayList(CapacitorRow).init(allocator);
    defer rows.deinit();

    while (try reader.readUntilDelimiterOrEofAlloc(allocator, '\n', 1024 * 1024)) |line| {
        defer allocator.free(line);
        if (line.len == 0) continue;

        var split = std.mem.splitScalar(u8, line, '\t');
        const lcsc_id = try parseU32(requiredField(&split));
        const package = requiredField(&split);
        const stock = try parseI32(requiredField(&split));
        const is_basic = (try parseI32(requiredField(&split))) != 0;
        const is_preferred = (try parseI32(requiredField(&split))) != 0;
        const capacitance_min_f = try parseF64(requiredField(&split));
        const capacitance_max_f = try parseF64(requiredField(&split));
        const tolerance_pct = try parseOptionalF64(optionalField(&split));
        const max_voltage_v = try parseOptionalF64(optionalField(&split));
        const tempco_raw = optionalField(&split);
        const tempco_id: u16 = if (tempco_raw.len == 0) 0 else try tempco_interner.intern(tempco_raw);

        try rows.append(.{
            .lcsc_id = lcsc_id,
            .package_id = try package_interner.intern(package),
            .stock = stock,
            .is_basic = is_basic,
            .is_preferred = is_preferred,
            .capacitance_min_f = capacitance_min_f,
            .capacitance_max_f = capacitance_max_f,
            .tolerance_pct = tolerance_pct,
            .max_voltage_v = max_voltage_v,
            .tempco_id = tempco_id,
        });
    }

    return .{ .items = try rows.toOwnedSlice(), .allocator = allocator };
}

fn requiredField(split: *std.mem.SplitIterator(u8, .scalar)) []const u8 {
    return split.next() orelse "";
}

fn optionalField(split: *std.mem.SplitIterator(u8, .scalar)) []const u8 {
    return split.next() orelse "";
}

fn parseU32(raw: []const u8) !u32 {
    return try std.fmt.parseInt(u32, raw, 10);
}

fn parseI32(raw: []const u8) !i32 {
    return try std.fmt.parseInt(i32, raw, 10);
}

fn parseF64(raw: []const u8) !f64 {
    return try std.fmt.parseFloat(f64, raw);
}

fn parseOptionalF64(raw: []const u8) !?f64 {
    if (raw.len == 0) return null;
    return try std.fmt.parseFloat(f64, raw);
}

const ResistorIndex = struct {
    all_sorted: []u32,
    by_package: []std.ArrayList(u32),

    fn deinit(self: ResistorIndex, allocator: std.mem.Allocator) void {
        allocator.free(self.all_sorted);
        for (self.by_package) |list| {
            list.deinit();
        }
        allocator.free(self.by_package);
    }
};

const CapacitorIndex = struct {
    all_sorted: []u32,
    by_package: []std.ArrayList(u32),

    fn deinit(self: CapacitorIndex, allocator: std.mem.Allocator) void {
        allocator.free(self.all_sorted);
        for (self.by_package) |list| {
            list.deinit();
        }
        allocator.free(self.by_package);
    }
};

fn buildResistorIndex(
    allocator: std.mem.Allocator,
    rows: []const ResistorRow,
    package_count: usize,
) !ResistorIndex {
    const all_sorted = try allocator.alloc(u32, rows.len);
    for (all_sorted, 0..) |*slot, idx| {
        slot.* = @intCast(idx);
    }
    std.sort.block(u32, all_sorted, rows, lessResistorMin);

    const by_package = try allocator.alloc(std.ArrayList(u32), package_count + 1);
    for (by_package) |*list| {
        list.* = std.ArrayList(u32).init(allocator);
    }
    for (rows, 0..) |row, idx| {
        try by_package[row.package_id].append(@intCast(idx));
    }
    for (by_package) |*list| {
        if (list.items.len > 1) {
            std.sort.block(u32, list.items, rows, lessResistorMin);
        }
    }

    return .{
        .all_sorted = all_sorted,
        .by_package = by_package,
    };
}

fn buildCapacitorIndex(
    allocator: std.mem.Allocator,
    rows: []const CapacitorRow,
    package_count: usize,
) !CapacitorIndex {
    const all_sorted = try allocator.alloc(u32, rows.len);
    for (all_sorted, 0..) |*slot, idx| {
        slot.* = @intCast(idx);
    }
    std.sort.block(u32, all_sorted, rows, lessCapacitorMin);

    const by_package = try allocator.alloc(std.ArrayList(u32), package_count + 1);
    for (by_package) |*list| {
        list.* = std.ArrayList(u32).init(allocator);
    }
    for (rows, 0..) |row, idx| {
        try by_package[row.package_id].append(@intCast(idx));
    }
    for (by_package) |*list| {
        if (list.items.len > 1) {
            std.sort.block(u32, list.items, rows, lessCapacitorMin);
        }
    }

    return .{
        .all_sorted = all_sorted,
        .by_package = by_package,
    };
}

fn lessResistorMin(rows: []const ResistorRow, lhs: u32, rhs: u32) bool {
    return rows[lhs].resistance_min_ohm < rows[rhs].resistance_min_ohm;
}

fn lessCapacitorMin(rows: []const CapacitorRow, lhs: u32, rhs: u32) bool {
    return rows[lhs].capacitance_min_f < rows[rhs].capacitance_min_f;
}

fn betterResistor(rows: []const ResistorRow, lhs: u32, rhs: u32) bool {
    const a = rows[lhs];
    const b = rows[rhs];
    if (a.is_preferred != b.is_preferred) return a.is_preferred;
    if (a.is_basic != b.is_basic) return a.is_basic;
    if (a.stock != b.stock) return a.stock > b.stock;
    return a.lcsc_id < b.lcsc_id;
}

fn betterCapacitor(rows: []const CapacitorRow, lhs: u32, rhs: u32) bool {
    const a = rows[lhs];
    const b = rows[rhs];
    if (a.is_preferred != b.is_preferred) return a.is_preferred;
    if (a.is_basic != b.is_basic) return a.is_basic;
    if (a.stock != b.stock) return a.stock > b.stock;
    return a.lcsc_id < b.lcsc_id;
}

fn lowerBoundResistor(indices: []const u32, rows: []const ResistorRow, value: f64) usize {
    var lo: usize = 0;
    var hi: usize = indices.len;
    while (lo < hi) {
        const mid = lo + (hi - lo) / 2;
        if (rows[indices[mid]].resistance_min_ohm < value) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    return lo;
}

fn lowerBoundCapacitor(indices: []const u32, rows: []const CapacitorRow, value: f64) usize {
    var lo: usize = 0;
    var hi: usize = indices.len;
    while (lo < hi) {
        const mid = lo + (hi - lo) / 2;
        if (rows[indices[mid]].capacitance_min_f < value) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    return lo;
}

const CoreSummary = struct {
    iterations: usize,
    warmup_iterations: usize,
    total_time_s: f64,
    qps: f64,
    overall: LatencySummary,
    per_case: []CaseSummary,
};

fn runBenchmark(
    allocator: std.mem.Allocator,
    resistors: []const ResistorRow,
    capacitors: []const CapacitorRow,
    resistor_index: ResistorIndex,
    capacitor_index: CapacitorIndex,
    package_interner: *const Interner,
    tempco_interner: *const Interner,
    iterations: usize,
    warmup: usize,
    seed: u64,
) !CoreSummary {
    var weighted_cases = std.ArrayList(usize).init(allocator);
    defer weighted_cases.deinit();

    for (CASES, 0..) |query_case, idx| {
        const weight = query_case.weight();
        var i: usize = 0;
        while (i < weight) : (i += 1) {
            try weighted_cases.append(idx);
        }
    }

    var rng = std.Random.DefaultPrng.init(seed);
    const random = rng.random();

    var warmup_count: usize = 0;
    while (warmup_count < warmup) : (warmup_count += 1) {
        const case_idx = weighted_cases.items[random.uintLessThan(usize, weighted_cases.items.len)];
        _ = executeCase(
            CASES[case_idx],
            resistors,
            capacitors,
            resistor_index,
            capacitor_index,
            package_interner,
            tempco_interner,
        );
    }

    var all_latencies = std.ArrayList(u64).init(allocator);
    defer all_latencies.deinit();

    var case_accum = try allocator.alloc(CaseAccum, CASES.len);
    defer {
        for (case_accum) |*acc| {
            acc.latencies.deinit();
        }
        allocator.free(case_accum);
    }
    for (case_accum) |*acc| {
        acc.* = .{
            .runs = 0,
            .candidate_sum = 0,
            .latencies = std.ArrayList(u64).init(allocator),
        };
    }

    const total_start_ns = std.time.nanoTimestamp();
    var iter: usize = 0;
    while (iter < iterations) : (iter += 1) {
        const case_idx = weighted_cases.items[random.uintLessThan(usize, weighted_cases.items.len)];
        const start_ns = std.time.nanoTimestamp();
        const count = executeCase(
            CASES[case_idx],
            resistors,
            capacitors,
            resistor_index,
            capacitor_index,
            package_interner,
            tempco_interner,
        );
        const elapsed_ns: u64 = @intCast(std.time.nanoTimestamp() - start_ns);
        try all_latencies.append(elapsed_ns);
        try case_accum[case_idx].latencies.append(elapsed_ns);
        case_accum[case_idx].runs += 1;
        case_accum[case_idx].candidate_sum += count;
    }
    const total_elapsed_ns: i128 = std.time.nanoTimestamp() - total_start_ns;

    const overall = summarizeLatencies(all_latencies.items);
    const total_time_s = @as(f64, @floatFromInt(total_elapsed_ns)) / 1e9;
    const qps = if (total_time_s > 0.0)
        @as(f64, @floatFromInt(iterations)) / total_time_s
    else
        0.0;

    var per_case = try allocator.alloc(CaseSummary, CASES.len);
    for (CASES, 0..) |query_case, idx| {
        const lat = case_accum[idx].latencies.items;
        const stats = summarizeLatencies(lat);
        const avg_candidates = if (case_accum[idx].runs == 0)
            0.0
        else
            @as(f64, @floatFromInt(case_accum[idx].candidate_sum)) /
                @as(f64, @floatFromInt(case_accum[idx].runs));
        per_case[idx] = .{
            .name = query_case.name(),
            .component_type = switch (query_case) {
                .resistor => "resistor",
                .capacitor => "capacitor",
            },
            .runs = case_accum[idx].runs,
            .p95_ms = stats.p95_ms,
            .avg_candidates = avg_candidates,
        };
    }

    return .{
        .iterations = iterations,
        .warmup_iterations = warmup,
        .total_time_s = total_time_s,
        .qps = qps,
        .overall = overall,
        .per_case = per_case,
    };
}

fn executeCase(
    query_case: QueryCase,
    resistors: []const ResistorRow,
    capacitors: []const CapacitorRow,
    resistor_index: ResistorIndex,
    capacitor_index: CapacitorIndex,
    package_interner: *const Interner,
    tempco_interner: *const Interner,
) usize {
    return switch (query_case) {
        .resistor => |query| executeResistorQuery(
            query,
            resistors,
            resistor_index,
            package_interner,
        ),
        .capacitor => |query| executeCapacitorQuery(
            query,
            capacitors,
            capacitor_index,
            package_interner,
            tempco_interner,
        ),
    };
}

fn executeResistorQuery(
    query: ResistorQuery,
    rows: []const ResistorRow,
    index: ResistorIndex,
    package_interner: *const Interner,
) usize {
    const package_id: ?u16 = if (query.package) |raw| package_interner.get(raw) else null;
    const indices: []const u32 = if (package_id) |id|
        if (id < index.by_package.len) index.by_package[id].items else &[_]u32{}
    else
        index.all_sorted;
    if (indices.len == 0) return 0;

    const start_idx: usize = if (query.resistance.minimum) |min_v|
        lowerBoundResistor(indices, rows, min_v)
    else
        0;
    var topk = ResistorTopK.init(query.limit);
    var i = start_idx;
    while (i < indices.len) : (i += 1) {
        const row = rows[indices[i]];
        if (query.resistance.maximum) |max_v| {
            if (row.resistance_min_ohm > max_v) break;
            if (row.resistance_max_ohm > max_v) continue;
        }
        if (query.resistance.minimum) |min_v| {
            if (row.resistance_min_ohm < min_v) continue;
        }
        if (query.tolerance_pct.maximum) |tol_max| {
            if (row.tolerance_pct == null) continue;
            if (row.tolerance_pct.? > tol_max) continue;
        }
        if (query.max_voltage_v.minimum) |vmin| {
            if (row.max_voltage_v == null) continue;
            if (row.max_voltage_v.? < vmin) continue;
        }
        if (row.stock < 1) continue;
        topk.consider(rows, indices[i]);
    }
    topk.finalize(rows);
    return topk.len;
}

fn executeCapacitorQuery(
    query: CapacitorQuery,
    rows: []const CapacitorRow,
    index: CapacitorIndex,
    package_interner: *const Interner,
    tempco_interner: *const Interner,
) usize {
    const package_id: ?u16 = if (query.package) |raw| package_interner.get(raw) else null;
    const tempco_id: ?u16 = if (query.exact_tempco) |raw| tempco_interner.get(raw) else null;
    const indices: []const u32 = if (package_id) |id|
        if (id < index.by_package.len) index.by_package[id].items else &[_]u32{}
    else
        index.all_sorted;
    if (indices.len == 0) return 0;

    const start_idx: usize = if (query.capacitance.minimum) |min_v|
        lowerBoundCapacitor(indices, rows, min_v)
    else
        0;
    var topk = CapacitorTopK.init(query.limit);
    var i = start_idx;
    while (i < indices.len) : (i += 1) {
        const row = rows[indices[i]];
        if (query.capacitance.maximum) |max_v| {
            if (row.capacitance_min_f > max_v) break;
            if (row.capacitance_max_f > max_v) continue;
        }
        if (query.capacitance.minimum) |min_v| {
            if (row.capacitance_min_f < min_v) continue;
        }
        if (query.tolerance_pct.maximum) |tol_max| {
            if (row.tolerance_pct == null) continue;
            if (row.tolerance_pct.? > tol_max) continue;
        }
        if (query.max_voltage_v.minimum) |vmin| {
            if (row.max_voltage_v == null) continue;
            if (row.max_voltage_v.? < vmin) continue;
        }
        if (tempco_id) |tid| {
            if (row.tempco_id != tid) continue;
        }
        if (row.stock < 1) continue;
        topk.consider(rows, indices[i]);
    }
    topk.finalize(rows);
    return topk.len;
}

fn summarizeLatencies(latencies_ns: []u64) LatencySummary {
    if (latencies_ns.len == 0) {
        return .{ .p50_ms = 0.0, .p95_ms = 0.0, .p99_ms = 0.0, .mean_ms = 0.0 };
    }
    const scratch = std.heap.page_allocator.alloc(u64, latencies_ns.len) catch @panic("OOM");
    defer std.heap.page_allocator.free(scratch);
    @memcpy(scratch, latencies_ns);
    std.sort.block(u64, scratch, {}, lessU64);

    var sum: u128 = 0;
    for (latencies_ns) |value| sum += value;
    const mean_ms = (@as(f64, @floatFromInt(sum)) /
        @as(f64, @floatFromInt(latencies_ns.len))) / 1e6;
    return .{
        .p50_ms = percentileMs(scratch, 50.0),
        .p95_ms = percentileMs(scratch, 95.0),
        .p99_ms = percentileMs(scratch, 99.0),
        .mean_ms = mean_ms,
    };
}

fn lessU64(_: void, lhs: u64, rhs: u64) bool {
    return lhs < rhs;
}

fn percentileMs(sorted_ns: []const u64, pct: f64) f64 {
    if (sorted_ns.len == 0) return 0.0;
    const len_minus_one = @as(f64, @floatFromInt(sorted_ns.len - 1));
    const rank = len_minus_one * (pct / 100.0);
    const lo: usize = @intFromFloat(@floor(rank));
    const hi: usize = @min(lo + 1, sorted_ns.len - 1);
    const frac = rank - @as(f64, @floatFromInt(lo));
    const lo_v = @as(f64, @floatFromInt(sorted_ns[lo]));
    const hi_v = @as(f64, @floatFromInt(sorted_ns[hi]));
    const value_ns = lo_v * (1.0 - frac) + hi_v * frac;
    return value_ns / 1e6;
}

fn parseCliArgs(allocator: std.mem.Allocator) !CliArgs {
    var args = try std.process.argsWithAllocator(allocator);
    defer args.deinit();

    _ = args.next();
    var out = CliArgs{
        .resistors_tsv = "",
        .capacitors_tsv = "",
    };

    while (args.next()) |arg| {
        if (std.mem.eql(u8, arg, "--resistors-tsv")) {
            out.resistors_tsv = args.next() orelse return error.InvalidArgument;
            continue;
        }
        if (std.mem.eql(u8, arg, "--capacitors-tsv")) {
            out.capacitors_tsv = args.next() orelse return error.InvalidArgument;
            continue;
        }
        if (std.mem.eql(u8, arg, "--iterations")) {
            const raw = args.next() orelse return error.InvalidArgument;
            out.iterations = try std.fmt.parseInt(usize, raw, 10);
            continue;
        }
        if (std.mem.eql(u8, arg, "--warmup")) {
            const raw = args.next() orelse return error.InvalidArgument;
            out.warmup = try std.fmt.parseInt(usize, raw, 10);
            continue;
        }
        if (std.mem.eql(u8, arg, "--seed")) {
            const raw = args.next() orelse return error.InvalidArgument;
            out.seed = try std.fmt.parseInt(u64, raw, 10);
            continue;
        }
        return error.InvalidArgument;
    }

    if (out.resistors_tsv.len == 0 or out.capacitors_tsv.len == 0) {
        return error.InvalidArgument;
    }
    return out;
}
