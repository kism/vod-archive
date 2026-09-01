"""Deriving, comparing, and caching per-video quality — the `.quality.json` sidecar.

The cache serves two purposes. First, it saves time and network/API hits: once a file's
quality is confirmed up to date it isn't re-probed against YouTube every run, just trusted for
`QUALITY_CACHE_TTL`. Second, it guards against a flaky cookie session — one that momentarily
can't see Premium formats — re-flagging an already-confirmed file: a stale probe that never
happens can't trigger a re-download that overwrites a good file with a worse one.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import ffmpeg

from .constants import QUALITY_CACHE_TTL, YOUTUBE_PREMIUM_BITRATE_INTRODUCED_DATE
from .models import QualityCache, QualityInfo
from .utils import print_debug

if TYPE_CHECKING:
    from pathlib import Path

PREMIUM_SIZE_TOLERANCE = 0.30  # A premium re-encode of the same codec lands within 30% of the advertised size


def quality_cache_path(file_path: Path) -> Path:
    """Sidecar path for a downloaded video, e.g. `foo.mkv` -> `foo.quality.json`."""
    return file_path.with_suffix(".quality.json")


def load_quality_cache(file_path: Path) -> QualityCache | None:
    """Load the quality sidecar for a file, tolerating it being missing or corrupt."""
    cache_path = quality_cache_path(file_path)
    if not cache_path.exists():
        return None
    try:
        return QualityCache.model_validate_json(cache_path.read_text(encoding="utf-8"))
    except ValueError as e:
        print_debug(f"{cache_path.name}: corrupt quality cache, ignoring ({e})")
        return None


def save_quality_cache(file_path: Path, cache: QualityCache) -> None:
    """Write the quality sidecar for a file."""
    quality_cache_path(file_path).write_text(cache.model_dump_json(indent=2), encoding="utf-8")


def is_cache_valid(cache: QualityCache) -> bool:
    """Whether a cached verdict can be trusted without re-probing YouTube."""
    if not cache.applicable:
        return True  # Upload predates Premium formats entirely; that never changes.
    if not cache.up_to_date:
        return False  # Known to need an upgrade; only a successful re-download clears this.
    return datetime.now(UTC) - cache.checked_at < QUALITY_CACHE_TTL


def normalize_vcodec(vcodec: str) -> str:
    """Normalize a yt-dlp vcodec string to a comparable ffprobe codec_name."""
    vcodec = vcodec.lower()
    if vcodec.startswith(("avc1", "avc3")):
        return "h264"
    if vcodec.startswith(("hvc1", "hev1")):
        return "hevc"
    if vcodec.startswith("av01"):
        return "av1"
    return vcodec.split(".")[0]


def get_best_audio_filesize(formats: list[dict[str, Any]]) -> int:
    """Return filesize of the best audio-only stream, or 0 if unavailable."""
    audio = [f for f in formats if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")]
    if not audio:
        return 0
    best = max(audio, key=lambda f: f.get("filesize") or f.get("filesize_approx") or 0)
    return best.get("filesize") or best.get("filesize_approx") or 0


def is_premium_match(
    existing_codec: str, existing_size: int, premium_formats: list[dict[str, Any]], audio_size: int
) -> bool:
    """Return True if existing file matches a premium format by codec and approximate filesize."""
    for fmt in premium_formats:
        if normalize_vcodec(fmt.get("vcodec", "")) != existing_codec:
            continue
        fmt_size = fmt.get("filesize") or fmt.get("filesize_approx") or 0
        if fmt_size == 0:
            return True  # No size info — codec match alone is sufficient
        expected = fmt_size + audio_size
        if abs(existing_size - expected) / expected <= PREMIUM_SIZE_TOLERANCE:
            return True
    return False


def probe_current_quality(file_path: Path) -> QualityInfo | None:
    """Inspect a downloaded file directly with ffprobe — no network needed.

    Works just as well on a file downloaded before this cache existed, since it reads the file
    itself rather than anything recorded at download time.
    """
    try:
        probe = ffmpeg.probe(str(file_path))
    except Exception as e:  # noqa: BLE001
        print_debug(f"{file_path.name}: ffprobe failed, can't derive current quality ({e})")
        return None

    video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    if not video_streams:
        return None
    audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
    audio = audio_streams[0] if audio_streams else None

    return QualityInfo(
        vcodec=video_streams[0].get("codec_name"),
        acodec=audio.get("codec_name") if audio else None,
        height=video_streams[0].get("height"),
        filesize=file_path.stat().st_size,
    )


def best_available_quality(formats: list[dict[str, Any]]) -> QualityInfo | None:
    """Describe the best video quality yt-dlp reports as available, flagging Premium formats.

    yt-dlp lists Premium-tier formats (higher bitrate, same resolution) alongside regular ones
    when the account has access to them; those are preferred over anything else on offer.
    """
    video_formats = [f for f in formats if f.get("vcodec") not in (None, "none")]
    if not video_formats:
        return None

    premium_formats = [f for f in video_formats if "Premium" in f.get("format_note", "")]
    pool = premium_formats or video_formats
    best = max(pool, key=lambda f: (f.get("height") or 0, f.get("filesize") or f.get("filesize_approx") or 0))

    video_size = best.get("filesize") or best.get("filesize_approx") or 0
    audio_size = get_best_audio_filesize(formats)
    return QualityInfo(
        format_id=best.get("format_id"),
        vcodec=best.get("vcodec"),
        height=best.get("height"),
        filesize=(video_size + audio_size) or None,
        is_premium=bool(premium_formats),
    )


def evaluate_quality(file_path: Path, video_id: str, info: dict[str, Any]) -> tuple[bool, QualityCache]:
    """Compare a downloaded file against yt-dlp's current formats for it.

    Returns whether it needs a Premium re-download, and the cache entry to persist either way —
    on a miss as much as a hit, so a file that turns out not to need one also stops costing a
    probe next run.
    """
    now = datetime.now(UTC)
    all_formats: list[dict[str, Any]] = info.get("formats", [])
    best_available = best_available_quality(all_formats)
    current = probe_current_quality(file_path)

    if current is None:
        print(f"⬆️  Queued for premium upgrade (corrupt/unreadable): {file_path.name}")
        cache = QualityCache(video_id=video_id, checked_at=now, up_to_date=False, best_available=best_available)
        return True, cache

    upload_date_str: str | None = info.get("upload_date")
    upload_date = datetime.strptime(upload_date_str, "%Y%m%d").replace(tzinfo=UTC) if upload_date_str else None
    if upload_date is None or upload_date < YOUTUBE_PREMIUM_BITRATE_INTRODUCED_DATE:
        print_debug(f"{file_path.name}: uploaded before April 2023, skipping premium check")
        cache = QualityCache(
            video_id=video_id,
            checked_at=now,
            up_to_date=True,
            applicable=False,
            current=current,
            best_available=best_available,
        )
        return False, cache

    premium_formats = [
        f for f in all_formats if "Premium" in f.get("format_note", "") and f.get("vcodec") not in (None, "none")
    ]
    if not premium_formats:
        print_debug(f"{file_path.name}: no premium formats available")
        cache = QualityCache(
            video_id=video_id, checked_at=now, up_to_date=True, current=current, best_available=best_available
        )
        return False, cache

    audio_size = get_best_audio_filesize(all_formats)
    up_to_date = is_premium_match(current.vcodec or "", file_path.stat().st_size, premium_formats, audio_size)
    print(f"✅ Already premium: {file_path.name}" if up_to_date else f"⬆️  Queued for premium upgrade: {file_path.name}")

    cache = QualityCache(
        video_id=video_id, checked_at=now, up_to_date=up_to_date, current=current, best_available=best_available
    )
    return not up_to_date, cache
