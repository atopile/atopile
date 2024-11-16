from rich.console import Console
from rich.theme import Theme

console = Console(theme=Theme({"logging.level.warning": "yellow"}))
