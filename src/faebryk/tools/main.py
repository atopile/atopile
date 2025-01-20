from faebryk.libs.tools.typer import typer_callback
from faebryk.tools.project import main as project_main
from faebryk.tools.refactor import main as refactor_main


@typer_callback(None)
def main():
    print("Running faebryk")
    pass


def __main__():
    main.add_typer(project_main, name="project")
    main.add_typer(refactor_main, name="refactor")
    main()


if __name__ == "__main__":
    __main__()
