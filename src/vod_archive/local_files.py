"""Everything about videos already on disk: scanning them and spotting stale quality."""

import re
import sys
from typing import TYPE_CHECKING

import yt_dlp

from .constants import DEFAULT_PATH, PARTIAL_FILE_EXTENSIONS, VIDEO_EXTENSIONS, VIDEO_ID_PATTERN
from .downloader import build_probe_opts
from .paths import rename_to_sanitized
from .quality import evaluate_quality, is_cache_valid, load_quality_cache, save_quality_cache
from .utils import console, print_debug, print_debug_var, random_sleep

if TYPE_CHECKING:
    from pathlib import Path


def scan_directory(path: Path) -> list[Path]:
    """Get list of videos in the output folder, deleting partials and sanitizing filenames.

    Every video found is renamed to a sanitized filename — see [`paths`][vod_archive.paths] — so
    a file downloaded before that sanitizing existed gets cleaned up too.
    """
    console.print("🔎 Scanning output folder for existing downloads", style="bold cyan")
    if path == DEFAULT_PATH:
        path.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        console.print(f"Folder doesnt exist: {path}", style="bold red")
        sys.exit(1)

    print_debug_var("path", path)

    existing_files: list[Path] = []
    for file in path.rglob("*"):
        if not file.is_file():
            continue
        if file.name.endswith(PARTIAL_FILE_EXTENSIONS):
            console.print(f"Removing partial download: {file}", style="yellow")  # Resuming isn't supported
            file.unlink()
        elif file.name.endswith(VIDEO_EXTENSIONS):
            existing_files.append(rename_to_sanitized(file))

    print_debug_var("existing_files", existing_files)
    return existing_files


def check_premium_upgrades(existing_files: list[Path]) -> list[str]:
    """Check existing downloads against premium formats and return URLs needing upgrade.

    Each file's verdict is cached alongside it (see [`quality`][vod_archive.quality]) — a file
    whose cache is still valid is trusted as-is and never re-probed.
    """
    console.print("🔍 Checking existing files for premium quality upgrades", style="bold cyan")
    upgrade_urls: list[str] = []

    with yt_dlp.YoutubeDL(build_probe_opts()) as ydl:
        for file_path in existing_files:
            match = re.search(VIDEO_ID_PATTERN, file_path.stem)
            if not match:
                print_debug(f"Could not extract video ID from: {file_path.name}")
                continue

            video_id = match.group(1)
            url = f"https://youtu.be/{video_id}"

            cache = load_quality_cache(file_path)
            if cache is not None and is_cache_valid(cache):
                print_debug(f"{file_path.name}: quality cache still valid, skipping probe")
                continue

            try:
                random_sleep()
                info = ydl.extract_info(url, download=False)
            except Exception as e:  # noqa: BLE001
                console.print(f"Could not fetch info for {video_id}: {e}", style="bold red")
                continue

            needs_upgrade, cache = evaluate_quality(file_path, video_id, info)
            save_quality_cache(file_path, cache)

            if needs_upgrade and url not in upgrade_urls:
                upgrade_urls.append(url)

    return upgrade_urls
