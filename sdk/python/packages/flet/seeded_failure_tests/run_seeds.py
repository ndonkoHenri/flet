"""
Runs the seeded failures of `test_seeded.py` one at a time and checks that
each ends the way it should: red where something is wrong, green for the
controls, and within a bounded time.

Fork only. Usage: `python run_seeds.py <prebuilt|flutter-test> [seed ...]`.
Writes `seed-logs/<seed>.log`, `seed-logs/results.json` and a table to the
job summary. Exits 1 when an outcome differs from the expectation.
"""

import contextlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGS = HERE / "seed-logs"
ON_CI = os.getenv("GITHUB_ACTIONS") == "true"
APP_PROCESS = "Flet.app/Contents/MacOS/Flet"

P, F = "prebuilt", "flutter-test"

# id, test, what is seeded, expected outcome per mode, text the output must
# contain per mode, extra environment, hard limit in seconds per mode.
# `known` is the outcome of a gap that is known and not closed: the run stays
# green on it and the table says so.
SEEDS = [
    dict(
        id="ok",
        test="test_ok",
        what="control: nothing is wrong",
        expect={P: "green", F: "green"},
        limit={F: 900},
    ),
    dict(
        id="render-overflow",
        test="test_render_overflow",
        what="render overflow",
        expect={P: "red", F: "red"},
        text={P: "A RenderFlex overflowed", F: "A RenderFlex overflowed"},
    ),
    dict(
        id="control-exception",
        test="test_control_exception",
        what="exception inside a control",
        expect={P: "red", F: "red"},
        text={
            P: "Controller's length property",
            F: "Controller's length property",
        },
    ),
    dict(
        id="never-settles",
        test="test_never_settles",
        what="app never settles (in the test)",
        expect={P: "red", F: "red"},
        text={P: "pump_and_settle", F: "pump_and_settle"},
    ),
    dict(
        id="never-settles-at-start",
        test="test_never_settles_at_start",
        what="app never settles (in its own main)",
        expect={P: "red", F: "red"},
        text={P: "Timed out during start", F: "Timed out during start"},
    ),
    dict(
        id="main-raises",
        test="test_main_raises",
        what="the app's main raises",
        expect={P: "red", F: "red"},
        text={P: "ValueError: seeded error", F: "ValueError: seeded error"},
    ),
    dict(
        id="app-killed",
        test="test_app_killed_mid_test",
        what="app killed mid-test (SIGKILL)",
        expect={P: "red", F: "red"},
        text={P: "exit code -9", F: "exit code 79"},
    ),
    dict(
        id="app-crashes",
        test="test_app_crashes_mid_test",
        what="app crashes mid-test (SIGSEGV)",
        expect={P: "red", F: "red"},
        text={P: "exit code -11", F: "exit code 79"},
    ),
    dict(
        id="app-frozen",
        test="test_app_frozen_mid_test",
        what="app frozen mid-test (SIGSTOP)",
        expect={P: "red", F: "red"},
        known={F: "green"},
        text={P: "did not exit within 10 seconds"},
    ),
    dict(
        id="app-frozen-tester-call",
        test="test_app_frozen_then_tester_call",
        what="app frozen, then a tester call without a timeout",
        expect={P: "red"},
        known={P: "hung"},
        limit={P: 90},
    ),
    dict(
        id="app-quits",
        test="test_app_quits_mid_test",
        what="app exits with code 0 mid-test",
        expect={P: "red", F: "red"},
    ),
    dict(
        id="never-connects",
        test="test_never_connects",
        what="app never connects (dead port)",
        expect={P: "red", F: "red"},
        text={P: "did not connect", F: "did not connect"},
        env={F: {"FLET_TEST_START_TIMEOUT": "300"}},
        limit={P: 150, F: 600},
    ),
    dict(
        id="port-taken",
        test="test_port_taken",
        what="server port already taken",
        expect={P: "red", F: "red"},
        text={
            P: "stopped before the Flutter app connected",
            F: "stopped before the Flutter app connected",
        },
    ),
    dict(
        id="binary-missing",
        test="test_app_start_fails",
        what="binary path does not exist",
        expect={P: "red"},
        text={P: "No such file or directory"},
        env={P: {"FLET_TEST_APP_BINARY": "/nonexistent/Flet.app/Contents/MacOS/Flet"}},
    ),
    dict(
        id="dies-before-connecting",
        test="test_app_start_fails",
        what="process dies before connecting",
        expect={P: "red"},
        text={P: "exited early with code 1"},
        env={P: {"FLET_TEST_APP_BINARY": "/usr/bin/false"}},
    ),
    dict(
        id="stale-media-kit-files",
        test="test_stale_media_kit_files",
        what="control: stale media_kit pid files in TMPDIR",
        expect={P: "green", F: "red"},
        text={P: "NativeReferenceHolder: Allocated", F: "exited early"},
        env={P: {"FLET_TEST_VERBOSE": "1"}, F: {"FLET_TEST_VERBOSE": "1"}},
    ),
]

DEFAULT_LIMIT = {P: 120, F: 420}
PHASE = re.compile(r"^\s*([\d.]+)s (setup|call|teardown)\s", re.M)
SUMMARY = re.compile(r"^=+ (.*) in [\d.]+s.* =+$", re.M)


def leftover_apps() -> list[str]:
    if not ON_CI:
        return []
    out = subprocess.run(
        ["pgrep", "-fl", APP_PROCESS], capture_output=True, text=True
    ).stdout
    found = [line for line in out.splitlines() if line.strip()]
    for line in found:
        with contextlib.suppress(ProcessLookupError, ValueError):
            os.kill(int(line.split()[0]), signal.SIGKILL)
    return found


def run_seed(seed: dict, mode: str) -> dict:
    env = dict(os.environ)
    env.update(seed.get("env", {}).get(mode, {}))
    limit = seed.get("limit", {}).get(mode, DEFAULT_LIMIT[mode])
    log = LOGS / f"{seed['id']}.log"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-s",
        "-rA",
        "--durations=0",
        "--durations-min=0",
        "-o",
        "log_cli=true",
        "-o",
        "log_cli_level=INFO",
        f"{HERE / 'test_seeded.py'}::{seed['test']}",
    ]
    started = time.monotonic()
    with open(log, "wb") as f:
        proc = subprocess.Popen(
            cmd,
            cwd=HERE.parents[2],
            env=env,
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            rc = proc.wait(timeout=limit)
            hung = False
        except subprocess.TimeoutExpired:
            hung = True
            os.killpg(proc.pid, signal.SIGKILL)
            rc = proc.wait()
    seconds = time.monotonic() - started
    output = log.read_text(errors="replace")
    actual = "hung" if hung else {0: "green", 1: "red"}.get(rc, f"broken (rc {rc})")
    text = seed.get("text", {}).get(mode)
    phases = {m.group(2): float(m.group(1)) for m in PHASE.finditer(output)}
    summary = SUMMARY.findall(output)
    leftovers = leftover_apps()
    if ON_CI:
        subprocess.run(["screencapture", "-x", str(LOGS / f"{seed['id']}.png")])
    expected = seed["expect"][mode]
    text_ok = text is None or text in output
    if actual == expected and text_ok:
        verdict = "ok"
    elif actual == seed.get("known", {}).get(mode):
        verdict = "known gap"
    else:
        verdict = "DIFFERS"
    return dict(
        id=seed["id"],
        what=seed["what"],
        mode=mode,
        expected=expected,
        actual=actual,
        rc=rc,
        seconds=round(seconds, 1),
        limit=limit,
        phases=phases,
        pytest_summary=summary[-1] if summary else "",
        text=text,
        text_found=None if text is None else text in output,
        leftovers=leftovers,
        verdict=verdict,
    )


def main() -> int:
    mode = sys.argv[1]
    only = sys.argv[2:]
    LOGS.mkdir(exist_ok=True)
    results = []
    for seed in SEEDS:
        if mode not in seed["expect"] or (only and seed["id"] not in only):
            continue
        print(f"::group::seed {seed['id']}: {seed['what']}", flush=True)
        result = run_seed(seed, mode)
        print((LOGS / f"{seed['id']}.log").read_text(errors="replace"))
        print("::endgroup::", flush=True)
        print(
            f"seed {result['id']}: expected {result['expected']}, "
            f"actual {result['actual']} after {result['seconds']} s "
            f"(phases {result['phases']}, {result['pytest_summary']}), "
            f"text {result['text']!r} found: {result['text_found']}, "
            f"left behind: {result['leftovers']} -> "
            f"{result['verdict']}",
            flush=True,
        )
        results.append(result)
    (LOGS / "results.json").write_text(json.dumps(results, indent=1))
    rows = [
        f"## Seeded failures, {mode}",
        "",
        "| seed | expected | actual | seconds | setup / call / teardown | "
        "pytest | text found | left behind | verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        phases = " / ".join(
            str(r["phases"].get(k, "-")) for k in ("setup", "call", "teardown")
        )
        rows.append(
            f"| {r['what']} | {r['expected']} | {r['actual']} | {r['seconds']} | "
            f"{phases} | {r['pytest_summary']} | {r['text_found']} | "
            f"{len(r['leftovers'])} | {r['verdict']} |"
        )
    table = "\n".join(rows)
    print(table)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(table + "\n")
    return 1 if any(r["verdict"] == "DIFFERS" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
