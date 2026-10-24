"""Vectorized satellite positions for the Sat-Radar map."""

from __future__ import annotations

from datetime import datetime, timezone
from math import pi

import numpy as np
from sgp4.api import Satrec, SatrecArray
from skyfield.api import load
from skyfield.framelib import itrs
from skyfield.sgp4lib import TEME


_EQUATORIAL_RADIUS_KM = 6378.137
_FLATTENING = 1 / 298.257223563
_ECCENTRICITY_SQUARED = _FLATTENING * (2 - _FLATTENING)
_POLAR_RADIUS_KM = _EQUATORIAL_RADIUS_KM * (1 - _FLATTENING)


def propagate_radar(catalogs: list[tuple[str, list[dict]]], at: datetime | None = None) -> dict:
    """Return one current WGS84 position per NORAD object across the given groups."""
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError("Radar time must include a timezone")

    models: list[Satrec] = []
    metadata: list[tuple[str, str, int]] = []
    seen: set[int] = set()
    for group, satellites in catalogs:
        for satellite in satellites:
            try:
                model = Satrec.twoline2rv(satellite["line1"], satellite["line2"])
            except (KeyError, TypeError, ValueError):
                continue
            if model.satnum <= 0 or model.satnum in seen:
                continue
            seen.add(model.satnum)
            models.append(model)
            metadata.append((satellite["name"], group, model.satnum))

    if not models:
        return {"total_cataloged": 0, "satellites": []}

    # SGP4 accepts arrays of satellites and times, avoiding a Skyfield call per object.
    julian = at.timestamp() / 86400.0 + 2440587.5
    whole = np.floor(julian)
    errors, teme_positions, teme_velocities = SatrecArray(models).sgp4(
        np.array([whole]), np.array([julian - whole])
    )
    teme_positions = teme_positions[:, 0, :]
    teme_velocities = teme_velocities[:, 0, :]

    # Skyfield provides the TEME and Earth-fixed frame rotations used by its
    # single-satellite propagator. Apply that same rotation to the whole array.
    time = load.timescale().from_datetime(at)
    rotation = itrs.rotation_at(time) @ TEME.rotation_at(time).T
    earth_fixed = teme_positions @ rotation.T
    x, y, z = earth_fixed.T
    distance_from_axis = np.hypot(x, y)
    longitude = np.degrees(np.arctan2(y, x))

    # Bowring's WGS84 conversion avoids treating the Earth as a sphere.
    second_eccentricity_squared = (
        _EQUATORIAL_RADIUS_KM**2 - _POLAR_RADIUS_KM**2
    ) / _POLAR_RADIUS_KM**2
    theta = np.arctan2(z * _EQUATORIAL_RADIUS_KM, distance_from_axis * _POLAR_RADIUS_KM)
    latitude = np.arctan2(
        z + second_eccentricity_squared * _POLAR_RADIUS_KM * np.sin(theta) ** 3,
        distance_from_axis - _ECCENTRICITY_SQUARED * _EQUATORIAL_RADIUS_KM * np.cos(theta) ** 3,
    )
    radius = _EQUATORIAL_RADIUS_KM / np.sqrt(1 - _ECCENTRICITY_SQUARED * np.sin(latitude) ** 2)
    altitude = np.where(
        distance_from_axis > 1e-9,
        distance_from_axis / np.cos(latitude) - radius,
        np.abs(z) - _POLAR_RADIUS_KM,
    )
    speed = np.linalg.norm(teme_velocities, axis=1)

    satellites = []
    for index, (name, group, norad_id) in enumerate(metadata):
        model = models[index]
        if errors[index, 0] or not np.isfinite(earth_fixed[index]).all() or not np.isfinite(altitude[index]):
            continue
        satellites.append({
            "id": norad_id,
            "name": name,
            "group": group,
            "latitude": round(float(np.degrees(latitude[index])), 3),
            "longitude": round(float(longitude[index]), 3),
            "altitude_km": round(float(altitude[index]), 1),
            "speed_km_s": round(float(speed[index]), 2),
            "inclination_deg": round(float(np.degrees(model.inclo)), 1),
            "period_min": round(float(2 * pi / model.no_kozai), 1) if model.no_kozai > 0 else None,
            "tle_age_days": round(float(julian - model.jdsatepoch - model.jdsatepochF), 1),
        })

    return {"total_cataloged": len(models), "satellites": satellites}
