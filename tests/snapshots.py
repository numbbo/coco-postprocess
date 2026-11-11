"""Golden-file snapshots of the text output of the post-processing.

A snapshot of a `pipeline.PipelineRun` consists of

- the list of all output files (including figures),
- the content of all generated text files (``.tex``, ``.html``, ``.js``),
- the list of broken relative links in the generated html files,

normalized such that it does not depend on time stamps, temporary
folders or the package version. Snapshots are stored gzipped as
``tests/snapshots/<scenario>.json.gz`` and are (re)written with
``pytest --update-snapshots``.
"""

import difflib
import gzip
import json
import os
import re

import cocopp

from pipeline import TIMESTAMP_RE

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
TEXT_EXTENSIONS = (".tex", ".html", ".js")
# copied verbatim from the package's static folder
STATIC_FILES = ("sorttable.js", "pprldflex.js", "pprldflex.css", "pprldflex.html")
_LINK_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"'#]+)""", re.IGNORECASE)


_HV_HASHES_RE = re.compile(r"hv-hashes inconsistent: (.*?) found!")


def _sorted_hashes(match):
    """the order of the hashes depends on PYTHONHASHSEED (set iteration order)"""
    return "hv-hashes inconsistent: %s found!" % " and ".join(sorted(match.group(1).split(" and ")))


_SIDEPANEL_RE = re.compile(r"(\\providecommand\{\\perfprofsidepanel\}\{\{(?:\\tiny\{\})?)(.*?)(\}\}\n)", re.DOTALL)


def _sorted_sidepanel(match):
    """the order of (nearly) tied algorithms in the pprldmany legend depends on
    floating point summation order, which depends on PYTHONHASHSEED"""
    entries = sorted(e.strip() for e in match.group(2).split("\\vfill"))
    return match.group(1) + "\n\\vfill ".join(entries) + match.group(3)


def normalize(text, replacements):
    """remove run-specific parts from `text`.

    Each replacement ``(old, new)`` is also applied to the LaTeX-escaped
    variants of ``old`` as written by the package.
    """
    for old, new in replacements:
        for variant in (old, old.replace("_", "\\_"), old.replace("_", " ")):
            text = text.replace(variant, new)
    text = TIMESTAMP_RE.sub("_<TIMESTAMP>", text)
    text = _HV_HASHES_RE.sub(_sorted_hashes, text)
    text = _SIDEPANEL_RE.sub(_sorted_sidepanel, text)
    return text.replace(cocopp.__version__, "<VERSION>")


def broken_links(run):
    """return sorted list of ``"page -> link"`` for relative links that don't resolve"""
    res = set()
    for name in run.files:
        if not name.endswith(".html"):
            continue
        path = os.path.join(run.outdir, name)
        with open(path, encoding="utf-8", errors="replace") as f:
            links = _LINK_RE.findall(f.read())
        for link in links:
            if ":" in link.split("/")[0]:  # http:, file:, javascript: ...
                continue
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(path), link))):
                res.add("%s -> %s" % (TIMESTAMP_RE.sub("_<TIMESTAMP>", name), TIMESTAMP_RE.sub("_<TIMESTAMP>", link)))
    return sorted(res)


def take(run, replacements=()):
    """return the snapshot `dict` of a `pipeline.PipelineRun`"""
    replacements = list(replacements) + [(run.workdir, "<WORKDIR>")]
    text = {}
    for name in run.files:
        if name.endswith(TEXT_EXTENSIONS) and os.path.basename(name) not in STATIC_FILES:
            with open(os.path.join(run.outdir, name), encoding="utf-8", errors="replace") as f:
                text[normalize(name, replacements)] = normalize(f.read(), replacements)
    return {
        "files": sorted(normalize(name, replacements) for name in run.files),
        "text": text,
        "broken_links": broken_links(run),
    }


def path(scenario):
    return os.path.join(SNAPSHOT_DIR, scenario + ".json.gz")


def save(scenario, snapshot):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    data = json.dumps(snapshot, indent=0, sort_keys=True).encode("utf-8")
    # mtime=0 makes the gzip file itself reproducible
    with open(path(scenario), "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as gz:
        gz.write(data)


def load(scenario):
    with gzip.open(path(scenario), "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def diff(expected, actual, max_lines=60):
    """return a human readable description of the differences or ``""``"""
    out = []
    for key in ("files", "broken_links"):
        missing = sorted(set(expected[key]) - set(actual[key]))
        added = sorted(set(actual[key]) - set(expected[key]))
        if missing or added:
            out.append("%s: %d missing, %d new" % (key, len(missing), len(added)))
            out += ["  - " + m for m in missing[:10]] + ["  + " + a for a in added[:10]]
    changed = sorted(n for n in set(expected["text"]) & set(actual["text"]) if expected["text"][n] != actual["text"][n])
    if changed:
        out.append("%d text file(s) differ: %s" % (len(changed), ", ".join(changed[:10]) + (" ..." if len(changed) > 10 else "")))
        name = changed[0]
        udiff = difflib.unified_diff(
            expected["text"][name].splitlines(), actual["text"][name].splitlines(), "expected/" + name, "actual/" + name, lineterm="", n=1
        )
        out += list(udiff)[:max_lines]
    return "\n".join(out)


def _main(argv):
    """command line interface to review snapshots::

        python tests/snapshots.py diff OLD.json.gz NEW.json.gz
        python tests/snapshots.py extract SNAPSHOT.json.gz FOLDER

    ``extract`` writes all text files of a snapshot into FOLDER, such that
    two extracted snapshots can be compared with any diff tool, e.g. after
    ``jj file show -r @- tests/snapshots/bbob-1.json.gz > old.json.gz``.
    """
    def read(name):
        with gzip.open(name, "rb") as f:
            return json.loads(f.read().decode("utf-8"))

    if len(argv) == 3 and argv[0] == "diff":
        print(diff(read(argv[1]), read(argv[2]), max_lines=10**6) or "no differences")
    elif len(argv) == 3 and argv[0] == "extract":
        snapshot = read(argv[1])
        for name, text in snapshot["text"].items():
            target = os.path.join(argv[2], *name.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(text)
        for key in ("files", "broken_links"):
            with open(os.path.join(argv[2], "_%s.txt" % key), "w", encoding="utf-8") as f:
                f.write("\n".join(snapshot[key]) + "\n")
    else:
        print(_main.__doc__)


if __name__ == "__main__":
    import sys

    _main(sys.argv[1:])
