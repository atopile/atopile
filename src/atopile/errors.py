import contextlib
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Type

import rich
from antlr4 import ParserRuleContext
from rich.traceback import Traceback

from atopile import telemetry
from atopile.parse_utils import get_src_info_from_ctx
from faebryk.libs.exceptions import UserException as _BaseBaseUserException
from faebryk.libs.exceptions import in_debug_session

logger = logging.getLogger(__name__)


class _BaseUserException(_BaseBaseUserException):
    """
    This exception is thrown when there's an error in the syntax of the language
    """

    def __init__(
        self,
        *args,
        addr: str | None = None,
        src_path: str | Path | None = None,
        src_line: int | None = None,
        src_col: int | None = None,
        src_stop_line: int | None = None,
        src_stop_col: int | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.addr = addr
        self.src_path = src_path
        self.src_line = src_line
        self.src_col = src_col
        self.src_stop_line = src_stop_line
        self.src_stop_col = src_stop_col

    @classmethod
    def from_ctx(
        cls, ctx: Optional[ParserRuleContext], message: str, *args, **kwargs
    ) -> "_BaseUserException":
        """Create an error from a context."""
        self = cls(message, *args, **kwargs)
        self.set_src_from_ctx(ctx)
        return self

    def set_src_from_ctx(self, ctx: ParserRuleContext):
        """Add source info from a context."""
        (
            self.src_path,
            self.src_line,
            self.src_col,
            self.src_stop_line,
            self.src_stop_col,
        ) = get_src_info_from_ctx(ctx)

    def get_frozen(self) -> tuple:
        return super().get_frozen() + (
            self.addr,
            self.src_path,
            self.src_line,
            self.src_col,
            self.src_stop_line,
            self.src_stop_col,
        )


class UserFatalException(_BaseUserException):
    """
    Something in the user's code meant we weren't able to continue.
    Don't display a traceback on these because we'll have already printed one.
    """


class UserException(_BaseUserException):
    """
    This exception is thrown when there's an error in ato code
    """


class UserSyntaxError(UserException):
    """
    Raised when there's an error in the syntax of the language
    """


class UserKeyError(UserException, KeyError):
    """
    Raised if a name isn't found in the current scope.
    """


class UserTypeError(UserException):
    """
    Raised if something is the wrong type.
    """


class UserValueError(UserException):
    """
    Raised if something is the correct type but an invalid value.
    """


class UserImportNotFoundError(UserException):
    """
    Raised if something has a conflicting name in the same scope.
    """


class UserAmbiguousReferenceError(UserException):
    """
    Raised if something has a conflicting name in the same scope.
    """


class UserFileNotFoundError(UserException, FileNotFoundError):
    """
    Raised if a file couldn't be found.
    """


class UserUnknownUnitError(UserException):
    """
    Raised if a unit couldn't be interpreted.
    """


class UserIncompatibleUnitError(UserException):
    """
    Raised if a unit couldn't be interpreted.
    """


class UserInfraError(UserException):
    """
    Raised when there's an issue contacting atopile
    infrastructure needed for an operation.
    """

    title = "Infrastructure Error"


class UserNotImplementedError(UserException):
    """
    Raised when a feature is not yet implemented.
    """


class UserBadParameterError(UserException):
    """
    Raised when a bad CLI param is given
    """

    title = "Bad Parameter"


class UserPythonLoadError(UserException):
    """
    Raised when a Python module couldn't be loaded.
    """


class UserPythonModuleError(UserException):
    """
    Raised when a user-provided Python module is faulty.
    """


class UserPythonConstructionError(UserPythonModuleError):
    """
    Raised when a Python module couldn't be constructed.
    """


_logged_exceptions: set[tuple[Type[Exception], tuple]] = set()


def _log_user_errors(ex: UserException | ExceptionGroup, de_dup: bool = True):
    """Helper function to consistently write errors to the log"""
    if isinstance(ex, ExceptionGroup):
        if ex.message:
            logger.error(ex.message)

        nice_errors, naughty_errors = ex.split((UserException, ExceptionGroup))

        if nice_errors:
            for e in nice_errors.exceptions:
                assert isinstance(e, UserException)
                _log_user_errors(e)

        if naughty_errors:
            raise naughty_errors

        return

    # Check if this error has already been logged
    hashable = ex.get_frozen()
    if de_dup and hashable in _logged_exceptions:
        return

    # Format and printout the error
    _logged_exceptions.add(hashable)
    logger.error(ex)


@contextmanager
def handle_user_errors(log_: logging.Logger = logger):
    """
    This helper function catches user exceptions and logs them.
    """
    try:
        yield

    except* _BaseBaseUserException as ex:
        # If we're in a debug session, we want to see the
        # unadulterated exception. We do this pre-logging because
        # we don't want the logging to potentially obstruct the debugger.
        if debugpy := in_debug_session():
            debugpy.breakpoint()

        # This is here to print out any straggling ato errors that weren't
        # printed via a lower-level accumulator of the likes
        _log_user_errors(ex)

        raise UserFatalException from ex


@contextmanager
def muffle_fatalities():
    """
    Decorator to quietly exit if a fatal error is raised.
    This is useful for the CLI, where we don't want to show a traceback.
    """

    do_exit = False
    try:
        with handle_user_errors():
            yield

    except* UserFatalException:
        if telemetry.telemetry_data is not None:
            telemetry.telemetry_data.ato_error = 1
        rich.print(
            "\n\nUnfortunately errors ^^^ stopped the build. "
            "If you need a hand jump on [#9656ce]Discord! https://discord.gg/mjtxARsr9V[/] :wave:"
        )
        do_exit = True

    except* Exception as ex:
        if isinstance(ex, BaseExceptionGroup):
            # Rich handles ExceptionGroups poorly, so we do it ourselves here
            for e in ex.exceptions:
                logger.error(f"Uncaught compiler exception: {e}")
                tb = Traceback.from_exception(
                    type(e), e, e.__traceback__, show_locals=True
                )
                rich.print(tb)

            with contextlib.suppress(Exception):
                telemetry.telemetry_data.crash += len(ex.exceptions)
        else:
            with contextlib.suppress(Exception):
                telemetry.telemetry_data.crash += 1

        raise

    finally:
        telemetry.log_telemetry()

    # Raisinng sys.exit here so all exceptions can be raised
    if do_exit:
        sys.exit(1)


@contextmanager
def log_ato_errors():
    """
    Decorator / context to log ato errors.
    """
    try:
        yield
    except* _BaseBaseUserException as ex:
        _log_user_errors(ex)
        raise
