import contextlib
import logging
import sys
from functools import wraps
from types import ModuleType
from typing import Callable, ContextManager, Iterable, Self, Type, cast

from rich.traceback import Traceback

log = logging.getLogger(__name__)


class UserException(Exception):
    """A user-caused exception."""

    # TODO: Add interface for getting user-facing exception information
    # - Origin?
    # - Title?
    # - Description?
    # - Suggestions?
    # - Help text?
    # __print__?

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DeprecatedException(UserException):
    """This feature is deprecated and will be removed in a future version."""


class UserResourceException(UserException):
    """Indicates an issue with a user-facing resource, e.g. layout files."""


def in_debug_session() -> ModuleType | None:
    """
    Return the debugpy module if we're in a debugging session.
    """
    if "debugpy" in sys.modules:
        import debugpy

        if debugpy.is_client_connected():
            return debugpy

    return None


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
        group_message: str | None = None,
    ) -> None:
        self.errors: list[Exception] = []

        # Set default values for the arguments
        # NOTE: we don't do this in the function signature because
        # we want the defaults to be the same here as in the iter_through_errors
        # function below
        self.accumulate_types = accumulate_types or (UserException,)
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

        # TODO: log the errors with the UserException protocol instead
        from atopile.errors import _log_user_errors

        _log_user_errors(ex, log)

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

            if len(displayed_errors) > 1:
                raise ExceptionGroup(self.group_message, displayed_errors)
            else:
                raise displayed_errors[0]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args):
        self.raise_errors()


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


def iter_through_errors[T](
    gen: Iterable[T],
    *accumulate_types: Type,
    group_message: str | None = None,
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
