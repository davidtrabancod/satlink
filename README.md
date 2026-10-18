# SatLink Studio

Plataforma de seguimiento de satélites, predicción de pases sobre estaciones terrestres y planificación de radioenlaces.

La interfaz es una aplicación web estática servida por FastAPI. La API usa Skyfield para propagar las órbitas y Vercel Python Functions para el despliegue.

## Funciones

- Seguimiento orbital con elementos TLE de CelesTrak.
- Vista 2D del recorrido terrestre y globo 3D interactivo.
- Predicción de AOS, elevación máxima y LOS para una estación terrestre.
- Configuración manual de la estación y geolocalización desde el navegador.
- Diseño adaptable a escritorio y móvil.

## Ejecutar localmente

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn index:app --reload
```

Abre <http://127.0.0.1:8000>.

## Desplegar en Vercel

1. Importa el repositorio en Vercel y deja el directorio raíz en `.`.
2. Vercel carga la aplicación FastAPI desde `index:app`, configurada en `pyproject.toml`, y toma las dependencias del mismo archivo.
3. Despliega el proyecto. No hace falta configurar variables de entorno.

El frontend está en `public/`; la API y el punto de entrada FastAPI están en `index.py`. Los cálculos orbitales existentes siguen en `src/satlink/core/`.

## Desarrollo

Las pruebas del motor orbital están en `tests/` y se ejecutan con `pytest`.
