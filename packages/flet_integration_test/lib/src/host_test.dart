// ignore_for_file: depend_on_referenced_packages

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:flet/flet.dart';
import 'flutter_tester.dart';

/// Runs an integration test in "host" mode: the Flet app under test runs in a
/// separate Python (pytest) process which also acts as the Flet server, and the
/// Flutter app connects back to it over a single transport (TCP/HTTP/UDS). The
/// [Tester] rides that same connection.
///
/// This is the mechanism used by the Flet dev "client" shell and the Flet
/// team's white-box tests. For testing an app built with `flet build` (embedded
/// Python over dart_bridge), use `runFletDeviceTest` instead.
///
/// [appMain] is the host app's `main(args)` entry point. [assignTester] is
/// called with the constructed [Tester] before `appMain` runs so the host can
/// wire it into its `FletApp(tester: ...)`.
///
/// The app URL, PID file path and assets directory come from the
/// `FLET_TEST_APP_URL`, `FLET_TEST_PID_FILE_PATH` and `FLET_TEST_ASSETS_DIR`
/// `--dart-define`s that `flutter test` passes. An app built once with this
/// test as its entry point and launched directly, with no `flutter` tool
/// attached, reads them from environment variables of the same names and
/// ends the process when the test completes: exit code 0 if it passed, 1 if
/// it failed.
///
/// Experiment switches, read from the environment at run time so one build
/// serves every variant:
///
/// * `FLET_TEST_EXP_STARTUP`: `fixed` (default) sleeps 500 ms and pumps for
///   1 s after calling [appMain]; `await-main` awaits the future [appMain]
///   returns; `first-widget` pumps frames until the app's [FletApp] is in the
///   widget tree.
/// * `FLET_TEST_EXP_EXIT`, direct launch only: `delay` (default) waits 2 s
///   before the process ends; `immediate` ends it at once and makes
///   `debugPrint` synchronous so no output is queued at that moment.
void runFletHostTest({
  required FutureOr<void> Function(List<String>) appMain,
  required void Function(Tester) assignTester,
}) {
  var binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  final stopwatch = Stopwatch()..start();

  final launchedDirectly =
      const String.fromEnvironment("FLET_TEST_APP_URL") == "" &&
          (Platform.environment["FLET_TEST_APP_URL"] ?? "") != "";
  final startup = Platform.environment["FLET_TEST_EXP_STARTUP"] ?? "fixed";
  final exitMode = launchedDirectly
      ? Platform.environment["FLET_TEST_EXP_EXIT"] ?? "delay"
      : "delay";
  if (!const ["fixed", "await-main", "first-widget"].contains(startup) ||
      !const ["delay", "immediate"].contains(exitMode)) {
    throw ArgumentError("Unknown FLET_TEST_EXP_STARTUP '$startup' or "
        "FLET_TEST_EXP_EXIT '$exitMode'");
  }
  if (exitMode == "immediate") {
    // The live test binding throttles debugPrint (12 KB bursts, then a 1 s
    // pause), so its queue can still hold the tail of the output when the
    // process ends.
    debugPrint = debugPrintSynchronously;
  }
  debugPrint("Flet host test: startup=$startup exit=$exitMode "
      "launchedDirectly=$launchedDirectly");

  // With the integration_test binding `flutter test` prints only
  // "Test failed. See exception logs above." without ever printing the
  // exception that failed the test (e.g. a render overflow reported during a
  // frame). Log it here so the failure reason is visible in the test process
  // output.
  final prevReportTestException = reportTestException;
  reportTestException = (details, testDescription) {
    debugPrint("Test exception ($testDescription): "
        "${details.exceptionAsString()}\n${details.stack ?? ''}");
    prevReportTestException(details, testDescription);
  };
  debugPrint("Flet host test: exception reporter installed");

  if (launchedDirectly) {
    binding.allTestsPassed.future.then((passed) {
      // Printed last: its presence in the log shows nothing was still queued.
      debugPrint("Flet host test: exiting, passed=$passed, at "
          "${stopwatch.elapsedMilliseconds} ms");
      exit(passed ? 0 : 1);
    });
  }

  if (exitMode == "delay") {
    tearDownAll(() async {
      // Exceptions are reported when the test body completes, moments before
      // the app process exits; give the device-log relay time to flush them so
      // they are not lost from the `flutter test` output.
      await Future.delayed(const Duration(seconds: 2));
    });
  }

  group('end-to-end test', () {
    testWidgets('test app', (tester) async {
      var dir = Directory.current.path;
      debugPrint("Current dir: $dir");

      var fletTester = FlutterWidgetTester(tester, binding);
      assignTester(fletTester);

      List<String> args = [];
      final fletTestAppUrl = launchedDirectly
          ? Platform.environment["FLET_TEST_APP_URL"]!
          : const String.fromEnvironment("FLET_TEST_APP_URL");
      if (fletTestAppUrl != "") {
        args.add(fletTestAppUrl);
      }

      final fletTestPidFile = launchedDirectly
          ? Platform.environment["FLET_TEST_PID_FILE_PATH"] ?? ""
          : const String.fromEnvironment("FLET_TEST_PID_FILE_PATH");
      if (fletTestPidFile != "") {
        args.add(fletTestPidFile);
      }

      final fletTestAssetsDir = launchedDirectly
          ? Platform.environment["FLET_TEST_ASSETS_DIR"] ?? ""
          : const String.fromEnvironment("FLET_TEST_ASSETS_DIR");
      if (fletTestAssetsDir != "") {
        args.add(fletTestAssetsDir);
      }

      debugPrint("Flet host test: body at ${stopwatch.elapsedMilliseconds} ms");
      switch (startup) {
        case "await-main":
          await appMain(args);
        case "first-widget":
          appMain(args);
          await _pumpUntilAppAttached(fletTester);
        default:
          appMain(args);
          await Future.delayed(const Duration(milliseconds: 500));
          await fletTester.pump(duration: const Duration(seconds: 1));
      }
      debugPrint(
          "Flet host test: app started at ${stopwatch.elapsedMilliseconds} ms");
      await fletTester.pumpAndSettle(
          duration: const Duration(milliseconds: 100));
      debugPrint("Flet host test: first settle at "
          "${stopwatch.elapsedMilliseconds} ms");
      await fletTester.waitForTeardown();
    });
  });
}

/// Pumps frames until the host app has attached its [FletApp] to the widget
/// tree.
///
/// The host app's `main` is asynchronous and calls `runApp` only after its
/// own start-up work. The live test binding draws a frame only while a pump
/// is in progress, so the pumping has to continue until `runApp` has run:
/// an app attached after the last pump would never build and never connect.
/// Throws when no [FletApp] is attached within [timeout].
Future<void> _pumpUntilAppAttached(FlutterWidgetTester tester,
    {Duration timeout = const Duration(minutes: 1)}) async {
  final stopwatch = Stopwatch()..start();
  while (find.byType(FletApp).evaluate().isEmpty) {
    if (stopwatch.elapsed > timeout) {
      throw TimeoutException(
          "The app did not attach a FletApp within $timeout.");
    }
    await tester.pump();
  }
}
