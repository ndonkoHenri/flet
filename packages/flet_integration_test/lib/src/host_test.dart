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
/// A directly launched app ends as soon as the test result is known, so it
/// prints with [debugPrintSynchronously]: the live test binding throttles
/// `debugPrint`, and output still queued at that moment, such as the end of
/// an exception report, would be lost. Under `flutter test` the process
/// waits 2 seconds before it ends, which gives the tool's device-log relay
/// time to pass the exception report on.
void runFletHostTest({
  required void Function(List<String>) appMain,
  required void Function(Tester) assignTester,
}) {
  var binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  final launchedDirectly =
      const String.fromEnvironment("FLET_TEST_APP_URL") == "" &&
          (Platform.environment["FLET_TEST_APP_URL"] ?? "") != "";
  if (launchedDirectly) {
    debugPrint = debugPrintSynchronously;
  }

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
    binding.allTestsPassed.future.then((passed) => exit(passed ? 0 : 1));
  } else {
    tearDownAll(() async {
      // Exceptions are reported when the test body completes, moments before
      // the app process exits; give the device-log relay time to flush them
      // so they are not lost from the `flutter test` output.
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

      appMain(args);

      await _waitForRunApp(binding);
      await fletTester.pumpAndSettle(
          duration: const Duration(milliseconds: 100));
      await fletTester.waitForTeardown();
    });
  });
}

/// Waits until the host app has called `runApp`.
///
/// The host app's `main` is asynchronous and calls `runApp` only after its
/// own start-up work, such as setting up the desktop window. The live test
/// binding draws a frame only while a pump is in progress, so the first
/// settle must not begin before `runApp` has run: an app attached after the
/// last pump would never build and never connect.
///
/// The test binding has attached a root widget of its own before the test
/// body runs, so `runApp` hands the root element a new widget and leaves it
/// dirty until the next frame. Polling for that draws no frame: frames
/// drawn before the app is attached change, in the last decimals of a
/// screenshot comparison, how some controls render afterwards. Throws when
/// the app has not called `runApp` within [timeout].
Future<void> _waitForRunApp(IntegrationTestWidgetsFlutterBinding binding,
    {Duration timeout = const Duration(seconds: 30)}) async {
  final stopwatch = Stopwatch()..start();
  while (!(binding.rootElement?.dirty ?? false)) {
    if (stopwatch.elapsed > timeout) {
      throw TimeoutException("The app did not call runApp within $timeout.");
    }
    await Future<void>.delayed(const Duration(milliseconds: 5));
  }
}
