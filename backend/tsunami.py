import requests
from datetime import datetime, timezone, timedelta


def get_tsunami_alerts():
    """
    Consulta USGS por sismos costeros de Chile en las últimas 24h
    que podrían generar tsunami. Umbrales calibrados para Chile.
    """
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

    params = {
        "format": "geojson",
        "minlatitude": -56,
        "maxlatitude": -17,
        "minlongitude": -76,
        "maxlongitude": -68,
        "minmagnitude": 6.0,
        "orderby": "time",
        "limit": 10,
        "starttime": start
    }

    alerts = []
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()

        for f in data.get("features", []):
            try:
                props = f["properties"]
                coords = f["geometry"]["coordinates"]
                lon = float(coords[0])
                lat = float(coords[1])
                depth = float(coords[2])
                mag = props.get("mag")

                # Validar magnitud
                if mag is None:
                    continue
                mag = float(mag)

                # Solo sismos costeros (zona de subducción chilena)
                if lon > -69.5:
                    continue

                # Umbrales calibrados para Chile
                if mag >= 7.5:
                    level = "ALERTA"
                    color = "#ff3333"
                elif mag >= 7.0:
                    level = "VIGILANCIA"
                    color = "#ff9500"
                elif mag >= 6.5:
                    level = "INFORMACIÓN"
                    color = "#ffd700"
                else:
                    level = "MONITOREO"
                    color = "#4fc3f7"

                alerts.append({
                    "magnitude": round(mag, 1),
                    "place": props.get("place", "Chile"),
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "depth": round(depth, 1),
                    "time": props.get("time"),
                    "level": level,
                    "color": color,
                    "url": props.get("url", "")
                })

            except (KeyError, ValueError, TypeError):
                continue

    except Exception as e:
        print("Error consultando USGS tsunami:", e)

    return {"count": len(alerts), "data": alerts}


def get_aftershocks(lat, lon, min_mag=2.5):
    """
    Busca réplicas de un sismo en un radio de ~150km
    en las últimas 48 horas usando USGS.
    """
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")

    # Radio aproximado de 1.5 grados (~165km)
    lat_delta = 1.5
    lon_delta = 1.5

    params = {
        "format": "geojson",
        "minlatitude": lat - lat_delta,
        "maxlatitude": lat + lat_delta,
        "minlongitude": lon - lon_delta,
        "maxlongitude": lon + lon_delta,
        "minmagnitude": min_mag,
        "orderby": "time",
        "starttime": start,
        "limit": 50
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        aftershocks = []

        for f in data.get("features", []):
            try:
                props = f["properties"]
                coords = f["geometry"]["coordinates"]
                mag = props.get("mag")
                if mag is None:
                    continue
                aftershocks.append({
                    "lat": round(float(coords[1]), 4),
                    "lon": round(float(coords[0]), 4),
                    "depth": round(float(coords[2]), 1),
                    "magnitude": round(float(mag), 1),
                    "place": props.get("place", "Chile"),
                    "time": props.get("time")
                })
            except (KeyError, ValueError, TypeError):
                continue

        return {"count": len(aftershocks), "data": aftershocks}

    except Exception as e:
        return {"count": 0, "data": [], "error": str(e)}