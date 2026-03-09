"""Central registry of ATO_* environment variable flags."""

from faebryk.libs.util import ConfigFlag, ConfigFlagString

# Build orchestration
ATO_BUILD_WORKER = ConfigFlag(
    "BUILD_WORKER", prefix="ATO_", descr="Worker subprocess flag"
)
ATO_BUILD_ID = ConfigFlagString(
    "BUILD_ID", prefix="ATO_", descr="Build session identifier"
)
ATO_BUILD_HISTORY_DB = ConfigFlagString(
    "BUILD_HISTORY_DB", prefix="ATO_", descr="Build history DB path"
)
ATO_LOG_SOURCE = ConfigFlagString(
    "LOG_SOURCE", prefix="ATO_", descr="Log output source label"
)

# Build options
ATO_TARGET = ConfigFlagString(
    "TARGET", prefix="ATO_", descr="Comma-separated include targets"
)
ATO_EXCLUDE_TARGET = ConfigFlagString(
    "EXCLUDE_TARGET", prefix="ATO_", descr="Comma-separated exclude targets"
)
ATO_FROZEN = ConfigFlag("FROZEN", prefix="ATO_", descr="Frozen rebuild (CI)")
ATO_KEEP_PICKED_PARTS = ConfigFlag(
    "KEEP_PICKED_PARTS", prefix="ATO_", descr="Keep picked parts"
)
ATO_KEEP_NET_NAMES = ConfigFlag("KEEP_NET_NAMES", prefix="ATO_", descr="Keep net names")
ATO_KEEP_DESIGNATORS = ConfigFlag(
    "KEEP_DESIGNATORS", prefix="ATO_", descr="Keep designators"
)
ATO_VERBOSE = ConfigFlag("VERBOSE", prefix="ATO_", descr="Verbose output")
ATO_FORCE_TERMINAL = ConfigFlag(
    "FORCE_TERMINAL", prefix="ATO_", descr="Force ANSI terminal"
)
ATO_SAFE = ConfigFlag("SAFE", prefix="ATO_", descr="Enable faulthandler/core dumps")

# Binary resolution
ATO_BINARY = ConfigFlagString("BINARY", prefix="ATO_", descr="Override ato binary path")
ATO_BINARY_PATH = ConfigFlagString(
    "BINARY_PATH", prefix="ATO_", descr="Alt ato binary path"
)
