import click
from atopile.visualizer.server import visualize
from . import build

@click.group()
def cli():
    pass

cli.add_command(visualize)
cli.add_command(build.build)

if __name__ == "__main__":
    cli()
