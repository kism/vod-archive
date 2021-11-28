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
    global ydl_opts

    nvideos = 0
    search = ''

    print_debug(args)

    if args.k:
        bearertoken = args.k

    if args.p:
        if args.p[-1] != '/':
            args.p = args.p + '/'

        ydl_opts['outtmpl'] = args.p + ydl_opts['outtmpl']

    if args.n:
        nvideos = args.n

    if args.s:
        search = args.s


    # Get twitch streamer user id
    request = "https://api.twitch.tv/helix/users"
    params = dict(login=args.b)
    headers = {"Authorization": "Bearer " + args.k, "Client-Id": args.c}
    response = requests.get(request, params=params, headers=headers)

    print_debug(response.json())

    if response.status_code != 200:
        print("All is heck, HTTP: " + str(response.status_code))
        exit(1)

    twitchuserjson = response.json()
    twitchuser = twitchuserjson['data'][0]['id']

    print('Twitch user: ' + args.b)
    print('Twitch ID  : ' + twitchuser)

    print('\nthis program is very incomplete')
    print('this program is very incomplete')
    print('this program is very incomplete')
    print('this program is very incomplete')

    exit(420)

    urllist = []
    nextpage = ''
    endloop = False
    nvideos = int(nvideos)

    while nvideos > 0 and endloop == False:
        nextrequest = 0
        if nvideos > 50:
            nextrequest = 50
            nvideos = nvideos - 50
        else:
            nextrequest = nvideos
            nvideos = 0

        request = "https://api.twitch.tv/" + args.c + "/clips"
        params = dict(key=bearertoken, )

        print("http request url: " + request + "\n" + str(params))

        try:
            response = requests.get(request, params=params)
        except:
            pass

        print("http response: " + str(response))

        if response.status_code != 200:
            print("All is heck, HTTP: " + str(response.status_code))
            exit(1)

        print_debug(response.json())

        ytresult = response.json()

        for key, value in ytresult.items():
            #print(key, value)
            pass

        print()













# Vars
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
    parser.add_argument('-b', type=str, required=True, help='Broadcaster login')
    parser.add_argument('-c', type=str, required=True, help='API Client ID')
    parser.add_argument('-k', type=str, required=True, help='API bearer token')
    parser.add_argument('-p', type=str, help='Path')
    parser.add_argument('-n', type=str, help='Number of videos')
    parser.add_argument('-s', type=str, help='Search Text')

    args = parser.parse_args()

    main(args)
