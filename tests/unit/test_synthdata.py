"""Sanity checks of the synthetic test data (`synthdata`) themselves.

If these fail, the data generator rather than `cocopp` is likely broken.
Note that `DataSetList` only *prints* I/O errors, hence a broken
generator can silently lead to empty data sets.
"""

import filecmp
import os

import numpy as np
import pytest

from cocopp import testbedsettings

import synthdata
from conftest import load


@pytest.mark.parametrize(
    "fixture, n_datasets, n_runs, suite",
    [
        ("bbob_alg_a", 24 * 5, 15, "bbob"),
        ("bbob_small", 4 * 2, 15, "bbob"),
        ("bbob_old_format", 2 * 2, 15, "bbob"),
        ("biobj_alg", 55 * 3, 10, "bbob-biobj"),
    ],
)
def test_fixture_data_load_completely(request, fixture, n_datasets, n_runs, suite):
    testbedsettings.reset_current_testbed()
    dsl = load(request.getfixturevalue(fixture))
    assert len(dsl) == n_datasets
    assert all(ds.nbRuns() == n_runs for ds in dsl)
    assert {ds.suite_name for ds in dsl} == {suite}
    assert testbedsettings.current_testbed.name == suite


def test_success_rates_are_mixed(bbob_alg_a):
    """the data should exercise both solved and unsolved code paths in all dimensions"""
    testbedsettings.reset_current_testbed()
    dsl = load(bbob_alg_a)
    for dim, dsl_dim in dsl.dictByDim().items():
        succ = [ds.detSuccesses([1e-8])[0] for ds in dsl_dim]
        assert max(succ) == 15 and min(succ) < 5, (dim, succ)
        assert any(0 < s < 15 for s in succ)


def test_generator_is_deterministic(tmp_path):
    np.random.seed(1)
    a = synthdata.write_bbob(str(tmp_path / "1"), "X", functions=(1, 7), dims=(2, 3), seed=3)
    np.random.seed(2)  # the global state must not matter
    b = synthdata.write_bbob(str(tmp_path / "2"), "X", functions=(1, 7), dims=(2, 3), seed=3)
    c = synthdata.write_bbob(str(tmp_path / "3"), "X", functions=(1, 7), dims=(2, 3), seed=4)
    files = sorted(os.path.relpath(os.path.join(r, f), a) for r, _, fs in os.walk(a) for f in fs)
    match, mismatch, errors = filecmp.cmpfiles(a, b, files, shallow=False)
    assert not mismatch and not errors and len(match) == len(files) == 2 + 2 * 2 * 2
    assert filecmp.cmpfiles(a, c, files, shallow=False)[1]  # another seed gives other data


def test_tiny_data_files(tmp_path):
    info = synthdata.write_tiny_bbob(str(tmp_path))
    lines = open(info).read().splitlines()
    assert len(lines) == 3 and lines[2].endswith("1:50|-5.0e-09, 2:100|4.5e-01, 3:30|-9.1e-09")
