#!/usr/bin/env bash
export PATH="/opt/ffmpeg:$PATH"
cd "$(dirname "$0")"

curl -LsSf https://astral.sh/uv/install.sh | sh

$HOME/.local/bin/uv venv --clear
source .venv/bin/activate
$HOME/.local/bin/uv sync --upgrade


apikey=AAA

# To get chennel id look for in the page source of a channel

# NPR
python -m vod_archive -k $apikey -c "UC4eYXhJI4-7wSWc8UNRwD4A" -s "Tiny Desk" -w -p /srv/Freya/Video/Concerts/_NPR/ -n 100000

echo -------------------------------------------------------------------------------------

# KEXP
python -m vod_archive -k $apikey -c "UC3I2GFN_F8WudD_2jUZbojA" -s "Full Performance" -w -p /srv/Freya/Video/Concerts/_KEXP/ -n 10000
