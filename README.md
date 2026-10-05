# 🛰️ SatLink Studio

> **Open-Source Satellite Tracking & Ground Station Link Planning Platform**

**SatLink Studio** es una plataforma orientada a la ingeniería de telecomunicaciones y la mecánica orbital. Permite el seguimiento de satélites en tiempo real, la predicción de pases sobre estaciones terrestres (*AOS*, *TCA*, *LOS*), la generación de diagramas polares de apuntamiento (*Skyplots*) y el análisis de presupuestos de enlace (*Link Budget*).

---

## 🚀 Características Principales

- **Seguimiento Orbital en Tiempo Real:** Propagación SGP4 de alta precisión consumiendo elementos TLE (*Two-Line Element set*) actualizados desde CelesTrak.
- **Predicción de Pases (Topocéntrica):** Cálculo de momentos clave de visibilidad (*AOS - Acquisition of Signal*, *TCA - Time of Closest Approach*, *LOS - Loss of Signal*) sobre coordenadas personalizadas de la Estación Terrestre.
- **Visualización Interactiva:** Mapas 2D con proyección equirrectangular y diagramas polares para el barrido de antenas.
- **Arquitectura Modular (Python):** Diseñado siguiendo la estructura moderna `src/` layout, facilísimo de extender y probar.

---

## 🛠️ Tech Stack

- **Lenguaje:** Python 3.10+
- **Mecánica Orbital:** Skyfield (SGP4)
- **Procesamiento de Datos:** NumPy, Pandas
- **Visualización:** Plotly, Streamlit
- **Testing:** Pytest

---

## 📁 Estructura del Repositorio

```text
satlink/
├── pyproject.toml              # Configuración del paquete y dependencias
├── src/
│   └── satlink/
│       ├── core/               # Motores astrodinámicos y de RF
│       │   ├── fetcher.py      # Cliente HTTP para TLEs de CelesTrak
│       │   ├── propagator.py   # Propagación SGP4 (ECI/ECEF)
│       │   └── passes.py       # Algoritmos topocéntricos (AER) y pases
│       └── ui/
│           └── app.py          # Dashboard interactivo en Streamlit
└── tests/                      # Suite de pruebas con Pytest