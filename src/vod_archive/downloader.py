"""yt-dlp options and the download loop."""

from typing import TYPE_CHECKING, Any

import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

from .constants import COOKIES_FILE, OUTPUT_TEMPLATE
from .models import YtDlpProgressHook, YtDlpVideoInfo
from .utils import print_debug_var, random_sleep

if TYPE_CHECKING:
    from pathlib import Path

# Shared by both the download and the metadata-probe clients.
YDL_BASE_OPTS: dict[str, Any] = {
    "js_runtimes": {"deno": {}},
    "remote_components": ["ejs:github"],
}

if COOKIES_FILE.exists():
    YDL_BASE_OPTS["cookiefile"] = str(COOKIES_FILE)


def _progress_hook(d: Any) -> None:
    """Script that ytdlp runs after downloading or something..."""
    hook = YtDlpProgressHook.model_validate(d)
    if hook.status == "finished":
        print("\nDone downloading, now converting ...")


def build_download_opts(output_path: Path, *, write_description: bool, overwrites: bool = False) -> dict[str, Any]:
    """Build the yt-dlp options used to actually fetch videos."""
    return {
        **YDL_BASE_OPTS,
        "format": "bestvideo+bestaudio",
        "merge_output_format": "mkv",
        "impersonate": ImpersonateTarget("firefox"),
        "outtmpl": str(output_path / OUTPUT_TEMPLATE),
        "writedescription": write_description,
        "overwrites": overwrites,
        "postprocessors": [
            {
                # Embed metadata in video using ffmpeg.
                # ℹ️ See yt_dlp.postprocessor.FFmpegMetadataPP for the arguments it accepts
                "key": "FFmpegMetadata",
                "add_chapters": True,
                "add_metadata": True,
            },
        ],
        "progress_hooks": [_progress_hook],
    }


def build_probe_opts() -> dict[str, Any]:
    """Build the yt-dlp options used to inspect a video without downloading it."""
    return {**YDL_BASE_OPTS, "quiet": True, "no_warnings": True}


def download_videos(url_list: list[str], ydl_opts: dict[str, Any], *, write_description: bool) -> None:
    """Given a list of URLs, download them with yt-dlp."""
    if len(url_list) == 0:
        print("No videos to download")
        return

    print("📺 Downloading Videos")
    print_debug_var("ydl_opts", ydl_opts)

    # ℹ️ See the public functions in yt_dlp.YoutubeDL for for other available functions.
    # Eg: "ydl.download", "ydl.download_with_info_file"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for yt_url in url_list:
            print("--- DOWNLOAD ITEM ---")
            print(f"Looking at youtube link: {yt_url}")

            info = YtDlpVideoInfo.model_validate(ydl.extract_info(yt_url))

            print(f"Downloading: {info.title} | {yt_url}")

            if write_description:
                print_debug_var("info.description", info.description)

            print("Download complete, sleeping a bit ...")
            random_sleep()
            print()

    print("Done downloading videos")
