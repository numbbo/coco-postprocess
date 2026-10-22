#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""COmparing Continuous Optimisers (COCO) post-processing package

This package (`cocopp`) generates output figures and tables in html format
and for including into LaTeX-documents.

The `cocopp.Interface` class contains the most basic commands and data of
the package, sufficient for most use cases.

A comprensive package documentation can be found at
https://coco-platform.org

>>> import cocopp
>>> sorted(cocopp.Interface.dir())
['archives', 'config', 'genericsettings', 'load', 'main', 'remote_archives']
>>> all(hasattr(cocopp, name) for name in cocopp.Interface.dir())
True

The main method of the `cocopp` package is `main` (currently aliased to
`cocopp.rungeneric.main`). While the `main` method allows basic use of the
post-processing through a command-line interface, the recommended usage
is from an IPython/Jupyter notebook shell:

>>> import cocopp
>>> cocopp.main('exdata/my_output another_folder yet_another_or_not')  # doctest:+SKIP

postprocesses data from one or several folders, for example data generated with
the `cocoex` module. Each folder should contain data of a full experiment with a
single algorithm. Within this folder, the data can be distributed over any
number and depth of subfolders.

Results can be explored from the ``ppdata/index.html`` file, unless a
a different output folder is specified with the ``-o`` option.

**Comparative data** from over 200 full experiments are archived online and
can be listed, filtered, and retrieved from `cocopp.archives` (of type
`OfficialArchives`) and processed alone or together with local data.

For example

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

To display algorithms in the background, the ``genericsettings.background``
variable needs to be set:

>>> cocopp.genericsettings.background = {None: cocopp.archives.bbob.get_all('bfgs')}  # doctest:+SKIP

where `None` invokes the default color (gray) and line style (solid)
``genericsettings.background_default_style``.

Now we could compare our own data with the first ``'bfgs'``-matching
archived algorithm where all other archived BFGS data are shown in the
background with

>>> cocopp.main('exdata/my_output bfgs!')  # doctest:+SKIP

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

    The following is somewhat outdated.

    Synopsis from a system shell::

        python -m cocopp [data_folder [more_data_folders]]

    or::

        python -c "import cocopp; cocopp.main('data_folder [more_data_folders]')"

    For this call to work, the path to this package must be in python
    search path, that is,

    * it can be in the current working directory, or
    * the path to the package was appended to the Python path, or
    * the package was installed (which essentially copies the package
      to a location which is in the path)

    ``data_folder`` may be a name from the known data archive, see e.g.
    ``cocopp.bbob``, or a uniquely matching substring of such a name, or a
    matching substring with added "!" in which case the first match is taken, or
    a matching substring with added "*" in which case all matches are taken, or
    a regular expression containing a '*' before the last character, in which
    case, for example, "bbob/.*7.*cma"  matches "bbob/2017/DTS-CMA-ES-Pitra.tgz"
    (among others).

    Usecase from a Python shell
    ---------------------------
    To fine-control the behavior of the module, it is highly recommended
    to work from an (I)Python shell or notebook. For example::

        import cocopp
        cocopp.genericsettings.background = {None: cocopp.bbob.get_all("2009/")}
        cocopp.main("data_folder " + cocopp.data_archive.get("2009/BFGS_ros_noiseless"))

    compares an experiment given in ``"data_folder"`` with BFGS and displays
    all archived results from 2009 in the background. ``cocopp.bbob`` is a
    `cocopp.archiving.COCODataArchive` class.

    With the background algorithms, this may take 5-15 minutes to complete,
    because more than 30 algorithm datasets are processed.

    Output
    ------

    The output figures and tables written by default to the output folder
    ``ppdata`` are used in the provided LaTeX templates:

    * ``*article.tex`` and ``*1*.tex``
      for results with a **single** algorithm
    * ``*cmp.tex`` and ``*2*.tex``
      for showing the comparison of **2** algorithms
    * ``*many.tex`` and ``*3*.tex``
      for showing the comparison of **more than 2** algorithms.

    The templates with ``noisy`` mentioned in the filename have to be used
    for the noisy testbed, the others for the noise-less one.

    These latex templates need to be copied in the current working directory
    and possibly edited so that the LaTeX commands ``\bbobdatapath`` and
    ``\algfolder`` point to the correct output folders of the post-processing.
    Compiling the template file with LaTeX should then produce a document.

    Keyword arguments:

    *argv* -- list of strings containing options and arguments. If not
       provided, sys.argv is accessed.

    *argv* must list folders containing COCO data files. Each of these
    folders should correspond to the data of ONE algorithm.

    Furthermore, argv can begin with facultative option flags:

    ``-h, --help``
        displays this message.

    ``-v, --verbose``
        verbose mode, prints out operations.

    ``-o, --output-dir=OUTPUTDIR``
        changes the default output directory (``ppdata``) to
        ``OUTPUTDIR``.

    ``--include-single``
        calls the postprocessing and in particular
        :py:func:`cocopp.rungeneric1.main` on each of the
        single input arguments separately.

    ``--no-rld-single-fcts``
        do not generate runlength distribution figures for each
        single function.

    ``--input-path=INPUTPATH``
        all folder/file arguments are prepended with the given value
        which must be a valid path.

    ``--parameter-sweep``
        if given, parse the algorithm name for a float and use the
        value to determine the color order in a colormap.

    ``--parameter-sweep-colormaps=colormaps``
        ``colormaps`` can, for example, be ``plasma.0.9,viridis``
        indicating (here two) map names separated by commata and
        optionally the range for each map.

    ``--in-a-hurry``
        takes values between 0 (default) and 1000, fast processing that
        does not write eps files and uses a small number of bootstrap samples

    ``--no-svg``
        do not generate the svg figures which are used in html files

    ``--conv``
        prepares also convergence plots with median function values over time

    ``--include-fonts``
        generated pdfs will have the fonts included (important for ACM style
        LaTeX submissions)

    Exceptions raised:

    *Usage* -- Gives back a usage message.

    Examples:

    Printing out this help message::

        $ python -m cocopp.rungeneric -h

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

    Details: this routine will

    * call sub-routine :py:func:`cocopp.rungeneric1.main` for one
      input argument (see also --include-single option); the input
      argument will be used as output sub-folder relative to the main
      output folder,
    * call sub-routine :py:func:`cocopp.rungenericmany.main`
      (2 or more input arguments) for the input arguments altogether.
    * alternatively call sub-routine :py:func:`cocopp.__main__.main` if option
      flag --test is used. In this case it will run through the
      post-processing tests.

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
