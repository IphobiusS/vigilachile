from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime, timezone
import io

def generate_pdf(quakes, fires, risk, ai_report, trends):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    elements = []

    # Colores
    primary = HexColor("#4fc3f7")
    dark = HexColor("#0a0e1a")
    warning = HexColor("#ffd700")
    danger = HexColor("#ff3333")
    gray = HexColor("#5c7a9e")

    # Estilos
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=24, textColor=primary,
        spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold"
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=11, textColor=gray,
        spaceAfter=2, alignment=TA_CENTER
    )
    date_style = ParagraphStyle(
        "Date", parent=styles["Normal"],
        fontSize=10, textColor=gray,
        spaceAfter=16, alignment=TA_CENTER
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        fontSize=13, textColor=primary,
        spaceBefore=16, spaceAfter=8,
        fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#333333"),
        spaceAfter=6, leading=16
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontSize=8, textColor=gray,
        spaceAfter=4
    )

    now_chile = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    # Header
    elements.append(Paragraph("🛰️ VigilaChile", title_style))
    elements.append(Paragraph("Sistema de Monitoreo de Desastres Naturales", subtitle_style))
    elements.append(Paragraph("Reporte Diario — " + now_chile, date_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=primary))
    elements.append(Spacer(1, 12))

    # Resumen ejecutivo
    elements.append(Paragraph("📊 Resumen Ejecutivo", section_style))

    risk_color = HexColor(risk.get("color", "#4fc3f7"))
    summary_data = [
        ["Indicador", "Valor", "Estado"],
        ["Sismos últimas 24h", str(len(quakes)), "Normal" if len(quakes) < 60 else "Elevado"],
        ["Magnitud máxima", str(max([q["magnitude"] for q in quakes], default=0)), ""],
        ["Focos de incendio", str(len(fires)), "Normal" if len(fires) < 5 else "Elevado"],
        ["Índice de riesgo", str(risk.get("score", "--")) + "/10", risk.get("level", "--")],
        ["Tendencia vs ayer", trends.get("trend", "--"), str(trends.get("percentage", 0)) + "%"],
    ]

    summary_table = Table(summary_data, colWidths=[6*cm, 4*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f9ff"), white]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#ccddee")),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ROWHEIGHT", (0, 0), (-1, -1), 20),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    # Análisis IA
    elements.append(Paragraph("🤖 Análisis IA en Tiempo Real", section_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=primary))
    elements.append(Spacer(1, 6))
    if ai_report:
        elements.append(Paragraph(ai_report, body_style))
    else:
        elements.append(Paragraph("Análisis no disponible.", body_style))
    elements.append(Spacer(1, 12))

    # Sismos más relevantes
    elements.append(Paragraph("🌍 Sismos Más Relevantes (M≥4.0)", section_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=primary))
    elements.append(Spacer(1, 6))

    major_quakes = [q for q in quakes if q.get("magnitude", 0) >= 4.0][:15]
    if major_quakes:
        quake_data = [["Magnitud", "Lugar", "Profundidad", "Hora (UTC)"]]
        for q in major_quakes:
            quake_data.append([
                "M" + str(q.get("magnitude", "--")),
                q.get("place", "--")[:45],
                str(q.get("depth", "--")) + " km",
                str(q.get("time", "--"))[:16] if q.get("time") else "--"
            ])

        quake_table = Table(quake_data, colWidths=[2.5*cm, 8*cm, 3*cm, 3.5*cm])
        quake_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f9ff"), white]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#ccddee")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ROWHEIGHT", (0, 0), (-1, -1), 18),
        ]))
        elements.append(quake_table)
    else:
        elements.append(Paragraph("No se registraron sismos de magnitud 4.0 o mayor.", body_style))

    elements.append(Spacer(1, 12))

    # Focos de incendio
    if fires:
        elements.append(Paragraph("🔥 Focos de Calor Activos", section_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ff6b35")))
        elements.append(Spacer(1, 6))
        fire_data = [["Latitud", "Longitud", "Brillo (K)", "Confianza", "Fecha"]]
        for f in fires:
            fire_data.append([
                str(round(f.get("lat", 0), 3)),
                str(round(f.get("lon", 0), 3)),
                str(f.get("brightness", "--")),
                str(f.get("confidence", "--")) + "%",
                str(f.get("date", "--"))
            ])
        fire_table = Table(fire_data, colWidths=[3*cm, 3*cm, 3*cm, 3*cm, 5*cm])
        fire_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#ff6b35")),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#fff5f0"), white]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#ffccaa")),
            ("ROWHEIGHT", (0, 0), (-1, -1), 18),
        ]))
        elements.append(fire_table)
        elements.append(Spacer(1, 12))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=1, color=primary))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Fuentes: Centro Sismológico Nacional (CSN) · Universidad de Chile · NASA FIRMS · USGS",
        small_style
    ))
    elements.append(Paragraph(
        "VigilaChile — Plataforma de Monitoreo de Desastres Naturales en Tiempo Real",
        small_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()