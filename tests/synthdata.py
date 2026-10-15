"""Deterministic generator for synthetic COCO experiment data.

The real data archives are several MB per algorithm and live online. For
offline, fast and reproducible tests we instead write small, *synthetic*
data folders that follow the on-disk formats written by the COCO
experiment loggers closely enough for `cocopp` to read them:

- single-objective ``bbob`` (and ``bbob-noisy``) data in the "new"
  (``data_format = 'bbob-new2'``, constraints evaluations in the second
  column) and the "old" (no ``data_format``) layouts, consisting of
  ``.info`` index files and ``.dat``/``.tdat`` data files;
- bi-objective ``bbob-biobj`` data (``indicator = 'hyp'``).

Every generator takes a ``seed`` and only uses its own
`numpy.random.Generator`, hence the produced files are byte-identical
for the same arguments, independently of the global numpy random state.

The simulated "optimizer" improves the best-so-far Delta-f value by a
random factor at random evaluation increments. Function and dimension
determine the convergence speed, such that some (function, dimension)
pairs are solved in all trials, some in a few and some in none, which
exercises the success/failure code paths of the post-processing.
"""

import os

import numpy as np

BBOB_DIMS = (2, 3, 5, 10, 20)
BBOB_FUNCTIONS = tuple(range(1, 25))
BBOB_INSTANCES = tuple(range(1, 16))
BIOBJ_DIMS = (2, 3, 5)
BIOBJ_FUNCTIONS = tuple(range(1, 56))
BIOBJ_INSTANCES = tuple(range(1, 11))

_PRECISION = 1e-8


def _log_spaced_evals(last, per_decade=10):
    """return sorted unique integer evaluations ``1, 2, ...`` up to `last`

    roughly log-uniformly spaced, always including 1 and `last`."""
    if last <= 1:
        return [1]
    n = int(np.ceil(np.log10(last) * per_decade)) + 1
    evals = np.unique(np.floor(np.logspace(0, np.log10(last), n)).astype(int))
    evals = [int(e) for e in evals if e < last]
    return evals + [int(last)]


def _trajectory(rng, f0, rate, budget, final=_PRECISION / 100):
    """simulate a monotone best-so-far trajectory.

    Return two lists ``evals`` and ``fvals`` (Delta f), where
    ``fvals[i]`` is the best-so-far value from evaluation ``evals[i]`` on.
    The first evaluation is always 1. The run stops when the `budget` is
    exhausted or `final` is reached; the last entry is the last
    evaluation.
    """
    evals, fvals = [1], [f0]
    e, f = 1, f0
    while True:
        e += int(rng.geometric(rate))
        if e > budget:
            break
        f *= 10 ** -rng.uniform(0.05, 0.6)
        evals.append(e)
        fvals.append(f)
        if f < final:
            break
    if evals[-1] < budget and fvals[-1] >= final:  # unsuccessful: ran into the budget
        evals.append(int(budget))
        fvals.append(fvals[-1])
    return evals, fvals


def _bbob_target_crossings(evals, fvals, nb_per_decade=5):
    """return indices into `evals` at which a new ``10**(i/5)`` target is reached,

    as written into ``.dat`` files by the bbob logger. Index 0 is always
    included and the final index is included when it reaches below the
    final precision."""
    idx = [0]
    level = np.floor(np.log10(fvals[0]) * nb_per_decade)
    for i in range(1, len(fvals)):
        new_level = np.floor(np.log10(max(fvals[i], 1e-300)) * nb_per_decade)
        if new_level < level:
            idx.append(i)
            level = new_level
    return idx


def _fmt(x):
    return "%+.9e" % x


def _bbob_line(e, df, fopt, dim, rng, old_format, g_per_f=0):
    # the real loggers write all ``dim`` coordinates, two suffice to keep files small
    x = " ".join("%+.4e" % v for v in rng.uniform(-4, 4, min(dim, 2)))
    second = _fmt(df + fopt) if old_format else "%d" % (g_per_f * e)
    return "%d %s %s %s %s %s\n" % (e, second, _fmt(df), _fmt(df + fopt), _fmt(df + fopt), x)


def _rate(rng, fun, dim, speed):
    """return the per-evaluation improvement probability for one trial on ``(fun, dim)``.

    The expected number of evaluations per improvement step is about
    ``c_f * dim**1.1 / speed`` where ``c_f`` grows with ``fun % 8`` from
    1.5 to about 12, such that with the default budget of ``200 * dim``
    the easy functions are always and the hard ones rarely solved.
    """
    c_f = 1.5 * 1.35 ** (fun % 8)
    return min(1.0, speed / (c_f * dim**1.1 * 10 ** rng.uniform(-0.3, 0.3)))


def write_bbob(
    root,
    alg_name="SYNTH-A",
    functions=BBOB_FUNCTIONS,
    dims=BBOB_DIMS,
    instances=BBOB_INSTANCES,
    seed=1,
    budget_multiplier=200,
    speed=1.0,
    suite="bbob",
    old_format=False,
    with_tdat=True,
    comment=None,
    g_per_f=None,
):
    """write a full synthetic single-objective experiment into ``root/alg_name``.

    Return the path of the algorithm folder. `speed` scales the
    convergence speed (larger is faster), such that different "algorithms"
    can be created from the same function. Only the generator seeded with
    `seed` is used.

    ``old_format=True`` writes the pre-2016 layout without ``suite``,
    ``data_format`` and ``logger`` in the header (second column is the
    current f-value instead of constraints evaluations).

    `g_per_f` is the number of constraints evaluations per f-evaluation,
    by default ``1 + (fun - 1) % 6`` for the ``bbob-constrained`` suite
    and zero otherwise.
    """
    rng = np.random.default_rng(seed)
    folder = os.path.join(root, alg_name)
    os.makedirs(folder, exist_ok=True)
    comment = comment if comment is not None else "%% %s: synthetic data, seed=%d" % (alg_name, seed)
    for fun in functions:
        g = g_per_f if g_per_f is not None else (1 + (fun - 1) % 6 if suite == "bbob-constrained" else 0)
        data_dir = "data_f%d" % fun
        os.makedirs(os.path.join(folder, data_dir), exist_ok=True)
        info_lines = []
        for dim in dims:
            budget = int(budget_multiplier * dim)
            base = "bbobexp_f%d_DIM%d" % (fun, dim)
            dat = open(os.path.join(folder, data_dir, base + ".dat"), "w")
            tdat = open(os.path.join(folder, data_dir, base + ".tdat"), "w") if with_tdat else None
            trial_infos = []
            for inst in instances:
                fopt = float(np.round(rng.uniform(-400, 400), 2))
                f0 = 10 ** rng.uniform(0.5, 3)
                rate = _rate(rng, fun, dim, speed)
                evals, fvals = _trajectory(rng, f0, rate, budget)
                header = (
                    "%% f evaluations | g evaluations | best noise-free fitness - Fopt (%.12e) + sum g_i+ |"
                    " measured fitness | best measured fitness or single-digit g-values | x1 | x2...\n" % fopt
                )
                dat.write(header)
                for i in _bbob_target_crossings(evals, fvals):
                    dat.write(_bbob_line(evals[i], fvals[i], fopt, dim, rng, old_format, g))
                if tdat:
                    tdat.write(header)
                    j = 0
                    for e in _log_spaced_evals(evals[-1]):
                        while j + 1 < len(evals) and evals[j + 1] <= e:
                            j += 1
                        tdat.write(_bbob_line(e, fvals[j], fopt, dim, rng, old_format, g))
                trial_infos.append("%d:%d|%.1e" % (inst, evals[-1], fvals[-1] - _PRECISION))
            dat.close()
            if tdat:
                tdat.close()
            if old_format:
                head = "funcId = %d, DIM = %d, Precision = %.3e, algId = '%s'" % (fun, dim, _PRECISION, alg_name)
            else:
                head = (
                    "suite = '%s', funcId = %d, DIM = %d, Precision = %.3e, algId = '%s',"
                    " coco_version = '2.6.0', logger = 'bbob', data_format = 'bbob-new2'" % (suite, fun, dim, _PRECISION, alg_name)
                )
            info_lines += [head, comment, "%s/%s.dat, " % (data_dir, base) + ", ".join(trial_infos)]
        with open(os.path.join(folder, "bbobexp_f%d.info" % fun), "w") as f:
            f.write("\n".join(info_lines) + "\n")
    return folder


def write_biobj(
    root,
    alg_name="SYNTH-BI",
    functions=BIOBJ_FUNCTIONS,
    dims=BIOBJ_DIMS,
    instances=BIOBJ_INSTANCES,
    seed=1,
    budget_multiplier=100,
    speed=1.0,
):
    """write a synthetic ``bbob-biobj`` experiment into ``root/alg_name``.

    The layout follows the 2016 biobj logger: one ``.info`` file per
    dimension in a ``dXX`` folder; each data line references a ``.dat``
    file in a ``folder`` subdirectory. Return the algorithm folder.
    """
    rng = np.random.default_rng(seed)
    folder = os.path.join(root, alg_name)
    for dim in dims:
        dim_dir = os.path.join(folder, "d%02d" % dim)
        group = "all-functions"
        os.makedirs(os.path.join(dim_dir, group), exist_ok=True)
        info = [
            "algorithm = '%s', indicator = 'hyp', folder = '%s', coco_version = '2.6.0'" % (alg_name, group),
            "%% %s: synthetic bi-objective data, seed=%d" % (alg_name, seed),
        ]
        for fun in functions:
            budget = int(budget_multiplier * dim)
            base = "bbob-biobj_f%02d_d%02d_hyp" % (fun, dim)
            dat = open(os.path.join(dim_dir, group, base + ".dat"), "w")
            tdat = open(os.path.join(dim_dir, group, base + ".tdat"), "w")
            trial_infos = []
            for inst in instances:
                # reference values are a property of the problem instance, not of the algorithm
                ref = np.random.default_rng((fun, dim, inst)).uniform(0.5, 1.0)
                hdr = "%%\n%% index = %d, name = synthetic_f%02d_i%02d_d%02d\n%% instance = %d, reference value = %.15e\n" % (
                    fun * 100 + inst, fun, inst, dim, inst, ref)
                f0 = 10 ** rng.uniform(-0.5, 0.5)
                rate = _rate(rng, fun, dim, speed)
                evals, fvals = _trajectory(rng, f0, rate, budget, final=1e-6)
                dat.write(hdr + "% function evaluation | indicator value | target hit\n")
                for i in _bbob_target_crossings(evals, fvals, nb_per_decade=10):
                    target_hit = 10 ** (np.floor(np.log10(max(fvals[i], 1e-300)) * 10) / 10)
                    dat.write("%d\t%.15e\t%.15e\n" % (evals[i], fvals[i], target_hit))
                tdat.write(hdr + "% function evaluation | indicator value\n")
                j = 0
                for e in _log_spaced_evals(evals[-1]):
                    while j + 1 < len(evals) and evals[j + 1] <= e:
                        j += 1
                    tdat.write("%d\t%.15e\n" % (e, fvals[j]))
                trial_infos.append("%d:%d|%.1e" % (inst, evals[-1], fvals[-1]))
            dat.close()
            tdat.close()
            # the file name is relative to `folder` given in the header
            info.append("function = %d, dim = %d, %s.dat, " % (fun, dim, base) + ", ".join(trial_infos))
        with open(os.path.join(dim_dir, "synthetic_d%02d_hyp.info" % dim), "w") as f:
            f.write("\n".join(info) + "\n")
    return folder


# hand-crafted tiny data set with hand-computable results, see `write_tiny_bbob`
TINY_TRIALS = {
    # instance: [(f-evaluations, g-evaluations, Delta f), ...]; the last line is the final evaluation
    1: [(1, 0, 95.0), (10, 0, 0.9), (50, 0, 5e-9)],
    2: [(1, 0, 45.0), (20, 0, 4.5), (100, 0, 0.45)],
    3: [(1, 0, 9.5), (5, 0, 9e-4), (30, 0, 9e-10)],
}


def write_tiny_bbob(root, alg_name="TINY", trials=None, suite="bbob", fun=1, dim=2):
    """write a single ``(fun, dim)`` data set with given `trials` into ``root/alg_name``.

    `trials` maps instance numbers to lists of ``(evals, g_evals, Delta_f)``
    tuples, or is a list of ``(instance, rows)`` pairs (to repeat
    instances). Each tuple is written to both the ``.dat`` and the ``.tdat``
    file such that the expected `DataSet` content can be computed by hand.
    Return the path of the ``.info`` file.
    """
    trials = TINY_TRIALS if trials is None else trials
    trials = list(trials.items()) if isinstance(trials, dict) else list(trials)
    folder = os.path.join(root, alg_name)
    os.makedirs(os.path.join(folder, "data_f%d" % fun), exist_ok=True)
    base = "data_f%d/bbobexp_f%d_DIM%d" % (fun, fun, dim)
    fopt = 10.0
    lines = []
    for inst, rows in trials:
        lines.append("%% f evaluations | g evaluations | best noise-free fitness - Fopt (%.12e) + sum g_i+ | ...\n" % fopt)
        for e, g, df in rows:
            lines.append("%d %d %s %s %s +0.0000e+00\n" % (e, g, _fmt(df), _fmt(df + fopt), _fmt(df + fopt)))
    for ext in (".dat", ".tdat"):
        with open(os.path.join(folder, base + ext), "w") as f:
            f.write("".join(lines))
    infos = ", ".join("%d:%d|%.1e" % (inst, rows[-1][0], rows[-1][2] - _PRECISION) for inst, rows in trials)
    info_file = os.path.join(folder, "bbobexp_f%d.info" % fun)
    with open(info_file, "w") as f:
        f.write(
            "suite = '%s', funcId = %d, DIM = %d, Precision = 1.000e-08, algId = '%s', coco_version = '2.6.0',"
            " logger = 'bbob', data_format = 'bbob-new2'\n" % (suite, fun, dim, alg_name)
        )
        f.write("%% %s: hand-crafted test data\n" % alg_name)
        f.write("%s.dat, %s\n" % (base, infos))
    return info_file
