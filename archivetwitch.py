#!/usr/bin/env python3
"""Download Twitch Clips."""

import argparse
import sys

import requests
import yt_dlp

YOUTUBE_API_PAGE_SIZE = 50

def my_hook(d) -> None:
    """Download hook."""
    if d["status"] == "finished":
        print("Done downloading, now converting ...")


def print_debug(text: str) -> None:
    """Print debug messages."""
    if debug:
        print("\033[93m" + str(text) + "\033[0m")


def main(args: argparse.Namespace) -> None:
    """Main function."""
    nvideos = 100
    search = ""

    print_debug(args)

    bearertoken = args.k

    if args.p:
        if args.p[-1] != "/":
            args.p = args.p + "/"

        ydl_opts["outtmpl"] = args.p + ydl_opts["outtmpl"]

    if args.n:
        nvideos = args.n

    if args.s:
        search = args.s

    # Get twitch streamer user id
    request = "https://api.twitch.tv/helix/users"
    params = {"login": args.b}
    headers = {"Authorization": "Bearer " + bearertoken, "Client-Id": args.c}
    response = requests.get(request, params=params, headers=headers, timeout=10)

    print_debug(response.json())

    if not response.ok:
        print("All is heck, HTTP: " + str(response.status_code))
        sys.exit(1)

    twitchuserjson = response.json()
    twitchuser = twitchuserjson["data"][0]["id"]

    print_debug("Twitch user: " + args.b)
    print_debug("Twitch ID  : " + twitchuser)

    urllist = []
    nextpage = ""
    endloop = False
    nvideos = int(nvideos)

    while nvideos > 0 and not endloop:
        nextrequest = 0
        if nvideos > YOUTUBE_API_PAGE_SIZE:
            nextrequest = YOUTUBE_API_PAGE_SIZE
            nvideos = nvideos - YOUTUBE_API_PAGE_SIZE
        else:
            nextrequest = nvideos
            nvideos = 0

        request = "https://api.twitch.tv/helix/clips"
        params = {"broadcaster_id": twitchuser, "after": nextpage, "first": nextrequest}
        headers = {"Authorization": "Bearer " + bearertoken, "Client-Id": args.c}

        print_debug("http request url: " + request + "\n" + str(params))

        try:
            response = requests.get(request, params=params, headers=headers, timeout=10)
        except:
            endloop = True

        print_debug("http response: " + str(response))

        if not response.ok:
            print("All is heck, HTTP: " + str(response.status_code))
            sys.exit(1)

        twitchclipresult = response.json()

        print_debug(twitchclipresult)

        print_debug("Items found: " + len(twitchclipresult["data"]))

        for i in range(len(twitchclipresult["data"])):
            urllist.extend([twitchclipresult["data"][i]["url"]])

        print_debug("\n" + str(urllist) + "\n")

        nextpage = twitchclipresult["pagination"]["cursor"]

    print("\nDownloading " + str(len(urllist)) + " clips form " + twitchuser + " (" + args.b + ")\n")

    # Add custom headers
    yt_dlp.utils.std_headers.update({"Referer": "https://www.google.com"})

    print_debug(ydl_opts)
    # ℹ️ See the public functions in yt_dlp.YoutubeDL for for other available functions.
    # Eg: "ydl.download", "ydl.download_with_info_file"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i in range(len(urllist)):
            wat = []
            wat.append(urllist[i])

            info = ydl.extract_info(wat[0])

            print("\n" + info["title"] + " | " + wat[0])

            ydl.download(wat)

            print()


# Vars
debug = False

ydl_opts = {
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
    parser = argparse.ArgumentParser(description="Archive a youtube channel")
    parser.add_argument("-b", type=str, required=True, help="Broadcaster login")
    parser.add_argument("-c", type=str, required=True, help="API Client ID")
    parser.add_argument("-k", type=str, required=True, help="API bearer token")
    parser.add_argument("-p", type=str, help="Path")
    parser.add_argument("-n", type=str, help="Number of videos")
    parser.add_argument("-s", type=str, help="Search Text")

    args = parser.parse_args()

    main(args)
