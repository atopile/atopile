import logging
from types import ModuleType, TracebackType

from rich._null_file import NullFile
from rich.console import ConsoleRenderable
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.text import Text
from rich.traceback import Traceback

import atopile
import faebryk
import faebryk.libs
import faebryk.libs.logging
from atopile.errors import (
    UserPythonModuleError,
    _BaseBaseUserException,
)

from . import console

_logged_exceptions: set[tuple[type[Exception], tuple]] = set()

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class LogHandler(RichHandler):
    """
    A logging handler that renders output with Rich.

    Suppresses frames from tracebacks conditionally depending on the exception type.
    """

    def __init__(
        self,
        *args,
        tracebacks_suppress_map: dict[type[BaseException], list[ModuleType]]
        | None = None,
        tracebacks_unwrap: list[type[BaseException]] | None = None,
        hide_traceback_types: tuple[type[BaseException], ...] = (),
        always_show_traceback_types: tuple[type[BaseException], ...] = (),
        traceback_level: int = logging.ERROR,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tracebacks_suppress_map = tracebacks_suppress_map or {}
        self.tracebacks_unwrap = tracebacks_unwrap or []
        self.hide_traceback_types = hide_traceback_types
        self.always_show_traceback_types = always_show_traceback_types
        self.traceback_level = traceback_level

    def _get_suppress(
        self, exc_type: type[BaseException] | None
    ) -> list[str | ModuleType]:
        """
        Get extended list of modules to suppress from tracebacks.
        """
        suppress = set(self.tracebacks_suppress)
        if exc_type is not None:
            for _type in self.tracebacks_suppress_map:
                if issubclass(exc_type, _type) or isinstance(exc_type, _type):
                    suppress.update(self.tracebacks_suppress_map[_type])
        return list(suppress)

    def _unwrap_chained_exceptions(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> tuple[type[BaseException] | None, BaseException | None, TracebackType | None]:
        def unwrap(exc: BaseException, exc_type: type[BaseException]) -> BaseException:
            """
            Unwraps an exception chain until we reach an exception
            that is not an instance of _type.
            """
            while isinstance(exc, exc_type) and exc.__cause__ is not None:
                exc = exc.__cause__
            return exc

        if exc_type is not None and exc_value is not None:
            while any(issubclass(exc_type, _type) for _type in self.tracebacks_unwrap):
                exc_value = unwrap(exc_value, exc_type)
                exc_type = type(exc_value)
                exc_traceback = exc_value.__traceback__

        return exc_type, exc_value, exc_traceback

    def _get_hashable(self, record: logging.LogRecord) -> tuple | None:
        if exc_info := getattr(record, "exc_info", None):
            _, exc_value, _ = exc_info
            if exc_value and isinstance(exc_value, _BaseBaseUserException):
                return exc_value.get_frozen()
        return None

    def _get_traceback(self, record: logging.LogRecord) -> Traceback | None:
        if not record.exc_info:
            return None

        exc_type, exc_value, exc_traceback = record.exc_info

        suppress = self._get_suppress(exc_type)

        hide_traceback = (
            isinstance(exc_value, self.hide_traceback_types)
            and not isinstance(exc_value, self.always_show_traceback_types)
        ) or record.levelno < self.traceback_level

        if isinstance(exc_value, UserPythonModuleError):
            exc_type, exc_value, exc_traceback = self._unwrap_chained_exceptions(
                exc_type, exc_value, exc_traceback
            )

        if hide_traceback or exc_type is None or exc_value is None:
            return None

        return Traceback.from_exception(
            exc_type,
            exc_value,
            exc_traceback,
            width=self.tracebacks_width,
            extra_lines=self.tracebacks_extra_lines,
            theme=self.tracebacks_theme,
            word_wrap=self.tracebacks_word_wrap,
            show_locals=self.tracebacks_show_locals,
            locals_max_length=self.locals_max_length,
            locals_max_string=self.locals_max_string,
            suppress=suppress,
        )

    def _render_message(
        self, record: logging.LogRecord, message: str
    ) -> "ConsoleRenderable":
        """Render message text in to Text.

        Args:
            record (LogRecord): logging Record.
            message (str): String containing log message.

        Returns:
            ConsoleRenderable: Renderable to display log message.
        """
        use_markdown = getattr(record, "markdown", False)
        use_markup = getattr(record, "markup", self.markup)
        highlighter = getattr(record, "highlighter", self.highlighter)

        if use_markdown:
            message_text = Markdown(message)
        else:
            message_text = Text.from_markup(message) if use_markup else Text(message)

            if highlighter:
                message_text = highlighter(message_text)

            if self.keywords is None:
                self.keywords = self.KEYWORDS

            if self.keywords:
                message_text.highlight_words(self.keywords, "logging.keyword")

        return message_text

    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        # special handling for exceptions only
        if record.exc_info is None:
            return self._render_message(record, message)

        _, exc, _ = record.exc_info

        if not isinstance(exc, ConsoleRenderable):
            return self._render_message(record, message)

        return exc

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        hashable = self._get_hashable(record)

        if hashable and hashable in _logged_exceptions:
            # we've already logged this
            return

        traceback = self._get_traceback(record)

        if self.formatter:
            record.message = record.getMessage()
            formatter = self.formatter
            if hasattr(formatter, "usesTime") and formatter.usesTime():
                record.asctime = formatter.formatTime(record, formatter.datefmt)
            message = formatter.formatMessage(record)
        else:
            message = record.getMessage()

        message_renderable = self.render_message(record, message)

        log_renderable = self.render(
            record=record, traceback=traceback, message_renderable=message_renderable
        )
        if isinstance(self.console.file, NullFile):
            # Handles pythonw, where stdout/stderr are null, and we return NullFile
            # instance from Console.file. In this case, we still want to make a log record # noqa: E501  # pre-existing
            # even though we won't be writing anything to a file.
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable, highlight=True)
            except Exception:
                self.handleError(record)

        if hashable:
            _logged_exceptions.add(hashable)


logger = logging.getLogger(__name__)

handler = LogHandler(
    console=console.console,
    rich_tracebacks=True,
    show_path=False,
    tracebacks_suppress=["typer"],
    tracebacks_suppress_map={UserPythonModuleError: [atopile, faebryk]},
    tracebacks_unwrap=[UserPythonModuleError],
    hide_traceback_types=(_BaseBaseUserException,),
    always_show_traceback_types=(UserPythonModuleError,),
    traceback_level=logging.ERROR,
)

handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))

faebryk.libs.logging.setup_basic_logging(handlers=[handler])
