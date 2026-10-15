"""Smoke tests of the command line entry points, run in subprocesses.

The subprocesses import the throw-away copy of the package (see the
``package_copy`` fixture) by putting it first on ``PYTHONPATH``, hence
they cannot write into the source tree either.
"""

import os
import subprocess
import sys

import pytest

import cocopp


@pytest.fixture
def run_python(package_copy, tmp_path):
    """return a function running ``python args...`` in `tmp_path`, returning the `CompletedProcess`"""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(package_copy.parent)] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p])
    env["MPLBACKEND"] = "Agg"

    def run(*args, timeout=600, env_update=None):
        return subprocess.run(
            [sys.executable] + list(args), cwd=str(tmp_path), env=dict(env, **(env_update or {})), capture_output=True, text=True, timeout=timeout
        )

    return run


def test_subprocess_uses_package_copy(run_python, package_copy):
    res = run_python("-c", "import cocopp; print(cocopp.__file__)")
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().startswith(str(package_copy))


def test_import_is_quiet_and_fast(run_python):
    res = run_python("-c", "import time; t = time.time(); import cocopp; print('%.2f' % (time.time() - t))")
    assert res.returncode == 0, res.stderr
    assert res.stdout.splitlines()[-1] and float(res.stdout.splitlines()[-1]) < 20
    assert len(res.stdout.splitlines()) == 1  # nothing else printed on import


def test_version(run_python):
    res = run_python("-c", "import cocopp; print(cocopp.__version__)")
    assert res.stdout.strip() == cocopp.__version__


def test_cli_without_arguments_prints_usage(run_python):
    res = run_python("-m", "cocopp")
    assert res.returncode == 0, res.stderr
    assert "Main routine for post-processing data from COCO" in res.stdout


def test_cli_help(run_python):
    res = run_python("-m", "cocopp", "--help")
    assert res.returncode == 0 and "--output-dir" in res.stdout


def test_cli_unknown_option(run_python):
    res = run_python("-m", "cocopp", "--no-such-option", "x")
    assert "For help use -h or --help" in res.stderr


def test_cli_missing_data(run_python, tmp_path):
    res = run_python("-m", "cocopp", "--no-interactive", str(tmp_path / "does-not-exist"))
    assert res.returncode != 0
    assert "does-not-exist" in res.stderr


@pytest.mark.slow
def test_cli_postprocess_single(run_python, bbob_small, tmp_path):
    res = run_python("-m", "cocopp", "--no-interactive", "-o", "out", bbob_small)
    assert res.returncode == 0, res.stderr[-3000:]
    assert "ALL done" in res.stdout
    assert (tmp_path / "out" / "index.html").exists()
    (folder,) = [d for d in os.listdir(tmp_path / "out") if os.path.isdir(tmp_path / "out" / d)]
    assert folder.startswith("SMALL_")
    assert (tmp_path / "out" / folder / "pptable_f001_05D.tex").exists()


@pytest.mark.slow
def test_cli_postprocess_two(run_python, bbob_small, bbob_small_b, tmp_path):
    res = run_python("-m", "cocopp", "--no-interactive", "--no-svg", "-o", "out", bbob_small, bbob_small_b)
    assert res.returncode == 0, res.stderr[-3000:]
    (folder,) = [d for d in os.listdir(tmp_path / "out") if os.path.isdir(tmp_path / "out" / d)]
    assert folder.startswith("SMALL_SMALL_")
    assert (tmp_path / "out" / folder / "pptables_f001_05D.tex").exists()


@pytest.mark.slow
def test_python_api_main_twice(run_python, bbob_small, bbob_old_format):
    """corresponds to subtest 19 of the former ``cocopp/test.py``"""
    script = "import cocopp; cocopp.main(%r); cocopp.main(%r)" % ("--no-interactive -o a " + bbob_small, "--no-interactive -o b " + bbob_old_format)
    res = run_python("-c", script)
    assert res.returncode == 0, res.stderr[-3000:]
    assert res.stdout.count("ALL done") == 2


def test_reduce_size_cli(run_python, tmp_path):
    import synthdata

    folder = synthdata.write_bbob(str(tmp_path / "data"), "RED", functions=(1,), dims=(10,), seed=5)
    res = run_python("-m", "cocopp.reduce_size", "--help")
    assert res.returncode == 0 and "reduce_size" in res.stdout
    res = run_python("-m", "cocopp.reduce_size", folder)
    assert res.returncode == 0, res.stderr
    assert len([d for d in os.listdir(tmp_path / "data") if d.startswith("RED-")]) == 1
    res = run_python("-m", "cocopp.reduce_size")
    assert res.returncode != 0 and "needs a folder name" in res.stderr


def test_findfiles_from_shell(run_python, bbob_small):
    res = run_python("-c", "from cocopp.findfiles import main; print(len(main(%r)))" % bbob_small)
    assert res.returncode == 0 and res.stdout.strip() == "4"


@pytest.mark.xfail(reason="the order of inconsistent hv-hashes in the version label depends on PYTHONHASHSEED", strict=True)
def test_version_label_independent_of_hash_seed(run_python):
    script = (
        "import cocopp; cocopp.testbedsettings.reference_values = {'A': 'a1b2c3', 'B': 'z9y8x7', 'C': 'k5l6m7'};"
        " print(cocopp.toolsdivers.get_version_label())"
    )
    labels = set()
    for seed in range(8):
        res = run_python("-c", script, env_update={"PYTHONHASHSEED": str(seed)})
        assert res.returncode == 0, res.stderr
        labels.add(res.stdout.strip())
    assert len(labels) == 1, labels
