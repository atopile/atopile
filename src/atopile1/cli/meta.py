import logging
import subprocess

import click
from rich.console import Console
from rich.table import Table

from atopile.utils import get_source_project_root, is_editable_install
from atopile.version import get_version

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.group()
def meta():
    pass


@meta.command()
def info():
    """
    Print out tabulated, coloured information about the installed atopile version
    """
    table = Table(title="atopile Info")
    table.add_column("Info", style="cyan")
    table.add_column("Value", style="magenta")

    # add the version
    table.add_row("Version", str(get_version()))

    # add whether it's an editable install, making it red if it is
    table.add_row(
        "Editable Install",
        str(is_editable_install()),
        style="red" if is_editable_install() else None,
    )

    # print the table
    console = Console()
    console.print(table)


@meta.command()
def update():
    """
    Update the CLI to the latest version either by:
    1. If editable; resintalling the editable version
    2. If not editable; too bad for the second
    """
    if is_editable_install():
        log.info("Reinstalling editable version...")
        log.warning(
            "This won't pull the latest from the repo to avoid overwriting local changes."
        )
        log.warning(
            "This won't install any new deps to avoid changing your environment."
        )
        subprocess.run(
            ['pip install --no-deps -e ."[dev,test,docs]"'],
            check=True,
            shell=True,
            cwd=str(get_source_project_root().resolve().absolute()),
        )
    else:
        raise NotImplementedError
