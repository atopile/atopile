#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scripts/worktree_fast.sh <name> [--start-point <ref>] [--base-dir <dir>] [--source-root <path>] [--force] [--skip-editable-install]
  scripts/worktree_fast.sh <name> --path <worktree-path> [--start-point <ref>] [--source-root <path>] [--force] [--skip-editable-install]

Creates a git worktree optimized for atopile development by reusing:
  - main tree virtualenv via CoW clone (isolated on write)
  - zig build cache via CoW clone
  - zig outputs via CoW clone

It also writes:
  - .atopile-worktree-env.sh (exports PYTHONPATH + ZIG_NORECOMPILE=1)
  - ato (wrapper that runs .venv/bin/ato with the env above)
  - editable install for this worktree via: python -m pip install -e <worktree>
EOF
}

die() {
    echo "error: $*" >&2
    exit 1
}

log() {
    echo "[worktree-fast] $*"
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

resolve_main_worktree() {
    git -C "$1" worktree list --porcelain | awk '/^worktree /{print substr($0, 10); exit}'
}

cow_clone_dir() {
    local src_dir="$1"
    local dst_dir="$2"
    local force="$3"

    if [[ ! -d "$src_dir" ]]; then
        return 1
    fi

    if [[ -e "$dst_dir" || -L "$dst_dir" ]]; then
        if [[ "$force" == "1" ]]; then
            rm -rf "$dst_dir"
        else
            die "$dst_dir already exists (use --force)"
        fi
    fi

    if cp -a --reflink=always "$src_dir" "$dst_dir" 2>/dev/null; then
        log "CoW cloned: $dst_dir (GNU cp reflink)"
        return 0
    fi

    if cp -R -c "$src_dir" "$dst_dir" 2>/dev/null; then
        log "CoW cloned: $dst_dir (BSD cp clonefile)"
        return 0
    fi

    log "CoW clone not available for $dst_dir; using full copy"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete "$src_dir/" "$dst_dir/"
    else
        cp -R "$src_dir" "$dst_dir"
    fi
    return 0
}

create_helper_files() {
    local worktree_path="$1"

    cat >"$worktree_path/.atopile-worktree-env.sh" <<'EOF'
#!/usr/bin/env sh
WORKTREE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export PYTHONPATH="$WORKTREE_ROOT/src:$WORKTREE_ROOT/tools/atopile_mkdocs_plugin${PYTHONPATH:+:$PYTHONPATH}"
export ZIG_NORECOMPILE="${ZIG_NORECOMPILE:-1}"
EOF
    chmod +x "$worktree_path/.atopile-worktree-env.sh"

    cat >"$worktree_path/ato" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
WORKTREE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$WORKTREE_ROOT/.atopile-worktree-env.sh"
exec "$WORKTREE_ROOT/.venv/bin/ato" "$@"
EOF
    chmod +x "$worktree_path/ato"
}

install_editable() {
    local worktree_path="$1"
    local python_bin="$worktree_path/.venv/bin/python"

    if "$python_bin" -m pip --version >/dev/null 2>&1; then
        "$python_bin" -m pip install -e "$worktree_path"
        return 0
    fi

    if command -v uv >/dev/null 2>&1; then
        uv pip install --python "$python_bin" -e "$worktree_path"
        return 0
    fi

    log "pip not found in worktree venv; trying ensurepip"
    "$python_bin" -m ensurepip --upgrade
    "$python_bin" -m pip install -e "$worktree_path"
}

NAME=""
WORKTREE_PATH=""
START_POINT="HEAD"
BASE_DIR=""
SOURCE_ROOT=""
FORCE=0
SKIP_EDITABLE_INSTALL=0

while [[ $# -gt 0 ]]; do
    case "$1" in
    -h | --help)
        usage
        exit 0
        ;;
    --path)
        [[ $# -ge 2 ]] || die "--path requires a value"
        WORKTREE_PATH="$2"
        shift 2
        ;;
    --start-point)
        [[ $# -ge 2 ]] || die "--start-point requires a value"
        START_POINT="$2"
        shift 2
        ;;
    --base-dir)
        [[ $# -ge 2 ]] || die "--base-dir requires a value"
        BASE_DIR="$2"
        shift 2
        ;;
    --source-root)
        [[ $# -ge 2 ]] || die "--source-root requires a value"
        SOURCE_ROOT="$2"
        shift 2
        ;;
    --force)
        FORCE=1
        shift
        ;;
    --skip-editable-install)
        SKIP_EDITABLE_INSTALL=1
        shift
        ;;
    --*)
        die "unknown option: $1"
        ;;
    *)
        if [[ -z "$NAME" ]]; then
            NAME="$1"
            shift
        else
            die "unexpected argument: $1"
        fi
        ;;
    esac
done

[[ -n "$NAME" ]] || {
    usage
    exit 1
}

require_cmd git
require_cmd awk

CURRENT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$CURRENT_ROOT" ]] || die "run this inside a git repository"

if [[ -z "$SOURCE_ROOT" ]]; then
    SOURCE_ROOT="$(resolve_main_worktree "$CURRENT_ROOT")"
fi
[[ -n "$SOURCE_ROOT" ]] || die "failed to detect main worktree path"
SOURCE_ROOT="$(cd "$SOURCE_ROOT" && pwd)"

[[ -d "$SOURCE_ROOT/.git" || -f "$SOURCE_ROOT/.git" ]] || die "source root is not a git worktree: $SOURCE_ROOT"
[[ -d "$SOURCE_ROOT/.venv" ]] || die "source root does not have .venv: $SOURCE_ROOT/.venv"

if [[ -z "$WORKTREE_PATH" ]]; then
    if [[ -z "$BASE_DIR" ]]; then
        BASE_DIR="$(dirname "$SOURCE_ROOT")"
    fi
    WORKTREE_PATH="$BASE_DIR/$NAME"
fi

if [[ -e "$WORKTREE_PATH" ]]; then
    die "target worktree path already exists: $WORKTREE_PATH"
fi

log "main worktree: $SOURCE_ROOT"
log "new worktree:  $WORKTREE_PATH"
log "start point:   $START_POINT"

if git -C "$SOURCE_ROOT" show-ref --verify --quiet "refs/heads/$NAME"; then
    log "branch '$NAME' already exists; creating worktree on existing branch"
    git -C "$SOURCE_ROOT" worktree add "$WORKTREE_PATH" "$NAME"
else
    log "creating branch '$NAME' from '$START_POINT'"
    git -C "$SOURCE_ROOT" worktree add -b "$NAME" "$WORKTREE_PATH" "$START_POINT"
fi

log "cloning venv (CoW if supported)"
cow_clone_dir "$SOURCE_ROOT/.venv" "$WORKTREE_PATH/.venv" "$FORCE" || die "failed to clone .venv"

if [[ -d "$SOURCE_ROOT/src/faebryk/core/zig/.zig-cache" ]]; then
    cow_clone_dir \
        "$SOURCE_ROOT/src/faebryk/core/zig/.zig-cache" \
        "$WORKTREE_PATH/src/faebryk/core/zig/.zig-cache" \
        "$FORCE" || die "failed to clone zig cache"
else
    log "zig cache not found in source tree; skipping cache clone"
fi

if [[ -d "$SOURCE_ROOT/src/faebryk/core/zig/zig-out" ]]; then
    cow_clone_dir \
        "$SOURCE_ROOT/src/faebryk/core/zig/zig-out" \
        "$WORKTREE_PATH/src/faebryk/core/zig/zig-out" \
        "$FORCE" || die "failed to clone zig-out"
else
    log "zig-out not found in source tree; skipping zig-out clone"
fi

create_helper_files "$WORKTREE_PATH"

if [[ "$SKIP_EDITABLE_INSTALL" == "0" ]]; then
    log "installing editable package into worktree venv"
    install_editable "$WORKTREE_PATH"
else
    log "skipping editable install (--skip-editable-install)"
fi

cat <<EOF

Done.
Use this worktree with:
  cd $WORKTREE_PATH
  . ./.atopile-worktree-env.sh
  ./ato --help

Notes:
  - This creates an isolated venv clone for the worktree.
  - Clone is CoW when supported by your filesystem/tools, otherwise a full copy.
  - Editable install is scoped to this worktree.
EOF
