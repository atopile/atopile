import logging

import click
from uvicorn.logging import ColourizedFormatter

from atopile.cli import build

# configure logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.formatter = ColourizedFormatter(
    fmt="%(levelprefix)s %(name)s %(message)s", use_colors=None
)
logging.root.addHandler(stream_handler)


# cli root
@click.version_option()
@click.group()
def cli():
    pass

cli.add_command(build.build)


if __name__ == "__main__":
    cli()
