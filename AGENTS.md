# vod-archive agent instructions

Video archiver: downloads YouTube channel videos via YouTube Data API v3 + yt-dlp.

## Setup & run

```bash
# Install deps (uses UV)
$HOME/.local/bin/uv venv --clear
source .venv/bin/activate
$HOME/.local/bin/uv sync --upgrade --all-extras

# Run
python -m vod_archive -k <API_KEY> -c <CHANNEL_ID> [-s <SEARCH>] [-p <OUTPUT_PATH>] [-n <MAX>] [-w] [--debug]
```

See [archiveyoutube_example.sh](archiveyoutube_example.sh) for real usage examples.

## Lint / type check

```bash
ruff check .
ruff format .
ty check .
```

## Architecture

| File | Role |
|------|------|
| `vod_archive/__main__.py` | Entry point. CLI args, YouTube API pagination, yt-dlp download loop |
| `vod_archive/models.py` | Pydantic v2 models for YouTube API responses and yt-dlp hooks |

## Key conventions

- **Python 3.11+**, line length 120, Google-style docstrings (enforced by ruff)
- Pydantic models use `populate_by_name=True` + `extra="allow"` to handle camelCase YouTube API fields with snake_case aliases
- Debug output: `\033[93m` yellow ANSI, gated by global `debug` flag
- yt-dlp config lives in `ydl_opts` dict in `__main__.py`; best video+audio merged to MKV, FFmpeg embeds metadata
- **ffmpeg must be in PATH** — example script prepends `/opt/ffmpeg`
- If `cookies.txt` exists in the package dir, it is passed to yt-dlp automatically (age-restricted/private videos)
- Partial downloads (`.part`, `.ytdl`) are cleaned up on startup — resuming is not supported

## Non-obvious behaviours

- Default search window = last 30 days. Change `published_after` / `published_before` in `main()` to archive older content
- `-n` is incremented by 1 internally to account for the channel itself appearing in search results
- YouTube API paginates at 50 results max; `get_youtube_video_urls()` handles this automatically
