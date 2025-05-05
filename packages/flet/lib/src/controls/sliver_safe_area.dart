import 'package:flet/src/extensions/control.dart';
import 'package:flet/src/utils/numbers.dart';
import 'package:flutter/material.dart';

import '../models/control.dart';
import '../utils/edge_insets.dart';
import '../widgets/error.dart';
import 'base_controls.dart';

class SliverSafeAreaControl extends StatelessWidget {
  final Control control;

  const SliverSafeAreaControl({super.key, required this.control});

  @override
  Widget build(BuildContext context) {
    debugPrint("SliverSafeArea build: ${control.id}");

    var safeArea = SliverSafeArea(
        left: control.getBool("avoid_intrusions_left", true)!,
        top: control.getBool("avoid_intrusions_top", true)!,
        right: control.getBool("avoid_intrusions_right", true)!,
        bottom: control.getBool("avoid_intrusions_bottom", true)!,
        minimum: control.getPadding("minimum_padding", EdgeInsets.zero)!,
        sliver: control.buildWidget("content") ??
            const ErrorControl(
                "SliverSafeArea.content must be provided and visible"));

    return ConstrainedControl(control: control, child: safeArea);
  }
}
