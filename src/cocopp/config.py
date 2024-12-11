#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""This module is an attempt for a global configuration file for various
parameters.

The import of this module changes default settings (attributes)
of other modules. This works, because each module has only one instance.

Before this module is imported somewhere, modules use their default settings.

This file could be dynamically modified and reloaded.

See also `genericsettings` which is a central place to define settings
used by other modules, but does not modify settings of other modules.

"""

import importlib
import collections
import warnings
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from . import ppfigdim
from . import genericsettings as settings, pproc, pprldistr
from . import testbedsettings as tbs
from . import dataformatsettings
from .comp2 import ppfig2, ppscatter
from .compall import pprldmany
from . import __path__  # import path for default genericsettings

if settings.test:
    np.seterr(all='raise')
np.seterr(under='ignore')  # ignore underflow


# genericsettings needs a pristine copy of itself to compare
# against so that it can output the changed settings.
gs_spec = importlib.util.find_spec('cocopp.genericsettings')
gs = importlib.util.module_from_spec(gs_spec)
gs_spec.loader.exec_module(gs)
settings.default_settings = gs


def config_target_values_setting(is_expensive, is_runlength_based):
    """manage target values setting in "expensive" optimization scenario.
    """
    if is_expensive:
        settings.maxevals_fix_display = settings.xlimit_expensive
    settings.runlength_based_targets = is_runlength_based or is_expensive

def _str_to_colormap(s, len_):
    """return a color iterator from a string like ``'plasma.1.8'``"""
    cvals = s.split('.')
    c0 = float('.' + cvals[1]) if len(cvals) > 1 and len(cvals[1]) > 1 else 0
    c1 = float('.' + cvals[2]) if len(cvals) > 2 else 1
    return iter(mpl.colors.to_hex(c) for c in
                    plt.get_cmap(cvals[0])(np.linspace(c0, c1, len_)))

def _index_after_parameter(name, return_first_digit_index=False):
    """return the first index after a sequence indicating a positive float.

    In particular, `1.23` or `1.2e-3` are correctly identified as a float.

    If `return_first_digit_index`, the index of the first digit is returned
    instead of the first index after the float.
    """
    found = False
    exponent = False
    accept_minus = False  # allow to read a minus in the exponent
    for i in range(len(name)):
        if '0' <= name[i] <= '9' or (
                name[i] == '.' and not exponent) or (
                accept_minus and name[i] == '-'):
            found = True
            if return_first_digit_index:
                return i
            accept_minus = False  # accept only once directly after 'e'
            continue
        elif found and not exponent and name[i].lower() == 'e':
            exponent = True
            accept_minus = True
            continue
        elif found:
            return i if name[i-1].lower() != 'e' else i - 1
    return -1

def map_indices_to_line_styles(names):
    """helper function for `config_line_styles`.

    Map each index of names to the index of the first appearence of the
    name, where equality of names is determined starting from after a float
    number (which represents a parameter value) using
    `_index_after_parameter`.
    """
    # names without preceeding float number
    nn = [name[_index_after_parameter(name):] for name in names]
    res = {k: nn.index(v) for k, v in enumerate(nn)}  # index gives the first match
    return res

def sorted_line_styles(styles, names, indices):
    """use the sorting of names up until and including a float to rearrange `styles`.

    This assumes that the ``names[indices]`` correspond to
    ``styles[indices]`` and that ``styles[indices]`` (colormap) are in
    increasing order on input. On output, ``sorted_styles`` are in
    increasing order w.r.t. the sorting of ``names[indices]``.
    """
    def sort_key(i):
        i0, i1 = _index_after_parameter(names[i], True), _index_after_parameter(names[i])
        return names[i][:i0], float(names[i][i0:i1])

    sorted_indices = sorted(indices, key=sort_key)
    # print(names, indices, sorted_indices)  # this looks correct
    sorted_styles = styles[:]
    # the line style of sorted_indices[k] becomes the style of indices[k]
    for i, j in zip(sorted_indices, indices):
        sorted_styles[i] = styles[j]
    return sorted_styles

def config_line_styles():
    '''configure `genericsettings.line_styles` for a parameter sweet

    if ``parameter_sweep`` is given on input. The colormap and range can be
    changed via the ``--parameter_sweep_colormaps=`` value. The default
    value is ``'plasma.0.9'``, viable alternatives are ``'viridis'`` or
    ``'gnuplot2.0.85'`` or a comma separated joined sequence of any of
    these, same color sweeps are 'Greens_r..7', 'Greys_r..7', 'Reds_r..7'.

    The sorting of the input arguments up to and including a float value in
    the name determines the positioning in the color map.

    Minor: The ``line_style_mapping`` attribute of `genericsettings` can be
    used to chose the marker and line style like ``{input_position:
    position_in_original_line_styles}``. When ``input_position`` is not
    present, the usual marker line style combination is used matching
    ``input_position``.

    TODO: we may want to keep the original symbol colors?
    '''
    if not settings.parameter_sweep:
        return
    if not settings.parameter_sweep_colormaps:
          cvals = settings.sequential_colormaps
    else:
        # check whether s gives a color map
        s = settings.parameter_sweep_colormaps
        if s.startswith(tuple(mpl.colormaps())):
            cvals = s.split(',')
        else:
            warnings.warn("{0} doesn't conform with any ``matplotlib.colormaps()={1}``"
                        "Hence we use the default {2}"
                        .format(s, plt.colormaps(), settings.sequential_colormaps))
            cvals = settings.sequential_colormaps
    # map algorithm argument index to first algorithm appearence index
    mapping = settings.line_style_mapping or map_indices_to_line_styles(
                        settings._current_args)
    counts = collections.Counter(mapping.values())  # count number of appearences
    if settings.verbose >= 0:
        print("config_line_styles: found {0} distinct algorithm(s) in indices {1} of {2} arguments"
              .format(len(counts), sorted(counts), len(mapping)))
        # print(mapping, counts)
        if settings.line_styles != settings._default_line_styles:
            print('config_line_styles:   line styles are (already) different from default')
            # return
    color_maps = {}
    for j, i in enumerate(sorted(counts)):
        try:
            color_maps[i] = _str_to_colormap(cvals[j % len(cvals)], counts[i])
        except ValueError as e:
            warnings.warn("exception {0} occured while generating color maps".format(e))
    _previous_line_styles = [d.copy() for d in settings.line_styles]
    # modify color in settings.line_styles and set same line and marker style
    # which should be idempotent when applied to line_styles repeatedly
    for i, j in sorted(mapping.items()):  # sorted w.r.t. input argument order
        # _current_args names and indices i must align?
        s = settings.line_styles[i]
        # s['markeredgecolor'] = s['color']  # doesn't work
        s['color'] = next(color_maps[j])  # CAVEAT: here the order of i matters!?
        for key in s.keys():
            if key != 'color':
                s[key] = settings.line_styles[j][key]
    if not settings.parameter_sweep_sort:
        return
    # sort styles for each algorithm
    for alg in counts:
        indices = [k for k in mapping if mapping[k] == alg]
        settings.line_styles = sorted_line_styles(
                settings.line_styles, settings._current_args, indices)
    if settings.verbose >= 0 and settings.line_styles == _previous_line_styles:
        print("config_line_styles:   didn't change lines styles")

def config(suite_name=None):
    """called from a high level, e.g. rungeneric, to configure the lower level
    modules via modifying parameter settings.
    """
    config_line_styles()
    config_target_values_setting(settings.isExpensive, settings.runlength_based_targets)
    if suite_name:
        tbs.load_current_testbed(suite_name, pproc.TargetValues)

    settings.simulated_runlength_bootstrap_sample_size = 10 + 990 / (1 + 10 * max(0, settings.in_a_hurry))

    if tbs.current_testbed and tbs.current_testbed.name not in tbs.suite_to_testbed:
        if ((settings.isExpensive in (True, 1) or
                settings.runlength_based_targets in (True, 1)) and
                tbs.current_testbed.reference_algorithm_filename == ''):
            warnings.warn('Expensive setting not yet supported with ' +
                          tbs.current_testbed.name +
                          ' testbed; using non-expensive setting instead.')
            settings.isExpensive = False
            settings.runlength_based_targets = False

    # pprldist.plotRLDistr2 needs to be revised regarding run_length based targets
    if settings.runlength_based_targets in (True, 1) and not tbs.current_testbed:
        # this message may be removed at some point
        print('  runlength-based targets are on, but there is no testbed available (yet)')
    if settings.runlength_based_targets in (True, 1) and tbs.current_testbed:
        
        print('Reference algorithm based target values, using ' +
              tbs.current_testbed.reference_algorithm_filename +
              ':\n  now for each function, the target '
              'values differ, but the "level of difficulty" '
              'is "the same".')

        reference_data = 'testbedsettings'
        # pprldmany:
        if 1 < 3:  # not yet functional, captions need to be adjusted and the bug reported by Ilya sorted out
            # pprldmany.caption = ... captions are still hard coded in LaTeX
            pprldmany.x_limit = settings.maxevals_fix_display  # always fixed

        if tbs.current_testbed:

            testbed = tbs.current_testbed

            testbed.scenario = tbs.scenario_rlbased
            # settings (to be used in rungenericmany while calling pprldistr.comp(...)):
            testbed.rldValsOfInterest = pproc.RunlengthBasedTargetValues(
                                        settings.target_runlengths_in_single_rldistr,
                                        reference_data=reference_data,
                                        force_different_targets_factor=10**-0.2)

            testbed.ppfigdim_target_values = pproc.RunlengthBasedTargetValues(
                                             settings.target_runlengths_in_scaling_figs,
                                             reference_data=reference_data,
                                             force_different_targets_factor=10**-0.2)

            testbed.pprldistr_target_values = pproc.RunlengthBasedTargetValues(
                                              settings.target_runlengths_in_single_rldistr,
                                              reference_data=reference_data,
                                              force_different_targets_factor=10**-0.2)

            testbed.pprldmany_target_values = pproc.RunlengthBasedTargetValues(
                                              settings.target_runlengths_pprldmany,
                                              reference_data=reference_data,
                                              smallest_target=1e-8 * 10**0.000,
                                              force_different_targets_factor=1,
                                              unique_target_values=True)

            testbed.ppscatter_target_values = pproc.RunlengthBasedTargetValues(
                                              settings.target_runlengths_ppscatter)
            # pptable:
            testbed.pptable_targetsOfInterest = pproc.RunlengthBasedTargetValues(
                                                testbed.pptable_target_runlengths,
                                                reference_data=reference_data,
                                                force_different_targets_factor=10**-0.2)
            # pptables:
            testbed.pptablemany_targetsOfInterest = pproc.RunlengthBasedTargetValues(
                                                 testbed.pptables_target_runlengths,
                                                 reference_data=reference_data,
                                                 force_different_targets_factor=10**-0.2)
            # ppfigs
            testbed.ppfigs_ftarget = pproc.RunlengthBasedTargetValues([settings.target_runlength],
                                                                      reference_data=reference_data)

        # pprldistr:
        pprldistr.runlen_xlimits_max = \
            settings.maxevals_fix_display / 2 if settings.maxevals_fix_display else None  # can be None
        pprldistr.runlen_xlimits_min = 10**-0.3  # can be None
        # ppfigdim:
        ppfigdim.xlim_max = settings.maxevals_fix_display
        if ppfigdim.xlim_max:
            ppfigdim.styles = [  # sort of rainbow style, most difficult (red) first
                      {'color': 'y', 'marker': '^', 'markeredgecolor': 'k', 'markeredgewidth': 2, 'linewidth': 4},
                      {'color': 'g', 'marker': '.', 'linewidth': 4},
                      {'color': 'r', 'marker': 'o', 'markeredgecolor': 'k', 'markeredgewidth': 2, 'linewidth': 4},
                      {'color': 'm', 'marker': '.', 'linewidth': 4},
                      {'color': 'c', 'marker': 'v', 'markeredgecolor': 'k', 'markeredgewidth': 2, 'linewidth': 4},
                      {'color': 'b', 'marker': '.', 'linewidth': 4},
                      {'color': 'k', 'marker': 'o', 'markeredgecolor': 'k', 'markeredgewidth': 2, 'linewidth': 4},
                    ]

        ppscatter.markersize = 16

    else:
        # here the default values of the modules apply
        pprldmany.x_limit = settings.xlimit_pprldmany  # ...should depend on noisy/noiseless
    if 11 < 3:  # for testing purpose
        if tbs.current_testbed:
            # TODO: this case needs to be tested yet: the current problem is that no noisy data are in this folder
            tbs.current_testbed.pprldmany_target_values = \
                pproc.RunlengthBasedTargetValues(10**np.arange(1, 4, 0.2), 'RANDOMSEARCH')

    pprldmany.fontsize = 20.0  # should depend on the number of data lines down to 10.0 ?

    ppscatter.markersize = 14

    ppfig2.linewidth = 4
 

def main():
    config()
