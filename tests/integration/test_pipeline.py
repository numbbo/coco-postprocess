"""Integration tests of the full post-processing pipeline (`cocopp.main`).

The scenarios from `pipeline.SCENARIOS` run once per session (see the
``pipeline_run`` fixture). The tests here check properties of the output
which a golden-file comparison cannot express well: that files are valid,
that the expected kinds of output exist, and that the numbers in the
tables agree with the data.
"""

import os
import re
import xml.etree.ElementTree as ET

import pytest

import cocopp
from cocopp import bestalg, pproc

import pipeline

pytestmark = pytest.mark.slow

# scenario: number of foreground algorithms
NUM_ALGS = {name: len(fixtures) for name, (fixtures, _, _) in pipeline.SCENARIOS.items()}


@pytest.mark.parametrize("scenario", sorted(pipeline.SCENARIOS))
class TestAllScenarios:
    def test_run_completed(self, scenario, pipeline_run):
        run = pipeline_run(scenario)
        assert "ALL done" in run.stdout
        assert isinstance(run.result, dict)
        assert all(len(dsl) > 0 for dsl in run.result.values())

    def test_top_level_files(self, scenario, pipeline_run):
        run = pipeline_run(scenario)
        assert "index.html" in run.files and "cocopp_commands.tex" in run.files
        commands = run.read("cocopp_commands.tex")
        assert "\\providecommand{\\numofalgs}{%d}" % NUM_ALGS[scenario] in commands
        assert "Data produced with COCO v" + cocopp.__version__ in commands
        index = run.read("index.html")
        for folder in run.subfolders:
            assert folder.split("_")[0] in index

    def test_figures_are_valid(self, scenario, pipeline_run):
        run = pipeline_run(scenario)
        pdfs = [f for f in run.files if f.endswith(".pdf")]
        svgs = [f for f in run.files if f.endswith(".svg")]
        assert pdfs and len(svgs) == len(pdfs)
        for f in pdfs:
            with open(os.path.join(run.outdir, f), "rb") as fh:
                assert fh.read(5) == b"%PDF-", f
        for f in svgs[:: max(1, len(svgs) // 50)]:  # parsing all takes too long
            assert ET.parse(os.path.join(run.outdir, f)).getroot().tag.endswith("svg"), f

    def test_text_files_are_not_empty(self, scenario, pipeline_run):
        run = pipeline_run(scenario)
        empty = [f for f in run.files if f.endswith((".tex", ".html")) and os.path.getsize(os.path.join(run.outdir, f)) == 0]
        assert not empty


class TestSingleAlgorithm:
    SCENARIO = "bbob-1"

    @pytest.fixture
    def run(self, pipeline_run):
        return pipeline_run(self.SCENARIO)

    @pytest.fixture
    def datasets(self, run):
        (dsl,) = run.result.values()
        return dsl

    def test_inventory(self, run):
        assert run.subfolders == ["SYNTH-A"]
        assert len(run.glob("SYNTH-A/pptable_f*_*D.tex")) == 24 * 5
        assert len(run.glob("SYNTH-A/ppfigdim_f*.pdf")) == 24
        assert len(run.glob("SYNTH-A/pprldistr_*D_*.pdf")) == 2 * 6  # dimensions of interest x function groups
        assert len(run.glob("SYNTH-A/pplogloss_*D_*.pdf")) == 2 * 6
        assert len(run.glob("SYNTH-A/pploglosstable_*D_noiselessall.tex")) == 2
        assert len(run.glob("SYNTH-A/pprldmany-single-functions/pprldmany_f*.pdf")) == 24
        assert len(run.glob("SYNTH-A/pprldmany-single-functions/pprldmany_gr_*_*D.pdf")) == 5 * 5
        for page in ["index1.html", "ppfigdim.html", "pptable.html", "pprldistr.html", "pplogloss.html", "pprldflex.html"]:
            assert run.glob("SYNTH-A/" + page), page
        assert not run.glob("*ppconv*") and not run.glob("*ppscatter*")

    def test_result_datasets(self, datasets, bbob_alg_a):
        assert len(datasets) == 24 * 5
        assert {ds.algId for ds in datasets} == {"SYNTH-A"}
        fresh = pproc.DataSetList(bbob_alg_a)
        for ds, ds0 in zip(sorted(datasets, key=lambda d: (d.dim, d.funcId)), fresh):
            assert ds == ds0 and not ds._data_differ(ds0)

    def test_pptable_success_counts(self, run, datasets):
        """the last two columns of the algorithm row are #successes and #trials at the final target"""
        cocopp.config.config("bbob")  # DataSet methods need the current testbed
        for ds in datasets:
            table = run.read("SYNTH-A/pptable_f%03d_%02dD.tex" % (ds.funcId, ds.dim))
            row = table.strip().splitlines()[-1]
            m = re.search(r"& (\d+) & /(\d+)\\\\$", row)
            assert m, row
            assert (int(m.group(1)), int(m.group(2))) == (ds.detSuccesses([1e-8])[0], ds.nbRuns()), (ds, row)

    def test_pptable_first_ert_ratio(self, run, datasets):
        """the first entry of the algorithm row is the ERT ratio to the reference algorithm for target Delta f = 10"""
        cocopp.config.config("bbob")
        reference = bestalg.load_reference_algorithm("refalgs/best2009-bbob.tar.gz", force=True)
        checked = 0
        for ds in datasets:
            if ds.dim not in (5, 20):
                continue
            row = run.read("SYNTH-A/pptable_f%03d_%02dD.tex" % (ds.funcId, ds.dim)).strip().splitlines()[-1]
            m = re.match(r"^ & (?:\$[^$]*\$)?(\d+)\s*&\s*(\.\d+)?\$", row)
            if not m:  # e.g. infinite ERT or another format
                continue
            value = float(m.group(1) + (m.group(2) or ""))
            ratio = ds.detERT([10])[0] / reference[(ds.dim, ds.funcId)].detERT([10])[0]
            assert value == pytest.approx(ratio, rel=0.06, abs=0.06), (ds, row)
            checked += 1
        assert checked >= 20

    def test_latex_commands(self, run):
        commands = run.read("cocopp_commands.tex")
        assert "\\providecommand{\\algname}{SYNTH-A{}}" in commands
        assert re.search(r"\\providecommand\{\\algfolder\}\{SYNTH-A_\d{6}h\d{4}/\}", commands)
        assert "the best algorithm from BBOB 2009" in commands

    def test_html_pages_link_figures(self, run):
        ppfigdim = run.read("SYNTH-A/ppfigdim.html")
        assert all("ppfigdim_f%03d.svg" % f in ppfigdim for f in range(1, 25))
        pptable = run.read("SYNTH-A/pptable.html")
        assert pptable.count("<table") >= 2


def test_expensive_setting_uses_budget_based_targets(pipeline_run):
    run = pipeline_run("bbob-1-expensive")
    default = pipeline_run("bbob-1")
    assert run.glob("SYNTH-A/pptable_f001_05D.tex")
    commands = run.read("cocopp_commands.tex")
    assert "budget" in commands.lower() or "runlength" in commands.lower()
    # tables differ from the default fixed-target setting
    assert run.read("SYNTH-A/pptable_f001_05D.tex") != default.read("SYNTH-A/pptable_f001_05D.tex")


def test_convergence_plots(pipeline_run):
    run = pipeline_run("bbob-1-conv")
    assert len(run.glob("SYNTH-A/ppconv_f*.pdf")) == 24
    assert "ppconv.html" in [os.path.basename(f) for f in run.files]


class TestComparisons:
    def test_two_algorithms(self, pipeline_run, bbob_alg_a, bbob_alg_b):
        run = pipeline_run("bbob-2")
        assert run.subfolders == ["SYNTH_SYNTH"]
        # quirk: the returned dict is keyed by (algId, comment), not by the input path
        assert list(run.result) == [("SYNTH-A", ""), ("SYNTH-B", "")]
        assert len(run.glob("SYNTH_SYNTH/pptables_f*_*D.tex")) == 24 * 5
        assert len(run.glob("SYNTH_SYNTH/ppscatter_f*.pdf")) == 24
        assert len(run.glob("SYNTH_SYNTH/ppfigs_f*.pdf")) == 24
        assert len(run.glob("SYNTH_SYNTH/pplogabs_*D_*.pdf")) == 2 * 7
        assert len(run.glob("SYNTH_SYNTH/pprldmany_*D_*.pdf")) == 5 * 6
        assert len(run.glob("SYNTH_SYNTH/pprldmany-single-functions/pprldmany_f*_*D.pdf")) == 24 * 5
        assert run.glob("SYNTH_SYNTH/pprldistr2.html")

    def test_two_algorithms_tables_have_a_row_per_algorithm(self, pipeline_run):
        run = pipeline_run("bbob-2")
        table = run.read("SYNTH_SYNTH/pptables_f001_05D.tex")
        assert len([line for line in table.splitlines() if line.endswith("/15\\\\")]) == 2
        assert "SYNTH-A" in run.read("SYNTH_SYNTH/pptables.html") and "SYNTH-B" in run.read("SYNTH_SYNTH/pptables.html")

    def test_significance_markers_in_tables(self, pipeline_run):
        """B is twice as fast as A, hence some ERT differences must be significant"""
        run = pipeline_run("bbob-2")
        tables = "".join(open(os.path.join(run.outdir, f)).read() for f in run.files if "/pptables_f" in f)
        assert "\\star" in tables or "downarrow" in tables or "uparrow" in tables

    def test_three_algorithms(self, pipeline_run):
        run = pipeline_run("bbob-3")
        assert run.subfolders == ["SYNTH_SYNTH_SYNTH"]
        assert len(run.glob("SYNTH_SYNTH_SYNTH/pptables_f*_*D.tex")) == 24 * 5
        # scatter plots and pairwise ECDF comparisons are only made for two algorithms
        assert not run.glob("*ppscatter*") and not run.glob("*pplogabs*")

    def test_include_single(self, pipeline_run):
        run = pipeline_run("bbob-small-include-single")
        assert run.subfolders == ["OLDFMT", "SMALL", "SMALL_OLDFM"]
        assert run.glob("SMALL/index1.html") and run.glob("OLDFMT/index1.html")
        assert run.glob("SMALL_OLDFM/index.html")
        # comparison tables only for the functions both algorithms have data for
        assert len(run.glob("SMALL_OLDFM/pptables_f*_*D.tex")) == 2 * 2 + 2 * 2

    def test_background_algorithms(self, pipeline_run):
        run = pipeline_run("bbob-1-background")
        assert run.subfolders == ["SYNTH", "SYNTH-A"]
        assert len(run.result) == 3  # foreground and background algorithms
        assert run.glob("SYNTH/pprldmany_05D_noiselessall.pdf")


class TestOtherSuites:
    def test_biobj_single(self, pipeline_run):
        run = pipeline_run("biobj-1")
        assert run.subfolders == ["SYNTH-BI"]
        assert len(run.glob("SYNTH-BI/pptable_f*_*D.tex")) == 55 * 3
        assert len(run.glob("SYNTH-BI/ppfigdim_f*.pdf")) == 55
        assert run.glob("SYNTH-BI/pprldmany-single-functions/pprldmany_gr_all-functions_*D.pdf")
        assert "best 2016" in run.read("cocopp_commands.tex") or "BBOB 2016" in run.read("cocopp_commands.tex")

    def test_biobj_two(self, pipeline_run):
        run = pipeline_run("biobj-2")
        assert run.subfolders == ["biobj_SYNTH_SYNTH"]
        assert len(run.glob("biobj_SYNTH_SYNTH/ppscatter_f*.pdf")) == 55
        assert len(run.glob("biobj_SYNTH_SYNTH/pptables_f*_*D.tex")) == 55 * 3

    def test_noisy(self, pipeline_run):
        run = pipeline_run("noisy-1")
        assert len(run.glob("SYNTH-NOISY/pptable_f1*_*D.tex")) == 30 * 3
        assert run.glob("SYNTH-NOISY/pprldistr_05D_nzall.pdf")
        assert run.glob("SYNTH-NOISY/pplogloss_20D_nzall.pdf")

    def test_constrained(self, pipeline_run):
        run = pipeline_run("constrained-1")
        assert len(run.glob("SYNTH-CONS/pptable_f*_*D.tex")) == 54 * 2
        assert len(run.glob("SYNTH-CONS/ppfigcons1_*_d*.pdf")) == 9 * 2
        assert run.glob("SYNTH-CONS/pprldistr_05D_all m=0n+1.pdf")  # quirk: blanks and '=' in file names
        (dsl,) = run.result.values()
        assert all(ds.has_constraints for ds in dsl)

    @pytest.mark.parametrize("scenario, folder, dims", [("largescale-1", "SYNTH-LS", (20, 40)), ("mixint-1", "SYNTH-MIXINT", (5, 10)), ("boxed-1", "SYNTH-BOXED", (2, 5))])
    def test_single_suites(self, pipeline_run, scenario, folder, dims):
        run = pipeline_run(scenario)
        assert run.subfolders == [folder]
        assert len(run.glob(folder + "/pptable_f*_*D.tex")) == 24 * len(dims)
        assert len(run.glob(folder + "/ppfigdim_f*.pdf")) == 24

    def test_old_format(self, pipeline_run):
        run = pipeline_run("bbob-old-format")
        assert run.subfolders == ["OLDFMT"]
        assert len(run.glob("OLDFMT/pptable_f*_*D.tex")) == 2 * 2


@pytest.mark.parametrize("option, present, absent", [
    ("--tab-only", ["pptable_f001_05D.tex"], ["ppfigdim_f001.pdf", "pprldistr_05D_noiselessall.pdf"]),
    ("--fig-only", ["ppfigdim_f001.pdf"], ["pptable_f001_05D.tex", "pprldistr_05D_noiselessall.pdf"]),
    ("--rld-only", ["pprldistr_05D_noiselessall.pdf"], ["pptable_f001_05D.tex", "ppfigdim_f001.pdf"]),
    ("--no-rld-single-fcts", ["pptable_f001_05D.tex"], ["pprldmany-single-functions/pprldmany_f001.pdf"]),
])
def test_output_options(option, present, absent, bbob_small, tmp_path):
    run = pipeline.run_main(option + " " + bbob_small, tmp_path)
    for f in present:
        assert run.glob("SMALL/" + f), (option, f)
    for f in absent:
        assert not run.glob("SMALL/" + f), (option, f)


def test_output_is_deterministic(bbob_small, tmp_path):
    import snapshots

    s1 = snapshots.take(pipeline.run_main(bbob_small, tmp_path / "a"))
    s2 = snapshots.take(pipeline.run_main(bbob_small, tmp_path / "b"))
    assert s1["files"] == s2["files"]
    assert not snapshots.diff(s1, s2)


def test_main_twice_in_same_session(bbob_small, bbob_old_format, tmp_path):
    """state must not leak between two calls in the same session (subtest 19 of the former cocopp/test.py)"""
    import contextlib
    import io
    import warnings

    from conftest import isolated_cocopp_state

    # the RNG is reseeded on entry of the table modules, otherwise their dispersion values differ
    with isolated_cocopp_state(tmp_path), warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()), pipeline.reseeded_entry_points():
        warnings.simplefilter("ignore")
        results = [cocopp.main("--no-interactive -o out%d %s" % (i, folder)) for i, folder in enumerate([bbob_small, bbob_old_format, bbob_small])]
    assert [list(r) for r in results] == [[("SMALL", "")], [("OLDFMT", "")], [("SMALL", "")]]
    first, third = (pipeline.PipelineRun(tmp_path, "out%d" % i, None, "", 0) for i in (0, 2))
    assert [pipeline.TIMESTAMP_RE.sub("", f) for f in first.files] == [pipeline.TIMESTAMP_RE.sub("", f) for f in third.files]
    for name in ["SMALL/pptable_f001_05D.tex", "SMALL/pptable_f015_02D.tex", "SMALL/pprldmany-single-functions/pprldmany_f008.tex"]:
        assert first.read(name) == third.read(name), name
