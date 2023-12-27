import itertools
import logging
import re
import textwrap
from pathlib import Path
from typing import Iterator, Optional

import caseconverter
import click
import requests
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
            help(
                f"""
                We recommend you create a Github repo for your project.

                If you don't have one, (Cmd/Ctrl +) click the link below to create one:

                [yellow]NOTE: only the public/private setting is important.[/]

                https://github.com/new?name={name}
                """
            )

            repo = rich.prompt.Prompt.ask(":rocket: What's the [cyan]repo's URL?[/]")

        # Check if it's an SSH repo
        if repo.startswith("git@"):
            if not rich.prompt.Confirm.ask(
                f"[cyan]{repo}[/] looks like an SSH repo. Is that correct?",
                default=True,
            ):
                repo = None
                continue
            # We can't further validate this easily
            break

        # Sanity check that the thing the user entered looks
        # like the repo for this project
        if not repo.startswith("https://github.com/") or not repo.endswith(name):
            if not rich.prompt.Confirm.ask(
                f"[cyan]{repo}[/] doesn't look like the right"
                " URL. Are you sure?",
                default=False,
            ):
                repo = None
                continue

        # Check something exists at the repo URL
        url_okay = True
        try:
            if not requests.get(repo, timeout=3).status_code == 200:
                url_okay = False
        except requests.exceptions.ConnectionError:
            url_okay = False

        if not url_okay:
            if not rich.prompt.Confirm.ask(
                f"[cyan]{repo}[/] doesn't seem to exist."
                " This may happen if the repo isn't public."
                " Are you sure?",
                default=False,
            ):
                repo = None
                continue

        # If we made it this far, we're good
        break

    rich.print(
        " ".join(
            [
                "ato create",
                "name ==",
                str(name),
                "type ==",
                str(type),
                "repo ==",
                str(repo),
            ]
        )
    )


if __name__ == "__main__":
    create()  # pylint: disable=no-value-for-parameter
