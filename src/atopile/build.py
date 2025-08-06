from typing import TYPE_CHECKING

from atopile.cli.logging_ import LoggingStage
from atopile.config import BuildType, config
from faebryk.library import _F as F

if TYPE_CHECKING:
    from faebryk.core.module import Module


def init_app() -> "Module":
    with LoggingStage(name=f"init-{config.build.name}", description="Initializing app"):
        match config.build.build_type:
            case BuildType.ATO:
                return _init_ato_app()
            case BuildType.PYTHON:
                app = _init_python_app()
                app.add(F.is_app_root())
                return app
            case _:
                raise ValueError(f"Unknown build type: {config.build.build_type}")


def _init_python_app() -> "Module":
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

    try:
        app = app_class()
    except Exception as e:
        raise errors.UserPythonConstructionError(
            f"Cannot construct build entry {config.build.address}"
        ) from e

    return app


def _init_ato_app() -> "Module":
    """Initialize a specific .ato build."""

    from atopile import front_end
    from atopile.datatypes import TypeRef
    from faebryk.libs.library import L

    node = front_end.bob.build_file(
        config.build.entry_file_path,
        TypeRef.from_path_str(config.build.entry_section),
    )
    assert isinstance(node, L.Module)
    return node
