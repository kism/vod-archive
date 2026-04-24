"""Downloads videos from a YouTube Channel with yt-dlp."""

import argparse
import contextlib
import json
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import ffmpeg
import requests
import yt_dlp

from vod_archive.models import YtApiSearchParams, YtApiSearchResponse, YtDlpProgressHook, YtDlpVideoInfo

debug = False
YT_API_VIDEOS_PER_PAGE = 50
DEFAULT_PATH = "output"

DATETIME_NOW = datetime.now()
DATETIME_YT_MIN = datetime(2007, 1, 1)  # About when NPR started


def my_hook(d: Any) -> None:
    """Script that ytdlp runs after downloading or something..."""
    hook = YtDlpProgressHook.model_validate(d)
    if hook.status == "finished":
        print("Done downloading, now converting ...")


def print_debug_var(name: str, in_text: Any) -> None:
    """Gross var debug print."""
    if debug:
        print("\033[93m--- DEBUG MESSAGE ---\033[0m")
        print(f"\033[93m{name}, {type(in_text)} \033[0m")
        if isinstance(in_text, dict):
            for text in in_text.items():
                print_debug(text)
        elif isinstance(in_text, list):
            for text in in_text:
                print_debug(text)
        else:
            print_debug(in_text)
        print("\033[93m---------------------\033[0m")


def print_debug(in_text: Any) -> None:
    """Gross debug print."""
    print(f"\033[93m{in_text}\033[0m")


def scan_directory(path: Path) -> list[Path]:
    """Get list of files in output folder."""
    print("🔎 Scanning output folder for existing downloads")
    if path == Path(DEFAULT_PATH):
        with contextlib.suppress(FileExistsError):
            path.mkdir(parents=True)

    if path.exists():
        print_debug_var("path", path)

        # Define the list of video file extensions you're interested in
        partial_file_extensions = (".part", ".ytdl")
        video_extensions = (".mp4", ".mkv", ".webm")

        existingfilelist: list[Path] = []
        for file in path.rglob("*"):
            if file.is_file():
                if file.name.endswith(partial_file_extensions):
                    print(f"Removing partial download: {file}")
                    file.unlink()
                elif file.name.endswith(video_extensions):
                    existingfilelist.append(file)

        print_debug_var("existingfilelist", existingfilelist)
    else:
        print(f"Folder doesnt exist: {path}")
        sys.exit()

    return existingfilelist


def get_youtube_video_urls(
    nvideos: int,
    existingfilelist: list[Path],
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[str]:
    """Use the YouTube API to get a list of videos from a YouTube channel."""
    print("🔎 Getting (searching) list of videos from the channel")
    url_list = []
    next_page = ""
    while nvideos > 0:
        nextrequest = 0
        if nvideos > YT_API_VIDEOS_PER_PAGE:
            nextrequest = YT_API_VIDEOS_PER_PAGE
            nvideos = nvideos - YT_API_VIDEOS_PER_PAGE
        else:
            nextrequest = nvideos
            nvideos = 0

        request = "https://www.googleapis.com/youtube/v3/search"
        params = YtApiSearchParams(
            key=args.k,
            q=args.s,
            channel_id=args.c,
            page_token=next_page,
            max_results=nextrequest,
            published_after=start_date.isoformat("T") + "Z" if start_date else None,
            published_before=end_date.isoformat("T") + "Z" if end_date else None,
        )

        print_debug_var("request", request)
        print_debug_var("params", params.model_dump())

        response = requests.get(request, params=params.to_request_params(), timeout=10)

        if not response.ok:
            print(f"ERROR searching YouTube: HTTP {response.status_code}")
            print(f"{response.json()}")
            sys.exit(1)

        yt_result = YtApiSearchResponse.model_validate(response.json())

        if debug:
            with Path("searchresults.json").open("w") as file:
                file.write(json.dumps(response.json()))

        for item in yt_result.items:
            print_debug_var("item", item.model_dump())
            if item.id.kind == "youtube#video" and item.id.video_id is not None:
                video_id = item.id.video_id

                duplicate_found = any(video_id in filepath.name for filepath in existingfilelist)

                if not duplicate_found:
                    url_list.append("https://youtu.be/" + video_id)
                else:
                    print(f"Skipping downloaded video: {item.snippet.title} [{video_id}]")

            elif item.id.kind == "youtube#channel":
                print(f"Found channel name btw: {item.snippet.title}")

        if yt_result.next_page_token is None:
            print("All search results have been looked through.")
            break
        next_page = yt_result.next_page_token

    print(f"Number of videos to download: {len(url_list)}")
    print_debug_var("url_list", url_list)

    return url_list


def download_videos(url_list: list) -> None:
    """Given a list of URLs, download them with yt-dlp."""
    if len(url_list) == 0:
        print("No videos to download")
        return

    print("📺 Downloading Videos")
    ydl_opts["writedescription"] = args.w

    ydl_opts["outtmpl"] = str(args.p / ydl_opts["outtmpl"])

    print_debug_var("ydl_opts", ydl_opts)

    # ℹ️ See the public functions in yt_dlp.YoutubeDL for for other available functions.
    # Eg: "ydl.download", "ydl.download_with_info_file"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for yt_url in url_list:
            print("--- DOWNLOAD ITEM ---")
            print(f"Looking at youtube link: {yt_url}")

            info = YtDlpVideoInfo.model_validate(ydl.extract_info(yt_url))

            print(f"Downloading: {info.title} | {yt_url}")

            if args.w:
                print_debug_var("info.description", info.description)

            print("Download complete, sleeping a bit ...")
            time.sleep(random.randint(5, 10))  # Sleep for a random time between downloads to be nice to YouTube
            print()

    print("Done downloading videos")


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
    size_tolerance = 0.30
    for fmt in premium_formats:
        if _normalize_vcodec(fmt.get("vcodec", "")) != existing_codec:
            continue
        fmt_size = fmt.get("filesize") or fmt.get("filesize_approx") or 0
        if fmt_size == 0:
            return True  # No size info — codec match alone is sufficient
        expected = fmt_size + audio_size
        if abs(existing_size - expected) / expected <= size_tolerance:
            return True
    return False


def check_premium_upgrades(existing_files: list[Path]) -> list[str]:
    """Check existing downloads against premium formats and return URLs needing upgrade."""
    print("🔍 Checking existing files for premium quality upgrades")

    ydl_check_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": ydl_opts.get("js_runtimes", {}),
        "remote_components": ydl_opts.get("remote_components", []),
    }
    if "cookiefile" in ydl_opts:
        ydl_check_opts["cookiefile"] = ydl_opts["cookiefile"]

    upgrade_urls: list[str] = []

    with yt_dlp.YoutubeDL(ydl_check_opts) as ydl:
        for file_path in existing_files:
            match = re.search(r"\[([A-Za-z0-9_-]{11})\]", file_path.stem)
            if not match:
                print_debug(f"Could not extract video ID from: {file_path.name}")
                continue

            video_id = match.group(1)
            url = f"https://youtu.be/{video_id}"

            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:  # noqa: BLE001
                print(f"Could not fetch info for {video_id}: {e}")
                continue

            all_formats: list[dict[str, Any]] = info.get("formats", [])
            premium_formats = [
                f for f in all_formats
                if "Premium" in f.get("format_note", "") and f.get("vcodec") not in (None, "none")
            ]

            if not premium_formats:
                print_debug(f"{video_id}: no premium formats available")
                continue

            audio_size = _get_best_audio_filesize(all_formats)

            try:
                probe = ffmpeg.probe(str(file_path))
            except Exception as e:  # noqa: BLE001
                if "Invalid data found when processing input" in str(e):
                    print(f"⬆️  Queued for premium upgrade (corrupt/unreadable): {file_path.name}")
                    upgrade_urls.append(url)
                else:
                    print(f"ffprobe failed for {file_path.name}: {e}")
                continue

            video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
            if not video_streams:
                print_debug(f"{file_path.name}: no video stream found in ffprobe output")
                continue

            existing_codec = video_streams[0].get("codec_name", "")
            existing_size = file_path.stat().st_size

            if _is_premium_match(existing_codec, existing_size, premium_formats, audio_size):
                print(f"✅ Already premium: {file_path.name}")
            else:
                print(f"⬆️  Queued for premium upgrade: {file_path.name}")
                upgrade_urls.append(url)

    return upgrade_urls


def main(args: argparse.Namespace) -> None:
    """Main."""
    existing_files = scan_directory(args.p)
    upgrade_urls = check_premium_upgrades(existing_files)

    if upgrade_urls:
        ydl_opts["overwrites"] = True

    url_list = get_youtube_video_urls(
        args.n, existing_files, start_date=DATETIME_NOW - timedelta(days=30), end_date=DATETIME_NOW
    )
    download_videos(upgrade_urls + url_list)

    # Pick a random 30-day window between DATETIME_YT_MIN and now
    start_date = DATETIME_YT_MIN + timedelta(
        seconds=int((DATETIME_NOW - DATETIME_YT_MIN).total_seconds() * random.random())
    )
    end_date = start_date + timedelta(days=30)
    url_list = get_youtube_video_urls(args.n, existing_files, start_date=start_date, end_date=end_date)
    download_videos(url_list)


ydl_opts = {
    "format": "bestvideo+bestaudio",
    "merge_output_format": "mkv",
    "js_runtimes": {"deno": {}},
    # "impersonate": "firefox",
    "remote_components": ["ejs:github"],
    "outtmpl": "%(upload_date)s %(title)s [%(id)s].%(ext)s",
    "writedescription": False,
    "postprocessors": [
        {
            # Embed metadata in video using ffmpeg.
            # ℹ️ See yt_dlp.postprocessor.FFmpegMetadataPP for the arguments it accepts
            "key": "FFmpegMetadata",
            "add_chapters": True,
            "add_metadata": True,
        },
    ],
    "progress_hooks": [my_hook],
}

if Path(__name__).parent.joinpath("cookies.txt").exists():
    ydl_opts["cookiefile"] = str(Path(__name__).parent.joinpath("cookies.txt"))


if __name__ == "__main__":
    print(f"🙋 {sys.argv[0]}")

    parser = argparse.ArgumentParser(description="Archive a youtube channel")
    parser.add_argument("--debug", action="store_true", help="Debug")
    parser.add_argument("-c", type=str, required=True, help="Channel ID")
    parser.add_argument("-k", type=str, required=True, help="API Key")
    parser.add_argument("-p", type=Path, default=DEFAULT_PATH, help="Path")
    parser.add_argument("-n", type=int, default=99999, help="Number of videos")
    parser.add_argument("-s", type=str, default="", help="Search Text")
    parser.add_argument("-w", action="store_true", default=False, help="Write video description to file")

    args = parser.parse_args()
    debug = args.debug

    args.n += 1  # The query will return the channel as a search result pretty often.

    args.s = f'"{args.s}"'  # Hopefully temp

    print(f"Archiving YouTube channel : https://www.youtube.com/channel/{args.c}")
    print(f"To location               : {args.p}")
    print(f"Search query              : {args.s}")

    main(args)
