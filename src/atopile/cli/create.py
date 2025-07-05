import itertools
import logging
import re
import subprocess
import sys
import textwrap
from enum import StrEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Callable, Iterator, cast

import caseconverter
import questionary
import rich
import typer
from cookiecutter.exceptions import OutputDirExistsException
from cookiecutter.main import cookiecutter
from more_itertools import first
from rich.table import Table

from atopile import errors, version
from atopile.address import AddrStr
from atopile.config import PROJECT_CONFIG_FILENAME, config
from atopile.telemetry import capture
from faebryk.libs.github import (
    GithubCLI,
    GithubCLINotFound,
    GithubRepoAlreadyExists,
    GithubRepoNotFound,
    GithubUserNotLoggedIn,
)
from faebryk.libs.logging import rich_print_robust
from faebryk.libs.util import get_code_bin_of_terminal, try_or

if TYPE_CHECKING:
    import git

    from faebryk.libs.picker.api.api import Component

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


create_app = typer.Typer(
    rich_markup_mode="rich", help="Create projects / build targets / components"
)


def help(text: str) -> None:  # pylint: disable=redefined-builtin
    """Print help text."""
    rich_print_robust("\n" + textwrap.dedent(text).strip() + "\n")


def _stuck_user_helper() -> Iterator[bool]:
    """Figure out if a user is stuck and help them exit."""
    threshold = 5
    for i in itertools.count():
        if i >= threshold:
            if questionary.confirm("Are you trying to exit?").unsafe_ask():
                rich_print_robust("No worries! Try Ctrl+C next time!")
                exit(0)
            threshold += 5
        yield True


stuck_user_helper_generator = _stuck_user_helper()


def _in_git_repo(path: Path) -> bool:
    """Check if the current directory is in a git repo."""
    import git

    try:
        git.Repo(path)
    except git.InvalidGitRepositoryError:
        return False
    return True


def query_helper[T: str | Path | bool](
    prompt: str,
    type_: type[T],
    clarifier: Callable[[Any], T] = lambda x: x,
    upgrader: Callable[[T], T] = lambda x: x,
    upgrader_msg: str | None = None,
    validator: str | Callable[[T], bool] | None = None,
    validation_failure_msg: str | None = "Value [cyan]{value}[/] is invalid",
    default: T | None = None,
    pre_entered: T | None = None,
    validate_default: bool = True,
) -> T:
    """Query a user for input."""
    rich_print_robust(prompt)

    # Check the default value
    if default is not None:
        if not isinstance(default, type_):
            raise ValueError(f"Default value {default} is not of type {type_}")

    # Make a querier
    if type_ is str:

        def querier() -> str:  # type: ignore
            return questionary.text(
                "",
                default=str(default or ""),
            ).unsafe_ask()

    elif type_ is Path:

        def querier() -> Path:  # type: ignore
            return Path(
                questionary.path(
                    "",
                    default=str(default or ""),
                ).unsafe_ask()
            )

    elif type_ is bool:
        assert default is None or isinstance(default, bool)
        if default is None:
            default = True  # type: ignore

        def querier() -> bool:
            return questionary.confirm(
                "",
                default=default,  # type: ignore
            ).unsafe_ask()

    else:
        raise ValueError(f"Unsupported query type: `{type_}`")

    # Ensure a validator
    # Default the validator to a regex match if it's a str
    if validator is None:

        def validator_func(value: T) -> bool:
            return True

    elif isinstance(validator, str):

        def validator_func(value: T) -> bool:
            return bool(re.match(validator, value))  # type: ignore

        if not validation_failure_msg:
            validation_failure_msg = f'Value must match regex: `r"{validator}"`'

    else:
        validator_func = validator  # type: ignore

    # Ensure the default provided is valid
    if default is not None and validate_default:
        if not validator_func(clarifier(default)):
            logger.debug(f"Default value {default} is invalid")

        if clarifier(default) != upgrader(clarifier(default)):
            logger.debug(f"Default value {default} doesn't meet best-practice")

        default = upgrader(clarifier(default))

    # When running non-interactively, we expect the value to be provided
    # at the command level, so we don't need to query the user for it
    # Validate and return the pre-entered value
    if not config.interactive:
        if pre_entered is None:
            raise ValueError("Value is required. Check at command level.")

        if not validator_func(pre_entered):
            if validation_failure_msg:
                msg = validation_failure_msg.format(value=pre_entered)
            else:
                msg = f"Value {pre_entered} is invalid"
            raise errors.UserException(msg)

        return pre_entered

    # Pre-entered values are expected to skip the query for a value in the first place
    # but progress through the validator and upgrader if we're running interactively
    value: T | None = pre_entered

    for _ in stuck_user_helper_generator:
        if value is None:
            value = clarifier(querier())  # type: ignore
        assert isinstance(value, type_)

        if (proposed_value := upgrader(value)) != value:
            if upgrader_msg:
                rich_print_robust(upgrader_msg.format(proposed_value=proposed_value))

            rich_print_robust(f"Use [cyan]{proposed_value}[/] instead?")
            if questionary.confirm("").unsafe_ask():
                value = proposed_value

        if not validator_func(value):
            if validation_failure_msg:
                rich_print_robust(validation_failure_msg.format(value=value))
            value = None
            continue

        return value

    raise RuntimeError("Unclear how we got here")


PROJECT_NAME_REQUIREMENTS = (
    "Project name must start with a letter and contain only letters, numbers, dashes"
    " and underscores. It will be used for the project directory and name on GitHub"
)


def setup_github(
    project_path: Path,
    gh_cli: GithubCLI,
    repo: "git.Repo",
):
    import git

    github_username = gh_cli.get_usernames()

    use_existing_repo = query_helper(
        "Use an existing GitHub repo?",
        bool,
        default=False,
    )

    if use_existing_repo:

        def _check_repo_and_add_remote(repo_id: str) -> bool:
            try:
                url = gh_cli.get_repo_url(repo_id)
                repo.create_remote("origin", url)
                rich_print_robust(f"Added remote origin: {url}")
                # Try to push, but don't fail validation if it doesn't work
                # (e.g. repo not empty, or other reasons)
                try:
                    rich_print_robust(
                        f"Attempting to push initial commit to"
                        f" {repo.active_branch.name}..."
                    )
                    repo.git.push("-u", "origin", repo.active_branch.name)
                    rich_print_robust("[green]Pushed successfully![/]")
                except git.GitCommandError as e:
                    rich_print_robust(
                        f"[yellow]Could not push to remote:[/yellow] {e.stderr.strip()}"
                    )
                    rich_print_robust("You may need to push manually.")
                return True
            except GithubRepoNotFound:
                rich_print_robust(f"[red]Repository {repo_id} not found on GitHub.[/]")
                return False
            except git.GitCommandError as e:
                # This might happen if remote 'origin' already exists
                rich_print_robust(
                    f"[red]Failed to add remote:[/red] {e.stderr.strip()}"
                )
                return False
            except KeyboardInterrupt:
                rich_print_robust("[red]Aborted.[/red]")
                return False
            except Exception as e:
                rich_print_robust(f"[red]An unexpected error occurred:[/red] {e}")
                return False

        query_helper(
            ":rocket: What's the [cyan]repo's org and project name?[/]\n",
            str,
            default=f"{github_username[0]}/{project_path.name}",
            validator=_check_repo_and_add_remote,
            validation_failure_msg="Remote could not be added: {value}",
            validate_default=False,
        )
    else:

        def _create_repo_and_add_remote(repo_id: str) -> bool:
            try:
                # This will create the repo, add remote 'origin'
                #   and push the current dir
                # We are currently in project_path, which is the root of
                #   the new git repo
                # Ask for visibility
                visibility = questionary.select(
                    "Choose repository visibility:",
                    choices=["public", "private"],
                    default="public",
                ).unsafe_ask()

                repo_url = gh_cli.create_repo(
                    repo_id,
                    visibility=visibility,
                    add_remote=True,
                    path=project_path,
                )
                rich_print_robust(
                    f"[green]Successfully created repository {repo_url} and"
                    " pushed initial commit![/]"
                )
                return True
            except GithubRepoAlreadyExists:
                rich_print_robust(
                    f"[red]Repository {repo_id} already exists on GitHub.[/]"
                )
                # We could offer to use it, but for now, let's just fail validation
                return False
            except git.GitCommandError as e:
                # This might happen if the push fails for some reason
                rich_print_robust(
                    f"[red]Failed during git operation (e.g. push):[/red]"
                    f" {e.stderr.strip()}"
                )
                return False
            except KeyboardInterrupt:
                rich_print_robust("[red]Aborted.[/red]")
                return False
            except Exception as e:
                rich_print_robust(f"[red]An unexpected error occurred:[/red] {e}")
                return False

        query_helper(
            ":rocket: Choose a [cyan]repo org and name:[/]\n",
            str,
            default=f"{github_username[0]}/{project_path.name}",
            validator=_create_repo_and_add_remote,
            validation_failure_msg="Remote could not be added: {value}",
            validate_default=False,
        )


@create_app.command()
@capture("cli:create_project_start", "cli:create_project_end")
def project(path: Annotated[Path | None, typer.Option()] = None):
    """
    Create a new ato project.
    """
    TEMPLATE_DIR = Path(__file__).parent.parent / "project-template"

    extra_context = {
        "__ato_version": version.get_installed_atopile_version(),
        "__python_path": sys.executable,
    }

    if path is None:
        if config.interactive:
            path = query_helper(
                ":rocket: Where should we create the project?",
                type_=Path,
                default=Path.cwd(),
                pre_entered=path,
                validator=lambda x: x.is_dir(),
            )
        else:
            path = Path.cwd()

    logging.info("Running cookie-cutter on the template")
    try:
        project_path = Path(
            cookiecutter(
                str(TEMPLATE_DIR),
                output_dir=str(path),
                no_input=not config.interactive,
                extra_context=dict(
                    filter(lambda x: x[1] is not None, extra_context.items())
                ),
            )
        )
    except OutputDirExistsException as e:
        raise errors.UserException(
            "Directory already exists. Please choose a different name."
        ) from e

    try:
        import git

        no_git = False
    except ImportError as e:
        # catch no git executable
        if "executable" not in e.msg:
            raise
        no_git = True

    if not no_git:
        # check if already in a git repo
        create_git_repo = not _in_git_repo(project_path)

        # check if gh binary is available
        gh_cli = try_or(GithubCLI, catch=(GithubCLINotFound, GithubUserNotLoggedIn))

        # git repo
        if create_git_repo:
            logging.info("Initializing git repo")
            repo = git.Repo.init(project_path)
            repo.git.add(A=True, f=True)
            try:
                repo.git.commit(m="Initial commit")
            except git.GitCommandError as e:
                if "Author identity unknown" in e.stderr:
                    rich_print_robust(
                        "[yellow]Warning: Author identity unknown. "
                        "Staged but not committed.[/yellow]"
                    )
                else:
                    raise

        create_github_repo = False
        if config.interactive and gh_cli and create_git_repo:
            create_github_repo = query_helper(
                "Host this project on GitHub? :octopus::cat:",
                bool,
                default=False,
            )

        # Github repo
        if create_github_repo:
            assert gh_cli is not None
            try:
                setup_github(project_path, gh_cli, repo)
            except Exception:
                rich_print_robust("[red]Creating GitHub repo interrupted.[/red]")
                return

    # Wew! New repo created!
    rich_print_robust(
        f':sparkles: [green]Created new project "{project_path.name}"![/] :sparkles:'
    )

    # check if running in vscode / cursor terminal
    if code_bin := get_code_bin_of_terminal():
        # open in vscode / cursor
        subprocess.Popen([code_bin, project_path])
    else:
        rich_print_robust(f" \n[cyan]cd {project_path.relative_to(Path.cwd())}[/cyan]")


@create_app.command("build-target")
@capture("cli:create_build_target_start", "cli:create_build_target_end")
def build_target(
    build_target: Annotated[str | None, typer.Option()] = None,
    file: Annotated[Path | None, typer.Option()] = None,
    module: Annotated[str | None, typer.Option()] = None,
    backup_name: Annotated[str | None, typer.Argument()] = None,
):
    """
    Create a new build configuration.
    - adds entry to ato.yaml
    - creates a new directory in layout
    """
    config.apply_options(None)

    try:
        src_path = config.project.paths.src
        config.project_dir  # touch property to ensure config's loaded from a project
    except ValueError:
        raise errors.UserNoProjectException()

    if backup_name is None:
        if build_target:
            backup_name = build_target
        elif file:
            backup_name = file.name.split(".", 1)[0]
        elif module:
            backup_name = module

    # If we're running non-interactively, all details must be provided
    if not config.interactive and not all([build_target, file, module]):
        raise errors.UserException(
            "--build-target, --file, and --module must all be"
            " provided when running non-interactively."
        )

    def _check_build_target_name(value: str) -> bool:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", value):
            rich_print_robust(
                "[red]Build-target names must start with a letter and"
                " contain only letters, numbers, dashes and underscores.[/]"
            )
            return False

        if value in config.project.builds:
            rich_print_robust(f"[red]Build-target `{value}` already exists[/]")
            return False

        return True

    build_target = query_helper(
        ":rocket: What's the [cyan]build-target[/] name?",
        type_=str,
        upgrader=caseconverter.kebabcase,
        upgrader_msg="We recommend using kebab-case for build-target names.",
        validator=_check_build_target_name,
        validation_failure_msg="",
        pre_entered=build_target,
        default=caseconverter.kebabcase(backup_name) if backup_name else None,
    )

    def _file_clarifier(value: Path) -> Path:
        if not value.is_absolute():
            # If it's a relative path wrt ./ (cwd) then respect that
            # else assume it's relative to the src directory
            if str(value).startswith("./") or str(value).startswith(".\\"):
                value = Path(value).resolve()
            else:
                value = src_path / value

        return value

    def _file_updator(value: Path) -> Path:
        value = value.with_stem(caseconverter.snakecase(value.stem))
        if value.suffix != ".ato":
            # Allow dots in filenames
            value = value.with_suffix(value.suffix + ".ato")
        return value

    def _file_validator(f: Path) -> bool:
        if f.is_dir():
            rich_print_robust(f"{f} is a directory")
            return False

        if f.suffix != ".ato":
            rich_print_robust(f"{f} must end in .ato")
            return False

        try:
            f.relative_to(src_path)
        except ValueError:
            rich_print_robust(f"{f} is outside the project's src dir")
            return False

        return True

    file = query_helper(
        ":rocket: What [cyan]file[/] should we add the module to?",
        type_=Path,
        clarifier=_file_clarifier,
        upgrader=_file_updator,
        upgrader_msg=(
            "We recommend using snake_case for file names, and it must end in .ato"
        ),
        validator=_file_validator,
        validation_failure_msg="",
        pre_entered=file,
        default=Path(caseconverter.snakecase(backup_name or build_target) + ".ato"),
    )

    module = query_helper(
        ":rocket: What [cyan]module[/] should we add to the file?",
        type_=str,
        validator=str.isidentifier,
        validation_failure_msg="",
        upgrader=caseconverter.pascalcase,
        upgrader_msg="We recommend using pascal-case for module names.",
        pre_entered=module,
        default=caseconverter.pascalcase(backup_name or build_target),
    )

    logger.debug(f"Creating build-target with {build_target=}, {file=}, {module=}")

    # Update project config
    logger.info(
        f"Adding build-target to {config.project.paths.root / PROJECT_CONFIG_FILENAME}"
    )

    def add_build_target(config_data: dict, new_data: dict):
        config_data["builds"][build_target] = new_data
        return config_data

    config.update_project_settings(
        add_build_target, {"entry": str(AddrStr.from_parts(file, module))}
    )

    # Create or add to file
    module_text = f"module {module}:\n    pass\n"

    if file.is_file():  # exists and is a file
        with file.open("a", encoding="utf-8") as f:
            f.write("\n")
            f.write(module_text)

    else:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(module_text, encoding="utf-8")

    rich_print_robust(
        ":sparkles: Successfully created a new build configuration "
        f"[cyan]{build_target}[/] at [cyan]{file}[/]! :sparkles:"
    )


class ComponentType(StrEnum):
    ato = auto()
    fab = auto()


@create_app.command()
@capture("cli:create_component_start", "cli:create_component_end")
def part(
    search_term: Annotated[str | None, typer.Option("--search", "-s")] = None,
    accept_single: Annotated[bool, typer.Option("--accept-single", "-a")] = False,
    project_dir: Annotated[Path | None, typer.Option("--project-dir", "-p")] = None,
):
    """Create a new component."""
    from faebryk.libs.picker.api.api import ApiHTTPError
    from faebryk.libs.picker.api.picker_lib import _extract_numeric_id, client
    from faebryk.libs.picker.lcsc import download_easyeda_info

    config.apply_options(None, working_dir=project_dir)

    # Find a component --------------------------------------------------------

    component: Component | None = None

    for _ in stuck_user_helper_generator:
        if not search_term:
            search_term = questionary.text(
                "Search for a component (Part Number or LCSC ID):"
            ).unsafe_ask()
            assert search_term is not None

        try:
            lcsc_id = _extract_numeric_id(search_term)
        except ValueError:
            lcsc_id = None

        try:
            if lcsc_id:
                components = client.fetch_part_by_lcsc(lcsc_id)
            else:
                if ":" in search_term:
                    mfr, search_term = search_term.split(":", 1)
                else:
                    # TODO: remove this once we have a fuzzy search
                    mfr = questionary.text("Enter the manufacturer").unsafe_ask()
                components = client.fetch_part_by_mfr(mfr, search_term)
        except ApiHTTPError as e:
            if e.response.status_code == 404:
                components = []
            else:
                raise

        if len(components) == 0:
            if config.interactive:
                rich_print_robust(f'No components found for "{search_term}"')
                search_term = None
                continue
            else:
                raise errors.UserBadParameterError(
                    f"No matching components found for '{search_term}'"
                )

        component_table = Table()
        component_table.add_column("Manufacturer")
        component_table.add_column("Part Number")
        component_table.add_column("Description")
        component_table.add_column("Supplier ID")
        component_table.add_column("Stock")

        components = sorted(components, key=lambda c: c.stock, reverse=True)

        for component in components:
            component_table.add_row(
                component.manufacturer_name,
                component.part_number,
                component.description,
                component.lcsc_display,
                str(component.stock),
            )

        rich.print(component_table)

        if len(components) == 1 and accept_single:
            component = first(components)
        else:
            choices = [
                {
                    "name": f"{component.manufacturer_name} {component.part_number}"
                    f" ({component.lcsc_display})",
                    "value": component,
                }
                for component in components
            ] + [{"name": "Search again...", "value": None}]

            component = questionary.select(
                "Select a component", choices=choices
            ).unsafe_ask()

        if component is not None:
            break

        # Reset the input terms to start over if we didn't find what we're looking for
        search_term = None

    # We have a component -----------------------------------------------------
    assert component is not None
    from faebryk.libs.part_lifecycle import PartIsNotAutoGenerated, PartLifecycle

    try:
        epart = download_easyeda_info(component.lcsc_display, get_model=True)
        apart = PartLifecycle.singleton().library.ingest_part_from_easyeda(epart)
    except PartIsNotAutoGenerated as e:
        raise errors.UserException(
            f"Part `{e.part.path}` already exists and is manually modified."
        ) from e
    except Exception as e:
        raise errors.UserException(str(e)) from e

    rich_print_robust(
        f":sparkles: Created {apart.identifier} at {apart.path} ! Import with:\n"
    )
    rich_print_robust(
        f"```ato\n{apart.generate_import_statement(config.project.paths.src)}\n```",
        markdown=True,
    )

    return apart, component


@create_app.command(deprecated=True)
@capture(
    "cli:create_component_start",
    "cli:create_component_end",
    properties={"deprecated_command": True},
)
def component(
    search_term: Annotated[str | None, typer.Option("--search", "-s")] = None,
):
    return part(search_term)


@create_app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.resilient_parsing:
        return

    if not ctx.invoked_subcommand:
        commands = cast(dict, ctx.command.commands)  # type: ignore  # commands is an attribute of the context
        command_name = questionary.select(
            "What would you like to create?",
            choices=[n for n, c in commands.items() if not c.hidden],
        ).unsafe_ask()

        assert command_name in commands

        # Run the command
        ctx.invoke(commands[command_name].callback)


if __name__ == "__main__":
    create_app()  # pylint: disable=no-value-for-parameter
