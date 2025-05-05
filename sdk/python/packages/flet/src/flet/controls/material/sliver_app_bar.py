from enum import Enum
from typing import Any, List, Optional


from flet.controls.base_control import control
from flet.controls.control import OptionalControl, Control
from flet.controls.material.app_bar import AppBar
from flet.controls.material.sliver import Sliver
from flet.controls.padding import OptionalPaddingValue
from flet.controls.types import Number, OptionalNumber, OptionalControlEventCallable

__all__ = ["SliverAppBar", "SliverAppBarType"]


class SliverAppBarType(Enum):
    MEDIUM = "medium"
    LARGE = "large"
    NORMAL = "normal"


@control("SliverAppBar")
class SliverAppBar(AppBar, Sliver):
    """
    A Material Design app bar that integrates with a SliverScrollView.

    -----

    Online docs: https://flet.dev/docs/controls/sliverappbar
    """

    flexible_space: OptionalControl = None
    actions_padding: OptionalPaddingValue = None
    collapsed_height: OptionalNumber = None
    pinned: bool = False
    snap: bool = False
    floating: Optional = False
    stretch: bool = False
    expanded_height: OptionalNumber = None
    force_elevated: bool = False
    toolbar_height: Number = 56.0
    stretch_trigger_offset: Number = 100.0
    type: SliverAppBarType = SliverAppBarType.NORMAL
    on_stretch: OptionalControlEventCallable = None

    def before_update(self):
        super().before_update()
        assert (
            self.stretch_trigger_offset > 0
        ), "stretch_trigger_offset must be greater than 0"
        assert (
            self.floating or not self.snap
        ), "snap can only be True when floating is True"
        assert (
            self.collapsed_height is None
            or self.collapsed_height >= self.toolbar_height
        ), f"collapsed_height ({self.collapsed_height}) must be greater than or equal to toolbar_height ({self.toolbar_height})"
