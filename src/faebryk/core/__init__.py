import logging
from enum import StrEnum

from faebryk.libs.util import ConfigFlagEnum

logger = logging.getLogger(__name__)


class LogLevel(StrEnum):
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARN = "WARN"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


log_level = ConfigFlagEnum(LogLevel, "CORE_LOG_LEVEL", LogLevel.INFO)
logger.setLevel(logging.getLevelNamesMapping()[log_level.get()])
