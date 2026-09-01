"""Debug printing, the shared rich console, and rate limiting helpers."""

import random
import time
from typing import Any

from rich.console import Console

# Titles and filenames routinely contain literal `[brackets]` (yt-dlp's `[video_id]`, timestamps,
# etc.) — markup stays off everywhere so none of that is ever parsed as a rich markup tag.
console = Console(markup=False)

_debug = False


def set_debug(*, enabled: bool) -> None:
    """Enable or disable debug output for the whole program."""
    global _debug  # noqa: PLW0603
    _debug = enabled


def print_debug(in_text: Any) -> None:
    """Gross debug print."""
    if _debug:
        console.print(in_text, style="yellow")


def print_debug_var(name: str, in_text: Any) -> None:
    """Gross var debug print."""
    if not _debug:
        return

    console.print("--- DEBUG MESSAGE ---", style="yellow")
    console.print(f"{name}, {type(in_text)} ", style="yellow")
    if isinstance(in_text, dict):
        for text in in_text.items():
            print_debug(text)
    elif isinstance(in_text, list):
        for text in in_text:
            print_debug(text)
    else:
        print_debug(in_text)
    console.print("---------------------", style="yellow")


def random_sleep() -> None:
    """Sleep for a random time between requests to be nice to YouTube."""
    time.sleep(random.randint(5, 10))


def is_debug() -> bool:
    """Whether debug output is enabled."""
    return _debug
