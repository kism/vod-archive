"""Checks for filename sanitizing and renaming existing files (and their sidecars) to match."""

from pathlib import Path

from vod_archive.paths import rename_to_sanitized, sanitize_name, sanitize_path


def test_sanitize_name_strips_straight_and_curly_quotes():
    assert sanitize_name('NPR: "Tiny Desk" Concert [abc12345678].mkv') == "NPR Tiny Desk Concert [abc12345678].mkv"
    assert sanitize_name("Rock N\u2019 Roll - Song [abc12345678].mkv") == "Rock N Roll - Song [abc12345678].mkv"
    assert sanitize_name("\u201cCurly\u201d quotes [abc12345678].mkv") == "Curly quotes [abc12345678].mkv"


def test_sanitize_name_leaves_already_clean_names_alone():
    assert sanitize_name("20240101 A Video [abcdefghijk].mkv") == "20240101 A Video [abcdefghijk].mkv"


def test_sanitize_name_collapses_whitespace_left_by_removed_quotes():
    assert sanitize_name('Title " Extra" End.mkv') == "Title Extra End.mkv"


def test_sanitize_path_keeps_parent_directory():
    original = Path('/videos/nested/A "Quoted" Title.mkv')
    assert sanitize_path(original) == Path("/videos/nested/A Quoted Title.mkv")


def test_rename_to_sanitized_renames_file_and_sidecars(tmp_path: Path):
    video = tmp_path / 'A "Quoted" Title [abcdefghijk].mkv'
    video.touch()
    quality = tmp_path / 'A "Quoted" Title [abcdefghijk].quality.json'
    quality.write_text("{}", encoding="utf-8")
    description = tmp_path / 'A "Quoted" Title [abcdefghijk].description'
    description.write_text("desc", encoding="utf-8")

    result = rename_to_sanitized(video)

    expected = tmp_path / "A Quoted Title [abcdefghijk].mkv"
    assert result == expected
    assert expected.exists()
    assert not video.exists()
    assert (tmp_path / "A Quoted Title [abcdefghijk].quality.json").exists()
    assert (tmp_path / "A Quoted Title [abcdefghijk].description").exists()
    assert not quality.exists()
    assert not description.exists()


def test_rename_to_sanitized_no_op_for_already_clean_file(tmp_path: Path):
    video = tmp_path / "20240101 A Video [abcdefghijk].mkv"
    video.touch()

    assert rename_to_sanitized(video) == video
    assert video.exists()


def test_rename_to_sanitized_missing_file_returns_unchanged(tmp_path: Path):
    missing = tmp_path / 'A "Quoted" Title.mkv'
    assert rename_to_sanitized(missing) == missing


def test_rename_to_sanitized_wont_clobber_existing_target(tmp_path: Path):
    video = tmp_path / 'A "Quoted" Title.mkv'
    video.touch()
    target = tmp_path / "A Quoted Title.mkv"
    target.touch()

    result = rename_to_sanitized(video)

    assert result == video
    assert video.exists()
