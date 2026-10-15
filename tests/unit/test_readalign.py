"""Unit tests for `cocopp.readalign` (reading and aligning raw data files)."""

import numpy as np
import pytest

from cocopp import dataformatsettings, readalign, testbedsettings, pproc

nan = np.nan


@pytest.fixture
def bbob_format(monkeypatch):
    """set the module globals `readalign` relies upon"""
    monkeypatch.setattr(dataformatsettings, "current_data_format", dataformatsettings.BBOBNewDataFormat())
    monkeypatch.setattr(testbedsettings, "current_testbed", testbedsettings.GECCOBBOBTestbed(pproc.TargetValues))


def _write(path, text):
    path.write_text(text)
    return str(path)


class TestSplit:
    def test_split_trials(self, tmp_path):
        fn = _write(
            tmp_path / "a.dat",
            "% instance = 1, reference value = 0.5\n1 0 10 0 0\n5 0 1 0 0\n"
            "% instance = 2, reference value = 0.25\n1 0 Inf 0 0\n2 0 -inf nan NaN\n",
        )
        data, algs, refs, succ = readalign.split([fn])
        assert len(data) == 2
        np.testing.assert_array_equal(data[0], [[1, 0, 10, 0, 0], [5, 0, 1, 0, 0]])
        assert data[1][0, 2] == np.inf and data[1][1, 2] == -np.inf and np.isnan(data[1][1, 3])
        assert refs == {1: 0.5, 2: 0.25}
        assert algs == [] and succ == []

    def test_split_with_index_filter(self, tmp_path):
        fn = _write(tmp_path / "a.dat", "%\n1 0 1 0 0\n%\n1 0 2 0 0\n%\n1 0 3 0 0\n")
        data = readalign.split([fn], idx_to_load=[True, False, True])[0]
        assert [d[0, 2] for d in data] == [1, 3]

    def test_split_reads_several_files(self, tmp_path):
        f1 = _write(tmp_path / "a.dat", "%\n1 0 1 0 0\n")
        f2 = _write(tmp_path / "b.dat", "%\n1 0 2 0 0\n")
        assert len(readalign.split([f1, f2])[0]) == 2

    def test_split_best_algorithm_columns(self, tmp_path):
        fn = _write(tmp_path / "best.dat", "% algorithm type = best\n1 0 1 0 0 ALG1 3 15\n2 0 0.5 0 0 ALG2 15 15\n")
        data, algs, refs, succ = readalign.split([fn])
        assert algs == ["ALG1", "ALG2"]
        assert succ == [[3, 15], [15, 15]]
        assert data[0].shape == (2, 5)

    def test_split_invalid_number_and_incomplete_line(self, tmp_path):
        # with `dim` given, lines must have dim + 5 entries
        fn = _write(tmp_path / "a.dat", "%\n1 0 x 0 0 7\n1 2\n")
        with pytest.warns(UserWarning):
            data = readalign.split([fn], dim=1)
        assert len(data[0]) == 1 and data[0][0].shape == (1, 6) and np.isnan(data[0][0][0, 2])

    def test_openfile_missing(self, tmp_path):
        with pytest.raises(IOError):
            readalign.openfile(str(tmp_path / "missing.dat"))


def test_is_close():
    assert readalign.is_close(1.0, 1.0 + 1e-12)
    assert not readalign.is_close(1.0, 1.001)
    assert readalign.is_close(0.0, 1e-12, abs_tol=1e-10)


class TestAlignment:
    def test_horizontal_alignment(self, bbob_format):
        # two trials: Delta f (column 2) over evaluations (column 0)
        t1 = np.array([[1, 0, 50.0], [10, 0, 2.0], [20, 0, 0.05]])
        t2 = np.array([[1, 0, 9.0], [3, 0, 0.5]])
        evals, maxevals, finalf = readalign.align_data(readalign.HMultiReader([t1, t2]), 0, 2)
        assert list(maxevals) == [20, 3]
        assert list(finalf) == [0.05, 0.5]
        # first row: smallest 10**(i/5) not smaller than the largest initial f-value
        assert evals[0, 0] == pytest.approx(10 ** (np.ceil(np.log10(50) * 5) / 5))
        assert list(evals[0, 1:]) == [1, 1]
        # rows are monotonously decreasing targets with non-decreasing evals
        assert np.all(np.diff(evals[:, 0]) < 0)
        e = np.where(np.isnan(evals[:, 1:]), np.inf, evals[:, 1:])
        assert np.all(np.diff(e, axis=0) >= 0)
        # the last row is the smallest 10**(i/5) target reached, i.e. the one just above 0.05
        assert evals[-1, 0] == pytest.approx(10 ** (-6 / 5))
        assert evals[-1, 1] == 20 and np.isnan(evals[-1, 2])

    def test_vertical_alignment(self, bbob_format):
        t1 = np.array([[1, 0, 50.0], [10, 0, 2.0], [20, 0, 0.05]])
        t2 = np.array([[1, 0, 9.0], [3, 0, 0.5]])
        funvals, maxevals, finalf = readalign.align_data(readalign.VMultiReader([t1, t2]), 0, 2)
        np.testing.assert_array_equal(funvals, [[1, 50, 9], [3, 50, 0.5], [10, 2, 0.5], [20, 0.05, 0.5]])
        assert list(maxevals) == [20, 3]

    def test_negative_fvalues(self, bbob_format):
        t1 = np.array([[1, 0, 5.0], [4, 0, -2.0]])
        evals, _, finalf = readalign.align_data(readalign.HMultiReader([t1]), 0, 2)
        assert finalf[0] == -2
        assert evals[-1, 0] <= 0 and evals[-1, 1] == 4

    def test_rewind_reader(self, bbob_format):
        t1 = np.array([[1, 7, 5.0], [4, 8, 0.1]])
        reader = readalign.HMultiReader([t1])
        e1 = readalign.align_data(reader, 0, 2)[0]
        e2 = readalign.align_data(reader, 1, 2, rewind_reader=True)[0]
        assert list(e1[:, 1]) == [1, 4] and list(e2[:, 1]) == [7, 8]

    def test_align_data_type_check(self):
        with pytest.raises(TypeError):
            readalign.align_data([np.zeros((2, 3))], 0, 2, rewind_reader=True)

    def test_empty_arrays_are_skipped(self, bbob_format):
        assert len(readalign.HMultiReader([np.zeros((0, 3)), np.ones((2, 3))])) == 1
        with pytest.raises(ValueError):
            readalign.MultiReader.SingleReader([])

    def test_array_alignment_merges_columns(self, bbob_format):
        a = np.array([[1, 50.0, 9.0], [3, 50, 0.5]])
        b = np.array([[1, 7.0], [2, 1.0]])
        res = readalign.alignArrayData(readalign.VArrayMultiReader([a, b]))
        np.testing.assert_array_equal(res, [[1, 50, 9, 7], [2, 50, 9, 1], [3, 50, 0.5, 1]])
