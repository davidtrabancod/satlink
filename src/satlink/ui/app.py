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
        --panel-raised: #15282a;
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
        background:
            radial-gradient(ellipse at 0% 0%, rgba(113, 215, 193, 0.1), transparent 36%),
            linear-gradient(180deg, rgba(13, 29, 31, 0.99), rgba(8, 19, 22, 0.99)) !important;
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebarContent"] {
        padding-top: 0 !important;
    }

    [data-testid="stSidebarHeader"] {
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
    }

    [data-testid="stSidebarHeader"] [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarHeader"] [data-testid="stSidebarCollapseButton"] button {
        visibility: visible !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebarHeader"] [data-testid="stSidebarCollapseButton"] button {
        border: 1px solid var(--line) !important;
        border-radius: 5px !important;
        background: rgba(113, 215, 193, 0.07) !important;
        color: var(--mint) !important;
    }

    .sidebar-identity {
        display: flex;
        width: 100%;
        align-items: center;
        padding: 0 0 8px;
        margin: 0 0 4px;
        border-bottom: 1px solid var(--line);
    }

    .sidebar-identity-copy {
        min-width: 0;
    }

    .sidebar-identity-title {
        color: #f5fffc;
        font: 700 23px/1 'Rajdhani', sans-serif;
        white-space: nowrap;
        text-shadow: 0 0 14px rgba(113, 215, 193, 0.35);
    }

    .sidebar-section {
        display: grid;
        grid-template-columns: 32px minmax(0, 1fr) auto;
        align-items: center;
        gap: 9px;
        padding: 0 0 11px;
        margin: 8px 0 13px;
        border-bottom: 1px solid rgba(113, 215, 193, 0.16);
    }

    .sidebar-section-index {
        display: grid;
        width: 32px;
        height: 34px;
        place-items: center;
        border: 1px solid rgba(113, 215, 193, 0.32);
        border-radius: 4px;
        background: rgba(113, 215, 193, 0.08);
        color: var(--mint);
        font: 500 12px 'DM Mono', monospace;
    }

    .sidebar-section-copy {
        display: flex;
        min-width: 0;
        flex-direction: column;
        gap: 2px;
    }

    .sidebar-section-kicker {
        color: var(--muted);
        font: 400 9px/1.15 'DM Mono', monospace;
        text-transform: uppercase;
    }

    .sidebar-section-title {
        color: var(--text);
        font: 700 17px/1.05 'Rajdhani', sans-serif;
        text-transform: uppercase;
    }

    .sidebar-section-badge {
        padding: 3px 5px;
        border: 1px solid rgba(245, 189, 103, 0.3);
        border-radius: 3px;
        color: var(--amber);
        font: 400 9px 'DM Mono', monospace;
    }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #b8c9c3;
        font-size: 15px;
        font-weight: 600;
    }

    [data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"] {
        min-height: 42px;
    }

    [data-testid="stSidebar"] [data-testid="stSelectbox"],
    [data-testid="stSidebar"] [data-testid="stNumberInput"] {
        margin-bottom: 8px;
    }

    [data-testid="stSidebar"] iframe[title="streamlit_geolocation.streamlit_geolocation"] {
        width: 100% !important;
        max-width: 100% !important;
        height: 46px !important;
        border: 0;
    }

    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(iframe[title="streamlit_geolocation.streamlit_geolocation"]) {
        order: 99;
    }

    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has([data-testid="stAlert"]) {
        order: 98;
    }

    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(.gps-confirmation) {
        order: 98;
    }

    .gps-confirmation {
        display: flex;
        align-items: center;
        gap: 9px;
        box-sizing: border-box;
        max-height: 44px;
        padding: 8px 10px;
        overflow: hidden;
        border: 1px solid rgba(113, 215, 193, 0.38);
        border-radius: 5px;
        background: linear-gradient(120deg, rgba(21, 40, 42, 0.98), rgba(13, 28, 30, 0.98));
        color: var(--text);
        font: 600 15px/1.15 'Rajdhani', sans-serif;
        box-shadow: 0 0 14px rgba(113, 215, 193, 0.1);
        animation: gps-confirmation-dismiss 3s ease-in forwards;
    }

    .gps-confirmation-icon {
        display: grid;
        flex: 0 0 20px;
        width: 20px;
        height: 20px;
        place-items: center;
        border: 1px solid rgba(113, 215, 193, 0.35);
        border-radius: 50%;
        background: rgba(113, 215, 193, 0.12);
        color: var(--mint);
        font: 700 12px 'DM Mono', monospace;
    }

    @keyframes gps-confirmation-dismiss {
        0%, 78% { opacity: 1; max-height: 44px; padding-top: 8px; padding-bottom: 8px; margin-top: 0; }
        100% { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; margin-top: -8px; border-color: transparent; transform: translateY(-4px); visibility: hidden; }
    }

    [data-testid="stWidgetLabel"] p {
        color: #d0ded9;
        font-family: 'Rajdhani', sans-serif;
        font-size: 16px;
        font-weight: 600;
    }

    [data-testid="stMarkdownContainer"] p {
        color: #c3d2cd;
    }

    [data-testid="stSelectbox"] [role="group"] {
        background: var(--panel) !important;
        border: 1px solid var(--line) !important;
        border-radius: 5px !important;
        transition: border-color 150ms ease, box-shadow 150ms ease;
    }

    [data-testid="stSelectbox"] [role="group"]:focus-within {
        border-color: var(--mint) !important;
        box-shadow: 0 0 0 1px rgba(113, 215, 193, 0.22);
    }

    [data-testid="stSelectbox"] input {
        background: transparent !important;
        border: 0 !important;
        color: var(--text) !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }

    [data-testid="stSelectbox"] button {
        background: transparent !important;
        border: 0 !important;
        color: var(--mint) !important;
    }

    [role="listbox"] {
        background: var(--panel-raised) !important;
        border: 1px solid var(--line) !important;
        border-radius: 5px !important;
    }

    [role="option"] { color: var(--text) !important; }
    [role="option"][aria-selected="true"] {
        background: rgba(113, 215, 193, 0.15) !important;
        color: var(--mint) !important;
    }

    [data-testid="stNumberInputContainer"] {
        overflow: hidden;
        background: var(--panel) !important;
        border: 1px solid var(--line) !important;
        border-radius: 5px !important;
        transition: border-color 150ms ease, box-shadow 150ms ease;
    }

    [data-testid="stNumberInputContainer"]:focus-within {
        border-color: var(--mint) !important;
        box-shadow: 0 0 0 1px rgba(113, 215, 193, 0.22);
    }

    [data-testid="stNumberInputField"] {
        background: transparent !important;
        border: 0 !important;
        color: var(--text) !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 14px !important;
    }

    [data-testid="stNumberInputStepDown"],
    [data-testid="stNumberInputStepUp"] {
        background: var(--panel-raised) !important;
        border-left: 1px solid var(--line) !important;
        color: var(--mint) !important;
        transition: background 150ms ease;
    }

    [data-testid="stNumberInputStepDown"]:hover,
    [data-testid="stNumberInputStepUp"]:hover {
        background: rgba(113, 215, 193, 0.14) !important;
    }

    [data-testid="stSlider"] [data-testid="stSliderThumbValue"] {
        background: var(--panel-raised) !important;
        border: 1px solid var(--line) !important;
        border-radius: 4px !important;
        color: var(--mint) !important;
        font-family: 'DM Mono', monospace !important;
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
        overflow: hidden;
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 5px;
    }

    [role="radiogroup"] [role="radio"] {
        min-height: 42px;
        min-width: 0;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        background: var(--panel) !important;
        border: 0 !important;
        border-right: 1px solid var(--line) !important;
        border-radius: 0 !important;
        color: #c3d2cd !important;
        white-space: normal;
        line-height: 1.1;
        transition: background 150ms ease, color 150ms ease;
    }

    [role="radiogroup"] [role="radio"][aria-checked="true"] {
        background: rgba(113, 215, 193, 0.14) !important;
        color: var(--mint) !important;
    }

    [role="radiogroup"] [role="radio"]:hover {
        background: rgba(113, 215, 193, 0.08) !important;
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
        font-size: 76px;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(113, 215, 193, 0.75), 0 0 34px rgba(113, 215, 193, 0.38);
    }

    .wordmark-studio {
        color: rgba(113, 215, 193, 0.84);
        font-size: 43px;
        font-weight: 600;
        text-shadow: 0 0 8px rgba(113, 215, 193, 0.38);
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
        .satlink-wordmark { gap: 0 12px; }
        .wordmark-satlink { font-size: 50px; }
        .wordmark-studio { font-size: 30px; }
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
if "gs_using_location" not in st.session_state:
    st.session_state.gs_using_location = False
if "_gs_location_signature" not in st.session_state:
    st.session_state._gs_location_signature = None


def _mark_ground_station_manual():
    st.session_state.gs_using_location = False

# 4. BARRA LATERAL (CONFIGURACIÓN)
st.sidebar.markdown("""
<div class="sidebar-identity">
    <div class="sidebar-identity-copy">
        <span class="sidebar-identity-title">MISSION CONSOLE</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div class="sidebar-section" role="heading" aria-level="3">
    <span class="sidebar-section-index">01</span>
    <span class="sidebar-section-copy">
        <span class="sidebar-section-kicker">Configuración satelital</span>
        <span class="sidebar-section-title">Satélite</span>
    </span>
    <span class="sidebar-section-badge">TLE</span>
</div>
""", unsafe_allow_html=True)
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

    st.sidebar.markdown("""
    <div class="sidebar-section" role="heading" aria-level="3">
        <span class="sidebar-section-index">02</span>
        <span class="sidebar-section-copy">
            <span class="sidebar-section-kicker">Segmento terrestre</span>
            <span class="sidebar-section-title">Estación terrestre</span>
        </span>
        <span class="sidebar-section-badge">GS</span>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        location = streamlit_geolocation()

    if location and location.get("latitude") is not None and location.get("longitude") is not None:
        location_signature = tuple(
            location.get(field)
            for field in ("latitude", "longitude", "altitude", "accuracy", "altitudeAccuracy", "heading", "speed")
        )
        if location_signature != st.session_state._gs_location_signature:
            st.session_state._gs_location_signature = location_signature
            st.session_state.gs_lat = float(location["latitude"])
            st.session_state.gs_lon = float(location["longitude"])
            if location.get("altitude") is not None:
                st.session_state.gs_alt = float(location["altitude"])
            st.session_state.gs_using_location = True
            st.sidebar.markdown("""
            <div class="gps-confirmation" role="status">
                <span class="gps-confirmation-icon" aria-hidden="true">✓</span>
                <span>GPS detectado correctamente</span>
            </div>
            """, unsafe_allow_html=True)

    gs_lat = st.sidebar.number_input(
        "Latitud (°)", key="gs_lat", format="%.4f", on_change=_mark_ground_station_manual
    )
    gs_lon = st.sidebar.number_input(
        "Longitud (°)", key="gs_lon", format="%.4f", on_change=_mark_ground_station_manual
    )
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

    location_button_label = "USANDO UBICACIÓN" if st.session_state.gs_using_location else "USAR MI UBICACIÓN"
    location_button_accessible_label = "Usando ubicación" if st.session_state.gs_using_location else "Usar mi ubicación actual"
    location_button_script = """
    const hookedLocationFrames = new WeakSet();
    const observedLocationDocuments = new WeakSet();

    function styleLocationButton() {
        let locationFrame;
        try {
            locationFrame = window.parent.document.querySelector(
                '[data-testid="stSidebar"] iframe[title="streamlit_geolocation.streamlit_geolocation"]'
            );
        } catch {
            return false;
        }
        if (!locationFrame) return false;

        const applyStyle = () => {
            try {
                const locationDocument = locationFrame.contentDocument;
                if (!locationDocument) return;

                let style = locationDocument.getElementById("satlink-location-style");
                if (!style) {
                    style = locationDocument.createElement("style");
                    style.id = "satlink-location-style";
                    locationDocument.head.appendChild(style);
                }
                style.textContent = `
                    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&display=swap');
                    :root { color-scheme: dark; }
                    html, body, #root { width: 100%; height: 100%; margin: 0; background: transparent !important; }
                    #root { display: flex; align-items: center; }
                    button {
                        box-sizing: border-box;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 9px;
                        width: 100%;
                        height: 42px;
                        padding: 0 12px;
                        border: 1px solid rgba(113, 215, 193, 0.42);
                        border-radius: 5px;
                        background: linear-gradient(120deg, #15282a, #102022);
                        color: #edf4ef;
                        font: 600 14px 'Rajdhani', sans-serif;
                        cursor: pointer;
                        transition: background 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
                    }
                    button::after { content: "${gpsButtonLabel}"; }
                    button[data-gps-using="true"] {
                        border-color: rgba(113, 215, 193, 0.78);
                        background: linear-gradient(120deg, rgba(113, 215, 193, 0.16), rgba(21, 40, 42, 0.98));
                        color: #71d7c1;
                        box-shadow: inset 0 0 12px rgba(113, 215, 193, 0.08);
                    }
                    button:hover {
                        border-color: #71d7c1;
                        background: rgba(113, 215, 193, 0.14);
                        box-shadow: 0 0 12px rgba(113, 215, 193, 0.16);
                    }
                    button:focus-visible { outline: 2px solid #71d7c1; outline-offset: 2px; }
                    button svg { width: 17px; height: 17px; color: #71d7c1; }
                `;

                const labelButton = () => {
                    const currentButton = locationDocument.querySelector("button");
                    if (currentButton) {
                        currentButton.setAttribute("aria-label", gpsButtonAccessibleLabel);
                        currentButton.title = gpsButtonAccessibleLabel;
                        currentButton.setAttribute("data-gps-using", String(gpsUsingLocation));
                    }
                };
                labelButton();
                if (!observedLocationDocuments.has(locationDocument)) {
                    new MutationObserver(labelButton).observe(locationDocument.body, {
                        childList: true,
                        subtree: true
                    });
                    observedLocationDocuments.add(locationDocument);
                }
            } catch {
                return;
            }
        };

        if (!hookedLocationFrames.has(locationFrame)) {
            locationFrame.addEventListener("load", applyStyle);
            hookedLocationFrames.add(locationFrame);
        }
        applyStyle();
        return true;
    }

    const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
    if (sidebar) {
        new MutationObserver(styleLocationButton).observe(sidebar, { childList: true, subtree: true });
    }
    styleLocationButton();
    window.setTimeout(styleLocationButton, 200);
    window.setTimeout(styleLocationButton, 800);
    """

    hud_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Rajdhani:wght@500;600;700&display=swap">
        <style>
            body {{ margin: 0; padding: 0; background-color: transparent; font-family: 'Rajdhani', sans-serif; color: #edf4ef; }}
            .mission-hud-box {{
                padding: 5px 0;
                display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 9px;
            }}
            .hud-cell {{
                position: relative; display: flex; min-width: 0; min-height: 68px;
                flex-direction: column; justify-content: center; align-items: center; gap: 5px;
                padding: 9px 8px; overflow: hidden; text-align: center;
                background: linear-gradient(145deg, rgba(22, 43, 44, 0.96), rgba(13, 28, 30, 0.96));
                border: 1px solid rgba(113, 215, 193, 0.18); border-radius: 5px;
                box-shadow: inset 0 1px rgba(255, 255, 255, 0.025), 0 5px 14px rgba(0, 0, 0, 0.12);
            }}
            .hud-cell::before {{
                content: ""; position: absolute; top: 0; left: 22%; width: 56%; height: 2px;
                background: linear-gradient(90deg, transparent, var(--tile-accent), transparent);
                box-shadow: 0 0 9px var(--tile-accent);
            }}
            .hud-cell:nth-child(1) {{ --tile-accent: #71d7c1; }}
            .hud-cell:nth-child(2) {{ --tile-accent: #f5bd67; }}
            .hud-cell:nth-child(3) {{ --tile-accent: #91b8f2; }}
            .hud-cell:nth-child(4) {{ --tile-accent: #ed9a8d; }}
            .hud-label {{ display: flex; align-items: center; justify-content: center; gap: 5px; color: #d0ded9; font-size: 13px; font-weight: 700; line-height: 1.15; text-transform: uppercase; }}
            .hud-value {{ color: var(--tile-accent); font-family: 'DM Mono', monospace; font-size: 16px; font-weight: 600; line-height: 1.2; overflow-wrap: anywhere; text-shadow: 0 0 10px color-mix(in srgb, var(--tile-accent) 24%, transparent); }}
            @media (max-width: 700px) {{
                .mission-hud-box {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }}
                .hud-cell {{ min-height: 30px; gap: 3px; padding: 5px 6px; }}
                .hud-label {{ font-size: 12px; }}
                .hud-value {{ font-size: 14px; }}
            }}
        </style>
    </head>
    <body>
        <div class="mission-hud-box">
            <div class="hud-cell"><div class="hud-label">🛰️ Satélite Activo</div><div class="hud-value">{selected_name}</div></div>
            <div class="hud-cell"><div class="hud-label">📡 Estación Terrestre</div><div class="hud-value">{gs_lat:.2f}°, {gs_lon:.2f}°</div></div>
            <div class="hud-cell"><div class="hud-label">⏳ {pass_label}</div><div class="hud-value">{countdown_str}</div></div>
            <div class="hud-cell"><div class="hud-label">🕒 Reloj Misión UTC</div><div id="hud-utc-clock" class="hud-value">--:--:-- UTC</div></div>
        </div>
        <script>
            const gpsButtonLabel = "{location_button_label}";
            const gpsButtonAccessibleLabel = "{location_button_accessible_label}";
            const gpsUsingLocation = {str(st.session_state.gs_using_location).lower()};
            {location_button_script}

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