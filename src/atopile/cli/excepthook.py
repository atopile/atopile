import sys

from atopile.logging import FLOG_FMT


def _handle_exception(exc_type, exc_value, exc_traceback):
    # avoid exceptions raised during import
    from atopile.errors import _BaseBaseUserException
    from atopile.logging import get_exception_display_message, logger

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
        # Use unified message extraction for consistency
        logger.exception(
            msg=get_exception_display_message(exc_value),
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    elif issubclass(exc_type, BaseExceptionGroup):
        for e in exc_value.exceptions:
            _handle_exception(type(e), e, e.__traceback__)
    else:
        logger.exception(
            "Uncaught compiler exception", exc_info=(exc_type, exc_value, exc_traceback)
        )


DISCORD_BANNER_TEXT = (
    "Unfortunately errors ^^^ stopped the build. "
    "If you need a hand jump on Discord! "
    "https://discord.gg/CRe5xaDBr3 👋"
)


def log_discord_banner() -> None:
    from atopile.logging import logger

    logger.info(DISCORD_BANNER_TEXT)


def handle_exception(exc_type, exc_value, exc_traceback):
    from atopile import telemetry

    try:
        _handle_exception(exc_type, exc_value, exc_traceback)
    except Exception as e:
        sys.__excepthook__(type(e), e, e.__traceback__)
    finally:
        telemetry.capture_exception(exc_value)
        log_discord_banner()
        sys.exit(1)


def install_worker_excepthook() -> None:
    def handle_worker_exception(exc_type, exc_value, exc_traceback):
        try:
            _handle_exception(exc_type, exc_value, exc_traceback)
        except Exception as e:
            sys.__excepthook__(type(e), e, e.__traceback__)
        finally:
            sys.exit(1)

    sys.excepthook = handle_worker_exception


if not FLOG_FMT:
    sys.excepthook = handle_exception
