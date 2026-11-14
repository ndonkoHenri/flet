"""
Fork-only pytest plugin for the parallel-instances experiment.

Each pytest process that runs tests (an xdist worker, or the main process when
xdist is off) writes one time-stamped log file `$PAR_LOG_DIR/<worker>.log` with:

- every line `FletTestApp` prints (launch and teardown markers, similarity
  lines and, with `FLET_TEST_VERBOSE=1`, the output of the app under test);
- every `INFO` log record (for example "App session started");
- one `START` line per test and one `REPORT` line per test phase with its
  outcome and duration, followed by the failure text when a phase fails.

xdist workers have no terminal: without this file their output would only be
visible, without timestamps, for tests that fail.

With `PAR_CASCADE=1` every app window is moved to a per-worker position right
after the app has started, so that windows of different workers do not sit
exactly on top of each other.
"""

import datetime
import logging
import os
from pathlib import Path

_log_file = None
_worker = "main"

# Window origins per worker index for `PAR_CASCADE=1`, on a 1024x768 display
# with 800x632 windows.
_CASCADE = [(0, 25), (224, 136), (112, 80)]


def _write(text) -> None:
    if _log_file is None:
        return
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    for line in str(text).splitlines() or [""]:
        _log_file.write(f"{ts} [{_worker}] {line}\n")
    _log_file.flush()


class _FileHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _write(f"{record.levelname} {record.name}: {record.getMessage()}")
        except Exception:
            pass


def pytest_configure(config):
    global _log_file, _worker
    log_dir = os.environ.get("PAR_LOG_DIR")
    if not log_dir:
        return
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if worker is None and getattr(config.option, "numprocesses", None):
        # xdist controller: it runs no tests.
        return
    _worker = worker or "main"
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    _log_file = open(  # noqa: SIM115
        Path(log_dir) / f"{_worker}.log", "a", encoding="utf-8", errors="replace"
    )

    import flet.testing.flet_test_app as fta

    original_print = fta._print

    def _print(*args, **kwargs):
        _write(" ".join(str(a) for a in args))
        original_print(*args, **kwargs)

    fta._print = _print

    handler = _FileHandler(level=logging.INFO)
    logging.getLogger().addHandler(handler)

    if os.environ.get("PAR_CASCADE") == "1":
        index = int(_worker[2:]) if _worker.startswith("gw") else 0
        left, top = _CASCADE[index % len(_CASCADE)]
        original_start = fta.FletTestApp.start

        async def start(self):
            await original_start(self)
            self.page.window.left = left
            self.page.window.top = top
            self.page.update()
            await self.tester.pump_and_settle()
            _write(f"Window moved to left={left} top={top}")

        fta.FletTestApp.start = start

    _write(f"worker log started, pid {os.getpid()}")


def pytest_runtest_logstart(nodeid, location):
    _write(f"START {nodeid}")


def pytest_runtest_logreport(report):
    if _log_file is None:
        return
    _write(
        f"REPORT {report.nodeid} {report.when} {report.outcome} "
        f"{report.duration:.3f}"
    )
    if report.failed:
        _write(f"FAILURE {report.nodeid} {report.when}\n{report.longreprtext}")


def pytest_unconfigure(config):
    global _log_file
    if _log_file is not None:
        _write("worker log closed")
        _log_file.close()
        _log_file = None
