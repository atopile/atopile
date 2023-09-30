import logging
import subprocess

import click

from atopile.version import get_version, is_editable_install, warn_editable_install
from atopile.utils import get_source_project_root

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.group()
def meta():
    pass


@meta.command()
def info():
    version = get_version()
    log.info(f"atopile installed: {version}")
    warn_editable_install()


@meta.command()
def update():
    """
    Update the CLI to the latest version either by:
    1. If editable; resintalling the editable version
    2. If not editable; too bad for the second
    """
    if is_editable_install():
        log.info("Reinstalling editable version...")
        log.warning("This won't pull the latest from the repo to avoid overwriting local changes.")
        log.warning("This won't install any new deps to avoid changing your environment.")
        subprocess.run(
            ["pip install --no-deps -e .\"[dev,test,docs]\""],
            check=True,
            shell=True,
            cwd=str(get_source_project_root().resolve().absolute()),
        )
    else:
        raise NotImplementedError
