# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Downloads videos from a YouTube channel: YouTube Data API v3 for discovery, yt-dlp for the actual download.

## Commands

```bash
# Setup (UV, not pip/poetry)
uv venv --clear && source .venv/bin/activate && uv sync --upgrade --all-extras

# Run
python -m vod_archive -k <API_KEY> -c <CHANNEL_ID> [-s <SEARCH>] [-p <OUT_DIR>] [-n <MAX>] [-w] [--debug]

# Lint / format / type check (all installed into .venv)
ruff check . && ruff format . && ty check .
```

`ffmpeg`/`ffprobe` must be on PATH — see [archiveyoutube_example.sh](archiveyoutube_example.sh), which prepends `/opt/ffmpeg` and holds real invocations for the NPR and KEXP channels.

There are no tests.

## Layout

- [vod_archive/__main__.py](vod_archive/__main__.py) — everything: CLI, API pagination, download loop, premium-upgrade check.
- [vod_archive/models.py](vod_archive/models.py) — Pydantic v2 models for the API responses and yt-dlp payloads.

## Non-obvious behaviour

**`args` and `debug` are module globals**, assigned only inside the `if __name__ == "__main__"` block. `get_youtube_video_urls()` and `download_videos()` read `args` directly rather than taking parameters, so they cannot be called from anywhere but that entry point without setting the global first.

**`ydl_opts` is a mutated module global.** `download_videos()` writes `outtmpl` (prefixing the output path) and `writedescription` into it; `main()` sets `overwrites` when upgrades are queued. It's defined *below* the functions that use it, before the `__main__` block.

**Each run does two archive passes plus an upgrade pass** ([`main()`](vod_archive/__main__.py#L320)):
1. Recent window — the last `WINDOW_TO_ARCHIVE` (30 days).
2. Random window — a random 30-day slice between `DATETIME_YT_MIN` (2007) and now, so repeated runs gradually backfill the channel's history.
3. Premium upgrade — search hits that already exist on disk are re-probed and re-downloaded if they look stale.

**Premium upgrade check** ([`check_premium_upgrades()`](vod_archive/__main__.py#L240)): pulls the video ID back out of the filename with a `\[([A-Za-z0-9_-]{11})\]` regex, compares yt-dlp's `Premium` formats against `ffmpeg.probe` (typed-ffmpeg, imported as `ffmpeg`) on the local file — codec match plus filesize within 30% of premium video + best audio. Only applies to uploads after `YOUTUBE_PREMIUM_BITRATE_INTRODUCED_DATE` (2023-04-01); files that fail ffprobe as corrupt are queued unconditionally. Any queued upgrade flips `overwrites=True` for the whole run.

**Duplicate detection is substring matching** — a video is "already downloaded" if its 11-char ID appears anywhere in an existing filename under `-p`.

**`-n` is incremented by 1** because the channel itself usually shows up as a search result. `-s` is wrapped in literal quotes (`"Hopefully temp"`). API paginates at 50/page; `get_youtube_video_urls()` loops for you.

**`cookies.txt` is looked up via `Path(__name__).parent`**, which resolves to the *current working directory*, not the package directory. Drop it next to wherever you invoke from for age-restricted videos.

**Partial downloads (`.part`, `.ytdl`) are deleted on startup** — resume is deliberately not supported.

**`random_sleep()` (5–10s) runs between every download and every probe** to be gentle on YouTube. Long runs are slow by design; don't "optimise" it away.

## Conventions

Python 3.11+, line length 120, Google docstrings. Ruff is `select = ["ALL"]` with a small ignore list in [pyproject.toml](pyproject.toml) — new rules land on you by default; prefer fixing over adding to the ignore list, and if you do add one, comment why like the existing entries do. Pydantic models use `populate_by_name=True` and alias camelCase API fields to snake_case; the yt-dlp models use `extra="allow"` since they only pin the subset actually read.

## Known stale

- [.github/workflows/ruff.yml](.github/workflows/ruff.yml) lints `archiveyoutube.py`, a file that no longer exists, and only on `main`/`test` (work happens on `develop`). It's effectively a no-op CI job.
