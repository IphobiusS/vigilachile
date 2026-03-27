from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fires import get_fires, cluster_fires
from quakes import get_quakes
from risk import calculate_risk
from analyzer import analyze_seismic_pattern, estimate_population
from volcanoes import get_volcanoes
from tsunami import get_tsunami_alerts, get_aftershocks
from pdf_report import generate_pdf
from regions import calculate_region_risk, get_vulnerability_index
from alerts import send_quake_alert
from weather import get_weather_data, get_weather_summary
from communes import search_communes, COMMUNES
import requests
import os
import logging
from datetime import datetime, timedelta, timezone

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vigilachile")

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

app = FastAPI(
    title="VigilaChile API",
    description="Monitoreo multi-amenaza en tiempo real para Chile",
    version="2.0.0"
)

# ===== CORS — restringido a dominios conocidos =====
ALLOWED_ORIGINS = [
    "https://vigilachile.vercel.app",
    "https://vigilachile.cl",
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ===== Metricas de impacto =====
_metrics = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "total_requests": 0,
    "requests_by_endpoint": {},
    "alerts_sent": 0,
    "alerts_log": [],
    "pdf_generated": 0,
    "unique_sessions": set(),
    "last_quake_detected": None,
    "last_fire_count": 0,
    "errors": 0,
}


@app.middleware("http")
async def track_metrics(request: Request, call_next):
    _metrics["total_requests"] += 1
    path = request.url.path
    _metrics["requests_by_endpoint"][path] = _metrics["requests_by_endpoint"].get(path, 0) + 1

    # Track unique sessions via User-Agent + IP (approximation)
    ua = request.headers.get("user-agent", "")[:50]
    client = request.client.host if request.client else "unknown"
    session_key = client + "|" + ua[:20]
    _metrics["unique_sessions"].add(session_key)

    response = await call_next(request)
    return response

# ===== Cache simple para evitar llamadas repetidas =====
_cache = {}
_cache_ttl = 60  # segundos
_cache_ttl_weather = 7200  # 2 horas para clima (evitar rate limit WeatherAPI)

def get_cached(key, fn):
    now = datetime.now(timezone.utc).timestamp()
    ttl = _cache_ttl_weather if key == "weather" else _cache_ttl
    if key in _cache and now - _cache[key]["ts"] < ttl:
        return _cache[key]["data"]
    data = fn()
    # Don't cache weather if ALL regions have errors
    if key == "weather":
        valid = [r for r in data.get("data", []) if "error" not in r]
        if len(valid) == 0 and key in _cache:
            return _cache[key]["data"]  # return old data instead of errors
        if len(valid) == 0:
            return data  # no old data, return errors but don't cache
    _cache[key] = {"data": data, "ts": now}
    return data

def cached_quakes():
    return get_cached("quakes", get_quakes)

def cached_fires():
    return get_cached("fires", get_fires)

def cached_weather():
    return get_cached("weather", get_weather_data)

# ===== Endpoints =====

@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "uptime_since": _metrics["started_at"]
    }

@app.get("/metrics")
def metrics():
    """Metricas de impacto y uso de la plataforma."""
    now = datetime.now(timezone.utc)
    started = datetime.fromisoformat(_metrics["started_at"])
    uptime_hours = round((now - started).total_seconds() / 3600, 1)

    return {
        "uptime_hours": uptime_hours,
        "started_at": _metrics["started_at"],
        "total_requests": _metrics["total_requests"],
        "unique_sessions_approx": len(_metrics["unique_sessions"]),
        "requests_by_endpoint": dict(sorted(
            _metrics["requests_by_endpoint"].items(),
            key=lambda x: x[1], reverse=True
        )),
        "alerts_sent": _metrics["alerts_sent"],
        "alerts_log": _metrics["alerts_log"][-20:],
        "pdf_generated": _metrics["pdf_generated"],
        "last_quake_detected": _metrics["last_quake_detected"],
        "last_fire_count": _metrics["last_fire_count"],
        "errors": _metrics["errors"],
        "cache_keys": list(_cache.keys()),
        "timestamp": now.isoformat()
    }

@app.get("/cache/clear")
def cache_clear():
    _cache.clear()
    return {"status": "cache cleared"}

@app.get("/quakes")
def quakes():
    return cached_quakes()

@app.get("/fires")
def fires():
    return cached_fires()

@app.get("/fires/clusters")
def fire_clusters():
    """
    Detección de frentes de incendio mediante clustering geoespacial DBSCAN.
    Agrupa focos VIIRS cercanos (<1.5km) en incendios individuales.
    Calcula: centroide, FRP total, área estimada, severidad.
    """
    f = cached_fires()
    return cluster_fires(f.get("data", []))

@app.get("/risk")
def risk():
    q = cached_quakes()
    f = cached_fires()
    return calculate_risk(q["data"], f["data"])

@app.get("/analyze")
def analyze():
    from concurrent.futures import ThreadPoolExecutor
    q = cached_quakes()
    f = cached_fires()
    r = calculate_risk(q["data"], f["data"])
    # Gather all threat data in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_v = executor.submit(get_volcanoes)
        fut_t = executor.submit(get_tsunami_alerts)
        fut_ws = executor.submit(lambda: get_weather_summary())
        v = fut_v.result()
        t = fut_t.result()
        try:
            ws = fut_ws.result()
        except Exception as e:
            logger.warning("Weather summary failed: %s", e)
            ws = None
    return analyze_seismic_pattern(q["data"], f["data"], r, volcanoes=v, tsunami=t, weather_summary=ws)

@app.get("/population/{lat}/{lon}/{magnitude}")
def population(lat: float, lon: float, magnitude: float):
    return estimate_population(lat, lon, magnitude)

@app.get("/volcanoes")
def volcanoes():
    return get_volcanoes()

@app.get("/tsunami")
def tsunami():
    return get_tsunami_alerts()

@app.get("/aftershocks/{lat}/{lon}")
def aftershocks(lat: float, lon: float):
    return get_aftershocks(lat, lon)

@app.get("/regions")
def regions():
    q = cached_quakes()
    f = cached_fires()
    return calculate_region_risk(q["data"], f["data"])

@app.get("/vulnerability")
def vulnerability():
    q = cached_quakes()
    f = cached_fires()
    return get_vulnerability_index(q["data"], f["data"])

@app.get("/check-alerts")
def check_alerts():
    q = cached_quakes()
    triggered = []
    for quake in q["data"]:
        if quake["magnitude"] >= 5.0:
            sent = send_quake_alert(quake)
            if sent:
                triggered.append(quake["place"])
                _metrics["alerts_sent"] += 1
                _metrics["alerts_log"].append({
                    "time": datetime.now(timezone.utc).isoformat(),
                    "place": quake["place"],
                    "magnitude": quake["magnitude"]
                })
    if q["data"]:
        _metrics["last_quake_detected"] = q["data"][0].get("place", "")
    return {"checked": len(q["data"]), "triggered": triggered}

def get_trends_data():
    # Use Chile timezone (UTC-3) for "today" and "yesterday"
    CHILE_TZ = timezone(timedelta(hours=-3))
    now_chile = datetime.now(CHILE_TZ)
    today_count = 0
    yesterday_count = 0
    today_max = 0.0
    yesterday_max = 0.0
    for i in range(2):
        date = (now_chile - timedelta(days=i)).strftime("%Y%m%d")
        try:
            res = requests.get(
                "https://api.xor.cl/sismo/historic/" + date,
                timeout=8
            )
            events = res.json().get("events", [])
            mags = []
            for e in events:
                try:
                    mags.append(float(e["magnitude"]["value"]))
                except (KeyError, ValueError, TypeError):
                    pass
            if i == 0:
                today_count = len(events)
                today_max = max(mags) if mags else 0.0
            else:
                yesterday_count = len(events)
                yesterday_max = max(mags) if mags else 0.0
        except Exception as e:
            logger.debug("Trends fetch day %d failed: %s", i, e)

    diff = today_count - yesterday_count
    pct = round(diff / yesterday_count * 100) if yesterday_count > 0 else 0
    return {
        "today": today_count,
        "yesterday": yesterday_count,
        "difference": diff,
        "percentage": pct,
        "trend": "aumentando" if diff > 5 else "disminuyendo" if diff < -5 else "estable",
        "today_max": round(today_max, 1),
        "yesterday_max": round(yesterday_max, 1)
    }

@app.get("/trends")
def trends():
    return get_trends_data()

@app.get("/report/pdf")
def report_pdf():
    from concurrent.futures import ThreadPoolExecutor
    q = cached_quakes()
    f = cached_fires()

    # Run independent calls in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        fut_risk = executor.submit(calculate_risk, q["data"], f["data"])
        fut_trends = executor.submit(get_trends_data)
        fut_volc = executor.submit(get_volcanoes)
        fut_tsun = executor.submit(get_tsunami_alerts)
        fut_weather = executor.submit(cached_weather)
        fut_reg = executor.submit(calculate_region_risk, q["data"], f["data"])

        r = fut_risk.result()
        t = fut_trends.result()
        v = fut_volc.result()
        ts = fut_tsun.result()
        w = fut_weather.result()
        reg = fut_reg.result()

    quakes_data = q["data"]
    fires_data = f["data"]

    total_quakes = len(quakes_data)
    max_mag = max([x["magnitude"] for x in quakes_data], default=0)
    total_fires = len(fires_data)

    top_zones = {}
    for qk in quakes_data:
        zone = qk["place"].split("de ")[-1].split("al ")[0].strip()
        top_zones[zone] = top_zones.get(zone, 0) + 1
    top_zone = max(top_zones, key=top_zones.get) if top_zones else "Chile"

    volc_data = v.get("data", [])
    volc_alerts = [x for x in volc_data if x.get("alert") != "Verde"]
    tsun_count = ts.get("count", 0)

    if volc_alerts:
        volc_str = "VOLCANES: " + str(len(volc_alerts)) + " en alerta (" + ", ".join([x["name"] + " " + x["alert"] for x in volc_alerts]) + ")\n"
    else:
        volc_str = "VOLCANES: Todos en alerta verde\n"

    prompt = (
        "Eres un sismologo chileno redactando un informe tecnico para un PDF profesional. "
        "CONTEXTO: Chile es el pais mas sismico del mundo. 20-50 sismos diarios M2.5+ es NORMAL. "
        "Solo M6.0+ amerita preocupacion. Volcanes en Alerta Amarilla es vigilancia estandar, NO emergencia. "
        "NO exageres. Si la actividad es normal para Chile, dilo.\n\n"
        "DATOS:\n"
        "SISMOS: " + str(total_quakes) + " eventos, max M" + str(max_mag) + ", zona activa: " + top_zone + "\n"
        "INCENDIOS: " + str(total_fires) + " focos activos\n"
        + volc_str +
        "TSUNAMI: " + ("ALERTA ACTIVA" if tsun_count > 0 else "Sin alertas") + "\n"
        "RIESGO: " + str(r.get("score", "--")) + "/10 (" + r.get("level", "--") + ")\n"
        "TENDENCIA: " + t.get("trend", "--") + " (" + str(t.get("percentage", 0)) + "% vs ayer)\n\n"
        "Escribe un parrafo tecnico, sobrio y realista. "
        "REGLAS ABSOLUTAS: "
        "1) Primera palabra: 'El territorio' o 'Chile' o 'Se registraron'. JAMAS titulo, encabezado, ANALISIS, REPORTE, VIGILACHILE. "
        "2) JAMAS firma ni footer: 'Generado por', 'VigilaChile', 'Sistema'. Termina con frase de cierre y punto. "
        "3) Sin simbolos (■●►), markdown, asteriscos, negritas. Solo texto plano. "
        "4) Tono sobrio, NO alarmista. Maximo 120 palabras."
    )

    try:
        if not ANTHROPIC_API_KEY:
            raise ValueError("API key no configurada")
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )
        ai = res.json()["content"][0]["text"]
    except Exception as e:
        logger.warning("PDF AI report failed: %s", e)
        ai = (
            "SISMOS: Se registraron " + str(total_quakes) + " eventos, magnitud maxima M" + str(max_mag) +
            ", zona mas activa " + top_zone + ". " +
            "INCENDIOS: " + str(total_fires) + " focos de calor activos. " +
            "VOLCANES: " + (str(len(volc_alerts)) + " en alerta." if volc_alerts else "Todos en verde.") + " " +
            "TSUNAMI: " + ("Alerta activa." if tsun_count > 0 else "Sin alertas.") + " " +
            "Riesgo compuesto: " + str(r.get("score", "--")) + "/10 (" + r.get("level", "--") + ")."
        )

    pdf_bytes = generate_pdf(quakes_data, fires_data, r, ai, t,
                             volcanoes=v, tsunami=ts, weather=w, regions=reg)
    _metrics["pdf_generated"] += 1
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=VigilaChile_" + now_str + ".pdf"}
    )


@app.get("/weather")
def weather():
    return cached_weather()

@app.get("/weather/summary")
def weather_summary():
    return get_weather_summary()

@app.get("/weather/region/{region_id}")
def weather_region(region_id: str):
    data = cached_weather()
    for r in data["data"]:
        if r["id"] == region_id:
            return r
    return {"error": "Región no encontrada"}

@app.get("/communes/search")
def communes_search(q: str = ""):
    return search_communes(q)


@app.get("/communes/info/{lat}/{lon}")
def commune_info(lat: float, lon: float):
    """Info local para una comuna: sismos 50km, incendios, volcanes próximos, clima."""
    q = cached_quakes()
    f = cached_fires()
    w = cached_weather()

    # Sismos dentro de 50km
    nearby_quakes = []
    for quake in q["data"]:
        dlat = abs(quake["lat"] - lat)
        dlon = abs(quake["lon"] - lon)
        # Aproximación rápida: 1 grado ~ 111km
        dist_approx = ((dlat * 111) ** 2 + (dlon * 111 * 0.7) ** 2) ** 0.5
        if dist_approx <= 50:
            nearby_quakes.append({**quake, "distance_km": round(dist_approx, 1)})
    nearby_quakes.sort(key=lambda x: x["distance_km"])

    # Incendios dentro de 80km
    nearby_fires = []
    for fire in f["data"]:
        dlat = abs(fire["lat"] - lat)
        dlon = abs(fire["lon"] - lon)
        dist_approx = ((dlat * 111) ** 2 + (dlon * 111 * 0.7) ** 2) ** 0.5
        if dist_approx <= 80:
            nearby_fires.append({**fire, "distance_km": round(dist_approx, 1)})
    nearby_fires.sort(key=lambda x: x["distance_km"])

    # Volcanes dentro de 150km
    from volcanoes import get_volcanoes
    volc_data = get_volcanoes()
    nearby_volcanoes = []
    for v in volc_data["data"]:
        dlat = abs(v["lat"] - lat)
        dlon = abs(v["lon"] - lon)
        dist_approx = ((dlat * 111) ** 2 + (dlon * 111 * 0.7) ** 2) ** 0.5
        if dist_approx <= 150:
            nearby_volcanoes.append({**v, "distance_km": round(dist_approx, 1)})
    nearby_volcanoes.sort(key=lambda x: x["distance_km"])

    # Clima de la región más cercana
    closest_weather = None
    min_dist = 9999
    for region in w.get("data", []):
        if "error" in region:
            continue
        dlat = abs(region["lat"] - lat)
        dlon = abs(region["lon"] - lon)
        dist = (dlat ** 2 + dlon ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            closest_weather = region

    return {
        "quakes": {"count": len(nearby_quakes), "data": nearby_quakes[:15]},
        "fires": {"count": len(nearby_fires), "data": nearby_fires[:10]},
        "volcanoes": {"count": len(nearby_volcanoes), "data": nearby_volcanoes[:5]},
        "weather": closest_weather
    }


@app.get("/history")
def history():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    now = datetime.now(timezone.utc)

    def fetch_day(i):
        date = (now - timedelta(days=i)).strftime("%Y%m%d")
        day_quakes = []
        try:
            res = requests.get(
                "https://api.xor.cl/sismo/historic/" + date,
                timeout=8
            )
            data = res.json()
            for s in data.get("events", []):
                try:
                    day_quakes.append({
                        "lat": float(s["latitude"]),
                        "lon": float(s["longitude"]),
                        "magnitude": float(s["magnitude"]["value"]),
                        "depth": float(s.get("depth", 0)),
                        "place": s.get("geo_reference", ""),
                        "time": s.get("utc_date", "")
                    })
                except (KeyError, ValueError, TypeError):
                    continue
        except Exception as e:
            logger.debug("History fetch day failed: %s", e)
        return day_quakes

    quakes = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_day, i): i for i in range(1, 31)}
        for future in as_completed(futures):
            try:
                quakes.extend(future.result())
            except Exception as e:
                logger.debug("History future failed: %s", e)
                continue

    return {"count": len(quakes), "data": quakes}