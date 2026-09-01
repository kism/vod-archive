"""Sanitizing yt-dlp's output filenames with pathvalidate, and renaming files (and sidecars) to match.

yt-dlp's own filename sanitizing keeps quote characters — a `"` in a title becomes a `'` rather
than being dropped — which is exactly what shouldn't be showing up in the archive. This strips
quote-like characters outright, then runs pathvalidate over what's left for everything else
(control characters, characters reserved on other filesystems, and so on). It deliberately
leaves yt-dlp's own substitutions — like `:` becoming ` -` — alone.
"""

import re
from typing import TYPE_CHECKING

from pathvalidate import sanitize_filename

from .quality import quality_cache_path
from .utils import console

if TYPE_CHECKING:
    from pathlib import Path

# Straight and curly double/single quotes — dropped outright, never substituted.
_QUOTE_CHARS = "\"'“”‘’"  # " ' “ ” ‘ ’
_QUOTE_TRANSLATION = dict.fromkeys(map(ord, _QUOTE_CHARS), None)


def sanitize_name(name: str) -> str:
    """Strip quote characters from a filename and run pathvalidate over what's left."""
    without_quotes = name.translate(_QUOTE_TRANSLATION)
    cleaned = sanitize_filename(without_quotes)
    return re.sub(r" {2,}", " ", cleaned).strip()


def sanitize_path(file_path: Path) -> Path:
    """The sanitized form of a file's path — same parent directory, cleaned-up name."""
    return file_path.with_name(sanitize_name(file_path.name))


def rename_to_sanitized(file_path: Path) -> Path:
    """Rename a video file (and its `.quality.json`/`.description` sidecars) to a sanitized name.

    Returns the file's new path, or its unchanged path if it was already clean or missing.
    """
    if not file_path.exists():
        return file_path

    sanitized = sanitize_path(file_path)
    if sanitized == file_path:
        return file_path

    if sanitized.exists():
        console.print(f"⚠️  Won't rename, target already exists: {sanitized.name}", style="yellow")
        return file_path

    console.print(f"✂️  Renaming (unsafe characters): {file_path.name} -> {sanitized.name}", style="yellow")
    file_path.rename(sanitized)

    old_quality = quality_cache_path(file_path)
    if old_quality.exists():
        old_quality.rename(quality_cache_path(sanitized))

    old_description = file_path.with_suffix(".description")
    if old_description.exists():
        old_description.rename(sanitized.with_suffix(".description"))

    return sanitized
