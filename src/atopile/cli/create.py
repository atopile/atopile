from enum import StrEnum, auto
import itertools
import logging
import re
import shutil
import sys
import tempfile
import textwrap
import webbrowser
from pathlib import Path
from typing import Annotated, Iterator, cast

import caseconverter
import click
import git
import jinja2
import questionary
import rich
import ruamel.yaml
import typer

from atopile import config, errors
from atopile.cli.common import configure_project_context
from atopile.cli.install import do_install
from atopile.utils import robustly_rm_dir
from faebryk.libs.exceptions import downgrade

# Set up logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


PROJECT_TEMPLATE = "https://github.com/atopile/project-template"

create_app = typer.Typer()


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
            if questionary.confirm("Are you trying to exit?").ask():
                rich.print("No worries! Try Ctrl+C next time!")
                exit(0)
            threshold += 5
        yield True


stuck_user_helper_generator = _stuck_user_helper()


def _in_git_repo(path: Path) -> bool:
    """Check if the current directory is in a git repo."""
    try:
        git.Repo(path)
    except git.InvalidGitRepositoryError:
        return False
    return True


@create_app.command()
def project(
    name: Annotated[str | None, typer.Argument()] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-r")] = None,
):  # pylint: disable=redefined-builtin
    """
    Create a new ato project.
    """

    # Get a project name
    kebab_name = None
    for _ in stuck_user_helper_generator:
        if not name:
            rich.print(":rocket: What's your project [cyan]name?[/]")
            name = questionary.text("").ask()

        if name is None:
            continue

        kebab_name = caseconverter.kebabcase(name)
        if name != kebab_name:
            help(
                f"""
                We recommend using kebab-case ([cyan]{kebab_name}[/])
                for your project name. It makes it easier to use your project
                with other tools (like git) and it embeds nicely into URLs.
                """
            )

            rich.print(f"Do you want to use [cyan]{kebab_name}[/] instead?")
            if questionary.confirm("").ask():
                name = kebab_name

        if check_name(name):
            break
        else:
            help(
                "[red]Project names must start with a letter and"
                " contain only letters, numbers, dashes and underscores.[/]"
            )
            name = None

    if (
        not repo
        and not questionary.confirm(
            "Would you like to create a new repo for this project?"
        ).ask()
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

            rich.print(":rocket: Open browser to create Github repo?")
            if questionary.confirm("").ask():
                webbrowser.open(make_repo_url)

            rich.print(":rocket: What's the [cyan]repo's URL?[/]")
            repo = questionary.text("").ask()

        # Try download the repo from the user-provided URL
        if Path(name).exists():
            raise click.ClickException(
                f"Directory {name} already exists. Please put the repo elsewhere or"
                " choose a different name."
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
            robustly_rm_dir(repo_obj.git_dir)
        except (PermissionError, OSError) as ex:
            with downgrade():
                raise errors.UserException(
                    f"Failed to remove .git directory: {repr(ex)}"
                ) from ex

        if not _in_git_repo(Path(repo_obj.working_dir).parent):
            # If we've created this project OUTSIDE an existing git repo
            # then re-init the repo so it has a clean history
            clean_repo = git.Repo.init(repo_obj.working_tree_dir)
            clean_repo.git.add(A=True)
            clean_repo.git.commit(m="Initial commit")

    # Install dependencies listed in the ato.yaml, typically just generics
    do_install(
        to_install=None,
        jlcpcb=False,
        link=True,
        upgrade=True,
        path=repo_obj.working_tree_dir,
    )

    # Wew! New repo created!
    rich.print(f':sparkles: [green]Created new project "{name}"![/] :sparkles:')


@create_app.command()
def build(
    name: Annotated[str | None, typer.Argument()] = None,
):
    """
    Create a new build configuration.
    - adds entry to ato.yaml
    - creates a new directory in layout
    """
    if not name:
        name = caseconverter.kebabcase(questionary.text("Enter the build name").ask())

    try:
        project_config = config.get_project_config_from_path(Path("."))
        project_context = config.ProjectContext.from_config(project_config)
        top_level_path = project_context.project_path
        layout_path = project_context.layout_path
        src_path = project_context.src_path
    except FileNotFoundError:
        raise errors.UserException(
            "Could not find the project directory, are you within an ato project?"
        )

    # Get user input for the entry file and module name
    rich.print("We will create a new ato file and add the entry to the ato.yaml")
    entry = questionary.text(
        "What would you like to call the entry file? (e.g., psuDebug)"
    ).ask()

    target_layout_path = layout_path / name
    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            git.Repo.clone_from(PROJECT_TEMPLATE, tmpdirname)
        except git.GitCommandError as ex:
            raise errors.UserException(
                f"Failed to clone layout template from {PROJECT_TEMPLATE}: {repr(ex)}"
            )
        source_layout_path = Path(tmpdirname) / "elec" / "layout" / "default"
        if not source_layout_path.exists():
            raise errors.UserException(
                f"The specified layout path {source_layout_path} does not exist."
            )
        else:
            target_layout_path.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_layout_path, target_layout_path, dirs_exist_ok=True)
            # Configure the files in the directory using the do_configure function
            do_configure(name, str(target_layout_path), debug=False)

        # Add the build to the ato.yaml file
        ato_yaml_path = top_level_path / config.CONFIG_FILENAME
        # Check if ato.yaml exists
        if not ato_yaml_path.exists():
            print(
                f"ato.yaml not found in {top_level_path}. Please ensure the file"
                " exists before proceeding."
            )
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
            ato_config["builds"][name] = {
                "entry": f"elec/src/{entry_file}:{entry_module}"
            }

            # Write the updated configuration back to ato.yaml
            with ato_yaml_path.open("w") as file:
                yaml.dump(ato_config, file)

        # create a new ato file with the entry file and module
        ato_file = src_path / entry_file
        ato_file.write_text(f"module {entry_module}:\n \tsignal gnd\n")

        rich.print(
            f":sparkles: Successfully created a new build configuration for {name}!"
            " :sparkles:"
        )


@create_app.command(hidden=True)
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


class ComponentType(StrEnum):
    ato = auto()
    fab = auto()


@create_app.command()
def component(
    lcsc: Annotated[str | None, typer.Option("--lcsc", "-l")] = None,
    mfr: Annotated[str | None, typer.Option("--mfr", "-m")] = None,
    mfr_pn: Annotated[str | None, typer.Option("--mfr-pn", "-p")] = None,
    type_: Annotated[ComponentType | None, typer.Option("--type", "-t")] = None,
):
    """Create a new component."""
    from natsort import natsorted

    from faebryk.libs.picker.api.picker_lib import (
        find_component_by_lcsc_id,
        find_component_by_mfr,
    )

    from faebryk.libs.picker.lcsc import download_easyeda_info
    from faebryk.libs.pycodegen import (
        fix_indent,
        format_and_write,
        gen_block,
        gen_repeated_block,
        sanitize_name,
    )
    import faebryk.libs.picker.lcsc as lcsc_
    from faebryk.tools.libadd import Template, find_part

    project_ctx = configure_project_context(None)

    # TODO: make lcsc build context aware
    # TODO: get these paths from the build context
    lcsc_.BUILD_FOLDER = project_ctx.project_path / "build"
    lcsc_.LIB_FOLDER = lcsc_.LIB_FOLDER / "kicad" / "libs"
    lcsc_.MODEL_PATH = None

    if lcsc:
        try:
            part = find_component_by_lcsc_id(name)
        except ValueError as e:
            raise errors.UserException(f"Invalid LCSC part number {name}") from e
        traits.append(
            "lcsc_id = L.f_field(F.has_descriptive_properties_defined)"
            f"({{'LCSC': '{name}'}})"
        )

    elif mfr:
        if "," in name:
            mfr_, mfr_pn = name.split(",", maxsplit=1)
        else:
            mfr_, mfr_pn = "", name
        try:
            part = find_component_by_mfr(mfr_, mfr_pn)
        except KeyErrorAmbiguous as e:
            # try find exact match
            try:
                part = find(e.duplicates, lambda x: x.mfr == mfr_pn)
            except KeyErrorNotFound:
                print(
                    f"Error: Ambiguous mfr_pn({mfr_pn}):"
                    f" {[(x.mfr_name, x.mfr) for x in e.duplicates]}"
                )
                print("Tip: Specify the full mfr_pn of your choice")
                sys.exit(1)


@create_app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """"""
    if ctx.resilient_parsing:
        return

    if not ctx.invoked_subcommand:
        commands = cast(dict, ctx.command.commands)  # type: ignore  # commands is an attribute of the context
        command_name = questionary.select(
            "What would you like to create?",
            choices=[n for n, c in commands.items() if not c.hidden],
        ).ask()

        assert command_name in commands

        # Run the command
        ctx.invoke(commands[command_name].callback)


if __name__ == "__main__":
    create_app()  # pylint: disable=no-value-for-parameter
