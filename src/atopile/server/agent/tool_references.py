"""Example and package-reference helpers for agent tools."""

from __future__ import annotations

import difflib
import os
from pathlib import Path
from typing import Any

from atopile.config import ProjectConfig
from atopile.server.agent import policy

_PACKAGE_REFERENCE_MAX_FILES_SCANNED = int(
    os.getenv("ATOPILE_AGENT_PACKAGE_REFERENCE_MAX_FILES_SCANNED", "5000")
)
_PACKAGE_REFERENCE_MAX_FILES_SCANNED = max(
    200,
    min(_PACKAGE_REFERENCE_MAX_FILES_SCANNED, 200_000),
)

def _resolve_examples_root(project_root: Path) -> Path:
    """Resolve the curated examples directory used for reference `.ato` code."""
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add_candidate(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        candidates.append(resolved)

    # Prefer workspace-relative discovery first.
    for parent in (project_root, *project_root.parents):
        add_candidate(parent / "examples")

    # Fallback to repository-relative discovery from this source file.
    try:
        repo_root = Path(__file__).resolve().parents[4]
    except IndexError:
        repo_root = Path(__file__).resolve().parent
    add_candidate(repo_root / "examples")

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    raise ValueError(
        "Reference examples directory not found. Expected an 'examples/' folder."
    )


def _collect_example_projects(
    examples_root: Path,
    *,
    include_without_ato_yaml: bool = False,
) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    for child in sorted(examples_root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        ato_yaml = child / "ato.yaml"
        has_ato_yaml = ato_yaml.exists()
        if not has_ato_yaml and not include_without_ato_yaml:
            continue

        ato_files = sorted(
            str(path.relative_to(child))
            for path in child.rglob("*.ato")
            if path.is_file()
        )
        projects.append(
            {
                "name": child.name,
                "path": str(child),
                "has_ato_yaml": has_ato_yaml,
                "ato_files": ato_files,
            }
        )
    return projects


def _resolve_example_project(example_root: Path, example_name: str) -> Path:
    cleaned = str(example_name).strip()
    if not cleaned:
        raise ValueError("example is required")
    if "/" in cleaned or "\\" in cleaned:
        raise ValueError("example must be a top-level example directory name")

    candidate = (example_root / cleaned).resolve()
    if not candidate.is_relative_to(example_root.resolve()):
        raise ValueError("example path escapes examples root")
    if not candidate.exists() or not candidate.is_dir():
        raise ValueError(f"Unknown example: {cleaned}")
    return candidate


def _resolve_example_ato_file(example_project_root: Path, path: str | None) -> Path:
    if isinstance(path, str) and path.strip():
        candidate = (example_project_root / path.strip()).resolve()
        if not candidate.is_relative_to(example_project_root.resolve()):
            raise ValueError("path escapes selected example root")
        if not candidate.exists() or not candidate.is_file():
            raise ValueError(f"Example file does not exist: {path}")
        if candidate.suffix.lower() != ".ato":
            raise ValueError("Only .ato files are supported by examples_read_ato")
        return candidate

    ato_files = sorted(
        candidate
        for candidate in example_project_root.rglob("*.ato")
        if candidate.is_file()
    )
    if not ato_files:
        raise ValueError("No .ato files found in selected example")
    return ato_files[0]


def _search_example_ato_files(
    *,
    examples_root: Path,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    if not needle:
        return []

    matches: list[dict[str, Any]] = []
    projects = _collect_example_projects(
        examples_root,
        include_without_ato_yaml=True,
    )
    for project in projects:
        example_name = str(project["name"])
        project_dir = examples_root / example_name
        for rel_path in project.get("ato_files", []):
            if not isinstance(rel_path, str) or not rel_path:
                continue
            file_path = project_dir / rel_path
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            for line_no, line in enumerate(text.splitlines(), start=1):
                if needle not in line.lower():
                    continue
                matches.append(
                    {
                        "example": example_name,
                        "path": f"{example_name}/{rel_path}",
                        "line": line_no,
                        "text": line.strip()[:260],
                    }
                )
                if len(matches) >= limit:
                    return matches
    return matches


def _resolve_package_reference_roots(project_root: Path) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    def add_root(path: Path | None) -> None:
        if path is None:
            return
        resolved = path.resolve()
        if resolved in seen:
            return
        if not resolved.exists() or not resolved.is_dir():
            return
        seen.add(resolved)
        roots.append(resolved)

    project_cfg = ProjectConfig.from_path(project_root)
    if project_cfg is not None:
        add_root(project_cfg.paths.modules)
    else:
        add_root(project_root / ".ato" / "modules")

    raw_extra_roots = os.getenv("ATOPILE_AGENT_PACKAGE_REFERENCE_ROOTS", "")
    if raw_extra_roots.strip():
        for token in raw_extra_roots.split(","):
            cleaned = token.strip()
            if not cleaned:
                continue
            candidate = Path(cleaned).expanduser()
            if not candidate.is_absolute():
                candidate = (project_root / candidate).resolve()
            add_root(candidate)

    return roots


def _infer_package_reference_metadata(
    *,
    root: Path,
    file_path: Path,
) -> tuple[str | None, str, str]:
    rel = file_path.relative_to(root)
    rel_path = str(rel)
    parts = rel.parts

    if len(parts) >= 3:
        package_identifier = f"{parts[0]}/{parts[1]}"
        path_in_package = str(Path(*parts[2:]))
    else:
        package_identifier = None
        path_in_package = rel_path

    return package_identifier, path_in_package, rel_path


def _iter_package_reference_files(
    *,
    roots: list[Path],
    package_query: str | None = None,
    path_query: str | None = None,
    max_files_scanned: int = _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
) -> tuple[list[dict[str, Any]], int, bool]:
    package_needle = (package_query or "").strip().lower()
    path_needle = (path_query or "").strip().lower()
    scanned = 0
    truncated = False
    records: list[dict[str, Any]] = []

    for root in roots:
        for file_path in root.rglob("*.ato"):
            rel = file_path.relative_to(root)
            if any(part.startswith(".") for part in rel.parts[:-1]):
                continue
            if ".cache" in rel.parts:
                continue

            scanned += 1
            if scanned > max_files_scanned:
                truncated = True
                return records, scanned, truncated

            package_identifier, path_in_package, rel_path = (
                _infer_package_reference_metadata(
                    root=root,
                    file_path=file_path,
                )
            )
            package_value = package_identifier or ""

            if package_needle and package_needle not in package_value.lower():
                continue
            if path_needle and path_needle not in rel_path.lower():
                continue

            records.append(
                {
                    "source_root": str(root),
                    "path": rel_path,
                    "absolute_path": str(file_path),
                    "package_identifier": package_identifier,
                    "path_in_package": path_in_package,
                }
            )

    return records, scanned, truncated


def _list_package_reference_files(
    *,
    project_root: Path,
    package_query: str | None,
    path_query: str | None,
    limit: int,
) -> dict[str, Any]:
    roots = _resolve_package_reference_roots(project_root)
    if not roots:
        return {
            "roots": [],
            "files": [],
            "packages": [],
            "total_files": 0,
            "returned": 0,
            "message": (
                "No package reference roots found. Install dependencies (creating "
                "`.ato/modules`) or configure ATOPILE_AGENT_PACKAGE_REFERENCE_ROOTS."
            ),
        }

    records, scanned, truncated = _iter_package_reference_files(
        roots=roots,
        package_query=package_query,
        path_query=path_query,
    )
    returned = records[:limit]

    package_counts: dict[str, int] = {}
    for record in records:
        package_identifier = record.get("package_identifier")
        key = (
            str(package_identifier)
            if isinstance(package_identifier, str) and package_identifier
            else "<unscoped>"
        )
        package_counts[key] = package_counts.get(key, 0) + 1
    top_packages = sorted(
        package_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )

    return {
        "roots": [str(root) for root in roots],
        "filters": {
            "package_query": package_query,
            "path_query": path_query,
        },
        "files": returned,
        "packages": [
            {"package_identifier": package_identifier, "file_count": count}
            for package_identifier, count in top_packages[:50]
        ],
        "total_files": len(records),
        "returned": len(returned),
        "scanned_files": scanned,
        "scan_truncated": truncated,
        "scan_cap_files": _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
    }


def _search_package_reference_files(
    *,
    project_root: Path,
    query: str,
    package_query: str | None,
    path_query: str | None,
    limit: int,
) -> dict[str, Any]:
    needle = query.strip().lower()
    if not needle:
        return {
            "roots": [],
            "query": query,
            "matches": [],
            "total": 0,
            "scanned_files": 0,
            "scan_truncated": False,
            "scan_cap_files": _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
        }

    roots = _resolve_package_reference_roots(project_root)
    if not roots:
        return {
            "roots": [],
            "query": query,
            "matches": [],
            "total": 0,
            "message": (
                "No package reference roots found. Install dependencies (creating "
                "`.ato/modules`) or configure ATOPILE_AGENT_PACKAGE_REFERENCE_ROOTS."
            ),
        }

    records, scanned, truncated = _iter_package_reference_files(
        roots=roots,
        package_query=package_query,
        path_query=path_query,
    )

    matches: list[dict[str, Any]] = []
    for record in records:
        file_path = Path(str(record["absolute_path"]))
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            if needle not in line.lower():
                continue
            matches.append(
                {
                    "package_identifier": record.get("package_identifier"),
                    "path": record.get("path"),
                    "path_in_package": record.get("path_in_package"),
                    "source_root": record.get("source_root"),
                    "line": line_no,
                    "text": line.strip()[:260],
                }
            )
            if len(matches) >= limit:
                return {
                    "roots": [str(root) for root in roots],
                    "query": query,
                    "filters": {
                        "package_query": package_query,
                        "path_query": path_query,
                    },
                    "matches": matches,
                    "total": len(matches),
                    "scanned_files": scanned,
                    "scan_truncated": truncated,
                    "scan_cap_files": _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
                }

    return {
        "roots": [str(root) for root in roots],
        "query": query,
        "filters": {
            "package_query": package_query,
            "path_query": path_query,
        },
        "matches": matches,
        "total": len(matches),
        "scanned_files": scanned,
        "scan_truncated": truncated,
        "scan_cap_files": _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
    }


def _read_package_reference_file(
    *,
    project_root: Path,
    package_identifier: str,
    path_in_package: str | None,
    start_line: int,
    max_lines: int,
) -> dict[str, Any]:
    roots = _resolve_package_reference_roots(project_root)
    if not roots:
        raise ValueError(
            "No package reference roots found. Install dependencies (creating "
            "`.ato/modules`) or configure ATOPILE_AGENT_PACKAGE_REFERENCE_ROOTS."
        )

    package_clean = package_identifier.strip().strip("/")
    if not package_clean or "/" not in package_clean:
        raise ValueError("package_identifier must look like 'owner/package'")

    rel_hint = (
        str(path_in_package).strip().lstrip("/")
        if isinstance(path_in_package, str) and path_in_package.strip()
        else None
    )

    selected_root: Path | None = None
    selected_file: Path | None = None
    selected_rel_path: str | None = None
    candidates_for_suggestions: list[str] = []
    for root in roots:
        package_root = (root / package_clean).resolve()
        if not package_root.exists() or not package_root.is_dir():
            continue

        candidates_for_suggestions.append(str(package_clean))
        if rel_hint:
            candidate = (package_root / rel_hint).resolve()
            if (
                candidate.exists()
                and candidate.is_file()
                and candidate.suffix.lower() == ".ato"
                and candidate.is_relative_to(package_root)
            ):
                selected_root = root
                selected_file = candidate
                selected_rel_path = str(candidate.relative_to(root))
                break
        else:
            ato_files = sorted(
                path for path in package_root.rglob("*.ato") if path.is_file()
            )
            if ato_files:
                selected_root = root
                selected_file = ato_files[0]
                selected_rel_path = str(ato_files[0].relative_to(root))
                break

    if selected_root is None or selected_file is None or selected_rel_path is None:
        available_records, _, _ = _iter_package_reference_files(roots=roots)
        available_packages = sorted(
            {
                str(record["package_identifier"])
                for record in available_records
                if isinstance(record.get("package_identifier"), str)
                and str(record["package_identifier"]).strip()
            }
        )
        suggestions = difflib.get_close_matches(
            package_clean,
            available_packages,
            n=8,
            cutoff=0.45,
        )
        raise ValueError(
            f"Package reference '{package_clean}' not found."
            + (f" Try one of: {', '.join(suggestions)}" if suggestions else "")
        )

    chunk = policy.read_file_chunk(
        selected_root,
        selected_rel_path,
        start_line=start_line,
        max_lines=max_lines,
    )
    return {
        "package_identifier": package_clean,
        "source_root": str(selected_root),
        "path_in_package": str(Path(selected_rel_path).relative_to(package_clean)),
        **chunk,
    }



