"""Unit tests for `cocopp.toolsstats` (statistics and bootstrapping helpers).

Where a function draws random numbers, either properties that hold for
every draw are tested or numpy's global random state is fixed (the
autouse fixture in ``conftest.py`` seeds it before each test).
"""

import math

import numpy as np
import pytest

from cocopp import toolsstats as ts

nan, inf = np.nan, np.inf


class TestSuccessPerformance:
    def test_sp1_all_successful(self):
        assert ts.sp1([1, 2, 3]) == (2.0, 1.0, 3)

    def test_sp1_with_maxvalue(self):
        # data >= maxvalue count as unsuccessful: mean(successful) / success rate
        res = ts.sp1([1, 2, 3, 10], maxvalue=5)
        assert res == pytest.approx((2.0 / 0.75, 0.75, 3))

    def test_sp1_with_issuccessful_and_nan(self):
        res = ts.sp1([1, nan, 3, 4], issuccessful=[True, True, False, True])
        # the nan entry is removed first, then 2 of 3 remaining are successful
        assert res == pytest.approx((2.5 / (2 / 3), 2 / 3, 2))

    def test_sp1_no_success_and_empty(self):
        assert ts.sp1([5, 6], maxvalue=1) == (inf, 0.0, 0)
        res = ts.sp1([nan, nan])
        assert all(np.isnan(r) for r in res)

    def test_sp_is_ert(self):
        # sum of all evaluations / number of successes
        assert ts.sp([1, 2, 3, 10], maxvalue=5) == pytest.approx((16 / 3, 0.75, 3))
        assert ts.sp([1, 2, 3]) == (2.0, 1.0, 3)

    def test_sp_no_success(self):
        assert ts.sp([5, 6], maxvalue=1) == (inf, 0.0, 0)
        assert ts.sp([5, 6], maxvalue=1, allowinf=False) == (11, 0.0, 0)

    def test_sp_issuccessful_with_nan_regression(self):
        # regression test for the bug fixed in July 2025 (sorting broke the
        # alignment between data and issuccessful when data contained nan)
        res = ts.sp([10, nan, 1, 5], issuccessful=[False, True, True, True])
        assert res == pytest.approx((16 / 2, 2 / 3, 2))

    @pytest.mark.parametrize("func", [ts.sp, ts.sp1])
    def test_input_validation(self, func):
        with pytest.raises(Exception):
            func(3)
        with pytest.raises(Exception):
            func([1, 2], issuccessful=3)
        with pytest.raises(Exception):
            func([1, 2], issuccessful=[True])


class TestPrctile:
    def test_docstring_example(self):
        pp = ts.prctile([2, 3, nan, 1], [5, 25, 50, 75, 95], ignore_nan=False)
        assert pp[:3] == [1.0, 1.5, 2.5]
        assert np.isnan(pp[3]) and np.isnan(pp[4])

    @pytest.mark.parametrize("n", [1, 2, 5, 15, 100])
    def test_agrees_with_numpy_hazen(self, n):
        rng = np.random.default_rng(n)
        x = rng.lognormal(size=n)
        p = [0, 2, 10, 25, 50, 75, 90, 98, 100]
        assert ts.prctile(x, p) == pytest.approx(np.percentile(x, p, method="hazen"))

    def test_scalar_and_out_of_range(self):
        x = [3, 1, 2]
        assert ts.prctile(x, 50) == [2]
        assert ts.prctile(x, [-10, 110]) == [1, 3]

    def test_ignores_none_and_nan_by_default(self):
        assert ts.prctile([None, 1, nan, 3], [50]) == [2.0]

    def test_empty(self):
        assert all(np.isnan(ts.prctile([], [10, 50])))

    def test_infinite_values_use_proximity(self):
        assert ts.prctile([1, 2, inf, inf], [60]) == [inf]
        assert ts.prctile([1, 2, inf, inf], [40]) == [2]

    def test_issorted_skips_sorting(self):
        # documents that issorted=True trusts the caller
        assert ts.prctile([3, 1, 2], [0], issorted=True) == [3]


class TestRandint:
    def test_randint_derandomized_docstring(self):
        np.random.seed(1)
        assert [int(i) for i in ts.randint_derandomized(0, 4, 6)] == [3, 2, 0, 1, 0, 2]

    @pytest.mark.parametrize("low, high, size", [(0, 5, None), (2, 7, 23), (10, None, 37), (0, 1, 3)])
    def test_each_value_once_per_chunk(self, low, high, size):
        res = ts.randint_derandomized(low, high, size)
        lo, hi = (0, low) if high is None else (low, high)
        n = hi - lo
        assert len(res) == (n if size is None else size)
        assert res.min() >= lo and res.max() < hi
        for i in range(0, len(res) - n + 1, n):
            assert sorted(res[i : i + n]) == list(range(lo, hi))

    def test_randint(self):
        r = ts.randint(5, 1000)
        assert r.shape == (1000,) and r.min() >= 0 and r.max() <= 4
        assert np.all(r == np.floor(r))

    def test_fix_data_number(self):
        data = [1, 2, 4]
        for n in [1, 3, 4, 14]:
            assert len(ts.fix_data_number(data, n)) == n
        assert ts.fix_data_number(data, 14)[2] == data[2]
        assert list(ts.fix_data_number(np.arange(10), 4, last_elements_randomized=False)) == [0, 1, 2, 3]
        with pytest.warns(UserWarning):
            ts.fix_data_number(data, 5, warn=True)


class TestSimulatedEvals:
    def test_docstring_example(self):
        np.random.seed(4)
        res = ts.simulated_evals(np.hstack([[1], [2, 4, 2, 6, 100]]), 5, 13)
        assert [int(i) for i in res[:3]] == [1, 1, 3]

    def test_all_successful_returns_resampled_data(self):
        evals = np.array([3.0, 5, 7])
        res = ts.simulated_evals(evals, 0, 9, return_as=np.asarray)
        assert sorted(res) == sorted(3 * list(evals))  # derandomized: each exactly 3 times

    def test_all_unsuccessful(self):
        for return_as in (sorted, list, np.asarray, np.array, tuple):
            res = ts.simulated_evals([1, 2], 2, 4, return_as=return_as)
            assert len(res) == 4 and all(np.isnan(res))

    def test_sums_contain_exactly_one_successful_run(self):
        succ, fail = [1, 10], [1000, 100000]
        res = ts.simulated_evals(succ + fail, len(fail), 200, return_as=np.asarray)
        # every value = (sum of failures) + (one success); success evals are < 1000
        assert np.all(np.isin(res % 1000, succ))

    def test_negative_convention(self):
        # nfails=-1: unsuccessful runs are given as negative values in any position
        res = ts.simulated_evals(np.array([-1000.0, 1, -100000, 10]), -1, 200, return_as=np.asarray)
        assert np.all(res > 0)
        assert np.all(np.isin(res % 1000, [1, 10]))

    def test_inconsistent_nfails(self):
        with pytest.raises(ValueError):
            ts.simulated_evals([1, 2], 3)

    def test_return_sorted_by_default(self):
        res = ts.simulated_evals([5, 1, 3], 0, 9)
        assert res == sorted(res)


class TestDraw:
    def test_drawSP_properties(self):
        prc, values = ts.drawSP([1, 2], [10, 20], [50], samplesize=100)
        assert len(values) == 100 and values == sorted(values)
        # each value is a (possibly empty) sum of failures plus one success
        assert all(v - 1 in _sums_of([10, 20], 50) or v - 2 in _sums_of([10, 20], 50) for v in values)
        assert prc == ts.prctile(values, [50], issorted=True)

    def test_drawSP_no_success_raises(self):
        with pytest.raises(NotImplementedError):
            ts.drawSP([], [10], [50])

    def test_draw_bootstrap_of_sp1(self):
        data = np.arange(1, 11)
        prc, values = ts.draw(data, [0, 50, 100], samplesize=200)
        assert len(values) == 200
        assert values == sorted(values)
        assert 1 <= prc[0] <= prc[1] <= prc[2] <= 10
        assert prc[1] == pytest.approx(5.5, abs=1.0)

    def test_draw_is_reproducible_with_seed(self):
        np.random.seed(5)
        r1 = ts.draw(np.arange(10), [50], samplesize=50)
        np.random.seed(5)
        r2 = ts.draw(np.arange(10), [50], samplesize=50)
        assert r1 == r2

    def test_drawSP_from_dataset_new_not_implemented(self):
        with pytest.raises(NotImplementedError):
            ts.drawSP_from_dataset_new(None, 1, None)


def _sums_of(values, max_terms):
    """all sums of up to `max_terms` elements drawn with replacement from `values`"""
    sums = {0}
    for _ in range(max_terms):
        sums |= {s + v for s in sums for v in values if s + v <= max_terms * max(values)}
    return sums


class TestRankSum:
    def test_ranksum_statistic_against_brute_force(self):
        rng = np.random.default_rng(1)
        x, y = rng.integers(0, 10, 7), rng.integers(0, 10, 9)
        expected = sum((yj < xi) + 0.5 * (yj == xi) for xi in x for yj in y)
        assert ts.ranksum_statistic(x, y) == expected

    def test_rankdata_with_ties(self):
        assert list(ts.rankdata([0, 2, 2, 3])) == [1.0, 2.5, 2.5, 4.0]
        assert list(ts.rankdata([[3, 1], [2, 2]])) == [4.0, 1.0, 2.5, 2.5]

    def test_fastsort(self):
        s, i = ts.fastsort(np.array([3, 1, 2]))
        assert list(s) == [1, 2, 3] and list(i) == [1, 2, 0]

    @pytest.mark.parametrize("z", [-7, -3, -1.5, -0.2, 0, 0.3, 1.0, 1.96, 2.5, 4, 8])
    def test_zprob_is_normal_cdf(self, z):
        assert float(ts.zprob(np.array(z))) == pytest.approx(0.5 * (1 + math.erf(z / math.sqrt(2))), abs=1e-6)

    def test_ranksumtest(self):
        x = [1, 2, 3, 4, 5]
        y = [6, 7, 8, 9, 10]
        z, p = ts.ranksumtest(x, y)
        n1, n2 = 5, 5
        expected_z = (15 - n1 * (n1 + n2 + 1) / 2) / math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
        assert z == pytest.approx(expected_z)
        assert p == pytest.approx(2 * (1 - 0.5 * (1 + math.erf(abs(expected_z) / math.sqrt(2)))), abs=1e-6)
        z2, p2 = ts.ranksumtest(y, x)
        assert z2 == pytest.approx(-z) and p2 == pytest.approx(p)

    def test_ranksumtest_identical_samples(self):
        z, p = ts.ranksumtest([1, 2, 3], [1, 2, 3])
        assert z == 0 and p == pytest.approx(1.0)


class TestBestAlgIndices:
    def test_from_ert_arrays(self):
        erts = np.array([[1, 5, inf], [2, 3, inf]])
        idx = ts.best_alg_indices(ert_ars=erts, median_finalfunvals=[0.5, 0.1])
        assert list(idx) == [0, 1, 1]  # last target: no ERT, best median final f-value


def test_sliding_window_data():
    np.random.seed(2)
    data = np.array([1.0, 3, 2, 5, inf, 4, 6])
    smooth, stats = ts.sliding_window_data(data, width=3, number_of_stats=2)
    assert isinstance(smooth, np.ndarray) and len(smooth) == len(data)
    assert smooth[0] == np.median([1, 3])
    assert smooth[4] == inf  # non-finite data are kept
    assert smooth[3] == np.median([2, 5])  # non-finite neighbors are ignored
    assert all(len(s[1]) == 7 for s in stats)


def test_sliding_window_data_small_width_is_identity():
    data = [1, 2, 3]
    assert ts.sliding_window_data(data, width=1) == (data, [])


@pytest.mark.xfail(reason="known bug: default number_of_stats=0 divides by zero", raises=ZeroDivisionError, strict=True)
def test_sliding_window_data_default_number_of_stats():
    ts.sliding_window_data([1.0, 2, 3, 4], width=2)


@pytest.mark.xfail(reason="known bug: malformed warning message formatting", raises=TypeError, strict=True)
def test_sliding_window_data_too_wide_window_warns():
    ts.sliding_window_data([1.0, 2], width=3, number_of_stats=1)


def test_equals_and_in_approximately():
    assert ts.equals_approximately(1.0, 1.0 + 1e-12)
    assert ts.equals_approximately(1e-20, 0)  # absolute tolerance
    assert not ts.equals_approximately(1.0, 1.1)
    assert ts.in_approximately(2.0, [1, 2 + 1e-12, 3])
    assert not ts.in_approximately(2.5, [1, 2, 3])


def test_evals_container():
    e = ts.Evals([1, 5], [2, 3])
    assert e() == [1, 1, 5, 5, 5]
    with pytest.raises(NotImplementedError):
        e.sort()
