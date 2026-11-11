#!/usr/bin/env python3
"""Tests for gitignore-duplicate-checker-cli.

Standard library unittest only. Run from the repo root:

    python3 tests/test_gitignore_duplicate_checker.py

or:

    python3 -m unittest discover -s tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "gitignore_duplicate_checker.py"
sys.path.insert(0, str(ROOT / "src"))

import gitignore_duplicate_checker as tool  # noqa: E402


def run_cli(*args, stdin_text=None):
    """Run the tool as a subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(SRC), *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return result.returncode, result.stdout, result.stderr


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestNormalise(unittest.TestCase):
    def test_exact_pattern_unchanged(self):
        self.assertEqual(tool.normalise("build"), "build")

    def test_trailing_slash_removed(self):
        self.assertEqual(tool.normalise("build/"), "build")

    def test_leading_and_trailing_spaces_trimmed(self):
        self.assertEqual(tool.normalise("  dist/  "), "dist")

    def test_negation_kept(self):
        self.assertEqual(tool.normalise("!foo"), "!foo")

    def test_negation_with_slash(self):
        self.assertEqual(tool.normalise("!foo/"), "!foo")

    def test_wildcard_pattern_unchanged(self):
        self.assertEqual(tool.normalise("*.pyc"), "*.pyc")

    def test_inner_spaces_kept(self):
        self.assertEqual(tool.normalise("my folder/"), "my folder")


class TestIsIgnorable(unittest.TestCase):
    def test_blank_line(self):
        self.assertTrue(tool.is_ignorable(""))

    def test_spaces_only(self):
        self.assertTrue(tool.is_ignorable("   "))

    def test_comment(self):
        self.assertTrue(tool.is_ignorable("# a comment"))

    def test_indented_comment(self):
        self.assertTrue(tool.is_ignorable("   # indented comment"))

    def test_pattern_not_ignorable(self):
        self.assertFalse(tool.is_ignorable("build/"))

    def test_escaped_hash_is_a_pattern(self):
        self.assertFalse(tool.is_ignorable("\\#file"))


class TestCheckLines(unittest.TestCase):
    def test_clean_file_no_problems(self):
        lines = ["build/", "dist/", "*.pyc", ""]
        self.assertEqual(tool.check_lines(lines), [])

    def test_exact_duplicate(self):
        problems = tool.check_lines(["build/", "dist/", "build/"])
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["line"], 3)
        self.assertEqual(problems[0]["first_line"], 1)
        self.assertEqual(problems[0]["pattern"], "build/")
        self.assertEqual(problems[0]["first_pattern"], "build/")

    def test_trailing_slash_duplicate(self):
        problems = tool.check_lines(["build/", "build"])
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["line"], 2)
        self.assertEqual(problems[0]["first_line"], 1)

    def test_whitespace_duplicate(self):
        problems = tool.check_lines(["dist/", "  dist/  "])
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["pattern"], "dist/")

    def test_three_copies_two_problems(self):
        problems = tool.check_lines(["a", "a", "a"])
        self.assertEqual(len(problems), 2)
        self.assertEqual([p["line"] for p in problems], [2, 3])
        self.assertTrue(all(p["first_line"] == 1 for p in problems))

    def test_negation_is_not_a_duplicate(self):
        problems = tool.check_lines(["foo", "!foo"])
        self.assertEqual(problems, [])

    def test_negation_duplicate_still_caught(self):
        problems = tool.check_lines(["!foo", "!foo"])
        self.assertEqual(len(problems), 1)

    def test_comments_and_blanks_skipped(self):
        lines = ["# build", "", "build/", "# build", "build/"]
        problems = tool.check_lines(lines)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["line"], 5)

    def test_case_sensitive(self):
        # Git patterns are case-sensitive on most systems, so
        # "Build" and "build" are different patterns.
        problems = tool.check_lines(["Build", "build"])
        self.assertEqual(problems, [])

    def test_empty_input(self):
        self.assertEqual(tool.check_lines([]), [])


class TestCheckFile(unittest.TestCase):
    def test_clean_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp) / ".gitignore", "build/\ndist/\n")
            problems, skipped = tool.check_file(path)
            self.assertEqual(problems, [])
            self.assertFalse(skipped)

    def test_duplicate_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp) / ".gitignore", "build/\nbuild\n")
            problems, _ = tool.check_file(path)
            self.assertEqual(len(problems), 1)
            self.assertIn("duplicate pattern", problems[0]["reason"])
            self.assertEqual(problems[0]["line"], 2)

    def test_missing_file_is_a_problem(self):
        problems, _ = tool.check_file(Path("/nonexistent/.gitignore"))
        self.assertEqual(len(problems), 1)
        self.assertIn("cannot read file", problems[0]["reason"])

    def test_non_utf8_file_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".gitignore"
            path.write_bytes(b"\xff\xfe bad bytes\n")
            problems, _ = tool.check_file(path)
            self.assertEqual(len(problems), 1)
            self.assertIn("UTF-8", problems[0]["reason"])

    def test_file_left_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp) / ".gitignore", "build/\nbuild\n")
            before = path.read_bytes()
            tool.check_file(path)
            self.assertEqual(path.read_bytes(), before)


class TestGather(unittest.TestCase):
    def test_direct_file_always_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp) / "notes.txt", "a\na\n")
            entries, checked, _ = tool.gather([str(path)], [], True)
            self.assertEqual(len(checked), 1)
            self.assertEqual(len(entries), 1)

    def test_folder_only_checks_gitignore_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / ".gitignore", "a\na\n")
            write(root / "other.txt", "a\na\n")
            write(root / "custom.gitignore", "b\nb\n")
            entries, checked, _ = tool.gather([str(root)], [], True)
            self.assertEqual(len(checked), 2)
            self.assertEqual(len(entries), 2)

    def test_git_folder_never_walked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / ".git" / ".gitignore", "a\na\n")
            write(root / ".gitignore", "ok\n")
            _entries, checked, _ = tool.gather([str(root)], [], True)
            self.assertEqual(len(checked), 1)
            self.assertEqual(checked[0]["file"], str(root / ".gitignore"))

    def test_no_recursive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / ".gitignore", "ok\n")
            write(root / "sub" / ".gitignore", "a\na\n")
            _entries, checked, _ = tool.gather([str(root)], [], False)
            self.assertEqual(len(checked), 1)

    def test_exclude_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / ".gitignore", "a\na\n")
            write(root / "sub" / ".gitignore", "b\nb\n")
            entries, checked, skipped = tool.gather(
                [str(root)], ["sub/.gitignore"], True
            )
            self.assertEqual(len(checked), 1)
            self.assertEqual(len(entries), 1)
            self.assertEqual(len(skipped), 1)

    def test_direct_file_checked_even_if_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp) / ".gitignore", "a\na\n")
            entries, checked, _ = tool.gather(
                [str(path)], [".gitignore"], True
            )
            self.assertEqual(len(checked), 1)
            self.assertEqual(len(entries), 1)

    def test_missing_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            tool.gather(["/nonexistent/path"], [], True)


class TestCLI(unittest.TestCase):
    def test_clean_file_exit_0(self):
        code, out, _err = run_cli("examples/good.gitignore")
        self.assertEqual(code, 0)
        self.assertIn("examples/good.gitignore: no duplicates", out)
        self.assertIn("no duplicate patterns found", out)

    def test_duplicates_exit_1(self):
        code, out, _err = run_cli("examples/duplicates.gitignore")
        self.assertEqual(code, 1)
        self.assertIn("FAIL examples/duplicates.gitignore:6:", out)
        self.assertIn("FAIL examples/duplicates.gitignore:9:", out)
        self.assertIn("FAIL examples/duplicates.gitignore:12:", out)
        self.assertIn("Checked 1 file(s), 3 problem(s) in 1 file(s).", out)

    def test_negation_exit_0(self):
        code, out, _err = run_cli("examples/negation.gitignore")
        self.assertEqual(code, 0)
        self.assertIn("no duplicates", out)

    def test_folder_walk(self):
        code, out, _err = run_cli("examples/")
        self.assertEqual(code, 1)
        self.assertIn("Checked 4 file(s), 4 problem(s) in 2 file(s).", out)
        self.assertIn("FAIL examples/sub/.gitignore:3:", out)

    def test_no_recursive_flag(self):
        code, out, _err = run_cli("--no-recursive", "examples/")
        self.assertEqual(code, 1)
        self.assertIn("Checked 3 file(s), 3 problem(s) in 1 file(s).", out)

    def test_stdin(self):
        code, out, _err = run_cli(
            "--stdin", stdin_text="build/\nbuild\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("FAIL <stdin>:2:", out)

    def test_stdin_clean(self):
        code, out, _err = run_cli("--stdin", stdin_text="build/\ndist/\n")
        self.assertEqual(code, 0)
        self.assertIn("no duplicate patterns found", out)

    def test_json_output(self):
        code, out, err = run_cli(
            "--json", "examples/duplicates.gitignore"
        )
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["summary"]["checked"], 1)
        self.assertEqual(data["summary"]["problems"], 3)
        self.assertEqual(data["summary"]["files_with_problems"], 1)
        self.assertEqual(len(data["files"][0]["problems"]), 3)
        self.assertEqual(data["files"][0]["problems"][0]["line"], 6)
        self.assertIn("Checked 1 file(s), 3 problem(s)", err)

    def test_json_clean(self):
        code, out, err = run_cli("--json", "examples/good.gitignore")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["summary"]["problems"], 0)
        self.assertIn("no duplicate patterns found", err)

    def test_version(self):
        code, out, _err = run_cli("--version")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "gitignore-duplicate-checker-cli 1.0.0")

    def test_missing_path_exit_2(self):
        code, _out, err = run_cli("/nonexistent/.gitignore")
        self.assertEqual(code, 2)
        self.assertIn("no such file or folder", err)

    def test_no_paths_exit_2(self):
        code, _out, err = run_cli()
        self.assertEqual(code, 2)
        self.assertIn("no .gitignore files to check", err)

    def test_empty_folder_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _out, err = run_cli(tmp)
            self.assertEqual(code, 2)
            self.assertIn("no .gitignore files to check", err)

    def test_bad_flag_exit_2(self):
        code, _out, err = run_cli("--nope")
        self.assertEqual(code, 2)
        self.assertIn("unrecognized arguments", err)


class TestBundledExamples(unittest.TestCase):
    def test_sample_output_matches_fresh_run(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)
        expected = (ROOT / "examples" / "sample-output.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(result.stdout, expected)

    def test_run_example_script_exits_zero(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)

    def test_readme_quotes_real_output(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for line in [
            "examples/good.gitignore: no duplicates",
            "OK — 1 file(s) checked, no duplicate patterns found.",
            "FAIL examples/duplicates.gitignore:6: duplicate pattern 'build' (first seen on line 2 as 'build/')",
            "FAIL examples/duplicates.gitignore:9: duplicate pattern 'dist/' (first seen on line 3 as 'dist/')",
            "FAIL examples/duplicates.gitignore:12: duplicate pattern 'build/' (first seen on line 2 as 'build/')",
            "Checked 1 file(s), 3 problem(s) in 1 file(s).",
            "FAIL examples/sub/.gitignore:3: duplicate pattern 'node_modules' (first seen on line 2 as 'node_modules/')",
            "Checked 4 file(s), 4 problem(s) in 2 file(s).",
        ]:
            self.assertIn(line, readme, f"README is missing real output: {line}")


class TestHygiene(unittest.TestCase):
    def _repo_files(self):
        # Hygiene scans exclude .git, __pycache__, and tests/ —
        # the test file itself names the banned words it scans
        # for, and its own path strings are not shipped content.
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d not in (".git", "__pycache__", "tests")
            )
            for name in filenames:
                yield Path(dirpath) / name

    def test_no_placeholder_text(self):
        banned = ["TODO", "coming soon", "lorem", "Lorem", "FIXME", "XXX"]
        for path in self._repo_files():
            if path.suffix in (".pyc",):
                continue
            text = path.read_bytes().decode("utf-8", errors="ignore")
            for word in banned:
                self.assertNotIn(
                    word, text, f"{word} found in {path.relative_to(ROOT)}"
                )

    def test_no_absolute_local_paths(self):
        for path in self._repo_files():
            text = path.read_bytes().decode("utf-8", errors="ignore")
            self.assertNotIn(
                "/home/hatch", text, f"absolute path in {path.relative_to(ROOT)}"
            )

    def test_stdlib_imports_only(self):
        source = (ROOT / "src" / "gitignore_duplicate_checker.py").read_text(
            encoding="utf-8"
        )
        stdlib = {
            "argparse",
            "fnmatch",
            "json",
            "os",
            "sys",
            "pathlib",
        }
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import "):
                names = stripped[7:].split(",")
                for name in names:
                    self.assertIn(
                        name.strip().split()[0], stdlib, f"non-stdlib import: {line}"
                    )
            elif stripped.startswith("from "):
                module = stripped[5:].split()[0]
                self.assertIn(
                    module.split(".")[0], stdlib, f"non-stdlib import: {line}"
                )

    def test_gitignore_first_line_is_env(self):
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_file_runs_the_test_file(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("tests/test_gitignore_duplicate_checker.py", ci)
        self.assertIn("setup-python", ci)


if __name__ == "__main__":
    unittest.main()
