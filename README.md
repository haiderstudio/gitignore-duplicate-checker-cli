# gitignore-duplicate-checker-cli

Check .gitignore files for duplicate patterns, fail CI on a duplicate.

[![CI](https://github.com/haiderstudio/gitignore-duplicate-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/gitignore-duplicate-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`gitignore_duplicate_checker` reads each `.gitignore`
file and compares its patterns after trimming whitespace
and trailing slashes:

- A `.gitignore` file grows by hand, one line at a time,
  and the same pattern gets written twice — once by you,
  once by a teammate, once by a tool. Nobody knows which
  copy is the live one, and a stale duplicate hides the
  fact that the pattern it guards was meant to be removed.
  This tool reports every duplicate with its file and
  line number, and exits 1 when any duplicate is found —
  so it can fail a CI run. A clean file exits 0.
- Patterns compare after trimming whitespace and trailing
  slashes, so `build/`, `build`, and `  build/  ` all count
  as the same pattern. That is the whole point: the same
  ignore written three different ways is still one
  duplicate.
- A leading `!` is part of the pattern, so `foo` and
  `!foo` are different patterns, not duplicates — the
  negation changes what the line means, and treating them
  as the same would be wrong.
- Comments (lines starting with `#`) and blank lines are
  ignored — they carry no pattern.
- Files come from the command line (one or more), or from
  a folder walk: every file named `.gitignore` (or ending
  in `.gitignore`) under a folder, recursively by default
  (`--no-recursive` stops at the top level). `.git`
  folders are never walked, and directory links are never
  followed, so a link cycle cannot loop the check.
- `--exclude PATTERN` skips files by glob, for example
  `--exclude 'sub/.gitignore'`. It can be repeated. A file
  passed directly on the command line is always checked,
  even if it matches an exclude pattern and even if it is
  not named `.gitignore`.
- `--stdin` reads one `.gitignore` file from standard
  input.
- `--json` prints the result as machine-readable JSON (the
  summary goes to standard error, so standard output stays
  clean JSON).
- It is report-only and runs fully offline: it never
  edits a file, sends nothing anywhere, and needs no API
  key. Python standard library only.

## What it does NOT do

- It does not edit or tidy a `.gitignore` file. A
  duplicate is reported; removing it is your job.
- It does not check whether a pattern is valid gitignore
  syntax, or whether a pattern actually matches any file.
  This tool's one job is duplicates.
- It does not check tracked files against ignore patterns
  — that is repo #41's `gitignore-checker-cli`
  (committed-by-mistake detection). This tool checks for
  duplicate patterns — a different job on the same file.
- It does not fetch anything from a live site. Every input
  is a local file or standard input.

## Who it is for

Anyone with a `.gitignore` file that more than one person
has edited: a team lead adding a CI step that fails the
build when a pattern is written twice, or anyone tidying
a long ignore file before a release. A duplicate pattern
is invisible in the file itself — this catches it before
it goes live.

## How this differs from similar tools

The exact name `gitignore-duplicate-checker-cli` matches 0
repositories on GitHub (checked Nov 10, 2026), and the
wider field is empty too: `gitignore duplicate checker`
matches 0 repositories. There is no rival that checks
`.gitignore` files for duplicate patterns. The closest
tool on the same file is our own repo #41,
`gitignore-checker-cli`, which checks tracked files
against ignore patterns — a different job. This tool does
one job: a Python standard-library-only CLI that checks
`.gitignore` files for duplicate patterns, reports each
one with file and line, and exits 1 for CI — no install
beyond Python, no website, no network.

## Install

Python standard library only — no packages to download. You need
Python 3.8 or newer. Clone the repo and run it in place:

```
git clone https://github.com/haiderstudio/gitignore-duplicate-checker-cli.git
cd gitignore-duplicate-checker-cli
python3 src/gitignore_duplicate_checker.py examples/good.gitignore
```

```
examples/good.gitignore: no duplicates
OK — 1 file(s) checked, no duplicate patterns found.
```

## Usage

Check one clean `.gitignore` file:

```
python3 src/gitignore_duplicate_checker.py examples/good.gitignore
```

```
examples/good.gitignore: no duplicates
OK — 1 file(s) checked, no duplicate patterns found.
```

Check a file with duplicates — exact, whitespace, and
trailing-slash copies:

```
python3 src/gitignore_duplicate_checker.py examples/duplicates.gitignore
```

```
FAIL examples/duplicates.gitignore:6: duplicate pattern 'build' (first seen on line 2 as 'build/')
FAIL examples/duplicates.gitignore:9: duplicate pattern 'dist/' (first seen on line 3 as 'dist/')
FAIL examples/duplicates.gitignore:12: duplicate pattern 'build/' (first seen on line 2 as 'build/')
Checked 1 file(s), 3 problem(s) in 1 file(s).
```

A negation is not a duplicate of the plain pattern:

```
python3 src/gitignore_duplicate_checker.py examples/negation.gitignore
```

```
examples/negation.gitignore: no duplicates
OK — 1 file(s) checked, no duplicate patterns found.
```

Check a whole folder:

```
python3 src/gitignore_duplicate_checker.py examples/
```

```
FAIL examples/duplicates.gitignore:6: duplicate pattern 'build' (first seen on line 2 as 'build/')
FAIL examples/duplicates.gitignore:9: duplicate pattern 'dist/' (first seen on line 3 as 'dist/')
FAIL examples/duplicates.gitignore:12: duplicate pattern 'build/' (first seen on line 2 as 'build/')
examples/good.gitignore: no duplicates
examples/negation.gitignore: no duplicates
FAIL examples/sub/.gitignore:3: duplicate pattern 'node_modules' (first seen on line 2 as 'node_modules/')
Checked 4 file(s), 4 problem(s) in 2 file(s).
```

Skip one file with `--exclude`:

```
python3 src/gitignore_duplicate_checker.py --exclude 'sub/.gitignore' examples/
```

```
FAIL examples/duplicates.gitignore:6: duplicate pattern 'build' (first seen on line 2 as 'build/')
FAIL examples/duplicates.gitignore:9: duplicate pattern 'dist/' (first seen on line 3 as 'dist/')
FAIL examples/duplicates.gitignore:12: duplicate pattern 'build/' (first seen on line 2 as 'build/')
examples/good.gitignore: no duplicates
examples/negation.gitignore: no duplicates
Checked 3 file(s), 3 problem(s) in 1 file(s).
```

Check one file from standard input:

```
python3 src/gitignore_duplicate_checker.py --stdin < examples/duplicates.gitignore
```

```
FAIL <stdin>:6: duplicate pattern 'build' (first seen on line 2 as 'build/')
FAIL <stdin>:9: duplicate pattern 'dist/' (first seen on line 3 as 'dist/')
FAIL <stdin>:12: duplicate pattern 'build/' (first seen on line 2 as 'build/')
Checked 1 file(s), 3 problem(s) in 1 file(s).
```

Machine-readable output with `--json` (the summary goes to
standard error, so standard output stays clean JSON):

```
python3 src/gitignore_duplicate_checker.py --json examples/duplicates.gitignore
```

```
{
  "files": [
    {
      "file": "examples/duplicates.gitignore",
      "problems": [
        {
          "line": 6,
          "pattern": "build",
          "first_line": 2,
          "first_pattern": "build/",
          "reason": "duplicate pattern 'build' (first seen on line 2 as 'build/')"
        },
        {
          "line": 9,
          "pattern": "dist/",
          "first_line": 3,
          "first_pattern": "dist/",
          "reason": "duplicate pattern 'dist/' (first seen on line 3 as 'dist/')"
        },
        {
          "line": 12,
          "pattern": "build/",
          "first_line": 2,
          "first_pattern": "build/",
          "reason": "duplicate pattern 'build/' (first seen on line 2 as 'build/')"
        }
      ]
    }
  ],
  "summary": {
    "checked": 1,
    "files_with_problems": 1,
    "problems": 3,
    "skipped": 0
  }
}
```

Exit codes: 0 when no duplicate pattern is found, 1 when
any duplicate is found, 2 for a usage problem (no
`.gitignore` files given, a bad flag, or a missing file or
folder).

## Examples

### 1. A file with three duplicates

`examples/duplicates.gitignore` holds the same patterns
written three ways — `build/` on line 2, `build` on line
6, `dist/` on line 3 with extra spaces on line 9, and
`build/` again on line 12:

```
python3 src/gitignore_duplicate_checker.py examples/duplicates.gitignore
```

```
FAIL examples/duplicates.gitignore:6: duplicate pattern 'build' (first seen on line 2 as 'build/')
FAIL examples/duplicates.gitignore:9: duplicate pattern 'dist/' (first seen on line 3 as 'dist/')
FAIL examples/duplicates.gitignore:12: duplicate pattern 'build/' (first seen on line 2 as 'build/')
Checked 1 file(s), 3 problem(s) in 1 file(s).
```

### 2. A negation is not a duplicate

`examples/negation.gitignore` has `!important.log` and
`important.log` side by side — the negation changes what
the line means, so the tool passes it:

```
python3 src/gitignore_duplicate_checker.py examples/negation.gitignore
```

```
examples/negation.gitignore: no duplicates
OK — 1 file(s) checked, no duplicate patterns found.
```

### 3. The bundled examples, all at once

```
sh examples/run-example.sh
```

The script checks one clean file (pass), then the file
with duplicates (fail, on purpose), then the negation
example (pass — `!foo` is not a duplicate of `foo`),
then the whole `examples/` folder (fail, on purpose —
it picks up the three duplicates plus the one in
`examples/sub/.gitignore`). Its full output is in
`examples/sample-output.md`, ending with `Checked 4
file(s), 4 problem(s) in 2 file(s).` The failing runs exit
1, which is the expected result — the script ends with
exit 0 so it can be run as a demo.

## How it is tested

Tests, standard library `unittest` only, no packages to install:

```
python3 tests/test_gitignore_duplicate_checker.py
```

The tests cover: normalising patterns (trailing slash,
whitespace, negation kept, wildcards, inner spaces),
ignorable lines (blank, comments, indented comments,
escaped hashes), duplicate detection (exact, trailing
slash, whitespace, three copies, negation not a
duplicate, negation duplicate caught, comments and
blanks skipped, case sensitivity, empty input), file
checks (clean file, duplicate file, missing file,
non-UTF-8 file, input file left unchanged), folder
walking (a direct file always checked, only `.gitignore`
names inside a folder, `.git` never walked,
`--no-recursive`, `--exclude`, a direct file checked
even if excluded, missing path), the CLI (exit 0/1/2,
each flag, `--stdin` good and bad, `--json` output,
`--version`, bad flags, missing paths, empty folders),
the bundled examples (sample output compared
byte-for-byte against a fresh run, and the README-quoted
outputs checked against it), and hygiene checks (no
placeholder text, no absolute paths, stdlib imports only,
`.env` first in `.gitignore`, CI file runs the test file).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea
of checking `.gitignore` files is not new — the similar
tool named above (our own repo #41,
`gitignore-checker-cli`) is listed in "How this differs"
— but every line of code here is original, and the tool
builds on nothing but Python's standard library.
