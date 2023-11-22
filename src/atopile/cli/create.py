"""CLI command definition for `ato create`."""

import logging
import os
import sys
from pathlib import Path

import click
import yaml
from git import Repo

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@click.argument("name")
@click.option("--blank", is_flag=True)
def create(name: str, blank: bool):
    """
    Create a new project from the atopile project template. eg. `ato create my_project`
    """
    # Resolve the absolute path for the name argument
    project_path = Path(name).resolve()
    project_name = project_path.name
    project_dir = project_path.parent

    log.info(f"Project name: {project_name}")
    log.info(f"Project directory: {project_dir}")

    if project_path.exists():
        log.error(f"Directory {project_path} already exists. Aborting.")
        sys.exit(1)

    # Clone the project template into the project directory
    project_template_url = (
        "https://gitlab.atopile.io/atopile/atopile-project-template.git"
    )
    log.info("Cloning project template from " + project_template_url)
    project_repo = Repo.clone_from(url=project_template_url, to_path=project_path)

    for submodule in project_repo.submodules:
        submodule.update(init=True)

    # Rename files in the cloned project path
    rename_files(project_dir, project_name)

    # Update ato.yaml in the cloned project path
    ato_yaml_path = project_path / "elec/src/ato.yaml"
    update_ato_yaml(ato_yaml_path, project_name)

    # If blank is True, update the content of the .ato file to a blank module
    if blank:
        log.info("Blank project selected. Removing template code.")
        ato_file_path = project_path / f"elec/src/{project_name}.ato"
        update_file_content(ato_file_path, f"module {project_name}:")

    make_initial_commit(project_path)

    # After all changes are done locally, create a new repo on GitLab
    new_repo_url = (
        f"https://gitlab.atopile.io/atopile/{project_name}.git"
    )  # Placeholder URL
    try:
        # Now, change the remote URL to the new repository and push the changes
        push_to_new_repo(project_path, new_repo_url)
    except Exception as e:
        log.error(f"Failed to push to new repository: {e}")
        log.info(
            "We recommend you find a new home for your project and push it there manually."
        )


def update_ato_yaml(file_path: Path, new_base_name: str):
    # Read the YAML file
    with open(file_path, "r") as stream:
        data = yaml.safe_load(stream)

    # Modify the 'root-file' and 'root-node' keys
    data["builds"]["default"]["root-file"] = f"{new_base_name}.ato"
    data["builds"]["default"]["root-node"] = f"{new_base_name}.ato:{new_base_name}"

    # Write the modified YAML file back
    with open(file_path, "w") as stream:
        yaml.safe_dump(data, stream, default_flow_style=False)


def update_file_content(file_path: Path, module_name):
    # Open the file in write mode and replace its contents
    with open(file_path, "w") as file:
        file.write(f"module {module_name}:")


def rename_files(project_dir, new_base_name):
    # Define the path to the directory containing the files
    repo_path = Path(project_dir)

    # Mapping of old file names to new file names
    files_to_rename = {
        "atopile-project-template.kicad_pcb": f"{new_base_name}.kicad_pcb",
        "atopile-project-template.kicad_prl": f"{new_base_name}.kicad_prl",
        "atopile-project-template.kicad_pro": f"{new_base_name}.kicad_pro",
        "template_code.ato": f"{new_base_name}.ato",
    }

    # Walk through all files in the directory and its subdirectories
    for dirpath, dirnames, filenames in os.walk(repo_path):
        for filename in filenames:
            if filename in files_to_rename:
                old_path = Path(dirpath) / filename
                new_name = files_to_rename[filename]
                new_path = Path(dirpath) / new_name
                old_path.rename(new_path)
                log.debug(f"Renamed {old_path} to {new_path}")


def push_to_new_repo(local_repo_path, new_repo_url):
    repo = Repo(local_repo_path)
    repo.git.remote("set-url", "origin", new_repo_url)

    # Check the current branch name instead of assuming it's 'master'
    current_branch = repo.active_branch.name

    # Push the current branch and set it to track the remote branch
    repo.git.push("origin", current_branch, "-u")
    log.info(f"Pushed to new repository: {new_repo_url}")


def make_initial_commit(repo_path, message="Initial commit"):
    repo = Repo(repo_path)
    repo.git.add(A=True)
    repo.git.commit("-m", message)
    log.info("Made initial commit")


# TODO: add sub module import git submodule add https://gitlab.atopile.io/atopile/modules.git elec/src/modules
