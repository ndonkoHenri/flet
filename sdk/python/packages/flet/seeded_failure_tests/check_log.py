"""
Checks a pytest log of the seeded-failure tests.

Usage: `python check_log.py <log file>`. Exits with 0 when every seeded
failure was detected and its exception text is complete, 1 otherwise.
"""

import re
import sys
from pathlib import Path

TEST_ID = re.compile(r"test_seeded_failures\.py::(test_\w+) ?(PASSED|FAILED|ERROR)?$")
BLOCK_HEADER = re.compile(r"══╡ EXCEPTION CAUGHT BY .+ ╞═+$")
BLOCK_FOOTER = re.compile(r"^(flutter: )?═{40,}$")
SUMMARY = "1 failed, 4 passed, 4 errors"

# test name: (outcomes pytest must report, exit code, texts that must be there)
EXPECTED = {
    "test_ok": (["PASSED"], 0, []),
    "test_render_overflow": (
        ["PASSED", "ERROR"],
        1,
        [
            "Test exception (test app): A RenderFlex overflowed by",
            "The overflowing RenderFlex has an orientation of Axis.horizontal.",
        ],
    ),
    "test_control_exception": (
        ["PASSED", "ERROR"],
        1,
        [
            "Test exception (test app): Controller's length property (2) does "
            "not match the number of tabs (3) present in TabBar's tabs property.",
        ],
    ),
    "test_layout_exception_every_frame": (
        ["PASSED", "ERROR"],
        1,
        ["Test exception (test app): Multiple exceptions ("],
    ),
    "test_never_settles": (
        ["FAILED", "ERROR"],
        1,
        [
            "Test exception (test app): Asynchronous call to guarded function leaked.",
        ],
    ),
}


def sections(lines: list[str]) -> dict[str, list[str]]:
    """
    Splits the log into the lines that belong to each test.

    Args:
        lines: The log, one entry per line.

    Returns:
        The lines between the first mention of a test and the first mention
        of the next one, by test name.
    """
    result: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if "short test summary info" in line or re.match(
            r"^=+ (ERRORS|FAILURES) =+$", line
        ):
            break
        m = TEST_ID.search(line)
        if m:
            current = m.group(1)
        if current:
            result.setdefault(current, []).append(line)
    return result


def main() -> int:
    """
    Prints one row per seeded test and the problems found.

    Returns:
        The process exit code.
    """
    lines = Path(sys.argv[1]).read_text(errors="replace").splitlines()
    by_test = sections(lines)
    problems = []
    print(
        f"{'test':36} {'outcomes':14} {'exit':>4} {'blocks':>6} {'closed':>6} "
        f"{'texts':>5} {'last line':>9}"
    )
    for name, (outcomes, exit_code, texts) in EXPECTED.items():
        body = by_test.get(name, [])
        seen = [m.group(2) for m in map(TEST_ID.search, body) if m and m.group(2)]
        codes = [
            int(m.group(1))
            for m in (re.search(r"has exited \(code (-?\d+)\)", ln) for ln in body)
            if m
        ]
        headers = sum(1 for ln in body if BLOCK_HEADER.search(ln))
        footers = sum(1 for ln in body if BLOCK_FOOTER.match(ln))
        found = sum(1 for t in texts if any(t in ln for ln in body))
        # The harness prints this line last, so everything before it was written.
        last = any("Flet host test: exiting, passed=" in ln for ln in body)
        print(
            f"{name:36} {'+'.join(seen):14} {codes[0] if codes else '?':>4} "
            f"{headers:6d} {footers:6d} {found}/{len(texts):<3} {last!s:>9}"
        )
        if seen != outcomes:
            problems.append(f"{name}: outcomes {seen}, expected {outcomes}")
        if codes != [exit_code]:
            problems.append(f"{name}: exit codes {codes}, expected [{exit_code}]")
        if found != len(texts):
            problems.append(f"{name}: {len(texts) - found} expected text(s) missing")
        if exit_code != 0 and headers == 0:
            problems.append(f"{name}: no exception block in the log")
        if headers != footers:
            problems.append(f"{name}: {headers} exception blocks, {footers} closed")
        if exit_code != 0 and not last:
            problems.append(f"{name}: the output ends before the harness' last line")
    if not any(SUMMARY in ln for ln in lines[-5:]):
        problems.append(f"pytest summary is not '{SUMMARY}': {lines[-1:]}")
    for problem in problems:
        print("PROBLEM:", problem)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
