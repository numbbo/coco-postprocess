"""Reduce the data size of COCO experiment folder(s) from the default logger.

Data are copied into a new folder and then reduced in place.

Usage on a system shell::

     python -m cocopp.reduce_size folder_name

`folder_name` may be a single experiment folder or may contain several full
experiment folders. In either case, the reduction is applied to all
admissible single data files found anywhere under `folder_name`.

Further arguments denote the functions applied to the files, by default
``reduce_dat reduce_tdat remove_x``.

Usage in an IPython/Python shell::

    import cocopp
    cocopp.reduce_size.main(folder_name)

A second argument may contain a `tuple` or `list` of the functions names
applied to the files, by default ``("reduce_dat", "reduce_tdat",
"remove_x")``.

Under a ``*nix`` shell, the result can then be check with ``du -sh *``.

Details: this script removes lines in the data files which are not needed
with `cocopp.main`. Comment lines starting with ``#`` or ``%`` are
unchanged. The first and third columns are considered as evaluations
(costs) and f-values (quality indicator to be minimized) respectively.
"""

import math
import os
import shutil
import sys
import time

number_of_ftargets = 20
final_ftarget = 1e-8
allowed_x_names = ["DIM2.", "DIM3.", "DIM5."]


def main(folder_name, apply=("reduce_dat", "reduce_tdat", "remove_x")):
    """`folder_name` contains output of a single COCO experiment, usually a folder in ``exdata``"""
    if folder_name.endswith("/") or folder_name[-1] == os.path.sep:
        folder_name = folder_name[:-1]
    new_name = "{0}-{1}".format(folder_name, time.strftime("%m%d%Hh%M%S"))
    shutil.copytree(folder_name, new_name)  # raise `FileExistsError` when new_name exists
    for folder, dirs, files in os.walk(new_name):
        # these dirs and files are in the current folder
        for filename in files:
            for transform in [globals()[n] for n in apply]:
                if _condition(filename, transform):  # transformation applies to this file type?
                    _rewrite(os.path.join(folder, filename), transform)


def is_comment(s):
    return s.lstrip().startswith(("%", "#"))


def is_empty(s):
    return len(s.strip()) == 0


def _condition(filename, transform):
    """should `transform` be applied to `filename`?

    Call the condition function for this `transform` on `filename`.
    """
    return {
        remove_x: remove_x_condition,
        reduce_tdat: reduce_tdat_condition,
        reduce_dat: reduce_dat_condition,
    }[transform](filename)


class TargetHit:
    """mininal class to indicate target hits based on file lines.

    Lines are split and assumed to have evals and the relevant f-value as
    first and third entry respectively. If evals (first column) decreased,
    the target is reset.
    """

    def __init__(self, number_of_targets, final_target):
        """`number_of_targets` per decade (factors of ten)"""
        self.number_of_targets = number_of_ftargets
        self.final_target = final_ftarget
        self._ieval = 0  # index where to read evals
        self._ifval = 2  # index where to read fval
        self.reset()

    def reset(self):
        self.current_target = math.inf
        self.current_eval = -1

    def __call__(self, line):
        """return `True` if the data line should be kept.

        Keep if either evals decreased (presumably due to a new run) or a
        new target was hit.
        """
        s = line.split()
        current_eval = int(s[self._ieval])
        if current_eval < self.current_eval:
            self.reset()
            return True
        self.current_eval = current_eval
        new_f = float(s[self._ifval])
        return self.update_target(new_f)

    def update_target(self, new_f):
        """return whether target was hit"""
        if new_f > self.current_target:
            return False
        # new_f hit the current target
        if self.current_target == 0:
            return False  # don't record more negative values
        if new_f < self.final_target or new_f <= 0:
            self.current_target = 0
            return True  # last entry to keep
        logf = math.log10(new_f)
        assert math.isfinite(logf)
        t = math.ceil(logf)  # compute new target from scratch
        while logf <= t:
            t -= 1.0 / self.number_of_targets
        self.current_target = 10**t
        assert new_f > self.current_target - 1e-16
        return True


def reduce_dat_condition(filename):
    return filename.endswith(".dat")


def reduce_dat(lines):
    """return a new list with fewer lines, remove everything after a negative target was hit too"""
    # % f evaluations | g evaluations | best noise-free fitness - Fopt (7.948000000000e+01) + sum g_i+ | measured fitness | best measured fitness or single-digit g-values | x1 | x2...
    new_lines = []
    keep_line = True  # whether we can overwrite the current last line
    target_hit = TargetHit(number_of_ftargets, final_ftarget)
    for line in lines:
        if is_empty(line) or is_comment(line):
            target_hit.reset()
            new_lines.append(line)  # overwrite only data lines with data lines
            keep_line = True
            continue
        if keep_line:  # keep previous line
            new_lines.append(line)
        else:  # overwrite line
            new_lines[-1] = line
        keep_line = target_hit(line)  # whether we can overwrite the current last line
    return new_lines


def reduce_tdat_condition(filename):
    return filename.endswith(".tdat")


def reduce_tdat(lines):
    """return a new list with first and last data lines only.

    Evaluations are assumed to be in the first column.
    """
    # % f evaluations | g evaluations | best noise-free fitness - Fopt (7.948000000000e+01) + sum g_i+ | measured fitness | best measured fitness or single-digit g-values | x1 | x2...
    _ieval = 0
    last_eval = -1
    new_lines = []
    for line in lines:
        current_eval = line.split(maxsplit=1)[_ieval]
        if not current_eval or is_comment(line):
            new_lines.append(line)
            last_eval = -1  # reset and keep this and next line
            continue
        current_eval = int(current_eval)
        if current_eval >= last_eval > 1:  # overwrite previous line
            new_lines[-1] = line
        else:
            new_lines.append(line)
        last_eval += 1  # feels like it could be simplified, but how?
        if last_eval:
            last_eval = current_eval
    return new_lines


def remove_x_condition(filename):
    """define on which files to apply `remove_x`"""
    if not filename.endswith((".dat", ".mdat", ".tdat")):
        return False
    return not any(s in filename for s in allowed_x_names)


def remove_x(lines):
    """change lines in place, keep only first 5 entries of data lines"""
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        lines[i] = " ".join(line.split()[:5]) + "\n"
    return lines


def _rewrite(file_path, transform):
    """read in `file_path`, apply `transform` to its lines, and rewrite it"""
    with open(file_path, "r") as f:
        lines = f.readlines()
    lines = transform(lines)
    with open(file_path, "w") as f:
        f.writelines(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("cocopp.reduce_size needs a folder name as argument or ``-h`` or ``--help``")
    elif len(sys.argv) == 2:
        if sys.argv[1] in ("-h", "--help"):
            print("\n", __doc__)
        else:
            main(sys.argv[1])
    else:
        main(sys.argv[1], apply=sys.argv[2:])
