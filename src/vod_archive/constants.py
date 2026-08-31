"""Constants and program metadata."""

from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PROGRAM_NAME = Path(__file__).parent.name.replace("_", "-").lower()
try:
    PROGRAM_VERSION = version(PROGRAM_NAME)
except PackageNotFoundError:  # pragma: no cover
    PROGRAM_VERSION = "<unknown, please run uv sync>"

DEFAULT_PATH = Path("output")
COOKIES_FILE = Path("cookies.txt")  # Relative to the working directory, for age restricted/private videos
OUTPUT_TEMPLATE = "%(upload_date)s %(title)s [%(id)s].%(ext)s"
MAX_VIDEOS_DEFAULT = 99999  # -n default, effectively "everything the search returns"

YT_API_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YT_API_VIDEOS_PER_PAGE = 50  # Hard limit imposed by the YouTube Data API v3

WINDOW_TO_ARCHIVE = timedelta(days=30)  # Default to archiving videos from the last 30 days
DATETIME_NOW = datetime.now(UTC)
DATETIME_YT_MIN = datetime(2007, 1, 1, tzinfo=UTC)  # About when NPR started
YOUTUBE_PREMIUM_BITRATE_INTRODUCED_DATE = datetime(2023, 4, 1, tzinfo=UTC)

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".webm")
PARTIAL_FILE_EXTENSIONS = (".part", ".ytdl")
VIDEO_ID_PATTERN = r"\[([A-Za-z0-9_-]{11})\]"  # yt-dlp writes the id into the filename, we read it back out
