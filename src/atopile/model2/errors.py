import logging
import textwrap
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Type

from atopile.model2 import types

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AtoError(Exception):
    """
    This exception is thrown when there's an error in the syntax of the language
    """

    def __init__(
        self,
        message: str,
        src_path: Optional[str | Path] = None,
        src_line: Optional[int] = None,
        src_col: Optional[int] = None,
        *args: object,
    ) -> None:
        super().__init__(message, *args)
        self.message = message
        self._src_path = src_path
        self.src_line = src_line
        self.src_col = src_col

    @property
    def user_facing_name(self):
        return self.__class__.__name__[3:]


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


class AtoNameConflictError(AtoError):
    """
    Raised if something has a conflicting name in the same scope.
    """


class AtoCircularDependencyError(AtoError):
    """
    Raised if something has a conflicting name in the same scope.
    """


class AtoImportNotFoundError(AtoError):
    """
    Raised if something has a conflicting name in the same scope.
    """


def get_locals_from_exception_in_class(ex: Exception, class_: Type) -> dict:
    for tb, _ in list(traceback.walk_tb(ex.__traceback__))[::-1]:
        if isinstance(tb.f_locals.get("self"), class_):
            return tb.f_locals
    return {}


@contextmanager
def ato_errors_to_log(
    file_path: Path,
    class_: Type,
    error_class: Type[AtoError] = AtoError,
    logger: Optional[logging.Logger] = None,
    reraise: bool = True,
) -> types.Class:
    """
    Compile the given tree into an atopile core representation
    """
    if logger is None:
        logger = log

    try:
        yield
    except Exception as ex:
        if ctx := get_locals_from_exception_in_class(ex, class_).get("ctx"):
            if isinstance(ex, error_class):
                message = ex.user_facing_name + ": " + ex.message
            else:
                message = f"Unprocessed '{repr(ex)}' occurred during compilation"

            logger.exception(
                textwrap.dedent(
                    f"""
                    {file_path}:{ctx.start.line}:{ctx.start.column}:
                    {message}
                    """
                ).strip()
            )
        if reraise:
            raise
