"""Fetch and locally cache TLE data from CelesTrak."""

import json
import os
import threading
import time
from pathlib import Path

import requests


FALLBACK_TLE = [
    {
        "name": "ISS (ZARYA)",
        "line1": "1 25544U 98067A   24080.52180556  .00016717  00000+0  30143-3 0  9991",
        "line2": "2 25544  51.6416 288.2562 0004724  91.6843 325.2638 15.49528348444985",
    }
]

_REFRESH_AFTER_SECONDS = 60 * 60
_refresh_locks = {}
_refresh_locks_guard = threading.Lock()


def _cache_path(group_name: str) -> Path:
    """Use a per-user cache that remains available after an app restart."""
    cache_root = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
    if cache_root:
        base = Path(cache_root)
    elif os.name == "nt":
        base = Path.home() / "AppData" / "Local"
    else:
        base = Path.home() / ".cache"
    return base / "SatLink" / "tle" / f"{group_name}.json"


def _read_cache(group_name: str):
    try:
        record = json.loads(_cache_path(group_name).read_text(encoding="utf-8"))
        satellites = record["satellites"]
        fetched_at = float(record["fetched_at"])
        if isinstance(satellites, list) and satellites:
            return satellites, fetched_at
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None, None


def _write_cache(group_name: str, satellites):
    path = _cache_path(group_name)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f"{path.name}.{threading.get_ident()}.tmp")
        temp_path.write_text(
            json.dumps({"fetched_at": time.time(), "satellites": satellites}),
            encoding="utf-8",
        )
        temp_path.replace(path)
    except OSError:
        # Keep the app usable if the local cache directory is not writable.
        pass


def _download_tles(group_name: str):
    url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group_name}&FORMAT=tle"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=(2, 4))
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Error cargando TLEs desde CelesTrak ({exc}).")
        return []

    lines = [line.strip() for line in response.text.splitlines() if line.strip()]
    satellites = []
    for index in range(0, len(lines) - 2, 3):
        name, line1, line2 = lines[index:index + 3]
        if line1.startswith("1 ") and line2.startswith("2 "):
            satellites.append({"name": name, "line1": line1, "line2": line2})
    return satellites


def _refresh_in_background(group_name: str):
    with _refresh_locks_guard:
        lock = _refresh_locks.setdefault(group_name, threading.Lock())
    if not lock.acquire(blocking=False):
        return

    def refresh():
        try:
            satellites = _download_tles(group_name)
            if satellites:
                _write_cache(group_name, satellites)
        finally:
            lock.release()

    try:
        threading.Thread(target=refresh, daemon=True).start()
    except RuntimeError:
        lock.release()


def fetch_tle_by_group(group_name: str = "stations"):
    """Return recent cached TLEs immediately, refreshing stale data in background."""
    cached_satellites, fetched_at = _read_cache(group_name)
    if cached_satellites:
        if time.time() - fetched_at > _REFRESH_AFTER_SECONDS:
            _refresh_in_background(group_name)
        return cached_satellites

    satellites = _download_tles(group_name)
    if satellites:
        _write_cache(group_name, satellites)
        return satellites
    return FALLBACK_TLE
