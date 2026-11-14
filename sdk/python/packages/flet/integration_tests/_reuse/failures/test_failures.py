"""
Seeded failures for the reused app process (`reuse_plugin`).

Tests 2, 4 and 6 fail on purpose; every other test has to pass in the same
pytest session. Run in file order.
"""

import asyncio
import os
import signal

import pytest

import flet as ft
import flet.testing as ftt


async def _simple(flet_app: ftt.FletTestApp, text: str):
    flet_app.page.add(ft.Text(text))
    await flet_app.tester.pump_and_settle()
    assert (await flet_app.tester.find_by_text(text)).count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_1_ok_before(flet_app_function):
    await _simple(flet_app_function, "before")


@pytest.mark.asyncio(loop_scope="function")
async def test_2_render_overflow(flet_app_function):
    """The body passes; Flutter reports a RenderFlex overflow during a frame."""
    flet_app_function.page.add(
        ft.Row([ft.Container(width=3000, height=50, bgcolor=ft.Colors.RED)])
    )
    await flet_app_function.tester.pump_and_settle()


@pytest.mark.asyncio(loop_scope="function")
async def test_3_ok_after_overflow(flet_app_function):
    await _simple(flet_app_function, "after overflow")


@pytest.mark.asyncio(loop_scope="function")
async def test_4_pump_and_settle_timeout(flet_app_function):
    """An endless animation: pump_and_settle never settles, Python gives up."""
    flet_app_function.page.add(ft.ProgressRing())
    await flet_app_function.tester.pump_and_settle(timeout=3)


@pytest.mark.asyncio(loop_scope="function")
async def test_5_ok_after_timeout(flet_app_function):
    await _simple(flet_app_function, "after timeout")


@pytest.mark.asyncio(loop_scope="function")
async def test_6_app_process_crash(flet_app_function):
    """SIGKILL the app process in the middle of a test."""
    await _simple(flet_app_function, "about to die")
    os.kill(flet_app_function._reuse_host.proc.pid, signal.SIGKILL)
    await asyncio.sleep(0.5)
    await flet_app_function.tester.pump_and_settle(timeout=3)


@pytest.mark.asyncio(loop_scope="function")
async def test_7_ok_after_crash(flet_app_function):
    await _simple(flet_app_function, "after crash")


@pytest.mark.asyncio(loop_scope="function")
async def test_8_ok_again(flet_app_function):
    await _simple(flet_app_function, "again")
