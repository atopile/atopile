import logging
import sys
import textwrap
import traceback
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Callable, ContextManager, Iterable, Iterator, Optional, Type, TypeVar

from antlr4 import ParserRuleContext, Token

from atopile.parse_utils import get_src_info_from_ctx, get_src_info_from_token

log = logging.getLogger(__name__)


T = TypeVar("T")


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
    def from_ctx(cls, ctx: ParserRuleContext, message: str, *args, **kwargs) -> "_BaseAtoError":
        """Create an error from a context."""
        src_path, src_line, src_col = get_src_info_from_ctx(ctx)
        return cls(message, src_path=src_path, src_line=src_line, src_col=src_col, *args, **kwargs)

    @property
    def title(self):
        """Return the name of this error, without the "Ato" prefix."""
        if self._title is not None:
            return self._title

        error_name = self.__class__.__name__
        if error_name.startswith("Ato"):
            return error_name[3:]
        return error_name


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


class AtoImportNotFoundError(AtoError):
    """
    Raised if something has a conflicting name in the same scope.
    """


class AtoAmbiguousReferenceError(AtoError):
    """
    Raised if something has a conflicting name in the same scope.
    """


def get_locals_from_exception_in_class(ex: Exception, class_: Type) -> dict:
    """Return the locals from the first frame in the traceback that's in the given class."""
    for tb, _ in list(traceback.walk_tb(ex.__traceback__))[::-1]:
        if isinstance(tb.f_locals.get("self"), class_):
            return tb.f_locals
    return {}


def _log_ato_errors(
    ex: AtoError | ExceptionGroup,
    logger: logging.Logger,
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

    # ensure we have values for all the components on the error string
    message = ex.title + "\n"

    if ex.src_path or ex.src_line or ex.src_col:
        message += (
            f"{ex.src_path or '<?>'}:{ex.src_line or '<?>'}:{ex.src_col or '<?>'}:\n"
        )

    message += textwrap.indent(ex.message, "--> ")

    logger.error(message.strip())
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Error info:\n", exc_info=ex)


@contextmanager
def handle_ato_errors(logger: Optional[logging.Logger] = None) -> None:
    """
    This helper function catches ato exceptions and logs them.
    """
    if logger is None:
        logger = log

    try:
        yield

    except (AtoError, ExceptionGroup) as ex:
        # FIXME: we're gonna repeat ourselves a lot if the same
        # error causes an issue multiple times (which they do)
        _log_ato_errors(ex, logger)
        raise AtoFatalError from ex


def muffle_fatalities(func):
    """
    Decorator to quietly exit if a fatal error is raised.
    This is useful for the CLI, where we don't want to show a traceback.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AtoFatalError:
            sys.exit(1)
        except ExceptionGroup as ex:
            _, not_fatal_errors = ex.split(AtoFatalError)
            if not_fatal_errors:
                raise not_fatal_errors from ex
            sys.exit(1)

    return wrapper


@contextmanager
def error_accumulator(
    accumulate_types: Optional[Type | tuple[Type]] = None,
    group_message: Optional[str] = None,
) -> Iterator[Callable[[], ContextManager]]:
    """
    Wraps a block of code and collects any ato errors raised while executing it.
    """
    errors: list[Exception] = []

    # Set default values for the arguments
    # NOTE: we don't do this in the function signature because
    # we want the defaults to be the same here as in the iter_through_errors
    # function below
    if accumulate_types is None:
        accumulate_types = AtoError

    if not group_message:
        group_message = ""

    @contextmanager
    def _collect_ato_errors():
        try:
            yield
        except accumulate_types as ex:
            errors.append(ex)
        except ExceptionGroup as ex:
            nice, naughty = ex.split(accumulate_types)
            if nice:
                errors.extend(nice.exceptions)
            if naughty:
                raise naughty from ex

    # FIXME: do we wanna slap this in a try-finally
    #  block so we also get to raise the exceptions
    #  we collected if a naughty error throws us out?
    yield _collect_ato_errors

    if errors:
        raise ExceptionGroup(group_message, errors)


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

    with error_accumulator(accumulate_types, group_message) as err_cltr:
        for item in gen:
            # NOTE: we don't create a single context manager for the whole generator
            # because generator context managers are a bit special
            yield err_cltr, item
