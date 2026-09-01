"""Discovering videos to archive via the YouTube Data API v3."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import requests

from .constants import YT_API_SEARCH_URL, YT_API_VIDEOS_PER_PAGE
from .models import YtApiSearchParams, YtApiSearchResponse
from .utils import console, is_debug, print_debug_var

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ChannelSearch:
    """What to search for, on which channel, with which credentials."""

    api_key: str
    channel_id: str
    query: str
    max_videos: int


class SearchResult(NamedTuple):
    """Search hits split into what needs downloading and what is already on disk."""

    new_urls: list[str]
    existing_files: list[Path]


def search_channel(
    search: ChannelSearch,
    existing_files: list[Path],
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> SearchResult:
    """Use the YouTube API to get a list of videos from a YouTube channel."""
    console.print("🔎 Getting (searching) list of videos from the channel", style="bold cyan")
    url_list: list[str] = []
    matched_existing: list[Path] = []
    next_page = ""
    remaining = search.max_videos

    while remaining > 0:
        this_request = min(remaining, YT_API_VIDEOS_PER_PAGE)
        remaining -= this_request

        params = YtApiSearchParams(
            key=search.api_key,
            q=search.query,
            channel_id=search.channel_id,
            page_token=next_page,
            max_results=this_request,
            published_after=start_date.isoformat() if start_date else None,
            published_before=end_date.isoformat() if end_date else None,
        )

        print_debug_var("request", YT_API_SEARCH_URL)
        print_debug_var("params", params.model_dump())

        response = requests.get(YT_API_SEARCH_URL, params=params.to_request_params(), timeout=10)

        if not response.ok:
            console.print(f"ERROR searching YouTube: HTTP {response.status_code}", style="bold red")
            console.print(response.text, style="bold red")
            sys.exit(1)

        yt_result = YtApiSearchResponse.model_validate(response.json())

        if is_debug():
            Path("searchresults.json").write_text(response.text, encoding="utf-8")

        page = _sort_items(yt_result, existing_files)
        url_list.extend(page.new_urls)
        matched_existing.extend(page.existing_files)

        if yt_result.next_page_token is None:
            console.print("All search results have been looked through.")
            break
        next_page = yt_result.next_page_token

    console.print(f"Number of videos to download: {len(url_list)}")
    print_debug_var("url_list", url_list)

    return SearchResult(url_list, matched_existing)


def _sort_items(yt_result: YtApiSearchResponse, existing_files: list[Path]) -> SearchResult:
    """Split one page of search results into new URLs and already-downloaded files."""
    url_list: list[str] = []
    matched_existing: list[Path] = []

    for item in yt_result.items:
        print_debug_var("item", item.model_dump())

        if item.id.kind == "youtube#video" and item.id.video_id is not None:
            video_id = item.id.video_id
            already_downloaded = [fp for fp in existing_files if video_id in fp.name]

            if already_downloaded:
                matched_existing.extend(already_downloaded)
                console.print(f"Skipping downloaded video: {item.snippet.title} [{video_id}]")
            else:
                url_list.append("https://youtu.be/" + video_id)

        elif item.id.kind == "youtube#channel":
            console.print(f"Found channel name btw: {item.snippet.title}")

    return SearchResult(url_list, matched_existing)
