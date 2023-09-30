import contextlib
import cProfile
import logging
import pstats
import time
from pathlib import Path
from typing import Callable, Optional, TypeVar

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def get_src_dir():
    return Path(__file__).parent.parent


def get_source_project_root():
    return Path(__file__).parent.parent.parent


def is_editable_install():
    return (get_source_project_root() / "pyproject.toml").exists()


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger: logging.Logger, log_level: int = logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ""

    def write(self, buf):
        temp_linebuf: str = self.linebuf + buf
        self.linebuf = ""
        for line in temp_linebuf.splitlines(True):
            # From the io.TextIOWrapper docs:
            #   On output, if newline is None, any '\n' characters written
            #   are translated to the system default line separator.
            # By default sys.stdout.write() expects '\n' newlines and then
            # translates them so this is still cross platform.
            if line[-1] == "\n":
                self.logger.log(self.log_level, line.rstrip())
            else:
                self.linebuf += line

    def flush(self):
        if self.linebuf != "":
            self.logger.log(self.log_level, self.linebuf.rstrip())
        self.linebuf = ""


@contextlib.contextmanager
def profile(
    profile_log: logging.Logger, entries: int = 20, sort_stats="cumtime", skip=False
):
    if skip:
        # skip allows you to include the profiler context in code and switch it easily downstream
        yield
        return

    prof = cProfile.Profile()
    prof.enable()
    start_time = time.time()
    log.info("Running profiler...")
    yield
    log.info(f"Finished profiling. Took {time.time() - start_time} seconds.")
    prof.disable()
    s = StreamToLogger(profile_log, logging.DEBUG)
    stats = pstats.Stats(prof, stream=s).sort_stats(sort_stats)
    stats.print_stats(entries)


# TODO: updating an input? wow... cruddy much?
def update_dict(target: dict, source: dict):
    for k, v in source.items():
        if isinstance(v, dict):
            if k not in target:
                target[k] = {}
            update_dict(target[k], v)
        else:
            target[k] = v


@contextlib.contextmanager
def timed(what_am_i_doing: str):
    start_time = time.time()
    log.info(what_am_i_doing)
    yield
    log.info("%s took %ss", what_am_i_doing, time.time() - start_time)


ShieldToNoneReturn = TypeVar("ShieldToNoneReturn")  # Return type
ShieldToNoneAargs = TypeVar(
    "ShieldToNoneAargs"
)  # Argument type (can be a tuple if multiple argument types)
ShieldToNoneKwargs = TypeVar(
    "ShieldToNoneKwargs"
)  # Keyword argument type (can be a dict if multiple kwarg types)


def shield_to_none(
    exception: BaseException,
    func: Callable[[ShieldToNoneAargs, ShieldToNoneKwargs], ShieldToNoneReturn],
    *args: ShieldToNoneAargs,
    **kwargs: ShieldToNoneKwargs,
) -> Optional[ShieldToNoneReturn]:
    """
    Shield the function from the exception, returning None if it's raised.
    """
    try:
        return func(*args, **kwargs)
    except exception:
        return None
