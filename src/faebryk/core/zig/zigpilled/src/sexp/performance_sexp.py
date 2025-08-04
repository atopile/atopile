#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "sexpdata",
# ]
# ///

import subprocess
import time
from pathlib import Path

import sexpdata

TEST_FILES_DIR = Path(__file__).parent / "test_files"
ZIG_OUT_DIR = Path(__file__).parent / "zig-out" / "bin"
PERFORMANCE_TEST_EXE = ZIG_OUT_DIR / "performance_sexp"


def count_tokens(data, depth=0):
    """Recursively count tokens and S-expressions in parsed data"""
    lparen = 0
    rparen = 0
    symbols = 0
    numbers = 0
    strings = 0
    lists = 0
    atoms = 0

    def count_recursive(item):
        nonlocal lparen, rparen, symbols, numbers, strings, lists, atoms

        if isinstance(item, list):
            lparen += 1
            rparen += 1
            lists += 1
            for sub_item in item:
                count_recursive(sub_item)
        elif isinstance(item, sexpdata.Symbol):
            symbols += 1
            atoms += 1
        elif isinstance(item, (int, float)):
            numbers += 1
            atoms += 1
        elif isinstance(item, str):
            strings += 1
            atoms += 1

    count_recursive(data)
    return (
        lparen,
        rparen,
        symbols,
        numbers,
        strings,
        0,
        lists,
        atoms,
    )  # 0 comments - Python parser strips them


def test_python(file_path):
    """Test Python sexpdata performance"""
    # Read file
    file_contents = file_path.read_text()
    file_size = len(file_contents)

    # Parse with timing
    start_time = time.time() * 1000  # milliseconds
    try:
        data = sexpdata.loads(file_contents)
        end_time = time.time() * 1000
        parse_time = int(end_time - start_time)

        # Count tokens
        lparen, rparen, symbols, numbers, strings, comments, lists, atoms = (
            count_tokens(data)
        )
        total_tokens = lparen + rparen + symbols + numbers + strings + comments

        return {
            "file_size": file_size,
            "tokenize_time": parse_time,  # Python does both in one pass
            "parse_time": 0,  # Already included in tokenize_time
            "total_tokens": total_tokens,
            "lparen": lparen,
            "rparen": rparen,
            "symbols": symbols,
            "numbers": numbers,
            "strings": strings,
            "comments": comments,
            "balanced": lparen == rparen,
            "sexp_count": 1 if isinstance(data, list) else 0,
            "list_count": lists,
            "atom_count": atoms,
            "error": None,
        }
    except Exception as e:
        return {"file_size": file_size, "error": str(e)}


def compile_zig_if_needed():
    """Build the Zig performance test using the build system"""
    build_file = Path(__file__).parent / "build.zig"

    if not build_file.exists():
        return {"error": f"Build file {build_file} not found"}

    # Check if we need to rebuild
    source_files = list(Path(__file__).parent.glob("*.zig"))
    if not source_files:
        return {"error": "No Zig source files found"}

    needs_compile = not PERFORMANCE_TEST_EXE.exists()
    if not needs_compile:
        # Check if any source is newer than executable
        exe_mtime = PERFORMANCE_TEST_EXE.stat().st_mtime
        for source in source_files:
            if source.stat().st_mtime > exe_mtime:
                needs_compile = True
                break

    if needs_compile:
        print("Building Zig performance test...")
        result = subprocess.run(
            ["zig", "build", "-Doptimize=ReleaseFast", "--build-file", str(build_file)],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {"error": f"Failed to build: {result.stderr}"}
        print("Build successful")

    return None


def test_zig(file_path):
    """Test Zig parallel tokenizer and AST parser performance"""
    # Compile if needed
    compile_error = compile_zig_if_needed()
    if compile_error:
        return compile_error

    # Run the performance test
    result = subprocess.run(
        [str(PERFORMANCE_TEST_EXE), str(file_path.absolute())],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return {"error": f"Zig test failed: {result.stderr}"}

    # Parse output
    for line in result.stderr.split("\n"):
        if line.startswith("RESULT:"):
            parts = line.replace("RESULT:", "").split(":")
            if len(parts) >= 15:
                return {
                    "file_size": int(parts[0]),
                    "tokenize_time": int(parts[1]),
                    "parse_time": int(parts[2]),
                    "total_tokens": int(parts[3]),
                    "lparen": int(parts[4]),
                    "rparen": int(parts[5]),
                    "symbols": int(parts[6]),
                    "numbers": int(parts[7]),
                    "strings": int(parts[8]),
                    "comments": int(parts[9]),
                    "balanced": parts[10] == "true",
                    "sexp_count": int(parts[11]),
                    "list_count": int(parts[12]),
                    "atom_count": int(parts[13]),
                    "cpu_count": int(parts[14]),
                    "error": None,
                }

    return {"error": "Could not parse Zig output"}


def format_results(name, results):
    """Format test results for display"""
    if results.get("error"):
        return f"{name}: ERROR - {results['error']}"

    tokens_str = (
        f"(L:{results['lparen']} R:{results['rparen']} "
        f"S:{results['symbols']} N:{results['numbers']} "
        f"Str:{results['strings']}"
    )

    # Add comments if present
    if results.get("comments", 0) > 0:
        tokens_str += f" C:{results['comments']}"

    tokens_str += ")"

    # Build timing string
    if results.get("parse_time", 0) > 0:
        time_str = (
            f"tokenize:{results['tokenize_time']}ms "
            f"+ parse:{results['parse_time']}ms = "
            f"{results['tokenize_time'] + results['parse_time']}ms"
        )
    else:
        time_str = f"{results['tokenize_time']}ms"

    # Add S-expression counts if available
    sexp_str = ""
    if "list_count" in results and "atom_count" in results:
        sexp_str = (
            f", S-exps: {results.get('sexp_count', 0)}"
            f" (Lists:{results['list_count']} Atoms:{results['atom_count']})"
        )

    return (
        f"{name}: {results['file_size']} bytes, "
        f"{time_str}, "
        f"{results['total_tokens']} tokens "
        f"{tokens_str} "
        f"{'✓' if results['balanced'] else '✗'}"
        f"{sexp_str}"
    )


def main():
    # Find all .kicad_pcb files in test_files directory
    test_files = sorted(TEST_FILES_DIR.glob("*.kicad_pcb"))

    if not test_files:
        print("No .kicad_pcb files found in test_files directory")
        return

    print(f"Found {len(test_files)} test files\n")

    for test_file in test_files:
        print(f"=== {test_file.name} ===")

        # Test Python
        python_results = test_python(test_file)
        print(format_results("Python", python_results))

        # Test Zig
        zig_results = test_zig(test_file)
        zig_name = "Zig"
        if zig_results.get("cpu_count"):
            zig_name += f" ({zig_results['cpu_count']} cores)"
        print(format_results(zig_name, zig_results))

        # Show speedup if both succeeded
        if not python_results.get("error") and not zig_results.get("error"):
            python_time = python_results["tokenize_time"] + python_results.get(
                "parse_time", 0
            )
            zig_time = zig_results["tokenize_time"] + zig_results["parse_time"]

            if zig_time > 0:
                speedup = python_time / zig_time
                print(f"Speedup: {speedup:.1f}x")
            else:
                print("Speedup: Too fast to measure accurately")

        # Show throughput
        if not zig_results.get("error"):
            file_size_mb = zig_results["file_size"] / (1024 * 1024)
            total_time_sec = (
                zig_results["tokenize_time"] + zig_results["parse_time"]
            ) / 1000.0
            if total_time_sec > 0:
                throughput = file_size_mb / total_time_sec
                print(f"Zig throughput: {throughput:.1f} MB/s")

        print()


if __name__ == "__main__":
    main()
