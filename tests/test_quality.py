"""Checks for the quality-derivation, comparison, and caching logic."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vod_archive.models import QualityCache, QualityInfo
from vod_archive.quality import (
    best_available_quality,
    evaluate_quality,
    get_best_audio_filesize,
    is_cache_valid,
    is_premium_match,
    load_quality_cache,
    normalize_vcodec,
    probe_current_quality,
    quality_cache_path,
    save_quality_cache,
)


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
        ("vp09.00.10.08", "vp9"),  # yt-dlp's fourcc form — the actual bug that motivated this test
        ("vp8", "vp8"),
        ("vp08.00.10.08", "vp8"),
    ],
)
def test_normalize_vcodec(vcodec, expected):
    assert normalize_vcodec(vcodec) == expected


def test_get_best_audio_filesize_picks_largest_audio_only_stream():
    formats = [
        {"vcodec": "avc1", "acodec": "none", "filesize": 999},  # video only, ignored
        {"vcodec": "none", "acodec": "opus", "filesize": 100},
        {"vcodec": None, "acodec": "mp4a", "filesize_approx": 250},  # approx counts
    ]
    assert get_best_audio_filesize(formats) == 250
    assert get_best_audio_filesize([]) == 0


def test_is_premium_match():
    premium = [{"vcodec": "avc1.640028", "filesize": 900}]

    # Within the 30% tolerance of 900 video + 100 audio.
    assert is_premium_match("h264", 1000, premium, 100)
    assert is_premium_match("h264", 1250, premium, 100)
    # Way under: this is the old low-bitrate encode, upgrade it.
    assert not is_premium_match("h264", 400, premium, 100)
    # Right size, wrong codec.
    assert not is_premium_match("vp9", 1000, premium, 100)
    # No size advertised, codec match alone is enough.
    assert is_premium_match("h264", 1, [{"vcodec": "avc1"}], 100)


def test_best_available_quality_prefers_premium_when_present():
    formats = [
        {"format_id": "137", "vcodec": "avc1.640028", "height": 1080, "filesize": 900, "format_note": "1080p"},
        {
            "format_id": "137-premium",
            "vcodec": "avc1.640028",
            "height": 1080,
            "filesize": 1200,
            "format_note": "1080p Premium",
        },
        {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "filesize": 100},
    ]

    best = best_available_quality(formats)

    assert best is not None
    assert best.format_id == "137-premium"
    assert best.is_premium is True
    assert best.filesize == 1300  # premium video + best audio


def test_best_available_quality_falls_back_to_regular_when_no_premium():
    formats = [{"format_id": "137", "vcodec": "avc1.640028", "height": 1080, "filesize": 900}]

    best = best_available_quality(formats)

    assert best is not None
    assert best.is_premium is False


def test_best_available_quality_none_when_no_video_formats():
    assert best_available_quality([{"vcodec": "none", "acodec": "mp4a"}]) is None


def test_probe_current_quality_returns_none_on_ffprobe_failure(tmp_path: Path):
    missing = tmp_path / "does-not-exist.mkv"
    assert probe_current_quality(missing) is None


def test_quality_cache_path_swaps_extension():
    assert quality_cache_path(Path("/videos/foo.mkv")) == Path("/videos/foo.quality.json")


def test_save_and_load_quality_cache_round_trip(tmp_path: Path):
    video = tmp_path / "foo.mkv"
    video.touch()
    cache = QualityCache(
        video_id="abcdefghijk",
        checked_at=datetime.now(UTC),
        up_to_date=True,
        current=QualityInfo(vcodec="h264", height=1080),
        best_available=QualityInfo(vcodec="h264", height=1080, is_premium=True),
    )

    save_quality_cache(video, cache)
    loaded = load_quality_cache(video)

    assert loaded == cache
    assert quality_cache_path(video).exists()


def test_load_quality_cache_missing_file_returns_none(tmp_path: Path):
    assert load_quality_cache(tmp_path / "foo.mkv") is None


def test_load_quality_cache_corrupt_file_returns_none(tmp_path: Path):
    video = tmp_path / "foo.mkv"
    quality_cache_path(video).write_text("not json", encoding="utf-8")
    assert load_quality_cache(video) is None


def test_is_cache_valid_not_applicable_never_expires():
    stale = QualityCache(
        video_id="x", checked_at=datetime.now(UTC) - timedelta(days=365), up_to_date=True, applicable=False
    )
    assert is_cache_valid(stale)


def test_is_cache_valid_up_to_date_within_ttl():
    fresh = QualityCache(video_id="x", checked_at=datetime.now(UTC), up_to_date=True)
    assert is_cache_valid(fresh)


def test_is_cache_valid_up_to_date_but_expired():
    stale = QualityCache(video_id="x", checked_at=datetime.now(UTC) - timedelta(days=365), up_to_date=True)
    assert not is_cache_valid(stale)


def test_is_cache_valid_not_up_to_date_always_rechecked():
    # Even a just-written "needs upgrade" verdict is re-checked next run, not trusted.
    needs_upgrade = QualityCache(video_id="x", checked_at=datetime.now(UTC), up_to_date=False)
    assert not is_cache_valid(needs_upgrade)


def test_evaluate_quality_corrupt_file_queues_unconditionally(tmp_path: Path):
    missing = tmp_path / "foo [abcdefghijk].mkv"  # ffprobe fails: file doesn't exist

    needs_upgrade, cache = evaluate_quality(missing, "abcdefghijk", {"formats": []})

    assert needs_upgrade
    assert not cache.up_to_date
    assert cache.current is None
