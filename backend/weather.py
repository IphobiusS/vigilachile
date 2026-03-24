import requests
from datetime import datetime, timezone, timedelta

# Coordenadas representativas de cada región de Chile
REGION_COORDS = [
    {"id": "tarapaca",      "name": "Tarapacá",       "lat": -20.2, "lon": -69.3, "zone": "norte_extremo"},
    {"id": "antofagasta",   "name": "Antofagasta",     "lat": -23.6, "lon": -70.4, "zone": "norte"},
    {"id": "atacama",       "name": "Atacama",         "lat": -27.4, "lon": -70.3, "zone": "norte"},
    {"id": "coquimbo",      "name": "Coquimbo",        "lat": -30.0, "lon": -71.2, "zone": "norte_chico"},
    {"id": "valparaiso",    "name": "Valparaíso",      "lat": -33.0, "lon": -71.6, "zone": "central"},
    {"id": "metropolitana", "name": "Metropolitana",   "lat": -33.5, "lon": -70.6, "zone": "central"},
    {"id": "ohiggins",      "name": "O'Higgins",       "lat": -34.6, "lon": -71.0, "zone": "central"},
    {"id": "maule",         "name": "Maule",           "lat": -35.5, "lon": -71.5, "zone": "sur"},
    {"id": "nuble",         "name": "Ñuble",           "lat": -36.7, "lon": -71.8, "zone": "sur"},
    {"id": "biobio",        "name": "Biobío",          "lat": -37.5, "lon": -72.5, "zone": "sur"},
    {"id": "araucania",     "name": "Araucanía",       "lat": -38.9, "lon": -72.6, "zone": "sur"},
    {"id": "los_rios",      "name": "Los Ríos",        "lat": -39.8, "lon": -73.2, "zone": "sur"},
    {"id": "los_lagos",     "name": "Los Lagos",       "lat": -41.5, "lon": -72.9, "zone": "sur"},
    {"id": "aysen",         "name": "Aysén",           "lat": -45.6, "lon": -72.1, "zone": "austral"},
    {"id": "magallanes",    "name": "Magallanes",      "lat": -53.2, "lon": -70.9, "zone": "austral"},
]

# Umbrales de lluvia por zona geográfica
# El norte de Chile es hipeárido — 5mm en Atacama es una emergencia
# El sur recibe lluvia constantemente — necesita mucho más para ser peligroso
ZONE_THRESHOLDS = {
    "norte_extremo": {"critical": 5,  "high": 2,  "moderate": 0.5, "low": 0.1},
    "norte":         {"critical": 10, "high": 5,  "moderate": 1,   "low": 0.2},
    "norte_chico":   {"critical": 20, "high": 10, "moderate": 3,   "low": 0.5},
    "central":       {"critical": 40, "high": 20, "moderate": 8,   "low": 1},
    "sur":           {"critical": 80, "high": 40, "moderate": 15,  "low": 3},
    "austral":       {"critical": 120,"high": 60, "moderate": 20,  "low": 5},
}


def get_weather_data():
    """
    Obtiene datos meteorológicos de Open-Meteo para las 15 regiones.
    Sequential con delay para evitar 429 rate limit.
    """
    import time as _time
    results = []
    now = datetime.now(timezone.utc)
    month = now.month
    seasonal_factor = 1.4 if 5 <= month <= 8 else 1.0

    for idx, region in enumerate(REGION_COORDS):
        if idx > 0:
            _time.sleep(0.5)

        success = False
        for attempt in range(2):
            try:
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": region["lat"],
                    "longitude": region["lon"],
                    "hourly": "precipitation,precipitation_probability,windspeed_10m,windgusts_10m,temperature_2m,relativehumidity_2m",
                    "current_weather": True,
                    "timezone": "America/Santiago",
                    "forecast_days": 2,
                    "timeformat": "unixtime"
                }
                res = requests.get(url, params=params, timeout=8)
                if res.status_code == 429:
                    _time.sleep(2)
                    continue
                res.raise_for_status()
                data = res.json()

                hourly = data.get("hourly", {})
                times = hourly.get("time", [])
                precip = hourly.get("precipitation", [])
                precip_prob = hourly.get("precipitation_probability", [])
                wind_h = hourly.get("windspeed_10m", [])
                gusts_h = hourly.get("windgusts_10m", [])
                temp_h = hourly.get("temperature_2m", [])
                humidity_h = hourly.get("relativehumidity_2m", [])
                current = data.get("current_weather", {})

                now_ts = now.timestamp()
                current_idx = 0
                for i, t in enumerate(times):
                    if t <= now_ts:
                        current_idx = i

                precip_now = float(precip[current_idx]) if current_idx < len(precip) else 0
                precip_24h = sum(float(precip[i]) for i in range(max(0, current_idx - 23), current_idx + 1) if i < len(precip))
                precip_72h = sum(float(precip[i]) for i in range(max(0, current_idx - 71), current_idx + 1) if i < len(precip))

                forecast_48h = []
                for i in range(current_idx + 1, min(current_idx + 49, len(times))):
                    forecast_48h.append({
                        "time": times[i],
                        "precipitation": round(float(precip[i]) if i < len(precip) else 0, 2),
                        "probability": int(precip_prob[i]) if i < len(precip_prob) else 0
                    })

                max_forecast_precip = max([h["precipitation"] for h in forecast_48h], default=0)
                max_forecast_prob = max([h["probability"] for h in forecast_48h], default=0)
                precip_forecast_total = sum(h["precipitation"] for h in forecast_48h)

                wind_now = float(wind_h[current_idx]) if current_idx < len(wind_h) else 0
                gust_now = float(gusts_h[current_idx]) if current_idx < len(gusts_h) else 0
                temp_now = float(temp_h[current_idx]) if current_idx < len(temp_h) else 0
                humidity_now = float(humidity_h[current_idx]) if current_idx < len(humidity_h) else 0

                risk = calculate_hydro_risk(
                    region=region, precip_now=precip_now, precip_24h=precip_24h,
                    precip_72h=precip_72h, precip_forecast=precip_forecast_total,
                    max_forecast=max_forecast_precip, max_prob=max_forecast_prob,
                    wind=wind_now, gust=gust_now, seasonal_factor=seasonal_factor
                )

                results.append({
                    "id": region["id"], "name": region["name"],
                    "lat": region["lat"], "lon": region["lon"], "zone": region["zone"],
                    "current": {
                        "precipitation_mm": round(precip_now, 2),
                        "temperature_c": round(temp_now, 1),
                        "humidity_pct": round(humidity_now, 1),
                        "wind_kmh": round(wind_now, 1),
                        "gust_kmh": round(gust_now, 1),
                        "weathercode": current.get("weathercode", 0)
                    },
                    "accumulated": {
                        "last_24h_mm": round(precip_24h, 2),
                        "last_72h_mm": round(precip_72h, 2)
                    },
                    "forecast": {
                        "next_48h_total_mm": round(precip_forecast_total, 2),
                        "max_hourly_mm": round(max_forecast_precip, 2),
                        "max_probability_pct": max_forecast_prob,
                        "hourly": forecast_48h[:24]
                    },
                    "risk": risk
                })
                success = True
                break

            except Exception:
                if attempt == 0:
                    _time.sleep(1)
                continue

        if not success:
            results.append({
                "id": region["id"], "name": region["name"],
                "lat": region["lat"], "lon": region["lon"], "zone": region["zone"],
                "error": "No se pudo obtener datos",
                "risk": {"level": "DESCONOCIDO", "color": "#5c7a9e", "score": 0, "description": "Sin datos disponibles"}
            })

    return {"count": len(results), "data": results, "updated": now.isoformat()}


def calculate_hydro_risk(region, precip_now, precip_24h, precip_72h,
                          precip_forecast, max_forecast, max_prob,
                          wind, gust, seasonal_factor):
    """
    Calcula el índice de riesgo hídrico considerando:
    - Precipitación actual y acumulada
    - Pronóstico próximas 48h
    - Zona geográfica (umbrales distintos norte/sur)
    - Factor estacional (invierno = más riesgo)
    - Viento fuerte como factor agravante
    """
    zone = region["zone"]
    thresholds = ZONE_THRESHOLDS[zone]

    score = 0

    # --- Factor lluvia actual ---
    if precip_now >= thresholds["critical"]:
        score += 40
    elif precip_now >= thresholds["high"]:
        score += 25
    elif precip_now >= thresholds["moderate"]:
        score += 12
    elif precip_now >= thresholds["low"]:
        score += 4

    # --- Factor acumulado 24h ---
    if precip_24h >= thresholds["critical"] * 8:
        score += 30
    elif precip_24h >= thresholds["critical"] * 4:
        score += 20
    elif precip_24h >= thresholds["critical"] * 2:
        score += 12
    elif precip_24h >= thresholds["critical"]:
        score += 6

    # --- Factor acumulado 72h (suelo saturado) ---
    if precip_72h >= thresholds["critical"] * 20:
        score += 15
    elif precip_72h >= thresholds["critical"] * 10:
        score += 10
    elif precip_72h >= thresholds["critical"] * 5:
        score += 5

    # --- Factor pronóstico ---
    forecast_risk = (precip_forecast / max(thresholds["critical"], 1)) * 10
    prob_factor = (max_prob / 100) * 5
    score += min(20, forecast_risk + prob_factor)

    # --- Factor viento ---
    if gust >= 100:   score += 10
    elif gust >= 70:  score += 6
    elif gust >= 50:  score += 3

    # --- Factor estacional ---
    score = score * seasonal_factor

    # --- Normalizar 0-100 ---
    score = min(100, max(0, round(score, 1)))

    # --- Nivel de alerta ---
    if score >= 70:
        level = "CRÍTICO"
        color = "#ff3333"
        description = get_risk_description(zone, "CRÍTICO", precip_now, precip_24h)
    elif score >= 45:
        level = "ALTO"
        color = "#ff9500"
        description = get_risk_description(zone, "ALTO", precip_now, precip_24h)
    elif score >= 20:
        level = "MODERADO"
        color = "#ffd700"
        description = get_risk_description(zone, "MODERADO", precip_now, precip_24h)
    elif score >= 5:
        level = "BAJO"
        color = "#4ade80"
        description = get_risk_description(zone, "BAJO", precip_now, precip_24h)
    else:
        level = "SIN RIESGO"
        color = "#ffffff"
        description = "Sin precipitaciones relevantes. Condiciones normales."

    return {
        "level": level,
        "color": color,
        "score": score,
        "description": description,
        "thresholds": thresholds
    }


def get_risk_description(zone, level, precip_now, precip_24h):
    """Descripción contextual según zona y nivel de riesgo."""
    zone_names = {
        "norte_extremo": "zona hipeárida del norte",
        "norte": "norte de Chile",
        "norte_chico": "norte chico",
        "central": "zona central",
        "sur": "zona sur",
        "austral": "zona austral"
    }
    zone_name = zone_names.get(zone, "la región")

    descriptions = {
        "CRÍTICO": (
            f"Precipitación crítica para la {zone_name} ({precip_now:.1f} mm/h actuales, "
            f"{precip_24h:.1f} mm acumulados en 24h). Riesgo alto de aluviones, "
            "desbordamiento de cauces y corte de rutas. Evite zonas de quebradas y cursos de agua."
        ),
        "ALTO": (
            f"Lluvia intensa en la {zone_name} ({precip_now:.1f} mm/h, "
            f"{precip_24h:.1f} mm en 24h). Posibles anegamientos y deslizamientos. "
            "Extreme precauciones en zonas bajas y riberas."
        ),
        "MODERADO": (
            f"Precipitación moderada en la {zone_name} ({precip_now:.1f} mm/h). "
            "Monitorear el nivel de cauces. Conduzca con precaución en rutas rurales."
        ),
        "BAJO": (
            f"Lluvia leve en la {zone_name} ({precip_now:.1f} mm/h). "
            "Sin riesgo significativo. Mantenga atención ante cambios."
        ),
    }
    return descriptions.get(level, "Sin información disponible.")


def get_weather_summary():
    """
    Resumen ejecutivo del estado meteorológico nacional.
    Retorna las regiones con mayor riesgo y estadísticas generales.
    """
    data = get_weather_data()
    regions = data["data"]

    # Filtrar regiones con datos válidos
    valid = [r for r in regions if "error" not in r]

    if not valid:
        return {"error": "Sin datos meteorológicos disponibles"}

    # Top regiones en riesgo
    sorted_by_risk = sorted(
        valid,
        key=lambda r: r["risk"]["score"],
        reverse=True
    )

    # Región con más lluvia actual
    max_rain_region = max(valid, key=lambda r: r["current"]["precipitation_mm"])

    # Total lluvioso (regiones con lluvia activa)
    rainy_regions = [r for r in valid if r["current"]["precipitation_mm"] > 0]

    # Nivel máximo de alerta
    level_order = {"CRÍTICO": 5, "ALTO": 4, "MODERADO": 3, "BAJO": 2, "SIN RIESGO": 1, "DESCONOCIDO": 0}
    max_level = max(valid, key=lambda r: level_order.get(r["risk"]["level"], 0))

    return {
        "max_risk_region": sorted_by_risk[0] if sorted_by_risk else None,
        "max_rain_region": max_rain_region,
        "rainy_regions_count": len(rainy_regions),
        "national_alert_level": max_level["risk"]["level"],
        "national_alert_color": max_level["risk"]["color"],
        "top_3_risk": sorted_by_risk[:3],
        "all_regions": valid,
        "updated": data["updated"]
    }