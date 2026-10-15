"""Unit tests for the LaTeX/number formatting helpers in `cocopp.pptex`.

Expected strings are characterization values of the current behavior;
they end up verbatim in the generated tables.
"""

import numpy as np
import pytest

from cocopp import pptex

inf = np.inf

# value: writeFEvals, writeFEvals2, writeFEvals2(.., 3), writeFEvals2(.., isscientific=True),
#        writeFEvalsMaxSymbols(.., 3), writeFEvalsMaxSymbols(.., 5),
#        writeFEvalsMaxPrec(.., 2), writeFEvalsMaxPrec(.., 3, maxfloatrepr=1e3)
FORMATS = [
    (1, ["1", "1", "1", "1.0e0", "1", "1", "1", "1"]),
    (7, ["7", "7", "7", "7.0e0", "7", "7", "7.0", "7.00"]),
    (12.5, ["12", "12", "12.5", "1.2e1", "12.5", "12.5", "12", "12.5"]),
    (123.456, ["120", "120", "123", "1.2e2", "123", "123.46", "123", "123"]),
    (1234.5, ["1200", "1200", "1230", "1.2e3", "1e3", "1234.5", "1234", "1.23e3"]),
    (102345, ["1e5", "1.0e5", "1.02e5", "1.0e5", "1e5", "1.02e5", "1.0e5", "1.02e5"]),
    (1e7, ["1e7", "1.0e7", "1.00e7", "1.0e7", "1e7", "1.00e7", "1.0e7", "1.00e7"]),
    (0.5, ["0.5", "0.5", "0.5", "5.0e-1", "0.5", "0.5", "0.50", "0.500"]),
    (0.0123, ["0.012", "0.012", "0.0123", "1.2e-2", "0.01", "0.0123", "0.01", "0.012"]),
    (inf, 8 * [r"$\infty$"]),
]


@pytest.mark.parametrize("val, expected", FORMATS)
def test_number_formats(val, expected):
    got = [
        pptex.writeFEvals(val),
        pptex.writeFEvals2(val),
        pptex.writeFEvals2(val, 3),
        pptex.writeFEvals2(val, isscientific=True),
        pptex.writeFEvalsMaxSymbols(val, 3),
        pptex.writeFEvalsMaxSymbols(val, 5),
        pptex.writeFEvalsMaxPrec(val, 2),
        pptex.writeFEvalsMaxPrec(val, 3, maxfloatrepr=1e3),
    ]
    assert got == expected


@pytest.mark.parametrize("val, as_int, as_float", [(5, "5", "5"), (123456, "1.2e5", "123456"), (12345678901234, "1e13", "12345678901234")])
def test_writeFEvals2_maxdigits(val, as_int, as_float):
    assert pptex.writeFEvals2(val, maxdigits=5) == as_int
    # quirk: maxdigits is only honored for `int` input
    assert pptex.writeFEvals2(float(val), maxdigits=5) == as_float


@pytest.mark.parametrize("func", [pptex.writeFEvals2, lambda x: pptex.writeFEvalsMaxSymbols(x, 3), lambda x: pptex.writeFEvalsMaxPrec(x, 2)])
def test_nan_is_rejected(func):
    with pytest.raises(AssertionError):
        func(np.nan)


def test_numtotext():
    assert [pptex.numtotext(n) for n in (0, 25, 26, 51, 52, 53, 104, 2755)] == ["A", "Z", "a", "z", "AA", "AB", "BA", "zz"]
    with pytest.raises(Exception):
        pptex.numtotext(2756)


def test_labels_colors_markers():
    assert pptex.writeLabels("a_b_c") == r"a\_b\_c"
    assert pptex.color_to_latex("k") == r"\color{Black}"
    assert pptex.color_to_latex("0.5") == r"\color[gray]{0.5}"
    assert pptex.color_to_latex("#123456") == "{}"
    assert pptex.marker_to_latex("o") == r"$\circ$"
    assert pptex.marker_to_html("o") == "&#9675;"


def test_table_latex():
    table = [["a", "b"], ["c", "d"]]
    # quirk: extra_eol is also appended to the last line, which has no \\
    assert pptex.tableLaTeX(table, spec="cc", extra_eol=[r"\hline"]) == "\\begin{tabular}{cc}\na & b\\\\\\hline\nc & d\\hline\n\\end{tabular}"
    # without the end of the tabular, the last line is terminated with \\
    assert pptex.tableLaTeX(table, spec="cc", add_begin_tabular=False, add_end_tabular=False) == "a & b\\\\\nc & d\\\\"
    assert pptex.tableXLaTeX(table, spec="cc") == "\\begin{tabularx}{1.0\\textwidth}{cc}\na & b\\\\\nc & d\n\\end{tabularx}"
    assert pptex.tableLaTeXStar(table, width="5cm", spec="cc") == "\\begin{tabular*}{5cm}{cc}\na & b\\\\\nc & d\n\\end{tabular*}"


def test_wrong_input_size_error():
    # quirk: __str__ returns the repr of the message
    assert str(pptex.WrongInputSizeError("arr", (2, 3), (3, 3))) == repr("The size of arr is (2, 3). One dimension must be of length (3, 3)!")
