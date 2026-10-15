"""Unit tests for settings modules (`testbedsettings`, `genericsettings`,
`config`, `dataformatsettings`), `findfiles`, `captions` and small helpers
of `ppfig`.
"""

import os
import tarfile
import zipfile

import numpy as np
import pytest

import cocopp
from cocopp import captions, config, dataformatsettings, findfiles, genericsettings, ppfig, pproc
from cocopp import testbedsettings as tbs

# suite name -> (testbed class name, .name, first and last function, instances_are_uniform, has_constraints)
TESTBEDS = {
    "bbob": ("GECCOBBOBTestbed", "bbob", 1, 24, True, False),
    "bbob-noisy": ("GECCOBBOBNoisyTestbed", "bbob", 101, 130, True, False),  # quirk: name is 'bbob'
    "bbob-biobj": ("GECCOBiObjBBOBTestbed", "bbob-biobj", 1, 55, False, False),
    "bbob-biobj-ext": ("GECCOBiObjExtBBOBTestbed", "bbob-biobj-ext", 1, 92, False, False),
    "bbob-constrained": ("CONSBBOBTestbed", "bbob-constrained", 1, 54, True, True),
    "bbob-largescale": ("BBOBLargeScaleTestbed", "bbob-largescale", 1, 24, True, False),
    "bbob-mixint": ("GECCOBBOBMixintTestbed", "bbob-mixint", 1, 24, True, False),
    "bbob-biobj-mixint": ("GECCOBBOBBiObjMixintTestbed", "bbob-biobj-mixint", 1, 92, False, False),
    "bbob-JOINED-bbob-largescale": ("BBOBLargeScaleJOINEDTestbed", "bbob", 1, 24, True, False),
    "bbob-boxed": ("SBOXCOSTTestbed", "bbob-boxed", 1, 24, True, False),
    "sbox-cost": ("SBOXCOSTTestbed", "bbob-boxed", 1, 24, True, False),
    "bbob-JOINED-bbob-boxed": ("SboxCostJOINEDTestbed", "bbob and bbob-boxed", 1, 24, True, False),
}


class TestTestbedSettings:
    def test_all_suites_are_tested(self):
        assert set(TESTBEDS) == set(tbs.suite_to_testbed)

    @pytest.mark.parametrize("suite", sorted(TESTBEDS))
    def test_load_current_testbed(self, suite):
        cls, name, first, last, uniform, constraints = TESTBEDS[suite]
        tb = tbs.load_current_testbed(suite, pproc.TargetValues)
        assert tb is tbs.current_testbed
        assert type(tb).__name__ == cls == tbs.get_testbed_from_suite(suite)
        assert tbs.SuiteClass(suite) is type(tb)
        assert (tb.name, tb.first_function_number, tb.last_function_number) == (name, first, last)
        assert tb.instances_are_uniform is uniform and tb.has_constraints is constraints
        assert tb.string_evals == ("evaluations" if constraints else "$f$-evaluations")
        assert tb.string_evals_short == ("evals" if constraints else "FEvals")
        # target value attributes are converted to the given class
        assert isinstance(tb.pprldmany_target_values, pproc.TargetValues)

    def test_unknown_suite(self):
        with pytest.raises(ValueError):
            tbs.get_testbed_from_suite("bbob-unknown")
        with pytest.raises(ValueError):
            tbs.load_current_testbed("bbob-unknown", pproc.TargetValues)

    def test_reset(self):
        tbs.load_current_testbed("bbob", pproc.TargetValues)
        tbs.reset_current_testbed()
        assert tbs.current_testbed is None

    def test_reference_values(self):
        tbs.reset_reference_values()
        assert tbs.get_reference_values(None) is None and tbs.get_first_reference_values() is None
        tbs.update_reference_values("A", "h1")
        tbs.copy_reference_values("A", "B")
        assert tbs.get_reference_values("B") == "h1" and tbs.get_reference_values(None) == "h1"
        with pytest.warns(UserWarning, match="different"):
            tbs.update_reference_values("C", "h2")
        assert tbs.get_reference_values(None) == {"h1", "h2"}
        assert tbs.get_first_reference_values() == "h1"
        tbs.reset_reference_values()
        assert tbs.reference_values == {}

    def test_info_and_short_names(self):
        tb = tbs.load_current_testbed("bbob", pproc.TargetValues)
        assert tb.info(1) == "F1 Sphere"
        assert tb.info().startswith("Testbed of 24 noiseless functions")
        names = tbs.get_short_names("bbob-benchmarkshortinfos.txt")
        assert sorted(names) == list(range(1, 25)) and names[1] == "Sphere"
        with pytest.warns(UserWarning):
            assert tbs.get_short_names("nonexisting.txt") is None

    def test_constraints(self):
        assert [tbs.CONSBBOBTestbed.number_of_constraints(10, f) for f in range(1, 8)] == [1, 3, 9, 16, 24, 54, 1]
        assert tbs.CONSBBOBTestbed.number_of_constraints(10, 4, active_only=True) == 11
        assert tbs.CONSBBOBTestbed.constraint_category(5) == "6ndiv4+9"
        assert tbs.CONSBBOBTestbed.constraint_category(5, active_only=True) == "6+n"
        with pytest.raises(NotImplementedError):
            tbs.Testbed.number_of_constraints(10, 1)

    def test_filter_bbob_and_largescale(self):
        class DS:
            def __init__(self, suite):
                self.suite_name = suite

        tb = tbs.load_current_testbed("bbob", pproc.TargetValues)
        dsl = [DS("bbob"), DS("bbob-largescale")]
        tb.filter(dsl)
        assert [ds.suite for ds in dsl] == ["bbob-largescale"] * 2
        dsl = [DS("bbob"), DS("bbob-boxed")]
        tb.filter(dsl)
        assert [ds.suite for ds in dsl] == ["bbob-JOINED-bbob-boxed"] * 2
        with pytest.raises(ValueError):
            tb.filter([DS("bbob-biobj")])


class TestConfig:
    @pytest.mark.parametrize(
        "name, first_digit, after",
        [(".1bb", 0, 2), ("s-.2bbb", 1, 4), ("ss1.23bbbb", 2, 6), ("sss-2e0bbbbb", 3, 7), ("ssss1.2e-3bbbbbb", 4, 10), ("abc", -1, 0)],
    )
    def test_index_after_float(self, name, first_digit, after):
        assert config._index_after_float(name, True) == first_digit
        assert config._index_after_float(name) == after

    def test_line_style_mapping(self):
        names = ["1.0-CMA", "2.0-CMA", "BFGS", "0.5-CMA"]
        assert config.map_indices_to_line_styles(names) == {0: 0, 1: 0, 2: 2, 3: 0}
        styles = ["s0", "s1", "s2", "s3"]
        # styles of the indices [0, 1, 3] are reassigned in the sorted order of 0.5, 1.0, 2.0
        assert config.sorted_line_styles(styles, names, [0, 1, 3]) == ["s1", "s3", "s2", "s0"]

    def test_str_to_colormap(self):
        colors = list(config._str_to_colormap("viridis..5", 3))
        assert len(colors) == 3 and all(c.startswith("#") for c in colors)
        assert colors[0] != colors[-1]

    def test_config_line_styles_parameter_sweep(self, monkeypatch):
        monkeypatch.setattr(genericsettings, "parameter_sweep", True)
        monkeypatch.setattr(genericsettings, "_current_args", ["a1.0x", "a2.0x", "b3.0y"])
        before = [dict(s) for s in genericsettings.line_styles]
        config.config_line_styles()
        after = genericsettings.line_styles
        assert after[0]["color"] != before[0]["color"]  # colors from the colormap
        assert after[0]["marker"] == after[1]["marker"]  # same algorithm family, same marker
        assert after[2]["marker"] != after[0]["marker"]

    @pytest.mark.xfail(reason="parameter sweep fails for algorithm names without a float", raises=ValueError, strict=True)
    def test_config_line_styles_parameter_sweep_name_without_float(self, monkeypatch):
        monkeypatch.setattr(genericsettings, "parameter_sweep", True)
        monkeypatch.setattr(genericsettings, "_current_args", ["a1.0x", "a2.0x", "b"])
        config.config_line_styles()

    def test_config_sets_testbed_and_bootstrap_size(self):
        config.config("bbob-biobj")
        assert tbs.current_testbed.name == "bbob-biobj"
        assert genericsettings.simulated_runlength_bootstrap_sample_size == pytest.approx(10 + 990 / (1 + 10 * genericsettings.in_a_hurry))
        from cocopp.compall import pprldmany

        assert pprldmany.x_limit == genericsettings.xlimit_pprldmany

    def test_config_expensive_uses_runlength_based_targets(self, monkeypatch, quiet):
        from cocopp import ppfigdim, pprldistr

        monkeypatch.setattr(genericsettings, "isExpensive", True)
        config.config("bbob")
        assert genericsettings.runlength_based_targets
        assert genericsettings.maxevals_fix_display == genericsettings.xlimit_expensive
        tb = tbs.current_testbed
        assert tb.scenario == tbs.scenario_rlbased
        for attr in ["pprldmany_target_values", "ppfigdim_target_values", "pptable_targetsOfInterest", "ppfigs_ftarget"]:
            assert isinstance(getattr(tb, attr), pproc.RunlengthBasedTargetValues), attr
        assert ppfigdim.xlim_max == genericsettings.xlimit_expensive
        assert pprldistr.runlen_xlimits_max == genericsettings.xlimit_expensive / 2

    def test_global_state_is_restored_after_previous_test(self):
        """the conftest fixture must undo `config` side effects of other tests"""
        from cocopp import ppfigdim

        assert genericsettings.isExpensive is False
        assert ppfigdim.xlim_max is None


class TestGenericSettings:
    def test_default_settings_copy(self):
        assert genericsettings.default_settings is not genericsettings
        assert genericsettings.default_settings.outputdir == "ppdata"
        assert cocopp.toolsdivers.diff_attr(genericsettings.default_settings, genericsettings) == [
            ["interactive_mode", True, False]  # set by conftest
        ]

    def test_instances_of_interest(self):
        assert genericsettings.instancesOfInterest2009 == {i: 3 for i in range(1, 6)}
        assert all(isinstance(d, dict) for d in genericsettings.instancesOfInterest)


def test_data_format_mapping():
    m = dataformatsettings.data_format_name_to_class_mapping
    assert m[None] is m["bbob"] is dataformatsettings.BBOBOldDataFormat
    assert m["bbob-new2"] is dataformatsettings.BBOBNewDataFormat
    biobj = m["bbob-biobj"]()
    assert (biobj.evaluation_idx, biobj.function_value_idx) == (0, 1)
    new = m["bbob-new"]()
    assert (new.evaluation_idx, new.evaluation_constraints_idx, new.function_value_idx) == (0, 1, 2)


class TestFindFiles:
    def test_recognized_filetypes(self, tmp_path):
        assert findfiles.is_recognized_repository_filetype(str(tmp_path))
        for name in ["a.tgz", "a.tar.gz", "a.tar", "a.zip"]:
            assert findfiles.is_recognized_repository_filetype(name)
            assert findfiles.is_recognized_repository_filetype2(name)
        assert not findfiles.is_recognized_repository_filetype("a.info")
        assert not findfiles.is_recognized_repository_filetype2(str(tmp_path))

    def test_main_lists_info_files(self, bbob_small):
        found = findfiles.main(bbob_small)
        assert sorted(os.path.basename(f) for f in found) == ["bbobexp_f1.info", "bbobexp_f15.info", "bbobexp_f2.info", "bbobexp_f8.info"]

    def test_main_warns_on_empty_folder(self, tmp_path):
        with pytest.warns(UserWarning, match="Could not find"):
            assert findfiles.main(str(tmp_path)) == []

    @pytest.mark.parametrize("kind", ["tgz", "zip"])
    def test_archives_are_extracted(self, tmp_path, bbob_small, kind):
        name = str(tmp_path / ("SMALL." + kind))
        if kind == "tgz":
            with tarfile.open(name, "w:gz") as tar:
                tar.add(bbob_small, arcname="SMALL")
        else:
            with zipfile.ZipFile(name, "w") as z:
                for root, _, files in os.walk(bbob_small):
                    for f in files:
                        p = os.path.join(root, f)
                        z.write(p, os.path.relpath(p, os.path.dirname(bbob_small)))
        found = findfiles.main(name)
        assert len(found) == 4
        assert all(os.sep + ".extracted_SMALL" + os.sep in f for f in found)
        assert findfiles.get_directory(name, False) == str(tmp_path / ".extracted_SMALL")

    def test_hash(self):
        assert findfiles.hash("abc") == "a9993e364706816aba3e25717850c26c9cd0d89d"
        assert findfiles.hash("abc", 4) == "a999" and findfiles.hash("abc", 0) == ""

    def test_output_directory_sub_folder(self, monkeypatch):
        monkeypatch.setattr(tbs, "current_testbed", None)
        assert findfiles.get_output_directory_sub_folder("data/ALG.tgz", addtime=False) == "ALG"
        assert findfiles.get_output_directory_sub_folder(["a/LONGNAME", "b/X"], addtime=False) == "LONGN_X"
        assert findfiles.get_output_directory_sub_folder(["a", "b"], addhash=3, addtime=False) == "a_b_" + findfiles.hash("ab", 3)
        args = ["a%d" % i for i in range(9)]
        assert findfiles.get_output_directory_sub_folder(args, addtime=False).endswith("a6_et_al")
        tbs.load_current_testbed("bbob-biobj", pproc.TargetValues)
        assert findfiles.get_output_directory_sub_folder("x/ALG", addtime=False) == "biobj_ALG"
        assert len(findfiles.get_output_directory_sub_folder("ALG")) == len("biobj_ALG_") + len("0101h0101") + 2
        with pytest.raises(ValueError):
            findfiles.get_output_directory_sub_folder([])


class TestCaptions:
    def test_all_keywords_are_replaced(self, quiet):
        config.config("bbob")
        for key in captions.replace_dict:
            res = captions.replace("x " + key + " y")
            assert "!!" not in res, key
        assert captions.replace("!!THE-REF-ALG!!") == "the best algorithm from BBOB 2009"
        assert captions.replace("!!TOTAL-NUM-OF-FUNCTIONS!!") == "24"
        assert captions.replace("!!NUM-OF-TARGETS-IN-ECDF!!") == "51"

    def test_html_replacements(self):
        config.config("bbob")
        assert captions.replace("!!DF!! 2-D a-b", html=True) == "&Delta;f 2different dimensions a&#8722;b"

    def test_unknown_keyword_warns(self):
        with pytest.warns(UserWarning, match="!!"):
            captions.replace("!!UNKNOWN!!")

    def test_reference_algorithm_text(self):
        config.config("bbob-constrained")
        assert captions.get_reference_algorithm_text(False) == ""
        with pytest.raises(NotImplementedError):
            captions.get_reference_algorithm_text(True)


class TestPpfigHelpers:
    def test_consecutive_numbers(self):
        assert ppfig.consecutiveNumbers([0, 1, 2, 4, 5, 7, 8, 9]) == "0-2, 4, 5, 7-9"
        assert ppfig.consecutiveNumbers([0, 1, 2, 4, 5, 7, 8, 9], "f") == "f0-f2, f4, f5, f7-f9"
        assert ppfig.groupByRange([1, 2, 5]) == [[1, 2], [5]]

    def test_enum(self):
        e = ppfig.enum("A", "B", C=7)
        assert (e.A, e.B, e.C) == (0, 1, 7)

    def test_discretize_limits(self):
        lo, hi = ppfig.discretize_limits((1, 70))
        assert lo == pytest.approx(10**-0.2)
        assert hi == pytest.approx(100 * (1 + 1e-6))
        assert ppfig.discretize_limits((1, 20))[1] == pytest.approx(30 * (1 + 1e-6))

    def test_marker_positions(self):
        x = np.logspace(0, 4, 50)
        y = np.linspace(0, 1, 50)
        xp, yp = ppfig.marker_positions(x, y, 3, 10, ax_limits=(1, 1e4, 0, 1))
        assert len(xp) == len(yp) <= 11
        assert xp[-1] == x[-1] and set(xp) <= set(x)

    def test_plot_unif_log_x_markers(self):
        lines = ppfig.plotUnifLogXMarkers(np.logspace(0, 3, 20), np.linspace(0, 1, 20), 3, marker="o", label="x")
        assert len(lines) == 3

    def test_save_figure(self, tmp_path):
        import matplotlib.pyplot as plt

        plt.plot([1, 2], [3, 4])
        ppfig.save_figure(str(tmp_path / "fig"))  # default formats from genericsettings
        assert (tmp_path / "fig.pdf").exists() and (tmp_path / "fig.svg").exists()
        ppfig.save_figure(str(tmp_path / "fig2"), format="png")
        assert (tmp_path / "fig2.png").exists()

    def test_html_links(self, tmp_path):
        (tmp_path / "f.html").write_text("")
        assert ppfig.add_link(str(tmp_path), "", "f.html", "label") == '<a href="f.html">label</a><br>\n'
        assert ppfig.add_link(str(tmp_path), "", "missing.html", "label") == ""
        assert ppfig.add_link(str(tmp_path), "sub", "x.html", "l", "  ", True, 5) == '  <a href="sub/x.html#5">l</a><br>\n'
        assert ppfig.format_link_list_entry_in_html("x") == "x<br>\n"
        assert ppfig.add_image("a.svg", True) == '<a href="a.svg"><IMG SRC="a.svg" height="160em"></a>'
        assert ppfig.add_image("a.svg", False, 10) == '<IMG SRC="a.svg" height="10em">'
