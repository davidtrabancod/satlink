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

# 2. ESTILO CSS CUSTOMIZADO (JERARQUÍA VISUAL & BANNER HUD COMPACTO)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Rajdhani:wght@500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Rajdhani', sans-serif !important;
    }

    h1 {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 900 !important;
        letter-spacing: 2px !important;
        background: linear-gradient(90deg, #00f3ff 0%, #0088ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px !important;
    }

    h2, h3, h4 {
        font-family: 'Orbitron', sans-serif !important;
        color: #00f3ff !important;
        letter-spacing: 1.2px;
    }

    /* Modificar etiquetas del Sidebar */
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-size: 15px !important;
    }

    /* CONTENEDOR HUD DE MISIÓN COMPACTO */
    .mission-hud-box {
        background: linear-gradient(135deg, rgba(13, 22, 45, 0.9) 0%, rgba(8, 14, 28, 0.95) 100%);
        border: 1px solid rgba(0, 243, 255, 0.35);
        border-radius: 10px;
        padding: 12px 20px;
        margin-top: 10px;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), inset 0 0 15px rgba(0, 243, 255, 0.05);
    }

    .hud-label {
        font-family: 'Rajdhani', sans-serif;
        font-size: 12px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .hud-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: #00f3ff;
        text-shadow: 0 0 10px rgba(0, 243, 255, 0.4);
    }

    .hud-value-highlight {
        font-family: 'Orbitron', sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: #ff3366;
        text-shadow: 0 0 10px rgba(255, 51, 102, 0.4);
    }

    /* Pestañas (Tabs) */
    button[data-baseweb="tab"] {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 14px !important;
        color: #cbd5e1 !important;
        padding: 10px 20px !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #00f3ff !important;
        border-bottom-color: #00f3ff !important;
    }

    /* Botones Neón */
    .stButton > button, .stDownloadButton > button {
        font-family: 'Orbitron', sans-serif !important;
        background: linear-gradient(135deg, #00f3ff 0%, #0066ff 100%) !important;
        color: #020617 !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 6px !important;
        box-shadow: 0 0 15px rgba(0, 243, 255, 0.4) !important;
    }

    #MainMenu, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ENCABEZADO PRINCIPAL
st.title("🛰️ SatLink Studio — Mission Control")
st.caption("⚡ Plataforma de seguimiento orbital, astrodinámica y simulación de radiofrecuencia (RF)")

# 3. INICIALIZAR SESSION STATE
if "gs_lat" not in st.session_state:
    st.session_state.gs_lat = 43.5357
if "gs_lon" not in st.session_state:
    st.session_state.gs_lon = -5.6615
if "gs_alt" not in st.session_state:
    st.session_state.gs_alt = 10.0

# 4. BARRA LATERAL - SECCIÓN 1: SATÉLITE
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

    # BARRA LATERAL - SECCIÓN 2: ESTACIÓN TERRESTRE
    st.sidebar.header("2. Estación Terrestre (GS)")

    with st.sidebar:
        location = streamlit_geolocation()

    if location and location.get("latitude") is not None:
        st.session_state.gs_lat = location["latitude"]
        st.session_state.gs_lon = location["longitude"]
        if location.get("altitude") is not None:
            st.session_state.gs_alt = location["altitude"]
        st.sidebar.success("📍 GPS detectado correctamente")

    gs_lat = st.sidebar.number_input("Latitud (°)", key="gs_lat", format="%.4f")
    gs_lon = st.sidebar.number_input("Longitud (°)", key="gs_lon", format="%.4f")
    gs_alt = st.sidebar.number_input("Altitud (m)", key="gs_alt", step=10.0)
    min_el = st.sidebar.slider("Máscara Elevación (°)", min_value=0, max_value=30, value=10, key="min_el_slider")

    # PRE-CALCULAR PREDICCIÓN DE PASES Y CUENTA ATRÁS
    now_utc = datetime.now(timezone.utc)
    predictor = PassPredictor(tle_data["name"], tle_data["line1"], tle_data["line2"])
    passes = predictor.predict_passes(gs_lat, gs_lon, alt_m=gs_alt, days=3, min_elevation_deg=min_el)

    countdown_str = "SIN PASES"
    pass_label = "PRÓXIMO PASE"
    is_active_pass = False

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

    # 5. TARJETA HUD GENERAL DE MISIÓN (NUEVO ORDEN: SATÉLITE -> GS -> CONTADOR AOS -> UTC)
    val_class = "hud-value-highlight" if is_active_pass else "hud-value"
    st.markdown(f"""
    <div class="mission-hud-box">
        <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
            <div>
                <div class="hud-label">🛰️ Satélite Activo</div>
                <div class="hud-value">{selected_name}</div>
            </div>
            <div style="border-left: 1px solid rgba(0, 243, 255, 0.2); height: 30px;"></div>
            <div>
                <div class="hud-label">📡 Estación Terrestre</div>
                <div class="hud-value">{gs_lat:.2f}°, {gs_lon:.2f}°</div>
            </div>
            <div style="border-left: 1px solid rgba(0, 243, 255, 0.2); height: 30px;"></div>
            <div>
                <div class="hud-label">⏳ {pass_label}</div>
                <div class="{val_class}">{countdown_str}</div>
            </div>
            <div style="border-left: 1px solid rgba(0, 243, 255, 0.2); height: 30px;"></div>
            <div>
                <div class="hud-label">🕒 Reloj Misión UTC</div>
                <div class="hud-value">{now_utc.strftime('%H:%M:%S UTC')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 6. PESTAÑAS PRINCIPALES DE VISTA
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Tracker 2D", 
        "🌐 Globo 3D", 
        "📡 Predicción de Pases", 
        "📊 Link Budget & Doppler"
    ])

    propagator = OrbitPropagator(tle_data["name"], tle_data["line1"], tle_data["line2"])
    state = propagator.get_current_state()
    ground_track = propagator.get_ground_track(minutes_past=50, minutes_future=50)

    # TAB 1: TRACKER 2D
    with tab1:
        st.markdown("##### 📍 Telemetría Instantánea del Satélite (Ground Track 2D)")
        
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
            mode="markers+text", marker=dict(size=14, color="#ff3366", symbol="diamond"),
            text=[f" <b>{state['name']}</b>"], textposition="top center", name="Satélite"
        ))
        fig_map.add_trace(go.Scattergeo(
            lon=[gs_lon], lat=[gs_lat],
            mode="markers+text", marker=dict(size=14, color="#ffcc00", symbol="star"),
            text=[" <b>Estación Terrestre</b>"], textposition="bottom center", name="Ground Station"
        ))
        fig_map.update_layout(
            geo=dict(
                showland=True, landcolor="rgb(20, 28, 48)",
                showocean=True, oceancolor="rgb(8, 12, 22)",
                projection_type="equirectangular"
            ),
            margin=dict(l=0, r=0, t=10, b=0), height=530, template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_map, use_container_width=True)

    # TAB 2: GLOBO 3D
    with tab2:
        st.subheader(f"Órbita Tridimensional ECEF — {state['name']}")

        phi = np.linspace(-np.pi/2, np.pi/2, 35)
        theta = np.linspace(-np.pi, np.pi, 35)
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

        fig_3d.add_trace(go.Surface(
            x=x_sphere, y=y_sphere, z=z_sphere,
            colorscale=[[0, "#0a192f"], [1, "#1e3a8a"]],
            opacity=0.45, showscale=False,
            lighting=dict(ambient=0.8, diffuse=0.6), name="Tierra"
        ))

        fig_3d.add_trace(go.Scatter3d(
            x=orbit_x, y=orbit_y, z=orbit_z,
            mode="lines", line=dict(color="#00f3ff", width=5), name="Órbita (±50 min)"
        ))

        fig_3d.add_trace(go.Scatter3d(
            x=[sat_x], y=[sat_y], z=[sat_z],
            mode="markers+text", marker=dict(size=9, color="#ff3366", symbol="diamond"),
            text=[f"  {state['name']}"], textposition="top right", name="Satélite"
        ))

        fig_3d.add_trace(go.Scatter3d(
            x=[gs_x], y=[gs_y], z=[gs_z],
            mode="markers+text", marker=dict(size=8, color="#ffcc00", symbol="circle"),
            text=["  Estación Terrestre"], textposition="top right", name="Ground Station"
        ))

        fig_3d.add_trace(go.Scatter3d(
            x=[gs_x, sat_x], y=[gs_y, sat_y], z=[gs_z, sat_z],
            mode="lines", line=dict(color="#ffcc00", width=3, dash="dash"), name="Línea de Vista (LOS)"
        ))

        fig_3d.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            scene=dict(
                xaxis=dict(title="X (km)", showbackground=False, gridcolor="#1e293b"),
                yaxis=dict(title="Y (km)", showbackground=False, gridcolor="#1e293b"),
                zaxis=dict(title="Z (km)", showbackground=False, gridcolor="#1e293b"),
                aspectmode="data"
            ),
            height=650, margin=dict(l=0, r=0, t=20, b=0)
        )

        st.plotly_chart(fig_3d, use_container_width=True)

    # TAB 3: PREDICCIÓN DE PASES & SKYPLOT
    with tab3:
        st.subheader(f"Próximos pases sobre la Estación ({gs_lat:.2f}°, {gs_lon:.2f}°)")

        if not passes:
            st.info("No se han detectado pases en los próximos 3 días con la máscara de elevación seleccionada.")
        else:
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
            
            df_passes = pd.DataFrame(table_data)
            st.dataframe(df_passes, use_container_width=True)

            st.download_button(
                label="📥 Exportar Tabla de Pases (CSV)",
                data=df_passes.to_csv(index=False).encode('utf-8'),
                file_name=f"pases_{tle_data['name'].replace(' ', '_')}.csv",
                mime="text/csv"
            )

            st.subheader("Diagrama Polar de Apuntamiento de Antena (Skyplot)")
            pass_idx = st.selectbox(
                "Selecciona un pase para analizar el barrido de antena", 
                range(len(passes)), 
                format_func=lambda i: f"Pase {i+1}: {table_data[i]['AOS (UTC)']} (Max El: {table_data[i]['Elevación Máx']})",
                key="skyplot_pass_select"
            )

            selected_pass = passes[pass_idx]
            traj = predictor.get_pass_trajectory(
                gs_lat, gs_lon, selected_pass["aos_time"], selected_pass["los_time"], step_seconds=5, alt_m=gs_alt
            )

            fig_polar = go.Figure()
            fig_polar.add_trace(go.Scatterpolar(
                r=traj["elevation"], theta=traj["azimuth"],
                mode="lines+markers",
                marker=dict(
                    size=5, 
                    color=traj["range_km"], 
                    colorscale="Viridis", 
                    showscale=True, 
                    colorbar=dict(
                        title=dict(text="Distancia (km)", side="top"),
                        x=1.12,
                        len=0.75
                    )
                ),
                line=dict(color="#00f3ff", width=2.5), name="Trayectoria"
            ))
            fig_polar.add_trace(go.Scatterpolar(
                r=[traj["elevation"].iloc[0]], theta=[traj["azimuth"].iloc[0]],
                mode="markers+text", marker=dict(size=11, color="#22c55e"),
                text=["AOS"], textposition="top center", name="AOS"
            ))
            max_idx = traj["elevation"].idxmax()
            fig_polar.add_trace(go.Scatterpolar(
                r=[traj["elevation"].iloc[max_idx]], theta=[traj["azimuth"].iloc[max_idx]],
                mode="markers+text", marker=dict(size=11, color="#eab308"),
                text=["Max El"], textposition="top center", name="Max El"
            ))
            fig_polar.add_trace(go.Scatterpolar(
                r=[traj["elevation"].iloc[-1]], theta=[traj["azimuth"].iloc[-1]],
                mode="markers+text", marker=dict(size=11, color="#ef4444"),
                text=["LOS"], textposition="top center", name="LOS"
            ))
            fig_polar.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                polar=dict(angularaxis=dict(direction="clockwise", rotation=90), radialaxis=dict(range=[90, 0], angle=90, dtick=15)),
                legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top", bgcolor="rgba(15, 23, 42, 0.6)"),
                height=600, margin=dict(l=60, r=120, t=40, b=40)
            )
            st.plotly_chart(fig_polar, use_container_width=True)

    # TAB 4: LINK BUDGET & SIMULACIÓN DE RF (DOPPLER + MARGEN)
    with tab4:
        st.subheader("⚙️ Parámetros de la Cadena de Radiofrecuencia (RF)")

        rf_col1, rf_col2 = st.columns(2)

        with rf_col1:
            st.markdown("#### Transmisor del Satélite (Downlink)")
            freq_mhz = st.number_input("Frecuencia Central (MHz)", value=437.5, step=1.0)
            tx_power_w = st.number_input("Potencia Transmisor (Watts)", value=1.0, step=0.5)
            tx_power_dbw = 10 * float(np.log10(max(tx_power_w, 1e-6)))
            tx_gain_dbi = st.number_input("Ganancia Antena Satélite (dBi)", value=2.15, step=0.5)
            tx_losses_db = st.number_input("Pérdidas de línea Satélite (dB)", value=1.0, step=0.5)

        with rf_col2:
            st.markdown("#### Estación Terrestre (Receptor)")
            rx_gain_dbi = st.number_input("Ganancia Antena Terrestre (dBi)", value=12.0, step=0.5)
            system_temp_k = st.number_input("Temperatura de Ruido Tsys (K)", value=300.0, step=10.0)
            bandwidth_khz = st.number_input("Ancho de Banda Canal (kHz)", value=12.5, step=1.0)
            rx_losses_db = st.number_input("Pérdidas Atmosféricas/Línea GS (dB)", value=1.5, step=0.5)
            required_ebn0 = st.number_input("Eb/N0 Requerido (dB)", value=10.0, step=0.5)

        if not passes:
            st.warning("No hay pases disponibles para realizar el cálculo de RF.")
        else:
            rf_pass_idx = st.selectbox(
                "Selecciona el pase para simular el Link Budget y el Efecto Doppler", 
                range(len(passes)), 
                format_func=lambda i: f"Pase {i+1}: {passes[i]['aos_time'].strftime('%Y-%m-%d %H:%M:%S')} (Max El: {passes[i]['max_elevation']:.1f}°)",
                key="rf_pass_select"
            )

            target_pass = passes[rf_pass_idx]
            traj_rf = predictor.get_pass_trajectory(
                gs_lat, gs_lon, target_pass["aos_time"], target_pass["los_time"], step_seconds=5, alt_m=gs_alt
            )

            tx = SatelliteTransmitter(freq_mhz, tx_power_dbw, tx_gain_dbi, tx_losses_db)
            rx = GroundStationReceiver(rx_gain_dbi, system_temp_k, bandwidth_khz * 1000.0, rx_losses_db, required_ebn0)
            calc = LinkBudgetCalculator(tx, rx)

            rf_results = calc.evaluate_link(traj_rf["range_km"].values)
            traj_rf["fspl_db"] = rf_results["fspl_db"]
            traj_rf["received_power_dbw"] = rf_results["received_power_dbw"]
            traj_rf["cn_ratio_db"] = rf_results["cn_ratio_db"]
            traj_rf["link_margin_db"] = rf_results["link_margin_db"]

            v_rel_km_s = np.gradient(traj_rf["range_km"].values, 5.0)
            doppler_hz = - (freq_mhz * 1e6) * (v_rel_km_s / C_SPEED_KM_S)
            traj_rf["doppler_khz"] = doppler_hz / 1000.0

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("EIRP Satélite", f"{tx.eirp_dbw:.2f} dBW")
            m_col2.metric("FSPL Mínima (Max El)", f"{traj_rf['fspl_db'].min():.1f} dB")
            m_col3.metric("C/N Máxima", f"{traj_rf['cn_ratio_db'].max():.1f} dB")
            
            min_margin = traj_rf['link_margin_db'].min()
            m_col4.metric(
                "Margen Mínimo", 
                f"{min_margin:.1f} dB",
                delta="ENLACE OK" if min_margin >= 0 else "NO CIERRA",
                delta_color="normal" if min_margin >= 0 else "inverse"
            )

            st.subheader("1. Evolución de C/N y Margen de Enlace durante el Pase")

            fig_rf = go.Figure()
            fig_rf.add_trace(go.Scatter(
                x=traj_rf["datetime"], y=traj_rf["cn_ratio_db"],
                mode="lines", name="Relación C/N (dB)", line=dict(color="#00f3ff", width=2.5)
            ))
            fig_rf.add_trace(go.Scatter(
                x=traj_rf["datetime"], y=traj_rf["link_margin_db"],
                mode="lines", name="Margen de Enlace (dB)", line=dict(color="#22c55e", width=2.5)
            ))
            fig_rf.add_hline(y=0, line_dash="dash", line_color="#ef4444", annotation_text="Umbral Mínimo (0 dB)")

            fig_rf.update_layout(
                xaxis_title="Hora (UTC)", yaxis_title="Decibelios (dB)",
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                height=400
            )
            st.plotly_chart(fig_rf, use_container_width=True)

            st.subheader("2. Desplazamiento Doppler Instantáneo (kHz)")

            fig_doppler = go.Figure()
            fig_doppler.add_trace(go.Scatter(
                x=traj_rf["datetime"], y=traj_rf["doppler_khz"],
                mode="lines", name="Doppler Shift (kHz)", line=dict(color="#f59e0b", width=2.5)
            ))
            fig_doppler.add_hline(y=0, line_dash="dash", line_color="#64748b", annotation_text="Frecuencia Central (0 kHz)")

            fig_doppler.update_layout(
                xaxis_title="Hora (UTC)", yaxis_title="Offset de Frecuencia Δf (kHz)",
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                height=350
            )
            st.plotly_chart(fig_doppler, use_container_width=True)

            st.subheader("3. Balance de Enlace Desglosado (Punto de Máx Elevación)")

            max_el_idx = traj_rf["elevation"].idxmax()
            p_max = traj_rf.iloc[max_el_idx]

            n0_dbw_hz = -228.6 + 10 * np.log10(system_temp_k)
            n_power_dbw = n0_dbw_hz + 10 * np.log10(bandwidth_khz * 1000.0)

            breakdown_df = pd.DataFrame([
                {"Concepto": "Frecuencia de Downlink", "Valor": f"{freq_mhz:.2f} MHz", "Detalle": "Frecuencia central del canal"},
                {"Concepto": "Potencia del Transmisor (Pt)", "Valor": f"{tx_power_dbw:.2f} dBW ({tx_power_w:.1f} W)", "Detalle": "Potencia emitida por el satélite"},
                {"Concepto": "Ganancia Antena Satélite (Gt)", "Valor": f"+{tx_gain_dbi:.2f} dBi", "Detalle": "Ganancia de la antena transmisora"},
                {"Concepto": "Pérdidas de Línea Satélite", "Valor": f"-{tx_losses_db:.2f} dB", "Detalle": "Pérdidas de acoplamiento en satélite"},
                {"Concepto": "EIRP Satélite", "Valor": f"{tx.eirp_dbw:.2f} dBW", "Detalle": "Potencia Isotrópica Radiada Equivalente"},
                {"Concepto": "Distancia a Máx Elevación", "Valor": f"{p_max['range_km']:.1f} km", "Detalle": "Distancia mínima durante el pase"},
                {"Concepto": "Pérdidas Espacio Libre (FSPL)", "Valor": f"-{p_max['fspl_db']:.2f} dB", "Detalle": "Atenuación por trayectoria espacial"},
                {"Concepto": "Otras Pérdidas (Atmosf./GS)", "Valor": f"-{rx_losses_db:.2f} dB", "Detalle": "Pérdidas en atmósfera y líneas GS"},
                {"Concepto": "Ganancia Antena GS (Gr)", "Valor": f"+{rx_gain_dbi:.2f} dBi", "Detalle": "Ganancia de la estación terrestre"},
                {"Concepto": "Potencia Recibida (Pr)", "Valor": f"{p_max['received_power_dbw']:.2f} dBW", "Detalle": "Potencia efectiva en el receptor"},
                {"Concepto": "Densidad de Ruido (N0)", "Valor": f"{n0_dbw_hz:.2f} dBW/Hz", "Detalle": "Ruido térmico del sistema (k*Tsys)"},
                {"Concepto": "Potencia Total de Ruido (N)", "Valor": f"{n_power_dbw:.2f} dBW", "Detalle": "Ruido acumulado en el ancho de banda"},
                {"Concepto": "Relación Portadora/Ruido (C/N)", "Valor": f"{p_max['cn_ratio_db']:.2f} dB", "Detalle": "Calidad de señal obtenida"},
                {"Concepto": "Eb/N0 Requerido", "Valor": f"{required_ebn0:.2f} dB", "Detalle": "Umbral mínimo para demodulación"},
                {"Concepto": "Margen de Enlace (Link Margin)", "Valor": f"{p_max['link_margin_db']:.2f} dB", "Detalle": "Excedente de potencia sobre el umbral"}
            ])

            st.dataframe(breakdown_df, use_container_width=True)

            st.download_button(
                label="📥 Exportar Simulación Completa de RF (CSV)",
                data=traj_rf[["datetime", "azimuth", "elevation", "range_km", "fspl_db", "received_power_dbw", "cn_ratio_db", "link_margin_db", "doppler_khz"]].to_csv(index=False).encode('utf-8'),
                file_name=f"simulacion_rf_{tle_data['name'].replace(' ', '_')}.csv",
                mime="text/csv"
            )

except Exception as e:
    st.error(f"Error al procesar el satélite: {e}")