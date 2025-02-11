from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from antlr4 import CommonTokenStream, ParserRuleContext, Token
from rich.console import Console, ConsoleOptions, ConsoleRenderable
from rich.highlighter import ReprHighlighter
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text

from atopile.parse_utils import (
    PygmentsLexerReconstructor,
    get_src_info_from_token,
)
from faebryk.libs.exceptions import UserException as _BaseBaseUserException

if TYPE_CHECKING:
    from faebryk.libs.picker.picker import PickError


def _render_tokens(
    token_stream: CommonTokenStream, start_token: Token, stop_token: Token
) -> list[ConsoleRenderable]:
    lexer = PygmentsLexerReconstructor.from_tokens(
        token_stream, start_token, stop_token, 1, 1
    )
    src_path, src_line, src_col = get_src_info_from_token(start_token)

    # Make the path relative to the current working directory, if possible
    try:
        src_path = Path(src_path).relative_to(Path.cwd())
    except ValueError:
        pass
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
        ),
    ]


class _BaseUserException(_BaseBaseUserException):
    """
    This exception is thrown when there's an error in the syntax of the language
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
        **kwargs,
    ):
        super().__init__(msg, *args, **kwargs)

        self.token_stream = token_stream
        self.origin_start = origin_start
        self.origin_stop = origin_stop
        self.traceback = traceback
        self.markdown = markdown

        if self.token_stream is None and (
            self.origin_start is not None or self.origin_stop is not None
        ):
            raise ValueError(
                "token_stream is required if origin_start or origin_stop is provided"
            )

    def attach_origin_from_ctx(self, ctx: ParserRuleContext) -> None:
        self.origin_start = ctx.start
        self.origin_stop = ctx.stop
        self.token_stream = ctx.parser.getInputStream()  # type: ignore

    @classmethod
    def from_ctx[T: _BaseUserException](
        cls: type[T],
        origin: ParserRuleContext | None,
        message: str,
        *args,
        traceback: Sequence[ParserRuleContext | None] | None = None,
        **kwargs,
    ) -> T:
        """Create an error from a context."""

        instance = cls(message, *args, traceback=traceback, **kwargs)

        if origin is not None:
            instance.attach_origin_from_ctx(origin)

        return instance

    @classmethod
    def from_tokens[T: _BaseUserException](
        cls: type[T],
        token_stream: CommonTokenStream,
        origin_start: Token,
        origin_stop: Token | None,
        message: str,
        *args,
        traceback: Sequence[ParserRuleContext | None] | None = None,
        **kwargs,
    ) -> T:
        """Create an error from a context."""

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
        renderables: list[ConsoleRenderable] = []

        if self.title:
            renderables += [Text(self.title, style="bold")]

        renderables += [
            Markdown(self.message)
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


class UserAssertionError(UserException):
    """
    Raised when an assertion fails.
    """


class UserPickError(UserException):
    """
    Raised when there's an error in the picker.
    """

    @classmethod
    def from_pick_error(cls, ex: "PickError") -> "UserPickError":
        from atopile.front_end import from_dsl

        if origin_t := ex.module.try_get_trait(from_dsl):
            origin = origin_t.src_ctx
        else:
            origin = None

        return cls.from_ctx(origin, ex.message)


class UserActionWithoutEffectError(UserException):
    """
    Raised when an action is performed but has no effect.
    """


class UserAlreadyExistsError(UserException):
    """
    Raised when something already exists.
    """
