"""Allow running the orchestrator as a module.

Usage:
    python -m tools.orchestrator serve
    python -m tools.orchestrator spawn "prompt"
    python -m tools.orchestrator --help
"""

from .cli.main import main

if __name__ == "__main__":
    main()
