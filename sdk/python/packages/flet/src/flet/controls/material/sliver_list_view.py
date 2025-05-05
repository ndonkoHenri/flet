from dataclasses import field
from typing import Any, List, Optional, Union

from flet.controls.adaptive_control import AdaptiveControl
from flet.controls.base_control import control
from flet.controls.constrained_control import ConstrainedControl
from flet.controls.control import Control
from flet.controls.material.sliver import Sliver
from flet.controls.scrollable_control import ScrollableControl
from flet.controls.types import OptionalNumber, Number

__all__ = ["SliverListView"]


@control("SliverListView")
class SliverListView(ConstrainedControl, ScrollableControl, AdaptiveControl, Sliver):
    """
    A sliver that places multiple box children in a linear array along the main axis.

    -----

    Online docs: https://flet.dev/docs/controls/sliverlistview
    """

    controls: List[Control] = field(default_factory=list)
    spacing: Number = 0.0
    divider_thickness: Number = 0.0
