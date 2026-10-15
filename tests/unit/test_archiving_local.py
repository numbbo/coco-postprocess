"""Unit tests for `cocopp.archiving` with *local* archives only.

Nothing here touches the network or the user's cache folder:
`ArchivesLocal.register`, which would record created archives in the
user's cache, is patched.
"""

import os
import tarfile

import pytest

from cocopp import archiving


@pytest.fixture
def registered(monkeypatch):
    calls = []
    monkeypatch.setattr(archiving.ArchivesLocal, "register", classmethod(lambda cls, folder: calls.append(folder)))
    return calls


@pytest.fixture
def archive_folder(tmp_path, bbob_small, bbob_old_format):
    """a folder with three zipped "data sets" in sub-folders"""
    root = tmp_path / "my-archive"
    for sub, src, name in [("2020", bbob_small, "SMALL_alg.tgz"), ("2021", bbob_old_format, "OLD_alg.tgz"), ("2021", bbob_small, "SMALL2.tgz")]:
        (root / sub).mkdir(parents=True, exist_ok=True)
        with tarfile.open(str(root / sub / name), "w:gz") as tar:
            tar.add(src, arcname=os.path.basename(src))
    (root / "README.md").write_text("ignored")
    return root


@pytest.fixture
def archive(archive_folder, registered):
    return archiving.create(str(archive_folder))


class TestCreateAndRead:
    def test_create(self, archive, archive_folder, registered):
        assert isinstance(archive, archiving.COCODataArchive)
        assert sorted(archive) == ["2020/SMALL_alg.tgz", "2021/OLD_alg.tgz", "2021/SMALL2.tgz"]
        assert registered == [str(archive_folder)]
        assert (archive_folder / archiving.default_definition_filename).exists()
        assert archive.remote_data_path is None
        assert archive.local_data_path == str(archive_folder)

    def test_definition_file(self, archive, archive_folder):
        defs = archiving.read_definition_file(str(archive_folder))
        assert sorted(d[0] for d in defs) == sorted(archive)
        name, hash_, size = [d for d in defs if d[0] == "2020/SMALL_alg.tgz"][0]
        assert hash_ == archiving._hash(str(archive_folder / "2020" / "SMALL_alg.tgz"))
        assert isinstance(size, int)

    def test_get_returns_existing_archive(self, archive, archive_folder):
        same = archiving.get(str(archive_folder))
        assert list(same) == list(archive)
        assert archiving.COCODataArchive.is_archive(str(archive_folder))
        assert not archiving.COCODataArchive.is_archive(str(archive_folder / "2020"))

    def test_not_an_archive(self, tmp_path):
        with pytest.raises(ValueError, match="seems not to"):
            archiving.COCODataArchive(str(tmp_path))
        with pytest.raises(ValueError):
            archiving.get(None)

    def test_recreate_makes_backup(self, archive, archive_folder, registered):
        archiving.create(str(archive_folder))
        backups = [f for f in os.listdir(archive_folder) if f.startswith("._" + archiving.default_definition_filename)]
        assert len(backups) == 1

    def test_empty_archive(self, tmp_path, registered):
        with pytest.warns(UserWarning, match="no data found"):
            assert archiving.create(str(tmp_path)) is None

    def test_unusual_file_warns(self, tmp_path, registered):
        (tmp_path / "data.abc").write_text("x")
        with pytest.warns(UserWarning, match="unusual file"):
            arch = archiving.create(str(tmp_path))
        assert list(arch) == ["data.abc"]


class TestFindAndGet:
    def test_find(self, archive):
        assert archive.find("small") == ["2020/SMALL_alg.tgz", "2021/SMALL2.tgz"]
        assert archive.find("2021", "small") == ["2021/SMALL2.tgz"]
        assert archive("old") == ["2021/OLD_alg.tgz"]
        assert archive.found == ["2021/OLD_alg.tgz"]

    def test_get(self, archive, archive_folder):
        path = archive.get("OLD")
        assert path == str(archive_folder / "2021" / "OLD_alg.tgz")
        assert archive.get(0) == archive.full_path(archive[0])
        archive.find("OLD")
        assert archive.get() == path  # first of last found
        assert archive.contains(path) and archive.contains("2021/OLD_alg.tgz")
        assert not archive.contains("nothing")

    def test_get_ambiguous_or_missing(self, archive):
        with pytest.raises(ValueError, match="multiple matches"):
            archive.get("SMALL")
        with pytest.raises(ValueError, match="no match"):
            archive.get("nonexisting")
        with pytest.raises(ValueError):
            archive.get("OLD", remote="yes")

    def test_get_all_first_and_extended(self, archive, archive_folder):
        assert len(archive.get_all("small")) == 2
        assert archive.get_first(["small"]) == str(archive_folder / "2020" / "SMALL_alg.tgz")
        assert archive.get_first(["nothing"]) is None
        archive.find("OLD")
        assert archive.get_found() == [str(archive_folder / "2021" / "OLD_alg.tgz")]
        assert archive.get_extended(["small!"]) == [str(archive_folder / "2020" / "SMALL_alg.tgz")]
        assert len(archive.get_extended("small*")) == 2
        assert archive.get_extended(["20.*SMALL"]) == archive.get_all("small")
        assert archive.get_extended([str(archive_folder)]) == [str(archive_folder)]  # existing path
        with pytest.raises(ValueError):
            archive.get_extended(["nonexisting"], remote=False)

    def test_downloaded_and_hash_check(self, archive, archive_folder):
        assert sorted(archive.downloaded) == sorted(archive)
        assert archive.consistency_check_data() == (3, 3)
        path = archive_folder / "2021" / "OLD_alg.tgz"
        with open(path, "ab") as f:
            f.write(b"corrupt")
        with pytest.raises(ValueError, match="wrong checksum"):
            archive.get("OLD")

    def test_missing_file_with_remote_false(self, archive, archive_folder):
        os.remove(archive_folder / "2021" / "OLD_alg.tgz")
        assert archive.get("OLD", remote=False) == ""

    @pytest.mark.xfail(reason="known bug: get_found passes all found names as AND-substrings to find", strict=True)
    def test_get_found_with_several_matches(self, archive):
        archive.find("small")
        assert len(archive.get_found()) == 2

    @pytest.mark.xfail(reason="known bug: malformed format string in COCODataArchive.update", raises=TypeError, strict=True)
    def test_update_without_url_prints_hint(self, archive, capsys):
        archive.update()
        assert "has no remote URL" in capsys.readouterr().out


class TestHelpers:
    def test_url_helpers(self):
        assert archiving._is_url("https://x") and archiving._is_url("HTTP://x") and not archiving._is_url("/x")
        folder = archiving._url_to_folder_name("https://numbbo.github.io/data-archive/data-archive/bbob")
        assert folder == os.path.join(archiving.default_archive_location, "da", "bbob")

    def test_str_to_list(self):
        assert archiving._str_to_list("a") == ["a"]
        assert archiving._str_to_list(("a",)) == ("a",)
        with pytest.raises(ValueError):
            archiving._str_to_list(3)

    def test_definition_file_names(self, tmp_path):
        assert archiving._definition_file_to_read(str(tmp_path)) == str(tmp_path / archiving.default_definition_filename)
        assert archiving._definition_file_to_write(str(tmp_path)) == str(tmp_path / archiving.default_definition_filename)
        assert archiving._definition_file_to_write(str(tmp_path), "x.txt") == str(tmp_path / "x.txt")
        with pytest.warns(UserWarning):
            archiving._definition_file_to_write(str(tmp_path / "other.txt"))

    def test_repr_definitions_is_sorted(self):
        s = archiving._repr_definitions([("b/x", "h", 1), ("a/y", "h", 2)])
        assert s.index("a/y") < s.index("b/x")
