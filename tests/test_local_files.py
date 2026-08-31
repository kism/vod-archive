"""Checks for the premium-upgrade matching logic."""

from pathlib import Path

import pytest

from vod_archive.local_files import _get_best_audio_filesize, _is_premium_match, _normalize_vcodec, scan_directory


@pytest.mark.parametrize(
    ("vcodec", "expected"),
    [
        ("avc1.640028", "h264"),
        ("avc3.640028", "h264"),
        ("hvc1.2.4.L153", "hevc"),
        ("hev1.1.6.L120", "hevc"),
        ("av01.0.08M.08", "av1"),
        ("VP9.2", "vp9"),
        ("vp9", "vp9"),
    ],
)
def test_normalize_vcodec(vcodec, expected):
    assert _normalize_vcodec(vcodec) == expected


def test_get_best_audio_filesize_picks_largest_audio_only_stream():
    formats = [
        {"vcodec": "avc1", "acodec": "none", "filesize": 999},  # video only, ignored
        {"vcodec": "none", "acodec": "opus", "filesize": 100},
        {"vcodec": None, "acodec": "mp4a", "filesize_approx": 250},  # approx counts
    ]
    assert _get_best_audio_filesize(formats) == 250
    assert _get_best_audio_filesize([]) == 0


def test_is_premium_match():
    premium = [{"vcodec": "avc1.640028", "filesize": 900}]

    # Within the 30% tolerance of 900 video + 100 audio.
    assert _is_premium_match("h264", 1000, premium, 100)
    assert _is_premium_match("h264", 1250, premium, 100)
    # Way under: this is the old low-bitrate encode, upgrade it.
    assert not _is_premium_match("h264", 400, premium, 100)
    # Right size, wrong codec.
    assert not _is_premium_match("vp9", 1000, premium, 100)
    # No size advertised, codec match alone is enough.
    assert _is_premium_match("h264", 1, [{"vcodec": "avc1"}], 100)


def test_scan_directory_collects_videos_and_removes_partials(tmp_path: Path):
    (tmp_path / "nested").mkdir()
    keep = tmp_path / "nested" / "20240101 A Video [abcdefghijk].mkv"
    partial = tmp_path / "20240101 B Video [abcdefghijl].mkv.part"
    for f in (keep, partial):
        f.touch()
    (tmp_path / "notes.txt").touch()

    assert scan_directory(tmp_path) == [keep]
    assert not partial.exists()
