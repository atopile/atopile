from faebryk.libs.tools.typer import typer_callback
from faebryk.tools.libadd import main as libadd_main
from faebryk.tools.project import main as project_main


@typer_callback(None)
def main():
    print("Running faebryk")
    pass


def __main__():
    main.add_typer(libadd_main, name="libadd")
    main.add_typer(project_main, name="project")
    main()


if __name__ == "__main__":
    __main__()
