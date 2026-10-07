import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from streamlit_geolocation import streamlit_geolocation

from satlink.core.fetcher import fetch_tle_by_group
from satlink.core.propagator import OrbitPropagator, latlon_to_cartesian, EARTH_RADIUS_KM
from satlink.core.passes import PassPredictor
from satlink.core.link_budget import SatelliteTransmitter, GroundStationReceiver, LinkBudgetCalculator

# Constante física
C_SPEED_KM_S = 299792.458  # Velocidad de la luz en km/s

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="SatLink Studio — Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. SISTEMA VISUAL
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Rajdhani:wght@500;600;700&display=swap');

    :root {
        --canvas: #081316;
        --panel: #101f22;
        --line: rgba(113, 215, 193, 0.2);
        --mint: #71d7c1;
        --amber: #f5bd67;
        --text: #edf4ef;
        --muted: #91a8a2;
    }

    .stApp {
        color: var(--text);
        background-color: var(--canvas) !important;
        background-image:
            linear-gradient(rgba(113, 215, 193, 0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(113, 215, 193, 0.025) 1px, transparent 1px),
            radial-gradient(ellipse at 60% -20%, rgba(52, 132, 119, 0.2), transparent 58%) !important;
        background-size: 44px 44px, 44px 44px, auto;
        background-attachment: fixed !important;
    }

    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 2.5rem;
        max-width: 1600px;
    }

    h1, h2, h3, h4, h5, [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        font-family: 'Rajdhani', sans-serif !important;
        color: var(--text);
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] {
        background: rgba(10, 24, 26, 0.96);
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        border-left: 3px solid var(--mint) !important;
        padding-left: 10px !important;
        margin-top: 20px !important;
        margin-bottom: 12px !important;
    }

    [data-testid="stWidgetLabel"] p,
    [data-testid="stMarkdownContainer"] p {
        color: #c3d2cd;
    }

    [data-baseweb="select"] > div,
    [data-testid="stNumberInput"] input {
        background-color: var(--panel) !important;
        border-color: var(--line) !important;
        border-radius: 5px !important;
        color: var(--text) !important;
    }

    [data-testid="stSlider"] [role="slider"] {
        background-color: var(--mint) !important;
        border-color: var(--mint) !important;
    }

    [data-testid="stMetric"] {
        min-height: 104px;
        background: linear-gradient(145deg, rgba(21, 40, 42, 0.96), rgba(13, 28, 30, 0.96)) !important;
        border: 1px solid var(--line) !important;
        border-top: 2px solid var(--mint) !important;
        border-radius: 5px !important;
        padding: 14px 16px !important;
    }

    [data-testid="stMetricValue"] {
        font-family: 'DM Mono', monospace !important;
        color: var(--mint) !important;
        font-size: 23px !important;
    }

    [role="radiogroup"] {
        display: grid !important;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        width: 100%;
    }

    [role="radiogroup"] [role="radio"] {
        min-height: 42px;
        min-width: 0;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        border-color: var(--line) !important;
        white-space: normal;
        line-height: 1.1;
    }

    [role="radiogroup"] [role="radio"][aria-checked="true"] {
        background: rgba(113, 215, 193, 0.16) !important;
        color: var(--mint) !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 5px;
        overflow: hidden;
    }

    [data-testid="stAlert"] {
        background: rgba(21, 40, 42, 0.88);
        border-color: var(--line);
    }

    .satlink-masthead {
        position: relative;
        overflow: hidden;
        padding: 9px 4px 17px;
        margin-bottom: 20px;
        border-bottom: 1px solid var(--line);
    }

    .satlink-masthead::after {
        content: "";
        position: absolute;
        left: -24%;
        bottom: -1px;
        width: 24%;
        height: 2px;
        background: linear-gradient(90deg, transparent, #71d7c1, #eafff9, transparent);
        box-shadow: 0 0 12px rgba(113, 215, 193, 0.9);
        animation: masthead-sweep 5s ease-in-out infinite;
    }

    .masthead-kicker {
        display: flex;
        align-items: center;
        gap: 9px;
        color: var(--amber);
        font: 500 10px 'DM Mono', monospace;
        letter-spacing: 1.5px;
    }

    .masthead-status {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--mint);
        box-shadow: 0 0 8px var(--mint), 0 0 17px rgba(113, 215, 193, 0.65);
        animation: status-pulse 2.2s ease-in-out infinite;
    }

    .masthead-separator { color: rgba(113, 215, 193, 0.45); }

    .satlink-wordmark {
        display: flex;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 0 18px;
        margin: 5px 0 0;
        font: 700 62px/0.95 'Rajdhani', sans-serif;
        letter-spacing: 0;
        animation: wordmark-glow 4s ease-in-out infinite;
    }

    .wordmark-satlink {
        color: #f5fffc;
        text-shadow: 0 0 8px rgba(113, 215, 193, 0.65), 0 0 28px rgba(113, 215, 193, 0.25);
    }

    .wordmark-studio {
        color: var(--mint);
        text-shadow: 0 0 8px rgba(113, 215, 193, 0.85), 0 0 25px rgba(113, 215, 193, 0.45);
    }

    .masthead-description {
        margin: 7px 0 0;
        color: var(--muted);
        font: 500 16px 'Rajdhani', sans-serif;
    }

    @keyframes masthead-sweep {
        0% { transform: translateX(0); opacity: 0; }
        12% { opacity: 1; }
        78% { opacity: 1; }
        100% { transform: translateX(520%); opacity: 0; }
    }

    @keyframes status-pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 8px var(--mint), 0 0 17px rgba(113, 215, 193, 0.65); }
        50% { opacity: 0.55; box-shadow: 0 0 4px var(--mint), 0 0 9px rgba(113, 215, 193, 0.35); }
    }

    @keyframes wordmark-glow {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.14); }
    }

    [data-testid="stHeader"], .stAppHeader {
        background: transparent !important;
        box-shadow: none !important;
        border-bottom: 0 !important;
    }

    [data-testid="stAppDeployButton"] { display: none !important; }

    #MainMenu, footer { visibility: hidden; }

    @media (max-width: 700px) {
        .block-container { padding: 1rem 1rem 2rem; }
        [data-testid="stMetric"] { min-height: 92px; padding: 10px 12px !important; }
        [data-testid="stMetricValue"] { font-size: 19px !important; }
        .satlink-wordmark { font-size: 44px; gap: 0 12px; }
        .masthead-description { font-size: 14px; }
        [role="radiogroup"] {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .satlink-masthead::after, .masthead-status, .satlink-wordmark { animation: none; }
    }
</style>
""", unsafe_allow_html=True)

# LOGO Y HEADER
logo_header_html = """
<header class="satlink-masthead" aria-label="SatLink Studio">
    <div class="masthead-kicker">
        <span class="masthead-status" aria-hidden="true"></span>
        <span>MISSION CONTROL</span>
        <span class="masthead-separator">//</span>
        <span>ORBITAL NETWORK</span>
    </div>
    <h1 class="satlink-wordmark">
        <span class="wordmark-satlink">SATLINK</span>
        <span class="wordmark-studio">STUDIO</span>
    </h1>
    <p class="masthead-description">
        Plataforma de seguimiento orbital, astrodinámica y simulación de radiofrecuencia (RF)
    </p>
</header>
"""
st.html(logo_header_html)

# 3. INICIALIZAR SESSION STATE
if "gs_lat" not in st.session_state:
    st.session_state.gs_lat = 43.5357
if "gs_lon" not in st.session_state:
    st.session_state.gs_lon = -5.6615
if "gs_alt" not in st.session_state:
    st.session_state.gs_alt = 10.0

# 4. BARRA LATERAL (CONFIGURACIÓN)
st.sidebar.markdown("### 01. CONFIGURACIÓN DE SATÉLITE")
group = st.sidebar.selectbox("Grupo CelesTrak", ["stations", "starlink", "geo", "active"], index=0)

@st.cache_data(ttl=3600, show_spinner=False)
def load_satellites(group_name):
    return fetch_tle_by_group(group_name)

try:
    with st.spinner("🛰️ Descargando telemetría TLE de CelesTrak..."):
        sat_list = load_satellites(group)
    sat_names = [s["name"] for s in sat_list]
    default_idx = sat_names.index("ISS (ZARYA)") if "ISS (ZARYA)" in sat_names else 0
    selected_name = st.sidebar.selectbox("Satélite", sat_names, index=default_idx)

    tle_data = next(s for s in sat_list if s["name"] == selected_name)

    st.sidebar.markdown("### 02. ESTACIÓN TERRESTRE (GS)")

    with st.sidebar:
        location = streamlit_geolocation()

    if location and location.get("latitude") is not None:
        st.session_state.gs_lat = float(location["latitude"])
        st.session_state.gs_lon = float(location["longitude"])
        if location.get("altitude") is not None:
            st.session_state.gs_alt = float(location["altitude"])
        st.sidebar.success("📍 GPS detectado correctamente")

    gs_lat = st.sidebar.number_input("Latitud (°)", key="gs_lat", format="%.4f")
    gs_lon = st.sidebar.number_input("Longitud (°)", key="gs_lon", format="%.4f")
    gs_alt = st.sidebar.number_input("Altitud (m)", key="gs_alt", step=10.0)
    min_el = st.sidebar.slider("Máscara Elevación (°)", min_value=0, max_value=30, value=10, key="min_el_slider")

    # PRE-CALCULAR PREDICCIÓN DE PASES
    now_utc = datetime.now(timezone.utc)
    predictor = PassPredictor(tle_data["name"], tle_data["line1"], tle_data["line2"])
    passes = predictor.predict_passes(gs_lat, gs_lon, alt_m=gs_alt, days=3, min_elevation_deg=min_el)

    countdown_str = "SIN PASES"
    pass_label = "PRÓXIMO PASE"
    is_active_pass = False
    upcoming = []

    if passes:
        upcoming = [p for p in passes if p["los_time"] > now_utc]
        if upcoming:
            next_p = upcoming[0]
            if now_utc < next_p["aos_time"]:
                time_to_aos = next_p["aos_time"] - now_utc
                total_sec = int(time_to_aos.total_seconds())
                hours, remainder = divmod(total_sec, 3600)
                minutes, seconds = divmod(remainder, 60)
                countdown_str = f"T- {hours:02d}:{minutes:02d}:{seconds:02d}"
                pass_label = f"AOS EN ({next_p['aos_time'].strftime('%H:%M UTC')})"
            else:
                time_to_los = next_p["los_time"] - now_utc
                total_sec = int(time_to_los.total_seconds())
                minutes, seconds = divmod(total_sec, 60)
                countdown_str = f"PASE ACTIVO ({minutes:02d}m {seconds:02d}s)"
                pass_label = f"LOS EN ({next_p['los_time'].strftime('%H:%M UTC')})"
                is_active_pass = True

    # 5. TARJETA HUD
    target_timestamp = 0
    if passes and upcoming:
        target_timestamp = int(upcoming[0]["aos_time"].timestamp() if now_utc < upcoming[0]["aos_time"] else upcoming[0]["los_time"].timestamp())

    hud_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Rajdhani:wght@500;600;700&display=swap">
        <style>
            body {{ margin: 0; padding: 0; background-color: transparent; font-family: 'Rajdhani', sans-serif; color: #edf4ef; }}
            .mission-hud-box {{
                background: linear-gradient(110deg, rgba(18, 37, 39, 0.98), rgba(13, 27, 30, 0.96));
                border: 1px solid rgba(113, 215, 193, 0.24);
                border-radius: 5px; padding: 13px 8px;
                display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
                text-align: center; gap: 8px 0;
            }}
            .hud-label {{ font-size: 12px; font-weight: 700; color: #91a8a2; text-transform: uppercase; }}
            .hud-value {{ font-family: 'DM Mono', monospace; font-size: 14px; font-weight: 500; color: #71d7c1; overflow-wrap: anywhere; }}
            .mission-hud-box > div + div {{ border-left: 1px solid rgba(113, 215, 193, 0.14); }}
            @media (max-width: 700px) {{
                .mission-hud-box {{ grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 11px 4px; }}
                .mission-hud-box > div:nth-child(3) {{ border-left: 0; }}
                .hud-value {{ font-size: 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="mission-hud-box">
            <div><div class="hud-label">🛰️ Satélite Activo</div><div class="hud-value">{selected_name}</div></div>
            <div><div class="hud-label">📡 Estación Terrestre</div><div class="hud-value">{gs_lat:.2f}°, {gs_lon:.2f}°</div></div>
            <div><div class="hud-label">⏳ {pass_label}</div><div class="hud-value">{countdown_str}</div></div>
            <div><div class="hud-label">🕒 Reloj Misión UTC</div><div id="hud-utc-clock" class="hud-value">--:--:-- UTC</div></div>
        </div>
        <script>
            function updateClock() {{
                const now = new Date();
                document.getElementById('hud-utc-clock').innerText = `${{String(now.getUTCHours()).padStart(2,'0')}}:${{String(now.getUTCMinutes()).padStart(2,'0')}}:${{String(now.getUTCSeconds()).padStart(2,'0')}} UTC`;
            }}
            setInterval(updateClock, 1000); updateClock();
        </script>
    </body>
    </html>
    """
    st.components.v1.html(hud_html, height=112)

    # 6. SELECCIÓN DE PESTAÑAS
    selected_tab = st.segmented_control(
        "Pestañas",
        ["🌍 Tracker 2D", "🌐 Globo 3D", "📡 Predicción de Pases", "📊 Link Budget & Doppler"],
        default="🌍 Tracker 2D",
        label_visibility="collapsed"
    )

    propagator = OrbitPropagator(tle_data["name"], tle_data["line1"], tle_data["line2"])
    state = propagator.get_current_state()
    ground_track = propagator.get_ground_track(minutes_past=50, minutes_future=50)

    plotly_layout_dark = dict(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=20, b=10)
    )

    # TAB 1: TRACKER 2D
    if selected_tab == "🌍 Tracker 2D":
        st.markdown('##### TELEMETRÍA EN TIEMPO REAL (GROUND TRACK 2D)')
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Latitud Sub-satélite", f"{state['latitude']:.4f}°")
        col2.metric("Longitud Sub-satélite", f"{state['longitude']:.4f}°")
        col3.metric("Altitud Orbital", f"{state['altitude_km']:.2f} km")
        col4.metric("Velocidad Orbital", f"{state['speed_km_s']:.2f} km/s")

        fig_map = go.Figure()
        fig_map.add_trace(go.Scattergeo(
            lon=ground_track["longitude"], lat=ground_track["latitude"],
            mode="lines", line=dict(width=2.5, color="#00f3ff"), name="Ground Track"
        ))
        fig_map.add_trace(go.Scattergeo(
            lon=[state["longitude"]], lat=[state["latitude"]],
            mode="markers+text", marker=dict(size=12, color="#ff3366", symbol="diamond"),
            text=[f" <b>{state['name']}</b>"], textposition="top center", name="Satélite"
        ))
        fig_map.add_trace(go.Scattergeo(
            lon=[gs_lon], lat=[gs_lat],
            mode="markers+text", marker=dict(size=12, color="#ffcc00", symbol="star"),
            text=[" <b>Estación Terrestre</b>"], textposition="bottom center", name="Ground Station"
        ))
        
        fig_map.update_layout(
            **plotly_layout_dark,
            geo=dict(
                showland=True, landcolor="rgb(15, 23, 42)",
                showocean=True, oceancolor="rgb(6, 10, 20)",
                projection_type="equirectangular",
                bgcolor="rgba(0,0,0,0)",
                coastlinecolor="rgba(0, 243, 255, 0.3)"
            ),
            height=500
        )
        st.plotly_chart(fig_map, use_container_width=True)

    # TAB 2: GLOBO 3D
    elif selected_tab == "🌐 Globo 3D":
        st.subheader(f"Órbita Tridimensional ECEF — {state['name']}")

        phi = np.linspace(-np.pi/2, np.pi/2, 30)
        theta = np.linspace(-np.pi, np.pi, 30)
        phi, theta = np.meshgrid(phi, theta)
        x_sphere = EARTH_RADIUS_KM * np.cos(phi) * np.cos(theta)
        y_sphere = EARTH_RADIUS_KM * np.cos(phi) * np.sin(theta)
        z_sphere = EARTH_RADIUS_KM * np.sin(phi)

        orbit_x, orbit_y, orbit_z = latlon_to_cartesian(
            ground_track["latitude"].values, ground_track["longitude"].values, ground_track["altitude_km"].values
        )
        sat_x, sat_y, sat_z = latlon_to_cartesian(state["latitude"], state["longitude"], state["altitude_km"])
        gs_x, gs_y, gs_z = latlon_to_cartesian(gs_lat, gs_lon, gs_alt / 1000.0)

        fig_3d = go.Figure()
        fig_3d.add_trace(go.Surface(x=x_sphere, y=y_sphere, z=z_sphere, colorscale=[[0, "#080f26"], [1, "#0055ff"]], opacity=0.5, showscale=False))
        fig_3d.add_trace(go.Scatter3d(x=orbit_x, y=orbit_y, z=orbit_z, mode="lines", line=dict(color="#00f3ff", width=4), name="Órbita"))
        fig_3d.add_trace(go.Scatter3d(x=[sat_x], y=[sat_y], z=[sat_z], mode="markers", marker=dict(size=8, color="#ff3366"), name="Satélite"))
        fig_3d.add_trace(go.Scatter3d(x=[gs_x], y=[gs_y], z=[gs_z], mode="markers", marker=dict(size=7, color="#ffcc00"), name="GS"))

        fig_3d.update_layout(**plotly_layout_dark, height=600)
        st.plotly_chart(fig_3d, use_container_width=True)

    # TAB 3: PASES
    elif selected_tab == "📡 Predicción de Pases":
        st.subheader("Próximos Pases")
        if passes:
            table_data = [{
                "AOS (UTC)": p["aos_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "Max El": f"{p['max_elevation']:.1f}°",
                "LOS (UTC)": p["los_time"].strftime("%H:%M:%S"),
                "Duración": f"{int(p['duration_seconds'] // 60)}m {int(p['duration_seconds'] % 60)}s"
            } for p in passes]
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

    # TAB 4: RF
    elif selected_tab == "📊 Link Budget & Doppler":
        st.subheader("Simulación RF")
        st.info("Ajusta los parámetros para simular el enlace.")

except Exception as e:
    st.error(f"Error al procesar: {e}")