#!/usr/bin/env python3

import json
import argparse
import requests
from requests import api
from requests.models import RequestEncodingMixin
import yt_dlp


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')


def print_debug(text):
    if debug:
        print('\033[93m' + text + '\033[0m')


def main(args):
    global apikey
    global ydl_opts

    nvideos = ''
    search = ''

    print(args)

    if args.k:
        apikey = args.k

    if args.n:
        nvideos = str(args.n)

    if args.s:
        search = args.s

    if args.w:
        ydl_opts['writedescription'] = True

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
        print_debug(response.json())

        ytresult = response.json()

        for key, value in ytresult.items():
            #print(key, value)
            pass

        print()

        urllist = []

        for i in range(len(ytresult['items'])):
            urllist.append("https://youtu.be/" +
                           ytresult['items'][i]['id']['videoId'])

        print(str(urllist) + '\n')

        # Add custom headers
        yt_dlp.utils.std_headers.update({'Referer': 'https://www.google.com'})

        print(ydl_opts)
        # ℹ️ See the public functions in yt_dlp.YoutubeDL for for other available functions.
        # Eg: "ydl.download", "ydl.download_with_info_file"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # ydl.download(urllist)

            for i in range(len(urllist)):
                wat = []
                wat.append(urllist[i])

                info = ydl.extract_info(wat[0])

                print('\n' + info['title'] + ' | ' + wat[0])

                ydl.download(wat)
                
                if args.w:
                    print_debug(info['description'])

                print()

    else:
        pass


# Vars
apikey = "AIzaSyCrR9oOvpdwXofYJZKwrHUKRrQ1HkALTX8"
exitcode = 1
debug = False

ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]',
    'outtmpl': '%(upload_date)s %(title)s [%(id)s].%(ext)s',
    'writedescription': False,
    'postprocessors': [{
        # Embed metadata in video using ffmpeg.
        # ℹ️ See yt_dlp.postprocessor.FFmpegMetadataPP for the arguments it accepts
        'key': 'FFmpegMetadata',
        'add_chapters': True,
        'add_metadata': True,
    }],
    'progress_hooks': [my_hook],
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Archive a youtube channel')
    parser.add_argument('-c', type=str, required=True, help='Channel ID')
    parser.add_argument('-k', type=str, help='API Key')
    parser.add_argument('-n', type=str, help='Number of videos')
    parser.add_argument('-s', type=str, help='Search Text')
    parser.add_argument('-w', action='store_true',
                        help='Write video description to file')

    args = parser.parse_args()

    main(args)
