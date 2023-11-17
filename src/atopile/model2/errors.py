import logging
import textwrap
import traceback
from contextlib import contextmanager
from enum import IntEnum
from pathlib import Path
from typing import Optional, Type

from antlr4 import InputStream, Token, ParserRuleContext

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# I think it'd make far more sense for this to exist in .parse
# however, it'd become a circular import
def get_src_info_from_token(token: Token) -> tuple[str, int, int]:
    """Get the source path, line, and column from a context"""
    input_stream: InputStream = token.getInputStream()
    return input_stream.name, token.line, token.column

def get_src_info_from_ctx(ctx: ParserRuleContext) -> tuple[str, int, int]:
    """Get the source path, line, and column from a context"""
    token: Token = ctx.start
    return get_src_info_from_token(token)


class AtoError(Exception):
    """
    This exception is thrown when there's an error in the syntax of the language
    """

    def __init__(
        self,
        message: str = "",
        src_path: Optional[str | Path] = None,
        src_line: Optional[int] = None,
        src_col: Optional[int] = None,
        *args: object,
    ) -> None:
        super().__init__(message, *args)
        self.message = message
        self.src_path = src_path
        self.src_line = src_line
        self.src_col = src_col

    @classmethod
    def from_token(cls, message: str, token: Token) -> "AtoError":
        src_path, src_line, src_col = get_src_info_from_token(token)
        return cls(message, src_path, src_line, src_col)

    @classmethod
    def from_ctx(cls, message: str, ctx: ParserRuleContext) -> "AtoError":
        src_path, src_line, src_col = get_src_info_from_ctx(ctx)
        return cls(message, src_path, src_line, src_col)

    @property
    def user_facing_name(self):
        error_name = self.__class__.__name__
        if error_name.startswith("Ato"):
            return error_name[3:]
        return error_name


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
    visitor_type: Type,
    logger: logging.Logger,
):
    """Helper function to consistently write errors to the log"""
    if isinstance(ex, ExceptionGroup):
        for e in ex.exceptions:
            _process_error(e, visitor_type, logger)
        return

    src_path = None
    start_line = None
    start_column = None

    # if we catch an ato error, we can reliably get the line and column from the exception itself
    # if not, we need to get the error's line and column from the context, if possible
    if isinstance(ex, AtoError):
        message = ex.user_facing_name + ": " + ex.message
        src_path = ex.src_path
        start_line = ex.src_line
        start_column = ex.src_col
    else:
        message = f"Unprocessed '{repr(ex)}' occurred during compilation"
        if visitor_type is not None:
            if ctx := get_locals_from_exception_in_class(ex, visitor_type).get("ctx"):
                src_path, start_line, start_column = get_src_info_from_ctx(ctx)

    # ensure we have values for all the components on the error string
    if src_path is None:
        src_path = "<?>"
    if start_line is None:
        start_line = "<?>"
    if start_column is None:
        start_column = "<?>"

    indented_message = textwrap.indent(message, "--> ")

    logger.error(
        textwrap.dedent(
            f"""
            {src_path}:{start_line}:{start_column}:
            {indented_message}
            """
        ).strip()
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Error info:\n", exc_info=ex)


class ReraiseBehavior(IntEnum):
    IGNORE = 0
    RERAISE = 1
    RAISE_ATO_ERROR = 2


@contextmanager
def write_errors_to_log(
    visitor_type: Optional[Type] = None,
    logger: Optional[logging.Logger] = None,
    reraise: ReraiseBehavior = ReraiseBehavior.RERAISE,
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
        _process_error(ex, visitor_type, logger)
        if reraise == ReraiseBehavior.RERAISE:
            raise
        elif reraise == ReraiseBehavior.RAISE_ATO_ERROR:
            raise AtoError from ex
