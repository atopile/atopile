# pylint: disable=logging-fstring-interpolation

"""
This CLI command provides the `ato install` command to:
- install dependencies
- download JLCPCB footprints
"""

import logging
import subprocess
from itertools import chain
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import click
import requests
import ruamel.yaml
from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from atopile import config, errors, version

yaml = ruamel.yaml.YAML()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command("install")
@click.argument("to_install", required=False)
@click.option("--jlcpcb", is_flag=True, help="JLCPCB component ID")
@click.option("--upgrade", is_flag=True, help="Upgrade dependencies")
@errors.muffle_fatalities
def install(to_install: str, jlcpcb: bool, upgrade: bool, path: Optional[Path] = None):
    install_core(to_install, jlcpcb, upgrade, path)


def install_core(
    to_install: str, jlcpcb: bool, upgrade: bool, path: Optional[Path] = None
):
    """
    Install a dependency of for the project.
    """

    current_path = Path.cwd()
    top_level_path = config.get_project_dir_from_path(Path(path or current_path))

    log.info(f"Installing {to_install} in {top_level_path}")

    cfg = config.get_project_config_from_path(top_level_path)
    ctx = config.ProjectContext.from_config(cfg)

    with errors.handle_ato_errors():
        if jlcpcb:
            # eg. "ato install --jlcpcb=C123"
            install_jlcpcb(to_install, top_level_path)
        elif to_install:
            # eg. "ato install some-atopile-module"
            installed_semver = install_dependency(to_install, ctx.module_path, upgrade)
            module_name, module_spec = split_module_spec(to_install)
            if module_spec is None and installed_semver:
                # If the user didn't specify a version, we'll
                # use the one we just installed as a basis
                to_install = f"{module_name} ^{installed_semver}"
            set_dependency_to_ato_yaml(top_level_path, to_install)

        else:
            # eg. "ato install"
            for _ctx, module_name in errors.iter_through_errors(cfg.dependencies):
                with _ctx():
                    install_dependency(module_name, ctx.module_path, upgrade)

    log.info("[green]Done![/] :call_me_hand:", extra={"markup": True})


def get_package_repo_from_registry(module_name: str) -> str:
    """
    Get the git repo for a package from the ato registry.
    """
    response = requests.post(
        "https://get-package-atsuhzfd5a-uc.a.run.app",
        json={"name": module_name},
        timeout=10,
    )
    if response.status_code == 500:
        raise errors.AtoError(f"Could not find package '{module_name}' in registry.")
    response.raise_for_status()
    return_data = response.json()
    try:
        return_url = return_data["data"]["repo_url"]
    except KeyError:
        raise errors.AtoError(f"No repo_url found for package '{module_name}'")
    return return_url


def split_module_spec(spec: str) -> tuple[str, Optional[str]]:
    """Splits a module spec string into the module name and the version spec."""
    for splitter in chain(version.OPERATORS, (" ", "@")):
        if splitter in spec:
            splitter_loc = spec.find(splitter)
            if splitter_loc < 0:
                continue

            module_name = spec[:splitter_loc].strip()
            version_spec = spec[splitter_loc:].strip()
            return module_name, version_spec

    return spec, None


def set_dependency_to_ato_yaml(top_level_path: Path, module_spec: str):
    """Add deps to the ato.yaml file"""
    # Get the existing config data
    ato_yaml_path = top_level_path / "ato.yaml"
    if not ato_yaml_path.exists():
        raise errors.AtoError(f"ato.yaml not found in {top_level_path}")

    with ato_yaml_path.open("r") as file:
        data = yaml.load(file) or {}

    # Add module to dependencies, avoiding duplicates
    dependencies: list[str] = data.setdefault("dependencies", [])
    dependencies_by_name: dict[str, str] = {
        split_module_spec(x)[0]: x for x in dependencies
    }

    module_to_install, _ = split_module_spec(module_spec)
    if module_to_install in dependencies_by_name:
        existing_spec = dependencies_by_name[module_to_install]
        if existing_spec != module_spec:
            dependencies.remove(existing_spec)

    if module_spec not in dependencies:
        dependencies.append(module_spec)

        with ato_yaml_path.open("w") as file:
            yaml.dump(data, file)


def install_dependency(
    module: str, module_dir: Path, upgrade: bool = False
) -> Optional[version.Version]:
    """
    Install a dependency of the name "module_name"
    into the project to "top_level_path"
    """
    # Figure out what we're trying to install here
    module_uri, module_spec = split_module_spec(module)
    if not module_spec:
        module_spec = "*"

    # Ensure the modules path exists
    module_dir.mkdir(parents=True, exist_ok=True)

    parsed_url = urlparse(module_uri)
    if not parsed_url.scheme:
        module_name = module_uri
        clone_url = get_package_repo_from_registry(module_uri)
    else:
        module_name = parsed_url.path.split("/")[-1]
        clone_url = module_uri

    try:
        # This will raise an exception if the directory does not exist
        repo = Repo(module_dir / module_name)
    except (InvalidGitRepositoryError, NoSuchPathError):
        # Directory does not contain a valid repo, clone into it
        log.info(f"Installing dependency {module_name}")
        repo = Repo.clone_from(clone_url, module_dir / module_name)

    else:
        # In this case the directory exists and contains a valid repo
        if upgrade:
            log.info(f"Fetching latest changes for {module_name}")
            repo.remotes.origin.fetch()
        else:
            log.info(
                f"{module_name} already exists. If you wish to upgrade, use --upgrade"
            )
            # here we're done because we don't want to play with peoples' deps under them
            return

    # Figure out what version of this thing we need
    semver_to_tag = {}
    installed_semver = None
    for tag in repo.tags:
        try:
            semver_to_tag[version.parse(tag.name)] = tag
        except errors.AtoError:
            log.debug(f"Tag {tag.name} is not a valid semver tag. Skipping.")

    if "@" in module_spec:
        # If there's an @ in the version, we're gonna check that thing out
        best_checkout = module_spec.strip(" @")
    elif semver_to_tag:
        # Otherwise we're gonna find the best tag meeting the semver spec
        valid_versions = [v for v in semver_to_tag if version.match(module_spec, v)]
        if not valid_versions:
            raise errors.AtoError(
                f"No versions of {module_name} match spec {module_spec}.\n"
                f"Available versions: {', '.join(map(str, semver_to_tag))}"
            )
        installed_semver = max(valid_versions)
        best_checkout = semver_to_tag[installed_semver]
    else:
        log.warning(
            "No semver tags found for this module. Using latest default branch :hot_pepper:.",
            extra={"markup": True},
        )
        return None

    # If the repo is dirty, throw an error
    if repo.is_dirty():
        raise errors.AtoError(
            f"Module {module_name} has uncommitted changes. Aborting."
        )

    # Checkout the best thing we've found
    ref_before_checkout = repo.head.commit

    # If the repo best_checkout is a branch, we need to checkout the origin/branch
    if best_checkout in repo.heads:
        best_checkout = f"origin/{best_checkout}"

    repo.git.checkout(best_checkout)

    if repo.head.commit == ref_before_checkout:
        log.info(
            f"Already on the best option ([cyan bold]{best_checkout}[/]) for {module_name}",
            extra={"markup": True},
        )
    else:
        log.info(
            f"Using :sparkles: [cyan bold]{best_checkout}[/] :sparkles: of {module_name}",
            extra={"markup": True},
        )

    if installed_semver:
        return best_checkout


def install_jlcpcb(component_id: str, top_level_path: Path):
    """Install a component from JLCPCB"""
    component_id = component_id.upper()
    if not component_id.startswith("C") or not component_id[1:].isdigit():
        raise errors.AtoError(f"Component id {component_id} is invalid. Aborting.")

    footprints_dir = top_level_path / "elec/footprints/footprints"

    log.info(f"Footprints directory: {footprints_dir}")

    command = [
        "easyeda2kicad",
        "--full",
        f"--lcsc_id={component_id}",
        f"--output={footprints_dir}",
        "--overwrite",
        "--ato",
        f"--ato_file_path={top_level_path / 'elec/src'}",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    # The stdout and stderr are captured due to 'capture_output=True'
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # Check the return code to see if the command was successful
    if result.returncode == 0:
        print("Command executed successfully")
    else:
        component_link = f"https://jlcpcb.com/partdetail/{component_id}"
        raise errors.AtoError(
            "Oh no! Looks like this component doesnt have a model available. "
            f"More information about the component can be found here: {component_link}"
        )
