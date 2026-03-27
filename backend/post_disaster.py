"""
Evaluación Post-Desastre — VigilaChile
Genera reportes de evaluación de daño estimado después de un sismo,
cruzando datos geoespaciales de múltiples fuentes sin exponer personal humano.

Combina: sismología (magnitud/profundidad), datos poblacionales,
infraestructura crítica, incendios activos VIIRS, y volcanes cercanos
para producir una evaluación integral de zona afectada.
"""

import math
import logging

logger = logging.getLogger(__name__)


# Infraestructura crítica de Chile (hospitales regionales, aeropuertos, puentes clave)
# Fuente: Ministerio de Salud, DGAC, MOP
CRITICAL_INFRASTRUCTURE = [
    # Hospitales regionales principales
    {"name": "Hospital Regional de Arica", "type": "hospital", "lat": -18.478, "lon": -70.318, "capacity": "alta"},
    {"name": "Hospital Regional de Iquique", "type": "hospital", "lat": -20.213, "lon": -70.143, "capacity": "alta"},
    {"name": "Hospital Regional de Antofagasta", "type": "hospital", "lat": -23.650, "lon": -70.400, "capacity": "alta"},
    {"name": "Hospital Regional de Copiapo", "type": "hospital", "lat": -27.367, "lon": -70.332, "capacity": "media"},
    {"name": "Hospital Regional de La Serena", "type": "hospital", "lat": -29.907, "lon": -71.252, "capacity": "alta"},
    {"name": "Hospital Van Buren (Valparaiso)", "type": "hospital", "lat": -33.047, "lon": -71.612, "capacity": "alta"},
    {"name": "Hospital San Borja Arriaran (Santiago)", "type": "hospital", "lat": -33.443, "lon": -70.652, "capacity": "alta"},
    {"name": "Hospital Barros Luco (Santiago)", "type": "hospital", "lat": -33.492, "lon": -70.653, "capacity": "alta"},
    {"name": "Hospital Regional de Rancagua", "type": "hospital", "lat": -34.170, "lon": -70.740, "capacity": "media"},
    {"name": "Hospital Regional de Talca", "type": "hospital", "lat": -35.426, "lon": -71.655, "capacity": "media"},
    {"name": "Hospital Regional de Concepcion", "type": "hospital", "lat": -36.827, "lon": -73.050, "capacity": "alta"},
    {"name": "Hospital Regional de Temuco", "type": "hospital", "lat": -38.735, "lon": -72.590, "capacity": "alta"},
    {"name": "Hospital Regional de Valdivia", "type": "hospital", "lat": -39.819, "lon": -73.236, "capacity": "media"},
    {"name": "Hospital Regional de Puerto Montt", "type": "hospital", "lat": -41.469, "lon": -72.936, "capacity": "alta"},
    {"name": "Hospital Regional de Coyhaique", "type": "hospital", "lat": -45.571, "lon": -72.066, "capacity": "media"},
    {"name": "Hospital Regional de Punta Arenas", "type": "hospital", "lat": -53.154, "lon": -70.911, "capacity": "media"},
    # Aeropuertos principales
    {"name": "Aeropuerto AMB (Santiago)", "type": "aeropuerto", "lat": -33.393, "lon": -70.786, "capacity": "alta"},
    {"name": "Aeropuerto Carriel Sur (Concepcion)", "type": "aeropuerto", "lat": -36.773, "lon": -73.063, "capacity": "alta"},
    {"name": "Aeropuerto La Araucania (Temuco)", "type": "aeropuerto", "lat": -38.926, "lon": -72.651, "capacity": "media"},
    {"name": "Aeropuerto El Tepual (Puerto Montt)", "type": "aeropuerto", "lat": -41.439, "lon": -73.094, "capacity": "media"},
    {"name": "Aeropuerto Diego Aracena (Iquique)", "type": "aeropuerto", "lat": -20.535, "lon": -70.181, "capacity": "media"},
    {"name": "Aeropuerto Cerro Moreno (Antofagasta)", "type": "aeropuerto", "lat": -23.444, "lon": -70.441, "capacity": "media"},
    # Puentes y viaductos críticos
    {"name": "Puente Biobio (Concepcion)", "type": "puente", "lat": -36.832, "lon": -73.067, "capacity": "alta"},
    {"name": "Puente Chacao (en construccion)", "type": "puente", "lat": -41.780, "lon": -73.513, "capacity": "alta"},
    {"name": "Viaducto Malleco (La Araucania)", "type": "puente", "lat": -37.800, "lon": -72.667, "capacity": "media"},
    # Represas
    {"name": "Central Ralco (Biobio)", "type": "represa", "lat": -37.917, "lon": -71.617, "capacity": "alta"},
    {"name": "Central Pangue (Biobio)", "type": "represa", "lat": -37.917, "lon": -71.533, "capacity": "alta"},
    {"name": "Embalse Rapel (O'Higgins)", "type": "represa", "lat": -34.050, "lon": -71.600, "capacity": "alta"},
]


def _haversine_km(lat1, lon1, lat2, lon2):
    """Distancia geodésica entre dos puntos en km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _estimate_mercalli(magnitude, depth_km, distance_km):
    """
    Estima intensidad Mercalli Modificada simplificada.
    Basado en atenuación por distancia y profundidad.
    """
    if magnitude < 3.0:
        return {"intensity": "I-II", "level": "imperceptible", "damage": "ninguno"}

    # Atenuación: intensidad decrece con distancia y profundidad
    # Fórmula simplificada basada en relaciones empíricas para Chile
    effective_distance = math.sqrt(distance_km ** 2 + depth_km ** 2)
    if effective_distance < 1:
        effective_distance = 1

    # Intensidad base por magnitud
    base_intensity = 1.5 * magnitude - 1.0
    # Atenuación logarítmica
    attenuation = 2.5 * math.log10(effective_distance)
    mmi = max(1, base_intensity - attenuation)

    if mmi >= 9:
        return {"intensity": "IX+", "level": "violento", "damage": "destruccion generalizada, colapso de estructuras"}
    elif mmi >= 8:
        return {"intensity": "VIII", "level": "severo", "damage": "dano considerable en edificios, caida de muros"}
    elif mmi >= 7:
        return {"intensity": "VII", "level": "muy fuerte", "damage": "dano moderado en estructuras, grietas en muros"}
    elif mmi >= 6:
        return {"intensity": "VI", "level": "fuerte", "damage": "sentido por todos, dano leve, objetos caen"}
    elif mmi >= 5:
        return {"intensity": "V", "level": "moderado", "damage": "sentido ampliamente, dano muy leve"}
    elif mmi >= 4:
        return {"intensity": "IV", "level": "ligero", "damage": "sentido por muchos en interiores"}
    elif mmi >= 3:
        return {"intensity": "III", "level": "debil", "damage": "sentido por algunos en interiores"}
    else:
        return {"intensity": "I-II", "level": "imperceptible", "damage": "ninguno"}


def assess_post_disaster(quake, fires=None, volcanoes=None):
    """
    Evaluación post-desastre para un sismo específico.

    Args:
        quake: dict con lat, lon, magnitude, depth, place, time
        fires: list de focos de incendio activos
        volcanoes: list de volcanes

    Returns:
        dict con evaluación integral de la zona afectada
    """
    lat = quake["lat"]
    lon = quake["lon"]
    mag = quake["magnitude"]
    depth = quake.get("depth", 30)
    place = quake.get("place", "Chile")

    # 1. Radio de afectación significativa por magnitud
    # Basado en datos reales de terremotos en Chile:
    # 27F 2010 (M8.8): daño significativo ~150km del epicentro
    # Illapel 2015 (M8.4): daño moderado ~100km
    # Estos son radios de DAÑO POTENCIAL, no de percepción
    impact_radii = {
        5.0: 15, 5.5: 25, 6.0: 40, 6.5: 60,
        7.0: 90, 7.5: 130, 8.0: 180, 8.5: 250, 9.0: 350
    }
    radius_km = 15
    for m, r in sorted(impact_radii.items()):
        if mag >= m:
            radius_km = r

    # 2. Intensidad Mercalli en el epicentro
    epicenter_mmi = _estimate_mercalli(mag, depth, 0)

    # 3. Estimación poblacional en zona de daño potencial
    # Densidad promedio por zona de Chile (hab/km²)
    if lat > -20:
        density = 5
    elif lat > -25:
        density = 8
    elif lat > -30:
        density = 12
    elif lat > -33:
        density = 80
    elif lat > -35:
        density = 180
    elif lat > -38:
        density = 40
    elif lat > -40:
        density = 25
    else:
        density = 3

    area_km2 = math.pi * (radius_km ** 2)
    # Factor 0.15: no toda el area esta habitada uniformemente
    population_affected = int(area_km2 * density * 0.15)

    # 4. Infraestructura crítica en zona de impacto
    affected_infra = []
    for infra in CRITICAL_INFRASTRUCTURE:
        dist = _haversine_km(lat, lon, infra["lat"], infra["lon"])
        if dist <= radius_km:
            mmi_at_infra = _estimate_mercalli(mag, depth, dist)
            affected_infra.append({
                "name": infra["name"],
                "type": infra["type"],
                "distance_km": round(dist, 1),
                "estimated_intensity": mmi_at_infra["intensity"],
                "estimated_damage": mmi_at_infra["damage"],
                "critical_capacity": infra["capacity"]
            })
    affected_infra.sort(key=lambda x: x["distance_km"])

    # 5. Incendios activos en zona (riesgo de incendios post-sismo por rotura de gas)
    fires_in_zone = []
    if fires:
        for f in fires:
            dist = _haversine_km(lat, lon, f["lat"], f["lon"])
            if dist <= radius_km:
                fires_in_zone.append({
                    "lat": f["lat"],
                    "lon": f["lon"],
                    "frp_mw": f.get("frp", 0),
                    "distance_km": round(dist, 1)
                })
    fires_in_zone.sort(key=lambda x: x["distance_km"])

    # 6. Volcanes cercanos que podrían activarse
    nearby_volcanoes = []
    if volcanoes:
        volc_list = volcanoes if isinstance(volcanoes, list) else volcanoes.get("data", [])
        for v in volc_list:
            dist = _haversine_km(lat, lon, v["lat"], v["lon"])
            if dist <= 200:  # Volcanes dentro de 200km
                nearby_volcanoes.append({
                    "name": v["name"],
                    "alert": v.get("alert", "Verde"),
                    "risk_rank": v.get("risk_rank"),
                    "distance_km": round(dist, 1)
                })
    nearby_volcanoes.sort(key=lambda x: x["distance_km"])

    # 7. Nivel de alerta sugerido
    if mag >= 7.5 or epicenter_mmi["intensity"] in ("IX+",):
        alert_level = "ROJA"
        alert_action = "Evacuacion inmediata. Activar protocolo nacional de emergencia. Desplegar equipos SAR."
    elif mag >= 6.5 or epicenter_mmi["intensity"] in ("VIII",):
        alert_level = "NARANJA"
        alert_action = "Alerta de tsunami para costa. Evaluar dano estructural en radio de " + str(radius_km) + "km. Activar hospitales de campaña."
    elif mag >= 5.5 or epicenter_mmi["intensity"] in ("VII",):
        alert_level = "AMARILLA"
        alert_action = "Inspeccion de infraestructura critica. Monitoreo de replicas. Preparar albergues."
    elif mag >= 4.5:
        alert_level = "VERDE-PREVENTIVA"
        alert_action = "Monitoreo de replicas. Sin accion inmediata requerida."
    else:
        alert_level = "VERDE"
        alert_action = "Sin accion requerida. Evento dentro de parametros normales."

    # 8. Recomendaciones para equipos de evaluación
    recommendations = []
    if len(affected_infra) > 0:
        hospitals = [i for i in affected_infra if i["type"] == "hospital"]
        bridges = [i for i in affected_infra if i["type"] in ("puente", "represa")]
        airports = [i for i in affected_infra if i["type"] == "aeropuerto"]
        if hospitals:
            recommendations.append("Verificar operatividad de " + str(len(hospitals)) + " hospital(es) en radio de " + str(radius_km) + "km")
        if bridges:
            recommendations.append("Inspeccionar " + str(len(bridges)) + " puente(s)/represa(s) — priorizar las mas cercanas al epicentro")
        if airports:
            recommendations.append("Confirmar estado de " + str(len(airports)) + " aeropuerto(s) para operaciones de ayuda")
    if len(fires_in_zone) > 0:
        high_frp = [f for f in fires_in_zone if f["frp_mw"] >= 20]
        recommendations.append("Focos de calor preexistentes en zona: " + str(len(fires_in_zone)) + " (" + str(len(high_frp)) + " de alta intensidad). Vigilar posible propagacion por dano en infraestructura de gas")
    if len(nearby_volcanoes) > 0:
        alert_volc = [v for v in nearby_volcanoes if v["alert"] != "Verde"]
        if alert_volc:
            recommendations.append("Monitorear " + str(len(alert_volc)) + " volcan(es) en alerta cercano(s): " + ", ".join([v["name"] for v in alert_volc]))
    if mag >= 6.5 and depth < 50:
        recommendations.append("Sismo superficial de alta magnitud: priorizar evaluacion visual con drones en zonas de dificil acceso")
    elif mag >= 6.0:
        recommendations.append("Evaluar dano estructural con drones en infraestructura critica cercana al epicentro")
    if not recommendations:
        recommendations.append("Sin acciones prioritarias. Mantener monitoreo de rutina")

    logger.info("Post-disaster assessment: M%.1f at (%.2f, %.2f), alert=%s, infra=%d, fires=%d",
                mag, lat, lon, alert_level, len(affected_infra), len(fires_in_zone))

    return {
        "earthquake": {
            "magnitude": mag,
            "depth_km": depth,
            "location": place,
            "lat": lat,
            "lon": lon,
            "time": quake.get("time", "")
        },
        "impact_assessment": {
            "impact_radius_km": radius_km,
            "epicenter_intensity": epicenter_mmi,
            "estimated_population_affected": population_affected,
            "population_density": "Alta" if density > 100 else "Media" if density > 20 else "Baja"
        },
        "infrastructure_at_risk": {
            "count": len(affected_infra),
            "description": "Instalaciones criticas dentro de " + str(radius_km) + "km del epicentro",
            "facilities": affected_infra[:10]
        },
        "fire_risk": {
            "active_fires_in_zone": len(fires_in_zone),
            "high_intensity_fires": len([f for f in fires_in_zone if f["frp_mw"] >= 20]),
            "description": "Focos de calor VIIRS preexistentes dentro del radio de impacto (no causados por el sismo)",
            "fires": fires_in_zone[:10]
        },
        "volcanic_risk": {
            "nearby_volcanoes": len(nearby_volcanoes),
            "volcanoes": nearby_volcanoes[:5]
        },
        "alert": {
            "level": alert_level,
            "recommended_action": alert_action
        },
        "recommendations": recommendations,
        "methodology": "Evaluacion automatizada cruzando datos sismicos (CSN), satelitales (VIIRS NOAA-20), volcanicos (SERNAGEOMIN) e infraestructura critica (MOP/MINSAL/DGAC). Intensidad estimada mediante atenuacion Mercalli simplificada."
    }
