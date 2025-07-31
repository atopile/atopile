import io
import logging
import shutil
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import ModuleType, TracebackType

import pathvalidate
from rich._null_file import NullFile
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.padding import Padding
from rich.progress import (
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    RenderableColumn,
    SpinnerColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Column
from rich.text import Text
from rich.traceback import Traceback

import atopile
import faebryk
import faebryk.libs
import faebryk.libs.logging
from atopile.errors import UserPythonModuleError, _BaseBaseUserException
from faebryk.libs.logging import FLOG_FMT
from faebryk.libs.util import Advancable, ConfigFlag

from . import console

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

import urllib3  # noqa: E402

urllib3.disable_warnings()  # FIXME: SSL

COLOR_LOGS = ConfigFlag("COLOR_LOGS", default=False)
NOW = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
_DEFAULT_FORMATTER = logging.Formatter("%(message)s", datefmt="[%X]")
_SHOW_LOG_FILE_PATH_THRESHOLD = 120


# displayed during LoggingStage
ALERT = logging.INFO + 5
logging.addLevelName(ALERT, "ALERT")


class LogHandler(RichHandler):
    """
    A logging handler that renders output with Rich.

    Suppresses frames from tracebacks conditionally depending on the exception type.
    """

    def __init__(
        self,
        *args,
        console: Console,
        rich_tracebacks: bool = True,
        show_path: bool = False,
        tracebacks_suppress: Iterable[str] | None = ["typer"],
        tracebacks_suppress_map: dict[type[BaseException], Iterable[ModuleType]]
        | None = {UserPythonModuleError: [atopile, faebryk]},
        tracebacks_unwrap: list[type[BaseException]] | None = [UserPythonModuleError],
        hide_traceback_types: tuple[type[BaseException], ...] = (
            _BaseBaseUserException,
        ),
        always_show_traceback_types: tuple[type[BaseException], ...] = (
            UserPythonModuleError,
        ),
        traceback_level: int = logging.ERROR,
        force_terminal: bool = False,
        **kwargs,
    ):
        super().__init__(
            *args,
            console=console,
            rich_tracebacks=rich_tracebacks,
            show_path=show_path,
            **kwargs,
        )
        self.tracebacks_suppress = tracebacks_suppress or []
        self.tracebacks_suppress_map = tracebacks_suppress_map or {}
        self.tracebacks_unwrap = tracebacks_unwrap or []
        self.hide_traceback_types = hide_traceback_types
        self.always_show_traceback_types = always_show_traceback_types
        self.traceback_level = traceback_level
        self._logged_exceptions = set()
        self._is_terminal = force_terminal or console.is_terminal

        self.addFilter(
            lambda record: record.name.startswith("atopile")
            or record.name.startswith("faebryk")
        )

    def _get_suppress(
        self, exc_type: type[BaseException] | None
    ) -> Iterable[str | ModuleType]:
        """
        Get extended list of modules to suppress from tracebacks.
        """
        suppress: set[str | ModuleType] = set(self.tracebacks_suppress)
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
        if not self._is_terminal:
            return Text(message)

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
        if record.exc_info is not None and isinstance(
            (exc := record.exc_info[1]), ConsoleRenderable
        ):
            # UserExceptions are already renderables
            return exc

        return self._render_message(record, message)

    def _get_hashable(self, record: logging.LogRecord) -> tuple | None:
        if exc_info := getattr(record, "exc_info", None):
            _, exc_value, _ = exc_info
            if exc_value and isinstance(exc_value, _BaseBaseUserException):
                return exc_value.get_frozen()
        return None

    def _prepare_emit(self, record: logging.LogRecord) -> ConsoleRenderable:
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

        return log_renderable

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return None

        log_renderable = self._prepare_emit(record)

        if isinstance(self.console.file, NullFile):
            # Handles pythonw, where stdout/stderr are null, and we return NullFile
            # instance from Console.file. In this case, we still want to make a log
            # record even though we won't be writing anything to a file.
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable)
            except Exception:
                self.handleError(record)
            finally:
                if hashable:
                    self._logged_exceptions.add(hashable)


class LiveLogHandler(LogHandler):
    def __init__(self, status: "LoggingStage", *args, **kwargs):
        super().__init__(*args, console=status._console, **kwargs)
        self.status = status

    def emit(self, record: logging.LogRecord) -> None:
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return

        try:
            if record.levelno >= logging.ERROR:
                self.status._error_count += 1
            elif record.levelno >= logging.WARNING:
                self.status._warning_count += 1

            self.status.refresh()

            if record.levelno == ALERT:
                self.status.alert(record.getMessage())

        except Exception:
            self.handleError(record)
        finally:
            if hashable:
                self._logged_exceptions.add(hashable)


class CaptureLogHandler(LogHandler):
    def __init__(self, status: "LoggingStage", console: Console, *args, **kwargs):
        super().__init__(*args, console=console, **kwargs)
        self.status = status

    def emit(self, record: logging.LogRecord) -> None:
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return

        try:
            super().emit(record)
        except Exception:
            self.handleError(record)
        finally:
            if hashable:
                self._logged_exceptions.add(hashable)


class IndentedProgress(Progress):
    def __init__(self, *args, indent: int = 20, **kwargs):
        self.indent = indent
        super().__init__(*args, **kwargs)

    def get_renderable(self):
        return Padding(super().get_renderable(), pad=(0, 0, 0, self.indent))


class ShortTimeElapsedColumn(TimeElapsedColumn):
    """Renders time elapsed."""

    def render(self, task: "Task") -> Text:
        """Show time elapsed."""
        elapsed = task.elapsed or 0
        return Text.from_markup(f"[blue][{elapsed:.1f}s][/blue]")


class StyledMofNCompleteColumn(MofNCompleteColumn):
    def render(self, task: "Task") -> Text:
        return Text.from_markup(
            f"[dim]{task.completed}[/dim]{self.separator}[dim]{task.total}[/dim]"
        )


class SpacerColumn(RenderableColumn):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, renderable=Text(), table_column=Column(ratio=1), **kwargs
        )


class CompletableSpinnerColumn(SpinnerColumn):
    class Status(StrEnum):
        SUCCESS = "[green]✓[/green]"
        FAILURE = "[red]✗[/red]"
        WARNING = "[yellow]⚠[/yellow]"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = None

    def complete(self, status: Status) -> None:
        self.status = status

    def render(self, task: "Task") -> RenderableType:
        text = (
            Text.from_markup(self.status)
            if self.status is not None
            else self.spinner.render(task.get_time())
        )
        return text


_log_sink_var = ContextVar[io.StringIO | None]("log_sink", default=None)


@contextmanager
def capture_logs():
    log_sink = _log_sink_var.get()
    _log_sink_var.set(io.StringIO())
    _log_sink = _log_sink_var.get()
    assert _log_sink is not None
    yield _log_sink
    _log_sink_var.set(log_sink)


@contextmanager
def log_exceptions(log_sink: io.StringIO):
    from atopile.cli.excepthook import _handle_exception

    exc_log_console = Console(file=log_sink)
    exc_log_handler = LogHandler(console=exc_log_console)
    logger.addHandler(exc_log_handler)

    try:
        yield
    except Exception as e:
        _handle_exception(type(e), e, e.__traceback__)
        raise e
    finally:
        logger.removeHandler(exc_log_handler)


class LoggingStage(Advancable):
    _LOG_LEVELS = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
    }

    def __init__(
        self, name: str, description: str, steps: int | None = None, indent: int = 20
    ):
        self.name = name
        self.description = description
        self.indent = indent
        self.steps = steps
        self._console = console.error_console
        self._warning_count = 0
        self._error_count = 0
        self._info_log_path = None
        self._log_handler = None
        self._capture_log_handler = None
        self._file_handlers = []
        self._original_handlers = {}
        self._sanitized_name = pathvalidate.sanitize_filename(self.name)
        self._result = None

        self._progress = IndentedProgress(
            *self._get_columns(),
            console=self._console,
            transient=False,
            auto_refresh=True,
            refresh_per_second=10,
            indent=self.indent,
            expand=True,
        )

    def _get_columns(self) -> tuple[ProgressColumn, ...]:
        show_log_file_path = (
            self._info_log_path and self._console.width >= _SHOW_LOG_FILE_PATH_THRESHOLD
        )

        return tuple(
            col
            for col in (
                CompletableSpinnerColumn(),
                TextColumn("{task.description}"),
                StyledMofNCompleteColumn() if self.steps is not None else None,
                ShortTimeElapsedColumn(),
                SpacerColumn(),
                TextColumn(
                    f"[dim]{self._info_log_path}[/dim]" if show_log_file_path else "",
                    justify="right",
                    table_column=Column(justify="right", overflow="ellipsis"),
                ),
            )
            if col is not None
        )

    def _update_columns(self) -> None:
        self._progress.columns = self._get_columns()

    def alert(self, message: str) -> None:
        message = f"[bold][yellow]![/yellow] {message}[/bold]"

        self._console.print(
            Padding(Text.from_markup(message), pad=(0, 0, 0, self.indent)),
            highlight=True,
        )

    def _generate_description(self) -> str:
        problems = []
        if self._error_count > 0:
            plural_e = "s" if self._error_count > 1 else ""
            problems.append(f"[red]{self._error_count} error{plural_e}[/red]")

        if self._warning_count > 0:
            plural_w = "s" if self._warning_count > 1 else ""
            problems.append(f"[yellow]{self._warning_count} warning{plural_w}[/yellow]")

        problems_text = f" ({', '.join(problems)})" if problems else ""
        return f"{self.description}{problems_text}"

    def refresh(self) -> None:
        if not hasattr(self, "_task_id"):
            return

        self._progress.update(self._task_id, description=self._generate_description())

    def set_total(self, total: int | None) -> None:
        self.steps = total
        self._update_columns()
        self._progress.update(self._task_id, total=total)
        self.refresh()

    def advance(self, advance: int = 1) -> None:
        assert self.steps is not None
        self._progress.advance(self._task_id, advance)

    def __enter__(self) -> "LoggingStage":
        self._setup_logging()
        self._update_columns()
        self._progress.start()
        self._task_id = self._progress.add_task(
            self.description, total=self.steps if self.steps is not None else 1
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._restore_logging()

        if exc_type is not None or self._error_count > 0:
            status = CompletableSpinnerColumn.Status.FAILURE
        elif self._warning_count > 0:
            status = CompletableSpinnerColumn.Status.WARNING
        else:
            status = CompletableSpinnerColumn.Status.SUCCESS

        for column in self._progress.columns:
            if isinstance(column, CompletableSpinnerColumn):
                column.complete(status)

        self.refresh()
        self._progress.stop()

    def _create_log_dir(self) -> Path:
        from atopile.config import config

        base_log_dir = Path(config.project.paths.logs) / "archive" / NOW

        try:
            build_cfg = config.build
            log_dir = base_log_dir / pathvalidate.sanitize_filename(build_cfg.name)
        except RuntimeError:
            log_dir = base_log_dir

        log_dir.mkdir(parents=True, exist_ok=True)

        latest_link = Path(config.project.paths.logs) / "latest"
        if latest_link.exists():
            if latest_link.is_symlink():
                latest_link.unlink()
            else:
                shutil.rmtree(latest_link)
        try:
            latest_link.symlink_to(base_log_dir, target_is_directory=True)
        except OSError:
            # If we can't symlink, just don't symlink
            # Logs are still written to the dated directory
            # Seems to happen on Windows if 'Developer Mode' is not enabled
            pass

        return log_dir

    def _setup_logging(self) -> None:
        root_logger = logging.getLogger()

        self._original_level = root_logger.level
        self._original_handlers = {"root": root_logger.handlers.copy()}

        # log all messages to at least one handler
        root_logger.setLevel(logging.DEBUG)

        self._log_handler = LiveLogHandler(self)
        self._log_handler.setFormatter(_DEFAULT_FORMATTER)
        self._log_handler.setLevel(self._original_level)

        if _log_sink_var.get() is not None:
            capture_console = Console(file=_log_sink_var.get())
            self._capture_log_handler = CaptureLogHandler(self, console=capture_console)
            self._capture_log_handler.setFormatter(_DEFAULT_FORMATTER)
            self._capture_log_handler.setLevel(logging.INFO)

        log_dir = self._create_log_dir()

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        root_logger.addHandler(self._log_handler)
        if self._capture_log_handler is not None:
            root_logger.addHandler(self._capture_log_handler)

        self._file_handlers = []
        self._file_handles = {}

        for level, level_name in self._LOG_LEVELS.items():
            log_file = log_dir / f"{self._sanitized_name}.{level_name}.log"

            self._file_handles[level_name] = log_file.open("w", encoding="utf-8")
            file_console = Console(
                file=self._file_handles[level_name],
                width=500,
                force_terminal=COLOR_LOGS.get(),
            )
            file_handler = LogHandler(
                console=file_console,
                force_terminal=COLOR_LOGS.get(),
                markup=False,
            )
            file_handler.setFormatter(_DEFAULT_FORMATTER)
            file_handler.setLevel(level)
            self._file_handlers.append(file_handler)
            root_logger.addHandler(file_handler)

            if level_name == "info":
                try:
                    info_log_path = log_file.relative_to(Path.cwd())
                except ValueError:
                    info_log_path = log_file

                self._info_log_path = info_log_path

    def _restore_logging(self) -> None:
        if not self._log_handler and not self._file_handlers:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(self._original_level)

        if self._log_handler in root_logger.handlers:
            root_logger.removeHandler(self._log_handler)

        if self._capture_log_handler in root_logger.handlers:
            root_logger.removeHandler(self._capture_log_handler)

        for file_handler in self._file_handlers:
            if file_handler in root_logger.handlers:
                root_logger.removeHandler(file_handler)
                file_handler.close()

        for file_handle in self._file_handles.values():
            file_handle.close()

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        for handler in self._original_handlers.get("root", []):
            root_logger.addHandler(handler)

        self._original_handlers = {}
        self._original_level = logging.INFO
        self._log_handler = None
        self._capture_log_handler = None
        self._file_handlers = []


handler = LogHandler(console=console.error_console)
handler.setFormatter(_DEFAULT_FORMATTER)

if FLOG_FMT:
    faebryk.libs.logging.setup_basic_logging()
else:
    logging.basicConfig(level=logging.INFO, handlers=[handler])

logger = logging.getLogger(__name__)
