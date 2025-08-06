# pylint: disable=logging-fstring-interpolation

"""
This CLI command provides the `ato install` command to:
- install dependencies
- download JLCPCB footprints
"""

import logging
from pathlib import Path
from typing import Annotated

import typer

from atopile import errors
from atopile.telemetry import capture

logger = logging.getLogger(__name__)

dependencies_app = typer.Typer(rich_markup_mode="rich")


@capture(
    "cli:install_start", "cli:install_end", properties={"deprecated_command": True}
)
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
        Path | None,
        typer.Option(
            "--local",
            "-l",
            help="Install from local path",
            hidden=True,  # deprecated
        ),
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

    if local:
        raise errors.UserBadParameterError(
            "--local flag has been removed. Use `ato add file://` instead",
            extra={"markdown": True},
        )

    if not to_install:
        if upgrade:
            raise errors.UserBadParameterError(
                "Upgrade flag is only supported when adding a package."
            )
        return sync(path=path)
    else:
        return add([to_install], upgrade=upgrade, path=path)


@capture("cli:sync_start", "cli:sync_end")
def sync(
    # TODO: only relevant when supporting version specs
    # upgrade: Annotated[
    #    bool,
    #    typer.Option(
    #        "--upgrade", "-U", help="Allow package upgrades, ignoring pinned versions"
    #    ),
    # ] = False,
    path: Annotated[
        Path | None, typer.Option("--project-path", "-C", help="Path to the project")
    ] = None,
):
    # TODO don't like uv's help string
    """
    Update the project's environment
    """
    from atopile.config import config
    from faebryk.libs.backend.packages import api
    from faebryk.libs.project.dependencies import ProjectDependencies

    config.apply_options(None, working_dir=path)

    try:
        ProjectDependencies(install_missing=True, clean_unmanaged_dirs=True)
    except (
        api.Errors.PackageNotFoundError,
        api.Errors.ReleaseNotFoundError,
        api.Errors.InvalidPackageIdentifierError,
    ) as e:
        raise errors.UserException(f"Error syncing dependencies: {e}") from e

    logger.info("[green]Done![/] :call_me_hand:", extra={"markup": True})


@capture("cli:add_start", "cli:add_end")
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
    from atopile.config import DependencySpec, config
    from faebryk.libs.backend.packages import api
    from faebryk.libs.project.dependencies import ProjectDependencies

    if not package:
        raise errors.UserException("No package identifier provided")

    config.apply_options(None, working_dir=path)

    deps = ProjectDependencies(install_missing=True, clean_unmanaged_dirs=True)
    try:
        deps.add_dependencies(
            *[DependencySpec.from_str(p) for p in package], upgrade=upgrade
        )
    except (
        api.Errors.PackageNotFoundError,
        api.Errors.ReleaseNotFoundError,
        api.Errors.InvalidPackageIdentifierError,
    ) as e:
        raise errors.UserException(f"Error adding dependencies: {e}") from e

    logger.info("[green]Done![/] :call_me_hand:", extra={"markup": True})


@capture("cli:remove_start", "cli:remove_end")
def remove(
    package: Annotated[list[str], typer.Argument(help="Name of package to remove")],
    path: Annotated[
        Path | None, typer.Option("--project-path", "-C", help="Path to the project")
    ] = None,
):
    """
    Remove dependencies from the project
    """
    from atopile.config import config
    from faebryk.libs.project.dependencies import ProjectDependencies

    config.apply_options(None, working_dir=path)

    deps = ProjectDependencies()
    deps.remove_dependencies(*package)

    logger.info("[green]Done![/] :call_me_hand:", extra={"markup": True})


@capture("cli:list_start", "cli:list_end")
def list():
    """
    List all dependencies in the project
    """
    from faebryk.libs.project.dependencies import ProjectDependencies, ProjectDependency
    from faebryk.libs.util import md_list

    deps = ProjectDependencies()
    # TODO bug, if A -> B, B deps
    # will not see that B is under root, because of the way DAG checks roots
    import rich.markdown

    rich.print(
        rich.markdown.Markdown(
            md_list(
                deps.dag.to_tree(extra_roots=deps.direct_deps),
                recursive=True,
                mapper=lambda x: x.spec.identifier
                if isinstance(x, ProjectDependency)
                else x,
            )
        )
    )


dependencies_app.command()(add)
dependencies_app.command()(remove)
dependencies_app.command()(sync)
dependencies_app.command()(list)
