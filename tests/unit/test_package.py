"""Tests of the package-level interface of `cocopp`.

These pin the public API so that a restructuring does not silently drop
names that users (and notebooks) rely upon.
"""

import importlib
import pkgutil

import pytest

import cocopp

ALL_MODULES = sorted(
    name
    for _, name, _ in pkgutil.walk_packages(cocopp.__path__, "cocopp.")
    # __main__ runs the CLI, the other two are scripts needing the network or local data
    if name not in ("cocopp.__main__", "cocopp.firstsession", "cocopp.pprldistr2009_hardestRLB")
)


def test_module_list_is_complete():
    # if this fails, a module was added or removed: update the tests accordingly
    assert len(ALL_MODULES) == 47
    for name in ["cocopp.pproc", "cocopp.compall.pprldmany", "cocopp.comp2.ppscatter", "cocopp.rungeneric"]:
        assert name in ALL_MODULES


@pytest.mark.parametrize("name", ALL_MODULES)
def test_all_modules_import(name, quiet):
    importlib.import_module(name)


def test_interface():
    assert sorted(cocopp.Interface.dir()) == ["archives", "config", "genericsettings", "load", "main", "remote_archives"]
    assert all(hasattr(cocopp, name) for name in cocopp.Interface.dir())
    assert cocopp.main is cocopp.rungeneric.main
    assert cocopp.load is cocopp.cococommands.load


def test_public_names():
    for name in ["set_seed", "archives", "data_archive", "archiving", "config", "genericsettings", "load", "load2", "info", "systeminfo", "pproc", "testbedsettings", "toolsdivers", "toolsstats", "bestalg", "__version__"]:
        assert hasattr(cocopp, name), name
    assert cocopp.archives is cocopp.archiving.official_archives
    assert cocopp.data_archive is cocopp.archives.all


def test_version():
    assert cocopp.__version__ == cocopp._version.__version__
    assert cocopp.__version__[0].isdigit()


def test_set_seed_is_numpy_seed():
    import numpy as np

    cocopp.set_seed(3)
    a = np.random.rand()
    np.random.seed(3)
    assert a == np.random.rand()


def test_main_without_arguments_prints_usage(capsys):
    with pytest.raises(SystemExit):
        cocopp.main([])
    assert "Main routine for post-processing data from COCO" in capsys.readouterr().out


def test_main_help(capsys):
    with pytest.raises(SystemExit):
        cocopp.main("-h")
    assert "--output-dir" in capsys.readouterr().out


def test_main_unknown_option(capsys):
    assert cocopp.main("--no-such-option x") == 2
    assert "For help use -h or --help" in capsys.readouterr().err


def test_systeminfo(capsys):
    cocopp.systeminfo()
    out = capsys.readouterr().out
    assert "Numpy" in out and "Matplotlib" in out and "cocopp " + cocopp.__version__ in out
