from pathlib import Path
from typing import Type

from antlr4 import ParserRuleContext

from atopile.parse_utils import get_src_info_from_ctx, reconstruct
from faebryk.libs.exceptions import UserException as _BaseBaseUserException


class _BaseUserException(_BaseBaseUserException):
    """
    This exception is thrown when there's an error in the syntax of the language
    """

    def __init__(
        self,
        *args,
        src_path: str | Path | None = None,
        src_line: int | None = None,
        src_col: int | None = None,
        src_stop_line: int | None = None,
        src_stop_col: int | None = None,
        src_reconstructed: str | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.src_path = src_path
        self.src_line = src_line
        self.src_col = src_col
        self.src_stop_line = src_stop_line
        self.src_stop_col = src_stop_col
        self.src_reconstructed = src_reconstructed

    class _SameCtx: ...

    @classmethod
    def from_ctx(
        cls,
        ctx: ParserRuleContext | None,
        message: str,
        *args,
        expand_before: int = 0,
        expand_after: int = 0,
        mark: ParserRuleContext | None | Type[_SameCtx] = _SameCtx,
        **kwargs,
    ) -> "_BaseUserException":
        """Create an error from a context."""
        self = cls(message, *args, **kwargs)

        if ctx is not None:
            self.set_src_from_ctx(ctx, expand_before, expand_after, mark)

        return self

    def set_src_from_ctx(
        self,
        ctx: ParserRuleContext,
        expand_before: int = 0,
        expand_after: int = 0,
        mark: ParserRuleContext | None | Type[_SameCtx] = _SameCtx,
    ):
        """Add source info from a context."""
        (
            self.src_path,
            self.src_line,
            self.src_col,
            self.src_stop_line,
            self.src_stop_col,
        ) = get_src_info_from_ctx(ctx)

        if mark is self._SameCtx:
            mark = ctx

        assert isinstance(mark, ParserRuleContext) or mark is None
        self.src_reconstructed = reconstruct(
            ctx, mark=mark, expand_before=expand_before, expand_after=expand_after
        )

    def get_frozen(self) -> tuple:
        return super().get_frozen() + (
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
