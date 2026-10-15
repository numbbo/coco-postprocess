"""Golden-file regression tests of the complete post-processing output.

Each scenario from `pipeline.SCENARIOS` is run once (cached for the test
session) on deterministic synthetic data with a fixed random seed, and
the normalized text output (all LaTeX tables and commands, html pages,
the list of produced files and of broken html links) is compared to
the stored snapshot in ``tests/snapshots``.

These tests are the safety net for refactoring: any change in the
produced numbers or formatting shows up as a diff. If a change is
intended, rewrite the snapshots with::

    pytest tests/regression --update-snapshots

and review the changes of the (gzipped) snapshots with, e.g.,
``python tests/snapshots.py`` (see `snapshots.diff`).
"""

import os

import pytest

import pipeline
import snapshots

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("scenario", sorted(pipeline.SCENARIOS))
def test_snapshot(scenario, pipeline_run, synth_root, request):
    run = pipeline_run(scenario)
    actual = snapshots.take(run, replacements=[(str(synth_root), "<DATA>")])
    if request.config.getoption("--update-snapshots"):
        snapshots.save(scenario, actual)
        pytest.skip("snapshot written")
    if not os.path.exists(snapshots.path(scenario)):
        pytest.fail("no snapshot for %s, run pytest with --update-snapshots" % scenario)
    expected = snapshots.load(scenario)
    differences = snapshots.diff(expected, actual)
    assert not differences, "output of scenario %s changed:\n%s" % (scenario, differences)


def test_no_orphaned_snapshots():
    stored = {f[: -len(".json.gz")] for f in os.listdir(snapshots.SNAPSHOT_DIR) if f.endswith(".json.gz")}
    assert stored <= set(pipeline.SCENARIOS)
