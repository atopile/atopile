"""
Exception handling utilities for atopile.

This module provides:
- Base UserException class for user-facing errors
- Source-located exceptions with token tracking for DSL errors
- Exception accumulation and collection utilities
- Downgrade utilities for converting exceptions to warnings
"""

from __future__ import annotations

import contextlib
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Hashable,
    Iterable,
    Self,
    Sequence,
    Type,
    cast,
)

from antlr4 import CommonTokenStream, ParserRuleContext, Token
from caseconverter import titlecase
from rich.console import Console, ConsoleOptions, ConsoleRenderable
from rich.highlighter import ReprHighlighter
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.traceback import Traceback

from faebryk.libs.util import groupby, md_list

if TYPE_CHECKING:
    import faebryk.core.node as fabll


# NOTE: Using standard logging here to avoid circular import.
# atopile.logging imports modules that eventually import atopile.errors.
logger = logging.getLogger(__name__)


# =============================================================================
# Base Exception Classes
# =============================================================================


class UserException(Exception):
    """
    Base class for user-caused exceptions.

    Provides Rich console rendering with title and message formatting.
    """

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
        """Return a frozen version of this error for deduplication."""
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


# Alias for backwards compatibility and clarity
_BaseBaseUserException = UserException


# =============================================================================
# Source-Located Exceptions (with token/file tracking)
# =============================================================================


def _render_tokens(
    token_stream: CommonTokenStream, start_token: Token, stop_token: Token
) -> list[ConsoleRenderable]:
    from atopile.compiler.parse_utils import (
        PygmentsLexerReconstructor,
        get_src_info_from_token,
    )

    lexer = PygmentsLexerReconstructor.from_tokens(
        token_stream, start_token, stop_token, 1, 1
    )
    src_path, src_line, src_col = get_src_info_from_token(start_token)

    # Use absolute path for clickability in terminals/IDEs
    src_path = Path(src_path).resolve()
    source_info = str(src_path)
    if src_line := src_line:
        source_info += f":{src_line}"
    if src_col := src_col:
        source_info += f":{src_col}"

    highlight_lines = set(range(start_token.line, stop_token.line + 1))

    return [
        Text("Source: ", style="bold") + Text(source_info, style="magenta"),
        Syntax(
            lexer.get_code(),
            lexer,
            line_numbers=True,
            start_line=lexer.start_line,
            indent_guides=True,
            highlight_lines=highlight_lines,
            background_color="default",
        ),
    ]


class SourceLocatedUserException(UserException):
    """
    Exception with source location tracking for DSL errors.

    Adds token stream and origin tracking for displaying the exact
    location in .ato files where an error occurred.
    """

    def __init__(
        self,
        msg: str,
        *args,
        token_stream: CommonTokenStream | None = None,
        origin_start: Token | None = None,
        origin_stop: Token | None = None,
        traceback: Sequence[ParserRuleContext | None] | None = None,
        markdown: bool = True,
        code: str | None = None,
        **kwargs,
    ):
        super().__init__(msg, *args, markdown=markdown, **kwargs)

        self.token_stream = token_stream
        self.origin_start = origin_start
        self.origin_stop = origin_stop
        self.traceback = traceback
        self.code = code

        if self.token_stream is None and (
            self.origin_start is not None or self.origin_stop is not None
        ):
            raise ValueError(
                "token_stream is required if origin_start or origin_stop is provided"
            )

    def attach_origin_from_ctx(self, ctx: ParserRuleContext) -> None:
        self.origin_start = ctx.start
        self.origin_stop = ctx.stop
        self.token_stream = ctx.parser.getInputStream()  # type: ignore[reportOptionalMemberAccess]

    @classmethod
    def from_ctx[T: SourceLocatedUserException](
        cls: type[T],
        origin: ParserRuleContext | None,
        message: str,
        *args,
        traceback: Sequence[ParserRuleContext | None] | None = None,
        **kwargs,
    ) -> T:
        """Create an error from a parser context."""
        instance = cls(message, *args, traceback=traceback, **kwargs)
        if origin is not None:
            instance.attach_origin_from_ctx(origin)
        return instance

    @classmethod
    def from_tokens[T: SourceLocatedUserException](
        cls: type[T],
        token_stream: CommonTokenStream,
        origin_start: Token,
        origin_stop: Token | None,
        message: str,
        *args,
        traceback: Sequence[ParserRuleContext | None] | None = None,
        **kwargs,
    ) -> T:
        """Create an error from tokens."""
        instance = cls(
            message,
            *args,
            token_stream=token_stream,
            origin_start=origin_start,
            origin_stop=origin_stop,
            traceback=traceback,
            **kwargs,
        )
        return instance

    def get_frozen(self) -> tuple:
        from atopile.compiler.parse_utils import get_src_info_from_token

        if self.origin_start and self.origin_stop:
            return (
                super().get_frozen()
                + get_src_info_from_token(self.origin_start)
                + get_src_info_from_token(self.origin_stop)
            )
        return super().get_frozen()

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
            renderables += [Text(self.title, style="bold red")]

        renderables += [
            _markdown(self.message)
            if self.markdown
            else ReprHighlighter()(Text(self.message))
        ]

        for ctx in self.traceback or []:
            if ctx is not None:
                assert self.token_stream is not None
                renderables += _render_tokens(self.token_stream, ctx.start, ctx.stop)

        if self.origin_start:
            assert self.token_stream is not None

            if self.origin_stop is None:
                origin_stop = self.origin_start
            else:
                origin_stop = self.origin_stop

            renderables += [Text("Code causing the error: ", style="bold")]
            renderables += _render_tokens(
                self.token_stream, self.origin_start, origin_stop
            )

        return renderables


# Alias for backwards compatibility
_BaseUserException = SourceLocatedUserException


# =============================================================================
# Specific Exception Types
# =============================================================================


class UserFatalException(SourceLocatedUserException):
    """
    Something in the user's code meant we weren't able to continue.
    Don't display a traceback on these because we'll have already printed one.
    """


class UserSyntaxError(SourceLocatedUserException):
    """Raised when there's an error in the syntax of the language."""


class UserKeyError(SourceLocatedUserException, KeyError):
    """Raised if a name isn't found in the current scope."""


class UserTypeError(SourceLocatedUserException):
    """Raised if something is the wrong type."""


class UserValueError(SourceLocatedUserException):
    """Raised if something is the correct type but an invalid value."""


class UserInvalidValueError(UserValueError):
    """Indicates an invalid enum value."""

    @classmethod
    def from_ctx(
        cls,
        origin: ParserRuleContext | None,
        enum_types: tuple[type[Enum], ...],
        enum_name: str | None = None,
        value: Any | None = None,
        **kwargs,
    ) -> UserInvalidValueError:
        expected_values = ", ".join(
            [
                f"`{member.name}`"
                for enum_type in enum_types
                for member in enum_type.__members__.values()
            ]
        )
        enum_names = enum_name or ", ".join(
            [enum_type.__qualname__ for enum_type in enum_types]
        )
        return super().from_ctx(
            origin=origin,
            message=(
                f"Invalid value for `{enum_names}`: `{value}`. "
                f"Expected one of: {expected_values}."
            ),
            **kwargs,
        )


class UserImportNotFoundError(SourceLocatedUserException):
    """Raised if an import couldn't be resolved."""


class UserAmbiguousReferenceError(SourceLocatedUserException):
    """Raised if something has a conflicting name in the same scope."""


class UserFileNotFoundError(SourceLocatedUserException, FileNotFoundError):
    """Raised if a file couldn't be found."""


class UserUnknownUnitError(SourceLocatedUserException):
    """Raised if a unit couldn't be interpreted."""


class UserIncompatibleUnitError(SourceLocatedUserException):
    """Raised if units are incompatible."""


class UserInfraError(SourceLocatedUserException):
    """Raised when there's an issue contacting atopile infrastructure."""

    _title = "Infrastructure Error"


class UserNotImplementedError(SourceLocatedUserException):
    """Raised when a feature is not yet implemented."""


class UserBadParameterError(SourceLocatedUserException):
    """Raised when a bad CLI param is given."""


class UserPythonLoadError(SourceLocatedUserException):
    """Raised when a Python module couldn't be loaded."""


class UserPythonModuleError(SourceLocatedUserException):
    """Raised when a user-provided Python module is faulty."""


class UserPythonConstructionError(UserPythonModuleError):
    """Raised when a Python module couldn't be constructed."""


class UserAssertionError(SourceLocatedUserException):
    """Raised when an assertion fails."""


class UserContradictionException(SourceLocatedUserException):
    """Raised when user-provided constraints contradict."""


class UserPickError(SourceLocatedUserException):
    """Raised when there's an error in the picker."""


class UserActionWithoutEffectError(SourceLocatedUserException):
    """Raised when an action is performed but has no effect."""


class UserAlreadyExistsError(SourceLocatedUserException):
    """Raised when something already exists."""


class UserNodeException(SourceLocatedUserException):
    """Raised when there's an error with a node operation."""

    @classmethod
    def from_node_exception(
        cls,
        node_ex: "fabll.NodeException",
        origin: ParserRuleContext | None,
        traceback: Sequence[ParserRuleContext | None] | None,
        *args,
        **kwargs,
    ) -> UserNodeException:
        return cls.from_ctx(
            origin,
            str(node_ex),
            *args,
            traceback=traceback,
            **kwargs,
        )


class UserNoProjectException(SourceLocatedUserException):
    """Raised when the project directory is not found."""

    def __init__(
        self,
        msg: str = (
            "Could not find the project directory, are you within an ato project?"
        ),
        search_path: Path | None = None,
        *args,
        **kwargs,
    ):
        if search_path:
            msg += f"\n\nSearch path: {search_path}"
        super().__init__(msg, *args, **kwargs)


class UserFeatureNotAvailableError(SourceLocatedUserException):
    """Raised when an experimental feature is not recognized."""


class UserFeatureNotEnabledError(SourceLocatedUserException):
    """Raised when an experimental feature has not been enabled."""


class UserTraitNotFoundError(SourceLocatedUserException):
    """Raised when a trait is not found."""


class UserTraitError(SourceLocatedUserException):
    """Raised when there's an error applying a trait."""


class UserInvalidTraitError(SourceLocatedUserException):
    """Raised when something other than a valid trait follows the `trait` keyword."""


class UserToolNotAvailableError(SourceLocatedUserException):
    """Raised when kicad-cli is required but not found."""


class UserExportError(SourceLocatedUserException):
    """Raised when there's an error exporting a file via the KiCad CLI."""


# =============================================================================
# Non-Source-Located Exceptions (don't need token tracking)
# =============================================================================


class DeprecatedException(UserException):
    """This feature is deprecated and will be removed in a future version."""


class UserResourceException(UserException):
    """Indicates an issue with a user-facing resource, e.g. layout files."""


class UserDesignCheckException(UserException):
    """Indicates a failing design check."""

    @classmethod
    def from_nodes(cls, message: str, nodes: Sequence["fabll.Node"]) -> Self:
        nodes = sorted(nodes, key=lambda n: n.get_full_name())
        if nodes:
            nodes_fmt = md_list(f"`{node.pretty_repr()}`" for node in nodes)
            message = f"{message}\n\nFor nodes: \n{nodes_fmt}"
        return cls(message)


# =============================================================================
# Exception Handling Utilities
# =============================================================================


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
        """Return a recreated instance of self."""
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
    """Iterate through all the non-group exceptions as a DFS pre-order."""
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

        class _Collector(Pacman):
            def nom_nom_nom(self_, exc: Exception, original_exinfo) -> None:  # noqa: N805
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
                return error

            # Display unique errors in order
            grouped_errors = groupby(self.errors, key=_key)
            errors = [group[0] for group in grouped_errors.values()]

            if len(errors) > 1:
                return ExceptionGroup(self.group_message, errors)
            else:
                return errors[0]

    def raise_errors(self):
        """Raise the collected errors as an exception group."""
        if ex := self.get_exception():
            raise ex

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args):
        self.raise_errors()


_collectors: list[DowngradedExceptionCollector] = []


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
            yield accumulator.collect, item


# =============================================================================
# CLI Helpers
# =============================================================================

DISCORD_BANNER_TEXT = (
    "Unfortunately errors ^^^ stopped the build. "
    "If you need a hand jump on Discord! "
    "https://discord.gg/CRe5xaDBr3 👋"
)


def log_discord_banner() -> None:
    """Log the Discord help banner."""
    from atopile.logging import logger

    logger.info(DISCORD_BANNER_TEXT)
