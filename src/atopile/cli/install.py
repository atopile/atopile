# pylint: disable=logging-fstring-interpolation

"""
This CLI command provides the `ato install` command to:
- install dependencies
- download JLCPCB footprints
"""

# import logging
# from pathlib import Path
# from typing import Annotated, Optional
#
# import questionary
# import ruamel.yaml
# import typer
# from git import GitCommandError, InvalidGitRepositoryError, NoSuchPathError, Repo
#
# import faebryk.libs.exceptions
# from atopile import errors, version
# from atopile.config import DependencySpec, ProjectConfig, config
# from faebryk.libs.project.dependencies import ProjectDependency
# from faebryk.libs.util import robustly_rm_dir

import logging
from pathlib import Path
from typing import Annotated

import questionary
import ruamel.yaml
import typer

from atopile import errors
from atopile.config import DependencySpec, config
from atopile.telemetry import log_to_posthog
from faebryk.libs.project.dependencies import ProjectDependencies, ProjectDependency
from faebryk.libs.util import indented_container

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
yaml = ruamel.yaml.YAML()

dependencies_app = typer.Typer(rich_markup_mode="rich")


@log_to_posthog("cli:install_end")
def install(
    to_install: Annotated[str | None, typer.Argument()] = None,
    jlcpcb: Annotated[
        bool, typer.Option("--jlcpcb", "-j", help="JLCPCB component ID", hidden=True)
    ] = False,
    vendor: Annotated[
        bool,
        typer.Option(
            "--vendor",
            help="Copy the contents of this dependency into the repo",
        ),
    ] = False,
    local: Annotated[
        Path | None, typer.Option("--local", "-l", help="Install from local path")
    ] = None,
    upgrade: Annotated[
        bool, typer.Option("--upgrade", "-u", help="Upgrade dependencies")
    ] = False,
    path: Annotated[Path | None, typer.Argument()] = None,
):
    """
    Install atopile packages or components from jlcpcb.com/parts.
    Deprecated: Use `ato sync` or `ato add` instead
    """
    if jlcpcb:
        raise errors.UserBadParameterError(
            "--jlcpcb flag has been replaced by `ato create component`"
        )

    if vendor:
        raise errors.UserBadParameterError(
            "--vendor flag has been removed."
            # TODO propose alternative
        )

    if not to_install:
        return sync(upgrade=upgrade, path=path)
    else:
        return add([to_install], upgrade=upgrade, path=path)


def sync(
    upgrade: Annotated[
        bool,
        typer.Option(
            "--upgrade", "-U", help="Allow package upgrades, ignoring pinned versions"
        ),
    ] = False,
    path: Annotated[
        Path | None, typer.Option("--project-path", "-C", help="Path to the project")
    ] = None,
):
    # TODO don't like uv's help string
    """
    Update the project's environment
    """

    config.apply_options(None)
    if path:
        config.project_dir = path

    ProjectDependencies(install_missing=True, clean_unmanaged_dirs=True)

    logger.info("[green]Done syncing![/] :call_me_hand:", extra={"markup": True})


def add(
    package: Annotated[
        list[str],
        typer.Argument(
            help="Package identifier of dependency to add.\n\n"
            "* from packages.atopile.io: <package-name>\\[@<version>]\n\n"
            "* from local project: file://<path-to-local-project-dir>/<package-name>\n\n"
            "* from git: git://<git-repo-url>\\[@<branch/tag/commit>]\n",
        ),
    ],
    upgrade: Annotated[
        bool,
        typer.Option(
            "--upgrade", "-U", help="Allow package upgrades, ignoring pinned versions"
        ),
    ] = False,
    path: Annotated[
        Path | None, typer.Option("--project-path", "-C", help="Path to the project")
    ] = None,
):
    """
    Add dependencies to the project
    """

    if not package:
        raise errors.UserException("No package identifier provided")

    config.apply_options(None)
    if path:
        config.project_dir = path

    deps = ProjectDependencies(install_missing=True, clean_unmanaged_dirs=True)
    deps.add_dependencies(
        *[DependencySpec.from_str(p) for p in package], upgrade=upgrade
    )

    logger.info(
        "[green]Done adding dependencies![/] :call_me_hand:", extra={"markup": True}
    )


def remove(
    package: Annotated[list[str], typer.Argument(help="Name of package to remove")],
    path: Annotated[
        Path | None, typer.Option("--project-path", "-C", help="Path to the project")
    ] = None,
):
    """
    Remove dependencies from the project
    """

    config.apply_options(None)
    if path:
        config.project_dir = path

    raise NotImplementedError("Remove not implemented")

    logger.info(
        "[green]Done removing dependencies![/] :call_me_hand:", extra={"markup": True}
    )


def list():
    """
    List all dependencies in the project
    """
    deps = ProjectDependencies()
    # TODO bug, if A -> B, B deps
    # will not see that B is under root, because of the way DAG checks roots
    print(
        indented_container(
            deps.dag.to_tree(),
            recursive=True,
            mapper=lambda x: x.spec.identifier
            if isinstance(x, ProjectDependency)
            else x,
        )
    )


dependencies_app.command()(add)
dependencies_app.command()(remove)
dependencies_app.command()(sync)
dependencies_app.command()(list)

# --------------------------------------------------------------------------------------


def check_missing_deps_or_offer_to_install():
    deps = ProjectDependencies()
    if deps.not_installed_dependencies:
        logger.warning(
            "It appears some dependencies are missing. Run `ato sync` to install them.",
            extra={"markdown": True},
        )

        if (
            config.interactive
            and questionary.confirm("Install missing dependencies now?").unsafe_ask()
        ):
            # Install project dependencies, without upgrading
            deps.install_missing_dependencies()
