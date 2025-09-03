#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "sexpdata",
#     "atopile"
# ]
# ///

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import sexpdata

from faebryk.libs.kicad.fileformats import kicad

SEXP_ROOT = Path(__file__).parent.parent.parent
TEST_FILES_DIR = SEXP_ROOT / "test" / "resources" / "v9"


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

        if file_path.suffix == ".net":
            _ = kicad.loads(kicad.netlist.NetlistFile, data)
            structure_time = int((time.time() * 1000) - end_time)
        elif file_path.suffix == ".kicad_pcb":
            _ = kicad.loads(kicad.pcb.PcbFile, data)
            structure_time = int((time.time() * 1000) - end_time)
        else:
            structure_time = 0

        # Count tokens
        lparen, rparen, symbols, numbers, strings, comments, lists, atoms = (
            count_tokens(data)
        )
        total_tokens = lparen + rparen + symbols + numbers + strings + comments

        return TestResults(
            file_size=file_size,
            tokenize_time=0,  # Python does both in one pass
            parse_time=parse_time,
            structure_time=structure_time,
            total_tokens=total_tokens,
            lparen=lparen,
            rparen=rparen,
            symbols=symbols,
            numbers=numbers,
            strings=strings,
            comments=comments,
            balanced=lparen == rparen,
            sexp_count=1 if isinstance(data, list) else 0,
            list_count=lists,
            atom_count=atoms,
            cpu_count=1,
        )
    except Exception as e:
        raise Exception(f"Python test failed: {e}")


@dataclass
class TestResults:
    file_size: int
    tokenize_time: int
    parse_time: int
    structure_time: int
    total_tokens: int
    lparen: int
    rparen: int
    symbols: int
    numbers: int
    strings: int
    comments: int
    balanced: bool
    sexp_count: int
    list_count: int
    atom_count: int
    cpu_count: int


def test_zig(file_path):
    """Test Zig parallel tokenizer and AST parser performance"""

    # Run the performance test
    result = subprocess.run(
        ["zig", "build", "perf", "--", str(file_path.absolute())],
        capture_output=True,
        text=True,
        cwd=SEXP_ROOT,
    )

    if result.returncode != 0:
        raise Exception(f"Zig test failed: {result.stderr}")

    # Parse output
    for line in result.stderr.split("\n"):
        if line.startswith("RESULT:"):
            parts = line.replace("RESULT:", "").split(":")
            if len(parts) >= 15:
                return TestResults(
                    file_size=int(parts[0]),
                    tokenize_time=int(parts[1]),
                    parse_time=int(parts[2]),
                    structure_time=int(parts[3]),
                    total_tokens=int(parts[4]),
                    lparen=int(parts[5]),
                    rparen=int(parts[6]),
                    symbols=int(parts[7]),
                    numbers=int(parts[8]),
                    strings=int(parts[9]),
                    comments=int(parts[10]),
                    balanced=parts[11] == "true",
                    sexp_count=int(parts[12]),
                    list_count=int(parts[13]),
                    atom_count=int(parts[14]),
                    cpu_count=int(parts[15]),
                )

    raise Exception("Could not parse Zig output")


def format_results(name, results: TestResults | None):
    if results is None:
        return f"{name}: ERROR - No results"

    """Format test results for display"""
    tokens_str = (
        f"(L:{results.lparen} R:{results.rparen} "
        f"S:{results.symbols} N:{results.numbers} "
        f"Str:{results.strings}"
    )

    # Add comments if present
    if results.comments > 0:
        tokens_str += f" C:{results.comments}"

    tokens_str += ")"

    # Build timing string
    time_str = (
        f"tokenize:{results.tokenize_time}ms "
        f"+ parse:{results.parse_time}ms "
        f"+ structure:{results.structure_time}ms "
        f"= {results.tokenize_time + results.parse_time + results.structure_time}ms"
    )

    # Add S-expression counts if available
    sexp_str = ""
    if results.list_count > 0 and results.atom_count > 0:
        sexp_str = (
            f", S-exps: {results.sexp_count}"
            f" (Lists:{results.list_count} Atoms:{results.atom_count})"
        )

    return (
        f"{name}: {results.file_size} bytes, "
        f"{time_str}, "
        f"{results.total_tokens} tokens "
        # f"{tokens_str} "
        f"{'✓' if results.balanced else '✗'}"
        f"{sexp_str}"
    )


def main():
    # Find all .kicad_pcb files in test_files directory
    test_files = sorted(TEST_FILES_DIR.glob("pcb/*.kicad_pcb"))

    if not test_files:
        print(f"No .kicad_pcb files found in {TEST_FILES_DIR}")
        return

    print(f"Found {len(test_files)} test files\n")

    for test_file in test_files:
        print(f"=== {test_file.name} ===")

        # Test Python
        try:
            python_results = test_python(test_file)
        except Exception:
            python_results = None

        print(format_results("Python", python_results))

        # Test Zig
        try:
            zig_results = test_zig(test_file)
        except Exception:
            zig_results = None

        zig_name = "Zig"
        if zig_results:
            zig_name += f" ({zig_results.cpu_count} cores)"
        print(format_results(zig_name, zig_results))

        # Show speedup if both succeeded
        if python_results and zig_results:
            python_time = (
                python_results.tokenize_time
                + python_results.parse_time
                + python_results.structure_time
            )
            zig_time = (
                zig_results.tokenize_time
                + zig_results.parse_time
                + zig_results.structure_time
            )

            if zig_time > 0:
                speedup = python_time / zig_time
                print(f"Speedup: {speedup:.1f}x")
            else:
                print("Speedup: Too fast to measure accurately")

        # Show throughput
        if zig_results:
            file_size_mb = zig_results.file_size / (1024 * 1024)
            total_time_sec = (
                zig_results.tokenize_time
                + zig_results.parse_time
                + zig_results.structure_time
            ) / 1000.0
            if total_time_sec > 0:
                throughput = file_size_mb / total_time_sec
                print(f"Zig throughput: {throughput:.1f} MB/s")

        print()


if __name__ == "__main__":
    main()
