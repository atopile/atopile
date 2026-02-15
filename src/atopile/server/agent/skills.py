"""Local fixed-skill loading for agent prompt injection."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class SkillDoc:
    id: str
    name: str
    description: str
    path: str
    body: str
    sections: dict[str, str]
    mtime: float


@dataclass
class _SkillCacheEntry:
    docs: list[SkillDoc]
    by_path_mtime: dict[str, float]
    loaded_at: float


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, _SkillCacheEntry] = {}


def load_skill_docs(
    *,
    skills_dir: Path,
    ttl_s: float = 10.0,
) -> list[SkillDoc]:
    now = time.time()
    root = str(skills_dir.resolve())
    by_path_mtime = _scan_skill_mtimes(skills_dir)

    with _CACHE_LOCK:
        cached = _CACHE.get(root)
        if (
            cached is not None
            and (now - cached.loaded_at) <= max(0.0, ttl_s)
            and cached.by_path_mtime == by_path_mtime
        ):
            return list(cached.docs)

    docs = _read_skill_docs(skills_dir, by_path_mtime)
    with _CACHE_LOCK:
        _CACHE[root] = _SkillCacheEntry(
            docs=list(docs),
            by_path_mtime=by_path_mtime,
            loaded_at=now,
        )
    return docs


def load_fixed_skill_docs(
    *,
    skills_dir: Path,
    skill_ids: list[str],
    ttl_s: float = 10.0,
) -> tuple[list[SkillDoc], list[str]]:
    docs = load_skill_docs(skills_dir=skills_dir, ttl_s=ttl_s)
    selected: list[SkillDoc] = []
    missing: list[str] = []

    for raw_id in skill_ids:
        requested_id = _normalize_skill_id(str(raw_id))
        if not requested_id:
            continue

        doc = _find_skill_by_id_alias(docs, requested_id)
        if doc is None:
            missing.append(requested_id)
            continue
        if any(existing.id == doc.id for existing in selected):
            continue
        selected.append(doc)

    return selected, missing


def render_fixed_skills_block(
    *,
    docs: list[SkillDoc],
    max_chars: int,
    per_skill_max_chars: dict[str, int] | None = None,
) -> str:
    if not docs:
        return "ACTIVE SKILLS:\n- none"

    sections = ["ACTIVE SKILLS (FULL DOCS):"]
    for doc in docs:
        doc_body = doc.body.strip()
        if per_skill_max_chars is not None:
            skill_cap = int(per_skill_max_chars.get(doc.id, 0))
            if skill_cap > 0:
                doc_body = _truncate(doc_body, skill_cap)
        sections.append(
            "\n".join(
                [
                    f"SKILL {doc.id}",
                    f"Source: {doc.path}",
                    doc_body,
                ]
            ).strip()
        )

    joined = "\n\n".join(sections)
    if max_chars <= 0:
        return ""
    if len(joined) <= max_chars:
        return joined
    return _truncate(joined, max_chars)


def build_fixed_skill_state(
    *,
    skills_dir: Path,
    requested_skill_ids: list[str],
    selected_docs: list[SkillDoc],
    missing_skill_ids: list[str],
    rendered_total_chars: int,
    max_chars: int,
    per_skill_max_chars: dict[str, int] | None = None,
) -> dict[str, Any]:
    normalized_requested_ids = [
        _normalize_skill_id(str(value))
        for value in requested_skill_ids
        if str(value).strip()
    ]
    return {
        "mode": "fixed",
        "skills_dir": str(skills_dir),
        "requested_skill_ids": normalized_requested_ids,
        "selected_skill_ids": [doc.id for doc in selected_docs],
        "selected_skills": [
            {
                "id": doc.id,
                "name": doc.name,
                "path": doc.path,
                "chars": len(doc.body),
            }
            for doc in selected_docs
        ],
        "missing_skill_ids": missing_skill_ids,
        "per_skill_max_chars": (
            {
                _normalize_skill_id(str(skill_id)): int(char_limit)
                for skill_id, char_limit in per_skill_max_chars.items()
            }
            if per_skill_max_chars
            else {}
        ),
        "reasoning": [
            "mode=fixed",
            "requested_ids=" + ",".join(normalized_requested_ids),
            "selected_ids=" + ",".join(doc.id for doc in selected_docs),
            (
                "missing_ids=" + ",".join(missing_skill_ids)
                if missing_skill_ids
                else "missing_ids=<none>"
            ),
            f"rendered_chars={rendered_total_chars}",
            f"max_chars={max_chars}",
        ],
        "total_chars": rendered_total_chars,
        "max_chars": max_chars,
        "generated_at": time.time(),
    }


def _scan_skill_mtimes(skills_dir: Path) -> dict[str, float]:
    if not skills_dir.exists() or not skills_dir.is_dir():
        return {}
    output: dict[str, float] = {}
    for file_path in skills_dir.glob("*/SKILL.md"):
        try:
            output[str(file_path)] = file_path.stat().st_mtime
        except OSError:
            continue
    return output


def _read_skill_docs(
    skills_dir: Path,
    by_path_mtime: dict[str, float],
) -> list[SkillDoc]:
    docs: list[SkillDoc] = []
    for raw_path in sorted(by_path_mtime.keys()):
        path = Path(raw_path)
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            continue

        frontmatter, body = _parse_frontmatter(raw)
        skill_id = _normalize_skill_id(path.parent.name)
        name = str(frontmatter.get("name") or skill_id).strip() or skill_id
        description = str(frontmatter.get("description") or "").strip()
        sections = _parse_sections(body)
        docs.append(
            SkillDoc(
                id=skill_id,
                name=name,
                description=description,
                path=str(path),
                body=body,
                sections=sections,
                mtime=by_path_mtime[raw_path],
            )
        )
    return docs


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(raw)
    if match is None:
        return {}, raw
    fm_text = match.group(1)
    body = raw[match.end() :]
    out: dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        clean_key = key.strip().lower()
        clean_value = value.strip().strip('"').strip("'")
        if clean_key:
            out[clean_key] = clean_value
    return out, body


def _parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    headers = list(_HEADER_RE.finditer(body))
    if not headers:
        return sections
    for index, header in enumerate(headers):
        name = header.group(2).strip()
        start = header.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(body)
        section_body = body[start:end].strip()
        if name:
            sections[name] = section_body
    return sections


def _normalize_skill_id(value: str) -> str:
    cleaned = value.strip().lower().replace("_", "-").replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9\-]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "unknown-skill"


def _find_skill_by_id_alias(docs: list[SkillDoc], alias: str) -> SkillDoc | None:
    normalized_alias = _normalize_skill_id(alias)
    for doc in docs:
        if doc.id == normalized_alias:
            return doc
    alias_variants = {
        normalized_alias.replace("-", "_"),
        normalized_alias.replace("_", "-"),
    }
    for doc in docs:
        if doc.id in alias_variants:
            return doc
    return None


def _truncate(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return value[: max_chars - 3].rstrip() + "..."
