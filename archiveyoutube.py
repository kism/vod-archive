#!/usr/bin/env python3

import json
import argparse
import requests
import os
from requests import api
from requests.models import RequestEncodingMixin
import yt_dlp


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')


def print_debug(text):
    if debug:
        print('\033[93m' + str(text) + '\033[0m')


def scan_directory(path):
    print_debug(path)

    existingfilelist = []
    for _, _, files in os.walk(path):
        for filename in files:
            if ".mp4" in filename:
                existingfilelist.append(filename)

    # print_debug("Directory List:")
    # print_debug(existingfilelist)
    return existingfilelist

def main(args):
    global ydl_opts

    nvideos = 99999
    search = ''

    print_debug(args)

    if args.k:
        apikey = args.k

    if args.p:
        if args.p[-1] != '/':
            args.p = args.p + '/'

        ydl_opts['outtmpl'] = args.p + ydl_opts['outtmpl']

    if args.n:
        nvideos = args.n

    if args.s:
        search = args.s

    if args.w:
        ydl_opts['writedescription'] = True

    urllist = []
    nextpage = ''
    endloop = False
    nvideos = int(nvideos)

    # Get files in folder
    existingfilelist = scan_directory(args.p)

    while nvideos > 0 and endloop == False:
        nextrequest = 0
        if nvideos > 50:
            nextrequest = 50
            nvideos = nvideos - 50
        else:
            nextrequest = nvideos
            nvideos = 0

        request = "https://www.googleapis.com/youtube/v3/search"
        params = dict(key=apikey, q=search, part="snippet",
                      channelId=args.c, pageToken=nextpage, maxResults=str(nextrequest), order="viewcount")

        print("http request url: " + request + "\n" + str(params))

        try:
            response = requests.get(request, params=params)
        except:
            pass

        print("http response: " + str(response))

        if response.status_code != 200:
            print("All is heck, HTTP: " + str(response.status_code))
            exit(1)

        # print_debug(response.json())

        ytresult = response.json()

        for key, value in ytresult.items():
            #print(key, value)
            pass

        print()

        for i in range(len(ytresult['items'])):
            duplicatefound = False
            try:
                videoid = ytresult['items'][i]['id']['videoId']
            except:
                print("No more youtube videos in query?")
                print_debug(ytresult)
                #endloop = True

            for existingvideofilename in existingfilelist:
                if videoid in existingvideofilename:
                    duplicatefound = True

            if not duplicatefound and not endloop:
                    urllist.append("https://youtu.be/" + videoid)

            else: 
                print("Skipping video: " + videoid)

        try:
            nextpage = ytresult['nextPageToken']
        except:
            print("No more results")
            endloop = True

        print('Number of Videos: ' + str(nvideos) +
              '\nURLs: ' + str(urllist) + '\n')

    # Add custom headers
    yt_dlp.utils.std_headers.update(
        {'Referer': 'https://www.google.com'})

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


# Vars
debug = True

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
    parser.add_argument('-k', type=str, required=True, help='API Key')
    parser.add_argument('-p', type=str, help='Path')
    parser.add_argument('-n', type=str, help='Number of videos')
    parser.add_argument('-s', type=str, help='Search Text')
    parser.add_argument('-w', action='store_true',
                        help='Write video description to file')

    args = parser.parse_args()

    main(args)
