"""
Seeded failures: each test provokes one way an integration test can go wrong.

Fork only. `run_seeds.py` runs them one at a time and compares the outcome
with what is expected in each launch mode.
"""

import asyncio
import os
import signal

import pytest

import flet as ft
import flet.testing as ftt


def _spinner_main(page: ft.Page):
    page.add(ft.ProgressRing(), ft.Text("spinning from main"))


def _raising_main(page: ft.Page):
    raise ValueError("seeded error in the app's main")


@pytest.mark.asyncio(loop_scope="function")
async def test_ok(flet_app_function: ftt.FletTestApp):
    """Control: nothing is wrong."""
    flet_app_function.page.add(ft.Text("hello"))
    await flet_app_function.tester.pump_and_settle()
    assert (await flet_app_function.tester.find_by_text("hello")).count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_render_overflow(flet_app_function: ftt.FletTestApp):
    """A row wider than the window overflows; the Python asserts pass."""
    flet_app_function.page.add(
        ft.Row(
            [
                ft.Container(width=3000, height=40, bgcolor=ft.Colors.RED),
                ft.Text("overflow"),
            ]
        )
    )
    await flet_app_function.tester.pump_and_settle()
    assert (await flet_app_function.tester.find_by_text("overflow")).count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_control_exception(flet_app_function: ftt.FletTestApp):
    """A control throws while building: `Tabs` of length 2 with 3 tabs."""
    flet_app_function.page.add(
        ft.Tabs(
            length=2,
            content=ft.Column(
                [
                    ft.TabBar(
                        tabs=[ft.Tab(label="a"), ft.Tab(label="b"), ft.Tab(label="c")]
                    ),
                    ft.TabBarView(controls=[ft.Text("1"), ft.Text("2")], height=50),
                ]
            ),
        ),
        ft.Text("after"),
    )
    await flet_app_function.tester.pump_and_settle()
    assert (await flet_app_function.tester.find_by_text("after")).count >= 0


@pytest.mark.asyncio(loop_scope="function")
async def test_never_settles(flet_app_function: ftt.FletTestApp):
    """An endless animation: `pump_and_settle` cannot complete."""
    flet_app_function.page.add(ft.ProgressRing(), ft.Text("spinning"))
    await flet_app_function.tester.pump_and_settle()


@pytest.mark.parametrize(
    "flet_app_function", [{"flet_app_main": _spinner_main}], indirect=True
)
@pytest.mark.asyncio(loop_scope="function")
async def test_never_settles_at_start(flet_app_function: ftt.FletTestApp):
    """The app's own `main` starts an endless animation, so start cannot settle."""
    assert (await flet_app_function.tester.find_by_text("spinning from main")).count


@pytest.mark.parametrize(
    "flet_app_function", [{"flet_app_main": _raising_main}], indirect=True
)
@pytest.mark.asyncio(loop_scope="function")
async def test_main_raises(flet_app_function: ftt.FletTestApp):
    """The app's own `main` raises."""
    await flet_app_function.tester.pump_and_settle()


@pytest.mark.asyncio(loop_scope="function")
async def test_app_killed_mid_test(app_pid, flet_app_function: ftt.FletTestApp):
    """SIGKILL of the app while the test runs; the tester is used afterwards."""
    flet_app_function.page.add(ft.Text("alive"))
    await flet_app_function.tester.pump_and_settle()
    os.kill(app_pid(flet_app_function), signal.SIGKILL)
    await asyncio.sleep(1)
    flet_app_function.page.add(ft.Text("after kill"))
    await flet_app_function.tester.pump_and_settle()
    assert (await flet_app_function.tester.find_by_text("after kill")).count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_app_crashes_mid_test(app_pid, flet_app_function: ftt.FletTestApp):
    """SIGSEGV of the app (a native crash); no tester call afterwards."""
    flet_app_function.page.add(ft.Text("alive"))
    await flet_app_function.tester.pump_and_settle()
    os.kill(app_pid(flet_app_function), signal.SIGSEGV)
    await asyncio.sleep(1)


@pytest.mark.asyncio(loop_scope="function")
async def test_app_frozen_mid_test(
    app_pid, kill_app_afterwards, flet_app_function: ftt.FletTestApp
):
    """SIGSTOP of the app: it stays alive but answers nothing, teardown included."""
    flet_app_function.page.add(ft.Text("alive"))
    await flet_app_function.tester.pump_and_settle()
    pid = app_pid(flet_app_function)
    kill_app_afterwards.append(pid)
    os.kill(pid, signal.SIGSTOP)
    await asyncio.sleep(1)


@pytest.mark.asyncio(loop_scope="function")
async def test_app_frozen_then_tester_call(
    app_pid, kill_app_afterwards, flet_app_function: ftt.FletTestApp
):
    """SIGSTOP of the app, then a tester call that has no timeout of its own."""
    flet_app_function.page.add(ft.Text("alive"))
    await flet_app_function.tester.pump_and_settle()
    pid = app_pid(flet_app_function)
    kill_app_afterwards.append(pid)
    os.kill(pid, signal.SIGSTOP)
    assert (await flet_app_function.tester.find_by_text("alive")).count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_app_quits_mid_test(flet_app_function: ftt.FletTestApp):
    """The app closes its window and exits with code 0 before the test ends."""
    flet_app_function.page.add(ft.Text("alive"))
    await flet_app_function.tester.pump_and_settle()
    try:
        await asyncio.wait_for(flet_app_function.page.window.destroy(), timeout=5)
    except Exception as e:
        print(f"seed: window.destroy() ended with {type(e).__name__}: {e}")
    await asyncio.sleep(2)


@pytest.mark.asyncio(loop_scope="function")
async def test_never_connects(dead_port, flet_app_function: ftt.FletTestApp):
    """The app is pointed at a port nobody listens on."""
    await flet_app_function.tester.pump_and_settle()


@pytest.mark.asyncio(loop_scope="function")
async def test_port_taken(taken_port, flet_app_function: ftt.FletTestApp):
    """Another listener holds the port the Flet server is told to use."""
    await flet_app_function.tester.pump_and_settle()


@pytest.mark.asyncio(loop_scope="function")
async def test_app_start_fails(flet_app_function: ftt.FletTestApp):
    """
    The configured binary cannot start a test app: `run_seeds.py` sets
    `FLET_TEST_APP_BINARY` to a missing path or to `/usr/bin/false`.
    """
    await flet_app_function.tester.pump_and_settle()


@pytest.mark.asyncio(loop_scope="function")
async def test_stale_media_kit_files(
    stale_media_kit_files, flet_app_function: ftt.FletTestApp
):
    """Control: stale per-process media_kit files in the temporary directory."""
    flet_app_function.page.add(ft.Text("hello"))
    await flet_app_function.tester.pump_and_settle()
    assert (await flet_app_function.tester.find_by_text("hello")).count == 1
