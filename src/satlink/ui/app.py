import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from streamlit_geolocation import streamlit_geolocation
from satlink.core.fetcher import fetch_tle_by_group
from satlink.core.propagator import OrbitPropagator
from satlink.core.passes import PassPredictor
from satlink.core.link_budget import SatelliteTransmitter, GroundStationReceiver, LinkBudgetCalculator

# 1. Configuración de página
st.set_page_config(page_title="SatLink Studio", layout="wide")

st.title("🛰️ SatLink Studio — Satellite & Ground Station Platform")
st.caption("Seguimiento orbital, predicción de pases y planificación de RF")

# 2. Inicializar st.session_state (Gijón por defecto)
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

    with st.sidebar:
        location = streamlit_geolocation()

    if location and location.get("latitude") is not None:
        st.session_state.gs_lat = location["latitude"]
        st.session_state.gs_lon = location["longitude"]
        if location.get("altitude") is not None:
            st.session_state.gs_alt = location["altitude"]
        st.sidebar.success("📍 Ubicación detectada por GPS/Navegador")

    gs_lat = st.sidebar.number_input("Latitud (°)", key="gs_lat", format="%.4f")
    gs_lon = st.sidebar.number_input("Longitud (°)", key="gs_lon", format="%.4f")
    gs_alt = st.sidebar.number_input("Altitud (m)", key="gs_alt", step=10.0)
    min_el = st.sidebar.slider("Máscara Elevación (°)", min_value=0, max_value=30, value=10, key="min_el_slider")

    # 5. PESTAÑAS PRINCIPALES
    tab1, tab2, tab3 = st.tabs(["🌍 Real-time Tracker", "📡 Predicción de Pases & Skyplot", "📊 Link Budget (RF)"])

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

    # Pre-calcular pases para TAB 2 y TAB 3
    predictor = PassPredictor(tle_data["name"], tle_data["line1"], tle_data["line2"])
    passes = predictor.predict_passes(gs_lat, gs_lon, alt_m=gs_alt, days=3, min_elevation_deg=min_el)

    # TAB 2: PREDICCIÓN DE PASES Y SKYPLOT
    with tab2:
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
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

            st.subheader("Diagrama Polar de Apuntamiento de Antena (Skyplot)")
            pass_idx = st.selectbox(
                "Selecciona un pase para analizar el barrido", 
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
                marker=dict(size=4, color=traj["range_km"], colorscale="Viridis", showscale=True, colorbar=dict(title="Distancia (km)")),
                line=dict(color="cyan", width=2), name="Trayectoria"
            ))
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
                polar=dict(angularaxis=dict(direction="clockwise", rotation=90), radialaxis=dict(range=[90, 0], angle=90, dtick=15)),
                height=600, margin=dict(l=40, r=40, t=40, b=40)
            )
            st.plotly_chart(fig_polar, use_container_width=True)

    # TAB 3: LINK BUDGET & RF ANALYSIS
    with tab3:
        st.subheader("⚙️ Parámetros de la Cadena de Radiofrecuencia (RF)")

        rf_col1, rf_col2 = st.columns(2)

        with rf_col1:
            st.markdown("#### Transmisor del Satélite (Downlink)")
            freq_mhz = st.number_input("Frecuencia (MHz)", value=437.5, step=1.0)
            tx_power_w = st.number_input("Potencia Transmisor (Watts)", value=1.0, step=0.5)
            tx_power_dbw = 10 * float(pd.Series(tx_power_w).apply(lambda x: 0 if x <= 0 else np.log10(x)).iloc[0])
            tx_gain_dbi = st.number_input("Ganancia Antena Satélite (dBi)", value=2.15, step=0.5)
            tx_losses_db = st.number_input("Pérdidas de línea Satélite (dB)", value=1.0, step=0.5)

        with rf_col2:
            st.markdown("#### Estación Terrestre (Receptor)")
            rx_gain_dbi = st.number_input("Ganancia Antena Terrestre (dBi)", value=12.0, step=0.5)
            system_temp_k = st.number_input("Temperatura de Ruido Tsys (K)", value=300.0, step=10.0)
            bandwidth_khz = st.number_input("Ancho de Banda (kHz)", value=12.5, step=1.0)
            rx_losses_db = st.number_input("Pérdidas Atmosféricas/Línea GS (dB)", value=1.5, step=0.5)
            required_ebn0 = st.number_input("Eb/N0 Requerido (dB)", value=10.0, step=0.5)

        if not passes:
            st.warning("No hay pases disponibles para realizar el cálculo de RF.")
        else:
            rf_pass_idx = st.selectbox(
                "Selecciona el pase para simular el Link Budget", 
                range(len(passes)), 
                format_func=lambda i: f"Pase {i+1}: {passes[i]['aos_time'].strftime('%Y-%m-%d %H:%M:%S')} (Max El: {passes[i]['max_elevation']:.1f}°)",
                key="rf_pass_select"
            )

            target_pass = passes[rf_pass_idx]
            traj_rf = predictor.get_pass_trajectory(
                gs_lat, gs_lon, target_pass["aos_time"], target_pass["los_time"], step_seconds=5, alt_m=gs_alt
            )

            # Instanciar calculador de Link Budget
            tx = SatelliteTransmitter(freq_mhz, tx_power_dbw, tx_gain_dbi, tx_losses_db)
            rx = GroundStationReceiver(rx_gain_dbi, system_temp_k, bandwidth_khz * 1000.0, rx_losses_db, required_ebn0)
            calc = LinkBudgetCalculator(tx, rx)

            # Evaluar el enlace para cada punto de la trayectoria
            rf_results = calc.evaluate_link(traj_rf["range_km"].values)
            traj_rf["fspl_db"] = rf_results["fspl_db"]
            traj_rf["received_power_dbw"] = rf_results["received_power_dbw"]
            traj_rf["cn_ratio_db"] = rf_results["cn_ratio_db"]
            traj_rf["link_margin_db"] = rf_results["link_margin_db"]

            # Métricas resumen del pase
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("EIRP Satélite", f"{tx.eirp_dbw:.2f} dBW")
            m_col2.metric("FSPL Máxima (AOS/LOS)", f"{traj_rf['fspl_db'].max():.1f} dB")
            m_col3.metric("C/N Máxima (Max El)", f"{traj_rf['cn_ratio_db'].max():.1f} dB")
            
            min_margin = traj_rf['link_margin_db'].min()
            m_col4.metric(
                "Margen Mínimo de Enlace", 
                f"{min_margin:.1f} dB",
                delta="OK (Enlace Cierra)" if min_margin >= 0 else "NO CIERRA",
                delta_color="normal" if min_margin >= 0 else "inverse"
            )

            # Gráficas de evolución temporal de RF durante el pase
            st.subheader("Evolución del Enlace durante el Pase")

            fig_rf = go.Figure()
            
            # Traza de C/N
            fig_rf.add_trace(go.Scatter(
                x=traj_rf["datetime"], y=traj_rf["cn_ratio_db"],
                mode="lines", name="Relación C/N (dB)", line=dict(color="cyan", width=2)
            ))
            
            # Traza de Margen de Enlace
            fig_rf.add_trace(go.Scatter(
                x=traj_rf["datetime"], y=traj_rf["link_margin_db"],
                mode="lines", name="Margen de Enlace (dB)", line=dict(color="lime", width=2)
            ))

            # Línea umbral de margen = 0 dB
            fig_rf.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Umbral de Recepción (0 dB)")

            fig_rf.update_layout(
                title="Carrier-to-Noise Ratio (C/N) y Margen de Enlace vs Tiempo",
                xaxis_title="Hora (UTC)",
                yaxis_title="Decibelios (dB)",
                template="plotly_dark",
                height=450
            )

            st.plotly_chart(fig_rf, use_container_width=True)

except Exception as e:
    st.error(f"Error al procesar el satélite: {e}")