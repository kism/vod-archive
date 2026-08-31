"""Everything about videos already on disk: scanning them and spotting stale quality."""

import re
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import ffmpeg
import yt_dlp

from .constants import (
    DEFAULT_PATH,
    PARTIAL_FILE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    VIDEO_ID_PATTERN,
    YOUTUBE_PREMIUM_BITRATE_INTRODUCED_DATE,
)
from .downloader import build_probe_opts
from .utils import print_debug, print_debug_var, random_sleep

if TYPE_CHECKING:
    from pathlib import Path

PREMIUM_SIZE_TOLERANCE = 0.30  # A premium re-encode of the same codec lands within 30% of the advertised size


def scan_directory(path: Path) -> list[Path]:
    """Get list of videos in the output folder, deleting any partial downloads found."""
    print("🔎 Scanning output folder for existing downloads")
    if path == DEFAULT_PATH:
        path.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        print(f"Folder doesnt exist: {path}")
        sys.exit(1)

    print_debug_var("path", path)

    existing_files: list[Path] = []
    for file in path.rglob("*"):
        if not file.is_file():
            continue
        if file.name.endswith(PARTIAL_FILE_EXTENSIONS):
            print(f"Removing partial download: {file}")  # Resuming is not supported, start clean
            file.unlink()
        elif file.name.endswith(VIDEO_EXTENSIONS):
            existing_files.append(file)

    print_debug_var("existing_files", existing_files)
    return existing_files


def _normalize_vcodec(vcodec: str) -> str:
    """Normalize a yt-dlp vcodec string to a comparable ffprobe codec_name."""
    vcodec = vcodec.lower()
    if vcodec.startswith(("avc1", "avc3")):
        return "h264"
    if vcodec.startswith(("hvc1", "hev1")):
        return "hevc"
    if vcodec.startswith("av01"):
        return "av1"
    return vcodec.split(".")[0]


def _get_best_audio_filesize(formats: list[dict[str, Any]]) -> int:
    """Return filesize of the best audio-only stream, or 0 if unavailable."""
    audio = [f for f in formats if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")]
    if not audio:
        return 0
    best = max(audio, key=lambda f: f.get("filesize") or f.get("filesize_approx") or 0)
    return best.get("filesize") or best.get("filesize_approx") or 0


def _is_premium_match(
    existing_codec: str, existing_size: int, premium_formats: list[dict[str, Any]], audio_size: int
) -> bool:
    """Return True if existing file matches a premium format by codec and approximate filesize."""
    for fmt in premium_formats:
        if _normalize_vcodec(fmt.get("vcodec", "")) != existing_codec:
            continue
        fmt_size = fmt.get("filesize") or fmt.get("filesize_approx") or 0
        if fmt_size == 0:
            return True  # No size info — codec match alone is sufficient
        expected = fmt_size + audio_size
        if abs(existing_size - expected) / expected <= PREMIUM_SIZE_TOLERANCE:
            return True
    return False


def _needs_upgrade(file_path: Path, info: dict[str, Any]) -> bool:
    """Compare one downloaded file against the premium formats YouTube now offers, reporting the verdict."""
    all_formats: list[dict[str, Any]] = info.get("formats", [])
    premium_formats = [
        f for f in all_formats if "Premium" in f.get("format_note", "") and f.get("vcodec") not in (None, "none")
    ]
    if not premium_formats:
        print_debug(f"{file_path.name}: no premium formats available")
        return False

    try:
        probe = ffmpeg.probe(str(file_path))
    except Exception as e:  # noqa: BLE001
        if "Invalid data found when processing input" in str(e):
            print(f"⬆️  Queued for premium upgrade (corrupt/unreadable): {file_path.name}")
            return True
        print(f"ffprobe failed for {file_path.name}: {e}")
        return False

    upload_date_str: str | None = info.get("upload_date")
    upload_date = datetime.strptime(upload_date_str, "%Y%m%d").replace(tzinfo=UTC) if upload_date_str else None
    if upload_date is None or upload_date < YOUTUBE_PREMIUM_BITRATE_INTRODUCED_DATE:
        print_debug(f"{file_path.name}: uploaded before April 2023, skipping premium check")
        return False

    video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    if not video_streams:
        print_debug(f"{file_path.name}: no video stream found in ffprobe output")
        return False

    audio_size = _get_best_audio_filesize(all_formats)
    existing_codec = video_streams[0].get("codec_name", "")

    if _is_premium_match(existing_codec, file_path.stat().st_size, premium_formats, audio_size):
        print(f"✅ Already premium: {file_path.name}")
        return False

    print(f"⬆️  Queued for premium upgrade: {file_path.name}")
    return True


def check_premium_upgrades(existing_files: list[Path]) -> list[str]:
    """Check existing downloads against premium formats and return URLs needing upgrade."""
    print("🔍 Checking existing files for premium quality upgrades")
    upgrade_urls: list[str] = []

    with yt_dlp.YoutubeDL(build_probe_opts()) as ydl:
        for file_path in existing_files:
            match = re.search(VIDEO_ID_PATTERN, file_path.stem)
            if not match:
                print_debug(f"Could not extract video ID from: {file_path.name}")
                continue

            video_id = match.group(1)
            url = f"https://youtu.be/{video_id}"

            try:
                random_sleep()
                info = ydl.extract_info(url, download=False)
            except Exception as e:  # noqa: BLE001
                print(f"Could not fetch info for {video_id}: {e}")
                continue

            if _needs_upgrade(file_path, info) and url not in upgrade_urls:
                upgrade_urls.append(url)

    return upgrade_urls
