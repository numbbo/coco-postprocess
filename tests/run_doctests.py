"""Run the doctests of all modules of the `cocopp` package found on the path.

Usage::

    python tests/run_doctests.py

Replaces ``python -m cocopp.test doctest`` of the removed legacy test
runner. As before, each ``.py`` file of the package is run with
`doctest.testfile` from within the package folder, because some doctests
rely on relative paths. Many doctests need the online data archives and
some write files into the package folder, hence the test suite runs this
script in a subprocess on a throw-away copy of the package (see
``tests/network/test_archives_online.py``).

Exit with status 1 if any doctest fails.
"""

import doctest
import os
import sys

import matplotlib

matplotlib.use("Agg")


def main():
    import cocopp

    package_dir = os.path.dirname(os.path.abspath(cocopp.__file__))
    os.chdir(package_dir)
    failures, tests, failed_files = 0, 0, []
    for root, _dirs, files in sorted(os.walk(package_dir)):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            f, t = doctest.testfile(path, module_relative=False, report=True)
            failures, tests = failures + f, tests + t
            if f:
                failed_files.append("%s (%d of %d failed)" % (os.path.relpath(path, package_dir), f, t))
    print("doctests: %d of %d examples failed" % (failures, tests))
    for name in failed_files:
        print("  failed: " + name)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
