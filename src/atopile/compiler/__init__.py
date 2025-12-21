from atopile.errors import UserException


class DslException(UserException):
    """Exception raised for DSL-level errors (user errors in ato code)."""


class CompilerException(Exception):
    """Exception raised for internal compiler failures (implementation errors)."""
