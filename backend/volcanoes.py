def get_volcanoes():
    """
    Volcanes activos de Chile monitoreados por SERNAGEOMIN.
    Fuente: Red Nacional de Vigilancia Volcánica — sernageomin.cl
    Alertas actualizadas a marzo 2026.
    """
    volcanoes = [
        {
            "name": "Villarrica",
            "lat": -39.42, "lon": -71.93,
            "alert": "Amarilla",
            "region": "Araucanía",
            "elevation": 2847,
            "description": "Actividad eruptiva menor continua. Monitoreo permanente."
        },
        {
            "name": "Copahue",
            "lat": -37.86, "lon": -71.17,
            "alert": "Amarilla",
            "region": "Biobío",
            "elevation": 2997,
            "description": "Actividad fumarólica elevada. Zona de exclusión activa."
        },
        {
            "name": "Nevados de Chillán",
            "lat": -36.86, "lon": -71.38,
            "alert": "Amarilla",
            "region": "Ñuble",
            "elevation": 3212,
            "description": "Actividad explosiva menor. Columnas de gases frecuentes."
        },
        {
            "name": "Calbuco",
            "lat": -41.33, "lon": -72.61,
            "alert": "Verde",
            "region": "Los Lagos",
            "elevation": 2003,
            "description": "Sin actividad relevante. Monitoreo rutinario."
        },
        {
            "name": "Hudson",
            "lat": -45.90, "lon": -72.97,
            "alert": "Verde",
            "region": "Aysén",
            "elevation": 1905,
            "description": "Sin actividad relevante."
        },
        {
            "name": "Láscar",
            "lat": -23.37, "lon": -67.73,
            "alert": "Verde",
            "region": "Antofagasta",
            "elevation": 5592,
            "description": "Actividad fumarólica normal para el volcán."
        },
        {
            "name": "Planchón-Peteroa",
            "lat": -35.24, "lon": -70.57,
            "alert": "Verde",
            "region": "Maule",
            "elevation": 4107,
            "description": "Sin actividad relevante."
        },
        {
            "name": "Llaima",
            "lat": -38.69, "lon": -71.73,
            "alert": "Verde",
            "region": "Araucanía",
            "elevation": 3125,
            "description": "Sin actividad relevante. Monitoreo rutinario."
        },
        {
            "name": "Osorno",
            "lat": -41.10, "lon": -72.49,
            "alert": "Verde",
            "region": "Los Lagos",
            "elevation": 2652,
            "description": "Sin actividad relevante."
        },
        {
            "name": "Tupungatito",
            "lat": -33.56, "lon": -69.80,
            "alert": "Verde",
            "region": "Metropolitana",
            "elevation": 5682,
            "description": "Sin actividad relevante."
        },
        {
            "name": "Tinguiririca",
            "lat": -34.81, "lon": -70.35,
            "alert": "Verde",
            "region": "O'Higgins",
            "elevation": 4280,
            "description": "Sin actividad relevante."
        },
        {
            "name": "San Pedro",
            "lat": -21.88, "lon": -68.40,
            "alert": "Verde",
            "region": "Antofagasta",
            "elevation": 6145,
            "description": "Sin actividad relevante."
        },
    ]
    return {"count": len(volcanoes), "data": volcanoes}