"""Tool directory and suggestion mediator for the sidebar agent."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from atopile.server.agent import tools


@dataclass(frozen=True)
class ToolDirectoryItem:
    name: str
    category: str
    purpose: str
    tooltip: str
    inputs: list[str]
    typical_output: str
    keywords: list[str]


_TOOL_DIRECTORY: dict[str, ToolDirectoryItem] = {
    "project_list_files": ToolDirectoryItem(
        name="project_list_files",
        category="project",
        purpose="List in-scope source/config files.",
        tooltip="List source files available to inspect in this project.",
        inputs=["limit"],
        typical_output="files, total",
        keywords=["list files", "tree", "directory", "project files"],
    ),
    "project_read_file": ToolDirectoryItem(
        name="project_read_file",
        category="project",
        purpose="Read file chunks with hashline anchors.",
        tooltip=(
            "Fetch file contents with LINE:HASH anchors "
            "(including .ato/modules package files)."
        ),
        inputs=["path", "start_line", "max_lines"],
        typical_output="path, content, start_line, end_line, total_lines",
        keywords=[
            "read file",
            "open file",
            "inspect file",
            "show file",
            "package file",
            ".ato/modules",
        ],
    ),
    "project_search": ToolDirectoryItem(
        name="project_search",
        category="project",
        purpose="Search project files by substring.",
        tooltip="Find where symbols or text appear across project files.",
        inputs=["query", "limit"],
        typical_output="matches, total",
        keywords=["search", "find", "grep", "look for", "where is"],
    ),
    "examples_list": ToolDirectoryItem(
        name="examples_list",
        category="examples",
        purpose="List curated example projects and their .ato files.",
        tooltip="Browse reference examples that can be used for .ato authoring.",
        inputs=["limit", "include_without_ato_yaml"],
        typical_output="examples_root, examples, total, returned",
        keywords=["examples", "reference", "sample projects", "templates"],
    ),
    "examples_search": ToolDirectoryItem(
        name="examples_search",
        category="examples",
        purpose="Search across curated example .ato files.",
        tooltip="Find matching patterns/snippets from example .ato files.",
        inputs=["query", "limit"],
        typical_output="query, matches, total",
        keywords=["example code", "reference code", "sample .ato", "search examples"],
    ),
    "examples_read_ato": ToolDirectoryItem(
        name="examples_read_ato",
        category="examples",
        purpose="Read an example .ato file by example name.",
        tooltip="Open a specific reference example .ato file.",
        inputs=["example", "path", "start_line", "max_lines"],
        typical_output="example, path, content, start_line, end_line, total_lines",
        keywords=["read example", "open example", "example ato", "reference ato"],
    ),
    "project_list_modules": ToolDirectoryItem(
        name="project_list_modules",
        category="project",
        purpose="List project modules/interfaces/components.",
        tooltip="Quick structural overview of defined modules in the project.",
        inputs=["type_filter", "limit"],
        typical_output="modules, total, types",
        keywords=[
            "modules",
            "architecture",
            "structure",
            "overview",
            "block",
            "module graph",
            "design review",
            "topology",
        ],
    ),
    "project_module_children": ToolDirectoryItem(
        name="project_module_children",
        category="project",
        purpose="Inspect module hierarchy and interfaces.",
        tooltip="Expand module internals (interfaces, params, nested children).",
        inputs=["entry_point", "max_depth"],
        typical_output="entry_point, children, counts",
        keywords=[
            "children",
            "ports",
            "interfaces",
            "nested",
            "hierarchy",
            "parameters",
            "params",
        ],
    ),
    "project_edit_file": ToolDirectoryItem(
        name="project_edit_file",
        category="edit",
        purpose="Apply hashline-anchored edits atomically.",
        tooltip="Apply safe, hash-anchored file edits in one deterministic call.",
        inputs=["path", "edits"],
        typical_output="operations_applied, first_changed_line, bytes",
        keywords=["edit", "change", "modify", "fix code", "patch"],
    ),
    "project_rename_path": ToolDirectoryItem(
        name="project_rename_path",
        category="edit",
        purpose="Rename or move project files/directories.",
        tooltip="Rename or move a file/folder within project scope.",
        inputs=["old_path", "new_path", "overwrite"],
        typical_output="old_path, new_path, kind, overwrote",
        keywords=["rename file", "move file", "rename module", "move path"],
    ),
    "project_delete_path": ToolDirectoryItem(
        name="project_delete_path",
        category="edit",
        purpose="Delete project files/directories.",
        tooltip="Delete a file/folder within project scope.",
        inputs=["path", "recursive"],
        typical_output="path, kind, deleted",
        keywords=["delete file", "remove file", "delete folder", "remove path"],
    ),
    "stdlib_list": ToolDirectoryItem(
        name="stdlib_list",
        category="library",
        purpose="Search and filter standard library items.",
        tooltip="Browse stdlib modules/interfaces with richer filters.",
        inputs=["type_filter", "search", "child_query", "parameter_query", "max_depth"],
        typical_output="items, total, returned",
        keywords=["stdlib", "library", "component", "interface", "trait"],
    ),
    "stdlib_get_item": ToolDirectoryItem(
        name="stdlib_get_item",
        category="library",
        purpose="Get detailed info for one stdlib item.",
        tooltip="Inspect one stdlib item including usage and child fields.",
        inputs=["item_id"],
        typical_output="found, item",
        keywords=["stdlib item", "details", "usage", "api"],
    ),
    "parts_search": ToolDirectoryItem(
        name="parts_search",
        category="parts",
        purpose="Search LCSC/JLC parts.",
        tooltip="Find purchasable parts from LCSC/JLC.",
        inputs=["query", "limit"],
        typical_output="parts, total",
        keywords=[
            "part",
            "parts",
            "lcsc",
            "jlc",
            "component search",
            "mcu",
            "sensor",
            "resistor",
            "capacitor",
            "connector",
            "ic",
            "footprint",
        ],
    ),
    "parts_install": ToolDirectoryItem(
        name="parts_install",
        category="parts",
        purpose="Install an LCSC part to project.",
        tooltip="Install a part by LCSC id into current project.",
        inputs=["lcsc_id"],
        typical_output="success, lcsc_id",
        keywords=["install part", "lcsc id", "add part"],
    ),
    "datasheet_read": ToolDirectoryItem(
        name="datasheet_read",
        category="parts",
        purpose="Attach a component datasheet PDF for model-native reading.",
        tooltip="Resolve datasheet from LCSC id/url/path and attach it as a PDF.",
        inputs=["lcsc_id", "url", "path", "target", "query"],
        typical_output="found, openai_file_id, source, filename",
        keywords=[
            "datasheet",
            "pdf",
            "pinout",
            "electrical characteristics",
            "absolute maximum",
            "timing",
            "application notes",
        ],
    ),
    "packages_search": ToolDirectoryItem(
        name="packages_search",
        category="packages",
        purpose="Search atopile packages.",
        tooltip="Search package registry for reusable modules.",
        inputs=["query"],
        typical_output="packages, total",
        keywords=[
            "package",
            "registry",
            "dependency",
            "library package",
            "module package",
        ],
    ),
    "packages_install": ToolDirectoryItem(
        name="packages_install",
        category="packages",
        purpose="Install a package dependency.",
        tooltip="Install a package (optionally pinned version).",
        inputs=["identifier", "version"],
        typical_output="success, identifier, version",
        keywords=["install package", "add dependency", "pin version"],
    ),
    "build_run": ToolDirectoryItem(
        name="build_run",
        category="build",
        purpose="Queue project builds.",
        tooltip="Start build(s) for selected targets.",
        inputs=[
            "targets",
            "entry",
            "standalone",
            "frozen",
            "include_targets",
            "exclude_targets",
        ],
        typical_output="success, build_targets, message",
        keywords=["build", "run build", "compile", "queue build"],
    ),
    "build_create": ToolDirectoryItem(
        name="build_create",
        category="build",
        purpose="Create build target.",
        tooltip="Create a new named build target in ato.yaml.",
        inputs=["name", "entry"],
        typical_output="success, target",
        keywords=["create build", "new target", "add build target"],
    ),
    "build_rename": ToolDirectoryItem(
        name="build_rename",
        category="build",
        purpose="Rename/update build target.",
        tooltip="Rename a build target or update its entry.",
        inputs=["old_name", "new_name", "new_entry"],
        typical_output="success, target",
        keywords=["rename build", "update target", "change build name"],
    ),
    "build_logs_search": ToolDirectoryItem(
        name="build_logs_search",
        category="build",
        purpose="Search logs and inspect build statuses.",
        tooltip=(
            "Retrieve logs or recent build IDs with failure diagnostics "
            "(defaults to INFO/WARNING/ERROR/ALERT)."
        ),
        inputs=["build_id", "query", "stage", "log_levels", "audience", "limit"],
        typical_output="logs/builds, total",
        keywords=["logs", "errors", "failed build", "why failed"],
    ),
    "design_diagnostics": ToolDirectoryItem(
        name="design_diagnostics",
        category="diagnostics",
        purpose="Run quick diagnostic summary.",
        tooltip="Summarize likely failures from builds/problems/modules.",
        inputs=["max_problems", "max_failure_logs"],
        typical_output="recent_builds, latest_failure_logs, problems",
        keywords=["diagnostic", "explain failure", "lint", "health check"],
    ),
    "autolayout_run": ToolDirectoryItem(
        name="autolayout_run",
        category="autolayout",
        purpose=(
            "Start background placement or routing with DeepPCB/autolayout provider."
        ),
        tooltip=(
            "Queue placement/routing as an autolayout job with provider options "
            "(timeout, batch timeout, webhooks, resume board)."
        ),
        inputs=[
            "build_target",
            "provider",
            "job_type",
            "routing_type",
            "timeout_minutes",
            "max_batch_timeout",
            "resume_board_id",
            "constraints",
            "options",
        ],
        typical_output="job_id, state, provider_job_ref, job",
        keywords=[
            "autolayout",
            "auto layout",
            "autoroute",
            "routing",
            "placement",
            "deeppcb",
            "route board",
            "place board",
        ],
    ),
    "autolayout_status": ToolDirectoryItem(
        name="autolayout_status",
        category="autolayout",
        purpose="Refresh autolayout state and candidates.",
        tooltip="Check autolayout progress, candidates, and terminal state.",
        inputs=[
            "job_id",
            "refresh",
            "include_candidates",
            "wait_seconds",
            "poll_interval_seconds",
        ],
        typical_output="state, candidate_count, job, candidates",
        keywords=[
            "autolayout status",
            "routing status",
            "placement status",
            "job status",
            "candidate status",
        ],
    ),
    "autolayout_fetch_to_layout": ToolDirectoryItem(
        name="autolayout_fetch_to_layout",
        category="autolayout",
        purpose="Apply selected routed/placed candidate into layouts/ with archive.",
        tooltip=(
            "Fetch candidate, apply to layout file, archive an iteration copy "
            "under layouts/autolayout_iterations, and report downloaded provider "
            "artifacts (JSON/SES/DSN when available)."
        ),
        inputs=["job_id", "candidate_id", "archive_iteration"],
        typical_output=(
            "selected_candidate_id, applied_layout_path, backup_layout_path, "
            "archived_iteration_path"
        ),
        keywords=[
            "fetch routed board",
            "apply candidate",
            "pull layout",
            "archive iteration",
            "use routed board",
        ],
    ),
    "autolayout_request_screenshot": ToolDirectoryItem(
        name="autolayout_request_screenshot",
        category="autolayout",
        purpose="Render 2D/3D screenshot files for current placed/routed layout.",
        tooltip=(
            "Generate board screenshots immediately, with optional 2D layer "
            "filters and drawing sheet excluded by default."
        ),
        inputs=["target", "view", "side", "layers"],
        typical_output="screenshot_paths, layers, drawing_sheet_excluded",
        keywords=[
            "screenshot",
            "render board",
            "2d image",
            "3d image",
            "board preview",
        ],
    ),
    "autolayout_configure_board_intent": ToolDirectoryItem(
        name="autolayout_configure_board_intent",
        category="autolayout",
        purpose="Configure plane/stackup intent in ato.yaml for a build target.",
        tooltip=(
            "Set ground-pour and stackup assumptions as autolayout constraints so "
            "the agent can express board intent before routing."
        ),
        inputs=[
            "build_target",
            "enable_ground_pours",
            "plane_nets",
            "plane_mode",
            "layer_count",
            "board_thickness_mm",
            "outer_copper_oz",
            "inner_copper_oz",
            "dielectric_er",
            "preserve_existing_routing",
            "notes",
        ],
        typical_output="build_target, plane_intent, stackup_intent, constraints_after",
        keywords=[
            "ground pour",
            "ground plane",
            "power plane",
            "plane net",
            "stackup",
            "board thickness",
            "copper weight",
            "dielectric",
            "impedance assumptions",
        ],
    ),
    "report_bom": ToolDirectoryItem(
        name="report_bom",
        category="reports",
        purpose="Read BOM artifact.",
        tooltip="Read and summarize generated BOM data for a target.",
        inputs=["target"],
        typical_output="found, bom",
        keywords=[
            "bom",
            "bill of materials",
            "components list",
            "parts list",
            "line items",
            "procurement",
        ],
    ),
    "report_variables": ToolDirectoryItem(
        name="report_variables",
        category="reports",
        purpose="Read variable report artifact.",
        tooltip="Inspect computed variables/parameters for a target.",
        inputs=["target"],
        typical_output="found, variables",
        keywords=[
            "variables",
            "parameter report",
            "computed values",
            "parameters",
            "params",
            "constraints",
        ],
    ),
    "manufacturing_generate": ToolDirectoryItem(
        name="manufacturing_generate",
        category="manufacturing",
        purpose="Generate manufacturing artifacts by queueing mfg-data build.",
        tooltip=(
            "Queue manufacturing generation (gerbers, pick-and-place, 3D, PCB "
            "summary) for a target."
        ),
        inputs=["target", "frozen", "include_targets", "exclude_targets"],
        typical_output="success, queued_build_id, build_targets, expected_outputs",
        keywords=[
            "generate manufacturing",
            "create manufacturing",
            "manufacturing files",
            "gerber",
            "pick and place",
            "pnp",
            "fabrication package",
            "production files",
            "mfg-data",
        ],
    ),
    "manufacturing_summary": ToolDirectoryItem(
        name="manufacturing_summary",
        category="manufacturing",
        purpose="Summarize build outputs and estimated cost.",
        tooltip="Review manufacturing outputs and rough cost estimate.",
        inputs=["target", "quantity"],
        typical_output="outputs, cost_estimate",
        keywords=["manufacturing", "gerbers", "cost", "production"],
    ),
}

_BUILD_ID_RE = re.compile(r"\b[a-f0-9]{8,}\b", re.IGNORECASE)
_AUTOLAYOUT_JOB_ID_RE = re.compile(r"\bal-[a-f0-9]{12}\b", re.IGNORECASE)
_FILE_RE = re.compile(r"([A-Za-z0-9_./-]+\.(?:ato|py|md|json|yaml|yml|toml|ts|tsx))")
_PDF_FILE_RE = re.compile(r"([A-Za-z0-9_./-]+\.pdf)\b", re.IGNORECASE)
_LCSC_RE = re.compile(r"\bC\d{3,}\b", re.IGNORECASE)
_ENTRY_POINT_RE = re.compile(r"([A-Za-z0-9_./-]+\.ato:[A-Za-z_][A-Za-z0-9_]*)")
_PACKAGE_RE = re.compile(
    r"\b([a-z0-9_.-]+/[a-z0-9_.-]+)(?:@([^\s]+))?\b",
    re.IGNORECASE,
)


def _available_tool_names() -> list[str]:
    names: list[str] = []
    for definition in tools.get_tool_definitions():
        if definition.get("type") != "function":
            continue
        raw_name = definition.get("name")
        if isinstance(raw_name, str):
            names.append(raw_name)
    return names


def get_tool_directory() -> list[dict[str, Any]]:
    """Return directory metadata for all currently advertised tools."""
    directory: list[dict[str, Any]] = []
    for name in _available_tool_names():
        item = _TOOL_DIRECTORY.get(name)
        if item is None:
            item = ToolDirectoryItem(
                name=name,
                category="other",
                purpose=name.replace("_", " "),
                tooltip=f"Use {name.replace('_', ' ')}.",
                inputs=[],
                typical_output="result",
                keywords=[name],
            )
        directory.append(
            {
                "name": item.name,
                "category": item.category,
                "purpose": item.purpose,
                "tooltip": item.tooltip,
                "inputs": item.inputs,
                "typical_output": item.typical_output,
                "keywords": item.keywords,
            }
        )
    directory.sort(key=lambda entry: (str(entry["category"]), str(entry["name"])))
    return directory


def update_tool_memory(
    current_memory: dict[str, dict[str, Any]],
    traces: list[Any],
) -> dict[str, dict[str, Any]]:
    """Update per-tool memory entries from a turn's tool traces."""
    updated = dict(current_memory)
    now = time.time()

    for trace in traces:
        name = getattr(trace, "name", None)
        if not isinstance(name, str) or not name:
            continue
        ok = bool(getattr(trace, "ok", False))
        result = getattr(trace, "result", {})
        if not isinstance(result, dict):
            result = {}

        summary = _summarize_result(name, ok, result)
        context_id = _extract_context_id(result)

        updated[name] = {
            "tool_name": name,
            "summary": summary,
            "ok": ok,
            "updated_at": now,
            "context_id": context_id,
        }

    return updated


def get_tool_memory_view(
    current_memory: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return memory entries with stale markers for UI."""
    now = time.time()
    entries: list[dict[str, Any]] = []
    for raw in current_memory.values():
        name = str(raw.get("tool_name", ""))
        updated_at = float(raw.get("updated_at", 0.0) or 0.0)
        age_s = max(0.0, now - updated_at) if updated_at else 0.0
        stale_after_s = _stale_after_seconds(name)
        is_stale = age_s > stale_after_s
        context_id = raw.get("context_id")
        stale_hint = None
        if is_stale:
            if isinstance(context_id, str) and context_id:
                stale_hint = f"result from {context_id}; rerun?"
            else:
                stale_hint = "result may be stale; rerun?"

        entries.append(
            {
                "tool_name": name,
                "summary": str(raw.get("summary", "")),
                "ok": bool(raw.get("ok", False)),
                "updated_at": updated_at,
                "age_seconds": round(age_s, 1),
                "stale": is_stale,
                "stale_hint": stale_hint,
                "context_id": context_id,
            }
        )

    entries.sort(key=lambda entry: float(entry.get("updated_at", 0.0)), reverse=True)
    return entries


def suggest_tools(
    *,
    message: str,
    history: list[dict[str, str]],
    selected_targets: list[str],
    tool_memory: dict[str, dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Rank likely tools for a message and provide argument/prompt hints."""
    text = message.strip().lower()
    context_text = " ".join(
        str(item.get("content", "")).lower() for item in history[-4:]
    ).strip()
    search_blob = text if text else context_text

    suggestions: list[dict[str, Any]] = []
    directory = get_tool_directory()
    memory_view = {
        str(item["tool_name"]): item for item in get_tool_memory_view(tool_memory)
    }

    for item in directory:
        name = str(item["name"])
        keywords = [str(keyword).lower() for keyword in item.get("keywords", [])]
        score = 0.0
        matched: list[str] = []

        for keyword in keywords:
            if keyword and keyword in search_blob:
                score += 1.5
                matched.append(keyword)

        if text and name in text:
            score += 2.0
            matched.append(name)

        if "build" in search_blob and str(item.get("category")) == "build":
            score += 0.7
        physical_part_terms = (
            "lcsc",
            "jlc",
            "footprint",
            "mcu",
            "sensor",
            "resistor",
            "capacitor",
            "connector",
            "part number",
        )
        if any(term in search_blob for term in physical_part_terms) and name in {
            "parts_search",
            "parts_install",
        }:
            score += 1.2
        package_terms = ("package", "dependency", "registry", "import")
        if any(term in search_blob for term in package_terms) and name in {
            "packages_search",
            "packages_install",
        }:
            score += 1.0
        structure_terms = (
            "architecture",
            "structure",
            "hierarchy",
            "module",
            "block diagram",
            "topology",
            "design overview",
        )
        if any(term in search_blob for term in structure_terms) and name in {
            "project_list_modules",
            "project_module_children",
        }:
            score += 1.3
        example_terms = (
            "example",
            "examples",
            "reference",
            "sample",
            "template",
            "how to write ato",
            "ato snippet",
            "similar design",
        )
        if any(term in search_blob for term in example_terms) and name in {
            "examples_list",
            "examples_search",
            "examples_read_ato",
        }:
            score += 1.9
        bom_terms = (
            "bom",
            "bill of materials",
            "parts list",
            "line items",
            "procurement",
        )
        if any(term in search_blob for term in bom_terms) and name == "report_bom":
            score += 1.6
        parameter_terms = (
            "variables",
            "parameters",
            "params",
            "constraints",
            "computed values",
        )
        if (
            any(term in search_blob for term in parameter_terms)
            and name == "report_variables"
        ):
            score += 1.6
        mfg_generate_terms = (
            "generate manufacturing",
            "create manufacturing",
            "manufacturing files",
            "gerber",
            "pick and place",
            "pnp",
            "fabrication package",
            "production files",
        )
        if (
            any(term in search_blob for term in mfg_generate_terms)
            and name == "manufacturing_generate"
        ):
            score += 1.9
        mfg_summary_terms = ("manufacturing summary", "cost estimate", "mfg summary")
        if (
            any(term in search_blob for term in mfg_summary_terms)
            and name == "manufacturing_summary"
        ):
            score += 1.4
        autolayout_terms = (
            "autolayout",
            "auto layout",
            "autoroute",
            "route board",
            "routing",
            "placement",
            "deeppcb",
            "pcb layout",
        )
        if any(term in search_blob for term in autolayout_terms):
            if name == "autolayout_run":
                score += 1.9
            elif name in {"autolayout_status", "autolayout_fetch_to_layout"}:
                score += 1.3
            elif name == "autolayout_configure_board_intent":
                score += 1.1
        stackup_terms = (
            "ground pour",
            "ground plane",
            "power plane",
            "stackup",
            "board thickness",
            "copper weight",
            "dielectric",
            "impedance",
            "controlled impedance",
        )
        if (
            any(term in search_blob for term in stackup_terms)
            and name == "autolayout_configure_board_intent"
        ):
            score += 2.1
        fetch_terms = (
            "fetch routed",
            "fetch placement",
            "apply candidate",
            "pull layout",
            "archive iteration",
        )
        if (
            any(term in search_blob for term in fetch_terms)
            and name == "autolayout_fetch_to_layout"
        ):
            score += 1.8
        screenshot_terms = (
            "screenshot",
            "render board",
            "board image",
            "2d image",
            "3d image",
            "board preview",
        )
        if (
            any(term in search_blob for term in screenshot_terms)
            and name == "autolayout_request_screenshot"
        ):
            score += 1.9
        if "failure" in search_blob and name in {
            "build_logs_search",
            "design_diagnostics",
        }:
            score += 1.1
        if selected_targets and name in {
            "build_run",
            "report_bom",
            "report_variables",
            "manufacturing_generate",
            "manufacturing_summary",
            "autolayout_run",
            "autolayout_request_screenshot",
            "autolayout_configure_board_intent",
        }:
            score += 0.3

        prefilled_args = _infer_prefilled_args(
            tool_name=name,
            message=message,
            selected_targets=selected_targets,
            memory_view=memory_view,
        )
        if prefilled_args:
            score += 0.8

        if score <= 0.0:
            continue

        reason = _reason_from_matches(
            name=name,
            matched_keywords=matched,
            default_reason=str(item.get("purpose", "")),
        )
        prefilled_prompt = _prefilled_prompt(name, prefilled_args)

        suggestions.append(
            {
                "name": name,
                "category": item.get("category"),
                "score": round(score, 2),
                "reason": reason,
                "tooltip": item.get("tooltip"),
                "prefilled_args": prefilled_args,
                "prefilled_prompt": prefilled_prompt,
                "kind": "tool",
            }
        )

    composite = _maybe_explain_failure_suggestion(
        message=message,
        memory_view=memory_view,
    )
    if composite:
        suggestions.append(composite)

    if not suggestions and text:
        defaults = ["project_read_file", "project_list_modules", "build_run"]
        for name in defaults:
            item = next((entry for entry in directory if entry["name"] == name), None)
            if item is None:
                continue
            suggestions.append(
                {
                    "name": name,
                    "category": item.get("category"),
                    "score": 0.5,
                    "reason": str(item.get("purpose", "")),
                    "tooltip": item.get("tooltip"),
                    "prefilled_args": {},
                    "prefilled_prompt": None,
                    "kind": "tool",
                }
            )

    suggestions.sort(
        key=lambda suggestion: (
            -float(suggestion.get("score", 0.0)),
            str(suggestion.get("name", "")),
        )
    )
    return suggestions[: max(1, limit)]


def _stale_after_seconds(tool_name: str) -> float:
    if tool_name.startswith("build") or tool_name.startswith("design_"):
        return 90.0
    if tool_name.startswith("autolayout_"):
        return 75.0
    if tool_name.startswith("project_"):
        return 300.0
    return 600.0


def _extract_context_id(result: dict[str, Any]) -> str | None:
    for key in (
        "job_id",
        "build_id",
        "provider_job_ref",
        "item_id",
        "path",
        "identifier",
    ):
        value = result.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _summarize_result(name: str, ok: bool, result: dict[str, Any]) -> str:
    if not ok:
        error = result.get("error")
        if isinstance(error, str) and error:
            return _trim(error, 120)
        return "failed"

    message = result.get("message")
    if isinstance(message, str) and message:
        return _trim(message, 120)
    total = result.get("total")
    if isinstance(total, int):
        return f"{total} items"
    ops = result.get("operations_applied")
    if isinstance(ops, int):
        return f"{ops} edits applied"
    if name == "build_run":
        targets = result.get("build_targets")
        if isinstance(targets, list):
            return f"{len(targets)} build(s) queued"
    if name == "autolayout_run":
        state = result.get("state")
        if isinstance(state, str) and state:
            return f"autolayout {state}"
        return "autolayout job queued"
    if name == "autolayout_status":
        state = result.get("state")
        candidate_count = result.get("candidate_count")
        if isinstance(state, str):
            if isinstance(candidate_count, int):
                return f"state={state}; candidates={candidate_count}"
            return f"state={state}"
    if name == "autolayout_fetch_to_layout":
        candidate = result.get("selected_candidate_id")
        if isinstance(candidate, str) and candidate:
            return f"applied {candidate}"
        return "layout candidate applied"
    if name == "autolayout_request_screenshot":
        view = result.get("view")
        if isinstance(view, str) and view:
            return f"{view} screenshot rendered"
        return "screenshot rendered"
    if name == "autolayout_configure_board_intent":
        target = result.get("build_target")
        if isinstance(target, str) and target:
            return f"board intent updated for {target}"
        return "board intent updated"
    return "ok"


def _trim(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _reason_from_matches(
    *,
    name: str,
    matched_keywords: list[str],
    default_reason: str,
) -> str:
    if matched_keywords:
        keyword = matched_keywords[0]
        return f"Matches '{keyword}' intent for {name}."
    return default_reason or f"Likely useful: {name}."


def _prefilled_prompt(tool_name: str, prefilled_args: dict[str, Any]) -> str | None:
    if not prefilled_args:
        return None
    return f"Use `{tool_name}` with arguments: {prefilled_args}"


def _infer_prefilled_args(
    *,
    tool_name: str,
    message: str,
    selected_targets: list[str],
    memory_view: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    text = message.strip()
    lower = text.lower()
    known_examples = {
        "quickstart",
        "passives",
        "equations",
        "pick_parts",
        "i2c",
        "esp32_minimal",
        "layout_reuse",
        "led_badge",
        "fabll_minimal",
    }

    if tool_name == "project_search":
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            return {"query": quoted.group(1)}
        find_for = re.search(r"(?:search|find|grep)\s+(?:for\s+)?(.+)", lower)
        if find_for:
            query = find_for.group(1).strip().strip(".")
            if query:
                return {"query": query}

    if tool_name == "examples_list":
        return {"limit": 20}

    if tool_name == "examples_search":
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            return {"query": quoted.group(1), "limit": 80}

        cleaned = re.sub(
            r"\b(example|examples|reference|sample|snippet|ato|show|find|search)\b",
            " ",
            lower,
        )
        query = " ".join(cleaned.split()).strip(".")
        if query:
            return {"query": query, "limit": 80}
        return {"query": "module", "limit": 80}

    if tool_name == "examples_read_ato":
        example_match = re.search(r"\bexamples/([a-z0-9_.-]+)\b", lower)
        if example_match:
            return {
                "example": example_match.group(1),
                "start_line": 1,
                "max_lines": 220,
            }
        for example_name in known_examples:
            if re.search(rf"\b{re.escape(example_name)}\b", lower):
                return {"example": example_name, "start_line": 1, "max_lines": 220}

    if tool_name == "project_read_file":
        file_match = _FILE_RE.search(text)
        if file_match:
            return {"path": file_match.group(1), "start_line": 1, "max_lines": 220}

    if tool_name == "project_module_children":
        entry_match = _ENTRY_POINT_RE.search(text)
        if entry_match:
            return {"entry_point": entry_match.group(1), "max_depth": 2}

    if tool_name == "build_logs_search":
        requested_levels: list[str] = []
        if "debug" in lower:
            requested_levels.append("DEBUG")
        if "info" in lower:
            requested_levels.append("INFO")
        if "warn" in lower:
            requested_levels.append("WARNING")
        if "error" in lower or "fail" in lower:
            requested_levels.append("ERROR")
        if "alert" in lower:
            requested_levels.append("ALERT")

        deduped_levels: list[str] = []
        for level in requested_levels:
            if level not in deduped_levels:
                deduped_levels.append(level)

        stage_match = re.search(r"(?:stage|phase)\s+([a-z0-9_.-]+)", lower)
        build_id_match = _BUILD_ID_RE.search(lower)
        if build_id_match:
            args: dict[str, Any] = {"build_id": build_id_match.group(0)}
            if "error" in lower or "fail" in lower:
                args["query"] = "error"
            if deduped_levels:
                args["log_levels"] = deduped_levels
            if stage_match:
                args["stage"] = stage_match.group(1)
            if "user logs" in lower:
                args["audience"] = "user"
            elif "developer logs" in lower:
                args["audience"] = "developer"
            return args
        recent = memory_view.get("build_run")
        if recent and isinstance(recent.get("context_id"), str):
            args = {"build_id": str(recent["context_id"])}
            if deduped_levels:
                args["log_levels"] = deduped_levels
            if stage_match:
                args["stage"] = stage_match.group(1)
            return args

    if tool_name == "autolayout_run":
        args: dict[str, Any] = {}
        if selected_targets:
            args["build_target"] = selected_targets[0]
        else:
            target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
            if target_match:
                candidate = target_match.group(1)
                if candidate not in {"for", "with", "from", "the"}:
                    args["build_target"] = candidate

        if "placement" in lower or "place components" in lower:
            args["job_type"] = "Placement"
        else:
            args["job_type"] = "Routing"

        if "keep existing" in lower or "protected wiring" in lower:
            args["routing_type"] = "CurrentProtectedWiring"
        elif "start from current" in lower:
            args["routing_type"] = "CurrentUnprotectedWiring"
        elif "empty board" in lower or "fresh routing" in lower:
            args["routing_type"] = "EmptyBoard"

        resume_id = re.search(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
            lower,
            re.IGNORECASE,
        )
        if resume_id and ("resume" in lower or "from board" in lower):
            args["resume_board_id"] = resume_id.group(0)
        return args

    if tool_name == "autolayout_status":
        args: dict[str, Any] = {}
        if any(token in lower for token in ("periodic", "check in", "monitor", "wait")):
            args["wait_seconds"] = 120
            args["poll_interval_seconds"] = 15
        job_match = _AUTOLAYOUT_JOB_ID_RE.search(lower)
        if job_match:
            args["job_id"] = job_match.group(0)
            return args
        recent = memory_view.get("autolayout_run")
        if recent and isinstance(recent.get("context_id"), str):
            args["job_id"] = str(recent["context_id"])
            return args

    if tool_name == "autolayout_fetch_to_layout":
        job_match = _AUTOLAYOUT_JOB_ID_RE.search(lower)
        if job_match:
            return {"job_id": job_match.group(0)}
        recent = memory_view.get("autolayout_run")
        if recent and isinstance(recent.get("context_id"), str):
            return {"job_id": str(recent["context_id"])}
        status_recent = memory_view.get("autolayout_status")
        if status_recent and isinstance(status_recent.get("context_id"), str):
            return {"job_id": str(status_recent["context_id"])}

    if tool_name == "autolayout_request_screenshot":
        args = {"view": "2d"}
        if "3d" in lower and "2d" in lower:
            args["view"] = "both"
        elif "3d" in lower:
            args["view"] = "3d"
        elif "both" in lower:
            args["view"] = "both"
        if "bottom" in lower or "back side" in lower or "backside" in lower:
            args["side"] = "bottom"
        elif "both sides" in lower:
            args["side"] = "both"
        else:
            args["side"] = "top"

        if selected_targets:
            args["target"] = selected_targets[0]
        else:
            target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
            if target_match:
                candidate = target_match.group(1)
                if candidate not in {"for", "with", "from", "the"}:
                    args["target"] = candidate
        return args

    if tool_name == "autolayout_configure_board_intent":
        args: dict[str, Any] = {}
        if selected_targets:
            args["build_target"] = selected_targets[0]

        if "no ground pour" in lower or "disable pour" in lower:
            args["enable_ground_pours"] = False
        elif any(
            token in lower for token in ("ground pour", "ground plane", "power plane")
        ):
            args["enable_ground_pours"] = True

        if "hatched" in lower:
            args["plane_mode"] = "hatched"
        elif "solid" in lower:
            args["plane_mode"] = "solid"

        if "4 layer" in lower or "4-layer" in lower:
            args["layer_count"] = 4
        elif "6 layer" in lower or "6-layer" in lower:
            args["layer_count"] = 6
        elif "2 layer" in lower or "2-layer" in lower:
            args["layer_count"] = 2

        if "1.6mm" in lower:
            args["board_thickness_mm"] = 1.6
        elif "0.8mm" in lower:
            args["board_thickness_mm"] = 0.8
        elif "1.0mm" in lower:
            args["board_thickness_mm"] = 1.0

        if "preserve existing routing" in lower:
            args["preserve_existing_routing"] = True
        elif "ignore existing routing" in lower:
            args["preserve_existing_routing"] = False

        if args:
            return args

    if tool_name == "parts_install":
        lcsc_match = _LCSC_RE.search(text)
        if lcsc_match:
            return {"lcsc_id": lcsc_match.group(0).upper()}

    if tool_name == "datasheet_read":
        default_target = selected_targets[0] if selected_targets else None
        lcsc_match = _LCSC_RE.search(text)
        if lcsc_match:
            args = {"lcsc_id": lcsc_match.group(0).upper()}
            if default_target:
                args["target"] = default_target
            return args

        url_match = re.search(r"https?://\S+", text)
        if url_match:
            url = url_match.group(0).rstrip(".,);]>")
            if url:
                args = {"url": url}
                if default_target:
                    args["target"] = default_target
                return args

        pdf_match = _PDF_FILE_RE.search(text)
        if pdf_match:
            args = {"path": pdf_match.group(1)}
            if default_target:
                args["target"] = default_target
            return args

    if tool_name == "parts_search":
        triggers = (
            "part",
            "component",
            "lcsc",
            "jlc",
            "mcu",
            "sensor",
            "resistor",
            "capacitor",
            "connector",
            "footprint",
        )
        if any(token in lower for token in triggers):
            cleaned = re.sub(
                r"\b(search|find|lookup|for|part|parts|component|components)\b",
                " ",
                lower,
            )
            query = " ".join(cleaned.split()).strip(".")
            if query:
                return {"query": query}

    if tool_name == "packages_install":
        package_match = _PACKAGE_RE.search(text)
        if package_match:
            identifier = package_match.group(1)
            version = package_match.group(2)
            if version:
                return {"identifier": identifier, "version": version}
            return {"identifier": identifier}

    if tool_name == "build_run":
        if selected_targets:
            return {"targets": [selected_targets[0]]}
        if "build" in lower:
            return {"targets": []}

    if tool_name == "manufacturing_generate":
        args: dict[str, Any] = {"include_targets": ["mfg-data"]}
        if selected_targets:
            args["target"] = selected_targets[0]
            return args
        target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
        if target_match:
            candidate = target_match.group(1)
            if candidate not in {"for", "with", "from", "the"}:
                args["target"] = candidate
        return args

    if tool_name in {
        "report_bom",
        "report_variables",
        "manufacturing_summary",
        "manufacturing_generate",
    }:
        if selected_targets:
            return {"target": selected_targets[0]}
        target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
        if target_match:
            candidate = target_match.group(1)
            if candidate not in {"for", "with", "from", "the"}:
                return {"target": candidate}

    return {}


def _maybe_explain_failure_suggestion(
    *,
    message: str,
    memory_view: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    text = message.strip().lower()
    trigger = any(
        phrase in text
        for phrase in (
            "explain failure",
            "why did it fail",
            "diagnose",
            "debug build",
            "lint current design",
        )
    )
    if not trigger and text:
        return None

    build_context = None
    build_logs_entry = memory_view.get("build_logs_search")
    if build_logs_entry:
        context_id = build_logs_entry.get("context_id")
        if isinstance(context_id, str) and context_id:
            build_context = context_id

    prompt = "Run `design_diagnostics`, then summarize likely root cause."
    if build_context:
        prompt += (
            f" Use `build_logs_search` with build_id='{build_context}' for details."
        )

    return {
        "name": "explain_failure",
        "category": "diagnostics",
        "score": 4.2,
        "reason": "Composite failure triage workflow.",
        "tooltip": ("Runs diagnostics-first failure analysis before suggesting fixes."),
        "prefilled_args": {"build_id": build_context} if build_context else {},
        "prefilled_prompt": prompt,
        "kind": "composite",
    }
