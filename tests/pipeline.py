"""Helpers to run the full post-processing pipeline (`cocopp.main`) in tests."""

import contextlib
import fnmatch
import io
import os
import re
import time
import warnings

import numpy as np

import cocopp

from conftest import SEED, isolated_cocopp_state

# the output sub-folder names end with a time stamp like _101509h5934
TIMESTAMP_RE = re.compile(r"_\d{6}h\d{4}")


class PipelineRun:
    """result of a single `cocopp.main` call, see `run_main`"""

    def __init__(self, workdir, outdir, result, stdout, duration):
        self.workdir = str(workdir)
        self.outdir = os.path.join(self.workdir, outdir)
        self.result = result
        self.stdout = stdout
        self.duration = duration

    @property
    def files(self):
        """sorted list of all output files relative to `outdir`"""
        return sorted(
            os.path.relpath(os.path.join(root, f), self.outdir).replace(os.sep, "/")
            for root, _, files in os.walk(self.outdir)
            for f in files
        )

    def glob(self, pattern):
        """output files matching `pattern`, e.g. ``'*/pptable_*.tex'``, with time stamps removed"""
        return [f for f in self.files if fnmatch.fnmatch(TIMESTAMP_RE.sub("", f), pattern)]

    @property
    def subfolders(self):
        """the output sub-folders without time stamps"""
        return sorted(TIMESTAMP_RE.sub("", d) for d in os.listdir(self.outdir) if os.path.isdir(os.path.join(self.outdir, d)))

    def path(self, relative_name):
        """absolute path of an output file given without time stamps"""
        matches = [f for f in self.files if TIMESTAMP_RE.sub("", f) == relative_name]
        assert len(matches) == 1, (relative_name, matches)
        return os.path.join(self.outdir, matches[0])

    def read(self, relative_name):
        with open(self.path(relative_name), encoding="utf-8", errors="replace") as f:
            return f.read()


# modules whose text output depends on the state of numpy's global random number generator
RESEEDED_FUNCTIONS = [("cocopp.pptable", "main"), ("cocopp.compall.pptables", "main"), ("cocopp.compall.pprldmany", "main")]


@contextlib.contextmanager
def reseeded_entry_points(functions=RESEEDED_FUNCTIONS, seed=SEED):
    """reseed numpy's global RNG whenever one of `functions` is called.

    Without this, the bootstrapped dispersion values in the tables depend
    on ``PYTHONHASHSEED``: `rungenericmany` iterates over function groups in
    `set` order before, consuming a data dependent number of random numbers.
    """
    import importlib

    originals = []
    for module_name, name in functions:
        module = importlib.import_module(module_name)
        original = getattr(module, name)

        def wrapper(*args, __original=original, **kwargs):
            np.random.seed(seed)
            return __original(*args, **kwargs)

        originals.append((module, name, original))
        setattr(module, name, wrapper)
    try:
        yield
    finally:
        for module, name, original in originals:
            setattr(module, name, original)


def run_main(args, workdir, setup=None, outdir="out"):
    """run ``cocopp.main('-o outdir ' + args)`` in `workdir` with isolated global state.

    `setup` is called within the isolated state before the run, e.g. to
    change `cocopp.genericsettings`. Numpy's global RNG is reseeded on
    entry of the table modules, see `reseeded_entry_points`. Return a
    `PipelineRun`.
    """
    stdout = io.StringIO()
    os.makedirs(str(workdir), exist_ok=True)
    with isolated_cocopp_state(workdir):
        if setup:
            setup()
        t0 = time.time()
        with warnings.catch_warnings(), contextlib.redirect_stdout(stdout), reseeded_entry_points():
            warnings.simplefilter("ignore")
            result = cocopp.main("--no-interactive -o %s %s" % (outdir, args))
        duration = time.time() - t0
    return PipelineRun(workdir, outdir, result, stdout.getvalue(), duration)


# name: (data fixtures, extra command line options, background data fixtures)
SCENARIOS = {
    "bbob-1": (["bbob_alg_a"], [], []),
    "bbob-2": (["bbob_alg_a", "bbob_alg_b"], [], []),
    "bbob-3": (["bbob_alg_a", "bbob_alg_b", "bbob_alg_c"], [], []),
    "bbob-1-expensive": (["bbob_alg_a"], ["--expensive"], []),
    "bbob-1-conv": (["bbob_alg_a"], ["--conv"], []),
    "bbob-1-background": (["bbob_alg_a"], [], ["bbob_alg_b", "bbob_alg_c"]),
    "bbob-old-format": (["bbob_old_format"], [], []),
    "bbob-small-include-single": (["bbob_small", "bbob_old_format"], ["--include-single"], []),
    "biobj-1": (["biobj_alg"], [], []),
    "biobj-2": (["biobj_alg", "biobj_alg_b"], [], []),
    "noisy-1": (["bbob_noisy"], [], []),
    "constrained-1": (["bbob_constrained"], [], []),
    "largescale-1": (["bbob_largescale"], [], []),
    "mixint-1": (["bbob_mixint"], [], []),
    "boxed-1": (["bbob_boxed"], [], []),
}
