"""
Focos de calor activos en Chile — NASA FIRMS
Fuente primaria: VIIRS NOAA-20 NRT (375m resolucion, near real-time)
Fuente secundaria: MODIS C6.1 CSV (1km resolucion, fallback)

VIIRS provee datos satelitales de mayor resolucion (375m vs 1km MODIS)
con deteccion near real-time del satelite NOAA-20.
"""

import requests
import csv
import io
import os
import logging
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
