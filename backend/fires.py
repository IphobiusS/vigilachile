"""
Focos de calor activos en Chile — NASA FIRMS
Fuente primaria: VIIRS NOAA-20 NRT (375m resolucion, near real-time)
Fuente secundaria: MODIS C6.1 CSV (1km resolucion, fallback)

VIIRS provee datos satelitales de mayor resolucion (375m vs 1km MODIS)
con deteccion near real-time del satelite NOAA-20.

Incluye clustering geoespacial para detectar frentes de incendio activos.
"""

import requests
import csv
import io
import os
import logging
import math
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")

# Bounding box Chile (amplio para captar todo el territorio incluyendo islas)
# Luego se filtra punto a punto con _is_in_chile()
CHILE_BBOX = "-76,-56,-66,-17"


def _is_in_chile(lat, lon):
    """
    Filtro geografico para determinar si un punto esta en territorio chileno.
    Chile es angosto (~180km) pero muy largo, y la frontera este varia por latitud.
    Ademas incluye territorios insulares (Juan Fernandez, Isla de Pascua NO incluida
    porque no tiene incendios forestales relevantes).
    """
    # Fuera de rango latitudinal de Chile continental
    if lat > -17.5 or lat < -56:
        return False

    # Regla general: Chile continental esta al oeste de la cordillera
    # La frontera este de Chile varia por latitud:
    if lat > -24:
        # Norte grande (Arica a Antofagasta): frontera ~-67.5 a -68.5
        return lon <= -67.0 and lon >= -76
    elif lat > -32:
        # Norte chico (Atacama a Coquimbo): frontera ~-69 a -70
        return lon <= -68.5 and lon >= -76
    elif lat > -36:
        # Zona central (Valparaiso a Maule): frontera ~-69.5 a -70
        return lon <= -69.5 and lon >= -76
    elif lat > -42:
        # Zona sur (Biobio a Los Lagos): frontera ~-71 a -71.5
        return lon <= -70.5 and lon >= -76
    elif lat > -46:
        # Zona austral norte (Aysen): frontera ~-71.5
        return lon <= -71.0 and lon >= -76
    elif lat > -52:
        # Patagonia (Aysen sur a Magallanes norte): frontera ~-70
        return lon <= -70.0 and lon >= -76
    else:
        # Magallanes y Tierra del Fuego chilena: complejo por el Estrecho
        # Chile: Punta Arenas (-70.9), Puerto Natales (-72.5), Porvenir (-70.3)
        # Argentina: Ushuaia (-68.3), Rio Grande (-67.7)
        return lon <= -69.5 and lon >= -76


def get_fires():
    """
    Obtiene focos de calor activos en Chile.
    1) VIIRS NOAA-20 NRT via FIRMS API (375m, near real-time) — requiere MAP_KEY
    2) Fallback: MODIS C6.1 CSV Sudamerica (1km, bulk download)
    """
    if FIRMS_MAP_KEY:
        result = _get_fires_viirs()
        if result and result["count"] >= 0:
            return result
        logger.warning("VIIRS failed, falling back to MODIS CSV")

    return _get_fires_modis_csv()


def _get_fires_viirs():
    """
    NASA FIRMS VIIRS NOAA-20 Near Real-Time API.
    Resolucion: 375m (4x mejor que MODIS)
    Latencia: datos disponibles ~3h despues del paso del satelite
    Formato: CSV con lat, lon, bright_ti4, confidence, acq_date, acq_time, satellite
    """
    url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/" + FIRMS_MAP_KEY + "/VIIRS_NOAA20_NRT/" + CHILE_BBOX + "/1"
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 401:
            logger.error("FIRMS API: invalid MAP_KEY")
            return None
        if response.status_code == 429:
            logger.warning("FIRMS API: rate limited")
            return None
        response.raise_for_status()

        fires = []
        reader = csv.DictReader(io.StringIO(response.text))

        for row in reader:
            try:
                lat = float(row.get("latitude", 0))
                lon = float(row.get("longitude", 0))

                # Filter: only Chile territory (exclude Argentina)
                if not _is_in_chile(lat, lon):
                    continue

                brightness = float(row.get("bright_ti4", row.get("brightness", 0)))
                confidence = row.get("confidence", "nominal")
                acq_date = row.get("acq_date", "")
                acq_time = row.get("acq_time", "")
                frp = float(row.get("frp", 0))  # Fire Radiative Power (MW)

                # Filtrar baja confianza
                if confidence in ("l", "low"):
                    continue

                # Mapear confianza VIIRS a porcentaje
                conf_pct = "85" if confidence in ("h", "high") else "65" if confidence in ("n", "nominal") else str(confidence)

                fires.append({
                    "lat": lat,
                    "lon": lon,
                    "brightness": round(brightness, 1),
                    "date": acq_date,
                    "time": acq_time,
                    "confidence": conf_pct,
                    "frp": round(frp, 1),
                    "satellite": "NOAA-20",
                    "instrument": "VIIRS",
                    "resolution": "375m"
                })
            except (ValueError, KeyError) as e:
                logger.debug("VIIRS row parse error: %s", e)
                continue

        logger.info("VIIRS NOAA-20: %d fire detections in Chile", len(fires))

        # Clasificar focos por intensidad (FRP = Fire Radiative Power en MW)
        high_frp = [f for f in fires if f["frp"] >= 20]
        medium_frp = [f for f in fires if 5 <= f["frp"] < 20]
        low_frp = [f for f in fires if f["frp"] < 5]
        high_conf = [f for f in fires if f["confidence"] == "85"]

        return {
            "count": len(fires),
            "data": fires,
            "source": "VIIRS_NOAA20_NRT",
            "summary": {
                "high_intensity": len(high_frp),
                "medium_intensity": len(medium_frp),
                "low_intensity": len(low_frp),
                "high_confidence": len(high_conf),
                "max_frp_mw": round(max((f["frp"] for f in fires), default=0), 1),
                "note": "FRP>=20MW: incendio activo significativo. FRP<5MW: probable quema agricola o anomalia termica menor."
            }
        }

    except requests.exceptions.Timeout:
        logger.warning("FIRMS VIIRS API timeout")
        return None
    except Exception as e:
        logger.error("FIRMS VIIRS API error: %s", str(e))
        return None


def _get_fires_modis_csv():
    """
    Fallback: NASA FIRMS MODIS C6.1 CSV para Sudamerica.
    Resolucion: 1km — menor que VIIRS pero sin requerir API key.
    """
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_South_America_24h.csv"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        fires = []
        reader = csv.DictReader(io.StringIO(response.text))

        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        for row in reader:
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                date = row.get("acq_date", "")
                brightness = float(row.get("brightness", 0))
                confidence = row.get("confidence", "0")

                if not _is_in_chile(lat, lon):
                    continue
                if date not in (today, yesterday):
                    continue
                try:
                    conf_val = int(confidence)
                    if conf_val < 20:
                        continue
                except (ValueError, TypeError):
                    pass

                fires.append({
                    "lat": lat,
                    "lon": lon,
                    "brightness": brightness,
                    "date": date,
                    "confidence": confidence,
                    "satellite": "Terra/Aqua",
                    "instrument": "MODIS",
                    "resolution": "1km"
                })
            except (ValueError, KeyError):
                continue

        logger.info("MODIS CSV: %d fire detections in Chile", len(fires))
        return {"count": len(fires), "data": fires, "source": "MODIS_C6.1"}

    except Exception as e:
        logger.error("MODIS CSV error: %s", str(e))
        return {"count": 0, "data": [], "source": "error", "error": str(e)}


# =====================================================================
# CLUSTERING GEOESPACIAL — Detección de frentes de incendio
# =====================================================================
# Algoritmo: DBSCAN simplificado (density-based spatial clustering)
# Agrupa focos VIIRS que estén a menos de `eps_km` kilómetros entre sí.
# Cada cluster representa un frente de incendio activo con:
# - Centroide (lat/lon), área estimada, FRP total, cantidad de focos
# - Clasificación: mega-incendio, incendio mayor, incendio moderado, foco menor
# =====================================================================

def _haversine_km(lat1, lon1, lat2, lon2):
    """Distancia entre dos puntos en km usando fórmula de Haversine."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cluster_fires(fires, eps_km=1.5, min_points=2):
    """
    Clustering geoespacial de focos de calor para detectar frentes de incendio.
    
    Algoritmo: DBSCAN simplificado (sin librería externa).
    - eps_km: radio máximo para considerar dos focos como parte del mismo incendio (default 1.5km)
    - min_points: mínimo de focos para formar un cluster (default 2)
    
    Un foco VIIRS a 375m de resolución cubre ~0.14 km². Focos a <1.5km probablemente
    son parte del mismo evento de fuego.
    
    Returns:
        dict con clusters (frentes de incendio) y isolated (focos aislados)
    """
    if not fires:
        return {"clusters": [], "isolated": [], "total_clusters": 0, "total_isolated": 0}

    n = len(fires)
    labels = [-1] * n  # -1 = sin asignar
    cluster_id = 0

    for i in range(n):
        if labels[i] != -1:
            continue
        
        # Buscar vecinos del punto i
        neighbors = []
        for j in range(n):
            if i == j:
                continue
            dist = _haversine_km(fires[i]["lat"], fires[i]["lon"], fires[j]["lat"], fires[j]["lon"])
            if dist <= eps_km:
                neighbors.append(j)
        
        if len(neighbors) < min_points - 1:
            # Punto aislado (no forma cluster)
            continue
        
        # Crear nuevo cluster
        labels[i] = cluster_id
        seed_set = list(neighbors)
        
        # Expandir cluster (BFS)
        k = 0
        while k < len(seed_set):
            j = seed_set[k]
            if labels[j] == -1 or labels[j] == -2:
                labels[j] = cluster_id
                # Buscar vecinos de j
                j_neighbors = []
                for m in range(n):
                    if m == j:
                        continue
                    if _haversine_km(fires[j]["lat"], fires[j]["lon"], fires[m]["lat"], fires[m]["lon"]) <= eps_km:
                        j_neighbors.append(m)
                if len(j_neighbors) >= min_points - 1:
                    for nn in j_neighbors:
                        if nn not in seed_set:
                            seed_set.append(nn)
            k += 1
        
        cluster_id += 1

    # Construir resultado
    clusters = {}
    isolated = []
    
    for i, label in enumerate(labels):
        if label == -1:
            isolated.append(fires[i])
        else:
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(fires[i])

    # Calcular estadísticas por cluster
    cluster_list = []
    for cid, points in clusters.items():
        lats = [p["lat"] for p in points]
        lons = [p["lon"] for p in points]
        frps = [p.get("frp", 0) for p in points]
        
        centroid_lat = sum(lats) / len(lats)
        centroid_lon = sum(lons) / len(lons)
        total_frp = round(sum(frps), 1)
        max_frp = round(max(frps), 1)
        
        # Área estimada: bounding box en km²
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        # 1 grado lat ≈ 111km, 1 grado lon ≈ 111km * cos(lat)
        height_km = lat_range * 111.0
        width_km = lon_range * 111.0 * math.cos(math.radians(centroid_lat))
        area_km2 = round(max(height_km * width_km, 0.14), 2)  # mínimo 1 pixel VIIRS
        
        # Calcular radio máximo desde centroide
        max_radius = 0
        for p in points:
            d = _haversine_km(centroid_lat, centroid_lon, p["lat"], p["lon"])
            if d > max_radius:
                max_radius = d
        
        # Clasificación del incendio
        if total_frp >= 500 or len(points) >= 50:
            category = "mega_incendio"
            severity = "CRÍTICO"
        elif total_frp >= 100 or len(points) >= 20:
            category = "incendio_mayor"
            severity = "ALTO"
        elif total_frp >= 30 or len(points) >= 5:
            category = "incendio_activo"
            severity = "MODERADO"
        else:
            category = "foco_menor"
            severity = "BAJO"
        
        cluster_list.append({
            "id": cid,
            "centroid_lat": round(centroid_lat, 4),
            "centroid_lon": round(centroid_lon, 4),
            "fire_count": len(points),
            "total_frp_mw": total_frp,
            "max_frp_mw": max_frp,
            "area_km2": area_km2,
            "radius_km": round(max_radius, 2),
            "category": category,
            "severity": severity,
            "satellite": points[0].get("satellite", "NOAA-20"),
            "fires": points  # focos individuales del cluster
        })
    
    # Ordenar por FRP total descendente
    cluster_list.sort(key=lambda c: c["total_frp_mw"], reverse=True)

    # Re-numerar IDs
    for i, c in enumerate(cluster_list):
        c["id"] = i + 1

    logger.info("Fire clustering: %d clusters, %d isolated from %d fires", len(cluster_list), len(isolated), n)

    return {
        "clusters": cluster_list,
        "isolated": isolated,
        "total_clusters": len(cluster_list),
        "total_isolated": len(isolated),
        "algorithm": "DBSCAN",
        "params": {"eps_km": eps_km, "min_points": min_points},
        "top_incident": cluster_list[0] if cluster_list else None
    }
