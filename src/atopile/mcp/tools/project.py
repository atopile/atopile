import logging
from pathlib import Path

from atopile.mcp.util import MCPTools
from faebryk.libs.util import root_by_file

logger = logging.getLogger(__name__)

project_tools = MCPTools()


@project_tools.register()
def find_project_from_filepath(absolute_path_to_file: Path) -> Path:
    """
    Find the project root from an .ato file inside that project.
    """

    path = absolute_path_to_file
    logger.info(f"Finding project from filepath: {path}")
    if not path.is_absolute():
        raise ValueError("Path is not absolute")
    if not path.exists():
        raise ValueError(f"Path {path} does not exist")
    if not path.is_file():
        raise ValueError(f"Path {path} is not a file")

    if path.suffix != ".ato":
        raise ValueError("Path is not an ato file")

    return root_by_file("ato.yaml", path.parent)
