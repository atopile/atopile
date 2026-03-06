"""System prompt construction and skill loading."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atopile.model import builds as builds_domain
from atopile.server.agent import policy
from atopile.server.agent.config import AgentConfig
from atopile.server.agent.orchestrator_helpers import (
    _allocate_fixed_skill_char_caps,
    _trim_user_message,
    _truncate_middle,
)
from atopile.server.domains import artifacts as artifacts_domain

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FixedSkillDoc:
    id: str
    path: Path
    body: str


def load_required_skill_docs(config: AgentConfig) -> list[FixedSkillDoc]:
    """Load all required fixed skill docs from disk."""
    docs: list[FixedSkillDoc] = []
    missing: list[str] = []
    for skill_id in config.fixed_skill_ids:
        skill_path = config.skills_dir / skill_id / "SKILL.md"
        try:
            body = skill_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            missing.append(skill_id)
            continue
        if not body:
            missing.append(skill_id)
            continue
        docs.append(FixedSkillDoc(id=skill_id, path=skill_path, body=body))

    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(
            "Missing required fixed skill docs. "
            f"Expected ids: {config.fixed_skill_ids}. Missing: {missing_text}."
        )
    return docs


def _render_fixed_skills_block(
    *,
    docs: list[FixedSkillDoc],
    per_skill_max_chars: dict[str, int],
    total_max_chars: int,
) -> str:
    sections = ["ACTIVE SKILLS (FULL DOCS):"]
    for doc in docs:
        body = doc.body
        skill_cap = int(per_skill_max_chars.get(doc.id, 0))
        if skill_cap > 0:
            body = _truncate_middle(body, skill_cap)
        sections.append(
            "\n".join(
                [
                    f"SKILL {doc.id}",
                    f"Source: {doc.path}",
                    body.strip(),
                ]
            ).strip()
        )
    block = "\n\n".join(sections)
    return _truncate_middle(block, total_max_chars)


def build_fixed_skill_state(
    *,
    config: AgentConfig,
    docs: list[FixedSkillDoc],
    rendered_total_chars: int,
    per_skill_max_chars: dict[str, int],
) -> dict[str, Any]:
    import time

    return {
        "mode": "fixed",
        "skills_dir": str(config.skills_dir),
        "requested_skill_ids": list(config.fixed_skill_ids),
        "selected_skill_ids": [doc.id for doc in docs],
        "selected_skills": [
            {"id": doc.id, "path": str(doc.path), "chars": len(doc.body)}
            for doc in docs
        ],
        "missing_skill_ids": [],
        "per_skill_max_chars": dict(per_skill_max_chars),
        "reasoning": [
            "mode=fixed",
            "selected_ids=" + ",".join(doc.id for doc in docs),
            f"rendered_chars={rendered_total_chars}",
            f"max_chars={config.fixed_skill_total_max_chars}",
        ],
        "total_chars": rendered_total_chars,
        "max_chars": config.fixed_skill_total_max_chars,
        "generated_at": time.time(),
    }


def build_system_prompt(
    *,
    config: AgentConfig,
    project_root: Path,
    selected_targets: list[str],
    include_session_primer: bool = True,
) -> tuple[str, dict[str, Any]]:
    """Build system prompt with skills. Returns (instructions, skill_state)."""
    fixed_docs = load_required_skill_docs(config)
    per_skill_max_chars = _allocate_fixed_skill_char_caps(
        docs=fixed_docs,
        token_budgets=config.fixed_skill_token_budgets,
        chars_per_token=config.fixed_skill_chars_per_token,
        total_max_chars=config.fixed_skill_total_max_chars,
    )
    skill_block = _render_fixed_skills_block(
        docs=fixed_docs,
        per_skill_max_chars=per_skill_max_chars,
        total_max_chars=config.fixed_skill_total_max_chars,
    )
    skill_state = build_fixed_skill_state(
        config=config,
        docs=fixed_docs,
        rendered_total_chars=len(skill_block),
        per_skill_max_chars=per_skill_max_chars,
    )

    chunks: list[str] = []
    if include_session_primer:
        targets_text = ", ".join(selected_targets) if selected_targets else "<none>"
        chunks.append(
            "Session primer (dynamic context):\n"
            f"- project_root: {project_root}\n"
            f"- selected_targets: {targets_text}"
        )
    if skill_block.strip():
        chunks.append(skill_block)
    joined = "\n\n".join(chunks)
    instructions = _truncate_middle(joined, config.prefix_max_chars)
    return instructions, skill_state


async def build_initial_user_message(
    *,
    project_root: Path,
    selected_targets: list[str],
    user_message: str,
    context_max_chars: int = 8_000,
    message_max_chars: int = 12_000,
) -> str:
    """Build the first user message with project context."""
    context_text = await _build_context(
        project_root=project_root,
        selected_targets=selected_targets,
    )
    context_text = _truncate_middle(context_text, context_max_chars)
    trimmed = _trim_user_message(user_message, message_max_chars)
    return (
        f"Project root: {project_root}\n"
        f"Selected targets: {selected_targets}\n"
        f"Context:\n{context_text}\n\n"
        f"Request:\n{trimmed}"
    )


async def _build_context(
    *,
    project_root: Path,
    selected_targets: list[str],
) -> str:
    files = await asyncio.to_thread(policy.list_context_files, project_root, 240)
    active = await _active_builds(project_root)
    recent = await _recent_builds(project_root)
    bom_targets = await _bom_targets(project_root)
    variables_targets = await _variables_targets(project_root)

    lines: list[str] = [
        "Project summary:",
        f"- root: {project_root}",
        f"- selected_targets: {selected_targets}",
        f"- context_files_count: {len(files)}",
        "- files:",
    ]
    lines.extend([f"  - {path}" for path in files[:120]])

    lines.append("- active_builds:")
    if active:
        for build in active:
            lines.append(
                f"  - {build.get('build_id')} "
                f"{build.get('target')} {build.get('status')}"
            )
    else:
        lines.append("  - none")

    lines.append("- recent_builds:")
    if recent:
        for build in recent:
            lines.append(
                "  - "
                f"{build.get('build_id')} {build.get('target')} "
                f"{build.get('status')} "
                f"errors={build.get('errors')} "
                f"warnings={build.get('warnings')}"
            )
    else:
        lines.append("  - none")

    lines.append("- report_targets:")
    lines.append(f"  - bom: {bom_targets if bom_targets else ['none']}")
    lines.append(
        f"  - variables: {variables_targets if variables_targets else ['none']}"
    )
    return "\n".join(lines)


async def _active_builds(project_root: Path) -> list[dict[str, Any]]:
    summary = await asyncio.to_thread(builds_domain.handle_get_active_builds)
    builds = summary.get("builds", []) if isinstance(summary, dict) else []
    return [
        build
        for build in builds
        if str(build.get("project_root", "")) == str(project_root)
    ]


async def _recent_builds(project_root: Path) -> list[dict[str, Any]]:
    payload = await asyncio.to_thread(
        builds_domain.handle_get_build_history, str(project_root), None, 20
    )
    if not isinstance(payload, dict):
        return []
    raw_builds = payload.get("builds", [])
    if not isinstance(raw_builds, list):
        return []
    recent: list[dict[str, Any]] = []
    for build in raw_builds:
        if not isinstance(build, dict):
            continue
        recent.append(
            {
                "build_id": build.get("buildId") or build.get("build_id"),
                "target": build.get("target"),
                "status": build.get("status"),
                "errors": build.get("errors", 0),
                "warnings": build.get("warnings", 0),
            }
        )
        if len(recent) >= 8:
            break
    return recent


async def _bom_targets(project_root: Path) -> list[str]:
    payload = await asyncio.to_thread(
        artifacts_domain.handle_get_bom_targets, str(project_root)
    )
    if not isinstance(payload, dict):
        return []
    targets = payload.get("targets")
    if not isinstance(targets, list):
        return []
    return [str(t) for t in targets if isinstance(t, str)]


async def _variables_targets(project_root: Path) -> list[str]:
    payload = await asyncio.to_thread(
        artifacts_domain.handle_get_variables_targets, str(project_root)
    )
    if not isinstance(payload, dict):
        return []
    targets = payload.get("targets")
    if not isinstance(targets, list):
        return []
    return [str(t) for t in targets if isinstance(t, str)]
