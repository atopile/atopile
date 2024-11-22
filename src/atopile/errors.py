import contextlib
import logging
import sys
import textwrap
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from types import ModuleType
from typing import Callable, ContextManager, Iterable, Optional, Self, Type, cast

import rich
from antlr4 import ParserRuleContext, Token
from rich.traceback import Traceback

from atopile import address, telemetry
from atopile.parse_utils import get_src_info_from_ctx, get_src_info_from_token

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
    def from_token(cls, token: Token, message: str, *args, **kwargs) -> "_BaseAtoError":
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
    ) -> "_BaseAtoError":
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


class AtoIncompatibleUnitError(AtoError):
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


class AtoBadParameterError(AtoError):
    """
    Raised when a bad CLI param is given
    """

    title = "Bad Parameter"


class AtoPythonLoadError(AtoError):
    """
    Raised when a Python module couldn't be loaded.
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
def handle_ato_errors(log_: logging.Logger = log):
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

        # This is here to print out any straggling ato errors that weren't
        # printed via a lower-level accumulator of the likes
        _log_ato_errors(ex, log_)

        raise AtoFatalError from ex


@contextmanager
def muffle_fatalities():
    """
    Decorator to quietly exit if a fatal error is raised.
    This is useful for the CLI, where we don't want to show a traceback.
    """

    do_exit = False
    try:
        with handle_ato_errors():
            yield

    except AtoFatalError:
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


class Pacman(contextlib.suppress):
    """
    A yellow spherical object that noms up exceptions.

    Similar to `contextlib.suppress`, but does something with the exception.
    """

    def __init__(
        self,
        *exceptions: Type | tuple[Type],
        default=None,
    ):
        self._exceptions = exceptions
        self.default = default

    def nom_nom_nom(
        self,
        exc: BaseException,
        original_exinfo: tuple[Type[BaseException], BaseException, Traceback],
    ):
        """Do something with the exception."""
        raise NotImplementedError

    # The following methods are copied and modified from contextlib.suppress
    # type errors are reproduced faithfully

    def __exit__(self, exctype, excinst, exctb):  # type: ignore
        # Unlike isinstance and issubclass, CPython exception handling
        # currently only looks at the concrete type hierarchy (ignoring
        # the instance and subclass checking hooks). While Guido considers
        # that a bug rather than a feature, it's a fairly hard one to fix
        # due to various internal implementation details. suppress provides
        # the simpler issubclass based semantics, rather than trying to
        # exactly reproduce the limitations of the CPython interpreter.
        #
        # See http://bugs.python.org/issue12029 for more details
        if exctype is None:
            return
        if issubclass(exctype, self._exceptions):
            self.nom_nom_nom(excinst, (exctype, excinst, exctb))  # type: ignore
            return True
        if issubclass(exctype, BaseExceptionGroup):
            excinst = cast(BaseExceptionGroup, excinst)
            match, rest = excinst.split(self._exceptions)  # type: ignore
            self.nom_nom_nom(match, (exctype, match, exctb))  # type: ignore
            if rest is None:
                return True
            raise rest
        return False

    # The following methods are copied and modified from contextlib.ContextDecorator

    def _recreate_cm(self):
        """Return a recreated instance of self.

        Allows an otherwise one-shot context manager like
        _GeneratorContextManager to support use as
        a decorator via implicit recreation.

        This is a private interface just for _GeneratorContextManager.
        See issue #11647 for details.
        """
        return self

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwds):
            with self._recreate_cm():
                return func(*args, **kwds)
            return self.default

        return inner


class ExceptionAccumulator:
    """
    Collect a group of errors and only raise
    an exception group at the end of execution.
    """

    def __init__(
        self,
        *accumulate_types: Type,
        group_message: Optional[str] = None,
    ) -> None:
        self.errors: list[Exception] = []

        # Set default values for the arguments
        # NOTE: we don't do this in the function signature because
        # we want the defaults to be the same here as in the iter_through_errors
        # function below
        self.accumulate_types = accumulate_types or (AtoError,)
        self.group_message = group_message or ""

    def collect(self) -> Pacman:
        class _Collector(Pacman):
            def nom_nom_nom(s, exc: BaseException, _):
                if isinstance(exc, BaseExceptionGroup):
                    self.errors.extend(exc.exceptions)
                else:
                    self.errors.append(exc)

        return _Collector(*self.accumulate_types)

    def add_errors(self, ex: ExceptionGroup):
        self.errors.extend(ex.exceptions)
        _log_ato_errors(ex, log)

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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args):
        self.raise_errors()


def iter_through_errors[T](
    gen: Iterable[T],
    *accumulate_types: Type,
    group_message: Optional[str] = None,
) -> Iterable[tuple[Callable[[], ContextManager], T]]:
    """
    Wraps an iterable and yields:
    - a context manager that collects any ato errors raised while processing the iterable
    - the item from the iterable
    """

    with ExceptionAccumulator(
        *accumulate_types, group_message=group_message
    ) as accumulator:
        for item in gen:
            # NOTE: we don't create a single context manager for the whole generator
            # because generator context managers are a bit special
            yield accumulator.collect, item


class downgrade[T: Exception](Pacman):
    """
    Similar to `contextlib.suppress`, but logs the exception instead.
    Can be used both as a context manager and as a function decorator.
    """

    def __init__(
        self,
        *exceptions: Type[T],
        default=None,
        to_level: int = logging.WARNING,
        logger: logging.Logger = log,
    ):
        super().__init__(exceptions, default=default)
        self.to_level = to_level
        self.logger = logger

    def nom_nom_nom(self, exc: T, _):
        if isinstance(exc, BaseExceptionGroup):
            exceptions = exc.exceptions
        else:
            exceptions = [exc]

        for e in exceptions:
            try:
                e.log(self.logger, self.to_level)
            except AttributeError:
                self.logger.log(self.to_level, e)


@contextmanager
def log_ato_errors():
    """
    Decorator / context to log ato errors.
    """
    try:
        yield
    except* AtoError as ex:
        _log_ato_errors(ex, log)
        raise
