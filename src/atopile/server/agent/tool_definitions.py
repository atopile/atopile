"""Static tool definition metadata for the agent runtime."""

from __future__ import annotations

from typing import Any

def get_tool_definitions() -> list[dict[str, Any]]:
    """OpenAI Responses API function-tool definitions."""
    return [
        {
            "type": "function",
            "name": "project_list_files",
            "description": "List source/config files in the selected project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 600,
                        "default": 300,
                    }
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_read_file",
            "description": (
                "Read a file chunk from the selected project (including package"
                " files under .ato/modules)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "minimum": 1, "default": 1},
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 220,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_search",
            "description": "Search source/config files by substring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 60,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "web_search",
            "description": (
                "Search the public web using Exa and return ranked sources "
                "for current/unknown external facts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 25,
                        "default": 8,
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["auto", "fast", "neural", "deep", "instant"],
                        "default": "auto",
                    },
                    "include_domains": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "exclude_domains": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "include_text": {"type": "boolean", "default": True},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "examples_list",
            "description": (
                "List curated atopile reference examples with available .ato files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 60,
                    },
                    "include_without_ato_yaml": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "examples_search",
            "description": ("Search across curated example .ato files by substring."),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 100,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "examples_read_ato",
            "description": ("Read a curated example .ato file by example name."),
            "parameters": {
                "type": "object",
                "properties": {
                    "example": {"type": "string"},
                    "path": {"type": ["string", "null"]},
                    "start_line": {"type": "integer", "minimum": 1, "default": 1},
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 220,
                    },
                },
                "required": ["example"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "package_ato_list",
            "description": (
                "List available package .ato reference files from `.ato/modules` "
                "and optional configured package reference roots."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "package_query": {"type": ["string", "null"]},
                    "path_query": {"type": ["string", "null"]},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 200,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "package_ato_search",
            "description": (
                "Search package .ato reference files by substring with optional "
                "package/path filtering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "package_query": {"type": ["string", "null"]},
                    "path_query": {"type": ["string", "null"]},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 120,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "package_ato_read",
            "description": (
                "Read one package .ato reference file by package identifier "
                "(owner/package) and optional path within that package."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "package_identifier": {"type": "string"},
                    "path_in_package": {"type": ["string", "null"]},
                    "start_line": {"type": "integer", "minimum": 1, "default": 1},
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 220,
                    },
                },
                "required": ["package_identifier"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_list_modules",
            "description": (
                "Primary structure tool. List project "
                "module/interface/component definitions for architecture "
                "overview."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type_filter": {"type": ["string", "null"]},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 200,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_module_children",
            "description": (
                "Primary deep-structure tool. Inspect hierarchical "
                "children/interfaces/parameters for one module entry point "
                "(use after project_list_modules)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_point": {"type": "string"},
                    "max_depth": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 5,
                        "default": 2,
                    },
                },
                "required": ["entry_point"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "stdlib_list",
            "description": (
                "Browse atopile stdlib modules/interfaces/traits/components with "
                "optional filtering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type_filter": {"type": ["string", "null"]},
                    "search": {"type": ["string", "null"]},
                    "child_query": {"type": ["string", "null"]},
                    "parameter_query": {"type": ["string", "null"]},
                    "max_depth": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 5,
                        "default": 2,
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 120,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "stdlib_get_item",
            "description": "Get details for one stdlib item by id/name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                },
                "required": ["item_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_edit_file",
            "description": "Apply hash-anchored edits to a project file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "edits": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "oneOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "set_line": {
                                            "type": "object",
                                            "properties": {
                                                "anchor": {"type": "string"},
                                                "new_text": {"type": "string"},
                                            },
                                            "required": ["anchor", "new_text"],
                                            "additionalProperties": False,
                                        }
                                    },
                                    "required": ["set_line"],
                                    "additionalProperties": False,
                                },
                                {
                                    "type": "object",
                                    "properties": {
                                        "replace_lines": {
                                            "type": "object",
                                            "properties": {
                                                "start_anchor": {"type": "string"},
                                                "end_anchor": {"type": "string"},
                                                "new_text": {"type": "string"},
                                            },
                                            "required": [
                                                "start_anchor",
                                                "end_anchor",
                                                "new_text",
                                            ],
                                            "additionalProperties": False,
                                        }
                                    },
                                    "required": ["replace_lines"],
                                    "additionalProperties": False,
                                },
                                {
                                    "type": "object",
                                    "properties": {
                                        "insert_after": {
                                            "type": "object",
                                            "properties": {
                                                "anchor": {"type": "string"},
                                                "text": {"type": "string"},
                                            },
                                            "required": ["anchor", "text"],
                                            "additionalProperties": False,
                                        }
                                    },
                                    "required": ["insert_after"],
                                    "additionalProperties": False,
                                },
                            ]
                        },
                    },
                },
                "required": ["path", "edits"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_create_path",
            "description": (
                "Create an in-scope directory or allowed file type. Allowed file "
                "extensions: .ato, .md, and .py (restricted to "
                "src/faebryk/library for fabll modules)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["file", "directory"],
                        "default": "file",
                    },
                    "content": {"type": "string", "default": ""},
                    "overwrite": {"type": "boolean", "default": False},
                    "parents": {"type": "boolean", "default": True},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_move_path",
            "description": (
                "Rearrange project files/directories by moving or renaming within "
                "the selected project scope."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "old_path": {"type": "string"},
                    "new_path": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": False},
                },
                "required": ["old_path", "new_path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_rename_path",
            "description": (
                "Rename or move a file/directory within the selected project scope."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "old_path": {"type": "string"},
                    "new_path": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": False},
                },
                "required": ["old_path", "new_path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_delete_path",
            "description": (
                "Delete a file/directory within the selected project scope."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "recursive": {"type": "boolean", "default": True},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "parts_search",
            "description": (
                "Search physical LCSC/JLC parts (ICs, passives, connectors)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 80,
                        "default": 20,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "parts_install",
            "description": "Install an LCSC part into the selected project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lcsc_id": {"type": "string"},
                },
                "required": ["lcsc_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "datasheet_read",
            "description": (
                "Resolve a datasheet PDF, upload it to OpenAI Files, and attach "
                "it for model-native reading. Prefer lcsc_id for graph-first "
                "project resolution."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lcsc_id": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "path": {"type": ["string", "null"]},
                    "target": {"type": ["string", "null"]},
                    "query": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "packages_search",
            "description": (
                "Search atopile registry packages (module/library dependencies)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "packages_install",
            "description": "Install an atopile package into the selected project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string"},
                    "version": {"type": ["string", "null"]},
                },
                "required": ["identifier"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_run",
            "description": "Queue a build for one or more targets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "entry": {"type": ["string", "null"]},
                    "standalone": {"type": "boolean", "default": False},
                    "frozen": {"type": "boolean", "default": False},
                    "include_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "exclude_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_create",
            "description": "Create a new build target in ato.yaml.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "entry": {"type": "string"},
                },
                "required": ["name", "entry"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_rename",
            "description": "Rename or update an existing build target.",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_name": {"type": "string"},
                    "new_name": {"type": ["string", "null"]},
                    "new_entry": {"type": ["string", "null"]},
                },
                "required": ["old_name"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_logs_search",
            "description": (
                "Search build logs or list recent builds with status/error "
                "summaries. Defaults to INFO/WARNING/ERROR/ALERT levels."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "build_id": {"type": ["string", "null"]},
                    "query": {"type": ["string", "null"]},
                    "stage": {"type": ["string", "null"]},
                    "log_levels": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "string",
                            "enum": [
                                "DEBUG",
                                "INFO",
                                "WARNING",
                                "ERROR",
                                "ALERT",
                            ],
                        },
                    },
                    "audience": {
                        "type": "string",
                        "enum": ["user", "developer", "agent", "all", "*"],
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 200,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "design_diagnostics",
            "description": (
                "Run quick diagnostics for the selected project (recent failures, "
                "problems, and module overview)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "max_problems": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 25,
                    },
                    "max_failure_logs": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 50,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_run",
            "description": (
                "Start an autolayout placement or routing run as a background task. "
                "Per-run timeout is capped at 2 minutes; use resume cycles for "
                "longer optimization."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "build_target": {"type": "string", "default": "default"},
                    "job_type": {
                        "type": "string",
                        "enum": ["Routing", "Placement"],
                        "default": "Routing",
                    },
                    "routing_type": {"type": ["string", "null"]},
                    "timeout_minutes": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 2,
                    },
                    "max_batch_timeout": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 3600,
                    },
                    "resume_board_id": {"type": ["string", "null"]},
                    "resume_stop_first": {"type": "boolean", "default": True},
                    "webhook_url": {"type": ["string", "null"]},
                    "webhook_token": {"type": ["string", "null"]},
                    "constraints": {"type": "object", "default": {}},
                    "options": {"type": "object", "default": {}},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_status",
            "description": (
                "Refresh an autolayout job and return state, candidates, and "
                "DeepPCB refs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": ["string", "null"]},
                    "refresh": {"type": "boolean", "default": True},
                    "include_candidates": {"type": "boolean", "default": True},
                    "wait_seconds": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 1800,
                        "default": 0,
                    },
                    "poll_interval_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 120,
                        "default": 10,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_fetch_to_layout",
            "description": (
                "Fetch one autolayout candidate into layouts/, apply it, archive "
                "an iteration snapshot, and return downloaded artifact paths "
                "(.kicad_pcb when available). If the job is "
                "still queued/running, return a check-back hint instead of "
                "applying early."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": ["string", "null"]},
                    "candidate_id": {"type": ["string", "null"]},
                    "archive_iteration": {"type": "boolean", "default": True},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_request_screenshot",
            "description": (
                "Render screenshot(s) of the current board layout (2D/3D) and "
                "return artifact paths. 2D rendering excludes the drawing sheet "
                "by default and can spotlight selected components by dimming the "
                "rest of the board."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "view": {
                        "type": "string",
                        "enum": ["2d", "3d", "both"],
                        "default": "2d",
                    },
                    "side": {
                        "type": "string",
                        "enum": ["top", "bottom", "both"],
                        "default": "top",
                    },
                    "layers": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "highlight_components": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "highlight_fuzzy_limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 6,
                    },
                    "dim_others": {"type": "boolean", "default": True},
                    "dim_opacity": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.72,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "layout_get_component_position",
            "description": (
                "Get one component footprint position/layer from the current "
                "KiCad layout by atopile_address (or reference fallback). "
                "Returns fuzzy suggestions when not found."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "target": {"type": "string", "default": "default"},
                    "fuzzy_limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 6,
                    },
                },
                "required": ["address"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "layout_set_component_position",
            "description": (
                "Set or nudge one component footprint transform in the current "
                "KiCad layout by atopile_address/reference. Supports absolute "
                "(x_mm/y_mm/rotation_deg) and relative "
                "(dx_mm/dy_mm/drotation_deg) modes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "target": {"type": "string", "default": "default"},
                    "mode": {
                        "type": "string",
                        "enum": ["absolute", "relative"],
                        "default": "absolute",
                    },
                    "x_mm": {"type": ["number", "null"]},
                    "y_mm": {"type": ["number", "null"]},
                    "rotation_deg": {"type": ["number", "null"]},
                    "dx_mm": {"type": ["number", "null"]},
                    "dy_mm": {"type": ["number", "null"]},
                    "drotation_deg": {"type": ["number", "null"]},
                    "layer": {"type": ["string", "null"]},
                    "fuzzy_limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 6,
                    },
                },
                "required": ["address"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "layout_run_drc",
            "description": (
                "Run KiCad PCB DRC for the current layout and return summary counts "
                "plus a saved JSON report path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "max_findings": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 120,
                    },
                    "max_items_per_finding": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 4,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_configure_board_intent",
            "description": (
                "Set board plane/stackup intent for a build target in ato.yaml so "
                "the agent can express ground pour and impedance assumptions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "build_target": {"type": "string", "default": "default"},
                    "enable_ground_pours": {"type": "boolean", "default": True},
                    "plane_nets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["GND"],
                    },
                    "plane_mode": {
                        "type": "string",
                        "enum": ["solid", "hatched"],
                        "default": "solid",
                    },
                    "min_plane_clearance_mm": {
                        "type": ["number", "null"],
                    },
                    "layer_count": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 64,
                    },
                    "board_thickness_mm": {"type": ["number", "null"]},
                    "outer_copper_oz": {"type": ["number", "null"]},
                    "inner_copper_oz": {"type": ["number", "null"]},
                    "dielectric_er": {"type": ["number", "null"]},
                    "preserve_existing_routing": {"type": ["boolean", "null"]},
                    "notes": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "report_bom",
            "description": (
                "Primary BOM report tool. Read generated BOM artifact data for "
                "a target."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "report_variables",
            "description": (
                "Primary parameter/variables report tool. Read computed "
                "variables artifact data for a target."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "manufacturing_generate",
            "description": (
                "Generate manufacturing artifacts by queueing a build with the "
                "mfg-data target. Use this to create gerbers, pick-and-place, "
                "3D outputs, and PCB summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "frozen": {"type": "boolean", "default": False},
                    "include_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["mfg-data"],
                    },
                    "exclude_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "manufacturing_summary",
            "description": "Get build outputs and a basic manufacturing cost estimate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "quantity": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5000,
                        "default": 10,
                    },
                },
                "additionalProperties": False,
            },
        },
    ]
