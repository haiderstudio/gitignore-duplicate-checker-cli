#!/usr/bin/env python3
"""Check .gitignore files for duplicate patterns, fail CI on a duplicate.

Run: python3 src/gitignore_duplicate_checker.py examples/good.gitignore
     python3 src/gitignore_duplicate_checker.py examples/
     python3 src/gitignore_duplicate_checker.py --json examples/duplicates.gitignore

The problem is quiet: a .gitignore file grows by hand,
one line at a time, and the same pattern gets written
twice — once by you, once by a teammate, once by a tool.
Nobody knows which copy is the live one, and a stale
duplicate hides the fact that the pattern it guards was
meant to be removed. This tool reads each .gitignore
file, compares patterns after trimming whitespace and
trailing slashes (so "build/" and "build" count as the
same pattern), reports every duplicate with its file and
line number, and exits 1 when any duplicate is found, so
it can fail a CI run. A clean file exits 0.

Comments (lines starting with #) and blank lines are
ignored. A leading "!" is part of the pattern, so "foo"
and "!foo" are different patterns, not duplicates — the
negation changes what the line means, and treating them
as the same would be wrong. A trailing slash is ignored
when comparing, because "foo/" and "foo" ignore the same
thing in practice. A trailing space is ignored too, since
Git ignores trailing spaces in a pattern unless they are
escaped.

It never edits a file. It is report-only and runs fully
offline: it sends nothing anywhere and needs no API key.

Exit codes: 0 when no duplicate pattern is found, 1 when
any duplicate is found, 2 for a usage or input problem (a
missing path, a bad flag, a bad --exclude value, or no
.gitignore file to check).

Python standard library only.
"""

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path

VERSION = "1.0.0"


def normalise(pattern):
    """Return the comparison form of one .gitignore pattern.

    Leading and trailing whitespace is trimmed, and a
    trailing slash is removed, so "build/" and "  build "
    both compare as "build". A leading "!" is kept — a
    negation is a different pattern, not a duplicate.
    """
    return pattern.strip().rstrip("/")


def is_ignorable(line):
    """Return True for lines that are not patterns.

    Blank lines and comment lines (a # as the first
    non-space character) carry no pattern.
    """
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def check_lines(lines):
    """Return the duplicate problems in one file's lines.

    lines is a list of the file's lines in order. Each
    problem is a dict with "line" (the duplicate's line
    number, starting at 1), "pattern" (the pattern as
    written on that line), and "first_line" (the line
    number where the pattern first appeared).
    """
    seen = {}
    problems = []
    for number, raw in enumerate(lines, start=1):
        if is_ignorable(raw):
            continue
        pattern = raw.strip()
        key = normalise(pattern)
        if key in seen:
            problems.append(
                {
                    "line": number,
                    "pattern": pattern,
                    "first_line": seen[key]["line"],
                    "first_pattern": seen[key]["pattern"],
                }
            )
        else:
            seen[key] = {"line": number, "pattern": pattern}
    return problems


def check_file(path):
    """Return (problems, skipped) for one .gitignore file.

    skipped is always False — nothing is skipped, a file
    that cannot be read is a problem.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return (
            [
                {
                    "line": 0,
                    "reason": "not readable as UTF-8 text",
                    "pattern": "",
                    "first_line": 0,
                    "first_pattern": "",
                }
            ],
            False,
        )
    except OSError as exc:
        return (
            [
                {
                    "line": 0,
                    "reason": f"cannot read file: {exc.strerror}",
                    "pattern": "",
                    "first_line": 0,
                    "first_pattern": "",
                }
            ],
            False,
        )
    problems = []
    for problem in check_lines(text.splitlines()):
        problems.append(
            {
                "line": problem["line"],
                "pattern": problem["pattern"],
                "first_line": problem["first_line"],
                "first_pattern": problem["first_pattern"],
                "reason": (
                    f"duplicate pattern '{problem['pattern']}' "
                    f"(first seen on line {problem['first_line']} "
                    f"as '{problem['first_pattern']}')"
                ),
            }
        )
    return problems, False


def _is_gitignore(name):
    return name == ".gitignore" or name.endswith(".gitignore")


def gather(paths, exclude, recursive):
    """Walk the given paths and return (entries, checked, skipped).

    entries is a list of (file, problem); checked is a list
    of one dict per file the tool tried, with file and
    problems; skipped is a list of files skipped by
    --exclude. A file passed on the command line is always
    checked, even if it matches --exclude and even if it is
    not named .gitignore. Inside a folder, only files named
    .gitignore (or ending in .gitignore) are checked.
    """
    entries = []
    checked = []
    skipped = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(raw)
        if path.is_file():
            problems, _was_skipped = check_file(path)
            checked.append({"file": str(path), "problems": problems})
            for problem in problems:
                entries.append((str(path), problem))
            continue
        if recursive:
            for dirpath, dirnames, filenames in _walk(path):
                for name in filenames:
                    if not _is_gitignore(name):
                        continue
                    candidate = Path(dirpath) / name
                    if _excluded(candidate, path, exclude):
                        skipped.append(str(candidate))
                        continue
                    problems, _was_skipped = check_file(candidate)
                    checked.append(
                        {"file": str(candidate), "problems": problems}
                    )
                    for problem in problems:
                        entries.append((str(candidate), problem))
        else:
            for candidate in sorted(path.iterdir()):
                if not candidate.is_file():
                    continue
                if not _is_gitignore(candidate.name):
                    continue
                if _excluded(candidate, path, exclude):
                    skipped.append(str(candidate))
                    continue
                problems, _was_skipped = check_file(candidate)
                checked.append(
                    {"file": str(candidate), "problems": problems}
                )
                for problem in problems:
                    entries.append((str(candidate), problem))
    return entries, checked, skipped


def _walk(root):
    """os.walk that never enters .git and never follows links."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        yield dirpath, dirnames, sorted(filenames)


def _excluded(candidate, root, patterns):
    name = candidate.name
    try:
        rel = str(candidate.relative_to(root))
    except ValueError:
        rel = name
    return any(
        fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern)
        for pattern in patterns
    )


def _format_problem(location, problem):
    return (
        f"FAIL {location}:{problem['line']}: "
        f"duplicate pattern '{problem['pattern']}' "
        f"(first seen on line {problem['first_line']} "
        f"as '{problem['first_pattern']}')"
    )


def _summary_line(checked, problems):
    total = len(problems)
    bad_files = len({f for f, _p in problems})
    if total:
        return (
            f"Checked {len(checked)} file(s), {total} "
            f"problem(s) in {bad_files} file(s)."
        )
    return (
        f"OK — {len(checked)} file(s) checked, "
        f"no duplicate patterns found."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gitignore-duplicate-checker-cli",
        description="Check .gitignore files for duplicate patterns.",
    )
    parser.add_argument(
        "paths", nargs="*", help="files or folders to check"
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read one .gitignore file from standard input",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="skip files matching this glob (repeatable)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="do not walk into subfolders",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as JSON (summary goes to stderr)",
    )
    parser.add_argument("--version", action="store_true", help="print the version")
    args = parser.parse_args(argv)

    if args.version:
        print(f"gitignore-duplicate-checker-cli {VERSION}")
        return 0

    entries = []
    checked = []
    skipped = []
    try:
        if args.paths:
            found, found_checked, found_skipped = gather(
                args.paths,
                args.exclude,
                not args.no_recursive,
            )
            entries.extend(found)
            checked.extend(found_checked)
            skipped.extend(found_skipped)
    except FileNotFoundError as exc:
        print(f"error: no such file or folder: {exc}", file=sys.stderr)
        return 2

    if args.stdin:
        text = sys.stdin.read()
        problems = []
        for problem in check_lines(text.splitlines()):
            problems.append(
                {
                    "line": problem["line"],
                    "pattern": problem["pattern"],
                    "first_line": problem["first_line"],
                    "first_pattern": problem["first_pattern"],
                    "reason": (
                        f"duplicate pattern '{problem['pattern']}' "
                        f"(first seen on line {problem['first_line']} "
                        f"as '{problem['first_pattern']}')"
                    ),
                }
            )
        checked.append({"file": "<stdin>", "problems": problems})
        for problem in problems:
            entries.append(("<stdin>", problem))

    if not checked:
        print("error: no .gitignore files to check", file=sys.stderr)
        return 2

    problems = entries
    bad_files = len({f for f, _p in problems})
    total = len(problems)
    summary = _summary_line(checked, problems)

    if args.json:
        files = []
        for entry in checked:
            files.append(
                {
                    "file": entry["file"],
                    "problems": entry["problems"],
                }
            )
        result = {
            "files": files,
            "summary": {
                "checked": len(checked),
                "files_with_problems": bad_files,
                "problems": total,
                "skipped": len(skipped),
            },
        }
        print(json.dumps(result, indent=2))
        print(summary, file=sys.stderr)
        return 1 if problems else 0

    for entry in checked:
        if entry["problems"]:
            for problem in entry["problems"]:
                print(_format_problem(entry["file"], problem))
        else:
            print(f"{entry['file']}: no duplicates")
    print(summary)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
