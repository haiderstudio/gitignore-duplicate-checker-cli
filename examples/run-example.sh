#!/bin/sh
# Check the bundled examples. The failing runs exit 1 on purpose,
# so each one ends with "|| true"; the script itself ends with
# exit 0 so it can be run as a demo. Run from the repo root:
# sh examples/run-example.sh
cd "$(dirname "$0")/.."
echo "== good.gitignore: no duplicates, passes =="
python3 src/gitignore_duplicate_checker.py examples/good.gitignore || true
echo
echo "== duplicates.gitignore: three duplicates =="
python3 src/gitignore_duplicate_checker.py examples/duplicates.gitignore || true
echo
echo "== negation.gitignore: !important.log is not a duplicate of important.log =="
python3 src/gitignore_duplicate_checker.py examples/negation.gitignore || true
echo
echo "== examples/: a folder walk, four problems =="
python3 src/gitignore_duplicate_checker.py examples/ || true
