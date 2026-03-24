import requests
from datetime import datetime, timezone, timedelta

def get_quakes():
    url = "https://api.xor.cl/sismo/recent"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Rolling 24h window — always show last 24 hours of seismic activity
        now = datetime.now(timezone.utc)
        cutoff_24h = now - timedelta(hours=24)

        quakes = []
        for sismo in data.get("events", []):
            try:
                time_str = sismo.get("utc_date", "")
                if time_str:
                    try:
                        t = datetime.fromisoformat(time_str.replace(" ", "T")).replace(tzinfo=timezone.utc)
                        if t < cutoff_24h:
                            continue
                    except:
                        pass

                quakes.append({
                    "lat": float(sismo["latitude"]),
                    "lon": float(sismo["longitude"]),
                    "depth": float(sismo.get("depth", 0)),
                    "magnitude": float(sismo["magnitude"]["value"]),
                    "place": sismo.get("geo_reference", "Chile"),
                    "time": time_str,
                    "url": sismo.get("url", "")
                })
            except (KeyError, ValueError):
                continue

        return {"count": len(quakes), "data": quakes}

    except Exception as e:
        return {"count": 0, "data": [], "error": str(e)}
