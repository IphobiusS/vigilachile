"""
Planificación de Despliegue de Drones — VigilaChile
Genera rutas de patrullaje y puntos de despliegue óptimos para drones
basándose en los frentes de incendio detectados por clustering DBSCAN.

Este módulo actúa como la "capa de inteligencia" que conecta datos satelitales
(VIIRS NOAA-20) con operaciones de drones para protección civil.

Funcionalidades:
- Waypoints priorizados por severidad de incendio
- Ruta de patrullaje optimizada (nearest-neighbor TSP)
- Estimación de tiempo de vuelo y cobertura
- Zonas de observación sugeridas para evaluación visual
"""

import math
import logging

logger = logging.getLogger(__name__)


def _haversine_km(lat1, lon1, lat2, lon2):
    """Distancia geodésica entre dos puntos en km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def plan_drone_deployment(clusters, base_lat=-33.393, base_lon=-70.786, max_drones=3, drone_range_km=80, drone_speed_kmh=60):
    """
    Genera un plan de despliegue de drones basado en frentes de incendio activos.

    Args:
        clusters: resultado de cluster_fires() — dict con "clusters" list
        base_lat/lon: base de operaciones (default: Aeropuerto AMB Santiago)
        max_drones: cantidad de drones disponibles
        drone_range_km: autonomía de vuelo (radio operativo)
        drone_speed_kmh: velocidad crucero del dron

    Returns:
        dict con plan de despliegue, waypoints y rutas
    """
    if not clusters or not clusters.get("clusters"):
        return {
            "status": "sin_objetivos",
            "message": "No se detectaron frentes de incendio que requieran despliegue de drones.",
            "missions": [],
            "total_clusters_detected": 0
        }

    all_clusters = clusters["clusters"]

    # Filtrar solo clusters que ameriten dron (MODERADO o superior)
    priority_clusters = [c for c in all_clusters if c["severity"] in ("CRÍTICO", "ALTO", "MODERADO")]

    if not priority_clusters:
        return {
            "status": "sin_prioridad",
            "message": "Todos los focos detectados son de baja intensidad. No se requiere despliegue de drones.",
            "missions": [],
            "total_clusters_detected": len(all_clusters)
        }

    # Agrupar clusters por zona geográfica para asignar a drones
    # Usamos K zonas (1 por dron disponible) con nearest-neighbor
    missions = []
    assigned = set()

    for drone_id in range(1, max_drones + 1):
        if len(assigned) >= len(priority_clusters):
            break

        # Encontrar el cluster no asignado de mayor prioridad
        best = None
        for i, c in enumerate(priority_clusters):
            if i not in assigned:
                best = i
                break

        if best is None:
            break

        # Construir ruta para este dron: nearest-neighbor desde el cluster principal
        route = [best]
        assigned.add(best)
        current = best

        while True:
            # Buscar el cluster no asignado más cercano al actual
            nearest = None
            nearest_dist = float("inf")
            for i, c in enumerate(priority_clusters):
                if i in assigned:
                    continue
                dist = _haversine_km(
                    priority_clusters[current]["centroid_lat"],
                    priority_clusters[current]["centroid_lon"],
                    c["centroid_lat"], c["centroid_lon"]
                )
                # Solo incluir si está dentro del rango operativo desde el cluster principal
                dist_from_start = _haversine_km(
                    priority_clusters[best]["centroid_lat"],
                    priority_clusters[best]["centroid_lon"],
                    c["centroid_lat"], c["centroid_lon"]
                )
                if dist < nearest_dist and dist_from_start <= drone_range_km:
                    nearest = i
                    nearest_dist = dist

            if nearest is None:
                break

            route.append(nearest)
            assigned.add(nearest)
            current = nearest

        # Calcular estadísticas de la misión
        waypoints = []
        total_distance = 0
        total_frp = 0
        prev_lat = priority_clusters[route[0]]["centroid_lat"]
        prev_lon = priority_clusters[route[0]]["centroid_lon"]

        for idx in route:
            c = priority_clusters[idx]
            dist_from_prev = _haversine_km(prev_lat, prev_lon, c["centroid_lat"], c["centroid_lon"])
            total_distance += dist_from_prev
            total_frp += c["total_frp_mw"]

            # Tiempo de observación sugerido por severidad
            obs_minutes = 15 if c["severity"] == "CRÍTICO" else 10 if c["severity"] == "ALTO" else 5

            waypoints.append({
                "order": len(waypoints) + 1,
                "cluster_id": c["id"],
                "lat": c["centroid_lat"],
                "lon": c["centroid_lon"],
                "severity": c["severity"],
                "category": c["category"].replace("_", " "),
                "fire_count": c["fire_count"],
                "total_frp_mw": c["total_frp_mw"],
                "area_km2": c["area_km2"],
                "observation_minutes": obs_minutes,
                "distance_from_previous_km": round(dist_from_prev, 1),
                "suggested_altitude_m": 120 if c["severity"] == "CRÍTICO" else 80,
                "camera_mode": "termica+visual" if c["total_frp_mw"] >= 100 else "termica"
            })
            prev_lat = c["centroid_lat"]
            prev_lon = c["centroid_lon"]

        flight_time_min = round((total_distance / drone_speed_kmh) * 60)
        obs_time_min = sum(w["observation_minutes"] for w in waypoints)
        total_mission_min = flight_time_min + obs_time_min

        missions.append({
            "drone_id": drone_id,
            "priority": "ALTA" if any(w["severity"] == "CRÍTICO" for w in waypoints) else "MEDIA",
            "waypoints": waypoints,
            "route_summary": {
                "total_waypoints": len(waypoints),
                "total_distance_km": round(total_distance, 1),
                "estimated_flight_time_min": flight_time_min,
                "estimated_observation_time_min": obs_time_min,
                "total_mission_time_min": total_mission_min,
                "total_frp_covered_mw": round(total_frp, 1),
                "clusters_covered": len(waypoints)
            }
        })

    # Estadísticas generales
    total_covered = sum(m["route_summary"]["clusters_covered"] for m in missions)
    uncovered = len(priority_clusters) - total_covered

    logger.info("Drone deployment: %d missions, %d/%d clusters covered",
                len(missions), total_covered, len(priority_clusters))

    return {
        "status": "plan_generado",
        "summary": {
            "total_clusters_detected": len(all_clusters),
            "priority_clusters": len(priority_clusters),
            "clusters_covered": total_covered,
            "clusters_uncovered": uncovered,
            "drones_deployed": len(missions),
            "total_mission_time_min": sum(m["route_summary"]["total_mission_time_min"] for m in missions)
        },
        "missions": missions,
        "uncovered_note": str(uncovered) + " frentes de menor prioridad no cubiertos por limitacion de drones" if uncovered > 0 else "Todos los frentes prioritarios cubiertos",
        "methodology": "Rutas generadas por algoritmo nearest-neighbor sobre clusters DBSCAN. Prioridad: CRITICO > ALTO > MODERADO. Autonomia dron: " + str(drone_range_km) + "km, velocidad: " + str(drone_speed_kmh) + "km/h."
    }
