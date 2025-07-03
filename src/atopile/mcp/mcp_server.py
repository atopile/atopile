import logging
from enum import StrEnum
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.util import ConfigFlag, root_by_file

mcp = FastMCP("atopile", stateless_http=True)


logger = logging.getLogger(__name__)

DEBUG = ConfigFlag("MCP_DEBUG", default=False)


def _setup_debug(enable: bool = False):
    """
    Setup debug logging to file
    """
    if not enable:
        return

    handler = logging.FileHandler(Path(__file__).parent / "mcp.log")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


_setup_debug(enable=bool(DEBUG))


class Language(StrEnum):
    FABLL = "fabll(python)"
    ATO = "ato"


class NodeInfo(BaseModel):
    name: str
    docstring: str
    locator: str
    language: Language
    code: str


class NodeInfoOverview(BaseModel):
    name: str
    docstring: str
    language: Language


def run_mcp(http: bool = False):
    logger.info("Starting atopile MCP server...")
    mcp.run(transport="streamable-http" if http else "stdio")


def _get_library_nodes(t: type[Node]) -> list[NodeInfoOverview]:
    import faebryk.library._F as F

    return [
        NodeInfoOverview(
            name=m.__name__,
            docstring=m.__doc__ or "",
            language=Language.FABLL,
        )
        for m in F.__dict__.values()
        if isinstance(m, type) and issubclass(m, t)
    ]


def _locator_from_file_path(path: Path) -> str:
    return f"#file://{path.as_posix()}"


def _get_library_node(name: str, t: type[Node] = Node) -> NodeInfo:
    import faebryk.library._F as F

    if name not in F.__dict__:
        raise ValueError(f"Type {name} not found")

    m = F.__dict__[name]

    if not isinstance(m, type) or not issubclass(m, t):
        raise ValueError(f"Type {name} is not a valid {t.__name__}")

    # get file of module
    file = m.__module__
    if file is None:
        raise ValueError(f"Type {name} is not part of a module")

    # import the module to get its file path
    import importlib

    module = importlib.import_module(file)

    if module.__file__ is None:
        raise ValueError(f"Type {name} has no file")

    # read file
    filepath = module.__file__
    path = Path(filepath)
    code = path.read_text(encoding="utf-8")

    node = getattr(module, name)
    # get docstring
    docstring = node.__doc__

    language = Language.FABLL
    locator = _locator_from_file_path(path)
    return NodeInfo(
        name=name, docstring=docstring, locator=locator, language=language, code=code
    )


@mcp.tool()
def get_library_interfaces() -> list[NodeInfoOverview]:
    return _get_library_nodes(ModuleInterface)


@mcp.tool()
def inspect_library_module_or_interface(name: str) -> NodeInfo:
    return _get_library_node(name)


@mcp.tool()
def get_library_modules() -> list[NodeInfoOverview]:
    return _get_library_nodes(Module)


@mcp.tool()
def build_project(absolute_project_dir: str, target_name_from_yaml: str) -> str:
    from atopile.cli.build import build

    try:
        build(
            selected_builds=[target_name_from_yaml],
            entry=absolute_project_dir,
            open_layout=False,
        )
    except Exception as e:
        raise ValueError(f"Failed to build project: {e}")

    return f"Built project {absolute_project_dir} with target {target_name_from_yaml}"


@mcp.tool()
def find_project_from_filepath(absolute_path_to_file: Path) -> Path:
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
