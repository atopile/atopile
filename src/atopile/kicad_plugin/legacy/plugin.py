from .common import log_exceptions, setup_logger


def activate():
    log = setup_logger(__name__)
    log.info("Activating Kicad atopile plugin")

    from .pullgroup import PullGroup

    with log_exceptions():
        PullGroup().register()

    log.info("Kicad atopile plugin loaded")


if __name__ == "__main__":
    activate()
