"""Checks for scanning downloaded files."""

from pathlib import Path

from vod_archive.local_files import scan_directory


def test_scan_directory_collects_videos_and_removes_partials(tmp_path: Path):
    (tmp_path / "nested").mkdir()
    keep = tmp_path / "nested" / "20240101 A Video [abcdefghijk].mkv"
    partial = tmp_path / "20240101 B Video [abcdefghijl].mkv.part"
    for f in (keep, partial):
        f.touch()
    (tmp_path / "notes.txt").touch()

    assert scan_directory(tmp_path) == [keep]
    assert not partial.exists()
