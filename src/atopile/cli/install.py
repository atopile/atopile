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

import ruamel.yaml
import typer

from atopile import errors
from atopile.config import config
from atopile.telemetry import log_to_posthog
from faebryk.libs.project.dependencies import ProjectDependency

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
yaml = ruamel.yaml.YAML()


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

    for spec in package:
        ProjectDependency(spec).install(allow_upgrade=upgrade)

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


# --------------------------------------------------------------------------------------


# def install_single_dependency(to_install: str, vendor: bool, upgrade: bool):
#     dependency = DependencySpec.from_str(to_install)
#     name = _name_and_clone_url_helper(dependency.name)[0]
#     if vendor:
#         dependency.link_broken = True
#         abs_path = config.project.paths.src / name
#         dependency.path = abs_path.relative_to(config.project.paths.root)
#     else:
#         dependency.link_broken = False
#         abs_path = config.project.paths.modules / name
#         dependency.path = abs_path.relative_to(config.project.paths.root)
#
#     try:
#         installed_version = install_dependency(dependency, upgrade, abs_path)
#     except GitCommandError as ex:
#         if "already exists and is not an empty directory" in ex.stderr:
#             # FIXME: shouldn't `--upgrade` do this already?
#             raise errors.UserException(
#                 f"Directory {abs_path} already exists and is not empty. "
#                 "Please move or remove it before installing this new content."
#             ) from ex
#         raise
#     # If the link's broken, remove the .git directory so git treats it as copy-pasted code # noqa: E501  # pre-existing
#     if dependency.link_broken:
#         try:
#             robustly_rm_dir(abs_path / ".git")
#         except (PermissionError, OSError, FileNotFoundError) as ex:
#             with faebryk.libs.exceptions.downgrade(errors.UserException):
#                 raise errors.UserException(
#                     f"Failed to remove .git directory: {repr(ex)}"
#                 ) from ex
#
#     if dependency.version_spec is None and installed_version:
#         # If the user didn't specify a version, we'll
#         # use the one we just installed as a basis
#         dependency.version_spec = f"@{installed_version}"
#
#     ProjectConfig.set_or_add_dependency(config, dependency)
#
#
# def install_project_dependencies(upgrade: bool):
#     for _ctx, dependency in faebryk.libs.exceptions.iter_through_errors(
#         config.project.dependencies or []
#     ):
#         with _ctx():
#             if dependency.source and dependency.source.local:
#                 install_local_dependency(dependency)
#                 continue
#
#             if not dependency.link_broken:
#                 # FIXME: these dependency objects are a little too entangled
#                 name = _name_and_clone_url_helper(dependency.name)[0]
#                 abs_path = config.project.paths.modules / name
#                 dependency.path = abs_path.relative_to(config.project.paths.root)
#
#                 try:
#                     install_dependency(dependency, upgrade, abs_path)
#                 except GitCommandError as ex:
#                     if "already exists and is not an empty directory" in ex.stderr:
#                         # FIXME: shouldn't `--upgrade` do this already?
#                         raise errors.UserException(
#                             f"Directory {abs_path} already exists and is not empty. "
#                             "Please move or remove it before installing this new content."  # noqa: E501  # pre-existing
#                         ) from ex
#                     raise
#
#
# # ------------------------------------------------------------------------------------
#
#
# def install_dependency(
#     dependency: DependencySpec, upgrade: bool, abs_path: Path
# ) -> Optional[str]:
#     """
#     Install a dependency of the name "module_name"
#     """
#     # Ensure the modules path exists
#     abs_path.parent.mkdir(parents=True, exist_ok=True)
#
#     # Figure out what we're trying to install here
#     module_spec = dependency.version_spec or "*"
#     module_name, clone_url = _name_and_clone_url_helper(dependency.name)
#
#     try:
#         # This will raise an exception if the directory does not exist
#         repo = Repo(abs_path)
#     except (InvalidGitRepositoryError, NoSuchPathError):
#         # Directory does not contain a valid repo, clone into it
#         logger.info(f"Installing dependency `{module_name}`")
#         repo = Repo.clone_from(clone_url, abs_path)
#         tracking = repo.active_branch.tracking_branch()
#         if tracking:
#             tracking.checkout()
#         else:
#             logger.warning(
#                 f"No tracking branch found for {module_name}, using current branch"
#             )
#     else:
#         # In this case the directory exists and contains a valid repo
#         if upgrade:
#             logger.info(f"Fetching latest changes for {module_name}")
#             repo.remotes.origin.fetch()
#         else:
#             logger.info(
#                 f"{module_name} already exists. If you wish to upgrade, use --upgrade"
#             )
#             # here we're done because we don't want to play with peoples' deps under them # noqa: E501  # pre-existing
#             return
#
#     # Figure out what version of this thing we need
#     semver_to_tag = {}
#     installed_semver = None
#     for tag in repo.tags:
#         try:
#             semver_to_tag[version.parse(tag.name)] = tag
#         except errors.UserException:
#             logger.debug(f"Tag {tag.name} is not a valid semver tag. Skipping.")
#
#     if "@" in module_spec:
#         # If there's an @ in the version, we're gonna check that thing out
#         best_checkout = module_spec.strip(" @")
#     elif semver_to_tag:
#         # Otherwise we're gonna find the best tag meeting the semver spec
#         valid_versions = [v for v in semver_to_tag if version.match(module_spec, v)]
#         if not valid_versions:
#             raise errors.UserException(
#                 f"No versions of {module_name} match spec {module_spec}.\n"
#                 f"Available versions: {', '.join(map(str, semver_to_tag))}"
#             )
#         installed_semver = max(valid_versions)
#         best_checkout = semver_to_tag[installed_semver]
#     else:
#         logger.warning(
#             "No semver tags found for this module. Using latest default branch :hot_pepper:.",  # noqa: E501  # pre-existing
#             extra={"markup": True},
#         )
#         return None
#
#     # If the repo is dirty, throw an error
#     if repo.is_dirty():
#         raise errors.UserException(
#             f"Module {module_name} has uncommitted changes. Aborting."
#         )
#
#     # Checkout the best thing we've found
#     ref_before_checkout = repo.head.commit
#
#     # If the repo best_checkout is a branch, we need to checkout the origin/branch
#     if best_checkout in repo.heads:
#         best_checkout = f"origin/{best_checkout}"
#
#     repo.git.checkout(best_checkout)
#
#     if repo.head.commit == ref_before_checkout:
#         logger.info(
#             f"Already on the best option ([cyan bold]{best_checkout}[/]) for {module_name}",  # noqa: E501  # pre-existing
#             extra={"markup": True},
#         )
#     else:
#         logger.info(
#             f"Using :sparkles: [cyan bold]{best_checkout}[/] :sparkles: of {module_name}",  # noqa: E501  # pre-existing
#             extra={"markup": True},
#         )
#
#     return repo.head.commit.hexsha
#
#
# # ------------------------------------------------------------------------------------
#
#
# def check_missing_deps() -> bool:
#     for dependency in config.project.dependencies or []:
#         if dependency.path:
#             dep_path = config.project.paths.root / dependency.path
#         else:
#             # FIXME: this should exist based on defaults in the config
#             dep_path = config.project.paths.modules / dependency.name
#
#         if not dep_path.exists():
#             return True
#
#     return False
#
#
def check_missing_deps_or_offer_to_install():
    return


#     if check_missing_deps():
#         logger.warning(
#             "It appears some dependencies are missing."
#             " Run `ato install` to install them.",
#             extra={"markdown": True},
#         )
#
#         if (
#             config.interactive
#             and questionary.confirm("Install missing dependencies now?").unsafe_ask()
#         ):
#             # Install project dependencies, without upgrading
#             install_project_dependencies(False)
#
