const std = @import("std");

const py_lib_name = "pyzig";

fn build_pyi(b: *std.Build, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode) *std.Build.Step {
    // Build a small executable that generates the pyi files
    const pyi_exe = b.addExecutable(.{
        .name = "pyi",
        .root_source_file = b.path("src/sexp/pyi.zig"),
        .target = target,
        .optimize = optimize,
    });

    const pyzig_mod = b.createModule(.{
        .root_source_file = b.path("src/pyzig/lib.zig"),
    });
    const sexp_mod = b.addModule("sexp", .{
        .root_source_file = b.path("src/sexp/lib.zig"),
    });
    pyi_exe.root_module.addImport("pyzig", pyzig_mod);
    pyi_exe.root_module.addImport("sexp", sexp_mod);

    // Run the executable to generate pyi files
    const run_gen = b.addRunArtifact(pyi_exe);
    // Pass the output directory as an argument
    run_gen.addArg(b.getInstallPath(.lib, "."));

    // Create a step that ensures the output directory exists
    const make_dir_step = b.addSystemCommand(&.{ "mkdir", "-p", b.getInstallPath(.lib, ".") });
    run_gen.step.dependOn(&make_dir_step.step);

    return &run_gen.step;
}

fn addPythonExtension(
    b: *std.Build,
    target: std.Build.ResolvedTarget,
    optimize: std.builtin.OptimizeMode,
    python_include: []const u8,
    python_lib_opt: ?[]const u8,
    python_lib_dir_opt: ?[]const u8,
) void {
    // Check if we should use auto-generated bindings
    const root_file = "src/sexp/py.zig";

    const python_ext = b.addSharedLibrary(.{
        .name = py_lib_name,
        .root_source_file = b.path(root_file),
        .target = target,
        .optimize = optimize,
        .pic = true,
    });

    const pyzig_mod = b.createModule(.{
        .root_source_file = b.path("src/pyzig/lib.zig"),
    });
    const sexp_mod = b.addModule("sexp", .{
        .root_source_file = b.path("src/sexp/lib.zig"),
    });
    python_ext.root_module.addImport("pyzig", pyzig_mod);
    python_ext.root_module.addImport("sexp", sexp_mod);

    python_ext.addIncludePath(.{ .cwd_relative = python_include });

    const builtin = @import("builtin");
    if (builtin.os.tag == .macos) {
        // Do not link libpython on macOS; allow undefined symbols to be
        // resolved at runtime by the Python interpreter (like distutils does).
        python_ext.linker_allow_shlib_undefined = true;
    }
    if (builtin.os.tag == .windows) {
        // On Windows, Python extension modules must link against the import library
        if (python_lib_opt) |python_lib| {
            if (python_lib_dir_opt) |lib_dir| {
                python_ext.addLibraryPath(.{ .cwd_relative = lib_dir });
            }
            python_ext.linkSystemLibrary(python_lib);
        } else {
            @panic("python-lib must be provided on Windows builds");
        }
    }

    python_ext.linkLibC();

    // Choose extension filename based on host OS at comptime
    // This value must be comptime-known for dest_sub_path.
    const ext = if (builtin.os.tag == .windows) ".pyd" else ".so";
    const install_python_ext = b.addInstallArtifact(python_ext, .{
        .dest_dir = .{ .override = .{ .custom = "lib" } },
        .dest_sub_path = py_lib_name ++ ext,
    });

    // Generate pyi file at build time (no Python needed!)
    const pyi_step = build_pyi(b, target, optimize);

    const python_ext_step = b.step("python-ext", "Build Python extension module");
    python_ext_step.dependOn(&install_python_ext.step);
    python_ext_step.dependOn(pyi_step);
}

fn build_pyzig(b: *std.Build, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode) void {
    const lib_mod = b.createModule(.{
        .root_source_file = b.path("src/pyzig/demo/root.zig"),
        .target = target,
        .optimize = optimize,
    });

    // Create library build step (optional, not part of default)
    const lib = b.addLibrary(.{
        .linkage = .static,
        .name = py_lib_name,
        .root_module = lib_mod,
    });
    const lib_step = b.step("lib", "Build static library");
    lib_step.dependOn(&b.addInstallArtifact(lib, .{}).step);

    // Creates a step for unit testing. This only builds the test executable
    // but does not run it.
    const lib_unit_tests = b.addTest(.{
        .root_module = lib_mod,
    });

    const run_lib_unit_tests = b.addRunArtifact(lib_unit_tests);

    // Similar to creating the run step earlier, this exposes a `test` step to
    // the `zig build --help` menu, providing a way for the user to request
    // running the unit tests.
    const test_step = b.step("test-pyzig", "Run unit tests");
    test_step.dependOn(&run_lib_unit_tests.step);

    // Add Python extension if options are provided
    const python_include = b.option([]const u8, "python-include", "Python include directory path");
    const python_lib = b.option([]const u8, "python-lib", "Python library name (Windows only; e.g., python313)");
    const python_lib_dir = b.option([]const u8, "python-lib-dir", "Directory containing the Python import library (Windows only)");

    if (python_include) |include_path| {
        addPythonExtension(b, target, optimize, include_path, python_lib, python_lib_dir);
    }
}

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Build a library from the source files
    const lib = b.addStaticLibrary(.{
        .name = "sexp",
        .root_source_file = b.path("src/sexp/lib.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(lib);

    build_pyzig(b, target, optimize);
}
