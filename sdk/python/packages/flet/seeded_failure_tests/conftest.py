"""
Fixtures for the seeded-failure tests.

These tests fail on purpose, to show that a failure inside the Flutter app
turns the run red and that its exception text reaches the log. They live
outside `integration_tests` so no real suite collects them.
"""

import os
from pathlib import Path

import pytest_asyncio

import flet.testing as ftt
from flet.controls.context import _context_page, context

os.environ.setdefault("FLET_NO_IMPELLER", "1")

_FLET_DIR = Path(__file__).resolve().parent.parent


@pytest_asyncio.fixture(scope="function")
async def flet_app_function(request):
    """
    Function-scoped Flet app, started and torn down like the real suites do.
    """
    flet_app = ftt.FletTestApp(
        flutter_app_dir=(_FLET_DIR / "../../../../client").resolve(),
        test_path=request.fspath,
        assets_dir=_FLET_DIR / "integration_tests" / "assets",
    )
    await flet_app.start()
    token = _context_page.set(flet_app.page)
    context.reset_auto_update()
    try:
        yield flet_app
    finally:
        _context_page.reset(token)
        await flet_app.teardown()
