"""Unit tests for `cocopp.cococommands` (``load``, ``load2``,
``DataWithFewSuccesses``) and the html/LaTeX description helpers
`cocopp.htmldesc` and `cocopp.preparetexforhtml`.
"""

import numpy as np
import pytest

import cocopp
from cocopp import cococommands, htmldesc, preparetexforhtml, pproc, testbedsettings

from conftest import load


class TestDataWithFewSuccesses:
    @pytest.fixture
    def few(self, bbob_small, quiet):
        testbedsettings.reset_current_testbed()
        return cococommands.DataWithFewSuccesses(bbob_small, minsuccesses=9)

    def test_attributes(self, few, bbob_small):
        dsl = load(bbob_small)
        assert few.trials == [15] * 8
        assert few.successes == [ds.detSuccesses([1e-8])[0] for ds in dsl]
        assert few.evaluations == pytest.approx([np.sum(ds.maxevals) / 15 for ds in dsl])
        assert few.input_parameters["minsuccesses"] == 9

    def test_all_and_budget_left(self, few):
        expected = {(f, d): v for (f, d), v in few.all.items()}
        assert all(v[1] < 9 for v in expected.values())
        assert all(v[2] == 15 for v in expected.values())
        assert list(few.all) == sorted(few.all)
        assert few.with_budget_left == few.all  # budget multiplier is inf
        few.budget_multiplier = 0
        assert few.with_budget_left == {}
        assert few.current == few.all

    def test_minsuccesses_and_threshold_changes(self, few):
        n = len(few.all)
        few.minsuccesses = 16
        assert len(few.all) == 8
        few.minsuccesses = 9
        few.compute_successes(1e2)  # easy target: everything solved
        assert len(few.all) == 0 < n or n == 0

    def test_from_datasetlist(self, bbob_small, quiet):
        dsl = load(bbob_small)
        few = cococommands.DataWithFewSuccesses(dsl, minsuccesses=16, exclude=[(1, 2)])
        assert (1, 2) not in few.all and len(few.all) == 7

    @pytest.mark.xfail(reason="known bug: print and __len__ use a non-existing `result` attribute", raises=AttributeError, strict=True)
    def test_len(self, few):
        len(few)


def test_true_number_of_trials(dsl_small):
    assert cococommands.true_number_of_trials(dsl_small[0]) == 15


class TestLoad2:
    def test_single_algorithm(self, bbob_small, quiet):
        testbedsettings.reset_current_testbed()
        dsl = cocopp.load2(bbob_small)
        assert isinstance(dsl, pproc.DataSetList) and len(dsl) == 8

    def test_filters(self, bbob_small, quiet):
        testbedsettings.reset_current_testbed()
        dsl = cocopp.load2(bbob_small, keep=lambda ds: ds.funcId < 10, remove=lambda ds: ds.funcId == 2)
        assert sorted({ds.funcId for ds in dsl}) == [1, 8]

    def test_several_algorithms(self, bbob_small, bbob_small_b, quiet):
        testbedsettings.reset_current_testbed()
        res = cocopp.load2([bbob_small, bbob_small_b])
        assert sorted(res) == [2, 5]
        assert list(res[5]) == [bbob_small, bbob_small_b]
        assert len(cocopp.load2([bbob_small, bbob_small_b], flat_list=True)) == 16


class TestHtmlDescriptions:
    def test_get_value(self):
        text = htmldesc.getValue("##bbobppfigdimlegendrlbased##")
        assert text and "##" not in text
        assert htmldesc.getValue("##not-a-key##") == ""
        assert len(htmldesc.descriptions) == 102

    def test_prepare_tex_for_html(self, tmp_path, quiet):
        out = tmp_path / "latex_commands_for_html.tex"
        preparetexforhtml.main(str(out))
        text = out.read_text()
        assert text.count("\\begin{document}") == 1 and text.rstrip().endswith("\\end{document}")
        # every scenario gets the same set of caption commands, each preceded by its html key
        for scenario in ["fixed", "rlbased", "biobjfixed", "bbobboxedfixed"]:
            assert "\\providecommand{\\bbobppfigdimlegend%s}" % scenario in text
            assert "\\#\\#bbobppfigdimlegend%s\\#\\#" % scenario in text
