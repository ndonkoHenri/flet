import 'package:flet/src/utils/numbers.dart';
import 'package:flutter/material.dart';

import '../models/control.dart';
import 'base_controls.dart';
import 'control_widget.dart';
import 'scroll_notification_control.dart';
import 'scrollable_control.dart';

class SliverListViewControl extends StatefulWidget {
  final Control control;

  const SliverListViewControl({super.key, required this.control});

  @override
  State<SliverListViewControl> createState() => _SliverListViewControlState();
}

class _SliverListViewControlState extends State<SliverListViewControl> {
  late final ScrollController _controller = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    debugPrint("SliverListViewControl build: ${widget.control.id}");

    var spacing = widget.control.getDouble("spacing", 0)!;
    var dividerThickness = widget.control.getDouble("divider_thickness", 0)!;
    var controls = widget.control.children("controls");
    var itemCount = controls.length;

    Widget sliverList = spacing > 0
        ? SliverList.separated(
            itemCount: itemCount,
            itemBuilder: (context, index) {
              return ControlWidget(control: controls[index]);
            },
            separatorBuilder: (context, index) {
              return dividerThickness == 0
                  ? SizedBox(height: spacing)
                  : Divider(height: spacing, thickness: dividerThickness);
            },
          )
        : SliverList.builder(
            itemCount: itemCount,
            itemBuilder: (context, index) {
              return ControlWidget(control: controls[index]);
            },
          );

    Widget child = ScrollableControl(
        control: widget.control,
        scrollDirection: Axis.vertical,
        scrollController: _controller,
        child: sliverList);

    if (widget.control.getBool("on_scroll", false)!) {
      child = ScrollNotificationControl(control: widget.control, child: child);
    }

    return ConstrainedControl(control: widget.control, child: child);
  }
}
