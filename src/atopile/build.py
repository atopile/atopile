from typing import TYPE_CHECKING

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from atopile.cli.logging_ import LoggingStage
from atopile.config import BuildType, config

if TYPE_CHECKING:
    from atopile.compiler.build import Linker


def init_app() -> "fabll.Node":
    with LoggingStage(name=f"init-{config.build.name}", description="Initializing app"):
        import faebryk.library._F as F
        from atopile.compiler.build import Linker, StdlibRegistry

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        stdlib = StdlibRegistry(tg)
        linker = Linker(config, stdlib, tg)

        match config.build.build_type:
            case BuildType.ATO:
                app = _init_ato_app(g=g, tg=tg, linker=linker)
            case BuildType.PYTHON:
                app = _init_python_app(g=g, tg=tg)
                fabll.Traits.create_and_add_instance_to(app, F.is_app_root)
                app.no_include_parents_in_full_name = True
            case _:
                raise ValueError(f"Unknown build type: {config.build.build_type}")

        return app


def _init_python_app(*, g: "graph.GraphView", tg: "fbrk.TypeGraph") -> "fabll.Node":
    """Initialize a specific .py build."""

    from atopile import errors
    from faebryk.libs.util import import_from_path

    try:
        app_class = import_from_path(
            config.build.entry_file_path, config.build.entry_section
        )
    except FileNotFoundError as e:
        raise errors.UserFileNotFoundError(
            f"Cannot find build entry {config.build.address}"
        ) from e
    except Exception as e:
        raise errors.UserPythonModuleError(
            f"Cannot import build entry {config.build.address}"
        ) from e

    if not isinstance(app_class, type):
        raise errors.UserPythonLoadError(
            f"Build entry {config.build.address} is not a module we can instantiate"
        )
    # check app_class is direct subclass of fabll.Node
    if not issubclass(app_class, fabll.Node):
        raise errors.UserPythonConstructionError(
            f"Build entry {config.build.address} is not a subclass of fabll.Node"
        )

    try:
        app = app_class.bind_typegraph(tg=tg).create_instance(g=g)
    except Exception as e:
        raise errors.UserPythonConstructionError(
            f"Cannot construct build entry {config.build.address}"
        ) from e

    return app


def _init_ato_app(
    *, g: "graph.GraphView", tg: "fbrk.TypeGraph", linker: "Linker"
) -> "fabll.Node":
    """Initialize a specific .ato build."""
    import faebryk.core.node as fabll
    from atopile.compiler.build import build_file

    result = build_file(
        g=g,
        tg=tg,
        import_path=config.build.entry_file_path.name,
        path=config.build.entry_file_path,
    )
    linker.link_imports(g, result.state)
    result.visitor.execute_pending()
    app_type = result.state.type_roots[config.build.entry_section]
    app_root = tg.instantiate_node(type_node=app_type, attributes={})
    return fabll.Node.bind_instance(app_root)
