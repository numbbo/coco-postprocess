"""Unit tests for `cocopp.toolsdivers`.

Many expected values below are *characterization* values: they pin the
current behavior (including some quirks, marked as such) so that a
refactoring does not change the produced tables and figures by accident.
"""

import os

import numpy as np
import pytest

import cocopp
from cocopp import toolsdivers as td


class TestStringLists:
    def test_stringlist_from_str_and_list(self):
        assert td.StringList("ab bc") == ["ab", "bc"]
        assert td.StringList(["x", "y"]).as_string == " x y "
        assert td.StringList(None) == []
        assert td.StringList("") == []

    def test_strlist_find_substring_and_regex(self):
        s = td.StrList(["abc", "bcd", "cde", " cde"])
        assert s("bc") == ["abc", "bcd"]
        assert s("a", "b") == ["abc"]
        assert s(["a", "b"]) == ["abc"]
        assert s(".c") == ["bcd", " cde"]
        assert s(".*c") == ["abc", "bcd", "cde", " cde"]
        assert s("BC") == ["abc", "bcd"]  # case insensitive

    def test_strlist_find_by_index(self):
        s = td.StrList(["abc", "bcd", "cde"])
        assert s(1) == ["bcd"]
        assert s([0, 2]) == ["abc", "cde"]
        assert s.found == ["abc", "cde"]
        assert isinstance(s.found, td.StrList)

    def test_strlist_find_with_leading_strs(self):
        s = td.StrList(["2009/BFGS", "2010/IPOP"])
        assert s.find("bbob/2009", leading_strs=["bbob/"]) == ["2009/BFGS"]
        # a trailing part of the leading string is removed as well
        assert s.find("ob/2010", leading_strs=["bbob/"]) == ["2010/IPOP"]

    def test_strlist_find_indices_and_print(self, capsys):
        s = td.StrList(["abc", "bcd", "cde"])
        assert s.find_indices("bc") == [0, 1]
        s.find("abc")
        found_before = list(s.found)
        s.print("d")
        out = capsys.readouterr().out
        assert "   1: 'bcd'" in out and "   2: 'cde'" in out
        assert list(s.found) == found_before  # print does not change found

    def test_strlist_as_string(self):
        assert td.StrList("a b").as_string == " a b "


def test_algorithm_list_ordered_dict():
    names = ["b", "a", "c"]
    d = dict(zip(names[::-1], [1, 2, 3]))
    res = td.AlgorithmList(names).ordered_dict(d)
    assert list(res) == names
    assert res == d


def test_algorithm_list_ordered_dict_appends_unknown_keys_sorted():
    with pytest.warns(UserWarning):
        res = td.AlgorithmList(["b"]).ordered_dict({"z": 1, "b": 2, "a": 3})
    assert list(res) == ["b", "a", "z"]


class TestFolderContexts:
    def test_infolder(self, tmp_path):
        before = os.getcwd()
        with td.Infolder(str(tmp_path)):
            assert os.path.samefile(os.getcwd(), tmp_path)
        assert os.getcwd() == before

    def test_infolder_gone_with_the_wind(self):
        before = os.getcwd()
        with td.InfolderGoneWithTheWind() as _:
            tmp = os.getcwd()
            assert tmp != before
            open("some_file", "w").close()
        assert os.getcwd() == before
        assert not os.path.exists(tmp)


def test_equals_approximately():
    assert td.equals_approximately(1.0, 1.0 + 1e-13)
    assert td.equals_approximately(-1.0, -1.0 - 1e-13)
    assert not td.equals_approximately(1.0, 1.001)
    assert td.equals_approximately(1e20, 1e20 * (1 + 1e-13))


def test_less_ignores_nan_without_warning():
    a = np.array([1.0, np.nan, 3.0])
    with np.errstate(invalid="raise"):
        res = td.less(a, 2.0)
    assert list(res) == [True, False, False]


def test_diff_attr():
    class A:
        pass

    a, b = A(), A()
    a.x, b.x = 1, 1
    a.y, b.y = 1, 2
    a._z, b._z = 1, 2
    a.only_a = 3
    assert td.diff_attr(a, b) == [["y", 1, 2]]


class TestFileHelpers:
    def test_prepend_to_file(self, tmp_path):
        fn = tmp_path / "f.tex"
        fn.write_text("old1\nold2\n")
        td.prepend_to_file(str(fn), ["new1", "new2"])
        assert fn.read_text() == "new1\nnew2\nold1\nold2\n"

    def test_prepend_to_new_file(self, tmp_path):
        fn = tmp_path / "new.tex"
        td.prepend_to_file(str(fn), ["a"])
        assert fn.read_text() == "a\n"

    def test_prepend_to_file_truncates(self, tmp_path, capsys):
        fn = tmp_path / "f.tex"
        fn.write_text("".join("%d\n" % i for i in range(10)))
        td.prepend_to_file(str(fn), ["x"], maxlines=2, warn_message="too long")
        assert fn.read_text().splitlines() == ["x", "0", "1", "2", "3"]
        assert "too long" in capsys.readouterr().out

    def test_replace_in_file(self, tmp_path, capsys):
        fn = tmp_path / "f.txt"
        fn.write_text("abc\nxbx\n")
        td.replace_in_file(str(fn), "b", "B")
        assert fn.read_text() == "aBc\nxBx\n"
        td.replace_in_file(str(tmp_path / "missing"), "a", "b")
        assert "does not exist" in capsys.readouterr().out

    def test_truncate_latex_command_file(self, tmp_path):
        fn = tmp_path / "cmd.tex"
        lines = ["\\providecommand{\\c%d}{}\n" % i for i in range(10)]
        fn.write_text("".join(lines))
        td.truncate_latex_command_file(str(fn), keeplines=3)
        # keeps keeplines + 1 lines, then stops at the next \providecommand
        assert fn.read_text() == "".join(lines[:4])

    def test_truncate_latex_command_file_creates_file(self, tmp_path):
        fn = tmp_path / "cmd.tex"
        td.truncate_latex_command_file(str(fn))
        assert fn.exists() and fn.read_text() == ""


@pytest.mark.parametrize(
    "name, p0, p1, p2, p3",
    [
        ("../data/BFGS_noiseless.tgz", "data/BFGS_noiseless.tgz", "BFGS_noiseless", "BFGS_noiseless", "BFGS_"),
        ("./x/y/BIPOP-CMA-ESdata.tar.gz", "x/y/BIPOP-CMA-ESdata.tar.gz", "BIPOP-CMA-ES", "y/BIPOP-CMA-ES", "BIPOP-CMA-ES"),
        # quirk: strip_pathname2 does not remove a .zip extension
        (" a/b/c.zip ", "a/b/c.zip", "c", "b/c.zip", "c"),
        ("a/.extracted_foo/bar", "a/.extracted_foo/bar", "bar", ".extracted_foo/bar", "bar"),
    ],
)
def test_strip_pathname(name, p0, p1, p2, p3):
    name = name.replace("/", os.sep)
    assert td.strip_pathname(name) == p0
    assert td.strip_pathname1(name) == p1
    assert td.strip_pathname2(name) == p2
    assert td.strip_pathname3(name) == p3


def test_str_to_latex():
    assert td.str_to_latex(r"a_b^c%d~e#f\g") == r"a b\^\,c\%d\ensuremath{\sim}e\#f\textbackslash{}g"


def test_number_of_digits_not_implemented():
    with pytest.raises(NotImplementedError):
        td.number_of_digits(3.0)


# value, num2str(v), num2str(v, 1), num2str(v, 3), num2str(v, 2, force_rounding=True)
NUM2STR = [
    (0, "0", "0", "0", "0"),
    (1, "1", "1", "1", "1"),
    (-1, "-1", "-1", "-1", "-1"),
    (0.5, "0.5", "0.5", "0.5", "0.5"),
    (12345, "12345", "1e4", "12345", "12000"),
    (1234.5, "1234", "1e3", "1234", "1200"),
    (123.45, "123", "123", "123", "120"),
    (12.345, "12", "12", "12.3", "12"),
    (1.2345, "1.2", "1", "1.23", "1.2"),
    (0.12345, "0.12", "0.1", "0.123", "0.12"),
    (0.012345, "0.012", "0.01", "0.0123", "0.012"),
    (0.0012345, "1.2e-3", "1e-3", "1.23e-3", "1.2e-3"),
    (1e-8, "1e-8", "1e-8", "1e-8", "1e-8"),
    (3.3e-12, "3.3e-12", "3e-12", "3.3e-12", "3.3e-12"),
    (1e5, "1e5", "1e5", "1e5", "1e5"),
    (1.5e6, "1.5e6", "2e6", "1.5e6", "1.5e6"),
    (123456789, "1.2e8", "1e8", "1.23e8", "1.2e8"),
    (-0.0234, "-0.023", "-0.02", "-0.0234", "-0.023"),
    (99.9, "100", "100", "99.9", "100"),
    (0.999, "1.0", "1", "0.999", "1.0"),
    (2.0, "2", "2", "2", "2"),
    (100, "100", "100", "100", "100"),
]


@pytest.mark.parametrize("val, s2, s1, s3, s2forced", NUM2STR)
def test_num2str(val, s2, s1, s3, s2forced):
    assert td.num2str(val) == s2
    assert td.num2str(val, 1) == s1
    assert td.num2str(val, 3) == s3
    assert td.num2str(val, 2, force_rounding=True) == s2forced


def test_num2str2_unused_helper():
    assert td._num2str2(0.99, 1) == "1e0"  # the "poor" formatting mentioned in its docstring
    assert td._num2str2(12345.6) == "12346"
    assert td._num2str2(0.00123, 2, True) == "+0.0012"


@pytest.mark.parametrize(
    "s, latex, html",
    [
        ("1e-8", "10^{-8}", "10<sup>-8</sup>"),
        ("-1e-12", "-10^{-12}", "-10<sup>-12</sup>"),
        ("2.3e5", r"2.3\times10^{5}", "2.3 x 10<sup>5</sup>"),
        ("12", "12", "12"),
    ],
)
def test_number_to_latex_and_html(s, latex, html):
    assert td.number_to_latex(s) == latex
    assert td.number_to_html(s) == html


@pytest.mark.parametrize(
    "ratio, html, tex, html_unsigned",
    [
        (0, "&divide;inf", r"\div inf", "&divide;inf"),
        (0.1, "&divide;10", r"\div 10", "&divide;10"),
        (0.4, "&divide;2.5", r"\div 2.5", "&divide;2.5"),
        (0.5, "-50%", r"-50\%", "-50%"),
        (0.9, "-10%", r"-10\%", "-10%"),
        (1, "0%", r"0\%", "0%"),
        (1.01, "+1%", r"+1\%", "1%"),
        (1.5, "+50%", r"+50\%", "50%"),
        (1.99, "+99%", r"+99\%", "99%"),
        (1.995, "&times;2.0", r"\times 2.0", "&times;2.0"),
        (2, "&times;2", r"\times 2", "&times;2"),
        (123.4, "&times;123", r"\times 123", "&times;123"),
    ],
)
def test_ratio2str(ratio, html, tex, html_unsigned):
    assert td.ratio2html(ratio) == html
    assert td.ratio2tex(ratio) == tex
    assert td.ratio2html(ratio, signed=False) == html_unsigned


def test_ratio2str_without_div_or_times():
    assert td._ratio2str(0.1, formdiv=None) == "-90%"
    assert td._ratio2str(5, formtimes=None) == "+400%"


def test_html_subsup():
    assert td.html_subsup(".5", "3", "x", "y") == "<math><msubsup><mn>x</mn><mn>.5y</mn><mn>3</mn></msubsup></math>"


@pytest.mark.parametrize(
    "succ, digit",
    [
        (0, None),
        (0.04, 0),  # quirk: rounds to a ".0" subscript although 0 < succ
        (0.05, 0),
        (0.5, 5),
        (0.94, 9),
        (0.95, None),
        (1, None),
    ],
)
def test_prepend_succ_str(succ, digit):
    tex, html, indent = td.prepend_succ_str(succ, "T", "H")
    if digit is None:
        assert (tex, html, indent) == ("T", "H", "")
    else:
        assert tex == r"$\!\!\!\!{}_{.%d}$T" % digit
        assert html == td.html_subsup(".%d" % digit, "") + "H"
        assert indent == 'style="text-indent: -0.5em;"'


def test_get_version_label_without_reference_values(monkeypatch):
    monkeypatch.setattr(cocopp.testbedsettings, "reference_values", {})
    assert td.get_version_label() == "v" + cocopp.__version__


def test_get_version_label_with_reference_values(monkeypatch):
    monkeypatch.setattr(cocopp.testbedsettings, "reference_values", {"A": "abc"})
    assert td.get_version_label() == "v%s, hv-hash=abc" % cocopp.__version__
    assert td.get_version_label("A") == "v%s, hv-hash=abc" % cocopp.__version__
    monkeypatch.setattr(cocopp.testbedsettings, "reference_values", {"A": "abc", "B": "def"})
    label = td.get_version_label()
    assert label.startswith("v%s, hv-hashes inconsistent:" % cocopp.__version__)
    assert label.endswith("found!") and "abc" in label and "def" in label


def test_path_in_package_is_redirected_by_conftest(package_copy):
    # the test suite redirects package files into a copy to keep the source tree clean
    assert td.path_in_package("refalgs") == os.path.join(str(package_copy), "refalgs")
    assert os.path.isdir(td.path_in_package("refalgs"))


def test_legend_sets_framealpha():
    import matplotlib.pyplot as plt

    plt.plot([1, 2], label="x")
    td.legend()
    assert plt.gca().get_legend().get_frame().get_alpha() == pytest.approx(0.2)
