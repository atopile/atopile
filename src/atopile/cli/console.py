import logging
from collections import deque

import rich
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.live import Live
from rich.padding import Padding
from rich.spinner import Spinner
from rich.text import Text

import faebryk.libs.logging

rich.reconfigure(theme=faebryk.libs.logging.theme)

# Console should be a singleton to avoid intermixing logging w/ other output
console = rich.get_console()
error_console = rich.console.Console(theme=faebryk.libs.logging.theme, stderr=True)


class ProgressStage:
    # TODO: smarter indenting

    def __init__(self, name: str, max_log_messages: int = 15, indent: int = 20):
        self.name = name
        self.indent = indent
        self._console = error_console
        self._spinner = Spinner("dots")
        self._log_messages = deque(maxlen=max_log_messages)

        self._log_handler = None
        self._original_handlers = {}

        self._live = Live(self._render_status(), console=self._console, transient=True)

    def _render_status(self) -> RenderableType:
        pad = (0, 0, 0, self.indent)  # (top, right, bottom, left)
        spinner_with_text = Padding(
            Columns([self._spinner, Text(self.name)], padding=(0, 1)), pad
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
        indicator = "[green]✓[/green]" if exc_type is None else "[red]✗[/red]"
        self._console.print(f"{' ' * self.indent}{indicator} {self.name}")

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

                    # Format log message based on level
                    if record.levelno >= logging.ERROR:
                        formatted_msg = f"{indent_str}[bold red]ERROR[/bold red]   {record.getMessage()}"
                    elif record.levelno >= logging.WARNING:
                        formatted_msg = f"{indent_str}[yellow]WARNING[/yellow] {record.getMessage()}"
                    elif record.levelno >= logging.INFO:
                        formatted_msg = (
                            f"{indent_str}[blue]INFO[/blue]    {record.getMessage()}"
                        )
                    else:
                        formatted_msg = (
                            f"{indent_str}[dim]DEBUG[/dim]   {record.getMessage()}"
                        )

                    self.status._add_log_message(formatted_msg)
                except Exception:
                    self.handleError(record)

        self._log_handler = LiveStatusHandler(self)

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        root_logger.addHandler(self._log_handler)

    def _restore_logging(self) -> None:
        if not self._log_handler:
            return

        root_logger = logging.getLogger()
        if self._log_handler in root_logger.handlers:
            root_logger.removeHandler(self._log_handler)

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        for handler in self._original_handlers.get("root", []):
            root_logger.addHandler(handler)

        self._original_handlers = {}
        self._log_handler = None

    def _add_log_message(self, message: str) -> None:
        self._log_messages.append(message)
        self._live.update(self._render_status())
