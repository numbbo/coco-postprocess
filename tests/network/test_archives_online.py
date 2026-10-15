"""Tests that need the official online COCO data archives.

These are skipped unless pytest is called with ``--run-network``. They
port the scenarios of the legacy test runner ``python -m cocopp.test``
(which is still used in CI) to pytest. Downloaded data are cached in
the user's cocopp cache folder (as with any use of `cocopp.archives`).

The full post-processing runs of the legacy "all" tests are additionally
marked ``slow``.
"""

import os
import subprocess
import sys

import pytest

import cocopp
from cocopp import archiving, pproc

import pipeline

pytestmark = pytest.mark.network


class TestOfficialArchives:
    def test_archive_names(self):
        names = cocopp.archives.names
        for suite in ["all", "bbob", "bbob-noisy", "bbob-biobj", "bbob-largescale", "bbob-mixint", "bbob-constrained"]:
            assert suite in names

    def test_find(self):
        found = cocopp.archives.bbob.find("bfgs")
        assert "2009/BFGS_ros_noiseless.tgz" in found
        assert cocopp.archives.bbob.find("bfgs") == cocopp.archives.bbob.find(".*bfgs")
        assert len(cocopp.archives.bbob.find("bfgs")) > len(cocopp.archives.bbob.find("bfgs.*"))
        assert cocopp.archives.all("bbob/2009/BFGS_ros") == ["bbob/2009/BFGS_ros_noiseless.tgz"]

    def test_names_are_unique(self):
        bbob = cocopp.archives.bbob
        for name in bbob:
            assert bbob.count(name) == 1 and len(bbob.find(name)) == 1, name

    def test_get_extended_patterns(self):
        arch = cocopp.archives.all
        assert len(arch.get_extended(["bbob/2009/BFGS_ros!"], remote=False)) == 1
        assert len(arch.get_extended(["bbob/2009/.*BFGS"], remote=False)) >= 1

    def test_remote_archives_list(self):
        urls = cocopp.remote_archives()
        assert len(urls) > 0 and all(u.startswith("http") for u in urls)

    def test_get_remote_archive_by_url(self):
        url = "https://cma-es.github.io/lq-cma/data-archives/lq-gecco2019"
        arch = archiving.get(url).update()
        assert len(arch) == 4
        assert arch.remote_data_path.split("//", 1)[1] == url.split("//", 1)[1]


def _run_official(args, tmp_path):
    return pipeline.run_main(args, tmp_path)


@pytest.mark.slow
@pytest.mark.parametrize(
    "args",
    [
        "bbob/2009/BFGS_ros_noiseless",  # legacy subtest 1
        "RANDOMSEARCH-4_Auger_bbob-biobj.tgz",  # legacy subtest 2
    ],
)
def test_postprocess_archived_data(args, tmp_path):
    run = _run_official(args, tmp_path)
    assert "ALL done" in run.stdout
    assert len(run.result) == 1


@pytest.mark.slow
def test_postprocess_constrained_archive_by_url(tmp_path):
    """legacy ``tmp_test_constrained``"""
    url = "https://numbbo.github.io/cocopp-playground/bbob-constrained/testdata/bbob-constrained"
    data_path = archiving.get(url).get("fmincon_consbbob")
    run = _run_official(data_path, tmp_path)
    assert "ALL done" in run.stdout


@pytest.mark.slow
@pytest.mark.parametrize(
    "args",
    [
        "BIPOP-CMA-ES_hansen_noiseless MCS_huyer_noiseless 2009/NEWUOA_ros_noiseless.tgz RANDOMSEARCH_auger_noiseless.tgz BFGS_ros_noiseless.tgz",
        "SMAC-BBOB_hutter_noiseless.tgz lmm-CMA-ES_auger_noiseless.tgz",
        "--include-single DE-PSO_garcia-nieto_noiseless.tgz VNS_garcia-martinez_noiseless.tgz",
        "--expensive VNS_garcia-martinez_noiseless.tgz",
        "RANDOMSEARCH-4_Auger_bbob-biobj.tgz RANDOMSEARCH-100_Auger_bbob-biobj.tgz",
        "NSGA-II-MATLAB_Auger_bbob-biobj.tgz RANDOMSEARCH-4_Auger_bbob-biobj.tgz RANDOMSEARCH-100_Auger_bbob-biobj.tgz",
        "MCS_huyer_noisy.tgz BFGS_ros_noisy.tgz",
        "test/RS-4.zip",
        "bbob/2009/BFGS! bbob-largescale/2019/LBFGS!",
        "NSGA-II! 2019/IBEA!",
        "constrained/2022/RandomSearch-5",
    ],
    ids=lambda a: a[:40],
)
def test_legacy_all_scenarios(args, tmp_path):
    """the "all" scenarios (subtests 3-20) of the legacy ``python -m cocopp.test all``"""
    run = _run_official(args, tmp_path)
    assert "ALL done" in run.stdout


@pytest.mark.slow
def test_legacy_main_twice_in_one_process(package_copy, tmp_path):
    """legacy subtest 19: post-process archived data twice in the same python session"""
    script = "import cocopp; cocopp.main('--no-interactive slsqp!'); cocopp.main('--no-interactive abc*')"
    env = dict(os.environ, PYTHONPATH=str(package_copy.parent), MPLBACKEND="Agg")
    res = subprocess.run([sys.executable, "-c", script], cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=3600)
    assert res.returncode == 0, res.stdout[-3000:] + res.stderr[-3000:]
    assert res.stdout.count("ALL done") == 2


def test_pickle_regression(quiet):
    """legacy ``do_pickle_regression_test``: data read from a pickle file equal data read from the archive"""
    name = cocopp.archives.all.get_extended("strained/2022/al3-cma")[0]
    dsl1 = pproc.get_DataSetList(name)
    if not pproc._pickle_file_read:
        dsl1 = pproc.get_DataSetList(name)  # second call reads the pickle written by the first
    assert pproc._pickle_file_read
    old, pproc._ignore_pickle_files = pproc._ignore_pickle_files, True
    try:
        dsl2 = pproc.get_DataSetList(name)
    finally:
        pproc._ignore_pickle_files = old
    assert not pproc._pickle_file_read
    dsl2._is_same_list_assert(dsl1)


@pytest.mark.slow
def test_package_doctests(package_copy):
    """run the doctests of all modules like ``python -m cocopp.test doctest`` (the CI does this)

    The doctests run in the throw-away package copy because they change
    into the package folder and may write files there.
    """
    env = dict(os.environ, PYTHONPATH=str(package_copy.parent), MPLBACKEND="Agg")
    res = subprocess.run([sys.executable, "-m", "cocopp.test", "doctest"], cwd=str(package_copy.parent), env=env, capture_output=True, text=True, timeout=1800)
    assert res.returncode == 0, res.stdout[-5000:] + res.stderr[-5000:]
