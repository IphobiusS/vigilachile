const API = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000"
  : "https://vigilachile-api.onrender.com";
const tooltip = document.getElementById("tooltip");
const detailPanel = document.getElementById("detail-panel");
const detailContent = document.getElementById("detail-content");

const map = L.map("map", { zoomControl: true });
map.setView([-33.5, -70.5], 5);

// ===== MOBILE MENU =====
(function() {
  var menuBtn = document.getElementById("mobile-menu-btn");
  var sidebar = document.getElementById("sidebar");
  var overlay = document.getElementById("mobile-overlay");
  function openMenu() {
    sidebar.classList.add("open");
    overlay.classList.add("visible");
    overlay.classList.remove("hidden");
    menuBtn.textContent = "✕";
  }
  function closeMenu() {
    sidebar.classList.remove("open");
    overlay.classList.remove("visible");
    overlay.classList.add("hidden");
    menuBtn.textContent = "☰";
    map.invalidateSize();
  }
  menuBtn.addEventListener("click", function() {
    if (sidebar.classList.contains("open")) closeMenu();
    else openMenu();
  });
  overlay.addEventListener("click", closeMenu);
  // Close sidebar when selecting a commune on mobile
  window.closeMobileMenu = closeMenu;
})();

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: "©OpenStreetMap ©CartoDB",
  maxZoom: 18
}).addTo(map);

// ===== LOADING HELPER =====
function showLoading(containerId, message, submessage) {
  var el = document.getElementById(containerId);
  if (!el) return;
  el.style.display = "flex";
  el.style.alignItems = "center";
  el.style.justifyContent = "center";
  el.style.minHeight = "200px";
  el.innerHTML =
    "<div style='display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px 20px;grid-column:1/-1'>" +
    "<div style='width:36px;height:36px;border:3px solid #1e2d4a;border-top:3px solid #4fc3f7;border-radius:50%;animation:spin 0.8s linear infinite'></div>" +
    "<div style='font-size:0.85rem;color:#8a9bbc;text-align:center'>" + (message || "Cargando...") + "</div>" +
    (submessage ? "<div style='font-size:0.72rem;color:#4a6080;text-align:center'>" + submessage + "</div>" : "") +
    "<div style='width:180px;height:4px;background:#1e2d4a;border-radius:2px;overflow:hidden'>" +
    "<div style='height:100%;background:#4fc3f7;border-radius:2px;animation:loadbar 2s ease-in-out infinite'></div>" +
    "</div>" +
    "</div>";
}

// Add keyframes dynamically
(function() {
  var style = document.createElement("style");
  style.textContent = "@keyframes spin{to{transform:rotate(360deg)}} @keyframes loadbar{0%{width:0;margin-left:0}50%{width:60%;margin-left:20%}100%{width:0;margin-left:100%}}";
  document.head.appendChild(style);
})();

let fireLayer = L.layerGroup().addTo(map);
let quakeLayer = L.layerGroup().addTo(map);
let riskLayer = L.layerGroup().addTo(map);
let volcanoLayer = L.layerGroup().addTo(map);
let regionLayer = L.layerGroup().addTo(map);
let aftershockLayer = null;
let heatLayer = null;
let userMarker = null;
let userLocation = null;
let allQuakes = [];
let allMarkers = [];
let minMag = 2.5;
let activeMarker = null;
let voiceEnabled = false;
let lastAnnouncedQuake = null;
let cachedAIReport = "";
let cachedRegions = [];
let kioskInterval = null;
let kioskDataInterval = null;
let liveInterval = null;
let aiCollapsed = false;
let statsCharts = {};
let lastQuakeTime = null;
let alertsSentThisSession = new Set();

// ===== RESUMEN AMENAZAS =====
let cachedVolcanoes = [];
let cachedTsunamiData = { count: 0 };
let cachedWeatherSummary = null;


const riskZones = [
  { lat: -36.0, lon: -72.5, label: "Zona Biobío — Alto riesgo sísmico", radius: 120000, color: "#ff3333" },
  { lat: -30.0, lon: -71.5, label: "Zona Coquimbo — Alto riesgo sísmico", radius: 100000, color: "#ff3333" },
  { lat: -20.0, lon: -70.2, label: "Zona Tarapacá — Alto riesgo sísmico", radius: 100000, color: "#ffd700" },
  { lat: -38.5, lon: -73.0, label: "Zona Araucanía — Riesgo incendios + sismos", radius: 90000, color: "#ff6b35" },
  { lat: -33.5, lon: -71.8, label: "Zona Valparaíso — Riesgo costero + tsunami", radius: 80000, color: "#ffd700" },
  { lat: -23.5, lon: -70.4, label: "Zona Antofagasta — Riesgo sísmico costero", radius: 90000, color: "#ffd700" },
];

const legend = L.control({ position: "bottomright" });
legend.onAdd = function() {
  const div = L.DomUtil.create("div", "legend");
  div.innerHTML =
    "<div class='legend-title'>🗺️ Leyenda</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#ff6b35'></span> Foco de calor</div>" +
    "<div class='legend-section'>Sismos por magnitud</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#4ade80'></span> M &lt; 4.5</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#ffd700'></span> M 4.5 – 6.0</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#ff3333'></span> M &gt; 6.0</div>" +
    "<div class='legend-section'>Volcanes</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#ffd700'></span> Alerta Amarilla</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#4ade80'></span> Alerta Verde</div>" +
    "<div class='legend-section'>Semáforo regiones</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#ff3333'></span> Alerta Roja</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#ff9500'></span> Alerta Naranja</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#ffd700'></span> Alerta Amarilla</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#4ade80'></span> Alerta Verde</div>" +
    "<div class='legend-item'><span class='legend-dot' style='background:#ffffff'></span> Sin Actividad</div>";
  return div;
};
legend.addTo(map);

function renderRiskZones() {
  riskZones.forEach(function(z) {
    L.circle([z.lat, z.lon], {
      radius: z.radius, fillColor: z.color, color: z.color,
      weight: 1, opacity: 0.4, fillOpacity: 0.08
    }).bindTooltip("⚠️ " + z.label, { sticky: true }).addTo(riskLayer);
  });
}

function showTooltip(e, html) {
  tooltip.innerHTML = html;
  tooltip.style.display = "block";
  tooltip.style.left = e.originalEvent.pageX + 14 + "px";
  tooltip.style.top = e.originalEvent.pageY + 14 + "px";
}
function hideTooltip() { tooltip.style.display = "none"; }

function timeAgo(utcString) {
  if (!utcString) return "";
  const then = new Date(utcString.replace(" ", "T") + "Z");
  const diff = Math.floor((Date.now() - then.getTime()) / 1000);
  if (diff < 0) return "ahora mismo";
  if (diff < 60) return "hace " + diff + " seg";
  if (diff < 3600) return "hace " + Math.floor(diff / 60) + " min";
  if (diff < 86400) return "hace " + Math.floor(diff / 3600) + "h " + Math.floor((diff % 3600) / 60) + "min";
  return "hace " + Math.floor(diff / 86400) + " días";
}

function utcToChile(utcString) {
  if (!utcString) return "--";
  const d = new Date(utcString.replace(" ", "T") + "Z");
  return d.toLocaleString("es-CL", {
    timeZone: "America/Santiago",
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  });
}

function isWithin24h(utcString) {
  if (!utcString) return false;
  const then = new Date(utcString.replace(" ", "T") + "Z");
  return (Date.now() - then.getTime()) < 86400000;
}

function tsunamiRisk(q) {
  if (q.magnitude < 6.5) return null;
  if (q.lon > -71.5) return null;
  return "🌊 ALERTA TSUNAMI POSIBLE — Sismo M" + q.magnitude + " en zona costera. Aléjese de la costa.";
}

function prepInfo(q) {
  if (q.magnitude < 4.0) return null;
  const guides = [
    "🏠 Identifica zonas seguras en tu hogar (bajo mesas, lejos de ventanas)",
    "🎒 Ten lista una mochila de emergencia con agua, linterna y documentos",
    "📻 Sintoniza Radio Nacional o SENAPRED en caso de corte eléctrico",
    "📍 Conoce la ruta de evacuación de tu barrio",
    "🚫 No uses ascensores tras un sismo importante"
  ];
  return guides[Math.floor(Math.random() * guides.length)];
}

// ===== TOAST NUEVO SISMO =====
function showNewQuakeToast(q) {
  const toast = document.getElementById("new-quake-toast");
  if (!toast) return;
  const color = q.magnitude >= 6 ? "#ff3333" : q.magnitude >= 4.5 ? "#ffd700" : "#4ade80";
  document.getElementById("toast-content").innerHTML =
    "⚡ <span style='color:" + color + "'>NUEVO SISMO M" + q.magnitude + "</span> — " + q.place + "<br>" +
    "<span style='font-size:0.78rem;color:#5c7a9e'>" + timeAgo(q.time) + "</span>";
  toast.classList.remove("hidden");
  setTimeout(function() { toast.classList.add("hidden"); }, 5000);
}

// ===== FEED EN VIVO =====
let liveFetchInProgress = false;
async function liveTick() {
  if (liveFetchInProgress) return;
  liveFetchInProgress = true;
  try {
    const res = await fetch(API + "/quakes");
    const json = await res.json();
    if (!json.data || json.data.length === 0) return;
    const newest = json.data[0];
    const newestTime = newest.time;
    if (lastQuakeTime && newestTime !== lastQuakeTime) {
      showNewQuakeToast(newest);
      if (voiceEnabled) speak("Nuevo sismo detectado. Magnitud " + newest.magnitude + " en " + newest.place + ".");
      allQuakes = json.data;
    cachedQuakesData = json.data;
    try { document.getElementById("qp-quakes-count").textContent = json.data.length; } catch(e) {}
    updateLastEvent();
      renderQuakes(allQuakes);
    }
    lastQuakeTime = newestTime;
    const color = newest.magnitude >= 6 ? "#ff3333" : newest.magnitude >= 4.5 ? "#ffd700" : "#4ade80";
    const liveEl = document.getElementById("live-last");
    if (liveEl) {
      liveEl.innerHTML =
        "Último: <b style='color:" + color + "'>M" + newest.magnitude + "</b> — " + newest.place + "<br>" +
        "<span style='color:#3a5270;font-size:0.68rem'>" + utcToChile(newest.time) + " · " + timeAgo(newest.time) + "</span>";
    }
  } catch(e) {
    console.error("Error en liveTick:", e);
  } finally {
    liveFetchInProgress = false;
  }
}

// ===== PANEL EVENTOS FLOTANTE =====
// Start collapsed on mobile
let eventsCollapsed = window.innerWidth <= 768;
if (eventsCollapsed) {
  document.getElementById("events-float-body").classList.add("collapsed");
  document.getElementById("events-toggle-btn").textContent = "▼";
}
document.getElementById("events-float-header").addEventListener("click", function() {
  eventsCollapsed = !eventsCollapsed;
  document.getElementById("events-float-body").classList.toggle("collapsed", eventsCollapsed);
  document.getElementById("events-toggle-btn").textContent = eventsCollapsed ? "▼" : "▲";
});

// ===== PANEL IA — DOCK INFERIOR =====
document.getElementById("ai-dock-bar").addEventListener("click", function() {
  aiCollapsed = !aiCollapsed;
  document.getElementById("ai-dock-body").classList.toggle("collapsed", aiCollapsed);
  document.getElementById("ai-dock-toggle").textContent = aiCollapsed ? "▲" : "▼";
});

if(document.getElementById("btn-ai")) document.getElementById("btn-ai").addEventListener("click", function() {
  const btn = document.getElementById("btn-ai");
  aiCollapsed = !aiCollapsed;
  document.getElementById("ai-dock-body").classList.toggle("collapsed", aiCollapsed);
  document.getElementById("ai-dock-toggle").textContent = aiCollapsed ? "▲" : "▼";
  btn.classList.toggle("active", !aiCollapsed);
});

// ===== MODO VOZ =====
function speak(text) {
  if (!voiceEnabled || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "es-CL"; utter.rate = 0.9;
  window.speechSynthesis.speak(utter);
}

if(document.getElementById("btn-voice")) document.getElementById("btn-voice").addEventListener("click", function() {
  voiceEnabled = !voiceEnabled;
  const btn = document.getElementById("btn-voice");
  btn.textContent = voiceEnabled ? "🔊" : "🔇";
  btn.classList.toggle("active", voiceEnabled);
  if (voiceEnabled) speak("Modo voz activado. VigilaChile monitoreando desastres en tiempo real.");
  else window.speechSynthesis.cancel();
});

// ===== MI UBICACIÓN =====
function distanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLon/2)**2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)));
}

if(document.getElementById("btn-location")) document.getElementById("btn-location").addEventListener("click", function() {
  if (!navigator.geolocation) return alert("Tu navegador no soporta geolocalización.");
  navigator.geolocation.getCurrentPosition(function(pos) {
    const lat = pos.coords.latitude, lon = pos.coords.longitude;
    userLocation = { lat, lon };
    if (userMarker) map.removeLayer(userMarker);
    userMarker = L.marker([lat, lon], {
      icon: L.divIcon({ className: "user-marker", iconSize: [16, 16] })
    }).addTo(map).bindPopup("📍 Tu ubicación").openPopup();
    map.setView([lat, lon], 8);
    document.getElementById("location-card").classList.remove("hidden");
    if (allQuakes.length > 0) {
      const nearest = allQuakes.reduce(function(a, b) {
        return distanceKm(lat, lon, a.lat, a.lon) < distanceKm(lat, lon, b.lat, b.lon) ? a : b;
      });
      const dist = distanceKm(lat, lon, nearest.lat, nearest.lon);
      const risk = dist < 50 ? "⚠️ Zona de riesgo" : dist < 150 ? "🟡 Precaución" : "✅ Zona segura";
      document.getElementById("location-content").innerHTML =
        "📍 <b>Tu ubicación detectada</b><br>Sismo más cercano: <b>M" + nearest.magnitude + "</b><br>" +
        nearest.place + "<br>Distancia: <b>" + dist + " km</b><br>Estado: <b>" + risk + "</b>";
      speak("Tu sismo más cercano es de magnitud " + nearest.magnitude + ", a " + dist + " kilómetros.");
    }
    if(document.getElementById("btn-location")) document.getElementById("btn-location").classList.add("active");
  }, function() { alert("No se pudo obtener tu ubicación."); });
});

// ===== COMPARTIR =====
function getShareText(q) {
  return "🚨 Sismo M" + q.magnitude + " en Chile\n📍 " + q.place + "\n🕐 " + utcToChile(q.time) + " (hora Chile)\n🌍 VigilaChile";
}

function getShareButtons(q) {
  const text = getShareText(q);
  const waUrl = "https://api.whatsapp.com/send?text=" + encodeURIComponent(text);
  const twUrl = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(text);
  return "<div class='share-row'>" +
    "<a class='share-btn' href='" + waUrl + "' target='_blank'>📲 WhatsApp</a>" +
    "<a class='share-btn twitter' href='" + twUrl + "' target='_blank'>🐦 Twitter</a>" +
    "<button class='share-btn copy' id='copy-btn'>📋 Copiar</button>" +
    "</div>";
}

if(document.getElementById("btn-share")) document.getElementById("btn-share").addEventListener("click", function() {
  const text =
    "🛰️ VigilaChile — Monitoreo de desastres naturales en tiempo real\n" +
    "📊 " + document.getElementById("quake-count").textContent + " sismos · " +
    "🔥 " + document.getElementById("fire-count").textContent + " focos activos · " +
    "🚨 Riesgo: " + document.getElementById("risk-score").textContent + "\n" +
    "🌐 https://vigilachile.vercel.app";
  if (navigator.share) {
    navigator.share({ title: "VigilaChile", text: text, url: "https://vigilachile.vercel.app" }).catch(function() {});
  } else {
    navigator.clipboard.writeText(text).then(function() { alert("✅ Información copiada al portapapeles."); });
  }
});

// ===== VOLCANES =====
async function loadVolcanoes() {
  volcanoLayer.clearLayers();
  try {
    const res = await fetch(API + "/volcanoes");
    const json = await res.json();
    json.data.forEach(function(v) {
      const color = v.alert === "Roja" ? "#ff3333" : v.alert === "Naranja" ? "#ff9500" : v.alert === "Amarilla" ? "#ffd700" : "#4ade80";
      const icon = L.divIcon({
        className: "",
        html: "<div style='width:14px;height:14px;background:" + color + ";border:2px solid white;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 0 6px " + color + "'></div>",
        iconSize: [14, 14], iconAnchor: [7, 14]
      });
      L.marker([v.lat, v.lon], { icon: icon })
        .bindTooltip(
          "<b>🌋 " + v.name + "</b><br>Alerta: <span style='color:" + color + ";font-weight:700'>" + v.alert + "</span><br>" +
          "Elevación: " + v.elevation + " m<br>Región: " + v.region,
          { sticky: true }
        ).addTo(volcanoLayer);
    });
    cachedVolcanoes = json.data;
    try { document.getElementById("qp-volcanoes-count").textContent = json.data.length; } catch(e) {}
    updateLastEvent();
    updateThreatSummary();
  } catch(e) { console.error("Error volcanes:", e); }
}

document.getElementById("toggle-volcanoes").addEventListener("change", function(e) {
  e.target.checked ? volcanoLayer.addTo(map) : map.removeLayer(volcanoLayer);
});

// ===== SEMÁFORO REGIONES =====
async function loadRegions() {
  regionLayer.clearLayers();
  try {
    const res = await fetch(API + "/regions");
    const json = await res.json();
cachedRegions = json.data;
    updateThreatSummary();
    json.data.forEach(function(r) {
      L.circle([r.lat, r.lon], {
        radius: 80000, fillColor: r.color, color: r.color,
        weight: 2, opacity: 0.7, fillOpacity: 0.15
      }).bindTooltip(
        "<b>" + r.name + "</b><br>" +
        "Alerta: <span style='color:" + r.color + ";font-weight:700'>" + r.level + "</span><br>" +
        "Sismos 24h: " + r.quakes_24h + " · Últimas 6h: " + r.quakes_6h + "<br>" +
        "Mag. máx: M" + r.max_magnitude + "<br>" +
        "Score: " + r.score +
        (r.tsunami_risk ? "<br>🌊 Riesgo tsunami activo" : "") +
        (r.fires_nearby > 0 ? "<br>🔥 " + r.fires_nearby + " focos de incendio" : ""),
        { sticky: true }
      ).addTo(regionLayer);

      L.marker([r.lat, r.lon], {
        icon: L.divIcon({
          className: "",
          html: "<div style='background:" + r.color + "22;border:1px solid " + r.color + ";border-radius:8px;padding:3px 7px;font-size:0.65rem;color:" + r.color + ";font-weight:700;white-space:nowrap'>" + r.name + "</div>",
          iconAnchor: [40, 10]
        }),
        zIndexOffset: -100
      }).addTo(regionLayer);
    });
  } catch(e) { console.error("Error regiones:", e); }
}

document.getElementById("toggle-regions").addEventListener("change", function(e) {
  e.target.checked ? regionLayer.addTo(map) : map.removeLayer(regionLayer);
});

// ===== TSUNAMI =====
async function loadTsunami() {
  try {
    const res = await fetch(API + "/tsunami");
    const json = await res.json();
    if (json.count > 0) {
      const t = json.data[0];
      const textEl = document.getElementById("alert-text");
      textEl.innerHTML =
        "🌊 TSUNAMI " + t.level + " — Sismo M" + t.magnitude + " · " + t.place +
        (t.url ? " · <a href='" + t.url + "' target='_blank' style='color:#fff;text-decoration:underline'>Ver detalles</a>" : "");
      document.getElementById("alert-banner").classList.remove("hidden");
      speak("Alerta de tsunami nivel " + t.level + " por sismo de magnitud " + t.magnitude + " en " + t.place);
    }
    cachedTsunamiData = json;
    updateThreatSummary();
  } catch(e) { console.error("Error tsunami:", e); }
}

// ===== RÉPLICAS =====
async function loadAftershocks(q) {
  if (aftershockLayer) map.removeLayer(aftershockLayer);
  aftershockLayer = L.layerGroup().addTo(map);
  try {
    const res = await fetch(API + "/aftershocks/" + q.lat + "/" + q.lon);
    const json = await res.json();
    let count = 0;
    json.data.forEach(function(a) {
      if (Math.abs(a.magnitude - q.magnitude) < 0.1) return;
      count++;
      L.circleMarker([a.lat, a.lon], {
        radius: Math.max(3, a.magnitude * 3),
        fillColor: "#ff9500", color: "#ffcc00",
        weight: 1, opacity: 0.8, fillOpacity: 0.4
      }).bindTooltip("<b>📡 Réplica M" + a.magnitude + "</b><br>" + a.place, { sticky: true })
        .addTo(aftershockLayer);
    });
    const el = document.getElementById("replica-info");
    if (el) el.textContent = "📡 " + count + " réplicas detectadas en radio de 150km (últimas 48h)";
  } catch(e) { console.error("Error réplicas:", e); }
}

// ===== PDF =====
document.getElementById("btn-pdf").addEventListener("click", async function() {
  const btn = document.getElementById("btn-pdf");
  btn.textContent = "⏳"; btn.classList.add("active");
  try {
    const res = await fetch(API + "/report/pdf");
    if (!res.ok) throw new Error("Error " + res.status);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "VigilaChile_" + new Date().toLocaleDateString("es-CL").replace(/\//g, "-") + ".pdf";
    a.click();
    URL.revokeObjectURL(url);
  } catch(e) { alert("Error generando PDF. Intenta nuevamente."); }
  finally { btn.textContent = "📄"; btn.classList.remove("active"); }
});

// ===== VULNERABILIDAD =====
document.getElementById("btn-vuln").addEventListener("click", async function() {
  document.getElementById("vuln-overlay").classList.remove("hidden");
  document.getElementById("btn-vuln").classList.add("active");
  await loadVulnerability();
});

document.getElementById("vuln-close").addEventListener("click", function() {
  document.getElementById("vuln-overlay").classList.add("hidden");
  document.getElementById("btn-vuln").classList.remove("active");
});

async function loadVulnerability() {
  const grid = document.getElementById("vuln-grid");
  grid.style.display = "block";
  showLoading("vuln-grid", "Calculando índices de vulnerabilidad", "Analizando datos sísmicos y de incendios por región...");
  try {
    const res = await fetch(API + "/vulnerability");
    const json = await res.json();
    grid.style.display = "";
    grid.innerHTML = "";
    json.data.forEach(function(r) {
      const vulnPct = Math.min(100, r.vulnerability_index);
      const card = document.createElement("div");
      card.className = "vuln-card";
      card.style.borderColor = r.color + "66";
      card.innerHTML =
        "<div class='vuln-card-header'>" +
        "<span class='vuln-region-name'>" + r.name + "</span>" +
        "<span class='vuln-badge-small' style='color:" + r.color + ";border-color:" + r.color + ";background:" + r.color + "22'>" + r.level + "</span>" +
        "</div>" +
        "<div class='vuln-stats'>" +
        "<div class='vuln-stat-item'>Sismos 24h<span>" + r.quakes_24h + "</span></div>" +
        "<div class='vuln-stat-item'>Mag. máx.<span>M" + r.max_magnitude + "</span></div>" +
        "<div class='vuln-stat-item'>Vulnerabilidad<span>" + r.vulnerability_level + "</span></div>" +
        "<div class='vuln-stat-item'>Incendios<span>" + r.fires_nearby + "</span></div>" +
        "</div>" +
        "<div class='vuln-index-bar'><div class='vuln-index-fill' style='width:" + vulnPct + "%;background:" + r.color + "'></div></div>" +
        "<div class='vuln-communes'>Comunas: " + r.communes.slice(0, 3).join(", ") + "</div>" +
        (r.tsunami_risk ? "<div style='font-size:0.72rem;color:#ff6666;margin-top:6px'>🌊 Riesgo tsunami activo</div>" : "");
      grid.appendChild(card);
    });
  } catch(e) {
    document.getElementById("vuln-grid").innerHTML = "<div style='grid-column:1/-1'><div class='loading-container'><div class='loading-text'>❌ Error cargando vulnerabilidad</div></div></div>";
  }
}

// ===== CALCULADORA EVACUACIÓN =====
document.getElementById("btn-evacuate").addEventListener("click", async function() {
  document.getElementById("evacuate-overlay").classList.remove("hidden");
  document.getElementById("btn-evacuate").classList.add("active");
  if (cachedRegions.length === 0) await loadRegions();
});

document.getElementById("evacuate-close").addEventListener("click", function() {
  document.getElementById("evacuate-overlay").classList.add("hidden");
  document.getElementById("btn-evacuate").classList.remove("active");
});

document.getElementById("evacuate-btn").addEventListener("click", function() {
  const regionId = document.getElementById("evacuate-region").value;
  if (!regionId) { alert("Selecciona tu región primero."); return; }
  const region = cachedRegions.find(function(r) { return r.id === regionId; });
  if (!region) { alert("Datos no disponibles. Intenta nuevamente."); return; }

  const result = document.getElementById("evacuate-result");
  result.classList.remove("hidden");

  const isCoastal = region.coastal;
  const hasTsunami = region.tsunami_risk;
  const levelColor = region.color;

  const instructions = {
  "ROJA": {
    icon: "🔴", title: "ALERTA ROJA — Sismo significativo registrado",
    steps: [
      "Se registró un sismo de magnitud relevante en tu región",
      "Mantente informado a través del CSN (sismologia.cl) y SENAPRED",
      "Revisa si hay daños en tu entorno inmediato",
      isCoastal ? "Mantente alejado de la costa hasta confirmar que no hay alerta de tsunami" : "Evita zonas de quebradas o construcciones dañadas",
      "Sintoniza Radio Nacional (630 AM) para información oficial",
      "Sigue solo fuentes oficiales — evita rumores en redes sociales"
    ]
  },
  "NARANJA": {
    icon: "🟠", title: "ALERTA NARANJA — Actividad sísmica elevada",
    steps: [
      "Se registra actividad sísmica por sobre lo habitual en tu región",
      "Verifica que tu entorno esté en buen estado estructural",
      "Ten a mano tu mochila de emergencia por precaución",
      isCoastal ? "Conoce las rutas de evacuación costera de tu ciudad" : "Identifica las zonas seguras de tu hogar",
      "Mantente atento a las actualizaciones del CSN y SENAPRED"
    ]
  },
  "AMARILLA": {
    icon: "🟡", title: "ALERTA AMARILLA — Atención preventiva",
    steps: [
      "Actividad sísmica moderada en tu región — dentro del rango habitual para Chile",
      "Buen momento para revisar tu plan familiar de emergencia",
      "Verifica que tu mochila de emergencia esté preparada",
      "Conoce el punto de encuentro de tu barrio",
      "Mantente informado a través del Centro Sismológico Nacional"
    ]
  },
  "ALERTA VERDE": {
    icon: "🟢", title: "ALERTA VERDE — Actividad leve, sin preocupación",
    steps: [
      "Actividad sísmica leve y dentro de rangos normales para Chile",
      "No se requiere ninguna acción especial",
      "Como siempre, es bueno tener preparado un plan de emergencia familiar",
      "Puedes revisar tus datos sísmicos en sismologia.cl"
    ]
  },
  "VERDE": {
    icon: "✅", title: "SIN ACTIVIDAD — Situación normal",
    steps: [
      "Sin actividad sísmica significativa en las últimas 24 horas",
      "Situación completamente normal para la región",
      "Aprovecha para revisar tu kit de emergencia si no lo has hecho",
      "Recuerda: en Chile siempre es bueno estar preparado"
    ]
  }
};

  const evInfo = instructions[region.level] || {
    icon: "🟢", title: "ZONA VERDE — Sin actividad relevante",
    steps: [
      "La actividad sísmica es normal para la región",
      "Mantén tu mochila de emergencia lista",
      "Conoce la ruta de evacuación de tu sector",
      "Sigue las instrucciones de SENAPRED"
    ]
  };

  const tsunamiSection = hasTsunami ?
    "<div class='evacuate-section'>" +
    "<h3>🌊 Alerta de Tsunami Activa</h3>" +
    "<div class='evacuate-alert-box' style='background:#ff333322;border:1px solid #ff3333;color:#ff9999'>" +
    "⚠️ Se ha detectado actividad sísmica costera que puede generar tsunami. " +
    "EVACÚE inmediatamente hacia zonas a más de 30 metros sobre el nivel del mar o a más de 2km de la costa. " +
    "No espere ver el mar retroceder. Siga las señales de evacuación.</div>" +
    "<p>📡 Monitorea alertas oficiales: <strong>shoa.cl</strong> · <strong>senapred.cl</strong></p>" +
    "</div>" : "";

  result.innerHTML =
    "<div class='evacuate-section' style='border-color:" + levelColor + "66'>" +
    "<h3>" + evInfo.icon + " " + evInfo.title + "</h3>" +
    "<div class='evacuate-alert-box' style='background:" + levelColor + "22;border:1px solid " + levelColor + ";color:" + levelColor + "'>" +
    "Región " + region.name + " · " + region.quakes_24h + " sismos en 24h · Mag. máx: M" + region.max_magnitude +
    "</div>" +
    "<ul>" + evInfo.steps.map(function(s) { return "<li>" + s + "</li>"; }).join("") + "</ul>" +
    "</div>" +
    tsunamiSection +
    "<div class='evacuate-section'>" +
    "<h3>📞 Números de emergencia</h3>" +
    "<p>🚒 Bomberos: <strong>132</strong></p>" +
    "<p>🚑 Ambulancia SAMU: <strong>131</strong></p>" +
    "<p>👮 Carabineros: <strong>133</strong></p>" +
    "<p>🆘 Emergencias: <strong>112</strong></p>" +
    "<p>🌊 SHOA (Tsunami): <strong>+56 32 220 8172</strong></p>" +
    "<p>📻 Radio Nacional: <strong>630 AM</strong></p>" +
    "</div>" +
    "<div class='evacuate-section'>" +
    "<h3>🎒 Lista mochila de emergencia</h3>" +
    "<ul>" +
    "<li>Agua potable (2 litros por persona)</li>" +
    "<li>Alimentos no perecibles (3 días)</li>" +
    "<li>Linterna y baterías de repuesto</li>" +
    "<li>Documentos de identidad y medicamentos</li>" +
    "<li>Radio a pilas o manivela</li>" +
    "<li>Botiquín básico de primeros auxilios</li>" +
    "<li>Ropa abrigada y zapatos resistentes</li>" +
    "<li>Dinero en efectivo</li>" +
    "</ul>" +
    "</div>";
});

// ===== ESTADÍSTICAS HISTÓRICAS =====
document.getElementById("btn-stats").addEventListener("click", async function() {
  document.getElementById("stats-overlay").classList.remove("hidden");
  document.getElementById("btn-stats").classList.add("active");
  await loadStats();
});

document.getElementById("stats-close").addEventListener("click", function() {
  document.getElementById("stats-overlay").classList.add("hidden");
  document.getElementById("btn-stats").classList.remove("active");
  // Limpiar charts al cerrar para evitar memory leaks
  Object.keys(statsCharts).forEach(function(k) {
    if (statsCharts[k]) { statsCharts[k].destroy(); delete statsCharts[k]; }
  });
});

async function loadStats() {
  const body = document.getElementById("stats-body");
  body.innerHTML = "";
  showLoading("stats-body", "Cargando estadísticas históricas", "Descargando datos de 30 días desde CSN...");
  // Limpiar charts previos
  Object.keys(statsCharts).forEach(function(k) {
    if (statsCharts[k]) { statsCharts[k].destroy(); delete statsCharts[k]; }
  });

  try {
    const res = await fetch(API + "/history");
    const json = await res.json();
    const data = json.data;
    const total = data.length;
    const maxMag = total > 0 ? Math.max.apply(null, data.map(function(q) { return q.magnitude; })) : 0;
    const avg = Math.round(total / 30);
    const m5 = data.filter(function(q) { return q.magnitude >= 5; }).length;

    body.innerHTML =
      "<div id='stats-summary'>" +
      "<div class='stats-card'><div class='stats-num'>" + total.toLocaleString("es-CL") + "</div><div class='stats-label'>Sismos 30 días</div></div>" +
      "<div class='stats-card'><div class='stats-num'>M" + maxMag.toFixed(1) + "</div><div class='stats-label'>Máxima 30 días</div></div>" +
      "<div class='stats-card'><div class='stats-num'>" + avg + "/día</div><div class='stats-label'>Promedio diario</div></div>" +
      "<div class='stats-card'><div class='stats-num'>" + m5 + "</div><div class='stats-label'>Sismos M≥5 (30d)</div></div>" +
      "</div>" +
      "<div id='stats-charts'>" +
      "<div class='stats-chart-box'><h3>Actividad diaria — últimos 30 días</h3><canvas id='chart-daily'></canvas></div>" +
      "<div class='stats-chart-box'><h3>Distribución por magnitud</h3><canvas id='chart-mag'></canvas></div>" +
      "<div class='stats-chart-box'><h3>Top 10 zonas más activas</h3><canvas id='chart-zones'></canvas></div>" +
      "<div class='stats-chart-box'><h3>Profundidad promedio por día (km)</h3><canvas id='chart-depth'></canvas></div>" +
      "</div>";

    // Gráfico 1: Actividad diaria
    const dailyCounts = {};
    data.forEach(function(q) {
      const day = q.time ? q.time.substring(0, 10) : "?";
      dailyCounts[day] = (dailyCounts[day] || 0) + 1;
    });
    const sortedDays = Object.keys(dailyCounts).sort();
    renderStatsChart("chart-daily", "bar",
      sortedDays.map(function(d) { return d.substring(5); }),
      sortedDays.map(function(d) { return dailyCounts[d]; }),
      "#4fc3f7");

    // Gráfico 2: Distribución por magnitud
    const magBins = { "2.5-3": 0, "3-4": 0, "4-5": 0, "5-6": 0, "6+": 0 };
    data.forEach(function(q) {
      if (q.magnitude < 3) magBins["2.5-3"]++;
      else if (q.magnitude < 4) magBins["3-4"]++;
      else if (q.magnitude < 5) magBins["4-5"]++;
      else if (q.magnitude < 6) magBins["5-6"]++;
      else magBins["6+"]++;
    });
    renderStatsChart("chart-mag", "doughnut",
      Object.keys(magBins), Object.values(magBins),
      ["#4ade80", "#4ade80aa", "#ffd700", "#ff9500", "#ff3333"]);

    // Gráfico 3: Top 10 zonas
    const zones = {};
    data.forEach(function(q) {
      const z = q.place ? q.place.split("de ").pop().split("al ")[0].trim() : "Desconocido";
      zones[z] = (zones[z] || 0) + 1;
    });
    const topZones = Object.entries(zones).sort(function(a, b) { return b[1] - a[1]; }).slice(0, 10);
    renderStatsChart("chart-zones", "bar",
      topZones.map(function(z) { return z[0]; }),
      topZones.map(function(z) { return z[1]; }),
      "#ffd700");

    // Gráfico 4: Profundidad promedio REAL por día (fix bug valores 0-1)
    const depthByDay = {};
    const depthCountByDay = {};
    data.forEach(function(q) {
      if (!q.time) return;
      const day = q.time.substring(5, 10);
      const depth = parseFloat(q.depth);
      if (!isNaN(depth) && depth > 0) {
        depthByDay[day] = (depthByDay[day] || 0) + depth;
        depthCountByDay[day] = (depthCountByDay[day] || 0) + 1;
      }
    });
    const depthDays = Object.keys(depthByDay).sort();
    const depthAvgs = depthDays.map(function(d) {
      return Math.round(depthByDay[d] / depthCountByDay[d]);
    });
    renderStatsChart("chart-depth", "line", depthDays, depthAvgs, "#ff9500");

  } catch(e) {
    document.getElementById("stats-body").innerHTML =
      "<div class='loading-container'><div class='loading-text'>❌ Error cargando estadísticas</div><div class='loading-subtext'>El servidor puede tardar en procesar 30 días de datos.</div></div>";
  }
}

function renderStatsChart(canvasId, type, labels, data, color) {
  if (statsCharts[canvasId]) { statsCharts[canvasId].destroy(); delete statsCharts[canvasId]; }
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const isArray = Array.isArray(color);
  statsCharts[canvasId] = new Chart(ctx, {
    type: type,
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: isArray ? color : (type === "line" ? "transparent" : color + "99"),
        borderColor: isArray ? color : color,
        borderWidth: type === "line" ? 2 : 1,
        borderRadius: type === "bar" ? 4 : 0,
        fill: false, tension: 0.4,
        pointRadius: type === "line" ? 3 : 0,
        pointBackgroundColor: type === "line" ? color : undefined
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: type === "doughnut", labels: { color: "#a0b4cc", font: { size: 11 } } }
      },
      scales: type !== "doughnut" ? {
        x: { ticks: { color: "#3a5270", font: { size: 9 }, maxRotation: 45 }, grid: { color: "#1e2d4a" } },
        y: { ticks: { color: "#5c7a9e", font: { size: 10 } }, grid: { color: "#1e2d4a" } }
      } : {}
    }
  });
}

// ===== ALERTAS EMAIL =====
async function checkEmailAlerts() {
  // Solo enviar alertas para sismos que no se han notificado en esta sesión
  const criticalQuakes = allQuakes.filter(function(q) {
    return q.magnitude >= 5.0 && !alertsSentThisSession.has(q.time + q.place);
  });
  if (criticalQuakes.length === 0) return;
  try {
    await fetch(API + "/check-alerts");
    criticalQuakes.forEach(function(q) {
      alertsSentThisSession.add(q.time + q.place);
    });
  } catch(e) {}
}

// ===== MODO QUIOSCO =====
function updateKioskData() {
  document.getElementById("kiosk-quakes").textContent = document.getElementById("quake-count").textContent;
  document.getElementById("kiosk-mag").textContent = document.getElementById("max-mag").textContent;
  document.getElementById("kiosk-fires").textContent = document.getElementById("fire-count").textContent;
  document.getElementById("kiosk-risk").textContent = document.getElementById("risk-score").textContent;

  if (cachedAIReport) {
    document.getElementById("kiosk-ai-text").textContent = cachedAIReport;
  } else {
    document.getElementById("kiosk-ai-text").innerHTML =
      "<span style='color:#3a5270'>⏳ Generando análisis IA...<br><br>Se actualizará automáticamente.</span>";
    loadAI();
  }

  if (allQuakes.length > 0) {
    const last = allQuakes[0];
    const color = last.magnitude >= 6 ? "#ff3333" : last.magnitude >= 4.5 ? "#ffd700" : "#4ade80";
    document.getElementById("kiosk-last-content").innerHTML =
      "<span class='last-mag' style='color:" + color + "'>M " + last.magnitude + "</span>" +
      "<span class='last-place'>📍 " + last.place + "</span>" +
      "<span class='last-detail'>🕐 Hora Chile: <b>" + utcToChile(last.time) + "</b></span>" +
      "<span class='last-detail'>🕳️ Profundidad: " + last.depth + " km</span>" +
      "<span class='last-detail'>⏱️ " + timeAgo(last.time) + "</span>";
  }

  const list = document.getElementById("kiosk-events-list");
  list.innerHTML = "";
  allQuakes
    .filter(function(q) { return q.magnitude >= 3.5 && isWithin24h(q.time); })
    .slice(0, 10)
    .forEach(function(q) {
      const li = document.createElement("li");
      const color = q.magnitude >= 5 ? "#ff6b35" : "#ffd700";
      const timeChile = utcToChile(q.time);
      const timePart = timeChile.includes(",") ? timeChile.split(",")[1].trim() : timeChile;
      li.innerHTML =
        "<span><span class='kiosk-ev-mag' style='color:" + color + "'>M" + q.magnitude + "</span>" +
        "<span class='kiosk-ev-place'>" + q.place + "</span></span>" +
        "<span class='kiosk-ev-time'>" + timePart + "</span>";
      list.appendChild(li);
    });

  document.getElementById("kiosk-update").textContent =
    "· Actualizado: " + new Date().toLocaleTimeString("es-CL", { timeZone: "America/Santiago" });
}

function updateKioskClock() {
  document.getElementById("kiosk-clock").textContent =
    new Date().toLocaleString("es-CL", { timeZone: "America/Santiago", dateStyle: "full", timeStyle: "medium" });
}

document.getElementById("btn-kiosk").addEventListener("click", function() {
  document.getElementById("kiosk-overlay").classList.remove("hidden");
  document.getElementById("btn-kiosk").classList.add("active");
  updateKioskData(); updateKioskClock();
  kioskInterval = setInterval(updateKioskClock, 1000);
  kioskDataInterval = setInterval(function() {
    updateKioskData();
    if (!cachedAIReport) loadAI();
  }, 10000);
  if (document.documentElement.requestFullscreen) {
    document.documentElement.requestFullscreen().catch(function() {});
  }
});

document.getElementById("kiosk-close").addEventListener("click", function() {
  document.getElementById("kiosk-overlay").classList.add("hidden");
  document.getElementById("btn-kiosk").classList.remove("active");
  clearInterval(kioskInterval); clearInterval(kioskDataInterval);
  if (document.exitFullscreen) document.exitFullscreen().catch(function() {});
});

// ===== MODO EMERGENCIA =====
// ===== RADIO DE EMERGENCIA =====
function showEmergencyRadio() {
  const existing = document.getElementById("radio-emergency");
  if (existing) return;

  const radio = document.createElement("div");
  radio.id = "radio-emergency";
  radio.innerHTML =
    "<div id='radio-header'>" +
    "<span>📻 Radio Nacional — EN VIVO</span>" +
    "<button id='radio-close-btn'>✕</button>" +
    "</div>" +
    "<audio id='radio-audio' controls autoplay>" +
    "<source src='https://unlimited1-us.dps.live/radionacional/radionacional.stream/playlist.m3u8' type='application/x-mpegURL'/>" +
    "<source src='http://streaming.radionacional.cl:8000/rnacional' type='audio/mpeg'/>" +
    "Tu navegador no soporta audio en vivo." +
    "</audio>" +
    "<p id='radio-info'>🔴 Sintoniza para instrucciones oficiales de SENAPRED</p>";

  document.body.appendChild(radio);

  document.getElementById("radio-close-btn").addEventListener("click", function() {
    const audioEl = document.getElementById("radio-audio");
    if (audioEl) { audioEl.pause(); audioEl.src = ""; }
    radio.remove();
  });
}

function hideEmergencyRadio() {
  const radio = document.getElementById("radio-emergency");
  if (radio) {
    const audioEl = document.getElementById("radio-audio");
    if (audioEl) { audioEl.pause(); audioEl.src = ""; }
    radio.remove();
  }
}

function triggerEmergency(q) {
  document.body.classList.add("emergency-mode");
  document.getElementById("emergency-quake").textContent =
    "Sismo M" + q.magnitude + " — " + q.place + " — Profundidad: " + q.depth + " km";
  document.getElementById("emergency-overlay").classList.remove("hidden");
  speak("Alerta. Sismo de magnitud " + q.magnitude + " detectado en " + q.place + ". Siga las instrucciones de emergencia.");
  notify("🚨 SISMO MAYOR DETECTADO", "M" + q.magnitude + " — " + q.place);
  // Abrir radio automáticamente
  showEmergencyRadio();
}

document.getElementById("emergency-close").addEventListener("click", function() {
  document.getElementById("emergency-overlay").classList.add("hidden");
  document.body.classList.remove("emergency-mode");
});

// ===== DETALLE =====
function highlightMarker(marker) {
  if (activeMarker) activeMarker.setStyle({ weight: 1, opacity: 0.9 });
  marker.setStyle({ weight: 3, opacity: 1, color: "#ffffff" });
  activeMarker = marker;
}

async function showDetail(q, marker) {
  if (marker) highlightMarker(marker);
  const color = q.magnitude >= 6 ? "#ff3333" : q.magnitude >= 4.5 ? "#ffd700" : "#4ade80";
  let popHtml = "";
  try {
    const res = await fetch(API + "/population/" + q.lat + "/" + q.lon + "/" + q.magnitude);
    const pop = await res.json();
    popHtml =
      "<div class='population-box'>🏘️ Población estimada en zona de afección:<br>" +
      "<strong>~" + pop.estimated_population.toLocaleString("es-CL") + " personas</strong><br>" +
      "Radio: " + pop.radius_km + " km · Densidad: " + pop.density_zone + "</div>";
  } catch(e) {}

  const tsunami = tsunamiRisk(q);
  const prep = prepInfo(q);
  detailContent.innerHTML =
    "<h2>🌍 Sismo M" + q.magnitude + "</h2>" +
    (tsunami ? "<div class='tsunami-alert'>" + tsunami + "</div>" : "") +
    "<p>📍 " + q.place + "</p>" +
    "<p>⏱️ " + timeAgo(q.time) + "</p>" +
    "<p>🕐 Hora Chile: " + utcToChile(q.time) + "</p>" +
    "<p>🕳️ Profundidad: " + q.depth + " km</p>" +
    "<p>💪 Magnitud: <span style='color:" + color + ";font-weight:700'>" + q.magnitude + "</span></p>" +
    popHtml +
    getShareButtons(q) +
    (prep ? "<div class='prep-tip'>💡 " + prep + "</div>" : "") +
    (q.magnitude >= 5.0 ? "<div class='prep-tip' id='replica-info'>📡 Cargando réplicas...</div>" : "") +
    (q.url ? "<a href='" + q.url + "' target='_blank'>Ver informe CSN →</a>" : "");

  setTimeout(function() {
    const copyBtn = document.getElementById("copy-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", function() {
        navigator.clipboard.writeText(getShareText(q)).then(function() { alert("¡Copiado!"); });
      });
    }
  }, 100);

  detailPanel.classList.remove("hidden");
  map.setView([q.lat, q.lon], 8, { animate: true });
  setTimeout(function() { map.panBy([150, 0], { animate: true }); }, 400);
  if (q.magnitude >= 4.5) speak("Sismo de magnitud " + q.magnitude + " en " + q.place + ". Profundidad " + q.depth + " kilómetros.");
  if (q.magnitude >= 5.0) loadAftershocks(q);
}

document.getElementById("close-detail").addEventListener("click", function() {
  detailPanel.classList.add("hidden");
  if (activeMarker) { activeMarker.setStyle({ weight: 1, opacity: 0.9 }); activeMarker = null; }
  if (aftershockLayer) { map.removeLayer(aftershockLayer); aftershockLayer = null; }
});

// ===== CARGA DE DATOS =====
async function loadRisk() {
  try {
    const res = await fetch(API + "/risk");
    const data = await res.json();
    document.getElementById("risk-score").textContent = data.score + "/10";
    document.getElementById("risk-score").style.color = data.color;
    document.getElementById("risk-level").textContent = "Riesgo " + data.level;
    document.getElementById("risk-desc").textContent = data.description;
    document.getElementById("risk-card").style.borderColor = data.color + "66";
  } catch(err) { console.error("Error risk:", err); }
}

async function loadTrends() {
  try {
    const res = await fetch(API + "/trends");
    const data = await res.json();
    const trendClass = data.trend === "aumentando" ? "trend-up" : data.trend === "disminuyendo" ? "trend-down" : "trend-stable";
    const trendIcon = data.trend === "aumentando" ? "📈" : data.trend === "disminuyendo" ? "📉" : "➡️";
    const sign = data.difference > 0 ? "+" : "";
    document.getElementById("trends-content").innerHTML =
      "<span class='" + trendClass + "'>" + trendIcon + " Actividad " + data.trend + "</span><br>" +
      "Hoy: <b>" + data.today + "</b> sismos · Ayer: <b>" + data.yesterday + "</b><br>" +
      "Diferencia: <span class='" + trendClass + "'>" + sign + data.difference + " (" + sign + data.percentage + "%)</span><br>" +
      "Mag. máx. hoy: <b>M" + data.today_max + "</b> · Ayer: <b>M" + data.yesterday_max + "</b>";
  } catch(err) { document.getElementById("trends-content").textContent = "No disponible"; }
}

async function loadAI() {
  document.getElementById("ai-report").textContent = "🤖 Analizando patrones sísmicos...";
  document.getElementById("ai-dock-preview").textContent = "Analizando patrones sísmicos...";
  try {
    const res = await fetch(API + "/analyze");
    const data = await res.json();
    cachedAIReport = data.report;

    // Clean: strip any AI-generated header before SISMOS
    var cleanReport = data.report
      .replace(/^.*?(REPORTE|ANÁLISIS|ANALISIS).*?(horas|actual|integral)\s*/i, "")
      .replace(/\*\*/g, "")
      .replace(/^#+\s*/gm, "")
      .replace(/^---+$/gm, "")
      .replace(/^>\s*/gm, "")
      .replace(/■/g, "")
      .trim();

    // Highlight section keywords
    var formatted = cleanReport
      .replace(/\b(SISMOS):/g, '<span class="ai-section-tag">🌍 SISMOS</span>:')
      .replace(/\b(INCENDIOS):/g, '<span class="ai-section-tag">🔥 INCENDIOS</span>:')
      .replace(/\b(VOLCANES):/g, '<span class="ai-section-tag">🌋 VOLCANES</span>:')
      .replace(/\b(TSUNAMI):/g, '<span class="ai-section-tag">🌊 TSUNAMI</span>:')
      .replace(/\b(CLIMA):/g, '<span class="ai-section-tag">🌧️ CLIMA</span>:')
      .replace(/\b(EVALUACI[ÓO]N):/gi, '<span class="ai-section-tag">📊 EVALUACIÓN</span>:');

    document.getElementById("ai-report").innerHTML = formatted;

    // Preview: first meaningful sentence (skip section tag)
    var previewText = cleanReport.substring(0, 120).replace(/SISMOS:\s*/, "") + "...";
    document.getElementById("ai-dock-preview").textContent = previewText;

    const trendText = data.trend === "increasing" ? "📈 Aumentando" : data.trend === "decreasing" ? "📉 Bajando" : "➡️ Estable";
    document.getElementById("ai-meta").innerHTML =
      "Zona más activa: <b>" + data.top_zone + "</b> · Últimas 6h: <b>" + data.recent_6h + "</b> · Tendencia: <b>" + trendText + "</b>";
    document.getElementById("ai-dock-meta").innerHTML =
      data.top_zone + " · " + trendText;
    if (!document.getElementById("kiosk-overlay").classList.contains("hidden")) {
      document.getElementById("kiosk-ai-text").textContent = cachedAIReport;
    }
  } catch(err) {
    document.getElementById("ai-report").textContent = "Análisis no disponible.";
    document.getElementById("ai-dock-preview").textContent = "Análisis no disponible.";
  }
}

// ===== QUICK DETAIL PANELS + LAST EVENT =====
var cachedQuakesData = [];
var cachedFiresData = [];
var cachedWeatherAll = [];

function updateLastEvent() {
  var el = document.getElementById("last-event-content");
  if (!el) return;
  var lines = [];
  if (cachedQuakesData.length > 0) {
    var top = cachedQuakesData.reduce(function(a,b) { return a.magnitude > b.magnitude ? a : b; });
    lines.push("🌍 Sismo más fuerte: <b style='color:#ffd700'>M" + top.magnitude + "</b> — " + top.place + " · " + timeAgo(top.time));
  }
  if (cachedFiresData.length > 0) {
    var hottest = cachedFiresData.reduce(function(a,b) { return a.brightness > b.brightness ? a : b; });
    lines.push("🔥 Foco más intenso: <b style='color:#ff6b35'>" + hottest.brightness + "K</b> · Confianza " + hottest.confidence + "%");
  }
  if (cachedVolcanoes.length > 0) {
    var alerts = cachedVolcanoes.filter(function(v) { return v.alert !== "Verde"; });
    if (alerts.length > 0) {
      lines.push("🌋 Volcanes en alerta: <b style='color:#ffd700'>" + alerts.map(function(v){return v.name}).join(", ") + "</b>");
    }
  }
  if (cachedWeatherAll.length > 0) {
    var rainy = cachedWeatherAll.filter(function(r) { return !r.error && r.current && r.current.precipitation_mm > 0; });
    if (rainy.length > 0) {
      var wettest = rainy.reduce(function(a,b) { return (a.current.precipitation_mm||0) > (b.current.precipitation_mm||0) ? a : b; });
      lines.push("🌧️ Lluvia activa: <b style='color:#6ba3d6'>" + wettest.name + "</b> " + wettest.current.precipitation_mm + " mm/h");
    }
  }
  el.innerHTML = lines.length > 0 ? lines.join("<br>") : "Sin eventos significativos en este momento.";
}

(function() {
  var detail = document.getElementById("quick-detail");
  if (!detail) return;
  var detailBody = document.getElementById("quick-detail-body");
  var detailTitle = document.getElementById("quick-detail-title");
  var activeBtn = null;

  function closeDetail() {
    detail.classList.add("hidden");
    if (activeBtn) { activeBtn.classList.remove("active"); activeBtn = null; }
  }
  document.getElementById("quick-detail-close").addEventListener("click", closeDetail);

  function togglePanel(btnId, title, renderFn) {
    var btn = document.getElementById(btnId);
    if (!btn) return;
    btn.addEventListener("click", function() {
      if (activeBtn === btn) { closeDetail(); return; }
      if (activeBtn) activeBtn.classList.remove("active");
      activeBtn = btn;
      btn.classList.add("active");
      detailTitle.textContent = title;
      detail.classList.remove("hidden");
      renderFn();
    });
  }

  togglePanel("qp-quakes", "🌍 Sismos últimas 24h", function() {
    var q = cachedQuakesData || [];
    if (!q.length) { detailBody.innerHTML = "<div style='padding:16px;color:#5c7a9e'>Sin datos.</div>"; return; }
    var html = "";
    var sorted = q.slice().sort(function(a,b) { return b.magnitude - a.magnitude; });
    sorted.forEach(function(s) {
      var c = s.magnitude >= 5 ? "#ff3333" : s.magnitude >= 4 ? "#ffd700" : s.magnitude >= 3 ? "#4ade80" : "#5c7a9e";
      html += "<div class='qd-item' onclick='map.flyTo([" + s.lat + "," + s.lon + "],10)'>" +
        "<span class='qd-mag' style='color:" + c + "'>M" + s.magnitude + "</span>" +
        "<span class='qd-place'>" + s.place + "</span>" +
        "<span class='qd-meta'>" + (s.depth || "--") + "km · " + timeAgo(s.time) + "</span></div>";
    });
    detailBody.innerHTML = html;
  });

  togglePanel("qp-fires", "🔥 Focos activos", function() {
    var f = cachedFiresData || [];
    if (!f.length) { detailBody.innerHTML = "<div style='padding:16px;color:#5c7a9e'>Sin focos.</div>"; return; }
    var html = "";
    f.slice().sort(function(a,b) { return b.brightness - a.brightness; }).forEach(function(fire) {
      html += "<div class='qd-item' onclick='map.flyTo([" + fire.lat + "," + fire.lon + "],12)'>" +
        "<span class='qd-mag' style='color:#ff6b35'>" + fire.brightness + "K</span>" +
        "<span class='qd-place'>Lat " + fire.lat.toFixed(2) + " · Lon " + fire.lon.toFixed(2) + "</span>" +
        "<span class='qd-meta'>Conf: " + fire.confidence + "%</span></div>";
    });
    detailBody.innerHTML = html;
  });

  togglePanel("qp-volcanoes", "🌋 Volcanes", function() {
    var v = cachedVolcanoes || [];
    if (!v.length) { detailBody.innerHTML = "<div style='padding:16px;color:#5c7a9e'>Sin datos.</div>"; return; }
    var html = "";
    v.forEach(function(vol) {
      var vc = vol.alert === "Amarilla" ? "#ffd700" : vol.alert === "Naranja" ? "#ff9500" : vol.alert === "Roja" ? "#ff3333" : "#4ade80";
      html += "<div class='qd-item' onclick='map.flyTo([" + vol.lat + "," + vol.lon + "],10)'>" +
        "<span class='qd-mag' style='color:" + vc + "'>" + vol.alert + "</span>" +
        "<span class='qd-place'><b>" + vol.name + "</b> · " + vol.region + "</span>" +
        "<span class='qd-meta'>" + vol.elevation + "m</span></div>";
    });
    detailBody.innerHTML = html;
  });

  togglePanel("qp-clima", "🌡️ Clima", function() {
    var w = cachedWeatherAll || [];
    if (!w.length) { detailBody.innerHTML = "<div style='padding:16px;color:#5c7a9e'>Sin datos.</div>"; return; }
    var html = "";
    w.forEach(function(r) {
      if (r.error) return;
      var c = r.current || {};
      var risk = r.risk || {};
      var rc = risk.color || "#5c7a9e";
      html += "<div class='qd-item'>" +
        "<span class='qd-temp'>" + (c.temperature_c || "--") + "°</span>" +
        "<span class='qd-place'><b>" + r.name + "</b> · " + (c.wind_kmh || 0) + "km/h · " + (c.precipitation_mm || 0) + "mm</span>" +
        "<span class='qd-meta' style='color:" + rc + "'>" + (risk.level || "--") + "</span></div>";
    });
    detailBody.innerHTML = html;
  });
})();

async function loadHeatmap() {
  const status = document.getElementById("heat-status");
  status.classList.remove("hidden");
  const messages = ["🛰️ Conectando con CSN...", "📡 Descargando 30 días...", "🗺️ Procesando sismos...", "✅ Renderizando..."];
  let i = 0;
  status.textContent = messages[0];
  const msgInterval = setInterval(function() {
    i = Math.min(i + 1, messages.length - 1);
    status.textContent = messages[i];
  }, 8000);
  try {
    const res = await fetch(API + "/history");
    const json = await res.json();
    clearInterval(msgInterval);
    status.textContent = "✅ " + json.count + " sismos cargados";
    setTimeout(function() { status.classList.add("hidden"); }, 3000);
    const points = json.data.map(function(q) { return [q.lat, q.lon, q.magnitude / 7]; });
    if (heatLayer) map.removeLayer(heatLayer);
    heatLayer = L.heatLayer(points, {
      radius: 25, blur: 20, maxZoom: 10,
      gradient: { 0.2: "#4fc3f7", 0.5: "#ffd700", 0.8: "#ff9500", 1.0: "#ff3333" }
    });
  } catch(err) {
    clearInterval(msgInterval);
    status.textContent = "❌ Error al cargar datos";
    setTimeout(function() { status.classList.add("hidden"); }, 3000);
  }
}

async function requestNotifications() {
  if ("Notification" in window && Notification.permission === "default") {
    await Notification.requestPermission();
  }
}

function notify(title, body) {
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification(title, { body: body });
  }
}

let magChart = null;
function renderChart(quakes) {
  const bins = { "2.5-3": 0, "3-4": 0, "4-5": 0, "5-6": 0, "6+": 0 };
  quakes.forEach(function(q) {
    if (q.magnitude < 3) bins["2.5-3"]++;
    else if (q.magnitude < 4) bins["3-4"]++;
    else if (q.magnitude < 5) bins["4-5"]++;
    else if (q.magnitude < 6) bins["5-6"]++;
    else bins["6+"]++;
  });
  var magCanvas = document.getElementById("magChart"); if(!magCanvas) return; const ctx = magCanvas.getContext("2d");
  if (magChart) magChart.destroy();
  magChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: Object.keys(bins),
      datasets: [{
        data: Object.values(bins),
        backgroundColor: ["#4ade80", "#4ade80", "#ffd700", "#ff9500", "#ff3333"],
        borderRadius: 4, borderSkipped: false
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#5c7a9e", font: { size: 10 } }, grid: { color: "#1e2d4a" } },
        y: { ticks: { color: "#5c7a9e", font: { size: 10 } }, grid: { color: "#1e2d4a" } }
      }
    }
  });
}

function checkAlert(quakes) {
  const critical = quakes.find(function(q) { return q.magnitude >= 6.5; });
  const major = quakes.find(function(q) { return q.magnitude >= 7.5; });
  const banner = document.getElementById("alert-banner");
  const textEl = document.getElementById("alert-text");
  if (major) triggerEmergency(major);
  if (critical) {
    const ts = tsunamiRisk(critical);
    const msg = ts ? ts : "Sismo M" + critical.magnitude + " — " + critical.place;
    textEl.textContent = msg;
    banner.classList.remove("hidden");
    notify("⚠️ VigilaChile", msg);
    if (lastAnnouncedQuake !== critical.time) {
      speak("Alerta sísmica. Sismo de magnitud " + critical.magnitude + " en " + critical.place + ".");
      lastAnnouncedQuake = critical.time;
    }
  } else {
    if (!(textEl.innerHTML || "").includes("TSUNAMI")) {
      banner.classList.add("hidden");
    }
  }
}

function renderQuakes(quakes) {
  quakeLayer.clearLayers();
  allMarkers = [];
  document.getElementById("events").innerHTML = "";
  const filtered = quakes.filter(function(q) { return q.magnitude >= minMag; });
  document.getElementById("quake-count").textContent = filtered.length;
  const maxMag = filtered.length > 0 ? Math.max.apply(null, filtered.map(function(q) { return q.magnitude; })) : null;
  document.getElementById("max-mag").textContent = maxMag ? maxMag.toFixed(1) : "--";
  checkAlert(filtered);
  renderChart(filtered);

  filtered.forEach(function(q) {
    const radius = Math.max(4, q.magnitude * 4);
    const color = q.magnitude >= 6 ? "#ff3333" : q.magnitude >= 4.5 ? "#ffd700" : "#4ade80";
    const circle = L.circleMarker([q.lat, q.lon], {
      radius: radius, fillColor: color, color: color,
      weight: 1, opacity: 0.9, fillOpacity: 0.5
    }).addTo(quakeLayer);
    allMarkers.push({ marker: circle, quake: q });
    circle.on("mouseover", function(e) {
      showTooltip(e,
        "<b>🌍 Sismo M" + q.magnitude + "</b><br>" + q.place +
        "<br>Profundidad: " + q.depth + " km<br>🕐 " + utcToChile(q.time) +
        "<br><span style='color:#5c7a9e'>" + timeAgo(q.time) + "</span>"
      );
    });
    circle.on("mouseout", hideTooltip);
    circle.on("click", function() { hideTooltip(); showDetail(q, circle); });

    if (q.magnitude >= 3.5 && isWithin24h(q.time)) {
      const li = document.createElement("li");
      li.className = q.magnitude >= 6 ? "quake critical" : "quake";
      li.innerHTML =
        "🌍 <b>M" + q.magnitude + "</b> — " + q.place +
        "<span class='time-ago'>🕐 " + utcToChile(q.time) + " · " + timeAgo(q.time) + "</span>";
      li.addEventListener("click", function() { showDetail(q, circle); });
      document.getElementById("events").appendChild(li);
    }
  });

  if (userLocation && filtered.length > 0) {
    const nearest = filtered.reduce(function(a, b) {
      return distanceKm(userLocation.lat, userLocation.lon, a.lat, a.lon) < distanceKm(userLocation.lat, userLocation.lon, b.lat, b.lon) ? a : b;
    });
    const dist = distanceKm(userLocation.lat, userLocation.lon, nearest.lat, nearest.lon);
    const risk = dist < 50 ? "⚠️ Zona de riesgo" : dist < 150 ? "🟡 Precaución" : "✅ Zona segura";
    document.getElementById("location-content").innerHTML =
      "📍 <b>Tu ubicación detectada</b><br>Sismo más cercano: <b>M" + nearest.magnitude + "</b><br>" +
      nearest.place + "<br>Distancia: <b>" + dist + " km</b><br>Estado: <b>" + risk + "</b>";
  }
}

async function loadFires() {
  fireLayer.clearLayers();
  try {
    const res = await fetch(API + "/fires");
    const json = await res.json();
    document.getElementById("fire-count").textContent = json.count;
    cachedFiresData = json.data;
    try { document.getElementById("qp-fires-count").textContent = json.count; } catch(e) {}
    updateLastEvent();
    json.data.forEach(function(f) {
      const radius = Math.max(6, (f.brightness - 300) / 10);
      L.circleMarker([f.lat, f.lon], {
        radius: radius + 8, fillColor: "#ff6b35", color: "#ff6b35",
        weight: 1, opacity: 0.3, fillOpacity: 0.12, className: "pulse-ring"
      }).addTo(fireLayer);
      const circle = L.circleMarker([f.lat, f.lon], {
        radius: radius, fillColor: "#ff6b35", color: "#ff9500",
        weight: 1.5, opacity: 1, fillOpacity: 0.85
      }).addTo(fireLayer);
      circle.on("mouseover", function(e) {
        showTooltip(e,
          "<b>🔥 Foco de calor</b><br>Brillo: " + f.brightness + " K<br>" +
          "Confianza: " + f.confidence + "%<br>Fecha: " + f.date
        );
      });
      circle.on("mouseout", hideTooltip);
      const li = document.createElement("li");
      li.className = "fire";
      li.textContent = "🔥 Foco — Brillo " + f.brightness + "K — " + f.date;
      li.style.cursor = "pointer";
      li.addEventListener("click", function() {
        map.setView([f.lat, f.lon], 10, { animate: true });
        L.popup()
          .setLatLng([f.lat, f.lon])
          .setContent(
            "<b>🔥 Foco de calor</b><br>" +
            "Brillo: " + f.brightness + " K<br>" +
            "Confianza: " + f.confidence + "%<br>" +
            "Fecha: " + f.date + "<br>" +
            "Coords: " + f.lat.toFixed(3) + ", " + f.lon.toFixed(3)
          )
          .openOn(map);
      });
      document.getElementById("events").prepend(li);
    });
  } catch(err) { document.getElementById("fire-count").textContent = "Error"; }
}

async function loadQuakes() {
  try {
    const res = await fetch(API + "/quakes");
    const json = await res.json();
    allQuakes = json.data;
    cachedQuakesData = json.data;
    try { document.getElementById("qp-quakes-count").textContent = json.data.length; } catch(e) {}
    updateLastEvent();
    if (allQuakes.length > 0 && !lastQuakeTime) {
      lastQuakeTime = allQuakes[0].time;
    }
    renderQuakes(allQuakes);
  } catch(err) { document.getElementById("quake-count").textContent = "Error"; }
}

document.getElementById("mag-slider").addEventListener("input", function() {
  minMag = parseFloat(this.value);
  document.getElementById("mag-value").textContent = minMag.toFixed(1);
  renderQuakes(allQuakes);
});

document.getElementById("toggle-fires").addEventListener("change", function(e) {
  e.target.checked ? fireLayer.addTo(map) : map.removeLayer(fireLayer);
});
document.getElementById("toggle-quakes").addEventListener("change", function(e) {
  e.target.checked ? quakeLayer.addTo(map) : map.removeLayer(quakeLayer);
});
document.getElementById("toggle-regions").addEventListener("change", function(e) {
  e.target.checked ? regionLayer.addTo(map) : map.removeLayer(regionLayer);
});
document.getElementById("toggle-risk").addEventListener("change", function(e) {
  e.target.checked ? riskLayer.addTo(map) : map.removeLayer(riskLayer);
});
document.getElementById("toggle-heat").addEventListener("change", async function(e) {
  if (e.target.checked) {
    if (!heatLayer) await loadHeatmap();
    if (heatLayer) heatLayer.addTo(map);
  } else {
    if (heatLayer) map.removeLayer(heatLayer);
    document.getElementById("heat-status").classList.add("hidden");
  }
});

if(document.getElementById("fullscreen-btn")) document.getElementById("fullscreen-btn").addEventListener("click", function() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
    document.getElementById("fullscreen-btn").textContent = "⊠";
  } else {
    document.exitFullscreen();
    document.getElementById("fullscreen-btn").textContent = "⛶";
  }
});

function startCountdown() {
  let seconds = 300;
  const footer = document.getElementById("footer");
  const interval = setInterval(function() {
    seconds--;
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    footer.textContent = "CSN · NASA FIRMS · Próxima actualización en " + min + ":" + String(sec).padStart(2, "0");
    if (seconds <= 0) { clearInterval(interval); refresh(); }
  }, 1000);
}


// ===== ACTUALIZAR RESUMEN AMENAZAS SIDEBAR =====
function updateThreatSummary() {
  const rows = document.querySelectorAll("#threat-summary .threat-row");
  if (rows.length < 4) return;

  // Volcanes
  const volcAlerts = cachedVolcanoes.filter(function(v) { return v.alert !== "Verde"; });
  const volcRoja = cachedVolcanoes.filter(function(v) { return v.alert === "Roja"; });
  const volcColor = volcRoja.length > 0 ? "#ff3333" : volcAlerts.length > 0 ? "#ffd700" : "#4ade80";
  const volcText = volcRoja.length > 0 ? volcRoja.length + " en alerta roja" :
                   volcAlerts.length > 0 ? volcAlerts.length + " en alerta" : "Sin alertas";
  // Volcanes bar: proportion of alerted volcanoes
  var volcBarPct = cachedVolcanoes.length > 0 ? Math.round((volcAlerts.length / cachedVolcanoes.length) * 100) : 0;
  setBadge(rows[0], volcColor, volcText, volcBarPct);

  // Tsunami
  var tsunColor = cachedTsunamiData.count > 0 ? "#ff3333" : "#ffffff";
  var tsunText = cachedTsunamiData.count > 0 ?
    cachedTsunamiData.data[0].level + " activo" : "Sin alertas";
  var tsunBarPct = cachedTsunamiData.count > 0 ? 100 : 0;
  setBadge(rows[1], tsunColor, tsunText, tsunBarPct);

  // Clima
  var climaColor = "#ffffff";
  var climaText = "Sin datos";
  var climaBarPct = 0;
  if (cachedWeatherSummary) {
    climaColor = cachedWeatherSummary.national_alert_color || "#ffffff";
    var lvl = cachedWeatherSummary.national_alert_level || "SIN RIESGO";
    var rainy = cachedWeatherSummary.rainy_regions_count || 0;
    climaText = lvl === "SIN RIESGO" ? "Sin riesgo activo" :
                rainy + " regiones con lluvia";
    climaBarPct = Math.round((rainy / 15) * 100);
  }
  setBadge(rows[2], climaColor, climaText, climaBarPct);

  // Regiones
  var regColor = "#ffffff";
  var regText = "Calculando...";
  var regBarPct = 0;
  if (cachedRegions.length > 0) {
    var rojas = cachedRegions.filter(function(r) { return r.level === "ROJA"; }).length;
    var naranjas = cachedRegions.filter(function(r) { return r.level === "NARANJA"; }).length;
    var amarillas = cachedRegions.filter(function(r) { return r.level === "AMARILLA"; }).length;
    var verdeAlerta = cachedRegions.filter(function(r) { return r.level === "ALERTA VERDE"; }).length;
    if (rojas > 0) { regColor = "#ff3333"; regText = rojas + " en alerta roja"; }
    else if (naranjas > 0) { regColor = "#ff9500"; regText = naranjas + " en alerta naranja"; }
    else if (amarillas > 0) { regColor = "#ffd700"; regText = amarillas + " en alerta amarilla"; }
    else if (verdeAlerta > 0) { regColor = "#4ade80"; regText = verdeAlerta + " en alerta verde"; }
    else { regColor = "#ffffff"; regText = "Sin actividad"; }
    var alertedRegs = cachedRegions.filter(function(r) { return r.level !== "VERDE"; }).length;
    regBarPct = Math.round((alertedRegs / cachedRegions.length) * 100);
  }
  setBadge(rows[3], regColor, regText, regBarPct);
}

function setBadge(row, color, text, barPct) {
  var badge = row.querySelector(".threat-badge");
  if (badge) {
    badge.textContent = text;
    badge.style.color = color;
    badge.style.borderColor = color;
    badge.style.background = color + "22";
  }
  var barFill = row.querySelector(".threat-bar-fill");
  if (barFill) {
    barFill.style.width = (barPct || 0) + "%";
    barFill.style.background = color;
  }
}

// ===== THREAT HOVER TOOLTIPS =====
(function() {
  var ttEl = document.getElementById("threat-tooltip");
  var hideTimer = null;

  function getTooltipContent(type) {
    if (type === "volc") {
      if (!cachedVolcanoes.length) return "<div class='tt-header'>🌋 Volcanes</div><div class='tt-item'>Cargando datos...</div>";
      var html = "<div class='tt-header'>🌋 Volcanes Activos (" + cachedVolcanoes.length + ")</div>";
      var alerts = cachedVolcanoes.filter(function(v) { return v.alert !== "Verde"; });
      if (alerts.length > 0) {
        alerts.forEach(function(v) {
          var c = v.alert === "Roja" ? "#ff3333" : v.alert === "Naranja" ? "#ff9500" : "#ffd700";
          html += "<div class='tt-item'>• <b>" + v.name + "</b> — <span style='color:" + c + "'>" + v.alert + "</span><br>" +
            "<span style='color:#3a5270;font-size:0.68rem'>" + v.description + "</span></div>";
        });
      }
      var verdes = cachedVolcanoes.filter(function(v) { return v.alert === "Verde"; });
      if (verdes.length > 0) {
        html += "<div class='tt-item' style='color:#3a5270;margin-top:4px'>" + verdes.length + " volcanes en alerta verde (normal)</div>";
      }
      return html;
    }
    if (type === "tsun") {
      if (cachedTsunamiData.count > 0) {
        var t = cachedTsunamiData.data[0];
        var c = t.color || "#ff3333";
        return "<div class='tt-header'>🌊 Alerta Tsunami</div>" +
          "<div class='tt-alert' style='background:" + c + "22;border:1px solid " + c + ";color:" + c + "'>" +
          t.level + " — M" + t.magnitude + "</div>" +
          "<div class='tt-item'>📍 " + t.place + "</div>" +
          "<div class='tt-item'>🕳️ Prof: " + t.depth + " km</div>" +
          "<div class='tt-item' style='color:#3a5270;font-size:0.68rem'>Fuente: USGS · Click para ver en mapa</div>";
      }
      return "<div class='tt-header'>🌊 Tsunami</div><div class='tt-item' style='color:#4ade80'>✅ Sin alertas activas</div>" +
        "<div class='tt-item' style='color:#3a5270;font-size:0.68rem'>Monitoreo USGS — sismos costeros M≥6.0 Chile</div>";
    }
    if (type === "clima") {
      if (!cachedWeatherSummary) return "<div class='tt-header'>🌧️ Clima</div><div class='tt-item'>Cargando...</div>";
      var s = cachedWeatherSummary;
      var html = "<div class='tt-header'>🌧️ Clima — Resumen Nacional</div>";
      html += "<div class='tt-item'>Estado: <b style='color:" + s.national_alert_color + "'>" + s.national_alert_level + "</b></div>";
      html += "<div class='tt-item'>Regiones con lluvia: <b>" + s.rainy_regions_count + "</b></div>";
      if (s.top_3_risk && s.top_3_risk.length > 0) {
        html += "<div style='margin-top:6px;font-size:0.68rem;color:#5c7a9e;text-transform:uppercase;letter-spacing:0.08em'>Mayor riesgo:</div>";
        s.top_3_risk.forEach(function(r) {
          var rc = r.risk.color;
          html += "<div class='tt-item'>• <b>" + r.name + "</b> — <span style='color:" + rc + "'>" + r.risk.level + "</span> (" + r.risk.score + ")</div>";
        });
      }
      html += "<div class='tt-item' style='color:#3a5270;font-size:0.68rem;margin-top:4px'>Click para ver detalle completo</div>";
      return html;
    }
    if (type === "reg") {
      if (!cachedRegions.length) return "<div class='tt-header'>🗺️ Regiones</div><div class='tt-item'>Calculando...</div>";
      var html = "<div class='tt-header'>🗺️ Semáforo Regiones</div>";
      var groups = { "ROJA": [], "NARANJA": [], "AMARILLA": [], "ALERTA VERDE": [] };
      cachedRegions.forEach(function(r) {
        if (groups[r.level]) groups[r.level].push(r.name);
      });
      var colors = { "ROJA": "#ff3333", "NARANJA": "#ff9500", "AMARILLA": "#ffd700", "ALERTA VERDE": "#4ade80" };
      var any = false;
      Object.keys(groups).forEach(function(level) {
        if (groups[level].length > 0) {
          any = true;
          html += "<div class='tt-item'><span style='color:" + colors[level] + ";font-weight:700'>" + level + ":</span> " + groups[level].join(", ") + "</div>";
        }
      });
      if (!any) html += "<div class='tt-item' style='color:#4ade80'>✅ Todas las regiones sin actividad significativa</div>";
      html += "<div class='tt-item' style='color:#3a5270;font-size:0.68rem;margin-top:4px'>Click para ver índice de vulnerabilidad</div>";
      return html;
    }
    return "";
  }

  document.querySelectorAll("#threat-summary .threat-row").forEach(function(row) {
    var type = row.getAttribute("data-threat");

    row.addEventListener("mouseenter", function(e) {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      ttEl.innerHTML = getTooltipContent(type);
      ttEl.classList.remove("hidden");
      positionTooltip(e);
    });
    row.addEventListener("mousemove", function(e) { positionTooltip(e); });
    row.addEventListener("mouseleave", function() {
      hideTimer = setTimeout(function() { ttEl.classList.add("hidden"); }, 200);
    });

    // Click handlers
    row.addEventListener("click", function() {
      ttEl.classList.add("hidden");
      if (type === "volc") {
        document.getElementById("toggle-volcanoes").checked = true;
        volcanoLayer.addTo(map);
        map.setView([-33.5, -70.5], 5, { animate: true });
      } else if (type === "tsun") {
        if (cachedTsunamiData.count > 0) {
          var t = cachedTsunamiData.data[0];
          map.setView([t.lat, t.lon], 7, { animate: true });
        }
      } else if (type === "clima") {
        document.getElementById("weather-overlay").classList.remove("hidden");
        document.getElementById("btn-weather").classList.add("active");
        loadWeather();
      } else if (type === "reg") {
        document.getElementById("btn-vuln").click();
      }
    });
  });

  function positionTooltip(e) {
    var rect = document.getElementById("sidebar").getBoundingClientRect();
    ttEl.style.left = (rect.right + 8) + "px";
    ttEl.style.top = Math.min(e.clientY - 20, window.innerHeight - ttEl.offsetHeight - 10) + "px";
  }
})();

// ===== CLIMA OVERLAY =====
document.getElementById("btn-weather").addEventListener("click", function() {
  document.getElementById("weather-overlay").classList.remove("hidden");
  document.getElementById("btn-weather").classList.add("active");
  loadWeather();
});

document.getElementById("weather-close").addEventListener("click", function() {
  document.getElementById("weather-overlay").classList.add("hidden");
  document.getElementById("btn-weather").classList.remove("active");
});

async function loadWeather() {
  showLoading("weather-body", "Consultando datos meteorológicos", "Conectando con Open-Meteo para 15 regiones de Chile...");
  try {
    var res = await fetch(API + "/weather");
    if (!res.ok) throw new Error("Error " + res.status);
    var json = await res.json();
    cachedWeatherSummary = null;
    try {
      var sumRes = await fetch(API + "/weather/summary");
      cachedWeatherSummary = await sumRes.json();
      updateThreatSummary();
    } catch(e) {}

    if (!json.data || json.data.length === 0) {
      document.getElementById("weather-body").innerHTML = "<div class='loading-container'><div class='loading-text'>Sin datos meteorológicos disponibles en este momento.</div></div>";
      return;
    }

    document.getElementById("weather-body").innerHTML = "<div id='weather-grid'></div>";
    var grid = document.getElementById("weather-grid");
    json.data.forEach(function(r) {
      if (r.error) return;
      var risk = r.risk || {};
      var color = risk.color || "#5c7a9e";
      var level = risk.level || "?";
      var score = risk.score || 0;
      var card = document.createElement("div");
      card.className = "weather-card";
      card.style.borderColor = color + "66";
      card.innerHTML =
        "<div class='weather-card-header'>" +
          "<span class='weather-region-name'>" + r.name + "</span>" +
          "<span class='weather-badge' style='color:" + color + ";border-color:" + color + ";background:" + color + "22'>" + level + "</span>" +
        "</div>" +
        "<div class='weather-stats'>" +
          "<div class='weather-stat-item'>Lluvia actual<span>" + (r.current ? r.current.precipitation_mm : 0) + " mm/h</span></div>" +
          "<div class='weather-stat-item'>Acumulado 24h<span>" + (r.accumulated ? r.accumulated.last_24h_mm : 0) + " mm</span></div>" +
          "<div class='weather-stat-item'>Temperatura<span>" + (r.current ? r.current.temperature_c : "--") + " °C</span></div>" +
          "<div class='weather-stat-item'>Viento<span>" + (r.current ? r.current.wind_kmh : 0) + " km/h</span></div>" +
          "<div class='weather-stat-item'>Pronóstico 48h<span>" + (r.forecast ? r.forecast.next_48h_total_mm : 0) + " mm</span></div>" +
          "<div class='weather-stat-item'>Prob. máx.<span>" + (r.forecast ? r.forecast.max_probability_pct : 0) + "%</span></div>" +
        "</div>" +
        "<div class='weather-bar'><div class='weather-bar-fill' style='width:" + Math.min(100, score) + "%;background:" + color + "'></div></div>" +
        "<div class='weather-desc'>" + (risk.description || "Sin datos") + "</div>";
      grid.appendChild(card);
    });
  } catch(e) {
    document.getElementById("weather-body").innerHTML = "<div class='loading-container'><div class='loading-text'>❌ Error cargando datos meteorológicos</div><div class='loading-subtext'>El servidor puede estar procesando otras solicitudes. Intenta en unos segundos.</div></div>";
  }
}

// ===== BUSCADOR DE COMUNAS =====
(function() {
  var input = document.getElementById("search-input");
  var resultsList = document.getElementById("search-results");
  var clearBtn = document.getElementById("search-clear");
  var debounceTimer = null;
  var communeMarker = null;

  input.addEventListener("input", function() {
    var q = input.value.trim();
    clearBtn.classList.toggle("hidden", q.length === 0);
    if (debounceTimer) clearTimeout(debounceTimer);
    if (q.length < 2) { resultsList.classList.add("hidden"); return; }
    debounceTimer = setTimeout(function() { searchCommunes(q); }, 200);
  });

  input.addEventListener("focus", function() {
    if (input.value.trim().length >= 2 && resultsList.children.length > 0) {
      resultsList.classList.remove("hidden");
    }
  });

  clearBtn.addEventListener("click", function() {
    input.value = "";
    clearBtn.classList.add("hidden");
    resultsList.classList.add("hidden");
    if (communeMarker) { map.removeLayer(communeMarker); communeMarker = null; }
  });

  // Close results on outside click
  document.addEventListener("click", function(e) {
    if (!e.target.closest("#search-container")) {
      resultsList.classList.add("hidden");
    }
  });

  async function searchCommunes(query) {
    try {
      var res = await fetch(API + "/communes/search?q=" + encodeURIComponent(query));
      var json = await res.json();
      resultsList.innerHTML = "";
      if (json.results.length === 0) {
        resultsList.innerHTML = "<li class='search-no-results'>No se encontraron resultados para \"" + query + "\"</li>";
        resultsList.classList.remove("hidden");
        return;
      }
      json.results.forEach(function(c) {
        var li = document.createElement("li");
        li.innerHTML = "<span class='sr-name'>" + highlightMatch(c.name, query) + "</span><span class='sr-region'>" + c.region + "</span>";
        li.addEventListener("click", function() {
          selectCommune(c);
        });
        resultsList.appendChild(li);
      });
      resultsList.classList.remove("hidden");
    } catch(e) {
      console.error("Error buscando comunas:", e);
    }
  }

  function highlightMatch(name, query) {
    var idx = name.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) {
      // Try normalized
      return name;
    }
    return name.substring(0, idx) + "<span class='sr-match'>" + name.substring(idx, idx + query.length) + "</span>" + name.substring(idx + query.length);
  }

  function selectCommune(c) {
    input.value = c.name;
    resultsList.classList.add("hidden");

    // Close mobile sidebar if open
    if (window.closeMobileMenu) window.closeMobileMenu();

    // Fly to commune
    map.flyTo([c.lat, c.lon], 11, { duration: 1.5 });

    // Place marker
    if (communeMarker) map.removeLayer(communeMarker);
    communeMarker = L.marker([c.lat, c.lon], {
      icon: L.divIcon({
        className: "",
        html: "<div style='background:#4fc3f7;border:3px solid white;border-radius:50%;width:18px;height:18px;box-shadow:0 0 12px #4fc3f7,0 0 24px #4fc3f766'></div>",
        iconSize: [18, 18], iconAnchor: [9, 9]
      })
    }).addTo(map).bindPopup("📍 <b>" + c.name + "</b><br>" + c.region).openPopup();

    // Load local info
    loadCommuneInfo(c);
  }

  async function loadCommuneInfo(c) {
    var panel = document.getElementById("commune-panel");
    var body = document.getElementById("commune-panel-body");
    var title = document.getElementById("commune-panel-title");
    panel.classList.remove("hidden");
    title.textContent = "📍 " + c.name + " — " + c.region;
    body.innerHTML = "<div id='commune-loading'>⏳ Cargando información local...</div>";

    try {
      var res = await fetch(API + "/communes/info/" + c.lat + "/" + c.lon);
      var data = await res.json();
      var html = "";

      // Clima
      if (data.weather && data.weather.current) {
        var w = data.weather;
        var rc = w.risk ? w.risk.color : "#5c7a9e";
        html += "<div class='cp-section'>" +
          "<div class='cp-section-title'>🌡️ Clima actual</div>" +
          "<div class='cp-weather-grid'>" +
            "<div class='cp-weather-item'><span class='cp-weather-value'>" + w.current.temperature_c + "°C</span><span class='cp-weather-label'>Temperatura</span></div>" +
            "<div class='cp-weather-item'><span class='cp-weather-value'>" + w.current.precipitation_mm + " mm</span><span class='cp-weather-label'>Lluvia</span></div>" +
            "<div class='cp-weather-item'><span class='cp-weather-value'>" + w.current.wind_kmh + " km/h</span><span class='cp-weather-label'>Viento</span></div>" +
            "<div class='cp-weather-item'><span class='cp-weather-value' style='color:" + rc + "'>" + (w.risk ? w.risk.level : "--") + "</span><span class='cp-weather-label'>Riesgo hídrico</span></div>" +
          "</div></div>";
      }

      // Sismos
      html += "<div class='cp-section'><div class='cp-section-title'>🌍 Sismos cercanos (50 km)</div>";
      if (data.quakes.count > 0) {
        html += "<div style='font-size:0.72rem;color:#5c7a9e;margin-bottom:6px'>" + data.quakes.count + " sismos en las últimas 24h</div>";
        data.quakes.data.slice(0, 8).forEach(function(q) {
          var qc = q.magnitude >= 6 ? "#ff3333" : q.magnitude >= 4.5 ? "#ffd700" : "#4ade80";
          html += "<div class='cp-item' onclick='map.flyTo([" + q.lat + "," + q.lon + "],10)'>" +
            "<span style='color:" + qc + ";font-weight:700'>M" + q.magnitude + "</span> · " + q.place +
            "<br><span style='color:#3a5270;font-size:0.65rem'>" + q.distance_km + " km · " + timeAgo(q.time) + "</span></div>";
        });
      } else {
        html += "<div class='cp-empty'>Sin sismos en las últimas 24h dentro de 50 km</div>";
      }
      html += "</div>";

      // Incendios
      html += "<div class='cp-section'><div class='cp-section-title'>🔥 Focos de calor cercanos (80 km)</div>";
      if (data.fires.count > 0) {
        html += "<div style='font-size:0.72rem;color:#5c7a9e;margin-bottom:6px'>" + data.fires.count + " focos activos</div>";
        data.fires.data.slice(0, 5).forEach(function(f) {
          html += "<div class='cp-item' onclick='map.flyTo([" + f.lat + "," + f.lon + "],12)'>" +
            "🔥 Brillo: " + f.brightness + " K · Confianza: " + f.confidence + "%" +
            "<br><span style='color:#3a5270;font-size:0.65rem'>" + f.distance_km + " km</span></div>";
        });
      } else {
        html += "<div class='cp-empty'>Sin focos de calor activos en 80 km</div>";
      }
      html += "</div>";

      // Volcanes
      html += "<div class='cp-section'><div class='cp-section-title'>🌋 Volcanes próximos (150 km)</div>";
      if (data.volcanoes.count > 0) {
        data.volcanoes.data.forEach(function(v) {
          var vc = v.alert === "Roja" ? "#ff3333" : v.alert === "Naranja" ? "#ff9500" : v.alert === "Amarilla" ? "#ffd700" : "#4ade80";
          html += "<div class='cp-item' onclick='map.flyTo([" + v.lat + "," + v.lon + "],10)'>" +
            "🌋 <b>" + v.name + "</b> — <span style='color:" + vc + "'>" + v.alert + "</span>" +
            "<br><span style='color:#3a5270;font-size:0.65rem'>" + v.distance_km + " km · " + v.elevation + " m · " + v.region + "</span></div>";
        });
      } else {
        html += "<div class='cp-empty'>Sin volcanes monitoreados en 150 km</div>";
      }
      html += "</div>";

      body.innerHTML = html;
    } catch(e) {
      body.innerHTML = "<div class='cp-empty'>❌ Error cargando datos. Verifica que el backend esté activo.</div>";
    }
  }

  // Close commune panel
  document.getElementById("commune-panel-close").addEventListener("click", function() {
    document.getElementById("commune-panel").classList.add("hidden");
    if (communeMarker) { map.removeLayer(communeMarker); communeMarker = null; }
  });
})();

async function refresh() {
  await loadQuakes();
  await loadFires();
  await loadRisk();
  await loadTrends();
  await loadVolcanoes();
  await loadTsunami();
  await loadRegions();
  loadAI();
  loadWeatherSummary();
  checkEmailAlerts();
  startCountdown();
  if (liveInterval) clearInterval(liveInterval);
  liveInterval = setInterval(liveTick, 30000);
}

async function loadWeatherSummary() {
  try {
    var res = await fetch(API + "/weather/summary");
    cachedWeatherSummary = await res.json();
    cachedWeatherAll = cachedWeatherSummary.all_regions || [];
    try { document.getElementById("qp-clima-count").textContent = cachedWeatherAll.filter(function(r){return !r.error;}).length; } catch(e) {}
    updateLastEvent();
    updateThreatSummary();
  } catch(e) { console.error("Error weather summary:", e); }
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(function() {});
}

setTimeout(function() { map.invalidateSize(); }, 100);
requestNotifications();
renderRiskZones();
refresh();