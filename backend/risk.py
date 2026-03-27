def calculate_risk(quakes, fires):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    cutoff_6h = now - timedelta(hours=6)
    cutoff_24h = now - timedelta(hours=24)

    recent_6h = []
    quakes_24h = []

    for q in quakes:
        try:
            t = datetime.fromisoformat(
                q["time"].replace(" ", "T")
            ).replace(tzinfo=timezone.utc)
            if t > cutoff_24h:
                quakes_24h.append(q)
            if t > cutoff_6h:
                recent_6h.append(q)
        except (ValueError, TypeError, KeyError):
            quakes_24h.append(q)  # si no tiene fecha, incluir igual

    score = 0
    max_mag = max([q["magnitude"] for q in quakes_24h], default=0)

    # Factor magnitud máxima — peso principal
    if max_mag >= 7.5:   score += 60
    elif max_mag >= 7.0: score += 45
    elif max_mag >= 6.5: score += 35
    elif max_mag >= 6.0: score += 20
    elif max_mag >= 5.5: score += 12
    elif max_mag >= 5.0: score += 7
    elif max_mag >= 4.5: score += 3
    elif max_mag >= 4.0: score += 1

    # Factor actividad reciente 6h — secundario
    for q in recent_6h:
        mag = q["magnitude"]
        if mag >= 6.0:   score += 15
        elif mag >= 5.0: score += 6
        elif mag >= 4.0: score += 2
        else:            score += 0.3

    # Factor incendios — ponderado por intensidad (FRP)
    high_frp = sum(1 for f in fires if f.get("frp", 0) >= 20)
    med_frp = sum(1 for f in fires if 5 <= f.get("frp", 0) < 20)
    low_frp = len(fires) - high_frp - med_frp
    fire_score = high_frp * 4 + med_frp * 2 + low_frp * 0.5
    score += min(20, fire_score)

    # Factor volumen general — muy suave para no inflar
    if len(quakes_24h) > 50: score += 3
    elif len(quakes_24h) > 30: score += 2
    elif len(quakes_24h) > 15: score += 1

    # Normalizar a 1-10
    normalized = min(10, max(1, round(score / 8)))

    if normalized <= 2:
        level = "Bajo"
        color = "#22c55e"
        description = "Actividad sísmica normal para Chile. Sin preocupación."
    elif normalized <= 4:
        level = "Moderado-Bajo"
        color = "#4fc3f7"
        description = "Actividad sísmica leve. Dentro del rango habitual para Chile."
    elif normalized <= 6:
        level = "Moderado"
        color = "#ffd700"
        description = "Actividad sísmica sobre el promedio. Mantén precaución."
    elif normalized <= 8:
        level = "Alto"
        color = "#ff9500"
        description = "Actividad sísmica elevada. Revisa tu plan de emergencia."
    else:
        level = "Crítico"
        color = "#ff3333"
        description = "Actividad sísmica crítica. Sigue las instrucciones de SENAPRED."

    return {
        "score": normalized,
        "level": level,
        "color": color,
        "description": description,
        "recent_quakes": len(recent_6h),
        "active_fires": len(fires),
        "max_magnitude": max_mag
    }