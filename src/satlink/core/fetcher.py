import requests

# TLEs de respaldo (Fallback) para la ISS por si CelesTrak bloquea o falla la red
FALLBACK_TLE = [
    {
        "name": "ISS (ZARYA)",
        "line1": "1 25544U 98067A   24080.52180556  .00016717  00000+0  30143-3 0  9991",
        "line2": "2 25544  51.6416 288.2562 0004724  91.6843 325.2638 15.49528348444985"
    }
]

def fetch_tle_by_group(group_name: str = "stations"):
    """
    Obtiene la lista de satélites TLE desde CelesTrak.
    Incluye User-Agent para evitar bloqueos 403 Forbidden.
    """
    url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group_name}&FORMAT=tle"
    
    # Encabezados para simular una petición legítima de navegador
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        lines = [line.strip() for line in response.text.splitlines() if line.strip()]
        
        satellites = []
        for i in range(0, len(lines) - 2, 3):
            name = lines[i]
            line1 = lines[i+1]
            line2 = lines[i+2]
            
            # Verificar formato TLE básico (deben empezar por 1 y 2)
            if line1.startswith("1 ") and line2.startswith("2 "):
                satellites.append({
                    "name": name,
                    "line1": line1,
                    "line2": line2
                })
        
        return satellites if satellites else FALLBACK_TLE

    except Exception as e:
        print(f"Error cargando TLEs desde CelesTrak ({e}). Usando datos de respaldo.")
        return FALLBACK_TLE