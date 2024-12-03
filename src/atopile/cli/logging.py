import logging
import textwrap
from types import ModuleType, TracebackType

from rich._null_file import NullFile
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.theme import Theme
from rich.traceback import Traceback

import atopile
import faebryk
from atopile.errors import (
    UserPythonModuleError,
    _BaseBaseUserException,
    _BaseUserException,
)


class NodeHighlighter(RegexHighlighter):
    """
    Apply style to anything that looks like an faebryk Node\n
    <*|XOR_with_NANDS.nands[2]|NAND.inputs[0]|Logic> with
    <*|TI_CD4011BE.nands[2]|ElectricNAND.inputs[0]|ElectricLogic>\n
    \t<> = Node\n
    \t|  = Type\n
    \t.  = Parent\n
    \t*  = Root
    """

    base_style = "node."
    highlights = [
        #  r"(?P<Rest>(.*))",
        r"(?P<Node>([/</>]))",
        r"[?=\|](?P<Type>([a-zA-Z_0-9]+))[?=\>]",
        r"[\.](?P<Child>([a-zA-Z_0-9]+))[?=\[]",
        r"[\|](?P<Parent>([a-zA-Z_0-9]+))[?=\.]",
        r"[?<=*.](?P<Root>(\*))",
        r"[?=\[](?P<Number>([0-9]+))[?=\]]",
    ]


_logged_exceptions: set[tuple[type[Exception], tuple]] = set()


class AtoLogHandler(RichHandler):
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
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tracebacks_suppress_map = tracebacks_suppress_map or {}
        self.tracebacks_unwrap = tracebacks_unwrap or []

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
            Unwraps an exception chain until we reach an exception that is not an instance of
            _type.
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

        hide_traceback = isinstance(
            exc_value, _BaseBaseUserException
        ) and not isinstance(exc_value, UserPythonModuleError)

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

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        message = self.format(record)
        hashable = self._get_hashable(record)

        if hashable and hashable in _logged_exceptions:
            # we've already logged this
            return

        traceback = self._get_traceback(record)

        message = record.getMessage()
        if self.formatter:
            record.message = record.getMessage()
            formatter = self.formatter
            if hasattr(formatter, "usesTime") and formatter.usesTime():
                record.asctime = formatter.formatTime(record, formatter.datefmt)
            message = formatter.formatMessage(record)

        message_renderable = self.render_message(record, message)

        log_renderable = self.render(
            record=record, traceback=traceback, message_renderable=message_renderable
        )
        if isinstance(self.console.file, NullFile):
            # Handles pythonw, where stdout/stderr are null, and we return NullFile
            # instance from Console.file. In this case, we still want to make a log record
            # even though we won't be writing anything to a file.
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable)
            except Exception:
                self.handleError(record)

        if hashable:
            _logged_exceptions.add(hashable)


class AtoLogFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(fmt="%(message)s", datefmt="[%X]")

    def format(self, record: logging.LogRecord) -> str:
        # special handling for exceptions only
        if record.exc_info is None:
            return super().format(record)

        _, exc, _ = record.exc_info

        if not isinstance(exc, _BaseBaseUserException):
            return super().format(record)

        header = ""

        if exc.title:
            header += f"[bold]{exc.title}[/]\n"
            record.markup = True

        # Attach source info if we have it
        if isinstance(exc, _BaseUserException):
            if source_info := exc.src_path:
                print(f"{source_info=}")
                source_info = str(source_info)
                if src_line := exc.src_line:
                    source_info += f":{src_line}"
                if src_col := exc.src_col:
                    source_info += f":{src_col}"

                header += f"{source_info}\n"

        indented_message = (
            textwrap.indent(record.getMessage(), "    ")
            if exc.title or source_info
            else record.getMessage()
        )

        return f"{header}{indented_message}".strip()


console = Console(
    theme=Theme(
        {
            "node.Node": "bold magenta",
            "node.Type": "bright_cyan",
            "node.Parent": "bright_red",
            "node.Child": "bright_yellow",
            "node.Root": "bold yellow",
            "node.Number": "bright_green",
            #   "node.Rest": "bright_black",
            "logging.level.warning": "yellow",
        }
    )
)


logger = logging.getLogger(__name__)

handler = AtoLogHandler(
    console=console,
    rich_tracebacks=True,
    show_path=False,
    tracebacks_suppress=["typer"],
    tracebacks_suppress_map={UserPythonModuleError: [atopile, faebryk]},
    tracebacks_unwrap=[UserPythonModuleError],
)

handler.setFormatter(AtoLogFormatter())

logging.basicConfig(level="INFO", handlers=[handler])
