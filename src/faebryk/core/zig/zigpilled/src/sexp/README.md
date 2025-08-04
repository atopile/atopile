# S-Expression Dataclass for Zig

This is a Zig implementation of S-expression serialization/deserialization for structs, similar to Python's dataclass_sexp. It's designed to work with KiCad file formats and other S-expression based formats.

## Files

- `ast.zig` - S-expression AST types and utilities
- `tokenizer.zig` - S-expression tokenizer
- `tokenizer_parallel.zig` - Parallel tokenizer for large files
- `dataclass_sexp.zig` - Main serialization/deserialization implementation
- `fp_lib_table.zig` - Example usage with KiCad fp-lib-table format
- `example_ast.zig` - Comprehensive example showing all features
- `performance_test.zig` - Performance comparison of sequential vs parallel tokenization
- `test_dataclass_sexp.zig` - Test suite
- `ast_test.zig` - AST tests
- `tokenizer_test.zig` - Tokenizer tests
- `build.zig` - Build configuration
- `test_files/` - Sample KiCad PCB files for testing

## Features

- Encode/decode Zig structs to/from S-expressions
- Positional fields
- Optional fields
- Multidict fields (multiple entries with same key)
- Custom field names
- Field ordering
- Compatible with KiCad file formats

## Usage

```zig
const std = @import("std");
const dataclass_sexp = @import("dataclass_sexp.zig");

const MyStruct = struct {
    name: []const u8,
    value: i32,
    
    pub const sexp_metadata = .{
        .name = .{ .positional = false },
        .value = .{ .positional = false },
    };
};

// Encode
const data = MyStruct{ .name = "test", .value = 42 };
const encoded = try dataclass_sexp.dumps(allocator, data);
// Result: ((name "test") (value 42))

// Decode
const decoded = try dataclass_sexp.loads(MyStruct, allocator, sexp);
```

## Field Metadata Options

- `positional`: Field appears without key name
- `multidict`: Field can appear multiple times (for slices)
- `sexp_name`: Override field name in S-expression
- `order`: Control field ordering

## Running Tests

```bash
zig test test_dataclass_sexp.zig
zig test tokenizer_test.zig
zig test ast_test.zig
```

## Examples

Run the examples:
```bash
zig run fp_lib_table.zig
zig run example_ast.zig
```

## Performance Testing

Test tokenization performance on large files:
```bash
zig build perf -- test_files/demomatrix.kicad_pcb
```

The parallel tokenizer provides significant speedup on files larger than 100KB.

## Performance Considerations

When parsing large S-expression files, use an ArenaAllocator instead of GeneralPurposeAllocator for dramatic performance improvements (up to 40x faster). The parser creates many small allocations for lists, and arena allocation avoids the overhead of individual allocation tracking.

```zig
// Slow (with GPA)
var sexp = try ast.parse(allocator, tokens);
defer sexp.deinit(allocator);

// Fast (with Arena)
var arena = std.heap.ArenaAllocator.init(allocator);
defer arena.deinit();
var sexp = try ast.parse(arena.allocator(), tokens);
```