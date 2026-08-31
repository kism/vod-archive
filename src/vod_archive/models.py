"""Pydantic models for YouTube API and yt-dlp data structures."""

from pydantic import BaseModel, ConfigDict, Field


class YtApiSearchParams(BaseModel):
    """Query parameters for the YouTube Data API v3 search endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    key: str
    q: str
    part: str = "snippet"
    channel_id: str | None = Field(None, serialization_alias="channelId")
    page_token: str = Field("", serialization_alias="pageToken")
    max_results: int = Field(50, serialization_alias="maxResults")
    order: str = "relevance"
    published_after: str | None = Field(None, serialization_alias="publishedAfter")
    published_before: str | None = Field(None, serialization_alias="publishedBefore")

    def to_request_params(self) -> dict[str, str]:
        """Serialise to a flat string dict suitable for requests."""
        return {k: str(v) for k, v in self.model_dump(by_alias=True, exclude_none=True).items()}


class YtApiSearchItemId(BaseModel):
    """The 'id' field of a YouTube search result item."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str
    video_id: str | None = Field(None, alias="videoId")
    channel_id: str | None = Field(None, alias="channelId")
    playlist_id: str | None = Field(None, alias="playlistId")


class YtApiSearchItemSnippet(BaseModel):
    """The 'snippet' field of a YouTube search result item."""

    title: str
    description: str | None = None
    channel_title: str | None = Field(None, alias="channelTitle")

    model_config = ConfigDict(populate_by_name=True)


class YtApiSearchItem(BaseModel):
    """A single item in a YouTube search response."""

    id: YtApiSearchItemId
    snippet: YtApiSearchItemSnippet


class YtApiSearchResponse(BaseModel):
    """Top-level response from the YouTube Data API v3 search endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[YtApiSearchItem]
    next_page_token: str | None = Field(None, alias="nextPageToken")


class YtDlpProgressHook(BaseModel):
    """Dict passed to yt-dlp progress hooks."""

    model_config = ConfigDict(extra="allow")

    status: str


class YtDlpVideoInfo(BaseModel):
    """Subset of yt-dlp extract_info result used by this project."""

    model_config = ConfigDict(extra="allow")

    title: str
    description: str | None = None
