import requests
from datetime import datetime, timezone, timedelta

# Chile timezone: UTC-3 (CLT standard) / UTC-4 (CLST summer)
# Chile uses UTC-3 most of the year since 2019
CHILE_TZ = timezone(timedelta(hours=-3))

def get_quakes():
    url = "https://api.xor.cl/sismo/recent"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Use Chile's midnight as cutoff, not rolling 24h UTC
        now_chile = datetime.now(CHILE_TZ)
        chile_midnight = now_chile.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = chile_midnight.astimezone(timezone.utc)

        quakes = []
        for sismo in data.get("events", []):
            try:
                time_str = sismo.get("utc_date", "")
                if time_str:
                    try:
                        t = datetime.fromisoformat(time_str.replace(" ", "T")).replace(tzinfo=timezone.utc)
                        if t < cutoff:
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