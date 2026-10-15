# Tests for `cocopp`

A pytest test suite meant as a safety net for restructuring the package.
It replaces the former test runner `python -m cocopp.test`.

## Running

```sh
uv venv && uv pip install -e . pytest      # or: pip install -e . pytest
pytest tests                               # everything except network tests, ~10 minutes
pytest tests -m "not slow"                 # unit, module and smoke tests, ~1 minute
pytest tests --run-network                 # also tests using the online data archives
pytest tests/network --run-network -k "not legacy"   # as in CI: archives, doctests, former default tests
python tests/run_doctests.py               # only the doctests (writes into the package folder!)
pytest tests -n auto                       # in parallel, with pytest-xdist installed
```

## Layout

| folder | content |
|---|---|
| `unit/` | functions and classes in isolation: statistics and formatting helpers, reading and aligning data, `DataSet`/`DataSetList`, target values, reference algorithms, settings, archives (local only), file utilities, the package interface |
| `integration/` | the plotting and table modules called directly (`test_modules.py`) and the full pipeline `cocopp.main` on many scenarios (`test_pipeline.py`) |
| `regression/` | golden-file snapshots of the complete text output of the pipeline |
| `smoke/` | the command line entry points, run in subprocesses |
| `network/` | the official online archives, the doctests, and the scenarios of the former `cocopp/test.py` |

Helpers:

- `synthdata.py` writes **deterministic synthetic COCO data** (bbob in the
  current and the pre-2016 format, bbob-noisy, bbob-constrained with
  g-evaluations, bbob-largescale, bbob-mixint, bbob-boxed, bbob-biobj) and a
  tiny hand-crafted data set whose runtimes and ERTs can be computed by hand.
  The real archives are several MB per algorithm, hence the synthetic data
  make the tests offline and fast.
- `pipeline.py` runs `cocopp.main` in-process and defines the `SCENARIOS`
  shared by the integration and regression tests (each runs once per session).
- `snapshots.py` takes, stores, compares and extracts output snapshots.
- `run_doctests.py` runs the doctests of all package modules.

## Isolation and randomness

`cocopp` keeps much state in module globals and writes files next to its
sources. `conftest.py` therefore, for every test,

- seeds numpy's global random number generator (`conftest.SEED`),
- restores the globals of all `cocopp` modules, the testbed class settings,
  matplotlib `rcParams`, numpy's random state and the working directory,
- runs the test in a fresh temporary working directory,

and for the whole session redirects package-relative files
(`toolsdivers.path_in_package`) into a temporary copy of the package. The
session fails if any test created files in the package or the repository
root. Subprocess tests import that same copy via `PYTHONPATH`.

## Snapshots

The regression tests compare the normalized output (time stamps, temporary
folders and the version are replaced by placeholders) with
`snapshots/<scenario>.json.gz`. After an *intended* change of the output:

```sh
pytest tests/regression --update-snapshots
python tests/snapshots.py diff old.json.gz tests/snapshots/bbob-1.json.gz
python tests/snapshots.py extract tests/snapshots/bbob-1.json.gz /tmp/bbob-1   # for any diff tool
```

where `old.json.gz` can be obtained with, e.g.,
`jj file show -r @- tests/snapshots/bbob-1.json.gz > old.json.gz`.

## Known bugs and quirks

Expected values are often *characterization* values that pin the current
behavior, quirks included (marked as such in comments). Known bugs are
documented as strict `xfail` tests, which start to fail once a bug is fixed
(then remove the `xfail` marker):

- `toolsstats.sliding_window_data`: division by zero with the default
  `number_of_stats=0` and a malformed warning message
- `pproc.DataSetList.append` lists merged index and data files twice
- `pproc.DataSetList.det_best_data` and `run_length_distributions`
  (single algorithm) fail under Python 3
- `DataSet.evals_with_simulated_restarts(..., instances_are_uniform=False)`
  returns unsuccessful runs as negative evaluations instead of `nan`
  when each instance was run once
- `archiving.COCODataArchive.get_found` returns nothing when several entries
  were found, `COCODataArchive.update` of a local archive raises `TypeError`
- `sanitycheck.main` uses a non-existing `rungeneric.shortoptlist`
- `cococommands.DataWithFewSuccesses.print` and `__len__` use a
  non-existing `result` attribute
- `config.config_line_styles` fails for algorithm names without a float
- the unused modules `ppsingle`, `ppfigparam` and `compall.ppperfprof` fail
- the version label lists inconsistent hv-hashes in `PYTHONHASHSEED`
  dependent order

The output is otherwise not fully reproducible for a given numpy seed
either, because it depends on `PYTHONHASHSEED`:

- the bootstrapped dispersion values in the comparison tables (`pptables`):
  `rungenericmany` iterates over function groups in `set` order before,
  consuming a data dependent number of random numbers. The pipeline runs
  in the tests therefore reseed numpy's RNG when entering the table modules
  (`pipeline.reseeded_entry_points`).
- the order of (nearly) tied algorithms in the `pprldmany` legends and of
  inconsistent hv-hashes; the snapshots normalize both by sorting.

Other observations: generated html pages contain a few broken links (e.g.
to `sorttable.js`, recorded in the snapshots), absolute data paths end up
in LaTeX legends, and importing `cocopp.firstsession` downloads data into
the current folder.
