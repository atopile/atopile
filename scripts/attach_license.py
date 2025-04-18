# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path

import typer

LICENSE = """# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
"""


def update_file(filepath: Path) -> bool:
    """Update a Python file with the license if it's not present."""

    with open(filepath, "r+", encoding="utf-8") as file:
        contents = file.read()

        if LICENSE not in contents:
            # Add the license at the top of the file and keep the rest as is
            file.seek(0, 0)
            file.write(LICENSE + "\n" + contents)
            return True

        return False


def add_license_to_python_files(directory: Path):
    """Add the license to all Python files in a directory that don't have it."""

    if not directory.is_dir():
        typer.echo(f"The provided path '{directory}' is not a directory.")
        raise typer.Exit(code=1)

    any_changed = False
    for filepath in directory.glob("**/*.py"):
        rc = update_file(filepath)
        any_changed = any_changed or rc

    raise typer.Exit(1 if any_changed else 0)


if __name__ == "__main__":
    typer.run(add_license_to_python_files)
