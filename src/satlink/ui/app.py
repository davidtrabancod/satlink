import json
from html import escape
import streamlit as st
import numpy as np
from pathlib import Path
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
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Rajdhani:wght@500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    :root {
        --canvas: #020d1b;
        --panel: #071c2d;
        --panel-raised: #0d2d45;
        --line: rgba(99, 212, 255, 0.24);
        --mint: #67d4ff;
        --amber: #9fc7ff;
        --text: #edf8ff;
        --muted: #9fbad3;
    }

    .stApp {
        color: var(--text);
        background-color: var(--canvas) !important;
        background-image:
            linear-gradient(rgba(103, 212, 255, 0.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(103, 212, 255, 0.035) 1px, transparent 1px),
            radial-gradient(ellipse at 60% -20%, rgba(47, 115, 255, 0.22), transparent 58%) !important;
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
        position: relative;
        overflow: hidden;
        min-height: 104px;
        background: linear-gradient(145deg, rgba(21, 40, 42, 0.96), rgba(13, 28, 30, 0.96)) !important;
        border: 1px solid var(--line) !important;
        border-top: 2px solid var(--mint) !important;
        border-radius: 5px !important;
        padding: 14px 16px !important;
        box-shadow: inset 0 1px rgba(255, 255, 255, 0.025), 0 5px 18px rgba(0, 0, 0, 0.16);
    }

    [data-testid="stMetric"]::before {
        content: "";
        position: absolute;
        z-index: 0;
        top: 0;
        bottom: 0;
        left: -38%;
        width: 28%;
        background: linear-gradient(90deg, transparent, rgba(113, 215, 193, 0.13), transparent);
        transform: skewX(-18deg);
        pointer-events: none;
        animation: telemetry-scan 9s ease-in-out infinite;
    }

    [data-testid="stMetric"]::after {
        content: "LIVE";
        position: absolute;
        z-index: 1;
        top: 10px;
        right: 12px;
        padding: 2px 5px;
        border: 1px solid rgba(113, 215, 193, 0.28);
        border-radius: 3px;
        color: rgba(113, 215, 193, 0.72);
        font: 500 9px 'DM Mono', monospace;
        letter-spacing: 1px;
        pointer-events: none;
        animation: telemetry-live 2.4s ease-in-out infinite;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {
        position: relative;
        z-index: 2;
    }

    [data-testid="stMetricLabel"] {
        display: flex;
        align-items: center;
        gap: 6px;
        padding-right: 48px;
    }

    [data-testid="stMetricLabel"]::before {
        content: "";
        width: 6px;
        height: 6px;
        flex: 0 0 6px;
        border-radius: 50%;
        background: var(--mint);
        box-shadow: 0 0 7px var(--mint);
        animation: telemetry-pulse 1.8s ease-in-out infinite;
    }

    [data-testid="stMetricValue"] {
        font-family: 'DM Mono', monospace !important;
        color: var(--mint) !important;
        font-size: 23px !important;
        text-shadow: 0 0 12px rgba(113, 215, 193, 0.24);
    }

    @keyframes telemetry-scan {
        0%, 18% { transform: translateX(0) skewX(-18deg); opacity: 0; }
        28% { opacity: 1; }
        68% { opacity: 0.72; }
        100% { transform: translateX(520%) skewX(-18deg); opacity: 0; }
    }

    @keyframes telemetry-live {
        0%, 100% { border-color: rgba(113, 215, 193, 0.22); color: rgba(113, 215, 193, 0.58); }
        50% { border-color: rgba(113, 215, 193, 0.68); color: var(--mint); }
    }

    @keyframes telemetry-pulse {
        0%, 100% { opacity: 0.62; transform: scale(0.82); }
        50% { opacity: 1; transform: scale(1.12); }
    }

    [role="radiogroup"] {
        display: grid !important;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        width: 100%;
        overflow: visible;
        gap: 1px;
        padding: 1px;
        background: linear-gradient(135deg, rgba(113, 215, 193, 0.18), rgba(113, 215, 193, 0.04));
        border: 1px solid rgba(113, 215, 193, 0.22);
        border-radius: 7px;
        box-shadow: inset 0 1px rgba(255, 255, 255, 0.035), 0 8px 24px rgba(0, 0, 0, 0.14);
    }

    [role="radiogroup"] [role="radio"] {
        position: relative;
        min-height: 48px;
        min-width: 0;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        letter-spacing: 0.1px;
        background-color: rgba(9, 24, 27, 0.96) !important;
        justify-content: flex-start !important;
        padding-left: 70px !important;
        text-align: left !important;
        background-repeat: no-repeat;
        background-position: 0 50%, -30px center;
        background-size: 150px 100%, 116px 116px;
        background-blend-mode: screen, normal;
        border: 0 !important;
        border-right: 1px solid rgba(113, 215, 193, 0.12) !important;
        border-radius: 0 !important;
        color: #c3d2cd !important;
        white-space: normal;
        line-height: 1.1;
        overflow: hidden;
        isolation: isolate;
        transition: background 180ms ease, color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
    }

    [role="radiogroup"] [role="radio"]:nth-child(1) {
        background-image: radial-gradient(circle at 0 50%, rgba(113, 215, 193, 0.2), transparent 62%), url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none'%3E%3Ccircle cx='32' cy='32' r='23' stroke='%2371d7c1' stroke-width='2' opacity='.62'/%3E%3Cpath d='M32 7v9M32 48v9M7 32h9M48 32h9' stroke='%2371d7c1' stroke-width='2' opacity='.58'/%3E%3Cpath d='m39 24-5 16-9 4 5-16 9-4Z' stroke='%2371d7c1' stroke-width='2.5' opacity='.95'/%3E%3Ccircle cx='32' cy='32' r='3' fill='%2371d7c1'/%3E%3C/svg%3E");
    }

    [role="radiogroup"] [role="radio"]:nth-child(2) {
        background-image: radial-gradient(circle at 0 50%, rgba(113, 215, 193, 0.2), transparent 62%), url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none'%3E%3Ccircle cx='32' cy='32' r='23' stroke='%2371d7c1' stroke-width='2' opacity='.62'/%3E%3Cellipse cx='32' cy='32' rx='10' ry='23' stroke='%2371d7c1' stroke-width='2' opacity='.84'/%3E%3Cpath d='M9 32h46M13 21h38M13 43h38' stroke='%2371d7c1' stroke-width='2' opacity='.7'/%3E%3C/svg%3E");
    }

    [role="radiogroup"] [role="radio"]:nth-child(3) {
        background-image: radial-gradient(circle at 0 50%, rgba(113, 215, 193, 0.2), transparent 62%), url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none'%3E%3Cpath d='M15 48h34M22 48l4-18h12l4 18' stroke='%2371d7c1' stroke-width='2.5' opacity='.82'/%3E%3Cpath d='m22 30 10-9 10 9-10 5-10-5Z' stroke='%2371d7c1' stroke-width='2.5' opacity='.95'/%3E%3Cpath d='M45 14c5 3 8 7 9 12M49 8c7 4 11 10 12 17' stroke='%2371d7c1' stroke-width='2' stroke-linecap='round' opacity='.72'/%3E%3C/svg%3E");
    }

    [role="radiogroup"] [role="radio"]:nth-child(4) {
        background-image: radial-gradient(circle at 0 50%, rgba(113, 215, 193, 0.2), transparent 62%), url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none'%3E%3Cpath d='M13 51V14M13 51h39' stroke='%2371d7c1' stroke-width='2.5' opacity='.72'/%3E%3Cpath d='m19 42 9-11 8 6 12-17' stroke='%2371d7c1' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round' opacity='.96'/%3E%3Ccircle cx='19' cy='42' r='2.5' fill='%2371d7c1'/%3E%3Ccircle cx='28' cy='31' r='2.5' fill='%2371d7c1'/%3E%3Ccircle cx='36' cy='37' r='2.5' fill='%2371d7c1'/%3E%3Ccircle cx='48' cy='20' r='2.5' fill='%2371d7c1'/%3E%3C/svg%3E");
    }

    [role="radiogroup"] [role="radio"] > div {
        position: relative;
        z-index: 2;
        width: 100%;
    }

    [role="radiogroup"] [role="radio"] [data-testid="stIconEmoji"] {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 25px;
        height: 25px;
        margin-right: 7px;
        border: 1px solid rgba(113, 215, 193, 0.18);
        border-radius: 50%;
        background: rgba(113, 215, 193, 0.07);
        filter: saturate(0.72);
        transition: border-color 180ms ease, background 180ms ease, filter 180ms ease, transform 180ms ease;
    }

    [role="radiogroup"] [role="radio"] [data-testid="stMarkdownContainer"] p {
        margin: 0 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        letter-spacing: 0.1px;
    }

    [role="radiogroup"] [role="radio"]:last-child {
        border-right: 0 !important;
    }

    [role="radiogroup"] [role="radio"][aria-checked="true"] {
        background-color: rgba(113, 215, 193, 0.29) !important;
        color: #f1fffb !important;
        filter: brightness(1.16) saturate(1.16);
        transform: scale(1.045);
        z-index: 4;
        box-shadow: inset 0 -4px var(--mint), inset 0 0 0 1px rgba(113, 215, 193, 0.42), inset 0 1px rgba(255, 255, 255, 0.12), 0 0 34px rgba(113, 215, 193, 0.28);
    }

    [role="radiogroup"] [role="radio"]::before {
        position: absolute;
        z-index: 3;
        top: 7px;
        left: 10px;
        color: rgba(113, 215, 193, 0.4);
        font: 500 8px 'DM Mono', monospace;
        letter-spacing: 1px;
        pointer-events: none;
    }

    [role="radiogroup"] [role="radio"]:nth-child(1)::before { content: "01"; }
    [role="radiogroup"] [role="radio"]:nth-child(2)::before { content: "02"; }
    [role="radiogroup"] [role="radio"]:nth-child(3)::before { content: "03"; }
    [role="radiogroup"] [role="radio"]:nth-child(4)::before { content: "04"; }

    [role="radiogroup"] [role="radio"][aria-checked="true"]::after {
        content: "";
        position: absolute;
        top: 0;
        left: 22%;
        right: 22%;
        height: 4px;
        background: var(--mint);
        box-shadow: 0 0 17px rgba(113, 215, 193, 1);
        pointer-events: none;
    }

    [role="radiogroup"] [role="radio"]:hover {
        background-color: rgba(113, 215, 193, 0.11) !important;
        color: #edf4ef !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 5px;
        overflow: hidden;
    }

    [data-testid="stPlotlyChart"] {
        width: 1080px !important;
        max-width: 100% !important;
        box-sizing: border-box;
        padding: 0;
        overflow: hidden;
        border: 0;
        border-radius: 0;
        background: transparent;
        box-shadow: none;
    }

    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"].st-key-tracker-map) {
        padding: 0 !important;
        border-color: rgba(113, 215, 193, 0.28) !important;
        box-shadow: inset 0 0 14px rgba(113, 215, 193, 0.035), 0 0 10px rgba(113, 215, 193, 0.06);
        animation: map-frame-neon 6s ease-in-out infinite;
    }

    [data-testid="stElementContainer"].st-key-globe-3d {
        overflow: hidden;
        border: 1px solid rgba(113, 215, 193, 0.28);
        border-radius: 8px;
        background: radial-gradient(circle at 50% 46%, rgba(19, 70, 78, 0.16), transparent 58%);
        box-shadow: inset 0 0 28px rgba(113, 215, 193, 0.045), 0 0 16px rgba(113, 215, 193, 0.07);
        animation: globe-frame-neon 7s ease-in-out infinite;
    }

    [data-testid="stElementContainer"].st-key-globe-3d [data-testid="stPlotlyChart"] {
        border-radius: 8px;
    }

    @keyframes globe-frame-neon {
        0%, 100% { border-color: rgba(113, 215, 193, 0.22); box-shadow: inset 0 0 28px rgba(113, 215, 193, 0.035), 0 0 10px rgba(113, 215, 193, 0.05); }
        50% { border-color: rgba(113, 215, 193, 0.52); box-shadow: inset 0 0 34px rgba(113, 215, 193, 0.065), 0 0 22px rgba(113, 215, 193, 0.13); }
    }

    @keyframes map-frame-neon {
        0%, 100% {
            border-color: rgba(113, 215, 193, 0.24) !important;
        }
        50% {
            border-color: rgba(113, 215, 193, 0.58) !important;
        }
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
        box-shadow: 0 0 8px var(--mint), 0 0 17px rgba(103, 212, 255, 0.7);
        animation: status-pulse 2.2s ease-in-out infinite;
    }

    .masthead-separator { color: rgba(103, 212, 255, 0.45); }

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
        color: #f5fbff;
        font-size: 76px;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(103, 212, 255, 0.75), 0 0 34px rgba(103, 212, 255, 0.38);
    }

    .wordmark-studio {
        color: rgba(103, 212, 255, 0.88);
        font-size: 43px;
        font-weight: 600;
        text-shadow: 0 0 8px rgba(103, 212, 255, 0.38);
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
        .satlink-masthead::after, .masthead-status, .satlink-wordmark,
        [data-testid="stMetric"]::before, [data-testid="stMetric"]::after,
        [data-testid="stMetricLabel"]::before,
        [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"].st-key-tracker-map),
        [data-testid="stElementContainer"].st-key-globe-3d { animation: none; }
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


@st.cache_data(ttl=3600, show_spinner=False)
def predict_passes_cached(satellite_name, line1, line2, gs_lat, gs_lon, gs_alt, min_el):
    predictor = PassPredictor(satellite_name, line1, line2)
    return predictor.predict_passes(
        gs_lat,
        gs_lon,
        alt_m=gs_alt,
        days=3,
        min_elevation_deg=min_el,
    )


@st.cache_data(ttl=60, show_spinner=False)
def get_ground_track_cached(satellite_name, line1, line2, minutes_past, minutes_future):
    propagator = OrbitPropagator(satellite_name, line1, line2)
    return propagator.get_ground_track(
        minutes_past=minutes_past,
        minutes_future=minutes_future,
    )


@st.cache_data(ttl=86400, show_spinner=False)
def load_world_outline():
    """Load low-resolution country coastlines for the lightweight tracker canvas."""
    outline_path = Path(__file__).with_name("assets") / "world_110m_admin_0_countries.geojson"
    with outline_path.open(encoding="utf-8") as outline_file:
        world = json.load(outline_file)

    polygons = []
    for feature in world.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") == "Polygon":
            countries = [coordinates]
        elif geometry.get("type") == "MultiPolygon":
            countries = coordinates
        else:
            continue
        for country in countries:
            if country and country[0]:
                polygons.append(country[0])
    return polygons


def render_tracker_map(ground_track, state, gs_lat, gs_lon):
    outline = load_world_outline()
    track = [
        [
            int(point_time.timestamp() * 1000),
            float(latitude),
            float(longitude),
        ]
        for point_time, latitude, longitude in zip(
            ground_track["datetime"],
            ground_track["latitude"],
            ground_track["longitude"],
        )
    ]
    payload = {
        "outline": outline,
        "track": track,
        "satelliteName": state["name"],
        "station": [float(gs_lat), float(gs_lon)],
    }

    st.components.v1.html(
        f"""
        <style>
            html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; background: #040c14; }}
            #tracker-stage {{ width: min(100%, 1080px); height: 100%; margin: 0 auto; overflow: hidden; border-radius: 7px; position: relative; background: #040c14; }}
            #tracker-canvas {{ display: block; width: 100%; height: 100%; touch-action: none; cursor: zoom-in; }}
        </style>
        <div id="tracker-stage"><canvas id="tracker-canvas"></canvas></div>
        <script>
            const data = {json.dumps(payload)};
            const stage = document.getElementById('tracker-stage');
            const canvas = document.getElementById('tracker-canvas');
            const ctx = canvas.getContext('2d', {{alpha: false}});
            const base = document.createElement('canvas');
            const baseCtx = base.getContext('2d', {{alpha: false}});
            let landPath = null;
            let graticulePath = null;
            let width = 1080;
            let height = 540;
            let mapScale = 1;
            let mapOffsetX = 0;
            let mapOffsetY = 0;
            let dpr = 1;
            let zoom = 1;
            let offsetX = 0;
            let offsetY = 0;
            const project = (lon, lat) => [
                mapOffsetX + ((lon + 180) / 360) * 1080 * mapScale,
                mapOffsetY + ((90 - lat) / 180) * 540 * mapScale,
            ];

            function drawBase() {{
                base.width = Math.round(width * dpr);
                base.height = Math.round(height * dpr);
                baseCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
                baseCtx.fillStyle = '#040c14';
                baseCtx.fillRect(0, 0, width, height);
                baseCtx.strokeStyle = 'rgba(91, 158, 203, 0.11)';
                baseCtx.lineWidth = 1;
                const graticule = new Path2D();
                for (let lon = -180; lon <= 180; lon += 30) {{
                    const x = project(lon, 0)[0];
                    graticule.moveTo(x, 0); graticule.lineTo(x, height);
                }}
                for (let lat = -90; lat <= 90; lat += 30) {{
                    const y = project(0, lat)[1];
                    graticule.moveTo(0, y); graticule.lineTo(width, y);
                }}
                graticulePath = graticule;
                baseCtx.stroke(graticulePath);

                const land = new Path2D();
                for (const polygon of data.outline) {{
                    if (polygon.length < 3) continue;
                    let started = false;
                    for (const coordinate of polygon) {{
                        const point = project(coordinate[0], coordinate[1]);
                        if (!started) {{ land.moveTo(point[0], point[1]); started = true; }}
                        else land.lineTo(point[0], point[1]);
                    }}
                    land.closePath();
                }}
                baseCtx.fillStyle = '#0d2031';
                landPath = land;
                baseCtx.fill(land, 'evenodd');
                baseCtx.strokeStyle = 'rgba(102, 196, 255, 0.42)';
                baseCtx.lineWidth = 0.65;
                baseCtx.stroke(land);
                return land;
            }}

            function draw() {{
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                ctx.fillStyle = '#040c14';
                ctx.fillRect(0, 0, width, height);
                ctx.setTransform(dpr * zoom, 0, 0, dpr * zoom, dpr * offsetX, dpr * offsetY);
                if (zoom <= 1.001 && offsetX === 0 && offsetY === 0) {{
                    ctx.drawImage(base, 0, 0, width, height);
                }} else {{
                    ctx.fillStyle = '#040c14';
                    ctx.fillRect(0, 0, width, height);
                    ctx.strokeStyle = 'rgba(91, 158, 203, 0.11)';
                    ctx.lineWidth = 1 / zoom;
                    ctx.stroke(graticulePath);
                    ctx.fillStyle = '#0d2031';
                    ctx.fill(landPath, 'evenodd');
                    ctx.strokeStyle = 'rgba(102, 196, 255, 0.42)';
                    ctx.lineWidth = 0.65 / zoom;
                    ctx.stroke(landPath);
                }}

                ctx.strokeStyle = '#6ad8ff';
                ctx.lineWidth = 2.5 / zoom;
                ctx.shadowColor = 'rgba(70, 202, 255, 0.72)';
                ctx.shadowBlur = 7 / zoom;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                ctx.beginPath();
                let drawing = false;
                let previousLongitude = null;
                for (const point of data.track) {{
                    const longitude = point[2];
                    if (previousLongitude !== null && Math.abs(longitude - previousLongitude) > 180) drawing = false;
                    const projected = project(longitude, point[1]);
                    if (drawing) ctx.lineTo(projected[0], projected[1]);
                    else {{ ctx.moveTo(projected[0], projected[1]); drawing = true; }}
                    previousLongitude = longitude;
                }}
                ctx.stroke();
                ctx.shadowBlur = 0;

                const stationPoint = project(data.station[1], data.station[0]);
                ctx.fillStyle = '#ffcc66';
                ctx.shadowColor = 'rgba(255, 198, 92, 0.8)';
                ctx.shadowBlur = 9 / zoom;
                ctx.beginPath();
                ctx.arc(stationPoint[0], stationPoint[1], 5 / zoom, 0, Math.PI * 2);
                ctx.fill();
                ctx.shadowBlur = 0;

                const now = Date.now();
                let left = data.track[0];
                let right = data.track[data.track.length - 1];
                let low = 0, high = data.track.length - 1;
                while (low <= high) {{
                    const middle = (low + high) >> 1;
                    if (data.track[middle][0] <= now) {{ left = data.track[middle]; low = middle + 1; }}
                    else {{ right = data.track[middle]; high = middle - 1; }}
                }}
                const span = Math.max(1, right[0] - left[0]);
                const fraction = Math.max(0, Math.min(1, (now - left[0]) / span));
                let longitudeDelta = right[2] - left[2];
                if (longitudeDelta > 180) longitudeDelta -= 360;
                if (longitudeDelta < -180) longitudeDelta += 360;
                let satelliteLongitude = left[2] + longitudeDelta * fraction;
                if (satelliteLongitude > 180) satelliteLongitude -= 360;
                if (satelliteLongitude < -180) satelliteLongitude += 360;
                const satellitePoint = project(satelliteLongitude, left[1] + (right[1] - left[1]) * fraction);
                ctx.fillStyle = 'rgba(255, 51, 102, 0.24)';
                ctx.shadowColor = '#ff3366';
                ctx.shadowBlur = 14 / zoom;
                ctx.beginPath();
                ctx.arc(satellitePoint[0], satellitePoint[1], 9 / zoom, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#ff6688';
                ctx.beginPath();
                ctx.moveTo(satellitePoint[0], satellitePoint[1] - 6 / zoom);
                ctx.lineTo(satellitePoint[0] + 6 / zoom, satellitePoint[1]);
                ctx.lineTo(satellitePoint[0], satellitePoint[1] + 6 / zoom);
                ctx.lineTo(satellitePoint[0] - 6 / zoom, satellitePoint[1]);
                ctx.closePath();
                ctx.fill();
                ctx.shadowBlur = 0;

                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                ctx.fillStyle = 'rgba(8, 19, 22, 0.86)';
                ctx.fillRect(14, 14, 246, 82);
                ctx.strokeStyle = 'rgba(113, 215, 193, 0.32)';
                ctx.strokeRect(14, 14, 246, 82);
                ctx.font = '12px DM Mono, monospace';
                ctx.fillStyle = '#6ad8ff';
                ctx.beginPath(); ctx.arc(26, 34, 3, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = '#edf4ef';
                ctx.fillText('GROUND TRACK', 36, 38);
                ctx.fillStyle = '#ff6688';
                ctx.beginPath(); ctx.arc(26, 58, 3, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = '#edf4ef';
                ctx.fillText('SATELLITE - ' + data.satelliteName, 36, 62);
                ctx.fillStyle = '#ffcc66';
                ctx.beginPath(); ctx.arc(26, 82, 3, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = '#edf4ef';
                ctx.fillText('GROUND STATION', 36, 86);
            }}

            function clampView() {{
                const mapWidth = 1080 * mapScale;
                const mapHeight = 540 * mapScale;
                const minX = width - (mapOffsetX + mapWidth) * zoom;
                const maxX = -mapOffsetX * zoom;
                const minY = height - (mapOffsetY + mapHeight) * zoom;
                const maxY = -mapOffsetY * zoom;
                offsetX = mapWidth * zoom <= width ? (width - mapWidth * zoom) / 2 - mapOffsetX * zoom : Math.max(minX, Math.min(maxX, offsetX));
                offsetY = mapHeight * zoom <= height ? (height - mapHeight * zoom) / 2 - mapOffsetY * zoom : Math.max(minY, Math.min(maxY, offsetY));
            }}

            function resize() {{
                const bounds = stage.getBoundingClientRect();
                dpr = Math.min(window.devicePixelRatio || 1, 1.5);
                width = Math.max(1, bounds.width);
                height = Math.max(1, bounds.height);
                mapScale = Math.min(width / 1080, height / 540);
                mapOffsetX = (width - 1080 * mapScale) / 2;
                mapOffsetY = (height - 540 * mapScale) / 2;
                clampView();
                canvas.width = Math.max(1, Math.round(bounds.width * dpr));
                canvas.height = Math.max(1, Math.round(bounds.height * dpr));
                drawBase();
                draw();
            }}

            canvas.addEventListener('wheel', event => {{
                event.preventDefault();
                const bounds = canvas.getBoundingClientRect();
                const x = event.clientX - bounds.left, y = event.clientY - bounds.top;
                const nextZoom = Math.max(1, Math.min(8, zoom * (event.deltaY < 0 ? 1.15 : 1 / 1.15)));
                if (nextZoom === 1) {{
                    zoom = 1; offsetX = 0; offsetY = 0;
                }} else {{
                    offsetX = x - (x - offsetX) * (nextZoom / zoom);
                    offsetY = y - (y - offsetY) * (nextZoom / zoom);
                    zoom = nextZoom;
                    clampView();
                }}
                draw();
            }}, {{passive: false}});
            new ResizeObserver(resize).observe(stage);
            resize();
            window.setInterval(draw, 1000);
        </script>
        """,
        height=542,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def build_globe_land_particles(radius_km):
    """Convierte la cartografía local en una textura de partículas 3D."""
    surface_path = Path(__file__).with_name("assets") / "world_50m_surface.npz"
    surface = np.load(surface_path)
    latitudes = surface["latitudes"]
    longitudes = surface["longitudes"]
    mask = surface["mask"] > 0.5
    sampled_mask = mask.copy()
    sampled_mask[::2, 1::2] = False
    sampled_mask[1::2, ::2] = False
    lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing="ij")

    land_latitudes = lat_grid[sampled_mask].astype(float)
    land_longitudes = lon_grid[sampled_mask].astype(float)

    particle_x, particle_y, particle_z = latlon_to_cartesian(
        land_latitudes,
        land_longitudes,
        0,
        r_earth=radius_km * 1.012,
    )

    return particle_x, particle_y, particle_z


try:
    with st.spinner("🛰️ Descargando telemetría TLE de CelesTrak..."):
        sat_list = load_satellites(group)
    if not sat_list:
        st.error(f"No hay datos de satelites disponibles para el grupo '{group}'.")
        st.info("CelesTrak puede limitar temporalmente las consultas. Prueba otro grupo o vuelve a intentarlo despues.")
        st.stop()
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
    passes = predict_passes_cached(
        tle_data["name"],
        tle_data["line1"],
        tle_data["line2"],
        float(gs_lat),
        float(gs_lon),
        float(gs_alt),
        int(min_el),
    )

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
            .hud-cell:nth-child(1) {{ --tile-accent: #7ad6ff; }}
            .hud-cell:nth-child(2) {{ --tile-accent: #a1c9ff; }}
            .hud-cell:nth-child(3) {{ --tile-accent: #7ee3ff; }}
            .hud-cell:nth-child(4) {{ --tile-accent: #c5d9ff; }}
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
        ["Tracker 2D", "Globo 3D", "Predicción de Pases", "Link Budget & Doppler"],
        default="Globo 3D",
        label_visibility="collapsed"
    )

    propagator = OrbitPropagator(tle_data["name"], tle_data["line1"], tle_data["line2"])
    state = propagator.get_current_state()
    ground_track = None
    if selected_tab in {"Tracker 2D", "Globo 3D"}:
        ground_track = get_ground_track_cached(
            tle_data["name"],
            tle_data["line1"],
            tle_data["line2"],
            50,
            50,
        )

    if selected_tab == "Tracker 2D":
        tracker_header_slot = st.empty()
        tracker_metrics_slot = st.empty()
        tracker_header_slot.markdown("##### TELEMETRY - LIVE GROUND TRACK 2D")
        with tracker_metrics_slot.container():
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Latitud sub-satelite", f"{state['latitude']:.4f}º")
            col2.metric("Longitud sub-satelite", f"{state['longitude']:.4f}º")
            col3.metric("Altitud Orbital", f"{state['altitude_km']:.2f} km")
            col4.metric("Velocidad Orbital", f"{state['speed_km_s']:.2f} km/s")

        map_frame = st.container(height=542, border=True)
        with map_frame:
            render_tracker_map(ground_track, state, gs_lat, gs_lon)

        @st.fragment(run_every="10s")
        def refresh_tracker_metrics():
            live_state = propagator.get_current_state()
            with tracker_metrics_slot.container():
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Latitud sub-satelite", f"{live_state['latitude']:.4f}º")
                col2.metric("Longitud sub-satelite", f"{live_state['longitude']:.4f}º")
                col3.metric("Altitud Orbital", f"{live_state['altitude_km']:.2f} km")
                col4.metric("Velocidad Orbital", f"{live_state['speed_km_s']:.2f} km/s")

        refresh_tracker_metrics()
        st.stop()

    # TAB 2: GLOBO 3D
    elif selected_tab == "Globo 3D":
        st.subheader(f"Órbita Tridimensional ECEF — {state['name']}")

        # Keep every land point: the canvas applies its camera rotation and
        # removes the far hemisphere for each animation frame.
        particle_x, particle_y, particle_z = build_globe_land_particles(
            float(EARTH_RADIUS_KM)
        )
        globe_points = np.column_stack([particle_x, particle_y, particle_z])
        orbit_x, orbit_y, orbit_z = latlon_to_cartesian(
            ground_track["latitude"].to_numpy(),
            ground_track["longitude"].to_numpy(),
            ground_track["altitude_km"].to_numpy(),
            r_earth=EARTH_RADIUS_KM,
        )
        satellite_x, satellite_y, satellite_z = latlon_to_cartesian(
            state["latitude"],
            state["longitude"],
            state["altitude_km"],
            r_earth=EARTH_RADIUS_KM,
        )
        land_vectors = np.asarray(globe_points)
        land_vectors /= np.linalg.norm(land_vectors, axis=1, keepdims=True)
        globe_payload = {
            "land": np.round(land_vectors, decimals=6).ravel().tolist(),
            "orbit": np.column_stack([orbit_x, orbit_y, orbit_z]).tolist(),
            "satellite": [float(satellite_x), float(satellite_y), float(satellite_z)],
            "earthRadius": float(EARTH_RADIUS_KM),
        }

        st.components.v1.html(
            f"""
            <style>
                html, body {{
                    width: 100%;
                    height: 100%;
                    margin: 0;
                    overflow: hidden;
                }}
                #satlink-globe-stage {{
                    box-sizing: border-box;
                    width: 100%;
                    height: 100%;
                    border: 1px solid rgba(62, 171, 255, 0.24);
                    border-radius: 8px;
                    background: #020b19;
                    overflow: hidden;
                    position: relative;
                    box-shadow: inset 0 0 40px rgba(0, 101, 202, 0.08), 0 0 30px rgba(0, 106, 255, 0.08);
                }}
            </style>
            <div id="satlink-globe-stage">
                <canvas id="satlink-globe-canvas" style="display:block; width:100%; height:100%; touch-action:none; cursor:grab;"></canvas>
            </div>
            <script>
                const payload = {json.dumps(globe_payload)};
                const stage = document.getElementById('satlink-globe-stage');
                const canvas = document.getElementById('satlink-globe-canvas');
                const ctx = canvas.getContext('2d', {{alpha: false}});
                const landBinCapacity = payload.land.length;
                const landBinCoordinates = [
                    new Float32Array(landBinCapacity),
                    new Float32Array(landBinCapacity),
                    new Float32Array(landBinCapacity),
                ];
                const landBinCounts = [0, 0, 0];
                let w = 0;
                let h = 0;
                let cx = 0;
                let cy = 0;
                let radius = 0;
                let cameraLongitude = -0.35;
                let cameraTilt = -1.15;
                let dragging = false;
                let lastPointerX = 0;
                let lastPointerY = 0;
                let previousFrame = 0;
                const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
                const stars = Array.from({{length: 150}}, (_, i) => {{
                    const a = Math.sin((i + 1) * 127.1) * 43758.5453;
                    const b = Math.sin((i + 1) * 269.5) * 22578.1459;
                    return {{
                        x: ((a - Math.floor(a)) * 0.96 + 0.02),
                        y: ((b - Math.floor(b)) * 0.96 + 0.02),
                        size: 0.5 + (i % 4) * 0.35,
                        alpha: 0.12 + (i % 5) * 0.045,
                    }};
                }});
                const graticuleLines = [];
                for (let latitude = -60; latitude <= 60; latitude += 30) {{
                    const lat = latitude * Math.PI / 180;
                    const points = [];
                    for (let longitude = -180; longitude <= 180; longitude += 3) {{
                        const lon = longitude * Math.PI / 180;
                        points.push([Math.cos(lat) * Math.cos(lon), Math.cos(lat) * Math.sin(lon), Math.sin(lat)]);
                    }}
                    graticuleLines.push(points);
                }}
                for (let longitude = -180; longitude < 180; longitude += 30) {{
                    const lon = longitude * Math.PI / 180;
                    const points = [];
                    for (let latitude = -88; latitude <= 88; latitude += 3) {{
                        const lat = latitude * Math.PI / 180;
                        points.push([Math.cos(lat) * Math.cos(lon), Math.cos(lat) * Math.sin(lon), Math.sin(lat)]);
                    }}
                    graticuleLines.push(points);
                }}

                function resizeCanvas() {{
                    const bounds = stage.getBoundingClientRect();
                    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
                    w = Math.max(1, bounds.width);
                    h = Math.max(1, bounds.height);
                    canvas.width = Math.round(w * dpr);
                    canvas.height = Math.round(h * dpr);
                    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                    cx = w * 0.5;
                    cy = h * 0.51;
                    radius = Math.min(w * 0.38, h * 0.44);
                }}

                function rotatePoint(x, y, z, cosLongitude, sinLongitude, cosTilt, sinTilt) {{
                    const rotatedX = x * cosLongitude - y * sinLongitude;
                    const rotatedY = x * sinLongitude + y * cosLongitude;
                    return {{
                        x: rotatedX,
                        y: rotatedY * cosTilt - z * sinTilt,
                        depth: rotatedY * sinTilt + z * cosTilt,
                    }};
                }}

                function project(x, y, depth) {{
                    return {{
                        x: cx + x * radius,
                        y: cy - y * radius,
                        depth: depth,
                    }};
                }}

                function drawBackground() {{
                    ctx.fillStyle = '#020b19';
                    ctx.fillRect(0, 0, w, h);
                    const vignette = ctx.createRadialGradient(cx, cy, radius * 0.2, cx, cy, Math.max(w, h) * 0.8);
                    vignette.addColorStop(0, 'rgba(7, 37, 73, 0.18)');
                    vignette.addColorStop(1, 'rgba(0, 3, 12, 0.2)');
                    ctx.fillStyle = vignette;
                    ctx.fillRect(0, 0, w, h);

                    for (const star of stars) {{
                        ctx.fillStyle = 'rgba(126, 196, 255, ' + star.alpha + ')';
                        ctx.fillRect(star.x * w, star.y * h, star.size, star.size);
                    }}
                    ctx.strokeStyle = 'rgba(63, 133, 205, 0.045)';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    for (let x = 0; x < w; x += 36) {{
                        ctx.moveTo(x, 0);
                        ctx.lineTo(x, h);
                    }}
                    for (let y = 0; y < h; y += 36) {{
                        ctx.moveTo(0, y);
                        ctx.lineTo(w, y);
                    }}
                    ctx.stroke();
                }}

                function drawSphere() {{
                    const halo = ctx.createRadialGradient(cx, cy, radius * 0.82, cx, cy, radius * 1.32);
                    halo.addColorStop(0, 'rgba(0, 163, 255, 0.34)');
                    halo.addColorStop(0.42, 'rgba(0, 111, 255, 0.2)');
                    halo.addColorStop(1, 'rgba(0, 54, 200, 0)');
                    ctx.fillStyle = halo;
                    ctx.beginPath();
                    ctx.arc(cx, cy, radius * 1.32, 0, Math.PI * 2);
                    ctx.fill();

                    const ocean = ctx.createRadialGradient(
                        cx - radius * 0.34, cy - radius * 0.38, radius * 0.04,
                        cx + radius * 0.12, cy + radius * 0.16, radius * 1.16
                    );
                    ocean.addColorStop(0, '#123b66');
                    ocean.addColorStop(0.38, '#08274b');
                    ocean.addColorStop(0.78, '#04152f');
                    ocean.addColorStop(1, '#010817');
                    ctx.fillStyle = ocean;
                    ctx.beginPath();
                    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                    ctx.fill();
                }}

                function drawGraticule(cosLongitude, sinLongitude, cosTilt, sinTilt) {{
                    const detailStride = dragging ? 2 : 1;
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(cx, cy, radius * 0.998, 0, Math.PI * 2);
                    ctx.clip();
                    ctx.lineWidth = 0.7;
                    ctx.strokeStyle = 'rgba(74, 190, 255, 0.22)';
                    ctx.beginPath();

                    function traceLine(points) {{
                        let drawing = false;
                        for (let index = 0; index < points.length; index += detailStride) {{
                            const point = points[index];
                            const p = rotatePoint(point[0], point[1], point[2], cosLongitude, sinLongitude, cosTilt, sinTilt);
                            if (p.depth <= 0) {{
                                drawing = false;
                                continue;
                            }}
                            const q = project(p.x, p.y, p.depth);
                            if (!drawing) {{
                                ctx.moveTo(q.x, q.y);
                                drawing = true;
                            }} else {{
                                ctx.lineTo(q.x, q.y);
                            }}
                        }}
                    }}

                    for (let index = 0; index < graticuleLines.length; index += detailStride) {{
                        traceLine(graticuleLines[index]);
                    }}
                    ctx.stroke();
                    ctx.restore();
                }}

                function drawLand(cosLongitude, sinLongitude, cosTilt, sinTilt) {{
                    landBinCounts.fill(0);
                    for (let index = 0; index < payload.land.length; index += 3) {{
                        const x = payload.land[index];
                        const y = payload.land[index + 1];
                        const z = payload.land[index + 2];
                        const rotatedX = x * cosLongitude - y * sinLongitude;
                        const rotatedY = x * sinLongitude + y * cosLongitude;
                        const depth = rotatedY * sinTilt + z * cosTilt;
                        if (depth <= 0) continue;

                        const bin = Math.min(2, Math.floor(depth * 3));
                        const binIndex = landBinCounts[bin];
                        const coordinates = landBinCoordinates[bin];
                        coordinates[binIndex] = cx + rotatedX * radius;
                        coordinates[binIndex + 1] = cy - (rotatedY * cosTilt - z * sinTilt) * radius;
                        coordinates[binIndex + 2] = 0.72 + depth * 1.12;
                        landBinCounts[bin] += 3;
                    }}

                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(cx, cy, radius * 0.999, 0, Math.PI * 2);
                    ctx.clip();
                    ctx.globalCompositeOperation = 'screen';
                    const colors = [
                        'rgba(23, 122, 255, 0.68)',
                        'rgba(38, 166, 255, 0.86)',
                        'rgba(126, 232, 255, 1)',
                    ];
                    for (let bin = 0; bin < landBinCoordinates.length; bin += 1) {{
                        const coordinates = landBinCoordinates[bin];
                        const count = landBinCounts[bin];
                        ctx.beginPath();
                        for (let index = 0; index < count; index += 3) {{
                            const x = coordinates[index];
                            const y = coordinates[index + 1];
                            const haloSize = coordinates[index + 2] * 2.1;
                            if (haloSize > 2) {{
                                ctx.rect(x - haloSize, y - haloSize, haloSize * 2, haloSize * 2);
                            }} else {{
                                ctx.moveTo(x + haloSize, y);
                                ctx.arc(x, y, haloSize, 0, Math.PI * 2);
                            }}
                        }}
                        ctx.fillStyle = 'rgba(0, 153, 255, 0.18)';
                        ctx.fill();

                        ctx.shadowBlur = 0;
                        ctx.beginPath();
                        for (let index = 0; index < count; index += 3) {{
                            const x = coordinates[index];
                            const y = coordinates[index + 1];
                            const size = coordinates[index + 2];
                            ctx.moveTo(x + size, y);
                            ctx.arc(x, y, size, 0, Math.PI * 2);
                        }}
                        ctx.fillStyle = colors[bin];
                        ctx.fill();
                    }}
                    ctx.shadowBlur = 0;
                    ctx.restore();
                }}

                function drawOrbit(cosLongitude, sinLongitude, cosTilt, sinTilt) {{
                    ctx.save();
                    ctx.globalCompositeOperation = 'screen';
                    const orbitPaths = {{front: [], rear: []}};
                    let currentPath = null;
                    let currentSide = null;
                    let previous = null;

                    function rotateOrbitPoint(point) {{
                        return rotatePoint(
                            point[0] / payload.earthRadius,
                            point[1] / payload.earthRadius,
                            point[2] / payload.earthRadius,
                            cosLongitude, sinLongitude, cosTilt, sinTilt
                        );
                    }}

                    function isOccluded(point) {{
                        return point.depth < 0 && Math.hypot(point.x, point.y) < 1;
                    }}

                    function interpolatePoint(start, end, amount) {{
                        return rotateOrbitPoint([
                            start[0] + (end[0] - start[0]) * amount,
                            start[1] + (end[1] - start[1]) * amount,
                            start[2] + (end[2] - start[2]) * amount,
                        ]);
                    }}

                    function findBoundary(start, end, occlusionBoundary) {{
                        let low = 0;
                        let high = 1;
                        const startPoint = rotateOrbitPoint(start);
                        const startIsBoundarySide = occlusionBoundary
                            ? isOccluded(startPoint)
                            : startPoint.depth < 0;
                        for (let iteration = 0; iteration < 24; iteration += 1) {{
                            const middle = (low + high) / 2;
                            const point = interpolatePoint(start, end, middle);
                            const isBoundarySide = occlusionBoundary
                                ? isOccluded(point)
                                : point.depth < 0;
                            if (isBoundarySide === startIsBoundarySide) {{
                                low = middle;
                            }} else {{
                                high = middle;
                            }}
                        }}
                        return interpolatePoint(start, end, (low + high) / 2);
                    }}

                    function addPoint(point) {{
                        const side = point.depth < 0 ? 'rear' : 'front';
                        if (!currentPath || currentSide !== side) {{
                            currentPath = [];
                            orbitPaths[side].push(currentPath);
                            currentSide = side;
                        }}
                        currentPath.push(project(point.x, point.y, point.depth));
                    }}

                    function finishPath() {{
                        currentPath = null;
                        currentSide = null;
                    }}

                    function processPoint(point, source) {{
                        if (!previous) {{
                            if (!isOccluded(point)) addPoint(point);
                            previous = {{point, source}};
                            return;
                        }}

                        const wasOccluded = isOccluded(previous.point);
                        const nowOccluded = isOccluded(point);
                        const previousIsRear = previous.point.depth < 0;
                        const nowIsRear = point.depth < 0;

                        if (!wasOccluded && !nowOccluded && previousIsRear !== nowIsRear) {{
                            const boundary = findBoundary(previous.source, source, false);
                            if (currentPath) {{
                                currentPath.push(project(boundary.x, boundary.y, boundary.depth));
                            }}
                            finishPath();
                            addPoint(boundary);
                            addPoint(point);
                        }} else if (!wasOccluded && nowOccluded) {{
                            const boundary = findBoundary(previous.source, source, true);
                            if (currentPath) {{
                                currentPath.push(project(boundary.x, boundary.y, boundary.depth));
                            }}
                            finishPath();
                        }} else if (wasOccluded && !nowOccluded) {{
                            const boundary = findBoundary(previous.source, source, true);
                            addPoint(boundary);
                            addPoint(point);
                        }} else if (!nowOccluded) {{
                            addPoint(point);
                        }} else {{
                            finishPath();
                        }}

                        previous = {{point, source}};
                    }}

                    for (let index = 0; index < payload.orbit.length - 1; index += 1) {{
                        const start = payload.orbit[index];
                        const end = payload.orbit[index + 1];
                        const subdivisions = dragging ? 2 : 8;
                        for (let step = 0; step <= subdivisions; step += 1) {{
                            if (index > 0 && step === 0) continue;
                            const amount = step / subdivisions;
                            const source = [
                                start[0] + (end[0] - start[0]) * amount,
                                start[1] + (end[1] - start[1]) * amount,
                                start[2] + (end[2] - start[2]) * amount,
                            ];
                            processPoint(rotateOrbitPoint(source), source);
                        }}
                    }}

                    ctx.lineCap = 'round';
                    ctx.lineJoin = 'round';
                    ctx.lineWidth = 2;
                    ctx.strokeStyle = 'rgba(30, 176, 255, 0.92)';
                    ctx.shadowColor = 'rgba(0, 174, 255, 0.96)';
                    ctx.shadowBlur = 13;
                    for (const side of ['rear', 'front']) {{
                        for (const path of orbitPaths[side]) {{
                            if (path.length < 2) continue;
                            ctx.beginPath();
                            ctx.moveTo(path[0].x, path[0].y);
                            for (let index = 1; index < path.length; index += 1) {{
                                ctx.lineTo(path[index].x, path[index].y);
                            }}
                            ctx.stroke();
                        }}
                    }}
                    ctx.shadowBlur = 0;

                    const point = payload.satellite;
                    const p = rotatePoint(
                        point[0] / payload.earthRadius,
                        point[1] / payload.earthRadius,
                        point[2] / payload.earthRadius,
                        cosLongitude, sinLongitude, cosTilt, sinTilt
                    );
                    if (!isOccluded(p)) {{
                        const q = project(p.x, p.y, p.depth);
                        ctx.beginPath();
                        ctx.arc(q.x, q.y, 7, 0, Math.PI * 2);
                        ctx.fillStyle = 'rgba(35, 174, 255, 0.3)';
                        ctx.shadowColor = '#35c7ff';
                        ctx.shadowBlur = 16;
                        ctx.fill();
                        ctx.beginPath();
                        ctx.arc(q.x, q.y, 3.4, 0, Math.PI * 2);
                        ctx.fillStyle = '#e8fbff';
                        ctx.shadowBlur = 8;
                        ctx.fill();
                    }}
                    ctx.restore();
                }}

                function render(timestamp) {{
                    const frameInterval = dragging ? 0 : 30;
                    if (previousFrame && timestamp - previousFrame < frameInterval) {{
                        if (!reducedMotion) window.requestAnimationFrame(render);
                        return;
                    }}
                    if (previousFrame && !dragging && !reducedMotion && timestamp - previousFrame > 32) {{
                        cameraLongitude += 0.000045 * (timestamp - previousFrame);
                    }}
                    previousFrame = timestamp;
                    const cosLongitude = Math.cos(cameraLongitude);
                    const sinLongitude = Math.sin(cameraLongitude);
                    const cosTilt = Math.cos(cameraTilt);
                    const sinTilt = Math.sin(cameraTilt);

                    drawBackground();
                    drawSphere();
                    drawGraticule(cosLongitude, sinLongitude, cosTilt, sinTilt);
                    drawLand(cosLongitude, sinLongitude, cosTilt, sinTilt);
                    drawOrbit(cosLongitude, sinLongitude, cosTilt, sinTilt);

                    const atmosphere = ctx.createRadialGradient(
                        cx - radius * 0.35, cy - radius * 0.4, radius * 0.68,
                        cx, cy, radius * 1.03
                    );
                    atmosphere.addColorStop(0, 'rgba(84, 194, 255, 0)');
                    atmosphere.addColorStop(0.84, 'rgba(26, 151, 255, 0.08)');
                    atmosphere.addColorStop(0.97, 'rgba(87, 220, 255, 0.68)');
                    atmosphere.addColorStop(1, 'rgba(22, 124, 255, 0.16)');
                    ctx.fillStyle = atmosphere;
                    ctx.beginPath();
                    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.strokeStyle = 'rgba(137, 235, 255, 0.94)';
                    ctx.lineWidth = 1.5;
                    ctx.shadowColor = 'rgba(0, 170, 255, 1)';
                    ctx.shadowBlur = 19;
                    ctx.stroke();
                    ctx.shadowBlur = 0;

                    if (!reducedMotion) window.requestAnimationFrame(render);
                }}

                canvas.addEventListener('pointerdown', (event) => {{
                    dragging = true;
                    lastPointerX = event.clientX;
                    lastPointerY = event.clientY;
                    canvas.setPointerCapture(event.pointerId);
                    canvas.style.cursor = 'grabbing';
                }});
                canvas.addEventListener('pointermove', (event) => {{
                    if (!dragging) return;
                    cameraLongitude += (event.clientX - lastPointerX) * 0.008;
                    cameraTilt = Math.max(-1.35, Math.min(1.35, cameraTilt + (event.clientY - lastPointerY) * 0.006));
                    lastPointerX = event.clientX;
                    lastPointerY = event.clientY;
                    if (reducedMotion) render(performance.now());
                }});
                canvas.addEventListener('pointerup', () => {{
                    dragging = false;
                    canvas.style.cursor = 'grab';
                    previousFrame = 0;
                    if (reducedMotion) render(performance.now());
                }});
                canvas.addEventListener('pointercancel', () => {{
                    dragging = false;
                    canvas.style.cursor = 'grab';
                    previousFrame = 0;
                    if (reducedMotion) render(performance.now());
                }});
                new ResizeObserver(() => {{
                    resizeCanvas();
                    if (reducedMotion) render(performance.now());
                }}).observe(stage);
                resizeCanvas();
                window.requestAnimationFrame(render);
            </script>
            """,
            height=620,
        )

    # TAB 3: PASES
    elif selected_tab == "Predicción de Pases":
        st.subheader("Próximos Pases")
        if passes:
            table_data = [{
                "AOS (UTC)": p["aos_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "Max El": f"{p['max_elevation']:.1f}°",
                "LOS (UTC)": p["los_time"].strftime("%H:%M:%S"),
                "Duración": f"{int(p['duration_seconds'] // 60)}m {int(p['duration_seconds'] % 60)}s"
            } for p in passes]
            rows_html = "".join(
                "<tr{}><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    " class='next-pass'" if index == 0 else "",
                    *(escape(str(value)) for value in row.values()),
                )
                for index, row in enumerate(table_data)
            )
            st.markdown(
                """
                <style>
                    .pass-table-wrap { overflow-x: auto; border: 1px solid rgba(103,212,255,.2); border-radius: 8px; }
                    table.pass-table { width: 100%; border-collapse: collapse; background: rgba(4,18,34,.82); }
                    .pass-table th { padding: 13px 16px; color: #9fbad3; background: rgba(24,61,91,.55); font: 600 12px 'DM Mono', monospace; text-align: left; text-transform: uppercase; letter-spacing: .06em; }
                    .pass-table td { padding: 13px 16px; color: #edf8ff; border-top: 1px solid rgba(103,212,255,.1); font: 500 14px 'DM Mono', monospace; }
                    .pass-table tr:nth-child(even) td { background: rgba(27,67,98,.16); }
                    .pass-table tr.next-pass td { color: #80e8ff; background: rgba(25,117,155,.17); }
                    .pass-table td:nth-child(2) { color: #ffc66d; }
                    @media (max-width: 640px) { .pass-table th, .pass-table td { padding: 10px 9px; font-size: 12px; } }
                </style>
                <div class="pass-table-wrap"><table class="pass-table">
                    <thead><tr><th>AOS (UTC)</th><th>Max El</th><th>LOS (UTC)</th><th>Duración</th></tr></thead>
                    <tbody>
                """
                + rows_html
                + "</tbody></table></div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("No hay pases visibles para los parámetros actuales.")

    # TAB 4: RF
    elif selected_tab == "Link Budget & Doppler":
        st.subheader("Simulación RF")
        st.info("Ajusta los parámetros para simular el enlace.")

except Exception as e:
    st.error(f"Error al procesar: {e}")
