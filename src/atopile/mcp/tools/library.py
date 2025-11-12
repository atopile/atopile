import logging
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.mcp.util import (
    Language,
    MCPTools,
    NodeInfo,
    NodeInfoOverview,
    NodeType,
)

logger = logging.getLogger(__name__)

library_tools = MCPTools()


def _locator_from_file_path(path: Path) -> str:
    return f"#file://{path.as_posix()}"


def _get_library_node(name: str, t: type[fabll.Node] = fabll.Node) -> NodeInfo:
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
    docstring = node.__doc__ or ""

    language = Language.FABLL
    locator = _locator_from_file_path(path)
    return NodeInfo(
        name=name, docstring=docstring, locator=locator, language=language, code=code
    )


@library_tools.register()
def inspect_library_module_or_interface(name: str) -> NodeInfo:
    """
    Inspect a standard library module or interface, returning information about its
    name, docstring, locator, language, and code.
    """
    return _get_library_node(name)

@library_tools.register()
def get_library_modules_or_interfaces(
    include_modules: bool = True,
    include_interfaces: bool = True,
    *,
    typegraph: fabll.TypeGraph,
) -> list[NodeInfoOverview]:
    """
    List all atopile standard library modules and interfaces.
    """
    if not include_modules and not include_interfaces:
        return []

    results: list[NodeInfoOverview] = []
    for m in F.__dict__.values():
        if not isinstance(m, type) or not issubclass(m, fabll.Node):
            continue

        bound = m.bind_typegraph(typegraph)
        is_interface = bound.check_if_instance_of_type_has_trait(fabll.is_interface)

        if is_interface and not include_interfaces:
            continue
        if not is_interface and not include_modules:
            continue

        results.append(
            NodeInfoOverview(
                name=m.__name__,
                docstring=m.__doc__ or "",
                language=Language.FABLL,
                type=NodeType.INTERFACE if is_interface else NodeType.MODULE,
            )
        )

    return results
