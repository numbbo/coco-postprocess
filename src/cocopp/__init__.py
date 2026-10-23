"""COmparing Continuous Optimisers (COCO) post-processing package

This package (`cocopp`) generates output figures and tables in html format
and for including into LaTeX-documents.

A comprensive package documentation can be found at https://coco-platform.org

The `cocopp.Interface` class contains the most basic commands and data of
the package, sufficient for most use cases.

A comprensive package documentation can be found at
https://coco-platform.org

`cocopp.main` is the main method of the `cocopp` package.

Further relevant entry points are

>>> import cocopp
>>> sorted(cocopp.Interface.dir())
['archives', 'config', 'genericsettings', 'load', 'main', 'remote_archives']

"""
from __future__ import absolute_import
import sys as _sys

import matplotlib  # just to make sure the following is actually done first
# matplotlib.use('Agg')  # To avoid window popup and use without X forwarding
# del matplotlib

from numpy.random import seed as set_seed

from .cococommands import *  # outdated
from . import config
from . import archiving
from . import rungeneric
from . import genericsettings
# from . import reduce_size  # leads to a warning in the ``python -m cocopp.reduce_size`` usecase

from ._version import __version__

__all__ = []

archives = archiving.official_archives  # just an alias
if archives is not None:
    data_archive = archives.all  # another alias, only for historical reasons
    archives.link_as_attributes_in(
        _sys.modules["cocopp"],  # more individual aliases
        except_for=["all", "test"],
    )

# data_archive = 'use `archives.all` instead'
# bbob = 'use `archives.bbob` instead'
# bbob_noisy = 'use `archives.bbob_noisy` instead'
# bbob_biobj = 'use `archives.bbob_biobj` instead'

def remote_archives():
    """return a list of URLs containing COCO archives.

    Elements of this list can be used directly with `cocopp.archiving.get`, see
    https://coco-platform.org/howto-publish.html#using-an-archive-by-url
    """
    return archiving.RemoteListOfArchives()

def main(argv=None):
    r"""Main routine for post-processing data from COCO.

    A comprensive package documentation can be found at
    https://coco-platform.org

    The package can be used either directly from a system shell, like::

        python -m cocopp [data_folder [more_data_folders]]

    and::

        python -c "import cocopp; cocopp.main('data_folder [more_data_folders]')"

    or, as recommended, from an IPython/Jupyter notebook shell, like

    >>> import cocopp
    >>> cocopp.main('exdata/my_output another_folder yet_another_or_not')  # doctest:+SKIP

    which allows to better fine control settings and further investigate the
    returned data list, see also below.

    Here ``data_folder`` is either a folder name containing experiment data,
    for example data generated with the `cocoex` module, usually into the
    `exdata` folder. Each folder should contain data of a single full experiment
    with a single algorithm. Within this folder, the data can be distributed
    over any number and depths of subfolders. `.info` files are the entry points
    for reading data.
     
    Or, ``data_folder`` is a name from the known data archive, see e.g.
    ``cocopp.bbob`` and ``cocopp.archives``, or a uniquely matching substring of
    such a name, or a matching substring with added "!" in which case the first
    match is taken, or a matching substring with added "*" in which case all
    matches are taken, or a regular expression containing a '*' before the last
    character, in which case, for example, "bbob/.*7.*cma"  matches
    "bbob/2017/DTS-CMA-ES-Pitra.tgz" (among others). For example::

        $ python -m cocopp 'bbob/.*/direct! ' 'bbob/.*/mcs! ' 'bbob/.*/fminunc! '

    processes three known algorithms run on the `bbob` testbed.

    Results can be explored from the ``ppdata/index.html`` file, unless a
    different output folder was specified with the ``-o`` option. By default, a
    browser opens to navigate the results.

    CAVEAT: when running `main` or `load` repeatedly on data sets *from
    different suites*, the routine may bail out. Running
    ``cocopp.config.config()`` may solve the problem, however sometimes a
    restart of Python is necessary.

    Options
    -------
    In both usecases the following options can be passed to `main`.

    ``-h, --help``
        displays this message.

    ``-v, --verbose``
        verbose mode, prints out operations.

    ``-o, --output-dir=OUTPUTDIR``
        changes the default output directory (``ppdata``) to
        ``OUTPUTDIR``.

    ``--input-path=INPUTPATH``
        all folder/file arguments are prepended with the given value
        which must be a valid path.

    ``--budget-based`` or ``--runlength-based``
        Use budget-based target values for budgets between D/2 and 50xD
        evaluations (see ``genericsettings.target_runlength*``) and based on a
        reference algorithm, by default ``best2009-bbob, best2009bbob-noisy,
        best2016-bbob-biobj, best2019-bbob-largescale``.

    ``--expensive``
        Use budget-based targets and adapt xlim to data with low budgets.

    ``--parameter-sweep``
        if given, parse the algorithm name for a float and use the
        value to determine the color order in a colormap.

    ``--parameter-sweep-colormaps=colormaps``
        ``colormaps`` can, for example, be ``plasma.0.9,viridis``
        indicating (here two) map names separated by commata and
        optionally the range for each map.

    ``--in-a-hurry``
        overwriting `genericsettings.in_a_hurry`, takes values between 0 and
        1000 (default) for faster processing that does not write eps files and
        uses a small number of bootstrap samples

    ``--include-single``
        calls the postprocessing and in particular
        `cocopp.rungeneric1.main` on each of the
        single input arguments separately.

    ``--conv``
        prepares also convergence plots with median function values over time when single processing is active

    ``--no-rld-single-fcts``
        do not generate runlength distribution figures for each
        single function.

    ``--no-svg``
        do not generate the svg figures which are used in html files

    ``--include-fonts``
        generated pdfs will have the fonts included (important for ACM style
        LaTeX submissions)

    ``--tab-only``
        Only generates tables which is fast.
    
    ``--fig-only``, ``--los-only``, ``--rld-only``, ``--sca-only``
        Only show some figures or runtime distributions.

    ``--no-interactive``
        Do not open browser at the end.

    Deprecated or inactive options are "noisy", "noise-free", "pickle",
    "crafting-effort=", "settings".


    Post-processing two algorithms in verbose mode::

        $ python -m cocopp -v AMALGAM BIPOP-CMA-ES

    From the python interpreter::

        >> import cocopp
        >> cocopp.main('-o outputfolder folder1 folder2')

    This will execute the post-processing on the data found in
    ``folder1`` and ``folder2`` and return the respective
    `DataSetList`. The ``-o`` option changes the output folder from the
    default ``ppdata`` to ``outputfolder``. The arguments can
    also be presented as a list of strings.


    Usecases from a Python shell or notebook
    ----------------------------------------
    To fine-control the behavior of the module, it is useful to work from an
    (I)Python shell or notebook. For example, to display algorithms in the
    background, the ``genericsettings.background`` variable can be set:

    >>> cocopp.genericsettings.background = {None:  # doctest:+SKIP
    ...              cocopp.bbob.get_all("2009/")}

    where `None` invokes the default color (gray) and line style (solid)
    ``genericsettings.background_default_style``.

    Now we could compare our own data with the first ``'bfgs'``-matching
    archived algorithm

    >>> cocopp.main("exdata/my_output " + cocopp.bbob.get("bfgs!"))  # doctest:+SKIP

    displaying all archived results from 2009 in the background. ``cocopp.bbob``
    is a `cocopp.archiving.COCODataArchive` class.

    With the background algorithms, this may take 5-15 minutes to complete,
    because more than 30 algorithm datasets are processed.

    **Comparative data** from over 390 full experiments are archived online and
    can be listed, filtered, and retrieved from `cocopp.archives` (of type
    `OfficialArchives`) and processed alone or together with local data.

    >>> cocopp.archives.bbob('bfgs')  # doctest:+ELLIPSIS,+SKIP,
    ['2009/BFGS_...

    lists all data sets containing ``'bfgs'`` in their name. The search can
    also use regular expressions where '.' matches any single
    character and '*' means one or more repetitions:

    >>> cocopp.archives.bbob('.*bfgs')  # doctest:+ELLIPSIS,+SKIP,
    ['2009/BFGS_...

    gives the same data sets as above and

    >>> cocopp.archives.all('bbob/.*bfgs')  # doctest:+ELLIPSIS,+SKIP,
    ['bbob/2009/BFGS_...

    gives also the same data sets, however extracted from the archive of all
    suites, which is the search domain when using `cocopp.main`.

    When calling the `cocopp.main` routine, a single trailing '!' or '*'
    have the special meaning of take-the-first-only and take-all, respectively.
    Hence, the first entry of the above selecting list can be postprocessed with

    >>> cocopp.main('bfgs!')  # doctest:+SKIP

    All `'bfgs'` matches from the `'bbob'` suite can be processed like

    >>> cocopp.main('bbob/.*bfgs')  # doctest:+SKIP

    (``cocopp.main('bfgs*')`` raises an error as data from incompatible suites
    cannot be processed together.)

    The postprocessing result of

    >>> cocopp.main('bbob/2009/*')  # doctest:+SKIP

    can be browsed at http://numbbo.github.io/ppdata-archive/bbob/2009 (or 2009-all).


    Output
    ------

    The output figures and tables written by default to the output folder
    ``ppdata`` can be browsed from `index.html` and are used in the provided
    LaTeX templates:

    * ``*article.tex`` and ``*1*.tex``
      for results with a **single** algorithm
    * ``*cmp.tex`` and ``*2*.tex``
      for showing the comparison of **2** algorithms
    * ``*many.tex`` and ``*3*.tex``
      for showing the comparison of **more than 2** algorithms.

    The templates with ``noisy`` mentioned in the filename have to be used
    for the noisy testbed.

    These latex templates need to be copied in the current working directory
    and possibly edited so that the LaTeX commands ``\bbobdatapath`` and
    ``\algfolder`` point to the correct output folders of the post-processing.
    Compiling the template file with LaTeX should then produce a document.


    Details
    -------
    Exceptions raised:

    *Usage* -- Gives back a usage message.

    This routine will

    * call sub-routine :py:func:`cocopp.rungeneric1.main` for one
      input argument (see also --include-single option); the input
      argument will be used as output sub-folder relative to the main
      output folder,
    * call sub-routine :py:func:`cocopp.rungenericmany.main`
      (2 or more input arguments) for the input arguments altogether.

"""
    return rungeneric.main(argv=None)

class Interface:
    """collection of the most user-relevant modules, methods and data.

    `archives`: online data archives of type `OfficialArchives`

    `archiving`: methods to archive data and retrieve archived data put online

    `remote_archives`: a function returning a list of URLs of known remote COCO archives

    `config`: dynamic configuration tool (advanced)

    `genericsettings`: basic settings

    `load`: loading data from disk

    `main`: post-processing data from disk
    """

    @classmethod
    def dir(cls):
        """return `dict` of non-private class attribute names->values"""
        return dict(it for it in cls.__dict__.items() if not it[0].startswith("_") and not it[0] == "dir")

    archives = archives
    config = config
    genericsettings = genericsettings
    load = load
    main = main
    remote_archives = remote_archives

# clean up namespace
del absolute_import
# del bestalg, captions, comp2, compall, htmldesc, pickle, ppconverrorbars
# del ppfig, ppfigdim, ppfigparam, pplogloss, pprldistr, pproc, pptable
# del pptex, readalign, rungeneric1, rungenericmany, toolsdivers, toolsstats

# cococommands, config, data_archive, dataformatsettings, findfiles,
# genericsettings, info, load, main, rungeneric, set_seed, systeminfo, testbedsettings,
