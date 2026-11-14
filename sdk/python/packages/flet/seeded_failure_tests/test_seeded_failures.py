"""
Tests that provoke a failure inside the Flutter app on purpose.

Expected outcome of the file: `test_ok` passes; the three exception tests
pass their Python assertions and error at teardown (the app exits with code
1); `test_never_settles` fails after the pump timeout and errors at teardown.
"""

import pytest

import flet as ft
import flet.testing as ftt


@pytest.mark.asyncio(loop_scope="function")
async def test_ok(flet_app_function: ftt.FletTestApp):
    """Control case: nothing is wrong."""
    flet_app_function.page.add(ft.Text("hello"))
    await flet_app_function.tester.pump_and_settle()
    assert (await flet_app_function.tester.find_by_text("hello")).count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_render_overflow(flet_app_function: ftt.FletTestApp):
    """A `Row` wider than the window overflows; the Python assertion passes."""
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
    """`Tabs` with a length that does not match its tabs throws while building."""
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
async def test_layout_exception_every_frame(flet_app_function: ftt.FletTestApp):
    """An expanding child in a scrollable `Column` throws at every layout."""
    flet_app_function.page.add(
        ft.Column(
            [ft.Container(expand=True, bgcolor=ft.Colors.RED, height=10)],
            scroll=ft.ScrollMode.AUTO,
        ),
        ft.Text("after"),
    )
    await flet_app_function.tester.pump_and_settle()
    assert (await flet_app_function.tester.find_by_text("after")).count >= 0


@pytest.mark.asyncio(loop_scope="function")
async def test_never_settles(flet_app_function: ftt.FletTestApp):
    """An endless animation keeps `pump_and_settle` from finishing."""
    flet_app_function.page.add(ft.ProgressRing(), ft.Text("spinning"))
    await flet_app_function.tester.pump_and_settle()
