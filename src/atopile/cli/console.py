import rich
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

import faebryk.libs.logging

rich.reconfigure(theme=faebryk.libs.logging.theme)

# Console should be a singleton to avoid intermixing logging w/ other output
console = rich.get_console()
error_console = rich.console.Console(theme=faebryk.libs.logging.theme, stderr=True)


class Status:
    def __init__(self, name: str):
        self.name = name
        self._spinner = Spinner("dots", text=name)
        self._live = Live(self._spinner, console=console, transient=True)

    @property
    def console(self) -> "Console":
        """Get the Console used by the Status objects."""
        return self._live.console

    def __enter__(self) -> "Status":
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._live.stop()
        if exc_type is None:
            console.print(f"[green]✓[/green] {self.name}")
        else:
            error_console.print(f"[red]✗[/red] {self.name}")
