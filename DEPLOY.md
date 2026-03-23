# 🚀 VigilaChile — Guía de Despliegue

## Estructura del repositorio para deploy

```
vigilachile/
├── backend/
│   ├── main.py
│   ├── fires.py
│   ├── quakes.py
│   ├── risk.py
│   ├── analyzer.py
│   ├── volcanoes.py
│   ├── tsunami.py
│   ├── regions.py
│   ├── alerts.py
│   ├── pdf_report.py
│   ├── weather.py
│   ├── communes.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── manifest.json
│   ├── sw.js
│   ├── icon-192.png
│   ├── icon-512.png
│   └── vercel.json
└── render.yaml
```

---

## PASO 1: Crear repositorio en GitHub

1. Ve a github.com → New Repository
2. Nombre: `vigilachile`
3. Público (necesario para Render/Vercel gratis)
4. NO inicialices con README
5. Desde tu terminal:

```bash
cd C:\Users\Sebastian\geoalert-chile
git init
git add .
git commit -m "VigilaChile v1.0 — Plataforma de monitoreo de desastres"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/vigilachile.git
git push -u origin main
```

**IMPORTANTE:** Crea un archivo `.gitignore` antes del push:
```
backend/venv/
backend/.env
__pycache__/
*.pyc
```

---

## PASO 2: Deploy Backend en Render

1. Ve a https://render.com → Sign up con GitHub
2. Click "New" → "Web Service"
3. Conecta tu repo `vigilachile`
4. Configura:
   - **Name:** `vigilachile-api`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

5. En "Environment Variables" agrega:
   - `ANTHROPIC_API_KEY` = tu API key de Anthropic

6. Click "Create Web Service"
7. Espera ~2-3 minutos a que termine el build
8. Tu URL será: `https://vigilachile-api.onrender.com`
9. Verifica: abre `https://vigilachile-api.onrender.com/health`

**NOTA:** En plan Free, el servicio se duerme tras 15 min sin uso.
La primera visita tras inactividad tarda ~30-50 segundos en despertar.

---

## PASO 3: Deploy Frontend en Vercel

1. Ve a https://vercel.com → Sign up con GitHub
2. Click "Add New" → "Project"
3. Importa tu repo `vigilachile`
4. Configura:
   - **Framework Preset:** Other
   - **Root Directory:** `frontend`
   - **Build Command:** (dejar vacío)
   - **Output Directory:** `.`

5. Click "Deploy"
6. Tu URL será algo como: `https://vigilachile.vercel.app`

**Para URL personalizada:**
- En Settings → Domains → agrega `vigilachile.vercel.app`

---

## PASO 4: Verificar todo funciona

1. Abre `https://vigilachile.vercel.app`
2. Debería cargar el mapa y conectarse al backend en Render
3. Verifica que:
   - Los sismos aparecen en el mapa
   - Los focos de incendio se muestran
   - El análisis IA se genera en el dock inferior
   - El buscador de comunas funciona
   - El PDF se descarga correctamente

---

## PASO 5: Si la URL del backend cambia

El archivo `app.js` auto-detecta el entorno:
- En localhost usa `http://127.0.0.1:8000`
- En producción usa `https://vigilachile-api.onrender.com`

Si tu URL de Render es diferente, edita la línea 3 de `app.js`:
```javascript
: "https://TU-URL-REAL.onrender.com";
```

---

## Troubleshooting

### El backend no arranca en Render
- Verifica que `requirements.txt` tenga todas las dependencias
- Revisa los logs en Render Dashboard → tu servicio → Logs

### La IA no genera reportes
- Verifica que `ANTHROPIC_API_KEY` esté configurada en Render
- El reporte de respaldo (sin IA) funciona automáticamente

### El frontend no conecta al backend
- Verifica que CORS está habilitado (ya lo está con `allow_origins=["*"]`)
- Abre la consola del navegador (F12) para ver errores de red

### El servicio de Render se duerme
- Normal en plan Free — la primera carga tarda ~30-50s
- Para el video pitch: abre la URL 1 minuto antes de grabar
