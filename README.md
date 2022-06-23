## vod-archive

Scripts for pulling youtube and twitch videos

Needs a youtube data v3 api key

### Prerequisites 

`pip3 install -r requirements.txt`

Make sure you also have ffmpeg installed and in your path

### Examples

Archive top 100 videos of a youtube channel

`archiveyoutube.py -k <api key> -c <youtube channel id> -n 100 -p /path/to/target/dir`

To get chennel id look for "externalId" in the page source of a channel

Archive all Tiny Desk Concerts from the NPR channel

`archiveyoutube.py -k <api key> -c "UC4eYXhJI4-7wSWc8UNRwD4A" -s "Tiny Desk" -w -p /path/to/target/dir`
