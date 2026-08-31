"""Downloads videos from a YouTube Channel with yt-dlp."""

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .constants import (
    DATETIME_NOW,
    DATETIME_YT_MIN,
    DEFAULT_PATH,
    PROGRAM_NAME,
    PROGRAM_VERSION,
    WINDOW_TO_ARCHIVE,
)
from .downloader import build_download_opts, download_videos
from .local_files import check_premium_upgrades, scan_directory
from .utils import set_debug
from .youtube_api import ChannelSearch, search_channel


def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME, description="Archive a youtube channel")
    parser.add_argument("--version", action="version", version=f"{PROGRAM_NAME} v{PROGRAM_VERSION}")
    parser.add_argument("--debug", action="store_true", help="Debug")
    parser.add_argument("-c", type=str, required=True, help="Channel ID")
    parser.add_argument("-k", type=str, required=True, help="API Key")
    parser.add_argument("-p", type=Path, default=DEFAULT_PATH, help="Path")
    parser.add_argument("-n", type=int, default=99999, help="Number of videos")
    parser.add_argument("-s", type=str, default="", help="Search Text")
    parser.add_argument("-w", action="store_true", default=False, help="Write video description to file")
    return parser.parse_args()


def _random_window() -> tuple[datetime, datetime]:
    """Pick a random WINDOW_TO_ARCHIVE-long window between DATETIME_YT_MIN and now."""
    elapsed = (DATETIME_NOW - DATETIME_YT_MIN).total_seconds()
    start_date = DATETIME_YT_MIN + timedelta(seconds=int(elapsed * random.random()))
    return start_date, start_date + WINDOW_TO_ARCHIVE


def main() -> None:
    """Archive recent videos, backfill a random slice of history, and upgrade stale downloads."""
    print(f"🙋 {sys.argv[0]}")
    args = _get_args()
    set_debug(enabled=args.debug)

    search = ChannelSearch(
        api_key=args.k,
        channel_id=args.c,
        query=f'"{args.s}"',  # Hopefully temp
        max_videos=args.n + 1,  # The query will return the channel as a search result pretty often.
    )

    print(f"Archiving YouTube channel : https://www.youtube.com/channel/{search.channel_id}")
    print(f"To location               : {args.p}")
    print(f"Search query              : {search.query}")

    existing_files = scan_directory(args.p)

    recent = search_channel(search, existing_files, start_date=DATETIME_NOW - WINDOW_TO_ARCHIVE, end_date=DATETIME_NOW)
    random_start, random_end = _random_window()
    backfill = search_channel(search, existing_files, start_date=random_start, end_date=random_end)

    # Deduplicated, order preserved
    files_to_check = list(dict.fromkeys(recent.existing_files + backfill.existing_files))
    upgrade_urls = check_premium_upgrades(files_to_check)

    ydl_opts = build_download_opts(args.p, write_description=args.w, overwrites=bool(upgrade_urls))

    print("\n --- Downloading Recent Videos ---")
    download_videos(upgrade_urls + recent.new_urls, ydl_opts, write_description=args.w)
    print("\n --- Downloading Random Videos ---")
    download_videos(backfill.new_urls, ydl_opts, write_description=args.w)


if __name__ == "__main__":
    main()  # pragma: no cover
