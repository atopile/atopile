"""Create a fast development worktree with cloned .venv and Zig artifacts.

Python rewrite of scripts/worktree_fast.sh.
"""

import shutil
import subprocess
from pathlib import Path


def _log(msg: str) -> None:
    print(f"[worktree] {msg}")


def _resolve_main_worktree(repo_path: Path) -> Path:
    """Return the path of the main (first) git worktree."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree "):])
    raise RuntimeError("failed to detect main worktree path")


def _clone_dir(src: Path, dst: Path, *, force: bool = False) -> None:
    """Clone a directory tree."""
    if not src.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {src}")

    if dst.exists() or dst.is_symlink():
        if force:
            shutil.rmtree(dst)
        else:
            raise FileExistsError(f"{dst} already exists (use --force)")

    shutil.copytree(src, dst, symlinks=True)
    _log(f"cloned: {dst}")


def _rewrite_venv_paths(source_root: Path, worktree_path: Path) -> None:
    """Rewrite absolute paths in the cloned venv from source_root to worktree_path."""
    venv = worktree_path / ".venv"
    source_str = str(source_root)
    dest_str = str(worktree_path)

    # 1. Rewrite .pth files (editable install source paths)
    site_packages = None
    for sp in (venv / "lib").glob("python*/site-packages"):
        site_packages = sp
        break

    if site_packages:
        for pth in site_packages.glob("_atopile*.pth"):
            text = pth.read_text()
            if source_str in text:
                pth.write_text(text.replace(source_str, dest_str))
                _log(f"rewrote: {pth}")

        # 2. Rewrite direct_url.json (PEP 660 editable metadata)
        for durl in site_packages.glob("atopile*.dist-info/direct_url.json"):
            text = durl.read_text()
            if source_str in text:
                durl.write_text(text.replace(source_str, dest_str))
                _log(f"rewrote: {durl}")

    # 3. Rewrite shebangs in all venv bin scripts
    count = 0
    bin_dir = venv / "bin"
    if bin_dir.is_dir():
        for script in bin_dir.iterdir():
            if not script.is_file():
                continue
            try:
                data = script.read_bytes()
                # Skip binary files (check for null bytes in first 512 bytes)
                if b"\x00" in data[:512]:
                    continue
                text = data.decode("utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            if source_str in text:
                script.write_text(text.replace(source_str, dest_str))
                count += 1
    _log(f"rewrote shebangs/paths in {count} scripts under .venv/bin/")

    # 4. Rewrite pyvenv.cfg if it references the source root
    pyvenv_cfg = venv / "pyvenv.cfg"
    if pyvenv_cfg.is_file():
        text = pyvenv_cfg.read_text()
        if source_str in text:
            pyvenv_cfg.write_text(text.replace(source_str, dest_str))
            _log(f"rewrote: {pyvenv_cfg}")


def _create_helper_files(worktree_path: Path) -> None:
    """Create .atopile-worktree-env.sh and ato wrapper script."""
    env_sh = worktree_path / ".atopile-worktree-env.sh"
    env_sh.write_text(
        '#!/usr/bin/env sh\n'
        'WORKTREE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"\n'
        'export PYTHONPATH="$WORKTREE_ROOT/src:$WORKTREE_ROOT/tools/'
        'atopile_mkdocs_plugin${PYTHONPATH:+:$PYTHONPATH}"\n'
    )
    env_sh.chmod(0o755)

    ato_wrapper = worktree_path / "ato"
    ato_wrapper.write_text(
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        'WORKTREE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        'source "$WORKTREE_ROOT/.atopile-worktree-env.sh"\n'
        'exec "$WORKTREE_ROOT/.venv/bin/ato" "$@"\n'
    )
    ato_wrapper.chmod(0o755)


def create_worktree(
    name: str,
    *,
    path: Path | None = None,
    start_point: str = "HEAD",
    base_dir: Path | None = None,
    source_root: Path | None = None,
    force: bool = False,
    skip_editable_install: bool = False,
) -> None:
    """Create a fast development worktree with cloned .venv and Zig artifacts."""
    # Resolve current repo root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    current_root = result.stdout.strip() if result.returncode == 0 else ""
    if not current_root:
        raise RuntimeError("run this inside a git repository")

    current_root = Path(current_root)

    # Resolve source root (main worktree)
    if source_root is None:
        source_root = _resolve_main_worktree(current_root)
    source_root = source_root.resolve()

    if not (source_root / ".git").exists():
        raise RuntimeError(f"source root is not a git worktree: {source_root}")
    if not (source_root / ".venv").is_dir():
        raise RuntimeError(f"source root does not have .venv: {source_root / '.venv'}")

    # Determine worktree path
    if path is None:
        if base_dir is None:
            base_dir = source_root.parent
        worktree_path = base_dir / name
    else:
        worktree_path = path

    if worktree_path.exists():
        raise RuntimeError(f"target worktree path already exists: {worktree_path}")

    _log(f"main worktree: {source_root}")
    _log(f"new worktree:  {worktree_path}")
    _log(f"start point:   {start_point}")

    # Create git worktree
    branch_exists = subprocess.run(
        ["git", "-C", str(source_root), "show-ref", "--verify", "--quiet",
         f"refs/heads/{name}"],
        capture_output=True,
    ).returncode == 0

    if branch_exists:
        _log(f"branch '{name}' already exists; creating worktree on existing branch")
        subprocess.run(
            ["git", "-C", str(source_root), "worktree", "add",
             str(worktree_path), name],
            check=True,
        )
    else:
        _log(f"creating branch '{name}' from '{start_point}'")
        subprocess.run(
            ["git", "-C", str(source_root), "worktree", "add", "-b", name,
             str(worktree_path), start_point],
            check=True,
        )

    # Clone .venv
    _log("cloning venv")
    _clone_dir(source_root / ".venv", worktree_path / ".venv", force=force)

    # Clone zig-out if it exists
    zig_out_src = source_root / "src" / "faebryk" / "core" / "zig" / "zig-out"
    if zig_out_src.is_dir():
        zig_out_dst = worktree_path / "src" / "faebryk" / "core" / "zig" / "zig-out"
        _clone_dir(zig_out_src, zig_out_dst, force=force)

        # Write source hash so build-on-import skips the expensive zig build
        _log("computing zig source hash")
        zig_dir = worktree_path / "src" / "faebryk" / "core" / "zig"

        # Import directly — compute_hash is stdlib-only, no faebryk deps
        from faebryk.core.zig.compute_hash import compute_source_hash

        source_hash = compute_source_hash(zig_dir=zig_dir)

        hash_file = zig_out_dst / "lib" / ".zig-source-hash"
        hash_file.parent.mkdir(parents=True, exist_ok=True)
        hash_file.write_text(source_hash)
        _log(f"wrote zig source hash: {source_hash}")
    else:
        _log("zig-out not found in source tree; skipping zig-out clone")

    # Create helper files
    _create_helper_files(worktree_path)

    # Rewrite venv paths
    if not skip_editable_install:
        _log(f"rewriting venv paths: {source_root} -> {worktree_path}")
        _rewrite_venv_paths(source_root, worktree_path)
    else:
        _log("skipping venv path rewrite (--skip-editable-install)")

    print(f"""
Done.
Use this worktree with:
  cd {worktree_path}
  . ./.atopile-worktree-env.sh
  ./ato --help

Notes:
  - This creates an isolated venv clone for the worktree.
  - Venv paths are rewritten in-place (no recompile needed).""")
