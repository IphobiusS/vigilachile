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

# Bounding box Chile: west,south,east,north
CHILE_BBOX = "-76,-56,-66,-17"


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
        return {"count": len(fires), "data": fires, "source": "VIIRS_NOAA20_NRT"}

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

                if not (-56 <= lat <= -17 and -76 <= lon <= -66):
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
