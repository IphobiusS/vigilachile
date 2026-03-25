from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fires import get_fires
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
from datetime import datetime, timedelta, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Cache simple para evitar llamadas repetidas =====
_cache = {}
_cache_ttl = 60  # segundos
_cache_ttl_weather = 7200  # 2 horas para clima

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
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

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

@app.get("/risk")
def risk():
    q = cached_quakes()
    f = cached_fires()
    return calculate_risk(q["data"], f["data"])

@app.get("/analyze")
def analyze():
    q = cached_quakes()
    f = cached_fires()
    r = calculate_risk(q["data"], f["data"])
    # Gather all threat data for comprehensive report
    v = get_volcanoes()
    t = get_tsunami_alerts()
    try:
        ws = get_weather_summary()
    except:
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
                except:
                    pass
            if i == 0:
                today_count = len(events)
                today_max = max(mags) if mags else 0.0
            else:
                yesterday_count = len(events)
                yesterday_max = max(mags) if mags else 0.0
        except:
            pass

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
    q = cached_quakes()
    f = cached_fires()
    r = calculate_risk(q["data"], f["data"])
    t = get_trends_data()
    v = get_volcanoes()
    ts = get_tsunami_alerts()
    w = cached_weather()
    reg = calculate_region_risk(q["data"], f["data"])
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

    prompt = (
        "Eres el sistema VigilaChile. Genera un analisis ejecutivo en español (maximo 150 palabras) "
        "cubriendo TODAS las amenazas monitoreadas para incluir en un PDF profesional:\n\n"
        "SISMOS: " + str(total_quakes) + " eventos, max M" + str(max_mag) + ", zona activa: " + top_zone + "\n"
        "INCENDIOS: " + str(total_fires) + " focos activos NASA FIRMS\n"
        "VOLCANES: " + str(len(volc_alerts)) + " en alerta (" + ", ".join([x["name"] + " " + x["alert"] for x in volc_alerts]) + ")\n" if volc_alerts else
        "VOLCANES: Todos en alerta verde\n"
        "TSUNAMI: " + ("ALERTA ACTIVA" if tsun_count > 0 else "Sin alertas") + "\n"
        "RIESGO: " + str(r.get("score", "--")) + "/10 (" + r.get("level", "--") + ")\n"
        "TENDENCIA: " + t.get("trend", "--") + " (" + str(t.get("percentage", 0)) + "% vs ayer)\n\n"
        "Escribe un parrafo fluido cubriendo sismos, incendios, volcanes, tsunami y clima. "
        "REGLAS ESTRICTAS: "
        "1) NO pongas titulo ni encabezado. Empieza directamente con el analisis. "
        "2) NO uses markdown, asteriscos, numerales (#), guiones, blockquotes (>), lineas (---), negritas ni simbolos especiales. "
        "3) Solo texto plano en parrafos continuos. Tono tecnico profesional. Maximo 120 palabras."
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
    except:
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
    # Use cache (1 hour TTL)
    now_ts = datetime.now(timezone.utc).timestamp()
    if "history" in _cache and now_ts - _cache["history"]["ts"] < 3600:
        return _cache["history"]["data"]

    from concurrent.futures import ThreadPoolExecutor
    now = datetime.now(timezone.utc)

    def fetch_day(i):
        date = (now - timedelta(days=i)).strftime("%Y%m%d")
        results = []
        try:
            res = requests.get(
                "https://api.xor.cl/sismo/historic/" + date,
                timeout=5
            )
            for s in res.json().get("events", []):
                try:
                    results.append({
                        "lat": float(s["latitude"]),
                        "lon": float(s["longitude"]),
                        "magnitude": float(s["magnitude"]["value"]),
                        "depth": float(s.get("depth", 0)),
                        "place": s.get("geo_reference", ""),
                        "time": s.get("utc_date", "")
                    })
                except:
                    continue
        except:
            pass
        return results

    quakes = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(fetch_day, range(1, 31))
        for day_quakes in results:
            quakes.extend(day_quakes)

    data = {"count": len(quakes), "data": quakes}
    _cache["history"] = {"data": data, "ts": now_ts}
    return data