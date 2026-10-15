"""Integration tests calling the figure and table modules directly.

`cocopp.main` calls these modules in a fixed sequence; calling them
individually on small data sets localizes failures and covers modules
that the pipeline does not (or no longer) use.
"""

import os
import warnings

import numpy as np
import pytest

from cocopp import algportfolio, bestalg, config, genericsettings, ppconverrorbars, ppfig, ppfigdim, ppfigparam, pplogloss, pprldistr
from cocopp import ppsingle, pptable, pproc, testbedsettings, toolsstats
from cocopp.comp2 import ppfig2, pprldistr2, ppscatter
from cocopp.compall import ppfigs, ppperfprof, pprldmany, pptables


@pytest.fixture
def two_algs(bbob_small, bbob_small_b, quiet):
    """``(dsList, sortedAlgs, dictAlg)`` of two small synthetic algorithms, configured for 'bbob'"""
    testbedsettings.reset_current_testbed()
    res = pproc.processInputArgs([bbob_small, bbob_small_b])
    config.config("bbob")
    return res


@pytest.fixture
def one_alg(two_algs):
    dsl, algs, dict_alg = two_algs
    return dict_alg[algs[0]]


@pytest.fixture
def out(tmp_path):
    return str(tmp_path)


def produced(folder):
    return sorted(os.listdir(folder))


def single_algorithm_pages(out, dsl):
    """write the html skeleton pages which `rungeneric1` creates before calling the modules"""
    ppfig.save_single_functions_html(os.path.join(out, "index1"), "title", htmlPage=ppfig.HtmlPage.ONE, function_groups=dsl.getFuncGroups())
    ppfig.save_single_functions_html(
        os.path.join(out, "pptable"), dimensions=sorted(dsl.dictByDim()), htmlPage=ppfig.HtmlPage.PPTABLE, parentFileName="index1"
    )


def many_algorithms_pages(out, dict_alg, algs):
    """write the html skeleton pages which `rungenericmany` creates before calling the modules"""
    groups = dict_alg[algs[0]].getFuncGroups()
    ppfig.save_single_functions_html(os.path.join(out, "index"), "", htmlPage=ppfig.HtmlPage.MANY, function_groups=groups)
    ppfig.save_single_functions_html(
        os.path.join(out, "pptables"),
        "",
        dimensions=sorted(pproc.dictAlgByDim(dict_alg)),
        htmlPage=ppfig.HtmlPage.PPTABLES,
        function_groups=groups,
        parentFileName="index",
    )


class TestSingleAlgorithmModules:
    def test_pptable(self, one_alg, out, tmp_path):
        single_algorithm_pages(out, one_alg)
        latex = str(tmp_path / "cmds.tex")
        pptable.main(one_alg, (2, 5), out, latex)
        tables = [f for f in produced(out) if f.startswith("pptable_")]
        assert tables == sorted("pptable_f%03d_%02dD.tex" % (f, d) for f in (1, 2, 8, 15) for d in (2, 5))
        assert "pptable_f001_05D" not in open(os.path.join(out, "pptable.html")).read()  # html gets the table itself
        assert "<table" in open(os.path.join(out, "pptable.html")).read()
        assert pptable.get_table_caption()

    def test_ppfigdim(self, one_alg, out):
        single_algorithm_pages(out, one_alg)
        ppfigdim.main(one_alg, testbedsettings.current_testbed.ppfigdim_target_values, out)
        assert [f for f in produced(out) if f.endswith(".pdf")] == ["ppfigdim_f%03d.pdf" % f for f in (1, 2, 8, 15)]

    def test_pprldistr(self, one_alg, out):
        pprldistr.main(one_alg.dictByDim()[5], True, out, "all")
        assert {"pprldistr_05D_all.pdf", "ppfvdistr_05D_all.pdf"} <= set(produced(out))

    def test_pplogloss(self, one_alg, out):
        pplogloss.main(one_alg.dictByDim()[5], 0.0, True, out, "all")
        assert "pplogloss_05D_all.pdf" in produced(out)

    def test_pprldmany_all_single_functions(self, two_algs, out):
        dsl, algs, dict_alg = two_algs
        single = {algs[0]: dict_alg[algs[0]]}
        single_algorithm_pages(out, dict_alg[algs[0]])
        pprldmany.all_single_functions(single, True, None, out, "index1", settings=genericsettings)
        assert sorted(os.listdir(os.path.join(out, "pprldmany-single-functions")))[:3] == ["pprldmany.html", "pprldmany.pdf", "pprldmany.svg"]

    def test_ppconverrorbars(self, two_algs, out):
        dsl, algs, dict_alg = two_algs
        single_algorithm_pages(out, dict_alg[algs[0]])
        ppconverrorbars.main({algs[0]: dict_alg[algs[0]]}, out, "index1")
        assert ["ppconv_f%03d.pdf" % f for f in (1, 2, 8, 15)] == [f for f in produced(out) if f.endswith(".pdf")]

    def test_ppfigparam_read_fun_infos(self):
        testbedsettings.load_current_testbed("bbob", pproc.TargetValues)
        assert ppfigparam.read_fun_infos()[1] == "1 Sphere"

    @pytest.mark.xfail(reason="ppfigparam.main (not used by the pipeline) fails with a numpy indexing error", raises=ValueError, strict=True)
    def test_ppfigparam(self, one_alg, out):
        ppfigparam.main(one_alg, outputdir=out)

    @pytest.mark.xfail(reason="ppsingle.main (not used by the pipeline) calls an undefined generatefigure", raises=NameError, strict=True)
    def test_ppsingle(self, one_alg, out):
        ppsingle.main(one_alg, out)


class TestComparisonModules:
    def test_pptables(self, two_algs, out, tmp_path):
        dsl, algs, dict_alg = two_algs
        many_algorithms_pages(out, dict_alg, algs)
        latex = str(tmp_path / "cmds.tex")
        for dim, by_dim in pproc.dictAlgByDim(dict_alg).items():
            pptables.main(by_dim, algs, out, True, latex)
        assert len([f for f in produced(out) if f.startswith("pptables_f")]) == 4 * 2
        table = open(os.path.join(out, "pptables_f001_05D.tex")).read()
        # one row per algorithm ending with #successes / #trials
        assert len([line for line in table.splitlines() if line.endswith("/15\\\\")]) == 2

    def test_pprldmany(self, two_algs, out):
        dsl, algs, dict_alg = two_algs
        pprldmany.main(pproc.dictAlgByDim(dict_alg)[5], order=algs, outputdir=out, info="05D_all", settings=genericsettings)
        assert "pprldmany_05D_all.pdf" in produced(out)

    def test_ppscatter(self, two_algs, out):
        dsl, algs, dict_alg = two_algs
        ppscatter.main(dict_alg[algs[1]], dict_alg[algs[0]], out, genericsettings)
        assert len([f for f in produced(out) if f.startswith("ppscatter_f") and f.endswith(".pdf")]) == 4

    def test_pprldistr2_and_comp(self, two_algs, out):
        dsl, algs, dict_alg = two_algs
        d0, d1 = (dict_alg[a].dictByDim()[5] for a in algs)
        pprldistr2.main(d0, d1, 5, testbedsettings.current_testbed.rldValsOfInterest, out, "05D_all")
        pprldistr.comp(d1, d0, testbedsettings.current_testbed.rldValsOfInterest, True, out, "all")
        assert {"pplogabs_05D_all.pdf", "pprldistr_05D_all.pdf"} <= set(produced(out))

    def test_ppfigs(self, two_algs, out, tmp_path):
        dsl, algs, dict_alg = two_algs
        ppfigs.main(dict_alg, "ppfigs", algs, out, str(tmp_path / "cmds.tex"))
        assert len([f for f in produced(out) if f.startswith("ppfigs_f") and f.endswith(".pdf")]) == 4

    def test_ppfig2(self, two_algs, out):
        """ppfig2 is not used by the pipeline anymore, but still works"""
        dsl, algs, dict_alg = two_algs
        ppfig2.main(dict_alg[algs[0]], dict_alg[algs[1]], 1e-8, out)
        assert produced(out)

    @pytest.mark.xfail(reason="ppperfprof.main (not used by the pipeline) calls dictAlgByDim on a dict", raises=AttributeError, strict=True)
    def test_ppperfprof(self, two_algs, out):
        dsl, algs, dict_alg = two_algs
        ppperfprof.main(pproc.dictAlgByDim(dict_alg)[5], outputdir=out, verbose=False)
        assert produced(out)

    def test_algportfolio(self, two_algs):
        dsl, algs, dict_alg = two_algs
        portfolio = algportfolio.build(dict_alg, algs)
        assert len(portfolio) == 8
        ds = portfolio.dictByDimFunc()[5][1][0]
        a, b = (dict_alg[alg].dictByDimFunc()[5][1][0] for alg in algs)
        # the portfolio runs the algorithms side by side on each trial
        assert ds.algId == ("SMALL", "SMALL-B")
        assert ds.nbRuns() == a.nbRuns() == 15
        targets = [10, 1e-1, 1e-8]
        for t, ert, ert_a, ert_b in zip(targets, ds.detERT(targets), a.detERT(targets), b.detERT(targets)):
            assert np.isfinite(ert) == (np.isfinite(ert_a) or np.isfinite(ert_b))


class TestSignificance:
    @pytest.fixture
    def pair(self, two_algs):
        dsl, algs, dict_alg = two_algs
        return [dict_alg[a].dictByDimFunc()[5][1][0] for a in algs]

    def test_same_data_is_not_significant(self, pair):
        res = toolsstats.significancetest(pair[0], pair[0], [10, 1e-1, 1e-8])
        assert all(z == 0 for z, p in res)
        assert all(p == pytest.approx(1) for z, p in res)

    def test_faster_algorithm_is_better(self, pair):
        slow, fast = pair
        res = toolsstats.significancetest(fast, slow, [1e-1, 1e-8])
        assert all(z > 0 for z, p in res)  # positive z means the first data set is better
        res2 = toolsstats.significancetest(slow, fast, [1e-1, 1e-8])
        assert [z for z, p in res2] == pytest.approx([-z for z, p in res])

    def test_significance_all_best_vs_other(self, two_algs):
        dsl, algs, dict_alg = two_algs
        datasets = [dict_alg[a].dictByDimFunc()[5][8][0] for a in algs]
        targets = [10, 1e-1, 1e-8]
        res, best = toolsstats.significance_all_best_vs_other(datasets, targets)
        assert len(res) == len(best) == len(targets)
        assert list(best) == list(toolsstats.best_alg_indices(datasets=datasets, targets=targets))

    def test_against_reference_algorithm(self, two_algs):
        dsl, algs, dict_alg = two_algs
        ref = bestalg.load_reference_algorithm(testbedsettings.current_testbed.reference_algorithm_filename, force=True)
        ds = dict_alg[algs[0]].dictByDimFunc()[5][1][0]
        res = toolsstats.significancetest(ref[(5, 1)], ds, [10, 1e-8])
        assert len(res) == 2 and all(0 <= p <= 1 for z, p in res)


def test_rungeneric1_and_rungenericmany_directly(two_algs, tmp_path, monkeypatch):
    """the sub-routines of `cocopp.main` can be called directly"""
    from cocopp import rungeneric1, rungenericmany

    dsl, algs, dict_alg = two_algs
    monkeypatch.chdir(tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dict_alg1 = rungeneric1.main(algs[0], "out1")
        testbedsettings.reset_current_testbed()
        dict_alg2 = rungenericmany.main(algs, "out2")
    # quirk: the returned dictionaries are keyed by (algId, comment) instead of input path
    assert list(dict_alg1) == [("SMALL", "")] and list(dict_alg2) == [("SMALL", ""), ("SMALL-B", "")]
    assert os.path.exists(tmp_path / "out1" / "index.html") and os.path.exists(tmp_path / "out2" / "index.html")
