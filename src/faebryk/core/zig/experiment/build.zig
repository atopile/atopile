const std = @import("std");

const py_lib_name = "pyzig";

fn build_pyi(b: *std.Build) *std.Build.Step {
    const pyi_content =
        \\class Nested:
        \\    x: int
        \\    y: str
        \\
        \\    def __init__(self, x: int, y: str) -> None: ...
        \\    def __repr__(self) -> str: ...
        \\
        \\class Top:
        \\    a: int
        \\    b: int
        \\    c: Nested
        \\
        \\    def __init__(self, a: int, b: int, c: Nested) -> None: ...
        \\    def __repr__(self) -> str: ...
        \\    def sum(self) -> int: ...
        \\
        \\def add(*, a: int, b: int) -> int: ...
        \\def get_default_top() -> Top: ...
        \\
    ;

    // Create a WriteFile step to generate the pyi file
    const write_files = b.addWriteFiles();
    _ = write_files.add("pyzig.pyi", pyi_content);
    
    // Install the pyi file to lib directory
    const install_pyi = b.addInstallFile(write_files.getDirectory().path(b, "pyzig.pyi"), "lib/pyzig.pyi");
    
    return &install_pyi.step;
}

fn addPythonExtension(b: *std.Build, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode, python_include: []const u8, python_lib: []const u8) void {
    const python_ext = b.addSharedLibrary(.{
        .name = py_lib_name,
        .root_source_file = b.path("src/python_ext.zig"),
        .target = target,
        .optimize = optimize,
        .pic = true,
    });

    python_ext.addIncludePath(.{ .cwd_relative = python_include });
    python_ext.linkSystemLibrary(python_lib);
    python_ext.linkLibC();

    const install_python_ext = b.addInstallArtifact(python_ext, .{
        .dest_dir = .{ .override = .{ .custom = "lib" } },
        .dest_sub_path = py_lib_name ++ ".so",
    });

    // Generate pyi file
    const pyi_step = build_pyi(b);

    const python_ext_step = b.step("python-ext", "Build Python extension module");
    python_ext_step.dependOn(&install_python_ext.step);
    python_ext_step.dependOn(pyi_step);
}

// Although this function looks imperative, note that its job is to
// declaratively construct a build graph that will be executed by an external
// runner.
pub fn build(b: *std.Build) void {
    // Standard target options allows the person running `zig build` to choose
    // what target to build for. Here we do not override the defaults, which
    // means any target is allowed, and the default is native. Other options
    // for restricting supported target set are available.
    const target = b.standardTargetOptions(.{});

    // Standard optimization options allow the person running `zig build` to select
    // between Debug, ReleaseSafe, ReleaseFast, and ReleaseSmall. Here we do not
    // set a preferred release mode, allowing the user to decide how to optimize.
    const optimize = b.standardOptimizeOption(.{});

    // This creates a "module", which represents a collection of source files alongside
    // some compilation options, such as optimization mode and linked system libraries.
    // Every executable or library we compile will be based on one or more modules.
    const lib_mod = b.createModule(.{
        // `root_source_file` is the Zig "entry point" of the module. If a module
        // only contains e.g. external object files, you can make this `null`.
        // In this case the main source file is merely a path, however, in more
        // complicated build scripts, this could be a generated file.
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
    });

    // We will also create a module for our other entry point, 'main.zig'.
    const exe_mod = b.createModule(.{
        // `root_source_file` is the Zig "entry point" of the module. If a module
        // only contains e.g. external object files, you can make this `null`.
        // In this case the main source file is merely a path, however, in more
        // complicated build scripts, this could be a generated file.
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    // Modules can depend on one another using the `std.Build.Module.addImport` function.
    // This is what allows Zig source code to use `@import("foo")` where 'foo' is not a
    // file path. In this case, we set up `exe_mod` to import `lib_mod`.
    exe_mod.addImport(py_lib_name ++ "_lib", lib_mod);

    // Create library build step (optional, not part of default)
    const lib = b.addLibrary(.{
        .linkage = .static,
        .name = py_lib_name,
        .root_module = lib_mod,
    });
    const lib_step = b.step("lib", "Build static library");
    lib_step.dependOn(&b.addInstallArtifact(lib, .{}).step);

    // Create executable build step (optional, not part of default)
    const exe = b.addExecutable(.{
        .name = py_lib_name,
        .root_module = exe_mod,
    });
    const exe_step = b.step("exe", "Build executable");
    exe_step.dependOn(&b.addInstallArtifact(exe, .{}).step);

    // This *creates* a Run step in the build graph, to be executed when another
    // step is evaluated that depends on it. The next line below will establish
    // such a dependency.
    const run_cmd = b.addRunArtifact(exe);

    // By making the run step depend on the exe step, it will build the exe when needed
    run_cmd.step.dependOn(exe_step);

    // This allows the user to pass arguments to the application in the build
    // command itself, like this: `zig build run -- arg1 arg2 etc`
    if (b.args) |args| {
        run_cmd.addArgs(args);
    }

    // This creates a build step. It will be visible in the `zig build --help` menu,
    // and can be selected like this: `zig build run`
    // This will evaluate the `run` step rather than the default, which is "install".
    const run_step = b.step("run", "Run the app");
    run_step.dependOn(&run_cmd.step);

    // Creates a step for unit testing. This only builds the test executable
    // but does not run it.
    const lib_unit_tests = b.addTest(.{
        .root_module = lib_mod,
    });

    const run_lib_unit_tests = b.addRunArtifact(lib_unit_tests);

    const exe_unit_tests = b.addTest(.{
        .root_module = exe_mod,
    });

    const run_exe_unit_tests = b.addRunArtifact(exe_unit_tests);

    // Similar to creating the run step earlier, this exposes a `test` step to
    // the `zig build --help` menu, providing a way for the user to request
    // running the unit tests.
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_lib_unit_tests.step);
    test_step.dependOn(&run_exe_unit_tests.step);

    // Add Python extension if options are provided
    const python_include = b.option([]const u8, "python-include", "Python include directory path");
    const python_lib = b.option([]const u8, "python-lib", "Python library name (e.g., python3.12)");

    if (python_include) |include_path| {
        if (python_lib) |lib_name| {
            addPythonExtension(b, target, optimize, include_path, lib_name);
        }
    }
}
