(() => {
  const $ = (selector) => document.querySelector(selector);
  const stage = $("#radar-stage"), canvas = $("#radar-canvas");
  if (!stage || !canvas) return;
  const context = canvas.getContext("2d", { alpha: false });
  const colors = { stations: "#e5fb9a", starlink: "#78e2ee", geo: "#bca9ff", active: "#89a8c5" };
  const groups = Object.keys(colors);
  const maxZoom = 64;
  const groupNames = { stations: "GRUPO ESTACIONES", starlink: "STARLINK", geo: "ÓRBITA GEO", active: "SATÉLITE ACTIVO" };
  const radar = {
    active: false, visibleGroups: new Set(groups), satellites: [], filtered: [], searchOpen: false, world: null, worldLoading: null,
    sourceNote: "",
    selectedId: null, selectionDismissed: false, hoverId: null, points: [], track: null, trackAt: 0, trackController: null,
    request: null, serial: 0, timer: 0, frame: 0,
    map: { width: 0, height: 0, scale: 1, zoom: 1, panX: 0, panY: 0, initialized: false },
    drag: null,
  };

  function status(message) { $("#radar-status").textContent = message; }
  function format(value, digits = 1) { return Number(value).toLocaleString("es-ES", { minimumFractionDigits: digits, maximumFractionDigits: digits }); }
  function groupColor(group) { return colors[group] || colors.active; }
  function selectedSatellite() { return radar.satellites.find((satellite) => satellite.id === radar.selectedId); }
  function visibleSatellites() { return radar.satellites.filter((satellite) => radar.visibleGroups.has(satellite.group)); }
  function updateZoomLabel() { $("#radar-zoom-label").textContent = `${format(radar.map.zoom, radar.map.zoom < 10 ? 1 : 0)}×`; }

  function syncGroups() {
    document.querySelectorAll("[data-radar-group]").forEach((button) => {
      const group = button.dataset.radarGroup;
      const active = group === "all" ? radar.visibleGroups.size === groups.length : radar.visibleGroups.has(group);
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    document.querySelectorAll("[data-radar-legend]").forEach((item) => {
      item.classList.toggle("is-off", !radar.visibleGroups.has(item.dataset.radarLegend));
    });
  }

  function updateVisibility() {
    const visible = visibleSatellites();
    $("#radar-total").textContent = visible.length.toLocaleString("es-ES");
    $("#radar-empty").hidden = radar.visibleGroups.size > 0;
    const selected = radar.selectionDismissed ? null : (
      visible.find((satellite) => satellite.id === radar.selectedId)
      || visible.find((satellite) => satellite.id === 25544)
      || visible[0]
    );
    if (selected) selectSatellite(selected);
    else clearSelection();
    $("#radar-hover").hidden = true;
    radar.hoverId = null;
    renderResults();
    if (!$("#radar-search").value.trim()) status(`${visible.length.toLocaleString("es-ES")} visibles de ${radar.satellites.length.toLocaleString("es-ES")} posiciones calculadas · próxima actualización en 10 s${radar.sourceNote}`);
    scheduleDraw();
  }

  function resize() {
    if (!radar.active) return;
    const width = Math.round(canvas.clientWidth), height = Math.round(canvas.clientHeight);
    if (!width || !height) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.6);
    const pixelWidth = Math.round(width * dpr), pixelHeight = Math.round(height * dpr);
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) { canvas.width = pixelWidth; canvas.height = pixelHeight; }
    radar.map.width = width;
    radar.map.height = height;
    radar.map.scale = Math.min(width / 360, height / 180) * .96;
    if (!radar.map.initialized) {
      radar.map.zoom = width < 680 ? 1.55 : 1;
      radar.map.initialized = true;
    }
    clampPan();
    updateZoomLabel();
    scheduleDraw();
  }

  function project(longitude, latitude) {
    const { width, height, scale, zoom, panX, panY } = radar.map;
    return [width / 2 + panX + longitude * scale * zoom, height / 2 + panY - latitude * scale * zoom];
  }

  function unproject(x, y) {
    const { width, height, scale, zoom, panX, panY } = radar.map;
    return [(x - width / 2 - panX) / (scale * zoom), -(y - height / 2 - panY) / (scale * zoom)];
  }

  function clampPan() {
    const map = radar.map;
    const horizontal = Math.max(0, (360 * map.scale * map.zoom - map.width) / 2);
    const vertical = Math.max(0, (180 * map.scale * map.zoom - map.height) / 2);
    map.panX = Math.max(-horizontal, Math.min(horizontal, map.panX));
    map.panY = Math.max(-vertical, Math.min(vertical, map.panY));
  }

  function zoomAt(factor, x = radar.map.width / 2, y = radar.map.height / 2) {
    const [longitude, latitude] = unproject(x, y);
    radar.map.zoom = Math.max(1, Math.min(maxZoom, radar.map.zoom * factor));
    const [newX, newY] = project(longitude, latitude);
    radar.map.panX += x - newX;
    radar.map.panY += y - newY;
    clampPan();
    updateZoomLabel();
    scheduleDraw();
  }

  function scheduleDraw() {
    if (!radar.active || radar.frame) return;
    radar.frame = requestAnimationFrame(() => { radar.frame = 0; draw(); });
  }

  function drawWorld() {
    if (!radar.world) return;
    context.beginPath();
    for (const feature of radar.world.features || []) {
      const geometry = feature.geometry;
      if (!geometry) continue;
      const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.type === "MultiPolygon" ? geometry.coordinates : [];
      for (const polygon of polygons) {
        for (const ring of polygon) {
          let previousLongitude = null;
          for (const [longitude, latitude] of ring) {
            const [x, y] = project(longitude, latitude);
            if (previousLongitude === null || Math.abs(longitude - previousLongitude) > 180) context.moveTo(x, y);
            else context.lineTo(x, y);
            previousLongitude = longitude;
          }
          context.closePath();
        }
      }
    }
    context.fillStyle = "rgba(19, 54, 72, .92)";
    context.fill("evenodd");
    context.strokeStyle = "rgba(116, 191, 207, .34)";
    context.lineWidth = .85;
    context.stroke();
  }

  function drawTrack() {
    if (!radar.track?.length) return;
    context.beginPath();
    let previous = null;
    for (const point of radar.track) {
      const [x, y] = project(point.longitude, point.latitude);
      if (previous === null || Math.abs(point.longitude - previous) > 180) context.moveTo(x, y);
      else context.lineTo(x, y);
      previous = point.longitude;
    }
    context.setLineDash([5, 5]);
    context.strokeStyle = "rgba(175, 246, 245, .7)";
    context.lineWidth = 1.3;
    context.shadowColor = "rgba(107, 238, 238, .65)";
    context.shadowBlur = 8;
    context.stroke();
    context.shadowBlur = 0;
    context.setLineDash([]);
  }

  function draw() {
    const { width, height } = radar.map;
    if (!width || !height) return;
    const dpr = canvas.width / width;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    const ocean = context.createRadialGradient(width * .53, height * .43, 0, width * .5, height * .5, Math.max(width, height) * .78);
    ocean.addColorStop(0, "#10324b"); ocean.addColorStop(.55, "#081e32"); ocean.addColorStop(1, "#051320");
    context.fillStyle = ocean;
    context.fillRect(0, 0, width, height);

    context.lineWidth = 1;
    context.strokeStyle = "rgba(98, 163, 190, .12)";
    context.beginPath();
    for (let longitude = -180; longitude <= 180; longitude += 30) {
      const [x, top] = project(longitude, 90), [, bottom] = project(longitude, -90);
      context.moveTo(x, top); context.lineTo(x, bottom);
    }
    for (let latitude = -90; latitude <= 90; latitude += 30) {
      const [left, y] = project(-180, latitude), [right] = project(180, latitude);
      context.moveTo(left, y); context.lineTo(right, y);
    }
    context.stroke();
    drawWorld();
    drawTrack();

    const grouped = { stations: [], starlink: [], geo: [], active: [] };
    radar.points = [];
    for (const satellite of radar.filtered) {
      const [x, y] = project(satellite.longitude, satellite.latitude);
      if (x < -8 || x > width + 8 || y < -8 || y > height + 8) continue;
      const point = { x, y, satellite };
      radar.points.push(point);
      (grouped[satellite.group] || grouped.active).push(point);
    }
    const radius = Math.min(3.1, 1 + Math.log2(radar.map.zoom) * .36);
    for (const [group, points] of Object.entries(grouped)) {
      if (!points.length) continue;
      context.beginPath();
      for (const point of points) {
        context.moveTo(point.x + radius, point.y);
        context.arc(point.x, point.y, radius, 0, Math.PI * 2);
      }
      context.fillStyle = groupColor(group);
      context.globalAlpha = group === "active" ? .69 : .82;
      if (radar.map.zoom >= 8) { context.shadowColor = groupColor(group); context.shadowBlur = 6; }
      context.fill();
      context.shadowBlur = 0;
      if (radar.map.zoom >= 5) {
        context.strokeStyle = "rgba(233, 252, 255, .32)";
        context.lineWidth = .65;
        context.stroke();
      }
    }
    context.globalAlpha = 1;
    const selectedPoint = radar.points.find((point) => point.satellite.id === radar.selectedId);
    const ring = $("#radar-selected-ring");
    ring.hidden = !selectedPoint;
    if (selectedPoint) {
      context.beginPath(); context.arc(selectedPoint.x, selectedPoint.y, 4.5, 0, Math.PI * 2);
      context.fillStyle = "#efffff"; context.shadowColor = groupColor(selectedPoint.satellite.group); context.shadowBlur = 22;
      context.fill(); context.shadowBlur = 0;
      ring.style.left = `${selectedPoint.x}px`; ring.style.top = `${selectedPoint.y}px`;
    }
  }

  function nearest(x, y) {
    let best = null, distance = 100;
    for (const point of radar.points) {
      const dx = point.x - x, dy = point.y - y, squared = dx * dx + dy * dy;
      if (squared < distance) { best = point; distance = squared; }
    }
    return best;
  }

  function renderDetail() {
    const satellite = selectedSatellite(), detail = $("#radar-detail");
    detail.hidden = !satellite;
    if (!satellite) return;
    $("#radar-detail-group").textContent = groupNames[satellite.group] || groupNames.active;
    $("#radar-detail-name").textContent = satellite.name;
    $("#radar-detail-id").textContent = `NORAD ${satellite.id} · TLE ${format(satellite.tle_age_days)} DÍAS`;
    $("#radar-detail-lat").textContent = `${format(satellite.latitude, 3)}°`;
    $("#radar-detail-lon").textContent = `${format(satellite.longitude, 3)}°`;
    $("#radar-detail-alt").textContent = `${format(satellite.altitude_km, 0)} km`;
    $("#radar-detail-speed").textContent = `${format(satellite.speed_km_s, 2)} km/s`;
    $("#radar-detail-inc").textContent = `${format(satellite.inclination_deg)}°`;
    $("#radar-detail-period").textContent = satellite.period_min ? `${format(satellite.period_min)} min` : "—";
  }

  function clearSelection() {
    radar.trackController?.abort();
    radar.track = null;
    radar.trackAt = 0;
    radar.selectedId = null;
    renderDetail();
    $("#radar-selected-ring").hidden = true;
    scheduleDraw();
  }

  async function loadTrack(satellite) {
    radar.trackController?.abort();
    const controller = new AbortController();
    radar.trackController = controller;
    radar.track = null;
    const params = new URLSearchParams({ group: satellite.group, name: satellite.name, include_track: "true" });
    try {
      const response = await fetch(`/api/mission?${params}`, { signal: controller.signal });
      if (!response.ok) return;
      const mission = await response.json();
      if (radar.selectedId !== satellite.id || controller.signal.aborted) return;
      radar.track = mission.track || null;
      radar.trackAt = Date.now();
      scheduleDraw();
    } catch (error) { if (error.name !== "AbortError") radar.track = null; }
  }

  function selectSatellite(satellite, { center = false } = {}) {
    if (!satellite) return;
    radar.selectionDismissed = false;
    const changed = radar.selectedId !== satellite.id;
    radar.selectedId = satellite.id;
    if (center) {
      const [x, y] = project(satellite.longitude, satellite.latitude);
      radar.map.panX += radar.map.width * .42 - x;
      radar.map.panY += radar.map.height * .5 - y;
      clampPan();
    }
    renderDetail();
    scheduleDraw();
    if (changed || Date.now() - radar.trackAt > 5 * 60 * 1000) loadTrack(satellite);
  }

  function renderResults() {
    const query = $("#radar-search").value.trim().toLocaleLowerCase("es-ES");
    const visible = visibleSatellites();
    radar.filtered = query ? visible.filter((satellite) => satellite.name.toLocaleLowerCase("es-ES").includes(query) || String(satellite.id).includes(query)) : visible;
    const results = $("#radar-results");
    results.hidden = !query || !radar.searchOpen;
    if (query) {
      const buttons = radar.filtered.slice(0, 8).map((satellite) => {
        const button = document.createElement("button");
        button.type = "button"; button.className = "radar-result";
        const name = document.createElement("strong"), id = document.createElement("small");
        name.textContent = satellite.name; id.textContent = `#${satellite.id}`;
        button.append(name, id);
        button.addEventListener("click", () => {
          selectSatellite(satellite, { center: true });
          radar.searchOpen = false;
          results.hidden = true;
          $("#radar-search").blur();
        });
        return button;
      });
      if (buttons.length) results.replaceChildren(...buttons);
      else {
        const empty = document.createElement("p");
        empty.className = "radar-no-results";
        empty.textContent = "Sin coincidencias en los grupos visibles.";
        results.replaceChildren(empty);
      }
    }
    scheduleDraw();
    if (query) status(`${format(radar.filtered.length, 0)} coincidencias en el catálogo.`);
  }

  async function loadWorld() {
    if (radar.world || radar.worldLoading) return radar.worldLoading;
    radar.worldLoading = fetch("/assets/world_110m_admin_0_countries.geojson")
      .then((response) => { if (!response.ok) throw new Error("No se pudo cargar el mapa"); return response.json(); })
      .then((world) => { radar.world = world; scheduleDraw(); return world; })
      .catch(() => { radar.worldLoading = null; });
    return radar.worldLoading;
  }

  async function refresh() {
    if (!radar.active) return;
    window.clearTimeout(radar.timer);
    radar.request?.abort();
    const controller = new AbortController(), serial = ++radar.serial;
    radar.request = controller;
    if (!radar.satellites.length) status("Sincronizando posiciones orbitales…");
    try {
      const response = await fetch("/api/radar?group=all", { signal: controller.signal });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `Error ${response.status}`);
      if (serial !== radar.serial || !radar.active) return;
      radar.satellites = result.satellites || [];
      $("#radar-timestamp").textContent = `${new Date(result.generated_at).toISOString().slice(11, 19)} UTC · ACTUALIZADO`;
      const unavailable = result.unavailable_groups?.length ? ` · grupos no disponibles: ${result.unavailable_groups.join(", ")}` : "";
      const stale = result.stale ? " · TLE de respaldo: precisión reducida" : "";
      radar.sourceNote = `${stale}${unavailable}`;
      updateVisibility();
    } catch (error) {
      if (error.name !== "AbortError" && serial === radar.serial) status(`No se pudieron actualizar las posiciones: ${error.message}. Reintentando…`);
    } finally {
      if (serial === radar.serial && radar.active) radar.timer = window.setTimeout(refresh, 10000);
    }
  }

  function activate() {
    if (radar.active) return;
    radar.active = true;
    requestAnimationFrame(resize);
    loadWorld();
    refresh();
  }

  function deactivate() {
    radar.active = false;
    window.clearTimeout(radar.timer);
    radar.request?.abort();
    radar.trackController?.abort();
    if (radar.frame) cancelAnimationFrame(radar.frame);
    radar.frame = 0;
    $("#radar-hover").hidden = true;
  }

  function pointerPosition(event) {
    const bounds = canvas.getBoundingClientRect();
    return [event.clientX - bounds.left, event.clientY - bounds.top];
  }

  canvas.addEventListener("pointerdown", (event) => {
    const [x, y] = pointerPosition(event);
    radar.drag = { x, y, panX: radar.map.panX, panY: radar.map.panY, moved: false };
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!radar.active) return;
    const [x, y] = pointerPosition(event);
    if (radar.drag) {
      const dx = x - radar.drag.x, dy = y - radar.drag.y;
      if (Math.hypot(dx, dy) > 4) radar.drag.moved = true;
      if (radar.drag.moved) {
        radar.map.panX = radar.drag.panX + dx;
        radar.map.panY = radar.drag.panY + dy;
        clampPan(); scheduleDraw();
      }
      return;
    }
    const [longitude, latitude] = unproject(x, y);
    $("#radar-coordinates").textContent = `${format(latitude, 2)}° / ${format(longitude, 2)}°`;
    const point = nearest(x, y), hover = $("#radar-hover");
    radar.hoverId = point?.satellite.id || null;
    hover.hidden = !point;
    canvas.style.cursor = point ? "pointer" : "crosshair";
    if (point) {
      const label = document.createElement("strong"), meta = document.createElement("small");
      label.textContent = point.satellite.name;
      meta.textContent = `NORAD ${point.satellite.id} · ${format(point.satellite.altitude_km, 0)} km`;
      hover.replaceChildren(label, meta);
      hover.style.left = `${Math.min(x, radar.map.width - 225)}px`;
      hover.style.top = `${Math.max(y, 55)}px`;
    }
  });
  canvas.addEventListener("pointerup", (event) => {
    if (!radar.drag) return;
    const moved = radar.drag.moved;
    radar.drag = null;
    if (!moved) {
      const [x, y] = pointerPosition(event);
      const point = nearest(x, y);
      if (point) selectSatellite(point.satellite);
    }
  });
  canvas.addEventListener("pointercancel", () => { radar.drag = null; });
  canvas.addEventListener("pointerleave", () => { if (!radar.drag) $("#radar-hover").hidden = true; });
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const [x, y] = pointerPosition(event);
    zoomAt(event.deltaY < 0 ? 1.18 : 1 / 1.18, x, y);
  }, { passive: false });

  $("#radar-zoom-in").addEventListener("click", () => zoomAt(1.35));
  $("#radar-zoom-out").addEventListener("click", () => zoomAt(1 / 1.35));
  $("#radar-reset").addEventListener("click", () => {
    radar.map.zoom = radar.map.width < 680 ? 1.55 : 1;
    radar.map.panX = 0; radar.map.panY = 0; updateZoomLabel(); scheduleDraw();
  });
  $("#radar-search").addEventListener("focus", () => { radar.searchOpen = true; renderResults(); });
  $("#radar-search").addEventListener("input", () => { radar.searchOpen = true; renderResults(); });
  $("#radar-search").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && radar.filtered[0]) {
      event.preventDefault(); selectSatellite(radar.filtered[0], { center: true });
      radar.searchOpen = false; $("#radar-results").hidden = true; event.currentTarget.blur();
    }
    if (event.key === "Escape") { event.currentTarget.value = ""; renderResults(); }
  });
  document.addEventListener("pointerdown", (event) => {
    if (!event.target.closest(".radar-search-wrap")) {
      radar.searchOpen = false;
      $("#radar-results").hidden = true;
    }
  });
  window.addEventListener("keydown", (event) => {
    if (radar.active && event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
      event.preventDefault(); $("#radar-search").focus();
    }
  });
  document.querySelectorAll("[data-radar-group]").forEach((button) => button.addEventListener("click", () => {
    const group = button.dataset.radarGroup;
    if (group === "all") radar.visibleGroups = new Set(groups);
    else if (radar.visibleGroups.has(group)) radar.visibleGroups.delete(group);
    else radar.visibleGroups.add(group);
    syncGroups();
    updateVisibility();
  }));
  $("#radar-close-detail").addEventListener("click", () => {
    radar.selectionDismissed = true;
    clearSelection();
  });
  $("#radar-open-satellite").addEventListener("click", () => {
    const satellite = selectedSatellite();
    if (satellite) window.dispatchEvent(new CustomEvent("satlink:open-satellite", { detail: { group: satellite.group, name: satellite.name } }));
  });
  new ResizeObserver(resize).observe(stage);
  window.SatRadar = { activate, deactivate };
})();
