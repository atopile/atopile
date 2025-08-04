const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Performance test executable
    const perf_test = b.addExecutable(.{
        .name = "performance_test",
        .root_source_file = b.path("performance_test.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(perf_test);

    // Example AST usage
    const example_ast = b.addExecutable(.{
        .name = "example_ast",
        .root_source_file = b.path("example_ast.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(example_ast);

    // Example fp_lib_table usage
    const fp_lib_table = b.addExecutable(.{
        .name = "fp_lib_table",
        .root_source_file = b.path("fp_lib_table.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(fp_lib_table);

    // Tests
    const tokenizer_test = b.addTest(.{
        .root_source_file = b.path("tokenizer_test.zig"),
        .target = target,
        .optimize = optimize,
    });

    const ast_test = b.addTest(.{
        .root_source_file = b.path("ast_test.zig"),
        .target = target,
        .optimize = optimize,
    });

    const dataclass_sexp_test = b.addTest(.{
        .root_source_file = b.path("test_dataclass_sexp.zig"),
        .target = target,
        .optimize = optimize,
    });

    const run_tokenizer_test = b.addRunArtifact(tokenizer_test);
    const run_ast_test = b.addRunArtifact(ast_test);
    const run_dataclass_sexp_test = b.addRunArtifact(dataclass_sexp_test);

    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_tokenizer_test.step);
    test_step.dependOn(&run_ast_test.step);
    test_step.dependOn(&run_dataclass_sexp_test.step);

    // Run example
    const run_example = b.addRunArtifact(example_ast);
    const example_step = b.step("example", "Run comprehensive example");
    example_step.dependOn(&run_example.step);

    // Run fp_lib_table example
    const run_fp_example = b.addRunArtifact(fp_lib_table);
    const fp_example_step = b.step("fp-example", "Run fp_lib_table example");
    fp_example_step.dependOn(&run_fp_example.step);
    
    // Run performance test
    const run_perf = b.addRunArtifact(perf_test);
    if (b.args) |args| {
        run_perf.addArgs(args);
    }
    const perf_step = b.step("perf", "Run performance test");
    perf_step.dependOn(&run_perf.step);
}
