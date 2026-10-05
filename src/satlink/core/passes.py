from datetime import datetime, timezone
from typing import List, Dict
import pandas as pd
import numpy as np
from skyfield.api import EarthSatellite, load, wgs84

class PassPredictor:
    def __init__(self, name: str, line1: str, line2: str):
        self.ts = load.timescale()
        self.satellite = EarthSatellite(line1, line2, name, self.ts)

    def predict_passes(
        self, 
        lat: float, 
        lon: float, 
        alt_m: float = 0.0, 
        days: int = 3, 
        min_elevation_deg: float = 10.0
    ) -> List[Dict]:
        """
        Calcula los pases visibles sobre la estación terrestre en un intervalo de días.
        """
        ground_station = wgs84.latlon(lat, lon, elevation_m=alt_m)
        t0 = self.ts.now()
        t1 = self.ts.from_datetime(t0.utc_datetime() + pd.Timedelta(days=days))
        
        # Búsqueda de eventos orbitales: 0=AOS, 1=Max El, 2=LOS
        times, events = self.satellite.find_events(
            ground_station, t0, t1, altitude_degrees=min_elevation_deg
        )
        
        passes = []
        current_pass = {}
        
        for time, event in zip(times, events):
            dt = time.utc_datetime()
            difference = (self.satellite - ground_station).at(time)
            topocentric = difference.altaz()
            alt, az, distance = topocentric[0], topocentric[1], topocentric[2]
            
            if event == 0:  # AOS
                current_pass = {
                    "aos_time": dt,
                    "aos_azimuth": az.degrees,
                }
            elif event == 1 and "aos_time" in current_pass:  # Max Elevation
                current_pass["max_el_time"] = dt
                current_pass["max_elevation"] = alt.degrees
                current_pass["min_range_km"] = distance.km
            elif event == 2 and "aos_time" in current_pass:  # LOS
                current_pass["los_time"] = dt
                current_pass["los_azimuth"] = az.degrees
                
                duration = (current_pass["los_time"] - current_pass["aos_time"]).total_seconds()
                current_pass["duration_seconds"] = duration
                
                passes.append(current_pass)
                current_pass = {}
                
        return passes

    def get_pass_trajectory(
        self, 
        lat: float, 
        lon: float, 
        aos_time: datetime, 
        los_time: datetime, 
        step_seconds: int = 5,
        alt_m: float = 0.0
    ) -> pd.DataFrame:
        """
        Genera los puntos (Azimuth, Elevation, Range) durante un pase
        para graficar el diagrama polar de apuntamiento.
        """
        ground_station = wgs84.latlon(lat, lon, elevation_m=alt_m)
        
        start_ts = aos_time.timestamp()
        end_ts = los_time.timestamp()
        timestamps = np.arange(start_ts, end_ts, step_seconds)
        datetimes = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in timestamps]
        
        t_skyfield = self.ts.from_datetimes(datetimes)
        difference = (self.satellite - ground_station).at(t_skyfield)
        topocentric = difference.altaz()
        
        return pd.DataFrame({
            "datetime": datetimes,
            "elevation": topocentric[0].degrees,
            "azimuth": topocentric[1].degrees,
            "range_km": topocentric[2].km
        })