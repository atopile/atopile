"""
Pytest plugin for minimal CI output.

Only prints start/result timestamps per test:
  <timestamp>: <test_name>: Start
  <timestamp>: <test_name>: PASSED/FAILED/SKIPPED/ERROR

All other output is suppressed (captured in junit.xml instead).
"""

import datetime
import sys

# Capture original stderr to write our output there (avoid pytest capture)
_original_stderr = sys.stderr


def pytest_configure(config):
    # Disable default terminal reporter to suppress all other output
    terminal = config.pluginmanager.get_plugin("terminalreporter")
    if terminal:
        config.pluginmanager.unregister(terminal)


def pytest_runtest_logstart(nodeid, location):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _original_stderr.write(f"{ts}: {nodeid}: Start\n")
    _original_stderr.flush()


def pytest_runtest_logreport(report):
    if report.when == "call":
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _original_stderr.write(f"{ts}: {report.nodeid}: {report.outcome.upper()}\n")
        _original_stderr.flush()
    elif report.when == "setup" and report.failed:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _original_stderr.write(f"{ts}: {report.nodeid}: ERROR\n")
        _original_stderr.flush()
