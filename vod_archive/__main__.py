"""Downloads videos from a YouTube Channel with yt-dlp."""

import argparse
import contextlib
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

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


def scan_directory(path: Path) -> list[str]:
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

        existingfilelist = []
        for file in path.rglob("*"):
            if file.is_file():
                if file.name.endswith(partial_file_extensions):
                    print(f"Removing partial download: {file}")
                    file.unlink()
                elif file.name.endswith(video_extensions):
                    existingfilelist.append(file.name)

        print_debug_var("existingfilelist", existingfilelist)
    else:
        print(f"Folder doesnt exist: {path}")
        sys.exit()

    return existingfilelist


def get_youtube_video_urls(
    nvideos: int,
    existingfilelist: list[str],
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

                duplicate_found = any(video_id in filename for filename in existingfilelist)

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
    ydl_opts["outtmpl"] = args.p + ydl_opts["outtmpl"]

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

            print("Download complete.")
            print()

    print("Done downloading videos")


def main(args: argparse.Namespace) -> None:
    """Main."""
    existingfilelist = scan_directory(args.p)

    url_list = get_youtube_video_urls(
        args.n, existingfilelist, start_date=DATETIME_NOW - timedelta(days=30), end_date=DATETIME_NOW
    )
    download_videos(url_list)

    # Pick a random 30-day window between DATETIME_YT_MIN and now
    start_date = DATETIME_YT_MIN + timedelta(
        seconds=int((DATETIME_NOW - DATETIME_YT_MIN).total_seconds() * random.random())
    )
    end_date = start_date + timedelta(days=30)
    url_list = get_youtube_video_urls(args.n, existingfilelist, start_date=start_date, end_date=end_date)
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
