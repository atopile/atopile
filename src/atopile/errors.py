from pathlib import Path
from typing import Any

from antlr4 import ParserRuleContext
from rich.console import Console, ConsoleOptions, ConsoleRenderable
from rich.syntax import Syntax
from rich.text import Text

from atopile.parse_utils import PygmentsLexerShim, get_src_info_from_ctx
from faebryk.libs.exceptions import UserException as _BaseBaseUserException


class _BaseUserException(_BaseBaseUserException):
    """
    This exception is thrown when there's an error in the syntax of the language
    """

    class _SameCtx: ...

    def __init__(
        self,
        *args,
        origin: Any | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.origin = origin

    @classmethod
    def from_ctx(
        cls,
        origin: ParserRuleContext | None,
        message: str,
        *args,
        **kwargs,
    ) -> "_BaseUserException":
        """Create an error from a context."""
        self = cls(message, *args, origin=origin, **kwargs)
        return self

    def get_frozen(self) -> tuple:
        if self.origin:
            return super().get_frozen() + get_src_info_from_ctx(self.origin)
        return super().get_frozen()

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> list[ConsoleRenderable]:
        renderables: list[ConsoleRenderable] = []
        if self.title:
            renderables += [Text(self.title, style="bold")]
        renderables += [Text(self.message)]

        if self.origin:
            (src_path, src_line, src_col, _, _) = get_src_info_from_ctx(self.origin)

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

            renderables += [
                Text("Source: ", style="bold") + Text(source_info, style="magenta"),
            ]

            if isinstance(self.origin, ParserRuleContext):
                lexer = PygmentsLexerShim.from_ctx(self.origin, 1, 1)
                renderables += [
                    Syntax(
                        lexer.get_code(),
                        lexer,  # type: ignore  # The PygmentsLexerShim is pygments.Lexer-y enough
                        line_numbers=True,
                        start_line=lexer.start_line,
                        indent_guides=True,
                        highlight_lines=lexer.ctx_lines,
                    )
                ]

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
