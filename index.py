"""FastAPI entry point for the Vercel deployment and local development."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from satlink.core.fetcher import fetch_tle_by_group  # noqa: E402
from satlink.core.passes import PassPredictor  # noqa: E402
from satlink.core.propagator import EARTH_RADIUS_KM, OrbitPropagator, latlon_to_cartesian  # noqa: E402

PUBLIC = ROOT / "public"
GROUPS = {"stations", "starlink", "geo", "active"}
_catalog_cache: dict[str, tuple[float, list[dict]]] = {}

app = FastAPI(title="SatLink Studio API", docs_url=None, redoc_url=None)


def _catalog(group: str) -> list[dict]:
    if group not in GROUPS:
        raise HTTPException(status_code=400, detail="Grupo CelesTrak no válido")
    now = datetime.now(timezone.utc).timestamp()
    cached = _catalog_cache.get(group)
    if cached and now - cached[0] < 2 * 60 * 60:
        return cached[1]
    satellites = fetch_tle_by_group(group)
    if not satellites:
        raise HTTPException(status_code=503, detail=f"No hay datos disponibles para el grupo {group}")
    _catalog_cache[group] = (now, satellites)
    return satellites


@app.get("/")
def home():
    return FileResponse(PUBLIC / "index.html")


@app.get("/api/catalog")
def get_catalog(group: str = Query("stations")):
    satellites = _catalog(group)
    stale = bool(satellites[0].get("_tle_stale"))
    fetched_at = satellites[0].get("_tle_fetched_at")
    return {
        "group": group,
        "stale": stale,
        "fetched_at": datetime.fromtimestamp(fetched_at, timezone.utc).isoformat() if fetched_at else None,
        "satellites": [
            {"name": satellite["name"], "line1": satellite["line1"], "line2": satellite["line2"]}
            for satellite in satellites
        ],
    }


@lru_cache(maxsize=64)
def _predict_passes(name: str, line1: str, line2: str, lat: float, lon: float, alt: float, min_el: int):
    predictor = PassPredictor(name, line1, line2)
    return predictor.predict_passes(lat, lon, alt_m=alt, days=3, min_elevation_deg=min_el)


@app.get("/api/mission")
def get_mission(
    group: str = Query("stations"),
    name: str = Query(...),
    lat: float = Query(43.5357, ge=-90, le=90),
    lon: float = Query(-5.6615, ge=-180, le=180),
    alt: float = Query(10, ge=-500, le=10000),
    min_el: int = Query(10, ge=0, le=30),
    include_track: bool = Query(False),
):
    satellite = next((item for item in _catalog(group) if item["name"] == name), None)
    if satellite is None:
        raise HTTPException(status_code=404, detail="Satélite no encontrado en el grupo seleccionado")

    line1, line2 = satellite["line1"], satellite["line2"]
    propagator = OrbitPropagator(name, line1, line2)
    state = propagator.get_current_state()
    passes = _predict_passes(name, line1, line2, lat, lon, alt, min_el)
    now = datetime.now(timezone.utc)
    upcoming = [item for item in passes if item["los_time"] > now]

    pass_status = {"label": "PRÓXIMO PASE", "countdown": "SIN PASES", "active": False, "event_timestamp": None}
    if upcoming:
        next_pass = upcoming[0]
        if now < next_pass["aos_time"]:
            seconds = max(0, int((next_pass["aos_time"] - now).total_seconds()))
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            pass_status = {
                "label": f"AOS EN ({next_pass['aos_time']:%H:%M} UTC)",
                "countdown": f"T- {hours:02d}:{minutes:02d}:{seconds:02d}",
                "active": False,
                "event_timestamp": int(next_pass["aos_time"].timestamp()),
            }
        else:
            seconds = max(0, int((next_pass["los_time"] - now).total_seconds()))
            minutes, seconds = divmod(seconds, 60)
            pass_status = {
                "label": f"LOS EN ({next_pass['los_time']:%H:%M} UTC)",
                "countdown": f"PASE ACTIVO ({minutes:02d}m {seconds:02d}s)",
                "active": True,
                "event_timestamp": int(next_pass["los_time"].timestamp()),
            }

    response = {
        "state": {
            "name": name,
            "datetime": state["datetime"].isoformat(),
            "latitude": state["latitude"],
            "longitude": state["longitude"],
            "altitude_km": state["altitude_km"],
            "speed_km_s": state["speed_km_s"],
        },
        "pass_status": pass_status,
        "passes": [
            {
                "aos_time": item["aos_time"].isoformat(),
                "max_el_time": item["max_el_time"].isoformat(),
                "max_elevation": item["max_elevation"],
                "min_range_km": item["min_range_km"],
                "los_time": item["los_time"].isoformat(),
                "duration_seconds": item["duration_seconds"],
            }
            for item in upcoming
        ],
    }

    if include_track:
        track = propagator.get_ground_track(minutes_past=50, minutes_future=50)
        x, y, z = latlon_to_cartesian(
            track["latitude"].to_numpy(),
            track["longitude"].to_numpy(),
            track["altitude_km"].to_numpy(),
            r_earth=EARTH_RADIUS_KM,
        )
        response["track"] = [
            {
                "timestamp": int(point_time.timestamp() * 1000),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "x": float(px),
                "y": float(py),
                "z": float(pz),
            }
            for point_time, latitude, longitude, px, py, pz in zip(
                track["datetime"], track["latitude"], track["longitude"], x, y, z
            )
        ]
        sx, sy, sz = latlon_to_cartesian(
            state["latitude"], state["longitude"], state["altitude_km"], r_earth=EARTH_RADIUS_KM
        )
        response["satellite_xyz"] = [float(sx), float(sy), float(sz)]

    return response


@lru_cache(maxsize=1)
def _land_points() -> list[list[float]]:
    import numpy as np

    surface = np.load(ROOT / "src" / "satlink" / "core" / "assets" / "world_50m_surface.npz")
    latitudes = surface["latitudes"]
    longitudes = surface["longitudes"]
    mask = surface["mask"] > 0.5
    mask[::2, 1::2] = False
    mask[1::2, ::2] = False
    lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing="ij")
    return np.column_stack((lat_grid[mask], lon_grid[mask])).round(4).tolist()


@app.get("/api/globe-land")
def globe_land():
    return {"points": _land_points(), "earth_radius": EARTH_RADIUS_KM}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/{asset_path:path}")
def static_file(asset_path: str):
    candidate = (PUBLIC / asset_path).resolve()
    if not candidate.is_relative_to(PUBLIC.resolve()) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="No encontrado")
    return FileResponse(candidate)
