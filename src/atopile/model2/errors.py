import logging
import textwrap
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Type


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


def _process_error(
    ex: Exception | ExceptionGroup,
    src_path: str,
    visitor_type: Type,
    logger: logging.Logger,
):
    """Helper function to consistently write errors to the log"""
    if isinstance(ex, ExceptionGroup):
        for e in ex.exceptions:
            _process_error(e, src_path, visitor_type, logger)
        return

    # if we catch an ato error, we can reliably get the line and column from the exception itself
    # if not, we need to get the error's line and column from the context, if possible
    if isinstance(ex, AtoError):
        message = ex.user_facing_name + ": " + ex.message
    else:
        message = f"Unprocessed '{repr(ex)}' occurred during compilation"
        if ctx := get_locals_from_exception_in_class(ex, visitor_type).get("ctx"):
            start_line = ctx.start.line
            start_column = ctx.start.column
        else:
            start_line = "Unknown"
            start_column = "Unknown"

    logger.exception(
        textwrap.dedent(
            f"""
            {src_path}:{start_line}:{start_column}:
            {message}
            """
        ).strip()
    )


@contextmanager
def write_errors_to_log(
    src_path: str,  # builtin errors don't have source info
    visitor_type: Type,
    logger: Optional[logging.Logger] = None,
    reraise: bool = True,
) -> None:
    """
    This helper function catches all exception and attempts to add "best effort" source info to them.
    It's designed to be used on visitors that are the first stage of compilation after parsing.
    It detects if the exception came from inside the visitor, and if so, attempts to add source info from the ANTLR ctx.
    """
    if logger is None:
        logger = log

    try:
        yield
    except (Exception, ExceptionGroup) as ex:
        _process_error(ex, src_path, visitor_type, logger)
        if reraise:
            raise

