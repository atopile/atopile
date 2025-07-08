import contextlib
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Callable,
    Hashable,
    Iterable,
    Self,
    Sequence,
    Type,
    cast,
)

from caseconverter import titlecase
from rich.console import Console, ConsoleOptions, ConsoleRenderable
from rich.markdown import Markdown
from rich.text import Text
from rich.traceback import Traceback

from faebryk.libs.logging import ReprHighlighter
from faebryk.libs.util import groupby, md_list

if TYPE_CHECKING:
    from faebryk.core.node import Node


logger = logging.getLogger(__name__)


class UserException(Exception):
    """A user-caused exception."""

    # TODO: Add / refine interface for getting user-facing exception information
    # - Origin?
    # - Title?
    # - Description?
    # - Suggestions?
    # - Help text?
    # __print__?

    def __init__(
        self,
        message: str = "",
        *args,
        title: str | None = None,
        markdown: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(message, *args, **kwargs)
        self.message = message
        self._title = title
        self.markdown = markdown

    @property
    def title(self):
        """Return the name of this error, without the "User" prefix."""
        if self._title is not None:
            return self._title

        error_name = self.__class__.__name__
        return titlecase(error_name.removeprefix("User"))

    def get_frozen(self) -> tuple:
        """Return a frozen version of this error."""
        return (self.__class__, self.message, self._title)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> list[ConsoleRenderable]:
        def _markdown(message: str) -> ConsoleRenderable:
            if console.is_terminal:
                return Markdown(message)
            else:
                return Text(message)

        renderables: list[ConsoleRenderable] = []
        if self.title:
            renderables += [Text(self.title, style="bold")]

        renderables += [
            _markdown(self.message)
            if self.markdown
            else ReprHighlighter()(self.message)
        ]

        return renderables


class DeprecatedException(UserException):
    """This feature is deprecated and will be removed in a future version."""


class UserResourceException(UserException):
    """Indicates an issue with a user-facing resource, e.g. layout files."""


class UserDesignCheckException(UserException):
    """Indicates a failing design check"""

    @classmethod
    def from_nodes(cls, message: str, nodes: Sequence["Node"]) -> Self:
        nodes = sorted(nodes, key=lambda n: str(n))
        msg = message
        if nodes:
            nodes_fmt = md_list(f"`{node}`" for node in nodes)
            msg += f"{msg}\n\nFor nodes: \n{nodes_fmt}"
        return cls(msg)


class Pacman[T: Exception](contextlib.suppress, ABC):
    """
    A yellow spherical object that noms up exceptions.

    Similar to `contextlib.suppress`, but does something with the exception.
    """

    _exceptions: tuple[Type[T], ...]

    def __init__(
        self,
        *exceptions: Type[T],
        default=None,
    ):
        self._exceptions = exceptions
        self.default = default

    @abstractmethod
    def nom_nom_nom(
        self,
        exc: T,
        original_exinfo: tuple[Type[T], T, Traceback],
    ) -> bool | None:
        """
        Do something with the exception.
        Return True if the exception should be raised.
        """
        # return boolean flipped to make default behavior to suppress

    # The following methods are copied and modified from contextlib.suppress
    # type errors are reproduced faithfully

    def _will_be__exit__(self, exctype, excinst, exctb):  # type: ignore  # Faithfully reproduce type error
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
            return not self.nom_nom_nom(excinst, (exctype, excinst, exctb))  # type: ignore
        if issubclass(exctype, BaseExceptionGroup):
            excinst = cast(BaseExceptionGroup, excinst)
            match, rest = excinst.split(self._exceptions)  # type: ignore
            if self.nom_nom_nom(match, (exctype, match, exctb)):  # type: ignore
                return False
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


# HACK: this is attached outside the class definition because
# linters/type-checkers are typically smart enough to know about,
# contextlib.supress, but key off it's __exit__ method
# By attaching it here, we don't have static analysis complaining
# that code is unreachable when using Pacman and it's subclasses
# to downgrade exceptions
Pacman.__exit__ = Pacman._will_be__exit__  # type: ignore


def iter_leaf_exceptions[T: Exception](ex: T | BaseExceptionGroup[T]) -> Iterable[T]:
    """Iter through all the non-group exceptions as a dfs pre-order"""
    if isinstance(ex, ExceptionGroup):
        for e in ex.exceptions:
            yield from iter_leaf_exceptions(e)
    else:
        yield cast(T, ex)


class accumulate:
    """
    Collect a group of errors and only raise
    an exception group at the end of execution.
    """

    def __init__(
        self,
        *accumulate_types: Type,
        group_message: str | None = None,
    ) -> None:
        self.errors: list[Exception] = []

        # Set default values for the arguments
        # NOTE: we don't do this in the function signature because
        # we want the defaults to be the same here as in the iter_through_errors
        # function below
        class _Collector(Pacman):
            def nom_nom_nom(s, exc: Exception, original_exinfo) -> None:
                self.errors.extend(iter_leaf_exceptions(exc))

        self.collector = _Collector(*(accumulate_types or (UserException,)))
        self.group_message = group_message or ""

    def collect(self) -> contextlib.suppress:
        return self.collector

    def get_exception(self) -> Exception | None:
        if self.errors:

            def _key(error: Exception) -> Hashable:
                if isinstance(error, UserException):
                    return error.get_frozen()

                # fallback to id()
                return error

            # Display unique errors in order
            grouped_errors = groupby(self.errors, key=_key)
            errors = [group[0] for group in grouped_errors.values()]

            if len(errors) > 1:
                return ExceptionGroup(self.group_message, errors)
            else:
                return errors[0]

    def raise_errors(self):
        """
        Raise the collected errors as an exception group.
        """
        if ex := self.get_exception():
            raise ex

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args):
        self.raise_errors()


_collectors: list["DowngradedExceptionCollector"] = []


class DowngradedExceptionCollector[T: Exception]:
    def __init__(self, exc_type: Type[T]):
        self.exceptions: list[tuple[T, int]] = []
        self.exc_type = exc_type

    def add(self, exception: Exception, severity: int = logging.WARNING):
        if isinstance(exception, self.exc_type):
            self.exceptions.append((exception, severity))

    def __enter__(self) -> Self:
        _collectors.append(self)
        return self

    def __exit__(self, *args):
        _collectors.remove(self)

    def __iter__(self) -> Iterator[tuple[T, int]]:
        return iter(self.exceptions)


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
        raise_anyway: bool = False,
        logger: logging.Logger = logger,
    ):
        super().__init__(*exceptions, default=default)

        if to_level >= logging.ERROR:
            raise ValueError("to_level must be less than ERROR")

        self.to_level = to_level
        self.logger = logger
        self.raise_anyway = raise_anyway

    def nom_nom_nom(self, exc: T, original_exinfo):
        if isinstance(exc, ExceptionGroup):
            exceptions = exc.exceptions
        else:
            exceptions = [exc]

        for e in exceptions:
            for collector in _collectors:
                collector.add(e, self.to_level)

            self.logger.log(self.to_level, str(e), exc_info=e, extra={"markdown": True})

        return self.raise_anyway


class suppress_after_count[T: Exception](Pacman):
    def __init__(
        self,
        limit: int,
        *exceptions: Type[T],
        default: bool = False,
        suppression_warning: str | None = None,
        logger: logging.Logger = logger,
    ):
        super().__init__(*exceptions, default=default)
        self.limit = limit
        self.counter = 0
        self.supression_warning = suppression_warning
        self.logger = logger

    def nom_nom_nom(self, exc: T, original_exinfo):
        self.counter += 1

        if self.counter == self.limit + 1 and self.supression_warning is not None:
            self.logger.warning(self.supression_warning)

        if self.counter <= self.limit:
            return True


def iter_through_errors[T](
    gen: Iterable[T],
    *accumulate_types: Type,
    group_message: str | None = None,
) -> Iterable[tuple[Callable[[], contextlib.suppress], T]]:
    """
    Wraps an iterable and yields:
    - a context manager that collects any ato errors
        raised while processing the iterable
    - the item from the iterable
    """

    with accumulate(*accumulate_types, group_message=group_message) as accumulator:
        for item in gen:
            # NOTE: we don't create a single context manager for the whole generator
            # because generator context managers are a bit special
            yield accumulator.collect, item


@contextlib.contextmanager
def log_user_errors(logger: logging.Logger = logger):
    """
    Log any exceptions raised within the context.
    """
    try:
        yield
    except UserException as e:
        logger.exception(e)
        raise
