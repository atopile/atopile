import sys

from faebryk.libs.logging import FLOG_FMT, rich_print_robust


def _handle_exception(exc_type, exc_value, exc_traceback):
    # avoid exceptions raised during import
    from atopile.cli.logging_ import logger
    from atopile.errors import _BaseBaseUserException

    # delayed import to improve startup time
    from faebryk.libs.util import in_debug_session

    if issubclass(exc_type, _BaseBaseUserException):
        # If we're in a debug session, we want to see the
        # unadulterated exception. We do this pre-logging because
        # we don't want the logging to potentially obstruct the debugger.
        if in_debug_session():
            import debugpy

            debugpy.breakpoint()

        # in case we missed logging closer to the source
        logger.exception(
            msg=exc_value.message, exc_info=(exc_type, exc_value, exc_traceback)
        )

    elif issubclass(exc_type, BaseExceptionGroup):
        for e in exc_value.exceptions:
            _handle_exception(type(e), e, e.__traceback__)
    else:
        logger.exception(
            "Uncaught compiler exception", exc_info=(exc_type, exc_value, exc_traceback)
        )


def handle_exception(exc_type, exc_value, exc_traceback):
    from atopile import telemetry

    try:
        _handle_exception(exc_type, exc_value, exc_traceback)
    except Exception as e:
        sys.__excepthook__(type(e), e, e.__traceback__)
    finally:
        telemetry.capture_exception(exc_value)

        rich_print_robust(
            "\n\nUnfortunately errors ^^^ stopped the build. "
            "If you need a hand jump on [#9656ce]Discord[/]! "
            "[link=https://discord.gg/CRe5xaDBr3]https://discord.gg/CRe5xaDBr3[/] "
            ":wave:"
        )
        sys.exit(1)


if not FLOG_FMT:
    sys.excepthook = handle_exception
