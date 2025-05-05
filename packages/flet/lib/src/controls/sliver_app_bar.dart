import 'package:collection/collection.dart';
import 'package:flet/src/extensions/control.dart';
import 'package:flet/src/utils/colors.dart';
import 'package:flet/src/utils/numbers.dart';
import 'package:flutter/material.dart';

import '../models/control.dart';
import '../utils/borders.dart';
import '../utils/edge_insets.dart';
import '../utils/misc.dart';
import '../utils/text.dart';
import '../utils/theme.dart';
import 'base_controls.dart';

enum SliverAppBarMode {
  medium,
  large,
}

class SliverAppBarControl extends StatelessWidget {
  final Control control;

  const SliverAppBarControl({super.key, required this.control});

  @override
  Widget build(BuildContext context) {
    debugPrint("SliverAppBar build: ${control.id}");
    var theme = Theme.of(context);

    var leading = control.buildWidget("leading");
    var title = control.buildWidget("title");
    var flexibleSpace = control.buildWidget("flexible_space");
    var actions = control.buildWidgets("actions");
    var leadingWidth = control.getDouble("leading_width");
    var automaticallyImplyLeading =
        control.getBool("automatically_imply_leading", true)!;
    var centerTitle = control.getBool("center_title", false)!;
    var toolbarHeight = control.getDouble("toolbar_height", 56.0)!;
    var foregroundColor = control.getColor("color", context);
    var backgroundColor = control.getColor("bgcolor", context);
    var elevation = control.getDouble("elevation");
    var systemOverlayStyle =
        theme.extension<SystemUiOverlayStyleTheme>()?.systemUiOverlayStyle;
    var shadowColor = control.getColor("shadow_color", context);
    var surfaceTintColor = control.getColor("surface_tint_color", context);
    var scrolledUnderElevation = control.getDouble("elevation_on_scroll");
    var forceMaterialTransparency =
        control.getBool("force_material_transparency", false)!;
    var primary = control.getBool("primary", true)!;
    var titleSpacing = control.getDouble("title_spacing");
    var excludeHeaderSemantics =
        control.getBool("exclude_header_semantics", false)!;
    var clipBehavior = control.getClipBehavior("clip_behavior");
    var titleTextStyle = control.getTextStyle("title_text_style", theme);
    var shape = control.getShape("shape", theme);
    var toolbarTextStyle = control.getTextStyle("toolbar_text_style", theme);
    var actionsPadding = control.getPadding("actions_padding");
    var collapsedHeight = control.getDouble("collapsed_height");
    var pinned = control.getBool("pinned", false)!;
    var snap = control.getBool("snap", false)!;
    var floating = control.getBool("floating", false)!;
    var stretch = control.getBool("stretch", false)!;
    var expandedHeight = control.getDouble("expanded_height");
    var forceElevated = control.getBool("force_elevated", false)!;
    var stretchTriggerOffset =
        control.getDouble("stretch_trigger_offset", 100.0)!;
    Future<void> onStretchTrigger() async {
      control.triggerEvent("stretch");
    }

    var type = SliverAppBarMode.values.firstWhereOrNull((e) =>
        e.name.toLowerCase() == control.getString("type")?.toLowerCase());

    var appBar = type == SliverAppBarMode.large
        ? SliverAppBar.large(
            leading: leading,
            leadingWidth: leadingWidth,
            automaticallyImplyLeading: automaticallyImplyLeading,
            title: title,
            centerTitle: centerTitle,
            toolbarHeight: toolbarHeight,
            foregroundColor: foregroundColor,
            backgroundColor: backgroundColor,
            elevation: elevation,
            actions: actions,
            systemOverlayStyle: systemOverlayStyle,
            shadowColor: shadowColor,
            surfaceTintColor: surfaceTintColor,
            scrolledUnderElevation: scrolledUnderElevation,
            forceMaterialTransparency: forceMaterialTransparency,
            primary: primary,
            titleSpacing: titleSpacing,
            excludeHeaderSemantics: excludeHeaderSemantics,
            clipBehavior: clipBehavior,
            titleTextStyle: titleTextStyle,
            shape: shape,
            toolbarTextStyle: toolbarTextStyle,
            actionsPadding: actionsPadding,
            collapsedHeight: collapsedHeight,
            pinned: pinned,
            snap: snap,
            floating: floating,
            stretch: stretch,
            expandedHeight: expandedHeight,
            forceElevated: forceElevated,
            stretchTriggerOffset: stretchTriggerOffset,
            flexibleSpace: flexibleSpace,
            onStretchTrigger: onStretchTrigger,
          )
        : type == SliverAppBarMode.medium
            ? SliverAppBar.medium(
                leading: leading,
                leadingWidth: leadingWidth,
                automaticallyImplyLeading: automaticallyImplyLeading,
                title: title,
                centerTitle: centerTitle,
                toolbarHeight: toolbarHeight,
                foregroundColor: foregroundColor,
                backgroundColor: backgroundColor,
                elevation: elevation,
                actions: actions,
                systemOverlayStyle: systemOverlayStyle,
                shadowColor: shadowColor,
                surfaceTintColor: surfaceTintColor,
                scrolledUnderElevation: scrolledUnderElevation,
                forceMaterialTransparency: forceMaterialTransparency,
                primary: primary,
                titleSpacing: titleSpacing,
                excludeHeaderSemantics: excludeHeaderSemantics,
                clipBehavior: clipBehavior,
                titleTextStyle: titleTextStyle,
                shape: shape,
                toolbarTextStyle: toolbarTextStyle,
                actionsPadding: actionsPadding,
                collapsedHeight: collapsedHeight,
                pinned: pinned,
                snap: snap,
                floating: floating,
                stretch: stretch,
                expandedHeight: expandedHeight,
                forceElevated: forceElevated,
                stretchTriggerOffset: stretchTriggerOffset,
                flexibleSpace: flexibleSpace,
                onStretchTrigger: onStretchTrigger,
              )
            : SliverAppBar(
                leading: leading,
                leadingWidth: leadingWidth,
                automaticallyImplyLeading: automaticallyImplyLeading,
                title: title,
                centerTitle: centerTitle,
                toolbarHeight: toolbarHeight,
                foregroundColor: foregroundColor,
                backgroundColor: backgroundColor,
                elevation: elevation,
                actions: actions,
                systemOverlayStyle: systemOverlayStyle,
                shadowColor: shadowColor,
                surfaceTintColor: surfaceTintColor,
                scrolledUnderElevation: scrolledUnderElevation,
                forceMaterialTransparency: forceMaterialTransparency,
                primary: primary,
                titleSpacing: titleSpacing,
                excludeHeaderSemantics: excludeHeaderSemantics,
                clipBehavior: clipBehavior,
                titleTextStyle: titleTextStyle,
                shape: shape,
                toolbarTextStyle: toolbarTextStyle,
                actionsPadding: actionsPadding,
                collapsedHeight: collapsedHeight,
                pinned: pinned,
                snap: snap,
                floating: floating,
                stretch: stretch,
                expandedHeight: expandedHeight,
                forceElevated: forceElevated,
                stretchTriggerOffset: stretchTriggerOffset,
                flexibleSpace: flexibleSpace,
                onStretchTrigger: onStretchTrigger,
              );

    return BaseControl(control: control, child: appBar);
  }
}
