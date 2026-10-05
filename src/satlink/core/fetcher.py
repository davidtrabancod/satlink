import requests
from typing import List, Dict

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"

def fetch_tle_by_group(group: str = "active") -> List[Dict[str, str]]:
    """
    Descarga TLEs de CelesTrak dada una categoría/grupo (e.g., 'stations', 'starlink', 'active').
    Retorna una lista de diccionarios con name, line1 y line2.
    """
    params = {"GROUP": group, "FORMAT": "tle"}
    try:
        response = requests.get(CELESTRAK_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Error al conectar con CelesTrak: {e}")

    lines = [line.strip() for line in response.text.strip().splitlines() if line.strip()]
    satellites = []

    for i in range(0, len(lines), 3):
        if i + 2 < len(lines):
            satellites.append({
                "name": lines[i],
                "line1": lines[i+1],
                "line2": lines[i+2]
            })

    return satellites