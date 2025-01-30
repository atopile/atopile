# pylint: disable=logging-fstring-interpolation

"""
This CLI command provides the `ato install` command to:
- install dependencies
- download JLCPCB footprints
"""

import logging
from pathlib import Path
from typing import Annotated, Optional
from urllib.parse import quote, urlparse

import questionary
import requests
import ruamel.yaml
import typer
from git import GitCommandError, InvalidGitRepositoryError, NoSuchPathError, Repo

import faebryk.libs.exceptions
from atopile import errors, version
from atopile.config import Dependency, ProjectConfig, config
from faebryk.libs.util import robustly_rm_dir
import shutil

yaml = ruamel.yaml.YAML()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
        bool, typer.Option("--local", "-l", help="Install from local path")
    ] = False,
    upgrade: Annotated[
        bool, typer.Option("--upgrade", "-u", help="Upgrade dependencies")
    ] = False,
    path: Annotated[Path | None, typer.Argument()] = None,
):
    """
    Install atopile packages or components from jlcpcb.com/parts
    """
    if jlcpcb:
        raise errors.UserBadParameterError(
            "--jlcpcb flag has been replaced by `ato create component`"
        )

    config.apply_options(None)

    do_install(to_install, vendor, upgrade, path)


def do_install(
    to_install: str | None,
    vendor: bool,
    upgrade: bool,
    path: Path | None,
):
    """
    Actually do the installation of the dependencies.
    This is split in two so that it can be called from `install` and `create`
    """

    if path is not None:
        config.project_dir = path

    if to_install is None:
        logger.info(f"Installing all dependencies in {config.project.paths.root}")
    else:
        logger.info(f"Installing {to_install} in {config.project.paths.root}")

    if to_install:
        # eg. "ato install some-atopile-module"
        install_single_dependency(to_install, vendor, upgrade)
    else:
        # eg. "ato install"
        install_project_dependencies(upgrade)

    logger.info("[green]Done![/] :call_me_hand:", extra={"markup": True})


def get_package_repo_from_registry(module_name: str) -> str:
    """
    Get the git repo for a package from the ato registry.
    """
    try:
        encoded_name = quote(module_name)
        response = requests.get(
            f"{config.project.services.packages.url}/v0/package/{encoded_name}",
            timeout=10,
        )
    except requests.exceptions.ReadTimeout as ex:
        raise errors.UserInfraError(
            f"Request to registry timed out for package '{module_name}'"
        ) from ex

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        try:
            _ = response.json()["detail"]
            if response.status_code == 404:
                raise errors.UserException(
                    f"Could not find package '{module_name}' in registry.",
                    markdown=False,
                ) from None
        except (KeyError, requests.exceptions.JSONDecodeError):
            pass

        raise errors.UserException(
            f"Error getting data for package '{module_name}': \n{ex}",
            markdown=False,
        )

    return_data = response.json()

    try:
        return_url = return_data["data"]["repo_url"]
    except KeyError as ex:
        raise errors.UserException(
            f"No repo_url found for package '{module_name}'"
        ) from ex
    return return_url


def install_single_dependency(to_install: str, vendor: bool, upgrade: bool):
    dependency = Dependency.from_str(to_install)
    name = _name_and_clone_url_helper(dependency.name)[0]
    if vendor:
        dependency.link_broken = True
        abs_path = config.project.paths.src / name
        dependency.path = abs_path.relative_to(config.project.paths.root)
    else:
        dependency.link_broken = False
        abs_path = config.project.paths.modules / name
        dependency.path = abs_path.relative_to(config.project.paths.root)

    try:
        installed_version = install_dependency(dependency, upgrade, abs_path)
    except GitCommandError as ex:
        if "already exists and is not an empty directory" in ex.stderr:
            # FIXME: shouldn't `--upgrade` do this already?
            raise errors.UserException(
                f"Directory {abs_path} already exists and is not empty. "
                "Please move or remove it before installing this new content."
            ) from ex
        raise
    # If the link's broken, remove the .git directory so git treats it as copy-pasted code # noqa: E501  # pre-existing
    if dependency.link_broken:
        try:
            robustly_rm_dir(abs_path / ".git")
        except (PermissionError, OSError, FileNotFoundError) as ex:
            with faebryk.libs.exceptions.downgrade(errors.UserException):
                raise errors.UserException(
                    f"Failed to remove .git directory: {repr(ex)}"
                ) from ex

    if dependency.version_spec is None and installed_version:
        # If the user didn't specify a version, we'll
        # use the one we just installed as a basis
        dependency.version_spec = f"@{installed_version}"

    def add_dependency(config_data, new_data):
        config_data["dependencies"] = [
            dep.model_dump()
            # add_dependencies is the field validator that loads the dependencies
            # from the config file. It ensures the format of the ato.yaml
            for dep in ProjectConfig.add_dependencies(
                config_data.get("dependencies"),
            )  # type: ignore  add_dependencies is a classmethod
        ]

        for i, dep in enumerate(config_data["dependencies"]):
            if dep["name"] == new_data["name"]:
                config_data["dependencies"][i] = new_data
                break
        else:
            config_data["dependencies"] = config_data["dependencies"] + [new_data]

        return config_data

    config.update_project_config(add_dependency, dependency.model_dump())


def install_project_dependencies(upgrade: bool):
    for _ctx, dependency in faebryk.libs.exceptions.iter_through_errors(
        config.project.dependencies or []
    ):
        with _ctx():
            if dependency.local:
                install_local_dependency(dependency)
                continue
            
            if not dependency.link_broken:
                # FIXME: these dependency objects are a little too entangled
                name = _name_and_clone_url_helper(dependency.name)[0]
                abs_path = config.project.paths.modules / name
                dependency.path = abs_path.relative_to(config.project.paths.root)

                try:
                    install_dependency(dependency, upgrade, abs_path)
                except GitCommandError as ex:
                    if "already exists and is not an empty directory" in ex.stderr:
                        # FIXME: shouldn't `--upgrade` do this already?
                        raise errors.UserException(
                            f"Directory {abs_path} already exists and is not empty. "
                            "Please move or remove it before installing this new content."  # noqa: E501  # pre-existing
                        ) from ex
                    raise

def install_local_dependency(dependency: Dependency):
    src = dependency.local
    dst = dependency.path or config.project.paths.modules / dependency.name
    if not src.exists():
        raise errors.UserException(f"Local dependency path {src} does not exist")
    shutil.copytree(src, dst, dirs_exist_ok=True)

def install_dependency(
    dependency: Dependency, upgrade: bool, abs_path: Path
) -> Optional[str]:
    """
    Install a dependency of the name "module_name"
    """
    # Ensure the modules path exists
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    # Figure out what we're trying to install here
    module_spec = dependency.version_spec or "*"
    module_name, clone_url = _name_and_clone_url_helper(dependency.name)

    try:
        # This will raise an exception if the directory does not exist
        repo = Repo(abs_path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        # Directory does not contain a valid repo, clone into it
        logger.info(f"Installing dependency `{module_name}`")
        repo = Repo.clone_from(clone_url, abs_path)
        tracking = repo.active_branch.tracking_branch()
        if tracking:
            tracking.checkout()
        else:
            logger.warning(
                f"No tracking branch found for {module_name}, using current branch"
            )
    else:
        # In this case the directory exists and contains a valid repo
        if upgrade:
            logger.info(f"Fetching latest changes for {module_name}")
            repo.remotes.origin.fetch()
        else:
            logger.info(
                f"{module_name} already exists. If you wish to upgrade, use --upgrade"
            )
            # here we're done because we don't want to play with peoples' deps under them # noqa: E501  # pre-existing
            return

    # Figure out what version of this thing we need
    semver_to_tag = {}
    installed_semver = None
    for tag in repo.tags:
        try:
            semver_to_tag[version.parse(tag.name)] = tag
        except errors.UserException:
            logger.debug(f"Tag {tag.name} is not a valid semver tag. Skipping.")

    if "@" in module_spec:
        # If there's an @ in the version, we're gonna check that thing out
        best_checkout = module_spec.strip(" @")
    elif semver_to_tag:
        # Otherwise we're gonna find the best tag meeting the semver spec
        valid_versions = [v for v in semver_to_tag if version.match(module_spec, v)]
        if not valid_versions:
            raise errors.UserException(
                f"No versions of {module_name} match spec {module_spec}.\n"
                f"Available versions: {', '.join(map(str, semver_to_tag))}"
            )
        installed_semver = max(valid_versions)
        best_checkout = semver_to_tag[installed_semver]
    else:
        logger.warning(
            "No semver tags found for this module. Using latest default branch :hot_pepper:.",  # noqa: E501  # pre-existing
            extra={"markup": True},
        )
        return None

    # If the repo is dirty, throw an error
    if repo.is_dirty():
        raise errors.UserException(
            f"Module {module_name} has uncommitted changes. Aborting."
        )

    # Checkout the best thing we've found
    ref_before_checkout = repo.head.commit

    # If the repo best_checkout is a branch, we need to checkout the origin/branch
    if best_checkout in repo.heads:
        best_checkout = f"origin/{best_checkout}"

    repo.git.checkout(best_checkout)

    if repo.head.commit == ref_before_checkout:
        logger.info(
            f"Already on the best option ([cyan bold]{best_checkout}[/]) for {module_name}",  # noqa: E501  # pre-existing
            extra={"markup": True},
        )
    else:
        logger.info(
            f"Using :sparkles: [cyan bold]{best_checkout}[/] :sparkles: of {module_name}",  # noqa: E501  # pre-existing
            extra={"markup": True},
        )

    return repo.head.commit.hexsha


def check_missing_deps() -> bool:
    for dependency in config.project.dependencies or []:
        if dependency.path:
            dep_path = config.project.paths.root / dependency.path
        else:
            # FIXME: this should exist based on defaults in the config
            dep_path = config.project.paths.modules / dependency.name

        if not dep_path.exists():
            return True

    return False


def check_missing_deps_or_offer_to_install():
    if check_missing_deps():
        logger.warning(
            "It appears some dependencies are missing."
            " Run `ato install` to install them.",
            extra={"markdown": True},
        )

        if (
            config.interactive
            and questionary.confirm("Install missing dependencies now?").unsafe_ask()
        ):
            # Install project dependencies, without upgrading
            install_project_dependencies(False)


def _name_and_clone_url_helper(name: str) -> tuple[str, str]:
    """Return the name of the package and the URL to clone it from."""
    parsed_url = urlparse(name)
    if not parsed_url.scheme:
        return name, get_package_repo_from_registry(name)
    else:
        splitted = parsed_url.path.split("/")
        return splitted[-1] or splitted[-2], name
