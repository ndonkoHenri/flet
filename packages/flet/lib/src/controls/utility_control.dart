import 'dart:convert';

import 'package:flet/flet.dart';
import 'package:flutter/material.dart';

import '../flet_control_backend.dart';
import '../models/control.dart';
import '../utils/alignment.dart';
import '../utils/animations.dart';
import '../utils/borders.dart';
import '../utils/box.dart';
import '../utils/edge_insets.dart';
import '../utils/gradient.dart';
import '../utils/images.dart';
import '../utils/launch_url.dart';
import '../utils/others.dart';
import 'create_control.dart';
import 'flet_store_mixin.dart';

class UtilityControl extends StatelessWidget with FletStoreMixin {
  final Control? parent;
  final Control control;
  final List<Control> children;
  final bool parentDisabled;
  final bool? parentAdaptive;
  final FletControlBackend backend;

  const UtilityControl(
      {super.key,
      this.parent,
      required this.control,
      required this.children,
      required this.parentDisabled,
      required this.parentAdaptive,
      required this.backend});

  @override
  Widget build(BuildContext context) {
    debugPrint("UtilityControl build: ${control.id}");
    bool disabled = control.isDisabled || parentDisabled;
    bool? adaptive = control.attrBool("adaptive") ?? parentAdaptive;
    var contentCtrls = children.where((c) => c.isVisible);
    bool ignoreInteractions = control.attrBool("ignoreInteractions", false)!;
    var colorFilter =
        parseColorFilter(control, "colorFilter", Theme.of(context));
    var blur = parseBlur(control, "blur");

    Widget? result;
    if (contentCtrls.isNotEmpty) {
      result = createControl(control, contentCtrls.first.id, disabled,
          parentAdaptive: adaptive);
    } else {
      return ErrorControl(
          "UtilityControl must have a visible content Control.");
    }
    var padding = parseEdgeInsets(control, "padding");
    var alignment = parseAlignment(control, "alignment");
    var sizeConstraints = parseBoxConstraints(control, "sizeConstraints");

    return withPageArgs((context, pageArgs) {

      if (colorFilter != null) {
        result = ColorFiltered(colorFilter: colorFilter, child: result);
      }

      if (ignoreInteractions) {
        result = IgnorePointer(child: result);
      }
      if (padding != null) {
        result = Padding(padding: padding, child: result);
      }

      if (sizeConstraints != null) {
        result = ConstrainedBox(constraints: sizeConstraints, child: result);
      }
      if (alignment != null) {
        result = Align(alignment: alignment, child: result);
      }

      return constrainedControl(context, result!, parent, control);
    });
  }
}
