from datetime import datetime, timezone
import numpy as np
import pandas as pd
from skyfield.api import EarthSatellite, load, wgs84

# Radio medio de la Tierra en kilómetros (WGS84 aproximado)
EARTH_RADIUS_KM = 6371.0


def latlon_to_cartesian(lat_deg: float, lon_deg: float, alt_km: float = 0.0, r_earth: float = EARTH_RADIUS_KM):
    """
    Convierte Latitud, Longitud y Altitud (WGS84) a Coordenadas Cartesianas 3D ECEF (km).
    Soporta tanto valores escalares como arrays de NumPy.
    """
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    r = r_earth + alt_km
    x = r * np.cos(lat_rad) * np.cos(lon_rad)
    y = r * np.cos(lat_rad) * np.sin(lon_rad)
    z = r * np.sin(lat_rad)
    return x, y, z


class OrbitPropagator:
    def __init__(self, name: str, line1: str, line2: str):
        self.ts = load.timescale()
        self.satellite = EarthSatellite(line1, line2, name, self.ts)

    def get_current_state(self, dt: datetime = None) -> dict:
        """
        Calcula el estado actual del satélite (Latitud, Longitud, Altitud y Velocidad).
        """
        if dt is None:
            dt = datetime.now(timezone.utc)
            
        t = self.ts.from_datetime(dt)
        geocentric = self.satellite.at(t)
        
        # Sub-satellite point (Proyección sobre el elipsoide terrestre WGS84)
        subpoint = wgs84.subpoint(geocentric)
        
        # Cálculo del módulo de la velocidad orbital en km/s
        velocity_vector = geocentric.velocity.km_per_s
        speed = float(np.linalg.norm(velocity_vector))

        return {
            "name": self.satellite.name,
            "datetime": dt,
            "latitude": subpoint.latitude.degrees,
            "longitude": subpoint.longitude.degrees,
            "altitude_km": subpoint.elevation.km,
            "speed_km_s": speed
        }

    def get_ground_track(
        self, 
        dt: datetime = None, 
        minutes_past: int = 45, 
        minutes_future: int = 45, 
        step_seconds: int = 60
    ) -> pd.DataFrame:
        """
        Calcula la trayectoria sobre la superficie terrestre (pasado y futuro)
        para representar la órbita continua en el mapa 2D y globo 3D.
        """
        if dt is None:
            dt = datetime.now(timezone.utc)

        start_time = dt.timestamp() - (minutes_past * 60)
        end_time = dt.timestamp() + (minutes_future * 60)
        
        timestamps = np.arange(start_time, end_time, step_seconds)
        datetimes = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in timestamps]
        
        t_skyfield = self.ts.from_datetimes(datetimes)
        geocentrics = self.satellite.at(t_skyfield)
        subpoints = wgs84.subpoint(geocentrics)

        return pd.DataFrame({
            "datetime": datetimes,
            "latitude": subpoints.latitude.degrees,
            "longitude": subpoints.longitude.degrees,
            "altitude_km": subpoints.elevation.km
        })