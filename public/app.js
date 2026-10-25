(() => {
  const $ = (selector) => document.querySelector(selector);
  const state = {
    group: "stations", name: "ISS (ZARYA)", tab: "globe", catalog: [], mission: null, refreshing: false,
    missionRequest: 0, missionController: null, catalogRequest: 0, catalogController: null, catalogTimer: 0, rfRequest: 0, rfController: null, rfTimer: 0,
    land: null, world: null, globe: { longitude: -.35, tilt: -1.15, dragging: false, lastX: 0, lastY: 0, frame: 0, previousTimestamp: 0 },
    countdownTarget: null,
    map: { zoom: 1, x: 0, y: 0, width: 1080, height: 540, scale: 1, ox: 0, oy: 0, dpr: 1 },
  };
  const tabNames = { tracker: "Tracker 2D", globe: "Globo 3D", passes: "Predicción de Pases", rf: "Link Budget & Doppler", radar: "Sat-Radar" };
  const requestedView = new URLSearchParams(window.location.search).get("view");
  if (Object.hasOwn(tabNames, requestedView)) state.tab = requestedView;
  try {
    const previousSelection = JSON.parse(window.sessionStorage.getItem("satlinkSelection") || "null");
    if (["stations", "starlink", "geo", "active"].includes(previousSelection?.group) && typeof previousSelection.name === "string" && previousSelection.name.length < 100) {
      state.group = previousSelection.group;
      state.name = previousSelection.name;
      $("#group-select").value = state.group;
      if (state.group !== "stations" || state.name !== "ISS (ZARYA)") $("#satellite-search").value = state.name;
    }
  } catch (_) {}

  function rememberSelection() {
    try { window.sessionStorage.setItem("satlinkSelection", JSON.stringify({ group: state.group, name: state.name })); } catch (_) {}
  }

  function showNotice(message, kind = "") {
    const notice = $("#notice");
    notice.textContent = message;
    notice.className = `notice ${kind}`;
    notice.hidden = !message;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, { headers: { Accept: "application/json" }, ...options });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `Error ${response.status}`);
    return body;
  }

  function queryParams(includeTrack = false) {
    const query = new URLSearchParams({
      group: state.group, name: state.name,
      lat: $("#latitude").value || "43.5357", lon: $("#longitude").value || "-5.6615",
      alt: $("#altitude").value || "10", min_el: $("#elevation-mask").value || "10",
      include_track: String(includeTrack),
    });
    return query.toString();
  }

  async function loadCatalog({ searchOnly = false } = {}) {
    const requestId = ++state.catalogRequest;
    state.catalogController?.abort();
    const controller = new AbortController();
    state.catalogController = controller;
    const groupSelect = $("#group-select");
    if (!searchOnly) { groupSelect.disabled = true; showNotice("Conectando con CelesTrak…"); }
    try {
      const params = new URLSearchParams({ group: state.group, search: $("#satellite-search").value.trim(), limit: "100" });
      const result = await api(`/api/catalog?${params}`, { signal: controller.signal });
      if (requestId !== state.catalogRequest) return;
      state.catalog = result.satellites;
      const select = $("#satellite-select");
      select.replaceChildren(...state.catalog.map((satellite) => {
        const option = document.createElement("option");
        option.value = satellite.name;
        option.textContent = satellite.name;
        return option;
      }));
      const currentOption = state.catalog.find((satellite) => satellite.name === state.name);
      if (searchOnly) {
        select.value = currentOption?.name || "";
      } else {
        const preferred = currentOption || state.catalog.find((satellite) => satellite.name === "ISS (ZARYA)") || state.catalog[0];
        state.name = preferred.name;
        select.value = state.name;
        rememberSelection();
      }
      const total = Number(result.total || 0);
      $("#satellite-count").textContent = total > result.returned
        ? `Mostrando ${result.returned} de ${total.toLocaleString("es-ES")} satélites. Afina la búsqueda para encontrar el resto.`
        : `${total.toLocaleString("es-ES")} satélite${total === 1 ? "" : "s"} disponible${total === 1 ? "" : "s"}.`;
      if (!searchOnly) {
        if (result.stale) {
          const date = result.fetched_at ? new Date(result.fetched_at).toLocaleString("es-ES", { timeZone: "UTC", dateStyle: "short", timeStyle: "short" }) : "fecha desconocida";
          showNotice(`CelesTrak no ha entregado datos nuevos. Se usa una copia de respaldo del ${date} UTC; las predicciones pueden estar desactualizadas.`, "warning");
        } else showNotice("");
        await loadMission();
      }
    } catch (error) {
      if (error.name !== "AbortError" && requestId === state.catalogRequest) {
        if (searchOnly) $("#satellite-count").textContent = `No se pudo buscar: ${error.message}`;
        else throw error;
      }
    } finally {
      if (requestId === state.catalogRequest && !searchOnly) groupSelect.disabled = false;
    }
  }

  async function loadMission() {
    const stationInputs = ["#latitude", "#longitude", "#altitude", "#elevation-mask"].map($);
    const invalidInput = stationInputs.find((input) => !input.checkValidity());
    if (invalidInput) { invalidInput.reportValidity(); return; }
    const requestId = ++state.missionRequest;
    state.missionController?.abort();
    const controller = new AbortController();
    state.missionController = controller;
    state.refreshing = true;
    try {
      const hasTrack = state.tab === "tracker" || state.tab === "globe";
      const result = await api(`/api/mission?${queryParams(hasTrack)}`, { signal: controller.signal });
      if (requestId !== state.missionRequest) return;
      state.mission = result;
      updateDashboard();
      if (state.tab === "tracker") drawTracker();
      if (state.tab === "globe") drawGlobe(performance.now(), true);
      if (state.tab === "passes") renderPasses();
      if (state.tab === "rf") calculateRf();
    } catch (error) {
      if (error.name !== "AbortError" && requestId === state.missionRequest) showNotice(`No se pudo actualizar la telemetría: ${error.message}`, "error");
    } finally {
      if (requestId === state.missionRequest) state.refreshing = false;
    }
  }

  function updateDashboard() {
    const mission = state.mission;
    if (!mission) return;
    const sat = mission.state;
    $("#hud-satellite").textContent = sat.name;
    $("#globe-satellite").textContent = sat.name;
    $("#hud-station").textContent = `${Number($("#latitude").value).toFixed(2)}°, ${Number($("#longitude").value).toFixed(2)}°`;
    $("#hud-pass-label").textContent = mission.pass_status.label;
    $("#hud-countdown").textContent = mission.pass_status.countdown;
    state.countdownTarget = mission.pass_status.event_timestamp;
    $("#metric-lat").textContent = `${sat.latitude.toFixed(4)}°`;
    $("#metric-lon").textContent = `${sat.longitude.toFixed(4)}°`;
    $("#metric-alt").textContent = `${sat.altitude_km.toFixed(2)} km`;
    $("#metric-speed").textContent = `${sat.speed_km_s.toFixed(2)} km/s`;
    if (state.tab === "tracker") drawTracker();
    if (state.tab === "globe") drawGlobe(performance.now(), true);
  }

  function renderPasses() {
    const body = $("#passes-body");
    const passes = state.mission?.passes || [];
    body.replaceChildren();
    $("#passes-empty").hidden = passes.length > 0;
    for (const [index, pass] of passes.entries()) {
      const row = document.createElement("tr");
      if (index === 0) row.classList.add("next-pass");
      const aos = new Date(pass.aos_time);
      const los = new Date(pass.los_time);
      const duration = Math.floor(pass.duration_seconds);
      const values = [
        `${aos.toISOString().slice(0, 10)} ${aos.toISOString().slice(11, 19)}`,
        `${pass.max_elevation.toFixed(1)}°`,
        los.toISOString().slice(11, 19),
        `${Math.floor(duration / 60)}m ${duration % 60}s`,
      ];
      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      body.append(row);
    }
  }

  function setTab(tab) {
    if (!tabNames[tab]) return;
    state.tab = tab;
    try { window.sessionStorage.setItem("satlinkActiveView", tab); } catch (_) {}
    document.querySelectorAll(".tab-button").forEach((button) => {
      const active = button.dataset.tab === tab;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    const activeName = $("#active-view-name");
    if (activeName) activeName.textContent = tabNames[tab];
    window.closeSatlinkViewMenu?.();
    document.querySelectorAll(".view").forEach((view) => { view.hidden = view.id !== `${tab}-view`; });
    document.body.classList.toggle("radar-mode", tab === "radar");
    if (tab === "radar") window.SatRadar?.activate();
    else window.SatRadar?.deactivate();
    if (["tracker", "globe", "passes", "rf"].includes(tab)) loadMission();
    if (tab === "passes" && state.mission) renderPasses();
    if (tab !== "globe" && state.globe.frame) { cancelAnimationFrame(state.globe.frame); state.globe.frame = 0; }
  }

  function calculateRf() {
    const form = $("#rf-form");
    if (!form.reportValidity()) return;
    const requestId = ++state.rfRequest;
    state.rfController?.abort();
    const controller = new AbortController();
    state.rfController = controller;
    const button = $("#rf-calculate");
    button.disabled = true;
    $("#rf-status").textContent = "Calculando geometría orbital y balance…";
    const params = new URLSearchParams({
      group: state.group, name: state.name, lat: $("#latitude").value, lon: $("#longitude").value,
      alt: $("#altitude").value, frequency_mhz: $("#rf-frequency").value,
      tx_power_dbw: $("#rf-tx-power").value, tx_gain_dbi: $("#rf-tx-gain").value,
      tx_losses_db: $("#rf-tx-losses").value, rx_gain_dbi: $("#rf-rx-gain").value,
      noise_temp_k: $("#rf-noise-temp").value, bandwidth_hz: $("#rf-bandwidth").value,
      required_ebn0_db: $("#rf-required-ebn0").value,
    });
    api(`/api/link-budget?${params}`, { signal: controller.signal }).then((result) => {
      if (requestId !== state.rfRequest) return;
      const db = (value) => `${Number(value).toFixed(2)} dB`;
      $("#rf-range").textContent = `${Number(result.range_km).toLocaleString("es-ES", { maximumFractionDigits: 2 })} km`;
      $("#rf-fspl").textContent = db(result.fspl_db);
      $("#rf-power").textContent = `${Number(result.received_power_dbw).toFixed(2)} dBW`;
      $("#rf-cn").textContent = db(result.cn_ratio_db);
      $("#rf-ebn0").textContent = db(result.ebn0_db);
      $("#rf-doppler").textContent = `${Number(result.doppler_hz).toFixed(1)} Hz`;
      const margin = $("#rf-margin-card");
      margin.classList.toggle("link-ok", result.visible && result.link_margin_db >= 0);
      margin.classList.toggle("link-low", !result.visible || result.link_margin_db < 0);
      $("#rf-margin").textContent = db(result.link_margin_db);
      $("#rf-margin-note").textContent = !result.visible ? `Satélite bajo el horizonte (${Number(result.elevation_deg).toFixed(1)}°)`
        : result.link_margin_db >= 0 ? `Enlace viable · elevación ${Number(result.elevation_deg).toFixed(1)}°`
          : `Margen insuficiente · elevación ${Number(result.elevation_deg).toFixed(1)}°`;
      $("#rf-status").textContent = "Estimación actualizada con la posición del satélite en este instante.";
    }).catch((error) => {
      if (error.name !== "AbortError" && requestId === state.rfRequest) $("#rf-status").textContent = `No se pudo calcular el enlace: ${error.message}`;
    }).finally(() => {
      if (requestId === state.rfRequest) button.disabled = false;
    });
  }

  async function loadWorld() {
    if (!state.world) state.world = await api("/assets/world_110m_admin_0_countries.geojson");
    return state.world;
  }

  async function loadLand() {
    if (!state.land) state.land = await api("/api/globe-land");
    return state.land;
  }

  function mapProjection(lon, lat) {
    const m = state.map;
    return [m.ox + ((lon + 180) / 360) * 1080 * m.scale, m.oy + ((90 - lat) / 180) * 540 * m.scale];
  }

  function drawTrackerBase(ctx, width, height) {
    const m = state.map;
    m.width = width; m.height = height;
    m.scale = Math.min(width / 1080, height / 540);
    m.ox = (width - 1080 * m.scale) / 2;
    m.oy = (height - 540 * m.scale) / 2;
    ctx.fillStyle = "#040c14";
    ctx.fillRect(0, 0, width, height);
    ctx.save();
    ctx.translate(m.x, m.y);
    ctx.scale(m.zoom, m.zoom);
    ctx.strokeStyle = "rgba(91,158,203,.11)";
    ctx.lineWidth = 1 / m.zoom;
    ctx.beginPath();
    for (let lon = -180; lon <= 180; lon += 30) { const [x] = mapProjection(lon, 0); ctx.moveTo(x, 0); ctx.lineTo(x, height); }
    for (let lat = -90; lat <= 90; lat += 30) { const [, y] = mapProjection(0, lat); ctx.moveTo(0, y); ctx.lineTo(width, y); }
    ctx.stroke();
    if (state.world) {
      ctx.beginPath();
      for (const feature of state.world.features || []) {
        const geometry = feature.geometry;
        if (!geometry) continue;
        const polygons = geometry.type === "Polygon" ? geometry.coordinates : geometry.coordinates || [];
        const rings = geometry.type === "Polygon" ? polygons : polygons.flatMap((polygon) => polygon);
        for (const ring of rings) {
          if (!ring.length) continue;
          ring.forEach(([lon, lat], index) => { const [x, y] = mapProjection(lon, lat); index ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
          ctx.closePath();
        }
      }
      ctx.fillStyle = "#0d2031"; ctx.fill("evenodd");
      ctx.strokeStyle = "rgba(102,196,255,.42)"; ctx.lineWidth = .65 / m.zoom; ctx.stroke();
    }
    ctx.restore();
  }

  function clampMap() {
    const m = state.map, mapW = 1080 * m.scale, mapH = 540 * m.scale;
    const minX = m.width - (m.ox + mapW) * m.zoom, maxX = -m.ox * m.zoom;
    const minY = m.height - (m.oy + mapH) * m.zoom, maxY = -m.oy * m.zoom;
    m.x = mapW * m.zoom <= m.width ? (m.width - mapW * m.zoom) / 2 - m.ox * m.zoom : Math.max(minX, Math.min(maxX, m.x));
    m.y = mapH * m.zoom <= m.height ? (m.height - mapH * m.zoom) / 2 - m.oy * m.zoom : Math.max(minY, Math.min(maxY, m.y));
  }

  function drawTracker() {
    if (!state.mission?.track || !state.world) return;
    const canvas = $("#tracker-canvas"), stage = $("#tracker-stage"), rect = stage.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const width = Math.max(1, rect.width), height = Math.max(1, rect.height);
    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
    }
    const ctx = canvas.getContext("2d", { alpha: false });
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawTrackerBase(ctx, width, height);
    const m = state.map, track = state.mission.track;
    clampMap();
    ctx.save(); ctx.translate(m.x, m.y); ctx.scale(m.zoom, m.zoom);
    ctx.beginPath(); let drawing = false, previous = null;
    for (const point of track) {
      if (previous !== null && Math.abs(point.longitude - previous) > 180) drawing = false;
      const [x, y] = mapProjection(point.longitude, point.latitude);
      if (drawing) ctx.lineTo(x, y); else { ctx.moveTo(x, y); drawing = true; }
      previous = point.longitude;
    }
    ctx.strokeStyle = "#6ad8ff"; ctx.lineWidth = 2.5 / m.zoom; ctx.shadowColor = "rgba(70,202,255,.72)"; ctx.shadowBlur = 7 / m.zoom; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke(); ctx.shadowBlur = 0;
    const station = mapProjection(Number($("#longitude").value), Number($("#latitude").value));
    ctx.fillStyle = "#ffcc66"; ctx.shadowColor = "rgba(255,198,92,.8)"; ctx.shadowBlur = 9 / m.zoom; ctx.beginPath(); ctx.arc(station[0], station[1], 5 / m.zoom, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
    const now = Date.now(); let left = track[0], right = track.at(-1);
    for (let i = 1; i < track.length; i++) { if (track[i].timestamp >= now) { left = track[i - 1]; right = track[i]; break; } }
    const fraction = Math.max(0, Math.min(1, (now - left.timestamp) / Math.max(1, right.timestamp - left.timestamp)));
    let lonDelta = right.longitude - left.longitude;
    if (lonDelta > 180) lonDelta -= 360; if (lonDelta < -180) lonDelta += 360;
    let satLon = left.longitude + lonDelta * fraction;
    if (satLon > 180) satLon -= 360; if (satLon < -180) satLon += 360;
    const sat = mapProjection(satLon, left.latitude + (right.latitude - left.latitude) * fraction);
    ctx.fillStyle = "rgba(255,51,102,.24)"; ctx.shadowColor = "#ff3366"; ctx.shadowBlur = 14 / m.zoom; ctx.beginPath(); ctx.arc(sat[0], sat[1], 9 / m.zoom, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#ff6688"; ctx.beginPath(); ctx.moveTo(sat[0], sat[1] - 6 / m.zoom); ctx.lineTo(sat[0] + 6 / m.zoom, sat[1]); ctx.lineTo(sat[0], sat[1] + 6 / m.zoom); ctx.lineTo(sat[0] - 6 / m.zoom, sat[1]); ctx.closePath(); ctx.fill(); ctx.shadowBlur = 0;
    ctx.restore();
    ctx.fillStyle = "rgba(8,19,22,.86)"; ctx.fillRect(14, 14, 246, 82); ctx.strokeStyle = "rgba(113,215,193,.32)"; ctx.strokeRect(14, 14, 246, 82);
    ctx.font = "400 10px 'Space Mono',monospace"; const legend = [["#6ad8ff", "GROUND TRACK"], ["#ff6688", `SATELLITE - ${state.name}`], ["#ffcc66", "GROUND STATION"]];
    legend.forEach(([color, label], index) => { const y = 38 + index * 24; ctx.fillStyle = color; ctx.beginPath(); ctx.arc(26, y - 4, 3, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = "#edf4ef"; ctx.fillText(label, 36, y); });
  }

  function resizeTracker() { if (state.tab === "tracker") drawTracker(); }

  function rotatePoint(x, y, z, cosLon, sinLon, cosTilt, sinTilt) {
    const rx = x * cosLon - y * sinLon, ry = x * sinLon + y * cosLon;
    return { x: rx, y: ry * cosTilt - z * sinTilt, depth: ry * sinTilt + z * cosTilt };
  }

  function drawGlobe(timestamp, force = false) {
    if (!state.mission?.track || !state.land) return;
    const canvas = $("#globe-canvas"), stage = $("#globe-stage"), rect = stage.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5), width = rect.width, height = rect.height;
    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) { canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr); }
    const ctx = canvas.getContext("2d", { alpha: false });
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const cx = width / 2, cy = height / 2, radius = Math.max(40, Math.min(width, height) * .41);
    const camera = state.globe;
    const cosLon = Math.cos(camera.longitude), sinLon = Math.sin(camera.longitude), cosTilt = Math.cos(camera.tilt), sinTilt = Math.sin(camera.tilt);
    const project = (p) => ({ x: cx + p.x * radius, y: cy - p.y * radius });

    const background = ctx.createRadialGradient(cx, cy, radius * .2, cx, cy, Math.max(width, height) * .72);
    background.addColorStop(0, "#071e3b"); background.addColorStop(1, "#020b19"); ctx.fillStyle = background; ctx.fillRect(0, 0, width, height);
    for (let i = 0; i < 95; i++) {
      const sx = (i * 127.17 % 997) / 997 * width, sy = (i * 311.71 % 991) / 991 * height;
      ctx.fillStyle = `rgba(82,179,255,${.13 + ((i * 13) % 50) / 100})`; ctx.fillRect(sx, sy, i % 9 ? 1 : 1.5, i % 9 ? 1 : 1.5);
    }
    const ocean = ctx.createRadialGradient(cx - radius * .35, cy - radius * .4, radius * .12, cx, cy, radius);
    ocean.addColorStop(0, "#123b66"); ocean.addColorStop(.38, "#08274b"); ocean.addColorStop(.78, "#04152f"); ocean.addColorStop(1, "#010817");
    ctx.fillStyle = ocean; ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.fill();

    ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, radius * .998, 0, Math.PI * 2); ctx.clip();
    ctx.strokeStyle = "rgba(74,190,255,.22)"; ctx.lineWidth = .7; ctx.beginPath();
    for (let lat = -60; lat <= 60; lat += 30) {
      let active = false;
      for (let lon = -180; lon <= 180; lon += 3) {
        const phi = lat * Math.PI / 180, lambda = lon * Math.PI / 180;
        const p = rotatePoint(Math.cos(phi) * Math.cos(lambda), Math.cos(phi) * Math.sin(lambda), Math.sin(phi), cosLon, sinLon, cosTilt, sinTilt);
        if (p.depth <= 0) { active = false; continue; }
        const q = project(p); active ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y); active = true;
      }
    }
    for (let lon = -150; lon <= 180; lon += 30) {
      let active = false;
      for (let lat = -90; lat <= 90; lat += 3) {
        const phi = lat * Math.PI / 180, lambda = lon * Math.PI / 180;
        const p = rotatePoint(Math.cos(phi) * Math.cos(lambda), Math.cos(phi) * Math.sin(lambda), Math.sin(phi), cosLon, sinLon, cosTilt, sinTilt);
        if (p.depth <= 0) { active = false; continue; }
        const q = project(p); active ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y); active = true;
      }
    }
    ctx.stroke();
    const bins = [[], [], []];
    for (const [lat, lon] of state.land.points) {
      const phi = lat * Math.PI / 180, lambda = lon * Math.PI / 180;
      const p = rotatePoint(Math.cos(phi) * Math.cos(lambda), Math.cos(phi) * Math.sin(lambda), Math.sin(phi), cosLon, sinLon, cosTilt, sinTilt);
      if (p.depth <= 0) continue;
      const q = project(p); bins[Math.min(2, Math.floor(p.depth * 3))].push([q.x, q.y, .72 + p.depth * 1.12]);
    }
    const landColors = ["rgba(23,122,255,.68)", "rgba(38,166,255,.86)", "rgba(126,232,255,1)"];
    bins.forEach((points, index) => {
      ctx.fillStyle = landColors[index]; ctx.beginPath();
      for (const [x, y, size] of points) { ctx.moveTo(x + size, y); ctx.arc(x, y, size, 0, Math.PI * 2); }
      ctx.fill();
    });

    // Draw only the near side of the orbit, splitting at the globe's silhouette.
    const track = state.mission.track;
    let pathOpen = false;
    ctx.beginPath();
    for (let i = 0; i < track.length - 1; i++) {
      const start = track[i], end = track[i + 1];
      for (let step = i ? 1 : 0; step <= 4; step++) {
        const f = step / 4;
        const v = [start.x + (end.x - start.x) * f, start.y + (end.y - start.y) * f, start.z + (end.z - start.z) * f];
        const p = rotatePoint(v[0] / state.land.earth_radius, v[1] / state.land.earth_radius, v[2] / state.land.earth_radius, cosLon, sinLon, cosTilt, sinTilt);
        const visible = p.depth > 0 || Math.hypot(p.x, p.y) > 1;
        if (!visible) { pathOpen = false; continue; }
        const q = project(p);
        if (!pathOpen) { ctx.moveTo(q.x, q.y); pathOpen = true; } else ctx.lineTo(q.x, q.y);
      }
    }
    ctx.lineWidth = 2; ctx.strokeStyle = "rgba(30,176,255,.96)"; ctx.shadowColor = "rgba(0,174,255,.96)"; ctx.shadowBlur = 13; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke(); ctx.shadowBlur = 0;
    const [sx, sy, sz] = state.mission.satellite_xyz;
    const satellite = rotatePoint(sx / state.land.earth_radius, sy / state.land.earth_radius, sz / state.land.earth_radius, cosLon, sinLon, cosTilt, sinTilt);
    if (satellite.depth > 0 || Math.hypot(satellite.x, satellite.y) > 1) {
      const q = project(satellite); ctx.fillStyle = "rgba(35,174,255,.3)"; ctx.shadowColor = "#35c7ff"; ctx.shadowBlur = 16; ctx.beginPath(); ctx.arc(q.x, q.y, 7, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = "#e8fbff"; ctx.shadowBlur = 8; ctx.beginPath(); ctx.arc(q.x, q.y, 3.4, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
    }
    ctx.restore();
    const atmosphere = ctx.createRadialGradient(cx - radius * .35, cy - radius * .4, radius * .68, cx, cy, radius * 1.03);
    atmosphere.addColorStop(0, "rgba(84,194,255,0)"); atmosphere.addColorStop(.84, "rgba(26,151,255,.08)"); atmosphere.addColorStop(.97, "rgba(87,220,255,.68)"); atmosphere.addColorStop(1, "rgba(22,124,255,.16)");
    ctx.fillStyle = atmosphere; ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.fill(); ctx.strokeStyle = "rgba(137,235,255,.94)"; ctx.lineWidth = 1.5; ctx.shadowColor = "#00aaff"; ctx.shadowBlur = 19; ctx.stroke(); ctx.shadowBlur = 0;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!camera.dragging && !reducedMotion && camera.previousTimestamp) camera.longitude += .000045 * (timestamp - camera.previousTimestamp);
    camera.previousTimestamp = timestamp;
    if (state.tab === "globe" && !reducedMotion && !camera.frame) {
      camera.frame = requestAnimationFrame((time) => { camera.frame = 0; drawGlobe(time); });
    }
  }

  function setupEvents() {
    let guideScrollFrame = 0;
    const stopGuideScroll = () => {
      if (guideScrollFrame) cancelAnimationFrame(guideScrollFrame);
      guideScrollFrame = 0;
    };
    window.addEventListener("wheel", stopGuideScroll, { passive: true });
    window.addEventListener("touchstart", stopGuideScroll, { passive: true });
    document.querySelectorAll(".sat-card-nav .card-nav-card[href^='#']").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const targetId = link.getAttribute("href");
        const section = $(targetId);
        if (!section) return;
        stopGuideScroll();
        if (window.location.hash !== targetId) window.history.pushState(null, "", targetId);
        const from = window.scrollY;
        const destination = Math.min(
          Math.max(0, section.getBoundingClientRect().top + from - 100),
          Math.max(0, document.documentElement.scrollHeight - window.innerHeight),
        );
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
          window.scrollTo(0, destination);
          return;
        }
        const duration = 420;
        const start = performance.now();
        const animate = (now) => {
          const progress = Math.min(1, (now - start) / duration);
          const eased = 1 - (1 - progress) ** 3;
          window.scrollTo(0, from + (destination - from) * eased);
          guideScrollFrame = progress < 1 ? requestAnimationFrame(animate) : 0;
        };
        guideScrollFrame = requestAnimationFrame(animate);
      });
    });
    $("#radar-exit").addEventListener("click", () => setTab("globe"));
    window.addEventListener("satlink:open-satellite", async (event) => {
      const { group, name } = event.detail;
      state.group = group;
      state.name = name;
      $("#group-select").value = group;
      $("#satellite-search").value = name;
      try { await loadCatalog(); setTab("tracker"); }
      catch (error) { showNotice(`No se pudo abrir la ficha orbital: ${error.message}`, "error"); }
    });
    if (window.matchMedia("(pointer: fine)").matches && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      let pointerFrame = 0;
      let pointerX = window.innerWidth * .72;
      let pointerY = window.innerHeight * .28;
      window.addEventListener("pointermove", (event) => {
        if (event.pointerType === "touch") return;
        pointerX = event.clientX;
        pointerY = event.clientY;
        if (pointerFrame) return;
        pointerFrame = requestAnimationFrame(() => {
          document.documentElement.style.setProperty("--cursor-x", `${pointerX}px`);
          document.documentElement.style.setProperty("--cursor-y", `${pointerY}px`);
          pointerFrame = 0;
        });
      }, { passive: true });
    }
    const customSelects = new Map();
    const syncCustomSelect = (select) => {
      const control = customSelects.get(select);
      if (!control) return;
      const selected = select.selectedOptions[0];
      control.value.textContent = selected?.textContent || "Selecciona una opción";
      control.trigger.disabled = select.disabled;
      control.menu.querySelectorAll(".picker-option").forEach((option) => {
        const active = option.dataset.value === select.value;
        option.setAttribute("aria-selected", String(active));
        option.classList.toggle("selected", active);
      });
    };
    const closePicker = (control, restoreFocus = false) => {
      control.menu.classList.remove("open");
      control.trigger.setAttribute("aria-expanded", "false");
      window.setTimeout(() => { if (!control.menu.classList.contains("open")) control.menu.hidden = true; }, 190);
      if (restoreFocus) control.trigger.focus();
    };
    const openPicker = (control) => {
      customSelects.forEach((other) => {
        if (other !== control) {
          other.menu.classList.remove("open");
          other.menu.hidden = true;
          other.trigger.setAttribute("aria-expanded", "false");
        }
      });
      const bounds = control.trigger.getBoundingClientRect();
      const menuHeight = Math.min(control.menu.querySelectorAll(".picker-option").length * 39 + 16, 260);
      const top = bounds.bottom + menuHeight + 12 <= window.innerHeight
        ? bounds.bottom + 8 : Math.max(12, bounds.top - menuHeight - 8);
      control.menu.style.left = `${Math.max(10, Math.min(bounds.left, window.innerWidth - bounds.width - 10))}px`;
      control.menu.style.width = `${bounds.width}px`;
      control.menu.style.top = `${top}px`;
      control.menu.hidden = false;
      requestAnimationFrame(() => control.menu.classList.add("open"));
      control.trigger.setAttribute("aria-expanded", "true");
    };
    const enhanceSelect = (select) => {
      if (!select || customSelects.has(select)) return;
      const label = document.querySelector(`label[for="${select.id}"]`);
      const wrapper = document.createElement("div");
      wrapper.className = "custom-select";
      const trigger = document.createElement("button");
      trigger.type = "button";
      trigger.className = "picker-trigger";
      trigger.id = `${select.id}-trigger`;
      trigger.setAttribute("aria-haspopup", "listbox");
      trigger.setAttribute("aria-expanded", "false");
      trigger.setAttribute("aria-label", label?.textContent.trim() || "Seleccionar opción");
      const icon = document.createElement("span");
      icon.className = "picker-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = select.id === "group-select" ? "◌" : "⌖";
      const value = document.createElement("span");
      value.className = "picker-value";
      const chevron = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      chevron.setAttribute("class", "picker-chevron");
      chevron.setAttribute("viewBox", "0 0 16 16");
      chevron.setAttribute("fill", "none");
      chevron.setAttribute("aria-hidden", "true");
      const chevronPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
      chevronPath.setAttribute("d", "m4 6 4 4 4-4");
      chevronPath.setAttribute("stroke", "currentColor");
      chevronPath.setAttribute("stroke-width", "1.5");
      chevronPath.setAttribute("stroke-linecap", "round");
      chevronPath.setAttribute("stroke-linejoin", "round");
      chevron.append(chevronPath);
      trigger.append(icon, value, chevron);
      const menu = document.createElement("div");
      menu.className = "picker-menu";
      menu.id = `${select.id}-menu`;
      menu.setAttribute("role", "listbox");
      menu.setAttribute("aria-label", label?.textContent.trim() || "Opciones");
      trigger.setAttribute("aria-controls", menu.id);
      select.parentNode.insertBefore(wrapper, select);
      wrapper.append(select, trigger);
      document.body.append(menu);
      select.classList.add("native-select-source");
      select.tabIndex = -1;
      select.setAttribute("aria-hidden", "true");
      if (label) label.htmlFor = trigger.id;
      const control = { select, trigger, menu, value };
      customSelects.set(select, control);
      const renderOptions = () => {
        const options = [...select.options].map((nativeOption) => {
          const option = document.createElement("button");
          option.type = "button";
          option.className = "picker-option";
          option.setAttribute("role", "option");
          option.dataset.value = nativeOption.value;
          const text = document.createElement("span");
          text.textContent = nativeOption.textContent;
          const check = document.createElement("i");
          check.setAttribute("aria-hidden", "true");
          check.textContent = "✓";
          option.append(text, check);
          option.addEventListener("click", () => {
            select.value = nativeOption.value;
            select.dispatchEvent(new Event("change", { bubbles: true }));
            syncCustomSelect(select);
            closePicker(control, true);
          });
          option.addEventListener("keydown", (event) => {
            const items = [...menu.querySelectorAll(".picker-option")];
            const index = items.indexOf(option);
            if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
              event.preventDefault();
              const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1
                : (index + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
              items[next]?.focus();
            }
            if (event.key === "Escape") { event.preventDefault(); closePicker(control, true); }
          });
          return option;
        });
        menu.replaceChildren(...options);
        syncCustomSelect(select);
      };
      renderOptions();
      select.addEventListener("change", () => syncCustomSelect(select));
      const observer = new MutationObserver(renderOptions);
      observer.observe(select, { childList: true, attributes: true, attributeFilter: ["disabled"] });
      trigger.addEventListener("click", () => trigger.getAttribute("aria-expanded") === "true" ? closePicker(control) : openPicker(control));
      trigger.addEventListener("keydown", (event) => {
        if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
          event.preventDefault();
          openPicker(control);
          const selected = menu.querySelector('.picker-option[aria-selected="true"]');
          (event.key === "ArrowUp" ? menu.lastElementChild : selected || menu.firstElementChild)?.focus();
        }
      });
    };
    enhanceSelect($("#group-select"));
    enhanceSelect($("#satellite-select"));
    document.addEventListener("pointerdown", (event) => {
      customSelects.forEach((control) => {
        if (!control.menu.contains(event.target) && !control.trigger.contains(event.target) && control.trigger.getAttribute("aria-expanded") === "true") closePicker(control);
      });
    });
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") customSelects.forEach((control) => { if (control.trigger.getAttribute("aria-expanded") === "true") closePicker(control, true); });
    });
    document.querySelectorAll("button").forEach((button) => {
      if (button.id === "sidebar-open") return;
      button.classList.add("specular-button");
      const glint = document.createElement("span");
      glint.className = "specular-glint";
      glint.setAttribute("aria-hidden", "true");
      button.prepend(glint);
      button.addEventListener("pointermove", (event) => {
        if (event.pointerType === "touch") return;
        const bounds = button.getBoundingClientRect();
        button.style.setProperty("--spec-x", `${event.clientX - bounds.left}px`);
        button.style.setProperty("--spec-y", `${event.clientY - bounds.top}px`);
      });
      button.addEventListener("pointerleave", () => button.classList.remove("specular-pressed"));
      button.addEventListener("pointerdown", () => button.classList.add("specular-pressed"));
      button.addEventListener("pointerup", () => button.classList.remove("specular-pressed"));
    });
    document.querySelectorAll(".overview-card, .metric-card, .rf-result-card, .rf-panel, .pass-table-wrap").forEach((card) => {
      card.classList.add("cursor-lit-card");
      const canTilt = card.matches(".overview-card, .metric-card, .rf-result-card");
      card.addEventListener("pointermove", (event) => {
        if (event.pointerType === "touch") return;
        const bounds = card.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width;
        const y = (event.clientY - bounds.top) / bounds.height;
        card.style.setProperty("--spot-x", `${x * 100}%`);
        card.style.setProperty("--spot-y", `${y * 100}%`);
        if (canTilt) {
          card.style.setProperty("--tilt-x", `${(x - .5) * 1.4}deg`);
          card.style.setProperty("--tilt-y", `${(.5 - y) * 1.4}deg`);
        }
        card.classList.add("is-illuminated");
      });
      card.addEventListener("pointerleave", () => {
        card.classList.remove("is-illuminated");
        card.style.setProperty("--tilt-x", "0deg");
        card.style.setProperty("--tilt-y", "0deg");
      });
    });
    const viewMenu = $("#view-menu"), viewTrigger = $("#view-select-trigger");
    let menuCloseTimer = 0;
    const closeViewMenu = () => {
      if (!viewMenu || !viewTrigger || viewMenu.hidden) return;
      window.clearTimeout(menuCloseTimer);
      viewMenu.classList.remove("open");
      viewTrigger.setAttribute("aria-expanded", "false");
      menuCloseTimer = window.setTimeout(() => { if (!viewMenu.classList.contains("open")) viewMenu.hidden = true; }, 220);
    };
    const openViewMenu = (focusActive = false) => {
      if (!viewMenu || !viewTrigger) return;
      window.clearTimeout(menuCloseTimer);
      viewMenu.hidden = false;
      requestAnimationFrame(() => viewMenu.classList.add("open"));
      viewTrigger.setAttribute("aria-expanded", "true");
      if (focusActive) viewMenu.querySelector(".tab-button.active")?.focus();
    };
    // setTab closes the menu after its event handlers have been installed.
    window.closeSatlinkViewMenu = closeViewMenu;
    viewTrigger?.addEventListener("click", () => viewMenu.hidden ? openViewMenu() : closeViewMenu());
    viewTrigger?.addEventListener("keydown", (event) => {
      if (["ArrowDown", "Enter", " "].includes(event.key)) { event.preventDefault(); openViewMenu(true); }
      if (event.key === "Escape") closeViewMenu();
    });
    viewMenu?.querySelectorAll(".tab-button").forEach((button) => {
      button.addEventListener("click", () => setTab(button.dataset.tab));
      button.addEventListener("keydown", (event) => {
        const options = [...viewMenu.querySelectorAll(".tab-button")];
        const index = options.indexOf(button);
        let next = null;
        if (event.key === "ArrowDown") next = (index + 1) % options.length;
        if (event.key === "ArrowUp") next = (index - 1 + options.length) % options.length;
        if (event.key === "Home") next = 0;
        if (event.key === "End") next = options.length - 1;
        if (next !== null) { event.preventDefault(); options[next].focus(); }
        if (event.key === "Escape") { event.preventDefault(); closeViewMenu(); viewTrigger.focus(); }
      });
    });
    document.addEventListener("pointerdown", (event) => { if (viewMenu && !viewMenu.contains(event.target) && !viewTrigger.contains(event.target)) closeViewMenu(); });
    const closeSidebar = () => {
      document.body.classList.add("sidebar-collapsed"); $("#sidebar").classList.add("hidden"); $("#sidebar-open").classList.add("visible");
      $("#sidebar-open").setAttribute("aria-expanded", "false"); $("#sidebar-close").setAttribute("aria-expanded", "false"); $("#sidebar-open").focus();
    };
    const openSidebar = () => {
      document.body.classList.remove("sidebar-collapsed"); $("#sidebar").classList.remove("hidden"); $("#sidebar-open").classList.remove("visible");
      $("#sidebar-open").setAttribute("aria-expanded", "true"); $("#sidebar-close").setAttribute("aria-expanded", "true"); $("#sidebar-close").focus();
    };
    // Keep the mission controls available as a compact drawer so the orbital canvas owns the stage.
    document.body.classList.add("sidebar-collapsed");
    $("#sidebar").classList.add("hidden");
    $("#sidebar-open").classList.add("visible");
    $("#sidebar-open").setAttribute("aria-expanded", "false");
    $("#sidebar-close").setAttribute("aria-expanded", "false");
    $("#sidebar-close").addEventListener("click", closeSidebar);
    $("#sidebar-open").addEventListener("click", openSidebar);
    $("#sidebar-open").addEventListener("pointerdown", (event) => {
      if (event.button === 0) openSidebar();
    });
    window.addEventListener("keydown", (event) => { if (event.key === "Escape" && viewMenu && !viewMenu.hidden) { closeViewMenu(); return; } if (event.key === "Escape" && !$("#sidebar").classList.contains("hidden")) closeSidebar(); });
    $("#group-select").addEventListener("change", async (event) => {
      const previousGroup = state.group;
      state.group = event.target.value;
      $("#satellite-search").value = "";
      try { await loadCatalog(); }
      catch (error) {
        if (error.name !== "AbortError") { state.group = previousGroup; event.target.value = previousGroup; showNotice(error.message, "error"); }
      }
    });
    $("#satellite-search").addEventListener("input", () => {
      window.clearTimeout(state.catalogTimer);
      state.catalogTimer = window.setTimeout(() => loadCatalog({ searchOnly: true }), 250);
    });
    $("#satellite-select").addEventListener("change", (event) => { state.name = event.target.value; rememberSelection(); loadMission(); });
    $("#elevation-mask").addEventListener("input", (event) => { $("#elevation-value").value = `${event.target.value}°`; });
    ["#latitude", "#longitude", "#altitude", "#elevation-mask"].forEach((selector) => $(selector).addEventListener("change", () => loadMission()));
    document.querySelectorAll("[data-step]").forEach((button) => button.addEventListener("click", () => {
      const input = $(`#${button.dataset.target}`), increment = Number(button.dataset.increment || input.step || 1);
      const decimals = Math.max((input.value.split(".")[1] || "").length, (String(increment).split(".")[1] || "").length);
      const step = increment * (button.dataset.step === "+" ? 1 : -1);
      const next = Math.max(Number(input.min), Math.min(Number(input.max), Number(input.value || 0) + step));
      input.value = decimals ? next.toFixed(decimals) : String(next);
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }));
    $("#rf-form").addEventListener("submit", (event) => { event.preventDefault(); calculateRf(); });
    $("#rf-form").addEventListener("input", () => {
      window.clearTimeout(state.rfTimer);
      state.rfTimer = window.setTimeout(calculateRf, 450);
    });
    $("#geolocate").addEventListener("click", () => {
      const button = $("#geolocate"), label = $("#location-label"), icon = button.querySelector(".location-icon"), status = $("#location-status");
      const showError = (message) => {
        button.disabled = false;
        button.classList.remove("is-loading", "is-success");
        button.setAttribute("aria-busy", "false");
        label.textContent = button.classList.contains("using") ? "Ubicación activa" : "Usar mi ubicación";
        icon.textContent = button.classList.contains("using") ? "✓" : "⌖";
        status.textContent = message;
        status.classList.add("is-error");
        status.hidden = false;
      };
      if (!navigator.geolocation) { showError("Este navegador no admite geolocalización."); return; }
      status.hidden = true;
      status.classList.remove("is-error");
      button.disabled = true;
      button.classList.remove("using", "is-success");
      button.classList.add("is-loading");
      button.setAttribute("aria-busy", "true");
      label.textContent = "Localizando…";
      icon.textContent = "";
      navigator.geolocation.getCurrentPosition((position) => {
        $("#latitude").value = position.coords.latitude.toFixed(4); $("#longitude").value = position.coords.longitude.toFixed(4);
        if (position.coords.altitude !== null) $("#altitude").value = position.coords.altitude.toFixed(0);
        button.disabled = false;
        button.classList.remove("is-loading");
        button.classList.add("using", "is-success");
        button.setAttribute("aria-busy", "false");
        icon.textContent = "✓";
        label.textContent = "Ubicación activa";
        window.setTimeout(() => button.classList.remove("is-success"), 1100);
        loadMission();
      }, (error) => {
        showError(error.code === 1 ? "Permite el acceso a la ubicación en el navegador." : "No se pudo obtener la ubicación actual.");
      }, { enableHighAccuracy: true, timeout: 10000 });
    });
    $("#tracker-canvas").addEventListener("wheel", (event) => {
      event.preventDefault();
      const bounds = event.currentTarget.getBoundingClientRect(), x = event.clientX - bounds.left, y = event.clientY - bounds.top, m = state.map;
      const nextZoom = Math.max(1, Math.min(8, m.zoom * (event.deltaY < 0 ? 1.15 : 1 / 1.15)));
      if (nextZoom === 1) { m.zoom = 1; m.x = 0; m.y = 0; }
      else { m.x = x - (x - m.x) * (nextZoom / m.zoom); m.y = y - (y - m.y) * (nextZoom / m.zoom); m.zoom = nextZoom; clampMap(); }
      drawTracker();
    }, { passive: false });
    const globeCanvas = $("#globe-canvas");
    globeCanvas.addEventListener("pointerdown", (event) => { const c = state.globe; c.dragging = true; c.lastX = event.clientX; c.lastY = event.clientY; globeCanvas.setPointerCapture(event.pointerId); });
    globeCanvas.addEventListener("pointermove", (event) => { const c = state.globe; if (!c.dragging) return; c.longitude += (event.clientX - c.lastX) * .008; c.tilt = Math.max(-1.35, Math.min(1.35, c.tilt + (event.clientY - c.lastY) * .006)); c.lastX = event.clientX; c.lastY = event.clientY; if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) drawGlobe(performance.now()); });
    const finishDrag = () => { state.globe.dragging = false; };
    globeCanvas.addEventListener("pointerup", finishDrag); globeCanvas.addEventListener("pointercancel", finishDrag);
    window.addEventListener("resize", resizeTracker);
  }

  function updateClock() {
    $("#hud-clock").textContent = `${new Date().toISOString().slice(11, 19)} UTC`;
    const topbarClock = $("#topbar-clock");
    if (topbarClock) topbarClock.textContent = `${new Date().toISOString().slice(11, 16)} UTC`;
    if (state.countdownTarget) {
      const seconds = Math.max(0, state.countdownTarget - Math.floor(Date.now() / 1000));
      if (seconds === 0) loadMission();
      else if (state.mission?.pass_status.active) $("#hud-countdown").textContent = `PASE ACTIVO (${Math.floor(seconds / 60)}m ${seconds % 60}s)`;
      else { const hours = Math.floor(seconds / 3600), minutes = Math.floor((seconds % 3600) / 60), rest = seconds % 60; $("#hud-countdown").textContent = `T- ${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`; }
    }
  }

  setupEvents();
  try { window.sessionStorage.setItem("satlinkActiveView", state.tab); } catch (_) {}
  if (state.tab !== "globe") setTab(state.tab);
  updateClock();
  window.setInterval(updateClock, 1000);
  window.setInterval(() => { if (["tracker", "globe"].includes(state.tab)) loadMission(); }, 10000);
  Promise.all([loadWorld(), loadLand()]).then(() => {
    if (state.tab === "globe") drawGlobe(performance.now());
    else if (state.tab === "tracker") drawTracker();
  }).catch(() => {});
  loadCatalog().catch((error) => showNotice(`No se pudieron cargar los satélites: ${error.message}`, "error"));
})();
