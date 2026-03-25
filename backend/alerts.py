import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASS = os.getenv("GMAIL_PASS", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")

sent_alerts = set()

def send_quake_alert(quake):
    if not GMAIL_USER or not GMAIL_PASS or not ALERT_EMAIL:
        return False

    key = str(quake.get("place", "")) + str(quake.get("time", ""))
    if key in sent_alerts:
        return False
    sent_alerts.add(key)

    subject = "🚨 VigilaChile — Sismo M" + str(quake["magnitude"]) + " — " + quake["place"]

    html = """
    <div style="font-family:Arial,sans-serif;background:#0a0e1a;color:#e0e6f0;padding:32px;border-radius:12px;">
      <h1 style="color:#4fc3f7;margin-bottom:4px;">🛰️ VigilaChile</h1>
      <p style="color:#5c7a9e;margin-top:0">Alerta Sísmica Automática</p>
      <hr style="border-color:#1e2d4a"/>
      <h2 style="color:#ffd700">🌍 Sismo M""" + str(quake["magnitude"]) + """</h2>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:8px;color:#5c7a9e">📍 Lugar</td><td style="padding:8px"><b>""" + str(quake["place"]) + """</b></td></tr>
        <tr><td style="padding:8px;color:#5c7a9e">🕳️ Profundidad</td><td style="padding:8px">""" + str(quake.get("depth", "--")) + """ km</td></tr>
        <tr><td style="padding:8px;color:#5c7a9e">⏱️ Hora UTC</td><td style="padding:8px">""" + str(quake.get("time", "--")) + """</td></tr>
      </table>
      <hr style="border-color:#1e2d4a"/>
      <p style="color:#5c7a9e;font-size:12px">
        Fuente: Centro Sismológico Nacional (CSN) · Universidad de Chile<br>
        VigilaChile — Sistema de Monitoreo de Desastres Naturales
      </p>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = ALERT_EMAIL
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())
        return True
    except Exception as e:
        print("Error enviando email:", e)
        return False