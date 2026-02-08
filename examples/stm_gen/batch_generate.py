#!/usr/bin/env python3
"""
Batch generator for STM32 .ato definitions.
Generates modules for a curated list across all STM32 families.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Root paths
SCRIPT_DIR = Path(__file__).parent
STM32_PIN_DATA = Path("/Users/narayanpowderly/projects/STM32_open_pin_data/mcu")
GEN_DIR = SCRIPT_DIR / "generated"

# Curated MCU list: (xml_filename, lcsc_search, description)
# Selected for:
#   - Coverage of all families (C/F0/F1/F3/F4/F7/G0/G4/H7/L0/L1/L4/L5/U5/WB/WL)
#   - Mix of packages (TSSOP20, QFN32, LQFP48/64/100/144)
#   - Popular dev-board chips (Blue Pill, Black Pill, Nucleo, etc.)
MCUS = [
    # ── C-series (Cortex-M0+, entry level) ──
    ("STM32C011F(4-6)Px.xml",        "STMicroelectronics:STM32C011F6P6",   "C0 entry TSSOP20"),
    ("STM32C031C(4-6)Tx.xml",        "STMicroelectronics:STM32C031C6T6",   "C0 value LQFP48"),

    # ── F0-series (Cortex-M0, value) ──
    ("STM32F030F4Px.xml",            "STMicroelectronics:STM32F030F4P6",   "F0 tiny TSSOP20"),
    ("STM32F042F6Px.xml",            "STMicroelectronics:STM32F042F6P6",   "F0 USB TSSOP20"),
    ("STM32F072CBYx.xml",            "STMicroelectronics:STM32F072CBT6",   "F0 USB+CAN LQFP48"),

    # ── F1-series (Cortex-M3, mainstream) ──
    ("STM32F103C(8-B)Tx.xml",        "STMicroelectronics:STM32F103C8T6",   "F1 BluePill LQFP48"),

    # ── F3-series (Cortex-M4F, mixed-signal) ──
    ("STM32F303C(B-C)Tx.xml",        "STMicroelectronics:STM32F303CCT6",   "F3 mixed-signal LQFP48"),

    # ── F4-series (Cortex-M4F, high performance) ──
    ("STM32F401C(B-C)Ux.xml",        "STMicroelectronics:STM32F401CCU6",   "F4 BlackPill QFN48"),
    ("STM32F407V(E-G)Tx.xml",        "STMicroelectronics:STM32F407VGT6",   "F4 Discovery LQFP100"),
    ("STM32F411C(C-E)Ux.xml",        "STMicroelectronics:STM32F411CEU6",   "F4 popular QFN48"),
    ("STM32F429ZITx.xml",            "STMicroelectronics:STM32F429ZIT6",   "F4 LCD LQFP144"),
    ("STM32F446R(C-E)Tx.xml",        "STMicroelectronics:STM32F446RET6",   "F4 I2S/SAI LQFP64"),

    # ── F7-series (Cortex-M7, performance) ──
    ("STM32F722R(C-E)Tx.xml",        "STMicroelectronics:STM32F722RET6",   "F7 entry LQFP64"),
    ("STM32F746ZGTx.xml",            "STMicroelectronics:STM32F746ZGT6",   "F7 reference LQFP144"),

    # ── G0-series (Cortex-M0+, mainstream) ──
    ("STM32G0B1R(B-C-E)Tx.xml",      "STMicroelectronics:STM32G0B1RET6",   "G0 USB LQFP64"),

    # ── G4-series (Cortex-M4F, high-perf mixed) ──
    ("STM32G431CBTxZ.xml",           "STMicroelectronics:STM32G431CBT6",   "G4 FDCAN LQFP48"),
    ("STM32G474R(B-C-E)Tx.xml",      "STMicroelectronics:STM32G474RET6",   "G4 HRTIM LQFP64"),

    # ── H7-series (Cortex-M7, max performance) ──
    ("STM32H723ZGTx.xml",            "STMicroelectronics:STM32H723ZGT6",   "H7 lite LQFP144"),
    ("STM32H743ZITx.xml",            "STMicroelectronics:STM32H743ZIT6",   "H7 reference LQFP144"),
    ("STM32H750VBTx.xml",            "STMicroelectronics:STM32H750VBT6",   "H7 value LQFP100"),

    # ── L0-series (Cortex-M0+, ultra-low-power) ──
    ("STM32L073R(B-Z)Tx.xml",        "STMicroelectronics:STM32L073RZT6",   "L0 LCD LQFP64"),

    # ── L1-series (Cortex-M3, ultra-low-power) ──
    ("STM32L151C(6-8-B)TxA.xml",     "STMicroelectronics:STM32L151CBT6A",  "L1 entry LQFP48"),

    # ── L4-series (Cortex-M4F, ultra-low-power) ──
    ("STM32L432K(B-C)Ux.xml",        "STMicroelectronics:STM32L432KCU6",   "L4 tiny QFN32"),
    ("STM32L476R(C-E-G)Tx.xml",      "STMicroelectronics:STM32L476RGT6",   "L4 reference LQFP64"),

    # ── L5-series (Cortex-M33, TrustZone) ──
    ("STM32L552ZETx.xml",            "STMicroelectronics:STM32L552ZET6",   "L5 TrustZone LQFP144"),

    # ── U5-series (Cortex-M33, ultra-low-power) ──
    ("STM32U575ZITx.xml",            "STMicroelectronics:STM32U575ZIT6Q",  "U5 ultra-LP LQFP144"),

    # ── WB-series (Cortex-M4F+M0+, BLE) ──
    ("STM32WB55RGVx.xml",            "STMicroelectronics:STM32WB55RGV6",   "WB BLE VFQFPN68"),

    # ── WL-series (Cortex-M4+M0+, LoRa) ──
    ("STM32WLE5JBIx.xml",            "STMicroelectronics:STM32WLE5JBI6",   "WL LoRa QFN48"),
]


def run_generator(xml_path: Path, search: str, output_path: Path) -> tuple[bool, str]:
    """Run stm32_gen.py for one MCU. Returns (success, message)."""
    cmd = [
        sys.executable, str(SCRIPT_DIR / "stm32_gen.py"),
        str(xml_path),
        "--mfr-search", search,
        "-o", str(output_path),
        "-p", str(SCRIPT_DIR),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
            env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
        )
        if result.returncode == 0:
            return True, result.stdout.strip().split("\n")[-1]
        else:
            # Get last meaningful error line
            err = result.stderr.strip() or result.stdout.strip()
            last_lines = [l for l in err.split("\n") if l.strip()][-3:]
            return False, "\n    ".join(last_lines)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)


def build_test(ato_file: Path) -> tuple[bool, str]:
    """Build-test a generated .ato file by creating a minimal main.ato and building."""
    # Read the generated file to find the module name
    content = ato_file.read_text()
    m = re.search(r"^module (\w+):", content, re.MULTILINE)
    if not m:
        return False, "No module found in generated file"
    module_name = m.group(1)

    # Get relative path from project dir
    rel_path = ato_file.relative_to(SCRIPT_DIR)

    test_content = f'''"""Build test for {module_name}"""
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("TRAITS")

import ElectricPower
from "{rel_path}" import {module_name}

module App:
    power_3v3 = new ElectricPower
    mcu = new {module_name}
    power_3v3 ~ mcu.power_3v3
'''
    test_file = SCRIPT_DIR / "main.ato"
    test_file.write_text(test_content)

    try:
        result = subprocess.run(
            ["ato", "build"],
            capture_output=True, text=True, timeout=120,
            cwd=str(SCRIPT_DIR),
        )
        if result.returncode == 0:
            return True, "BUILD OK"
        else:
            err = result.stderr.strip() or result.stdout.strip()
            last_lines = [l for l in err.split("\n") if l.strip()][-3:]
            return False, "\n    ".join(last_lines)
    except subprocess.TimeoutExpired:
        return False, "BUILD TIMEOUT"
    except Exception as e:
        return False, str(e)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip MCUs that already have a generated .ato file")
    parser.add_argument("--build-test", action="store_true",
                        help="Build-test each generated file")
    parser.add_argument("--family", type=str, default=None,
                        help="Only generate for a specific family prefix (e.g. 'F4', 'H7')")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of MCUs to generate")
    args = parser.parse_args()

    GEN_DIR.mkdir(exist_ok=True)

    # Filter MCU list
    targets = MCUS
    if args.family:
        targets = [(x, s, d) for x, s, d in targets if args.family.upper() in x[:10].upper()]
    if args.limit:
        targets = targets[:args.limit]

    print(f"{'=' * 72}")
    print(f"  STM32 .ato Batch Generator")
    print(f"  Targets: {len(targets)} MCUs")
    print(f"{'=' * 72}")

    results = {"success": [], "gen_fail": [], "build_fail": [], "skipped": []}
    start_time = time.time()

    for i, (xml_name, search, desc) in enumerate(targets):
        # Derive output filename from search term
        part_name = search.split(":")[-1]
        output_name = f"{part_name.lower().replace('stm32', 'stm32')}.ato"
        output_path = GEN_DIR / output_name

        print(f"\n[{i+1}/{len(targets)}] {part_name} — {desc}")

        if args.skip_existing and output_path.exists():
            print(f"  SKIP (already exists)")
            results["skipped"].append(part_name)
            continue

        xml_path = STM32_PIN_DATA / xml_name
        if not xml_path.exists():
            print(f"  ERROR: XML not found: {xml_name}")
            results["gen_fail"].append((part_name, "XML not found"))
            continue

        # Generate
        ok, msg = run_generator(xml_path, search, output_path)
        if not ok:
            print(f"  GEN FAIL: {msg}")
            results["gen_fail"].append((part_name, msg))
            continue

        file_size = output_path.stat().st_size
        print(f"  Generated: {output_name} ({file_size} bytes)")

        # Optional build test
        if args.build_test:
            bok, bmsg = build_test(output_path)
            if bok:
                print(f"  {bmsg}")
                results["success"].append(part_name)
            else:
                print(f"  BUILD FAIL: {bmsg}")
                results["build_fail"].append((part_name, bmsg))
        else:
            results["success"].append(part_name)

    elapsed = time.time() - start_time

    # Summary
    print(f"\n{'=' * 72}")
    print(f"  BATCH COMPLETE — {elapsed:.1f}s elapsed")
    print(f"{'=' * 72}")
    print(f"  Generated OK : {len(results['success'])}")
    print(f"  Gen Failed   : {len(results['gen_fail'])}")
    print(f"  Build Failed : {len(results['build_fail'])}")
    print(f"  Skipped      : {len(results['skipped'])}")
    print(f"{'=' * 72}")

    if results["gen_fail"]:
        print("\n  Generation failures:")
        for name, reason in results["gen_fail"]:
            print(f"    - {name}: {reason[:100]}")

    if results["build_fail"]:
        print("\n  Build failures:")
        for name, reason in results["build_fail"]:
            print(f"    - {name}: {reason[:100]}")

    # Write results JSON for easy inspection
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "elapsed_seconds": round(elapsed, 1),
        "success": results["success"],
        "gen_failures": [{"name": n, "reason": r} for n, r in results["gen_fail"]],
        "build_failures": [{"name": n, "reason": r} for n, r in results["build_fail"]],
        "skipped": results["skipped"],
    }
    report_path = GEN_DIR / "batch_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report: {report_path}")

    return 0 if not results["gen_fail"] and not results["build_fail"] else 1


if __name__ == "__main__":
    sys.exit(main())
