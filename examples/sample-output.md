== good.gitignore: no duplicates, passes ==
examples/good.gitignore: no duplicates
OK — 1 file(s) checked, no duplicate patterns found.

== duplicates.gitignore: three duplicates ==
FAIL examples/duplicates.gitignore:6: duplicate pattern 'build' (first seen on line 2 as 'build/')
FAIL examples/duplicates.gitignore:9: duplicate pattern 'dist/' (first seen on line 3 as 'dist/')
FAIL examples/duplicates.gitignore:12: duplicate pattern 'build/' (first seen on line 2 as 'build/')
Checked 1 file(s), 3 problem(s) in 1 file(s).

== negation.gitignore: !important.log is not a duplicate of important.log ==
examples/negation.gitignore: no duplicates
OK — 1 file(s) checked, no duplicate patterns found.

== examples/: a folder walk, four problems ==
FAIL examples/duplicates.gitignore:6: duplicate pattern 'build' (first seen on line 2 as 'build/')
FAIL examples/duplicates.gitignore:9: duplicate pattern 'dist/' (first seen on line 3 as 'dist/')
FAIL examples/duplicates.gitignore:12: duplicate pattern 'build/' (first seen on line 2 as 'build/')
examples/good.gitignore: no duplicates
examples/negation.gitignore: no duplicates
FAIL examples/sub/.gitignore:3: duplicate pattern 'node_modules' (first seen on line 2 as 'node_modules/')
Checked 4 file(s), 4 problem(s) in 2 file(s).
