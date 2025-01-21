import itertools
import logging
import re
import shutil
import sys
import tempfile
import textwrap
import webbrowser
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated, Any, Iterator, cast

import caseconverter
import click
import git
import jinja2
import questionary
import rich
import ruamel.yaml
import typer
from natsort import natsorted
from rich.table import Table

from atopile import errors
from atopile.cli.install import do_install
from atopile.config import PROJECT_CONFIG_FILENAME, config
from faebryk.libs.exceptions import downgrade
from faebryk.libs.picker.api.api import ApiHTTPError, Component
from faebryk.libs.picker.api.picker_lib import _extract_numeric_id
from faebryk.libs.picker.lcsc import download_easyeda_info
from faebryk.libs.pycodegen import (
    fix_indent,
    format_and_write,
    gen_block,
    gen_repeated_block,
    sanitize_name,
)
from faebryk.libs.util import (
    groupby,
    robustly_rm_dir,
)

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
            if questionary.confirm("Are you trying to exit?").unsafe_ask():
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
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
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
            name = questionary.text("").unsafe_ask()

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
            if questionary.confirm("").unsafe_ask():
                name = kebab_name

        if check_name(name):
            break
        else:
            help(
                "[red]Project names must start with a letter and"
                " contain only letters, numbers, dashes and underscores.[/]"
            )
            name = None

    assert name is not None

    if (
        not repo
        and not questionary.confirm(
            "Would you like to create a new repo for this project?"
        ).unsafe_ask()
    ):
        repo = PROJECT_TEMPLATE

    # Get a repo
    repo_obj: git.Repo | None = None
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
            if questionary.confirm("").unsafe_ask():
                webbrowser.open(make_repo_url)

            rich.print(":rocket: What's the [cyan]repo's URL?[/]")
            repo = questionary.text("").unsafe_ask()

        assert repo is not None

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

    assert repo_obj is not None
    assert repo_obj.working_tree_dir is not None

    # Configure the project
    do_configure(name, str(repo_obj.working_tree_dir), debug=False)

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
            robustly_rm_dir(Path(repo_obj.git_dir))
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
        link=True,
        upgrade=True,
        path=Path(repo_obj.working_tree_dir),
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
        name = caseconverter.kebabcase(
            questionary.text("Enter the build name").unsafe_ask()
        )

    try:
        top_level_path = config.project.paths.root
        layout_path = config.project.paths.layout
        src_path = config.project.paths.src
    except FileNotFoundError:
        raise errors.UserException(
            "Could not find the project directory, are you within an ato project?"
        )

    # Get user input for the entry file and module name
    rich.print("We will create a new ato file and add the entry to the ato.yaml")
    entry = questionary.text(
        "What would you like to call the entry file? (e.g., psuDebug)"
    ).unsafe_ask()

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
        ato_yaml_path = (
            top_level_path / config.project.paths.root / PROJECT_CONFIG_FILENAME
        )
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
    search_term: Annotated[str | None, typer.Option("--search", "-s")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    filename: Annotated[str | None, typer.Option("--filename", "-f")] = None,
    type_: Annotated[ComponentType | None, typer.Option("--type", "-t")] = None,
):
    """Create a new component."""
    from faebryk.libs.picker.api.models import Component
    from faebryk.libs.picker.api.picker_lib import client
    from faebryk.libs.pycodegen import sanitize_name

    try:
        config.apply_options(None)
    except errors.UserBadParameterError:
        config.apply_options(None, standalone=True)

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
                # TODO: remove this once we have a fuzzy search
                mfr = questionary.text("Enter the manufacturer").unsafe_ask()
                components = client.fetch_part_by_mfr(mfr, search_term)
        except ApiHTTPError as e:
            if e.response.status_code == 404:
                components = []
            else:
                raise

        if len(components) == 0:
            rich.print(f'No components found for "{search_term}"')
            search_term = None
            continue

        component_table = Table()
        component_table.add_column("Part Number")
        component_table.add_column("Manufacturer")
        component_table.add_column("Description")

        for component in components:
            component_table.add_row(
                component.manufacturer_name,
                component.part_number,
                component.description,
            )

        rich.print(component_table)

        choices = [
            {
                "name": f"{component.manufacturer_name} {component.part_number}",
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

    # TODO: templated ato components too
    # if type_ is None:
    #     type_ = ComponentType.fab
    if type_ is None:
        type_ = questionary.select(
            "Select the component type", choices=list(ComponentType)
        ).unsafe_ask()
        assert type_ is not None

    if name is None:
        name = questionary.text(
            "Enter the name of the component",
            default=caseconverter.pascalcase(
                sanitize_name(component.manufacturer_name + " " + component.part_number)
            ),
        ).unsafe_ask()

    sanitized_name = sanitize_name(name)
    if sanitized_name != name:
        rich.print(f"Sanitized name: {sanitized_name}")

    if type_ == ComponentType.ato:
        extension = ".ato"
    elif type_ == ComponentType.fab:
        extension = ".py"
    else:
        raise ValueError(f"Invalid component type: {type_}")

    out_path: Path | None = None
    for _ in stuck_user_helper_generator:
        if filename is None:
            filename = questionary.text(
                "Enter the filename of the component",
                default=caseconverter.snakecase(name) + extension,
            ).unsafe_ask()

        assert filename is not None

        filepath = Path(filename)
        if filepath.absolute():
            out_path = filepath.resolve()
        else:
            out_path = (config.project.paths.src / filename).resolve()

        if out_path.exists():
            rich.print(f"File {out_path} already exists")
            filename = None
            continue

        if not out_path.parent.exists():
            rich.print(
                f"Directory {out_path.parent} does not exist. Creating it now..."
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)

        break

    assert out_path is not None

    if type_ == ComponentType.ato:
        template = AtoTemplate(name=sanitized_name, base="Module")
        template.add_part(component)
        out = template.dumps()
        out_path.write_text(out)
        rich.print(f":sparkles: Created {out_path} !")

    elif type_ == ComponentType.fab:
        template = FabllTemplate(name=sanitized_name, base="Module")
        template.add_part(component)
        out = template.dumps()
        format_and_write(out, out_path)
        rich.print(f":sparkles: Created {out_path} !")


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


@dataclass
class CTX:
    path: Path
    pypath: str
    overwrite: bool


@dataclass
class Template(ABC):
    name: str
    base: str
    imports: list[str] = field(default_factory=list)
    nodes: list[str] = field(default_factory=list)
    docstring: str = "TODO: Docstring describing your module"

    def _process_part(self, part: Component) -> tuple[str, Any]:
        """Common part processing logic used by child classes."""
        name = sanitize_name(f"{part.manufacturer_name}_{part.part_number}")
        assert isinstance(name, str)
        _, _, _, _, easyeda_symbol, _ = download_easyeda_info(
            part.lcsc_display, get_model=False
        )
        return name, easyeda_symbol

    @abstractmethod
    def add_part(self, part: Component): ...


@dataclass
class AtoTemplate(Template):
    attributes: list[str] = field(default_factory=list)
    pins: list[str] = field(default_factory=list)
    defined_signals: set[str] = field(default_factory=set)

    def add_part(self, part: Component):
        # Get common processed data
        self.name, easyeda_symbol = self._process_part(part)

        # Set docstring with description
        self.docstring = part.description

        # Add component metadata
        self.attributes.extend(
            [
                f'lcsc_id = "{part.lcsc_display}"',
                f'manufacturer = "{part.manufacturer_name}"',
                f'mpn = "{part.part_number}"',
            ]
        )

        # Add datasheet if available
        if part.datasheet_url:
            self.attributes.append(f'datasheet_url = "{part.datasheet_url}"')

        # Add designator prefix from EasyEDA symbol
        designator_prefix = easyeda_symbol.info.prefix.replace("?", "")
        self.attributes.append(f'designator_prefix = "{designator_prefix}"')

        # Collect and sort pins first
        sorted_pins = []
        if hasattr(easyeda_symbol, "units") and easyeda_symbol.units:
            for unit in easyeda_symbol.units:
                if hasattr(unit, "pins"):
                    for pin in unit.pins:
                        pin_num = pin.settings.spice_pin_number
                        pin_name = pin.name.text
                        if (
                            pin_name
                            and pin_name not in ["NC", "nc"]
                            and not re.match(r"^[0-9]+$", pin_name)
                        ):
                            sorted_pins.append((sanitize_name(pin_name), pin_num))

        # Sort pins by name using natsort
        sorted_pins = natsorted(sorted_pins, key=lambda x: x[0])

        # Process sorted pins
        for pin_name, pin_num in sorted_pins:
            if pin_name not in self.defined_signals:
                self.pins.append(f"signal {pin_name} ~ pin {pin_num}")
                self.defined_signals.add(pin_name)
            else:
                self.pins.append(f"{pin_name} ~ pin {pin_num}")

    def dumps(self) -> str:
        output = f"component {self.name}:\n"
        output += f'    """{self.name} component"""\n'

        # Add attributes
        for attr in self.attributes:
            output += f"    {attr}\n"

        # Add blank line after attributes
        output += "\n"

        if self.pins:
            output += "    # pins\n"
            for pin in self.pins:
                output += f"    {pin}\n"

        return output


@dataclass
class FabllTemplate(Template):
    traits: list[str] = field(default_factory=list)

    def add_part(self, part: Component):
        # Get common processed data
        self.name, easyeda_symbol = self._process_part(part)

        designator_prefix = easyeda_symbol.info.prefix.replace("?", "")
        self.traits.append(
            f"designator_prefix = L.f_field(F.has_designator_prefix_defined)"
            f"('{designator_prefix}')"
        )

        self.traits.append(
            "lcsc_id = L.f_field(F.has_descriptive_properties_defined)"
            f"({{'LCSC': '{self.name}'}})"
        )

        self.imports.append(
            "from faebryk.libs.picker.picker import DescriptiveProperties"
        )
        self.traits.append(
            f"descriptive_properties = L.f_field(F.has_descriptive_properties_defined)"
            f"({{DescriptiveProperties.manufacturer: '{part.manufacturer_name}', "
            f"DescriptiveProperties.partno: '{part.part_number}'}})"
        )

        if url := part.datasheet_url:
            self.traits.append(
                f"datasheet = L.f_field(F.has_datasheet_defined)('{url}')"
            )

        partdoc = part.description.replace("  ", "\n")
        self.docstring = f"{self.docstring}\n\n{partdoc}"

        # pins --------------------------------
        no_name: list[str] = []
        no_connection: list[str] = []
        interface_names_by_pin_num: dict[str, str] = {}

        for unit in easyeda_symbol.units:
            for pin in unit.pins:
                pin_num = pin.settings.spice_pin_number
                pin_name = pin.name.text
                if re.match(r"^[0-9]+$", pin_name):
                    no_name.append(pin_num)
                elif pin_name in ["NC", "nc"]:
                    no_connection.append(pin_num)
                else:
                    pyname = sanitize_name(pin_name)
                    interface_names_by_pin_num[pin_num] = pyname

        self.nodes.append(
            "#TODO: Change auto-generated interface types to actual high level types"
        )

        _interface_lines_by_min_pin_num = {}
        for interface_name, _items in groupby(
            interface_names_by_pin_num.items(), lambda x: x[1]
        ).items():
            pin_nums = [x[0] for x in _items]
            line = f"{interface_name}: F.Electrical  # {"pin" if len(pin_nums) == 1 else "pins"}: {", ".join(pin_nums)}"  # noqa: E501  # pre-existing
            _interface_lines_by_min_pin_num[min(pin_nums)] = line
        self.nodes.extend(
            line
            for _, line in natsorted(
                _interface_lines_by_min_pin_num.items(), key=lambda x: x[0]
            )
        )

        if no_name:
            self.nodes.append(f"unnamed = L.list_field({len(no_name)}, F.Electrical)")

        pin_lines = (
            [
                f'"{pin_num}": self.{interface_name},'
                for pin_num, interface_name in interface_names_by_pin_num.items()
            ]
            + [f'"{pin_num}": None,' for pin_num in no_connection]
            + [f'"{pin_num}": self.unnamed[{i}],' for i, pin_num in enumerate(no_name)]
        )
        self.traits.append(
            fix_indent(f"""
            @L.rt_field
            def attach_via_pinmap(self):
                return F.can_attach_to_footprint_via_pinmap(
                    {{
                        {gen_repeated_block(natsorted(pin_lines))}
                    }}
                )
        """)
        )

    def dumps(self) -> str:
        always_import = [
            "import faebryk.library._F as F  # noqa: F401",
            f"from faebryk.core.{self.base.lower()} import {self.base}",
            "from faebryk.libs.library import L  # noqa: F401",
            "from faebryk.libs.units import P  # noqa: F401",
        ]

        self.imports = always_import + self.imports

        out = fix_indent(f"""
            # This file is part of the faebryk project
            # SPDX-License-Identifier: MIT

            import logging

            {gen_repeated_block(self.imports)}

            logger = logging.getLogger(__name__)

            class {self.name}({self.base}):
                \"\"\"
                {gen_block(self.docstring)}
                \"\"\"

                # ----------------------------------------
                #     modules, interfaces, parameters
                # ----------------------------------------
                {gen_repeated_block(self.nodes)}

                # ----------------------------------------
                #                 traits
                # ----------------------------------------
                {gen_repeated_block(self.traits)}

                def __preinit__(self):
                    # ------------------------------------
                    #           connections
                    # ------------------------------------

                    # ------------------------------------
                    #          parametrization
                    # ------------------------------------
                    pass
        """)

        return out
