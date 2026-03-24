REGIONS = [
    {
        "id": "tarapaca", "name": "Tarapacá", "lat": -20.2, "lon": -69.3,
        "coastal": True, "population": 300000, "seismic_factor": 0.9,
        "tsunami_risk": True, "communes": ["Iquique", "Alto Hospicio", "Pozo Almonte"]
    },
    {
        "id": "antofagasta", "name": "Antofagasta", "lat": -23.6, "lon": -68.2,
        "coastal": True, "population": 690000, "seismic_factor": 0.95,
        "tsunami_risk": True, "communes": ["Antofagasta", "Calama", "Tocopilla", "Socaire"]
    },
    {
        "id": "atacama", "name": "Atacama", "lat": -27.4, "lon": -70.3,
        "coastal": True, "population": 290000, "seismic_factor": 0.85,
        "tsunami_risk": True, "communes": ["Copiapó", "Vallenar", "Chañaral"]
    },
    {
        "id": "coquimbo", "name": "Coquimbo", "lat": -30.0, "lon": -70.9,
        "coastal": True, "population": 780000, "seismic_factor": 0.9,
        "tsunami_risk": True, "communes": ["La Serena", "Coquimbo", "Ovalle"]
    },
    {
        "id": "valparaiso", "name": "Valparaíso", "lat": -33.0, "lon": -71.3,
        "coastal": True, "population": 1800000, "seismic_factor": 0.85,
        "tsunami_risk": True, "communes": ["Valparaíso", "Viña del Mar", "Quilpué", "San Antonio"]
    },
    {
        "id": "metropolitana", "name": "Metropolitana", "lat": -33.5, "lon": -70.6,
        "coastal": False, "population": 8000000, "seismic_factor": 0.75,
        "tsunami_risk": False, "communes": ["Santiago", "Puente Alto", "Maipú", "Las Condes"]
    },
    {
        "id": "ohiggins", "name": "O'Higgins", "lat": -34.6, "lon": -71.0,
        "coastal": False, "population": 920000, "seismic_factor": 0.8,
        "tsunami_risk": False, "communes": ["Rancagua", "San Fernando", "Pichilemu"]
    },
    {
        "id": "maule", "name": "Maule", "lat": -35.5, "lon": -71.5,
        "coastal": True, "population": 1100000, "seismic_factor": 0.88,
        "tsunami_risk": True, "communes": ["Talca", "Curicó", "Linares", "Constitución"]
    },
    {
        "id": "nuble", "name": "Ñuble", "lat": -36.7, "lon": -71.8,
        "coastal": False, "population": 500000, "seismic_factor": 0.82,
        "tsunami_risk": False, "communes": ["Chillán", "Los Ángeles"]
    },
    {
        "id": "biobio", "name": "Biobío", "lat": -37.5, "lon": -72.5,
        "coastal": True, "population": 1600000, "seismic_factor": 0.92,
        "tsunami_risk": True, "communes": ["Concepción", "Talcahuano", "Los Ángeles", "Coronel"]
    },
    {
        "id": "araucania", "name": "Araucanía", "lat": -38.9, "lon": -72.6,
        "coastal": True, "population": 990000, "seismic_factor": 0.8,
        "tsunami_risk": False, "communes": ["Temuco", "Villarrica", "Pucón", "Angol"]
    },
    {
        "id": "los_rios", "name": "Los Ríos", "lat": -39.8, "lon": -73.2,
        "coastal": True, "population": 400000, "seismic_factor": 0.78,
        "tsunami_risk": True, "communes": ["Valdivia", "La Unión", "Panguipulli"]
    },
    {
        "id": "los_lagos", "name": "Los Lagos", "lat": -41.5, "lon": -72.9,
        "coastal": True, "population": 870000, "seismic_factor": 0.75,
        "tsunami_risk": True, "communes": ["Puerto Montt", "Castro", "Osorno", "Puerto Varas"]
    },
    {
        "id": "aysen", "name": "Aysén", "lat": -45.6, "lon": -72.1,
        "coastal": True, "population": 110000, "seismic_factor": 0.7,
        "tsunami_risk": False, "communes": ["Coyhaique", "Aysén"]
    },
    {
        "id": "magallanes", "name": "Magallanes", "lat": -53.2, "lon": -70.9,
        "coastal": True, "population": 170000, "seismic_factor": 0.6,
        "tsunami_risk": False, "communes": ["Punta Arenas", "Puerto Natales"]
    },
]


def calculate_region_risk(quakes, fires):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    cutoff_6h = now - timedelta(hours=6)
    results = []

    for region in REGIONS:
        lat, lon = region["lat"], region["lon"]
        radius = 2.0  # grados — más preciso

        nearby_24h = []
        nearby_6h = []

        for q in quakes:
            try:
                qlat = float(q["lat"])
                qlon = float(q["lon"])
                if abs(qlat - lat) < radius and abs(qlon - lon) < radius:
                    nearby_24h.append(q)
                    qt = q.get("time", "")
                    if qt:
                        try:
                            qtime = datetime.fromisoformat(
                                qt.replace(" ", "T")
                            ).replace(tzinfo=timezone.utc)
                            if qtime > cutoff_6h:
                                nearby_6h.append(q)
                        except:
                            pass
            except:
                pass

        max_mag = max([q["magnitude"] for q in nearby_24h], default=0)
        count_24h = len(nearby_24h)
        count_6h = len(nearby_6h)

        nearby_fires = sum(
            1 for f in fires
            if abs(f.get("lat", 0) - lat) < radius
            and abs(f.get("lon", 0) - lon) < radius
        )

        # Score calibrado — Chile tiene alta actividad normal
        seismic_score = min(60, (max_mag * 10) + (count_24h * 0.3) + (count_6h * 1.5))
        fire_score = min(20, nearby_fires * 5)
        coastal_bonus = 10 if region["coastal"] and max_mag >= 6.5 else 0
        pop_factor = min(10, region["population"] / 1000000)
        vuln_score = (seismic_score * region["seismic_factor"]) + fire_score + coastal_bonus + pop_factor

        # Umbrales calibrados para la realidad sísmica chilena
        # En Chile, 20-30 sismos diarios M2.5+ es completamente normal
        if max_mag >= 6.5 or (max_mag >= 6.0 and count_24h >= 20):
            level = "ROJA"
            color = "#ff3333"
        elif max_mag >= 6.0 or (max_mag >= 5.5 and count_24h >= 15):
            level = "NARANJA"
            color = "#ff9500"
        elif max_mag >= 5.0 or (max_mag >= 4.5 and count_24h >= 20):
            level = "AMARILLA"
            color = "#ffd700"
        elif max_mag >= 4.0 or count_24h >= 8:
            level = "ALERTA VERDE"
            color = "#4ade80"
        elif count_24h > 0:
            level = "VERDE"
            color = "#22c55e"
        else:
            level = "SIN ACTIVIDAD"
            color = "#5c7a9e"

        results.append({
            "id": region["id"],
            "name": region["name"],
            "lat": lat,
            "lon": lon,
            "level": level,
            "color": color,
            "score": round(vuln_score, 1),
            "max_magnitude": max_mag,
            "quakes_24h": count_24h,
            "quakes_6h": count_6h,
            "fires_nearby": nearby_fires,
            "coastal": region["coastal"],
            "tsunami_risk": region["tsunami_risk"] and max_mag >= 6.5,
            "population": region["population"],
            "communes": region["communes"]
        })

    return {"count": len(results), "data": results}


def get_vulnerability_index(quakes, fires):
    regions_data = calculate_region_risk(quakes, fires)
    for r in regions_data["data"]:
        seismic = min(40, r["max_magnitude"] * 5 + r["quakes_24h"] * 0.2)
        coastal = 15 if r["coastal"] else 0
        pop = min(15, r["population"] / 600000)
        fire = min(10, r["fires_nearby"] * 2)
        activity = min(10, r["quakes_6h"] * 1.5)
        r["vulnerability_index"] = round(seismic + coastal + pop + fire + activity, 1)
        r["vulnerability_level"] = (
            "Crítico" if r["vulnerability_index"] >= 65 else
            "Alto" if r["vulnerability_index"] >= 45 else
            "Moderado" if r["vulnerability_index"] >= 25 else
            "Bajo"
        )
    return regions_data