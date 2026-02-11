"""Compute a deterministic hash of zig source files + build config.

Standalone script (stdlib only, no faebryk imports) so it can be used from:
- build-on-import (zig/__init__.py)
- worktree creation (atopile/worktree.py)
- CI cache key (.github/workflows/pytest.yml)
- CMake POST_BUILD (CMakeLists.txt)
"""

import hashlib
import os
from pathlib import Path


def compute_source_hash(
    zig_dir: Path | None = None,
    release_mode: str | None = None,
) -> str:
    """Hash all zig source files + build config to detect changes."""
    if zig_dir is None:
        zig_dir = Path(__file__).parent
    if release_mode is None:
        release_mode = os.environ.get("FBRK_ZIG_RELEASEMODE", "ReleaseFast")
    h = hashlib.sha256()
    zig_files = sorted([*(zig_dir / "src").rglob("*.zig"), zig_dir / "build.zig"])
    for path in zig_files:
        h.update(path.relative_to(zig_dir).as_posix().encode())
        h.update(path.read_bytes())
    h.update(release_mode.encode())
    return h.hexdigest()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-o", "--output", type=Path, help="Write hash to file")
    p.add_argument("--zig-dir", type=Path, help="Zig source directory")
    args = p.parse_args()
    h = compute_source_hash(zig_dir=args.zig_dir)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(h)
    else:
        print(h)
