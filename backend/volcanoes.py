"""
Volcanes activos de Chile — SERNAGEOMIN RNVV
Fuente primaria: Scraping de sernageomin.cl/alertas-volcanicas/
Fallback: Base de datos local de 45 volcanes monitoreados por OVDAS

Los 45 volcanes mas peligrosos de Chile son monitoreados 24/7 por el
Observatorio Volcanologico de los Andes del Sur (OVDAS) en Temuco.
Datos base: Plataforma de Datos para la Resiliencia ante Desastres (itrend)
"""

import requests
import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_volc_cache = {"data": None, "ts": 0, "source": "none"}
_VOLC_CACHE_TTL = 3600  # 1 hora

# =====================================================================
# BASE DE DATOS — 45 volcanes monitoreados por RNVV-OVDAS
# Fuente: Plataforma de Datos Resiliencia + SERNAGEOMIN
# risk_rank: Ranking de Riesgo Especifico 2023 (1 = mayor riesgo)
# =====================================================================
VOLCANOES_DB = [
    {"id": "taapaca", "name": "Taapaca", "lat": -18.099, "lon": -69.500, "region": "Arica y Parinacota", "elevation": 5861, "risk_rank": 37, "alert": "Verde", "description": "Complejo volcanico sin actividad reciente significativa."},
    {"id": "parinacota", "name": "Parinacota", "lat": -18.162, "lon": -69.143, "region": "Arica y Parinacota", "elevation": 6342, "risk_rank": 22, "alert": "Verde", "description": "Estratovolcan fronterizo. Monitoreo rutinario."},
    {"id": "guallatiri", "name": "Guallatiri", "lat": -18.424, "lon": -69.090, "region": "Arica y Parinacota", "elevation": 6071, "risk_rank": 30, "alert": "Verde", "description": "Actividad fumarolica persistente."},
    {"id": "isluga", "name": "Isluga", "lat": -19.155, "lon": -68.834, "region": "Tarapaca", "elevation": 5550, "risk_rank": 59, "alert": "Verde", "description": "Complejo volcanico con ultima erupcion en 1960."},
    {"id": "irruputuncu", "name": "Irruputuncu", "lat": -20.732, "lon": -68.566, "region": "Tarapaca", "elevation": 5163, "risk_rank": 47, "alert": "Verde", "description": "Estratovolcan fronterizo. Actividad fumarolica leve."},
    {"id": "olca", "name": "Olca-Paruma", "lat": -20.935, "lon": -68.478, "region": "Antofagasta", "elevation": 5407, "risk_rank": 51, "alert": "Verde", "description": "Complejo volcanico con fumarolas activas."},
    {"id": "san_pedro", "name": "San Pedro", "lat": -21.880, "lon": -68.400, "region": "Antofagasta", "elevation": 6145, "risk_rank": 41, "alert": "Verde", "description": "Uno de los volcanes mas altos de Chile."},
    {"id": "lascar", "name": "Lascar", "lat": -23.370, "lon": -67.730, "region": "Antofagasta", "elevation": 5592, "risk_rank": 14, "alert": "Verde", "description": "Volcan mas activo del norte. Actividad fumarolica permanente."},
    {"id": "lastarria", "name": "Lastarria", "lat": -25.168, "lon": -68.507, "region": "Antofagasta", "elevation": 5697, "risk_rank": 56, "alert": "Verde", "description": "Zona de anomalias termicas. Deformacion activa."},
    {"id": "tupungatito", "name": "Tupungatito", "lat": -33.400, "lon": -69.800, "region": "Metropolitana", "elevation": 5682, "risk_rank": 16, "alert": "Verde", "description": "Volcan mas cercano a Santiago. Zona alta cordillera."},
    {"id": "san_jose", "name": "San Jose", "lat": -33.782, "lon": -69.897, "region": "Metropolitana", "elevation": 5856, "risk_rank": 19, "alert": "Verde", "description": "Fumarolas persistentes. Fronterizo."},
    {"id": "maipo", "name": "Maipo", "lat": -34.161, "lon": -69.833, "region": "Metropolitana", "elevation": 5264, "risk_rank": 20, "alert": "Verde", "description": "Caldera con actividad menor."},
    {"id": "tinguiririca", "name": "Tinguiririca", "lat": -34.810, "lon": -70.350, "region": "O'Higgins", "elevation": 4280, "risk_rank": 21, "alert": "Verde", "description": "Sin actividad relevante."},
    {"id": "planchon_peteroa", "name": "Planchon-Peteroa", "lat": -35.240, "lon": -70.570, "region": "Maule", "elevation": 3977, "risk_rank": 5, "alert": "Verde", "description": "Actividad fumarolica y episodios de ceniza recurrentes."},
    {"id": "descabezado_grande", "name": "Descabezado Grande", "lat": -35.580, "lon": -70.750, "region": "Maule", "elevation": 3953, "risk_rank": 31, "alert": "Verde", "description": "Sin actividad significativa reciente."},
    {"id": "laguna_del_maule", "name": "Laguna del Maule", "lat": -36.058, "lon": -70.491, "region": "Maule", "elevation": 3092, "risk_rank": 23, "alert": "Amarilla", "description": "Inflacion del terreno activa desde 2007. Intrusion magmatica en profundidad."},
    {"id": "nevados_de_chillan", "name": "Nevados de Chillan", "lat": -36.860, "lon": -71.380, "region": "Nuble", "elevation": 3212, "risk_rank": 6, "alert": "Amarilla", "description": "Actividad explosiva menor. Columnas de gases frecuentes."},
    {"id": "copahue", "name": "Copahue", "lat": -37.860, "lon": -71.170, "region": "Biobio", "elevation": 2997, "risk_rank": 7, "alert": "Amarilla", "description": "Actividad fumarolica elevada. Zona de exclusion activa."},
    {"id": "antuco", "name": "Antuco", "lat": -37.406, "lon": -71.349, "region": "Biobio", "elevation": 2979, "risk_rank": 24, "alert": "Verde", "description": "Sin actividad relevante."},
    {"id": "callaqui", "name": "Callaqui", "lat": -37.923, "lon": -71.446, "region": "Biobio", "elevation": 3164, "risk_rank": 25, "alert": "Verde", "description": "Sin actividad relevante."},
    {"id": "lonquimay", "name": "Lonquimay", "lat": -38.377, "lon": -71.580, "region": "Araucania", "elevation": 2865, "risk_rank": 11, "alert": "Verde", "description": "Ultima erupcion 1988-1990. Monitoreo permanente."},
    {"id": "llaima", "name": "Llaima", "lat": -38.692, "lon": -71.729, "region": "Araucania", "elevation": 3125, "risk_rank": 3, "alert": "Verde", "description": "Uno de los volcanes mas activos de Chile. Monitoreo intensivo."},
    {"id": "sollipulli", "name": "Sollipulli", "lat": -38.974, "lon": -71.517, "region": "Araucania", "elevation": 2282, "risk_rank": 15, "alert": "Verde", "description": "Caldera con glaciar. Potencial explosivo alto."},
    {"id": "villarrica", "name": "Villarrica", "lat": -39.420, "lon": -71.930, "region": "Araucania", "elevation": 2847, "risk_rank": 1, "alert": "Amarilla", "description": "Volcan mas activo de Chile. Lago de lava permanente. Monitoreo 24/7."},
    {"id": "quetrupillan", "name": "Quetrupillan", "lat": -39.500, "lon": -71.770, "region": "Araucania", "elevation": 2360, "risk_rank": 29, "alert": "Verde", "description": "Sin actividad relevante."},
    {"id": "lanin", "name": "Lanin", "lat": -39.633, "lon": -71.500, "region": "Araucania", "elevation": 3747, "risk_rank": 33, "alert": "Verde", "description": "Estratovolcan fronterizo. Sin actividad reciente."},
    {"id": "mocho_choshuenco", "name": "Mocho-Choshuenco", "lat": -39.927, "lon": -72.027, "region": "Los Rios", "elevation": 2422, "risk_rank": 10, "alert": "Verde", "description": "Complejo volcanico con glaciar."},
    {"id": "carran", "name": "Carran-Los Venados", "lat": -40.350, "lon": -72.070, "region": "Los Rios", "elevation": 1114, "risk_rank": 18, "alert": "Verde", "description": "Ultima erupcion 1979. Actividad freatica."},
    {"id": "puyehue", "name": "Puyehue-Cordon Caulle", "lat": -40.590, "lon": -72.117, "region": "Los Rios", "elevation": 2236, "risk_rank": 4, "alert": "Verde", "description": "Erupcion 2011 afecto trafico aereo hemisferico."},
    {"id": "antillanca", "name": "Antillanca", "lat": -40.771, "lon": -72.153, "region": "Los Lagos", "elevation": 1990, "risk_rank": 34, "alert": "Verde", "description": "Grupo volcanico monogenetico."},
    {"id": "osorno", "name": "Osorno", "lat": -41.100, "lon": -72.493, "region": "Los Lagos", "elevation": 2652, "risk_rank": 9, "alert": "Verde", "description": "Estratovolcan iconico. Sin actividad relevante."},
    {"id": "calbuco", "name": "Calbuco", "lat": -41.326, "lon": -72.614, "region": "Los Lagos", "elevation": 2003, "risk_rank": 2, "alert": "Verde", "description": "Erupcion explosiva sorpresiva en 2015. Monitoreo prioritario."},
    {"id": "yate", "name": "Yate", "lat": -41.755, "lon": -72.396, "region": "Los Lagos", "elevation": 2187, "risk_rank": 26, "alert": "Verde", "description": "Sin actividad relevante."},
    {"id": "hornopiren", "name": "Hornopiren", "lat": -41.874, "lon": -72.431, "region": "Los Lagos", "elevation": 1572, "risk_rank": 36, "alert": "Verde", "description": "Sin actividad relevante."},
    {"id": "huequi", "name": "Huequi", "lat": -42.377, "lon": -72.578, "region": "Los Lagos", "elevation": 1318, "risk_rank": 32, "alert": "Verde", "description": "Erupciones freaticas historicas."},
    {"id": "michinmahuida", "name": "Michinmahuida", "lat": -42.790, "lon": -72.439, "region": "Los Lagos", "elevation": 2404, "risk_rank": 12, "alert": "Verde", "description": "Estratovolcan cubierto de glaciares."},
    {"id": "chaiten", "name": "Chaiten", "lat": -42.835, "lon": -72.646, "region": "Los Lagos", "elevation": 1122, "risk_rank": 8, "alert": "Verde", "description": "Erupcion 2008 destruyo la ciudad. Domo activo."},
    {"id": "corcovado", "name": "Corcovado", "lat": -43.190, "lon": -72.793, "region": "Los Lagos", "elevation": 2300, "risk_rank": 42, "alert": "Verde", "description": "Estratovolcan aislado."},
    {"id": "melimoyu", "name": "Melimoyu", "lat": -44.075, "lon": -72.860, "region": "Aysen", "elevation": 2400, "risk_rank": 28, "alert": "Verde", "description": "Sin actividad relevante."},
    {"id": "mentolat", "name": "Mentolat", "lat": -44.696, "lon": -73.076, "region": "Aysen", "elevation": 1605, "risk_rank": 39, "alert": "Verde", "description": "Sin actividad relevante."},
    {"id": "cay", "name": "Cay", "lat": -45.062, "lon": -72.985, "region": "Aysen", "elevation": 2200, "risk_rank": 65, "alert": "Verde", "description": "Estratovolcan con actividad sismica ocasional."},
    {"id": "maca", "name": "Maca", "lat": -45.105, "lon": -73.169, "region": "Aysen", "elevation": 2265, "risk_rank": 44, "alert": "Verde", "description": "Actividad sismica ocasional."},
    {"id": "hudson", "name": "Hudson", "lat": -45.900, "lon": -72.970, "region": "Aysen", "elevation": 1905, "risk_rank": 13, "alert": "Verde", "description": "Erupciones catastroficas en 1971 y 1991."},
]


def get_volcanoes():
    """
    Obtiene volcanes con alertas actualizadas.
    1) Intenta scraping de SERNAGEOMIN (si disponible)
    2) Fallback: base de datos local completa de 45 volcanes
    Cachea resultado por 1 hora.
    """
    now = datetime.now(timezone.utc).timestamp()

    if _volc_cache["data"] and (now - _volc_cache["ts"]) < _VOLC_CACHE_TTL:
        return _volc_cache["data"]

    live_alerts = _scrape_sernageomin_alerts()

    if live_alerts:
        volcanoes = _merge_alerts(live_alerts)
        source = "sernageomin_live"
    else:
        volcanoes = [v.copy() for v in VOLCANOES_DB]
        source = "local_db"

    result = {
        "count": len(volcanoes),
        "data": volcanoes,
        "source": source,
        "updated": datetime.now(timezone.utc).isoformat()
    }

    _volc_cache["data"] = result
    _volc_cache["ts"] = now
    _volc_cache["source"] = source

    return result


def _scrape_sernageomin_alerts():
    """
    Intenta obtener alertas volcanicas vigentes desde SERNAGEOMIN.
    La web esta en reestructuracion post-incidente informatico (feb 2026),
    por lo que puede fallar — el fallback local lo cubre.
    """
    try:
        res = requests.get(
            "https://www.sernageomin.cl/alertas-volcanicas/",
            timeout=10,
            headers={"User-Agent": "VigilaChile/1.0 (monitoreo desastres Chile)"}
        )
        if res.status_code != 200:
            logger.warning("SERNAGEOMIN status %d", res.status_code)
            return None

        html = res.text
        alerts = {}

        patterns = [
            r'(?:alerta|Alerta)\s+(Roja|Naranja|Amarilla)\s*[:\-\u2013]?\s*(?:volc[aá]n)?\s*([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\s\-]+)',
            r'(?:volc[aá]n)\s+([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\s\-]+)\s*[:\-\u2013]?\s*(?:alerta|Alerta)\s+(Roja|Naranja|Amarilla)',
            r'([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\s\-]+?)\s+(?:se\s+encuentra\s+en\s+)?alerta\s+t[eé]cnica\s+(Roja|Naranja|Amarilla)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    if match[0].strip().lower() in ("roja", "naranja", "amarilla"):
                        alert_level = match[0].strip().capitalize()
                        volcano_name = match[1].strip()
                    else:
                        volcano_name = match[0].strip()
                        alert_level = match[1].strip().capitalize()

                    volcano_name = volcano_name.strip(" .,;:\u2013-")
                    if len(volcano_name) > 3 and alert_level in ("Roja", "Naranja", "Amarilla"):
                        alerts[_normalize(volcano_name)] = alert_level

        if alerts:
            logger.info("SERNAGEOMIN scrape OK: %d alerts: %s", len(alerts), alerts)
            return alerts

        return None

    except requests.exceptions.Timeout:
        logger.warning("SERNAGEOMIN scrape timeout")
        return None
    except Exception as e:
        logger.warning("SERNAGEOMIN scrape error: %s", str(e))
        return None


def _merge_alerts(live_alerts):
    """Merge live alert data into the local volcano database."""
    volcanoes = []
    for v in VOLCANOES_DB:
        vc = v.copy()
        name_norm = _normalize(v["name"])

        for alert_name, alert_level in live_alerts.items():
            if alert_name in name_norm or name_norm in alert_name or alert_name == name_norm:
                vc["alert"] = alert_level
                vc["alert_source"] = "sernageomin_live"
                break

        volcanoes.append(vc)
    return volcanoes


def _normalize(text):
    replacements = {
        "\u00e1": "a", "\u00e9": "e", "\u00ed": "i", "\u00f3": "o", "\u00fa": "u",
        "\u00c1": "a", "\u00c9": "e", "\u00cd": "i", "\u00d3": "o", "\u00da": "u",
        "\u00f1": "n", "\u00d1": "n"
    }
    t = text.lower().strip()
    for k, v in replacements.items():
        t = t.replace(k, v)
    return t
