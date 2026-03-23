from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime, timezone
import io

def generate_pdf(quakes, fires, risk, ai_report, trends, volcanoes=None, tsunami=None, weather=None, regions=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    primary = HexColor("#4fc3f7")
    orange_c = HexColor("#ff9500")
    yellow_c = HexColor("#ffd700")
    danger = HexColor("#ff3333")
    fire_c = HexColor("#ff6b35")
    gray = HexColor("#5c7a9e")
    clima_c = HexColor("#6ba3d6")

    title_s = ParagraphStyle("T", parent=styles["Title"], fontSize=24, textColor=primary, spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold")
    sub_s = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11, textColor=gray, spaceAfter=2, alignment=TA_CENTER)
    date_s = ParagraphStyle("Dt", parent=styles["Normal"], fontSize=10, textColor=gray, spaceAfter=16, alignment=TA_CENTER)
    sec_s = ParagraphStyle("Sec", parent=styles["Heading2"], fontSize=13, textColor=primary, spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold")
    body_s = ParagraphStyle("Bd", parent=styles["Normal"], fontSize=10, textColor=HexColor("#333333"), spaceAfter=6, leading=16)
    note_s = ParagraphStyle("Nt", parent=styles["Normal"], fontSize=9, textColor=HexColor("#555555"), spaceAfter=4, leading=14)
    small_s = ParagraphStyle("Sm", parent=styles["Normal"], fontSize=8, textColor=gray, spaceAfter=4)

    now_chile = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    def clean_text(text):
        """Strip any markdown that sneaks through from the AI."""
        if not text:
            return ""
        import re
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # *italic*
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # # headers
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)  # --- lines
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)  # > blockquotes
        text = re.sub(r'^-\s+', '', text, flags=re.MULTILINE)  # - bullets
        text = text.replace('■', '').strip()
        return text

    cell_s = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, textColor=HexColor("#333333"), leading=10)
    cell_s_left = ParagraphStyle("CellL", parent=styles["Normal"], fontSize=8, textColor=HexColor("#333333"), leading=10, alignment=TA_LEFT)

    def make_table(data, widths, header_color):
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f9ff"), white]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#ccddee")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # HEADER
    elements.append(Paragraph("VigilaChile", title_s))
    elements.append(Paragraph("Plataforma de Monitoreo Integral de Desastres Naturales", sub_s))
    elements.append(Paragraph("Reporte Ejecutivo — " + now_chile, date_s))
    elements.append(HRFlowable(width="100%", thickness=1, color=primary))
    elements.append(Spacer(1, 12))

    # RESUMEN EJECUTIVO
    elements.append(Paragraph("Resumen Ejecutivo", sec_s))
    max_mag = max([q["magnitude"] for q in quakes], default=0)
    volc_data = (volcanoes if isinstance(volcanoes, list) else volcanoes.get("data", [])) if volcanoes else []
    volc_alerts = [v for v in volc_data if v.get("alert") != "Verde"]
    tsun_data = (tsunami if isinstance(tsunami, list) else tsunami.get("data", [])) if tsunami else []
    tsun_count = len(tsun_data) if isinstance(tsun_data, list) else 0

    summary = [
        ["Amenaza", "Estado", "Detalle"],
        ["Sismos (24h)", str(len(quakes)) + " eventos", "Mag. max: M" + str(max_mag)],
        ["Incendios", str(len(fires)) + " focos activos", "Normal" if len(fires) < 5 else "Elevado"],
        ["Volcanes", str(len(volc_alerts)) + " en alerta", ", ".join([v["name"] for v in volc_alerts[:3]]) if volc_alerts else "Todos en verde"],
        ["Tsunami", "ALERTA ACTIVA" if tsun_count > 0 else "Sin alertas", "Monitoreo USGS"],
        ["Riesgo compuesto", str(risk.get("score", "--")) + "/10", risk.get("level", "--")],
        ["Tendencia", trends.get("trend", "--"), str(trends.get("percentage", 0)) + "% vs ayer"],
    ]
    elements.append(make_table(summary, [4.5*cm, 4.5*cm, 6*cm], primary))
    elements.append(Spacer(1, 12))

    # ANALISIS IA
    elements.append(Paragraph("Analisis IA en Tiempo Real", sec_s))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=primary))
    elements.append(Spacer(1, 6))
    cleaned_ai = clean_text(ai_report) if ai_report else "Analisis no disponible."
    elements.append(Paragraph(cleaned_ai, body_s))
    elements.append(Spacer(1, 12))

    # SISMOS
    elements.append(Paragraph("Sismos Relevantes (M4.0+)", sec_s))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=primary))
    elements.append(Spacer(1, 6))
    major = [q for q in quakes if q.get("magnitude", 0) >= 4.0][:15]
    if major:
        qd = [["Mag.", "Lugar", "Prof.", "Hora UTC"]]
        for q in major:
            qd.append([
                "M" + str(q.get("magnitude", "--")),
                Paragraph(q.get("place", "--"), cell_s_left),
                str(q.get("depth", "--")) + " km",
                str(q.get("time", "--"))[:16]
            ])
        elements.append(make_table(qd, [2.5*cm, 8*cm, 3*cm, 3.5*cm], primary))
    else:
        elements.append(Paragraph("No se registraron sismos M4.0+ en las ultimas 24 horas.", body_s))
    elements.append(Spacer(1, 10))

    # VOLCANES
    elements.append(Paragraph("Estado Volcanico — SERNAGEOMIN", sec_s))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=yellow_c))
    elements.append(Spacer(1, 6))
    if volc_data:
        vd = [["Volcan", "Region", "Alerta", "Elev.", "Observacion"]]
        for v in volc_data:
            vd.append([
                v.get("name", "--"),
                v.get("region", "--"),
                v.get("alert", "--"),
                str(v.get("elevation", "--")) + " m",
                Paragraph(v.get("description", "--"), cell_s_left)
            ])
        elements.append(make_table(vd, [2.5*cm, 2.5*cm, 1.8*cm, 1.5*cm, 6.7*cm], yellow_c))
    else:
        elements.append(Paragraph("Sin datos de volcanes.", body_s))
    elements.append(Spacer(1, 10))

    # TSUNAMI
    elements.append(Paragraph("Alertas de Tsunami — USGS", sec_s))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=danger))
    elements.append(Spacer(1, 6))
    if isinstance(tsun_data, list) and len(tsun_data) > 0:
        for t in tsun_data:
            elements.append(Paragraph("ALERTA " + str(t.get("level", "")) + " — Sismo M" + str(t.get("magnitude", "")) + " en " + str(t.get("place", "")) + " · Prof: " + str(t.get("depth", "")) + " km", body_s))
    else:
        elements.append(Paragraph("Sin alertas de tsunami activas. Monitoreo continuo de sismos costeros M6.0+ en zona de subduccion chilena.", note_s))
    elements.append(Spacer(1, 10))

    # CLIMA
    elements.append(Paragraph("Clima e Inundaciones — Open-Meteo", sec_s))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=clima_c))
    elements.append(Spacer(1, 6))
    weather_data = (weather if isinstance(weather, list) else weather.get("data", [])) if weather else []
    active_w = [w for w in weather_data if "error" not in w and (w.get("current", {}).get("precipitation_mm", 0) > 0 or w.get("risk", {}).get("score", 0) > 10)]
    if active_w:
        wd = [["Region", "Lluvia", "Acum.24h", "Temp.", "Viento", "Riesgo"]]
        for w in active_w:
            c = w.get("current", {})
            a = w.get("accumulated", {})
            r = w.get("risk", {})
            wd.append([w.get("name", "--"), str(c.get("precipitation_mm", 0)) + " mm/h", str(a.get("last_24h_mm", 0)) + " mm", str(c.get("temperature_c", "--")) + " C", str(c.get("wind_kmh", 0)) + " km/h", r.get("level", "--")])
        elements.append(make_table(wd, [3*cm, 2.5*cm, 2.5*cm, 2*cm, 2.5*cm, 2.5*cm], clima_c))
    else:
        elements.append(Paragraph("Sin precipitaciones significativas. Condiciones meteorologicas normales a nivel nacional.", note_s))
    elements.append(Spacer(1, 10))

    # SEMAFORO REGIONES
    reg_data = (regions if isinstance(regions, list) else regions.get("data", [])) if regions else []
    alert_regs = [r for r in reg_data if r.get("level") not in ("VERDE", None)]
    if alert_regs:
        elements.append(Paragraph("Semaforo Regional", sec_s))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=orange_c))
        elements.append(Spacer(1, 6))
        rd = [["Region", "Alerta", "Sismos 24h", "Mag.max", "Incendios"]]
        for r in sorted(alert_regs, key=lambda x: x.get("score", 0), reverse=True):
            rd.append([r.get("name", "--"), r.get("level", "--"), str(r.get("quakes_24h", 0)), "M" + str(r.get("max_magnitude", 0)), str(r.get("fires_nearby", 0))])
        elements.append(make_table(rd, [4*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm], orange_c))
        elements.append(Spacer(1, 10))

    # INCENDIOS
    if fires:
        elements.append(Paragraph("Focos de Calor — NASA FIRMS", sec_s))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=fire_c))
        elements.append(Spacer(1, 6))
        fd = [["Latitud", "Longitud", "Brillo (K)", "Confianza", "Fecha"]]
        for f in fires[:20]:
            fd.append([str(round(f.get("lat", 0), 3)), str(round(f.get("lon", 0), 3)), str(f.get("brightness", "--")), str(f.get("confidence", "--")) + "%", str(f.get("date", "--"))])
        elements.append(make_table(fd, [3*cm, 3*cm, 3*cm, 3*cm, 5*cm], fire_c))
        elements.append(Spacer(1, 12))

    # FOOTER
    elements.append(HRFlowable(width="100%", thickness=1, color=primary))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Fuentes: CSN · Universidad de Chile · NASA FIRMS · USGS · SERNAGEOMIN · Open-Meteo · SENAPRED", small_s))
    elements.append(Paragraph("VigilaChile — Plataforma de Monitoreo Integral de Desastres Naturales en Tiempo Real", small_s))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
