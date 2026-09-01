# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Downloads videos from a YouTube channel: YouTube Data API v3 for discovery, yt-dlp for the download. See [README.md](README.md) for the user-facing flags and [README_DEV.md](README_DEV.md) for dev setup.

## Commands

```bash
uv sync --all-extras   # setup; uv manages the venv and the Python toolchain
uv run vod-archive -k <API_KEY> -c <CHANNEL_ID> [-s <SEARCH>] [-p <OUT_DIR>] [-n <MAX>] [-w] [--debug]

uv run ruff check . && uv run ruff format . && uv run ty check .
uv run pytest                       # all tests
uv run pytest tests/test_quality.py::test_is_premium_match   # one test
uv run coverage run && uv run coverage report   # config in pyproject.toml
```

`ffmpeg`/`ffprobe` must be on `PATH` — [archiveyoutube_example.sh](archiveyoutube_example.sh) prepends `/opt/ffmpeg` and holds the real NPR/KEXP invocations.

Src layout with the `uv_build` backend, so the package is only importable once `uv sync` has installed it into `.venv`. Always drive it through `uv run`; a bare `python -m vod_archive` from the repo root will not find the package.

## Module split

| Module | Owns |
|---|---|
| [`__main__.py`](src/vod_archive/__main__.py) | Argparse and the `main()` orchestration; the only place that reads `args` |
| [`constants.py`](src/vod_archive/constants.py) | Program metadata plus every tunable — date windows, extensions, API URL |
| [`youtube_api.py`](src/vod_archive/youtube_api.py) | Searching the channel, paginating, splitting hits into new vs already-downloaded |
| [`downloader.py`](src/vod_archive/downloader.py) | yt-dlp option construction and the download loop |
| [`local_files.py`](src/vod_archive/local_files.py) | Everything about files already on disk: scanning, and premium-upgrade detection |
| [`quality.py`](src/vod_archive/quality.py) | Deriving, comparing, and caching per-video quality — the `.quality.json` sidecar |
| [`paths.py`](src/vod_archive/paths.py) | Sanitizing yt-dlp's output filenames with pathvalidate, and renaming files (plus sidecars) to match |
| [`models.py`](src/vod_archive/models.py) | Pydantic v2 models for the API responses, yt-dlp payloads, and the quality cache |
| [`utils.py`](src/vod_archive/utils.py) | The shared rich `console`, debug printing, and `random_sleep()` |

There are no globals for CLI state: `main()` builds a `ChannelSearch` and a `ydl_opts` dict and passes them down. `utils.set_debug()` is the one piece of process-wide state, set once in `main()`.

## Non-obvious behaviour

**Each run does three passes** ([`main()`](src/vod_archive/__main__.py)):
1. Recent — the last `WINDOW_TO_ARCHIVE` (30 days).
2. Backfill — a random 30-day slice between `DATETIME_YT_MIN` (2007) and now, so repeated runs gradually walk the channel's history.
3. Premium upgrade — search hits that already exist on disk get re-probed and queued for re-download if stale.

**Premium upgrade detection** ([`evaluate_quality()`](src/vod_archive/quality.py)): pulls the video ID back out of the filename with `VIDEO_ID_PATTERN`, then compares yt-dlp's `Premium` formats against `ffmpeg.probe` (typed-ffmpeg, imported as `ffmpeg`) on the local file — codec must match and filesize must be within `PREMIUM_SIZE_TOLERANCE` of premium video + best audio. Only applies to uploads after `YOUTUBE_PREMIUM_BITRATE_INTRODUCED_DATE` (2023-04-01). Files that fail ffprobe as corrupt are queued unconditionally. Any queued upgrade sets `overwrites=True` for the whole run.

**The `.quality.json` sidecar** ([`quality.py`](src/vod_archive/quality.py)): written next to every downloaded file (`foo.mkv` → `foo.quality.json`), recording its current codec/height/filesize (from `ffmpeg.probe`, so it backfills fine for files that predate this cache), the best quality yt-dlp reported available at last check (flagging `Premium` formats), and whether the file was up to date. `check_premium_upgrades()` trusts a cached `up_to_date=True` verdict for `QUALITY_CACHE_TTL` (90 days) instead of re-probing, and trusts `applicable=False` (upload predates Premium formats) forever — `is_cache_valid()` is the one place that decides. A `False` verdict is always re-checked. This is what keeps a flaky cookie session — one that momentarily can't see Premium formats — from re-flagging an already-confirmed file: the stale probe simply never happens, so it can't trigger a re-download that overwrites a good file with a worse one. `download_videos()` writes the sidecar itself right after each download, reusing the same `info` yt-dlp already fetched (no extra network hit).

**Filenames are sanitized with pathvalidate, not just yt-dlp's own sanitizing** ([`paths.py`](src/vod_archive/paths.py)): yt-dlp substitutes characters it considers unsafe (`:` → ` -`) but only converts `"` to `'` rather than dropping it. `sanitize_name()` strips straight and curly quote characters outright first, then runs pathvalidate's `sanitize_filename()` over what's left. `rename_to_sanitized()` applies this to a file and renames its `.quality.json`/`.description` sidecars alongside it (skipping the rename if the sanitized name already exists, to avoid clobbering). `scan_directory()` runs it over every existing file on every run — so files downloaded before this existed get cleaned up retroactively — and `download_videos()` runs it on each freshly downloaded file before writing its quality cache.

**All output goes through the shared rich `console`** ([`utils.py`](src/vod_archive/utils.py)), constructed with `markup=False` — filenames and titles routinely contain literal `[brackets]` (the `[video_id]` yt-dlp writes into every filename, for one), and rich would otherwise try to parse those as markup tags.

**Duplicate detection is substring matching** — a video counts as downloaded if its 11-char ID appears anywhere in a filename under `-p`.

**`-n` is incremented by 1** because the channel itself usually appears as a search result. `-s` is wrapped in literal quotes (marked "Hopefully temp"). The API paginates at 50/page; `search_channel()` loops for you.

**`cookies.txt` is resolved relative to the working directory**, not the package — see `COOKIES_FILE`.

**Partial downloads (`.part`, `.ytdl`) are deleted on startup** — resume is deliberately not supported.

**`random_sleep()` (5–10s) runs between every download and every metadata probe** to be gentle on YouTube. Long runs are slow by design; don't optimise it away.

## Conventions

Python 3.14, line length 120, Google docstrings. Ruff is `select = ["ALL"]` with a small ignore list in [pyproject.toml](pyproject.toml) — new rules land on you by default, so prefer fixing over ignoring, and comment the reason like the existing entries do. `requires-python` drives ruff's target version, which is why annotation-only imports sit in `if TYPE_CHECKING:` blocks (TC003).

Pydantic models use `populate_by_name=True` and alias camelCase API fields to snake_case; the yt-dlp models use `extra="allow"` since they only pin the subset actually read.

[AGENTS.md](AGENTS.md) is a symlink to this file.
