import 'package:flet/src/controls/control_widget.dart';
import 'package:flet/src/utils/numbers.dart';
import 'package:flutter/material.dart';

import '../models/control.dart';
import 'base_controls.dart';
import 'scroll_notification_control.dart';
import 'scrollable_control.dart';

class SliverGridViewControl extends StatefulWidget {
  final Control control;

  const SliverGridViewControl({super.key, required this.control});

  @override
  State<SliverGridViewControl> createState() => _SliverGridViewControlState();
}

class _SliverGridViewControlState extends State<SliverGridViewControl> {
  late final ScrollController _controller = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    debugPrint("SliverGridViewControl build: ${widget.control.id}");

    var spacing = widget.control.getDouble("spacing", 0)!;
    var controls = widget.control.children("controls");
    var maxExtent = widget.control.getDouble("max_extent");
    var runSpacing = widget.control.getDouble("run_spacing", 10)!;
    var runsCount = widget.control.getInt("runs_count", 1)!;
    var childAspectRatio = widget.control.getDouble("child_apect_ratio", 1)!;
    var buildControlsOnDemand =
        widget.control.getBool("build_controls_on_demand", true)!;

    var gridDelegate = maxExtent == null
        ? SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: runsCount,
            mainAxisSpacing: spacing,
            crossAxisSpacing: runSpacing,
            childAspectRatio: childAspectRatio)
        : SliverGridDelegateWithMaxCrossAxisExtent(
            maxCrossAxisExtent: maxExtent,
            mainAxisSpacing: spacing,
            crossAxisSpacing: runSpacing,
            childAspectRatio: childAspectRatio);

    Widget child = buildControlsOnDemand
        ? SliverGrid.builder(
            itemCount: controls.length,
            gridDelegate: gridDelegate,
            itemBuilder: (context, index) {
              return ControlWidget(control: controls[index]);
            },
          )
        : SliverGrid(
            gridDelegate: gridDelegate,
            delegate: SliverChildBuilderDelegate(
              (context, index) => ControlWidget(control: controls[index]),
              childCount: controls.length,
            ),
          );
    child = ScrollableControl(
        control: widget.control,
        scrollDirection: Axis.vertical,
        scrollController: _controller,
        child: child);

    if (widget.control.getBool("on_scroll", false)!) {
      child = ScrollNotificationControl(control: widget.control, child: child);
    }

    return ConstrainedControl(control: widget.control, child: child);
  }
}
