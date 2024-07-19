import collections.abc
import logging
import sys
import textwrap
import traceback
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Callable, ContextManager, Iterable, Optional, Type, TypeVar
from types import ModuleType

import rich
from antlr4 import ParserRuleContext, Token

from atopile import address
from atopile.parse_utils import get_src_info_from_ctx, get_src_info_from_token
from atopile import telemetry

log = logging.getLogger(__name__)


class _BaseAtoError(Exception):
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
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.message = args[0] if args else ""
        self._title = title
        self.addr = addr
        self.src_path = src_path
        self.src_line = src_line
        self.src_col = src_col

    @classmethod
    def from_token(cls, token: Token, message: str, *args, **kwargs) -> "_BaseAtoError":
        """Create an error from a token."""
        src_path, src_line, src_col = get_src_info_from_token(token)
        return cls(message, src_path=src_path, src_line=src_line, src_col=src_col, *args, **kwargs)

    @classmethod
    def from_ctx(cls, ctx: Optional[ParserRuleContext], message: str, *args, **kwargs) -> "_BaseAtoError":
        """Create an error from a context."""
        self = cls(message, *args, **kwargs)
        self.set_src_from_ctx(ctx)
        return self

    def set_src_from_ctx(self, ctx: ParserRuleContext):
        """Add source info from a context."""
        src_path, src_line, src_col, *_ = get_src_info_from_ctx(ctx)
        self.src_path = src_path
        self.src_line = src_line
        self.src_col = src_col

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
            format_error(
                self,
                logger.isEnabledFor(logging.DEBUG)
            ),
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
        )


class AtoFatalError(_BaseAtoError):
    """
    Something in the user's code meant we weren't able to continue.
    Don't display a traceback on these because we'll have already printed one.
    """


class AtoError(_BaseAtoError):
    """
    This exception is thrown when there's an error in ato code
    """


class AtoSyntaxError(AtoError):
    """
    Raised when there's an error in the syntax of the language
    """


class AtoKeyError(AtoError, KeyError):
    """
    Raised if a name isn't found in the current scope.
    """


class AtoTypeError(AtoError):
    """
    Raised if something is the wrong type.
    """


class AtoValueError(AtoError):
    """
    Raised if something is the wrong type.
    """


class AtoImportNotFoundError(AtoError):
    """
    Raised if something has a conflicting name in the same scope.
    """


class AtoAmbiguousReferenceError(AtoError):
    """
    Raised if something has a conflicting name in the same scope.
    """


class AtoFileNotFoundError(AtoError, FileNotFoundError):
    """
    Raised if a file couldn't be found.
    """


class AtoUnknownUnitError(AtoError):
    """
    Raised if a unit couldn't be interpreted.
    """


class AtoInfraError(AtoError):
    """
    Raised when there's an issue contacting atopile
    infrastructure needed for an operation.
    """
    title = "Infrastructure Error"


class AtoNotImplementedError(AtoError):
    """
    Raised when a feature is not yet implemented.
    """


class CountingError(AtoError):
    count = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.__class__.count is not None:
            self.__class__.count -= 1

    def log(self, *args, **kwargs):
        if self.__class__.count > 0:
            super().log(*args, **kwargs)
        if self.__class__.count == 0:
            log.warning("... forgoing more \"%s\" errors of ", self.title or self.__class__.__name__)


class ImplicitDeclarationFutureDeprecationWarning(CountingError):
    """
    Raised when a feature is deprecated and will be removed in the future.
    """
    title = "Implicit Declaration Future Deprecation Warning"
    count = 5


def get_locals_from_exception_in_class(ex: Exception, class_: Type) -> dict:
    """Return the locals from the first frame in the traceback that's in the given class."""
    for tb, _ in list(traceback.walk_tb(ex.__traceback__))[::-1]:
        if isinstance(tb.f_locals.get("self"), class_):
            return tb.f_locals
    return {}


def format_error(ex: AtoError, debug: bool = False) -> str:
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
def _log_ato_errors(
    ex: AtoError | ExceptionGroup,
    logger: logging.Logger,
    de_dup: bool = True,
):
    """Helper function to consistently write errors to the log"""
    if isinstance(ex, ExceptionGroup):
        if ex.message:
            logger.error(ex.message)

        nice_errors, naughty_errors = ex.split((AtoError, ExceptionGroup))
        for e in nice_errors.exceptions:
            _log_ato_errors(e, logger)

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


def in_debug_session() -> Optional[ModuleType]:
    """
    Return the debugpy module if we're in a debugging session.
    """
    if "debugpy" in sys.modules:
        import debugpy
        if debugpy.is_client_connected():
            return debugpy

    return None


@contextmanager
def handle_ato_errors(logger: logging.Logger = log) -> None:
    """
    This helper function catches ato exceptions and logs them.
    """
    try:
        yield

    except* AtoError as ex:
        # If we're in a debug session, we want to see the
        # unadulterated exception. We do this pre-logging because
        # we don't want the logging to potentially obstruct the debugger.
        if debugpy := in_debug_session():
            debugpy.breakpoint()

        raise AtoFatalError from ex


def muffle_fatalities(func):
    """
    Decorator to quietly exit if a fatal error is raised.
    This is useful for the CLI, where we don't want to show a traceback.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        do_exit = False
        try:
            with handle_ato_errors():
                return func(*args, **kwargs)

        except* AtoFatalError:
            telemetry.telemetry_data.ato_error = 1
            rich.print(
                "\n\nUnfortunately errors ^^^ stopped the build. "
                "If you need a hand jump on [#9656ce]Discord! https://discord.gg/mjtxARsr9V[/] :wave:"
            )
            do_exit = True

        except* Exception as ex:
            telemetry.telemetry_data.crash += len(ex.exceptions)
            raise ex

        finally:
            telemetry.log_telemetry()

        # Raisinng sys.exit here so all exceptions can be raised
        if do_exit:
            sys.exit(1)

    return wrapper


class ExceptionAccumulator:
    """
    Collect a group of errors and only raise
    an exception group at the end of execution.
    """

    def __init__(
        self,
        accumulate_types: Optional[Type[Exception]] = None,
        group_message: Optional[str] = None,
    ) -> None:
        self.errors: list[Exception] = []

        # Set default values for the arguments
        # NOTE: we don't do this in the function signature because
        # we want the defaults to be the same here as in the iter_through_errors
        # function below
        self.accumulate_types = accumulate_types or AtoError
        self.group_message = group_message or ""

    def make_collector(self):
        """
        Return a context manager that collects any ato errors raised while executing it.
        """
        @contextmanager
        def _collect_ato_errors(ctx: Optional[ParserRuleContext] = None):
            try:
                yield
            except* self.accumulate_types as ex:
                if debugpy := in_debug_session():
                    debugpy.breakpoint()
                for e in ex.exceptions:
                    if ctx and hasattr(e, "set_src_from_ctx"):
                        e.set_src_from_ctx(ctx)
                self.errors.extend(ex.exceptions)
                _log_ato_errors(ex, log)

        return _collect_ato_errors

    def raise_errors(self):
        """
        Raise the collected errors as an exception group.
        """
        if self.errors:
            # Display unique errors in order
            # FIXME: this is both hard to understand and wildly inefficient
            displayed_errors = []
            for error in self.errors:
                if not any(
                    existing_error.__dict__ == error.__dict__
                    for existing_error in displayed_errors
                ):
                    displayed_errors.append(error)

            raise ExceptionGroup(self.group_message, displayed_errors)

    def __enter__(self) -> Callable[[], ContextManager]:
        return self.make_collector()

    def __exit__(self, *args):
        self.raise_errors()


T = TypeVar("T")


def iter_through_errors(
    gen: Iterable[T],
    accumulate_types: Optional[Type | tuple[Type]] = None,
    group_message: Optional[str] = None,
) -> Iterable[tuple[Callable[[], ContextManager], T]]:
    """
    Wraps an iterable and yields:
    - a context manager that collects any ato errors raised while processing the iterable
    - the item from the iterable
    """

    with ExceptionAccumulator(accumulate_types, group_message) as err_cltr:
        for item in gen:
            # NOTE: we don't create a single context manager for the whole generator
            # because generator context managers are a bit special
            yield err_cltr, item


C = TypeVar("C", bound=Callable)


def downgrade(
    func: C,
    exs: Type | tuple[Type],
    default = None,
    to_level: int = logging.WARNING,
    logger: logging.Logger = log,
) -> C:
    """
    Return a wrapped version of your function that catches the given exceptions
    and logs their contents as warning, instead returning a default value
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exs as ex:
            try:
                ex.log(logger, to_level)
            except AttributeError:
                logger.log(to_level, ex)
            if isinstance(default, collections.abc.Callable):
                return default(*args, *kwargs)
            return default

    return wrapper


def log_ato_errors(func):
    """
    Decorator to log ato errors.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except* AtoError as ex:
            _log_ato_errors(ex, log)
            raise

    return wrapper
