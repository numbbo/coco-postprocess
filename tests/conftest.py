"""Shared fixtures for the `cocopp` test suite.

The package keeps a lot of state in module globals (``genericsettings``,
``testbedsettings.current_testbed``, ``bestalg.bestAlgorithmEntries``,
plotting defaults changed by ``config.config()``, ...) and writes files
next to its own sources (extracted reference algorithms and pickle
caches). The fixtures here

- force the non-interactive ``Agg`` matplotlib backend,
- redirect all package-relative file access (`toolsdivers.path_in_package`)
  to a throw-away copy of the package so that tests never write into the
  source tree,
- snapshot and restore the module globals of all ``cocopp`` modules,
  the testbed class settings, matplotlib's ``rcParams``, the global numpy
  random state and the working directory around *every* test,
- seed numpy's global random number generator before every test,
- provide deterministic synthetic COCO data sets (see `synthdata`).

Markers:

- ``slow``: runs the full post-processing pipeline (seconds to minutes).
  Deselect with ``-m "not slow"``.
- ``network``: needs internet access to the official COCO data archives.
  These tests are skipped unless ``--run-network`` is given.
"""

import contextlib
import copy
import os
import shutil
import sys
import types
import warnings

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))
import synthdata  # noqa: E402

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import cocopp  # noqa: E402
    from cocopp import testbedsettings, toolsdivers  # noqa: E402

PACKAGE_DIR = os.path.dirname(os.path.abspath(cocopp.__file__))
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 20240521


def pytest_addoption(parser):
    parser.addoption("--run-network", action="store_true", default=False, help="run tests that download data from the official COCO archives")
    parser.addoption(
        "--update-snapshots", action="store_true", default=False, help="rewrite the golden output snapshots in tests/snapshots instead of comparing"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: runs (parts of) the full post-processing pipeline")
    config.addinivalue_line("markers", "network: needs access to the official online COCO data archives")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-network"):
        return
    skip = pytest.mark.skip(reason="needs --run-network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


# --------------------------------------------------------------------------
# keep the source tree clean
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def package_copy(tmp_path_factory):
    """a throw-away copy of the installed `cocopp` package folder.

    Its parent folder can be put on ``PYTHONPATH`` for subprocesses.
    """
    root = tmp_path_factory.mktemp("pkgcopy")
    shutil.copytree(
        PACKAGE_DIR,
        root / "cocopp",
        ignore=shutil.ignore_patterns("__pycache__", ".extracted_*", "*.pickle"),
    )
    return root / "cocopp"


@pytest.fixture(scope="session", autouse=True)
def _redirect_package_files(package_copy):
    """make `toolsdivers.path_in_package` point into `package_copy`.

    The reference algorithms in ``refalgs/`` are extracted (and pickled)
    next to the archives, i.e. inside the package, on first use.
    """
    original = toolsdivers.path_in_package

    def path_in_package(sub_path=""):
        return os.path.join(str(package_copy), sub_path)

    toolsdivers.path_in_package = path_in_package
    yield
    toolsdivers.path_in_package = original


def _listing(folder):
    return set(os.listdir(folder)) if os.path.isdir(folder) else set()


@pytest.fixture(scope="session", autouse=True)
def _assert_source_tree_untouched():
    """fail the session if tests created files in the package or repository root.

    Tests run in a temporary working directory (see `_isolate_global_state`)
    and package files are redirected (see `_redirect_package_files`), hence
    new files would indicate a test, or a code path, writing to an
    unexpected place.
    """
    folders = [PACKAGE_DIR, os.path.join(PACKAGE_DIR, "refalgs"), REPO_DIR]
    before = {f: _listing(f) for f in folders}
    yield
    new = {f: sorted(_listing(f) - before[f] - {".pytest_cache"}) for f in folders}
    new = {f: n for f, n in new.items() if n}
    assert not new, "tests created files in the source tree: %s" % new


# --------------------------------------------------------------------------
# global state isolation
# --------------------------------------------------------------------------

_SKIP_TYPES = (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type)
# containers whose content is restored in place, other objects are only rebound
_CONTAINERS = (dict, list, set, np.ndarray)
_NO_COPY = object()


def _snapshot_module(mod):
    """return ``{name: (original_object, deep_copy_or__NO_COPY)}``.

    Only containers are deep-copied. Other objects (e.g. the archives or
    the current testbed) are only remembered by reference: they are
    often shared between modules (``from .archiving import
    official_archives``) and restoring their content would break the
    identity of objects referenced from elsewhere.
    """
    state = {}
    for key, val in vars(mod).items():
        if key.startswith("__") or isinstance(val, _SKIP_TYPES):
            continue
        saved = _NO_COPY
        if isinstance(val, _CONTAINERS):
            try:
                saved = copy.deepcopy(val)
            except Exception:
                pass
        state[key] = (val, saved)
    return state


def _restore_content(obj, saved):
    """restore the content of container `obj` in place from its deep copy `saved`.

    Like this, the identity of containers that are shared between modules
    (e.g. via ``from module import name``) is preserved.
    """
    if saved is _NO_COPY or type(obj) is not type(saved):
        return
    if isinstance(obj, np.ndarray):
        if obj.shape == saved.shape and obj.flags.writeable:
            obj[...] = saved
    elif isinstance(obj, dict):
        obj.clear()
        obj.update(saved)
    elif isinstance(obj, list):
        obj[:] = saved
    elif isinstance(obj, set):
        obj.clear()
        obj.update(saved)


def _restore_module(mod, state):
    for key in [k for k, v in vars(mod).items() if not k.startswith("__") and k not in state and not isinstance(v, _SKIP_TYPES)]:
        delattr(mod, key)  # added during the test
    for key, (original, saved) in state.items():
        _restore_content(original, saved)
        setattr(mod, key, original)


def _testbed_classes():
    return [c for c in vars(testbedsettings).values() if isinstance(c, type) and issubclass(c, testbedsettings.Testbed)]


@contextlib.contextmanager
def isolated_cocopp_state(workdir, seed=SEED):
    """context manager to snapshot and restore the global state of `cocopp`.

    Restores module globals of all ``cocopp`` modules, the testbed class
    settings, matplotlib's ``rcParams``, numpy's random state and error
    settings, and the working directory. Within the context, numpy's
    global RNG is seeded with `seed`, `cocopp` never opens a web browser,
    and the working directory is `workdir`, because the package writes
    output (e.g. ``ppdata``) relative to the current folder.
    """
    modules = {name: mod for name, mod in sys.modules.items() if name == "cocopp" or name.startswith("cocopp.")}
    states = {name: _snapshot_module(mod) for name, mod in modules.items()}
    class_settings = {cls: (cls.__dict__["settings"], copy.deepcopy(cls.__dict__["settings"])) for cls in _testbed_classes() if "settings" in cls.__dict__}
    rc = matplotlib.rcParams.copy()
    rng_state = np.random.get_state()
    np_err = np.geterr()
    cwd = os.getcwd()
    cocopp.genericsettings.interactive_mode = False  # never open a web browser
    np.random.seed(seed)
    os.chdir(str(workdir))
    try:
        yield
    finally:
        os.chdir(cwd)
        import matplotlib.pyplot as plt

        plt.close("all")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            matplotlib.rcParams.update(rc)
        np.random.set_state(rng_state)
        np.seterr(**np_err)
        for cls, (original, saved) in class_settings.items():
            _restore_content(original, saved)
            cls.settings = original
        for name, state in states.items():
            _restore_module(modules[name], state)


@pytest.fixture(autouse=True)
def _isolate_global_state(tmp_path_factory):
    """run every test in `isolated_cocopp_state` within a fresh working directory"""
    with isolated_cocopp_state(tmp_path_factory.mktemp("cwd")):
        yield


# --------------------------------------------------------------------------
# synthetic data
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def synth_root(tmp_path_factory):
    return tmp_path_factory.mktemp("synthdata")


@pytest.fixture(scope="session")
def bbob_alg_a(synth_root):
    """full synthetic ``bbob`` experiment (24 functions, 5 dimensions, 15 instances)"""
    return synthdata.write_bbob(str(synth_root / "bbob"), "SYNTH-A", seed=1)


@pytest.fixture(scope="session")
def bbob_alg_b(synth_root):
    """a second, faster synthetic ``bbob`` "algorithm" on the same problems"""
    return synthdata.write_bbob(str(synth_root / "bbob"), "SYNTH-B", seed=2, speed=2.0)


@pytest.fixture(scope="session")
def bbob_alg_c(synth_root):
    """a third, slower synthetic ``bbob`` "algorithm" """
    return synthdata.write_bbob(str(synth_root / "bbob"), "SYNTH-C", seed=3, speed=0.6)


@pytest.fixture(scope="session")
def bbob_small(synth_root):
    """a small synthetic ``bbob`` experiment: f1, f2, f8, f15 in 2-D and 5-D"""
    return synthdata.write_bbob(str(synth_root / "small"), "SMALL", functions=(1, 2, 8, 15), dims=(2, 5), seed=11)


@pytest.fixture(scope="session")
def bbob_small_b(synth_root):
    """a second "algorithm" on the problems of `bbob_small`, twice as fast"""
    return synthdata.write_bbob(str(synth_root / "small"), "SMALL-B", functions=(1, 2, 8, 15), dims=(2, 5), seed=13, speed=2.0)


@pytest.fixture(scope="session")
def bbob_old_format(synth_root):
    """small synthetic data in the pre-2016 layout without suite/data_format"""
    return synthdata.write_bbob(str(synth_root / "old"), "OLDFMT", functions=(1, 2), dims=(2, 5), seed=12, old_format=True)


@pytest.fixture(scope="session")
def biobj_alg(synth_root):
    """full synthetic ``bbob-biobj`` experiment (55 functions, 2/3/5-D, 10 instances)"""
    return synthdata.write_biobj(str(synth_root / "biobj"), "SYNTH-BI", seed=21)


@pytest.fixture(scope="session")
def biobj_alg_b(synth_root):
    return synthdata.write_biobj(str(synth_root / "biobj"), "SYNTH-BI-B", seed=22, speed=2.0)


@pytest.fixture(scope="session")
def bbob_noisy(synth_root):
    return synthdata.write_bbob(str(synth_root / "noisy"), "SYNTH-NOISY", functions=range(101, 131), dims=(2, 5, 20), seed=31, suite="bbob-noisy")


@pytest.fixture(scope="session")
def bbob_constrained(synth_root):
    """constrained data with g-evaluations, see `synthdata.write_bbob`"""
    return synthdata.write_bbob(str(synth_root / "cons"), "SYNTH-CONS", functions=range(1, 55), dims=(2, 5), seed=32, suite="bbob-constrained")


@pytest.fixture(scope="session")
def bbob_largescale(synth_root):
    return synthdata.write_bbob(str(synth_root / "ls"), "SYNTH-LS", dims=(20, 40), seed=33, suite="bbob-largescale", budget_multiplier=50)


@pytest.fixture(scope="session")
def bbob_mixint(synth_root):
    return synthdata.write_bbob(str(synth_root / "mixint"), "SYNTH-MIXINT", dims=(5, 10), seed=34, suite="bbob-mixint")


@pytest.fixture(scope="session")
def bbob_boxed(synth_root):
    return synthdata.write_bbob(str(synth_root / "boxed"), "SYNTH-BOXED", dims=(2, 5), seed=35, suite="bbob-boxed")


@pytest.fixture(scope="session")
def pipeline_run(request, tmp_path_factory):
    """return a function ``run(scenario_name)`` returning a cached `pipeline.PipelineRun`.

    Scenarios are defined in `pipeline.SCENARIOS`; each is run at most
    once per test session.
    """
    import pipeline

    cache = {}

    def run(name):
        if name not in cache:
            fixtures, options, background = pipeline.SCENARIOS[name]
            folders = [request.getfixturevalue(f) for f in fixtures]
            background = [request.getfixturevalue(f) for f in background]

            def setup():
                if background:
                    cocopp.genericsettings.background = {None: background}

            args = " ".join(list(options) + folders)
            cache[name] = pipeline.run_main(args, tmp_path_factory.mktemp("run-" + name), setup=setup)
        return cache[name]

    return run


@pytest.fixture
def quiet():
    """silence the (many) warnings the package emits while loading data"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def load(path):
    """load a `DataSetList` without the package's chatter"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return cocopp.pproc.DataSetList(str(path))


@pytest.fixture
def dsl_small(bbob_small):
    """freshly loaded `DataSetList` of `bbob_small` (8 data sets)"""
    testbedsettings.reset_current_testbed()
    return load(bbob_small)
