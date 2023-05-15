import click
from atopile.visualizer.server import visualize

@click.group()
def cli():
    pass

cli.add_command(visualize)

if __name__ == "__main__":
    cli()
