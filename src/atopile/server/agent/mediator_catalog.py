"""Static tool directory metadata for the agent mediator."""

from __future__ import annotations

from dataclasses import dataclass

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
    tool_role: str = "discovery"  # "discovery", "execution", or "both"


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
    "web_search": ToolDirectoryItem(
        name="web_search",
        category="research",
        purpose="Search the public web using Exa.",
        tooltip=(
            "Use web search for current external facts, vendor datasheets, "
            "hardware design guides, and application notes not present in "
            "project files."
        ),
        inputs=[
            "query",
            "num_results",
            "search_type",
            "content_mode",
            "max_characters",
            "max_age_hours",
            "include_domains",
            "exclude_domains",
        ],
        typical_output="query, returned_results, results",
        keywords=[
            "web search",
            "search web",
            "internet",
            "latest",
            "news",
            "look up",
            "external docs",
            "release notes",
            "datasheet",
            "application note",
            "design guide",
            "pinout",
        ],
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
    "package_ato_list": ToolDirectoryItem(
        name="package_ato_list",
        category="examples",
        purpose="List package .ato reference files from installed modules.",
        tooltip=(
            "Discover package source files under .ato/modules and configured "
            "reference roots."
        ),
        inputs=["package_query", "path_query", "limit"],
        typical_output="roots, files, packages, total_files",
        keywords=[
            "package ato list",
            "installed package source",
            "module references",
            ".ato/modules",
            "reference corpus",
        ],
    ),
    "package_ato_search": ToolDirectoryItem(
        name="package_ato_search",
        category="examples",
        purpose="Search package .ato reference files with filters.",
        tooltip=(
            "Search installed package .ato code by text, package id, or path "
            "for reusable design patterns."
        ),
        inputs=["query", "package_query", "path_query", "limit"],
        typical_output="query, matches, total, scanned_files",
        keywords=[
            "package ato search",
            "search package source",
            "reference patterns",
            "scan modules",
            "look through package code",
        ],
    ),
    "package_ato_read": ToolDirectoryItem(
        name="package_ato_read",
        category="examples",
        purpose="Read one package .ato file by package id/path.",
        tooltip="Open a package .ato source file for detailed pattern review.",
        inputs=["package_identifier", "path_in_package", "start_line", "max_lines"],
        typical_output=(
            "package_identifier, path_in_package, path, content, start_line, end_line"
        ),
        keywords=[
            "read package ato",
            "open package source",
            "package file",
            "reference implementation",
        ],
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
        tool_role="execution",
    ),
    "project_create_path": ToolDirectoryItem(
        name="project_create_path",
        category="edit",
        purpose="Create allowed files (.ato/.md/fabll .py) and directories.",
        tooltip=(
            "Create files or folders in project scope with extension/path policy "
            "enforcement."
        ),
        inputs=["path", "kind", "content", "overwrite", "parents"],
        typical_output="path, kind, created, bytes, extension",
        keywords=[
            "create file",
            "new file",
            "create folder",
            "mkdir",
            "scaffold",
            "bootstrap",
        ],
        tool_role="execution",
    ),
    "project_create_file": ToolDirectoryItem(
        name="project_create_file",
        category="edit",
        purpose="Create an allowed file in project scope.",
        tooltip=(
            "Create a file with extension/path policy enforcement "
            "(same policy as project_create_path)."
        ),
        inputs=["path", "content", "overwrite", "parents"],
        typical_output="path, kind=file, created, bytes, extension",
        keywords=[
            "create file",
            "new file",
            "add file",
            "scaffold file",
        ],
        tool_role="execution",
    ),
    "project_create_folder": ToolDirectoryItem(
        name="project_create_folder",
        category="edit",
        purpose="Create a folder/directory in project scope.",
        tooltip="Create a folder (same policy as project_create_path kind=directory).",
        inputs=["path", "parents"],
        typical_output="path, kind=directory, created",
        keywords=[
            "create folder",
            "new folder",
            "create directory",
            "new directory",
            "mkdir",
        ],
        tool_role="execution",
    ),
    "project_move_path": ToolDirectoryItem(
        name="project_move_path",
        category="edit",
        purpose="Move/rearrange project files/directories.",
        tooltip="Move or rename a file/folder within project scope.",
        inputs=["old_path", "new_path", "overwrite"],
        typical_output="old_path, new_path, kind, overwrote",
        keywords=["move file", "move folder", "rearrange", "rename path"],
        tool_role="execution",
    ),
    "project_rename_path": ToolDirectoryItem(
        name="project_rename_path",
        category="edit",
        purpose="Rename or move project files/directories.",
        tooltip="Rename or move a file/folder within project scope.",
        inputs=["old_path", "new_path", "overwrite"],
        typical_output="old_path, new_path, kind, overwrote",
        keywords=[
            "rename file",
            "rename folder",
            "rename directory",
            "move file",
            "move folder",
            "rename module",
            "move path",
        ],
        tool_role="execution",
    ),
    "project_delete_path": ToolDirectoryItem(
        name="project_delete_path",
        category="edit",
        purpose="Delete project files/directories.",
        tooltip="Delete a file/folder within project scope.",
        inputs=["path", "recursive"],
        typical_output="path, kind, deleted",
        keywords=["delete file", "remove file", "delete folder", "remove path"],
        tool_role="execution",
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
    "package_create_local": ToolDirectoryItem(
        name="package_create_local",
        category="project",
        purpose="Create an empty local sub-package scaffold.",
        tooltip=(
            "Create a reusable package under packages/ and add it as a file "
            "dependency when no physical part install is needed."
        ),
        inputs=["name", "entry_module", "description"],
        typical_output="path, identifier, import_statement",
        keywords=[
            "subpackage",
            "local package",
            "create local package",
            "reusable local package",
            "packages dir",
            "reusable module",
            "package scaffold",
        ],
        tool_role="execution",
    ),
    "workspace_list_targets": ToolDirectoryItem(
        name="workspace_list_targets",
        category="project",
        purpose="List workspace build targets.",
        tooltip=(
            "Discover targets from nested ato.yaml files under the current "
            "project, especially after creating local packages."
        ),
        inputs=[],
        typical_output="projects, total_targets",
        keywords=["targets", "workspace builds", "subpackages", "ato.yaml"],
    ),
    "parts_install": ToolDirectoryItem(
        name="parts_install",
        category="parts",
        purpose="Install an LCSC part or create a packaged wrapper for it.",
        tooltip=(
            "Install a part by LCSC id into the current project, or set "
            "create_package=true to generate a reusable local package under "
            "packages/. Set project_path to install into a nested package "
            "project when refining that package in isolation."
        ),
        inputs=["lcsc_id", "create_package", "project_path"],
        typical_output=(
            "success, lcsc_id, path, created_package, identifier, import_statement"
        ),
        keywords=[
            "install part",
            "lcsc id",
            "add part",
            "local package",
            "wrapper package",
        ],
        tool_role="execution",
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
        tool_role="execution",
    ),
    "package_agent_spawn": ToolDirectoryItem(
        name="package_agent_spawn",
        category="packages",
        purpose="Spawn a package-specialist worker for one package project.",
        tooltip=(
            "Delegate package wrapper implementation to a scoped package worker. "
            "Pass the existing package project path, a concise goal, and optional "
            "comments about what matters most to the top-level design."
        ),
        inputs=["project_path", "goal", "comments", "selected_targets"],
        typical_output="worker_id, package_project_path, status",
        keywords=[
            "delegate package",
            "package worker",
            "subagent",
            "spawn package agent",
            "parallel package work",
        ],
        tool_role="execution",
    ),
    "package_agent_list": ToolDirectoryItem(
        name="package_agent_list",
        category="packages",
        purpose="List package-specialist workers.",
        tooltip="Inspect active or recent package workers for the current run.",
        inputs=[],
        typical_output="workers, total",
        keywords=["list package workers", "subagents", "delegated tasks"],
    ),
    "package_agent_get": ToolDirectoryItem(
        name="package_agent_get",
        category="packages",
        purpose="Inspect one package-specialist worker.",
        tooltip=(
            "Get status, summary, changed files, and build summaries for one worker."
        ),
        inputs=["worker_id"],
        typical_output="worker",
        keywords=["worker status", "package worker status", "inspect subagent"],
    ),
    "package_agent_wait": ToolDirectoryItem(
        name="package_agent_wait",
        category="packages",
        purpose="Wait for a package-specialist worker to finish.",
        tooltip="Block until a package worker finishes or times out.",
        inputs=["worker_id", "timeout_seconds"],
        typical_output="worker",
        keywords=["wait for worker", "join subagent", "wait package agent"],
        tool_role="execution",
    ),
    "package_agent_message": ToolDirectoryItem(
        name="package_agent_message",
        category="packages",
        purpose="Send follow-up guidance to a package-specialist worker.",
        tooltip=(
            "Clarify priorities for a running package worker without "
            "taking over the work."
        ),
        inputs=["worker_id", "message"],
        typical_output="worker_id, status, queued_message",
        keywords=["message subagent", "steer package worker", "update package worker"],
        tool_role="execution",
    ),
    "package_agent_stop": ToolDirectoryItem(
        name="package_agent_stop",
        category="packages",
        purpose="Gracefully stop a package-specialist worker.",
        tooltip="Request a clean stop for a running package worker.",
        inputs=["worker_id"],
        typical_output="worker_id, status",
        keywords=["stop subagent", "stop package worker", "cancel package agent"],
        tool_role="execution",
    ),
    "build_run": ToolDirectoryItem(
        name="build_run",
        category="build",
        purpose="Queue project builds.",
        tooltip=(
            "Start build(s) for selected targets. For package validation, use "
            "workspace_list_targets to find the nested package target and "
            "build it via project_path rather than creating standalone builds."
        ),
        inputs=[
            "targets",
            "entry",
            "frozen",
            "include_targets",
            "exclude_targets",
            "project_path",
        ],
        typical_output="success, build_targets, message",
        keywords=["build", "run build", "compile", "queue build"],
        tool_role="execution",
    ),
    "build_create": ToolDirectoryItem(
        name="build_create",
        category="build",
        purpose="Create build target.",
        tooltip="Create a new named build target in ato.yaml.",
        inputs=["name", "entry"],
        typical_output="success, target",
        keywords=["create build", "new target", "add build target"],
        tool_role="execution",
    ),
    "build_rename": ToolDirectoryItem(
        name="build_rename",
        category="build",
        purpose="Rename/update build target.",
        tooltip="Rename a build target or update its entry.",
        inputs=["old_name", "new_name", "new_entry"],
        typical_output="success, target",
        keywords=["rename build", "update target", "change build name"],
        tool_role="execution",
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
    "autolayout_webhook_gateway": ToolDirectoryItem(
        name="autolayout_webhook_gateway",
        category="autolayout",
        purpose="Manage webhook-only dev tunnel for DeepPCB callbacks.",
        tooltip=(
            "Start/status/stop a local gateway that only exposes the DeepPCB "
            "webhook endpoint publicly (via cloudflared or local-only mode)."
        ),
        inputs=[
            "action",
            "tunnel_provider",
            "internal_api_base_url",
            "gateway_host",
            "gateway_port",
            "webhook_token",
        ],
        typical_output="status.webhook_url, status.running, status.gateway_port",
        keywords=[
            "webhook gateway",
            "cloudflared",
            "deeppcb webhook",
            "tunnel",
            "public webhook",
        ],
        tool_role="both",
    ),
    "autolayout_run": ToolDirectoryItem(
        name="autolayout_run",
        category="autolayout",
        purpose="Start background placement or routing with DeepPCB.",
        tooltip=(
            "Queue placement/routing as an autolayout job with timeout/batch/"
            "webhook/resume options. Per-run timeout is "
            "capped at 2 minutes, so use iterative resume cycles for longer runs."
        ),
        inputs=[
            "build_target",
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
        tool_role="execution",
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
            "under layouts/autolayout_iterations, and report downloaded candidate "
            "artifacts (JSON/SES/DSN when available). If the job is still running, "
            "it returns a check-back hint instead of applying early."
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
        tool_role="execution",
    ),
    "autolayout_request_screenshot": ToolDirectoryItem(
        name="autolayout_request_screenshot",
        category="autolayout",
        purpose="Render 2D/3D screenshot files for current placed/routed layout.",
        tooltip=(
            "Generate board screenshots immediately, with optional 2D layer "
            "filters and drawing sheet excluded by default. Supports highlighting "
            "specific components while dimming the rest of the board."
        ),
        inputs=[
            "target",
            "view",
            "side",
            "layers",
            "highlight_components",
            "dim_others",
            "dim_opacity",
        ],
        typical_output="screenshot_paths, layers, drawing_sheet_excluded",
        keywords=[
            "screenshot",
            "render board",
            "2d image",
            "3d image",
            "board preview",
            "highlight component",
            "spotlight component",
        ],
        tool_role="execution",
    ),
    "layout_get_component_position": ToolDirectoryItem(
        name="layout_get_component_position",
        category="layout",
        purpose="Query component XY/rotation by atopile address or reference.",
        tooltip=(
            "Fetch current component placement from the .kicad_pcb with fuzzy "
            "suggestions when an address is close but not exact."
        ),
        inputs=["address", "target", "fuzzy_limit"],
        typical_output="found, matched_by, component, suggestions",
        keywords=[
            "component position",
            "where is component",
            "placement query",
            "atopile address",
            "reference designator",
            "xy rotation",
        ],
    ),
    "layout_set_component_position": ToolDirectoryItem(
        name="layout_set_component_position",
        category="layout",
        purpose="Set or nudge component XY/rotation in the PCB layout.",
        tooltip=(
            "Apply absolute or relative placement transforms "
            "(x/y/rotation or dx/dy/drotation)."
        ),
        inputs=[
            "address",
            "target",
            "mode",
            "x_mm",
            "y_mm",
            "rotation_deg",
            "dx_mm",
            "dy_mm",
            "drotation_deg",
            "layer",
        ],
        typical_output="updated, before, after, delta",
        keywords=[
            "move component",
            "set component position",
            "nudge component",
            "rotate component",
            "placement edit",
            "layout transform",
        ],
        tool_role="execution",
    ),
    "layout_run_drc": ToolDirectoryItem(
        name="layout_run_drc",
        category="layout",
        purpose="Run KiCad DRC and summarize layout rule violations.",
        tooltip=(
            "Runs KiCad DRC on the active board and returns error/warning counts "
            "plus a saved JSON report path."
        ),
        inputs=["target", "max_findings", "max_items_per_finding"],
        typical_output="total_findings, error_count, warning_count, report_path",
        keywords=[
            "drc",
            "design rule check",
            "erc",
            "rule violations",
            "board check",
        ],
        tool_role="both",
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
        tool_role="execution",
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
        tool_role="execution",
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


def available_tool_names() -> list[str]:
    names = sorted(set(tools.get_tool_names()) & set(_TOOL_DIRECTORY.keys()))
    return names


def discovery_tool_names() -> set[str]:
    """Tool names classified as discovery (or both)."""
    return {
        name
        for name, item in _TOOL_DIRECTORY.items()
        if item.tool_role in ("discovery", "both")
    }


def execution_tool_names() -> set[str]:
    """Tool names classified as execution (or both)."""
    return {
        name
        for name, item in _TOOL_DIRECTORY.items()
        if item.tool_role in ("execution", "both")
    }


def get_tool_directory_items() -> list[dict[str, object]]:
    return [
        {
            "name": item.name,
            "category": item.category,
            "purpose": item.purpose,
            "tooltip": item.tooltip,
            "inputs": item.inputs,
            "typicalOutput": item.typical_output,
            "keywords": item.keywords,
        }
        for item in _TOOL_DIRECTORY.values()
        if item.name in available_tool_names()
    ]
