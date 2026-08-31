"""Debug printing and rate limiting helpers."""

import random
import time
from typing import Any

_debug = False


def set_debug(*, enabled: bool) -> None:
    """Enable or disable debug output for the whole program."""
    global _debug  # noqa: PLW0603
    _debug = enabled


def print_debug(in_text: Any) -> None:
    """Gross debug print."""
    if _debug:
        print(f"\033[93m{in_text}\033[0m")


def print_debug_var(name: str, in_text: Any) -> None:
    """Gross var debug print."""
    if not _debug:
        return

    print("\033[93m--- DEBUG MESSAGE ---\033[0m")
    print(f"\033[93m{name}, {type(in_text)} \033[0m")
    if isinstance(in_text, dict):
        for text in in_text.items():
            print_debug(text)
    elif isinstance(in_text, list):
        for text in in_text:
            print_debug(text)
    else:
        print_debug(in_text)
    print("\033[93m---------------------\033[0m")


def random_sleep() -> None:
    """Sleep for a random time between requests to be nice to YouTube."""
    time.sleep(random.randint(5, 10))


def is_debug() -> bool:
    """Whether debug output is enabled."""
    return _debug
