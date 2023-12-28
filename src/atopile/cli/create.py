import itertools
import logging
import os
import re
import sys
import textwrap
import webbrowser
from pathlib import Path
from typing import Iterator, Optional

import caseconverter
import click
import git
import rich
import rich.prompt

# Set up logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


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


PROJECT_TYPES = ["board", "module"]


@click.command()
@click.argument("name", required=False)
@click.option(
    "--type", type=click.Choice(PROJECT_TYPES, case_sensitive=False), default=None
)
@click.option("-r", "--repo", default=None)
def create(
    name: Optional[str], type: Optional[str], repo: Optional[str]
):  # pylint: disable=redefined-builtin
    """
    Create a new ato project.
    """
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

    # Get a project type
    for _ in stuck_user_helper_generator:
        if not type:
            type = rich.prompt.Prompt.ask(
                ":rocket: What type of project is this?",
                choices=PROJECT_TYPES,
                default="board",
            )

        if type in PROJECT_TYPES:
            break
        else:
            help(
                f"[red]{type}[/] is not a valid project type."
                f" Please choose one of [cyan]{', '.join(PROJECT_TYPES)}[/]."
            )
            type = None

    # Get a repo
    for _ in stuck_user_helper_generator:
        if not repo:
            make_repo_url = f"https://github.com/new?name={name}&template_owner=atopile&template_name=project-template"

            if rich.prompt.Confirm.ask(":rocket: Open browser to create Github repo?", default=True):
                webbrowser.open(make_repo_url)
            else:
                help(
                    f"""
                    We recommend you create a Github repo for your project.

                    If you don't have one, (Cmd/Ctrl +) click the link below to create one:

                    [yellow]NOTE: only the public/private setting is important.[/]

                    {make_repo_url}
                    """
                )

            repo = rich.prompt.Prompt.ask(":rocket: What's the [cyan]repo's URL?[/]")

        # Try download the repo from the user-provided URL
        try:
            repo_obj = git.Repo.clone_from(repo, name)
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
    configure_path = Path(repo_obj.working_tree_dir) / "configure.py"
    if not configure_path.exists():
        rich.print("[yellow]No configure.py found. Skipping.[/]")
    else:
        if os.system(f"{sys.executable} {configure_path} --no-debug {name}"):
            rich.print("[red]configure.py failed.[/]")
            raise click.Abort()

    # Commit the configured project
    # force the add, because we're potentially modifying things in gitiignored locations
    repo_obj.git.add(A=True, f=True)
    repo_obj.git.commit(m="Configure project")

    # Wew! New repo created!
    rich.print(f":sparkles: [green]Created new project \"{name}\"![/] :sparkles:")

if __name__ == "__main__":
    create()  # pylint: disable=no-value-for-parameter
