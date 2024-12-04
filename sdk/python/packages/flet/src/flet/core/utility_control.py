import json
import warnings
from typing import Any, List, Optional, Tuple, Union

from flet.core.adaptive_control import AdaptiveControl
from flet.core.alignment import Alignment
from flet.core.animation import AnimationValue
from flet.core.badge import BadgeValue
from flet.core.blur import Blur
from flet.core.border import Border
from flet.core.box import (
    BoxConstraints,
    BoxDecoration,
    BoxShadow,
    BoxShape,
    ColorFilter,
    DecorationImage,
)
from flet.core.constrained_control import ConstrainedControl
from flet.core.control import Control, OptionalNumber
from flet.core.control_event import ControlEvent
from flet.core.event_handler import EventHandler
from flet.core.gradients import Gradient
from flet.core.ref import Ref
from flet.core.theme import Theme
from flet.core.tooltip import TooltipValue
from flet.core.types import (
    BlendMode,
    BorderRadiusValue,
    ClipBehavior,
    ColorEnums,
    ColorValue,
    ImageFit,
    ImageRepeat,
    MarginValue,
    Number,
    OffsetValue,
    OptionalControlEventCallable,
    OptionalEventCallable,
    PaddingValue,
    ResponsiveNumber,
    RotateValue,
    ScaleValue,
    ThemeMode,
    UrlTarget,
)


class UtilityControl(ConstrainedControl, AdaptiveControl):
    """

    -----

    Online docs: https://flet.dev/docs/controls/utilitycontrol
    """

    def __init__(
        self,
        content: Optional[Control] = None,
        padding: PaddingValue = None,
        margin: MarginValue = None,
        alignment: Optional[Alignment] = None,
        bgcolor: Optional[ColorValue] = None,
        gradient: Optional[Gradient] = None,
        blend_mode: Optional[BlendMode] = None,
        border: Optional[Border] = None,
        border_radius: BorderRadiusValue = None,
        shape: Optional[BoxShape] = None,
        clip_behavior: Optional[ClipBehavior] = None,
        animate: Optional[AnimationValue] = None,
        blur: Union[None, Number, Tuple[Number, Number], Blur] = None,
        shadow: Union[None, BoxShadow, List[BoxShadow]] = None,
        theme: Optional[Theme] = None,
        theme_mode: Optional[ThemeMode] = None,
        color_filter: Optional[ColorFilter] = None,
        size_constraints: Optional[BoxConstraints] = None,
        ignore_interactions: Optional[bool] = None,
        background_decoration: Optional[BoxDecoration] = None,
        foreground_decoration: Optional[BoxDecoration] = None,
        #
        # ConstrainedControl and AdaptiveControl
        #
        ref: Optional[Ref] = None,
        key: Optional[str] = None,
        width: OptionalNumber = None,
        height: OptionalNumber = None,
        left: OptionalNumber = None,
        top: OptionalNumber = None,
        right: OptionalNumber = None,
        bottom: OptionalNumber = None,
        expand: Union[None, bool, int] = None,
        expand_loose: Optional[bool] = None,
        col: Optional[ResponsiveNumber] = None,
        opacity: OptionalNumber = None,
        rotate: RotateValue = None,
        scale: ScaleValue = None,
        offset: OffsetValue = None,
        aspect_ratio: OptionalNumber = None,
        animate_opacity: Optional[AnimationValue] = None,
        animate_size: Optional[AnimationValue] = None,
        animate_position: Optional[AnimationValue] = None,
        animate_rotation: Optional[AnimationValue] = None,
        animate_scale: Optional[AnimationValue] = None,
        animate_offset: Optional[AnimationValue] = None,
        on_animation_end: OptionalControlEventCallable = None,
        tooltip: TooltipValue = None,
        badge: Optional[BadgeValue] = None,
        visible: Optional[bool] = None,
        disabled: Optional[bool] = None,
        data: Any = None,
        rtl: Optional[bool] = None,
        adaptive: Optional[bool] = None,
    ):
        ConstrainedControl.__init__(
            self,
            ref=ref,
            key=key,
            width=width,
            height=height,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            expand=expand,
            expand_loose=expand_loose,
            col=col,
            opacity=opacity,
            rotate=rotate,
            scale=scale,
            offset=offset,
            aspect_ratio=aspect_ratio,
            animate_opacity=animate_opacity,
            animate_size=animate_size,
            animate_position=animate_position,
            animate_rotation=animate_rotation,
            animate_scale=animate_scale,
            animate_offset=animate_offset,
            on_animation_end=on_animation_end,
            tooltip=tooltip,
            badge=badge,
            visible=visible,
            disabled=disabled,
            data=data,
            rtl=rtl,
        )

        AdaptiveControl.__init__(self, adaptive=adaptive)

        self.content = content
        self.padding = padding
        self.margin = margin
        self.alignment = alignment
        self.bgcolor = bgcolor
        self.gradient = gradient
        self.blend_mode = blend_mode
        self.border = border
        self.border_radius = border_radius
        self.shape = shape
        self.clip_behavior = clip_behavior
        self.animate = animate
        self.blur = blur
        self.shadow = shadow
        self.theme = theme
        self.theme_mode = theme_mode
        self.color_filter = color_filter
        self.ignore_interactions = ignore_interactions
        self.foreground_decoration = foreground_decoration
        self.size_constraints = size_constraints

    def _get_control_name(self):
        return "utility"

    def before_update(self):
        super().before_update()
        self._set_attr_json("padding", self.__padding)
        self._set_attr_json("alignment", self.__alignment)
        self._set_attr_json("blur", self.__blur)
        self._set_attr_json("shadow", self.__shadow if self.__shadow else None)
        self._set_attr_json("theme", self.__theme)
        self._set_attr_json("colorFilter", self.__color_filter)
        self._set_attr_json("foregroundDecoration", self.__foreground_decoration)
        self._set_attr_json("sizeConstraints", self.__size_constraints)

    def _get_children(self):
        children = []
        if self.__content is not None:
            self.__content._set_attr_internal("n", "content")
            children.append(self.__content)
        return children

    # alignment
    @property
    def alignment(self) -> Optional[Alignment]:
        """:obj:`Alignment`, optional: Align the child control within the container.

        Alignment is an instance of `alignment.Alignment` class object with `x` and `y` properties
        representing the distance from the center of a rectangle.
        """
        return self.__alignment

    @alignment.setter
    def alignment(self, value: Optional[Alignment]):
        self.__alignment = value

    # padding
    @property
    def padding(self) -> PaddingValue:
        return self.__padding

    @padding.setter
    def padding(self, value: PaddingValue):
        self.__padding = value

    # foreground_decoration
    @property
    def foreground_decoration(self) -> Optional[BoxDecoration]:
        return self.__foreground_decoration

    @foreground_decoration.setter
    def foreground_decoration(self, value: Optional[BoxDecoration]):
        self.__foreground_decoration = value

    # margin
    @property
    def margin(self) -> MarginValue:
        return self.__margin

    @margin.setter
    def margin(self, value: MarginValue):
        self.__margin = value

    # size_constraints
    @property
    def size_constraints(self) -> Optional[BoxConstraints]:
        return self.__size_constraints

    @size_constraints.setter
    def size_constraints(self, value: Optional[BoxConstraints]):
        self.__size_constraints = value

    # blend_mode
    @property
    def blend_mode(self) -> Optional[BlendMode]:
        return self.__blend_mode

    @blend_mode.setter
    def blend_mode(self, value: Optional[BlendMode]):
        self.__blend_mode = value
        self._set_enum_attr("blendMode", value, BlendMode)

    # blur
    @property
    def blur(self) -> Union[None, Number, Tuple[Number, Number], Blur]:
        return self.__blur

    @blur.setter
    def blur(
        self,
        value: Union[None, Number, Tuple[Number, Number], Blur],
    ):
        self.__blur = value

    # shadow
    @property
    def shadow(self) -> Union[None, BoxShadow, List[BoxShadow]]:
        return self.__shadow

    @shadow.setter
    def shadow(self, value: Union[None, BoxShadow, List[BoxShadow]]):
        self.__shadow = value if value is not None else []

    # color_filter
    @property
    def color_filter(self) -> Optional[ColorFilter]:
        return self.__color_filter

    @color_filter.setter
    def color_filter(self, value: Optional[ColorFilter]):
        self.__color_filter = value

    # border
    @property
    def border(self) -> Optional[Border]:
        return self.__border

    @border.setter
    def border(self, value: Optional[Border]):
        self.__border = value

    # border_radius
    @property
    def border_radius(self) -> BorderRadiusValue:
        return self.__border_radius

    @border_radius.setter
    def border_radius(self, value: BorderRadiusValue):
        self.__border_radius = value

    # ignore_interactions
    @property
    def ignore_interactions(self) -> Optional[bool]:
        return self._get_attr("ignoreInteractions", data_type="bool", def_value=False)

    @ignore_interactions.setter
    def ignore_interactions(self, value: Optional[str]):
        self._set_attr("ignoreInteractions", value)

    # content
    @property
    def content(self) -> Optional[Control]:
        return self.__content

    @content.setter
    def content(self, value: Optional[Control]):
        self.__content = value

    # shape
    @property
    def shape(self) -> Optional[BoxShape]:
        return self.__shape

    @shape.setter
    def shape(self, value: Optional[BoxShape]):
        self.__shape = value
        self._set_enum_attr("shape", value, BoxShape)

    # clip_behavior
    @property
    def clip_behavior(self) -> Optional[ClipBehavior]:
        return self.__clip_behavior

    @clip_behavior.setter
    def clip_behavior(self, value: Optional[ClipBehavior]):
        self.__clip_behavior = value
        self._set_enum_attr("clipBehavior", value, ClipBehavior)

    # animate
    @property
    def animate(self) -> Optional[AnimationValue]:
        return self.__animate

    @animate.setter
    def animate(self, value: Optional[AnimationValue]):
        self.__animate = value

    # url
    @property
    def url(self) -> Optional[str]:
        return self._get_attr("url")

    @url.setter
    def url(self, value: Optional[str]):
        self._set_attr("url", value)

    # url_target
    @property
    def url_target(self) -> Optional[UrlTarget]:
        return self.__url_target

    @url_target.setter
    def url_target(self, value: Optional[UrlTarget]):
        self.__url_target = value
        self._set_enum_attr("urlTarget", value, UrlTarget)

    # theme
    @property
    def theme(self) -> Optional[Theme]:
        return self.__theme

    @theme.setter
    def theme(self, value: Optional[Theme]):
        self.__theme = value

    # theme_mode
    @property
    def theme_mode(self) -> Optional[ThemeMode]:
        return self.__theme_mode

    @theme_mode.setter
    def theme_mode(self, value: Optional[ThemeMode]):
        self.__theme_mode = value
        self._set_enum_attr("themeMode", value, ThemeMode)
