"""Tests for f1analytics.data.cache.

We never hit FastF1's network layer here — only verify that our thin wrapper
manages the cache directory and calls fastf1.Cache.enable_cache correctly.
"""

from __future__ import annotations

import f1analytics.data.cache as cache_module


def test_enable_cache_creates_directory(tmp_path, monkeypatch):
    target_dir = tmp_path / "fastf1_cache"
    monkeypatch.setattr(cache_module, "_cache_enabled", False)
    monkeypatch.setattr(cache_module.fastf1.Cache, "enable_cache", lambda path: None)

    resolved = cache_module.enable_cache(target_dir)

    assert resolved == target_dir
    assert target_dir.is_dir()


def test_enable_cache_defaults_to_config_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(cache_module, "_cache_enabled", False)
    monkeypatch.setattr(cache_module, "FASTF1_CACHE_DIR", tmp_path / "default_cache")
    monkeypatch.setattr(cache_module.fastf1.Cache, "enable_cache", lambda path: None)

    resolved = cache_module.enable_cache()

    assert resolved == tmp_path / "default_cache"
    assert resolved.is_dir()


def test_enable_cache_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(cache_module, "_cache_enabled", False)
    calls: list[str] = []
    monkeypatch.setattr(
        cache_module.fastf1.Cache, "enable_cache", lambda path: calls.append(path)
    )

    cache_module.enable_cache(tmp_path / "a")
    cache_module.enable_cache()  # no explicit dir -> should not re-trigger fastf1 call

    assert len(calls) == 1
