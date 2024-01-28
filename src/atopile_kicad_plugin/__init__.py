from pathlib import Path


if Path("~/.atopile/debug").expanduser().exists():
    from .common import log
    log.info("Starting debug session")
    try:
        import debugpy
        log.debug("Imported debugpy")
        debugpy.listen(("localhost", 5678))
        log.debug("Started server")
        debugpy.wait_for_client()
        log.debug("Waiting for client")
    except ImportError:
        log.error("debugpy not installed")


from . import pullgroup, pushgroup
