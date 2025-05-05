from flet.controls.base_control import control
from flet.controls.core.safe_area import SafeArea
from flet.controls.material.sliver import Sliver

__all__ = ["SliverSafeArea"]


@control("SliverSafeArea")
class SliverSafeArea(SafeArea, Sliver):
    """
    A sliver that insets another sliver by sufficient padding to avoid intrusions by the operating system.

    -----

    Online docs: https://flet.dev/docs/controls/sliversafearea
    """

    pass
