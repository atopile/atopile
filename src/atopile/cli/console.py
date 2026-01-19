import rich
from rich.theme import Theme

# Theme for faebryk-style node highlighting
faebryk_theme = Theme(
    {
        "node.Node": "bold magenta",
        "node.Type": "bright_cyan",
        "node.Parent": "bright_red",
        "node.Child": "bright_yellow",
        "node.Root": "bold yellow",
        "node.Number": "bright_green",
        "logging.level.warning": "yellow",
        "node.Quantity": "bright_yellow",
        "node.IsSubset": "bright_blue",
        "node.Predicate": "bright_magenta",
        "node.Op": "red",
    }
)

rich.reconfigure(theme=faebryk_theme)

# Console should be a singleton to avoid intermixing logging w/ other output
console = rich.get_console()
error_console = rich.console.Console(theme=faebryk_theme, stderr=True)
