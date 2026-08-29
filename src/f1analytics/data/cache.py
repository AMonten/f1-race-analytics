"""FastF1 on-disk cache management.

FastF1 downloads session data (timing, laps, telemetry, weather) from the
official F1 live-timing and Ergast-derived endpoints. Without caching, every
page load or script run would re-download the same session, which is slow
and puts unnecessary load on upstream services. This module enables FastF1's
built-in cache exactly once per process and centralises where the cache
lives so it can be overridden (see `f1analytics.config.FASTF1_CACHE_DIR`).
"""

from __future__ import annotations

import logging
from pathlib import Path

import fastf1

from f1analytics.config import FASTF1_CACHE_DIR

logger = logging.getLogger(__name__)

_cache_enabled = False


def enable_cache(cache_dir: Path | str | None = None) -> Path:
    """Enable FastF1's disk cache, creating the directory if needed.

    Safe to call multiple times: after the first call, subsequent calls are
    no-ops unless a different `cache_dir` is explicitly requested.

    Args:
        cache_dir: Directory to store cached session data in. Defaults to
            `f1analytics.config.FASTF1_CACHE_DIR`.

    Returns:
        The resolved cache directory path.
    """
    global _cache_enabled

    resolved_dir = Path(cache_dir) if cache_dir is not None else FASTF1_CACHE_DIR
    resolved_dir.mkdir(parents=True, exist_ok=True)

    if _cache_enabled and cache_dir is None:
        return resolved_dir

    fastf1.Cache.enable_cache(str(resolved_dir))
    _cache_enabled = True
    logger.info("FastF1 cache enabled at %s", resolved_dir)
    return resolved_dir
