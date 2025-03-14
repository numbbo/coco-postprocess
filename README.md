<h1 align="center">
    <table border="0">
  <td>
      <img src="https://raw.githubusercontent.com/numbbo/coco/0ea5f5784c5fa0543261d9c104b490d2d95566f9/logo/coco-pp-300.webp">          
  </td>
  <td>
      COmparing Continuous Optimisers (COCO) PostProcess
</td>
</table>
</h1>

[![version](https://img.shields.io/pypi/v/cocopp?color=blue)](https://pypi.org/project/cocopp)
[![license](https://img.shields.io/pypi/l/cocopp)](https://pypi.org/project/cocopp)
[![download](https://img.shields.io/pypi/dm/cocopp.svg?label=PyPI%20downloads)][pypi]
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.2594848.svg)][codereference]
[![paper](https://img.shields.io/badge/DOI-10.1080%2F10556788.2020.1808977-blue)][paper]

The [`cocopp`](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.html) Python package
implements the postprocess part of [COCO: A Platform for Comparing Continuous Optimizers in a Black-Box Setting][paper], comparing not only continuous optimisers.
The package uses data generated with the [COCO framework](https://coco-platform.org) and produces output figures and tables in `html` format and for inclusion into `LaTeX` documents.

## Documentation

The main documentation pages for the `coco-postprocess` package `cocopp` can be found at

- [getting-started](https://numbbo.it/getting-started#postprocess)
- [API documentation](https://numbbo.github.io/coco-doc/apidocs/cocopp)
- [Issue tracker and bug reports](https://github.com/numbbo/coco-postprocess/issues)
- [source code page](https://github.com/numbbo/coco-postprocess) on GitHub
- [COCO home page](https://coco-platform.org)

Below are the installation instruction and some usage examples.

## Installation

To install the latest release from [PyPI](https://pypi.org/project/cocopp):

```sh
    pip install -U cocopp
```

To install the current main branch:

```sh
    git clone https://github.com/numbbo/coco-postprocess.git
    cd coco-postprocess
    pip install .
```

## Usage

The main interface to the [`cocopp`](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.html) package is the [`main`](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.rungeneric.html#main) method (an alias to [`cocopp.rungeneric.main`](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.rungeneric.html#main)). The [`main`](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.rungeneric.html#main) method allows for basic usage of `cocopp` through a shell command-line interface. The recommended use is however from an IPython/Jupyter shell or notebook:

<pre class="py-doctest"><span class="py-prompt">>>></span> <span class="py-keyword">import</span> cocopp
<span class="py-prompt">>>></span> dslist = cocopp.main(<span class="py-string">'exdata/my_output another_folder yet_another_or_not'</span>)  <span class="py-comment"></span></pre>

postprocesses data from one or several folders, for example data generated with the help from the [`cocoex`](https://numbbo.github.io/coco-doc/apidocs/cocoex) module. Each folder should contain data of a full experiment with a single algorithm. (Within the folder the data can be distributed over subfolders). Results can be explored from the <tt class="rst-docutils literal">ppdata/index.html</tt> file, unless a a different output folder is specified with the <tt class="rst-docutils literal"><span class="pre">-o</span></tt> option. **Comparative data** from over 200 full experiments are archived online and can be listed, filtered, and retrieved from [archives](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.archiving.COCODataArchive.html) which are attributes of [`cocopp.archives`](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.archiving.OfficialArchives.html) and processed alone or together with local data. For example

<pre class="py-doctest"><span class="py-prompt">>>></span> cocopp.archives.bbob(<span class="py-string">'bfgs'</span>)  <span class="py-comment"></span>
<span class="py-output">['2009/BFGS_...</span></pre>

lists all data sets run on the `bbob` testbed containing <tt class="rst-docutils literal">'bfgs'</tt> in their name. The first in the list can be postprocessed by

<pre class="py-doctest"><span class="py-prompt">>>></span> dslist = cocopp.main(<span class="py-string">'bfgs!'</span>)  <span class="py-comment"></span></pre>

All of them can be processed like

<pre class="py-doctest"><span class="py-prompt">>>></span> dslist = cocopp.main(<span class="py-string">'bfgs*'</span>)  <span class="py-comment"></span></pre>

Only a trailing `*` is accepted and any string containing the substring is matched. The postprocessing result of

<pre class="py-doctest"><span class="py-prompt">>>></span> dslist = cocopp.main(<span class="py-string">'bbob/2009/*'</span>)  <span class="py-comment"></span></pre>

can be browsed at [https://numbbo.github.io/ppdata-archive/bbob/2009](https://numbbo.github.io/ppdata-archive/bbob/2009). To display algorithms in the background, the [`cocopp.genericsettings.background`](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.genericsettings.html) variable needs to be set:

<pre class="py-doctest"><span class="py-prompt">>>></span> cocopp.genericsettings.background = {<span class="py-builtin">None</span>: cocopp.archives.bbob.get_all(<span class="py-string">'bfgs'</span>)}  <span class="py-comment"></span></pre>

where [`None`](http://docs.python.org/library/constants.html#None) invokes the default color (grey) and line style (solid) [`cocopp.genericsettings.background_default_style`](https://numbbo.github.io/coco-doc/apidocs/cocopp/cocopp.genericsettings.html). Now we could compare our own data with the first <tt class="rst-docutils literal">'bfgs'</tt>-matching archived algorithm where all other archived BFGS data are shown in the background with the command

<pre class="py-doctest"><span class="py-prompt">>>></span> dslist = cocopp.main(<span class="py-string">'exdata/my_output bfgs!'</span>)  <span class="py-comment"></span></pre>

[codereference]: https://doi.org/10.5281/zenodo.2594848
[paper]: https://doi.org/10.1080/10556788.2020.1808977
[pypi]: https://pypi.org/project/cocopp

