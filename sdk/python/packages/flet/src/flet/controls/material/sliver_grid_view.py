from dataclasses import field
from typing import Any, List, Optional, Union

from flet.controls.adaptive_control import AdaptiveControl
from flet.controls.base_control import control
from flet.controls.constrained_control import ConstrainedControl
from flet.controls.control import Control
from flet.controls.material.sliver import Sliver
from flet.controls.scrollable_control import ScrollableControl
from flet.controls.types import OptionalNumber, Number

__all__ = ["SliverGridView"]


@control("SliverGridView")
class SliverGridView(ConstrainedControl, ScrollableControl, AdaptiveControl, Sliver):
    """
    A sliver that places multiple box children in a linear array along the main axis.

    -----

    Online docs: https://flet.dev/docs/controls/slivergridview
    """

    controls: List[Control] = field(default_factory=list)
    runs_count: int = 1
    max_extent: Optional[int] = None
    spacing: Number = 10.0
    run_spacing: Number = 10.0
    child_aspect_ratio: Number = 1.0
    build_controls_on_demand: bool = True
