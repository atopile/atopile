import itertools
import logging
import os
import re
import shutil
import stat
import sys
import tempfile
import textwrap
import webbrowser
from pathlib import Path
from typing import Iterator, Optional

import caseconverter
import click
import git
import jinja2
import rich
import ruamel.yaml

from atopile import config, errors
from atopile.cli.install import install_core

# Set up logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


PROJECT_TEMPLATE = "https://github.com/atopile/project-template"


def check_name(name: str) -> bool:
    """
    Check if a name is valid.
    """
    if re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", name):
        return True
    else:
        return False


def help(text: str) -> None:  # pylint: disable=redefined-builtin
    """Print help text."""
    rich.print("\n" + textwrap.dedent(text).strip() + "\n")


def _stuck_user_helper() -> Iterator[bool]:
    """Figure out if a user is stuck and help them exit."""
    threshold = 5
    for i in itertools.count():
        if i >= threshold:
            if rich.prompt.Confirm.ask("Are you trying to exit?"):
                rich.print("No worries! Try Ctrl+C next time!")
                exit(0)
            threshold += 5
        yield True


stuck_user_helper_generator = _stuck_user_helper()


@click.group()
def dev():
    pass



def _robustly_rm_dir(path: Path) -> None:
    """Remove a directory and all its contents."""
    def remove_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(path, onerror=remove_readonly)


def _in_git_repo(path: Path) -> bool:
    """Check if the current directory is in a git repo."""
    try:
        git.Repo(path)
    except git.InvalidGitRepositoryError:
        return False
    return True


@dev.command()
@click.argument("name", required=False)
@click.option("-r", "--repo", default=None)
def create(
    name: Optional[str],
    repo: Optional[str],
):  # pylint: disable=redefined-builtin
    """
    Create a new ato project or build configuration.
    """
    type = rich.prompt.Prompt.ask("What do you want to create", choices=["project", "build"])

    if type == "build":
        create_build()
        return

    # Get a project name
    kebab_name = None
    for _ in stuck_user_helper_generator:
        if not name:
            name = rich.prompt.Prompt.ask(
                ":rocket: What's your project [cyan]name?[/]", default=kebab_name
            )

        if name is None:
            continue

        kebab_name = caseconverter.kebabcase(name)
        if name != kebab_name:
            help(
                f"""
                We recommend using kebab-case ([cyan]{kebab_name}[/]) for your project name.
                It makes it easier to use your project with other tools (like git) and it embeds nicely into URLs.
                """
            )

            if rich.prompt.Confirm.ask(
                f"Do you want to use [cyan]{kebab_name}[/] instead?", default=True
            ):
                name = kebab_name

        if check_name(name):
            break
        else:
            help(
                "[red]Project names must start with a letter and"
                " contain only letters, numbers, dashes and underscores.[/]"
            )
            name = None

    if not repo and not rich.prompt.Confirm.ask(
        "Would you like to create a new repo for this project?"
    ):
        repo = PROJECT_TEMPLATE

    # Get a repo
    for _ in stuck_user_helper_generator:
        if not repo:
            make_repo_url = f"https://github.com/new?name={name}&template_owner=atopile&template_name=project-template"

            help(
                f"""
                We recommend you create a Github repo for your project.

                If you already have a repo, you can respond [yellow]n[/]
                to the next question and provide the URL to your repo.

                If you don't have one, you can respond yes to the next question
                or (Cmd/Ctrl +) click the link below to create one.

                Just select the template you want to use.

                {make_repo_url}
                """
            )
            if rich.prompt.Confirm.ask(
                ":rocket: Open browser to create Github repo?", default=True
            ):
                webbrowser.open(make_repo_url)

            repo = rich.prompt.Prompt.ask(":rocket: What's the [cyan]repo's URL?[/]")

        # Try download the repo from the user-provided URL
        if Path(name).exists():
            raise click.ClickException(
                f"Directory {name} already exists. Please put the repo elsewhere or choose a different name."
            )

        try:
            repo_obj = git.Repo.clone_from(repo, name, depth=1)
            break
        except git.GitCommandError as ex:
            help(
                f"""
                [red]Failed to clone repo from {repo}[/]

                {ex.stdout}
                {ex.stderr}
                """
            )
            repo = None

    # Configure the project
    do_configure(name, repo_obj.working_tree_dir, debug=False)

    # Commit the configured project
    # force the add, because we're potentially
    # modifying things in gitignored locations
    if repo_obj.is_dirty():
        repo_obj.git.add(A=True, f=True)
        repo_obj.git.commit(m="Configure project")
    else:
        rich.print(
            "[yellow]No changes to commit! Seems like the"
            " template you used mightn't be configurable?[/]"
        )

    # If this repo's remote it PROJECT_TEMPLATE, cleanup the git history
    if repo_obj.remotes.origin.url == PROJECT_TEMPLATE:
        try:
            _robustly_rm_dir(repo_obj.git_dir)
        except (PermissionError, OSError) as ex:
            errors.AtoError(
                f"Failed to remove .git directory: {repr(ex)}"
            ).log(log, logging.WARNING)
        if not _in_git_repo(Path(repo_obj.working_dir).parent):
            # If we've created this project OUTSIDE an existing git repo
            # then re-init the repo so it has a clean history
            clean_repo = git.Repo.init(repo_obj.working_tree_dir)
            clean_repo.git.add(A=True)
            clean_repo.git.commit(m="Initial commit")

    # Install dependencies listed in the ato.yaml, typically just generics
    install_core(
        to_install="", jlcpcb=False, upgrade=True, path=repo_obj.working_tree_dir
    )

    # Wew! New repo created!
    rich.print(f':sparkles: [green]Created new project "{name}"![/] :sparkles:')


def create_build():
    """
    Create a new build configuration.
    - adds entry to ato.yaml
    - creates a new directory in layout
    """
    build_name = caseconverter.kebabcase(rich.prompt.Prompt.ask("Enter the build name"))
    try:
        project_config = config.get_project_config_from_path(Path("."))
        project_context = config.ProjectContext.from_config(project_config)
        top_level_path = project_context.project_path
        layout_path = project_context.layout_path
        src_path = project_context.src_path
    except FileNotFoundError:
        raise errors.AtoError("Could not find the project directory, are you within an ato project?")

    # Get user input for the entry file and module name
    rich.print("We will create a new ato file and add the entry to the ato.yaml")
    entry = rich.prompt.Prompt.ask("What would you like to call the entry file? (e.g., psuDebug)")

    target_layout_path = layout_path / build_name
    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            git.Repo.clone_from(PROJECT_TEMPLATE, tmpdirname)
        except git.GitCommandError as ex:
            raise errors.AtoError(f"Failed to clone layout template from {PROJECT_TEMPLATE}: {repr(ex)}")
        source_layout_path = Path(tmpdirname) / "elec" / "layout" / "default"
        if not source_layout_path.exists():
            raise errors.AtoError(f"The specified layout path {source_layout_path} does not exist.")
        else:
            target_layout_path.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_layout_path, target_layout_path, dirs_exist_ok=True)
            # Configure the files in the directory using the do_configure function
            do_configure(build_name, str(target_layout_path), debug=False)

        # Add the build to the ato.yaml file
        ato_yaml_path = top_level_path / config.CONFIG_FILENAME
        # Check if ato.yaml exists
        if not ato_yaml_path.exists():
            print(f"ato.yaml not found in {top_level_path}. Please ensure the file exists before proceeding.")
        else:
            # Load the existing YAML configuration
            yaml = ruamel.yaml.YAML()
            with ato_yaml_path.open("r") as file:
                ato_config = yaml.load(file)

            entry_file = Path(caseconverter.kebabcase(entry)).with_suffix(".ato")
            entry_module = caseconverter.pascalcase(entry)

            # Update the ato_config with the new build information
            if "builds" not in ato_config:
                ato_config["builds"] = {}
            ato_config["builds"][build_name] = {
                "entry": f"elec/src/{entry_file}:{entry_module}"
            }

            # Write the updated configuration back to ato.yaml
            with ato_yaml_path.open("w") as file:
                yaml.dump(ato_config, file)


        # create a new ato file with the entry file and module
        ato_file = src_path / entry_file

        ato_file.write_text(f"module {entry_module}:\n \tsignal gnd\n")

        rich.print(f":sparkles: Successfully created a new build configuration for {build_name}! :sparkles:")


@dev.command()
@click.argument("name")
@click.argument("repo_path")
def configure(name: str, repo_path: str):
    """Command useful in developing templates."""
    do_configure(name, repo_path, debug=True)


def do_configure(name: str, _repo_path: str, debug: bool):
    """Configure the project."""
    repo_path = Path(_repo_path)
    try:
        author = git.Repo(repo_path).git.config("user.name")
    except (git.GitCommandError, git.InvalidGitRepositoryError):
        author = "Original Author"

    template_globals = {
        "name": name,
        "caseconverter": caseconverter,
        "repo_root": repo_path,
        "python_path": sys.executable,
        "author": author,
    }

    # Load templates
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(repo_path)))

    for template_path in repo_path.glob("**/*.j2"):
        # Figure out the target path and variables and what not
        target_path = template_path.parent / template_path.name.replace(
            ".j2", ""
        ).replace("__name__", caseconverter.kebabcase(name))

        template_globals["rel_path"] = target_path

        template = env.get_template(
            str(template_path.relative_to(repo_path).as_posix()),
            globals=template_globals,
        )

        # Make the noise!
        with target_path.open("w") as f:
            for chunk in template.generate():
                f.write(chunk)

        # Remove the template
        if not debug:
            template_path.unlink()


if __name__ == "__main__":
    dev()  # pylint: disable=no-value-for-parameter
