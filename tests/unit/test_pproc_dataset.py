"""Unit tests of `cocopp.pproc.DataSet` on a tiny hand-crafted data set.

The data (see `synthdata.TINY_TRIALS`) consist of three trials on f1 in
2-D with the following best-so-far Delta f values::

    instance 1: eval 1 -> 95,  eval 10 -> 0.9,  eval 50 -> 5e-9  (solved)
    instance 2: eval 1 -> 45,  eval 20 -> 4.5,  eval 100 -> 0.45 (not solved)
    instance 3: eval 1 -> 9.5, eval 5 -> 9e-4,  eval 30 -> 9e-10 (solved)

hence all expected values below can be (and were) computed by hand.
"""

import os
import pickle

import numpy as np
import pytest

import cocopp
from cocopp import genericsettings, pproc, testbedsettings

import synthdata

nan = np.nan
TARGETS = [100, 10, 1, 0.1, 1e-3, 1e-8]
EXPECTED_EVALS = [[1, 1, 1], [10, 20, 1], [10, 100, 5], [50, nan, 5], [50, nan, 5], [50, nan, 30]]
EXPECTED_ERT = [1, 31 / 3, 115 / 3, 155 / 2, 155 / 2, 180 / 2]
EXPECTED_SUCCESSES = [3, 3, 3, 2, 2, 2]


def assert_nan_equal(a, b):
    np.testing.assert_array_equal(np.asarray(a, dtype=float), np.asarray(b, dtype=float))


@pytest.fixture
def tiny(tmp_path, quiet):
    testbedsettings.reset_current_testbed()
    info = synthdata.write_tiny_bbob(str(tmp_path))
    dsl = pproc.DataSetList(info)
    assert len(dsl) == 1
    return dsl[0]


def _load_tiny(tmp_path, name, trials, **kwargs):
    testbedsettings.reset_current_testbed()
    return pproc.DataSetList(synthdata.write_tiny_bbob(str(tmp_path), name, trials=trials, **kwargs))[0]


class TestReading:
    def test_header_attributes(self, tiny):
        assert (tiny.funcId, tiny.dim, tiny.algId) == (1, 2, "TINY")
        assert tiny.precision == 1e-8
        assert tiny.suite_name == "bbob"
        assert tiny.get_data_format() == "bbob-new2"
        assert tiny.comment == "% TINY: hand-crafted test data"
        assert not tiny.isBiobjective()
        assert not tiny.has_constraints
        assert repr(tiny) == "DataSet(TINY on f1 2-D)"

    def test_loading_sets_current_testbed(self, tiny):
        assert isinstance(testbedsettings.current_testbed, testbedsettings.GECCOBBOBTestbed)

    def test_run_information_from_info_file(self, tiny):
        assert tiny.instancenumbers == [1, 2, 3]
        assert tiny.readmaxevals == [50, 100, 30]
        # f - ftarget as written with one digit precision by `write_tiny_bbob`
        assert tiny.readfinalFminusFtarget == [-5e-9, 0.45, -9.1e-9]
        assert tiny.isFinalized == [True, True, True]
        assert tiny.dataFiles == [os.path.join("data_f1", "bbobexp_f1_DIM2.dat")]

    def test_maxevals_and_finalfunvals(self, tiny):
        assert list(tiny.maxevals) == [50, 100, 30]
        assert tiny.max_eval == 100 == tiny.mMaxEvals()
        assert list(tiny.finalfunvals) == pytest.approx([5e-9, 0.45, 9e-10])
        assert tiny.nbRuns() == tiny.nbRuns_raw == 3

    def test_evals_first_row_and_targets(self, tiny):
        assert list(tiny.evals[0, 1:]) == [1, 1, 1]
        assert tiny.evals[0, 0] == pytest.approx(100)  # 10**(i/5) just above 95
        assert all(np.diff(tiny.evals[:, 0]) < 0)
        # targets are on the 10**(i/5) grid, the last is cut just below precision 1e-8
        grid = np.log10(tiny.evals[:-1, 0]) * 5
        assert grid == pytest.approx(np.round(grid))
        assert tiny.evals[-1, 0] == pytest.approx(1e-8 / 1.001)
        assert all(tiny.evals[:, 0] == tiny.target)

    def test_funvals(self, tiny):
        assert_nan_equal(
            tiny.funvals,
            [
                [1, 95, 45, 9.5],
                [5, 95, 45, 9e-4],
                [10, 0.9, 45, 9e-4],
                [20, 0.9, 4.5, 9e-4],
                [30, 0.9, 4.5, 9e-10],
                [50, 5e-9, 4.5, 9e-10],
                [100, 5e-9, 0.45, 9e-10],
            ],
        )

    def test_consistency_check(self, tiny):
        with pytest.warns(UserWarning, match="less than 15 instances"):
            assert tiny.consistency_check() is False


class TestRuntimes:
    def test_detEvals(self, tiny):
        for res, expected in zip(tiny.detEvals(TARGETS), EXPECTED_EVALS):
            assert_nan_equal(res, expected)

    def test_detEvals_order_follows_input(self, tiny):
        rev = tiny.detEvals(TARGETS[::-1])
        for res, expected in zip(rev, EXPECTED_EVALS[::-1]):
            assert_nan_equal(res, expected)

    def test_detEvals_too_difficult_target(self, tiny):
        assert all(np.isnan(tiny.detEvals([1e-12])[0]))

    def test_detEvals_complement_unsuccessful(self, tiny):
        assert list(tiny.detEvals([1e-8], complement_unsuccessful=-1)[0]) == [50, -100, 30]
        assert list(tiny.detEvals([1e-8], complement_unsuccessful=lambda m: m + 1)[0]) == [50, 101, 30]
        assert np.isnan(tiny.detEvals([1e-8])[0][1])  # data are not changed

    def test_detEvals_by_instance(self, tiny):
        assert list(tiny.detEvals([10], instance=2)[0]) == [20]
        res = tiny.detEvals_by_instance([10, 1])
        assert list(res) == [1, 2, 3]
        assert [list(v[1]) for v in res.values()] == [[10], [100], [5]]
        with pytest.raises(ValueError):
            tiny.detEvals([10], instance=7)

    def test_detEvals_bootstrap_draws_from_data(self, tiny):
        res = tiny.detEvals([1], bootstrap=True)[0]
        assert len(res) == 3 and set(res) <= {10, 100, 5}

    def test_detEvals2_agrees(self, tiny):
        for a, b in zip(tiny._detEvals2(TARGETS), tiny.detEvals(TARGETS)):
            assert_nan_equal(a, b)

    def test_detERT_and_ert(self, tiny):
        assert tiny.detERT(TARGETS) == pytest.approx(EXPECTED_ERT)
        assert tiny.detERT([1e-12]) == [np.inf]
        assert len(tiny.ert) == len(tiny.target)
        assert tiny.ert[0] == 1

    def test_detSuccesses(self, tiny):
        assert tiny.detSuccesses(TARGETS) == EXPECTED_SUCCESSES
        assert list(tiny.detSuccessRates(TARGETS)) == pytest.approx(np.array(EXPECTED_SUCCESSES) / 3)
        assert tiny.successes_by_instance() == {1: 1, 2: 0, 3: 1}

    def test_detAverageEvals(self, tiny):
        # sum(evals of successes + maxevals of failures) / nbRuns == ERT * success rate
        expected = [1, 31 / 3, 115 / 3, 155 / 3, 155 / 3, 180 / 3]
        assert list(tiny.detAverageEvals(TARGETS)) == pytest.approx(expected)

    def test_generateRLData(self, tiny):
        res = tiny.generateRLData([10, 1e-8])
        assert list(res[10][1:]) == [10, 20, 1]
        assert_nan_equal(res[1e-8][1:], [50, nan, 30])

    def test_median_evals(self, tiny):
        assert_nan_equal(tiny.median_evals([10, 1, 1e-8]), [10, 10, 50])
        assert tiny.median_evals()[0] == 1

    def test_number_of_better_runs(self, tiny):
        assert tiny._number_of_better_runs(1, 10) == 1.5  # 5 < 10, 10 == 10 counts 1/2
        assert tiny._number_of_better_runs([1, 1e-8], np.nan) == [3, 2]

    def test_info_str(self, tiny):
        s = tiny.info_str()
        assert "Algorithm: TINY" in s and "Number of trials: 3" in s
        assert "min / max number of evals per trial: 30 / 100" in s
        assert "  1.0e+01 |       0       0       5      10      10 |      5.2   3" in s


class TestInstances:
    def test_instance_bookkeeping(self, tiny):
        assert tiny.createDictInstance() == {1: [0], 2: [1], 3: [2]}
        assert tiny.createDictInstanceCount() == {1: 1, 2: 1, 3: 1}
        assert tiny.instance_index_lists() == {1: [0], 2: [1], 3: [2]}
        assert tiny.trial_count_by_instance == {1: 1, 2: 1, 3: 1}
        assert tiny.instance_multipliers == (1, 1, 1)
        assert tiny.instancenumbers_balanced == [1, 2, 3]
        assert not tiny._need_balancing
        assert tiny._instance_repetitions == 0

    def test_budget_effective_estimates(self, tiny):
        assert tiny.budget_effective_estimates == {1: 50, 2: 100, 3: 30}
        assert tiny._budget_estimates == {1: 50, 2: 100, 3: 30}

    def test_splitByTrials(self, tiny):
        evals, funvals = tiny.splitByTrials()
        assert set(evals) == {1, 2, 3}
        assert evals[2].shape == (len(tiny.evals), 1, 1)
        assert tiny.splitByTrials("evals").keys() == evals.keys()
        assert tiny.splitByTrials("funvals")[3][0, 0, 0] == 9.5

    def test_balancing_repeated_instances(self, tmp_path, quiet):
        trials = [(1, synthdata.TINY_TRIALS[1]), (1, synthdata.TINY_TRIALS[2]), (2, synthdata.TINY_TRIALS[3])]
        ds = _load_tiny(tmp_path, "REP", trials)
        assert ds.instancenumbers == [1, 1, 2]
        assert ds.instance_multipliers == (1, 1, 2)
        assert ds.instancenumbers_balanced == (1, 1, 2, 2)
        assert ds.nbRuns() == 4 and ds.nbRuns_raw == 3
        assert list(ds.maxevals) == [50, 100, 30, 30]
        assert_nan_equal(ds.evals[-1, 1:], [50, nan, 30, 30])
        assert ds.detERT([1e-8]) == pytest.approx([(50 + 100 + 30 + 30) / 3])
        assert ds.detSuccesses([1e-8]) == [3]
        assert ds.detSuccesses([1e-8], raw_values=True) == [2]

    def test_balancing_can_be_switched_off(self, tmp_path, quiet, monkeypatch):
        trials = [(1, synthdata.TINY_TRIALS[1]), (1, synthdata.TINY_TRIALS[2]), (2, synthdata.TINY_TRIALS[3])]
        ds = _load_tiny(tmp_path, "REP", trials)
        monkeypatch.setattr(genericsettings, "balance_instances", False)
        assert ds.nbRuns() == 3
        assert ds.detERT([1e-8]) == pytest.approx([180 / 2])

    def test_evals_appended(self, tmp_path, quiet, monkeypatch):
        trials = [(1, synthdata.TINY_TRIALS[2]), (1, synthdata.TINY_TRIALS[1]), (2, synthdata.TINY_TRIALS[3])]
        ds = _load_tiny(tmp_path, "APP", trials)
        assert not ds.evals_are_appended  # too few remaining trials by default
        monkeypatch.setattr(genericsettings, "appended_evals_minimal_trials", 2)
        assert ds.evals_are_appended
        app = ds.evals_appended
        assert app.shape == (len(ds._evals), 3)
        # instance 1: the failed first run (100 evals) is restarted with the second run
        assert app[-1, 1] == 100 + 50


class TestSimulatedRestarts:
    def test_all_successful_target_reproduces_data(self, tiny):
        sim = tiny.evals_with_simulated_restarts([1], samplesize=3)[0]
        assert sorted(sim) == [5, 10, 100]

    def test_restarts_add_unsuccessful_runs(self, tiny):
        sim = tiny.evals_with_simulated_restarts([1e-8], samplesize=300)[0]
        assert len(sim) == 300
        # each simulated run = k * 100 (failed trial) + 50 or 30 (successful trial)
        assert np.all(np.isin(sim % 100, [30, 50]))

    def test_default_samplesize(self, tiny):
        sim = tiny.evals_with_simulated_restarts([1e-8])[0]
        assert len(sim) == 45  # smallest multiple of nbRuns() >= 45

    def test_unsolved_target_gives_nan(self, tiny):
        assert all(np.isnan(tiny.evals_with_simulated_restarts([1e-12], samplesize=6)[0]))

    def test_within_instance_restarts(self, tiny):
        sim = tiny.evals_with_simulated_restarts([1e-8], samplesize=30, instances_are_uniform=False)[0]
        assert len(sim) == 30
        assert np.sum(np.isnan(sim)) == 10  # instance 2 never succeeds
        assert set(sim[np.isfinite(sim)]) == {50, 30}  # no restarts across instances

    def test_within_instance_restarts_singular_instances_characterization(self, tiny):
        # with one trial per instance and default samplesize, the data are returned as is,
        # with unsuccessful runs as negative maxevals (see the xfail test below)
        sim = tiny.evals_with_simulated_restarts([1e-8], instances_are_uniform=False)[0]
        assert list(sim) == [50, -100, 30]

    @pytest.mark.xfail(reason="docstring says unsuccessful runs are nan, but they are returned as -maxevals", strict=True)
    def test_within_instance_restarts_singular_instances_documented(self, tiny):
        sim = tiny.evals_with_simulated_restarts([1e-8], instances_are_uniform=False)[0]
        assert np.isnan(sim[1])

    def test_percentiles(self, tiny):
        res = tiny.percentiles([10, 1e-12], prctiles=50)
        assert res[0] == 10 and np.isnan(res[1])
        assert len(tiny.percentiles([1], (10, 90))[0]) == 2

    def test_bootstrap_sample_size(self, tiny):
        assert tiny.bootstrap_sample_size(10) == 12
        assert tiny.bootstrap_sample_size(0) == 3


class TestMisc:
    def test_equality(self, tiny, tmp_path, quiet):
        other = _load_tiny(tmp_path / "x", "TINY", synthdata.TINY_TRIALS)
        assert tiny == other and not tiny != other
        assert tiny._data_differ(other) == []
        other3 = _load_tiny(tmp_path / "y", "TINY", {1: synthdata.TINY_TRIALS[1], 2: synthdata.TINY_TRIALS[3]})
        assert tiny._data_differ(other3)  # different data
        other.algId = "OTHER"
        assert tiny != other

    def test_pickle_roundtrip(self, tiny):
        ds = pickle.loads(pickle.dumps(tiny))
        assert ds == tiny and not ds._data_differ(tiny)
        assert ds.detERT(TARGETS) == pytest.approx(EXPECTED_ERT)

    def test_pickle_to_file(self, tiny, tmp_path):
        tiny.pickle(str(tmp_path))
        assert os.path.exists(tmp_path / "ppdata_f001_02.pickle.gz")

    def test_argsort(self, tiny):
        # columns sorted from best to worst: instance 3 (30 evals), 1 (50), 2 (failed)
        assert list(tiny._argsort()) == [3, 1, 2]

    def test_largest_finite_index(self):
        f = pproc.DataSet._largest_finite_index
        assert f(np.array([1.0, 2, nan, nan])) == 1
        assert f(np.array([nan, nan])) == -1
        assert f(np.array([1.0, 2, 3])) == 2

    def test_plot_smoke(self, tiny):
        ax = tiny.plot()
        assert "F1 in dimension 2" in ax.get_title()
        with pytest.raises(ValueError):
            tiny.plot(smallest_target=1e6)

    def test_number_of_constraints_not_available_for_bbob(self, tiny):
        with pytest.raises(NotImplementedError):
            tiny.number_of_constraints


def test_constrained_evaluations_are_summed(tmp_path, quiet):
    trials = {1: [(1, 2, 95.0), (10, 30, 0.9), (50, 80, 5e-9)], 2: [(1, 2, 45.0), (20, 40, 4.5), (100, 150, 0.45)]}
    ds = _load_tiny(tmp_path, "CONS", trials, suite="bbob-constrained")
    assert testbedsettings.current_testbed.name == "bbob-constrained"
    assert ds.has_constraints
    assert ds.readmaxevals == [50, 100]  # f-evaluations only
    assert list(ds.maxevals) == [130, 250]  # f + g from the last .tdat line
    assert list(ds.evals[0, 1:]) == [3, 3]
    assert list(ds.detEvals([1])[0]) == [40, 250]
    assert list(ds.evals_function[0, 1:]) == [1, 1]
    assert list(ds.evals_constraints[0, 1:]) == [2, 2]
    assert ds.number_of_constraints == 1


def test_constrained_evaluation_weights(tmp_path, quiet, monkeypatch):
    trials = {1: [(1, 2, 95.0), (10, 30, 0.9), (50, 80, 5e-9)]}
    monkeypatch.setattr(genericsettings, "weight_evaluations_constraints", [1, 0])
    ds = _load_tiny(tmp_path, "CONS0", trials, suite="bbob-constrained")
    assert not ds.has_constraints  # g-evaluations are ignored entirely
    assert list(ds.detEvals([1])[0]) == [10]


def test_instances_of_interest_filter(tmp_path, quiet, monkeypatch):
    monkeypatch.setitem(testbedsettings.GECCOBBOBTestbed.settings, "instancesOfInterest", [1, 3])
    ds = _load_tiny(tmp_path, "TINY", synthdata.TINY_TRIALS)
    assert ds.instancenumbers == [1, 3]
    assert_nan_equal(ds.detEvals([1e-8])[0], [50, 30])


def test_old_data_format(bbob_old_format, quiet):
    testbedsettings.reset_current_testbed()
    dsl = pproc.DataSetList(bbob_old_format)
    assert len(dsl) == 4
    ds = dsl[0]
    assert ds.get_data_format() is None
    assert ds.suite_name == "bbob"
    assert ds.instancenumbers == list(range(1, 16))
    assert ds.evals.shape[1] == 16


def test_suite_name_fallbacks(tiny):
    del tiny.suite
    assert tiny.suite_name == "bbob"
    tiny.funcId = 101
    assert tiny.suite_name == "bbob-noisy"
    tiny.suite = "sbox-cost"
    assert tiny.suite_name == "bbob-boxed"


def test_cococommands_load(tiny, tmp_path, quiet):
    info = synthdata.write_tiny_bbob(str(tmp_path / "load"))
    dsl = cocopp.load(info)
    assert len(dsl) == 1 and dsl[0] == tiny
