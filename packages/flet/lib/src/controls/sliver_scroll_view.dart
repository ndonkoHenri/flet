import 'package:flet/src/extensions/control.dart';
import 'package:flet/src/utils/numbers.dart';
import 'package:flutter/material.dart';

import '../models/control.dart';
import '../utils/misc.dart';
import 'base_controls.dart';
import 'scroll_notification_control.dart';
import 'scrollable_control.dart';

class SliverScrollViewControl extends StatefulWidget {
  final Control control;

  const SliverScrollViewControl({super.key, required this.control});

  @override
  State<SliverScrollViewControl> createState() =>
      _SliverScrollViewControlState();
}

class _SliverScrollViewControlState extends State<SliverScrollViewControl> {
  late final ScrollController _controller = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    debugPrint("SliverScrollView build: ${widget.control.id}");

    var ctrls = widget.control.buildWidgets("controls");
    var scrollDirection = widget.control.getBool("horizontal", false)!
        ? Axis.horizontal
        : Axis.vertical;

    Widget scrollView = CustomScrollView(
      clipBehavior:
          widget.control.getClipBehavior("clip_behavior", Clip.hardEdge)!,
      reverse: widget.control.getBool("reverse", false)!,
      scrollDirection: scrollDirection,
      shrinkWrap: widget.control.getBool("shrink_wrap", false)!,
      semanticChildCount:
          widget.control.getInt("semantic_child_count", ctrls.length),
      anchor: widget.control.getDouble("anchor", 0.0)!,
      primary: widget.control.getBool("primary"),
      cacheExtent: widget.control.getDouble("cache_extent"),
      slivers: ctrls,
    );
    Widget child = ScrollableControl(
        control: widget.control,
        scrollDirection: scrollDirection,
        scrollController: _controller,
        child: scrollView);

    if (widget.control.getBool("on_scroll", false)!) {
      child = ScrollNotificationControl(control: widget.control, child: child);
    }

    return BaseControl(control: widget.control, child: child);
  }
}
