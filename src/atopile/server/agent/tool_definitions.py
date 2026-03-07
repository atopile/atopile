"""Static tool definition metadata for the agent runtime."""

from __future__ import annotations

from typing import Any

from atopile.server.agent.tool_definitions_project import (
    get_project_tool_definitions,
)


def get_tool_definitions() -> list[dict[str, Any]]:
    """OpenAI Responses API function-tool definitions."""
    return [
        *get_project_tool_definitions(),
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
            "description": (
                "Install an LCSC part into the selected project. Set "
                "create_package=true to also generate the canonical reusable "
                "wrapper package under packages/ for that part. Refine that "
                "generated package file in place and import it directly from "
                "main.ato."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lcsc_id": {"type": "string"},
                    "create_package": {"type": "boolean", "default": False},
                    "project_path": {"type": ["string", "null"]},
                },
                "required": ["lcsc_id"],
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
            "description": (
                "Queue a build for one or more targets in the selected project "
                "or a nested package project. For local packages under "
                "packages/, first use workspace_list_targets to discover the "
                "package target, then call build_run with targets plus "
                "project_path pointing at that nested package project. Do not "
                "create synthetic standalone package builds just to validate "
                "generated local wrappers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "entry": {"type": ["string", "null"]},
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
                    "project_path": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_create",
            "description": (
                "Create a new project-level build target in ato.yaml. Use this "
                "for real top-level or explicitly desired project builds, not as "
                "the default way to validate generated local package wrappers "
                "that are already discoverable via workspace_list_targets."
            ),
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
                "summaries. Defaults to INFO/WARNING/ERROR/ALERT levels. "
                "When a build_id is provided, check the top-level "
                "'first_error' field first — it contains the first "
                "ERROR/ALERT entry with message, stage, source_file, "
                "source_line, and ato_traceback (if available), saving "
                "you from scanning the full logs array."
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
            "name": "layout_set_board_shape",
            "description": (
                "Create or replace the rectangular board outline (Edge.Cuts) "
                "in the KiCad PCB file. Clears any existing outline first. "
                "Supports optional rounded corners."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "width_mm": {
                        "type": "number",
                        "description": "Board width in mm.",
                    },
                    "height_mm": {
                        "type": "number",
                        "description": "Board height in mm.",
                    },
                    "corner_radius_mm": {
                        "type": "number",
                        "default": 0,
                        "description": (
                            "Rounded corner radius in mm. "
                            "Must be <= min(width, height) / 2."
                        ),
                    },
                    "center_x_mm": {
                        "type": "number",
                        "default": 100,
                        "description": "Board center X coordinate in mm.",
                    },
                    "center_y_mm": {
                        "type": "number",
                        "default": 100,
                        "description": "Board center Y coordinate in mm.",
                    },
                },
                "required": ["width_mm", "height_mm"],
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
