"""Unit tests for the data-file utilities `cocopp.reduce_size` and `cocopp.sanitycheck`."""

import os
import warnings

import pytest

from cocopp import reduce_size as rs
from cocopp import sanitycheck
from cocopp.ppfig import Usage

import synthdata

HEADER = "% f evaluations | g evaluations | best noise-free fitness - Fopt | ...\n"


class TestReduceSize:
    def test_target_hit(self):
        hit = rs.TargetHit(20, 1e-8)
        assert hit("1 0 100 x\n")
        assert not hit("2 0 100 x\n")  # same f-value: no new target
        assert hit("3 0 50 x\n")
        assert not hit("4 0 49 x\n")  # within the same 10**(1/20) band
        assert hit("5 0 1e-9 x\n")  # final target
        assert not hit("6 0 1e-12 x\n")  # nothing after the final target
        assert hit("1 0 100 x\n")  # evaluations decreased: new run, reset

    def test_reduce_dat(self):
        lines = [HEADER] + ["%d 0 %g 0 0\n" % (e, f) for e, f in [(1, 100), (2, 100), (3, 99), (4, 50), (5, 49), (6, 48)]]
        res = rs.reduce_dat(lines)
        assert res[0] == HEADER
        # lines hitting a new 10**(-1/20) target band are kept, others are overwritten
        # by the next line, hence the last line is always kept
        assert [line.split()[0] for line in res[1:]] == ["1", "4", "6"]

    def test_reduce_tdat_keeps_first_and_last(self):
        lines = [HEADER] + ["%d 0 1 0 0\n" % e for e in range(1, 9)] + [HEADER] + ["%d 0 1 0 0\n" % e for e in (1, 2, 3)]
        res = rs.reduce_tdat(lines)
        evals = [line.split()[0] if not line.startswith("%") else "%" for line in res]
        assert evals == ["%", "1", "8", "%", "1", "3"]

    def test_remove_x(self):
        lines = [HEADER, "1 0 3 4 5 6 7 8\n"]
        assert rs.remove_x(lines) == [HEADER, "1 0 3 4 5\n"]

    @pytest.mark.parametrize(
        "name, dat, tdat, x",
        [("f_DIM2.dat", True, False, False), ("f_DIM10.tdat", False, True, True), ("f_DIM10.mdat", False, False, True), ("f.info", False, False, False)],
    )
    def test_conditions(self, name, dat, tdat, x):
        assert rs.reduce_dat_condition(name) == dat
        assert rs.reduce_tdat_condition(name) == tdat
        assert rs.remove_x_condition(name) == x

    def test_main_on_synthetic_data(self, tmp_path, quiet):
        import cocopp

        folder = synthdata.write_bbob(str(tmp_path), "RED", functions=(1,), dims=(2, 10), seed=5)
        before = cocopp.pproc.DataSetList(folder)
        rs.main(folder)
        reduced = [d for d in os.listdir(tmp_path) if d.startswith("RED-")]
        assert len(reduced) == 1
        red_folder = os.path.join(str(tmp_path), reduced[0])
        size = lambda f: sum(os.path.getsize(os.path.join(r, n)) for r, _, ns in os.walk(f) for n in ns)  # noqa: E731
        assert size(red_folder) < size(folder)
        after = cocopp.pproc.DataSetList(red_folder)
        # the reduction must not change the post-processed data
        for ds0, ds1 in zip(before, after):
            assert not ds0._data_differ(ds1)
            assert list(ds0.maxevals) == list(ds1.maxevals)


class TestSanityCheck:
    def test_is_correct_instances(self):
        assert sanitycheck.is_correct_instances(list(range(1, 16)))
        assert sanitycheck.is_correct_instances(3 * [1, 2, 3, 4, 5])
        assert not sanitycheck.is_correct_instances([1, 2, 3])

    def test_checkinfofile_ok(self, bbob_small, capsys):
        sanitycheck.checkinfofile(os.path.join(bbob_small, "bbobexp_f1.info"))
        out = capsys.readouterr().out
        # quirk: the reported line numbers are 0-based
        assert "entry l0-2 is ok" in out and "entry l3-5 is ok" in out

    def test_checkinfofile_wrong_instances(self, tmp_path):
        info = synthdata.write_tiny_bbob(str(tmp_path))
        with pytest.raises(Usage, match="instances"):
            sanitycheck.checkinfofile(info, verbose=False)

    def test_checkinfofile_missing_data(self, tmp_path):
        info = synthdata.write_tiny_bbob(str(tmp_path))
        os.remove(os.path.join(os.path.dirname(info), "data_f1", "bbobexp_f1_DIM2.tdat"))
        with pytest.raises(IOError):
            sanitycheck.checkinfofile(info, verbose=False)

    @pytest.mark.xfail(reason="known bug: sanitycheck.main uses rungeneric.shortoptlist which does not exist", raises=AttributeError, strict=True)
    def test_main(self, bbob_small):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sanitycheck.main([bbob_small])
