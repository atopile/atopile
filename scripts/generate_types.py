#!/usr/bin/env python3
"""
Generate TypeScript types from Pydantic models.

This script extracts JSON schemas from Pydantic models in atopile.dataclasses
and converts them to TypeScript using quicktype.

Usage:
    python scripts/generate_types.py

The generated types are written to src/ui-server/src/types/generated.ts
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Models to export (the main ones used by the frontend)
MODELS_TO_EXPORT = [
    "AppState",
    "Project",
    "BuildTarget",
    "Build",
    "BuildStage",
    "PackageInfo",
    "PackageDetails",
    "PackageVersion",
    "Problem",
    "ProblemFilter",
    "StdLibItem",
    "StdLibChild",
    "BOMData",
    "BOMComponent",
    "BOMParameter",
    "BOMUsage",
    "VariablesData",
    "VariableNode",
    "Variable",
    "ModuleDefinition",
    "ModuleChild",
    "FileTreeNode",
    "DependencyInfo",
    "AtopileConfig",
    "DetectedInstallation",
    "InstallProgress",
]


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def get_model_schema(model) -> dict:
    """Get JSON schema for a single model, with camelCase field names."""
    schema = model.model_json_schema(mode="serialization")

    # Keep $defs for quicktype to resolve (it handles circular refs)
    # But convert all field names to camelCase

    def convert_to_camel(obj, in_properties=False):
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                # Convert property names to camelCase
                if in_properties and not k.startswith("$"):
                    new_key = to_camel_case(k)
                else:
                    new_key = k

                # Recursively convert, noting if we're in a properties block
                if k == "properties":
                    result[new_key] = convert_to_camel(v, in_properties=True)
                elif k == "required" and isinstance(v, list):
                    # Convert required field names too
                    result[new_key] = [to_camel_case(name) for name in v]
                else:
                    result[new_key] = convert_to_camel(v, in_properties=False)
            return result
        elif isinstance(obj, list):
            return [convert_to_camel(item, in_properties=False) for item in obj]
        return obj

    return convert_to_camel(schema)


def get_all_schemas() -> dict[str, dict]:
    """Get schemas for all models."""
    from atopile import dataclasses as dc

    schemas = {}
    for model_name in MODELS_TO_EXPORT:
        model = getattr(dc, model_name, None)
        if model is None:
            print(f"Warning: Model {model_name} not found, skipping")
            continue

        try:
            schemas[model_name] = get_model_schema(model)
        except Exception as e:
            print(f"Warning: Failed to get schema for {model_name}: {e}")
            import traceback

            traceback.print_exc()

    return schemas


def convert_with_quicktype(schemas: dict[str, dict], output_path: Path) -> bool:
    """Convert JSON schemas to TypeScript using quicktype."""
    ui_server_dir = Path(__file__).parent.parent / "src" / "ui-server"

    # Write each schema to a temp file
    temp_files = []
    try:
        for name, schema in schemas.items():
            # Add title for quicktype
            schema["title"] = name
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, prefix=f"{name}_"
            ) as f:
                json.dump(schema, f, indent=2)
                temp_files.append(f.name)

        # Run quicktype with all schema files
        args = [
            "npx",
            "quicktype",
            "--lang",
            "typescript",
            "--src-lang",
            "schema",
            "--just-types",
            "--no-enums",  # Use string literals instead of enums for compatibility
            "-o",
            str(output_path),
        ] + temp_files

        print(f"Running quicktype with {len(temp_files)} schemas...")
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=ui_server_dir,
        )

        if result.returncode != 0:
            print(f"Error running quicktype: {result.stderr}")
            print(f"stdout: {result.stdout}")
            return False

        return True

    finally:
        # Clean up temp files
        for f in temp_files:
            Path(f).unlink(missing_ok=True)


def add_header(output_path: Path) -> None:
    """Add a header comment to the generated file."""
    content = output_path.read_text()

    header = """/**
 * AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
 *
 * This file is generated from Python Pydantic models in:
 *   src/atopile/dataclasses.py
 *
 * To regenerate, run:
 *   python scripts/generate_types.py
 *
 * The source of truth is the Python Pydantic models.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

"""

    output_path.write_text(header + content)


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    output_path = repo_root / "src" / "ui-server" / "src" / "types" / "generated.ts"

    print("Generating JSON schemas from Pydantic models...")
    schemas = get_all_schemas()
    print(f"Generated schemas for {len(schemas)} models")

    # Save combined schema for debugging
    schema_output = repo_root / "src" / "ui-server" / "src" / "types" / "schema.json"
    schema_output.write_text(json.dumps(schemas, indent=2))
    print(f"Schemas written to {schema_output}")

    print("Converting to TypeScript with quicktype...")
    if not convert_with_quicktype(schemas, output_path):
        print("Failed to convert to TypeScript")
        sys.exit(1)

    add_header(output_path)

    print(f"TypeScript types written to {output_path}")
    print("Done!")


if __name__ == "__main__":
    main()
