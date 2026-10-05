import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from streamlit_geolocation import streamlit_geolocation
from satlink.core.fetcher import fetch_tle_by_group
from satlink.core.propagator import OrbitPropagator
from satlink.core.passes import PassPredictor

# 1. Configuración de página (DEBE SER LA PRIMERA INSTRUCCIÓN DE STREAMLIT)
st.set_page_config(page_title="SatLink Studio", layout="wide")

st.title("🛰️ SatLink Studio — Satellite & Ground Station Platform")
st.caption("Seguimiento orbital, predicción de pases y planificación de RF")

# 2. Inicializar st.session_state con valores por defecto (Gijón)
if "gs_lat" not in st.session_state:
    st.session_state.gs_lat = 43.5357
if "gs_lon" not in st.session_state:
    st.session_state.gs_lon = -5.6615
if "gs_alt" not in st.session_state:
    st.session_state.gs_alt = 10.0

# 3. BARRA LATERAL - SECCIÓN 1: SATÉLITE
st.sidebar.header("1. Configuración de Satélite")
group = st.sidebar.selectbox("Grupo CelesTrak", ["stations", "starlink", "geo", "active"], index=0)

@st.cache_data(ttl=3600)
def load_satellites(group_name):
    return fetch_tle_by_group(group_name)

try:
    sat_list = load_satellites(group)
    sat_names = [s["name"] for s in sat_list]
    default_idx = sat_names.index("ISS (ZARYA)") if "ISS (ZARYA)" in sat_names else 0
    selected_name = st.sidebar.selectbox("Satélite", sat_names, index=default_idx)

    tle_data = next(s for s in sat_list if s["name"] == selected_name)

    # 4. BARRA LATERAL - SECCIÓN 2: ESTACIÓN TERRESTRE
    st.sidebar.header("2. Estación Terrestre (GS)")

    # Renderizar el componente de geolocalización DENTRO de la barra lateral
    with st.sidebar:
        location = streamlit_geolocation()

    if location and location.get("latitude") is not None:
        st.session_state.gs_lat = location["latitude"]
        st.session_state.gs_lon = location["longitude"]
        if location.get("altitude") is not None:
            st.session_state.gs_alt = location["altitude"]
        st.sidebar.success("📍 Ubicación detectada por GPS/Navegador")

    # Inputs vinculados a session_state
    gs_lat = st.sidebar.number_input("Latitud (°)", key="gs_lat", format="%.4f")
    gs_lon = st.sidebar.number_input("Longitud (°)", key="gs_lon", format="%.4f")
    gs_alt = st.sidebar.number_input("Altitud (m)", key="gs_alt", step=10.0)
    min_el = st.sidebar.slider("Máscara Elevación (°)", min_value=0, max_value=30, value=10, key="min_el_slider")

    # 5. PESTAÑAS PRINCIPALES
    tab1, tab2 = st.tabs(["🌍 Real-time Tracker", "📡 Predicción de Pases & Skyplot"])

    # TAB 1: TRACKER 2D
    with tab1:
        propagator = OrbitPropagator(tle_data["name"], tle_data["line1"], tle_data["line2"])
        state = propagator.get_current_state()
        ground_track = propagator.get_ground_track(minutes_past=50, minutes_future=50)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Latitud", f"{state['latitude']:.4f}°")
        col2.metric("Longitud", f"{state['longitude']:.4f}°")
        col3.metric("Altitud", f"{state['altitude_km']:.2f} km")
        col4.metric("Velocidad", f"{state['speed_km_s']:.2f} km/s")

        fig_map = go.Figure()
        fig_map.add_trace(go.Scattergeo(
            lon=ground_track["longitude"], lat=ground_track["latitude"],
            mode="lines", line=dict(width=2, color="cyan"), name="Ground Track"
        ))
        fig_map.add_trace(go.Scattergeo(
            lon=[state["longitude"]], lat=[state["latitude"]],
            mode="markers+text", marker=dict(size=10, color="red"),
            text=[state["name"]], textposition="top center", name="Satélite"
        ))
        fig_map.add_trace(go.Scattergeo(
            lon=[gs_lon], lat=[gs_lat],
            mode="markers+text", marker=dict(size=10, color="yellow", symbol="star"),
            text=["Estación Terrestre"], textposition="bottom center", name="Ground Station"
        ))
        fig_map.update_layout(
            geo=dict(showland=True, landcolor="rgb(30, 30, 30)", showocean=True, oceancolor="rgb(10, 15, 30)", projection_type="equirectangular"),
            margin=dict(l=0, r=0, t=20, b=0), height=500, template="plotly_dark"
        )
        st.plotly_chart(fig_map, use_container_width=True)

    # TAB 2: PREDICCIÓN DE PASES Y DIAGRAMA POLAR
    with tab2:
        st.subheader(f"Próximos pases sobre la Estación ({gs_lat:.2f}°, {gs_lon:.2f}°)")
        predictor = PassPredictor(tle_data["name"], tle_data["line1"], tle_data["line2"])
        passes = predictor.predict_passes(gs_lat, gs_lon, alt_m=gs_alt, days=3, min_elevation_deg=min_el)

        if not passes:
            st.info("No se han detectado pases en los próximos 3 días con la máscara de elevación seleccionada.")
        else:
            # Formatear tabla de pases
            table_data = []
            for p in passes:
                table_data.append({
                    "AOS (UTC)": p["aos_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "Azimut AOS": f"{p['aos_azimuth']:.1f}°",
                    "Max El (UTC)": p["max_el_time"].strftime("%H:%M:%S"),
                    "Elevación Máx": f"{p['max_elevation']:.1f}°",
                    "Distancia Mín": f"{p['min_range_km']:.1f} km",
                    "LOS (UTC)": p["los_time"].strftime("%H:%M:%S"),
                    "Azimut LOS": f"{p['los_azimuth']:.1f}°",
                    "Duración": f"{int(p['duration_seconds'] // 60)}m {int(p['duration_seconds'] % 60)}s"
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

            # Selección de un pase para ver diagrama polar
            st.subheader("Diagrama Polar de Apuntamiento de Antena (Skyplot)")
            pass_idx = st.selectbox(
                "Selecciona un pase para analizar el barrido", 
                range(len(passes)), 
                format_func=lambda i: f"Pase {i+1}: {table_data[i]['AOS (UTC)']} (Max El: {table_data[i]['Elevación Máx']})"
            )

            selected_pass = passes[pass_idx]
            traj = predictor.get_pass_trajectory(
                gs_lat, gs_lon, selected_pass["aos_time"], selected_pass["los_time"], step_seconds=5, alt_m=gs_alt
            )

            # Figura Polar (Skyplot)
            fig_polar = go.Figure()

            # Trayectoria completa del pase
            fig_polar.add_trace(go.Scatterpolar(
                r=traj["elevation"],
                theta=traj["azimuth"],
                mode="lines+markers",
                marker=dict(size=4, color=traj["range_km"], colorscale="Viridis", showscale=True, colorbar=dict(title="Distancia (km)")),
                line=dict(color="cyan", width=2),
                name="Trayectoria del Pase"
            ))

            # Puntos clave (AOS, Max El, LOS)
            fig_polar.add_trace(go.Scatterpolar(
                r=[traj["elevation"].iloc[0]], theta=[traj["azimuth"].iloc[0]],
                mode="markers+text", marker=dict(size=10, color="green"),
                text=["AOS"], textposition="top center", name="AOS"
            ))

            max_idx = traj["elevation"].idxmax()
            fig_polar.add_trace(go.Scatterpolar(
                r=[traj["elevation"].iloc[max_idx]], theta=[traj["azimuth"].iloc[max_idx]],
                mode="markers+text", marker=dict(size=10, color="yellow"),
                text=["Max El"], textposition="top center", name="Max El"
            ))

            fig_polar.add_trace(go.Scatterpolar(
                r=[traj["elevation"].iloc[-1]], theta=[traj["azimuth"].iloc[-1]],
                mode="markers+text", marker=dict(size=10, color="red"),
                text=["LOS"], textposition="top center", name="LOS"
            ))

            fig_polar.update_layout(
                template="plotly_dark",
                polar=dict(
                    angularaxis=dict(direction="clockwise", rotation=90),  # 0° Arriba (Norte)
                    radialaxis=dict(range=[90, 0], angle=90, dtick=15)    # 90° centro, 0° borde
                ),
                height=600,
                margin=dict(l=40, r=40, t=40, b=40)
            )

            st.plotly_chart(fig_polar, use_container_width=True)

except Exception as e:
    st.error(f"Error al procesar el satélite: {e}")