import requests
import csv
import io
from datetime import datetime, timedelta, timezone

def get_fires():
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

                # Solo Chile
                if not (-56 <= lat <= -17 and -76 <= lon <= -66):
                    continue

                # Solo últimas 24h reales
                if date not in (today, yesterday):
                    continue

                # Filtrar focos de baja confianza
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
                    "confidence": confidence
                })
            except (ValueError, KeyError):
                continue

        return {"count": len(fires), "data": fires}

    except Exception as e:
        return {"count": 0, "data": [], "error": str(e)}