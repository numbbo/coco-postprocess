"""Unit tests for `DataSetList`, the ``dictAlg*`` helpers, target value
classes and other module-level functions of `cocopp.pproc`, and for the
reference ("best") algorithm construction in `cocopp.bestalg`.
"""

import os
import pickle

import numpy as np
import pytest

import cocopp
from cocopp import bestalg, pproc, testbedsettings

import synthdata
from conftest import load


class TestParseInfo:
    def test_parseinfo(self):
        s = "suite = 'bbob', funcId = 1, DIM = 2, Precision = 1.000e-08, algId = 'A, B', coco_version = '2.6'"
        assert pproc.parseinfo(s) == [
            ("suite", "bbob"),
            ("funcId", 1),
            ("DIM", 2),
            ("Precision", 1e-08),
            ("algId", "A, B"),
            ("coco_version", "2.6"),
        ]

    def test_parseinfo_quotes_inside_values(self):
        assert pproc.parseinfo("algId = 'it's'") == [("algId", "it's")]
        assert pproc.parseinfo('algId = "x"') == [("algId", "x")]

    def test_parseinfo_biobj_data_line(self):
        res = dict(pproc.parseinfo("function =  2, dim =  5, f.dat, 1:500|6.1e-003"))
        assert res == {"function": 2, "dim": 5}

    def test_parseinfoold(self):
        assert pproc.parseinfoold("funcId = 1, algId = 'x'") == [("algId", "x"), ("funcId", 1)]


def test_align_list():
    assert pproc.align_list(["a", "b"], [1, 1, 2]) == ["a", "a", "b"]


def test_set_unique_algId():
    class D:
        def __init__(self, a):
            self.algId = a

    taken = [D("A"), D("B")]
    new = [D("A"), D("C"), D("B")]
    pproc.set_unique_algId(new, taken)
    assert [d.algId for d in new] == ["A 2", "C", "B 2"]
    new = [D("A")]
    pproc.set_unique_algId(new, None, taken_ids=["A", "A 2"])
    assert new[0].algId == "A 3"


class TestTargetValues:
    def test_target_values(self):
        targets = [10**i for i in np.arange(2, -8.1, -0.2)]
        tv = pproc.TargetValues(targets)
        assert tv() == targets and tv((1, 20)) == targets
        assert len(tv) == len(targets)
        assert tv.short_info == "absolute targets"
        assert tv.label_name() == "Df"

    def test_sorted_and_labels(self):
        tv = pproc.TargetValues([1e-8, 10, 0.1])
        assert tv() == [10, 0.1, 1e-8]
        assert tv.labels() == ["10", "0.1", "1e-8"]
        assert tv.loglabels() == ["1", "-1", "-8"]
        assert tv.label(0) == "10" and tv.loglabel(2) == "-8"

    def test_discretize(self):
        tv = pproc.TargetValues([1.1e-3, 9e-2], discretize=True)
        assert tv() == pytest.approx([10**-1, 10**-3])  # rounded to the 10**(i/5) grid
        assert pproc.TargetValues([3.0])(discretize=True) == pytest.approx([10**0.4])

    def test_cast_and_as_target_values(self):
        tv = pproc.TargetValues([1, 2])
        assert pproc.TargetValues.cast(tv) is tv
        assert pproc.TargetValues.cast([1, 2])() == [2, 1]
        assert pproc.asTargetValues(tv) is tv
        assert pproc.asTargetValues([1])() == [1]
        rl = pproc.RunlengthBasedTargetValues([1, 10])
        assert pproc.asTargetValues(rl) is rl
        with pytest.raises(NotImplementedError):
            pproc.asTargetValues("x")


class TestRunlengthBasedTargetValues:
    @pytest.fixture
    def reference(self, bbob_alg_a, bbob_alg_b, quiet):
        testbedsettings.reset_current_testbed()
        dsl, algs, dict_alg = pproc.processInputArgs([bbob_alg_a, bbob_alg_b])
        return bestalg.generate(dict_alg, "REF")

    def test_basic_attributes(self):
        rl = pproc.RunlengthBasedTargetValues([10, 0.5, 3])
        assert rl.run_lengths == [0.5, 3, 10]
        assert len(rl) == 3
        assert rl.labels() == ["0.5", "3", "10"]
        assert rl.loglabel(0) == "-0.30"
        assert rl.label_name() == "RL/dim"
        assert pproc.RunlengthBasedTargetValues([1], times_dimension=False).label_name() == "RL"
        assert pproc.RunlengthBasedTargetValues.cast(rl) is rl
        assert pproc.RunlengthBasedTargetValues.cast([1, 2]).run_lengths == [1, 2]

    def test_requires_fun_dim(self, reference):
        with pytest.raises(ValueError):
            pproc.RunlengthBasedTargetValues([1], reference_data=reference)()

    def test_targets_from_reference_data(self, reference):
        run_lengths = [0.5, 1.2, 3, 10, 50]
        rl = pproc.RunlengthBasedTargetValues(run_lengths, reference_data=reference, force_different_targets_factor=1)
        for fun_dim in [(1, 5), (6, 2), (21, 20)]:
            targets = rl(fun_dim)
            ref = reference[fun_dim[::-1]]
            assert len(targets) == len(run_lengths)
            assert all(np.diff(targets) <= 0) and targets[-1] >= 1e-8
            # recompute: the best target reached by the reference within rl * dim, divided by 10**0.2
            for t, r in zip(targets, run_lengths):
                idx = np.nonzero(ref.ert[ref.target >= 1e-8] <= max(1, r * fun_dim[1]))[0]
                expected = ref.target[0] if not len(idx) else max(1e-8, (1 + 1e-9) * ref.target[idx[-1]] / 10**0.2)
                assert t == pytest.approx(expected)
        assert rl.reference_algorithm == "REF"

    def test_forced_different_targets(self, reference):
        rl = pproc.RunlengthBasedTargetValues([1, 1.01, 1.02], reference_data=reference)
        targets = rl((1, 5))
        assert targets[1] == pytest.approx(targets[0] / 10**0.04)

    def test_unique_and_discretized_targets(self, reference):
        rl = pproc.RunlengthBasedTargetValues([1, 1.01, 1.02, 1e9], reference_data=reference, force_different_targets_factor=1, unique_target_values=True)
        targets = rl((1, 5))
        assert len(targets) == len(set(targets)) < 4
        disc = pproc.RunlengthBasedTargetValues([1, 10], reference_data=reference)((1, 5), discretize=True)
        assert np.log10(disc) * 5 == pytest.approx(np.round(np.log10(disc) * 5))

    def test_shipped_reference_algorithm(self, quiet):
        cocopp.config.config("bbob")
        rl = pproc.RunlengthBasedTargetValues([0.5, 1.2, 3, 10, 50])
        t = rl(fun_dim=(1, 20))
        assert 6.30957345e01 <= t[0] <= 6.30957346e01  # from the package doctest
        assert t[-1] == 1e-8
        assert rl.reference_algorithm == "refalgs/best2009-bbob.tar.gz"


class TestDataSetList:
    def test_load_folder(self, dsl_small):
        assert len(dsl_small) == 8
        assert isinstance(dsl_small, pproc.DataSetList)
        # sorted by dimension, then function
        assert [(ds.dim, ds.funcId) for ds in dsl_small] == [(d, f) for d in (2, 5) for f in (1, 2, 8, 15)]
        assert all(ds.algId == "SMALL" for ds in dsl_small)
        assert dsl_small.current_testbed is testbedsettings.current_testbed

    def test_from_datasets_and_empty(self, dsl_small):
        assert pproc.DataSetList() == []
        assert pproc.DataSetList(list(dsl_small)) == dsl_small

    def test_append_rejects_non_datasets(self, dsl_small):
        dsl = pproc.DataSetList()
        with pytest.warns(UserWarning):
            dsl.append(3)
        with pytest.raises(ValueError):
            dsl.append(3, check_data_type=True)

    def test_append_same_dataset_twice_is_skipped(self, dsl_small):
        with pytest.warns(UserWarning, match="found twice"):
            dsl_small.append(pickle.loads(pickle.dumps(dsl_small[0])))
        assert len(dsl_small) == 8

    def test_append_merges_trials(self, tmp_path, quiet):
        """two index entries of the same algorithm/function/dimension are merged"""
        a = synthdata.write_tiny_bbob(str(tmp_path / "a"), "M", trials={1: synthdata.TINY_TRIALS[1]})
        b = synthdata.write_tiny_bbob(str(tmp_path / "b"), "M", trials={2: synthdata.TINY_TRIALS[2], 3: synthdata.TINY_TRIALS[3]})
        testbedsettings.reset_current_testbed()
        dsl = pproc.DataSetList([a, b])
        assert len(dsl) == 1
        ds = dsl[0]
        assert ds.instancenumbers == [1, 2, 3]
        assert list(ds.maxevals) == [50, 100, 30]
        assert ds.detERT([1, 1e-8]) == pytest.approx([115 / 3, 90])
        # characterization: the merged index file is listed twice (see xfail test below)
        assert ds.indexFiles == [a, b, b]

    @pytest.mark.xfail(reason="known bug: DataSetList.append extends indexFiles/dataFiles twice when merging", strict=True)
    def test_append_merges_file_lists_once(self, tmp_path, quiet):
        a = synthdata.write_tiny_bbob(str(tmp_path / "a"), "M", trials={1: synthdata.TINY_TRIALS[1]})
        b = synthdata.write_tiny_bbob(str(tmp_path / "b"), "M", trials={2: synthdata.TINY_TRIALS[2]})
        testbedsettings.reset_current_testbed()
        ds = pproc.DataSetList([a, b])[0]
        assert ds.indexFiles == [a, b]
        assert len(ds.dataFiles) == 2

    def test_missing_input_warns(self, tmp_path, capsys):
        with pytest.warns(UserWarning, match="not found"):
            dsl = pproc.DataSetList([str(tmp_path / "nothing.xyz")])
        assert len(dsl) == 0

    def test_dict_by(self, dsl_small):
        assert sorted(dsl_small.dictByDim()) == [2, 5]
        assert sorted(dsl_small.dictByFunc()) == [1, 2, 8, 15]
        assert list(dsl_small.dictByAlg()) == [("SMALL", "")]
        assert dsl_small.by("dim").keys() == dsl_small.dictByDim().keys()
        assert sorted(dsl_small.dictByDimFunc()[5]) == [1, 2, 8, 15]
        assert list(dsl_small.dictByNoise()) == ["noiselessall"]
        assert sorted(dsl_small.dictByParam("dim")) == [2, 5]
        assert list(dsl_small.dictByParam("nonexisting")) == [None]

    def test_function_groups(self, dsl_small):
        groups = dsl_small.dictByFuncGroup()
        assert {k: sorted({ds.funcId for ds in v}) for k, v in groups.items()} == {"separ": [1, 2], "lcond": [8], "multi": [15]}
        assert list(dsl_small.getFuncGroups().items()) == [
            ("separ", "Separable functions"),
            ("lcond", "Misc. moderate functions"),
            ("multi", "Multi-modal functions"),
        ]
        assert not dsl_small.isBiobjective()

    def test_filter_and_filtered(self, dsl_small):
        unimodal = dsl_small.filtered(lambda ds: ds.funcId < 10)
        assert isinstance(unimodal, pproc.DataSetList) and len(unimodal) == 6
        assert dsl_small.filtered(None) == [] and len(dsl_small.filtered(True, list)) == 8
        removed = dsl_small.filter(lambda ds: ds.dim == 2, verbose=2)
        assert len(removed) == 4 and len(dsl_small) == 4
        dsl_small.remove_if(lambda ds: ds.funcId == 15)
        assert sorted(ds.funcId for ds in dsl_small) == [1, 2, 8]
        assert dsl_small.filter(None) is None and len(dsl_small) == 3

    def test_sort(self, dsl_small):
        dsl_small.sort(key1="funcId", key2="dim")
        assert [(ds.funcId, ds.dim) for ds in dsl_small][:3] == [(1, 2), (1, 5), (2, 2)]

    def test_info(self, dsl_small, capsys):
        dsl_small.info("all")
        out = capsys.readouterr().out
        assert "8 data set(s)" in out and "Algorithm(s): SMALL" in out
        assert "4 Functions with IDs 1, 2, 8, 15" in out
        assert "Dimension(s): 2, 5" in out
        assert "Max evals: [400, 1000]" in out
        pproc.DataSetList().info()
        assert capsys.readouterr().out == "[]\n"

    def test_get_all_data_lines_and_best_lines(self, dsl_small):
        lines, scores = dsl_small.get_all_data_lines(1e-1, 1, 5)
        assert len(lines) == 1 and scores == dsl_small[4].detERT([1e-1])
        with pytest.warns(UserWarning):
            best, best_scores = dsl_small.det_best_data_lines([10, 1e-1], 1, 5)
        assert list(best_scores) == dsl_small[4].detERT([10, 1e-1])

    @pytest.mark.xfail(reason="known bug: np.sort on dict_values in det_best_data", strict=True)
    def test_det_best_data(self, dsl_small):
        dsl_small.det_best_data([10, 1e-1], 1, 5)

    @pytest.mark.xfail(reason="known bug: dict.values()[0] in run_length_distributions (py2 code)", raises=TypeError, strict=True)
    def test_run_length_distributions_single_alg(self, dsl_small):
        dsl_small.run_length_distributions(5, [10, 1e-1])

    def test_run_length_distributions(self, dsl_small):
        rld, left = dsl_small.run_length_distributions(5, [10, 1e-1], flatten_output_dict=False)
        data, solved, processed = rld[("SMALL", "")]
        assert processed == [1, 2, 8, 15]
        assert len(data) == 4 * 2 * 15
        assert np.all(np.diff(data[np.isfinite(data)]) >= 0)
        # the left envelope of a single algorithm is its data, with inf instead of nan
        np.testing.assert_array_equal(left, np.where(np.isnan(data), np.inf, data))

    def test_reference_values_hash(self, dsl_small, biobj_alg, quiet):
        assert dsl_small.get_reference_values_hash() is None
        testbedsettings.reset_current_testbed()
        dsl = load(biobj_alg)
        h = dsl.get_reference_values_hash()
        assert isinstance(h, str) and len(h) == 16
        assert h == load(biobj_alg).get_reference_values_hash()

    def test_is_same_list_assert(self, dsl_small, bbob_small):
        dsl_small._is_same_list_assert(load(bbob_small))


class TestDictAlg:
    @pytest.fixture
    def dict_alg(self, bbob_alg_a, bbob_alg_b, quiet):
        testbedsettings.reset_current_testbed()
        dsl, algs, dict_alg = pproc.processInputArgs([bbob_alg_a, bbob_alg_b])
        return dsl, algs, dict_alg

    def test_processInputArgs(self, dict_alg, bbob_alg_a, bbob_alg_b):
        dsl, algs, d = dict_alg
        assert algs == [bbob_alg_a, bbob_alg_b]
        assert list(d) == algs
        assert len(dsl) == 240
        assert all(ds._data_folder == bbob_alg_a for ds in d[bbob_alg_a])
        assert set(testbedsettings.reference_values) == {"SYNTH-A", "SYNTH-B"}

    def test_processInputArgs_errors(self, tmp_path):
        with pytest.raises(Exception, match="could not be found"):
            pproc.processInputArgs([str(tmp_path / "missing")])
        single = tmp_path / "a.info"
        single.write_text("")
        with pytest.warns(UserWarning, match="single file"):
            assert pproc.processInputArgs([str(single)])[0] == []

    def test_same_algorithm_twice_gets_unique_names(self, bbob_small, quiet):
        testbedsettings.reset_current_testbed()
        dsl, algs, d = pproc.processInputArgs([bbob_small, bbob_small + os.sep])
        assert algs == [bbob_small]  # trailing separators are stripped
        assert {ds.algId for ds in dsl} == {"SMALL", "SMALL 2"}

    def test_by_dim(self, dict_alg):
        _, algs, d = dict_alg
        by_dim = pproc.dictAlgByDim(d)
        assert sorted(by_dim) == [2, 3, 5, 10, 20]
        assert list(by_dim[5]) == algs and len(by_dim[5][algs[0]]) == 24
        assert pproc.DictAlg(d).by_dim().keys() == by_dim.keys()
        by_dim2 = pproc.dictAlgByDim2(d)
        assert {k: {a: len(v) for a, v in x.items()} for k, x in by_dim2.items()} == {
            k: {a: len(v) for a, v in x.items()} for k, x in by_dim.items()
        }

    def test_by_fun_noise_group(self, dict_alg):
        _, algs, d = dict_alg
        assert sorted(pproc.dictAlgByFun(d)) == list(range(1, 25))
        assert list(pproc.dictAlgByNoi(d)) == ["noiselessall"]
        groups = pproc.dictAlgByFuncGroup(d)
        assert sorted(groups) == ["hcond", "lcond", "mult2", "multi", "separ"]
        assert len(groups["separ"][algs[1]]) == 5 * 5

    def test_missing_dimension_is_filled_with_empty_list(self, bbob_small, bbob_alg_a, quiet):
        testbedsettings.reset_current_testbed()
        _, algs, d = pproc.processInputArgs([bbob_small, bbob_alg_a])
        by_dim = pproc.dictAlgByDim(d)
        assert len(by_dim[20][bbob_small]) == 0 and len(by_dim[20][bbob_alg_a]) == 24


class TestGetDataSetList:
    def test_pickle_cache_for_archives(self, tmp_path, bbob_small, quiet, monkeypatch):
        import tarfile

        archive = str(tmp_path / "SMALL.tgz")
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(bbob_small, arcname="SMALL")
        monkeypatch.chdir(tmp_path)
        testbedsettings.reset_current_testbed()
        dsl1 = pproc.get_DataSetList(archive)
        assert pproc._pickle_file_read == ""
        assert os.path.exists(archive + ".pickle")
        assert os.path.isdir(tmp_path / ".extracted_SMALL")
        dsl2 = pproc.get_DataSetList(archive)
        assert pproc._pickle_file_read == archive + ".pickle"
        dsl2._is_same_list_assert(dsl1)
        monkeypatch.setattr(pproc, "_ignore_pickle_files", True)
        dsl3 = pproc.get_DataSetList(archive)
        assert pproc._pickle_file_read == ""
        dsl3._is_same_list_assert(dsl1)

    def test_folders_are_not_pickled(self, bbob_small, quiet):
        testbedsettings.reset_current_testbed()
        dsl = pproc.get_DataSetList(bbob_small)
        assert len(dsl) == 8
        assert not os.path.exists(bbob_small + ".pickle")


class TestBestAlg:
    @pytest.fixture
    def algs(self, bbob_alg_a, bbob_alg_b, quiet):
        testbedsettings.reset_current_testbed()
        return pproc.processInputArgs([bbob_alg_a, bbob_alg_b])

    def test_best_ert_is_minimum_of_algorithm_erts(self, algs):
        dsl, names, dict_alg = algs
        best = bestalg.generate(dict_alg, "BEST")
        assert len(best) == 24 * 5
        targets = [100, 10, 1, 1e-1, 1e-3, 1e-5, 1e-7, 1e-8]
        for (dim, fun), ba in list(best.items())[::7]:
            erts = [pproc.DataSetList(dict_alg[a]).dictByDimFunc()[dim][fun][0].detERT(targets) for a in names]
            assert ba.detERT(targets) == pytest.approx(np.min(erts, axis=0))
            assert (ba.dim, ba.funcId, ba.algId) == (dim, fun, "BEST")
            assert set(ba.best_algorithm_data) <= set(names)
            assert repr(ba) == "{alg: BEST, F%d, dim: %d}" % (fun, dim)
            assert ba.comment == "Combination of " + ", ".join(names)

    def test_best_detEvals_comes_from_best_algorithm(self, algs):
        dsl, names, dict_alg = algs
        ba = bestalg.generate(dict_alg, "BEST")[(5, 1)]
        evals, alg_names, _ = ba.detEvals([1e-1, 1e-12])
        source = pproc.DataSetList(dict_alg[alg_names[0]]).dictByDimFunc()[5][1][0]
        np.testing.assert_array_equal(evals[0], source.detEvals([1e-1])[0])
        assert alg_names[1] is None and np.all(np.isnan(evals[1]))
        assert ba.get_success_ratio(1e-1) == (np.sum(np.isfinite(evals[0])), 15)

    def test_custom_generate_roundtrip(self, algs, tmp_path, monkeypatch, bbob_alg_a, bbob_alg_b):
        monkeypatch.chdir(tmp_path)
        bestalg.custom_generate([bbob_alg_a, bbob_alg_b], "myref")
        assert os.path.exists(tmp_path / "myref.tar.gz")
        assert os.path.exists(tmp_path / "myref" / "bbob-bestalg.info")
        testbedsettings.reset_current_testbed()
        entries = bestalg.load_reference_algorithm(str(tmp_path / "myref"), force=True, relative_load=False)
        direct = bestalg.generate(algs[2], "BEST")
        targets = [10, 1e-1, 1e-8]
        for key in [(2, 1), (5, 8), (20, 24)]:
            # the written ERTs are rounded to integers
            assert entries[key].detERT(targets) == pytest.approx(direct[key].detERT(targets), abs=0.5)

    def test_load_reference_algorithm(self, quiet):
        bestalg.reset_reference_algorithm()
        assert bestalg.bestAlgorithmEntries == {}
        cocopp.config.config("bbob")
        entries = bestalg.load_reference_algorithm("refalgs/best2009-bbob.tar.gz")
        assert len(entries) == 24 * 6
        assert bestalg.load_reference_algorithm("anything") is entries  # cached unless forced
        assert bestalg.load_reference_algorithm("", force=True) is None

    def test_get_used_instance_list(self):
        assert bestalg.get_used_instance_list([[1, 2], [1, 2]]) == "1,2"
        assert bestalg.get_used_instance_list([[1, 2], [3]]) == "[1,2],[3]"
        assert bestalg.get_used_instance_list([]) is None
