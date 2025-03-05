import logging
import shutil
from collections import deque
from datetime import datetime
from pathlib import Path

import pathvalidate
import rich
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.live import Live
from rich.padding import Padding
from rich.spinner import Spinner
from rich.text import Text

import faebryk.libs.logging
from atopile.config import config

rich.reconfigure(theme=faebryk.libs.logging.theme)

# Console should be a singleton to avoid intermixing logging w/ other output
console = rich.get_console()
error_console = rich.console.Console(theme=faebryk.libs.logging.theme, stderr=True)

_STAGE_SUCCESS = "[green]✓[/green]"
_STAGE_FAILURE = "[red]✗[/red]"


class ProgressStage:
    # TODO: smarter indenting

    def __init__(
        self, name: str, description: str, max_log_messages: int = 15, indent: int = 20
    ):
        self.name = name
        self.description = description
        self.indent = indent
        self._console = error_console
        self._spinner = Spinner("dots")
        self._log_messages = deque(maxlen=max_log_messages)

        self._log_handler = None
        self._file_handlers = []
        self._original_handlers = {}

        self._live = Live(self._render_status(), console=self._console, transient=True)

    def _render_status(self) -> RenderableType:
        pad = (0, 0, 0, self.indent)  # (top, right, bottom, left)
        spinner_with_text = Padding(
            Columns([self._spinner, Text(self.description)], padding=(0, 1)), pad
        )

        if self._log_messages:
            log_renderables = [Text.from_markup(msg) for msg in self._log_messages]
            return Group(spinner_with_text, *log_renderables)

        return spinner_with_text

    def __enter__(self) -> "ProgressStage":
        self._setup_logging()
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._restore_logging()
        self._live.stop()
        indicator = _STAGE_SUCCESS if exc_type is None else _STAGE_FAILURE
        self._console.print(f"{' ' * self.indent}{indicator} {self.description}")

    def _setup_logging(self) -> None:
        # TODO: contextvar?

        root_logger = logging.getLogger()
        self._original_handlers = {"root": root_logger.handlers.copy()}

        class LiveStatusHandler(logging.Handler):
            def __init__(self, status: "ProgressStage"):
                super().__init__()
                self.status = status
                self.setLevel(logging.DEBUG)

            def emit(self, record: logging.LogRecord) -> None:
                try:
                    indent_str = " " * self.status.indent

                    # Only add non-debug messages to the console display
                    if record.levelno >= logging.INFO:
                        if record.levelno >= logging.ERROR:
                            formatted_msg = f"{indent_str}[bold red]ERROR[/bold red]   {record.getMessage()}"
                        elif record.levelno >= logging.WARNING:
                            formatted_msg = f"{indent_str}[yellow]WARNING[/yellow] {record.getMessage()}"
                        else:  # This is INFO level
                            formatted_msg = f"{indent_str}[blue]INFO[/blue]    {record.getMessage()}"

                        # Only add messages that aren't debug level to the console
                        self.status._add_log_message(formatted_msg)
                    # Debug messages are still logged to the file via the file handler,
                    # but we don't add them to the console display
                except Exception:
                    self.handleError(record)

        self._log_handler = LiveStatusHandler(self)

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = Path(config.project.paths.logs) / now
        log_dir.mkdir(parents=True, exist_ok=True)

        latest_link = Path(config.project.paths.logs) / "latest"
        if latest_link.exists():
            if latest_link.is_symlink():
                latest_link.unlink()
            else:
                shutil.rmtree(latest_link)
        latest_link.symlink_to(log_dir, target_is_directory=True)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        root_logger.addHandler(self._log_handler)
        self._file_handlers = []
        log_levels = {
            logging.DEBUG: "debug",
            logging.INFO: "info",
            logging.WARNING: "warning",
            logging.ERROR: "error",
        }

        sanitized_name = pathvalidate.sanitize_filename(self.name)
        for level, level_name in log_levels.items():
            log_file = log_dir / f"{sanitized_name}.{level_name}.log"
            file_handler = logging.FileHandler(log_file, mode="w")

            def filter_for_level(record, lvl=level):
                return record.levelno >= lvl

            file_handler.addFilter(filter_for_level)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)

            self._file_handlers.append(file_handler)
            root_logger.addHandler(file_handler)

    def _restore_logging(self) -> None:
        if not self._log_handler and not self._file_handlers:
            return

        root_logger = logging.getLogger()

        if self._log_handler in root_logger.handlers:
            root_logger.removeHandler(self._log_handler)

        for file_handler in self._file_handlers:
            if file_handler in root_logger.handlers:
                root_logger.removeHandler(file_handler)
                file_handler.close()

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        for handler in self._original_handlers.get("root", []):
            root_logger.addHandler(handler)

        self._original_handlers = {}
        self._log_handler = None
        self._file_handlers = []

    def _add_log_message(self, message: str) -> None:
        self._log_messages.append(message)
        self._live.update(self._render_status())
