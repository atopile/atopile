const std = @import("std");

const MAX_LIMIT = 512;

const ColumnSchema = struct {
    name: []const u8,
    kind: []const u8,
};

const RangeBoundSchema = struct {
    field: []const u8,
    min_field: []const u8,
    max_field: []const u8,
};

const ComponentSchema = struct {
    component_type: []const u8,
    tsv: []const u8,
    columns: []const ColumnSchema,
    range_bounds: ?[]const RangeBoundSchema = null,
};

const SchemaFile = struct {
    components: []const ComponentSchema,
};

const ExactFilter = struct {
    field: []const u8,
    number_value: ?f64 = null,
    string_value: ?[]const u8 = null,
};

const RangeFilter = struct {
    field: []const u8,
    minimum: ?f64 = null,
    maximum: ?f64 = null,
};

const RequestPayload = struct {
    component_type: []const u8,
    qty: i32 = 1,
    limit: usize = 50,
    package: ?[]const u8 = null,
    exact_filters: ?[]const ExactFilter = null,
    range_filters: ?[]const RangeFilter = null,
};

const ErrorResponse = struct {
    ok: bool = false,
    @"error": []const u8,
    error_type: []const u8,
};

const CliArgs = struct {
    schema_path: []const u8,
};

const CoreRow = struct {
    lcsc_id: u32,
    stock: i32,
    is_basic: bool,
    is_preferred: bool,
    package_id: u16,
};

const NumericKind = enum {
    integer,
    real,
};

const NumericColumn = struct {
    name: []const u8,
    kind: NumericKind,
    values: []f64,
};

const TextColumn = struct {
    name: []const u8,
    values: []u16,
};

const RangeBound = struct {
    field: []const u8,
    min_numeric_idx: usize,
    max_numeric_idx: usize,
};

const Dataset = struct {
    component_type: []const u8,
    rows: []CoreRow,
    numeric_columns: []NumericColumn,
    text_columns: []TextColumn,
    range_bounds: []RangeBound,
    by_package: std.ArrayList(std.ArrayList(u32)),
    allocator: std.mem.Allocator,

    fn deinit(self: *Dataset) void {
        self.allocator.free(self.rows);
        for (self.numeric_columns) |column| {
            self.allocator.free(column.values);
        }
        self.allocator.free(self.numeric_columns);
        for (self.text_columns) |column| {
            self.allocator.free(column.values);
        }
        self.allocator.free(self.text_columns);
        self.allocator.free(self.range_bounds);
        for (self.by_package.items) |*list| {
            list.deinit();
        }
        self.by_package.deinit();
    }

    fn findNumericColumn(self: *const Dataset, name: []const u8) ?usize {
        for (self.numeric_columns, 0..) |column, idx| {
            if (std.mem.eql(u8, column.name, name)) return idx;
        }
        return null;
    }

    fn findTextColumn(self: *const Dataset, name: []const u8) ?usize {
        for (self.text_columns, 0..) |column, idx| {
            if (std.mem.eql(u8, column.name, name)) return idx;
        }
        return null;
    }

    fn findRangeBound(self: *const Dataset, field: []const u8) ?RangeBound {
        for (self.range_bounds) |bound| {
            if (std.mem.eql(u8, bound.field, field)) return bound;
        }
        return null;
    }
};

const Interner = struct {
    map: std.StringHashMap(u16),
    values: std.ArrayList([]const u8),
    allocator: std.mem.Allocator,

    fn init(allocator: std.mem.Allocator) Interner {
        return .{
            .map = std.StringHashMap(u16).init(allocator),
            .values = std.ArrayList([]const u8).init(allocator),
            .allocator = allocator,
        };
    }

    fn deinit(self: *Interner) void {
        for (self.values.items) |value| {
            self.allocator.free(value);
        }
        self.map.deinit();
        self.values.deinit();
    }

    fn intern(self: *Interner, value: []const u8) !u16 {
        if (self.map.get(value)) |existing| return existing;
        const owned = try self.allocator.dupe(u8, value);
        const id: u16 = @intCast(self.values.items.len + 1);
        try self.values.append(owned);
        try self.map.put(owned, id);
        return id;
    }

    fn get(self: *const Interner, value: []const u8) ?u16 {
        return self.map.get(value);
    }

    fn valueById(self: *const Interner, id: u16) []const u8 {
        if (id == 0) return "";
        const index: usize = @intCast(id - 1);
        if (index >= self.values.items.len) return "";
        return self.values.items[index];
    }
};

const ResolvedExact = union(enum) {
    numeric: struct {
        column_idx: usize,
        value: f64,
    },
    text: struct {
        column_idx: usize,
        value_id: u16,
    },
};

const ResolvedRange = struct {
    min_column_idx: usize,
    max_column_idx: usize,
    minimum: ?f64,
    maximum: ?f64,
};

const GenericTopK = struct {
    limit: usize,
    len: usize = 0,
    items: [MAX_LIMIT]u32 = undefined,

    fn init(limit: usize) GenericTopK {
        return .{ .limit = @min(limit, MAX_LIMIT) };
    }

    fn consider(self: *GenericTopK, rows: []const CoreRow, row_index: u32) void {
        if (self.limit == 0) return;
        if (self.len < self.limit) {
            self.items[self.len] = row_index;
            self.len += 1;
            return;
        }
        var worst: usize = 0;
        var i: usize = 1;
        while (i < self.len) : (i += 1) {
            if (betterRow(rows, self.items[worst], self.items[i])) {
                worst = i;
            }
        }
        if (betterRow(rows, row_index, self.items[worst])) {
            self.items[worst] = row_index;
        }
    }

    fn finalize(self: *GenericTopK, rows: []const CoreRow) void {
        var i: usize = 1;
        while (i < self.len) : (i += 1) {
            const value = self.items[i];
            var j = i;
            while (j > 0 and betterRow(rows, value, self.items[j - 1])) : (j -= 1) {
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

    const schema_bytes = try std.fs.cwd().readFileAlloc(allocator, args.schema_path, 64 * 1024 * 1024);
    defer allocator.free(schema_bytes);

    var parsed_schema = try std.json.parseFromSlice(SchemaFile, allocator, schema_bytes, .{});
    defer parsed_schema.deinit();

    var package_interner = Interner.init(allocator);
    defer package_interner.deinit();
    var text_interner = Interner.init(allocator);
    defer text_interner.deinit();

    const schema = parsed_schema.value;
    var datasets = try allocator.alloc(Dataset, schema.components.len);
    defer allocator.free(datasets);
    for (schema.components, 0..) |component_schema, idx| {
        datasets[idx] = try loadDataset(
            allocator,
            component_schema,
            &package_interner,
            &text_interner,
        );
    }
    defer {
        for (datasets) |*dataset| {
            dataset.deinit();
        }
    }

    var stdout_buffer = std.io.bufferedWriter(std.io.getStdOut().writer());
    const out = stdout_buffer.writer();
    var stdin_buffer = std.io.bufferedReader(std.io.getStdIn().reader());
    var in = stdin_buffer.reader();

    while (true) {
        const maybe_line = try in.readUntilDelimiterOrEofAlloc(allocator, '\n', 8 * 1024 * 1024);
        if (maybe_line == null) break;
        const line = maybe_line.?;
        defer allocator.free(line);
        if (line.len == 0) continue;

        var arena = std.heap.ArenaAllocator.init(allocator);
        defer arena.deinit();
        const request_alloc = arena.allocator();

        const parsed_request = std.json.parseFromSlice(RequestPayload, request_alloc, line, .{}) catch {
            try writeError(out, "invalid request json", "validation");
            try stdout_buffer.flush();
            continue;
        };
        defer parsed_request.deinit();
        const req = parsed_request.value;

        const dataset = findDataset(datasets, req.component_type) orelse {
            try writeError(out, "unsupported component_type", "validation");
            try stdout_buffer.flush();
            continue;
        };

        var candidate_indices: [MAX_LIMIT]u32 = undefined;
        const query_count = executeQuery(
            request_alloc,
            dataset,
            req,
            &package_interner,
            &text_interner,
            &candidate_indices,
        ) catch |err| {
            if (err == error.Validation) {
                try writeError(out, "invalid query filters", "validation");
            } else {
                try writeError(out, "query execution failed", "internal");
            }
            try stdout_buffer.flush();
            continue;
        };

        try writeSuccessResponse(
            out,
            dataset,
            candidate_indices[0..query_count],
            &package_interner,
            &text_interner,
        );
        try stdout_buffer.flush();
    }
}

fn parseCliArgs(allocator: std.mem.Allocator) !CliArgs {
    var args = try std.process.argsWithAllocator(allocator);
    defer args.deinit();

    _ = args.next();
    var out = CliArgs{ .schema_path = "" };
    while (args.next()) |arg| {
        if (std.mem.eql(u8, arg, "--schema")) {
            out.schema_path = args.next() orelse return error.InvalidArgument;
            continue;
        }
        return error.InvalidArgument;
    }
    if (out.schema_path.len == 0) return error.InvalidArgument;
    return out;
}

fn findDataset(datasets: []Dataset, component_type: []const u8) ?*Dataset {
    for (datasets) |*dataset| {
        if (std.mem.eql(u8, dataset.component_type, component_type)) return dataset;
    }
    return null;
}

fn loadDataset(
    allocator: std.mem.Allocator,
    schema: ComponentSchema,
    package_interner: *Interner,
    text_interner: *Interner,
) !Dataset {
    const core_indexes = try resolveCoreIndexes(schema.columns);
    var numeric_specs = std.ArrayList(struct {
        schema_idx: usize,
        name: []const u8,
        kind: NumericKind,
    }).init(allocator);
    defer numeric_specs.deinit();

    var text_specs = std.ArrayList(struct {
        schema_idx: usize,
        name: []const u8,
    }).init(allocator);
    defer text_specs.deinit();

    for (schema.columns, 0..) |column, schema_idx| {
        if (schema_idx == core_indexes.lcsc_id or
            schema_idx == core_indexes.package or
            schema_idx == core_indexes.stock or
            schema_idx == core_indexes.is_basic or
            schema_idx == core_indexes.is_preferred)
        {
            continue;
        }
        if (std.mem.eql(u8, column.kind, "text")) {
            try text_specs.append(.{
                .schema_idx = schema_idx,
                .name = column.name,
            });
            continue;
        }
        const kind: NumericKind = if (std.mem.eql(u8, column.kind, "int"))
            .integer
        else if (std.mem.eql(u8, column.kind, "real"))
            .real
        else
            return error.InvalidSchema;
        try numeric_specs.append(.{
            .schema_idx = schema_idx,
            .name = column.name,
            .kind = kind,
        });
    }

    const row_count = try countTsvRows(allocator, schema.tsv);
    var rows = try allocator.alloc(CoreRow, row_count);

    var numeric_columns = try allocator.alloc(NumericColumn, numeric_specs.items.len);
    for (numeric_specs.items, 0..) |spec, idx| {
        const values = try allocator.alloc(f64, row_count);
        for (values) |*slot| {
            slot.* = std.math.nan(f64);
        }
        numeric_columns[idx] = .{
            .name = spec.name,
            .kind = spec.kind,
            .values = values,
        };
    }

    var text_columns = try allocator.alloc(TextColumn, text_specs.items.len);
    for (text_specs.items, 0..) |spec, idx| {
        const values = try allocator.alloc(u16, row_count);
        @memset(values, 0);
        text_columns[idx] = .{
            .name = spec.name,
            .values = values,
        };
    }

    var by_package = std.ArrayList(std.ArrayList(u32)).init(allocator);

    const file = try std.fs.cwd().openFile(schema.tsv, .{ .mode = .read_only });
    defer file.close();
    var buffered = std.io.bufferedReader(file.reader());
    var reader = buffered.reader();

    var row_idx: usize = 0;
    while (try reader.readUntilDelimiterOrEofAlloc(allocator, '\n', 1024 * 1024)) |line| {
        defer allocator.free(line);
        if (line.len == 0) continue;
        var split = std.mem.splitScalar(u8, line, '\t');

        var fields = try allocator.alloc([]const u8, schema.columns.len);
        defer allocator.free(fields);
        var i: usize = 0;
        while (i < schema.columns.len) : (i += 1) {
            fields[i] = split.next() orelse "";
        }
        if (split.next() != null) return error.InvalidSchema;

        const lcsc_id = try parseU32(fields[core_indexes.lcsc_id]);
        const package = fields[core_indexes.package];
        const stock = try parseI32(fields[core_indexes.stock]);
        const is_basic = (try parseI32(fields[core_indexes.is_basic])) != 0;
        const is_preferred = (try parseI32(fields[core_indexes.is_preferred])) != 0;

        const package_id = try package_interner.intern(package);
        try ensurePackageLists(&by_package, allocator, package_id);
        try by_package.items[package_id].append(@intCast(row_idx));

        rows[row_idx] = .{
            .lcsc_id = lcsc_id,
            .stock = stock,
            .is_basic = is_basic,
            .is_preferred = is_preferred,
            .package_id = package_id,
        };

        for (numeric_specs.items, 0..) |spec, numeric_idx| {
            const raw = fields[spec.schema_idx];
            if (raw.len == 0) {
                numeric_columns[numeric_idx].values[row_idx] = std.math.nan(f64);
                continue;
            }
            numeric_columns[numeric_idx].values[row_idx] = switch (spec.kind) {
                .integer => @floatFromInt(try std.fmt.parseInt(i64, raw, 10)),
                .real => try std.fmt.parseFloat(f64, raw),
            };
        }

        for (text_specs.items, 0..) |spec, text_idx| {
            const raw = fields[spec.schema_idx];
            if (raw.len == 0) {
                text_columns[text_idx].values[row_idx] = 0;
                continue;
            }
            text_columns[text_idx].values[row_idx] = try text_interner.intern(raw);
        }

        row_idx += 1;
    }
    if (row_idx != row_count) return error.InvalidSchema;

    const range_bounds = try buildRangeBounds(allocator, schema, numeric_columns);

    return .{
        .component_type = schema.component_type,
        .rows = rows,
        .numeric_columns = numeric_columns,
        .text_columns = text_columns,
        .range_bounds = range_bounds,
        .by_package = by_package,
        .allocator = allocator,
    };
}

const CoreIndexes = struct {
    lcsc_id: usize,
    package: usize,
    stock: usize,
    is_basic: usize,
    is_preferred: usize,
};

fn resolveCoreIndexes(columns: []const ColumnSchema) !CoreIndexes {
    var out = CoreIndexes{
        .lcsc_id = std.math.maxInt(usize),
        .package = std.math.maxInt(usize),
        .stock = std.math.maxInt(usize),
        .is_basic = std.math.maxInt(usize),
        .is_preferred = std.math.maxInt(usize),
    };
    for (columns, 0..) |column, idx| {
        if (std.mem.eql(u8, column.name, "lcsc_id")) out.lcsc_id = idx;
        if (std.mem.eql(u8, column.name, "package")) out.package = idx;
        if (std.mem.eql(u8, column.name, "stock")) out.stock = idx;
        if (std.mem.eql(u8, column.name, "is_basic")) out.is_basic = idx;
        if (std.mem.eql(u8, column.name, "is_preferred")) out.is_preferred = idx;
    }
    if (out.lcsc_id == std.math.maxInt(usize) or
        out.package == std.math.maxInt(usize) or
        out.stock == std.math.maxInt(usize) or
        out.is_basic == std.math.maxInt(usize) or
        out.is_preferred == std.math.maxInt(usize))
    {
        return error.InvalidSchema;
    }
    return out;
}

fn countTsvRows(allocator: std.mem.Allocator, path: []const u8) !usize {
    const file = try std.fs.cwd().openFile(path, .{ .mode = .read_only });
    defer file.close();
    var buffered = std.io.bufferedReader(file.reader());
    var reader = buffered.reader();

    var count: usize = 0;
    while (try reader.readUntilDelimiterOrEofAlloc(allocator, '\n', 1024 * 1024)) |line| {
        defer allocator.free(line);
        if (line.len == 0) continue;
        count += 1;
    }
    return count;
}

fn ensurePackageLists(
    lists: *std.ArrayList(std.ArrayList(u32)),
    allocator: std.mem.Allocator,
    package_id: u16,
) !void {
    while (lists.items.len <= package_id) {
        try lists.append(std.ArrayList(u32).init(allocator));
    }
}

fn buildRangeBounds(
    allocator: std.mem.Allocator,
    schema: ComponentSchema,
    numeric_columns: []const NumericColumn,
) ![]RangeBound {
    if (schema.range_bounds == null) {
        return try allocator.alloc(RangeBound, 0);
    }
    const raw_bounds = schema.range_bounds.?;
    var out = try allocator.alloc(RangeBound, raw_bounds.len);
    for (raw_bounds, 0..) |bound, idx| {
        const min_idx = findNumericColumnByName(numeric_columns, bound.min_field) orelse return error.InvalidSchema;
        const max_idx = findNumericColumnByName(numeric_columns, bound.max_field) orelse return error.InvalidSchema;
        out[idx] = .{
            .field = bound.field,
            .min_numeric_idx = min_idx,
            .max_numeric_idx = max_idx,
        };
    }
    return out;
}

fn findNumericColumnByName(columns: []const NumericColumn, name: []const u8) ?usize {
    for (columns, 0..) |column, idx| {
        if (std.mem.eql(u8, column.name, name)) return idx;
    }
    return null;
}

fn parseU32(raw: []const u8) !u32 {
    return try std.fmt.parseInt(u32, raw, 10);
}

fn parseI32(raw: []const u8) !i32 {
    return try std.fmt.parseInt(i32, raw, 10);
}

fn betterRow(rows: []const CoreRow, lhs: u32, rhs: u32) bool {
    const a = rows[lhs];
    const b = rows[rhs];
    if (a.is_preferred != b.is_preferred) return a.is_preferred;
    if (a.is_basic != b.is_basic) return a.is_basic;
    if (a.stock != b.stock) return a.stock > b.stock;
    return a.lcsc_id < b.lcsc_id;
}

fn executeQuery(
    allocator: std.mem.Allocator,
    dataset: *const Dataset,
    req: RequestPayload,
    package_interner: *const Interner,
    text_interner: *const Interner,
    out_indices: *[MAX_LIMIT]u32,
) !usize {
    const limit = @min(req.limit, MAX_LIMIT);
    var topk = GenericTopK.init(limit);

    var resolved_exact = std.ArrayList(ResolvedExact).init(allocator);
    defer resolved_exact.deinit();
    if (req.exact_filters) |filters| {
        for (filters) |filter| {
            if (dataset.findTextColumn(filter.field)) |text_idx| {
                const value = filter.string_value orelse return error.Validation;
                const value_id = text_interner.get(value) orelse 0;
                try resolved_exact.append(.{ .text = .{
                    .column_idx = text_idx,
                    .value_id = value_id,
                } });
                continue;
            }
            if (dataset.findNumericColumn(filter.field)) |numeric_idx| {
                const value = filter.number_value orelse return error.Validation;
                try resolved_exact.append(.{ .numeric = .{
                    .column_idx = numeric_idx,
                    .value = value,
                } });
                continue;
            }
            return error.Validation;
        }
    }

    var resolved_ranges = std.ArrayList(ResolvedRange).init(allocator);
    defer resolved_ranges.deinit();
    if (req.range_filters) |filters| {
        for (filters) |filter| {
            if (dataset.findRangeBound(filter.field)) |bound| {
                try resolved_ranges.append(.{
                    .min_column_idx = bound.min_numeric_idx,
                    .max_column_idx = bound.max_numeric_idx,
                    .minimum = filter.minimum,
                    .maximum = filter.maximum,
                });
                continue;
            }
            const numeric_idx = dataset.findNumericColumn(filter.field) orelse return error.Validation;
            try resolved_ranges.append(.{
                .min_column_idx = numeric_idx,
                .max_column_idx = numeric_idx,
                .minimum = filter.minimum,
                .maximum = filter.maximum,
            });
        }
    }

    if (req.package) |package| {
        const package_id = package_interner.get(package) orelse {
            return 0;
        };
        if (package_id >= dataset.by_package.items.len) {
            return 0;
        }
        for (dataset.by_package.items[package_id].items) |row_idx| {
            if (!rowMatches(dataset, req, row_idx, resolved_exact.items, resolved_ranges.items)) continue;
            topk.consider(dataset.rows, row_idx);
        }
    } else {
        for (dataset.rows, 0..) |_, row_idx| {
            const index: u32 = @intCast(row_idx);
            if (!rowMatches(dataset, req, index, resolved_exact.items, resolved_ranges.items)) continue;
            topk.consider(dataset.rows, index);
        }
    }

    topk.finalize(dataset.rows);
    @memcpy(out_indices[0..topk.len], topk.items[0..topk.len]);
    return topk.len;
}

fn rowMatches(
    dataset: *const Dataset,
    req: RequestPayload,
    row_idx: u32,
    exact_filters: []const ResolvedExact,
    range_filters: []const ResolvedRange,
) bool {
    const row = dataset.rows[row_idx];
    if (row.stock < req.qty) return false;

    for (exact_filters) |filter| {
        switch (filter) {
            .text => |resolved| {
                const current = dataset.text_columns[resolved.column_idx].values[row_idx];
                if (current != resolved.value_id) return false;
            },
            .numeric => |resolved| {
                const current = dataset.numeric_columns[resolved.column_idx].values[row_idx];
                if (std.math.isNan(current)) return false;
                if (current != resolved.value) return false;
            },
        }
    }

    for (range_filters) |range_filter| {
        const min_value = dataset.numeric_columns[range_filter.min_column_idx].values[row_idx];
        const max_value = dataset.numeric_columns[range_filter.max_column_idx].values[row_idx];
        if (range_filter.minimum) |minimum| {
            if (std.math.isNan(min_value) or min_value < minimum) return false;
        }
        if (range_filter.maximum) |maximum| {
            if (std.math.isNan(max_value) or max_value > maximum) return false;
        }
    }

    return true;
}

fn writeSuccessResponse(
    out: anytype,
    dataset: *const Dataset,
    candidate_indices: []const u32,
    package_interner: *const Interner,
    text_interner: *const Interner,
) !void {
    try out.writeAll("{\"ok\":true,\"candidates\":[");
    for (candidate_indices, 0..) |row_idx, i| {
        if (i != 0) try out.writeByte(',');
        const row = dataset.rows[row_idx];
        try out.writeByte('{');
        try out.print("\"lcsc_id\":{d}", .{row.lcsc_id});
        try out.print(",\"stock\":{d}", .{row.stock});
        try out.print(",\"is_basic\":{s}", .{if (row.is_basic) "true" else "false"});
        try out.print(",\"is_preferred\":{s}", .{if (row.is_preferred) "true" else "false"});
        try out.writeAll(",\"package\":");
        try std.json.stringify(package_interner.valueById(row.package_id), .{}, out);

        for (dataset.numeric_columns) |column| {
            try out.print(",\"{s}\":", .{column.name});
            const value = column.values[row_idx];
            if (std.math.isNan(value)) {
                try out.writeAll("null");
                continue;
            }
            switch (column.kind) {
                .integer => try out.print("{d}", .{@as(i64, @intFromFloat(value))}),
                .real => try out.print("{d}", .{value}),
            }
        }

        for (dataset.text_columns) |column| {
            try out.print(",\"{s}\":", .{column.name});
            const value_id = column.values[row_idx];
            if (value_id == 0) {
                try out.writeAll("null");
                continue;
            }
            try std.json.stringify(text_interner.valueById(value_id), .{}, out);
        }

        try out.writeByte('}');
    }
    try out.writeAll("]}\n");
}

fn writeError(out: anytype, message: []const u8, error_type: []const u8) !void {
    try std.json.stringify(
        ErrorResponse{
            .@"error" = message,
            .error_type = error_type,
        },
        .{},
        out,
    );
    try out.writeByte('\n');
}
