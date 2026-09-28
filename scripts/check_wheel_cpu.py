#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["iced-x86==1.21.0"]
# ///
"""
Check that the x86_64 machine code in wheels runs on a given CPU level.

The Zig core is compiled for the CPU model in ATOPILE_ZIG_CPU (see
src/faebryk/core/zig/CMakeLists.txt). Without it, Zig targets the build machine's
CPU, and the wheel crashes with SIGILL / STATUS_ILLEGAL_INSTRUCTION (0xC000001D) on
CPUs lacking any of that machine's extensions (e.g. AVX-512).

This disassembles the code sections of every x86_64 PE, ELF and Mach-O file in the
given wheels and fails if any instruction needs a CPU feature above the level, or
cannot be decoded (e.g. because it is newer than the disassembler). Binaries for
other architectures are skipped.

Usage:
    uv run scripts/check_wheel_cpu.py --cpu baseline wheelhouse/
"""

import argparse
import struct
import sys
import zipfile
from collections import Counter
from collections.abc import Callable, Iterator
from pathlib import Path

from iced_x86 import (
    Code,
    CpuidFeature,
    Decoder,
    DecoderOptions,
    Formatter,
    FormatterSyntax,
    Mnemonic,
)

# CPUID features (iced-x86 names) of the x86-64 psABI levels, keyed by the matching
# Zig CPU model. The first level is what every x86-64 CPU supports, plus CET_IBT:
# ENDBR64, which CPUs without CET execute as a NOP. LAHF_SAHF is added by _scan,
# since iced-x86 counts LAHF/SAHF as 8086 although 64-bit mode needs a CPUID bit.
_V1 = (
    "INTEL8086 INTEL186 INTEL286 INTEL386 INTEL486 X64 CPUID TSC PAUSE MULTIBYTENOP"
    " CLFSH SYSCALL FPU FPU287 FPU387 CMOV CX8 FXSR MMX SSE SSE2 CET_IBT"
)
_V2 = f"{_V1} CMPXCHG16B LAHF_SAHF POPCNT SSE3 SSSE3 SSE4_1 SSE4_2"
_V3 = f"{_V2} AVX AVX2 BMI1 BMI2 F16C FMA LZCNT MOVBE XSAVE"
_V4 = f"{_V3} AVX512F AVX512BW AVX512CD AVX512DQ AVX512VL"
LEVELS = {
    "x86_64": set(_V1.split()),
    "x86_64_v2": set(_V2.split()),
    "x86_64_v3": set(_V3.split()),
    "x86_64_v4": set(_V4.split()),
}
# Zig's "baseline" is x86_64, except on macOS where it is core2
_CORE2 = set(f"{_V1} CMPXCHG16B LAHF_SAHF SSE3 SSSE3".split())

_FEATURE_NAMES = {v: k for k, v in vars(CpuidFeature).items() if isinstance(v, int)}
_NATIVE_SUFFIXES = {".so", ".pyd", ".dylib", ".dll", ".exe"}
_MAGICS = (b"MZ", b"\x7fELF", b"\xcf\xfa\xed\xfe")

# LLVM emits TZCNT's encoding (REP BSF) even without BMI1, where it gives the same
# result as BSF, which is what CPUs without BMI1 run it as. So decode it as BSF; a
# build that really targets BMI1 is still caught by ANDN, BLSR etc.
_DECODER_OPTIONS = DecoderOptions.NO_MPFX_0FBC

# (address, code) of each executable section
Sections = list[tuple[int, bytes]]
Parser = Callable[[bytes], tuple[str, Sections]]


def _pe(data: bytes) -> tuple[str, Sections]:
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    machine, n_sections = struct.unpack_from("<2H", data, pe + 4)
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    image_base = struct.unpack_from("<Q", data, pe + 48)[0]
    table = pe + 24 + optional_size
    sections = []
    for i in range(n_sections):
        header = table + 40 * i
        vsize, rva, raw_size, raw_ptr = struct.unpack_from("<4I", data, header + 8)
        flags = struct.unpack_from("<I", data, header + 36)[0]
        if flags & 0x20000000:  # IMAGE_SCN_MEM_EXECUTE
            size = min(vsize, raw_size) if vsize else raw_size
            sections.append((image_base + rva, data[raw_ptr : raw_ptr + size]))
    return {0x8664: "x86_64", 0xAA64: "arm64"}.get(machine, hex(machine)), sections


def _elf(data: bytes) -> tuple[str, Sections]:
    if data[4:6] != b"\x02\x01":
        raise ValueError("not a 64-bit little-endian ELF")
    machine = struct.unpack_from("<H", data, 18)[0]
    table = struct.unpack_from("<Q", data, 40)[0]
    entry_size, n_sections = struct.unpack_from("<2H", data, 58)
    sections = []
    for i in range(n_sections):
        header = table + entry_size * i
        _, kind, flags, addr, offset, size = struct.unpack_from("<2I4Q", data, header)
        if flags & 0x4 and kind != 8:  # SHF_EXECINSTR, not SHT_NOBITS
            sections.append((addr, data[offset : offset + size]))
    return {62: "x86_64", 183: "arm64"}.get(machine, str(machine)), sections


def _macho(data: bytes) -> tuple[str, Sections]:
    cpu, _, _, n_commands = struct.unpack_from("<4I", data, 4)
    code = []  # (address, offset, size)
    data_in_code = []  # (offset, size), e.g. jump tables inside the code
    command = 32
    for _ in range(n_commands):
        kind, command_size = struct.unpack_from("<2I", data, command)
        if kind == 0x19:  # LC_SEGMENT_64
            for i in range(struct.unpack_from("<I", data, command + 64)[0]):
                header = command + 72 + 80 * i
                addr, size, offset = struct.unpack_from("<2QI", data, header + 32)
                flags = struct.unpack_from("<I", data, header + 64)[0]
                # S_ATTR_PURE_INSTRUCTIONS | S_ATTR_SOME_INSTRUCTIONS, not S_ZEROFILL
                if flags & 0x80000400 and flags & 0xFF != 1:
                    code.append((addr, offset, size))
        elif kind == 0x29:  # LC_DATA_IN_CODE
            offset, size = struct.unpack_from("<2I", data, command + 8)
            data_in_code += struct.iter_unpack("<IH2x", data[offset : offset + size])
        command += command_size
    sections = []
    for addr, offset, size in code:
        start = offset
        for skip, length in sorted(data_in_code):
            if start <= skip < offset + size:
                sections.append((addr + start - offset, data[start:skip]))
                start = skip + length
        sections.append((addr + start - offset, data[start : offset + size]))
    return {0x01000007: "x86_64", 0x0100000C: "arm64"}.get(cpu, hex(cpu)), sections


def _format(data: bytes) -> Parser | None:
    """The parser for a native binary, or None if data is not one."""
    if data[:4] == b"\x7fELF":
        return _elf
    if data[:4] == b"\xcf\xfa\xed\xfe":
        return _macho
    if data[:2] == b"MZ" and len(data) >= 0x40:
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe : pe + 4] == b"PE\0\0":
            return _pe
    return None


def _binaries(wheel: Path) -> Iterator[tuple[str, bytes, Parser | None]]:
    """Native binaries in the wheel, and files named like one (parser None)."""
    with zipfile.ZipFile(wheel) as zf:
        for info in zf.infolist():
            with zf.open(info) as f:
                head = f.read(4)
            named_native = Path(info.filename).suffix in _NATIVE_SUFFIXES
            if not (named_native or head.startswith(_MAGICS)):
                continue
            data = zf.read(info)
            parser = _format(data)
            if parser or named_native:
                yield info.filename, data, parser


def _scan(
    sections: Sections, allowed: set[str]
) -> tuple[int, Counter[str], dict[str, str]]:
    """Count instructions, and problems by feature with an example of each."""
    formatter = Formatter(FormatterSyntax.INTEL)
    disallowed_by_code: dict[int, list[str]] = {}
    total = 0
    problems: Counter[str] = Counter()
    examples: dict[str, str] = {}
    for address, code in sections:
        for instr in Decoder(64, code, _DECODER_OPTIONS, ip=address):
            total += 1
            if instr.code == Code.INVALID:
                start = instr.ip - address
                problems["undecodable"] += 1
                example = code[start : start + instr.len].hex(" ")
                examples.setdefault("undecodable", f"{instr.ip:#x} {example}")
                continue
            features = disallowed_by_code.get(instr.code)
            if features is None:
                names = [_FEATURE_NAMES[f] for f in instr.cpuid_features()]
                if instr.mnemonic in (Mnemonic.LAHF, Mnemonic.SAHF):
                    names.append("LAHF_SAHF")
                features = [name for name in names if name not in allowed]
                disallowed_by_code[instr.code] = features
            for name in features:
                problems[name] += 1
                examples.setdefault(name, f"{instr.ip:#x} {formatter.format(instr)}")
    return total, problems, examples


def _check(name: str, data: bytes, parse: Parser | None, cpu: str) -> bool:
    """Print the result for one binary, and return whether it passed."""
    try:
        if parse is None:
            raise ValueError("unsupported binary format")
        machine, sections = parse(data)
    except (ValueError, struct.error) as e:
        print(f"  {name}: error: {e}")
        return False
    if machine != "x86_64":
        print(f"  {name}: {machine}, skipped")
        return True
    if cpu == "baseline":
        allowed = _CORE2 if parse is _macho else LEVELS["x86_64"]
    else:
        allowed = LEVELS[cpu]
    total, problems, examples = _scan(sections, allowed)
    if not total:
        print(f"  {name}: error: no code found")
        return False
    if problems:
        count = sum(problems.values())
        print(f"  {name}: {count} of {total} instructions need more than {cpu}")
        for problem, n in problems.most_common():
            print(f"    {problem}: {n}, e.g. {examples[problem]}")
        return False
    print(f"  {name}: ok, {total} instructions")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--cpu",
        required=True,
        choices=[*LEVELS, "baseline"],
        help="highest CPU level the code may need, as a Zig CPU model",
    )
    parser.add_argument(
        "paths", nargs="+", type=Path, help="wheels, or directories of wheels"
    )
    args = parser.parse_args()

    if missing := [str(path) for path in args.paths if not path.exists()]:
        print(f"error: not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    wheels = [
        wheel
        for path in args.paths
        for wheel in (sorted(path.glob("*.whl")) if path.is_dir() else [path])
    ]
    if not wheels:
        print("error: no wheels found", file=sys.stderr)
        return 2

    failed = 0
    for wheel in wheels:
        print(wheel.name)
        binaries = list(_binaries(wheel))
        if not binaries:
            print("  error: no native binaries found")
            failed += 1
        failed += sum(not _check(*binary, args.cpu) for binary in binaries)

    if failed:
        print(f"\n{failed} problem(s) found, see above")
        return 1
    print(f"\nAll x86_64 binaries are compatible with {args.cpu}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
