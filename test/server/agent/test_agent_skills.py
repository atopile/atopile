from __future__ import annotations

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


def test_load_skill_docs_parses_frontmatter_and_sections(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "lsp",
        name="lsp",
        description="Language server behavior and invariants.",
        quickstart="python -m atopile.lsp.lsp_server",
        best_practice="Never crash LSP handlers.",
    )
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "SKILL.md").write_text("no frontmatter", encoding="utf-8")

    docs = skills.load_skill_docs(skills_dir=tmp_path, ttl_s=0)
    ids = {doc.id for doc in docs}
    assert "lsp" in ids
    assert "broken" in ids
    lsp = next(doc for doc in docs if doc.id == "lsp")
    assert lsp.name == "lsp"
    assert "Language server behavior" in lsp.description
    assert "Quick Start" in lsp.sections


def test_select_skills_includes_baseline_and_relevant_match(tmp_path: Path) -> None:
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


def test_load_skill_docs_refreshes_when_file_changes(tmp_path: Path) -> None:
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
