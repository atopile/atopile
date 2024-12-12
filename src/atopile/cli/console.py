import rich

import faebryk.libs.logging

rich.reconfigure(theme=faebryk.libs.logging.theme)

# Console should be a singleton to avoid intermixing logging w/ other output
console = rich.get_console()
