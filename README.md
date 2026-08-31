# vod-archive

[![Check (Ruff)](https://github.com/kism/vod-archive/actions/workflows/check.yml/badge.svg)](https://github.com/kism/vod-archive/actions/workflows/check.yml)
[![Type Check (ty)](https://github.com/kism/vod-archive/actions/workflows/check_types.yml/badge.svg)](https://github.com/kism/vod-archive/actions/workflows/check_types.yml)

Archives a YouTube channel: the YouTube Data API v3 finds the videos, [yt-dlp](https://github.com/yt-dlp/yt-dlp) downloads them.

Each run does three things — grabs anything new from the last 30 days, backfills a random 30-day slice of the channel's history, and re-downloads any existing file that YouTube now offers in a higher premium bitrate.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- `ffmpeg` and `ffprobe` on `PATH`

## Run

```bash
uv run vod-archive -k <API_KEY> -c <CHANNEL_ID> [-s <SEARCH>] [-p <OUTPUT_PATH>] [-n <MAX>] [-w] [--debug]
```

| Flag | Meaning |
|------|---------|
| `-k` | YouTube Data API v3 key |
| `-c` | Channel ID — find it in the page source of the channel |
| `-s` | Search text, quoted for you as an exact phrase |
| `-p` | Output directory (default `output/`, the only path created for you — any other must already exist) |
| `-n` | Max videos per search (default: effectively unlimited) |
| `-w` | Write each video's description to a `.description` file |
| `--debug` | Verbose output, and dump the raw search response to `searchresults.json` |

Drop a `cookies.txt` in the working directory to reach age-restricted or private videos.

[archiveyoutube_example.sh](archiveyoutube_example.sh) is a real invocation for the NPR and KEXP channels.

## Check / Test

```bash
uv run ruff check .   # lint, rules live in pyproject.toml
uv run ruff format .  # format
uv run ty check .     # type check
uv run pytest         # test
```
