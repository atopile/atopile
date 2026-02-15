"""Local skill loading and compact skill-card selection for agent prompts."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_\-./]{1,}", re.IGNORECASE)
_PATH_RE = re.compile(r"\b(?:src|test|tools|docs)/[A-Za-z0-9_./-]+\b")
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$", re.MULTILINE)
_CODEBLOCK_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class SkillDoc:
    id: str
    name: str
    description: str
    path: str
    body: str
    sections: dict[str, str]
    mtime: float


@dataclass(frozen=True)
class SkillCard:
    id: str
    name: str
    score: float
    text: str
    chars: int


@dataclass(frozen=True)
class SkillSelection:
    cards: list[SkillCard]
    reasoning: list[str]
    skills_dir: str
    total_chars: int


@dataclass
class _SkillCacheEntry:
    docs: list[SkillDoc]
    by_path_mtime: dict[str, float]
    loaded_at: float


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, _SkillCacheEntry] = {}

_DEFAULT_TOOLS_BY_SKILL: dict[str, list[str]] = {
    "domain-layer": ["build_run", "build_logs_search", "manufacturing_generate"],
    "compiler": ["project_read_file", "build_run", "design_diagnostics"],
    "lsp": ["project_list_modules", "project_module_children", "project_read_file"],
    "library": ["stdlib_list", "stdlib_get_item", "parts_search"],
    "graph": ["project_list_modules", "project_module_children"],
    "solver": ["report_variables", "design_diagnostics", "build_logs_search"],
    "dev": ["project_read_file", "project_edit_file", "build_run"],
}
_FIXED_SKILL_ID_ALIASES: dict[str, tuple[str, ...]] = {
    # Migration alias: allow runtime to request `ato` while legacy skill id
    # still exists as `ato-language`.
    "ato": ("ato-language",),
}


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
            for alias in _FIXED_SKILL_ID_ALIASES.get(requested_id, ()):
                doc = _find_skill_by_id_alias(docs, alias)
                if doc is not None:
                    break

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
) -> str:
    if not docs:
        return "ACTIVE SKILLS:\n- none"

    sections = ["ACTIVE SKILLS (FULL DOCS):"]
    for doc in docs:
        sections.append(
            "\n".join(
                [
                    f"SKILL {doc.id}",
                    f"Source: {doc.path}",
                    doc.body.strip(),
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
        "reasoning": [
            "mode=fixed",
            "requested_ids=" + ",".join(normalized_requested_ids),
            "selected_ids=" + ",".join(doc.id for doc in selected_docs),
            "missing_ids=" + ",".join(missing_skill_ids)
            if missing_skill_ids
            else "missing_ids=<none>",
            f"rendered_chars={rendered_total_chars}",
            f"max_chars={max_chars}",
        ],
        "total_chars": rendered_total_chars,
        "max_chars": max_chars,
        "generated_at": time.time(),
    }


def select_skills_for_turn(
    *,
    skills_dir: Path,
    user_message: str,
    selected_targets: list[str],
    history: list[dict[str, str]] | None,
    tool_memory: dict[str, dict[str, Any]] | None,
    top_k: int = 3,
    per_card_max_chars: int = 1800,
    total_max_chars: int = 6000,
    ttl_s: float = 10.0,
) -> SkillSelection:
    docs = load_skill_docs(skills_dir=skills_dir, ttl_s=ttl_s)
    if not docs:
        return SkillSelection(
            cards=[],
            reasoning=["No local skills found; using base prompt only."],
            skills_dir=str(skills_dir),
            total_chars=0,
        )

    features = _collect_turn_features(
        user_message=user_message,
        selected_targets=selected_targets,
        history=history or [],
        tool_memory=tool_memory or {},
    )
    scored = _score_skills(docs, features)

    selected: list[tuple[SkillDoc, float]] = []
    baseline_ids = {"dev", "domain-layer"}
    for baseline in baseline_ids:
        maybe_doc = _find_skill_by_id_alias(docs, baseline)
        if maybe_doc is None:
            continue
        maybe_score = next(
            (score for doc, score in scored if doc.id == maybe_doc.id),
            0.0,
        )
        selected.append((maybe_doc, maybe_score))

    for doc, score in scored:
        if any(existing.id == doc.id for existing, _ in selected):
            continue
        selected.append((doc, score))
        non_baseline_count = len(
            [item for item in selected if item[0].id not in baseline_ids]
        )
        if non_baseline_count >= max(1, top_k):
            break

    cards: list[SkillCard] = []
    total_chars_used = 0
    for doc, score in selected:
        remaining = max(0, total_max_chars - total_chars_used)
        if remaining <= 0:
            break
        card_budget = min(per_card_max_chars, remaining)
        text = _build_skill_card_text(doc=doc, score=score, max_chars=card_budget)
        chars = len(text)
        if chars <= 0:
            continue
        cards.append(
            SkillCard(
                id=doc.id,
                name=doc.name,
                score=score,
                text=text,
                chars=chars,
            )
        )
        total_chars_used += chars

    reasoning = _build_selection_reasoning(cards=cards, features=features, docs=docs)
    return SkillSelection(
        cards=cards,
        reasoning=reasoning,
        skills_dir=str(skills_dir),
        total_chars=total_chars_used,
    )


def render_active_skills_block(selection: SkillSelection) -> str:
    if not selection.cards:
        return "ACTIVE SKILLS:\n- none"
    lines: list[str] = ["ACTIVE SKILLS:"]
    for card in selection.cards:
        lines.append(card.text)
    return "\n\n".join(lines)


def build_skill_state(selection: SkillSelection) -> dict[str, Any]:
    return {
        "skills_dir": selection.skills_dir,
        "selected_skill_ids": [card.id for card in selection.cards],
        "selected_skills": [
            {
                "id": card.id,
                "name": card.name,
                "score": round(card.score, 3),
                "chars": card.chars,
            }
            for card in selection.cards
        ],
        "reasoning": selection.reasoning,
        "total_chars": selection.total_chars,
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


def _collect_turn_features(
    *,
    user_message: str,
    selected_targets: list[str],
    history: list[dict[str, str]],
    tool_memory: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    history_text = " ".join(
        str(item.get("content", "")) for item in history[-4:] if isinstance(item, dict)
    )
    failed_tool_text = " ".join(
        str(value.get("summary", ""))
        for value in tool_memory.values()
        if isinstance(value, dict) and not bool(value.get("ok", True))
    )
    combined = " ".join(
        [
            user_message or "",
            history_text,
            failed_tool_text,
            " ".join(selected_targets),
        ]
    )
    tokens = [token.lower() for token in _WORD_RE.findall(combined)]
    return {
        "tokens": tokens,
        "token_set": set(tokens),
        "selected_targets": [target.lower() for target in selected_targets],
        "user_message": user_message.lower(),
    }


def _score_skills(
    docs: list[SkillDoc],
    features: dict[str, Any],
) -> list[tuple[SkillDoc, float]]:
    token_set: set[str] = set(features.get("token_set", set()))
    selected_targets: list[str] = list(features.get("selected_targets", []))
    scored: list[tuple[SkillDoc, float]] = []
    for doc in docs:
        score = 0.0
        doc_name_words = set(word.lower() for word in _WORD_RE.findall(doc.name))
        desc_words = set(word.lower() for word in _WORD_RE.findall(doc.description))
        body_words = set(word.lower() for word in _WORD_RE.findall(doc.body[:2400]))
        score += 4.0 * len(token_set & doc_name_words)
        score += 3.0 * len(token_set & desc_words)
        score += 2.0 * len(token_set & body_words)
        if doc.id in token_set:
            score += 5.0
        if any(doc.id in target for target in selected_targets):
            score += 2.0
        scored.append((doc, score))
    scored.sort(key=lambda item: (item[1], item[0].id), reverse=True)
    return scored


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


def _build_skill_card_text(*, doc: SkillDoc, score: float, max_chars: int) -> str:
    tools = ", ".join(_preferred_tools_for_skill(doc))
    do_rules = _extract_bullets(
        doc=doc,
        section_names=[
            "Best Practices",
            "Core Invariants",
            "How to Work With / Develop / Test",
        ],
        fallback=(
            "Follow module invariants and validate with targeted checks "
            "before broad retries."
        ),
    )
    avoid_rules = _extract_avoid_rule(doc)
    key_files = ", ".join(sorted(set(_PATH_RE.findall(doc.body)))[:5]) or doc.path
    quickstart = _extract_quickstart(doc)

    lines = [
        f"SKILL {doc.id} (score={score:.1f})",
        "Use when: "
        + _truncate(
            doc.description or "This module is relevant for the current request.",
            220,
        ),
        f"Preferred tools: {tools}",
        f"Do: {_truncate(do_rules, 320)}",
        f"Avoid: {_truncate(avoid_rules, 220)}",
        f"Key files: {_truncate(key_files, 240)}",
        f"Quickstart: {_truncate(quickstart, 320)}",
    ]
    text = "\n".join(lines)
    if len(text) <= max(64, max_chars):
        return text
    return _truncate(text, max(64, max_chars))


def _preferred_tools_for_skill(doc: SkillDoc) -> list[str]:
    default_tools = _DEFAULT_TOOLS_BY_SKILL.get(doc.id)
    if default_tools:
        return default_tools
    return ["project_read_file", "project_edit_file", "build_run"]


def _extract_bullets(
    *,
    doc: SkillDoc,
    section_names: list[str],
    fallback: str,
) -> str:
    for section_name in section_names:
        content = doc.sections.get(section_name)
        if not content:
            continue
        bullets = [match.group(1).strip() for match in _BULLET_RE.finditer(content)]
        if bullets:
            return "; ".join(bullets[:3])
    return fallback


def _extract_avoid_rule(doc: SkillDoc) -> str:
    body = doc.body.lower()
    if "never" in body:
        return "Avoid violating explicit NEVER rules in this skill."
    if "do not" in body:
        return "Avoid actions this skill marks as 'do not'."
    return "Avoid bypassing module-specific invariants or scope boundaries."


def _extract_quickstart(doc: SkillDoc) -> str:
    quickstart = doc.sections.get("Quick Start", "")
    if quickstart:
        codeblock = _CODEBLOCK_RE.search(quickstart)
        if codeblock is not None:
            return " ".join(
                line.strip() for line in codeblock.group(1).splitlines() if line.strip()
            )
        summary = " ".join(
            line.strip() for line in quickstart.splitlines() if line.strip()
        )
        if summary:
            return summary
    return (
        "Inspect key files, then use the relevant project/build tools "
        "for the requested change."
    )


def _build_selection_reasoning(
    *,
    cards: list[SkillCard],
    features: dict[str, Any],
    docs: list[SkillDoc],
) -> list[str]:
    if not cards:
        return ["No skills selected."]
    token_count = len(features.get("tokens", []))
    lines = [
        f"selected={len(cards)} of {len(docs)} skills",
        f"feature_tokens={token_count}",
        "selected_ids=" + ",".join(card.id for card in cards),
    ]
    return lines


def _truncate(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return value[: max_chars - 3].rstrip() + "..."


# Colocated tests moved from `test/server/agent/test_agent_skills.py`.
try:
    import pytest
except Exception:  # pragma: no cover - runtime deployments may omit pytest
    pytest = None

if pytest is not None:
    import time
    from pathlib import Path

    from atopile.server.agent import skills

    def _write_skill(
        root: Path,
        skill_id: str,
        *,
        name: str,
        description: str,
        quickstart: str,
        best_practice: str,
    ) -> None:
        skill_dir = root / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            (
                "---\n"
                f"name: {name}\n"
                f'description: "{description}"\n'
                "---\n\n"
                f"# {name}\n\n"
                "## Quick Start\n\n"
                f"{quickstart}\n\n"
                "## Best Practices\n\n"
                f"- {best_practice}\n\n"
                "## Relevant Files\n\n"
                "- src/atopile/lsp/lsp_server.py\n"
            ),
            encoding="utf-8",
        )

    def _test_load_skill_docs_parses_frontmatter_and_sections(tmp_path: Path) -> None:
        _write_skill(
            tmp_path,
            "lsp",
            name="lsp",
            description="Language server behavior and invariants.",
            quickstart="python -m atopile.lsp.lsp_server",
            best_practice="Never crash LSP handlers.",
        )
        (tmp_path / "broken").mkdir()
        (tmp_path / "broken" / "SKILL.md").write_text(
            "no frontmatter", encoding="utf-8"
        )

        docs = skills.load_skill_docs(skills_dir=tmp_path, ttl_s=0)
        ids = {doc.id for doc in docs}
        assert "lsp" in ids
        assert "broken" in ids
        lsp = next(doc for doc in docs if doc.id == "lsp")
        assert lsp.name == "lsp"
        assert "Language server behavior" in lsp.description
        assert "Quick Start" in lsp.sections

    def _test_select_skills_includes_baseline_and_relevant_match(
        tmp_path: Path,
    ) -> None:
        _write_skill(
            tmp_path,
            "lsp",
            name="lsp",
            description="Autocomplete, hover, language server, diagnostics.",
            quickstart="python -m atopile.lsp.lsp_server",
            best_practice="Keep per-document graphs stable.",
        )
        _write_skill(
            tmp_path,
            "compiler",
            name="compiler",
            description="Compilation pipeline and parser behavior.",
            quickstart="ato build",
            best_practice="Preserve parser diagnostics.",
        )
        _write_skill(
            tmp_path,
            "dev",
            name="dev",
            description="General development workflow.",
            quickstart="ato dev test",
            best_practice="Run focused checks first.",
        )
        _write_skill(
            tmp_path,
            "domain-layer",
            name="domain-layer",
            description="Build targets, exporters, manufacturing flow.",
            quickstart="ato build",
            best_practice="Follow build step invariants.",
        )

        selection = skills.select_skills_for_turn(
            skills_dir=tmp_path,
            user_message="LSP autocomplete and hover is broken",
            selected_targets=["default"],
            history=[],
            tool_memory={},
            top_k=2,
            ttl_s=0,
        )
        ids = [card.id for card in selection.cards]
        assert "dev" in ids
        assert "domain-layer" in ids
        assert "lsp" in ids

    def _test_load_skill_docs_refreshes_when_file_changes(tmp_path: Path) -> None:
        _write_skill(
            tmp_path,
            "compiler",
            name="compiler",
            description="Old description",
            quickstart="ato build",
            best_practice="Keep diagnostics.",
        )
        docs_before = skills.load_skill_docs(skills_dir=tmp_path, ttl_s=1000)
        compiler_before = next(doc for doc in docs_before if doc.id == "compiler")
        assert compiler_before.description == "Old description"

        time.sleep(0.01)
        _write_skill(
            tmp_path,
            "compiler",
            name="compiler",
            description="New description",
            quickstart="ato build",
            best_practice="Keep diagnostics.",
        )
        docs_after = skills.load_skill_docs(skills_dir=tmp_path, ttl_s=1000)
        compiler_after = next(doc for doc in docs_after if doc.id == "compiler")
        assert compiler_after.description == "New description"

    class TestAgentSkills:
        test_load_skill_docs_parses_frontmatter_and_sections = staticmethod(
            _test_load_skill_docs_parses_frontmatter_and_sections
        )
        test_select_skills_includes_baseline_and_relevant_match = staticmethod(
            _test_select_skills_includes_baseline_and_relevant_match
        )
        test_load_skill_docs_refreshes_when_file_changes = staticmethod(
            _test_load_skill_docs_refreshes_when_file_changes
        )
