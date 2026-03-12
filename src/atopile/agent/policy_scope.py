"""Project scope and file-list helpers for agent policy."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from atopile.dataclasses import AppContext

_ALLOWED_EXTENSIONS = {
    ".ato",
    ".py",
    ".pyi",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".sh",
}

_EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "__pycache__",
    ".ato",
    "build",
    "node_modules",
    "dist",
    "coverage",
}

_MAX_CONTEXT_FILE_BYTES = 180_000


def resolve_project_root(
    project_root: str,
    ctx: AppContext,
    *,
    scope_error_cls: type[Exception],
) -> Path:
    root = Path(project_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise scope_error_cls(f"Project root does not exist: {project_root}")

    if ctx.workspace_paths:
        allowed = [p.expanduser().resolve() for p in ctx.workspace_paths]
        if not any(root.is_relative_to(ws) or root == ws for ws in allowed):
            raise scope_error_cls("Project root is outside the current workspace scope")

    ato_yaml = root / "ato.yaml"
    if not ato_yaml.exists():
        raise scope_error_cls(f"No ato.yaml found in project root: {project_root}")

    return root


def resolve_scoped_path(
    project_root: Path,
    path: str,
    *,
    scope_error_cls: type[Exception],
) -> Path:
    raw = Path(path).expanduser()
    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        candidate = (project_root / raw).resolve()

    if not candidate.is_relative_to(project_root):
        raise scope_error_cls(f"Path is outside project scope: {path}")

    return candidate


def package_path_aliases(path: str) -> list[str]:
    """Return compatible package path aliases for historical layouts."""
    raw = Path(path)
    parts = raw.parts
    aliases: list[str] = []

    if len(parts) >= 3 and parts[0] == ".ato" and parts[1] in {"deps", "packages"}:
        aliases.append(str(Path(".ato", "modules", *parts[2:])))

    if parts and parts[0] != ".ato":
        aliases.append(str(Path(".ato", "modules", *parts)))

    deduped: list[str] = []
    for alias in aliases:
        if alias != path and alias not in deduped:
            deduped.append(alias)
    return deduped


def resolve_readable_file_path(
    project_root: Path,
    path: str,
    *,
    resolve_scoped_path_fn: Callable[[Path, str], Path],
    scope_error_cls: type[Exception],
) -> tuple[Path, str]:
    """Resolve a readable in-scope file path with package-path compatibility."""
    candidates = [path, *package_path_aliases(path)]
    resolved_attempts: list[tuple[str, Path]] = []
    for candidate_path in candidates:
        candidate = resolve_scoped_path_fn(project_root, candidate_path)
        resolved_attempts.append((candidate_path, candidate))
        if candidate.exists() and candidate.is_file():
            return candidate, candidate_path

    for candidate_path, candidate in resolved_attempts:
        parent = candidate.parent
        if candidate.suffix.lower() != ".ato":
            continue
        if not parent.exists() or not parent.is_dir():
            continue
        ato_files = sorted(p for p in parent.glob("*.ato") if p.is_file())
        if len(ato_files) == 1:
            return ato_files[0], candidate_path

    suggestion_candidates: list[str] = []
    for candidate_path, candidate in resolved_attempts:
        if candidate_path != path:
            suggestion_candidates.append(candidate_path)

        parent = candidate.parent
        if parent.exists() and parent.is_dir():
            for ato_file in sorted(parent.glob("*.ato"))[:3]:
                if not ato_file.is_file():
                    continue
                rel = str(ato_file.relative_to(project_root))
                suggestion_candidates.append(rel)

    seen: set[str] = set()
    suggestions: list[str] = []
    for suggestion in suggestion_candidates:
        if suggestion in seen:
            continue
        seen.add(suggestion)
        suggestions.append(suggestion)

    if suggestions:
        hint = ", ".join(suggestions[:4])
        raise scope_error_cls(f"File does not exist: {path}. Try: {hint}")
    raise scope_error_cls(f"File does not exist: {path}")


def is_context_file(path: Path, project_root: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() not in _ALLOWED_EXTENSIONS:
        return False
    if path.stat().st_size > _MAX_CONTEXT_FILE_BYTES:
        return False
    for part in path.relative_to(project_root).parts:
        if part in _EXCLUDED_DIR_NAMES:
            return False
    return True


def list_context_files(project_root: Path, limit: int = 300) -> list[str]:
    results: list[str] = []
    for file_path in sorted(project_root.rglob("*")):
        if len(results) >= limit:
            break
        if not is_context_file(file_path, project_root):
            continue
        results.append(str(file_path.relative_to(project_root)))
    return results
