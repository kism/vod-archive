#!/usr/bin/env python3
"""Downloads videos from a YouTube Channel with yt-dlp."""

import argparse
import contextlib
import os
import sys

import requests
import yt_dlp

debug = False
YT_API_VIDEOS_PER_PAGE = 50
DEFAULT_PATH = "output"


def my_hook(d: any) -> None:
    """Script that ytdlp runs after downloading or something..."""
    if d["status"] == "finished":
        print("Done downloading, now converting ...")


def print_debug(name: str, in_text: any) -> None:
    """Gross debug print."""
    if debug:
        print("\033[93m--- DEBUG MESSAGE ---\033[0m")
        print(f"\033[93m{name}, {type(in_text)} \033[0m")
        if isinstance(in_text, dict):
            for text in in_text.items():
                print(f"\033[93m{text}\033[0m")
        elif isinstance(in_text, list):
            for text in in_text:
                print(f"\033[93m{text}\033[0m")
        else:
            print(f"\033[93m{in_text}\033[0m")
        print("\033[93m---------------------\033[0m")


def scan_directory(path: str) -> list:
    """Get list of files in output folder."""
    print("🔎 Scanning output folder for existing downloads")
    if path == (DEFAULT_PATH + os.sep):
        with contextlib.suppress(FileExistsError):
            os.makedirs(path)

    if os.path.exists(path):
        print_debug("path", path)

        # Define the list of video file extensions you're interested in
        partial_file_extensions = (".part", ".ytdl")
        video_extensions = (".mp4", ".mkv", ".webm")

        existingfilelist = []
        for _, _, files in os.walk(path):
            for filename in files:
                if filename.endswith(partial_file_extensions):
                    print(f"Removing partial download: {path}{filename}")
                    os.remove(path + filename)
                elif filename.endswith(video_extensions):
                    existingfilelist.append(filename)

        print_debug("existingfilelist", existingfilelist)
    else:
        print(f"Folder doesnt exist: {path}")
        sys.exit()

    return existingfilelist


def get_youtube_video_urls(nvideos: int, existingfilelist: int) -> list:
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
        params = {
            "key": args.k,
            "q": args.s,
            "part": "snippet",
            "channelId": args.c,
            "pageToken": next_page,
            "maxResults": str(nextrequest),
            "order": "relevance",
        }

        print_debug("request", request)
        print_debug("params", params)

        response = requests.get(request, params=params, timeout=10)

        if not response.ok:
            print(f"All is heck, HTTP: {response.status_code}")
            sys.exit(1)

        yt_result = response.json()

        print_debug("yt_result.items", yt_result["items"])

        for i in range(len(yt_result["items"])):  # FIXME TODO
            duplicatefound = False
            try:
                video_id = yt_result["items"][i]["id"]["videoId"]
            except KeyError:
                print("All videos found?")
                break

            for existingvideofilename in existingfilelist:
                if video_id in existingvideofilename:
                    duplicatefound = True

            if not duplicatefound:
                url_list.append("https://youtu.be/" + video_id)

            else:
                print(f'Skipping downloaded video: {yt_result["items"][i]["snippet"]["title"]} [{video_id}]')

        try:
            next_page = yt_result["next_pageToken"]
        except KeyError:
            break

        print(f"Number of videos to download: {nvideos}")
        print(f"URLs: {url_list}")

    return url_list


def download_videos(url_list: list) -> None:
    """Given a list of URLs, download them with yt-dlp."""
    if len(url_list) == 0:
        print("No videos to download")
        return

    print("📺 Downloading Videos")
    ydl_opts["writedescription"] = args.w
    ydl_opts["outtmpl"] = args.p + ydl_opts["outtmpl"]

    # Add custom headers
    yt_dlp.utils.std_headers.update({"Referer": "https://www.google.com"})

    print_debug("ydl_opts", ydl_opts)

    # ℹ️ See the public functions in yt_dlp.YoutubeDL for for other available functions.
    # Eg: "ydl.download", "ydl.download_with_info_file"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i in range(len(url_list)):
            print(f" Looking at youtube link: {url_list[i]}")

            info = ydl.extract_info(url_list[i])

            print(f"Downloading: {info['title']} | {url_list[i]}")

            ydl.download([url_list[i]])

            if args.w:
                print_debug('info["description"]', info["description"])

            print("Download complete.")
            print()

    print("Done downloading videos")


def main(args: argparse.Namespace) -> None:
    """Main."""
    existingfilelist = scan_directory(args.p)
    url_list = get_youtube_video_urls(args.n, existingfilelist)
    download_videos(url_list)


ydl_opts = {
    "format": "bestvideo+bestaudio",
    "merge_output_format": "mkv",
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


if __name__ == "__main__":
    print(f"🙋 {sys.argv[0]}")

    parser = argparse.ArgumentParser(description="Archive a youtube channel")
    parser.add_argument("--debug", action="store_true", help="Debug")
    parser.add_argument("-c", type=str, required=True, help="Channel ID")
    parser.add_argument("-k", type=str, required=True, help="API Key")
    parser.add_argument("-p", type=str, default=DEFAULT_PATH, help="Path")
    parser.add_argument("-n", type=int, default=99999, help="Number of videos")
    parser.add_argument("-s", type=str, default="", help="Search Text")
    parser.add_argument("-w", action="store_true", default=False, help="Write video description to file")

    args = parser.parse_args()
    debug = args.debug

    print_debug("args", args)
    if args.p[-1] != os.sep:
        args.p = args.p + os.sep

    print(f"Archiving YouTube channel : https://www.youtube.com/channel/{args.c}")
    print(f"To location               : {args.p}")
    print(f"Search query              : {args.s}")

    main(args)
