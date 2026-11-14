"""
Experimental pytest plugin for "fix A": one Flutter app process per pytest session,
a brand new Flet server + session per fixture instance.

Load with:  PYTHONPATH=<this dir> pytest -p reuse_plugin ...

The app is built once from `client/integration_test_reuse/reuse_host.dart`.
`FletTestApp.start` / `teardown` are replaced at import time when
`FLET_REUSE_BINARY` is set. The process handle and the control channel hold NO asyncio
object: every command is one blocking HTTP request run with
asyncio.to_thread() from whatever loop the fixture is on (function or module).

Environment:
  FLET_REUSE_BINARY        path to the prebuilt host binary (required)
  FLET_REUSE_SHAPE         loop | multi          (default multi)
  FLET_REUSE_RESET_WINDOW  1 | 0                 (default 1)
  FLET_REUSE_RELEASE_INPUT 1 | 0                 (default 1)
  FLET_REUSE_MAX_SESSIONS  recycle the process after N sessions (0 = never)
  FLET_REUSE_FRESH         1 = one process per fixture instance (this is fix C
                           through the same binary, for comparison)
  FLET_REUSE_RESULTS       jsonl file: one row per session and per screenshot
  FLET_REUSE_LOG_DIR       where host process logs go
"""

import asyncio
import contextlib
import hashlib
import http.client
import inspect
import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

import flet as ft
from flet.testing import flet_test_app as _fta
from flet.testing.tester import Tester
from flet.utils.environment import without_host_python_config
from flet.utils.network import get_free_tcp_port

FTA = _fta.FletTestApp
_P = "_FletTestApp__"

BINARY = os.environ.get("FLET_REUSE_BINARY", "")
SHAPE = os.environ.get("FLET_REUSE_SHAPE", "multi")
RESET_WINDOW = os.environ.get("FLET_REUSE_RESET_WINDOW", "1") == "1"
RELEASE_INPUT = os.environ.get("FLET_REUSE_RELEASE_INPUT", "1") == "1"
MAX_SESSIONS = int(os.environ.get("FLET_REUSE_MAX_SESSIONS", "0"))
FRESH = os.environ.get("FLET_REUSE_FRESH", "0") == "1"
RESULTS = os.environ.get("FLET_REUSE_RESULTS", "")
LOG_DIR = Path(os.environ.get("FLET_REUSE_LOG_DIR", tempfile.gettempdir()))


def _record(row: dict):
    if not RESULTS:
        return
    row["t"] = round(time.time(), 3)
    with open(RESULTS, "a") as f:
        f.write(json.dumps(row) + "\n")


def _nodeid() -> str:
    return os.environ.get("PYTEST_CURRENT_TEST", "?").rsplit(" (", 1)[0]


class Host:
    """One running app process plus its control channel. No asyncio state."""

    _count = 0

    def __init__(self):
        Host._count += 1
        self.idx = Host._count
        self.port = get_free_tcp_port()
        env = without_host_python_config()
        env["FLET_TEST_HOST_PORT"] = str(self.port)
        env["FLET_HOST_SHAPE"] = SHAPE
        env["FLET_HOST_ROOT_FRAMES"] = os.environ.get("FLET_REUSE_ROOT_FRAMES", "1")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.log_path = LOG_DIR / f"host-{os.getpid()}-{self.idx}.log"
        self._log = open(self.log_path, "ab")  # noqa: SIM115
        self.sessions = 0
        self.busy = False
        self.dead = False
        t0 = time.perf_counter()
        self.proc = subprocess.Popen(
            [BINARY], env=env, stdout=self._log, stderr=subprocess.STDOUT
        )
        self._wait_ready(180)
        self.launch_s = time.perf_counter() - t0
        _record(
            {
                "kind": "launch",
                "host": self.idx,
                "pid": self.proc.pid,
                "launch_s": round(self.launch_s, 3),
            }
        )
        print(
            f"\n[reuse] host {self.idx} pid {self.proc.pid} ready in "
            f"{self.launch_s:.2f}s (control port {self.port})"
        )

    def _wait_ready(self, timeout: float):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"host exited early with code {self.proc.returncode}\n"
                    + self.log_tail()
                )
            try:
                self.request("/status", {}, timeout=2)
                return
            except OSError:
                time.sleep(0.05)
        self.kill()
        raise TimeoutError("host control channel did not come up")

    def request(self, path: str, payload: dict, timeout: float = 30) -> dict:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            conn.request(
                "POST",
                path,
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            return json.loads(conn.getresponse().read())
        finally:
            conn.close()

    def alive(self) -> bool:
        return not self.dead and self.proc.poll() is None

    def log_tail(self, n: int = 4000) -> str:
        with contextlib.suppress(OSError):
            data = Path(self.log_path).read_bytes()
            return data[-n:].decode(errors="replace")
        return ""

    def kill(self):
        self.dead = True
        if self.proc.poll() is None:
            self.proc.kill()
            with contextlib.suppress(Exception):
                self.proc.wait(5)

    def shutdown(self) -> "int | None":
        if self.proc.poll() is None and not self.dead:
            with contextlib.suppress(Exception):
                self.request("/exit", {}, timeout=5)
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.kill()
        elif self.proc.poll() is None:
            self.kill()
        self.dead = True
        return self.proc.returncode


class Pool:
    """
    Idle hosts are reused. Two apps alive at the same time (a module-scoped
    fixture plus a function-scoped one) get two processes.
    """

    hosts: "list[Host]" = []
    retired: "list[Host]" = []

    @classmethod
    def acquire(cls) -> Host:
        for h in list(cls.hosts):
            if not h.alive():
                cls.hosts.remove(h)
                cls.retired.append(h)
                print(
                    f"\n[reuse] host {h.idx} is gone "
                    f"(exit code {h.proc.returncode}); starting a new one"
                )
        for h in cls.hosts:
            if not h.busy:
                h.busy = True
                return h
        h = Host()
        h.busy = True
        cls.hosts.append(h)
        return h

    @classmethod
    def release(cls, h: Host, recycle: bool = False):
        h.busy = False
        if (
            recycle
            or FRESH
            or (MAX_SESSIONS and h.sessions >= MAX_SESSIONS)
            or not h.alive()
        ):
            code = h.shutdown()
            if h in cls.hosts:
                cls.hosts.remove(h)
            cls.retired.append(h)
            return code
        return None

    @classmethod
    def shutdown_all(cls):
        codes = []
        for h in list(cls.hosts):
            codes.append((h.idx, h.sessions, h.shutdown()))
            cls.retired.append(h)
        cls.hosts.clear()
        return codes


async def _start(self: FTA):
    ready = asyncio.Event()
    main_error: list = []

    async def main(page: ft.Page):
        try:
            setattr(self, _P + "page", page)
            setattr(self, _P + "tester", Tester())
            page.theme_mode = ft.ThemeMode.LIGHT
            page.update()
            app_main = getattr(self, _P + "flet_app_main")
            if inspect.iscoroutinefunction(app_main):
                await app_main(page)
            elif callable(app_main):
                app_main(page)
            if not getattr(self, _P + "skip_pump_and_settle"):
                await getattr(self, _P + "pump_and_settle_with_timeout")("start")
        except BaseException as e:
            main_error.append(e)
            raise
        finally:
            ready.set()

    if self.test_platform is None:
        self.test_platform = {
            "Windows": "windows",
            "Linux": "linux",
            "Darwin": "macos",
        }.get(platform.system(), "unknown")
    if not self.test_device:
        self.test_device = self.test_platform

    t0 = time.perf_counter()
    port = get_free_tcp_port()
    setattr(self, _P + "tcp_port", port)
    assets_dir = getattr(self, _P + "assets_dir")
    # Keep a reference: an unreferenced task can be garbage collected.
    self._reuse_server_task = asyncio.create_task(
        ft.run_async(main, port=port, assets_dir=str(assets_dir), view=None)
    )
    self._reuse_t_start = time.time()

    host = await asyncio.to_thread(Pool.acquire)
    self._reuse_host = host
    host.sessions += 1
    self._reuse_log_offset = (
        Path(host.log_path).stat().st_size if Path(host.log_path).exists() else 0
    )
    t1 = time.perf_counter()
    try:
        resp = await asyncio.to_thread(
            host.request,
            "/start",
            {
                "url": f"tcp://127.0.0.1:{port}",
                "pid_file": str(
                    Path(tempfile.gettempdir()) / f"flet_app_pid_{port}.txt"
                ),
                "assets_dir": str(assets_dir),
                "settle": os.environ.get("FLET_REUSE_SETTLE", "0") == "1",
            },
            60,
        )
    except Exception as e:
        host.kill()
        raise RuntimeError(
            f"[reuse] host {host.idx} did not answer /start: {e!r}\n" + host.log_tail()
        ) from e
    if not resp.get("ok"):
        host.kill()
        raise RuntimeError(f"[reuse] /start failed: {resp}")
    t2 = time.perf_counter()
    deadline = time.monotonic() + 60
    while not ready.is_set():
        await asyncio.sleep(0.01)
        if not host.alive():
            raise RuntimeError(
                f"[reuse] host {host.idx} exited while starting a session "
                f"(code {host.proc.returncode})\n" + host.log_tail()
            )
        if time.monotonic() > deadline:
            host.kill()
            raise TimeoutError("[reuse] session did not become ready in 60 s")
    if main_error:
        raise main_error[0]
    t3 = time.perf_counter()
    page = self.page
    self._reuse_row = {
        "kind": "session",
        "nodeid": _nodeid(),
        "host": host.idx,
        "pid": host.proc.pid,
        "session": resp.get("session"),
        "acquire_s": round(t1 - t0, 4),
        "start_req_s": round(t2 - t1, 4),
        "ready_wait_s": round(t3 - t2, 4),
        "start_total_s": round(t3 - t0, 4),
        "main_ms": resp.get("main_ms"),
        "mount_ms": resp.get("mount_ms"),
        "page_size": [page.width, page.height],
        "window": [
            page.window.width,
            page.window.height,
            page.window.left,
            page.window.top,
        ],
        "focused": page.window.focused,
        "platform_brightness": str(page.platform_brightness),
    }


async def _teardown(self: FTA):
    host: Host = self._reuse_host
    t0 = time.perf_counter()
    res: dict = {}
    err = None
    try:
        res = await asyncio.to_thread(
            host.request,
            "/end",
            {
                "reset_window": RESET_WINDOW,
                "reset_focus": SHAPE == "loop"
                and os.environ.get("FLET_REUSE_RESET_FOCUS", "1") == "1",
                "release_input": RELEASE_INPUT,
                "reset_mode": os.environ.get("FLET_REUSE_RESET_MODE", "pump100"),
                "reset_when": os.environ.get("FLET_REUSE_RESET_WHEN", "before"),
            },
            30,
        )
    except Exception as e:
        err = e
    task = self._reuse_server_task
    task.cancel()
    with contextlib.suppress(BaseException):
        await asyncio.wait({task}, timeout=2)
    t1 = time.perf_counter()
    row = getattr(self, "_reuse_row", {"kind": "session", "nodeid": _nodeid()})
    row.update(
        {
            "end_s": round(t1 - t0, 4),
            "body_s": round(time.time() - self._reuse_t_start, 3)
            - row.get("start_total_s", 0),
            "unmount_ms": res.get("unmount_ms"),
            "steps_ms": res.get("steps_ms"),
            "rss_mb": round(res.get("rss", 0) / 1048576, 1),
            "window_at_end": res.get("window"),
            "window_repaired": res.get("window_repaired"),
            "exceptions": res.get("exceptions", []),
            "ended_early": res.get("ended_early", False),
            "end_error": repr(err) if err else None,
        }
    )
    if err is not None or not res.get("ok"):
        code = host.proc.poll()
        tail = host.log_tail()
        host.kill()
        Pool.release(host)
        row["host_exit_code"] = code
        _record(row)
        _SESSIONS.append(row)
        raise RuntimeError(
            f"[reuse] host {host.idx} failed at session end "
            f"(error {err!r}, response {res}, exit code {code}). The process is "
            f"recycled.\n{tail}"
        )
    exit_code = Pool.release(host)
    row["host_exit_code"] = exit_code
    _record(row)
    _SESSIONS.append(row)
    print(
        f"\n[reuse] session {row.get('session')} host {host.idx}: "
        f"start {row.get('start_total_s')}s (acquire {row.get('acquire_s')}, "
        f"/start {row.get('start_req_s')}, ready {row.get('ready_wait_s')}), "
        f"alive {row.get('body_s', 0):.2f}s, end {row.get('end_s')}s, "
        f"repaired {row.get('window_repaired')}, rss {row.get('rss_mb')} MB"
    )
    if res.get("exceptions"):
        text = "\n".join(res["exceptions"])
        raise RuntimeError(
            f"Flutter reported an exception during this session "
            f"(host {host.idx}, session {res.get('session')}):\n{text}"
        )
    if FRESH and exit_code not in (0, None):
        raise RuntimeError(f"Flutter process failed with exit code {exit_code}")


_SESSIONS: "list[dict]" = []

_orig_assert_screenshot = FTA.assert_screenshot
_orig_compare = FTA._compare_images_rgb
_current_shot: dict = {}


def _assert_screenshot(self, name, screenshot, similarity_threshold=0):
    _current_shot.clear()
    _current_shot.update(
        {"name": name, "sha1": hashlib.sha1(screenshot).hexdigest()[:16]}
    )
    # The original writes "<dir>_<name>_actual.png" next to the golden when a
    # comparison fails. Keep the repo checkout clean: move it out afterwards.
    test_path = Path(getattr(self, _P + "test_path"))
    gdir = (
        test_path.parent
        / "golden"
        / str(self.test_platform)
        / test_path.stem.removeprefix("test_")
    )
    actual = gdir / f"{gdir.stem}_{name.removeprefix('test_')}_actual.png"
    existed = actual.exists()
    try:
        return _orig_assert_screenshot(self, name, screenshot, similarity_threshold)
    finally:
        _current_shot.clear()
        if not existed and actual.exists():
            dest = LOG_DIR / "actuals"
            dest.mkdir(parents=True, exist_ok=True)
            actual.replace(dest / actual.name)


def _compare(self, img1, img2):
    sim = _orig_compare(self, img1, img2)
    if _current_shot:
        _record(
            {
                "kind": "shot",
                "nodeid": _nodeid(),
                "name": _current_shot["name"],
                "sha1": _current_shot["sha1"],
                "similarity": float(sim),
                "size": list(img2.size),
            }
        )
    return sim


if BINARY:
    FTA.start = _start
    FTA.teardown = _teardown
    FTA.assert_screenshot = _assert_screenshot
    FTA._compare_images_rgb = _compare


def pytest_runtest_logreport(report):
    if report.when == "call" or report.outcome != "passed":
        _record(
            {
                "kind": "result",
                "nodeid": report.nodeid,
                "when": report.when,
                "outcome": report.outcome,
                "duration": round(report.duration, 3),
            }
        )


def pytest_sessionfinish(session, exitstatus):
    codes = Pool.shutdown_all()
    for idx, sessions, code in codes:
        print(f"\n[reuse] host {idx}: {sessions} sessions, exit code {code}")
        _record({"kind": "host_exit", "host": idx, "sessions": sessions, "code": code})
    if not _SESSIONS:
        return

    def total(key):
        return sum(r.get(key) or 0 for r in _SESSIONS)

    rss = [r["rss_mb"] for r in _SESSIONS if r.get("rss_mb")]
    print(
        f"[reuse] summary: sessions {len(_SESSIONS)}, hosts started {Host._count}, "
        f"start {total('start_total_s'):.1f}s "
        f"(acquire {total('acquire_s'):.1f}, /start {total('start_req_s'):.1f}, "
        f"ready {total('ready_wait_s'):.1f}), alive {total('body_s'):.1f}s, "
        f"end {total('end_s'):.1f}s, window repaired "
        f"{sum(bool(r.get('window_repaired')) for r in _SESSIONS)}, "
        f"sessions with exceptions "
        f"{sum(bool(r.get('exceptions')) for r in _SESSIONS)}, "
        f"end errors {sum(bool(r.get('end_error')) for r in _SESSIONS)}"
    )
    if rss:
        print(
            f"[reuse] rss MB: first {rss[0]}, max {max(rss)}, last {rss[-1]}, "
            f"n {len(rss)}"
        )
