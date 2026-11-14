"""
Fixtures for the seeded-failure checks of the macOS integration tests.

Fork only: these tests fail on purpose and are run one by one by
`run_seeds.py`, never as part of the integration test suites.
"""

import asyncio
import os
import re
import signal
import socket
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

import flet.testing as ftt
from flet.controls.context import _context_page, context

os.environ.setdefault("FLET_NO_IMPELLER", "1")

REPO = Path(__file__).resolve().parents[5]
PID_FILE = Path(tempfile.gettempdir()) / "flet_app_pid.txt"
STALE_ADDRESS = "532968632320"


@pytest.fixture
def app_pid():
    """
    Returns a function giving the process ID of the app under test: the
    launched binary, or with `flutter test` the app the tool started, read
    from the PID file the client writes.
    """

    def get(app: ftt.FletTestApp) -> int:
        if os.getenv("FLET_TEST_APP_BINARY"):
            return app._FletTestApp__flutter_process.pid
        return int(PID_FILE.read_text())

    return get


@pytest.fixture
def taken_port():
    """A TCP port on which another listener is already accepting connections."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    yield sock.getsockname()[1]
    sock.close()


@pytest.fixture
def dead_port(monkeypatch):
    """Makes the app under test connect to a port nobody listens on."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    spawn = asyncio.create_subprocess_exec

    async def spawn_with_dead_port(*args, **kwargs):
        args = [
            re.sub(r"(FLET_TEST_APP_URL=.+:)\d+$", rf"\g<1>{port}", str(a))
            for a in args
        ]
        env = dict(kwargs["env"])
        if "FLET_TEST_APP_URL" in env:
            env["FLET_TEST_APP_URL"] = re.sub(
                r":\d+$", f":{port}", env["FLET_TEST_APP_URL"]
            )
        kwargs["env"] = env
        print(f"seed: app pointed at dead port {port}")
        return await spawn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn_with_dead_port)
    return port


@pytest.fixture
def stale_media_kit_files(tmp_path, monkeypatch):
    """
    Points `TMPDIR` at a directory that holds a stale media_kit
    `NativeReferenceHolder` file for every process ID, as a long-lived
    machine ends up with after process IDs wrap.
    """
    stale = tmp_path / "stale"
    stale.mkdir()
    for pid in range(1, 100000):
        (stale / f"com.alexmercerind.media_kit.NativeReferenceHolder.{pid}").write_text(
            STALE_ADDRESS
        )
    monkeypatch.setenv("TMPDIR", str(stale))
    print(f"seed: TMPDIR={stale} with 99999 stale media_kit files")
    return stale


@pytest.fixture
def kill_app_afterwards():
    """Kills the processes a test registers, after the app fixture's teardown."""
    pids: list[int] = []
    yield pids
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"seed: killed leftover app process {pid}")
        except ProcessLookupError:
            pass


@pytest_asyncio.fixture(scope="function")
async def flet_app_function(request):
    """Function-scoped app fixture, as in `integration_tests/conftest.py`."""
    params = dict(getattr(request, "param", {}))
    if "taken_port" in request.fixturenames:
        params["tcp_port"] = request.getfixturevalue("taken_port")
    app = ftt.FletTestApp(
        flutter_app_dir=REPO / "client",
        test_path=request.fspath,
        assets_dir=Path(__file__).resolve().parent.parent
        / "integration_tests"
        / "assets",
        **params,
    )
    await app.start()
    token = _context_page.set(app.page)
    context.reset_auto_update()
    try:
        yield app
    finally:
        _context_page.reset(token)
        await app.teardown()
