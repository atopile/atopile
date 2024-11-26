import contextlib
import logging
import sys
import textwrap
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Type

import rich
from antlr4 import ParserRuleContext, Token
from rich.traceback import Traceback

from atopile import address, telemetry
from atopile.parse_utils import get_src_info_from_ctx, get_src_info_from_token
from faebryk.libs.exception import in_debug_session, UserException

log = logging.getLogger(__name__)


class _BaseUserException(Exception):
    """
    This exception is thrown when there's an error in the syntax of the language
    """

    def __init__(
        self,
        *args,
        title: Optional[str] = None,
        addr: Optional[str] = None,
        src_path: Optional[str | Path] = None,
        src_line: Optional[int] = None,
        src_col: Optional[int] = None,
        src_stop_line: Optional[int] = None,
        src_stop_col: Optional[int] = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.message = args[0] if args else ""
        self._title = title
        self.addr = addr
        self.src_path = src_path
        self.src_line = src_line
        self.src_col = src_col
        self.src_stop_line = src_stop_line
        self.src_stop_col = src_stop_col

    @classmethod
    def from_token(
        cls, token: Token, message: str, *args, **kwargs
    ) -> "_BaseUserException":
        """Create an error from a token."""
        src_path, src_line, src_col = get_src_info_from_token(token)
        return cls(
            message,
            src_path=src_path,
            src_line=src_line,
            src_col=src_col,
            *args,
            **kwargs,
        )

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

    @property
    def title(self):
        """Return the name of this error, without the "Ato" prefix."""
        if self._title is not None:
            return self._title

        error_name = self.__class__.__name__
        if error_name.startswith("Ato"):
            return error_name[3:]
        return error_name

    def log(self, logger: logging.Logger = log, to_level: int = logging.ERROR):
        """
        Log the error to the given logger.
        """
        logger.log(
            to_level,
            format_error(self, logger.isEnabledFor(logging.DEBUG)),
            extra={"markup": True},
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Error info:\n", exc_info=self)

    def get_frozen(self) -> tuple:
        """
        Return a frozen version of this error.
        """
        return (
            self.__class__,
            self.message,
            self._title,
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
    Raised if something is the wrong type.
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


class CountingError(UserException):
    count = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.__class__.count is not None:
            self.__class__.count -= 1

    def log(self, *args, **kwargs):
        if self.__class__.count > 0:
            super().log(*args, **kwargs)
        if self.__class__.count == 0:
            log.warning(
                '... forgoing more "%s" errors of ',
                self.title or self.__class__.__name__,
            )


class ImplicitDeclarationFutureDeprecationWarning(CountingError):
    """
    Raised when a feature is deprecated and will be removed in the future.
    """

    title = "Implicit Declaration Future Deprecation Warning"
    count = 5


def format_error(ex: UserException, debug: bool = False) -> str:
    """
    Format an error into a string.
    """
    # Ensure we have values for all the components on the error string
    message = f"[bold]{ex.title}[/]\n"

    # Attach source info if we have it
    if ex.src_path:
        source_info = str(ex.src_path)
        if ex.src_line:
            source_info += f":{ex.src_line}"
            if ex.src_col:
                source_info += f":{ex.src_col}"
        message += f"{source_info}\n"

    # Replace the address in the string, if we have it attached
    fmt_message = textwrap.indent(str(ex.message), "    ")
    if ex.addr:
        if debug:
            addr = ex.addr
        else:
            addr = address.from_parts(
                Path(address.get_file(ex.addr)).name,
                address.get_entry_section(ex.addr),
                address.get_instance_section(ex.addr),
            )
        # FIXME: we ignore the escaping of the address here
        fmt_addr = f"[bold cyan]{addr}[/]"

        if "$addr" in fmt_message:
            fmt_message = fmt_message.replace("$addr", fmt_addr)
        else:
            if not ex.src_path:
                message += f"Address: {fmt_addr}\n"

    # Add the message from the exception
    message += fmt_message

    return message.strip()


_logged_exceptions: set[tuple[Type[Exception], tuple]] = set()


def _log_user_errors(
    ex: UserException | ExceptionGroup,
    logger: logging.Logger,
    de_dup: bool = True,
):
    """Helper function to consistently write errors to the log"""
    if isinstance(ex, ExceptionGroup):
        if ex.message:
            logger.error(ex.message)

        nice_errors, naughty_errors = ex.split((UserException, ExceptionGroup))
        for e in nice_errors.exceptions:
            _log_user_errors(e, logger)

        if naughty_errors:
            raise naughty_errors

        return

    # Check if this error has already been logged
    hashable = ex.get_frozen()
    if de_dup and hashable in _logged_exceptions:
        return

    # Format and printout the error
    _logged_exceptions.add(hashable)
    ex.log(logger)


@contextmanager
def handle_user_errors(log_: logging.Logger = log):
    """
    This helper function catches user exceptions and logs them.
    """
    try:
        yield

    except* UserException as ex:
        # If we're in a debug session, we want to see the
        # unadulterated exception. We do this pre-logging because
        # we don't want the logging to potentially obstruct the debugger.
        if debugpy := in_debug_session():
            debugpy.breakpoint()

        # This is here to print out any straggling ato errors that weren't
        # printed via a lower-level accumulator of the likes
        _log_user_errors(ex, log_)

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

    except UserFatalException:
        if telemetry.telemetry_data is not None:
            telemetry.telemetry_data.ato_error = 1
        rich.print(
            "\n\nUnfortunately errors ^^^ stopped the build. "
            "If you need a hand jump on [#9656ce]Discord! https://discord.gg/mjtxARsr9V[/] :wave:"
        )
        do_exit = True

    except Exception as ex:
        if isinstance(ex, BaseExceptionGroup):
            # Rich handles ExceptionGroups poorly, so we do it ourselves here
            for e in ex.exceptions:
                log.error(f"Uncaught compiler exception: {e}")
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
    except* UserException as ex:
        _log_user_errors(ex, log)
        raise
