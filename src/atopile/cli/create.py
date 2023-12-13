import logging
import textwrap
from pathlib import Path

import click
import yaml
from caseconverter import kebabcase, pascalcase
from git import InvalidGitRepositoryError, Repo

from .install import install_dependencies_from_yaml, add_dependency_to_ato_yaml

# Set up logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Constants
PROJECT_BASE_URL = "https://gitlab.atopile.io/community-projects"
MODULES_BASE_URL = "https://gitlab.atopile.io/packages"
PROJECT_TEMPLATE_URL = "https://gitlab.atopile.io/atopile/atopile-project-template.git"
MODULES_TEMPLATE_URL = "https://gitlab.atopile.io/packages/module-template.git"
MODULES_DIR = ".ato/modules"


@click.command()
@click.argument("name")
def create(name: str):
    """
    Create a new project or module. If within a repo, creates a module.
    Otherwise, creates a new project.
    """
    processed_proj_name = kebabcase(name)
    project_type, project_path, top_level_dir = determine_project_type_and_path(processed_proj_name)
    clone_project_template(project_type, project_path)

    if project_type == "module":
        project_path, new_repo_url = init_module(project_path, top_level_dir, processed_proj_name)
    else:
        project_path, new_repo_url = init_project(project_path, top_level_dir, processed_proj_name)

    commit_message = f"Initial commit for {processed_proj_name}"
    commit_changes(project_path, commit_message)

    push_to_new_repo(project_path, new_repo_url)

    log.info(f"New project created at {PROJECT_BASE_URL}/{processed_proj_name}")

    if project_type == "module":
        logging.log(
            msg=f"New module created at {MODULES_BASE_URL}/{processed_proj_name}", level=logging.INFO
        )
    else:
        cwd = Path.cwd()
        prj_path = Path(processed_proj_name+"/")
        log.info(f"Installing dependencies for {cwd/prj_path}")
        install_dependencies_from_yaml(cwd/prj_path)
        logging.log(
            msg=f"New project created at {PROJECT_BASE_URL}/{processed_proj_name}", level=logging.INFO
        )


def determine_project_type_and_path(name):
    try:
        repo = Repo(".", search_parent_directories=True)
        top_level_dir = Path(repo.git.rev_parse("--show-toplevel"))
        project_type = "module"
        project_path = top_level_dir / ".ato" / "modules" / name
        log.info("Detected existing ato project. Creating a module.")
    except InvalidGitRepositoryError:
        project_type = "project"
        project_path = Path(name).resolve()
        top_level_dir = project_path.parent
        log.info("No ato project detected. Creating a new project.")
    return project_type, project_path, top_level_dir


def commit_changes(repo_path, commit_message):
    repo = Repo(repo_path)
    repo.git.add(A=True)  # Adds all changes to the staging area
    repo.index.commit(commit_message)  # Commits the changes


def clone_project_template(project_type, project_path):
    template_url = (
        MODULES_TEMPLATE_URL if project_type == "module" else PROJECT_TEMPLATE_URL
    )
    # if project_path.exists():
    #     log.error(f"Directory {project_path} already exists. Aborting.")
    #     sys.exit(1)
    log.info(f"Cloning from {template_url}")
    repo = Repo.clone_from(url=template_url, to_path=project_path)
    repo.git.remote("remove", "origin")


def init_module(module_path, top_level_dir, name):
    # Module-specific initialization logic
    new_repo_url = f"{MODULES_BASE_URL}/{name}.git"

    # Add dependency to ato.yaml
    add_dependency_to_ato_yaml(top_level_dir, name)

    # Add to projects gitignore
    with open(top_level_dir / ".gitignore", "a") as gitignore:
        gitignore.write(f"\n{name}/\n")

    return module_path, new_repo_url


def init_project(project_path: Path, top_level_dir, name):
    """
    Initialize a new project.
    """
    project_name = kebabcase(name)

    # Create project directory and any necessary files
    project_path.mkdir(parents=True, exist_ok=True)

    # We're using the following files as templates. If we
    # encounter the string "template123", we should
    # replace it with the project name
    rename_lines_in = [
        "elec/layout/default/template123.kicad_pro",
        "README.md",
        "elec/src/template123.ato",
    ]

    for file in rename_lines_in:
        file_path = project_path / file
        with open(file_path, "r") as f:
            lines = f.readlines()

        with open(file_path, "w") as f:
            for line in lines:
                if "template123" in line:
                    line = line.replace("template123", project_name)
                f.write(line)

    # Rename layout files
    # Move all the files prefixed with template123 to the new project name
    renamed_files: list[Path] = []
    for file in project_path.rglob("**/template123.*"):
        new_name = file.name.replace("template123", project_name)
        new_path = file.parent / new_name
        file.rename(new_path)
        renamed_files.append(new_path)

    # Update the entrypoint's name
    module_name = pascalcase(name)
    entry_file = project_path / f"elec/src/{project_name}.ato"
    with open(entry_file, "w") as f:
        f.write(
            textwrap.dedent(
                f"""
                module {module_name}:
                    # start here!
                """
            ).strip()
        )

    # Update the ato.yaml file with the new project name
    file_path = project_path / "ato.yaml"
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)

    data["builds"]["default"]["entry"] = f"elec/src/{project_name}.ato:{module_name}"

    with open(file_path, "w") as file:
        yaml.safe_dump(data, file)

    # Return the local path and the URL for the new project repository
    new_repo_url = f"git@gitlab.atopile.io:community-projects/{project_name}.git"

    return project_path, new_repo_url


def push_to_new_repo(local_repo_path, new_repo_url):
    """
    Push the local project to the new repository using SSH keys.
    """
    try:
        repo = Repo(local_repo_path)
        repo.git.remote("add", "origin", new_repo_url)
        current_branch = repo.active_branch.name
        repo.git.push("origin", current_branch, "-u")
        log.info(f"Pushed to new repository: {new_repo_url}")
        return True
    except Exception as e:
        log.error(f"Failed to push to new repository: {e}")
