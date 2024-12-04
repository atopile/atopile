from typing import Annotated
import typer
import questionary

app = typer.Typer()
create_app = typer.Typer()
app.add_typer(create_app, name="create")


@create_app.command("project")
def create_project(name: str):
    print(f"Creating project: {name}")


@create_app.command("component")
def create_component(name: Annotated[str | None, typer.Argument()] = None):
    if name is None:
        name = questionary.path("Enter the component name").ask()

    print(f"Creating component: {name}")


@create_app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.resilient_parsing:
        return

    if not ctx.invoked_subcommand:
        command_name = questionary.select("Which command would you like to run?", choices=list(ctx.command.commands.keys())).ask()

        if command_name not in ctx.command.commands:
            raise typer.Abort()

        # Run the command
        ctx.invoke(ctx.command.commands[command_name].callback)


if __name__ == "__main__":
    app()
