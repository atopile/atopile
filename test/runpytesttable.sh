#!/bin/bash

pytest -rA -vv "$@" 2>&1 \
  | sed -n '/short test summary info/,$p' \
  | python -c 'import sys
from collections import defaultdict

groups = defaultdict(list)

for raw in sys.stdin:
    line = raw.rstrip("\n")
    if not line.startswith("FAILED "):
        continue

    # Strip leading "FAILED "
    rest = line[6:]

    if " - " in rest:
        test_part, msg = rest.split(" - ", 1)
        key = msg.strip()
    else:
        key = rest.strip()

    groups[key].append(line)

if not groups:
    print("No FAILED lines found.")
    raise SystemExit

for message, lines in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    print(f"{len(lines):3} × {message}")
    for l in lines:
        print(f"    {l}")
    print()'