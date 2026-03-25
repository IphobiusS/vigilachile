import requests
import os
from datetime import datetime, timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

# Coordenadas representativas de cada region de Chile
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
    Obtiene datos meteorologicos de WeatherAPI.com para las 15 regiones.
    Una llamada por region con forecast de 2 dias.
    """
    results = []
    now = datetime.now(timezone.utc)
    month = now.month
    seasonal_factor = 1.4 if 5 <= month <= 8 else 1.0

    api_key = WEATHER_API_KEY
    if not api_key:
        return {"count": 0, "data": [], "error": "WEATHER_API_KEY not configured"}

    for region in REGION_COORDS:
        try:
            url = "https://api.weatherapi.com/v1/forecast.json"
            params = {
                "key": api_key,
                "q": str(region["lat"]) + "," + str(region["lon"]),
                "days": 2,
                "aqi": "no",
                "alerts": "no"
            }
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()

            current = data.get("current", {})
            forecast_days = data.get("forecast", {}).get("forecastday", [])

            # Current conditions
            precip_now = float(current.get("precip_mm", 0))
            temp_now = float(current.get("temp_c", 0))
            humidity_now = float(current.get("humidity", 0))
            wind_now = float(current.get("wind_kph", 0))
            gust_now = float(current.get("gust_kph", 0))
            weathercode = current.get("condition", {}).get("code", 0)

            # Accumulated from hourly data
            precip_24h = 0
            precip_72h = 0
            forecast_48h = []
            now_epoch = now.timestamp()

            for day in forecast_days:
                for hour in day.get("hour", []):
                    hour_epoch = hour.get("time_epoch", 0)
                    hour_precip = float(hour.get("precip_mm", 0))
                    hour_prob = int(hour.get("chance_of_rain", 0))

                    # Last 24h accumulation
                    if now_epoch - hour_epoch <= 86400 and hour_epoch <= now_epoch:
                        precip_24h += hour_precip

                    # Future hours for forecast
                    if hour_epoch > now_epoch:
                        forecast_48h.append({
                            "time": hour_epoch,
                            "precipitation": round(hour_precip, 2),
                            "probability": hour_prob
                        })

            precip_72h = precip_24h  # Only 2 days of data available

            max_forecast_precip = max([h["precipitation"] for h in forecast_48h], default=0)
            max_forecast_prob = max([h["probability"] for h in forecast_48h], default=0)
            precip_forecast_total = sum(h["precipitation"] for h in forecast_48h)

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
                    "weathercode": weathercode
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

        except Exception as e:
            results.append({
                "id": region["id"], "name": region["name"],
                "lat": region["lat"], "lon": region["lon"], "zone": region["zone"],
                "error": str(e),
                "risk": {"level": "DESCONOCIDO", "color": "#5c7a9e", "score": 0, "description": "Sin datos disponibles"}
            })

    return {"count": len(results), "data": results, "updated": now.isoformat()}


def calculate_hydro_risk(region, precip_now, precip_24h, precip_72h,
                          precip_forecast, max_forecast, max_prob,
                          wind, gust, seasonal_factor):
    zone = region["zone"]
    thresholds = ZONE_THRESHOLDS[zone]
    score = 0

    if precip_now >= thresholds["critical"]:     score += 40
    elif precip_now >= thresholds["high"]:        score += 25
    elif precip_now >= thresholds["moderate"]:    score += 12
    elif precip_now >= thresholds["low"]:         score += 4

    if precip_24h >= thresholds["critical"] * 8:  score += 30
    elif precip_24h >= thresholds["critical"] * 4: score += 20
    elif precip_24h >= thresholds["critical"] * 2: score += 12
    elif precip_24h >= thresholds["critical"]:     score += 6

    if precip_72h >= thresholds["critical"] * 20:  score += 15
    elif precip_72h >= thresholds["critical"] * 10: score += 10
    elif precip_72h >= thresholds["critical"] * 5:  score += 5

    forecast_risk = (precip_forecast / max(thresholds["critical"], 1)) * 10
    prob_factor = (max_prob / 100) * 5
    score += min(20, forecast_risk + prob_factor)

    if gust >= 100:   score += 10
    elif gust >= 70:  score += 6
    elif gust >= 50:  score += 3

    score = score * seasonal_factor
    score = min(100, max(0, round(score, 1)))

    if score >= 70:
        level = "CRÍTICO"
        color = "#ff3333"
        description = get_risk_description(region["zone"], "CRÍTICO", precip_now, precip_24h)
    elif score >= 45:
        level = "ALTO"
        color = "#ff9500"
        description = get_risk_description(region["zone"], "ALTO", precip_now, precip_24h)
    elif score >= 20:
        level = "MODERADO"
        color = "#ffd700"
        description = get_risk_description(region["zone"], "MODERADO", precip_now, precip_24h)
    elif score >= 5:
        level = "BAJO"
        color = "#4ade80"
        description = get_risk_description(region["zone"], "BAJO", precip_now, precip_24h)
    else:
        level = "SIN RIESGO"
        color = "#ffffff"
        description = "Sin precipitaciones relevantes. Condiciones normales."

    return {"level": level, "color": color, "score": score, "description": description, "thresholds": thresholds}


def get_risk_description(zone, level, precip_now, precip_24h):
    zone_names = {
        "norte_extremo": "zona hiperárida del norte",
        "norte": "norte de Chile",
        "norte_chico": "norte chico",
        "central": "zona central",
        "sur": "zona sur",
        "austral": "zona austral"
    }
    zone_name = zone_names.get(zone, "la región")
    descriptions = {
        "CRÍTICO": f"Precipitación crítica para la {zone_name} ({precip_now:.1f} mm/h, {precip_24h:.1f} mm en 24h). Riesgo de aluviones y desbordamiento.",
        "ALTO": f"Lluvia intensa en la {zone_name} ({precip_now:.1f} mm/h, {precip_24h:.1f} mm en 24h). Posibles anegamientos.",
        "MODERADO": f"Precipitación moderada en la {zone_name} ({precip_now:.1f} mm/h). Monitorear cauces.",
        "BAJO": f"Lluvia leve en la {zone_name} ({precip_now:.1f} mm/h). Sin riesgo significativo.",
    }
    return descriptions.get(level, "Sin información disponible.")


def get_weather_summary():
    data = get_weather_data()
    regions = data["data"]
    valid = [r for r in regions if "error" not in r]

    if not valid:
        return {"error": "Sin datos meteorológicos disponibles"}

    sorted_by_risk = sorted(valid, key=lambda r: r["risk"]["score"], reverse=True)
    max_rain_region = max(valid, key=lambda r: r["current"]["precipitation_mm"])
    rainy_regions = [r for r in valid if r["current"]["precipitation_mm"] > 0]
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
