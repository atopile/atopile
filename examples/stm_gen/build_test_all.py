#!/usr/bin/env python3
"""
Build-test all generated .ato files.
Writes main.ato for each, runs `ato build` in the project dir, reports results.
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GEN_DIR = SCRIPT_DIR / "generated"
MAIN_ATO = SCRIPT_DIR / "main.ato"


def build_test_one(ato_file: Path) -> tuple[str, bool, str, float]:
    """Build-test one .ato file. Returns (name, success, message, duration)."""
    t0 = time.time()
    name = ato_file.stem

    content = ato_file.read_text()
    m = re.search(r"^module (\w+):", content, re.MULTILINE)
    if not m:
        return name, False, "No module found", time.time() - t0
    module_name = m.group(1)
    rel_path = ato_file.relative_to(SCRIPT_DIR)

    test_content = f'''"""Build test for {module_name}"""
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("TRAITS")
#pragma experiment("MODULE_TEMPLATING")

import ElectricPower
from "{rel_path}" import {module_name}

module App:
    power_3v3 = new ElectricPower
    mcu = new {module_name}
    power_3v3 ~ mcu.power_3v3
'''
    MAIN_ATO.write_text(test_content)

    try:
        result = subprocess.run(
            ["ato", "build"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(SCRIPT_DIR),
        )
        duration = time.time() - t0
        if result.returncode == 0:
            return name, True, "OK", duration
        else:
            err = result.stderr.strip() or result.stdout.strip()
            lines = [line.strip() for line in err.split("\n") if line.strip()]
            error_msg = "Unknown error"
            for line in lines:
                if "error" in line.lower() or "Error" in line:
                    error_msg = line[:200]
                    break
            if error_msg == "Unknown error" and lines:
                error_msg = lines[-1][:200]
            return name, False, error_msg, duration
    except subprocess.TimeoutExpired:
        return name, False, "TIMEOUT", time.time() - t0
    except Exception as e:
        return name, False, str(e)[:200], time.time() - t0


def main():
    ato_files = sorted(GEN_DIR.glob("*.ato"))
    # Skip non-ato files like JSON reports
    ato_files = [f for f in ato_files if f.suffix == ".ato"]
    if not ato_files:
        print("No .ato files found in generated/")
        return 1

    print(f"Build-testing {len(ato_files)} files sequentially...")
    print("=" * 72)

    results = []
    start = time.time()

    for i, f in enumerate(ato_files):
        name, ok, msg, dur = build_test_one(f)
        status = "PASS" if ok else "FAIL"
        details = "" if ok else f" {msg}"
        print(
            f"  [{i + 1:2d}/{len(ato_files)}] [{status}] "
            f"{name:30s} ({dur:.1f}s){details}"
        )
        results.append({"name": name, "ok": ok, "msg": msg, "duration": round(dur, 1)})

    elapsed = time.time() - start
    passed = sum(1 for r in results if r["ok"])
    failed = sum(1 for r in results if not r["ok"])

    print("=" * 72)
    print(f"  {passed} passed, {failed} failed — {elapsed:.1f}s total")
    print("=" * 72)

    if failed:
        print("\n  Failures:")
        for r in results:
            if not r["ok"]:
                print(f"    {r['name']}: {r['msg']}")

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "elapsed": round(elapsed, 1),
        "results": sorted(results, key=lambda x: x["name"]),
    }
    report_path = GEN_DIR / "build_test_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report: {report_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
