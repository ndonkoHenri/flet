from typing import List

from flet.controls.adaptive_control import AdaptiveControl
from flet.controls.base_control import control
from flet.controls.material.sliver import Sliver
from flet.controls.types import Number, ClipBehavior, OptionalNumber, OptionalInt

__all__ = ["SliverScrollView"]


@control("SliverScrollView")
class SliverScrollView(AdaptiveControl, Sliver):
    """
    A scroll view that creates custom scroll effects using slivers.

    -----

    Online docs: https://flet.dev/docs/controls/sliverscrollview
    """

    slivers: List[Sliver]
    clip_behavior: ClipBehavior = ClipBehavior.HARD_EDGE
    reverse: bool = False
    horizontal: bool = False
    shrink_wrap: bool = False
    semantic_child_count: OptionalInt = None
    anchor: Number = 0.0
    primary: bool = False
    cache_extent: OptionalNumber = None
