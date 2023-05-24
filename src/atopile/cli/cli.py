import click
from atopile.visualizer.server import viewer
from . import build

@click.group()
def cli():
    pass

cli.add_command(viewer)
cli.add_command(build.build)

if __name__ == "__main__":
    cli()
