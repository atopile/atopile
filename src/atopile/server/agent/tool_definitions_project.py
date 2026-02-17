"""Project/file tool definition metadata for the agent runtime."""

from __future__ import annotations

from typing import Any


def get_project_tool_definitions() -> list[dict[str, Any]]:
    """Project scope inspection/editing tool definitions."""
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
                    "content_mode": {
                        "type": "string",
                        "enum": ["none", "highlights", "text"],
                        "default": "highlights",
                    },
                    "max_characters": {
                        "type": "integer",
                        "minimum": 200,
                        "maximum": 100000,
                    },
                    "max_age_hours": {"type": "integer", "minimum": -1},
                    "include_text": {
                        "type": "boolean",
                        "description": "Deprecated alias. Prefer content_mode.",
                    },
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
            "name": "project_create_file",
            "description": (
                "Create an in-scope file (same policy as project_create_path). "
                "Allowed file extensions: .ato, .md, and .py (restricted to "
                "src/faebryk/library for fabll modules)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
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
            "name": "project_create_folder",
            "description": (
                "Create an in-scope directory/folder (same policy as "
                "project_create_path with kind='directory')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
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
    ]
