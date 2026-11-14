// Experimental entrypoint for "fix A": ONE Flutter process, MANY Flet sessions.
// Built once with
//   flutter build macos --debug -t integration_test_reuse/reuse_host.dart
// (cwd = client) and launched directly as a binary by the pytest plugin
// sdk/python/packages/flet/integration_tests/_reuse/reuse_plugin.py.
// It lives outside integration_test/ so `flutter test integration_test` does
// not pick it up.
//
// Control channel: a loopback HttpServer inside the app (port from the
// environment variable FLET_TEST_HOST_PORT). It does not depend on the Flet
// connection.
//   POST /start {url, pid_file, assets_dir}  mount the client against that URL
//   POST /end   {reset_window, clear_image_cache}  unmount, report exceptions
//   POST /exit                               finish, exit code 0/1
//   POST /status                             answered at once, never queued
//
// Two shapes, chosen at RUN time with FLET_HOST_SHAPE:
//   loop  = one long-running testWidgets that loops over sessions
//   multi = FLET_HOST_MAX_TESTS registered testWidgets, one session each
//
// ignore_for_file: depend_on_referenced_packages, invalid_use_of_visible_for_testing_member, avoid_print

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' show PlatformDispatcher;

import 'package:flet_client/main.dart' as app;
import 'package:flet_integration_test/flet_integration_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:window_manager/window_manager.dart';

final _sw = Stopwatch()..start();
void _log(String m) => print('HOST +${_sw.elapsedMilliseconds}ms $m');

class _Cmd {
  _Cmd(this.path, this.body, this.req);
  final String path;
  final Map<String, dynamic> body;
  final HttpRequest req;

  Future<void> reply(Map<String, dynamic> m) async {
    try {
      req.response.statusCode = 200;
      req.response.headers.contentType = ContentType.json;
      req.response.write(jsonEncode(m));
      await req.response.close();
    } catch (e) {
      _log('reply to $path failed: $e');
    }
  }
}

final _queue = <_Cmd>[];
Completer<void>? _waiter;
int _sessions = 0;
String _state = 'idle';
Size? _baselineSize;
Offset? _baselinePos;
final _asyncErrors = <String>[];
final _testFailures = <String>[];

List<String> _takeAsyncErrors() {
  final r = List<String>.from(_asyncErrors);
  _asyncErrors.clear();
  return r;
}

Future<_Cmd> _nextCmd() async {
  while (_queue.isEmpty) {
    final c = Completer<void>();
    _waiter = c;
    await c.future;
  }
  return _queue.removeAt(0);
}

Future<HttpServer> _startControl() async {
  final port = int.parse(Platform.environment['FLET_TEST_HOST_PORT'] ?? '0');
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, port);
  _log('control port ${server.port} pid $pid');
  server.listen((req) async {
    final text = await utf8.decoder.bind(req).join();
    final body = text.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(text) as Map<String, dynamic>;
    final cmd = _Cmd(req.uri.path, body, req);
    if (cmd.path == '/status') {
      await cmd.reply({
        'ok': true,
        'pid': pid,
        'state': _state,
        'sessions': _sessions,
        'rss': ProcessInfo.currentRss,
        'uptime_ms': _sw.elapsedMilliseconds,
      });
      return;
    }
    if (cmd.path == '/inject') {
      // Failure injection: an uncaught async error raised by code that a
      // frame started (what a widget's own Future does).
      SchedulerBinding.instance.addPostFrameCallback((_) {
        Future<void>.delayed(const Duration(milliseconds: 5),
            () => throw StateError('injected async error from frame code'));
      });
      SchedulerBinding.instance.scheduleFrame();
      await cmd.reply({'ok': true});
      return;
    }
    _queue.add(cmd);
    final w = _waiter;
    _waiter = null;
    w?.complete();
  });
  return server;
}

/// Mounts the client app for one session: calls the unchanged client `main()`
/// with a new URL. The previous root is a SizedBox, so `runApp(FletApp(...))`
/// creates a new element, a new FletBackend and a new socket.
Future<Map<String, dynamic>> _mount(
    FlutterWidgetTester ft, Map<String, dynamic> body,
    {required bool guard}) async {
  final t0 = _sw.elapsedMilliseconds;
  _sessions++;
  _state = 'mounting';
  app.tester = ft;
  final args = <String>[
    body['url'] as String,
    body['pid_file'] as String,
    body['assets_dir'] as String,
  ];
  if (guard) {
    // Run the app in its own error zone: an uncaught async error raised by
    // this session's code is recorded against this session instead of ending
    // the one long testWidgets.
    final done = Completer<void>();
    runZonedGuarded(() {
      app.main(args).then((_) => done.complete(),
          onError: (Object e, StackTrace st) => done.completeError(e, st));
    }, (e, st) {
      _log('session $_sessions async error: $e');
      _asyncErrors.add('$e\n$st');
    });
    await done.future;
  } else {
    await app.main(args);
  }
  final t1 = _sw.elapsedMilliseconds;
  // One frame is needed: the page registers only after its first layout
  // (page size, media, window state). The Python side does its own
  // pump_and_settle before it reports ready, so no settle here by default.
  await ft.pump();
  if (body['settle'] == true) {
    await ft.pumpAndSettle(duration: const Duration(milliseconds: 100));
  }
  if (_baselineSize == null) {
    _baselineSize = await windowManager.getSize();
    _baselinePos = await windowManager.getPosition();
    _log('baseline window $_baselineSize at $_baselinePos');
  }
  _state = 'mounted';
  final t2 = _sw.elapsedMilliseconds;
  _log('session $_sessions mounted: main ${t1 - t0} ms, total ${t2 - t0} ms');
  return {
    'ok': true,
    'session': _sessions,
    'main_ms': t1 - t0,
    'mount_ms': t2 - t0,
  };
}

/// Puts the window back to the size and position of the first session.
/// Returns true when something had to be repaired.
Future<bool> _repairWindow(
    FlutterWidgetTester ft, Map<String, dynamic> body, Size size, Offset pos) async {
  if (body['reset_window'] != true ||
      _baselineSize == null ||
      (size == _baselineSize && pos == _baselinePos)) {
    return false;
  }
  final mode = body['reset_mode'] ?? 'pump';
  final f = windowManager.setBounds(null,
      position: _baselinePos, size: _baselineSize);
  if (mode == 'await') {
    await f;
    await ft.pump();
    return true;
  }
  // Keep producing frames while the native resize is in flight: the macOS
  // embedder blocks until a frame of the new size arrives and logs
  // "Resize timed out" after 1 s when nothing pumps.
  var done = false;
  f.whenComplete(() => done = true);
  var n = 0;
  while (!done && n < 200) {
    await ft.pump(
        duration: mode == 'pump100' ? const Duration(milliseconds: 100) : null);
    n++;
  }
  await f;
  await ft.pump();
  return true;
}

/// Unmounts the client app and resets process-level state.
Future<Map<String, dynamic>> _unmount(
    FlutterWidgetTester ft, Map<String, dynamic> body) async {
  final t0 = _sw.elapsedMilliseconds;
  _state = 'unmounting';
  final size = await windowManager.getSize();
  final pos = await windowManager.getPosition();
  var repaired = false;
  final before = body['reset_when'] == 'before';
  if (before) {
    // Repair while the app is still mounted, the way a test's own
    // resize_page() runs.
    repaired = await _repairWindow(ft, body, size, pos);
  }
  final tQuery = _sw.elapsedMilliseconds;
  // Replace the root without the tester lock: a pumpAndSettle that the
  // session left spinning on an endless animation holds the lock and settles
  // only once the tree is gone.
  runApp(SizedBox.shrink(key: UniqueKey()));
  await ft.pump();
  final tPump = _sw.elapsedMilliseconds;
  if (body['release_input'] != false) {
    await ft.releaseInput();
  }
  await ft.pump();
  final tRelease = _sw.elapsedMilliseconds;
  if (body['clear_image_cache'] != false) {
    PaintingBinding.instance.imageCache
      ..clear()
      ..clearLiveImages();
  }
  if (!before) {
    repaired = await _repairWindow(ft, body, size, pos);
  }
  if (body['reset_focus'] == true) {
    // What TestWidgetsFlutterBinding.postTest() does between two testWidgets;
    // needed only in the "loop" shape, where the binding never runs it.
    final owner = WidgetsBinding.instance.buildOwner!;
    owner.focusManager.dispose();
    owner.focusManager = FocusManager()..registerGlobalHandlers();
    HardwareKeyboard.instance.clearState();
    ServicesBinding.instance.keyEventManager.clearState();
    RendererBinding.instance.initMouseTracker();
    await ft.pump();
  }
  _state = 'idle';
  final t1 = _sw.elapsedMilliseconds;
  return {
    'ok': true,
    'session': _sessions,
    'unmount_ms': t1 - t0,
    'steps_ms': [tQuery - t0, tPump - tQuery, tRelease - tPump, t1 - tRelease],
    'window': [size.width, size.height, pos.dx, pos.dy],
    'window_repaired': repaired,
    'rss': ProcessInfo.currentRss,
    'async_errors': _takeAsyncErrors(),
  };
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  final env = Platform.environment;
  final shape = env['FLET_HOST_SHAPE'] ?? 'loop';
  final maxTests = int.tryParse(env['FLET_HOST_MAX_TESTS'] ?? '') ?? 3000;
  final guard = env['FLET_HOST_GUARD'] != '0';
  _log('shape=$shape maxTests=$maxTests guard=$guard');

  final prevReportTestException = reportTestException;
  reportTestException = (details, testDescription) {
    print('Test exception ($testDescription): '
        '${details.exceptionAsString()}\n${details.stack ?? ''}');
    _testFailures.add('[$testDescription] ${details.exceptionAsString()}');
    prevReportTestException(details, testDescription);
  };

  binding.allTestsPassed.future.then((ok) {
    _log('allTestsPassed=$ok, exiting');
    exit(ok ? 0 : 1);
  });

  if (env['FLET_HOST_ROOT_FRAMES'] == '1') {
    // PlatformDispatcher callbacks are bound to the zone that registers them.
    // Without this the first testWidgets registers the frame callbacks, so
    // the frames of EVERY later session run in the first test's zone and an
    // uncaught async error from frame code is reported against a test that
    // has already finished ("after the test had completed": logged, lost).
    // Registered here they run in the root zone and such errors reach
    // PlatformDispatcher.onError, where they are recorded for the session
    // that is mounted now.
    SchedulerBinding.instance.ensureFrameCallbacksRegistered();
    PlatformDispatcher.instance.onError = (Object e, StackTrace st) {
      _log('root-zone async error during session $_sessions: $e');
      _asyncErrors.add('$e\n$st');
      return true;
    };
  }

  final control = _startControl();

  if (shape == 'loop') {
    testWidgets('host loop', (tester) async {
      final ft = FlutterWidgetTester(tester, binding);
      await control;
      var mounted = false;
      while (true) {
        final cmd = await _nextCmd();
        try {
          switch (cmd.path) {
            case '/start':
              if (mounted) {
                _log('start while mounted: unmounting first');
                await _unmount(ft, const {});
                tester.takeException();
              }
              final r = await _mount(ft, cmd.body, guard: guard);
              mounted = true;
              await cmd.reply(r);
            case '/end':
              final r = await _unmount(ft, cmd.body);
              mounted = false;
              final ex = tester.takeException();
              r['exceptions'] = <String>[
                if (ex != null) ex.toString(),
                ...(r['async_errors'] as List<String>),
              ];
              await cmd.reply(r);
            case '/exit':
              await cmd.reply({'ok': true, 'sessions': _sessions});
              return;
            default:
              await cmd.reply({'ok': false, 'error': 'unknown ${cmd.path}'});
          }
        } catch (e, st) {
          _log('command ${cmd.path} failed: $e\n$st');
          await cmd.reply({'ok': false, 'error': '$e\n$st'});
        }
      }
    });
  } else {
    _Cmd? pendingEnd;
    Map<String, dynamic>? pendingEndInfo;

    // Runs after the test body AND after the binding's end-of-test checks,
    // so a failure the binding reports for this testWidgets is in
    // _testFailures by now.
    tearDown(() async {
      final end = pendingEnd;
      if (end != null) {
        pendingEnd = null;
        final info = pendingEndInfo!;
        info['exceptions'] = <String>[
          ..._testFailures,
          ...(info['async_errors'] as List<String>),
        ];
        _testFailures.clear();
        await end.reply(info);
      }
    });

    for (var i = 1; i <= maxTests; i++) {
      testWidgets('session ${i.toString().padLeft(5, '0')}', (tester) async {
        final ft = FlutterWidgetTester(tester, binding);
        await control;
        _Cmd cmd;
        while (true) {
          cmd = await _nextCmd();
          if (cmd.path == '/start') break;
          if (cmd.path == '/exit') {
            final ok = binding.failureMethodsDetails.isEmpty;
            await cmd.reply({
              'ok': true,
              'sessions': _sessions,
              'failed_tests': binding.failureMethodsDetails.length,
            });
            _log('exit requested, failed tests: '
                '${binding.failureMethodsDetails.length}');
            exit(ok ? 0 : 1);
          }
          if (cmd.path == '/end') {
            // The previous testWidgets ended before its /end arrived (an
            // uncaught async error completes a test at once).
            await cmd.reply({
              'ok': true,
              'ended_early': true,
              'exceptions': List<String>.from(_testFailures),
              'rss': ProcessInfo.currentRss,
            });
            _testFailures.clear();
            continue;
          }
          await cmd.reply({'ok': false, 'error': 'unknown ${cmd.path}'});
        }
        _testFailures.clear();
        await cmd.reply(await _mount(ft, cmd.body, guard: false));
        final end = await _nextCmd();
        pendingEndInfo = await _unmount(ft, end.body);
        pendingEnd = end;
        // Any pending framework exception is left in place on purpose: the
        // binding fails THIS testWidgets with it.
      });
    }
  }
}
