const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Performance test executable
    const perf_test = b.addExecutable(.{
        .name = "performance_sexp",
        .root_source_file = b.path("performance_sexp.zig"),
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

    const tokenizer_test = b.addTest(.{
        .root_source_file = b.path("test_tokenizer.zig"),
        .target = target,
        .optimize = optimize,
    });

    const ast_test = b.addTest(.{
        .root_source_file = b.path("test_ast.zig"),
        .target = target,
        .optimize = optimize,
    });

    const structure_test = b.addTest(.{
        .root_source_file = b.path("test_structure.zig"),
        .target = target,
        .optimize = optimize,
    });

    const run_tokenizer_test = b.addRunArtifact(tokenizer_test);
    const run_ast_test = b.addRunArtifact(ast_test);
    const run_structure_test = b.addRunArtifact(structure_test);

    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_tokenizer_test.step);
    test_step.dependOn(&run_ast_test.step);
    test_step.dependOn(&run_structure_test.step);

    // Run example
    const run_example = b.addRunArtifact(example_ast);
    const example_step = b.step("example", "Run comprehensive example");
    example_step.dependOn(&run_example.step);

    // Run performance test
    const run_perf = b.addRunArtifact(perf_test);
    if (b.args) |args| {
        run_perf.addArgs(args);
    }
    const perf_step = b.step("perf", "Run performance test");
    perf_step.dependOn(&run_perf.step);
}
