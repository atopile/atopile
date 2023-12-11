import logging
import subprocess
import sys
from pathlib import Path

import click
import yaml
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def install_dependency(module_name: str, top_level_path: Path, upgrade: bool = False):
    modules_path = top_level_path / ".ato" / "modules"
    modules_path.mkdir(parents=True, exist_ok=True)
    try:
        # This will raise an exception if the directory does not exist
        repo = Repo(modules_path / module_name)
    except (InvalidGitRepositoryError, NoSuchPathError):
        # Directory does not contain a valid repo, clone into it
        log.info(f"cloning {module_name} dependency")
        clone_url = f"https://gitlab.atopile.io/packages/{module_name}"
        Repo.clone_from(clone_url, modules_path / module_name)
    else:
        # In this case the directory exists and contains a valid repo
        if upgrade:
            log.info(f"pulling latest changes for {module_name}")
            repo.remotes.origin.pull()
        else:
            log.info(f"{module_name} already exists. skipping. If you wish to upgrade, use --upgrade")


def install_dependencies_from_yaml(top_level_path: Path, upgrade: bool = False):
    ato_yaml_path = top_level_path / "ato.yaml"
    if not ato_yaml_path.exists():
        logging.error("ato.yaml not found at the top level of the repo")
        return

    with ato_yaml_path.open("r") as file:
        data = yaml.safe_load(file) or {}

    dependencies = data.get("dependencies", [])
    for module_name in dependencies:
        install_dependency(module_name, top_level_path, upgrade)


@click.command()
@click.argument("module_name", required=False)
@click.option("--jlcpcb", required=False, help="JLCPCB component ID")
@click.option("--upgrade", is_flag=True, help="Upgrade dependencies")
def install(module_name: str, jlcpcb: str, upgrade: bool):
    repo = Repo(".", search_parent_directories=True)
    top_level_path = Path(repo.working_tree_dir)

    if module_name:
        # eg. "ato install some-atopile-module"
        install_dependency(module_name, top_level_path, upgrade)
        add_dependency_to_ato_yaml(top_level_path, module_name)
    elif jlcpcb:
        # eg. "ato install --jlcpcb=C123"
        install_jlcpcb(jlcpcb)
    else:
        # eg. "ato install"
        install_dependencies_from_yaml(top_level_path, upgrade)


def install_jlcpcb(component_id: str):
    component_id = component_id.upper()
    if not component_id.startswith("C") or not component_id[1:].isdigit():
        log.error(f"Component id {component_id} is invalid. Aborting.")
        sys.exit(1)

    # TODO: replace garbage below with project.path.lib_path when we restructure the ato.yaml

    # Get the top level of the git module the user is currently within
    repo = Repo(".", search_parent_directories=True)
    top_level_path = Path(repo.working_tree_dir)

    # Get the remote URL
    remote_url = repo.remote().url

    # Set the footprints_dir based on the remote URL
    if remote_url == "git@gitlab.atopile.io:atopile/modules.git":
        footprints_dir = top_level_path / "footprints"
    else:
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
    result = subprocess.run(command, capture_output=True, text=True)

    # The stdout and stderr are captured due to 'capture_output=True'
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # Check the return code to see if the command was successful
    if result.returncode == 0:
        print("Command executed successfully")
    else:
        print("Command failed")


def add_dependency_to_ato_yaml(top_level_path: Path, module_name: str):
    ato_yaml_path = top_level_path / "ato.yaml"
    if not ato_yaml_path.exists():
        logging.error("ato.yaml not found at the top level of the repo")
        return

    with ato_yaml_path.open("r") as file:
        data = yaml.safe_load(file) or {}

    # Add module to dependencies, avoiding duplicates
    dependencies: list[str] = data.setdefault("dependencies", [])
    if module_name not in dependencies:
        dependencies.append(module_name)

        with ato_yaml_path.open("w") as file:
            yaml.safe_dump(data, file, default_flow_style=False)
