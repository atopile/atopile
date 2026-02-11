#!/usr/bin/env python3
"""
Generate TypeScript types from Pydantic models.

This script extracts JSON schemas from Pydantic models in atopile.dataclasses
and converts them to TypeScript using quicktype.

Usage:
    python scripts/generate_types.py

The generated types are written to src/ui-server/src/types/gen/generated.ts
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

# Models to export, grouped by domain
MODELS_TO_EXPORT = [
    # Project & build
    "Project",
    "BuildTarget",
    "Build",
    "BuildStage",
    # Packages
    "PackageInfo",
    "PackageDetails",
    "PackageVersion",
    "DependencyInfo",
    "SyncPackagesRequest",
    "SyncPackagesResponse",
    # Problems
    "Problem",
    "ProblemFilter",
    # Standard library
    "StdLibItem",
    "StdLibChild",
    # BOM
    "BOMData",
    "BOMComponent",
    "BOMParameter",
    "BOMUsage",
    # Variables
    "VariablesData",
    "VariableNode",
    "Variable",
    # Modules
    "ModuleDefinition",
    "ModuleChild",
    # Config & installation
    "AtopileConfig",
    "DetectedInstallation",
    "InstallProgress",
    # Events
    "EventMessage",
]

GENERATED_HEADER = """\
/**
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


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def get_model_schema(model) -> dict:
    """Get JSON schema for a single model, with camelCase field names."""
    schema = model.model_json_schema(mode="serialization")

    def convert_schema(obj, in_properties=False):
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                # Rename $defs -> definitions for quicktype (draft-07) compatibility
                if k == "$defs":
                    new_key = "definitions"
                elif in_properties and not k.startswith("$"):
                    new_key = to_camel_case(k)
                else:
                    new_key = k

                # Rewrite $ref paths from $defs to definitions
                if k == "$ref" and isinstance(v, str):
                    result[new_key] = v.replace("#/$defs/", "#/definitions/")
                elif k == "properties":
                    result[new_key] = convert_schema(v, in_properties=True)
                elif k == "required" and isinstance(v, list):
                    result[new_key] = [to_camel_case(name) for name in v]
                else:
                    result[new_key] = convert_schema(v, in_properties=False)
            return result
        elif isinstance(obj, list):
            return [convert_schema(item, in_properties=False) for item in obj]
        return obj

    return convert_schema(schema)


def get_all_schemas() -> dict[str, dict]:
    """Get schemas for all models."""
    from atopile import dataclasses as dc

    schemas = {}
    for model_name in MODELS_TO_EXPORT:
        model = getattr(dc, model_name, None)
        if model is None:
            print(f"Warning: Model {model_name} not found, skipping")
            continue

        schemas[model_name] = get_model_schema(model)

    return schemas


def ensure_node_deps(ui_server_dir: Path) -> bool:
    """Run npm install if node_modules is missing. Returns False on failure."""
    node_modules = ui_server_dir / "node_modules"
    package_lock = ui_server_dir / "package-lock.json"
    needs_install = not node_modules.exists() or (
        package_lock.exists()
        and package_lock.stat().st_mtime > node_modules.stat().st_mtime
    )
    if not needs_install:
        return True

    install_cmd = "ci" if package_lock.exists() else "install"
    print(f"node_modules missing or stale, running npm {install_cmd}...")
    npm = shutil.which("npm")
    if npm is None:
        print("Error: npm not found")
        return False

    result = subprocess.run(
        [npm, install_cmd],
        capture_output=True,
        text=True,
        cwd=ui_server_dir,
        stdin=subprocess.DEVNULL,
    )

    if result.returncode != 0:
        print(f"Error running npm {install_cmd}: {result.stderr}")
        if result.stdout:
            print(f"stdout: {result.stdout}")
        return False

    return True


def run_quicktype(
    schemas: dict[str, dict], output_path: Path, ui_server_dir: Path
) -> bool:
    """Convert JSON schemas to TypeScript using quicktype."""
    npx = shutil.which("npx")
    if npx is None:
        print("Error: npx not found")
        return False

    # Write each schema to a temp file in cwd so quicktype gets simple
    # relative paths (avoids Windows URI resolution issues with C:\ drive paths)
    temp_files = []
    try:
        for name, schema in schemas.items():
            schema["title"] = name
            temp_path = ui_server_dir / f"{name}_schema.json"
            temp_path.write_text(json.dumps(schema, indent=2))
            temp_files.append(temp_path.name)

        args = [
            npx,
            "quicktype",
            "--lang",
            "typescript",
            "--src-lang",
            "schema",
            "--just-types",
            "--no-enums",
            "-o",
            str(output_path),
        ] + temp_files

        print(f"Running quicktype with {len(temp_files)} schemas...")
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=ui_server_dir,
            stdin=subprocess.DEVNULL,
        )

        if result.returncode != 0:
            print(f"Error running quicktype: {result.stderr}")
            if result.stdout:
                print(f"stdout: {result.stdout}")
            return False

        return True

    finally:
        for f in temp_files:
            (ui_server_dir / f).unlink(missing_ok=True)


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    ui_server_dir = repo_root / "src" / "ui-server"
    gen_dir = ui_server_dir / "src" / "types" / "gen"
    output_path = gen_dir / "generated.ts"
    gen_dir.mkdir(parents=True, exist_ok=True)

    print("Generating JSON schemas from Pydantic models...")
    schemas = get_all_schemas()
    print(f"Generated schemas for {len(schemas)} models")

    # Save combined schema for debugging
    (gen_dir / "schema.json").write_text(json.dumps(schemas, indent=2))

    if not ensure_node_deps(ui_server_dir):
        sys.exit(1)

    print("Converting to TypeScript with quicktype...")
    if not run_quicktype(schemas, output_path, ui_server_dir):
        print("Failed to convert to TypeScript")
        sys.exit(1)

    # Prepend header to generated file
    content = output_path.read_text()
    output_path.write_text(GENERATED_HEADER + content)

    print(f"TypeScript types written to {output_path}")
    print("Done!")


if __name__ == "__main__":
    main()
