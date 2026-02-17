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
            "Use web search for current external facts not present in project files."
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
    ),
    "project_move_path": ToolDirectoryItem(
        name="project_move_path",
        category="edit",
        purpose="Move/rearrange project files/directories.",
        tooltip="Move or rename a file/folder within project scope.",
        inputs=["old_path", "new_path", "overwrite"],
        typical_output="old_path, new_path, kind, overwrote",
        keywords=["move file", "move folder", "rearrange", "rename path"],
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


def available_tool_names() -> list[str]:
    names = sorted(set(tools.get_tool_names()) & set(_TOOL_DIRECTORY.keys()))
    return names


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
