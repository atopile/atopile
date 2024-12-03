import contextlib
import sys
from types import ModuleType

import rich

from atopile import telemetry
from atopile.cli.logging import logger
from atopile.errors import _BaseBaseUserException


def in_debug_session() -> ModuleType | None:
    """
    Return the debugpy module if we're in a debugging session.
    """
    if "debugpy" in sys.modules:
        import os

        os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
        import debugpy

        if debugpy.is_client_connected():
            return debugpy

    return None


def _handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, _BaseBaseUserException):
        # If we're in a debug session, we want to see the
        # unadulterated exception. We do this pre-logging because
        # we don't want the logging to potentially obstruct the debugger.
        if debugpy := in_debug_session():
            debugpy.breakpoint()

        # in case we missed logging closer to the source
        logger.exception(
            msg=exc_value.message, exc_info=(exc_type, exc_value, exc_traceback)
        )

        if telemetry.telemetry_data is not None:
            with contextlib.suppress(Exception):
                telemetry.telemetry_data.ato_error += 1
    elif issubclass(exc_type, BaseExceptionGroup):
        for e in exc_value.exceptions:
            _handle_exception(type(e), e, e.__traceback__)
    else:
        with contextlib.suppress(Exception):
            telemetry.telemetry_data.crash += 1
        logger.exception("Uncaught compiler exception", exc_info=exc_value)


def handle_exception(exc_type, exc_value, exc_traceback):
    try:
        _handle_exception(exc_type, exc_value, exc_traceback)
    except Exception as e:
        sys.__excepthook__(type(e), e, e.__traceback__)
    finally:
        with contextlib.suppress(Exception):
            telemetry.log_telemetry()

        rich.print(
            "\n\nUnfortunately errors ^^^ stopped the build. "
            "If you need a hand jump on [#9656ce]Discord! https://discord.gg/mjtxARsr9V[/] :wave:"
        )
        sys.exit(1)


sys.excepthook = handle_exception
