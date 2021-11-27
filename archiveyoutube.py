#!/usr/bin/env python3

import json
import argparse
import requests
from requests import api
from requests.models import RequestEncodingMixin
import yt_dlp


class MyLogger:
    def debug(self, msg):
        # For compatability with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            pass
        else:
            self.info(msg)

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')


def main(args):
    global apikey

    nvideos = ''
    search = ''

    print(args)

    if args.k:
        apikey = args.k

    if args.n:
        nvideos = str(args.n)

    if args.s:
        search = args.s

    request = "https://www.googleapis.com/youtube/v3/search"
    params = dict(key=apikey, q=search, part="snippet",
                  channelId=args.c, maxResults=nvideos, order="viewcount")

    print("http request url: " + request + "\n" + str(params))

    try:
        response = requests.get(request, params=params)
    except:
        pass

    print("http response: " + str(response))

    if response.status_code == 200:
        print(response.json())
        print()

        ytresult = response.json()

        for key, value in ytresult.items():
            print(key, value)

        print()

        urllist = []

        for i in range(len(ytresult['items'])):
            urllist.append("https://youtu.be/" +
                           ytresult['items'][i]['id']['videoId'])

        print(urllist)

        global yt_dlp

        # Add custom headers
        #yt_dlp.utils.std_headers.update({'Referer': 'https://www.google.com'})

        # ℹ️ See the public functions in yt_dlp.YoutubeDL for for other available functions.
        # Eg: "ydl.download", "ydl.download_with_info_file"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i in range(len(urllist)):
                wat = []
                wat.append(urllist[i])
                print(wat)
                ydl.download(wat)
            # ydl.add_post_processor(MyCustomPP())
        #    info = ydl.extract_info(
        #        'https://www.youtube.com/watch?v=BaW_jenozKc')

            # ℹ️ ydl.sanitize_info makes the info json-serializable
            # print(json.dumps(ydl.sanitize_info(info)))

        pass
    else:
        pass


# Vars
apikey = "AIzaSyCrR9oOvpdwXofYJZKwrHUKRrQ1HkALTX8"
exitcode = 1

ydl_opts = {
    'format': 'best',
    'outtmpl': '%(upload_date)s %(title)s [%(id)s].%(ext)s',
    'postprocessors': [{
        # Embed metadata in video using ffmpeg.
        # ℹ️ See yt_dlp.postprocessor.FFmpegMetadataPP for the arguments it accepts
        'key': 'FFmpegMetadata',
        'add_chapters': True,
        'add_metadata': True,
    }],
    'logger': MyLogger(),
    'progress_hooks': [my_hook],
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Archive a youtube channel')
    parser.add_argument('-c', type=str, required=True, help='Channel ID')
    parser.add_argument('-k', type=str, help='API Key')
    parser.add_argument('-n', type=str, help='Number of videos')
    parser.add_argument('-s', type=str, help='Search Text')

    args = parser.parse_args()

    main(args)
