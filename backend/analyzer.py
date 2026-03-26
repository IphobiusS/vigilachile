import requests
import os
from datetime import datetime, timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

def analyze_seismic_pattern(quakes, fires, risk, volcanoes=None, tsunami=None, weather_summary=None):
    if not quakes:
        return {
            "report": "Sin datos sísmicos disponibles en este momento.",
            "trend": "stable",
            "recent_6h": 0,
            "total_24h": 0,
            "top_zone": "Chile",
            "max_magnitude": 0,
            "avg_magnitude": 0
        }

    total = len(quakes)
    magnitudes = [q["magnitude"] for q in quakes]
    max_mag = max(magnitudes)
    avg_mag = sum(magnitudes) / total

    # Zona más activa
    zones = {}
    for q in quakes:
        place = q["place"].split("de ")[-1].split("al ")[0].strip()
        zones[place] = zones.get(place, 0) + 1
    top_zone = max(zones, key=zones.get) if zones else "Chile"

    # Sismos últimas 6h
    now = datetime.now(timezone.utc)
    recent = []
    for q in quakes:
        try:
            t = datetime.fromisoformat(
                q["time"].replace(" ", "T")
            ).replace(tzinfo=timezone.utc)
            if t > now - timedelta(hours=6):
                recent.append(q)
        except:
            pass

    # Detectar enjambre sísmico
    is_swarm = len(recent) > 8 and max_mag < 5.0

    # Desglose temporal detallado
    last_1h = []
    last_3h = []
    last_12h = []
    for q in quakes:
        try:
            t = datetime.fromisoformat(q["time"].replace(" ", "T")).replace(tzinfo=timezone.utc)
            delta = (now - t).total_seconds() / 3600
            if delta <= 1: last_1h.append(q)
            if delta <= 3: last_3h.append(q)
            if delta <= 12: last_12h.append(q)
        except:
            pass

    sorted_by_time = sorted(quakes, key=lambda q: q.get("time", ""), reverse=True)
    top5_recent = sorted_by_time[:5]
    top5_detail = ""
    for q in top5_recent:
        top5_detail += "  · M" + str(q["magnitude"]) + " " + q["place"] + " prof:" + str(q.get("depth", "?")) + "km\n"

    top3_zones = sorted(zones.items(), key=lambda x: x[1], reverse=True)[:3]
    zones_detail = ", ".join([z[0] + " (" + str(z[1]) + ")" for z in top3_zones])

    # === Construir datos de TODAS las amenazas ===
    # Volcanes
    volc_section = ""
    if volcanoes:
        volc_data = volcanoes if isinstance(volcanoes, list) else volcanoes.get("data", [])
        alerts = [v for v in volc_data if v.get("alert") != "Verde"]
        if alerts:
            volc_names = ", ".join([v["name"] + " (" + v["alert"] + ")" for v in alerts])
            volc_section = "- Volcanes en alerta: " + str(len(alerts)) + " — " + volc_names + "\n"
        else:
            volc_section = "- Volcanes: Todos en alerta verde (normal)\n"

    # Tsunami
    tsun_section = ""
    if tsunami:
        tsun_data = tsunami if isinstance(tsunami, list) else tsunami.get("data", [])
        tsun_count = len(tsun_data) if isinstance(tsun_data, list) else 0
        if tsun_count > 0:
            t = tsun_data[0]
            tsun_section = "- TSUNAMI: Alerta " + str(t.get("level", "")) + " — M" + str(t.get("magnitude", "")) + " " + str(t.get("place", "")) + "\n"
        else:
            tsun_section = "- Tsunami: Sin alertas activas\n"

    # Clima
    clima_section = ""
    if weather_summary:
        rainy = weather_summary.get("rainy_regions_count", 0)
        nat_level = weather_summary.get("national_alert_level", "SIN RIESGO")
        top3 = weather_summary.get("top_3_risk", [])
        clima_section = "- Clima nacional: " + nat_level + " — " + str(rainy) + " regiones con lluvia\n"
        if top3:
            for r in top3[:2]:
                clima_section += "  · " + r.get("name", "") + ": " + r.get("risk", {}).get("level", "") + " (score " + str(r.get("risk", {}).get("score", 0)) + ")\n"

    prompt = (
        "Eres un sismólogo chileno senior redactando un informe de situación. "
        "CONTEXTO: Chile es el país más sísmico del mundo. 20-50 sismos diarios M2.5+ es normal. "
        "Solo M6.0+ amerita alarma real. Volcanes Alerta Amarilla es vigilancia estándar. "
        "No exageres, pero SÉ ESPECÍFICO con los datos — menciona eventos concretos, horas y zonas.\n\n"
        "DATOS DETALLADOS ÚLTIMAS 24 HORAS:\n"
        "SISMOS: " + str(total) + " eventos totales\n"
        "- Última hora: " + str(len(last_1h)) + " sismos\n"
        "- Últimas 3h: " + str(len(last_3h)) + " sismos\n"
        "- Últimas 6h: " + str(len(recent)) + " sismos\n"
        "- Últimas 12h: " + str(len(last_12h)) + " sismos\n"
        "- Magnitud máxima: M" + str(max_mag) + " · Promedio: M" + str(round(avg_mag, 1)) + "\n"
        "- Zonas más activas: " + zones_detail + "\n"
        "- 5 sismos más recientes:\n" + top5_detail
        + ("- PATRON: Posible enjambre sísmico activo\n" if is_swarm else "") +
        "INCENDIOS: " + str(len(fires)) + " focos activos\n"
        + volc_section + tsun_section + clima_section +
        "RIESGO COMPUESTO: " + str(risk["score"]) + "/10 (" + risk["level"] + ")\n\n"
        "Genera un informe DETALLADO y ESPECÍFICO. Menciona datos concretos: cuántos sismos recientes, "
        "zonas específicas, magnitudes. NO repitas frases genéricas sin contexto.\n\n"
        "FORMATO — empieza DIRECTAMENTE con 'SISMOS:':\n"
        "SISMOS: [2-3 frases detalladas con desglose temporal y zonas]\n"
        "INCENDIOS: [1-2 frases]\n"
        "VOLCANES: [1-2 frases]\n"
        "TSUNAMI: [1 frase]\n"
        "CLIMA: [1-2 frases con regiones]\n"
        "EVALUACION: [conclusión calibrada para Chile]\n\n"
        "REGLAS: "
        "1) Empieza con 'SISMOS:'. Sin titulo ni encabezado previo. "
        "2) Sin markdown, asteriscos, negritas, simbolos (■●►), firmas ni footer. "
        "3) Tono técnico profesional, ESPECÍFICO no genérico. Máximo 250 palabras."
    )

    try:
        if not ANTHROPIC_API_KEY:
            raise ValueError("API key no configurada")

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )
        data = response.json()
        report = data["content"][0]["text"]

        trend = "stable"
        if len(recent) > total * 0.4:
            trend = "increasing"
        elif len(recent) < total * 0.1:
            trend = "decreasing"

        return {
            "report": report,
            "trend": trend,
            "recent_6h": len(recent),
            "total_24h": total,
            "top_zone": top_zone,
            "max_magnitude": max_mag,
            "avg_magnitude": round(avg_mag, 1)
        }

    except Exception as e:
        # Reporte de respaldo sin IA
        nivel = risk["level"]
        backup = (
            "SISMOS: Se registraron " + str(total) + " eventos, magnitud máxima M" + str(max_mag) + ", zona más activa " + top_zone + ". "
            + ("Posible enjambre sísmico. " if is_swarm else "") +
            "INCENDIOS: " + str(len(fires)) + " focos de calor activos. "
            "VOLCANES: " + (volc_section.replace("- Volcanes: ", "").replace("- Volcanes en alerta: ", "").strip() if volc_section else "Sin datos.") + " "
            "TSUNAMI: " + ("Alerta activa." if tsunami and len(tsunami.get("data", [])) > 0 else "Sin alertas.") + " "
            "CLIMA: " + (str(weather_summary.get("rainy_regions_count", 0)) + " regiones con lluvia." if weather_summary else "Sin datos.") + " "
            "EVALUACIÓN: Riesgo " + str(risk["score"]) + "/10 (" + nivel + "). "
            "Actividad dentro de rangos " + ("elevados" if risk["score"] > 6 else "normales") + " para Chile."
        )
        trend = "stable"
        if len(recent) > total * 0.4:
            trend = "increasing"
        elif len(recent) < total * 0.1:
            trend = "decreasing"

        return {
            "report": backup,
            "trend": trend,
            "recent_6h": len(recent),
            "total_24h": total,
            "top_zone": top_zone,
            "max_magnitude": max_mag,
            "avg_magnitude": round(avg_mag, 1)
        }


def estimate_population(lat, lon, magnitude):
    radios = {
        2.5: 10, 3.0: 20, 3.5: 35, 4.0: 60,
        4.5: 100, 5.0: 150, 5.5: 200, 6.0: 300,
        6.5: 450, 7.0: 600
    }

    radio_km = 60
    for mag, r in sorted(radios.items()):
        if magnitude >= mag:
            radio_km = r

    # Densidad poblacional por zona de Chile
    if lat > -20:        density = 5    # Norte extremo
    elif lat > -25:      density = 8    # Norte
    elif lat > -30:      density = 12   # Norte-Centro
    elif lat > -33:      density = 80   # Zona Central Norte
    elif lat > -35:      density = 180  # RM y alrededores
    elif lat > -38:      density = 40   # Centro-Sur
    elif lat > -40:      density = 25   # Sur
    else:                density = 3    # Patagonia

    area_km2 = 3.14159 * (radio_km ** 2)
    population = int(area_km2 * density * 0.3)

    return {
        "estimated_population": population,
        "radius_km": radio_km,
        "density_zone": "Alta" if density > 100 else "Media" if density > 20 else "Baja"
    }